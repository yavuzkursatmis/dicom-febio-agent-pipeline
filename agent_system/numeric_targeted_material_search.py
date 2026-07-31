from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.numeric_targeted_literature_tools import run_numeric_material_search


def main():
    parser = argparse.ArgumentParser(description="Numeric-targeted material literature search.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--max-records-per-source", type=int, default=8)

    args = parser.parse_args()

    result = run_numeric_material_search(
        case_id=args.case_id,
        max_records_per_source=args.max_records_per_source
    )

    print("NUMERIC_TARGETED_MATERIAL_SEARCH_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("RAW_RECORDS_COUNT=" + str(result.get("raw_records_count", 0)))
    print("RECORDS_COUNT=" + str(result.get("records_count", 0)))
    print("SOURCE_ERRORS_COUNT=" + str(len(result.get("source_errors", []))))
    print("BLOCKERS=" + str(result.get("blockers", [])))

    records = result.get("records", [])
    if records:
        top = records[0]
        print("TOP_SCORE=" + str(top.get("numeric_relevance_score", "")))
        print("TOP_TITLE=" + str(top.get("title", "")))
        print("TOP_URL=" + str(top.get("url", "")))
        print("TOP_REASONS=" + str(top.get("numeric_relevance_reasons", [])))
    else:
        print("TOP_SCORE=")
        print("TOP_TITLE=")
        print("TOP_URL=")
        print("TOP_REASONS=")


if __name__ == "__main__":
    main()
