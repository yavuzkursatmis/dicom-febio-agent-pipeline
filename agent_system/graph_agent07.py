from pathlib import Path
import json
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
from agent_system.tools.segmentation_langchain_tool import segmentation_tool
from agent_system.tools.segmentation_validation_langchain_tool import segmentation_validation_tool
from agent_system.tools.material_selection_langchain_tool import material_selection_tool
from agent_system.tools.material_review_gate_tools import build_material_review_gate
from agent_system.tools.material_review_approval_tools import validate_material_review_input


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


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

    result = dicom_safety_tool.invoke({"case_id": state["case_id"]})

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

    result = image_quality_tool.invoke({"case_id": state["case_id"]})

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

    result = target_understanding_tool.invoke({"case_id": state["case_id"]})

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


def segmentation_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "SEGMENTATION_AGENT":
        state["current_agent"] = "SEGMENTATION_AGENT_SKIPPED"
        return state

    result = segmentation_tool.invoke({
        "case_id": state["case_id"],
        "reuse_existing": True
    })

    state["current_agent"] = "SEGMENTATION_AGENT"
    state["next_agent"] = result["next_agent"]
    state["segmentation_status"] = result["segmentation_status"]
    state["preprocessing_required"] = result["preprocessing_required"]
    state["resampling_applied"] = result["resampling_applied"]
    state["original_spacing"] = result["original_spacing"]
    state["target_spacing"] = result["target_spacing"]
    state["resampled_spacing"] = result["resampled_spacing"]
    state["segmentation_mode"] = result["segmentation_mode"]
    state["segmentation_tool"] = result["segmentation_tool"]
    state["segmentation_mask_path"] = result["segmentation_mask_path"]
    state["raw_segmentation_output_dir"] = result["raw_segmentation_output_dir"]
    state["segmentation_result"] = result
    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])
    return state


def segmentation_validation_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "SEGMENTATION_VALIDATION_AGENT":
        state["current_agent"] = "SEGMENTATION_VALIDATION_AGENT_SKIPPED"
        return state

    result = segmentation_validation_tool.invoke({"case_id": state["case_id"]})

    state["current_agent"] = "SEGMENTATION_VALIDATION_AGENT"
    state["next_agent"] = result["next_agent"]
    state["segmentation_validation_status"] = result["segmentation_validation_status"]
    state["mask_exists"] = result["mask_exists"]
    state["mask_read_success"] = result["mask_read_success"]
    state["mask_is_empty"] = result["mask_is_empty"]
    state["mask_voxel_count"] = result["mask_voxel_count"]
    state["mask_volume_cm3"] = result["mask_volume_cm3"]
    state["image_mask_size_match"] = result["image_mask_size_match"]
    state["image_mask_spacing_match"] = result["image_mask_spacing_match"]
    state["segmentation_validation_result"] = result
    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])
    return state


def human_review_gate_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "HUMAN_REVIEW_GATE":
        state["current_agent"] = "HUMAN_REVIEW_GATE_SKIPPED"
        return state

    review_path = ROOT / "cases" / state["case_id"] / "06_human_review" / "HUMAN_REVIEW_RESULT.json"

    if not review_path.exists():
        state["current_agent"] = "HUMAN_REVIEW_GATE"
        state["human_review_status"] = "HUMAN_REVIEW_RESULT_NOT_FOUND"
        state["next_agent"] = "USER_ACTION_REQUIRED"
        state["blockers"] = state.get("blockers", []) + ["HUMAN_REVIEW_RESULT_NOT_FOUND"]
        return state

    review = load_json(review_path)
    state["current_agent"] = "HUMAN_REVIEW_GATE"
    state["human_review_result"] = review
    state["human_review_status"] = review.get("human_review_status", "")

    if bool(review.get("approved", False)) and review.get("approved_next_agent") == "MATERIAL_SELECTION_AGENT":
        state["next_agent"] = "MATERIAL_SELECTION_AGENT"
    else:
        state["next_agent"] = "USER_ACTION_REQUIRED"
        state["blockers"] = state.get("blockers", []) + ["HUMAN_REVIEW_NOT_APPROVED_FOR_MATERIAL_SELECTION"]

    return state


def material_selection_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "MATERIAL_SELECTION_AGENT":
        state["current_agent"] = "MATERIAL_SELECTION_AGENT_SKIPPED"
        return state

    result = material_selection_tool.invoke({
        "case_id": state["case_id"],
        "max_records_per_source": 3
    })

    state["current_agent"] = "MATERIAL_SELECTION_AGENT"
    state["next_agent"] = result["next_agent"]
    state["material_selection_status"] = result["material_selection_status"]
    state["active_literature_search_required"] = result["active_literature_search_required"]
    state["literature_search_performed"] = result["literature_search_performed"]
    state["literature_search_success"] = result["literature_search_success"]
    state["literature_records_count"] = result["literature_records_count"]
    state["material_domain"] = result["material_domain"]
    state["material_model"] = result["material_model"]
    state["elastic_modulus_MPa"] = result["elastic_modulus_MPa"]
    state["poisson_ratio"] = result["poisson_ratio"]
    state["uncertainty_level"] = result["uncertainty_level"]
    state["material_selection_result"] = result
    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])
    return state


def material_review_gate_node(state: CaseState) -> CaseState:
    if state.get("next_agent") != "HUMAN_REVIEW_GATE":
        state["current_agent"] = "MATERIAL_REVIEW_GATE_SKIPPED"
        return state

    if state.get("material_selection_status", "") == "":
        state["current_agent"] = "MATERIAL_REVIEW_GATE_SKIPPED"
        return state

    result = build_material_review_gate(case_id=state["case_id"])

    state["current_agent"] = "MATERIAL_REVIEW_GATE"
    state["material_review_status"] = result.get("material_review_status", "")
    state["material_review_result"] = result
    state["next_agent"] = result.get("approved_next_agent", "USER_ACTION_REQUIRED")

    return state



def material_review_approval_node(state: CaseState) -> CaseState:
    if state.get("material_review_status", "") == "":
        state["current_agent"] = "MATERIAL_REVIEW_APPROVAL_SKIPPED"
        return state

    result = validate_material_review_input(case_id=state["case_id"])

    state["current_agent"] = "MATERIAL_REVIEW_APPROVAL_VALIDATOR"
    state["material_review_approval_status"] = result.get("material_review_approval_status", "")
    state["material_review_approval_result"] = result
    state["next_agent"] = result.get("approved_next_agent", "USER_ACTION_REQUIRED")
    state["warnings"] = state.get("warnings", []) + result.get("warnings", [])
    state["blockers"] = state.get("blockers", []) + result.get("blockers", [])

    return state

def build_agent07_graph():
    graph = StateGraph(CaseState)

    graph.add_node("data_intake_agent", data_intake_node)
    graph.add_node("dicom_safety_agent", dicom_safety_node)
    graph.add_node("image_quality_agent", image_quality_node)
    graph.add_node("target_understanding_agent", target_understanding_node)
    graph.add_node("segmentation_agent", segmentation_node)
    graph.add_node("segmentation_validation_agent", segmentation_validation_node)
    graph.add_node("human_review_gate", human_review_gate_node)
    graph.add_node("material_selection_agent", material_selection_node)
    graph.add_node("material_review_gate", material_review_gate_node)
    graph.add_node("material_review_approval", material_review_approval_node)

    graph.add_edge(START, "data_intake_agent")
    graph.add_edge("data_intake_agent", "dicom_safety_agent")
    graph.add_edge("dicom_safety_agent", "image_quality_agent")
    graph.add_edge("image_quality_agent", "target_understanding_agent")
    graph.add_edge("target_understanding_agent", "segmentation_agent")
    graph.add_edge("segmentation_agent", "segmentation_validation_agent")
    graph.add_edge("segmentation_validation_agent", "human_review_gate")
    graph.add_edge("human_review_gate", "material_selection_agent")
    graph.add_edge("material_selection_agent", "material_review_gate")
    graph.add_edge("material_review_gate", "material_review_approval")
    graph.add_edge("material_review_approval", END)

    return graph.compile()


agent07_graph = build_agent07_graph()



