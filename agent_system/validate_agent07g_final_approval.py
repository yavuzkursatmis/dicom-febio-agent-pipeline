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

    package_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE.json"
    gate_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07G_SHEAR_WARNING_REVIEW_GATE_RESULT.json"
    review_input_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07G_SHEAR_WARNING_REVIEW_INPUT.json"

    final_package_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"
    final_validation_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_FINAL_VALIDATION_RESULT.json"

    package = load_json(package_path)
    gate = load_json(gate_path)
    review = load_json(review_input_path)

    blockers = []
    warnings = []

    forbidden_manual_fields = [
        "manual_Gxy", "manual_Gxz", "manual_Gyz",
        "manual_shear_values", "manual_equation",
        "manual_E", "manual_density", "manual_HU", "manual_poisson"
    ]

    for key in forbidden_manual_fields:
        if str(review.get(key, "")).strip():
            blockers.append("MANUAL_FIELD_DETECTED:" + key)

    decision = review.get("reviewer_decision", "").strip().upper()
    approved_id = review.get("approved_resolution_candidate_id", "").strip()

    if decision != "APPROVED":
        blockers.append("REVIEWER_DECISION_NOT_APPROVED")

    if not approved_id:
        blockers.append("APPROVED_RESOLUTION_CANDIDATE_ID_MISSING")

    allowed = gate.get("allowed_resolution_candidates", [])
    matches = [x for x in allowed if x.get("resolution_candidate_id") == approved_id]

    if not matches:
        blockers.append("APPROVED_RESOLUTION_CANDIDATE_ID_NOT_ALLOWED")

    if review.get("approved_for_agent08") is not True:
        blockers.append("APPROVED_FOR_AGENT08_NOT_TRUE")

    if review.get("approved_next_agent") != "AGENT_08_GEOMETRY_MESH_PREPARATION":
        blockers.append("APPROVED_NEXT_AGENT_MUST_BE_AGENT_08_GEOMETRY_MESH_PREPARATION")

    if review.get("clinical_use") is True:
        blockers.append("CLINICAL_USE_MUST_BE_FALSE")

    selected = matches[0] if matches else None

    if selected:
        resolved = selected.get("resolved_shear_scales", {})

        required = ["Gxy", "Gxz", "Gyz"]
        for key in required:
            value = resolved.get(key)
            if value is None:
                blockers.append("RESOLVED_SHEAR_SCALE_MISSING:" + key)
            else:
                try:
                    value = float(value)
                    if value <= 0:
                        blockers.append("RESOLVED_SHEAR_SCALE_NOT_POSITIVE:" + key)
                except Exception:
                    blockers.append("RESOLVED_SHEAR_SCALE_NOT_NUMERIC:" + key)

    if blockers:
        status = "AGENT07G_FINAL_APPROVAL_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        approved_for_agent08 = False
        selected_resolution = None
    else:
        status = "AGENT07G_FINAL_APPROVAL_PASS"
        next_agent = "AGENT_08_GEOMETRY_MESH_PREPARATION"
        approved_for_agent08 = True
        selected_resolution = selected

        final_package = dict(package)
        final_package["status"] = "MATERIAL_LAW_VALIDATED_WITH_HUMAN_REVIEWED_WARNING"
        final_package["next_agent"] = "AGENT_08_GEOMETRY_MESH_PREPARATION"
        final_package["approved_for_agent08"] = True
        final_package["finalized_at"] = datetime.now().isoformat(timespec="seconds")
        final_package["validated_package_source"] = str(package_path)
        final_package["human_reviewed_warning_resolution"] = selected_resolution
        final_package["structured_law"]["resolved_shear_scales"] = selected_resolution["resolved_shear_scales"]
        final_package["rules_after_final_validation"] = [
            "Manual values were not introduced.",
            "Agent-derived shear warning resolution was approved by human review.",
            "This package may be consumed by Agent-08 for geometry/mesh preparation metadata.",
            "Sensitivity analysis remains mandatory downstream."
        ]

        save_json(final_package_path, final_package)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "final_approval_status": status,
        "next_agent": next_agent,
        "approved_for_agent08": approved_for_agent08,
        "approved_resolution_candidate_id": approved_id,
        "selected_resolution": selected_resolution,
        "final_validated_material_law_package": str(final_package_path) if approved_for_agent08 else "",
        "source_review_input_json": str(review_input_path),
        "source_gate_json": str(gate_path),
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "Only an agent-derived resolution candidate can pass.",
            "Manual values or equations invalidate approval.",
            "Passing this gate closes Agent-07 and opens Agent-08.",
            "This remains non-clinical pipeline-development approval."
        ],
    }

    save_json(final_validation_path, result)

    print("AGENT07G_FINAL_APPROVAL_VALIDATED=True")
    print("FINAL_APPROVAL_STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("APPROVED_FOR_AGENT08=" + str(approved_for_agent08))
    print("APPROVED_RESOLUTION_CANDIDATE_ID=" + approved_id)
    print("FINAL_VALIDATED_MATERIAL_LAW_PACKAGE=" + result["final_validated_material_law_package"])
    print("WARNINGS=" + str(warnings))
    print("BLOCKERS=" + str(blockers))

    if selected_resolution:
        print("SELECTED_RESOLVED_SHEAR_SCALES=" + str(selected_resolution.get("resolved_shear_scales", {})))


if __name__ == "__main__":
    main()
