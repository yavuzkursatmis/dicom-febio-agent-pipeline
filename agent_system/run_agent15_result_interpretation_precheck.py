from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.result_interpretation_precheck_schema import ResultInterpretationPrecheckInput
from agent_system.tools.result_interpretation_precheck_tools import (
    run_result_interpretation_precheck,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-15 Result Interpretation Precheck Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--result-extraction-path", default="")

    args = parser.parse_args()

    user_input = ResultInterpretationPrecheckInput(
        case_id=args.case_id,
        result_extraction_path=args.result_extraction_path,
    )

    result = run_result_interpretation_precheck(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_15_RESULT_INTERPRETATION_PRECHECK_COMPLETED=True")
    print("INTERPRETATION_PRECHECK_STATUS=" + result.interpretation_precheck_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("RESULT_EXTRACTION_PASSED=" + str(result.result_extraction_passed))
    print("SOLVER_COMPLETED=" + str(result.solver_completed))
    print("XPLT_PRESENT=" + str(result.xplt_present))
    print("XPLT_BINARY_FIELD_EXTRACTION_PERFORMED=" + str(result.xplt_binary_field_extraction_performed))
    print("QUANTITATIVE_FIELD_INTERPRETATION_ALLOWED=" + str(result.quantitative_field_interpretation_allowed))
    print("SOLVER_LOG_INTERPRETATION_ALLOWED=" + str(result.solver_log_interpretation_allowed))
    print("CLINICAL_INTERPRETATION_ALLOWED=" + str(result.clinical_interpretation_allowed))
    print("ACADEMIC_PIPELINE_REPORTING_ALLOWED=" + str(result.academic_pipeline_reporting_allowed))
    print("ALLOWED_INTERPRETATION_SCOPE=" + str(result.allowed_interpretation_scope))
    print("PROHIBITED_INTERPRETATION_SCOPE=" + str(result.prohibited_interpretation_scope))
    print("REQUIRED_NEXT_ACTIONS=" + str(result.required_next_actions))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
