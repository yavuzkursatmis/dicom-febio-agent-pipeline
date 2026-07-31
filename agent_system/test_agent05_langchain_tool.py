from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.segmentation_langchain_tool import segmentation_tool


result = segmentation_tool.invoke({
    "case_id": "real_dicom_check_001_anon",
    "reuse_existing": True
})

print("AGENT_05_LANGCHAIN_TOOL_TEST=True")
print("SEGMENTATION_STATUS=" + result["segmentation_status"])
print("PREPROCESSING_REQUIRED=" + str(result["preprocessing_required"]))
print("RESAMPLING_APPLIED=" + str(result["resampling_applied"]))
print("ORIGINAL_SPACING=" + result["original_spacing"])
print("TARGET_SPACING=" + result["target_spacing"])
print("RESAMPLED_SPACING=" + result["resampled_spacing"])
print("SEGMENTATION_TARGET=" + result["segmentation_target"])
print("SEGMENTATION_TOOL=" + result["segmentation_tool"])
print("SEGMENTATION_MASK_PATH=" + result["segmentation_mask_path"])
print("NEXT_AGENT=" + result["next_agent"])
print("WARNINGS=" + str(result["warnings"]))
print("BLOCKERS=" + str(result["blockers"]))
print("OUTPUT_JSON=" + result["output_json"])
