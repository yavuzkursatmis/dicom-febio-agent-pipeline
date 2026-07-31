from typing import List, Optional, Literal
from pydantic import BaseModel, Field


SafetyStatus = Literal[
    "DICOM_SAFETY_PASS",
    "BLOCKED_NOT_DICOM",
    "DICOM_READ_FAIL",
    "BLOCKED_NOT_CT",
    "HUMAN_REVIEW_REQUIRED"
]


class DicomSafetyInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    data_intake_json: Optional[str] = Field(
        default=None,
        description="Agent-01 DATA_INTAKE_RESULT.json yolu"
    )


class DicomSafetyResult(BaseModel):
    case_id: str
    safety_status: SafetyStatus
    dicom_file_count: int
    readable_dicom_count: int
    modality_detected: str
    is_ct: bool
    phi_risk_detected: bool
    burned_in_annotation_risk: bool
    human_review_required: bool
    next_agent: str
    warnings: List[str] = []
    blockers: List[str] = []
    output_json: str
    output_csv: str
