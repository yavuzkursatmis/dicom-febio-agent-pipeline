from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent03 import agent03_graph


state = {
    "case_id": "test_agent03_langgraph",
    "input_path": str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom'),
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 + Agent-02 + Agent-03 LangGraph testi"
}

result = agent03_graph.invoke(state)

print("AGENT_03_LANGGRAPH_NODE_TEST=True")

print("DATA_STATUS=" + result.get("data_status", ""))
print("DETECTED_INPUT_TYPE=" + result.get("detected_input_type", ""))

print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IS_CT=" + str(result.get("is_ct", "")))

print("IMAGE_QUALITY_STATUS=" + result.get("image_quality_status", ""))
print("SERIES_READ_SUCCESS=" + str(result.get("series_read_success", "")))
print("SLICE_COUNT=" + str(result.get("slice_count", "")))
print("IMAGE_SIZE=" + result.get("image_size", ""))
print("SPACING=" + result.get("spacing", ""))

print("NEXT_AGENT=" + result.get("next_agent", ""))
print("WARNINGS=" + str(result.get("warnings", [])))
print("BLOCKERS=" + str(result.get("blockers", [])))
