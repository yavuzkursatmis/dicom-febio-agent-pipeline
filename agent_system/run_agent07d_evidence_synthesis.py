from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.evidence_synthesis_material_estimator import run_evidence_synthesis_material_estimator


def main():
    parser = argparse.ArgumentParser(description="Agent-07D Evidence Synthesis Material Estimator")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--material-selection-json", default=None)
    parser.add_argument("--resolved-literature-json", default=None)
    parser.add_argument("--minimum-sources-per-required-property", type=int, default=2)

    args = parser.parse_args()

    result = run_evidence_synthesis_material_estimator(
        case_id=args.case_id,
        material_selection_json=args.material_selection_json,
        resolved_literature_json=args.resolved_literature_json,
        minimum_sources_per_required_property=args.minimum_sources_per_required_property,
    )

    elastic = result.get("synthesized_parameters", {}).get("elastic_modulus_MPa", {})
    poisson = result.get("synthesized_parameters", {}).get("poisson_ratio", {})

    print("AGENT_07D_EVIDENCE_SYNTHESIS_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("SYNTHESIS_CANDIDATE_ID=" + result.get("synthesis_candidate_id", ""))
    print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
    print("ANATOMICAL_REGION=" + result.get("anatomical_region", ""))
    print("SOURCE_LITERATURE_RECORDS_COUNT=" + str(result.get("source_literature_records_count", 0)))
    print("PROPERTY_CANDIDATES_COUNT=" + str(result.get("property_candidates_count", 0)))

    print("ELASTIC_AVAILABLE=" + str(elastic.get("available", False)))
    print("ELASTIC_SOURCE_COUNT=" + str(elastic.get("source_count", 0)))
    print("ELASTIC_PROPOSED_MPA=" + str(elastic.get("proposed_value", None)))
    print("ELASTIC_LOWER_MPA=" + str(elastic.get("lower_bound", None)))
    print("ELASTIC_UPPER_MPA=" + str(elastic.get("upper_bound", None)))

    print("POISSON_AVAILABLE=" + str(poisson.get("available", False)))
    print("POISSON_SOURCE_COUNT=" + str(poisson.get("source_count", 0)))
    print("POISSON_PROPOSED=" + str(poisson.get("proposed_value", None)))
    print("POISSON_LOWER=" + str(poisson.get("lower_bound", None)))
    print("POISSON_UPPER=" + str(poisson.get("upper_bound", None)))

    print("GLOBAL_UNCERTAINTY_LEVEL=" + result.get("global_uncertainty_level", ""))
    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
