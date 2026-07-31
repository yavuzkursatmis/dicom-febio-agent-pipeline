from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.image_quality_langchain_tool import image_quality_tool


result = image_quality_tool.invoke({
    "case_id": "test_agent01_dicom"
})

print("AGENT_03_LANGCHAIN_TOOL_TEST=True")
print("IMAGE_QUALITY_STATUS=" + result["image_quality_status"])
print("SERIES_READ_SUCCESS=" + str(result["series_read_success"]))
print("SLICE_COUNT=" + str(result["slice_count"]))
print("IMAGE_SIZE=" + result["image_size"])
print("SPACING=" + result["spacing"])
print("NEXT_AGENT=" + result["next_agent"])
print("OUTPUT_JSON=" + result["output_json"])
