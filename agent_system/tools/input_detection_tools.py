from pathlib import Path
import pydicom


def list_files(input_path: str):
    p = Path(input_path)

    if not p.exists():
        return []

    if p.is_file():
        return [p]

    return [x for x in p.rglob("*") if x.is_file()]


def has_nifti_extension(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".nii") or name.endswith(".nii.gz")


def looks_like_manual_mask(path: Path) -> bool:
    text = str(path).lower()
    return has_nifti_extension(path) and (
        "mask" in text
        or "seg" in text
        or "label" in text
        or "annotation" in text
    )


def looks_like_dicom(path: Path) -> bool:
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        required_tags = [
            "SOPClassUID",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "Modality",
        ]
        return any(hasattr(ds, tag) for tag in required_tags)
    except Exception:
        return False


def detect_input_type(input_path: str):
    p = Path(input_path)

    if not p.exists():
        return {
            "detected_input_type": "MISSING",
            "file_count": 0,
            "warnings": [],
            "blockers": ["INPUT_PATH_NOT_FOUND"],
        }

    files = list_files(input_path)

    if len(files) == 0:
        return {
            "detected_input_type": "MISSING",
            "file_count": 0,
            "warnings": [],
            "blockers": ["EMPTY_FOLDER"],
        }

    dicom_files = []
    nifti_files = []
    mask_files = []
    unsupported_files = []

    for f in files:
        if looks_like_manual_mask(f):
            mask_files.append(f)
        elif has_nifti_extension(f):
            nifti_files.append(f)
        elif looks_like_dicom(f):
            dicom_files.append(f)
        else:
            unsupported_files.append(f)

    detected = []

    if dicom_files:
        detected.append("DICOM")
    if nifti_files:
        detected.append("NIFTI")
    if mask_files:
        detected.append("MANUAL_MASK")

    warnings = []

    if unsupported_files:
        warnings.append(f"UNSUPPORTED_FILE_COUNT={len(unsupported_files)}")

    if len(detected) == 0:
        return {
            "detected_input_type": "UNSUPPORTED",
            "file_count": len(files),
            "warnings": warnings,
            "blockers": ["NO_SUPPORTED_MEDICAL_IMAGE_FOUND"],
        }

    if len(detected) > 1:
        return {
            "detected_input_type": "MULTIPLE_INPUT_TYPES",
            "file_count": len(files),
            "warnings": warnings + [f"DETECTED_TYPES={','.join(detected)}"],
            "blockers": ["MULTIPLE_INPUT_TYPES_FOUND"],
        }

    return {
        "detected_input_type": detected[0],
        "file_count": len(files),
        "warnings": warnings,
        "blockers": [],
    }


def next_agent_for_input_type(detected_input_type: str):
    if detected_input_type == "DICOM":
        return "DICOM_SAFETY_AGENT"

    if detected_input_type == "NIFTI":
        return "IMAGE_QUALITY_AGENT"

    if detected_input_type == "MANUAL_MASK":
        return "SEGMENTATION_VALIDATION_AGENT"

    if detected_input_type == "MULTIPLE_INPUT_TYPES":
        return "USER_SELECTION_REQUIRED"

    return "USER_ACTION_REQUIRED"
