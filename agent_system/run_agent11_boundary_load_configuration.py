from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.boundary_load_configuration_schema import BoundaryLoadConfigurationInput
from agent_system.tools.boundary_load_configuration_tools import (
    run_boundary_load_configuration,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-11 Boundary / Load Configuration Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--febio-model-result-path", default="")
    parser.add_argument("--febio-model-path", default="")
    parser.add_argument("--volume-mesh-path", default="")
    parser.add_argument("--endplate-band-fraction", type=float, default=0.08)
    parser.add_argument("--development-engineering-strain", type=float, default=0.005)
    parser.add_argument("--prescribed-displacement-mm", type=float, default=0.0)
    parser.add_argument("--load-protocol-path", default="")

    args = parser.parse_args()

    user_input = BoundaryLoadConfigurationInput(
        case_id=args.case_id,
        febio_model_result_path=args.febio_model_result_path,
        febio_model_path=args.febio_model_path,
        volume_mesh_path=args.volume_mesh_path,
        endplate_band_fraction=args.endplate_band_fraction,
        development_engineering_strain=args.development_engineering_strain,
        prescribed_displacement_mm=args.prescribed_displacement_mm,
        load_protocol_path=args.load_protocol_path,
    )

    result = run_boundary_load_configuration(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_11_BOUNDARY_LOAD_CONFIGURATION_COMPLETED=True")
    print("BOUNDARY_LOAD_STATUS=" + result.boundary_load_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("FEBIO_MODEL_GENERATION_PASSED=" + str(result.febio_model_generation_passed))
    print("BASE_MODEL_READ_SUCCESS=" + str(result.base_model_read_success))
    print("MESH_READ_SUCCESS=" + str(result.mesh_read_success))
    print("ANALYSIS_TYPE=" + result.analysis_type)
    print("LOAD_REGION=" + result.load_region)
    print("FIXED_REGION=" + result.fixed_region)
    print("HEIGHT_MM=" + str(result.height_mm))
    print("ENDPLATE_BAND_FRACTION=" + str(result.endplate_band_fraction))
    print("FIXED_NODE_COUNT=" + str(result.fixed_node_count))
    print("LOADED_NODE_COUNT=" + str(result.loaded_node_count))
    print("PRESCRIBED_DISPLACEMENT_MM=" + str(result.prescribed_displacement_mm))
    print("LOAD_MAGNITUDE_SOURCE=" + result.load_magnitude_source)
    print("NODE_SETS_CSV=" + result.node_sets_csv)
    print("BOUNDARY_CANDIDATE_CREATED=" + str(result.boundary_candidate_created))
    print("FEBIO_MODEL_BOUNDARY_CANDIDATE_PATH=" + result.febio_model_boundary_candidate_path)
    print("SOLVER_READY=" + str(result.solver_ready))
    print("HUMAN_REVIEW_REQUIRED=" + str(result.human_review_required))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()

