from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.targeted_literature_quality_filter import filter_targeted_literature


def main():
    parser = argparse.ArgumentParser(description="Filter and rank target-specific material literature before full-text extraction.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--min-score", type=int, default=8)
    parser.add_argument("--max-records", type=int, default=60)

    args = parser.parse_args()

    result = filter_targeted_literature(
        case_id=args.case_id,
        input_json=args.input_json,
        min_score=args.min_score,
        max_records=args.max_records,
    )

    print("TARGETED_LITERATURE_QUALITY_FILTER_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("ORIGINAL_RECORDS_COUNT=" + str(result.get("original_records_count", 0)))
    print("FILTERED_RECORDS_COUNT=" + str(result.get("filtered_records_count", 0)))
    print("REJECTED_RECORDS_COUNT=" + str(result.get("rejected_records_count", 0)))
    print("BLOCKERS=" + str(result.get("blockers", [])))

    records = result.get("records", [])
    if records:
        top = records[0]
        print("TOP_SCORE=" + str(top.get("quality_score", "")))
        print("TOP_TITLE=" + str(top.get("title", "")))
        print("TOP_URL=" + str(top.get("url", "")))
        print("TOP_REASONS=" + str(top.get("quality_reasons", [])))
    else:
        print("TOP_SCORE=")
        print("TOP_TITLE=")
        print("TOP_URL=")
        print("TOP_REASONS=")


if __name__ == "__main__":
    main()
