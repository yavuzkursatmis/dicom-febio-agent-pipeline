from pathlib import Path
import argparse
import json
import sys
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.segmentation_schema import SegmentationInput, SegmentationResult
from agent_system.tools.segmentation_tools import (
    load_config,
    read_dicom_series,
    save_nifti,
    spacing_to_string,
    should_resample,
    resample_image,
    run_totalsegmentator,
    find_target_mask,
    copy_mask_to_standard_path,
    write_text,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def default_data_intake_json(case_id: str):
    return ROOT / "cases" / case_id / "00_input_manifest" / "DATA_INTAKE_RESULT.json"


def default_image_quality_json(case_id: str):
    return ROOT / "cases" / case_id / "02_image_quality" / "IMAGE_QUALITY_RESULT.json"


def default_target_json(case_id: str):
    return ROOT / "cases" / case_id / "03_target_understanding" / "TARGET_UNDERSTANDING_RESULT.json"


def blocked_result(case_id: str, output_json: Path, preprocessing_json: Path, blocker: str):
    result = SegmentationResult(
        case_id=case_id,
        segmentation_status="BLOCKED_BY_TARGET_UNDERSTANDING",
        preprocessing_required=False,
        resampling_applied=False,
        original_spacing="",
        target_spacing="",
        resampled_spacing="",
        segmentation_mode="",
        segmentation_tool="",
        segmentation_target="",
        original_volume_path="",
        resampled_volume_path="",
        segmentation_mask_path="",
        raw_segmentation_output_dir="",
        next_agent="USER_ACTION_REQUIRED",
        human_review_required=True,
        warnings=[],
        blockers=[blocker],
        preprocessing_json=str(preprocessing_json),
        output_json=str(output_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False

    save_json(output_json, data)
    save_json(preprocessing_json, data)

    return result


def run_segmentation(user_input: SegmentationInput) -> SegmentationResult:
    case_id = user_input.case_id

    data_intake_path = Path(user_input.data_intake_json) if user_input.data_intake_json else default_data_intake_json(case_id)
    image_quality_path = Path(user_input.image_quality_json) if user_input.image_quality_json else default_image_quality_json(case_id)
    target_path = Path(user_input.target_understanding_json) if user_input.target_understanding_json else default_target_json(case_id)

    output_dir = ROOT / "cases" / case_id / "04_segmentation"
    preprocessing_json = output_dir / "PREPROCESSING_RESULT.json"
    output_json = output_dir / "SEGMENTATION_RESULT.json"

    if user_input.reuse_existing and output_json.exists():
        existing = load_json(output_json)
        mask_path = existing.get("segmentation_mask_path", "")
        if mask_path and Path(mask_path).exists():
            return SegmentationResult(**existing)

    original_volume_path = output_dir / "volume_original.nii.gz"
    resampled_volume_path = output_dir / "volume_resampled.nii.gz"
    segmentation_mask_path = output_dir / "segmentation_mask.nii.gz"
    raw_segmentation_output_dir = output_dir / "totalsegmentator_raw"

    if not data_intake_path.exists():
        return blocked_result(case_id, output_json, preprocessing_json, "DATA_INTAKE_RESULT_NOT_FOUND")

    if not image_quality_path.exists():
        return blocked_result(case_id, output_json, preprocessing_json, "IMAGE_QUALITY_RESULT_NOT_FOUND")

    if not target_path.exists():
        return blocked_result(case_id, output_json, preprocessing_json, "TARGET_UNDERSTANDING_RESULT_NOT_FOUND")

    data_intake = load_json(data_intake_path)
    image_quality = load_json(image_quality_path)
    target = load_json(target_path)

    if target.get("target_understanding_status") != "TARGET_UNDERSTANDING_PASS":
        return blocked_result(case_id, output_json, preprocessing_json, "TARGET_UNDERSTANDING_NOT_PASSED")

    config = load_config()

    input_path = data_intake.get("input_path", "")
    segmentation_target = target.get("segmentation_target", "")

    warnings = []
    blockers = []

    segmentation_mode = config.get("default_segmentation_mode", "AUTO_SEGMENTATION")
    segmentation_tool = config.get("default_segmentation_tool", "TotalSegmentator")

    try:
        image, series_files = read_dicom_series(input_path)
    except Exception as e:
        blockers.append(f"DICOM_VOLUME_READ_FAIL={type(e).__name__}")
        result_status = "SEGMENTATION_FAIL"

        result = SegmentationResult(
            case_id=case_id,
            segmentation_status=result_status,
            preprocessing_required=False,
            resampling_applied=False,
            original_spacing="",
            target_spacing="",
            resampled_spacing="",
            segmentation_mode=segmentation_mode,
            segmentation_tool=segmentation_tool,
            segmentation_target=segmentation_target,
            original_volume_path="",
            resampled_volume_path="",
            segmentation_mask_path="",
            raw_segmentation_output_dir=str(raw_segmentation_output_dir),
            next_agent="USER_ACTION_REQUIRED",
            human_review_required=True,
            warnings=warnings,
            blockers=blockers,
            preprocessing_json=str(preprocessing_json),
            output_json=str(output_json),
        )

        data = result.model_dump()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        data["clinical_use"] = False
        save_json(output_json, data)
        save_json(preprocessing_json, data)
        return result

    original_spacing = spacing_to_string(image.GetSpacing())
    save_nifti(image, original_volume_path)

    preprocessing_required = should_resample(image_quality, config)

    target_spacing_values = config.get("resampling_policy", {}).get("target_spacing_mm", [0.75, 0.75, 0.75])
    target_spacing_tuple = tuple(float(x) for x in target_spacing_values)
    target_spacing = spacing_to_string(target_spacing_tuple)

    if preprocessing_required:
        resampled_image = resample_image(image, target_spacing_tuple)
        save_nifti(resampled_image, resampled_volume_path)
        resampling_applied = True
        resampled_spacing = spacing_to_string(resampled_image.GetSpacing())
        segmentation_input = resampled_volume_path
        warnings.append("HIGH_VOXEL_ANISOTROPY_RESAMPLED")
    else:
        resampling_applied = False
        resampled_spacing = original_spacing
        segmentation_input = original_volume_path

    preprocessing_data = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "preprocessing_required": preprocessing_required,
        "resampling_applied": resampling_applied,
        "original_spacing": original_spacing,
        "target_spacing": target_spacing,
        "resampled_spacing": resampled_spacing,
        "original_volume_path": str(original_volume_path),
        "resampled_volume_path": str(resampled_volume_path) if resampling_applied else "",
        "reason": image_quality.get("warnings", []),
        "clinical_use": False,
    }

    save_json(preprocessing_json, preprocessing_data)

    if segmentation_mode != "AUTO_SEGMENTATION":
        blockers.append("ONLY_AUTO_SEGMENTATION_IMPLEMENTED_IN_THIS_VERSION")

    if segmentation_tool != "TotalSegmentator":
        blockers.append("ONLY_TOTALSEGMENTATOR_IMPLEMENTED_IN_THIS_VERSION")

    if blockers:
        segmentation_status = "SEGMENTATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
    else:
        seg_run = run_totalsegmentator(segmentation_input, raw_segmentation_output_dir)

        write_text(
            output_dir / "totalsegmentator_stdout.txt",
            seg_run.get("stdout", "")
        )
        write_text(
            output_dir / "totalsegmentator_stderr.txt",
            seg_run.get("stderr", "")
        )

        if not seg_run.get("tool_available", False):
            segmentation_status = "SEGMENTATION_TOOL_NOT_AVAILABLE"
            blockers.append("TOTALSEGMENTATOR_COMMAND_NOT_FOUND")
            next_agent = "USER_ACTION_REQUIRED"
        elif not seg_run.get("success", False):
            segmentation_status = "SEGMENTATION_FAIL"
            blockers.append("TOTALSEGMENTATOR_RUN_FAILED")
            next_agent = "USER_ACTION_REQUIRED"
        else:
            found_mask = find_target_mask(raw_segmentation_output_dir, segmentation_target)

            if found_mask is None:
                segmentation_status = "SEGMENTATION_FAIL"
                blockers.append("TARGET_MASK_NOT_FOUND_IN_TOTALSEGMENTATOR_OUTPUT")
                next_agent = "USER_ACTION_REQUIRED"
            else:
                copy_mask_to_standard_path(found_mask, segmentation_mask_path)
                segmentation_status = "SEGMENTATION_WARNING" if warnings else "SEGMENTATION_PASS"
                next_agent = "SEGMENTATION_VALIDATION_AGENT"

    result = SegmentationResult(
        case_id=case_id,
        segmentation_status=segmentation_status,
        preprocessing_required=preprocessing_required,
        resampling_applied=resampling_applied,
        original_spacing=original_spacing,
        target_spacing=target_spacing,
        resampled_spacing=resampled_spacing,
        segmentation_mode=segmentation_mode,
        segmentation_tool=segmentation_tool,
        segmentation_target=segmentation_target,
        original_volume_path=str(original_volume_path),
        resampled_volume_path=str(resampled_volume_path) if resampling_applied else "",
        segmentation_mask_path=str(segmentation_mask_path) if segmentation_mask_path.exists() else "",
        raw_segmentation_output_dir=str(raw_segmentation_output_dir),
        next_agent=next_agent,
        human_review_required=True,
        warnings=warnings,
        blockers=blockers,
        preprocessing_json=str(preprocessing_json),
        output_json=str(output_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_data_intake_json"] = str(data_intake_path)
    data["source_image_quality_json"] = str(image_quality_path)
    data["source_target_understanding_json"] = str(target_path)

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "segmentation_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Durum: {segmentation_status}\n"
        f"- Hedef: {segmentation_target}\n"
        f"- Original spacing: {original_spacing}\n"
        f"- Target spacing: {target_spacing}\n"
        f"- Resampling applied: {resampling_applied}\n"
        f"- Tool: {segmentation_tool}\n"
        f"- Mask path: {str(segmentation_mask_path) if segmentation_mask_path.exists() else ''}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-05 Segmentation / Preprocessing Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-intake-json", default=None)
    parser.add_argument("--image-quality-json", default=None)
    parser.add_argument("--target-understanding-json", default=None)

    args = parser.parse_args()

    result = run_segmentation(SegmentationInput(
        case_id=args.case_id,
        data_intake_json=args.data_intake_json,
        image_quality_json=args.image_quality_json,
        target_understanding_json=args.target_understanding_json,
        reuse_existing=True,
    ))

    print("AGENT_05_SEGMENTATION_COMPLETED=True")
    print(f"SEGMENTATION_STATUS={result.segmentation_status}")
    print(f"PREPROCESSING_REQUIRED={result.preprocessing_required}")
    print(f"RESAMPLING_APPLIED={result.resampling_applied}")
    print(f"ORIGINAL_SPACING={result.original_spacing}")
    print(f"TARGET_SPACING={result.target_spacing}")
    print(f"RESAMPLED_SPACING={result.resampled_spacing}")
    print(f"SEGMENTATION_TARGET={result.segmentation_target}")
    print(f"SEGMENTATION_TOOL={result.segmentation_tool}")
    print(f"SEGMENTATION_MASK_PATH={result.segmentation_mask_path}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"WARNINGS={result.warnings}")
    print(f"BLOCKERS={result.blockers}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()

