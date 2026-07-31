from typing import List, Optional, Literal
from pydantic import BaseModel, Field


TargetUnderstandingStatus = Literal[
    "TARGET_UNDERSTANDING_PASS",
    "TARGET_UNDERSTANDING_NEEDS_REVIEW",
    "TARGET_UNDERSTANDING_FAIL",
    "BLOCKED_BY_IMAGE_QUALITY"
]


class TargetUnderstandingInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    data_intake_json: Optional[str] = Field(
        default=None,
        description="Agent-01 DATA_INTAKE_RESULT.json yolu"
    )
    image_quality_json: Optional[str] = Field(
        default=None,
        description="Agent-03 IMAGE_QUALITY_RESULT.json yolu"
    )


class TargetUnderstandingResult(BaseModel):
    case_id: str
    target_understanding_status: TargetUnderstandingStatus

    standardized_anatomical_target: str
    segmentation_target: str

    standardized_analysis_type: str
    standardized_test_application_region: str

    load_region: str
    boundary_condition_hint: str

    confidence_level: str
    llm_confidence_level: str = ""
    llm_human_review_required: bool = False
    human_review_required: bool

    llm_used: bool
    canonicalization_applied: bool = False
    reasoning_summary: str
    validation_notes: List[str] = Field(default_factory=list)

    next_agent: str
    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

    output_json: str
