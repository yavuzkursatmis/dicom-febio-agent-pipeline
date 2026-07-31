from pydantic import BaseModel, Field
from typing import List, Dict


class AcademicReportDraftInput(BaseModel):
    case_id: str
    interpretation_precheck_path: str = ""
    language: str = "tr"


class AcademicReportDraftResult(BaseModel):
    case_id: str
    academic_report_status: str
    next_agent: str

    interpretation_precheck_path: str = ""
    interpretation_precheck_passed: bool = False
    academic_pipeline_reporting_allowed: bool = False
    quantitative_field_interpretation_allowed: bool = False
    clinical_interpretation_allowed: bool = False

    included_source_files: List[str] = Field(default_factory=list)
    missing_optional_source_files: List[str] = Field(default_factory=list)

    report_markdown_path: str = ""
    report_text_path: str = ""
    report_metadata_json_path: str = ""

    report_sections_created: List[str] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
