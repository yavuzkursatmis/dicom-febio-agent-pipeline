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

from agent_system.schemas.image_quality_schema import ImageQualityInput, ImageQualityResult
from agent_system.tools.image_quality_tools import make_quality_profile


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


def default_safety_json(case_id: str):
    return ROOT / "cases" / case_id / "01_safety" / "DICOM_SAFETY_RESULT.json"


def default_intake_json(case_id: str):
    return ROOT / "cases" / case_id / "00_input_manifest" / "DATA_INTAKE_RESULT.json"


def run_image_quality(user_input: ImageQualityInput) -> ImageQualityResult:
    case_id = user_input.case_id
    safety_path = Path(user_input.dicom_safety_json) if user_input.dicom_safety_json else default_safety_json(case_id)
    intake_path = default_intake_json(case_id)

    output_dir = ROOT / "cases" / case_id / "02_image_quality"
    output_json = output_dir / "IMAGE_QUALITY_RESULT.json"
    output_csv = output_dir / "IMAGE_QUALITY_PROFILE.csv"

    warnings = []
    blockers = []

    if not safety_path.exists():
        result = ImageQualityResult(
            case_id=case_id,
            image_quality_status="BLOCKED_BY_DICOM_SAFETY",
            series_read_success=False,
            slice_count=0,
            image_size="",
            spacing="",
            slice_thickness=0.0,
            voxel_anisotropy=0.0,
            intensity_min=0.0,
            intensity_max=0.0,
            intensity_mean=0.0,
            next_agent="USER_ACTION_REQUIRED",
            warnings=[],
            blockers=["DICOM_SAFETY_RESULT_NOT_FOUND"],
            output_json=str(output_json),
            output_csv=str(output_csv),
        )
        data = result.model_dump()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        data["clinical_use"] = False
        save_json(output_json, data)
        return result

    safety = load_json(safety_path)

    if safety.get("safety_status") != "DICOM_SAFETY_PASS":
        result = ImageQualityResult(
            case_id=case_id,
            image_quality_status="BLOCKED_BY_DICOM_SAFETY",
            series_read_success=False,
            slice_count=0,
            image_size="",
            spacing="",
            slice_thickness=0.0,
            voxel_anisotropy=0.0,
            intensity_min=0.0,
            intensity_max=0.0,
            intensity_mean=0.0,
            next_agent="USER_ACTION_REQUIRED",
            warnings=[],
            blockers=["DICOM_SAFETY_NOT_PASSED"],
            output_json=str(output_json),
            output_csv=str(output_csv),
        )
        data = result.model_dump()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        data["clinical_use"] = False
        save_json(output_json, data)
        return result

    if not intake_path.exists():
        blockers.append("DATA_INTAKE_RESULT_NOT_FOUND")
        input_path = ""
    else:
        intake = load_json(intake_path)
        input_path = intake.get("input_path", "")

    profile = make_quality_profile(input_path) if input_path else {
        "rows": [],
        "series_read_success": False,
        "slice_count": 0,
        "image_size": "",
        "spacing": "",
        "slice_thickness": 0.0,
        "voxel_anisotropy": 0.0,
        "intensity_min": 0.0,
        "intensity_max": 0.0,
        "intensity_mean": 0.0,
        "warnings": [],
        "blockers": ["INPUT_PATH_MISSING"],
    }

    write_csv(output_csv, profile["rows"])

    warnings.extend(profile["warnings"])
    blockers.extend(profile["blockers"])

    if blockers:
        image_quality_status = "DICOM_SERIES_READ_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
    elif warnings:
        image_quality_status = "IMAGE_QUALITY_WARNING"
        next_agent = "TARGET_UNDERSTANDING_AGENT"
    else:
        image_quality_status = "IMAGE_QUALITY_PASS"
        next_agent = "TARGET_UNDERSTANDING_AGENT"

    result = ImageQualityResult(
        case_id=case_id,
        image_quality_status=image_quality_status,
        series_read_success=profile["series_read_success"],
        slice_count=profile["slice_count"],
        image_size=profile["image_size"],
        spacing=profile["spacing"],
        slice_thickness=profile["slice_thickness"],
        voxel_anisotropy=profile["voxel_anisotropy"],
        intensity_min=profile["intensity_min"],
        intensity_max=profile["intensity_max"],
        intensity_mean=profile["intensity_mean"],
        next_agent=next_agent,
        warnings=warnings,
        blockers=blockers,
        output_json=str(output_json),
        output_csv=str(output_csv),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_dicom_safety_json"] = str(safety_path)

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "image_quality_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Durum: {image_quality_status}\n"
        f"- Slice sayısı: {profile['slice_count']}\n"
        f"- Görüntü boyutu: {profile['image_size']}\n"
        f"- Spacing: {profile['spacing']}\n"
        f"- Slice thickness: {profile['slice_thickness']}\n"
        f"- Voxel anisotropy: {profile['voxel_anisotropy']}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-03 Image Quality Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--dicom-safety-json", default=None)

    args = parser.parse_args()

    result = run_image_quality(ImageQualityInput(
        case_id=args.case_id,
        dicom_safety_json=args.dicom_safety_json,
    ))

    print("AGENT_03_IMAGE_QUALITY_COMPLETED=True")
    print(f"IMAGE_QUALITY_STATUS={result.image_quality_status}")
    print(f"SERIES_READ_SUCCESS={result.series_read_success}")
    print(f"SLICE_COUNT={result.slice_count}")
    print(f"IMAGE_SIZE={result.image_size}")
    print(f"SPACING={result.spacing}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()
