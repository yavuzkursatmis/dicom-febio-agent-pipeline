from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent05 import agent05_graph


state = {
    "case_id": "real_dicom_check_001_anon",
    "input_path": r"C:\dicom_test_data\case_real_001_anon",
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 to Agent-05 LangGraph gerçek anonim DICOM testi"
}

result = agent05_graph.invoke(state)

print("AGENT_05_LANGGRAPH_NODE_TEST=True")

print("DATA_STATUS=" + result.get("data_status", ""))
print("DETECTED_INPUT_TYPE=" + result.get("detected_input_type", ""))
print("FILE_COUNT=" + str(result.get("file_count", "")))

print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IS_CT=" + str(result.get("is_ct", "")))
print("PHI_RISK_DETECTED=" + str(result.get("phi_risk_detected", "")))

print("IMAGE_QUALITY_STATUS=" + result.get("image_quality_status", ""))
print("SLICE_COUNT=" + str(result.get("slice_count", "")))
print("VOXEL_ANISOTROPY=" + str(result.get("voxel_anisotropy", "")))

print("TARGET_UNDERSTANDING_STATUS=" + result.get("target_understanding_status", ""))
print("SEGMENTATION_TARGET=" + result.get("segmentation_target", ""))
print("STANDARDIZED_ANALYSIS_TYPE=" + result.get("standardized_analysis_type", ""))
print("LOAD_REGION=" + result.get("load_region", ""))

print("SEGMENTATION_STATUS=" + result.get("segmentation_status", ""))
print("PREPROCESSING_REQUIRED=" + str(result.get("preprocessing_required", "")))
print("RESAMPLING_APPLIED=" + str(result.get("resampling_applied", "")))
print("ORIGINAL_SPACING=" + result.get("original_spacing", ""))
print("TARGET_SPACING=" + result.get("target_spacing", ""))
print("RESAMPLED_SPACING=" + result.get("resampled_spacing", ""))
print("SEGMENTATION_MASK_PATH=" + result.get("segmentation_mask_path", ""))

print("NEXT_AGENT=" + result.get("next_agent", ""))
print("WARNINGS=" + str(result.get("warnings", [])))
print("BLOCKERS=" + str(result.get("blockers", [])))
