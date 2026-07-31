from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_literature_expansion_tools import expand_material_literature


def main():
    parser = argparse.ArgumentParser(description="Expand material literature search with property-specific queries.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--max-records-per-source", type=int, default=5)

    args = parser.parse_args()

    result = expand_material_literature(
        case_id=args.case_id,
        max_records_per_source=args.max_records_per_source,
    )

    print("MATERIAL_LITERATURE_EXPANSION_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("CASE_ID=" + result.get("case_id", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("ORIGINAL_RECORDS_COUNT=" + str(result.get("original_records_count", 0)))
    print("NEW_RECORDS_COUNT=" + str(result.get("new_records_count", 0)))
    print("EXPANDED_RECORDS_COUNT=" + str(result.get("expanded_records_count", 0)))
    print("SOURCE_ERRORS_COUNT=" + str(len(result.get("source_errors", []))))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
