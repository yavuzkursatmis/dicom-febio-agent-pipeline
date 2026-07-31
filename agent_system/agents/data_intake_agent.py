from pathlib import Path
import argparse
import json
import sys
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.data_intake_schema import DataIntakeInput, DataIntakeResult
from agent_system.tools.input_detection_tools import detect_input_type, next_agent_for_input_type


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def run_data_intake(user_input: DataIntakeInput) -> DataIntakeResult:
    case_folder = ROOT / "cases" / user_input.case_id
    output_json = case_folder / "00_input_manifest" / "DATA_INTAKE_RESULT.json"

    detection = detect_input_type(user_input.input_path)
    detected_type = detection["detected_input_type"]
    blockers = detection["blockers"]
    warnings = detection["warnings"]
    file_count = detection["file_count"]

    if detected_type == "MISSING" and "EMPTY_FOLDER" in blockers:
        data_status = "EMPTY_FOLDER"
    elif detected_type == "MISSING":
        data_status = "DATA_MISSING"
    elif detected_type == "UNSUPPORTED":
        data_status = "UNSUPPORTED_FORMAT"
    elif detected_type == "MULTIPLE_INPUT_TYPES":
        data_status = "MULTIPLE_INPUT_TYPES_FOUND"
    else:
        data_status = "DATA_READY"

    supported_format = data_status == "DATA_READY"
    next_agent = next_agent_for_input_type(detected_type)

    result = DataIntakeResult(
        case_id=user_input.case_id,
        input_path=user_input.input_path,
        data_status=data_status,
        detected_input_type=detected_type,
        file_count=file_count,
        supported_format=supported_format,
        case_folder=str(case_folder),
        anatomical_target=user_input.anatomical_target,
        analysis_type=user_input.analysis_type,
        test_application_region=user_input.test_application_region,
        user_notes_optional=user_input.user_notes_optional or "",
        next_agent=next_agent,
        warnings=warnings,
        blockers=blockers,
        output_json=str(output_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["human_review_required"] = True

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "data_intake_notes.md",
        f"\n## Case: {user_input.case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Veri tipi: {detected_type}\n"
        f"- Dosya sayısı: {file_count}\n"
        f"- Hedef bölge: {user_input.anatomical_target}\n"
        f"- Test türü: {user_input.analysis_type}\n"
        f"- Test uygulama yeri: {user_input.test_application_region}\n"
        f"- Durum: {data_status}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-01 Data Intake Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--anatomical-target", required=True)
    parser.add_argument("--analysis-type", required=True)
    parser.add_argument("--test-application-region", required=True)
    parser.add_argument("--user-notes-optional", default="")

    args = parser.parse_args()

    user_input = DataIntakeInput(
        case_id=args.case_id,
        input_path=args.input_path,
        anatomical_target=args.anatomical_target,
        analysis_type=args.analysis_type,
        test_application_region=args.test_application_region,
        user_notes_optional=args.user_notes_optional,
    )

    result = run_data_intake(user_input)

    print("AGENT_01_DATA_INTAKE_COMPLETED=True")
    print(f"DATA_STATUS={result.data_status}")
    print(f"DETECTED_INPUT_TYPE={result.detected_input_type}")
    print(f"FILE_COUNT={result.file_count}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()
