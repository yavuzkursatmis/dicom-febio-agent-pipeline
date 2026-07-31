from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.febio_solver_execution_schema import FebioSolverExecutionInput
from agent_system.tools.febio_solver_execution_tools import (
    run_febio_solver_execution,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-12 FEBio Solver Execution Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--boundary-review-result-path", default="")
    parser.add_argument("--solver-ready-febio-model-path", default="")
    parser.add_argument("--febio-exe-path", default="")
    parser.add_argument("--timeout-seconds", type=int, default=1800)

    args = parser.parse_args()

    user_input = FebioSolverExecutionInput(
        case_id=args.case_id,
        boundary_review_result_path=args.boundary_review_result_path,
        solver_ready_febio_model_path=args.solver_ready_febio_model_path,
        febio_exe_path=args.febio_exe_path,
        timeout_seconds=args.timeout_seconds,
    )

    result = run_febio_solver_execution(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_12_FEBIO_SOLVER_EXECUTION_COMPLETED=True")
    print("SOLVER_EXECUTION_STATUS=" + result.solver_execution_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("BOUNDARY_LOAD_REVIEW_APPROVED=" + str(result.boundary_load_review_approved))
    print("SOLVER_MODEL_EXISTS=" + str(result.solver_model_exists))
    print("SOLVER_RUN_ATTEMPTED=" + str(result.solver_run_attempted))
    print("SOLVER_RUN_SUCCESS=" + str(result.solver_run_success))
    print("SOLVER_RETURN_CODE=" + str(result.solver_return_code))
    print("NORMAL_TERMINATION_DETECTED=" + str(result.normal_termination_detected))
    print("ERROR_DETECTED=" + str(result.error_detected))
    print("FEBIO_EXE_PATH=" + result.febio_exe_path)
    print("SOLVER_READY_FEBIO_MODEL_PATH=" + result.solver_ready_febio_model_path)
    print("SOLVER_WORKING_DIRECTORY=" + result.solver_working_directory)
    print("SOLVER_STDOUT_PATH=" + result.solver_stdout_path)
    print("SOLVER_STDERR_PATH=" + result.solver_stderr_path)
    print("SOLVER_COMBINED_LOG_PATH=" + result.solver_combined_log_path)
    print("FEBIO_LOG_FILES=" + str(result.febio_log_files))
    print("FEBIO_OUTPUT_FILES=" + str(result.febio_output_files))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
