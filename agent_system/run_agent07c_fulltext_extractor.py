from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.fulltext_material_extraction_tools import run_fulltext_material_extraction


def main():
    parser = argparse.ArgumentParser(description="Agent-07C Full-text/PDF/table material extractor.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--material-selection-json", default=None)
    parser.add_argument("--literature-candidates-json", default=None)
    parser.add_argument("--max-records", type=int, default=40)
    parser.add_argument("--max-pdf-links-per-record", type=int, default=2)

    args = parser.parse_args()

    result = run_fulltext_material_extraction(
        case_id=args.case_id,
        material_selection_json=args.material_selection_json,
        literature_candidates_json=args.literature_candidates_json,
        max_records=args.max_records,
        max_pdf_links_per_record=args.max_pdf_links_per_record,
    )

    print("AGENT_07C_FULLTEXT_MATERIAL_EXTRACTOR_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("SOURCE_LITERATURE_RECORDS_COUNT=" + str(result.get("source_literature_records_count", 0)))
    print("PROCESSED_RECORDS_COUNT=" + str(result.get("processed_records_count", 0)))
    print("AGENT07C_CANDIDATES_COUNT=" + str(result.get("agent07b_candidates_count", 0)))
    print("CANDIDATE_SETS_COUNT=" + str(result.get("candidate_sets_count", 0)))

    sets = result.get("candidate_sets", [])
    if sets:
        top = sets[0]
        print("TOP_CANDIDATE_SET_ID=" + str(top.get("candidate_set_id", "")))
        print("TOP_ELASTIC_MODULUS_MPA=" + str(top.get("elastic_modulus_MPa", "")))
        print("TOP_POISSON_RATIO=" + str(top.get("poisson_ratio", "")))
        print("TOP_SOURCE_TITLE=" + str(top.get("source_title", "")))
        print("TOP_SOURCE_URL=" + str(top.get("source_url", "")))
    else:
        print("TOP_CANDIDATE_SET_ID=")
        print("TOP_ELASTIC_MODULUS_MPA=")
        print("TOP_POISSON_RATIO=")
        print("TOP_SOURCE_TITLE=")
        print("TOP_SOURCE_URL=")

    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
