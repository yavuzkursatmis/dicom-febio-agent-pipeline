from pathlib import Path
import argparse
import csv
import json
import sys
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.dicom_safety_schema import DicomSafetyInput, DicomSafetyResult
from agent_system.tools.dicom_safety_tools import scan_dicom_folder


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def default_data_intake_json(case_id: str):
    return ROOT / "cases" / case_id / "00_input_manifest" / "DATA_INTAKE_RESULT.json"


def run_dicom_safety(user_input: DicomSafetyInput) -> DicomSafetyResult:
    case_id = user_input.case_id
    data_intake_path = Path(user_input.data_intake_json) if user_input.data_intake_json else default_data_intake_json(case_id)

    output_dir = ROOT / "cases" / case_id / "01_safety"
    output_json = output_dir / "DICOM_SAFETY_RESULT.json"
    output_csv = output_dir / "DICOM_HEADER_SCAN.csv"

    warnings = []
    blockers = []

    if not data_intake_path.exists():
        result = DicomSafetyResult(
            case_id=case_id,
            safety_status="BLOCKED_NOT_DICOM",
            dicom_file_count=0,
            readable_dicom_count=0,
            modality_detected="",
            is_ct=False,
            phi_risk_detected=False,
            burned_in_annotation_risk=False,
            human_review_required=True,
            next_agent="USER_ACTION_REQUIRED",
            warnings=[],
            blockers=["DATA_INTAKE_RESULT_NOT_FOUND"],
            output_json=str(output_json),
            output_csv=str(output_csv),
        )
        data = result.model_dump()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        data["clinical_use"] = False
        save_json(output_json, data)
        return result

    intake = load_json(data_intake_path)

    if intake.get("detected_input_type") != "DICOM" or intake.get("data_status") != "DATA_READY":
        result = DicomSafetyResult(
            case_id=case_id,
            safety_status="BLOCKED_NOT_DICOM",
            dicom_file_count=0,
            readable_dicom_count=0,
            modality_detected=str(intake.get("detected_input_type", "")),
            is_ct=False,
            phi_risk_detected=False,
            burned_in_annotation_risk=False,
            human_review_required=True,
            next_agent="USER_ACTION_REQUIRED",
            warnings=[],
            blockers=["INPUT_IS_NOT_READY_DICOM"],
            output_json=str(output_json),
            output_csv=str(output_csv),
        )
        data = result.model_dump()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        data["clinical_use"] = False
        save_json(output_json, data)
        return result

    input_path = intake["input_path"]

    scan = scan_dicom_folder(input_path)
    write_csv(output_csv, scan["rows"])

    dicom_file_count = scan["file_count"]
    readable_count = scan["readable_count"]
    modalities = scan["modalities"]
    modality_detected = ",".join(modalities)
    is_ct = modalities == ["CT"]

    phi_risk = bool(scan["phi_risk_detected"])
    burned_risk = bool(scan["burned_in_annotation_risk"])

    if readable_count == 0:
        safety_status = "DICOM_READ_FAIL"
        blockers.append("NO_READABLE_DICOM")
        next_agent = "USER_ACTION_REQUIRED"
    elif not is_ct:
        safety_status = "BLOCKED_NOT_CT"
        blockers.append("MODALITY_IS_NOT_CT")
        next_agent = "USER_ACTION_REQUIRED"
    elif phi_risk or burned_risk:
        safety_status = "HUMAN_REVIEW_REQUIRED"
        if phi_risk:
            blockers.append("PHI_RISK_DETECTED")
        if burned_risk:
            blockers.append("BURNED_IN_ANNOTATION_RISK")
        next_agent = "HUMAN_REVIEW_GATE"
    else:
        safety_status = "DICOM_SAFETY_PASS"
        next_agent = "IMAGE_QUALITY_AGENT"

    result = DicomSafetyResult(
        case_id=case_id,
        safety_status=safety_status,
        dicom_file_count=dicom_file_count,
        readable_dicom_count=readable_count,
        modality_detected=modality_detected,
        is_ct=is_ct,
        phi_risk_detected=phi_risk,
        burned_in_annotation_risk=burned_risk,
        human_review_required=True,
        next_agent=next_agent,
        warnings=warnings,
        blockers=blockers,
        output_json=str(output_json),
        output_csv=str(output_csv),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_data_intake_json"] = str(data_intake_path)

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "dicom_safety_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- DICOM dosya sayısı: {dicom_file_count}\n"
        f"- Okunabilir DICOM sayısı: {readable_count}\n"
        f"- Modality: {modality_detected}\n"
        f"- CT: {is_ct}\n"
        f"- PHI riski: {phi_risk}\n"
        f"- Burned-in annotation riski: {burned_risk}\n"
        f"- Güvenlik durumu: {safety_status}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-02 DICOM Safety Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-intake-json", default=None)

    args = parser.parse_args()

    user_input = DicomSafetyInput(
        case_id=args.case_id,
        data_intake_json=args.data_intake_json,
    )

    result = run_dicom_safety(user_input)

    print("AGENT_02_DICOM_SAFETY_COMPLETED=True")
    print(f"SAFETY_STATUS={result.safety_status}")
    print(f"DICOM_FILE_COUNT={result.dicom_file_count}")
    print(f"READABLE_DICOM_COUNT={result.readable_dicom_count}")
    print(f"MODALITY_DETECTED={result.modality_detected}")
    print(f"IS_CT={result.is_ct}")
    print(f"PHI_RISK_DETECTED={result.phi_risk_detected}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()
