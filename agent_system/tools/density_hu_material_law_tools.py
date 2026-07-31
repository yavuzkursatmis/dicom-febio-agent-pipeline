from pathlib import Path
import json
import csv
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def default_material_selection_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_SELECTION_RESULT.json"


def density_hu_search_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_DENSITY_HU.json"


def default_resolved_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_RESOLVED.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "08_material_review"
    return {
        "result_json": out_dir / "AGENT07E_DENSITY_HU_LAW_CANDIDATES.json",
        "csv": out_dir / "AGENT07E_DENSITY_HU_LAW_CANDIDATES.csv",
        "review_json": out_dir / "AGENT07E_DENSITY_HU_LAW_REVIEW.json",
    }


def clean_text(text: str):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text: str):
    text = clean_text(text).lower()
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for a, b in repl.items():
        text = text.replace(a, b)
    return text


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if "cartilage" in t or "meniscus" in t:
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t:
        return "ligament"

    if "muscle" in t:
        return "muscle"

    return normalize(material_domain or "unknown")


def build_density_hu_queries(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    if material_domain != "bone" or family != "spine_vertebra":
        return []

    targets = [
        anatomical_region,
        "vertebral bone",
        "vertebral body",
        "human vertebral body",
        "thoracic vertebra",
        "vertebral cancellous bone",
        "vertebral trabecular bone",
        "spine finite element bone density",
    ]

    query_templates = [
        "{target} CT density elastic modulus finite element",
        "{target} Hounsfield unit elastic modulus bone",
        "{target} apparent density Young modulus",
        "{target} ash density elastic modulus",
        "{target} density modulus relationship bone",
        "{target} density based material properties finite element",
        "{target} CT-based finite element elastic modulus density",
        "{target} heterogeneous material properties CT finite element",
        "{target} Hounsfield density Young's modulus",
    ]

    extra = [
        "vertebral bone density elastic modulus relationship",
        "vertebral trabecular bone apparent density elastic modulus",
        "CT based finite element vertebral bone elastic modulus density",
        "Hounsfield units apparent density elastic modulus vertebral bone",
        "cancellous bone density modulus relationship vertebra",
        "human vertebral trabecular bone density Young modulus",
        "bone mineral density elastic modulus vertebral finite element",
        "Keyak bone density elastic modulus CT finite element",
        "Morgan Keaveny vertebral trabecular bone density elastic modulus",
    ]

    queries = []

    for target in targets:
        for template in query_templates:
            queries.append(template.format(target=target))

    queries.extend(extra)

    cleaned = []
    for q in queries:
        q = " ".join(q.split())
        if q not in cleaned:
            cleaned.append(q)

    return cleaned


def record_key(record: dict):
    doi = normalize(record.get("doi", ""))
    if doi:
        return "doi:" + doi

    url = normalize(record.get("url", ""))
    if url:
        return "url:" + url

    title = normalize(record.get("title", ""))
    return "title:" + title


def deduplicate_records(records: List[Dict[str, Any]]):
    seen = set()
    unique = []

    for r in records:
        key = record_key(r)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return unique


def score_density_hu_record(record: dict, anatomical_region: str, material_domain: str):
    # Query alanı burada kullanılmaz. Kaynağın kendi title/abstract/url/doi içeriği skorlanır.
    text = normalize(" ".join([
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("url", ""),
        record.get("doi", ""),
    ]))

    score = 0
    reasons = []
    blockers = []

    target_terms = [
        "vertebra", "vertebral", "vertebral body",
        "spine", "spinal", "thoracic", "cervical", "lumbar"
    ]

    bone_terms = [
        "bone", "cortical", "cancellous", "trabecular"
    ]

    density_terms = [
        "density", "apparent density", "ash density",
        "bone mineral density", "bmd", "hounsfield", "hounsfield unit", "hu",
        "computed tomography", "ct-based", "ct based"
    ]

    modulus_terms = [
        "elastic modulus", "young modulus", "young's modulus",
        "modulus of elasticity", "material properties",
        "finite element", "linear elastic"
    ]

    formula_terms = [
        "relationship", "equation", "power law", "correlation", "conversion"
    ]

    if any(t in text for t in target_terms):
        score += 5
        reasons.append("target_context")

    if any(t in text for t in bone_terms):
        score += 4
        reasons.append("bone_context")

    if any(t in text for t in density_terms):
        score += 5
        reasons.append("density_or_hu_context")

    if any(t in text for t in modulus_terms):
        score += 5
        reasons.append("modulus_or_fe_context")

    if any(t in text for t in formula_terms):
        score += 2
        reasons.append("relationship_context")

    negative_terms = [
        "steel", "metal", "metals", "aluminum", "aluminium",
        "concrete", "soil", "bentonite", "bridge", "overcrossing",
        "electric properties", "linear electric", "fatigue crack growth",
        "regular polygons"
    ]

    for term in negative_terms:
        if term in text:
            score -= 10
            blockers.append("negative:" + term)

    if record.get("doi") or record.get("url"):
        score += 1
        reasons.append("traceable_source")

    strict_match = (
        any(t in text for t in target_terms)
        and any(t in text for t in bone_terms)
        and any(t in text for t in density_terms)
        and any(t in text for t in modulus_terms)
    )

    return {
        "score": score,
        "reasons": reasons,
        "blockers": blockers,
        "strict_match": strict_match,
    }


def run_density_hu_law_search(case_id: str, max_records_per_source: int = 8):
    from agent_system.tools.material_selection_tools import active_literature_search

    material_path = default_material_selection_json(case_id)
    out_path = density_hu_search_json(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "records": [],
            "records_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(out_path, result)
        return result

    material = load_json(material_path)

    material_domain = material.get("material_domain", "unknown_requires_review")
    anatomical_region = material.get("anatomical_region", "")
    family = infer_target_family(anatomical_region, material_domain)

    queries = build_density_hu_queries(anatomical_region, material_domain)

    if not queries:
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "DENSITY_HU_LAW_SEARCH_NOT_APPLICABLE",
            "anatomical_region": anatomical_region,
            "material_domain": material_domain,
            "target_family": family,
            "records": [],
            "records_count": 0,
            "blockers": ["DENSITY_HU_LAW_SEARCH_NOT_APPLICABLE_TO_THIS_DOMAIN"],
            "clinical_use": False,
        }
        save_json(out_path, result)
        return result

    search_result = active_literature_search(
        queries=queries,
        limit_per_source=max_records_per_source
    )

    raw_records = deduplicate_records(search_result.get("records", []))

    accepted = []
    rejected = []

    for record in raw_records:
        s = score_density_hu_record(record, anatomical_region, material_domain)

        item = dict(record)
        item["density_hu_relevance_score"] = s["score"]
        item["density_hu_relevance_reasons"] = s["reasons"]
        item["density_hu_relevance_blockers"] = s["blockers"]
        item["strict_density_hu_source_match"] = s["strict_match"]

        if (
            s["score"] >= 10
            and s["strict_match"]
            and not any(b.startswith("negative:") for b in s["blockers"])
        ):
            accepted.append(item)
        else:
            rejected.append(item)

    accepted = sorted(accepted, key=lambda x: x.get("density_hu_relevance_score", 0), reverse=True)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "DENSITY_HU_MATERIAL_LAW_SEARCH_COMPLETED",
        "anatomical_region": anatomical_region,
        "material_domain": material_domain,
        "target_family": family,
        "queries": queries,
        "raw_records_count": len(raw_records),
        "records_count": len(accepted),
        "records": accepted,
        "rejected_records_preview": rejected[:40],
        "source_errors": search_result.get("source_errors", []),
        "clinical_use": False,
        "rules": [
            "This search targets CT/HU/density-based bone material law sources.",
            "No material value is assigned here.",
            "Only source title/abstract/url/doi are scored; query leakage is not allowed.",
            "Agent-07E extraction must still derive law candidates from resolved source text."
        ],
        "blockers": [] if accepted else ["NO_DENSITY_HU_MATERIAL_LAW_RECORDS"],
    }

    save_json(out_path, result)
    return result


def context_window(text: str, start: int, window: int = 900):
    a = max(0, start - window)
    b = min(len(text), start + window)
    return clean_text(text[a:b])


def has_any(text: str, terms: List[str]):
    t = normalize(text)
    return [term for term in terms if normalize(term) in t]


def extract_formula_snippets(context: str):
    snippets = []

    patterns = [
        r"\bE\s*=\s*[^.;\n]{0,220}",
        r"\belastic modulus\s*\(?E\)?[^.;\n]{0,260}",
        r"\byoung'?s modulus\s*\(?E\)?[^.;\n]{0,260}",
        r"\bmodulus of elasticity[^.;\n]{0,260}",
        r"\bapparent density\s*=\s*[^.;\n]{0,220}",
        r"\bash density\s*=\s*[^.;\n]{0,220}",
        r"\bdensity\s*=\s*[^.;\n]{0,220}",
        r"\bHU\s*[^.;\n]{0,220}",
        r"\bHounsfield[^.;\n]{0,220}",
        r"\bρ\s*=\s*[^.;\n]{0,220}",
        r"\brho\s*=\s*[^.;\n]{0,220}",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, context, flags=re.I):
            snippet = clean_text(m.group(0))
            if len(snippet) >= 8 and snippet not in snippets:
                snippets.append(snippet)

    return snippets[:10]


def make_law_candidate_id(item: dict):
    raw = "|".join([
        str(item.get("case_id", "")),
        str(item.get("law_family", "")),
        str(item.get("source_title", "")),
        str(item.get("source_doi", "")),
        str(item.get("context_excerpt", ""))[:500],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def score_law_context(context: str, anatomical_region: str, material_domain: str):
    target_terms = [
        "vertebra", "vertebral", "vertebral body",
        "spine", "spinal", "thoracic", "cervical", "lumbar"
    ]

    bone_terms = [
        "bone", "cortical", "cancellous", "trabecular"
    ]

    density_terms = [
        "density", "apparent density", "ash density",
        "bone mineral density", "bmd", "hounsfield", "hounsfield unit",
        "hu", "computed tomography", "ct"
    ]

    modulus_terms = [
        "elastic modulus", "young modulus", "young's modulus",
        "modulus of elasticity", "modulus", "linear elastic"
    ]

    formula_terms = [
        "=", "^", "relationship", "equation", "power law", "correlation", "converted"
    ]

    negative_terms = [
        "steel", "metal", "metals", "aluminum", "aluminium",
        "concrete", "soil", "bentonite", "bridge", "overcrossing",
        "electric properties", "linear electric", "fatigue crack growth",
        "regular polygons"
    ]

    positives = {
        "target": has_any(context, target_terms),
        "bone": has_any(context, bone_terms),
        "density": has_any(context, density_terms),
        "modulus": has_any(context, modulus_terms),
        "formula": has_any(context, formula_terms),
    }

    negatives = has_any(context, negative_terms)

    score = 0
    score += 4 if positives["target"] else 0
    score += 4 if positives["bone"] else 0
    score += 4 if positives["density"] else 0
    score += 4 if positives["modulus"] else 0
    score += 2 if positives["formula"] else 0
    score -= 8 * len(negatives)

    return score, positives, negatives


def run_density_hu_law_extraction(
    case_id: str,
    material_selection_json: Optional[str] = None,
    resolved_literature_json: Optional[str] = None,
):
    material_path = Path(material_selection_json) if material_selection_json else default_material_selection_json(case_id)
    literature_path = Path(resolved_literature_json) if resolved_literature_json else default_resolved_json(case_id)

    paths = output_paths(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "law_candidates_count": 0,
            "complete_law_candidates_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(paths["result_json"], result)
        return result

    if not literature_path.exists():
        result = {
            "case_id": case_id,
            "status": "RESOLVED_LITERATURE_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "law_candidates_count": 0,
            "complete_law_candidates_count": 0,
            "blockers": ["RESOLVED_LITERATURE_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(paths["result_json"], result)
        return result

    material = load_json(material_path)
    literature = load_json(literature_path)

    material_domain = material.get("material_domain", "unknown_requires_review")
    anatomical_region = material.get("anatomical_region", "")
    family = infer_target_family(anatomical_region, material_domain)

    records = literature.get("records", [])

    law_candidates = []

    keywords = [
        "hounsfield", "HU", "computed tomography", "CT",
        "apparent density", "ash density", "bone mineral density",
        "density", "elastic modulus", "young", "modulus"
    ]

    for record in records:
        text = clean_text(" ".join([
            record.get("title", ""),
            record.get("abstract", ""),
        ]))

        lower = text.lower()

        seen_contexts = set()

        for keyword in keywords:
            start = 0
            while True:
                idx = lower.find(keyword.lower(), start)

                if idx < 0:
                    break

                ctx = context_window(text, idx, window=900)
                ctx_key = ctx[:500]

                start = idx + len(keyword)

                if ctx_key in seen_contexts:
                    continue

                seen_contexts.add(ctx_key)

                score, positives, negatives = score_law_context(ctx, anatomical_region, material_domain)

                if negatives:
                    continue

                has_target = bool(positives["target"])
                has_bone = bool(positives["bone"])
                has_density = bool(positives["density"])
                has_modulus = bool(positives["modulus"])

                if not (has_target and has_bone and has_density and has_modulus):
                    continue

                formula_snippets = extract_formula_snippets(ctx)

                has_formula_like_text = bool(formula_snippets)

                law_family = "density_based_heterogeneous"

                candidate = {
                    "law_candidate_id": "",
                    "case_id": case_id,
                    "material_domain": material_domain,
                    "anatomical_region": anatomical_region,
                    "target_family": family,
                    "law_family": law_family,
                    "law_status": "FORMULA_CANDIDATE" if has_formula_like_text else "CONTEXT_CANDIDATE",
                    "complete_law_candidate": bool(has_formula_like_text and has_density and has_modulus),
                    "source": record.get("source", ""),
                    "source_title": record.get("title", ""),
                    "source_year": record.get("year", ""),
                    "source_doi": record.get("doi", ""),
                    "source_url": record.get("url", ""),
                    "source_pmid": record.get("pmid", ""),
                    "source_pmcid": record.get("pmcid", ""),
                    "context_excerpt": ctx[:2000],
                    "formula_snippets": formula_snippets,
                    "context_score": score,
                    "positive_target_terms": positives["target"],
                    "positive_bone_terms": positives["bone"],
                    "positive_density_terms": positives["density"],
                    "positive_modulus_terms": positives["modulus"],
                    "positive_formula_terms": positives["formula"],
                    "negative_terms": negatives,
                    "clinical_use": False,
                }

                candidate["law_candidate_id"] = make_law_candidate_id(candidate)
                law_candidates.append(candidate)

    unique = {}
    for c in law_candidates:
        unique[c["law_candidate_id"]] = c

    law_candidates = sorted(unique.values(), key=lambda x: x.get("context_score", 0), reverse=True)
    complete = [x for x in law_candidates if x.get("complete_law_candidate")]

    if complete:
        status = "DENSITY_HU_LAW_CANDIDATES_AVAILABLE_FOR_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    elif law_candidates:
        status = "DENSITY_HU_CONTEXT_CANDIDATES_NEED_REVIEW"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_COMPLETE_DENSITY_HU_FORMULA_CANDIDATE"]
    else:
        status = "DENSITY_HU_LAW_EXTRACTION_NEEDS_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_DENSITY_HU_LAW_CANDIDATES"]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "target_family": family,
        "source_literature_records_count": len(records),
        "law_candidates_count": len(law_candidates),
        "complete_law_candidates_count": len(complete),
        "law_candidates": law_candidates,
        "source_material_selection_json": str(material_path),
        "source_resolved_literature_json": str(literature_path),
        "clinical_use": False,
        "warnings": [
            "Density/HU-based law candidates are not direct FEBio material assignments.",
            "Human review is required before selecting any law candidate.",
            "If selected, downstream sensitivity analysis remains required."
        ],
        "blockers": blockers,
        "rules": [
            "Manual material values are forbidden.",
            "This extractor searches for density/HU/CT to modulus law candidates.",
            "GEOMETRY_AGENT remains blocked until a source-linked law candidate is approved.",
            "For non-bone tissues, domain-specific material law agents should be used instead."
        ],
    }

    save_json(paths["result_json"], result)
    export_csv(paths["csv"], law_candidates)

    review = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT07E_DENSITY_HU_LAW_REVIEW",
        "reviewer_decision": "PENDING",
        "approved_law_candidate_id": "",
        "approved_for_geometry_agent": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,
        "source_density_hu_law_json": str(paths["result_json"]),
        "rules": [
            "Approve only an agent-derived law_candidate_id.",
            "Do not manually enter equations or material values.",
            "Reject if law candidate is not target/domain appropriate.",
            "Sensitivity analysis is mandatory after approval."
        ],
    }

    if not paths["review_json"].exists():
        save_json(paths["review_json"], review)

    return result
