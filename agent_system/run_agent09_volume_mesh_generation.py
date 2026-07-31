from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.volume_mesh_generation_schema import VolumeMeshGenerationInput
from agent_system.tools.volume_mesh_generation_tools import (
    run_volume_mesh_generation,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-09 Volume Mesh Generation Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--geometry-result-path", default="")
    parser.add_argument("--surface-stl-path", default="")
    parser.add_argument("--gmsh-exe-path", default="")
    parser.add_argument("--mesh-size-min", type=float, default=0.75)
    parser.add_argument("--mesh-size-max", type=float, default=3.0)

    args = parser.parse_args()

    user_input = VolumeMeshGenerationInput(
        case_id=args.case_id,
        geometry_result_path=args.geometry_result_path,
        surface_stl_path=args.surface_stl_path,
        gmsh_exe_path=args.gmsh_exe_path,
        mesh_size_min=args.mesh_size_min,
        mesh_size_max=args.mesh_size_max,
    )

    result = run_volume_mesh_generation(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_09_VOLUME_MESH_GENERATION_COMPLETED=True")
    print("VOLUME_MESH_STATUS=" + result.volume_mesh_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("GEOMETRY_PASSED=" + str(result.geometry_passed))
    print("MATERIAL_LAW_VALIDATED=" + str(result.material_law_validated))
    print("GMSH_RUN_SUCCESS=" + str(result.gmsh_run_success))
    print("GMSH_RETURN_CODE=" + str(result.gmsh_return_code))
    print("GMSH_EXE_PATH=" + result.gmsh_exe_path)
    print("SURFACE_STL_PATH=" + result.surface_stl_path)
    print("VOLUME_MESH_PATH=" + result.volume_mesh_path)
    print("VOLUME_MESH_VTK_PATH=" + result.volume_mesh_vtk_path)
    print("MESH_CREATED=" + str(result.mesh_created))
    print("NODE_COUNT=" + str(result.node_count))
    print("TETRA_COUNT=" + str(result.tetra_count))
    print("TRIANGLE_COUNT=" + str(result.triangle_count))
    print("TETRA_VOLUME_TOTAL_CM3=" + str(result.tetra_volume_total_cm3))
    print("TETRA_VOLUME_MIN_MM3=" + str(result.tetra_volume_min_mm3))
    print("TETRA_VOLUME_MAX_MM3=" + str(result.tetra_volume_max_mm3))
    print("SIMPLE_ASPECT_RATIO_MAX=" + str(result.simple_aspect_ratio_max))
    print("SIMPLE_ASPECT_RATIO_MEAN=" + str(result.simple_aspect_ratio_mean))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
