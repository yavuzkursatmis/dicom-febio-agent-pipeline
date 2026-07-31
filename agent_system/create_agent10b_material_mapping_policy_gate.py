from pathlib import Path
import json
import hashlib
from datetime import datetime

import numpy as np
import meshio
import SimpleITK as sitk

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def make_id(raw: str):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def collect_tetra_cells(mesh):
    cells = []
    for block in mesh.cells:
        if block.type == "tetra":
            cells.append(block.data)
    if not cells:
        return np.empty((0, 4), dtype=int)
    return np.vstack(cells)


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

    return ct_array[iz, iy, ix]


def main():
    case_id = "real_dicom_check_001_anon_T1"

    mesh_path = ROOT / "cases" / case_id / "10_volume_mesh_generation" / "volume_mesh.msh"
    ct_path = ROOT / "cases" / case_id / "04_segmentation" / "volume_resampled.nii.gz"
    material_path = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"
    diagnostic_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10A_MATERIAL_MAPPING_DIAGNOSTIC.json"

    out_dir = ROOT / "cases" / case_id / "11_febio_model_generation"
    gate_path = out_dir / "AGENT10B_MATERIAL_MAPPING_POLICY_GATE_RESULT.json"
    review_input_path = out_dir / "AGENT10B_MATERIAL_MAPPING_POLICY_REVIEW_INPUT.json"

    package = load_json(material_path)
    diagnostic = load_json(diagnostic_path)

    law = package["structured_law"]
    intercept = float(law["hu_to_density"]["intercept"])
    slope = float(law["hu_to_density"]["slope"])

    mesh = meshio.read(mesh_path)
    points = np.asarray(mesh.points, dtype=float)
    tetra = collect_tetra_cells(mesh)

    image = sitk.ReadImage(str(ct_path))
    ct_array = sitk.GetArrayFromImage(image).astype(float)
    spacing_xyz = list(image.GetSpacing())

    hu = element_centroid_hu(points, tetra, ct_array, spacing_xyz)
    density = intercept + slope * hu

    valid = density > 0
    invalid = ~valid

    blockers = []
    candidates = []

    invalid_fraction = float(invalid.sum() / len(density))
    max_allowed_invalid_fraction = 0.05

    if int(invalid.sum()) == 0:
        blockers.append("NO_INVALID_DENSITY_ELEMENTS_FOUND_POLICY_NOT_NEEDED")

    if invalid_fraction > max_allowed_invalid_fraction:
        blockers.append("INVALID_DENSITY_FRACTION_TOO_HIGH_FOR_AUTOMATED_POLICY")

    if not valid.any():
        blockers.append("NO_POSITIVE_DENSITY_VALUES_AVAILABLE_FOR_DATA_DERIVED_FLOOR")

    if not blockers:
        positive_density_values = density[valid]
        density_floor = float(np.min(positive_density_values))

        candidate_raw = json.dumps({
            "case_id": case_id,
            "policy_type": "CLIP_NON_POSITIVE_DENSITY_TO_MIN_POSITIVE_CASE_DERIVED_DENSITY",
            "density_floor_g_cm3": density_floor,
            "invalid_density_count": int(invalid.sum()),
            "invalid_density_fraction": invalid_fraction,
            "source_formula": law["hu_to_density"],
            "diagnostic": diagnostic,
        }, ensure_ascii=False, sort_keys=True)

        policy_candidate_id = make_id(candidate_raw)

        candidates.append({
            "policy_candidate_id": policy_candidate_id,
            "policy_type": "CLIP_NON_POSITIVE_DENSITY_TO_MIN_POSITIVE_CASE_DERIVED_DENSITY",
            "density_floor_g_cm3": density_floor,
            "invalid_density_count": int(invalid.sum()),
            "invalid_density_fraction": invalid_fraction,
            "valid_density_count": int(valid.sum()),
            "max_allowed_invalid_fraction": max_allowed_invalid_fraction,
            "hu_zero_density_threshold": float(-intercept / slope),
            "reasoning_summary": (
                "A small fraction of elements produced non-positive density because their centroid HU values "
                "fall below the zero-density threshold of the approved HU-density law. The agent proposes replacing "
                "only those invalid densities with the lowest positive density computed from this same case using "
                "the approved source-derived formula. This avoids manual material entry and preserves source/data traceability."
            ),
            "manual_values_entered": False,
            "clinical_use": False,
        })

    if candidates:
        gate_status = "WAITING_FOR_AGENT10B_MAPPING_POLICY_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
    else:
        gate_status = "NO_VALID_MAPPING_POLICY_CANDIDATE"
        next_agent = "USER_ACTION_REQUIRED"

    gate = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status,
        "next_agent": next_agent,
        "allowed_policy_candidates": candidates,
        "source_diagnostic_json": str(diagnostic_path),
        "source_material_law_package": str(material_path),
        "clinical_use": False,
        "blockers": blockers,
        "rules": [
            "Manual density, HU, E, or Poisson values are forbidden.",
            "Only an agent-derived policy_candidate_id may be approved.",
            "The policy is allowed only if invalid density fraction is small.",
            "The density floor must be computed from the same case and approved source-derived formula.",
            "This is pipeline-development approval, not clinical approval."
        ],
    }

    save_json(gate_path, gate)

    review_input = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT10B_MATERIAL_MAPPING_POLICY_APPROVAL",
        "reviewer_decision": "PENDING",
        "approved_policy_candidate_id": "",
        "approved_for_agent10_retry": False,
        "approved_next_agent": "AGENT_10_FEBIO_MODEL_GENERATION_RETRY",
        "clinical_use": False,
        "reviewer_notes": "",
        "source_policy_gate_json": str(gate_path),
        "rules": [
            "Do not manually enter density, HU, E, Poisson, or equation values.",
            "Approve only one policy_candidate_id from allowed_policy_candidates.",
            "Approval only permits Agent-10 retry."
        ],
    }

    if not review_input_path.exists():
        save_json(review_input_path, review_input)

    print("AGENT10B_MATERIAL_MAPPING_POLICY_GATE_CREATED=True")
    print("GATE_STATUS=" + gate_status)
    print("NEXT_AGENT=" + next_agent)
    print("POLICY_CANDIDATES_COUNT=" + str(len(candidates)))
    print("BLOCKERS=" + str(blockers))

    if candidates:
        c = candidates[0]
        print("TOP_POLICY_CANDIDATE_ID=" + c["policy_candidate_id"])
        print("TOP_POLICY_TYPE=" + c["policy_type"])
        print("INVALID_DENSITY_COUNT=" + str(c["invalid_density_count"]))
        print("INVALID_DENSITY_FRACTION=" + str(c["invalid_density_fraction"]))
        print("DENSITY_FLOOR_G_CM3=" + str(c["density_floor_g_cm3"]))
        print("REASONING=" + c["reasoning_summary"])


if __name__ == "__main__":
    main()
