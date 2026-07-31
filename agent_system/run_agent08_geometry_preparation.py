from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.geometry_preparation_schema import GeometryPreparationInput
from agent_system.tools.geometry_preparation_tools import (
    run_geometry_preparation,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-08 Geometry / Mesh Preparation Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--segmentation-mask-path", default=None)
    parser.add_argument("--material-law-package-path", default=None)

    args = parser.parse_args()

    user_input = GeometryPreparationInput(
        case_id=args.case_id,
        segmentation_mask_path=args.segmentation_mask_path,
        material_law_package_path=args.material_law_package_path,
    )

    result = run_geometry_preparation(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_08_GEOMETRY_PREPARATION_COMPLETED=True")
    print("GEOMETRY_STATUS=" + result.geometry_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("MATERIAL_LAW_VALIDATED=" + str(result.material_law_validated))
    print("MASK_READ_SUCCESS=" + str(result.mask_read_success))
    print("MASK_IS_EMPTY=" + str(result.mask_is_empty))
    print("VOXEL_COUNT=" + str(result.voxel_count))
    print("OBJECT_VOLUME_CM3=" + str(result.object_volume_cm3))
    print("SURFACE_CREATED=" + str(result.surface_created))
    print("SURFACE_STL_PATH=" + result.surface_stl_path)
    print("SURFACE_VERTICES_COUNT=" + str(result.surface_vertices_count))
    print("SURFACE_FACES_COUNT=" + str(result.surface_faces_count))
    print("SURFACE_AREA_MM2=" + str(result.surface_area_mm2))
    print("IS_WATERTIGHT=" + str(result.is_watertight))
    print("EULER_NUMBER=" + str(result.euler_number))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
