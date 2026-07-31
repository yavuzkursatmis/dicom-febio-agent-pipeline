from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_law_structuring_tools import structure_material_law


def main():
    parser = argparse.ArgumentParser(description="Agent-07F Material Law Structuring Agent")
    parser.add_argument("--case-id", required=True)

    args = parser.parse_args()

    result = structure_material_law(case_id=args.case_id)

    law = result.get("structured_law", {})

    print("AGENT_07F_MATERIAL_LAW_STRUCTURING_COMPLETED=True")
    print("STATUS=" + result.get("status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("MATERIAL_LAW_PACKAGE_ID=" + result.get("material_law_package_id", ""))
    print("READY_FOR_MATERIAL_LAW_VALIDATION=" + str(result.get("ready_for_material_law_validation", False)))
    print("APPROVED_LAW_CANDIDATE_ID=" + result.get("approved_law_candidate_id", ""))
    print("MATERIAL_LAW_FAMILY=" + result.get("material_law_family", ""))

    hu_density = law.get("hu_to_density", {})
    density_elastic = law.get("density_to_elastic_modulus", {})
    directional = law.get("directional_modulus_relations", [])
    shear = law.get("shear_modulus_relations", [])
    poisson = law.get("poisson_relations", [])

    print("HU_TO_DENSITY_FOUND=" + str(hu_density.get("found", False)))
    print("HU_TO_DENSITY_FORMULA=" + str(hu_density.get("formula_text", "")))

    print("DENSITY_TO_ELASTIC_FOUND=" + str(density_elastic.get("found", False)))
    print("DENSITY_TO_ELASTIC_FORMULA=" + str(density_elastic.get("formula_text", "")))

    print("DIRECTIONAL_RELATIONS_COUNT=" + str(len(directional)))
    print("SHEAR_RELATIONS_COUNT=" + str(len(shear)))
    print("POISSON_RELATIONS_COUNT=" + str(len(poisson)))

    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
