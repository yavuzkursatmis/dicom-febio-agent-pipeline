from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.segmentation_schema import SegmentationInput
from agent_system.agents.segmentation_agent import run_segmentation


def segmentation_tool_func(
    case_id: str,
    data_intake_json: str = None,
    image_quality_json: str = None,
    target_understanding_json: str = None,
    reuse_existing: bool = True,
):
    user_input = SegmentationInput(
        case_id=case_id,
        data_intake_json=data_intake_json,
        image_quality_json=image_quality_json,
        target_understanding_json=target_understanding_json,
        reuse_existing=reuse_existing,
    )

    result = run_segmentation(user_input)
    return result.model_dump()


segmentation_tool = StructuredTool.from_function(
    name="segmentation_tool",
    description=(
        "DICOM/CT hacmini segmentasyona hazırlar, gerekirse resampling uygular "
        "ve hedef anatomik yapı için segmentasyon maskesi üretir. "
        "HIGH_VOXEL_ANISOTROPY durumunda preprocessing/resampling kararını uygular."
    ),
    func=segmentation_tool_func,
    args_schema=SegmentationInput,
)
