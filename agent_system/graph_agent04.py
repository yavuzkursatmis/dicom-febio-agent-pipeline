from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langgraph.graph import StateGraph, START, END

from agent_system.state import CaseState
from agent_system.tools.data_intake_langchain_tool import data_intake_tool
from agent_system.tools.dicom_safety_langchain_tool import dicom_safety_tool
from agent_system.tools.image_quality_langchain_tool import image_quality_tool
from agent_system.tools.target_understanding_langchain_tool import target_understanding_tool


def data_intake_node(state: CaseState) -> CaseState:
    result = data_intake_tool.invoke({
        "case_id": state["case_id"],
        "input_path": state["input_path"],
        "anatomical_target": state["anatomical_target"],
        "analysis_type": state["analysis_type"],
        "test_application_region": state["test_application_region"],
        "user_notes_optional": state.get("user_notes_optional", ""),
    })

    state["current_agent"] = "DATA_INTAKE_AGENT"
    state["next_agent"] = result["next_agent"]

    state["data_status"] = result["data_status"]
    state["detected_input_type"] = result["detected_input_type"]
    state["file_count"] = result["file_count"]
    state["supported_format"] = result["supported_format"]
    state["data_intake_result"] = result

    state["warnings"] = result.get("warnings", [])
    state["blockers"] = result.get("blockers", [])

    return state


def dicom_safety_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "DICOM_SAFETY_AGENT":
        state["current_agent"] = "DICOM_SAFETY_AGENT_SKIPPED"
        return state

    result = dicom_safety_tool.invoke({
        "case_id": state["case_id"]
    })

    state["current_agent"] = "DICOM_SAFETY_AGENT"
    state["next_agent"] = result["next_agent"]

    state["safety_status"] = result["safety_status"]
    state["dicom_file_count"] = result["dicom_file_count"]
    state["readable_dicom_count"] = result["readable_dicom_count"]
    state["modality_detected"] = result["modality_detected"]
    state["is_ct"] = result["is_ct"]
    state["phi_risk_detected"] = result["phi_risk_detected"]
    state["burned_in_annotation_risk"] = result["burned_in_annotation_risk"]
    state["dicom_safety_result"] = result

    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])

    return state


def image_quality_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "IMAGE_QUALITY_AGENT":
        state["current_agent"] = "IMAGE_QUALITY_AGENT_SKIPPED"
        return state

    result = image_quality_tool.invoke({
        "case_id": state["case_id"]
    })

    state["current_agent"] = "IMAGE_QUALITY_AGENT"
    state["next_agent"] = result["next_agent"]

    state["image_quality_status"] = result["image_quality_status"]
    state["series_read_success"] = result["series_read_success"]
    state["slice_count"] = result["slice_count"]
    state["image_size"] = result["image_size"]
    state["spacing"] = result["spacing"]
    state["slice_thickness"] = result["slice_thickness"]
    state["voxel_anisotropy"] = result["voxel_anisotropy"]
    state["intensity_min"] = result["intensity_min"]
    state["intensity_max"] = result["intensity_max"]
    state["intensity_mean"] = result["intensity_mean"]
    state["image_quality_result"] = result

    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])

    return state


def target_understanding_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "TARGET_UNDERSTANDING_AGENT":
        state["current_agent"] = "TARGET_UNDERSTANDING_AGENT_SKIPPED"
        return state

    result = target_understanding_tool.invoke({
        "case_id": state["case_id"]
    })

    state["current_agent"] = "TARGET_UNDERSTANDING_AGENT"
    state["next_agent"] = result["next_agent"]

    state["target_understanding_status"] = result["target_understanding_status"]
    state["standardized_anatomical_target"] = result["standardized_anatomical_target"]
    state["segmentation_target"] = result["segmentation_target"]
    state["standardized_analysis_type"] = result["standardized_analysis_type"]
    state["standardized_test_application_region"] = result["standardized_test_application_region"]
    state["load_region"] = result["load_region"]
    state["boundary_condition_hint"] = result["boundary_condition_hint"]
    state["confidence_level"] = result["confidence_level"]
    state["llm_confidence_level"] = result["llm_confidence_level"]
    state["llm_human_review_required"] = result["llm_human_review_required"]
    state["human_review_required"] = result["human_review_required"]
    state["llm_used"] = result["llm_used"]
    state["canonicalization_applied"] = result["canonicalization_applied"]
    state["validation_notes"] = result["validation_notes"]
    state["target_understanding_result"] = result

    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])

    return state


def build_agent04_graph():
    graph = StateGraph(CaseState)

    graph.add_node("data_intake_agent", data_intake_node)
    graph.add_node("dicom_safety_agent", dicom_safety_node)
    graph.add_node("image_quality_agent", image_quality_node)
    graph.add_node("target_understanding_agent", target_understanding_node)

    graph.add_edge(START, "data_intake_agent")
    graph.add_edge("data_intake_agent", "dicom_safety_agent")
    graph.add_edge("dicom_safety_agent", "image_quality_agent")
    graph.add_edge("image_quality_agent", "target_understanding_agent")
    graph.add_edge("target_understanding_agent", END)

    return graph.compile()


agent04_graph = build_agent04_graph()
