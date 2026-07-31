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


def numeric_targeted_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_NUMERIC_TARGETED.json"


def normalize(text: str):
    if not text:
        return ""
    text = str(text).lower()
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if any(x in t for x in ["femur", "femoral", "hip"]):
        return "femur_hip"

    if "cartilage" in t or "meniscus" in t:
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t:
        return "ligament"

    if "muscle" in t:
        return "muscle"

    return normalize(material_domain or "unknown")


def build_numeric_queries(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    queries = []

    base_targets = [anatomical_region]

    if family == "spine_vertebra":
        base_targets += [
            "vertebral body",
            "vertebral bone",
            "human vertebra",
            "human vertebral body",
            "thoracic vertebra",
            "spine finite element vertebral bone"
        ]

    elif material_domain == "cartilage":
        base_targets += [
            "articular cartilage",
            "cartilage finite element"
        ]

    elif material_domain == "tendon":
        base_targets += [
            "tendon tensile modulus",
            "tendon finite element material properties"
        ]

    elif material_domain == "ligament":
        base_targets += [
            "ligament tensile modulus",
            "ligament finite element material properties"
        ]

    elif material_domain == "muscle":
        base_targets += [
            "skeletal muscle hyperelastic parameters",
            "passive muscle material properties"
        ]

    elif material_domain == "implant_material":
        base_targets += [
            "Ti6Al4V elastic modulus Poisson ratio",
            "tantalum elastic modulus Poisson ratio"
        ]

    for target in base_targets:
        queries.extend([
            f'{target} Young modulus Poisson ratio MPa',
            f'{target} elastic modulus Poisson ratio MPa',
            f'{target} material properties table Young modulus Poisson ratio',
            f'{target} finite element material properties table',
            f'{target} linear elastic material properties Poisson',
            f'{target} Young modulus MPa Poisson',
            f'{target} elastic modulus GPa Poisson ratio'
        ])

    if family == "spine_vertebra":
        queries.extend([
            'vertebral cancellous bone Young modulus Poisson ratio MPa',
            'vertebral cortical bone Young modulus Poisson ratio MPa',
            'cancellous bone vertebra elastic modulus Poisson ratio',
            'cortical bone vertebra elastic modulus Poisson ratio',
            'finite element spine material properties table cortical cancellous bone',
            'vertebral body finite element material properties table elastic modulus Poisson',
            'human vertebral trabecular bone Young modulus Poisson ratio'
        ])

    cleaned = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in cleaned:
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


def deduplicate(records):
    seen = set()
    unique = []

    for r in records:
        key = record_key(r)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return unique


def score_numeric_relevance(record: dict, anatomical_region: str, material_domain: str):
    # IMPORTANT:
    # Do not include record["query"] in scoring.
    # Query text can create false target/property matches even when the source itself is irrelevant.
    text = normalize(" ".join([
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("url", ""),
        record.get("doi", "")
    ]))

    score = 0
    reasons = []
    blockers = []

    positive_terms = [
        "young modulus",
        "young's modulus",
        "elastic modulus",
        "poisson",
        "poisson ratio",
        "material properties",
        "material property",
        "finite element",
        "linear elastic",
        "mpa",
        "gpa",
        "table"
    ]

    for term in positive_terms:
        if term in text:
            score += 2
            reasons.append("positive:" + term)

    family = infer_target_family(anatomical_region, material_domain)

    if family == "spine_vertebra":
        target_terms = [
            "vertebra",
            "vertebral",
            "vertebral body",
            "spine",
            "spinal",
            "thoracic",
            "cervical",
            "lumbar"
        ]
        if any(t in text for t in target_terms):
            score += 5
            reasons.append("target_family_match")

        negative_terms = [
            "beagle", "canine", "dog", "rat", "rabbit", "mouse", "mice",
            "femoral", "femur", "femoral head", "tibia", "humerus",
            "bentonite", "bridge", "overcrossing", "electric properties"
        ]

        for term in negative_terms:
            if term in text:
                score -= 10
                blockers.append("negative:" + term)

    if record.get("doi") or record.get("url"):
        score += 1
        reasons.append("traceable_source")

    return {
        "score": score,
        "reasons": reasons,
        "blockers": blockers
    }


def run_numeric_material_search(case_id: str, max_records_per_source: int = 8):
    from agent_system.tools.material_selection_tools import active_literature_search

    material_path = default_material_selection_json(case_id)
    output_path = numeric_targeted_json(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "records": [],
            "records_count": 0,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(output_path, result)
        return result

    material = load_json(material_path)

    anatomical_region = material.get("anatomical_region", "")
    material_domain = material.get("material_domain", "unknown_requires_review")

    queries = build_numeric_queries(anatomical_region, material_domain)

    search_result = active_literature_search(
        queries=queries,
        limit_per_source=max_records_per_source
    )

    records = deduplicate(search_result.get("records", []))

    enriched = []
    rejected = []

    for r in records:
        s = score_numeric_relevance(r, anatomical_region, material_domain)
        item = dict(r)
        item["numeric_relevance_score"] = s["score"]
        item["numeric_relevance_reasons"] = s["reasons"]
        item["numeric_relevance_blockers"] = s["blockers"]

        source_text = normalize(" ".join([
            r.get("title", ""),
            r.get("abstract", ""),
            r.get("url", ""),
            r.get("doi", "")
        ]))

        family = infer_target_family(anatomical_region, material_domain)

        if family == "spine_vertebra":
            has_target_context = any(t in source_text for t in [
                "vertebra", "vertebral", "vertebral body", "spine", "spinal",
                "thoracic", "cervical", "lumbar"
            ])
            has_bone_context = any(t in source_text for t in [
                "bone", "cortical", "cancellous", "trabecular"
            ])
            has_property_context = any(t in source_text for t in [
                "young", "young's modulus", "elastic modulus", "modulus of elasticity",
                "poisson", "material properties", "linear elastic", "finite element"
            ])

            strict_source_match = has_target_context and has_bone_context and has_property_context
        else:
            strict_source_match = True

        if (
            s["score"] >= 8
            and strict_source_match
            and not any(b.startswith("negative:") for b in s["blockers"])
        ):
            enriched.append(item)
        else:
            item["strict_source_match"] = strict_source_match
            rejected.append(item)

    enriched = sorted(enriched, key=lambda x: x.get("numeric_relevance_score", 0), reverse=True)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "NUMERIC_TARGETED_MATERIAL_LITERATURE_SEARCH_COMPLETED",
        "anatomical_region": anatomical_region,
        "material_domain": material_domain,
        "queries": queries,
        "raw_records_count": len(records),
        "records_count": len(enriched),
        "records": enriched,
        "rejected_records_preview": rejected[:30],
        "source_errors": search_result.get("source_errors", []),
        "clinical_use": False,
        "rules": [
            "This search targets numeric material-property sources.",
            "No material value is assigned here.",
            "Agent-07C must still extract values from resolved source text.",
            "Manual value entry remains forbidden."
        ],
        "blockers": [] if enriched else ["NO_NUMERIC_TARGETED_LITERATURE_RECORDS"]
    }

    save_json(output_path, result)
    return result
