from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.academic_report_draft_schema import AcademicReportDraftInput
from agent_system.tools.academic_report_draft_tools import (
    run_academic_report_draft,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-16 Academic Report Draft Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--interpretation-precheck-path", default="")
    parser.add_argument("--language", default="tr")

    args = parser.parse_args()

    user_input = AcademicReportDraftInput(
        case_id=args.case_id,
        interpretation_precheck_path=args.interpretation_precheck_path,
        language=args.language,
    )

    result = run_academic_report_draft(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_16_ACADEMIC_REPORT_DRAFT_COMPLETED=True")
    print("ACADEMIC_REPORT_STATUS=" + result.academic_report_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("INTERPRETATION_PRECHECK_PASSED=" + str(result.interpretation_precheck_passed))
    print("ACADEMIC_PIPELINE_REPORTING_ALLOWED=" + str(result.academic_pipeline_reporting_allowed))
    print("QUANTITATIVE_FIELD_INTERPRETATION_ALLOWED=" + str(result.quantitative_field_interpretation_allowed))
    print("CLINICAL_INTERPRETATION_ALLOWED=" + str(result.clinical_interpretation_allowed))
    print("REPORT_MARKDOWN_PATH=" + result.report_markdown_path)
    print("REPORT_TEXT_PATH=" + result.report_text_path)
    print("REPORT_METADATA_JSON_PATH=" + result.report_metadata_json_path)
    print("REPORT_SECTIONS_CREATED=" + str(result.report_sections_created))
    print("INCLUDED_SOURCE_FILES_COUNT=" + str(len(result.included_source_files)))
    print("MISSING_OPTIONAL_SOURCE_FILES_COUNT=" + str(len(result.missing_optional_source_files)))
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
