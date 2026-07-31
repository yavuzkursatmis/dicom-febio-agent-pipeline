from pydantic import BaseModel, Field
from typing import List, Dict


class ResultExtractionInput(BaseModel):
    case_id: str
    solver_result_validation_path: str = ""


class ResultExtractionResult(BaseModel):
    case_id: str
    result_extraction_status: str
    next_agent: str

    solver_result_validation_path: str = ""
    solver_validation_passed: bool = False

    xplt_files_found: List[str] = Field(default_factory=list)
    xplt_files_nonempty: List[str] = Field(default_factory=list)
    xplt_file_info: List[Dict] = Field(default_factory=list)

    selected_solver_log_path: str = ""
    solver_log_exists: bool = False
    solver_log_line_count: int = 0

    normal_termination_detected: bool = False
    convergence_terms_detected: List[str] = Field(default_factory=list)

    parsed_solver_metrics: Dict = Field(default_factory=dict)
    extracted_csv_path: str = ""
    extraction_summary_path: str = ""

    xplt_binary_field_extraction_performed: bool = False
    result_summary_ready: bool = False
    human_review_required: bool = False

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
