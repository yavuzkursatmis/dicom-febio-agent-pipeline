from pathlib import Path
import json
from datetime import datetime

from agent_system.schemas.solver_result_validation_schema import (
    SolverResultValidationInput,
    SolverResultValidationResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_solver_execution_result_path(case_id: str):
    return ROOT / "cases" / case_id / "13_solver_execution" / "FEBIO_SOLVER_EXECUTION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "14_solver_result_validation"
    return {
        "result_json": out_dir / "SOLVER_RESULT_VALIDATION_RESULT.json",
        "log_summary_txt": out_dir / "SOLVER_LOG_VALIDATION_SUMMARY.txt",
    }


def read_text(path: Path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def search_output_files(solver_work_dir: Path, model_path: Path):
    search_dirs = []

    if solver_work_dir.exists():
        search_dirs.append(solver_work_dir)

    if model_path.exists() and model_path.parent.exists():
        search_dirs.append(model_path.parent)

    patterns = [
        "*.xplt",
        "*.plt",
        "*.log",
        "*.txt",
        "*.csv",
    ]

    found = []

    for d in search_dirs:
        for pattern in patterns:
            for p in d.glob(pattern):
                found.append(str(p))

    return sorted(set(found))


def classify_terms(log_text: str):
    low = log_text.lower()

    convergence_terms = []
    critical_terms = []

    positive_terms = [
        "normal termination",
        "convergence",
        "time step",
        "stiffness reformation",
        "augmentation",
        "total elapsed time",
    ]

    critical_keywords = [
        "fatal error",
        "abnormal termination",
        "negative jacobian",
        "zero pivot",
        "nan",
        "singular",
        "failed to converge",
        "unrecognized tag",
        "invalid tag",
        "parse error",
    ]

    for term in positive_terms:
        if term in low:
            convergence_terms.append(term)

    for term in critical_keywords:
        if term in low:
            critical_terms.append(term)

    return sorted(set(convergence_terms)), sorted(set(critical_terms))


def run_solver_result_validation(user_input: SolverResultValidationInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    solver_result_path = Path(user_input.solver_execution_result_path) if user_input.solver_execution_result_path else default_solver_execution_result_path(case_id)

    if not solver_result_path.exists():
        result = SolverResultValidationResult(
            case_id=case_id,
            solver_result_validation_status="SOLVER_EXECUTION_RESULT_NOT_FOUND",
            next_agent="USER_ACTION_REQUIRED",
            solver_execution_result_path=str(solver_result_path),
            blockers=["SOLVER_EXECUTION_RESULT_NOT_FOUND"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    solver_result = load_json(solver_result_path)

    solver_status_passed = solver_result.get("solver_execution_status") == "SOLVER_EXECUTION_PASS"
    solver_return_code = int(solver_result.get("solver_return_code", -1))
    normal_termination = solver_result.get("normal_termination_detected") is True

    combined_log_path = Path(solver_result.get("solver_combined_log_path", ""))
    model_path = Path(solver_result.get("solver_ready_febio_model_path", ""))
    solver_work_dir = Path(solver_result.get("solver_working_directory", ""))

    combined_log_exists = combined_log_path.exists()
    combined_log_text = read_text(combined_log_path)
    combined_lines = combined_log_text.splitlines()

    convergence_terms, critical_terms = classify_terms(combined_log_text)

    if not solver_status_passed:
        blockers.append("SOLVER_EXECUTION_STATUS_NOT_PASS")

    if not normal_termination:
        blockers.append("NORMAL_TERMINATION_NOT_CONFIRMED")

    if not combined_log_exists:
        blockers.append("SOLVER_COMBINED_LOG_NOT_FOUND")

    nonzero_return_code_with_normal = solver_return_code != 0 and normal_termination

    if nonzero_return_code_with_normal:
        warnings.append(f"NONZERO_RETURN_CODE_WITH_NORMAL_TERMINATION:{solver_return_code}")

    if critical_terms:
        blockers.append("CRITICAL_SOLVER_TERMS_DETECTED:" + ",".join(critical_terms))

    candidate_outputs = search_output_files(solver_work_dir, model_path)

    xplt_files = [
        p for p in candidate_outputs
        if p.lower().endswith(".xplt")
    ]

    log_files = [
        p for p in candidate_outputs
        if p.lower().endswith(".log") or p.lower().endswith(".txt")
    ]

    if not xplt_files:
        warnings.append("XPLT_OUTPUT_FILE_NOT_FOUND_RESULT_EXTRACTION_MAY_BE_LIMITED")

    if not log_files:
        warnings.append("NO_SOLVER_LOG_OR_TEXT_FILES_FOUND")

    if blockers:
        status = "SOLVER_RESULT_VALIDATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        extraction_ready = False
        human_review_required = False
    elif warnings:
        status = "SOLVER_RESULT_VALIDATION_WARNING"
        next_agent = "HUMAN_REVIEW_GATE"
        extraction_ready = bool(xplt_files)
        human_review_required = True
    else:
        status = "SOLVER_RESULT_VALIDATION_PASS"
        next_agent = "AGENT_14_RESULT_EXTRACTION"
        extraction_ready = True
        human_review_required = False

    result = SolverResultValidationResult(
        case_id=case_id,
        solver_result_validation_status=status,
        next_agent=next_agent,
        solver_execution_result_path=str(solver_result_path),
        solver_status_passed=solver_status_passed,
        solver_return_code=solver_return_code,
        normal_termination_detected=normal_termination,
        nonzero_return_code_with_normal_termination=nonzero_return_code_with_normal,
        combined_log_path=str(combined_log_path),
        combined_log_exists=combined_log_exists,
        combined_log_line_count=len(combined_lines),
        solver_ready_febio_model_path=str(model_path),
        solver_working_directory=str(solver_work_dir),
        xplt_files_found=xplt_files,
        log_files_found=log_files,
        all_candidate_output_files=candidate_outputs,
        convergence_terms_detected=convergence_terms,
        critical_error_terms_detected=critical_terms,
        result_extraction_ready=extraction_ready,
        human_review_required=human_review_required,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    summary = f"""
Agent-13 Solver Result Validation
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Status: {status}
Next agent: {next_agent}

Solver status passed: {solver_status_passed}
Solver return code: {solver_return_code}
Normal termination detected: {normal_termination}
Nonzero return code with normal termination: {nonzero_return_code_with_normal}

Combined log:
{combined_log_path}
Line count: {len(combined_lines)}

XPLT files:
{xplt_files}

Log files:
{log_files}

Convergence terms:
{convergence_terms}

Critical terms:
{critical_terms}

Warnings:
{result.warnings}

Blockers:
{result.blockers}
"""
    paths["log_summary_txt"].write_text(summary, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: SolverResultValidationResult):
    note_path = ROOT / "paper_notes" / "solver_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-13 Solver Result Validation

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.solver_result_validation_status}
Sonraki ajan: {result.next_agent}

Kontroller:
- Solver execution pass: {result.solver_status_passed}
- Return code: {result.solver_return_code}
- Normal termination: {result.normal_termination_detected}
- Nonzero return code with normal termination: {result.nonzero_return_code_with_normal_termination}
- XPLT files found: {result.xplt_files_found}
- Critical terms: {result.critical_error_terms_detected}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}

Not:
Bu ajan sonuç yorumu yapmaz. Sadece solver çıktısının güvenilir ve çıkarılabilir olup olmadığını doğrular.
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
