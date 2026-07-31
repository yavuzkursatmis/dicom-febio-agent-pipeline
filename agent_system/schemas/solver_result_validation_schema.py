from pydantic import BaseModel, Field
from typing import List


class SolverResultValidationInput(BaseModel):
    case_id: str
    solver_execution_result_path: str = ""


class SolverResultValidationResult(BaseModel):
    case_id: str
    solver_result_validation_status: str
    next_agent: str

    solver_execution_result_path: str = ""
    solver_status_passed: bool = False

    solver_return_code: int = -1
    normal_termination_detected: bool = False
    nonzero_return_code_with_normal_termination: bool = False

    combined_log_path: str = ""
    combined_log_exists: bool = False
    combined_log_line_count: int = 0

    solver_ready_febio_model_path: str = ""
    solver_working_directory: str = ""

    xplt_files_found: List[str] = Field(default_factory=list)
    log_files_found: List[str] = Field(default_factory=list)
    all_candidate_output_files: List[str] = Field(default_factory=list)

    convergence_terms_detected: List[str] = Field(default_factory=list)
    critical_error_terms_detected: List[str] = Field(default_factory=list)

    result_extraction_ready: bool = False
    human_review_required: bool = False

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
