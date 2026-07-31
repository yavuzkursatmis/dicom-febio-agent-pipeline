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

from agent_system.schemas.segmentation_validation_schema import (
    SegmentationValidationInput,
    SegmentationValidationResult,
)
from agent_system.tools.segmentation_validation_tools import (
    path_exists,
    read_image,
    calculate_mask_profile,
    broad_volume_warning,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def default_segmentation_json(case_id: str):
    return ROOT / "cases" / case_id / "04_segmentation" / "SEGMENTATION_RESULT.json"


def empty_result(
    case_id: str,
    output_json: Path,
    output_csv: Path,
    status: str,
    blocker: str,
):
    result = SegmentationValidationResult(
        case_id=case_id,
        segmentation_validation_status=status,
        mask_exists=False,
        mask_read_success=False,
        mask_is_empty=True,
        mask_voxel_count=0,
        mask_volume_mm3=0.0,
        mask_volume_cm3=0.0,
        reference_image_path="",
        mask_size="",
        reference_size="",
        mask_spacing="",
        reference_spacing="",
        image_mask_size_match=False,
        image_mask_spacing_match=False,
        resampling_applied=False,
        human_review_required=True,
        next_agent="USER_ACTION_REQUIRED",
        warnings=[],
        blockers=[blocker],
        output_json=str(output_json),
        output_csv=str(output_csv),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False

    save_json(output_json, data)
    write_csv(output_csv, data)

    return result


def select_reference_image(segmentation: dict) -> str:
    resampling_applied = bool(segmentation.get("resampling_applied", False))

    if resampling_applied:
        resampled = segmentation.get("resampled_volume_path", "")
        if resampled and Path(resampled).exists():
            return resampled

    return segmentation.get("original_volume_path", "")


def run_segmentation_validation(
    user_input: SegmentationValidationInput,
) -> SegmentationValidationResult:

    case_id = user_input.case_id

    segmentation_path = Path(user_input.segmentation_json) if user_input.segmentation_json else default_segmentation_json(case_id)

    output_dir = ROOT / "cases" / case_id / "05_segmentation_validation"
    output_json = output_dir / "SEGMENTATION_VALIDATION_RESULT.json"
    output_csv = output_dir / "MASK_VALIDATION_PROFILE.csv"

    if not segmentation_path.exists():
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "BLOCKED_BY_SEGMENTATION",
            "SEGMENTATION_RESULT_NOT_FOUND",
        )

    segmentation = load_json(segmentation_path)

    segmentation_status = segmentation.get("segmentation_status", "")
    if segmentation_status not in ["SEGMENTATION_PASS", "SEGMENTATION_WARNING"]:
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "BLOCKED_BY_SEGMENTATION",
            "SEGMENTATION_NOT_PASSED",
        )

    warnings = []
    blockers = []

    mask_path = segmentation.get("segmentation_mask_path", "")
    reference_image_path = select_reference_image(segmentation)
    resampling_applied = bool(segmentation.get("resampling_applied", False))

    mask_exists = path_exists(mask_path)

    if not mask_exists:
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "SEGMENTATION_VALIDATION_FAIL",
            "SEGMENTATION_MASK_NOT_FOUND",
        )

    mask_image, mask_read_success, mask_error = read_image(mask_path)

    if not mask_read_success:
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "SEGMENTATION_VALIDATION_FAIL",
            "SEGMENTATION_MASK_READ_FAIL=" + mask_error,
        )

    if not path_exists(reference_image_path):
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "SEGMENTATION_VALIDATION_FAIL",
            "REFERENCE_IMAGE_NOT_FOUND",
        )

    reference_image, reference_read_success, reference_error = read_image(reference_image_path)

    if not reference_read_success:
        return empty_result(
            case_id,
            output_json,
            output_csv,
            "SEGMENTATION_VALIDATION_FAIL",
            "REFERENCE_IMAGE_READ_FAIL=" + reference_error,
        )

    profile = calculate_mask_profile(mask_image, reference_image)

    if profile["mask_is_empty"]:
        blockers.append("SEGMENTATION_MASK_IS_EMPTY")

    if profile["mask_voxel_count"] <= 0:
        blockers.append("MASK_VOXEL_COUNT_ZERO")

    if not profile["image_mask_size_match"]:
        blockers.append("IMAGE_MASK_SIZE_MISMATCH")

    if not profile["image_mask_spacing_match"]:
        blockers.append("IMAGE_MASK_SPACING_MISMATCH")

    if broad_volume_warning(profile["mask_volume_cm3"]):
        warnings.append("MASK_VOLUME_OUTSIDE_BROAD_TECHNICAL_RANGE")

    segmentation_warnings = segmentation.get("warnings", [])

    if resampling_applied:
        warnings.append("RESAMPLING_APPLIED_REVIEW_REQUIRED")

    if "HIGH_VOXEL_ANISOTROPY_RESAMPLED" in segmentation_warnings:
        warnings.append("HIGH_VOXEL_ANISOTROPY_RESAMPLED_VALIDATION_NOTE")

    if blockers:
        validation_status = "SEGMENTATION_VALIDATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        human_review_required = True
    elif warnings:
        validation_status = "SEGMENTATION_VALIDATION_WARNING"
        next_agent = "HUMAN_REVIEW_GATE"
        human_review_required = True
    else:
        validation_status = "SEGMENTATION_VALIDATION_PASS"
        next_agent = "MATERIAL_SELECTION_AGENT"
        human_review_required = False

    result = SegmentationValidationResult(
        case_id=case_id,
        segmentation_validation_status=validation_status,
        mask_exists=mask_exists,
        mask_read_success=mask_read_success,
        mask_is_empty=profile["mask_is_empty"],
        mask_voxel_count=profile["mask_voxel_count"],
        mask_volume_mm3=profile["mask_volume_mm3"],
        mask_volume_cm3=profile["mask_volume_cm3"],
        reference_image_path=reference_image_path,
        mask_size=profile["mask_size"],
        reference_size=profile["reference_size"],
        mask_spacing=profile["mask_spacing"],
        reference_spacing=profile["reference_spacing"],
        image_mask_size_match=profile["image_mask_size_match"],
        image_mask_spacing_match=profile["image_mask_spacing_match"],
        resampling_applied=resampling_applied,
        human_review_required=human_review_required,
        next_agent=next_agent,
        warnings=warnings,
        blockers=blockers,
        output_json=str(output_json),
        output_csv=str(output_csv),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_segmentation_json"] = str(segmentation_path)
    data["segmentation_target"] = segmentation.get("segmentation_target", "")

    save_json(output_json, data)
    write_csv(output_csv, data)

    append_text(
        ROOT / "paper_notes" / "segmentation_validation_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Durum: {validation_status}\n"
        f"- Mask exists: {mask_exists}\n"
        f"- Mask voxel count: {profile['mask_voxel_count']}\n"
        f"- Mask volume cm3: {profile['mask_volume_cm3']}\n"
        f"- Size match: {profile['image_mask_size_match']}\n"
        f"- Spacing match: {profile['image_mask_spacing_match']}\n"
        f"- Resampling applied: {resampling_applied}\n"
        f"- Next agent: {next_agent}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-06 Segmentation Validation Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--segmentation-json", default=None)

    args = parser.parse_args()

    result = run_segmentation_validation(SegmentationValidationInput(
        case_id=args.case_id,
        segmentation_json=args.segmentation_json,
    ))

    print("AGENT_06_SEGMENTATION_VALIDATION_COMPLETED=True")
    print(f"SEGMENTATION_VALIDATION_STATUS={result.segmentation_validation_status}")
    print(f"MASK_EXISTS={result.mask_exists}")
    print(f"MASK_READ_SUCCESS={result.mask_read_success}")
    print(f"MASK_IS_EMPTY={result.mask_is_empty}")
    print(f"MASK_VOXEL_COUNT={result.mask_voxel_count}")
    print(f"MASK_VOLUME_CM3={result.mask_volume_cm3}")
    print(f"IMAGE_MASK_SIZE_MATCH={result.image_mask_size_match}")
    print(f"IMAGE_MASK_SPACING_MATCH={result.image_mask_spacing_match}")
    print(f"RESAMPLING_APPLIED={result.resampling_applied}")
    print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"WARNINGS={result.warnings}")
    print(f"BLOCKERS={result.blockers}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()
