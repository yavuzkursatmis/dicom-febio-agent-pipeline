from pathlib import Path
import json
from datetime import datetime

from agent_system.schemas.full_pipeline_audit_schema import (
    FullPipelineAuditInput,
    FullPipelineAuditResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def file_status(path: Path):
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def case_paths(case_id: str):
    c = ROOT / "cases" / case_id

    return {
        "agent10_febio_model": c / "11_febio_model_generation" / "FEBIO_MODEL_GENERATION_RESULT.json",
        "agent11_boundary_load": c / "12_boundary_load_configuration" / "BOUNDARY_LOAD_CONFIGURATION_RESULT.json",
        "agent11_review": c / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json",
        "agent12_solver": c / "13_solver_execution" / "FEBIO_SOLVER_EXECUTION_RESULT.json",
        "agent13_solver_validation": c / "14_solver_result_validation" / "SOLVER_RESULT_VALIDATION_RESULT.json",
        "agent14_result_extraction": c / "15_result_extraction" / "RESULT_EXTRACTION_RESULT.json",
        "agent15_interpretation_precheck": c / "16_result_interpretation_precheck" / "RESULT_INTERPRETATION_PRECHECK_RESULT.json",
        "agent16_academic_report": c / "17_academic_report_draft" / "ACADEMIC_REPORT_DRAFT_RESULT.json",
        "academic_report_md": c / "17_academic_report_draft" / "ACADEMIC_REPORT_DRAFT.md",
    }


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "18_full_pipeline_audit"

    return {
        "result_json": out_dir / "FULL_PIPELINE_AUDIT_RESULT.json",
        "summary_txt": out_dir / "FULL_PIPELINE_AUDIT_SUMMARY.txt",
    }


def g(data, key, default=None):
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def run_full_pipeline_audit(user_input: FullPipelineAuditInput):
    case_id = user_input.case_id
    paths = case_paths(case_id)
    out = output_paths(case_id)

    warnings = []
    blockers = []

    required_files_checked = {}
    loaded = {}

    for key, path in paths.items():
        required_files_checked[key] = file_status(path)

        if not path.exists():
            blockers.append(f"REQUIRED_FILE_MISSING:{key}")
            continue

        if path.suffix.lower() == ".json":
            try:
                loaded[key] = load_json(path)
            except Exception as e:
                blockers.append(f"JSON_READ_FAIL:{key}:{type(e).__name__}:{e}")

    a10 = loaded.get("agent10_febio_model", {})
    a11 = loaded.get("agent11_boundary_load", {})
    a11r = loaded.get("agent11_review", {})
    a12 = loaded.get("agent12_solver", {})
    a13 = loaded.get("agent13_solver_validation", {})
    a14 = loaded.get("agent14_result_extraction", {})
    a15 = loaded.get("agent15_interpretation_precheck", {})
    a16 = loaded.get("agent16_academic_report", {})

    required_status_checks = {
        "agent10_febio_model_pass": g(a10, "febio_model_status") == "FEBIO_MODEL_GENERATION_PASS",
        "agent11_boundary_load_review_required": g(a11, "boundary_load_status") == "BOUNDARY_LOAD_CONFIGURATION_REVIEW_REQUIRED",
        "agent11_review_approved": g(a11r, "approval_status") == "BOUNDARY_LOAD_REVIEW_APPROVED",
        "agent12_solver_pass": g(a12, "solver_execution_status") == "SOLVER_EXECUTION_PASS",
        "agent12_return_code_zero": g(a12, "solver_return_code") == 0,
        "agent12_normal_termination": g(a12, "normal_termination_detected") is True,
        "agent13_validation_pass": g(a13, "solver_result_validation_status") == "SOLVER_RESULT_VALIDATION_PASS",
        "agent14_extraction_pass": g(a14, "result_extraction_status") == "RESULT_EXTRACTION_PASS",
        "agent15_precheck_acceptable": g(a15, "interpretation_precheck_status") in [
            "INTERPRETATION_PRECHECK_PASS",
            "INTERPRETATION_PRECHECK_LIMITED_PASS",
        ],
        "agent16_report_pass": g(a16, "academic_report_status") == "ACADEMIC_REPORT_DRAFT_PASS",
    }

    for key, ok in required_status_checks.items():
        if not ok:
            blockers.append(f"STATUS_CHECK_FAILED:{key}")

    human_review_checks = {
        "boundary_load_review_approved": g(a11r, "approved_for_solver_execution") is True,
        "clinical_use_false_or_absent": g(a11r, "clinical_use", False) is False,
    }

    for key, ok in human_review_checks.items():
        if not ok:
            blockers.append(f"HUMAN_REVIEW_CHECK_FAILED:{key}")

    xplt_files = g(a13, "xplt_files_found", []) or []
    xplt_nonempty = g(a14, "xplt_files_nonempty", []) or []

    output_file_checks = {
        "xplt_reported_by_agent13": len(xplt_files) > 0,
        "xplt_nonempty_by_agent14": len(xplt_nonempty) > 0,
        "academic_report_md_exists": paths["academic_report_md"].exists(),
        "academic_report_md_nonempty": paths["academic_report_md"].exists() and paths["academic_report_md"].stat().st_size > 0,
    }

    for key, ok in output_file_checks.items():
        if not ok:
            blockers.append(f"OUTPUT_FILE_CHECK_FAILED:{key}")

    scientific_safety_checks = {
        "clinical_interpretation_blocked": g(a15, "clinical_interpretation_allowed") is False,
        "academic_pipeline_reporting_allowed": g(a15, "academic_pipeline_reporting_allowed") is True,
        "quantitative_field_interpretation_flag_recorded": "quantitative_field_interpretation_allowed" in a15,
        "xplt_binary_field_extraction_recorded": "xplt_binary_field_extraction_performed" in a15,
        "no_agent15_blockers": len(g(a15, "blockers", []) or []) == 0,
        "no_agent16_blockers": len(g(a16, "blockers", []) or []) == 0,
    }

    for key, ok in scientific_safety_checks.items():
        if not ok:
            blockers.append(f"SCIENTIFIC_SAFETY_CHECK_FAILED:{key}")

    if g(a15, "quantitative_field_interpretation_allowed") is False:
        warnings.append("QUANTITATIVE_FIELD_INTERPRETATION_NOT_ALLOWED_XPLT_MANUAL_OR_EXTERNAL_REVIEW_REQUIRED")

    if g(a14, "xplt_binary_field_extraction_performed") is False:
        warnings.append("XPLT_BINARY_FIELD_EXTRACTION_NOT_PERFORMED_BY_AGENT_SYSTEM")

    if blockers:
        status = "FULL_PIPELINE_AUDIT_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
    elif warnings:
        status = "FULL_PIPELINE_AUDIT_LIMITED_PASS"
        next_agent = "LANGCHAIN_LANGGRAPH_INTEGRATION_PREP"
    else:
        status = "FULL_PIPELINE_AUDIT_PASS"
        next_agent = "LANGCHAIN_LANGGRAPH_INTEGRATION_PREP"

    result = FullPipelineAuditResult(
        case_id=case_id,
        full_pipeline_audit_status=status,
        next_agent=next_agent,
        required_files_checked=required_files_checked,
        required_status_checks=required_status_checks,
        human_review_checks=human_review_checks,
        scientific_safety_checks=scientific_safety_checks,
        output_file_checks=output_file_checks,
        audit_summary_path=str(out["summary_txt"]),
        audit_json_path=str(out["result_json"]),
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(out["result_json"], result.model_dump())

    summary = f"""
Agent-17 Full Pipeline Audit
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Status: {status}
Next agent: {next_agent}

Required status checks:
{json.dumps(required_status_checks, indent=2, ensure_ascii=False)}

Human review checks:
{json.dumps(human_review_checks, indent=2, ensure_ascii=False)}

Scientific safety checks:
{json.dumps(scientific_safety_checks, indent=2, ensure_ascii=False)}

Output file checks:
{json.dumps(output_file_checks, indent=2, ensure_ascii=False)}

Warnings:
{json.dumps(result.warnings, indent=2, ensure_ascii=False)}

Blockers:
{json.dumps(result.blockers, indent=2, ensure_ascii=False)}
"""
    out["summary_txt"].write_text(summary, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: FullPipelineAuditResult):
    note_path = ROOT / "paper_notes" / "pipeline_audit_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-17 Full Pipeline Audit

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.full_pipeline_audit_status}
Sonraki ajan: {result.next_agent}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
