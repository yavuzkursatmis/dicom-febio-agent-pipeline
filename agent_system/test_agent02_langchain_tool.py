from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.dicom_safety_langchain_tool import dicom_safety_tool


result = dicom_safety_tool.invoke({
    "case_id": "test_agent01_dicom"
})

print("AGENT_02_LANGCHAIN_TOOL_TEST=True")
print("SAFETY_STATUS=" + result["safety_status"])
print("IS_CT=" + str(result["is_ct"]))
print("PHI_RISK_DETECTED=" + str(result["phi_risk_detected"]))
print("NEXT_AGENT=" + result["next_agent"])
print("OUTPUT_JSON=" + result["output_json"])
