from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.febio_model_generation_schema import FebioModelGenerationInput
from agent_system.tools.febio_model_generation_tools import (
    run_febio_model_generation,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-10 FEBio Model Generation Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--volume-mesh-result-path", default="")
    parser.add_argument("--volume-mesh-path", default="")
    parser.add_argument("--material-law-package-path", default="")
    parser.add_argument("--reference-ct-path", default="")
    parser.add_argument("--material-bin-count", type=int, default=20)

    args = parser.parse_args()

    user_input = FebioModelGenerationInput(
        case_id=args.case_id,
        volume_mesh_result_path=args.volume_mesh_result_path,
        volume_mesh_path=args.volume_mesh_path,
        material_law_package_path=args.material_law_package_path,
        reference_ct_path=args.reference_ct_path,
        material_bin_count=args.material_bin_count,
    )

    result = run_febio_model_generation(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_10_FEBIO_MODEL_GENERATION_COMPLETED=True")
    print("FEBIO_MODEL_STATUS=" + result.febio_model_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("VOLUME_MESH_PASSED=" + str(result.volume_mesh_passed))
    print("MATERIAL_LAW_VALIDATED=" + str(result.material_law_validated))
    print("CT_READ_SUCCESS=" + str(result.ct_read_success))
    print("FEBIO_MODEL_CREATED=" + str(result.febio_model_created))
    print("FEBIO_MODEL_PATH=" + result.febio_model_path)
    print("NODE_COUNT=" + str(result.node_count))
    print("TETRA_COUNT=" + str(result.tetra_count))
    print("MATERIAL_BIN_COUNT=" + str(result.material_bin_count))
    print("HU_MIN=" + str(result.hu_min))
    print("HU_MAX=" + str(result.hu_max))
    print("HU_MEAN=" + str(result.hu_mean))
    print("DENSITY_MIN_G_CM3=" + str(result.density_min_g_cm3))
    print("DENSITY_MAX_G_CM3=" + str(result.density_max_g_cm3))
    print("EZ_MIN_MPA=" + str(result.ez_min_mpa))
    print("EZ_MAX_MPA=" + str(result.ez_max_mpa))
    print("MATERIAL_BINS_CSV=" + result.material_bins_csv)
    print("ELEMENT_MATERIAL_ASSIGNMENTS_CSV=" + result.element_material_assignments_csv)
    print("SOLVER_READY=" + str(result.solver_ready))
    print("BOUNDARY_CONDITIONS_INCLUDED=" + str(result.boundary_conditions_included))
    print("LOADS_INCLUDED=" + str(result.loads_included))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
