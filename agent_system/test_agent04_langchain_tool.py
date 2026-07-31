from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.target_understanding_langchain_tool import target_understanding_tool


result = target_understanding_tool.invoke({
    "case_id": "test_agent03_langgraph"
})

print("AGENT_04_LANGCHAIN_TOOL_TEST=True")
print("TARGET_UNDERSTANDING_STATUS=" + result["target_understanding_status"])
print("SEGMENTATION_TARGET=" + result["segmentation_target"])
print("STANDARDIZED_ANALYSIS_TYPE=" + result["standardized_analysis_type"])
print("LOAD_REGION=" + result["load_region"])
print("CONFIDENCE_LEVEL=" + result["confidence_level"])
print("LLM_CONFIDENCE_LEVEL=" + result["llm_confidence_level"])
print("HUMAN_REVIEW_REQUIRED=" + str(result["human_review_required"]))
print("LLM_USED=" + str(result["llm_used"]))
print("CANONICALIZATION_APPLIED=" + str(result["canonicalization_applied"]))
print("NEXT_AGENT=" + result["next_agent"])
print("WARNINGS=" + str(result["warnings"]))
print("BLOCKERS=" + str(result["blockers"]))
print("OUTPUT_JSON=" + result["output_json"])
