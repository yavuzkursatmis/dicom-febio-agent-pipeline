from pathlib import Path
import json
import shutil
import subprocess
import re

import SimpleITK as sitk

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_config():
    path = ROOT / "agent_system" / "configs" / "segmentation_config.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_dicom_series(input_path: str):
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(input_path))

    if not series_ids:
        raise RuntimeError("NO_DICOM_SERIES_FOUND")

    series_files = reader.GetGDCMSeriesFileNames(str(input_path), series_ids[0])
    reader.SetFileNames(series_files)
    image = reader.Execute()

    return image, series_files


def save_nifti(image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(path), True)


def spacing_to_string(spacing):
    return ",".join(str(round(float(x), 6)) for x in spacing)


def parse_spacing_string(spacing_text: str):
    if not spacing_text:
        return []

    values = []
    for x in str(spacing_text).split(","):
        try:
            values.append(float(x.strip()))
        except Exception:
            pass

    return values


def should_resample(image_quality: dict, config: dict):
    warnings = image_quality.get("warnings", [])
    anisotropy = float(image_quality.get("voxel_anisotropy", 0.0))
    threshold = float(config.get("anisotropy_warning_threshold", 4.0))

    if "HIGH_VOXEL_ANISOTROPY" in warnings:
        return True

    if anisotropy >= threshold:
        return True

    return False


def resample_image(image, target_spacing):
    original_spacing = image.GetSpacing()
    original_size = image.GetSize()

    new_size = [
        int(round(original_size[i] * (original_spacing[i] / target_spacing[i])))
        for i in range(3)
    ]

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing(target_spacing)
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetInterpolator(sitk.sitkLinear)

    return resampler.Execute(image)


def command_exists(command_name: str):
    try:
        result = subprocess.run(
            [command_name, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
        )
        return result.returncode in [0, 1]
    except Exception:
        return False


def run_totalsegmentator(input_nifti: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    command_candidates = [
        "TotalSegmentator",
        "totalsegmentator",
    ]

    selected_command = None

    for cmd in command_candidates:
        if command_exists(cmd):
            selected_command = cmd
            break

    if selected_command is None:
        return {
            "success": False,
            "tool_available": False,
            "command": "",
            "stdout": "",
            "stderr": "TotalSegmentator command not found.",
        }

    cmd = [
        selected_command,
        "-i",
        str(input_nifti),
        "-o",
        str(output_dir),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return {
        "success": result.returncode == 0,
        "tool_available": True,
        "command": " ".join(cmd),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def normalize_target_name(target: str):
    t = str(target).strip().lower()
    t = t.replace("ı", "i")
    t = t.replace("ğ", "g")
    t = t.replace("ü", "u")
    t = t.replace("ş", "s")
    t = t.replace("ö", "o")
    t = t.replace("ç", "c")
    return t


def vertebra_code_from_target(target: str):
    t = normalize_target_name(target)
    match = re.search(r"\b(l[1-5]|t[1-9]|t1[0-2]|c[1-7])\b", t)
    if match:
        return match.group(1).upper()
    return ""


def find_target_mask(raw_output_dir: Path, segmentation_target: str):
    vertebra_code = vertebra_code_from_target(segmentation_target)

    if not vertebra_code:
        return None

    candidates = []

    for path in raw_output_dir.rglob("*.nii.gz"):
        name = path.name.lower()

        if vertebra_code.lower() in name and "vertebra" in name:
            candidates.append(path)

    if candidates:
        return candidates[0]

    for path in raw_output_dir.rglob("*.nii.gz"):
        name = path.name.lower()

        if vertebra_code.lower() in name:
            candidates.append(path)

    if candidates:
        return candidates[0]

    expected = raw_output_dir / f"vertebrae_{vertebra_code}.nii.gz"
    if expected.exists():
        return expected

    return None


def copy_mask_to_standard_path(source_mask: Path, target_mask: Path):
    target_mask.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(source_mask), str(target_mask))


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

