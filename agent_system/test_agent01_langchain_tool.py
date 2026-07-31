from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.data_intake_langchain_tool import data_intake_tool


result = data_intake_tool.invoke({
    "case_id": "test_agent01_langchain_tool",
    "input_path": str(PROJECT_ROOT / 'user_data' / 'test_agent01_dicom'),
    "anatomical_target": "L1 vertebra",
    "analysis_type": "aksiyel basma",
    "test_application_region": "L1 vertebra üst yüzeyi",
    "user_notes_optional": "LangChain tool testi"
})

print("AGENT_01_LANGCHAIN_TOOL_TEST=True")
print("DATA_STATUS=" + result["data_status"])
print("DETECTED_INPUT_TYPE=" + result["detected_input_type"])
print("NEXT_AGENT=" + result["next_agent"])
print("OUTPUT_JSON=" + result["output_json"])
