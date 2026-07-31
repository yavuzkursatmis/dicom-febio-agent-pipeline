from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.segmentation_validation_schema import SegmentationValidationInput
from agent_system.agents.segmentation_validation_agent import run_segmentation_validation


def segmentation_validation_tool_func(
    case_id: str,
    segmentation_json: str = None,
):
    user_input = SegmentationValidationInput(
        case_id=case_id,
        segmentation_json=segmentation_json,
    )

    result = run_segmentation_validation(user_input)
    return result.model_dump()


segmentation_validation_tool = StructuredTool.from_function(
    name="segmentation_validation_tool",
    description=(
        "Agent-05 tarafından üretilen segmentasyon maskesini doğrular. "
        "Maskenin varlığını, okunabilirliğini, boş olup olmadığını, voxel sayısını, "
        "hacmini, görüntü ile boyut/spacing uyumunu kontrol eder."
    ),
    func=segmentation_validation_tool_func,
    args_schema=SegmentationValidationInput,
)
