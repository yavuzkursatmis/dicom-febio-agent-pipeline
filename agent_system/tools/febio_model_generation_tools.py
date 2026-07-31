from pathlib import Path
import json
import csv
from datetime import datetime
import html

import numpy as np
import meshio
import SimpleITK as sitk

from agent_system.schemas.febio_model_generation_schema import (
    FebioModelGenerationInput,
    FebioModelGenerationResult,
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


def default_volume_mesh_result_path(case_id: str):
    return ROOT / "cases" / case_id / "10_volume_mesh_generation" / "VOLUME_MESH_GENERATION_RESULT.json"


def default_material_law_package_path(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"


def default_reference_ct_path(case_id: str):
    resampled = ROOT / "cases" / case_id / "04_segmentation" / "volume_resampled.nii.gz"
    original = ROOT / "cases" / case_id / "04_segmentation" / "volume_original.nii.gz"

    if resampled.exists():
        return resampled

    return original


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "11_febio_model_generation"
    return {
        "result_json": out_dir / "FEBIO_MODEL_GENERATION_RESULT.json",
        "febio_model": out_dir / "febio_model_base.feb",
        "material_bins_csv": out_dir / "FEBIO_MATERIAL_BINS.csv",
        "element_assignments_csv": out_dir / "FEBIO_ELEMENT_MATERIAL_ASSIGNMENTS.csv",
        "notes_txt": out_dir / "FEBIO_MODEL_GENERATION_NOTES.txt",
    }


def validate_volume_mesh_result(path: Path):
    blockers = []
    mesh_path = ""
    passed = False

    if not path.exists():
        return False, "", ["VOLUME_MESH_GENERATION_RESULT_NOT_FOUND"]

    data = load_json(path)
    passed = data.get("volume_mesh_status") == "VOLUME_MESH_GENERATION_PASS"
    mesh_path = data.get("volume_mesh_path", "")

    if not passed:
        blockers.append("VOLUME_MESH_STATUS_NOT_PASS")

    if not mesh_path:
        blockers.append("VOLUME_MESH_PATH_MISSING")
    elif not Path(mesh_path).exists():
        blockers.append("VOLUME_MESH_FILE_NOT_FOUND")

    return passed and not blockers, mesh_path, blockers


def validate_material_package(path: Path):
    blockers = []

    if not path.exists():
        return False, {}, ["VALIDATED_MATERIAL_LAW_PACKAGE_NOT_FOUND"]

    data = load_json(path)

    if data.get("status") != "MATERIAL_LAW_VALIDATED_WITH_HUMAN_REVIEWED_WARNING":
        blockers.append("MATERIAL_LAW_PACKAGE_STATUS_NOT_FINAL_VALIDATED")

    if data.get("approved_for_agent08") is not True:
        blockers.append("MATERIAL_LAW_PACKAGE_NOT_APPROVED_FOR_AGENT08")

    if data.get("clinical_use") is True:
        blockers.append("MATERIAL_LAW_PACKAGE_CLINICAL_USE_TRUE_NOT_ALLOWED")

    return len(blockers) == 0, data, blockers


def collect_tetra_cells(mesh):
    cells = []

    for block in mesh.cells:
        if block.type == "tetra":
            cells.append(block.data)

    if not cells:
        return np.empty((0, 4), dtype=int)

    return np.vstack(cells)


def read_ct_volume(path: Path):
    image = sitk.ReadImage(str(path))
    array = sitk.GetArrayFromImage(image).astype(float)

    spacing_xyz = list(image.GetSpacing())
    size_xyz = list(image.GetSize())

    return image, array, spacing_xyz, size_xyz


def parse_directional_scales(package):
    relations = package.get("structured_law", {}).get("directional_modulus_relations", [])

    scales = {}

    for relation in relations:
        if relation.get("relation_type") != "directional_modulus_scaling":
            continue

        scale = relation.get("scale_factor")

        for variable in relation.get("variables", []):
            scales[variable] = float(scale)

    return scales


def parse_poisson_map(package):
    relations = package.get("structured_law", {}).get("poisson_relations", [])

    values = {}

    for relation in relations:
        if "variable" in relation:
            values[relation["variable"]] = float(relation.get("value"))

        if "variables" in relation:
            for variable in relation.get("variables", []):
                values[variable] = float(relation.get("value"))

    return values


def get_material_law_constants(package):
    law = package.get("structured_law", {})

    hu_density = law.get("hu_to_density", {})
    density_elastic = law.get("density_to_elastic_modulus", {})

    resolved_shear = law.get("resolved_shear_scales", {})

    directional = parse_directional_scales(package)
    poisson = parse_poisson_map(package)

    constants = {
        "hu_density_intercept": float(hu_density.get("intercept")),
        "hu_density_slope": float(hu_density.get("slope")),
        "elastic_coefficient": float(density_elastic.get("coefficient")),
        "elastic_exponent": float(density_elastic.get("exponent")),
        "Ex_scale": float(directional.get("Ex")),
        "Ey_scale": float(directional.get("Ey")),
        "Gxy_scale": float(resolved_shear.get("Gxy")),
        "Gxz_scale": float(resolved_shear.get("Gxz")),
        "Gyz_scale": float(resolved_shear.get("Gyz")),
        "nu_xy": float(poisson.get("nu_xy")),
        "nu_xz": float(poisson.get("nu_xz")),
        "nu_yz": float(poisson.get("nu_yz")),
    }

    return constants


def element_centroid_hu(points, tetra, ct_array, spacing_xyz):
    centroids = points[tetra].mean(axis=1)

    sx, sy, sz = spacing_xyz
    size_z, size_y, size_x = ct_array.shape

    ix = np.rint(centroids[:, 0] / sx).astype(int)
    iy = np.rint(centroids[:, 1] / sy).astype(int)
    iz = np.rint(centroids[:, 2] / sz).astype(int)

    ix = np.clip(ix, 0, size_x - 1)
    iy = np.clip(iy, 0, size_y - 1)
    iz = np.clip(iz, 0, size_z - 1)

    hu = ct_array[iz, iy, ix]

    return hu


def compute_material_values(hu, constants):
    raw_density = constants["hu_density_intercept"] + constants["hu_density_slope"] * hu
    effective_density = raw_density.copy()

    mapping_policy = constants.get("mapping_policy", {})
    policy_candidate = mapping_policy.get("policy_candidate", {}) if mapping_policy.get("approved") else {}

    invalid_density = effective_density <= 0
    policy_applied_count = int(invalid_density.sum())

    if policy_applied_count > 0 and mapping_policy.get("approved"):
        density_floor = float(policy_candidate.get("density_floor_g_cm3"))
        effective_density[invalid_density] = density_floor

    ez = constants["elastic_coefficient"] * np.power(effective_density, constants["elastic_exponent"])

    ex = constants["Ex_scale"] * ez
    ey = constants["Ey_scale"] * ez

    gxy = constants["Gxy_scale"] * ez
    gxz = constants["Gxz_scale"] * ez
    gyz = constants["Gyz_scale"] * ez

    return {
        "hu": hu,
        "raw_density": raw_density,
        "density": effective_density,
        "density_domain_policy_applied_count": policy_applied_count,
        "density_domain_policy_applied": bool(policy_applied_count > 0 and mapping_policy.get("approved")),
        "Ez": ez,
        "Ex": ex,
        "Ey": ey,
        "Gxy": gxy,
        "Gxz": gxz,
        "Gyz": gyz,
        "nu_xy": np.full_like(ez, constants["nu_xy"], dtype=float),
        "nu_xz": np.full_like(ez, constants["nu_xz"], dtype=float),
        "nu_yz": np.full_like(ez, constants["nu_yz"], dtype=float),
    }


def assign_bins(values, requested_bin_count: int):
    ez = values["Ez"]

    finite = ez[np.isfinite(ez)]

    if finite.size == 0:
        raise ValueError("No finite Ez values for material binning.")

    requested_bin_count = max(1, int(requested_bin_count))

    if finite.size < requested_bin_count:
        requested_bin_count = int(finite.size)

    edges = np.quantile(finite, np.linspace(0, 1, requested_bin_count + 1))
    edges = np.unique(edges)

    if len(edges) < 2:
        bin_ids = np.ones_like(ez, dtype=int)
        used_edges = np.array([finite.min(), finite.max()])
    else:
        bin_ids = np.searchsorted(edges[1:-1], ez, side="right") + 1
        used_edges = edges

    actual_bins = sorted(set(int(x) for x in bin_ids.tolist()))

    return bin_ids, used_edges, actual_bins


def build_material_bins(values, bin_ids, constants):
    rows = []

    for bin_id in sorted(set(int(x) for x in bin_ids.tolist())):
        idx = bin_ids == bin_id

        row = {
            "material_id": int(bin_id),
            "material_name": f"mat_bin_{int(bin_id):03d}",
            "element_count": int(idx.sum()),
            "hu_mean": float(values["hu"][idx].mean()),
            "hu_min": float(values["hu"][idx].min()),
            "hu_max": float(values["hu"][idx].max()),
            "density_mean_g_cm3": float(values["density"][idx].mean()),
            "Ez_MPa": float(values["Ez"][idx].mean()),
            "Ex_MPa": float(values["Ex"][idx].mean()),
            "Ey_MPa": float(values["Ey"][idx].mean()),
            "Gxy_MPa": float(values["Gxy"][idx].mean()),
            "Gxz_MPa": float(values["Gxz"][idx].mean()),
            "Gyz_MPa": float(values["Gyz"][idx].mean()),
            "nu_xy": constants["nu_xy"],
            "nu_xz": constants["nu_xz"],
            "nu_yz": constants["nu_yz"],
        }

        rows.append(row)

    return rows


def build_element_assignments(tetra, bin_ids, values):
    rows = []

    for i, mat_id in enumerate(bin_ids):
        rows.append({
            "element_id": i + 1,
            "material_id": int(mat_id),
            "hu": float(values["hu"][i]),
            "density_g_cm3": float(values["density"][i]),
            "Ez_MPa": float(values["Ez"][i]),
        })

    return rows


def write_febio_model(path: Path, points, tetra, bin_ids, material_bins, package_path: Path, mesh_path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    bins_by_id = {int(row["material_id"]): row for row in material_bins}

    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<febio_spec version="4.0">\n')
        f.write('  <Module type="solid"/>\n')

        f.write('  <Control>\n')
        f.write('    <analysis>STATIC</analysis>\n')
        f.write('    <time_steps>10</time_steps>\n')
        f.write('    <step_size>0.1</step_size>\n')
        f.write('    <solver>\n')
        f.write('      <max_refs>15</max_refs>\n')
        f.write('      <dtol>0.001</dtol>\n')
        f.write('      <etol>0.01</etol>\n')
        f.write('      <rtol>0</rtol>\n')
        f.write('      <lstol>0.9</lstol>\n')
        f.write('    </solver>\n')
        f.write('  </Control>\n')

        f.write('  <Material>\n')
        for row in material_bins:
            mid = int(row["material_id"])
            name = html.escape(row["material_name"])

            f.write(f'    <material id="{mid}" name="{name}" type="orthotropic elastic">\n')
            f.write(f'      <E1>{row["Ex_MPa"]:.10g}</E1>\n')
            f.write(f'      <E2>{row["Ey_MPa"]:.10g}</E2>\n')
            f.write(f'      <E3>{row["Ez_MPa"]:.10g}</E3>\n')
            f.write(f'      <v12>{row["nu_xy"]:.10g}</v12>\n')
            f.write(f'      <v23>{row["nu_yz"]:.10g}</v23>\n')
            f.write(f'      <v31>{row["nu_xz"]:.10g}</v31>\n')
            f.write(f'      <G12>{row["Gxy_MPa"]:.10g}</G12>\n')
            f.write(f'      <G23>{row["Gyz_MPa"]:.10g}</G23>\n')
            f.write(f'      <G31>{row["Gxz_MPa"]:.10g}</G31>\n')
            f.write('    </material>\n')
        f.write('  </Material>\n')

        f.write('  <Mesh>\n')
        f.write('    <Nodes name="Object01">\n')
        for i, p in enumerate(points, start=1):
            f.write(f'      <node id="{i}">{p[0]:.10g},{p[1]:.10g},{p[2]:.10g}</node>\n')
        f.write('    </Nodes>\n')

        element_id = 1
        for mat_id in sorted(bins_by_id.keys()):
            part_name = f'mat_bin_{mat_id:03d}'
            f.write(f'    <Elements type="tet4" name="{part_name}">\n')

            indices = np.where(bin_ids == mat_id)[0]

            for idx in indices:
                tet = tetra[idx] + 1
                f.write(
                    f'      <elem id="{element_id}">{tet[0]},{tet[1]},{tet[2]},{tet[3]}</elem>\n'
                )
                element_id += 1

            f.write('    </Elements>\n')

        f.write('  </Mesh>\n')

        f.write('  <MeshDomains>\n')
        for mat_id in sorted(bins_by_id.keys()):
            part_name = f'mat_bin_{mat_id:03d}'
            mat_name = html.escape(bins_by_id[mat_id]["material_name"])
            f.write(f'    <SolidDomain name="{part_name}" mat="{mat_name}"/>\n')
        f.write('  </MeshDomains>\n')

        f.write('  <Output>\n')
        f.write('    <plotfile type="febio">\n')
        f.write('      <var type="displacement"/>\n')
        f.write('      <var type="stress"/>\n')
        f.write('    </plotfile>\n')
        f.write('  </Output>\n')


        f.write('</febio_spec>\n')


def default_mapping_policy_path(case_id: str):
    return ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_APPROVED.json"


def load_approved_mapping_policy(case_id: str):
    path = default_mapping_policy_path(case_id)

    if not path.exists():
        return {
            "approved": False,
            "policy_path": str(path),
            "policy_candidate": {},
        }

    data = load_json(path)

    if data.get("approved") is not True:
        return {
            "approved": False,
            "policy_path": str(path),
            "policy_candidate": {},
        }

    return {
        "approved": True,
        "policy_path": str(path),
        "policy_candidate": data.get("policy_candidate", {}),
    }


def run_febio_model_generation(user_input: FebioModelGenerationInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    volume_mesh_result_path = Path(user_input.volume_mesh_result_path) if user_input.volume_mesh_result_path else default_volume_mesh_result_path(case_id)
    material_package_path = Path(user_input.material_law_package_path) if user_input.material_law_package_path else default_material_law_package_path(case_id)
    reference_ct_path = Path(user_input.reference_ct_path) if user_input.reference_ct_path else default_reference_ct_path(case_id)

    mesh_ok, mesh_path_from_result, mesh_blockers = validate_volume_mesh_result(volume_mesh_result_path)
    blockers.extend(mesh_blockers)

    volume_mesh_path = Path(user_input.volume_mesh_path) if user_input.volume_mesh_path else Path(mesh_path_from_result)

    if user_input.volume_mesh_path and not volume_mesh_path.exists():
        blockers.append("USER_PROVIDED_VOLUME_MESH_NOT_FOUND")

    material_ok, package, material_blockers = validate_material_package(material_package_path)
    blockers.extend(material_blockers)

    if not reference_ct_path.exists():
        blockers.append("REFERENCE_CT_VOLUME_NOT_FOUND")

    if blockers:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="FEBIO_MODEL_GENERATION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    try:
        mesh = meshio.read(volume_mesh_path)
        points = np.asarray(mesh.points, dtype=float)
        tetra = collect_tetra_cells(mesh)
    except Exception as e:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="VOLUME_MESH_READ_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=[f"VOLUME_MESH_READ_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    if tetra.shape[0] == 0:
        blockers.append("NO_TETRA_ELEMENTS_IN_VOLUME_MESH")

    try:
        ct_image, ct_array, spacing_xyz, size_xyz = read_ct_volume(reference_ct_path)
        ct_read_success = True
    except Exception as e:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="REFERENCE_CT_READ_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            warnings=warnings,
            blockers=[f"REFERENCE_CT_READ_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    try:
        constants = get_material_law_constants(package)
        constants["mapping_policy"] = load_approved_mapping_policy(case_id)
    except Exception as e:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="MATERIAL_LAW_CONSTANTS_PARSE_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            ct_read_success=ct_read_success,
            warnings=warnings,
            blockers=[f"MATERIAL_LAW_CONSTANTS_PARSE_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    hu = element_centroid_hu(points, tetra, ct_array, spacing_xyz)
    values = compute_material_values(hu, constants)

    raw_invalid_density_count = int(np.sum(values.get("raw_density", values["density"]) <= 0))

    if raw_invalid_density_count > 0:
        policy = constants.get("mapping_policy", {})
        candidate = policy.get("policy_candidate", {})

        if not policy.get("approved"):
            blockers.append("RAW_NON_POSITIVE_DENSITY_FOUND_AND_NO_APPROVED_MAPPING_POLICY")
        else:
            expected_count = int(candidate.get("invalid_density_count", -1))
            if expected_count != raw_invalid_density_count:
                warnings.append(
                    f"MAPPING_POLICY_INVALID_COUNT_MISMATCH:{expected_count}_vs_{raw_invalid_density_count}"
                )
            else:
                warnings.append(
                    f"APPROVED_DENSITY_DOMAIN_POLICY_APPLIED_TO_ELEMENTS:{raw_invalid_density_count}"
                )

    if np.any(values["density"] <= 0):
        blockers.append("NON_POSITIVE_EFFECTIVE_DENSITY_COMPUTED_FOR_SOME_ELEMENTS")

    if np.any(values["Ez"] <= 0):
        blockers.append("NON_POSITIVE_EZ_COMPUTED_FOR_SOME_ELEMENTS")

    if np.any(~np.isfinite(values["Ez"])):
        blockers.append("NON_FINITE_EZ_COMPUTED_FOR_SOME_ELEMENTS")

    if blockers:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="FEBIO_MATERIAL_MAPPING_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            ct_read_success=ct_read_success,
            node_count=int(points.shape[0]),
            tetra_count=int(tetra.shape[0]),
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    bin_ids, edges, actual_bins = assign_bins(values, user_input.material_bin_count)
    material_bins = build_material_bins(values, bin_ids, constants)
    assignments = build_element_assignments(tetra, bin_ids, values)

    export_csv(paths["material_bins_csv"], material_bins)
    export_csv(paths["element_assignments_csv"], assignments)

    try:
        write_febio_model(
            path=paths["febio_model"],
            points=points,
            tetra=tetra,
            bin_ids=bin_ids,
            material_bins=material_bins,
            package_path=material_package_path,
            mesh_path=volume_mesh_path,
        )
    except Exception as e:
        result = FebioModelGenerationResult(
            case_id=case_id,
            febio_model_status="FEBIO_FILE_WRITE_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            volume_mesh_result_path=str(volume_mesh_result_path),
            volume_mesh_path=str(volume_mesh_path),
            material_law_package_path=str(material_package_path),
            reference_ct_path=str(reference_ct_path),
            volume_mesh_passed=mesh_ok,
            material_law_validated=material_ok,
            ct_read_success=ct_read_success,
            node_count=int(points.shape[0]),
            tetra_count=int(tetra.shape[0]),
            material_bin_count=len(material_bins),
            warnings=warnings,
            blockers=[f"FEBIO_FILE_WRITE_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    if not paths["febio_model"].exists():
        blockers.append("FEBIO_MODEL_FILE_NOT_CREATED")

    if len(material_bins) < 2:
        warnings.append("LOW_MATERIAL_BIN_COUNT_REVIEW_REQUIRED")

    status = "FEBIO_MODEL_GENERATION_PASS" if not blockers else "FEBIO_MODEL_GENERATION_FAIL"
    next_agent = "AGENT_11_BOUNDARY_LOAD_CONFIGURATION" if not blockers else "USER_ACTION_REQUIRED"

    result = FebioModelGenerationResult(
        case_id=case_id,
        febio_model_status=status,
        next_agent=next_agent,
        volume_mesh_result_path=str(volume_mesh_result_path),
        volume_mesh_path=str(volume_mesh_path),
        material_law_package_path=str(material_package_path),
        reference_ct_path=str(reference_ct_path),
        volume_mesh_passed=mesh_ok,
        material_law_validated=material_ok,
        ct_read_success=ct_read_success,
        febio_model_path=str(paths["febio_model"]),
        febio_model_created=paths["febio_model"].exists(),
        node_count=int(points.shape[0]),
        tetra_count=int(tetra.shape[0]),
        material_bin_count=len(material_bins),
        hu_min=float(np.min(values["hu"])),
        hu_max=float(np.max(values["hu"])),
        hu_mean=float(np.mean(values["hu"])),
        density_min_g_cm3=float(np.min(values["density"])),
        density_max_g_cm3=float(np.max(values["density"])),
        ez_min_mpa=float(np.min(values["Ez"])),
        ez_max_mpa=float(np.max(values["Ez"])),
        material_bins_csv=str(paths["material_bins_csv"]),
        element_material_assignments_csv=str(paths["element_assignments_csv"]),
        solver_ready=False,
        boundary_conditions_included=False,
        loads_included=False,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    notes = f"""
Agent-10 FEBio Model Generation
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Generated FEBio base model:
{paths["febio_model"]}

Important:
- Boundary conditions are not included yet.
- Loads are not included yet.
- Solver should not be run before Agent-11.
- Material bins were derived from CT HU values and the validated HU/density material-law package.
- No manual material values were introduced.
"""
    paths["notes_txt"].write_text(notes, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: FebioModelGenerationResult):
    note_path = ROOT / "paper_notes" / "febio_model_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-10 FEBio Model Generation

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.febio_model_status}
Sonraki ajan: {result.next_agent}

Girdi:
- Volume mesh: {result.volume_mesh_path}
- Material-law package: {result.material_law_package_path}
- Reference CT volume: {result.reference_ct_path}

Ã‡Ä±ktÄ±:
- FEBio base model: {result.febio_model_path}
- Material bins CSV: {result.material_bins_csv}
- Element material assignments CSV: {result.element_material_assignments_csv}

Model metrikleri:
- Node count: {result.node_count}
- Tetra count: {result.tetra_count}
- Material bin count: {result.material_bin_count}
- HU min/max/mean: {result.hu_min}, {result.hu_max}, {result.hu_mean}
- Ez min/max MPa: {result.ez_min_mpa}, {result.ez_max_mpa}

Not:
Bu ajan yalnÄ±zca FEBio base model Ã¼retir. Boundary condition ve load iÃ§ermez. Solver-ready deÄŸildir.
UyarÄ±lar: {result.warnings}
BloklayÄ±cÄ±lar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)

