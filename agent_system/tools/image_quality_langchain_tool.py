from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.image_quality_schema import ImageQualityInput
from agent_system.agents.image_quality_agent import run_image_quality


def image_quality_tool_func(
    case_id: str,
    dicom_safety_json: str = None,
):
    user_input = ImageQualityInput(
        case_id=case_id,
        dicom_safety_json=dicom_safety_json,
    )

    result = run_image_quality(user_input)
    return result.model_dump()


image_quality_tool = StructuredTool.from_function(
    name="image_quality_tool",
    description=(
        "DICOM güvenlik kontrolünden geçen görüntünün teknik kalite profilini çıkarır. "
        "Slice count, spacing, slice thickness, voxel anisotropy ve intensity/HU aralığını kontrol eder."
    ),
    func=image_quality_tool_func,
    args_schema=ImageQualityInput,
)
