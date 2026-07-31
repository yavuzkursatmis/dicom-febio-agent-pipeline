from typing import List, Optional, Literal
from pydantic import BaseModel, Field


ImageQualityStatus = Literal[
    "IMAGE_QUALITY_PASS",
    "IMAGE_QUALITY_WARNING",
    "IMAGE_QUALITY_FAIL",
    "BLOCKED_BY_DICOM_SAFETY",
    "DICOM_SERIES_READ_FAIL"
]


class ImageQualityInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    dicom_safety_json: Optional[str] = Field(
        default=None,
        description="Agent-02 DICOM_SAFETY_RESULT.json yolu"
    )


class ImageQualityResult(BaseModel):
    case_id: str
    image_quality_status: ImageQualityStatus
    series_read_success: bool
    slice_count: int
    image_size: str
    spacing: str
    slice_thickness: float
    voxel_anisotropy: float
    intensity_min: float
    intensity_max: float
    intensity_mean: float
    next_agent: str
    warnings: List[str] = []
    blockers: List[str] = []
    output_json: str
    output_csv: str
