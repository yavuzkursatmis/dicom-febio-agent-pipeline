from pathlib import Path
import json
import re
from datetime import datetime

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


def default_expanded_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_EXPANDED.json"


def targeted_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED.json"


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


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if any(x in t for x in ["femur", "femoral", "hip"]):
        return "femur_hip"

    if any(x in t for x in ["tibia", "tibial"]):
        return "tibia"

    if any(x in t for x in ["humerus", "humeral"]):
        return "humerus"

    if "cartilage" in t or "meniscus" in t:
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t:
        return "ligament"

    if "muscle" in t:
        return "muscle"

    return normalize(material_domain or "unknown")


def positive_terms_for_family(target_family: str, anatomical_region: str):
    base = []

    if target_family == "spine_vertebra":
        base = [
            "vertebra",
            "vertebral",
            "vertebral body",
            "spine",
            "spinal",
            "thoracic",
            "cervical",
            "lumbar",
            "T1",
            "human vertebra",
            "human spine"
        ]

    elif target_family == "femur_hip":
        base = [
            "femur",
            "femoral",
            "femoral head",
            "hip"
        ]

    elif target_family == "tibia":
        base = [
            "tibia",
            "tibial"
        ]

    elif target_family == "cartilage":
        base = [
            "cartilage",
            "articular cartilage",
            "meniscus"
        ]

    elif target_family == "tendon":
        base = [
            "tendon"
        ]

    elif target_family == "ligament":
        base = [
            "ligament",
            "ACL",
            "PCL"
        ]

    elif target_family == "muscle":
        base = [
            "muscle",
            "skeletal muscle"
        ]

    else:
        base = [anatomical_region]

    cleaned = []
    for item in [anatomical_region] + base:
        item = " ".join(str(item).split())
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned


def negative_terms_for_family(target_family: str):
    animal_terms = [
        "beagle",
        "canine",
        "dog",
        "ovine",
        "sheep",
        "bovine",
        "cow",
        "porcine",
        "pig",
        "rat",
        "rabbit",
        "mouse",
        "murine",
        "goat",
        "equine",
        "horse"
    ]

    anatomy_mismatch = []

    if target_family == "spine_vertebra":
        anatomy_mismatch = [
            "femoral head",
            "femur",
            "femoral",
            "tibia",
            "tibial",
            "humerus",
            "mandible",
            "skull"
        ]

    return animal_terms + anatomy_mismatch


def record_text(record: dict):
    return normalize(" ".join([
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("url", ""),
        record.get("doi", ""),
        record.get("query", "")
    ]))


def record_matches_target(record: dict, positive_terms: list, negative_terms: list):
    text = record_text(record)

    positive_hit = any(normalize(term) in text for term in positive_terms if term)
    negative_hit = any(normalize(term) in text for term in negative_terms if term)

    return positive_hit and not negative_hit


def record_key(record: dict):
    doi = normalize(record.get("doi", ""))
    if doi:
        return "doi:" + doi

    url = normalize(record.get("url", ""))
    if url:
        return "url:" + url

    title = normalize(record.get("title", ""))
    return "title:" + title


def deduplicate_records(records):
    seen = set()
    unique = []

    for r in records:
        key = record_key(r)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return unique


def build_target_specific_queries(anatomical_region: str, material_domain: str):
    target_family = infer_target_family(anatomical_region, material_domain)
    positive_terms = positive_terms_for_family(target_family, anatomical_region)

    queries = []

    for target in positive_terms[:10]:
        queries.extend([
            f'{target} Young modulus Poisson ratio',
            f'{target} elastic modulus Poisson ratio',
            f'{target} finite element material properties Young modulus Poisson ratio',
            f'{target} linear elastic material properties',
            f'{target} biomechanical material properties',
        ])

    if target_family == "spine_vertebra":
        queries.extend([
            "human vertebral body Young modulus Poisson ratio finite element",
            "human vertebra cancellous bone Young modulus Poisson ratio",
            "human vertebra cortical bone Young modulus Poisson ratio",
            "thoracic vertebra elastic modulus Poisson ratio",
            "spine finite element model vertebral bone Young modulus Poisson ratio",
            "vertebral body material properties finite element elastic modulus Poisson ratio",
        ])

    cleaned = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in cleaned:
            cleaned.append(q)

    return cleaned


def run_target_specific_material_literature_expansion(case_id: str, max_records_per_source: int = 5):
    from agent_system.tools.material_selection_tools import active_literature_search

    material_path = default_material_selection_json(case_id)
    expanded_path = default_expanded_candidates_json(case_id)
    output_path = targeted_candidates_json(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "targeted_records_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(output_path, result)
        return result

    material = load_json(material_path)

    anatomical_region = material.get("anatomical_region", "")
    material_domain = material.get("material_domain", "unknown_requires_review")
    target_family = infer_target_family(anatomical_region, material_domain)

    positive_terms = positive_terms_for_family(target_family, anatomical_region)
    negative_terms = negative_terms_for_family(target_family)

    queries = build_target_specific_queries(
        anatomical_region=anatomical_region,
        material_domain=material_domain,
    )

    previous_records = []
    previous_source_errors = []

    if expanded_path.exists():
        previous_data = load_json(expanded_path)
        previous_records = previous_data.get("records", [])
        previous_source_errors = previous_data.get("source_errors", [])

    search_result = active_literature_search(
        queries=queries,
        limit_per_source=max_records_per_source,
    )

    new_records = search_result.get("records", [])
    new_errors = search_result.get("source_errors", [])

    combined = deduplicate_records(previous_records + new_records)

    target_matched = [
        r for r in combined
        if record_matches_target(r, positive_terms, negative_terms)
    ]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "TARGET_SPECIFIC_MATERIAL_LITERATURE_EXPANDED",
        "anatomical_region": anatomical_region,
        "material_domain": material_domain,
        "target_family": target_family,
        "positive_terms": positive_terms,
        "negative_terms": negative_terms,
        "previous_records_count": len(previous_records),
        "new_records_count": len(new_records),
        "combined_records_count": len(combined),
        "targeted_records_count": len(target_matched),
        "queries": queries,
        "records": target_matched,
        "source_errors": previous_source_errors + new_errors,
        "clinical_use": False,
        "rules": [
            "This expansion is target-specific.",
            "Broad material-domain match is not enough.",
            "Animal and non-target anatomical records are filtered when they conflict with the requested target.",
            "No material value is manually assigned."
        ],
        "blockers": [] if target_matched else ["NO_TARGET_SPECIFIC_LITERATURE_RECORDS"]
    }

    save_json(output_path, result)
    return result
