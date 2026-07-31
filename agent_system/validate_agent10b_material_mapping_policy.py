from pathlib import Path
import json
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
    case_id = "real_dicom_check_001_anon_T1"

    gate_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_GATE_RESULT.json"
    review_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_REVIEW_INPUT.json"
    approved_policy_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_APPROVED.json"
    validation_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_VALIDATION_RESULT.json"

    gate = load_json(gate_path)
    review = load_json(review_path)

    blockers = []
    warnings = []

    forbidden_manual_fields = [
        "manual_density", "manual_density_floor", "manual_HU",
        "manual_E", "manual_poisson", "manual_equation",
        "manual_material_value"
    ]

    for key in forbidden_manual_fields:
        if str(review.get(key, "")).strip():
            blockers.append("MANUAL_FIELD_DETECTED:" + key)

    decision = review.get("reviewer_decision", "").strip().upper()
    approved_id = review.get("approved_policy_candidate_id", "").strip()

    if decision != "APPROVED":
        blockers.append("REVIEWER_DECISION_NOT_APPROVED")

    if not approved_id:
        blockers.append("APPROVED_POLICY_CANDIDATE_ID_MISSING")

    allowed = gate.get("allowed_policy_candidates", [])
    matches = [x for x in allowed if x.get("policy_candidate_id") == approved_id]

    if not matches:
        blockers.append("APPROVED_POLICY_CANDIDATE_ID_NOT_ALLOWED")

    if review.get("approved_for_agent10_retry") is not True:
        blockers.append("APPROVED_FOR_AGENT10_RETRY_NOT_TRUE")

    if review.get("clinical_use") is True:
        blockers.append("CLINICAL_USE_MUST_BE_FALSE")

    selected = matches[0] if matches else None

    if selected:
        if float(selected.get("density_floor_g_cm3", 0)) <= 0:
            blockers.append("DENSITY_FLOOR_NOT_POSITIVE")

        if float(selected.get("invalid_density_fraction", 1)) > float(selected.get("max_allowed_invalid_fraction", 0)):
            blockers.append("INVALID_DENSITY_FRACTION_EXCEEDS_ALLOWED_LIMIT")

        if selected.get("manual_values_entered") is True:
            blockers.append("POLICY_MARKED_MANUAL_VALUES_ENTERED")

    if blockers:
        status = "AGENT10B_MAPPING_POLICY_APPROVAL_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        approved_for_agent10_retry = False
    else:
        status = "AGENT10B_MAPPING_POLICY_APPROVED"
        next_agent = "AGENT_10_FEBIO_MODEL_GENERATION_RETRY"
        approved_for_agent10_retry = True

        approved_policy = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "approved": True,
            "approval_status": status,
            "next_agent": next_agent,
            "approved_for_agent10_retry": True,
            "policy_candidate": selected,
            "clinical_use": False,
            "rules": [
                "No manual material values were introduced.",
                "The density floor is computed from the same case and approved HU-density law.",
                "The policy only applies to elements with non-positive density under the approved law.",
                "Agent-10 retry must log the number of corrected elements."
            ],
        }

        save_json(approved_policy_path, approved_policy)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approval_status": status,
        "next_agent": next_agent,
        "approved_for_agent10_retry": approved_for_agent10_retry,
        "approved_policy_candidate_id": approved_id,
        "approved_policy_path": str(approved_policy_path) if approved_for_agent10_retry else "",
        "selected_policy": selected,
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
    }

    save_json(validation_path, result)

    print("AGENT10B_MAPPING_POLICY_VALIDATED=True")
    print("APPROVAL_STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("APPROVED_FOR_AGENT10_RETRY=" + str(approved_for_agent10_retry))
    print("APPROVED_POLICY_CANDIDATE_ID=" + approved_id)
    print("APPROVED_POLICY_PATH=" + result["approved_policy_path"])
    print("WARNINGS=" + str(warnings))
    print("BLOCKERS=" + str(blockers))

    if selected:
        print("SELECTED_POLICY_TYPE=" + selected.get("policy_type", ""))
        print("SELECTED_DENSITY_FLOOR_G_CM3=" + str(selected.get("density_floor_g_cm3", "")))
        print("SELECTED_INVALID_DENSITY_COUNT=" + str(selected.get("invalid_density_count", "")))
        print("SELECTED_INVALID_DENSITY_FRACTION=" + str(selected.get("invalid_density_fraction", "")))


if __name__ == "__main__":
    main()
