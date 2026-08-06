from pathlib import Path
import json
import csv
from datetime import datetime

from agent_system.schemas.result_extraction_schema import (
    ResultExtractionInput,
    ResultExtractionResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_validation_path(case_id: str):
    return ROOT / "cases" / case_id / "14_solver_result_validation" / "SOLVER_RESULT_VALIDATION_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "15_result_extraction"
    return {
        "result_json": out_dir / "RESULT_EXTRACTION_RESULT.json",
        "metrics_csv": out_dir / "SOLVER_LOG_EXTRACTED_METRICS.csv",
        "summary_txt": out_dir / "RESULT_EXTRACTION_SUMMARY.txt",
    }


def file_info(path: Path):
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": 0,
            "suffix": path.suffix.lower(),
            "modified": "",
        }

    st = path.stat()

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": st.st_size,
        "suffix": path.suffix.lower(),
        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


def read_text(path: Path):
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def choose_solver_log(log_files):
    paths = [Path(p) for p in log_files]

    febio_logs = [
        p for p in paths
        if p.exists()
        and p.suffix.lower() == ".log"
        and "solver_ready_candidate" in p.name.lower()
    ]

    if febio_logs:
        return str(sorted(febio_logs, key=lambda x: x.stat().st_size, reverse=True)[0])

    combined_logs = [
        p for p in paths
        if p.exists()
        and "combined" in p.name.lower()
    ]

    if combined_logs:
        return str(sorted(combined_logs, key=lambda x: x.stat().st_size, reverse=True)[0])

    existing = [p for p in paths if p.exists()]

    if existing:
        return str(sorted(existing, key=lambda x: x.stat().st_size, reverse=True)[0])

    return ""


def parse_solver_log(log_text: str):
    import re

    lower = log_text.lower()
    lines = log_text.splitlines()

    def last_summary_int(pattern: str, fallback: int) -> int:
        matches = re.findall(
            pattern,
            log_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        return int(matches[-1]) if matches else fallback

    normal_termination_detected = bool(
        re.search(
            (
                r"N\s*O\s*R\s*M\s*A\s*L"
                r"\s+T\s*E\s*R\s*M\s*I\s*N\s*A\s*T\s*I\s*O\s*N"
            ),
            log_text,
            flags=re.IGNORECASE,
        )
    ) or "normal termination" in lower

    time_step_fallback = len(
        re.findall(
            r"^\s*=+\s*beginning time step\b",
            log_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )

    time_step_count = last_summary_int(
        r"Number of time steps completed\s*\.*\s*:\s*(\d+)",
        time_step_fallback,
    )

    convergence_count = len(
        re.findall(
            r"^\s*-+\s*converged at time\s*:",
            log_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )

    reformation_fallback = len(
        re.findall(
            r"^\s*Reforming stiffness matrix:\s*reformation\s*#\d+",
            log_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )

    stiffness_reformation_count = last_summary_int(
        r"Total number of stiffness reformations\s*\.*\s*:\s*(\d+)",
        reformation_fallback,
    )

    metrics = {
        "normal_termination_detected": normal_termination_detected,
        "line_count": len(lines),
        "time_step_count": time_step_count,
        "convergence_count": convergence_count,
        "stiffness_reformation_count": stiffness_reformation_count,
        "fatal_error_count": lower.count("fatal error"),
        "error_count": lower.count("error"),
        "warning_count": lower.count("warning"),
        "tail_last_80_lines": "\n".join(lines[-80:]),
    }

    return metrics


def write_metrics_csv(path: Path, metrics: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()

        for key, value in metrics.items():
            writer.writerow({
                "metric": key,
                "value": json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value,
            })


def run_result_extraction(user_input: ResultExtractionInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    validation_path = Path(user_input.solver_result_validation_path) if user_input.solver_result_validation_path else default_validation_path(case_id)

    if not validation_path.exists():
        result = ResultExtractionResult(
            case_id=case_id,
            result_extraction_status="RESULT_EXTRACTION_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            solver_result_validation_path=str(validation_path),
            blockers=["SOLVER_RESULT_VALIDATION_FILE_NOT_FOUND"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    validation = load_json(validation_path)

    solver_validation_passed = validation.get("solver_result_validation_status") == "SOLVER_RESULT_VALIDATION_PASS"
    normal_termination = validation.get("normal_termination_detected") is True

    if not solver_validation_passed:
        blockers.append("SOLVER_RESULT_VALIDATION_NOT_PASS")

    if not normal_termination:
        blockers.append("NORMAL_TERMINATION_NOT_CONFIRMED")

    xplt_files = validation.get("xplt_files_found", [])
    log_files = validation.get("log_files_found", [])
    convergence_terms = validation.get("convergence_terms_detected", [])

    xplt_infos = [file_info(Path(p)) for p in xplt_files]

    xplt_nonempty = [
        info["path"]
        for info in xplt_infos
        if info["exists"] and info["size_bytes"] > 4
    ]

    if not xplt_files:
        blockers.append("NO_XPLT_FILE_FOUND")

    if xplt_files and not xplt_nonempty:
        blockers.append("XPLT_EXISTS_BUT_SIZE_INVALID")

    selected_log = choose_solver_log(log_files)
    selected_log_path = Path(selected_log) if selected_log else Path("")

    if not selected_log:
        blockers.append("NO_SOLVER_LOG_SELECTED")

    solver_log_text = read_text(selected_log_path) if selected_log else ""
    solver_log_exists = selected_log_path.exists() if selected_log else False

    if selected_log and not solver_log_exists:
        blockers.append("SELECTED_SOLVER_LOG_NOT_FOUND")

    metrics = parse_solver_log(solver_log_text) if solver_log_text else {}

    if metrics.get("fatal_error_count", 0) > 0:
        blockers.append("FATAL_ERROR_FOUND_IN_SELECTED_SOLVER_LOG")

    if metrics.get("error_count", 0) > 0:
        warnings.append(f"ERROR_TERM_COUNT_IN_SELECTED_LOG:{metrics.get('error_count')}")

    write_metrics_csv(paths["metrics_csv"], metrics)

    if blockers:
        status = "RESULT_EXTRACTION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        result_ready = False
        human_review = False
    elif warnings:
        status = "RESULT_EXTRACTION_WARNING"
        next_agent = "HUMAN_REVIEW_GATE"
        result_ready = True
        human_review = True
    else:
        status = "RESULT_EXTRACTION_PASS"
        next_agent = "AGENT_15_RESULT_INTERPRETATION_PRECHECK"
        result_ready = True
        human_review = False

    result = ResultExtractionResult(
        case_id=case_id,
        result_extraction_status=status,
        next_agent=next_agent,
        solver_result_validation_path=str(validation_path),
        solver_validation_passed=solver_validation_passed,
        xplt_files_found=xplt_files,
        xplt_files_nonempty=xplt_nonempty,
        xplt_file_info=xplt_infos,
        selected_solver_log_path=selected_log,
        solver_log_exists=solver_log_exists,
        solver_log_line_count=len(solver_log_text.splitlines()),
        normal_termination_detected=normal_termination,
        convergence_terms_detected=convergence_terms,
        parsed_solver_metrics=metrics,
        extracted_csv_path=str(paths["metrics_csv"]),
        extraction_summary_path=str(paths["summary_txt"]),
        xplt_binary_field_extraction_performed=False,
        result_summary_ready=result_ready,
        human_review_required=human_review,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    summary = f"""
Agent-14 Result Extraction
Date: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Status: {status}
Next agent: {next_agent}

Solver validation passed: {solver_validation_passed}
Normal termination detected: {normal_termination}

XPLT files:
{json.dumps(xplt_infos, indent=2, ensure_ascii=False)}

Selected solver log:
{selected_log}

Solver log line count:
{result.solver_log_line_count}

Parsed solver metrics:
{json.dumps(metrics, indent=2, ensure_ascii=False)}

Important limitation:
This Agent-14 version verifies the XPLT result file and extracts solver-log metrics.
It does not parse binary displacement/stress fields from the XPLT file.
Therefore, no field-level biomechanical interpretation is made here.

Warnings:
{result.warnings}

Blockers:
{result.blockers}
"""

    paths["summary_txt"].write_text(summary, encoding="utf-8")

    return result


def append_paper_note(case_id: str, result: ResultExtractionResult):
    note_path = ROOT / "paper_notes" / "result_extraction_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-14 Result Extraction

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.result_extraction_status}
Sonraki ajan: {result.next_agent}

Çıktılar:
- XPLT files: {result.xplt_files_found}
- Non-empty XPLT files: {result.xplt_files_nonempty}
- Selected solver log: {result.selected_solver_log_path}
- Extracted CSV: {result.extracted_csv_path}

Sınırlılık:
Bu sürüm .xplt binary dosyasından displacement/stress alanlarını parse etmez.
Yorum yapılmadan önce sonuç çıkarımı ve güvenlik kontrolü ayrılır.

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
