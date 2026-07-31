from typing import List, Optional, Literal
from pydantic import BaseModel, Field


SegmentationValidationStatus = Literal[
    "SEGMENTATION_VALIDATION_PASS",
    "SEGMENTATION_VALIDATION_WARNING",
    "SEGMENTATION_VALIDATION_FAIL",
    "BLOCKED_BY_SEGMENTATION"
]


class SegmentationValidationInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    segmentation_json: Optional[str] = Field(
        default=None,
        description="Agent-05 SEGMENTATION_RESULT.json yolu"
    )


class SegmentationValidationResult(BaseModel):
    case_id: str
    segmentation_validation_status: SegmentationValidationStatus

    mask_exists: bool
    mask_read_success: bool
    mask_is_empty: bool

    mask_voxel_count: int
    mask_volume_mm3: float
    mask_volume_cm3: float

    reference_image_path: str
    mask_size: str
    reference_size: str
    mask_spacing: str
    reference_spacing: str

    image_mask_size_match: bool
    image_mask_spacing_match: bool

    resampling_applied: bool
    human_review_required: bool

    next_agent: str

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

    output_json: str
    output_csv: str
