from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.target_specific_material_literature_tools import run_target_specific_material_literature_expansion


def main():
    parser = argparse.ArgumentParser(description="Target-specific material literature expansion.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--max-records-per-source", type=int, default=5)

    args = parser.parse_args()

    result = run_target_specific_material_literature_expansion(
        case_id=args.case_id,
        max_records_per_source=args.max_records_per_source,
    )

    print("TARGET_SPECIFIC_MATERIAL_LITERATURE_EXPANSION_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("CASE_ID=" + result.get("case_id", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("TARGET_FAMILY=" + result.get("target_family", ""))
    print("PREVIOUS_RECORDS_COUNT=" + str(result.get("previous_records_count", 0)))
    print("NEW_RECORDS_COUNT=" + str(result.get("new_records_count", 0)))
    print("COMBINED_RECORDS_COUNT=" + str(result.get("combined_records_count", 0)))
    print("TARGETED_RECORDS_COUNT=" + str(result.get("targeted_records_count", 0)))
    print("SOURCE_ERRORS_COUNT=" + str(len(result.get("source_errors", []))))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
