
from pathlib import Path
import subprocess
import json
from typing import Dict, Any, List

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"
FEBIO_EXE = Path(r"C:\Program Files\FEBioStudio\bin\febio4.exe")
GMSH_EXE = Path(r"C:\Tools\gmsh\gmsh.exe")


class AgentRunInput(BaseModel):
    case_id: str = Field(..., description="Case ID to process.")
    timeout_seconds: int = Field(1800, description="Maximum runtime in seconds.")


def case_dir(case_id: str) -> Path:
    return ROOT / "cases" / case_id


def parse_stdout_key_values(stdout: str) -> Dict[str, Any]:
    parsed = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def json_to_key_values(data: Dict[str, Any]) -> Dict[str, str]:
    parsed = {}
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            parsed[str(key).upper()] = repr(value)
        else:
            parsed[str(key).upper()] = str(value)
    return parsed


def run_script(script_relative_path: str, args: List[str], timeout_seconds: int = 1800) -> Dict[str, Any]:
    script_path = ROOT / script_relative_path

    if not script_path.exists():
        return {
            "success": False,
            "script": str(script_path),
            "return_code": -1,
            "stdout": "",
            "stderr": "",
            "parsed_stdout": {"BLOCKERS": f"['SCRIPT_NOT_FOUND:{script_path}']"},
            "blockers": [f"SCRIPT_NOT_FOUND:{script_path}"],
        }

    cmd = [str(PYTHON_EXE), str(script_path)] + args

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "script": str(script_path),
            "command": cmd,
            "return_code": -2,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "parsed_stdout": {"BLOCKERS": "['SUBPROCESS_TIMEOUT']"},
            "blockers": ["SUBPROCESS_TIMEOUT"],
        }

    parsed_stdout = parse_stdout_key_values(completed.stdout)

    return {
        "success": completed.returncode == 0,
        "script": str(script_path),
        "command": cmd,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_stdout": parsed_stdout,
        "blockers": [] if completed.returncode == 0 else [f"RETURN_CODE_NONZERO:{completed.returncode}"],
    }


def read_json_gate(case_id: str, relative_path: str, required: Dict[str, str] | None = None) -> Dict[str, Any]:
    path = case_dir(case_id) / relative_path

    if not path.exists():
        return {
            "success": False,
            "script": "json_gate",
            "json_path": str(path),
            "return_code": -1,
            "stdout": "",
            "stderr": "",
            "parsed_stdout": {"BLOCKERS": f"['JSON_GATE_FILE_NOT_FOUND:{path}']"},
            "blockers": [f"JSON_GATE_FILE_NOT_FOUND:{path}"],
        }

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    parsed = json_to_key_values(data)

    blockers = data.get("blockers", data.get("BLOCKERS", []))
    if blockers is None:
        blockers = []
    if isinstance(blockers, str):
        blockers = [] if blockers.strip() in ["", "[]"] else [blockers]

    if required:
        upper = {str(k).upper(): v for k, v in data.items()}
        for key, expected in required.items():
            actual = str(upper.get(key.upper(), ""))
            if actual != expected:
                blockers.append(f"JSON_GATE_REQUIRED_VALUE_NOT_MET:{key}:{actual}_NE_{expected}")

    return {
        "success": len(blockers) == 0,
        "script": "json_gate",
        "json_path": str(path),
        "return_code": 0 if len(blockers) == 0 else -1,
        "stdout": "\n".join(f"{k}={v}" for k, v in parsed.items()),
        "stderr": "",
        "parsed_stdout": parsed | {"BLOCKERS": repr(blockers)},
        "blockers": blockers,
    }


def run_agent08_geometry_preparation(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent08_geometry_preparation.py",
        [
            "--case-id", case_id,
            "--segmentation-mask-path", str(c / "05_segmentation" / "segmentation_mask.nii.gz"),
            "--material-law-package-path", str(c / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"),
        ],
        timeout_seconds,
    )


def run_agent09_volume_mesh_generation(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent09_volume_mesh_generation.py",
        [
            "--case-id", case_id,
            "--geometry-result-path", str(c / "09_geometry_mesh_preparation" / "GEOMETRY_PREPARATION_RESULT.json"),
            "--surface-stl-path", str(c / "09_geometry_mesh_preparation" / "geometry_surface.stl"),
            "--gmsh-exe-path", str(GMSH_EXE),
        ],
        timeout_seconds,
    )


def run_agent10_febio_model_generation(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent10_febio_model_generation.py",
        [
            "--case-id", case_id,
            "--volume-mesh-result-path", str(c / "10_volume_mesh_generation" / "VOLUME_MESH_GENERATION_RESULT.json"),
            "--volume-mesh-path", str(c / "10_volume_mesh_generation" / "volume_mesh.msh"),
            "--material-law-package-path", str(c / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE_VALIDATED.json"),
            "--reference-ct-path", str(c / "05_segmentation" / "input_ct_for_segmentation.nii.gz"),
            "--material-bin-count", "20",
        ],
        timeout_seconds,
    )


def run_agent11_boundary_load_configuration(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent11_boundary_load_configuration.py",
        [
            "--case-id", case_id,
            "--febio-model-result-path", str(c / "11_febio_model_generation" / "FEBIO_MODEL_GENERATION_RESULT.json"),
            "--febio-model-path", str(c / "11_febio_model_generation" / "febio_model_base.feb"),
            "--volume-mesh-path", str(c / "10_volume_mesh_generation" / "volume_mesh.msh"),
            "--load-protocol-path", str(c / "12_boundary_load_configuration" / "AGENT11V2_LOAD_PROTOCOL_CANDIDATE.json"),
            "--endplate-band-fraction", "0.08",
        ],
        timeout_seconds,
    )


def run_agent11_review_validation(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    return read_json_gate(
        case_id,
        "12_boundary_load_configuration/BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json",
        required={"APPROVED_FOR_SOLVER_EXECUTION": "True"},
    )


def run_agent12_febio_solver_execution(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent12_febio_solver_execution.py",
        [
            "--case-id", case_id,
            "--boundary-review-result-path", str(c / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json"),
            "--febio-exe-path", str(FEBIO_EXE),
            "--timeout-seconds", str(timeout_seconds),
        ],
        timeout_seconds,
    )


def run_agent13_solver_result_validation(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent13_solver_result_validation.py",
        [
            "--case-id", case_id,
            "--solver-execution-result-path", str(c / "13_solver_execution" / "FEBIO_SOLVER_EXECUTION_RESULT.json"),
        ],
        timeout_seconds,
    )


def run_agent14_result_extraction(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent14_result_extraction.py",
        [
            "--case-id", case_id,
            "--solver-result-validation-path", str(c / "14_solver_result_validation" / "SOLVER_RESULT_VALIDATION_RESULT.json"),
        ],
        timeout_seconds,
    )


def run_agent15_result_interpretation_precheck(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent15_result_interpretation_precheck.py",
        [
            "--case-id", case_id,
            "--result-extraction-path", str(c / "15_result_extraction" / "RESULT_EXTRACTION_RESULT.json"),
        ],
        timeout_seconds,
    )


def run_agent16_academic_report_draft(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    c = case_dir(case_id)
    return run_script(
        "agent_system/run_agent16_academic_report_draft.py",
        [
            "--case-id", case_id,
            "--interpretation-precheck-path", str(c / "16_result_interpretation_precheck" / "RESULT_INTERPRETATION_PRECHECK_RESULT.json"),
            "--language", "tr",
        ],
        timeout_seconds,
    )


def run_agent17_full_pipeline_audit(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    return run_script(
        "agent_system/run_agent17_full_pipeline_audit.py",
        ["--case-id", case_id],
        timeout_seconds,
    )


def run_clean_t1_upstream_evidence_audit(case_id: str, timeout_seconds: int = 1800) -> Dict[str, Any]:
    return read_json_gate(
        case_id,
        "18_full_pipeline_audit/CLEAN_T1_UPSTREAM_EVIDENCE_AUDIT.json",
        required={"AUDIT_STATUS": "CLEAN_T1_UPSTREAM_AUDIT_PASS"},
    )


AGENT_TOOL_FUNCTIONS = {
    "agent08_geometry_preparation": run_agent08_geometry_preparation,
    "agent09_volume_mesh_generation": run_agent09_volume_mesh_generation,
    "agent10_febio_model_generation": run_agent10_febio_model_generation,
    "agent11_boundary_load_configuration": run_agent11_boundary_load_configuration,
    "agent11_review_validation": run_agent11_review_validation,
    "agent12_febio_solver_execution": run_agent12_febio_solver_execution,
    "agent13_solver_result_validation": run_agent13_solver_result_validation,
    "agent14_result_extraction": run_agent14_result_extraction,
    "agent15_result_interpretation_precheck": run_agent15_result_interpretation_precheck,
    "agent16_academic_report_draft": run_agent16_academic_report_draft,
    "agent17_full_pipeline_audit": run_agent17_full_pipeline_audit,
    "clean_t1_upstream_evidence_audit": run_clean_t1_upstream_evidence_audit,
}


def make_structured_tool(name: str, func):
    return StructuredTool.from_function(
        func=func,
        name=name,
        description=f"Run deterministic pipeline tool: {name}",
        args_schema=AgentRunInput,
    )


LANGCHAIN_AGENT_TOOLS = [
    make_structured_tool(name, func)
    for name, func in AGENT_TOOL_FUNCTIONS.items()
]


def get_langchain_agent_tools():
    return LANGCHAIN_AGENT_TOOLS


def get_tool_names():
    return [tool.name for tool in LANGCHAIN_AGENT_TOOLS]
