from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.general_material_extractor_tools import run_general_material_extraction


def main():
    parser = argparse.ArgumentParser(description="Agent-07B General Tissue Material Extractor")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--material-selection-json", default=None)
    parser.add_argument("--literature-candidates-json", default=None)
    parser.add_argument("--no-fetch-full-text", action="store_true")

    args = parser.parse_args()

    result = run_general_material_extraction(
        case_id=args.case_id,
        material_selection_json=args.material_selection_json,
        literature_candidates_json=args.literature_candidates_json,
        fetch_full_text=not args.no_fetch_full_text,
    )

    print("AGENT_07B_GENERAL_MATERIAL_EXTRACTOR_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("SOURCE_LITERATURE_RECORDS_COUNT=" + str(result.get("source_literature_records_count", 0)))
    print("AGENT07B_CANDIDATES_COUNT=" + str(result.get("agent07b_candidates_count", 0)))
    print("CANDIDATE_SETS_COUNT=" + str(result.get("candidate_sets_count", 0)))

    sets = result.get("candidate_sets", [])
    if sets:
        top = sets[0]
        print("TOP_CANDIDATE_SET_ID=" + str(top.get("candidate_set_id", "")))
        print("TOP_ELASTIC_MODULUS_MPA=" + str(top.get("elastic_modulus_MPa", "")))
        print("TOP_POISSON_RATIO=" + str(top.get("poisson_ratio", "")))
        print("TOP_SOURCE_TITLE=" + str(top.get("source_title", "")))
    else:
        print("TOP_CANDIDATE_SET_ID=")
        print("TOP_ELASTIC_MODULUS_MPA=")
        print("TOP_POISSON_RATIO=")
        print("TOP_SOURCE_TITLE=")

    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
