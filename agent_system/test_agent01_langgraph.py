from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent01 import agent01_graph


state = {
    "case_id": "test_agent01_langgraph",
    "input_path": str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom'),
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "LangGraph node testi"
}

result = agent01_graph.invoke(state)

print("AGENT_01_LANGGRAPH_NODE_TEST=True")
print("CURRENT_AGENT=" + result["current_agent"])
print("DATA_STATUS=" + result["data_status"])
print("DETECTED_INPUT_TYPE=" + result["detected_input_type"])
print("NEXT_AGENT=" + result["next_agent"])
print("FILE_COUNT=" + str(result["file_count"]))
