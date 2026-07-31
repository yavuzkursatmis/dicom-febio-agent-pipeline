from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_review_gate_tools import build_material_review_gate


def main():
    parser = argparse.ArgumentParser(description="Create dynamic Material Review Gate files")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--material-selection-json", default=None)

    args = parser.parse_args()

    result = build_material_review_gate(
        case_id=args.case_id,
        material_selection_json=args.material_selection_json,
    )

    print("MATERIAL_REVIEW_GATE_CREATED=True")
    print("CASE_ID=" + result.get("case_id", ""))
    print("MATERIAL_REVIEW_STATUS=" + result.get("material_review_status", ""))
    print("APPROVED=" + str(result.get("approved", False)))
    print("APPROVED_NEXT_AGENT=" + result.get("approved_next_agent", ""))
    print("MISSING_REQUIRED_PARAMETERS=" + str(result.get("missing_required_parameters", [])))
    print("ANATOMICAL_TARGET=" + result.get("dynamic_source", {}).get("anatomical_target", ""))
    print("MATERIAL_DOMAIN=" + result.get("dynamic_source", {}).get("material_domain", ""))
    print("LITERATURE_RECORDS_COUNT=" + str(result.get("dynamic_source", {}).get("literature_records_count", "")))


if __name__ == "__main__":
    main()
