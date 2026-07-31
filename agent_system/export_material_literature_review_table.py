from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_literature_review_tools import export_literature_review_table


def main():
    parser = argparse.ArgumentParser(description="Export Agent-07 literature candidates to a human-review CSV table.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--candidates-json", default=None)

    args = parser.parse_args()

    result = export_literature_review_table(
        case_id=args.case_id,
        candidates_json=args.candidates_json,
    )

    print("MATERIAL_LITERATURE_REVIEW_TABLE_CREATED=True")
    print("CASE_ID=" + result.get("case_id", ""))
    print("STATUS=" + result.get("status", ""))
    print("RECORDS_COUNT=" + str(result.get("records_count", 0)))
    print("SOURCE_ERRORS_COUNT=" + str(result.get("source_errors_count", 0)))
    print("REVIEW_TABLE_CSV=" + result.get("review_table_csv", ""))


if __name__ == "__main__":
    main()
