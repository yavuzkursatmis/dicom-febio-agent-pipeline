from pathlib import Path
import json
import csv
import re
import hashlib
from datetime import datetime
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


def load_config():
    path = ROOT / "agent_system" / "configs" / "material_extraction_config.json"
    return load_json(path)


def default_material_selection_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_SELECTION_RESULT.json"


def default_literature_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "08_material_review"
    return {
        "json": out_dir / "AGENT07B_MATERIAL_CANDIDATES.json",
        "csv": out_dir / "AGENT07B_MATERIAL_CANDIDATES.csv",
        "review": out_dir / "AGENT07B_CANDIDATE_REVIEW.json",
    }


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_url_text(url: str, timeout: int = 20, max_chars: int = 120000) -> str:
    if not url:
        return ""

    try:
        headers = {"User-Agent": "dicom-febio-agent-agent07b/0.1"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()

        content_type = r.headers.get("content-type", "").lower()

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return extract_pdf_text(r.content, max_chars=max_chars)

        return clean_text(r.text)[:max_chars]

    except Exception:
        return ""


def extract_pdf_text(content: bytes, max_chars: int = 120000) -> str:
    try:
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        pages = []

        for page in reader.pages[:20]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue

        return clean_text(" ".join(pages))[:max_chars]

    except Exception:
        return ""


def normalize_unit(value: float, unit: str):
    u = str(unit).replace(" ", "").lower()

    if u == "pa":
        return value / 1_000_000.0, "MPa"

    if u == "kpa":
        return value / 1000.0, "MPa"

    if u == "mpa":
        return value, "MPa"

    if u == "gpa":
        return value * 1000.0, "MPa"

    if u in ["kg/m3", "kg/m^3"]:
        return value, "kg/m3"

    if u in ["g/cm3", "g/cm^3"]:
        return value * 1000.0, "kg/m3"

    return value, unit


def make_candidate_id(candidate: dict):
    raw = "|".join([
        str(candidate.get("case_id", "")),
        str(candidate.get("material_domain", "")),
        str(candidate.get("material_model_family", "")),
        str(candidate.get("property_name", "")),
        str(candidate.get("normalized_value", "")),
        str(candidate.get("normalized_unit", "")),
        str(candidate.get("source_title", "")),
        str(candidate.get("source_doi", "")),
        str(candidate.get("context_excerpt", ""))[:300],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def source_key(record: dict):
    doi = str(record.get("doi", "")).strip().lower()
    if doi:
        return doi

    url = str(record.get("url", "")).strip().lower()
    title = str(record.get("title", "")).strip().lower()

    return url or title


def get_domain_terms(material_domain: str, config: dict) -> List[str]:
    profiles = config.get("domain_keyword_profiles", {})
    return profiles.get(material_domain, []) + profiles.get("soft_tissue", [])


def extract_context(text: str, position: int, window: int = 450):
    start = max(0, position - window)
    end = min(len(text), position + window)
    return clean_text(text[start:end])


def domain_context_score(context: str, material_domain: str, config: dict):
    text = context.lower()
    terms = [t.lower() for t in get_domain_terms(material_domain, config)]
    score = 0

    for term in terms:
        if term and term in text:
            score += 1

    return min(score, 5)


def extract_linear_elastic_candidates(
    case_id: str,
    text: str,
    record: dict,
    material_domain: str,
    anatomical_region: str,
    config: dict
):
    candidates = []

    property_patterns = {
        "elastic_modulus": [
            r"young'?s modulus",
            r"young modulus",
            r"elastic modulus",
            r"tensile modulus",
            r"compressive modulus",
            r"modulus of elasticity",
            r"\bE\b"
        ],
        "poisson_ratio": [
            r"poisson'?s ratio",
            r"poisson ratio",
            r"\bnu\b",
            r"ν"
        ],
        "density": [
            r"\bdensity\b",
            r"apparent density",
            r"ash density"
        ]
    }

    value_unit = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(Pa|kPa|MPa|GPa|kg/m3|kg/m\^3|g/cm3|g/cm\^3)"

    for property_name, patterns in property_patterns.items():
        for p in patterns:
            if property_name == "poisson_ratio":
                regexes = [
                    rf"({p})[^0-9]{{0,120}}(0\.\d+)",
                    rf"(0\.\d+)[^A-Za-z0-9]{{0,120}}({p})"
                ]
            elif property_name == "density":
                regexes = [
                    rf"({p})[^0-9]{{0,160}}{value_unit}",
                    rf"{value_unit}[^A-Za-z0-9]{{0,160}}({p})"
                ]
            else:
                regexes = [
                    rf"({p})[^0-9]{{0,160}}{value_unit}",
                    rf"{value_unit}[^A-Za-z0-9]{{0,160}}({p})"
                ]

            for rgx in regexes:
                for m in re.finditer(rgx, text, flags=re.I):
                    context = extract_context(text, m.start())

                    if property_name == "poisson_ratio":
                        values = re.findall(r"0\.\d+", m.group(0))
                        if not values:
                            continue
                        raw_value = float(values[0])
                        raw_unit = ""
                        normalized_value = raw_value
                        normalized_unit = ""
                        if not (0.0 < normalized_value < 0.5):
                            continue
                    else:
                        vals = re.findall(value_unit, m.group(0), flags=re.I)
                        if not vals:
                            continue
                        raw_value = float(vals[0][0])
                        raw_unit = vals[0][1]
                        normalized_value, normalized_unit = normalize_unit(raw_value, raw_unit)

                        if property_name == "elastic_modulus":
                            if not (0.0001 <= normalized_value <= 300000):
                                continue

                        if property_name == "density":
                            if not (1 <= normalized_value <= 30000):
                                continue

                    score = 2 + domain_context_score(context, material_domain, config)

                    if property_name in ["elastic_modulus", "poisson_ratio"]:
                        score += 2

                    candidate = {
                        "candidate_id": "",
                        "case_id": case_id,
                        "value_origin": "AGENT_DERIVED_FROM_LITERATURE_TEXT",
                        "material_domain": material_domain,
                        "anatomical_region": anatomical_region,
                        "material_model_family": "linear_elastic_isotropic",
                        "property_name": property_name,
                        "raw_value": raw_value,
                        "raw_unit": raw_unit,
                        "normalized_value": round(float(normalized_value), 8),
                        "normalized_unit": normalized_unit,
                        "source": record.get("source", ""),
                        "source_title": record.get("title", ""),
                        "source_year": record.get("year", ""),
                        "source_doi": record.get("doi", ""),
                        "source_url": record.get("url", ""),
                        "context_excerpt": context,
                        "extraction_method": "general_regex_property_value_context",
                        "confidence_score": score,
                        "uncertainty_level": "medium" if score >= 6 else "high",
                        "clinical_use": False
                    }

                    candidate["candidate_id"] = make_candidate_id(candidate)
                    candidates.append(candidate)

    return candidates



def get_allowed_model_families(material_domain: str, config: dict):
    policy = config.get("domain_model_policy", {})
    domain_policy = policy.get(material_domain, {})
    return domain_policy.get("preferred_model_families", [])


def context_has_explicit_hyperelastic_model(context: str):
    t = context.lower()
    required_terms = [
        "hyperelastic",
        "neo-hookean",
        "neo hookean",
        "mooney-rivlin",
        "mooney rivlin",
        "ogden",
        "yeoh"
    ]
    return any(term in t for term in required_terms)


def hyperelastic_allowed_for_domain(material_domain: str, context: str, config: dict):
    allowed = get_allowed_model_families(material_domain, config)

    if "hyperelastic" not in allowed:
        return False

    domain_policy = config.get("domain_model_policy", {}).get(material_domain, {})
    allow_without_explicit = bool(domain_policy.get("allow_hyperelastic_without_explicit_model_term", False))

    if allow_without_explicit:
        return True

    return context_has_explicit_hyperelastic_model(context)

def extract_hyperelastic_candidates(
    case_id: str,
    text: str,
    record: dict,
    material_domain: str,
    anatomical_region: str,
    config: dict
):
    candidates = []

    terms = config.get("material_model_families", {}).get("hyperelastic", {}).get("accepted_property_terms", [])
    if not terms:
        return []

    for term in terms:
        pattern = rf"({re.escape(term)})[^0-9\-+]{{0,80}}([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
        for m in re.finditer(pattern, text, flags=re.I):
            value = float(m.group(2))
            context = extract_context(text, m.start())

            if not hyperelastic_allowed_for_domain(material_domain, context, config):
                continue

            # mu and D1 are too generic unless an explicit hyperelastic model is nearby.
            if str(term).lower() in ["mu", "d1"] and not context_has_explicit_hyperelastic_model(context):
                continue

            score = 2 + domain_context_score(context, material_domain, config)

            candidate = {
                "candidate_id": "",
                "case_id": case_id,
                "value_origin": "AGENT_DERIVED_FROM_LITERATURE_TEXT",
                "material_domain": material_domain,
                "anatomical_region": anatomical_region,
                "material_model_family": "hyperelastic",
                "property_name": term,
                "raw_value": value,
                "raw_unit": "",
                "normalized_value": value,
                "normalized_unit": "",
                "source": record.get("source", ""),
                "source_title": record.get("title", ""),
                "source_year": record.get("year", ""),
                "source_doi": record.get("doi", ""),
                "source_url": record.get("url", ""),
                "context_excerpt": context,
                "extraction_method": "general_regex_hyperelastic_parameter",
                "confidence_score": score,
                "uncertainty_level": "high",
                "clinical_use": False
            }

            candidate["candidate_id"] = make_candidate_id(candidate)
            candidates.append(candidate)

    return candidates


def deduplicate_candidates(candidates: List[Dict[str, Any]]):
    seen = set()
    unique = []

    for c in candidates:
        key = (
            c.get("material_domain"),
            c.get("material_model_family"),
            c.get("property_name"),
            c.get("normalized_value"),
            c.get("normalized_unit"),
            c.get("source_doi") or c.get("source_url") or c.get("source_title"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(c)

    return unique


def group_candidate_sets(candidates: List[Dict[str, Any]]):
    """
    Aynı kaynak içinde linear elastic için E + Poisson birlikte varsa candidate_set üretir.
    Geometry Agent için ileride tek tek property değil, candidate_set onaylanacak.
    """
    groups = {}

    for c in candidates:
        if c.get("material_model_family") != "linear_elastic_isotropic":
            continue

        key = (
            c.get("source_doi") or c.get("source_url") or c.get("source_title"),
            c.get("material_domain"),
            c.get("anatomical_region")
        )
        groups.setdefault(key, []).append(c)

    sets = []

    for key, items in groups.items():
        e_items = [x for x in items if x.get("property_name") == "elastic_modulus"]
        nu_items = [x for x in items if x.get("property_name") == "poisson_ratio"]

        if not e_items or not nu_items:
            continue

        best_e = sorted(e_items, key=lambda x: x.get("confidence_score", 0), reverse=True)[0]
        best_nu = sorted(nu_items, key=lambda x: x.get("confidence_score", 0), reverse=True)[0]

        set_raw = "|".join([
            best_e.get("candidate_id", ""),
            best_nu.get("candidate_id", ""),
            best_e.get("source_title", "")
        ])
        set_id = hashlib.sha256(set_raw.encode("utf-8")).hexdigest()[:16]

        sets.append({
            "candidate_set_id": set_id,
            "material_model_family": "linear_elastic_isotropic",
            "material_domain": best_e.get("material_domain", ""),
            "anatomical_region": best_e.get("anatomical_region", ""),
            "elastic_modulus_MPa": best_e.get("normalized_value"),
            "poisson_ratio": best_nu.get("normalized_value"),
            "elastic_modulus_candidate_id": best_e.get("candidate_id"),
            "poisson_ratio_candidate_id": best_nu.get("candidate_id"),
            "source_title": best_e.get("source_title", ""),
            "source_doi": best_e.get("source_doi", ""),
            "source_url": best_e.get("source_url", ""),
            "confidence_score": best_e.get("confidence_score", 0) + best_nu.get("confidence_score", 0),
            "uncertainty_level": "medium",
            "clinical_use": False
        })

    return sorted(sets, key=lambda x: x.get("confidence_score", 0), reverse=True)


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


def run_general_material_extraction(
    case_id: str,
    material_selection_json: Optional[str] = None,
    literature_candidates_json: Optional[str] = None,
    fetch_full_text: bool = True
):
    config = load_config()

    material_path = Path(material_selection_json) if material_selection_json else default_material_selection_json(case_id)
    literature_path = Path(literature_candidates_json) if literature_candidates_json else default_literature_candidates_json(case_id)

    paths = output_paths(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "agent07b_candidates_count": 0,
            "candidate_sets_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(paths["json"], result)
        return result

    if not literature_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "MATERIAL_LITERATURE_CANDIDATES_NOT_FOUND",
            "agent07b_candidates_count": 0,
            "candidate_sets_count": 0,
            "blockers": ["MATERIAL_LITERATURE_CANDIDATES_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(paths["json"], result)
        return result

    material = load_json(material_path)
    literature = load_json(literature_path)

    material_domain = material.get("material_domain", "unknown_requires_review")
    anatomical_region = material.get("anatomical_region", "")

    if material_domain not in config.get("supported_material_domains", []):
        material_domain = "unknown_requires_review"

    records = literature.get("records", [])

    all_candidates = []
    fetch_notes = []

    for record in records:
        text_parts = [
            record.get("title", ""),
            record.get("abstract", "")
        ]

        if fetch_full_text:
            fetched = fetch_url_text(record.get("url", ""))
            if fetched:
                text_parts.append(fetched)
                fetch_notes.append({
                    "source_title": record.get("title", ""),
                    "source_url": record.get("url", ""),
                    "fetched_text_length": len(fetched)
                })

        combined_text = clean_text(" ".join(text_parts))

        all_candidates.extend(
            extract_linear_elastic_candidates(
                case_id=case_id,
                text=combined_text,
                record=record,
                material_domain=material_domain,
                anatomical_region=anatomical_region,
                config=config,
            )
        )

        all_candidates.extend(
            extract_hyperelastic_candidates(
                case_id=case_id,
                text=combined_text,
                record=record,
                material_domain=material_domain,
                anatomical_region=anatomical_region,
                config=config,
            )
        )

    all_candidates = deduplicate_candidates(all_candidates)
    all_candidates = sorted(all_candidates, key=lambda x: x.get("confidence_score", 0), reverse=True)

    candidate_sets = group_candidate_sets(all_candidates)

    if len(candidate_sets) > 0:
        status = "MATERIAL_CANDIDATE_SETS_AVAILABLE_FOR_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
    elif len(all_candidates) > 0:
        status = "MATERIAL_PARTIAL_CANDIDATES_NEED_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"
    else:
        status = "MATERIAL_CANDIDATE_EXTRACTION_NEEDS_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "fetch_full_text": fetch_full_text,
        "source_literature_records_count": len(records),
        "agent07b_candidates_count": len(all_candidates),
        "candidate_sets_count": len(candidate_sets),
        "agent07b_candidates": all_candidates,
        "candidate_sets": candidate_sets,
        "source_material_selection_json": str(material_path),
        "source_literature_candidates_json": str(literature_path),
        "fetch_notes_count": len(fetch_notes),
        "fetch_notes": fetch_notes[:20],
        "clinical_use": False,
        "rules": [
            "Manual material value entry is not allowed.",
            "Human reviewer may approve or reject only agent-derived candidate_set_id or candidate_id.",
            "GEOMETRY_AGENT requires validated approval of an agent-derived candidate_set_id.",
            "No fallback or test material values are assigned."
        ],
        "warnings": [],
        "blockers": [] if len(candidate_sets) > 0 else ["NO_COMPLETE_AGENT_DERIVED_MATERIAL_CANDIDATE_SET"]
    }

    save_json(paths["json"], result)
    export_csv(paths["csv"], all_candidates)

    review = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT07B_CANDIDATE_SET_APPROVAL",
        "reviewer_decision": "PENDING",
        "approved_candidate_set_id": "",
        "approved_candidate_id": "",
        "approved_for_geometry_agent": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,
        "source_agent07b_candidates_json": str(paths["json"]),
        "rules": [
            "Do not manually enter numeric material values.",
            "Approve only an agent-derived candidate_set_id when possible.",
            "If no complete candidate_set exists, request more evidence or keep pending.",
            "GEOMETRY_AGENT is allowed only after validator confirms approved candidate exists."
        ]
    }

    if not paths["review"].exists():
        save_json(paths["review"], review)

    return result





