from typing import List, Optional, Literal
from pydantic import BaseModel, Field


SegmentationStatus = Literal[
    "SEGMENTATION_PASS",
    "SEGMENTATION_WARNING",
    "SEGMENTATION_FAIL",
    "BLOCKED_BY_TARGET_UNDERSTANDING",
    "PREPROCESSING_REQUIRED",
    "SEGMENTATION_TOOL_NOT_AVAILABLE"
]


class SegmentationInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    data_intake_json: Optional[str] = Field(default=None)
    image_quality_json: Optional[str] = Field(default=None)
    target_understanding_json: Optional[str] = Field(default=None)
    reuse_existing: bool = Field(default=True)


class SegmentationResult(BaseModel):
    case_id: str
    segmentation_status: SegmentationStatus

    preprocessing_required: bool
    resampling_applied: bool

    original_spacing: str
    target_spacing: str
    resampled_spacing: str

    segmentation_mode: str
    segmentation_tool: str
    segmentation_target: str

    original_volume_path: str
    resampled_volume_path: str
    segmentation_mask_path: str
    raw_segmentation_output_dir: str

    next_agent: str
    human_review_required: bool

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

    preprocessing_json: str
    output_json: str
