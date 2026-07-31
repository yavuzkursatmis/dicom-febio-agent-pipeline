from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_review_approval_tools import validate_material_review_input


def main():
    parser = argparse.ArgumentParser(description="Validate source-supported material review input")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--review-input-json", default=None)

    args = parser.parse_args()

    result = validate_material_review_input(
        case_id=args.case_id,
        review_input_json=args.review_input_json,
    )

    print("MATERIAL_REVIEW_APPROVAL_VALIDATED=True")
    print("CASE_ID=" + result.get("case_id", ""))
    print("MATERIAL_REVIEW_APPROVAL_STATUS=" + result.get("material_review_approval_status", ""))
    print("APPROVED=" + str(result.get("approved", False)))
    print("APPROVED_NEXT_AGENT=" + result.get("approved_next_agent", ""))
    print("VALID_TRACEABLE_SOURCE_COUNT=" + str(result.get("valid_traceable_source_count", 0)))
    print("ELASTIC_MODULUS_MPA=" + str(result.get("validated_parameters", {}).get("elastic_modulus_MPa", "")))
    print("POISSON_RATIO=" + str(result.get("validated_parameters", {}).get("poisson_ratio", "")))
    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
