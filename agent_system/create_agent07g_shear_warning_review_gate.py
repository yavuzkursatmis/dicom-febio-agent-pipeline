from pathlib import Path
import json
import hashlib
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def make_id(raw: str):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def main():
    case_id = "real_dicom_check_001_anon_T1"

    package_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE.json"
    validation_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_VALIDATION_RESULT.json"

    out_dir = ROOT / "cases" / case_id / "08_material_review"
    gate_path = out_dir / "AGENT07G_SHEAR_WARNING_REVIEW_GATE_RESULT.json"
    review_input_path = out_dir / "AGENT07G_SHEAR_WARNING_REVIEW_INPUT.json"

    package = load_json(package_path)
    validation = load_json(validation_path)

    warnings = validation.get("warnings", [])
    law = package.get("structured_law", {})
    shear_relations = law.get("shear_modulus_relations", [])

    blockers = []
    candidates = []

    has_shear_conflict = any("SHEAR_SCALE_CONFLICT" in str(w) for w in warnings)

    if not has_shear_conflict:
        blockers.append("NO_SHEAR_SCALE_CONFLICT_WARNING_FOUND")

    gxy_primary = None
    raw_conflict_scale = None
    raw_relations = []

    for relation in shear_relations:
        raw_relations.append(relation)

        if relation.get("variable") == "Gxy" and not relation.get("warning"):
            gxy_primary = relation.get("scale_factor")

        if relation.get("warning") and "variables" in relation:
            vars_ = relation.get("variables", [])
            if "Gxy" in vars_ and "Gyz" in vars_:
                raw_conflict_scale = relation.get("scale_factor")

    if gxy_primary is None:
        blockers.append("PRIMARY_GXY_SCALE_NOT_FOUND")

    if raw_conflict_scale is None:
        blockers.append("RAW_CONFLICT_SCALE_NOT_FOUND")

    if not blockers:
        resolved = {
            "Gxy": gxy_primary,
            "Gxz": raw_conflict_scale,
            "Gyz": raw_conflict_scale,
        }

        raw_for_id = json.dumps({
            "case_id": case_id,
            "package_id": package.get("material_law_package_id", ""),
            "approved_law_candidate_id": package.get("approved_law_candidate_id", ""),
            "raw_relations": raw_relations,
            "resolved": resolved,
        }, sort_keys=True, ensure_ascii=False)

        candidate_id = make_id(raw_for_id)

        candidates.append({
            "resolution_candidate_id": candidate_id,
            "resolution_type": "AGENT_DERIVED_OCR_DISAMBIGUATION_ORTHOTROPIC_SHEAR",
            "resolved_shear_scales": resolved,
            "source_raw_shear_relations": raw_relations,
            "reasoning_summary": (
                "Source text contains one explicit Gxy relation and one duplicated/conflicting raw relation. "
                "For an orthotropic vertebral bone law, the agent proposes preserving Gxy=0.121Ez and interpreting "
                "the second paired relation as Gxz=Gyz=0.157Ez, subject to human source review."
            ),
            "manual_values_entered": False,
            "clinical_use": False,
        })

    if candidates:
        gate_status = "WAITING_FOR_AGENT07G_SHEAR_RESOLUTION_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
    else:
        gate_status = "NO_VALID_SHEAR_RESOLUTION_CANDIDATE"
        next_agent = "USER_ACTION_REQUIRED"

    gate = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status,
        "next_agent": next_agent,
        "allowed_resolution_candidates": candidates,
        "source_material_law_package": str(package_path),
        "source_validation_result": str(validation_path),
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "Manual shear values are forbidden.",
            "Manual equations are forbidden.",
            "Only an agent-derived resolution_candidate_id may be approved.",
            "Approval resolves the warning for pipeline development only.",
            "This is not clinical approval."
        ],
    }

    save_json(gate_path, gate)

    review_input = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT07G_SHEAR_WARNING_RESOLUTION_APPROVAL",
        "reviewer_decision": "PENDING",
        "approved_resolution_candidate_id": "",
        "approved_for_agent08": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,
        "reviewer_notes": "",
        "source_review_gate_json": str(gate_path),
        "rules": [
            "Approve only one resolution_candidate_id from allowed_resolution_candidates.",
            "Do not manually enter Gxy, Gxz, Gyz, E, density, HU, or Poisson values.",
            "Approval allows Agent-08 only after final validation package is created.",
            "This approval is for software pipeline development, not clinical use."
        ],
    }

    if not review_input_path.exists():
        save_json(review_input_path, review_input)

    print("AGENT07G_SHEAR_WARNING_REVIEW_GATE_CREATED=True")
    print("GATE_STATUS=" + gate_status)
    print("NEXT_AGENT=" + next_agent)
    print("RESOLUTION_CANDIDATES_COUNT=" + str(len(candidates)))
    print("BLOCKERS=" + str(blockers))

    if candidates:
        top = candidates[0]
        print("TOP_RESOLUTION_CANDIDATE_ID=" + top["resolution_candidate_id"])
        print("TOP_RESOLUTION_TYPE=" + top["resolution_type"])
        print("TOP_RESOLVED_SHEAR_SCALES=" + str(top["resolved_shear_scales"]))
        print("TOP_REASONING=" + top["reasoning_summary"])


if __name__ == "__main__":
    main()
