from pathlib import Path
import json
import csv
from datetime import datetime
import html

import numpy as np
import meshio

from agent_system.schemas.boundary_load_configuration_schema import (
    BoundaryLoadConfigurationInput,
    BoundaryLoadConfigurationResult,
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


def default_febio_model_result_path(case_id: str):
    return ROOT / "cases" / case_id / "11_febio_model_generation" / "FEBIO_MODEL_GENERATION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "12_boundary_load_configuration"
    return {
        "result_json": out_dir / "BOUNDARY_LOAD_CONFIGURATION_RESULT.json",
        "node_sets_csv": out_dir / "BOUNDARY_NODE_SETS.csv",
        "febio_candidate": out_dir / "febio_model_boundary_load_candidate.feb",
        "review_input": out_dir / "BOUNDARY_LOAD_REVIEW_INPUT.json",
    }


def find_target_understanding(case_id: str):
    case_dir = ROOT / "cases" / case_id
    candidates = list(case_dir.rglob("TARGET_UNDERSTANDING_RESULT.json"))

    if not candidates:
        return {}

    try:
        return load_json(candidates[0])
    except Exception:
        return {}


def validate_febio_model_result(path: Path):
    blockers = []

    if not path.exists():
        return {
            "ok": False,
            "febio_model_path": "",
            "volume_mesh_path": "",
            "blockers": ["FEBIO_MODEL_GENERATION_RESULT_NOT_FOUND"],
        }

    data = load_json(path)

    passed = data.get("febio_model_status") == "FEBIO_MODEL_GENERATION_PASS"
    febio_model_path = data.get("febio_model_path", "")
    volume_mesh_path = data.get("volume_mesh_path", "")

    if not passed:
        blockers.append("FEBIO_MODEL_STATUS_NOT_PASS")

    if not febio_model_path:
        blockers.append("FEBIO_MODEL_PATH_MISSING")
    elif not Path(febio_model_path).exists():
        blockers.append("FEBIO_MODEL_FILE_NOT_FOUND")

    if not volume_mesh_path:
        blockers.append("VOLUME_MESH_PATH_MISSING")
    elif not Path(volume_mesh_path).exists():
        blockers.append("VOLUME_MESH_FILE_NOT_FOUND")

    return {
        "ok": len(blockers) == 0,
        "febio_model_path": febio_model_path,
        "volume_mesh_path": volume_mesh_path,
        "blockers": blockers,
    }


def read_mesh_points(mesh_path: Path):
    mesh = meshio.read(mesh_path)
    points = np.asarray(mesh.points, dtype=float)
    return points


def select_endplate_nodes(points, band_fraction: float):
    z = points[:, 2]

    z_min = float(np.min(z))
    z_max = float(np.max(z))
    height = z_max - z_min

    if height <= 0:
        raise ValueError("Invalid mesh height: z_max <= z_min")

    band_fraction = float(band_fraction)
    if band_fraction <= 0 or band_fraction >= 0.5:
        raise ValueError("endplate_band_fraction must be in (0, 0.5)")

    inferior_threshold = z_min + band_fraction * height
    superior_threshold = z_max - band_fraction * height

    inferior_ids = np.where(z <= inferior_threshold)[0] + 1
    superior_ids = np.where(z >= superior_threshold)[0] + 1

    return {
        "z_min": z_min,
        "z_max": z_max,
        "height": height,
        "inferior_threshold": float(inferior_threshold),
        "superior_threshold": float(superior_threshold),
        "inferior_node_ids": inferior_ids.astype(int).tolist(),
        "superior_node_ids": superior_ids.astype(int).tolist(),
    }


def chunk_list(values, chunk_size=20):
    for i in range(0, len(values), chunk_size):
        yield values[i:i + chunk_size]


def node_set_xml(name: str, node_ids):
    """
    FEBio 4.12 accepts NodeSet as a comma-separated node-id value.
    The previous child-node form <node id="..."/> caused:
    tag "NodeSet": invalid value
    """
    clean_ids = [int(x) for x in node_ids]

    lines = [f'    <NodeSet name="{html.escape(name)}">']

    for chunk in chunk_list(clean_ids, chunk_size=20):
        lines.append("      " + ",".join(str(x) for x in chunk))

    lines.append('    </NodeSet>')
    return "\n".join(lines)


def boundary_load_xml(displacement_mm: float):
    return f'''
  <Boundary>
    <bc name="fix_inferior_xyz" type="zero displacement" node_set="inferior_fixed_nodes">
      <x_dof>1</x_dof>
      <y_dof>1</y_dof>
      <z_dof>1</z_dof>
    </bc>
    <bc name="prescribed_superior_z_compression" type="prescribed displacement" node_set="superior_loaded_nodes">
      <dof>z</dof>
      <value lc="1">{displacement_mm:.10g}</value>
      <relative>0</relative>
    </bc>
  </Boundary>

  <LoadData>
    <load_controller id="1" name="compression_ramp" type="loadcurve">
      <interpolate>LINEAR</interpolate>
      <points>
        <point>0,0</point>
        <point>1,1</point>
      </points>
    </load_controller>
  </LoadData>
'''


def insert_boundary_load_candidate(base_feb: Path, out_feb: Path, inferior_ids, superior_ids, displacement_mm: float):
    text = base_feb.read_text(encoding="utf-8-sig")

    node_sets = "\n".join([
        node_set_xml("inferior_fixed_nodes", inferior_ids),
        node_set_xml("superior_loaded_nodes", superior_ids),
    ])

    if "</Mesh>" not in text:
        raise ValueError("FEBio base file does not contain </Mesh> tag.")

    text = text.replace("</Mesh>", node_sets + "\n  </Mesh>", 1)

    bl_xml = boundary_load_xml(displacement_mm)

    if "<Output>" in text:
        text = text.replace("  <Output>", bl_xml + "\n  <Output>", 1)
    else:
        text = text.replace("</febio_spec>", bl_xml + "\n</febio_spec>", 1)

    out_feb.parent.mkdir(parents=True, exist_ok=True)
    out_feb.write_text(text, encoding="utf-8")


def create_review_input(path: Path, case_id: str, candidate_feb: Path, displacement_mm: float):
    review = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT11_BOUNDARY_LOAD_CONFIGURATION_REVIEW",
        "reviewer_decision": "PENDING",
        "approved_boundary_load_candidate": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "approved_for_solver_configuration": False,
        "clinical_use": False,
        "candidate_febio_model_path": str(candidate_feb),
        "reviewer_notes": "",
        "rules": [
            "This candidate is protocol-derived for axial compression setup.",
            "The prescribed displacement was derived from the approved protocol candidate and still requires human review before solver execution.",
            "Solver must not be run until this review is approved.",
            "Manual edits to FEBio file are not allowed in the automated pipeline."
        ],
        "candidate_parameters": {
            "prescribed_displacement_mm": displacement_mm,
            "load_type": "prescribed_superior_z_displacement",
            "fixed_region": "inferior_endplate",
            "loaded_region": "superior_endplate"
        }
    }

    if not path.exists():
        save_json(path, review)


def run_boundary_load_configuration(user_input: BoundaryLoadConfigurationInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    febio_result_path = Path(user_input.febio_model_result_path) if user_input.febio_model_result_path else default_febio_model_result_path(case_id)

    febio_validation = validate_febio_model_result(febio_result_path)
    blockers.extend(febio_validation["blockers"])

    base_feb_path = Path(user_input.febio_model_path) if user_input.febio_model_path else Path(febio_validation.get("febio_model_path", ""))
    mesh_path = Path(user_input.volume_mesh_path) if user_input.volume_mesh_path else Path(febio_validation.get("volume_mesh_path", ""))

    target = find_target_understanding(case_id)

    analysis_type = (
        target.get("standardized_analysis_type")
        or target.get("analysis_type")
        or "axial_compression"
    )

    load_region = (
        target.get("load_region")
        or target.get("standardized_load_region")
        or "superior_endplate"
    )

    if analysis_type != "axial_compression":
        warnings.append(f"ANALYSIS_TYPE_NOT_AXIAL_COMPRESSION_REVIEW_REQUIRED:{analysis_type}")

    if load_region != "superior_endplate":
        warnings.append(f"LOAD_REGION_NOT_SUPERIOR_ENDPLATE_REVIEW_REQUIRED:{load_region}")

    if blockers:
        result = BoundaryLoadConfigurationResult(
            case_id=case_id,
            boundary_load_status="BOUNDARY_LOAD_CONFIGURATION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            febio_model_result_path=str(febio_result_path),
            febio_model_base_path=str(base_feb_path),
            volume_mesh_path=str(mesh_path),
            febio_model_generation_passed=febio_validation["ok"],
            analysis_type=analysis_type,
            load_region=load_region,
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    try:
        points = read_mesh_points(mesh_path)
        mesh_read_success = True
    except Exception as e:
        result = BoundaryLoadConfigurationResult(
            case_id=case_id,
            boundary_load_status="VOLUME_MESH_READ_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            febio_model_result_path=str(febio_result_path),
            febio_model_base_path=str(base_feb_path),
            volume_mesh_path=str(mesh_path),
            febio_model_generation_passed=febio_validation["ok"],
            base_model_read_success=base_feb_path.exists(),
            analysis_type=analysis_type,
            load_region=load_region,
            warnings=warnings,
            blockers=[f"VOLUME_MESH_READ_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    try:
        selected = select_endplate_nodes(points, user_input.endplate_band_fraction)
    except Exception as e:
        result = BoundaryLoadConfigurationResult(
            case_id=case_id,
            boundary_load_status="ENDPLATE_NODE_SELECTION_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            febio_model_result_path=str(febio_result_path),
            febio_model_base_path=str(base_feb_path),
            volume_mesh_path=str(mesh_path),
            febio_model_generation_passed=febio_validation["ok"],
            base_model_read_success=base_feb_path.exists(),
            mesh_read_success=mesh_read_success,
            analysis_type=analysis_type,
            load_region=load_region,
            warnings=warnings,
            blockers=[f"ENDPLATE_NODE_SELECTION_FAIL:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    inferior_ids = selected["inferior_node_ids"]
    superior_ids = selected["superior_node_ids"]

    if len(inferior_ids) < 10:
        blockers.append("TOO_FEW_INFERIOR_FIXED_NODES")

    if len(superior_ids) < 10:
        blockers.append("TOO_FEW_SUPERIOR_LOADED_NODES")

    protocol_path_text = str(getattr(user_input, "load_protocol_path", "") or "").strip()

    if protocol_path_text:
        protocol_path = Path(protocol_path_text)

        if not protocol_path.exists():
            blockers.append("LOAD_PROTOCOL_FILE_NOT_FOUND")
            displacement_mm = 0.0
            load_magnitude_source = "LOAD_PROTOCOL_FILE_NOT_FOUND"
        else:
            protocol = load_json(protocol_path)

            if protocol.get("protocol_status") != "LOAD_PROTOCOL_CANDIDATE_APPROVED_FOR_AGENT11_APPLICATION":
                blockers.append("LOAD_PROTOCOL_NOT_APPROVED_FOR_AGENT11_APPLICATION")
                displacement_mm = 0.0
                load_magnitude_source = "LOAD_PROTOCOL_INVALID"
            else:
                apparent_strain = float(protocol.get("apparent_strain", 0.0))

                if apparent_strain <= 0:
                    blockers.append("LOAD_PROTOCOL_APPARENT_STRAIN_NON_POSITIVE")
                    displacement_mm = 0.0
                    load_magnitude_source = "LOAD_PROTOCOL_INVALID_APPARENT_STRAIN"
                else:
                    displacement_mm = -apparent_strain * selected["height"]
                    load_magnitude_source = "LITERATURE_PROTOCOL_DERIVED_APPARENT_STRAIN"
                    warnings.append(
                        "LITERATURE_PROTOCOL_DERIVED_LOAD_REVIEW_REQUIRED:"
                        + str(round(displacement_mm, 6))
                    )

    elif user_input.prescribed_displacement_mm != 0:
        displacement_mm = float(user_input.prescribed_displacement_mm)
        load_magnitude_source = "USER_PROVIDED_REVIEW_REQUIRED"
        warnings.append("USER_PROVIDED_LOAD_MAGNITUDE_REQUIRES_REVIEW")

    else:
        blockers.append("LOAD_PROTOCOL_REQUIRED_NO_DEVELOPMENT_LOAD_ALLOWED")
        displacement_mm = 0.0
        load_magnitude_source = "BLOCKED_NO_PROTOCOL_DERIVED_LOAD"

    node_rows = []

    for node_id in inferior_ids:
        node_rows.append({"node_id": node_id, "node_set": "inferior_fixed_nodes"})

    for node_id in superior_ids:
        node_rows.append({"node_id": node_id, "node_set": "superior_loaded_nodes"})

    export_csv(paths["node_sets_csv"], node_rows)

    if blockers:
        status = "BOUNDARY_LOAD_CONFIGURATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        boundary_candidate_created = False
    else:
        try:
            insert_boundary_load_candidate(
                base_feb=base_feb_path,
                out_feb=paths["febio_candidate"],
                inferior_ids=inferior_ids,
                superior_ids=superior_ids,
                displacement_mm=displacement_mm,
            )
            boundary_candidate_created = True
        except Exception as e:
            blockers.append(f"FEBIO_BOUNDARY_LOAD_CANDIDATE_WRITE_FAIL:{type(e).__name__}:{e}")
            boundary_candidate_created = False

        if blockers:
            status = "BOUNDARY_LOAD_CONFIGURATION_FAIL"
            next_agent = "USER_ACTION_REQUIRED"
        else:
            status = "BOUNDARY_LOAD_CONFIGURATION_REVIEW_REQUIRED"
            next_agent = "HUMAN_REVIEW_GATE"
            create_review_input(paths["review_input"], case_id, paths["febio_candidate"], displacement_mm)

    result = BoundaryLoadConfigurationResult(
        case_id=case_id,
        boundary_load_status=status,
        next_agent=next_agent,
        febio_model_result_path=str(febio_result_path),
        febio_model_base_path=str(base_feb_path),
        febio_model_boundary_candidate_path=str(paths["febio_candidate"]) if boundary_candidate_created else "",
        volume_mesh_path=str(mesh_path),
        febio_model_generation_passed=febio_validation["ok"],
        base_model_read_success=base_feb_path.exists(),
        mesh_read_success=mesh_read_success,
        analysis_type=analysis_type,
        load_region=load_region,
        z_min_mm=selected["z_min"],
        z_max_mm=selected["z_max"],
        height_mm=selected["height"],
        endplate_band_fraction=user_input.endplate_band_fraction,
        inferior_threshold_z_mm=selected["inferior_threshold"],
        superior_threshold_z_mm=selected["superior_threshold"],
        fixed_node_count=len(inferior_ids),
        loaded_node_count=len(superior_ids),
        prescribed_displacement_mm=displacement_mm,
        development_engineering_strain=user_input.development_engineering_strain,
        load_magnitude_source=load_magnitude_source,
        node_sets_csv=str(paths["node_sets_csv"]),
        boundary_candidate_created=boundary_candidate_created,
        solver_ready=False,
        human_review_required=True,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())
    return result


def append_paper_note(case_id: str, result: BoundaryLoadConfigurationResult):
    note_path = ROOT / "paper_notes" / "febio_model_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-11 Boundary / Load Configuration

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.boundary_load_status}
Sonraki ajan: {result.next_agent}

Girdi:
- FEBio base model: {result.febio_model_base_path}
- Volume mesh: {result.volume_mesh_path}

Boundary/load candidate:
- Fixed node set: inferior_fixed_nodes
- Loaded node set: superior_loaded_nodes
- Fixed node count: {result.fixed_node_count}
- Loaded node count: {result.loaded_node_count}
- Prescribed displacement mm: {result.prescribed_displacement_mm}
- Load magnitude source: {result.load_magnitude_source}
- Candidate FEBio model: {result.febio_model_boundary_candidate_path}

Not:
Bu ajan solver Ã§alÄ±ÅŸtÄ±rmaz. OluÅŸturulan boundary/load candidate insan review onayÄ± olmadan solver-ready kabul edilmez.
UyarÄ±lar: {result.warnings}
BloklayÄ±cÄ±lar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)

