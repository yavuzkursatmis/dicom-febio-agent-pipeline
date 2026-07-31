from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.result_extraction_schema import ResultExtractionInput
from agent_system.tools.result_extraction_tools import (
    run_result_extraction,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-14 Result Extraction Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--solver-result-validation-path", default="")

    args = parser.parse_args()

    user_input = ResultExtractionInput(
        case_id=args.case_id,
        solver_result_validation_path=args.solver_result_validation_path,
    )

    result = run_result_extraction(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_14_RESULT_EXTRACTION_COMPLETED=True")
    print("RESULT_EXTRACTION_STATUS=" + result.result_extraction_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("SOLVER_VALIDATION_PASSED=" + str(result.solver_validation_passed))
    print("NORMAL_TERMINATION_DETECTED=" + str(result.normal_termination_detected))
    print("XPLT_FILES_FOUND=" + str(result.xplt_files_found))
    print("XPLT_FILES_NONEMPTY=" + str(result.xplt_files_nonempty))
    print("SELECTED_SOLVER_LOG_PATH=" + result.selected_solver_log_path)
    print("SOLVER_LOG_EXISTS=" + str(result.solver_log_exists))
    print("SOLVER_LOG_LINE_COUNT=" + str(result.solver_log_line_count))
    print("CONVERGENCE_TERMS_DETECTED=" + str(result.convergence_terms_detected))
    print("EXTRACTED_CSV_PATH=" + result.extracted_csv_path)
    print("EXTRACTION_SUMMARY_PATH=" + result.extraction_summary_path)
    print("XPLT_BINARY_FIELD_EXTRACTION_PERFORMED=" + str(result.xplt_binary_field_extraction_performed))
    print("RESULT_SUMMARY_READY=" + str(result.result_summary_ready))
    print("HUMAN_REVIEW_REQUIRED=" + str(result.human_review_required))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
