from pathlib import Path
import json
import shutil
import subprocess
from datetime import datetime

from agent_system.schemas.febio_solver_execution_schema import (
    FebioSolverExecutionInput,
    FebioSolverExecutionResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_boundary_review_result_path(case_id: str):
    return ROOT / "cases" / case_id / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "13_solver_execution"
    return {
        "result_json": out_dir / "FEBIO_SOLVER_EXECUTION_RESULT.json",
        "stdout": out_dir / "febio_solver_stdout.txt",
        "stderr": out_dir / "febio_solver_stderr.txt",
        "combined": out_dir / "febio_solver_combined_log.txt",
        "run_notes": out_dir / "FEBIO_SOLVER_RUN_NOTES.txt",
    }


def find_febio_exe(user_path: str = ""):
    candidates = []

    if user_path:
        candidates.append(Path(user_path))

    candidates.extend([
        Path(r"C:\Program Files\FEBioStudio\bin\febio4.exe"),
        Path(r"C:\Program Files\FEBioStudio\bin\febio.exe"),
        Path(r"C:\Program Files\FEBio\bin\febio4.exe"),
        Path(r"C:\Program Files\FEBio\bin\febio.exe"),
    ])

    which_febio4 = shutil.which("febio4")
    which_febio = shutil.which("febio")

    if which_febio4:
        candidates.append(Path(which_febio4))

    if which_febio:
        candidates.append(Path(which_febio))

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return ""


def validate_boundary_review(path: Path):
    blockers = []

    if not path.exists():
        return {
            "approved": False,
            "solver_model_path": "",
            "blockers": ["BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT_NOT_FOUND"],
        }

    data = load_json(path)

    approved = data.get("approval_status") == "BOUNDARY_LOAD_REVIEW_APPROVED"
    approved_for_solver = data.get("approved_for_solver_execution") is True
    model_path = data.get("solver_ready_febio_model_path", "")

    if not approved:
        blockers.append("BOUNDARY_LOAD_REVIEW_NOT_APPROVED")

    if not approved_for_solver:
        blockers.append("NOT_APPROVED_FOR_SOLVER_EXECUTION")

    if not model_path:
        blockers.append("SOLVER_READY_FEBIO_MODEL_PATH_MISSING")
    elif not Path(model_path).exists():
        blockers.append("SOLVER_READY_FEBIO_MODEL_FILE_NOT_FOUND")

    return {
        "approved": approved and approved_for_solver and not blockers,
        "solver_model_path": model_path,
        "blockers": blockers,
    }


def collect_solver_files(work_dir: Path):
    files = []

    patterns = [
        "*.log",
        "*.xplt",
        "*.plt",
        "*.txt",
        "*.csv",
    ]

    for pattern in patterns:
        for path in work_dir.glob(pattern):
            files.append(str(path))

    return sorted(set(files))


def detect_solver_status(text: str):
    upper = text.upper()

    # FEBio may print either:
    # "NORMAL TERMINATION"
    # or banner-spaced form: "N O R M A L   T E R M I N A T I O N"
    compact_alpha = "".join(ch for ch in upper if ch.isalpha())

    normal = (
        "NORMAL TERMINATION" in upper
        or "NORMALTERMINATION" in compact_alpha
    )

    error_terms = [
        "ERROR",
        "FAILED",
        "FATAL",
        "EXCEPTION",
        "ABNORMAL TERMINATION",
    ]

    error = any(term in upper for term in error_terms)

    # If normal termination is detected, non-critical generic terms do not make
    # the run an error. Caller still checks return code.
    return normal, error


def run_solver_command(febio_exe: str, model_path: Path, work_dir: Path, timeout_seconds: int):
    """
    FEBio versions differ in command-line syntax.
    First try: febio4.exe -i model.feb
    If that fails immediately, try: febio4.exe model.feb
    """

    attempts = [
        [febio_exe, "-i", str(model_path)],
        [febio_exe, str(model_path)],
    ]

    last_completed = None

    for cmd in attempts:
        completed = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        last_completed = completed

        combined = (completed.stdout or "") + "\n" + (completed.stderr or "")

        # Accept if normal termination or return code 0.
        if completed.returncode == 0 or "NORMAL TERMINATION" in combined.upper():
            return completed, cmd

        # If command-line syntax is rejected, fallback to next attempt.
        if "-i" in cmd:
            syntax_indicators = [
                "unknown option",
                "invalid option",
                "usage",
                "unrecognized",
            ]
            if any(x in combined.lower() for x in syntax_indicators):
                continue

        # If solver actually ran and failed, do not hide it with fallback.
        break

    return last_completed, attempts[-1]


def run_febio_solver_execution(user_input: FebioSolverExecutionInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    boundary_review_path = Path(user_input.boundary_review_result_path) if user_input.boundary_review_result_path else default_boundary_review_result_path(case_id)

    review = validate_boundary_review(boundary_review_path)
    blockers.extend(review["blockers"])

    solver_model_path = Path(user_input.solver_ready_febio_model_path) if user_input.solver_ready_febio_model_path else Path(review.get("solver_model_path", ""))

    if user_input.solver_ready_febio_model_path and not solver_model_path.exists():
        blockers.append("USER_PROVIDED_SOLVER_READY_MODEL_NOT_FOUND")

    febio_exe = find_febio_exe(user_input.febio_exe_path)

    if not febio_exe:
        blockers.append("FEBIO_EXECUTABLE_NOT_FOUND")

    solver_work_dir = paths["result_json"].parent
    solver_work_dir.mkdir(parents=True, exist_ok=True)

    if blockers:
        result = FebioSolverExecutionResult(
            case_id=case_id,
            solver_execution_status="SOLVER_EXECUTION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            boundary_review_result_path=str(boundary_review_path),
            solver_ready_febio_model_path=str(solver_model_path),
            febio_exe_path=febio_exe,
            boundary_load_review_approved=review["approved"],
            solver_model_exists=solver_model_path.exists() if str(solver_model_path) else False,
            solver_working_directory=str(solver_work_dir),
            solver_stdout_path=str(paths["stdout"]),
            solver_stderr_path=str(paths["stderr"]),
            solver_combined_log_path=str(paths["combined"]),
            warnings=warnings,
            blockers=list(dict.fromkeys(blockers)),
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    try:
        completed, used_cmd = run_solver_command(
            febio_exe=febio_exe,
            model_path=solver_model_path,
            work_dir=solver_work_dir,
            timeout_seconds=user_input.timeout_seconds,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        combined = stdout + "\n" + stderr

        paths["stdout"].write_text(stdout, encoding="utf-8", errors="replace")
        paths["stderr"].write_text(stderr, encoding="utf-8", errors="replace")
        paths["combined"].write_text(combined, encoding="utf-8", errors="replace")

        return_code = int(completed.returncode)

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        combined = str(stdout) + "\n" + str(stderr)

        paths["stdout"].write_text(str(stdout), encoding="utf-8", errors="replace")
        paths["stderr"].write_text(str(stderr), encoding="utf-8", errors="replace")
        paths["combined"].write_text(combined, encoding="utf-8", errors="replace")

        result = FebioSolverExecutionResult(
            case_id=case_id,
            solver_execution_status="SOLVER_EXECUTION_TIMEOUT",
            next_agent="USER_ACTION_REQUIRED",
            boundary_review_result_path=str(boundary_review_path),
            solver_ready_febio_model_path=str(solver_model_path),
            febio_exe_path=febio_exe,
            boundary_load_review_approved=review["approved"],
            solver_model_exists=solver_model_path.exists(),
            solver_run_attempted=True,
            solver_run_success=False,
            solver_return_code=-1,
            normal_termination_detected=False,
            error_detected=True,
            solver_working_directory=str(solver_work_dir),
            solver_stdout_path=str(paths["stdout"]),
            solver_stderr_path=str(paths["stderr"]),
            solver_combined_log_path=str(paths["combined"]),
            warnings=warnings,
            blockers=[f"SOLVER_TIMEOUT_AFTER_SECONDS:{user_input.timeout_seconds}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    except Exception as e:
        result = FebioSolverExecutionResult(
            case_id=case_id,
            solver_execution_status="SOLVER_EXECUTION_FAIL",
            next_agent="USER_ACTION_REQUIRED",
            boundary_review_result_path=str(boundary_review_path),
            solver_ready_febio_model_path=str(solver_model_path),
            febio_exe_path=febio_exe,
            boundary_load_review_approved=review["approved"],
            solver_model_exists=solver_model_path.exists(),
            solver_run_attempted=True,
            solver_run_success=False,
            solver_return_code=-1,
            normal_termination_detected=False,
            error_detected=True,
            solver_working_directory=str(solver_work_dir),
            solver_stdout_path=str(paths["stdout"]),
            solver_stderr_path=str(paths["stderr"]),
            solver_combined_log_path=str(paths["combined"]),
            warnings=warnings,
            blockers=[f"SOLVER_EXECUTION_EXCEPTION:{type(e).__name__}:{e}"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    log_text = paths["combined"].read_text(encoding="utf-8", errors="replace")

    # Also inspect solver-generated log files if present.
    solver_files = collect_solver_files(solver_work_dir)
    log_files = [p for p in solver_files if p.lower().endswith(".log") or p.lower().endswith(".txt")]

    for lf in log_files:
        try:
            log_text += "\n" + Path(lf).read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    normal, error = detect_solver_status(log_text)

    if return_code != 0 and not normal:
        blockers.append(f"FEBIO_RETURN_CODE_NONZERO:{return_code}")

    if not normal:
        blockers.append("NORMAL_TERMINATION_NOT_DETECTED")

    if error and not normal:
        blockers.append("SOLVER_ERROR_TERMS_DETECTED")

    if blockers:
        status = "SOLVER_EXECUTION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        solver_success = False
    else:
        status = "SOLVER_EXECUTION_PASS"
        next_agent = "AGENT_13_SOLVER_RESULT_VALIDATION"
        solver_success = True

    result = FebioSolverExecutionResult(
        case_id=case_id,
        solver_execution_status=status,
        next_agent=next_agent,
        boundary_review_result_path=str(boundary_review_path),
        solver_ready_febio_model_path=str(solver_model_path),
        febio_exe_path=febio_exe,
        boundary_load_review_approved=review["approved"],
        solver_model_exists=solver_model_path.exists(),
        solver_run_attempted=True,
        solver_run_success=solver_success,
        solver_return_code=return_code,
        normal_termination_detected=normal,
        error_detected=error and not normal,
        solver_working_directory=str(solver_work_dir),
        solver_stdout_path=str(paths["stdout"]),
        solver_stderr_path=str(paths["stderr"]),
        solver_combined_log_path=str(paths["combined"]),
        febio_log_files=log_files,
        febio_output_files=solver_files,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    notes = f"""
Agent-12 FEBio Solver Execution
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Status: {status}
Next agent: {next_agent}

FEBio executable:
{febio_exe}

Solver-ready model:
{solver_model_path}

Working directory:
{solver_work_dir}

Return code:
{return_code}

Normal termination detected:
{normal}

Blockers:
{result.blockers}
"""

    paths["run_notes"].write_text(notes, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: FebioSolverExecutionResult):
    note_path = ROOT / "paper_notes" / "solver_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-12 FEBio Solver Execution

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.solver_execution_status}
Sonraki ajan: {result.next_agent}

Girdi:
- Solver-ready FEBio model: {result.solver_ready_febio_model_path}
- FEBio executable: {result.febio_exe_path}

Çalıştırma:
- Solver attempted: {result.solver_run_attempted}
- Return code: {result.solver_return_code}
- Normal termination: {result.normal_termination_detected}

Log dosyaları:
- stdout: {result.solver_stdout_path}
- stderr: {result.solver_stderr_path}
- combined: {result.solver_combined_log_path}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}

Not:
Bu ajan sonuç yorumu yapmaz. Sadece solver çalıştırır ve normal termination/log kontrolü yapar.
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
