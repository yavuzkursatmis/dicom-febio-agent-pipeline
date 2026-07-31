from pathlib import Path
import json
import csv
from datetime import datetime

import numpy as np
import SimpleITK as sitk
from skimage import measure
import trimesh

from agent_system.schemas.geometry_preparation_schema import (
    GeometryPreparationInput,
    GeometryPreparationResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def export_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def default_mask_path(case_id: str):
    return ROOT / "cases" / case_id / "05_segmentation" / "segmentation_mask.nii.gz"


def default_material_law_package_path(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "09_geometry_mesh_preparation"
    return {
        "result_json": out_dir / "GEOMETRY_PREPARATION_RESULT.json",
        "profile_csv": out_dir / "GEOMETRY_PROFILE.csv",
        "surface_stl": out_dir / "geometry_surface.stl",
    }


def validate_material_law_package(path: Path):
    if not path.exists():
        return False, ["VALIDATED_MATERIAL_LAW_PACKAGE_NOT_FOUND"]

    data = load_json(path)

    blockers = []

    if data.get("status") != "MATERIAL_LAW_VALIDATED_WITH_HUMAN_REVIEWED_WARNING":
        blockers.append("MATERIAL_LAW_PACKAGE_STATUS_NOT_FINAL_VALIDATED")

    if data.get("approved_for_agent08") is not True:
        blockers.append("MATERIAL_LAW_PACKAGE_NOT_APPROVED_FOR_AGENT08")

    if data.get("clinical_use") is True:
        blockers.append("MATERIAL_LAW_PACKAGE_CLINICAL_USE_TRUE_NOT_ALLOWED")

    return len(blockers) == 0, blockers


def read_mask(mask_path: Path):
    image = sitk.ReadImage(str(mask_path))
    array = sitk.GetArrayFromImage(image)

    # SimpleITK spacing is x,y,z. Array order is z,y,x.
    spacing_xyz = list(image.GetSpacing())
    spacing_zyx = [spacing_xyz[2], spacing_xyz[1], spacing_xyz[0]]

    mask = array > 0

    return image, mask, spacing_xyz, spacing_zyx


def create_surface_from_mask(mask, spacing_zyx, output_stl_path: Path):
    # marching_cubes expects array order z,y,x and spacing in same order.
    verts_zyx, faces, normals, values = measure.marching_cubes(
        mask.astype(np.uint8),
        level=0.5,
        spacing=spacing_zyx,
    )

    # Convert z,y,x vertices to x,y,z for STL.
    verts_xyz = verts_zyx[:, [2, 1, 0]]

    mesh = trimesh.Trimesh(
        vertices=verts_xyz,
        faces=faces,
        process=False,
    )

    output_stl_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output_stl_path))

    return mesh


def run_geometry_preparation(user_input: GeometryPreparationInput):
    case_id = user_input.case_id

    paths = output_paths(case_id)

    mask_path = Path(user_input.segmentation_mask_path) if user_input.segmentation_mask_path else default_mask_path(case_id)
    material_path = Path(user_input.material_law_package_path) if user_input.material_law_package_path else default_material_law_package_path(case_id)

    warnings = []
    blockers = []

    material_ok, material_blockers = validate_material_law_package(material_path)

    if not material_ok:
        blockers.extend(material_blockers)

    if not mask_path.exists():
        blockers.append("SEGMENTATION_MASK_NOT_FOUND")

    if blockers:
        result = GeometryPreparationResult(
            case_id=case_id,
            geometry_status="GEOMETRY_PREPARATION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            mask_path=str(mask_path),
            material_law_package_path=str(material_path),
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=blockers,
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    try:
        image, mask, spacing_xyz, spacing_zyx = read_mask(mask_path)
        mask_read_success = True
    except Exception as e:
        result = GeometryPreparationResult(
            case_id=case_id,
            geometry_status="MASK_READ_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            mask_path=str(mask_path),
            material_law_package_path=str(material_path),
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=[f"MASK_READ_FAIL:{type(e).__name__}:{e}"],
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    voxel_count = int(mask.sum())
    mask_is_empty = voxel_count == 0

    voxel_volume_mm3 = float(spacing_xyz[0] * spacing_xyz[1] * spacing_xyz[2])
    object_volume_mm3 = float(voxel_count * voxel_volume_mm3)
    object_volume_cm3 = object_volume_mm3 / 1000.0

    image_size = list(image.GetSize())

    if mask_is_empty:
        blockers.append("SEGMENTATION_MASK_IS_EMPTY")

    if voxel_count < 50:
        blockers.append("SEGMENTATION_MASK_TOO_SMALL_FOR_GEOMETRY")

    if blockers:
        result = GeometryPreparationResult(
            case_id=case_id,
            geometry_status="GEOMETRY_PREPARATION_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            mask_path=str(mask_path),
            material_law_package_path=str(material_path),
            mask_read_success=mask_read_success,
            mask_is_empty=mask_is_empty,
            voxel_count=voxel_count,
            voxel_volume_mm3=voxel_volume_mm3,
            object_volume_mm3=object_volume_mm3,
            object_volume_cm3=object_volume_cm3,
            spacing=spacing_xyz,
            image_size=image_size,
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=blockers,
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    try:
        mesh = create_surface_from_mask(mask, spacing_zyx, paths["surface_stl"])
        surface_created = True
    except Exception as e:
        result = GeometryPreparationResult(
            case_id=case_id,
            geometry_status="SURFACE_CREATION_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            mask_path=str(mask_path),
            material_law_package_path=str(material_path),
            mask_read_success=mask_read_success,
            mask_is_empty=mask_is_empty,
            voxel_count=voxel_count,
            voxel_volume_mm3=voxel_volume_mm3,
            object_volume_mm3=object_volume_mm3,
            object_volume_cm3=object_volume_cm3,
            spacing=spacing_xyz,
            image_size=image_size,
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=[f"SURFACE_CREATION_FAIL:{type(e).__name__}:{e}"],
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    surface_vertices_count = int(len(mesh.vertices))
    surface_faces_count = int(len(mesh.faces))
    surface_area_mm2 = float(mesh.area)

    bounds = mesh.bounds
    bbox_mm = [
        float(bounds[0][0]),
        float(bounds[0][1]),
        float(bounds[0][2]),
        float(bounds[1][0]),
        float(bounds[1][1]),
        float(bounds[1][2]),
    ]

    is_watertight = bool(mesh.is_watertight)
    euler_number = int(mesh.euler_number)

    if not is_watertight:
        warnings.append("SURFACE_NOT_WATERTIGHT_REVIEW_REQUIRED")

    if surface_faces_count < 100:
        warnings.append("LOW_SURFACE_FACE_COUNT_REVIEW_REQUIRED")

    if object_volume_cm3 <= 0:
        blockers.append("OBJECT_VOLUME_NOT_POSITIVE")

    if surface_created and not blockers:
        if warnings:
            status = "GEOMETRY_PREPARATION_WARNING"
            next_agent = "HUMAN_REVIEW_GATE"
        else:
            status = "GEOMETRY_PREPARATION_PASS"
            next_agent = "AGENT_09_VOLUME_MESH_GENERATION"
    else:
        status = "GEOMETRY_PREPARATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"

    result = GeometryPreparationResult(
        case_id=case_id,
        geometry_status=status,
        next_agent=next_agent,
        mask_path=str(mask_path),
        material_law_package_path=str(material_path),
        mask_read_success=mask_read_success,
        mask_is_empty=mask_is_empty,
        voxel_count=voxel_count,
        voxel_volume_mm3=voxel_volume_mm3,
        object_volume_mm3=object_volume_mm3,
        object_volume_cm3=object_volume_cm3,
        spacing=spacing_xyz,
        image_size=image_size,
        surface_stl_path=str(paths["surface_stl"]),
        surface_created=surface_created,
        surface_vertices_count=surface_vertices_count,
        surface_faces_count=surface_faces_count,
        surface_area_mm2=surface_area_mm2,
        bounding_box_mm=bbox_mm,
        is_watertight=is_watertight,
        euler_number=euler_number,
        material_law_validated=material_ok,
        warnings=warnings,
        blockers=blockers,
    )

    save_json(paths["result_json"], result.model_dump())
    export_csv(paths["profile_csv"], [result.model_dump()])

    return result


def append_paper_note(case_id: str, result: GeometryPreparationResult):
    note_path = ROOT / "paper_notes" / "geometry_mesh_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-08 Geometry / Mesh Preparation

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.geometry_status}
Sonraki ajan: {result.next_agent}

Girdi:
- Segmentasyon maskesi: {result.mask_path}
- Validated material-law paketi: {result.material_law_package_path}

Geometri metrikleri:
- Voxel count: {result.voxel_count}
- Volume cm3: {result.object_volume_cm3}
- Surface vertices: {result.surface_vertices_count}
- Surface faces: {result.surface_faces_count}
- Surface area mm2: {result.surface_area_mm2}
- Watertight: {result.is_watertight}
- Euler number: {result.euler_number}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}

Not:
Bu ajan FEBio modeli kurmaz ve solver çalıştırmaz. Çıktı yüzey geometrisi ve mesh hazırlık metrikleridir.
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
