from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent04 import agent04_graph


state = {
    "case_id": "test_agent04_langgraph",
    "input_path": str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom'),
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 + Agent-02 + Agent-03 + Agent-04 LangGraph testi"
}

result = agent04_graph.invoke(state)

print("AGENT_04_LANGGRAPH_NODE_TEST=True")

print("DATA_STATUS=" + result.get("data_status", ""))
print("DETECTED_INPUT_TYPE=" + result.get("detected_input_type", ""))

print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IS_CT=" + str(result.get("is_ct", "")))

print("IMAGE_QUALITY_STATUS=" + result.get("image_quality_status", ""))
print("SLICE_COUNT=" + str(result.get("slice_count", "")))

print("TARGET_UNDERSTANDING_STATUS=" + result.get("target_understanding_status", ""))
print("SEGMENTATION_TARGET=" + result.get("segmentation_target", ""))
print("STANDARDIZED_ANALYSIS_TYPE=" + result.get("standardized_analysis_type", ""))
print("LOAD_REGION=" + result.get("load_region", ""))
print("CONFIDENCE_LEVEL=" + result.get("confidence_level", ""))
print("LLM_CONFIDENCE_LEVEL=" + result.get("llm_confidence_level", ""))
print("HUMAN_REVIEW_REQUIRED=" + str(result.get("human_review_required", "")))
print("LLM_USED=" + str(result.get("llm_used", "")))
print("CANONICALIZATION_APPLIED=" + str(result.get("canonicalization_applied", "")))

print("NEXT_AGENT=" + result.get("next_agent", ""))
print("WARNINGS=" + str(result.get("warnings", [])))
print("BLOCKERS=" + str(result.get("blockers", [])))
