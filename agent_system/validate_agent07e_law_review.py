from pathlib import Path
import json
import csv
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    case_id = "real_dicom_check_001_anon_T1"

    review_input_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_LAW_REVIEW_INPUT.json"
    gate_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_LAW_REVIEW_GATE_RESULT.json"
    source_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_SOURCE_LEVEL_LAW_REVIEW.csv"

    out_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_LAW_REVIEW_VALIDATION_RESULT.json"

    review = load_json(review_input_json)
    gate = load_json(gate_json)
    source_rows = read_csv(source_csv)

    blockers = []
    warnings = []

    approved_id = review.get("approved_law_candidate_id", "").strip()
    approved_source_key = review.get("approved_source_key", "").strip()
    decision = review.get("reviewer_decision", "").strip().upper()

    forbidden_manual_fields = [
        "manual_equation",
        "manual_elastic_modulus",
        "manual_elastic_modulus_MPa",
        "manual_poisson_ratio",
        "manual_density",
        "manual_hu_mapping",
        "manual_material_value",
    ]

    for key in forbidden_manual_fields:
        if str(review.get(key, "")).strip():
            blockers.append("MANUAL_MATERIAL_OR_EQUATION_FIELD_DETECTED:" + key)

    if decision != "APPROVED":
        blockers.append("REVIEWER_DECISION_NOT_APPROVED")

    if not approved_id:
        blockers.append("APPROVED_LAW_CANDIDATE_ID_MISSING")

    matching_rows = [
        row for row in source_rows
        if row.get("representative_law_candidate_id") == approved_id
        and row.get("source_decision") == "SOURCE_HAS_USABLE_EQUATION"
    ]

    if not matching_rows:
        blockers.append("APPROVED_LAW_CANDIDATE_ID_NOT_IN_USABLE_SOURCE_LIST")

    if approved_source_key:
        matching_key_rows = [
            row for row in matching_rows
            if row.get("source_key") == approved_source_key
        ]

        if not matching_key_rows:
            blockers.append("APPROVED_SOURCE_KEY_DOES_NOT_MATCH_CANDIDATE")
    else:
        warnings.append("APPROVED_SOURCE_KEY_EMPTY_BUT_CANDIDATE_ID_MATCH_CAN_STILL_BE_CHECKED")

    if review.get("approved_for_material_law_structuring_agent") is not True:
        blockers.append("APPROVED_FOR_MATERIAL_LAW_STRUCTURING_AGENT_NOT_TRUE")

    if review.get("approved_next_agent") != "MATERIAL_LAW_STRUCTURING_AGENT":
        blockers.append("APPROVED_NEXT_AGENT_MUST_BE_MATERIAL_LAW_STRUCTURING_AGENT")

    if review.get("clinical_use") is True:
        blockers.append("CLINICAL_USE_MUST_BE_FALSE")

    if blockers:
        status = "AGENT07E_LAW_REVIEW_APPROVAL_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        approved_for_next = False
        selected_source = None
    else:
        status = "AGENT07E_LAW_REVIEW_APPROVED"
        next_agent = "MATERIAL_LAW_STRUCTURING_AGENT"
        approved_for_next = True
        selected_source = matching_rows[0]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approval_status": status,
        "next_agent": next_agent,
        "approved_for_next_agent": approved_for_next,
        "approved_law_candidate_id": approved_id,
        "approved_source_key": approved_source_key,
        "selected_source": selected_source,
        "source_review_input_json": str(review_input_json),
        "source_review_gate_json": str(gate_json),
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "Only source-linked, agent-derived law_candidate_id approval is valid.",
            "Manual equations or manual values invalidate approval.",
            "Approval opens MATERIAL_LAW_STRUCTURING_AGENT only.",
            "GEOMETRY_AGENT remains blocked until structured material law validation is complete."
        ],
    }

    save_json(out_json, result)

    print("AGENT07E_LAW_REVIEW_VALIDATED=True")
    print("APPROVAL_STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("APPROVED_FOR_NEXT_AGENT=" + str(approved_for_next))
    print("APPROVED_LAW_CANDIDATE_ID=" + approved_id)
    print("WARNINGS=" + str(warnings))
    print("BLOCKERS=" + str(blockers))

    if selected_source:
        print("SELECTED_SOURCE_TITLE=" + selected_source.get("source_title", "")[:220])
        print("SELECTED_USABLE_EQUATIONS=" + selected_source.get("usable_equations", "")[:900])


if __name__ == "__main__":
    main()
