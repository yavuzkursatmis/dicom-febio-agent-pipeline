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


def default_targeted_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED.json"


def quality_filtered_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED_FILTERED.json"


def normalize(text: str):
    if not text:
        return ""
    text = str(text).lower()
    repl = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c"
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def record_text(record: dict):
    return normalize(" ".join([
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("query", ""),
        record.get("url", ""),
        record.get("doi", "")
    ]))


def score_record(record: dict):
    text = record_text(record)
    title = normalize(record.get("title", ""))

    score = 0
    reasons = []
    blockers = []

    strong_positive = [
        "material properties",
        "material property",
        "finite element model",
        "finite element",
        "young modulus",
        "young's modulus",
        "elastic modulus",
        "poisson ratio",
        "poisson's ratio",
        "linear elastic",
        "vertebral body",
        "vertebral bone",
        "vertebra",
        "spine",
        "spinal",
        "cancellous bone",
        "cortical bone",
        "trabecular bone"
    ]

    for term in strong_positive:
        if term in text:
            score += 2
            reasons.append("positive:" + term)

    target_terms = [
        "vertebra",
        "vertebral",
        "vertebral body",
        "spine",
        "spinal",
        "thoracic",
        "cervical",
        "lumbar",
        "t1"
    ]

    if any(term in text for term in target_terms):
        score += 5
        reasons.append("target_family_match")

    material_terms = [
        "bone",
        "cortical",
        "cancellous",
        "trabecular"
    ]

    if any(term in text for term in material_terms):
        score += 3
        reasons.append("bone_material_match")

    property_pair_terms = [
        ("young", "poisson"),
        ("elastic modulus", "poisson"),
        ("material properties", "finite element"),
        ("linear elastic", "poisson")
    ]

    for a, b in property_pair_terms:
        if a in text and b in text:
            score += 5
            reasons.append("property_pair:" + a + "+" + b)

    hard_negative = [
        "beagle",
        "canine",
        "dog",
        "ovine",
        "sheep",
        "bovine",
        "porcine",
        "rat",
        "rabbit",
        "mouse",
        "mice",
        "murine",
        "femoral head",
        "femur",
        "femoral",
        "bentonite",
        "bridge",
        "overcrossing",
        "electric properties",
        "linear electric",
        "torsion for regular polygons"
    ]

    for term in hard_negative:
        if term in text:
            score -= 10
            blockers.append("negative:" + term)

    weak_negative_title_prefixes = [
        "figure ",
        "table of contents",
        "chapter ",
        "an optimal finite element mesh"
    ]

    for prefix in weak_negative_title_prefixes:
        if title.startswith(prefix):
            score -= 6
            blockers.append("weak_negative_title:" + prefix)

    # Ligament/muscle records are not primary material sources for a bone-domain T1 vertebra case.
    non_bone_soft_tissue_terms = [
        "spinal ligaments",
        "ligament",
        "muscle"
    ]

    for term in non_bone_soft_tissue_terms:
        if term in text and "bone" not in text:
            score -= 4
            blockers.append("non_bone_context:" + term)

    has_trace = bool(record.get("doi") or record.get("url"))
    if has_trace:
        score += 1
        reasons.append("traceable_source")

    return {
        "score": score,
        "reasons": reasons,
        "blockers": blockers
    }


def filter_targeted_literature(case_id: str, input_json: str = None, min_score: int = 8, max_records: int = 60):
    source_path = Path(input_json) if input_json else default_targeted_json(case_id)
    output_path = quality_filtered_json(case_id)

    if not source_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "TARGETED_LITERATURE_NOT_FOUND",
            "records": [],
            "records_count": 0,
            "blockers": ["TARGETED_LITERATURE_JSON_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(output_path, result)
        return result

    data = load_json(source_path)
    records = data.get("records", [])

    scored = []
    rejected = []

    for r in records:
        s = score_record(r)
        enriched = dict(r)
        enriched["quality_score"] = s["score"]
        enriched["quality_reasons"] = s["reasons"]
        enriched["quality_blockers"] = s["blockers"]

        if s["score"] >= min_score and not any(b.startswith("negative:") for b in s["blockers"]):
            scored.append(enriched)
        else:
            rejected.append(enriched)

    scored = sorted(scored, key=lambda x: x.get("quality_score", 0), reverse=True)
    scored = scored[:max_records]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "TARGETED_LITERATURE_QUALITY_FILTERED",
        "source_targeted_json": str(source_path),
        "original_records_count": len(records),
        "filtered_records_count": len(scored),
        "rejected_records_count": len(rejected),
        "records": scored,
        "rejected_records_preview": rejected[:30],
        "source_errors": data.get("source_errors", []),
        "clinical_use": False,
        "rules": [
            "Quality filtering does not assign material values.",
            "Records are ranked before full-text extraction.",
            "Animal, non-target anatomy, and non-biomechanical engineering records are filtered out.",
            "Agent-07C must still extract source-linked values from text."
        ],
        "blockers": [] if scored else ["NO_QUALITY_FILTERED_TARGETED_RECORDS"]
    }

    save_json(output_path, result)
    return result
