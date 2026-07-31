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

    norm_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_EQUATION_NORMALIZATION_RESULT.json"
    source_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_SOURCE_LEVEL_LAW_REVIEW.csv"

    out_dir = ROOT / "cases" / case_id / "08_material_review"
    gate_json = out_dir / "AGENT07E_LAW_REVIEW_GATE_RESULT.json"
    review_input_json = out_dir / "AGENT07E_LAW_REVIEW_INPUT.json"

    norm = load_json(norm_json)
    source_rows = read_csv(source_csv)

    usable_sources = [
        row for row in source_rows
        if row.get("source_decision") == "SOURCE_HAS_USABLE_EQUATION"
    ]

    choices = []

    for idx, row in enumerate(usable_sources, start=1):
        choices.append({
            "choice_rank": idx,
            "law_candidate_id": row.get("representative_law_candidate_id", ""),
            "source_key": row.get("source_key", ""),
            "source_title": row.get("source_title", ""),
            "source_url": row.get("source_url", ""),
            "source_doi": row.get("source_doi", ""),
            "source_pmid": row.get("source_pmid", ""),
            "usable_equations": row.get("usable_equations", ""),
            "formula_snippets": row.get("formula_snippets", ""),
            "source_decision": row.get("source_decision", ""),
            "review_note": "Agent-derived source-level density/HU material law candidate."
        })

    if choices:
        gate_status = "WAITING_FOR_AGENT07E_LAW_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    else:
        gate_status = "NO_USABLE_AGENT07E_LAW_CHOICES"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_USABLE_AGENT07E_LAW_CHOICES"]

    gate = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status,
        "next_agent": next_agent,
        "usable_law_choices_count": len(choices),
        "source_equation_normalization_json": str(norm_json),
        "source_level_law_review_csv": str(source_csv),
        "allowed_choices": choices,
        "clinical_use": False,
        "rules": [
            "Only an agent-derived law_candidate_id may be approved.",
            "Manual equations are not allowed.",
            "Manual elastic modulus, Poisson ratio, density, or HU mapping values are not allowed.",
            "Approval opens MATERIAL_LAW_STRUCTURING_AGENT, not GEOMETRY_AGENT directly.",
            "GEOMETRY_AGENT remains blocked until the approved law is converted to a machine-readable material-law package."
        ],
        "blockers": blockers,
    }

    save_json(gate_json, gate)

    review_input = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT07E_DENSITY_HU_LAW_APPROVAL",
        "reviewer_decision": "PENDING",
        "approved_law_candidate_id": "",
        "approved_source_key": "",
        "approved_for_material_law_structuring_agent": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,
        "reviewer_notes": "",
        "source_review_gate_json": str(gate_json),
        "rules": [
            "Do not manually enter or edit equations.",
            "Do not manually enter E, ν, density, or HU mapping values.",
            "Approve only one law_candidate_id from allowed_choices.",
            "Use APPROVED only if the source and equation are acceptable for software pipeline development.",
            "This is not clinical approval."
        ]
    }

    if not review_input_json.exists():
        save_json(review_input_json, review_input)

    print("AGENT07E_LAW_REVIEW_GATE_CREATED=True")
    print("GATE_STATUS=" + gate_status)
    print("NEXT_AGENT=" + next_agent)
    print("USABLE_LAW_CHOICES_COUNT=" + str(len(choices)))
    print("BLOCKERS=" + str(blockers))

    print("\nTOP_CHOICES")
    for choice in choices[:5]:
        print("-" * 80)
        print("RANK=" + str(choice["choice_rank"]))
        print("LAW_CANDIDATE_ID=" + choice["law_candidate_id"])
        print("SOURCE_TITLE=" + choice["source_title"][:220])
        print("SOURCE_URL=" + choice["source_url"][:220])
        print("USABLE_EQUATIONS=" + choice["usable_equations"][:900])


if __name__ == "__main__":
    main()
