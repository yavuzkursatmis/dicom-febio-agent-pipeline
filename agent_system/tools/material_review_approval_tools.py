from pathlib import Path
import json
import math
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_review_input_json(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "MATERIAL_PARAMETER_REVIEW_INPUT.json"


def default_approval_json(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "MATERIAL_REVIEW_APPROVAL_RESULT.json"


def is_number(value):
    if value is None:
        return False
    try:
        value = float(value)
        return math.isfinite(value)
    except Exception:
        return False


def has_traceable_source(source: dict):
    title = str(source.get("title", "")).strip()
    doi = str(source.get("doi", "")).strip()
    url = str(source.get("url", "")).strip()
    parameter_supported = str(source.get("parameter_supported", "")).strip()
    reported = str(source.get("reported_value_or_range", "")).strip()

    if not title:
        return False

    if not parameter_supported:
        return False

    if not reported:
        return False

    if doi or url:
        return True

    return False


def validate_material_review_input(case_id: str, review_input_json: str = None):
    input_path = Path(review_input_json) if review_input_json else default_review_input_json(case_id)
    output_path = default_approval_json(case_id)

    if not input_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "material_review_approval_status": "MATERIAL_REVIEW_INPUT_NOT_FOUND",
            "approved": False,
            "approved_next_agent": "USER_ACTION_REQUIRED",
            "clinical_use": False,
            "warnings": [],
            "blockers": ["MATERIAL_PARAMETER_REVIEW_INPUT_NOT_FOUND"]
        }
        save_json(output_path, result)
        return result

    data = load_json(input_path)

    warnings = []
    blockers = []

    elastic_modulus = data.get("elastic_modulus_MPa")
    poisson_ratio = data.get("poisson_ratio")
    density = data.get("density_kg_m3")

    if not is_number(elastic_modulus):
        blockers.append("ELASTIC_MODULUS_MPA_MISSING_OR_INVALID")
    elif float(elastic_modulus) <= 0:
        blockers.append("ELASTIC_MODULUS_MPA_MUST_BE_POSITIVE")

    if not is_number(poisson_ratio):
        blockers.append("POISSON_RATIO_MISSING_OR_INVALID")
    elif not (0.0 < float(poisson_ratio) < 0.5):
        blockers.append("POISSON_RATIO_OUT_OF_VALID_LINEAR_ELASTIC_RANGE")

    if density is not None:
        if not is_number(density):
            warnings.append("DENSITY_KG_M3_INVALID_IGNORED")
        elif float(density) <= 0:
            warnings.append("DENSITY_KG_M3_NON_POSITIVE_IGNORED")

    material_model = str(data.get("material_model", "")).strip()
    if not material_model or material_model == "not_selected":
        blockers.append("MATERIAL_MODEL_NOT_SELECTED")

    if not bool(data.get("source_supported", False)):
        blockers.append("SOURCE_SUPPORTED_FALSE")

    sources = data.get("sources", [])
    if not isinstance(sources, list) or len(sources) == 0:
        blockers.append("NO_SOURCES_PROVIDED")
        valid_sources = []
    else:
        valid_sources = [s for s in sources if isinstance(s, dict) and has_traceable_source(s)]

    if len(valid_sources) == 0:
        blockers.append("NO_TRACEABLE_SOURCE_FOR_PARAMETERS")

    reviewer_decision = str(data.get("reviewer_decision", "")).strip().upper()
    if reviewer_decision != "APPROVED":
        blockers.append("REVIEWER_DECISION_NOT_APPROVED")

    if not bool(data.get("approved_for_geometry_agent", False)):
        blockers.append("APPROVED_FOR_GEOMETRY_AGENT_FALSE")

    if str(data.get("approved_next_agent", "")).strip() != "GEOMETRY_AGENT":
        blockers.append("APPROVED_NEXT_AGENT_NOT_GEOMETRY_AGENT")

    if blockers:
        status = "MATERIAL_REVIEW_APPROVAL_FAIL"
        approved = False
        approved_next_agent = "USER_ACTION_REQUIRED"
    else:
        status = "MATERIAL_REVIEW_APPROVAL_PASS"
        approved = True
        approved_next_agent = "GEOMETRY_AGENT"

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "material_review_approval_status": status,
        "approved": approved,
        "approved_next_agent": approved_next_agent,
        "clinical_use": False,

        "validated_parameters": {
            "anatomical_target": data.get("anatomical_target", ""),
            "material_domain": data.get("material_domain", ""),
            "material_model": material_model,
            "tissue_assumption": data.get("tissue_assumption", ""),
            "elastic_modulus_MPa": elastic_modulus,
            "poisson_ratio": poisson_ratio,
            "density_kg_m3": density
        },

        "source_supported": bool(data.get("source_supported", False)),
        "valid_traceable_source_count": len(valid_sources),
        "sources": valid_sources,

        "selected_value_rationale": data.get("selected_value_rationale", ""),
        "uncertainty_level": data.get("uncertainty_level", "high"),

        "warnings": warnings,
        "blockers": blockers,

        "source_review_input_json": str(input_path)
    }

    save_json(output_path, result)
    return result
