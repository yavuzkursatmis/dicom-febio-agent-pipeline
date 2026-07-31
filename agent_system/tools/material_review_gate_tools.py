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


def material_review_dir(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review"


def required_missing_parameters(material_result: dict):
    missing = []

    if material_result.get("elastic_modulus_MPa") is None:
        missing.append("elastic_modulus_MPa")

    if material_result.get("poisson_ratio") is None:
        missing.append("poisson_ratio")

    return missing


def source_support_available(material_result: dict):
    selected_sources = material_result.get("selected_sources", [])
    return isinstance(selected_sources, list) and len(selected_sources) > 0


def review_input_contains_user_entered_data(existing: dict):
    """
    Kullanıcı sonradan kaynak destekli parametre girdiyse bu dosya ezilmemelidir.
    Boş/PENDING şablonlar korunmaz; yeniden üretilebilir.
    """
    if not isinstance(existing, dict):
        return False

    if existing.get("elastic_modulus_MPa") is not None:
        return True

    if existing.get("poisson_ratio") is not None:
        return True

    if bool(existing.get("source_supported", False)):
        return True

    if str(existing.get("reviewer_decision", "")).strip().upper() != "PENDING":
        return True

    if bool(existing.get("approved_for_geometry_agent", False)):
        return True

    sources = existing.get("sources", [])
    if isinstance(sources, list):
        for s in sources:
            if not isinstance(s, dict):
                continue
            useful_fields = [
                s.get("title"),
                s.get("doi"),
                s.get("url"),
                s.get("reported_value_or_range"),
                s.get("parameter_supported"),
            ]
            if any(str(x or "").strip() for x in useful_fields):
                return True

    return False


def build_material_review_gate(case_id: str, material_selection_json: str = None):
    material_path = Path(material_selection_json) if material_selection_json else default_material_selection_json(case_id)

    review_dir = material_review_dir(case_id)
    gate_json = review_dir / "MATERIAL_REVIEW_GATE_RESULT.json"
    input_json = review_dir / "MATERIAL_PARAMETER_REVIEW_INPUT.json"

    if not material_path.exists():
        gate = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "material_review_status": "BLOCKED_MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "approved": False,
            "approved_next_agent": "USER_ACTION_REQUIRED",
            "clinical_use": False,
            "preserved_existing_parameter_review_input": False,
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"]
        }
        save_json(gate_json, gate)
        return gate

    material = load_json(material_path)

    anatomical_target = material.get("anatomical_region", "")
    material_domain = material.get("material_domain", "")
    material_model = material.get("material_model", "not_selected")

    missing = required_missing_parameters(material)
    has_sources = source_support_available(material)

    literature_records_count = int(material.get("literature_records_count", 0))
    literature_search_performed = bool(material.get("literature_search_performed", False))
    literature_search_success = bool(material.get("literature_search_success", False))

    if missing:
        review_status = "WAITING_FOR_SOURCE_SUPPORTED_PARAMETERS"
        approved_for_geometry_agent = False
        approved_next_agent = "USER_ACTION_REQUIRED"
        reason = "Required source-supported material parameters are missing."
    elif not has_sources:
        review_status = "WAITING_FOR_TRACEABLE_SOURCES"
        approved_for_geometry_agent = False
        approved_next_agent = "USER_ACTION_REQUIRED"
        reason = "Material parameters exist but traceable source records are missing."
    else:
        review_status = "PENDING_HUMAN_REVIEW_WITH_SOURCE_SUPPORTED_PARAMETERS"
        approved_for_geometry_agent = False
        approved_next_agent = "USER_ACTION_REQUIRED"
        reason = "Source-supported material parameters are available but require human approval."

    preserved_existing_input = False

    parameter_input = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),

        "anatomical_target": anatomical_target,
        "material_domain": material_domain,
        "material_model": material_model if material_model else "not_selected",
        "tissue_assumption": material.get("tissue_assumption", ""),

        "elastic_modulus_MPa": material.get("elastic_modulus_MPa"),
        "poisson_ratio": material.get("poisson_ratio"),
        "density_kg_m3": material.get("density_kg_m3"),

        "source_supported": bool((not missing) and has_sources),
        "selected_value_rationale": material.get("selected_value_rationale", ""),
        "uncertainty_level": material.get("uncertainty_level", "high"),

        "sources": material.get("selected_sources", []),

        "missing_required_parameters": missing,

        "reviewer_decision": "PENDING",
        "approved_for_geometry_agent": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,

        "rules": [
            "Do not enter unsupported test/default values.",
            "At least elastic_modulus_MPa and poisson_ratio must be source-supported before GEOMETRY_AGENT.",
            "Every selected parameter must include a DOI, PubMed link, journal URL, or traceable reference.",
            "If sources disagree widely, uncertainty_level must remain medium or high.",
            "This is not clinical approval."
        ]
    }

    if input_json.exists():
        try:
            existing_input = load_json(input_json)
            if review_input_contains_user_entered_data(existing_input):
                preserved_existing_input = True
            else:
                save_json(input_json, parameter_input)
        except Exception:
            save_json(input_json, parameter_input)
    else:
        save_json(input_json, parameter_input)

    gate = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "material_review_status": review_status,
        "approved": False,
        "review_scope": "Material parameter review after Agent-07 literature search",
        "reason": reason,
        "clinical_use": False,

        "dynamic_source": {
            "source_material_selection_json": str(material_path),
            "anatomical_target": anatomical_target,
            "material_domain": material_domain,
            "material_model": material_model,
            "literature_search_performed": literature_search_performed,
            "literature_search_success": literature_search_success,
            "literature_records_count": literature_records_count,
            "material_selection_status": material.get("material_selection_status", ""),
            "agent07_next_agent": material.get("next_agent", "")
        },

        "missing_required_parameters": missing,

        "current_parameters": {
            "elastic_modulus_MPa": material.get("elastic_modulus_MPa"),
            "poisson_ratio": material.get("poisson_ratio"),
            "density_kg_m3": material.get("density_kg_m3")
        },

        "required_before_next_stage": [
            "Source-supported elastic_modulus_MPa",
            "Source-supported poisson_ratio",
            "Material model assumption",
            "Traceable literature source",
            "Reviewer approval"
        ],

        "approved_for_geometry_agent": approved_for_geometry_agent,
        "approved_next_agent": approved_next_agent,
        "preserved_existing_parameter_review_input": preserved_existing_input,

        "review_notes": [
            "This file was generated dynamically from Agent-07 output.",
            "Existing user-entered material review input is preserved if it contains reviewed values or traceable sources.",
            "No geometry or FEBio model should be generated before source-supported material parameters are approved.",
            "Test/default material values are not allowed as final analysis parameters.",
            "This is not clinical approval."
        ],

        "warnings": material.get("warnings", []),
        "blockers": material.get("blockers", [])
    }

    save_json(gate_json, gate)

    return gate
