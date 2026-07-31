from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent07 import agent07_graph


state = {
    "case_id": "real_dicom_check_001_anon_T1",
    "input_path": r"C:\dicom_test_data\case_real_001_anon",
    "anatomical_target": "T1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "T1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 to Agent-07 LangGraph T1 gerçek anonim DICOM testi"
}

result = agent07_graph.invoke(state)

print("AGENT_07_LANGGRAPH_NODE_TEST=True")

print("DATA_STATUS=" + result.get("data_status", ""))
print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IMAGE_QUALITY_STATUS=" + result.get("image_quality_status", ""))
print("TARGET_UNDERSTANDING_STATUS=" + result.get("target_understanding_status", ""))
print("SEGMENTATION_STATUS=" + result.get("segmentation_status", ""))
print("SEGMENTATION_VALIDATION_STATUS=" + result.get("segmentation_validation_status", ""))

print("HUMAN_REVIEW_STATUS=" + result.get("human_review_status", ""))

print("MATERIAL_SELECTION_STATUS=" + result.get("material_selection_status", ""))
print("ACTIVE_LITERATURE_SEARCH_REQUIRED=" + str(result.get("active_literature_search_required", "")))
print("LITERATURE_SEARCH_PERFORMED=" + str(result.get("literature_search_performed", "")))
print("LITERATURE_SEARCH_SUCCESS=" + str(result.get("literature_search_success", "")))
print("LITERATURE_RECORDS_COUNT=" + str(result.get("literature_records_count", "")))
print("MATERIAL_DOMAIN=" + result.get("material_domain", ""))
print("MATERIAL_MODEL=" + result.get("material_model", ""))
print("ELASTIC_MODULUS_MPA=" + str(result.get("elastic_modulus_MPa", "")))
print("POISSON_RATIO=" + str(result.get("poisson_ratio", "")))
print("UNCERTAINTY_LEVEL=" + result.get("uncertainty_level", ""))

print("MATERIAL_REVIEW_STATUS=" + result.get("material_review_status", ""))
print("MATERIAL_REVIEW_APPROVAL_STATUS=" + result.get("material_review_approval_status", ""))

print("NEXT_AGENT=" + result.get("next_agent", ""))
print("WARNINGS=" + str(result.get("warnings", [])))
print("BLOCKERS=" + str(result.get("blockers", [])))

