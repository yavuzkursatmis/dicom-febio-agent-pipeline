from pathlib import Path
import argparse
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.full_pipeline_audit_schema import FullPipelineAuditInput
from agent_system.tools.full_pipeline_audit_tools import (
    run_full_pipeline_audit,
    append_paper_note,
)


def main():
    parser = argparse.ArgumentParser(description="Agent-17 Full Pipeline Audit Agent")
    parser.add_argument("--case-id", required=True)

    args = parser.parse_args()

    user_input = FullPipelineAuditInput(case_id=args.case_id)

    result = run_full_pipeline_audit(user_input)
    append_paper_note(args.case_id, result)

    print("AGENT_17_FULL_PIPELINE_AUDIT_COMPLETED=True")
    print("FULL_PIPELINE_AUDIT_STATUS=" + result.full_pipeline_audit_status)
    print("NEXT_AGENT=" + result.next_agent)
    print("REQUIRED_STATUS_CHECKS=" + str(result.required_status_checks))
    print("HUMAN_REVIEW_CHECKS=" + str(result.human_review_checks))
    print("SCIENTIFIC_SAFETY_CHECKS=" + str(result.scientific_safety_checks))
    print("OUTPUT_FILE_CHECKS=" + str(result.output_file_checks))
    print("AUDIT_SUMMARY_PATH=" + result.audit_summary_path)
    print("AUDIT_JSON_PATH=" + result.audit_json_path)
    print("WARNINGS=" + str(result.warnings))
    print("BLOCKERS=" + str(result.blockers))


if __name__ == "__main__":
    main()
