from pathlib import Path
import json
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def file_status(path: Path):
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def main():
    case_id = "real_dicom_check_001_anon_T1"
    case_dir = ROOT / "cases" / case_id

    agents = [
        {
            "agent_id": "AGENT_01_DATA_INTAKE",
            "role": "Input detection and case initialization",
            "langgraph_node_required": True,
            "human_review_gate": False,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_02_DICOM_SAFETY",
            "role": "DICOM safety and PHI risk screening",
            "langgraph_node_required": True,
            "human_review_gate": False,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_03_IMAGE_QUALITY",
            "role": "Image quality and spacing checks",
            "langgraph_node_required": True,
            "human_review_gate": False,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_04_TARGET_UNDERSTANDING",
            "role": "Target/test understanding",
            "langgraph_node_required": True,
            "human_review_gate": False,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_05_SEGMENTATION",
            "role": "Segmentation/preprocessing",
            "langgraph_node_required": True,
            "human_review_gate": False,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_06_SEGMENTATION_VALIDATION",
            "role": "Segmentation validation",
            "langgraph_node_required": True,
            "human_review_gate": True,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_07_MATERIAL_SELECTION",
            "role": "Literature-backed material law selection and validation",
            "langgraph_node_required": True,
            "human_review_gate": True,
            "current_status": "IMPLEMENTED_EARLIER",
        },
        {
            "agent_id": "AGENT_08_GEOMETRY_PREPARATION",
            "role": "Mask to watertight STL geometry",
            "run_script": "agent_system/run_agent08_geometry_preparation.py",
            "result_json": case_dir / "09_geometry_mesh_preparation" / "GEOMETRY_PREPARATION_RESULT.json",
            "expected_pass_status": "GEOMETRY_PREPARATION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_09_VOLUME_MESH_GENERATION",
            "role": "STL to tetrahedral volume mesh",
            "run_script": "agent_system/run_agent09_volume_mesh_generation.py",
            "result_json": case_dir / "10_volume_mesh_generation" / "VOLUME_MESH_GENERATION_RESULT.json",
            "expected_pass_status": "VOLUME_MESH_GENERATION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_10_FEBIO_MODEL_GENERATION",
            "role": "Volume mesh and HU-density material law to FEBio base model",
            "run_script": "agent_system/run_agent10_febio_model_generation.py",
            "result_json": case_dir / "11_febio_model_generation" / "FEBIO_MODEL_GENERATION_RESULT.json",
            "expected_pass_status": "FEBIO_MODEL_GENERATION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_11_BOUNDARY_LOAD_CONFIGURATION",
            "role": "Boundary/load candidate creation",
            "run_script": "agent_system/run_agent11_boundary_load_configuration.py",
            "result_json": case_dir / "12_boundary_load_configuration" / "BOUNDARY_LOAD_CONFIGURATION_RESULT.json",
            "expected_pass_status": "BOUNDARY_LOAD_CONFIGURATION_REVIEW_REQUIRED",
            "langgraph_node_required": True,
            "human_review_gate": True,
        },
        {
            "agent_id": "AGENT_11_REVIEW_VALIDATION",
            "role": "Boundary/load human review validation",
            "run_script": "agent_system/validate_agent11_boundary_load_review.py",
            "result_json": case_dir / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json",
            "expected_pass_status": "BOUNDARY_LOAD_REVIEW_APPROVED",
            "langgraph_node_required": True,
            "human_review_gate": True,
        },
        {
            "agent_id": "AGENT_12_FEBIO_SOLVER_EXECUTION",
            "role": "FEBio solver execution",
            "run_script": "agent_system/run_agent12_febio_solver_execution.py",
            "result_json": case_dir / "13_solver_execution" / "FEBIO_SOLVER_EXECUTION_RESULT.json",
            "expected_pass_status": "SOLVER_EXECUTION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_13_SOLVER_RESULT_VALIDATION",
            "role": "Solver result validation",
            "run_script": "agent_system/run_agent13_solver_result_validation.py",
            "result_json": case_dir / "14_solver_result_validation" / "SOLVER_RESULT_VALIDATION_RESULT.json",
            "expected_pass_status": "SOLVER_RESULT_VALIDATION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_14_RESULT_EXTRACTION",
            "role": "Result extraction and solver-log metrics",
            "run_script": "agent_system/run_agent14_result_extraction.py",
            "result_json": case_dir / "15_result_extraction" / "RESULT_EXTRACTION_RESULT.json",
            "expected_pass_status": "RESULT_EXTRACTION_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_15_RESULT_INTERPRETATION_PRECHECK",
            "role": "Interpretation safety precheck",
            "run_script": "agent_system/run_agent15_result_interpretation_precheck.py",
            "result_json": case_dir / "16_result_interpretation_precheck" / "RESULT_INTERPRETATION_PRECHECK_RESULT.json",
            "expected_pass_status": "INTERPRETATION_PRECHECK_LIMITED_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_16_ACADEMIC_REPORT_DRAFT",
            "role": "Academic report draft",
            "run_script": "agent_system/run_agent16_academic_report_draft.py",
            "result_json": case_dir / "17_academic_report_draft" / "ACADEMIC_REPORT_DRAFT_RESULT.json",
            "expected_pass_status": "ACADEMIC_REPORT_DRAFT_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
        {
            "agent_id": "AGENT_17_FULL_PIPELINE_AUDIT",
            "role": "Full scientific and workflow audit",
            "run_script": "agent_system/run_agent17_full_pipeline_audit.py",
            "result_json": case_dir / "18_full_pipeline_audit" / "FULL_PIPELINE_AUDIT_RESULT.json",
            "expected_pass_status": "FULL_PIPELINE_AUDIT_LIMITED_PASS",
            "langgraph_node_required": True,
            "human_review_gate": False,
        },
    ]

    for agent in agents:
        if "run_script" in agent:
            agent["run_script_status"] = file_status(ROOT / agent["run_script"])

        if "result_json" in agent:
            agent["result_json_status"] = file_status(Path(agent["result_json"]))
            agent["result_json"] = str(agent["result_json"])

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "case_id": case_id,
        "integration_stage": "LANGCHAIN_LANGGRAPH_INTEGRATION_PREP",
        "current_pipeline_status": "FULL_PIPELINE_AUDIT_LIMITED_PASS",
        "next_stage": "LANGCHAIN_TOOL_WRAPPERS_AND_LANGGRAPH_NODES",
        "integration_principle": {
            "do_not_rewrite_working_tools": True,
            "wrap_existing_deterministic_tools": True,
            "preserve_human_review_gates": True,
            "preserve_scientific_safety_limits": True,
            "streamlit_should_call_langgraph_not_individual_scripts": True,
        },
        "agents": agents,
    }

    out_json = ROOT / "agent_system" / "integration" / "LANGGRAPH_INTEGRATION_MANIFEST.json"
    out_md = ROOT / "agent_system" / "integration" / "LANGGRAPH_INTEGRATION_PLAN.md"

    out_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    md = []
    md.append("# LangChain / LangGraph Integration Plan")
    md.append("")
    md.append(f"Created at: {manifest['created_at']}")
    md.append(f"Case ID: `{case_id}`")
    md.append("")
    md.append("## Current status")
    md.append("")
    md.append("The deterministic scientific pipeline has reached `FULL_PIPELINE_AUDIT_LIMITED_PASS`.")
    md.append("")
    md.append("## Integration rule")
    md.append("")
    md.append("Existing deterministic tools will not be rewritten. They will be wrapped as LangChain tools and connected as LangGraph nodes.")
    md.append("")
    md.append("## Agents")
    md.append("")
    md.append("| Agent | Role | LangGraph Node | Human Review |")
    md.append("|---|---|---:|---:|")

    for agent in agents:
        md.append(
            f"| `{agent['agent_id']}` | {agent['role']} | `{agent['langgraph_node_required']}` | `{agent['human_review_gate']}` |"
        )

    md.append("")
    md.append("## Next implementation step")
    md.append("")
    md.append("Create LangChain tool wrappers for deterministic agents, then build the first LangGraph supervisor workflow.")

    out_md.write_text("\n".join(md), encoding="utf-8")

    print("LANGGRAPH_INTEGRATION_MANIFEST_CREATED=True")
    print("MANIFEST_JSON_PATH=" + str(out_json))
    print("INTEGRATION_PLAN_MD_PATH=" + str(out_md))
    print("AGENT_COUNT=" + str(len(agents)))
    print("NEXT_STAGE=LANGCHAIN_TOOL_WRAPPERS_AND_LANGGRAPH_NODES")


if __name__ == "__main__":
    main()
