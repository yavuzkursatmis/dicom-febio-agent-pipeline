from typing import List, Optional, Literal
from pydantic import BaseModel, Field


InputType = Literal[
    "DICOM",
    "NIFTI",
    "MANUAL_MASK",
    "MULTIPLE_INPUT_TYPES",
    "UNSUPPORTED",
    "MISSING"
]


DataStatus = Literal[
    "DATA_READY",
    "DATA_MISSING",
    "EMPTY_FOLDER",
    "UNSUPPORTED_FORMAT",
    "MULTIPLE_INPUT_TYPES_FOUND"
]


class DataIntakeInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    input_path: str = Field(..., description="Kullanıcının yüklediği dosya veya klasör yolu")
    anatomical_target: str = Field(..., description="Analiz edilecek anatomik bölge")
    analysis_type: str = Field(..., description="Uygulanacak test türü")
    test_application_region: str = Field(..., description="Testin uygulanacağı yer")
    user_notes_optional: Optional[str] = ""


class DataIntakeResult(BaseModel):
    case_id: str
    input_path: str
    data_status: DataStatus
    detected_input_type: InputType
    file_count: int
    supported_format: bool
    case_folder: str
    anatomical_target: str
    analysis_type: str
    test_application_region: str
    user_notes_optional: str = ""
    next_agent: str
    warnings: List[str] = []
    blockers: List[str] = []
    output_json: str
