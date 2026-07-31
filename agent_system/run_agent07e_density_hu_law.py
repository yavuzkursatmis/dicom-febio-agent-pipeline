from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.density_hu_material_law_tools import (
    run_density_hu_law_search,
    run_density_hu_law_extraction,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-07E Density/HU material law search and extractor")
    parser.add_argument("--mode", required=True, choices=["search", "extract"])
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--max-records-per-source", type=int, default=8)
    parser.add_argument("--material-selection-json", default=None)
    parser.add_argument("--resolved-literature-json", default=None)

    args = parser.parse_args()

    if args.mode == "search":
        result = run_density_hu_law_search(
            case_id=args.case_id,
            max_records_per_source=args.max_records_per_source,
        )

        print("AGENT_07E_DENSITY_HU_SEARCH_COMPLETED=True")
        print("STATUS=" + result.get("status", ""))
        print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
        print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
        print("TARGET_FAMILY=" + result.get("target_family", ""))
        print("RAW_RECORDS_COUNT=" + str(result.get("raw_records_count", 0)))
        print("RECORDS_COUNT=" + str(result.get("records_count", 0)))
        print("SOURCE_ERRORS_COUNT=" + str(len(result.get("source_errors", []))))
        print("BLOCKERS=" + str(result.get("blockers", [])))

        records = result.get("records", [])
        if records:
            top = records[0]
            print("TOP_SCORE=" + str(top.get("density_hu_relevance_score", "")))
            print("TOP_TITLE=" + str(top.get("title", "")))
            print("TOP_URL=" + str(top.get("url", "")))
            print("TOP_REASONS=" + str(top.get("density_hu_relevance_reasons", [])))
        else:
            print("TOP_SCORE=")
            print("TOP_TITLE=")
            print("TOP_URL=")
            print("TOP_REASONS=")

    else:
        result = run_density_hu_law_extraction(
            case_id=args.case_id,
            material_selection_json=args.material_selection_json,
            resolved_literature_json=args.resolved_literature_json,
        )

        print("AGENT_07E_DENSITY_HU_LAW_EXTRACTION_COMPLETED=True")
        print("STATUS=" + result.get("status", ""))
        print("NEXT_AGENT=" + result.get("next_agent", ""))
        print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
        print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
        print("TARGET_FAMILY=" + result.get("target_family", ""))
        print("SOURCE_LITERATURE_RECORDS_COUNT=" + str(result.get("source_literature_records_count", 0)))
        print("LAW_CANDIDATES_COUNT=" + str(result.get("law_candidates_count", 0)))
        print("COMPLETE_LAW_CANDIDATES_COUNT=" + str(result.get("complete_law_candidates_count", 0)))

        candidates = result.get("law_candidates", [])
        if candidates:
            top = candidates[0]
            print("TOP_LAW_CANDIDATE_ID=" + str(top.get("law_candidate_id", "")))
            print("TOP_LAW_STATUS=" + str(top.get("law_status", "")))
            print("TOP_COMPLETE=" + str(top.get("complete_law_candidate", "")))
            print("TOP_SOURCE_TITLE=" + str(top.get("source_title", "")))
            print("TOP_SOURCE_URL=" + str(top.get("source_url", "")))
            print("TOP_FORMULA_SNIPPETS=" + str(top.get("formula_snippets", []))[:600])
        else:
            print("TOP_LAW_CANDIDATE_ID=")
            print("TOP_LAW_STATUS=")
            print("TOP_COMPLETE=")
            print("TOP_SOURCE_TITLE=")
            print("TOP_SOURCE_URL=")
            print("TOP_FORMULA_SNIPPETS=")

        print("WARNINGS=" + str(result.get("warnings", [])))
        print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
