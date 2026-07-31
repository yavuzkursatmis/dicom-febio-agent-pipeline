from pathlib import Path
import json
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


def default_original_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES.json"


def expanded_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_EXPANDED.json"


def load_extraction_config():
    return load_json(ROOT / "agent_system" / "configs" / "material_extraction_config.json")


def record_key(record: dict):
    doi = str(record.get("doi", "")).strip().lower()
    if doi:
        return "doi:" + doi

    url = str(record.get("url", "")).strip().lower()
    if url:
        return "url:" + url

    title = str(record.get("title", "")).strip().lower()
    return "title:" + title


def deduplicate_records(records):
    seen = set()
    unique = []

    for r in records:
        key = record_key(r)
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return unique


def build_property_specific_queries(anatomical_region: str, material_domain: str, config: dict):
    domain_terms = config.get("domain_keyword_profiles", {}).get(material_domain, [])

    if not domain_terms:
        domain_terms = [material_domain]

    queries = []

    base_targets = [anatomical_region] + domain_terms[:8]

    for target in base_targets:
        if not target:
            continue

        queries.extend([
            f'{target} Young modulus Poisson ratio',
            f'{target} elastic modulus Poisson ratio finite element',
            f'{target} material properties Young modulus Poisson ratio',
            f'{target} biomechanical material properties Poisson ratio',
            f'{target} linear elastic properties finite element',
        ])

    if material_domain == "bone":
        queries.extend([
            f'{anatomical_region} cancellous bone Young modulus Poisson ratio',
            f'{anatomical_region} cortical bone Young modulus Poisson ratio',
            'vertebral cancellous bone Young modulus Poisson ratio finite element',
            'vertebral cortical bone Young modulus Poisson ratio finite element',
            'spine finite element material properties Young modulus Poisson ratio vertebra',
        ])

    if material_domain == "cartilage":
        queries.extend([
            f'{anatomical_region} cartilage compressive modulus Poisson ratio',
            f'{anatomical_region} cartilage elastic modulus Poisson ratio',
            'articular cartilage finite element material properties Poisson ratio',
        ])

    if material_domain == "tendon":
        queries.extend([
            f'{anatomical_region} tendon Young modulus Poisson ratio',
            f'{anatomical_region} tendon tensile modulus finite element',
            'tendon material properties Young modulus Poisson ratio finite element',
        ])

    if material_domain == "ligament":
        queries.extend([
            f'{anatomical_region} ligament Young modulus Poisson ratio',
            f'{anatomical_region} ligament tensile modulus finite element',
            'ligament material properties Young modulus Poisson ratio finite element',
        ])

    if material_domain == "muscle":
        queries.extend([
            f'{anatomical_region} muscle hyperelastic parameters finite element',
            f'{anatomical_region} passive muscle material properties',
            'skeletal muscle hyperelastic Ogden Mooney Rivlin parameters',
        ])

    if material_domain == "implant_material":
        queries.extend([
            f'{anatomical_region} implant material elastic modulus Poisson ratio',
            'Ti6Al4V elastic modulus Poisson ratio biomedical implant',
            'tantalum elastic modulus Poisson ratio orthopedic implant',
        ])

    cleaned = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in cleaned:
            cleaned.append(q)

    return cleaned


def expand_material_literature(case_id: str, max_records_per_source: int = 5):
    from agent_system.tools.material_selection_tools import active_literature_search

    material_path = default_material_selection_json(case_id)
    original_path = default_original_candidates_json(case_id)
    output_path = expanded_candidates_json(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "expanded_records_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(output_path, result)
        return result

    material = load_json(material_path)
    config = load_extraction_config()

    anatomical_region = material.get("anatomical_region", "")
    material_domain = material.get("material_domain", "unknown_requires_review")

    queries = build_property_specific_queries(
        anatomical_region=anatomical_region,
        material_domain=material_domain,
        config=config,
    )

    original_records = []
    original_source_errors = []

    if original_path.exists():
        original_data = load_json(original_path)
        original_records = original_data.get("records", [])
        original_source_errors = original_data.get("source_errors", [])

    search_result = active_literature_search(
        queries=queries,
        limit_per_source=max_records_per_source,
    )

    new_records = search_result.get("records", [])
    new_errors = search_result.get("source_errors", [])

    combined_records = deduplicate_records(original_records + new_records)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "MATERIAL_LITERATURE_EXPANDED",
        "anatomical_region": anatomical_region,
        "material_domain": material_domain,
        "original_records_count": len(original_records),
        "new_records_count": len(new_records),
        "expanded_records_count": len(combined_records),
        "queries": queries,
        "records": combined_records,
        "source_errors": original_source_errors + new_errors,
        "clinical_use": False,
        "rules": [
            "Expanded search is property-specific.",
            "No material value is manually entered.",
            "Agent-07B must still extract source-linked candidate values.",
            "GEOMETRY_AGENT remains blocked until a complete candidate_set is validated."
        ]
    }

    save_json(output_path, result)
    return result
