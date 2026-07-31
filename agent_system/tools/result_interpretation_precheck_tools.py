from pathlib import Path
import json
from datetime import datetime

from agent_system.schemas.result_interpretation_precheck_schema import (
    ResultInterpretationPrecheckInput,
    ResultInterpretationPrecheckResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_result_extraction_path(case_id: str):
    return ROOT / "cases" / case_id / "15_result_extraction" / "RESULT_EXTRACTION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "16_result_interpretation_precheck"
    return {
        "result_json": out_dir / "RESULT_INTERPRETATION_PRECHECK_RESULT.json",
        "summary_txt": out_dir / "RESULT_INTERPRETATION_PRECHECK_SUMMARY.txt",
    }


def run_result_interpretation_precheck(user_input: ResultInterpretationPrecheckInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    extraction_path = Path(user_input.result_extraction_path) if user_input.result_extraction_path else default_result_extraction_path(case_id)

    if not extraction_path.exists():
        result = ResultInterpretationPrecheckResult(
            case_id=case_id,
            interpretation_precheck_status="INTERPRETATION_PRECHECK_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            result_extraction_path=str(extraction_path),
            blockers=["RESULT_EXTRACTION_RESULT_NOT_FOUND"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    extraction = load_json(extraction_path)

    extraction_passed = extraction.get("result_extraction_status") == "RESULT_EXTRACTION_PASS"
    xplt_files_nonempty = extraction.get("xplt_files_nonempty", [])
    xplt_present = len(xplt_files_nonempty) > 0
    binary_extracted = extraction.get("xplt_binary_field_extraction_performed") is True
    normal_termination = extraction.get("normal_termination_detected") is True
    extraction_blockers = extraction.get("blockers", [])

    if not extraction_passed:
        blockers.append("RESULT_EXTRACTION_NOT_PASS")

    if extraction_blockers:
        blockers.append("RESULT_EXTRACTION_HAS_BLOCKERS")

    if not normal_termination:
        blockers.append("NORMAL_TERMINATION_NOT_CONFIRMED")

    if not xplt_present:
        blockers.append("VALID_XPLT_NOT_PRESENT")

    solver_completed = extraction_passed and normal_termination and xplt_present and not blockers

    quantitative_allowed = False
    solver_log_allowed = False
    clinical_allowed = False
    academic_pipeline_allowed = False

    allowed_scope = []
    prohibited_scope = []
    required_next_actions = []

    if solver_completed:
        solver_log_allowed = True
        academic_pipeline_allowed = True

        allowed_scope.extend([
            "Solver completion status may be reported.",
            "NORMAL TERMINATION may be reported.",
            "XPLT file existence and non-empty status may be reported.",
            "Solver log metrics may be reported.",
            "Pipeline-development limitations may be reported.",
        ])

        if binary_extracted:
            quantitative_allowed = True
            allowed_scope.append("Extracted displacement/stress field summaries may be interpreted within stated limitations.")
        else:
            quantitative_allowed = False
            warnings.append("XPLT_BINARY_FIELDS_NOT_EXTRACTED_QUANTITATIVE_INTERPRETATION_BLOCKED")
            prohibited_scope.extend([
                "Do not report maximum displacement.",
                "Do not report maximum stress.",
                "Do not report strain distribution.",
                "Do not make field-level biomechanical claims.",
                "Do not compare local stress/strain regions.",
            ])
            required_next_actions.append("Implement or use a validated XPLT field extraction method before quantitative biomechanical interpretation.")

        clinical_allowed = False
        prohibited_scope.extend([
            "Do not make clinical diagnosis.",
            "Do not claim patient-specific treatment decision support.",
            "Do not claim validated clinical accuracy.",
            "Do not present the pipeline-development load as a clinical physiological load.",
        ])

    if blockers:
        status = "INTERPRETATION_PRECHECK_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
    elif warnings:
        status = "INTERPRETATION_PRECHECK_LIMITED_PASS"
        next_agent = "AGENT_16_ACADEMIC_REPORT_DRAFT"
    else:
        status = "INTERPRETATION_PRECHECK_PASS"
        next_agent = "AGENT_16_ACADEMIC_REPORT_DRAFT"

    precheck_summary = {
        "solver_completed": solver_completed,
        "normal_termination": normal_termination,
        "xplt_present": xplt_present,
        "xplt_binary_field_extraction_performed": binary_extracted,
        "quantitative_field_interpretation_allowed": quantitative_allowed,
        "solver_log_interpretation_allowed": solver_log_allowed,
        "clinical_interpretation_allowed": clinical_allowed,
        "academic_pipeline_reporting_allowed": academic_pipeline_allowed,
    }

    result = ResultInterpretationPrecheckResult(
        case_id=case_id,
        interpretation_precheck_status=status,
        next_agent=next_agent,
        result_extraction_path=str(extraction_path),
        result_extraction_passed=extraction_passed,
        solver_completed=solver_completed,
        xplt_present=xplt_present,
        xplt_binary_field_extraction_performed=binary_extracted,
        quantitative_field_interpretation_allowed=quantitative_allowed,
        solver_log_interpretation_allowed=solver_log_allowed,
        clinical_interpretation_allowed=clinical_allowed,
        academic_pipeline_reporting_allowed=academic_pipeline_allowed,
        allowed_interpretation_scope=allowed_scope,
        prohibited_interpretation_scope=prohibited_scope,
        required_next_actions=required_next_actions,
        precheck_summary=precheck_summary,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    summary = f"""
Agent-15 Result Interpretation Precheck
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Status: {status}
Next agent: {next_agent}

Precheck summary:
{json.dumps(precheck_summary, indent=2, ensure_ascii=False)}

Allowed interpretation scope:
{json.dumps(allowed_scope, indent=2, ensure_ascii=False)}

Prohibited interpretation scope:
{json.dumps(prohibited_scope, indent=2, ensure_ascii=False)}

Required next actions:
{json.dumps(required_next_actions, indent=2, ensure_ascii=False)}

Warnings:
{result.warnings}

Blockers:
{result.blockers}
"""

    paths["summary_txt"].write_text(summary, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: ResultInterpretationPrecheckResult):
    note_path = ROOT / "paper_notes" / "result_interpretation_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-15 Result Interpretation Precheck

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.interpretation_precheck_status}
Sonraki ajan: {result.next_agent}

Karar:
- Solver completed: {result.solver_completed}
- XPLT present: {result.xplt_present}
- XPLT binary field extraction performed: {result.xplt_binary_field_extraction_performed}
- Quantitative field interpretation allowed: {result.quantitative_field_interpretation_allowed}
- Solver log interpretation allowed: {result.solver_log_interpretation_allowed}
- Clinical interpretation allowed: {result.clinical_interpretation_allowed}
- Academic pipeline reporting allowed: {result.academic_pipeline_reporting_allowed}

Sınırlılık:
XPLT binary field extraction yapılmadıysa maksimum displacement, maksimum stress veya alan bazlı gerilme/şekil değiştirme yorumu yapılmaz.

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
