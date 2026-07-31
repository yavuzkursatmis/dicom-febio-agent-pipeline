from pathlib import Path
import json
import csv
import shutil
import subprocess
from datetime import datetime

import numpy as np
import meshio

from agent_system.schemas.volume_mesh_generation_schema import (
    VolumeMeshGenerationInput,
    VolumeMeshGenerationResult,
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


def default_geometry_result_path(case_id: str):
    return ROOT / "cases" / case_id / "09_geometry_mesh_preparation" / "GEOMETRY_PREPARATION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "10_volume_mesh_generation"
    return {
        "result_json": out_dir / "VOLUME_MESH_GENERATION_RESULT.json",
        "profile_csv": out_dir / "VOLUME_MESH_PROFILE.csv",
        "geo_file": out_dir / "volume_mesh.geo",
        "volume_mesh": out_dir / "volume_mesh.msh",
        "volume_mesh_vtk": out_dir / "volume_mesh.vtk",
        "gmsh_stdout": out_dir / "gmsh_stdout.txt",
        "gmsh_stderr": out_dir / "gmsh_stderr.txt",
    }


def find_gmsh(user_path: str = ""):
    candidates = []

    if user_path:
        candidates.append(Path(user_path))

    candidates.extend([
        Path(r"C:\Tools\gmsh\gmsh.exe"),
        Path(r"C:\Program Files\Gmsh\gmsh.exe"),
        Path(r"C:\Program Files (x86)\Gmsh\gmsh.exe"),
    ])

    which = shutil.which("gmsh")
    if which:
        candidates.append(Path(which))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return ""


def validate_geometry_result(path: Path):
    blockers = []
    surface_stl = ""
    material_validated = False
    geometry_passed = False

    if not path.exists():
        return {
            "ok": False,
            "surface_stl": "",
            "material_law_validated": False,
            "geometry_passed": False,
            "blockers": ["GEOMETRY_PREPARATION_RESULT_NOT_FOUND"],
        }

    data = load_json(path)

    geometry_passed = data.get("geometry_status") == "GEOMETRY_PREPARATION_PASS"
    material_validated = data.get("material_law_validated") is True
    surface_stl = data.get("surface_stl_path", "")

    if not geometry_passed:
        blockers.append("GEOMETRY_PREPARATION_NOT_PASS")

    if not material_validated:
        blockers.append("MATERIAL_LAW_NOT_VALIDATED_IN_GEOMETRY_RESULT")

    if not surface_stl:
        blockers.append("SURFACE_STL_PATH_MISSING_IN_GEOMETRY_RESULT")
    elif not Path(surface_stl).exists():
        blockers.append("SURFACE_STL_FILE_NOT_FOUND")

    return {
        "ok": len(blockers) == 0,
        "surface_stl": surface_stl,
        "material_law_validated": material_validated,
        "geometry_passed": geometry_passed,
        "blockers": blockers,
    }


def write_geo_file(path: Path, stl_path: Path, msh_path: Path, mesh_size_min: float, mesh_size_max: float):
    stl = stl_path.resolve().as_posix()
    msh = msh_path.resolve().as_posix()

    content = f'''
Mesh.MshFileVersion = 2.2;
Mesh.MeshSizeMin = {mesh_size_min};
Mesh.MeshSizeMax = {mesh_size_max};
Mesh.Algorithm3D = 1;
Mesh.Optimize = 1;
Mesh.OptimizeNetgen = 1;

Merge "{stl}";

// STL yüzeyinden topolojik yüzey oluştur.
// Bu STL Agent-08'den watertight olarak geldiği için tek kapalı yüzey varsayılır.
CreateTopology;

Surface Loop(1) = {{1}};
Volume(1) = {{1}};

Physical Surface("surface") = {{1}};
Physical Volume("volume") = {{1}};

Mesh 3;
Save "{msh}";
'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_gmsh(gmsh_path: str, geo_path: Path, stdout_path: Path, stderr_path: Path):
    cmd = [
        gmsh_path,
        str(geo_path),
        "-3",
        "-v",
        "2",
    ]

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    stdout_path.write_text(completed.stdout or "", encoding="utf-8", errors="replace")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8", errors="replace")

    return completed.returncode


def cell_count(mesh, cell_type: str):
    count = 0
    for block in mesh.cells:
        if block.type == cell_type:
            count += len(block.data)
    return int(count)


def collect_cells(mesh, cell_type: str):
    cells = []
    for block in mesh.cells:
        if block.type == cell_type:
            cells.append(block.data)

    if not cells:
        return np.empty((0, 4), dtype=int)

    return np.vstack(cells)


def tetra_volumes(points, tetra):
    if tetra.size == 0:
        return np.array([], dtype=float)

    p0 = points[tetra[:, 0]]
    p1 = points[tetra[:, 1]]
    p2 = points[tetra[:, 2]]
    p3 = points[tetra[:, 3]]

    volumes = np.abs(
        np.einsum("ij,ij->i", p1 - p0, np.cross(p2 - p0, p3 - p0))
    ) / 6.0

    return volumes


def edge_quality(points, tetra):
    if tetra.size == 0:
        return {
            "edge_min": 0.0,
            "edge_max": 0.0,
            "edge_mean": 0.0,
            "aspect_max": 0.0,
            "aspect_mean": 0.0,
        }

    edges = [
        (0, 1), (0, 2), (0, 3),
        (1, 2), (1, 3),
        (2, 3),
    ]

    all_lengths = []
    aspect_ratios = []

    for tet in tetra:
        pts = points[tet]
        lengths = []

        for a, b in edges:
            lengths.append(float(np.linalg.norm(pts[a] - pts[b])))

        lengths = np.array(lengths, dtype=float)
        all_lengths.extend(lengths.tolist())

        min_l = float(lengths.min())
        max_l = float(lengths.max())

        if min_l > 0:
            aspect_ratios.append(max_l / min_l)

    all_lengths = np.array(all_lengths, dtype=float)
    aspect_ratios = np.array(aspect_ratios, dtype=float) if aspect_ratios else np.array([0.0])

    return {
        "edge_min": float(all_lengths.min()) if all_lengths.size else 0.0,
        "edge_max": float(all_lengths.max()) if all_lengths.size else 0.0,
        "edge_mean": float(all_lengths.mean()) if all_lengths.size else 0.0,
        "aspect_max": float(aspect_ratios.max()) if aspect_ratios.size else 0.0,
        "aspect_mean": float(aspect_ratios.mean()) if aspect_ratios.size else 0.0,
    }


def analyze_mesh(mesh_path: Path, vtk_path: Path):
    mesh = meshio.read(mesh_path)

    points = np.asarray(mesh.points, dtype=float)
    tetra = collect_cells(mesh, "tetra")

    node_count = int(points.shape[0])
    tetra_count = int(tetra.shape[0])
    triangle_count = cell_count(mesh, "triangle")

    volumes = tetra_volumes(points, tetra)
    quality = edge_quality(points, tetra)

    try:
        meshio.write(vtk_path, mesh)
    except Exception:
        pass

    return {
        "node_count": node_count,
        "tetra_count": tetra_count,
        "triangle_count": triangle_count,
        "vol_min": float(volumes.min()) if volumes.size else 0.0,
        "vol_max": float(volumes.max()) if volumes.size else 0.0,
        "vol_mean": float(volumes.mean()) if volumes.size else 0.0,
        "vol_total": float(volumes.sum()) if volumes.size else 0.0,
        "edge_min": quality["edge_min"],
        "edge_max": quality["edge_max"],
        "edge_mean": quality["edge_mean"],
        "aspect_max": quality["aspect_max"],
        "aspect_mean": quality["aspect_mean"],
    }


def run_volume_mesh_generation(user_input: VolumeMeshGenerationInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    geometry_result_path = Path(user_input.geometry_result_path) if user_input.geometry_result_path else default_geometry_result_path(case_id)

    geometry = validate_geometry_result(geometry_result_path)
    blockers.extend(geometry["blockers"])

    surface_stl_path = Path(user_input.surface_stl_path) if user_input.surface_stl_path else Path(geometry.get("surface_stl", ""))

    if user_input.surface_stl_path and not surface_stl_path.exists():
        blockers.append("USER_PROVIDED_SURFACE_STL_NOT_FOUND")

    gmsh_path = find_gmsh(user_input.gmsh_exe_path)

    if not gmsh_path:
        blockers.append("GMSH_EXECUTABLE_NOT_FOUND")

    if blockers:
        result = VolumeMeshGenerationResult(
            case_id=case_id,
            volume_mesh_status="VOLUME_MESH_GENERATION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            geometry_result_path=str(geometry_result_path),
            surface_stl_path=str(surface_stl_path),
            gmsh_exe_path=gmsh_path,
            material_law_validated=geometry["material_law_validated"],
            geometry_passed=geometry["geometry_passed"],
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    write_geo_file(
        path=paths["geo_file"],
        stl_path=surface_stl_path,
        msh_path=paths["volume_mesh"],
        mesh_size_min=user_input.mesh_size_min,
        mesh_size_max=user_input.mesh_size_max,
    )

    try:
        return_code = run_gmsh(
            gmsh_path=gmsh_path,
            geo_path=paths["geo_file"],
            stdout_path=paths["gmsh_stdout"],
            stderr_path=paths["gmsh_stderr"],
        )
    except Exception as e:
        result = VolumeMeshGenerationResult(
            case_id=case_id,
            volume_mesh_status="GMSH_RUN_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            geometry_result_path=str(geometry_result_path),
            surface_stl_path=str(surface_stl_path),
            gmsh_exe_path=gmsh_path,
            gmsh_stdout_path=str(paths["gmsh_stdout"]),
            gmsh_stderr_path=str(paths["gmsh_stderr"]),
            material_law_validated=geometry["material_law_validated"],
            geometry_passed=geometry["geometry_passed"],
            warnings=warnings,
            blockers=[f"GMSH_RUN_FAIL:{type(e).__name__}:{e}"],
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    if return_code != 0:
        blockers.append(f"GMSH_RETURN_CODE_NONZERO:{return_code}")

    if not paths["volume_mesh"].exists():
        blockers.append("VOLUME_MESH_FILE_NOT_CREATED")

    if blockers:
        result = VolumeMeshGenerationResult(
            case_id=case_id,
            volume_mesh_status="VOLUME_MESH_GENERATION_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            geometry_result_path=str(geometry_result_path),
            surface_stl_path=str(surface_stl_path),
            gmsh_exe_path=gmsh_path,
            gmsh_run_success=False,
            gmsh_template_used="CreateTopology_single_surface",
            gmsh_return_code=return_code,
            gmsh_stdout_path=str(paths["gmsh_stdout"]),
            gmsh_stderr_path=str(paths["gmsh_stderr"]),
            volume_mesh_path=str(paths["volume_mesh"]),
            material_law_validated=geometry["material_law_validated"],
            geometry_passed=geometry["geometry_passed"],
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    try:
        metrics = analyze_mesh(paths["volume_mesh"], paths["volume_mesh_vtk"])
    except Exception as e:
        result = VolumeMeshGenerationResult(
            case_id=case_id,
            volume_mesh_status="VOLUME_MESH_READ_OR_ANALYSIS_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            geometry_result_path=str(geometry_result_path),
            surface_stl_path=str(surface_stl_path),
            gmsh_exe_path=gmsh_path,
            gmsh_run_success=True,
            gmsh_template_used="CreateTopology_single_surface",
            gmsh_return_code=return_code,
            gmsh_stdout_path=str(paths["gmsh_stdout"]),
            gmsh_stderr_path=str(paths["gmsh_stderr"]),
            volume_mesh_path=str(paths["volume_mesh"]),
            mesh_created=True,
            material_law_validated=geometry["material_law_validated"],
            geometry_passed=geometry["geometry_passed"],
            warnings=warnings,
            blockers=[f"VOLUME_MESH_READ_OR_ANALYSIS_FAIL:{type(e).__name__}:{e}"],
        )

        save_json(paths["result_json"], result.model_dump())
        export_csv(paths["profile_csv"], [result.model_dump()])
        return result

    if metrics["tetra_count"] <= 0:
        blockers.append("NO_TETRAHEDRAL_ELEMENTS_FOUND")

    if metrics["vol_min"] <= 0:
        blockers.append("NON_POSITIVE_TETRA_VOLUME_FOUND")

    if metrics["tetra_count"] < 100:
        warnings.append("LOW_TETRA_COUNT_REVIEW_REQUIRED")

    if metrics["aspect_max"] > 20:
        warnings.append(f"HIGH_SIMPLE_ASPECT_RATIO_REVIEW_REQUIRED:{round(metrics['aspect_max'], 3)}")

    if warnings:
        status = "VOLUME_MESH_GENERATION_WARNING"
        next_agent = "HUMAN_REVIEW_GATE"
    elif blockers:
        status = "VOLUME_MESH_GENERATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
    else:
        status = "VOLUME_MESH_GENERATION_PASS"
        next_agent = "AGENT_10_FEBIO_MODEL_GENERATION"

    result = VolumeMeshGenerationResult(
        case_id=case_id,
        volume_mesh_status=status,
        next_agent=next_agent,
        geometry_result_path=str(geometry_result_path),
        surface_stl_path=str(surface_stl_path),
        gmsh_exe_path=gmsh_path,
        gmsh_run_success=True,
        gmsh_template_used="CreateTopology_single_surface",
        gmsh_return_code=return_code,
        gmsh_stdout_path=str(paths["gmsh_stdout"]),
        gmsh_stderr_path=str(paths["gmsh_stderr"]),
        volume_mesh_path=str(paths["volume_mesh"]),
        volume_mesh_vtk_path=str(paths["volume_mesh_vtk"]),
        mesh_created=True,
        node_count=metrics["node_count"],
        tetra_count=metrics["tetra_count"],
        triangle_count=metrics["triangle_count"],
        tetra_volume_min_mm3=metrics["vol_min"],
        tetra_volume_max_mm3=metrics["vol_max"],
        tetra_volume_mean_mm3=metrics["vol_mean"],
        tetra_volume_total_mm3=metrics["vol_total"],
        tetra_volume_total_cm3=metrics["vol_total"] / 1000.0,
        edge_length_min_mm=metrics["edge_min"],
        edge_length_max_mm=metrics["edge_max"],
        edge_length_mean_mm=metrics["edge_mean"],
        simple_aspect_ratio_max=metrics["aspect_max"],
        simple_aspect_ratio_mean=metrics["aspect_mean"],
        material_law_validated=geometry["material_law_validated"],
        geometry_passed=geometry["geometry_passed"],
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())
    export_csv(paths["profile_csv"], [result.model_dump()])

    return result


def append_paper_note(case_id: str, result: VolumeMeshGenerationResult):
    note_path = ROOT / "paper_notes" / "geometry_mesh_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-09 Volume Mesh Generation

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.volume_mesh_status}
Sonraki ajan: {result.next_agent}

Girdi:
- Geometry result: {result.geometry_result_path}
- Surface STL: {result.surface_stl_path}
- Gmsh: {result.gmsh_exe_path}

Çıktı:
- Volume mesh: {result.volume_mesh_path}
- VTK: {result.volume_mesh_vtk_path}

Mesh metrikleri:
- Node count: {result.node_count}
- Tetra count: {result.tetra_count}
- Triangle count: {result.triangle_count}
- Total tetra volume cm3: {result.tetra_volume_total_cm3}
- Mean tetra volume mm3: {result.tetra_volume_mean_mm3}
- Simple aspect ratio max: {result.simple_aspect_ratio_max}
- Simple aspect ratio mean: {result.simple_aspect_ratio_mean}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}

Not:
Bu ajan FEBio modeli kurmaz. Sadece hacim tetrahedral mesh üretir ve kalite metriklerini çıkarır.
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)

