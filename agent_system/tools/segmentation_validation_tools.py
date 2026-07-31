from pathlib import Path
import numpy as np
import SimpleITK as sitk


def path_exists(path_text: str) -> bool:
    if not path_text:
        return False
    return Path(path_text).exists()


def read_image(path_text: str):
    try:
        image = sitk.ReadImage(str(path_text))
        return image, True, ""
    except Exception as e:
        return None, False, f"{type(e).__name__}: {e}"


def tuple_to_string(values):
    return ",".join(str(round(float(x), 6)) for x in values)


def size_to_string(values):
    return "x".join(str(int(x)) for x in values)


def spacing_matches(a, b, tolerance=1e-4) -> bool:
    if len(a) != len(b):
        return False

    for x, y in zip(a, b):
        if abs(float(x) - float(y)) > tolerance:
            return False

    return True


def calculate_mask_profile(mask_image, reference_image):
    mask_arr = sitk.GetArrayFromImage(mask_image)

    foreground = mask_arr > 0
    voxel_count = int(np.count_nonzero(foreground))
    mask_is_empty = voxel_count == 0

    spacing = mask_image.GetSpacing()
    voxel_volume_mm3 = float(spacing[0] * spacing[1] * spacing[2])
    mask_volume_mm3 = float(voxel_count * voxel_volume_mm3)
    mask_volume_cm3 = float(mask_volume_mm3 / 1000.0)

    mask_size = mask_image.GetSize()
    reference_size = reference_image.GetSize()

    mask_spacing = mask_image.GetSpacing()
    reference_spacing = reference_image.GetSpacing()

    return {
        "mask_is_empty": mask_is_empty,
        "mask_voxel_count": voxel_count,
        "mask_volume_mm3": round(mask_volume_mm3, 6),
        "mask_volume_cm3": round(mask_volume_cm3, 6),
        "mask_size": size_to_string(mask_size),
        "reference_size": size_to_string(reference_size),
        "mask_spacing": tuple_to_string(mask_spacing),
        "reference_spacing": tuple_to_string(reference_spacing),
        "image_mask_size_match": mask_size == reference_size,
        "image_mask_spacing_match": spacing_matches(mask_spacing, reference_spacing),
    }


def broad_volume_warning(mask_volume_cm3: float) -> bool:
    """
    Geniş teknik aralık kontrolü.
    Klinik tanı veya anatomik doğruluk kararı değildir.
    Amaç, aşırı küçük/aşırı büyük maskeleri yakalamaktır.
    """
    if mask_volume_cm3 < 1.0:
        return True

    if mask_volume_cm3 > 250.0:
        return True

    return False
