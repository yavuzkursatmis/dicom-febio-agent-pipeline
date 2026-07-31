from pathlib import Path
import json
import csv
import re
import hashlib
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional

import requests

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_material_selection_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_SELECTION_RESULT.json"


def default_targeted_literature_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "08_material_review"
    return {
        "json": out_dir / "AGENT07C_FULLTEXT_MATERIAL_CANDIDATES.json",
        "csv": out_dir / "AGENT07C_FULLTEXT_MATERIAL_CANDIDATES.csv",
        "sets_csv": out_dir / "AGENT07C_FULLTEXT_CANDIDATE_SETS.csv",
        "fetch_log": out_dir / "AGENT07C_FULLTEXT_FETCH_LOG.json",
    }


def normalize(text: str):
    if not text:
        return ""
    text = str(text).lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str, keep_newlines: bool = False):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\r\n|\r", "\n", text)

    if keep_newlines:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_to_text(html: str):
    if not html:
        return ""

    html = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.I | re.S)

    # Table and block tags become line breaks so table-like rows survive.
    html = re.sub(r"</(tr|p|div|li|table|section|h1|h2|h3|h4)>", "\n", html, flags=re.I)
    html = re.sub(r"<(br|br/|br\s*/)>", "\n", html, flags=re.I)

    html = re.sub(r"<[^>]+>", " ", html)
    return clean_text(html, keep_newlines=True)


def extract_pdf_links(html: str, base_url: str, max_links: int = 3):
    if not html:
        return []

    links = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        href = m.group(1)
        if ".pdf" in href.lower():
            full = urljoin(base_url, href)
            if full not in links:
                links.append(full)

    return links[:max_links]


def extract_pdf_text(content: bytes, max_pages: int = 30):
    try:
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        pages = []

        for page in reader.pages[:max_pages]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue

        return clean_text("\n".join(pages), keep_newlines=True)

    except Exception:
        return ""


def fetch_url_text(url: str, timeout: int = 20, max_pdf_links: int = 2):
    result = {
        "url": url,
        "status": "NOT_FETCHED",
        "main_text": "",
        "pdf_links": [],
        "pdf_texts_count": 0,
        "error": "",
    }

    if not url:
        result["status"] = "EMPTY_URL"
        return result

    try:
        headers = {"User-Agent": "dicom-febio-agent-agent07c/0.1"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()

        content_type = r.headers.get("content-type", "").lower()

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            result["main_text"] = extract_pdf_text(r.content)
            result["status"] = "PDF_FETCHED"
            return result

        html = r.text
        result["main_text"] = strip_html_to_text(html)
        result["pdf_links"] = extract_pdf_links(html, url, max_links=max_pdf_links)
        result["status"] = "HTML_FETCHED"

        pdf_texts = []
        for pdf_url in result["pdf_links"]:
            try:
                pr = requests.get(pdf_url, headers=headers, timeout=timeout)
                pr.raise_for_status()
                pdf_text = extract_pdf_text(pr.content)
                if pdf_text:
                    pdf_texts.append(pdf_text)
            except Exception:
                continue

        if pdf_texts:
            result["main_text"] = result["main_text"] + "\n\n" + "\n\n".join(pdf_texts)
            result["pdf_texts_count"] = len(pdf_texts)

        return result

    except Exception as e:
        result["status"] = "FETCH_FAILED"
        result["error"] = f"{type(e).__name__}: {e}"
        return result


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if any(x in t for x in ["femur", "femoral", "hip"]):
        return "femur_hip"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t:
        return "ligament"

    if "cartilage" in t or "meniscus" in t:
        return "cartilage"

    if "muscle" in t:
        return "muscle"

    return normalize(material_domain or "unknown")


def positive_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)
    terms = set()

    for x in re.split(r"[^A-Za-z0-9]+", anatomical_region):
        if len(x) >= 2:
            terms.add(x.lower())

    if family == "spine_vertebra":
        terms.update([
            "vertebra",
            "vertebral",
            "vertebral body",
            "spine",
            "spinal",
            "thoracic",
            "cervical",
            "lumbar",
            "t1",
        ])

    if material_domain == "bone":
        terms.update(["bone", "cortical", "cancellous", "trabecular"])

    if material_domain == "cartilage":
        terms.update(["cartilage", "articular cartilage", "meniscus"])

    if material_domain == "tendon":
        terms.update(["tendon"])

    if material_domain == "ligament":
        terms.update(["ligament", "acl", "pcl"])

    if material_domain == "muscle":
        terms.update(["muscle", "skeletal muscle"])

    return sorted(terms)


def negative_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    animal = [
        "beagle", "canine", "dog", "ovine", "sheep", "bovine", "cow",
        "porcine", "pig", "rat", "rabbit", "mouse", "murine", "goat",
        "equine", "horse"
    ]

    mismatch = []

    if family == "spine_vertebra":
        mismatch = [
            "femoral head", "femur", "femoral", "tibia", "tibial",
            "humerus", "mandible", "skull"
        ]

    return sorted(set(animal + mismatch))


def has_negative_context(text: str, anatomical_region: str, material_domain: str):
    t = normalize(text)
    return [term for term in negative_terms(anatomical_region, material_domain) if normalize(term) in t]


def has_positive_context(text: str, anatomical_region: str, material_domain: str):
    t = normalize(text)
    return [term for term in positive_terms(anatomical_region, material_domain) if normalize(term) in t]


def normalize_unit_to_mpa(value: float, unit: str):
    u = str(unit).replace(" ", "").lower()

    if u == "pa":
        return value / 1_000_000.0

    if u == "kpa":
        return value / 1000.0

    if u == "mpa":
        return value

    if u == "gpa":
        return value * 1000.0

    return value


def infer_unit_from_context(context: str):
    c = normalize(context)

    if "gpa" in c:
        return "GPa"

    if "mpa" in c:
        return "MPa"

    if "kpa" in c:
        return "kPa"

    if re.search(r"\bpa\b", c):
        return "Pa"

    return ""


def context_window(text: str, start: int, window: int = 700):
    a = max(0, start - window)
    b = min(len(text), start + window)
    return clean_text(text[a:b], keep_newlines=False)


def make_candidate_id(candidate: dict):
    raw = "|".join([
        str(candidate.get("case_id", "")),
        str(candidate.get("property_name", "")),
        str(candidate.get("normalized_value", "")),
        str(candidate.get("normalized_unit", "")),
        str(candidate.get("source_title", "")),
        str(candidate.get("source_doi", "")),
        str(candidate.get("context_excerpt", ""))[:300],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_set_id(e_candidate: dict, nu_candidate: dict):
    raw = "|".join([
        e_candidate.get("candidate_id", ""),
        nu_candidate.get("candidate_id", ""),
        e_candidate.get("source_title", ""),
        e_candidate.get("source_doi", ""),
        e_candidate.get("source_url", ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_property_candidate(
    case_id: str,
    record: dict,
    material_domain: str,
    anatomical_region: str,
    property_name: str,
    raw_value,
    raw_unit: str,
    normalized_value,
    normalized_unit: str,
    context_excerpt: str,
    extraction_method: str,
    score: int,
):
    candidate = {
        "candidate_id": "",
        "case_id": case_id,
        "value_origin": "AGENT_DERIVED_FROM_FULLTEXT_OR_TABLE",
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "material_model_family": "linear_elastic_isotropic",
        "property_name": property_name,
        "raw_value": raw_value,
        "raw_unit": raw_unit,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "source": record.get("source", ""),
        "source_title": record.get("title", ""),
        "source_year": record.get("year", ""),
        "source_doi": record.get("doi", ""),
        "source_url": record.get("url", ""),
        "context_excerpt": clean_text(context_excerpt, keep_newlines=False)[:1500],
        "extraction_method": extraction_method,
        "confidence_score": score,
        "uncertainty_level": "medium" if score >= 8 else "high",
        "clinical_use": False,
    }

    candidate["candidate_id"] = make_candidate_id(candidate)
    return candidate


def build_candidate_set(e_candidate: dict, nu_candidate: dict, context_excerpt: str, extraction_method: str):
    confidence = int(e_candidate.get("confidence_score", 0)) + int(nu_candidate.get("confidence_score", 0))

    candidate_set = {
        "candidate_set_id": "",
        "material_model_family": "linear_elastic_isotropic",
        "material_domain": e_candidate.get("material_domain", ""),
        "anatomical_region": e_candidate.get("anatomical_region", ""),
        "elastic_modulus_MPa": e_candidate.get("normalized_value"),
        "poisson_ratio": nu_candidate.get("normalized_value"),
        "density_kg_m3": None,
        "elastic_modulus_candidate_id": e_candidate.get("candidate_id"),
        "poisson_ratio_candidate_id": nu_candidate.get("candidate_id"),
        "source": e_candidate.get("source", ""),
        "source_title": e_candidate.get("source_title", ""),
        "source_year": e_candidate.get("source_year", ""),
        "source_doi": e_candidate.get("source_doi", ""),
        "source_url": e_candidate.get("source_url", ""),
        "context_excerpt": clean_text(context_excerpt, keep_newlines=False)[:1500],
        "extraction_method": extraction_method,
        "confidence_score": confidence,
        "uncertainty_level": "medium" if confidence >= 16 else "high",
        "clinical_use": False,
    }

    candidate_set["candidate_set_id"] = make_set_id(e_candidate, nu_candidate)
    return candidate_set


def score_context(context: str, anatomical_region: str, material_domain: str):
    positives = has_positive_context(context, anatomical_region, material_domain)
    negatives = has_negative_context(context, anatomical_region, material_domain)

    score = 2 + min(len(positives), 6)

    if "poisson" in normalize(context):
        score += 2

    if "young" in normalize(context) or "elastic modulus" in normalize(context):
        score += 2

    if negatives:
        score -= 5 * len(negatives)

    return score, positives, negatives


def extract_paired_candidates_from_text(case_id: str, text: str, record: dict, material_domain: str, anatomical_region: str):
    property_candidates = []
    candidate_sets = []

    e_terms = r"(young'?s modulus|young modulus|elastic modulus|modulus of elasticity|tensile modulus|compressive modulus)"
    nu_terms = r"(poisson'?s ratio|poisson ratio|ν|nu)"
    number = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    unit = r"(Pa|kPa|MPa|GPa)"
    nu_value = r"(0?\.\d+)"

    patterns = [
        rf"{e_terms}[^0-9]{{0,180}}{number}\s*{unit}[\s\S]{{0,350}}?{nu_terms}[^0-9]{{0,80}}{nu_value}",
        rf"{nu_terms}[^0-9]{{0,80}}{nu_value}[\s\S]{{0,350}}?{e_terms}[^0-9]{{0,180}}{number}\s*{unit}",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            ctx = context_window(text, m.start(), window=900)
            score, positives, negatives = score_context(ctx, anatomical_region, material_domain)

            if negatives:
                continue

            values_with_units = re.findall(rf"{number}\s*{unit}", m.group(0), flags=re.I)
            nu_values = re.findall(nu_value, m.group(0))

            if not values_with_units or not nu_values:
                continue

            e_raw = float(values_with_units[0][0])
            e_unit = values_with_units[0][1]
            e_mpa = normalize_unit_to_mpa(e_raw, e_unit)

            # Choose first valid Poisson-like value.
            nu_candidates = [float(x) for x in nu_values if 0.0 < float(x) < 0.5]
            if not nu_candidates:
                continue

            nu = nu_candidates[0]

            if not (0.0001 <= e_mpa <= 300000):
                continue

            e_candidate = build_property_candidate(
                case_id, record, material_domain, anatomical_region,
                "elastic_modulus", e_raw, e_unit, round(e_mpa, 8), "MPa",
                ctx, "fulltext_paired_regex", score
            )

            nu_candidate = build_property_candidate(
                case_id, record, material_domain, anatomical_region,
                "poisson_ratio", nu, "", round(nu, 8), "",
                ctx, "fulltext_paired_regex", score
            )

            property_candidates.extend([e_candidate, nu_candidate])
            candidate_sets.append(
                build_candidate_set(e_candidate, nu_candidate, ctx, "fulltext_paired_regex")
            )

    return property_candidates, candidate_sets


def extract_table_like_candidates(case_id: str, text: str, record: dict, material_domain: str, anatomical_region: str):
    property_candidates = []
    candidate_sets = []

    lines = [clean_text(x, keep_newlines=False) for x in text.splitlines()]
    lines = [x for x in lines if 4 <= len(x) <= 500]

    recent_header = ""

    for idx, line in enumerate(lines):
        low = normalize(line)

        if any(k in low for k in ["young", "elastic modulus", "modulus", "poisson", "material properties"]):
            recent_header = " ".join(lines[max(0, idx - 2): idx + 1])

        context = " ".join(lines[max(0, idx - 4): min(len(lines), idx + 5)])
        context_low = normalize(context)

        if not recent_header:
            continue

        if not any(k in context_low for k in ["poisson", "young", "elastic modulus", "modulus"]):
            continue

        positives = has_positive_context(context, anatomical_region, material_domain)
        negatives = has_negative_context(context, anatomical_region, material_domain)

        if negatives:
            continue

        if not positives:
            continue

        # Line must look like a material row, not a random numerical sentence.
        material_row_terms = [
            "bone", "cortical", "cancellous", "trabecular", "vertebral",
            "cartilage", "tendon", "ligament", "muscle", "soft tissue"
        ]

        if not any(term in context_low for term in material_row_terms):
            continue

        unit = infer_unit_from_context(recent_header + " " + context)
        if not unit:
            continue

        nums = re.findall(r"(?<![A-Za-z0-9])([-+]?\d+(?:\.\d+)?)(?![A-Za-z0-9])", line)
        numeric = [float(x) for x in nums]

        if len(numeric) < 2:
            continue

        possible_nu = [x for x in numeric if 0.0 < x < 0.5]
        possible_e = [x for x in numeric if x > 0.0001 and x not in possible_nu]

        if not possible_e or not possible_nu:
            continue

        e_raw = possible_e[0]
        nu = possible_nu[0]
        e_mpa = normalize_unit_to_mpa(e_raw, unit)

        if not (0.0001 <= e_mpa <= 300000):
            continue

        score, _, _ = score_context(context, anatomical_region, material_domain)
        score += 2

        e_candidate = build_property_candidate(
            case_id, record, material_domain, anatomical_region,
            "elastic_modulus", e_raw, unit, round(e_mpa, 8), "MPa",
            context, "fulltext_table_like_row", score
        )

        nu_candidate = build_property_candidate(
            case_id, record, material_domain, anatomical_region,
            "poisson_ratio", nu, "", round(nu, 8), "",
            context, "fulltext_table_like_row", score
        )

        property_candidates.extend([e_candidate, nu_candidate])
        candidate_sets.append(
            build_candidate_set(e_candidate, nu_candidate, context, "fulltext_table_like_row")
        )

    return property_candidates, candidate_sets


def deduplicate_by_id(items: List[Dict[str, Any]], id_key: str):
    seen = set()
    unique = []

    for item in items:
        key = item.get(id_key)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique


def export_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_fulltext_material_extraction(
    case_id: str,
    material_selection_json: Optional[str] = None,
    literature_candidates_json: Optional[str] = None,
    max_records: int = 40,
    max_pdf_links_per_record: int = 2
):
    material_path = Path(material_selection_json) if material_selection_json else default_material_selection_json(case_id)
    literature_path = Path(literature_candidates_json) if literature_candidates_json else default_targeted_literature_json(case_id)

    paths = output_paths(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "source_literature_records_count": 0,
            "processed_records_count": 0,
            "agent07b_candidates_count": 0,
            "candidate_sets_count": 0,
            "clinical_use": False,
            "warnings": [],
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
        }
        save_json(paths["json"], result)
        return result

    if not literature_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "TARGETED_LITERATURE_CANDIDATES_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "source_literature_records_count": 0,
            "processed_records_count": 0,
            "agent07b_candidates_count": 0,
            "candidate_sets_count": 0,
            "clinical_use": False,
            "warnings": [],
            "blockers": ["TARGETED_LITERATURE_CANDIDATES_NOT_FOUND"],
        }
        save_json(paths["json"], result)
        return result

    material = load_json(material_path)
    literature = load_json(literature_path)

    material_domain = material.get("material_domain", "unknown_requires_review")
    anatomical_region = material.get("anatomical_region", "")

    records = literature.get("records", [])
    records_to_process = records[:max_records]

    all_candidates = []
    all_sets = []
    fetch_log = []

    for idx, record in enumerate(records_to_process, start=1):
        title = record.get("title", "")
        abstract = record.get("abstract", "")
        url = record.get("url", "")

        base_text = clean_text(f"{title}\n{abstract}", keep_newlines=True)

        fetched = fetch_url_text(url, max_pdf_links=max_pdf_links_per_record)
        fetch_log.append({
            "index": idx,
            "title": title,
            "url": url,
            "status": fetched.get("status", ""),
            "main_text_length": len(fetched.get("main_text", "")),
            "pdf_links": fetched.get("pdf_links", []),
            "pdf_texts_count": fetched.get("pdf_texts_count", 0),
            "error": fetched.get("error", ""),
        })

        combined_text = clean_text(base_text + "\n\n" + fetched.get("main_text", ""), keep_newlines=True)

        p_candidates, p_sets = extract_paired_candidates_from_text(
            case_id, combined_text, record, material_domain, anatomical_region
        )

        t_candidates, t_sets = extract_table_like_candidates(
            case_id, combined_text, record, material_domain, anatomical_region
        )

        all_candidates.extend(p_candidates)
        all_candidates.extend(t_candidates)
        all_sets.extend(p_sets)
        all_sets.extend(t_sets)

    all_candidates = deduplicate_by_id(all_candidates, "candidate_id")
    all_sets = deduplicate_by_id(all_sets, "candidate_set_id")

    all_candidates = sorted(all_candidates, key=lambda x: x.get("confidence_score", 0), reverse=True)
    all_sets = sorted(all_sets, key=lambda x: x.get("confidence_score", 0), reverse=True)

    if all_sets:
        status = "FULLTEXT_CANDIDATE_SETS_AVAILABLE_FOR_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    elif all_candidates:
        status = "FULLTEXT_PARTIAL_CANDIDATES_NEED_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_COMPLETE_FULLTEXT_CANDIDATE_SET"]
    else:
        status = "FULLTEXT_CANDIDATE_EXTRACTION_NEEDS_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_FULLTEXT_AGENT_DERIVED_MATERIAL_CANDIDATES"]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "source_literature_records_count": len(records),
        "processed_records_count": len(records_to_process),
        "agent07b_candidates_count": len(all_candidates),
        "candidate_sets_count": len(all_sets),
        "agent07b_candidates": all_candidates,
        "candidate_sets": all_sets,
        "source_material_selection_json": str(material_path),
        "source_literature_candidates_json": str(literature_path),
        "fetch_log_json": str(paths["fetch_log"]),
        "clinical_use": False,
        "warnings": [],
        "blockers": blockers,
        "rules": [
            "No manual material value entry is allowed.",
            "Values must be derived from source text, PDF text, or table-like rows.",
            "Candidate sets still require target relevance validation.",
            "GEOMETRY_AGENT remains blocked unless a target-relevant agent-derived candidate set is approved."
        ],
    }

    save_json(paths["json"], result)
    save_json(paths["fetch_log"], {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "records_processed": len(records_to_process),
        "fetch_log": fetch_log,
        "clinical_use": False,
    })

    export_csv(paths["csv"], all_candidates)
    export_csv(paths["sets_csv"], all_sets)

    return result
