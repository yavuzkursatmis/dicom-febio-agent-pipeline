from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.candidate_set_relevance_validator import validate_candidate_set_relevance


def main():
    parser = argparse.ArgumentParser(description="Validate Agent-07B candidate set target relevance.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--agent07b-json", default=None)

    args = parser.parse_args()

    result = validate_candidate_set_relevance(
        case_id=args.case_id,
        agent07b_json=args.agent07b_json,
    )

    print("AGENT07B_CANDIDATE_SET_RELEVANCE_VALIDATED=True")
    print("STATUS=" + result.get("status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("CANDIDATE_SETS_COUNT=" + str(result.get("candidate_sets_count", 0)))
    print("ACCEPTABLE_CANDIDATE_SETS_COUNT=" + str(result.get("acceptable_candidate_sets_count", 0)))
    print("BLOCKERS=" + str(result.get("blockers", [])))

    evaluated = result.get("evaluated_candidate_sets", [])
    if evaluated:
        top = evaluated[0]
        print("TOP_CANDIDATE_SET_ID=" + str(top.get("candidate_set_id", "")))
        print("TOP_RELEVANCE_DECISION=" + str(top.get("decision", "")))
        print("TOP_RELEVANCE_SCORE=" + str(top.get("target_relevance_score", "")))
        print("TOP_TARGET_FAMILY=" + str(top.get("target_family", "")))
        print("TOP_POSITIVE_MATCHES=" + str(top.get("matched_positive_terms", [])))
        print("TOP_NEGATIVE_MATCHES=" + str(top.get("matched_negative_terms", [])))
        print("TOP_SOURCE_TITLE=" + str(top.get("candidate_set", {}).get("source_title", "")))


if __name__ == "__main__":
    main()
