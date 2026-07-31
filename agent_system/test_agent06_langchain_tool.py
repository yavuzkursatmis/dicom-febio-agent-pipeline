from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.segmentation_validation_langchain_tool import segmentation_validation_tool


result = segmentation_validation_tool.invoke({
    "case_id": "real_dicom_check_001_anon_T1"
})

print("AGENT_06_LANGCHAIN_TOOL_TEST=True")
print("SEGMENTATION_VALIDATION_STATUS=" + result["segmentation_validation_status"])
print("MASK_EXISTS=" + str(result["mask_exists"]))
print("MASK_READ_SUCCESS=" + str(result["mask_read_success"]))
print("MASK_IS_EMPTY=" + str(result["mask_is_empty"]))
print("MASK_VOXEL_COUNT=" + str(result["mask_voxel_count"]))
print("MASK_VOLUME_CM3=" + str(result["mask_volume_cm3"]))
print("IMAGE_MASK_SIZE_MATCH=" + str(result["image_mask_size_match"]))
print("IMAGE_MASK_SPACING_MATCH=" + str(result["image_mask_spacing_match"]))
print("RESAMPLING_APPLIED=" + str(result["resampling_applied"]))
print("HUMAN_REVIEW_REQUIRED=" + str(result["human_review_required"]))
print("NEXT_AGENT=" + result["next_agent"])
print("WARNINGS=" + str(result["warnings"]))
print("BLOCKERS=" + str(result["blockers"]))
print("OUTPUT_JSON=" + result["output_json"])
