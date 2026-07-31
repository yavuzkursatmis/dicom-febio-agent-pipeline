from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.solver_result_validation_schema import SolverResultValidationInput
from agent_system.tools.solver_result_validation_tools import (
    run_solver_result_validation,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-13 Solver Result Validation Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--solver-execution-result-path", default="")

    args = parser.parse_args()

    user_input = SolverResultValidationInput(
        case_id=args.case_id,
        solver_execution_result_path=args.solver_execution_result_path,
    )

    result = run_solver_result_validation(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_13_SOLVER_RESULT_VALIDATION_COMPLETED=True")
    print("SOLVER_RESULT_VALIDATION_STATUS=" + result.solver_result_validation_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("SOLVER_STATUS_PASSED=" + str(result.solver_status_passed))
    print("SOLVER_RETURN_CODE=" + str(result.solver_return_code))
    print("NORMAL_TERMINATION_DETECTED=" + str(result.normal_termination_detected))
    print("NONZERO_RETURN_CODE_WITH_NORMAL_TERMINATION=" + str(result.nonzero_return_code_with_normal_termination))
    print("COMBINED_LOG_EXISTS=" + str(result.combined_log_exists))
    print("COMBINED_LOG_LINE_COUNT=" + str(result.combined_log_line_count))
    print("XPLT_FILES_FOUND=" + str(result.xplt_files_found))
    print("LOG_FILES_FOUND=" + str(result.log_files_found))
    print("CONVERGENCE_TERMS_DETECTED=" + str(result.convergence_terms_detected))
    print("CRITICAL_ERROR_TERMS_DETECTED=" + str(result.critical_error_terms_detected))
    print("RESULT_EXTRACTION_READY=" + str(result.result_extraction_ready))
    print("HUMAN_REVIEW_REQUIRED=" + str(result.human_review_required))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
