from pathlib import Path
import pydicom
import SimpleITK as sitk
import numpy as np


def list_files(input_path: str):
    p = Path(input_path)

    if not p.exists():
        return []

    if p.is_file():
        return [p]

    return [x for x in p.rglob("*") if x.is_file()]


def read_dicom_header(path: Path):
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        required = ["SOPClassUID", "StudyInstanceUID", "SeriesInstanceUID", "Modality"]
        is_dicom = any(hasattr(ds, tag) for tag in required)
        if not is_dicom:
            return None
        return ds
    except Exception:
        return None


def safe_float(value, default=0.0):
    try:
        if isinstance(value, (list, tuple)):
            value = value[0]
        return float(value)
    except Exception:
        return default


def scan_dicom_headers(input_path: str):
    files = list_files(input_path)
    rows = []

    for f in files:
        ds = read_dicom_header(f)
        if ds is None:
            continue

        pixel_spacing = getattr(ds, "PixelSpacing", ["", ""])
        spacing_x = safe_float(pixel_spacing[0]) if len(pixel_spacing) > 0 else 0.0
        spacing_y = safe_float(pixel_spacing[1]) if len(pixel_spacing) > 1 else 0.0

        row = {
            "path": str(f),
            "modality": str(getattr(ds, "Modality", "")),
            "rows": int(getattr(ds, "Rows", 0)) if hasattr(ds, "Rows") else 0,
            "columns": int(getattr(ds, "Columns", 0)) if hasattr(ds, "Columns") else 0,
            "pixel_spacing_x": spacing_x,
            "pixel_spacing_y": spacing_y,
            "slice_thickness": safe_float(getattr(ds, "SliceThickness", 0.0)),
            "instance_number": str(getattr(ds, "InstanceNumber", "")),
            "series_uid": str(getattr(ds, "SeriesInstanceUID", "")),
        }

        rows.append(row)

    return rows


def try_read_volume_with_simpleitk(input_path: str):
    try:
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(input_path)

        if not series_ids:
            return {
                "success": False,
                "error": "NO_GDCM_SERIES_FOUND",
                "size": "",
                "spacing": "",
                "intensity_min": 0.0,
                "intensity_max": 0.0,
                "intensity_mean": 0.0,
            }

        series_files = reader.GetGDCMSeriesFileNames(input_path, series_ids[0])
        reader.SetFileNames(series_files)
        image = reader.Execute()

        arr = sitk.GetArrayFromImage(image)

        return {
            "success": True,
            "error": "",
            "size": "x".join(str(x) for x in image.GetSize()),
            "spacing": ",".join(str(round(float(x), 6)) for x in image.GetSpacing()),
            "intensity_min": float(np.min(arr)),
            "intensity_max": float(np.max(arr)),
            "intensity_mean": float(np.mean(arr)),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
            "size": "",
            "spacing": "",
            "intensity_min": 0.0,
            "intensity_max": 0.0,
            "intensity_mean": 0.0,
        }


def make_quality_profile(input_path: str):
    rows = scan_dicom_headers(input_path)
    volume = try_read_volume_with_simpleitk(input_path)

    slice_count = len(rows)

    if rows:
        first = rows[0]
        image_size = f'{first["columns"]}x{first["rows"]}'
        sx = first["pixel_spacing_x"]
        sy = first["pixel_spacing_y"]
        st = first["slice_thickness"]
        spacing = f"{sx},{sy},{st}"
    else:
        image_size = ""
        sx = sy = st = 0.0
        spacing = ""

    smallest_inplane = min([v for v in [sx, sy] if v > 0], default=0.0)

    if smallest_inplane > 0 and st > 0:
        voxel_anisotropy = round(max(st / smallest_inplane, smallest_inplane / st), 6)
    else:
        voxel_anisotropy = 0.0

    warnings = []
    blockers = []

    if slice_count == 0:
        blockers.append("NO_READABLE_DICOM_HEADERS")

    if slice_count < 2:
        warnings.append("SLICE_COUNT_LOW")

    if sx <= 0 or sy <= 0:
        warnings.append("PIXEL_SPACING_MISSING_OR_INVALID")

    if st <= 0:
        warnings.append("SLICE_THICKNESS_MISSING_OR_INVALID")

    if voxel_anisotropy >= 4:
        warnings.append("HIGH_VOXEL_ANISOTROPY")

    if not volume["success"]:
        warnings.append("SIMPLEITK_VOLUME_READ_WARNING=" + volume["error"])

    return {
        "rows": rows,
        "series_read_success": volume["success"],
        "slice_count": slice_count,
        "image_size": image_size,
        "spacing": volume["spacing"] if volume["spacing"] else spacing,
        "slice_thickness": float(st),
        "voxel_anisotropy": float(voxel_anisotropy),
        "intensity_min": float(volume["intensity_min"]),
        "intensity_max": float(volume["intensity_max"]),
        "intensity_mean": float(volume["intensity_mean"]),
        "warnings": warnings,
        "blockers": blockers,
    }
