from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.graph_agent02 import agent02_graph


state = {
    "case_id": "test_agent02_langgraph",
    "input_path": str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom'),
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "Agent-01 + Agent-02 LangGraph testi"
}

result = agent02_graph.invoke(state)

print("AGENT_02_LANGGRAPH_NODE_TEST=True")
print("DATA_STATUS=" + result["data_status"])
print("DETECTED_INPUT_TYPE=" + result["detected_input_type"])
print("SAFETY_STATUS=" + result.get("safety_status", ""))
print("IS_CT=" + str(result.get("is_ct", "")))
print("PHI_RISK_DETECTED=" + str(result.get("phi_risk_detected", "")))
print("NEXT_AGENT=" + result["next_agent"])
