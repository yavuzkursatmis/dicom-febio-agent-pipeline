from pydantic import BaseModel, Field
from typing import List, Dict


class ResultInterpretationPrecheckInput(BaseModel):
    case_id: str
    result_extraction_path: str = ""


class ResultInterpretationPrecheckResult(BaseModel):
    case_id: str
    interpretation_precheck_status: str
    next_agent: str

    result_extraction_path: str = ""
    result_extraction_passed: bool = False

    solver_completed: bool = False
    xplt_present: bool = False
    xplt_binary_field_extraction_performed: bool = False

    quantitative_field_interpretation_allowed: bool = False
    solver_log_interpretation_allowed: bool = False
    clinical_interpretation_allowed: bool = False
    academic_pipeline_reporting_allowed: bool = False

    allowed_interpretation_scope: List[str] = Field(default_factory=list)
    prohibited_interpretation_scope: List[str] = Field(default_factory=list)

    required_next_actions: List[str] = Field(default_factory=list)
    precheck_summary: Dict = Field(default_factory=dict)

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
