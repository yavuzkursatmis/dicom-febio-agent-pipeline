from pydantic import BaseModel, Field
from typing import List, Dict


class FullPipelineAuditInput(BaseModel):
    case_id: str


class FullPipelineAuditResult(BaseModel):
    case_id: str
    full_pipeline_audit_status: str
    next_agent: str

    required_files_checked: Dict = Field(default_factory=dict)
    required_status_checks: Dict = Field(default_factory=dict)
    human_review_checks: Dict = Field(default_factory=dict)
    scientific_safety_checks: Dict = Field(default_factory=dict)
    output_file_checks: Dict = Field(default_factory=dict)

    audit_summary_path: str = ""
    audit_json_path: str = ""

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
