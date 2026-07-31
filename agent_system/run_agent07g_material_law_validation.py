from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_law_validation_tools import validate_material_law


def main():
    parser = argparse.ArgumentParser(description="Agent-07G Material Law Validation Agent")
    parser.add_argument("--case-id", required=True)

    args = parser.parse_args()

    result = validate_material_law(case_id=args.case_id)

    print("AGENT_07G_MATERIAL_LAW_VALIDATION_COMPLETED=True")
    print("VALIDATION_STATUS=" + result.get("validation_status", ""))
    print("NEXT_AGENT=" + result.get("next_agent", ""))
    print("APPROVED_FOR_AGENT08=" + str(result.get("approved_for_agent08", False)))
    print("MATERIAL_LAW_PACKAGE_ID=" + result.get("material_law_package_id", ""))
    print("APPROVED_LAW_CANDIDATE_ID=" + result.get("approved_law_candidate_id", ""))

    hu_density = result.get("hu_to_density", {})
    elastic = result.get("density_to_elastic_modulus", {})

    print("HU_TO_DENSITY_INTERCEPT=" + str(hu_density.get("intercept", "")))
    print("HU_TO_DENSITY_SLOPE=" + str(hu_density.get("slope", "")))
    print("ELASTIC_COEFFICIENT=" + str(elastic.get("coefficient", "")))
    print("ELASTIC_EXPONENT=" + str(elastic.get("exponent", "")))

    print("DIRECTIONAL_SCALES=" + str(result.get("directional_scales", {})))
    print("SHEAR_SCALES=" + str(result.get("shear_scales", {})))
    print("POISSON_MAP=" + str(result.get("poisson_map", {})))

    samples = result.get("sample_hu_validation", [])
    if samples:
        first = samples[0]
        last = samples[-1]
        print("SAMPLE_FIRST=" + str(first))
        print("SAMPLE_LAST=" + str(last))

    stability = result.get("orthotropic_stability_results", [])
    if stability:
        stable_all = all(x.get("orthotropic_stable") is True for x in stability)
        print("ORTHOTROPIC_STABILITY_ALL_PASS=" + str(stable_all))
        print("ORTHOTROPIC_STABILITY_FIRST=" + str(stability[0]))
        print("ORTHOTROPIC_STABILITY_LAST=" + str(stability[-1]))
    else:
        print("ORTHOTROPIC_STABILITY_ALL_PASS=False")
        print("ORTHOTROPIC_STABILITY_FIRST=")
        print("ORTHOTROPIC_STABILITY_LAST=")

    print("WARNINGS=" + str(result.get("warnings", [])))
    print("BLOCKERS=" + str(result.get("blockers", [])))


if __name__ == "__main__":
    main()
