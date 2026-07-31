from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent06 import agent06_graph


state = {
    "case_id": "real_dicom_check_001_anon_T1",
    "input_path": r"C:\dicom_test_data\case_real_001_anon",
    "anatomical_target": "T1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "T1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 to Agent-06 LangGraph T1 gerçek anonim DICOM testi"
}

result = agent06_graph.invoke(state)

print("AGENT_06_LANGGRAPH_NODE_TEST=True")

print("DATA_STATUS=" + result.get("data_status", ""))
print("DETECTED_INPUT_TYPE=" + result.get("detected_input_type", ""))
print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IMAGE_QUALITY_STATUS=" + result.get("image_quality_status", ""))
print("TARGET_UNDERSTANDING_STATUS=" + result.get("target_understanding_status", ""))
print("SEGMENTATION_STATUS=" + result.get("segmentation_status", ""))

print("SEGMENTATION_VALIDATION_STATUS=" + result.get("segmentation_validation_status", ""))
print("MASK_EXISTS=" + str(result.get("mask_exists", "")))
print("MASK_READ_SUCCESS=" + str(result.get("mask_read_success", "")))
print("MASK_IS_EMPTY=" + str(result.get("mask_is_empty", "")))
print("MASK_VOXEL_COUNT=" + str(result.get("mask_voxel_count", "")))
print("MASK_VOLUME_CM3=" + str(result.get("mask_volume_cm3", "")))
print("IMAGE_MASK_SIZE_MATCH=" + str(result.get("image_mask_size_match", "")))
print("IMAGE_MASK_SPACING_MATCH=" + str(result.get("image_mask_spacing_match", "")))

print("NEXT_AGENT=" + result.get("next_agent", ""))
print("WARNINGS=" + str(result.get("warnings", [])))
print("BLOCKERS=" + str(result.get("blockers", [])))
