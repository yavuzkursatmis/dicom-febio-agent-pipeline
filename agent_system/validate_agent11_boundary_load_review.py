from pathlib import Path
import json
import shutil
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    case_id = "case_real_001_20260716_170655"

    result_path = ROOT / "cases" / case_id / "12_boundary_load_configuration" / "BOUNDARY_LOAD_CONFIGURATION_RESULT.json"
    review_path = ROOT / "cases" / case_id / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_INPUT.json"

    final_model_path = ROOT / "cases" / case_id / "12_boundary_load_configuration" / "febio_model_solver_ready_candidate.feb"
    approval_path = ROOT / "cases" / case_id / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json"

    result = load_json(result_path)
    review = load_json(review_path)

    blockers = []
    warnings = []

    forbidden_manual_fields = [
        "manual_load",
        "manual_force",
        "manual_displacement",
        "manual_boundary_condition",
        "manual_node_set",
        "manual_febio_edit",
    ]

    for key in forbidden_manual_fields:
        if str(review.get(key, "")).strip():
            blockers.append("MANUAL_FIELD_DETECTED:" + key)

    if result.get("boundary_load_status") != "BOUNDARY_LOAD_CONFIGURATION_REVIEW_REQUIRED":
        blockers.append("BOUNDARY_LOAD_STATUS_NOT_REVIEW_REQUIRED")

    if result.get("boundary_candidate_created") is not True:
        blockers.append("BOUNDARY_CANDIDATE_NOT_CREATED")

    candidate_feb = result.get("febio_model_boundary_candidate_path", "")

    if not candidate_feb:
        blockers.append("CANDIDATE_FEBIO_MODEL_PATH_MISSING")
    elif not Path(candidate_feb).exists():
        blockers.append("CANDIDATE_FEBIO_MODEL_FILE_NOT_FOUND")

    if result.get("analysis_type") != "axial_compression":
        blockers.append("ANALYSIS_TYPE_NOT_AXIAL_COMPRESSION")

    if result.get("load_region") != "superior_endplate":
        blockers.append("LOAD_REGION_NOT_SUPERIOR_ENDPLATE")

    if result.get("fixed_node_count", 0) <= 0:
        blockers.append("FIXED_NODE_COUNT_NOT_POSITIVE")

    if result.get("loaded_node_count", 0) <= 0:
        blockers.append("LOADED_NODE_COUNT_NOT_POSITIVE")

    if result.get("prescribed_displacement_mm", 0) >= 0:
        blockers.append("PRESCRIBED_DISPLACEMENT_NOT_COMPRESSIVE_NEGATIVE_Z")

    if result.get("solver_ready") is True:
        warnings.append("SOURCE_RESULT_ALREADY_SOLVER_READY_UNEXPECTED")

    decision = review.get("reviewer_decision", "").strip().upper()

    if decision != "APPROVED":
        blockers.append("REVIEWER_DECISION_NOT_APPROVED")

    if review.get("approved_boundary_load_candidate") is not True:
        blockers.append("APPROVED_BOUNDARY_LOAD_CANDIDATE_NOT_TRUE")

    if review.get("approved_for_solver_configuration") is not True:
        blockers.append("APPROVED_FOR_SOLVER_CONFIGURATION_NOT_TRUE")

    if review.get("approved_next_agent") != "AGENT_12_FEBIO_SOLVER_EXECUTION":
        blockers.append("APPROVED_NEXT_AGENT_MUST_BE_AGENT_12_FEBIO_SOLVER_EXECUTION")

    if review.get("clinical_use") is True:
        blockers.append("CLINICAL_USE_MUST_BE_FALSE")

    if blockers:
        status = "BOUNDARY_LOAD_REVIEW_APPROVAL_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        approved_for_solver = False
    else:
        status = "BOUNDARY_LOAD_REVIEW_APPROVED"
        next_agent = "AGENT_12_FEBIO_SOLVER_EXECUTION"
        approved_for_solver = True
        shutil.copyfile(candidate_feb, final_model_path)

    validation = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approval_status": status,
        "next_agent": next_agent,
        "approved_for_solver_execution": approved_for_solver,
        "source_boundary_load_result": str(result_path),
        "source_review_input": str(review_path),
        "candidate_febio_model_path": candidate_feb,
        "solver_ready_febio_model_path": str(final_model_path) if approved_for_solver else "",
        "analysis_type": result.get("analysis_type", ""),
        "load_region": result.get("load_region", ""),
        "fixed_node_count": result.get("fixed_node_count", 0),
        "loaded_node_count": result.get("loaded_node_count", 0),
        "prescribed_displacement_mm": result.get("prescribed_displacement_mm", 0),
        "load_magnitude_source": result.get("load_magnitude_source", ""),
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "No manual FEBio edits are allowed.",
            "No manual load or displacement value is accepted.",
            "This approval is for protocol-derived boundary/load solver configuration only.",
            "Clinical use remains false.",
            "Solver execution may start only if approved_for_solver_execution is true."
        ],
    }

    save_json(approval_path, validation)

    print("AGENT11_BOUNDARY_LOAD_REVIEW_VALIDATED=True")
    print("APPROVAL_STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("APPROVED_FOR_SOLVER_EXECUTION=" + str(approved_for_solver))
    print("SOLVER_READY_FEBIO_MODEL_PATH=" + validation["solver_ready_febio_model_path"])
    print("PRESCRIBED_DISPLACEMENT_MM=" + str(validation["prescribed_displacement_mm"]))
    print("FIXED_NODE_COUNT=" + str(validation["fixed_node_count"]))
    print("LOADED_NODE_COUNT=" + str(validation["loaded_node_count"]))
    print("WARNINGS=" + str(warnings))
    print("BLOCKERS=" + str(blockers))


if __name__ == "__main__":
    main()

