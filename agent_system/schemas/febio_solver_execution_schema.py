from pydantic import BaseModel, Field
from typing import List


class FebioSolverExecutionInput(BaseModel):
    case_id: str
    boundary_review_result_path: str = ""
    solver_ready_febio_model_path: str = ""
    febio_exe_path: str = ""
    timeout_seconds: int = 1800


class FebioSolverExecutionResult(BaseModel):
    case_id: str
    solver_execution_status: str
    next_agent: str

    boundary_review_result_path: str = ""
    solver_ready_febio_model_path: str = ""
    febio_exe_path: str = ""

    boundary_load_review_approved: bool = False
    solver_model_exists: bool = False

    solver_run_attempted: bool = False
    solver_run_success: bool = False
    solver_return_code: int = -1

    normal_termination_detected: bool = False
    error_detected: bool = False

    solver_working_directory: str = ""
    solver_stdout_path: str = ""
    solver_stderr_path: str = ""
    solver_combined_log_path: str = ""

    febio_log_files: List[str] = Field(default_factory=list)
    febio_output_files: List[str] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
