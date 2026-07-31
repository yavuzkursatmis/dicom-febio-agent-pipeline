from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.literature_resolver_tools import resolve_literature_records


def main():
    parser = argparse.ArgumentParser(description="Resolve PubMed/DOI/PMC abstracts and full text for material literature records.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--max-records", type=int, default=60)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)

    args = parser.parse_args()

    result = resolve_literature_records(
        case_id=args.case_id,
        input_json=args.input_json,
        max_records=args.max_records,
        sleep_seconds=args.sleep_seconds,
    )

    print("LITERATURE_RESOLVER_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("CASE_ID=" + result.get("case_id", ""))
    print("RECORDS_COUNT=" + str(result.get("records_count", 0)))
    print("PROCESSED_RECORDS_COUNT=" + str(result.get("processed_records_count", 0)))
    print("RESOLVED_RECORDS_COUNT=" + str(result.get("resolved_records_count", 0)))
    print("BLOCKERS=" + str(result.get("blockers", [])))

    logs = result.get("resolution_log", [])
    if logs:
        lengths = [int(x.get("resolved_text_length", 0)) for x in logs]
        print("MAX_RESOLVED_TEXT_LENGTH=" + str(max(lengths)))
        print("TEXT_OVER_1000_COUNT=" + str(sum(1 for x in lengths if x >= 1000)))
        print("TEXT_OVER_5000_COUNT=" + str(sum(1 for x in lengths if x >= 5000)))

        print("TOP_RESOLVED_RECORDS")
        top_logs = sorted(logs, key=lambda x: int(x.get("resolved_text_length", 0)), reverse=True)[:5]
        for item in top_logs:
            print("-" * 80)
            print("TITLE=" + str(item.get("title", ""))[:220])
            print("PMID=" + str(item.get("pmid", "")))
            print("DOI=" + str(item.get("doi", "")))
            print("PMCID=" + str(item.get("pmcid", "")))
            print("RESOLVED_TEXT_LENGTH=" + str(item.get("resolved_text_length", 0)))
            print("PUBMED_ABSTRACT_LENGTH=" + str(item.get("pubmed_abstract_length", 0)))
            print("PMC_FULLTEXT_LENGTH=" + str(item.get("pmc_fulltext_length", 0)))
            print("PUBLISHER_STATUS=" + str(item.get("publisher_status", "")))


if __name__ == "__main__":
    main()
