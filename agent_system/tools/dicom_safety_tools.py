from pathlib import Path
import pydicom


PHI_TAGS = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "OtherPatientIDs",
    "OtherPatientNames",
    "ReferringPhysicianName",
    "OperatorsName",
    "AccessionNumber",
    "InstitutionName",
]


SAFE_WORDS = [
    "",
    "anonymous",
    "anon",
    "anonymized",
    "deidentified",
    "de-identified",
    "test",
    "none",
    "null",
]


def list_files(input_path: str):
    p = Path(input_path)

    if not p.exists():
        return []

    if p.is_file():
        return [p]

    return [x for x in p.rglob("*") if x.is_file()]


def safe_string(value):
    try:
        return str(value).strip()
    except Exception:
        return ""


def looks_safe_placeholder(value: str):
    v = value.lower().strip()

    if v in SAFE_WORDS:
        return True

    for word in SAFE_WORDS:
        if word and word in v:
            return True

    return False


def read_dicom_header(path: Path):
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        required = ["SOPClassUID", "StudyInstanceUID", "SeriesInstanceUID", "Modality"]
        is_dicom = any(hasattr(ds, tag) for tag in required)

        if not is_dicom:
            return None, False, "not a DICOM-like header"

        return ds, True, ""

    except Exception as e:
        return None, False, f"{type(e).__name__}: {e}"


def scan_single_dicom(path: Path):
    ds, readable, error = read_dicom_header(path)

    row = {
        "path": str(path),
        "readable": readable,
        "error": error,
        "modality": "",
        "phi_tags_found": "",
        "burned_in_annotation": "",
        "recognizable_visual_features": "",
    }

    if not readable or ds is None:
        return row

    row["modality"] = safe_string(getattr(ds, "Modality", ""))

    phi_found = []

    for tag in PHI_TAGS:
        if hasattr(ds, tag):
            value = safe_string(getattr(ds, tag))
            if value and not looks_safe_placeholder(value):
                phi_found.append(tag)

    row["phi_tags_found"] = ";".join(phi_found)

    if hasattr(ds, "BurnedInAnnotation"):
        row["burned_in_annotation"] = safe_string(getattr(ds, "BurnedInAnnotation"))

    if hasattr(ds, "RecognizableVisualFeatures"):
        row["recognizable_visual_features"] = safe_string(getattr(ds, "RecognizableVisualFeatures"))

    return row


def scan_dicom_folder(input_path: str):
    files = list_files(input_path)
    rows = []

    for f in files:
        rows.append(scan_single_dicom(f))

    readable = [r for r in rows if r["readable"]]
    modalities = sorted(set(r["modality"] for r in readable if r["modality"]))

    phi_risk = any(r["phi_tags_found"] for r in readable)

    burned_risk = any(
        str(r["burned_in_annotation"]).upper() == "YES"
        or str(r["recognizable_visual_features"]).upper() == "YES"
        for r in readable
    )

    return {
        "rows": rows,
        "file_count": len(files),
        "readable_count": len(readable),
        "modalities": modalities,
        "phi_risk_detected": phi_risk,
        "burned_in_annotation_risk": burned_risk,
    }
