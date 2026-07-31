from pathlib import Path
import json
import csv
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def export_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def default_package_path(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "08_material_review"
    return {
        "json": out_dir / "APPROVED_MATERIAL_LAW_VALIDATION_RESULT.json",
        "csv": out_dir / "APPROVED_MATERIAL_LAW_VALIDATION_REPORT.csv",
    }


def compute_density(intercept: float, slope: float, hu: float):
    return intercept + slope * hu


def compute_ez(coefficient: float, exponent: float, density: float):
    if density <= 0:
        return None
    return coefficient * (density ** exponent)


def parse_poisson_map(poisson_relations):
    values = {}

    for relation in poisson_relations:
        if "variable" in relation:
            values[relation["variable"]] = relation.get("value")

        if "variables" in relation:
            for variable in relation.get("variables", []):
                values[variable] = relation.get("value")

    return values


def parse_directional_scales(directional_relations):
    values = {}

    for relation in directional_relations:
        if relation.get("relation_type") != "directional_modulus_scaling":
            continue

        scale = relation.get("scale_factor")

        for variable in relation.get("variables", []):
            values[variable] = scale

    return values


def parse_shear_scales(shear_relations):
    values = {}
    warnings = []

    for relation in shear_relations:
        scale = relation.get("scale_factor")

        variables = []
        if "variable" in relation:
            variables.append(relation.get("variable"))

        if "variables" in relation:
            variables.extend(relation.get("variables", []))

        if relation.get("warning"):
            warnings.append("RAW_SHEAR_RELATION_WARNING:" + relation.get("warning"))

        for variable in variables:
            if not variable:
                continue

            if variable in values and values[variable] != scale:
                warnings.append(
                    f"SHEAR_SCALE_CONFLICT:{variable}:{values[variable]}_vs_{scale}"
                )

            values[variable] = scale

    return values, warnings


def orthotropic_stability_check(ex, ey, ez, nu_xy, nu_xz, nu_yz):
    """
    Engineering constants stability check for orthotropic elastic material.

    Reciprocal Poisson values:
    nu_yx = nu_xy * Ey / Ex
    nu_zx = nu_xz * Ez / Ex
    nu_zy = nu_yz * Ez / Ey

    Stability determinant condition:
    1 - nu_xy*nu_yx - nu_yz*nu_zy - nu_xz*nu_zx - 2*nu_yx*nu_zy*nu_xz > 0
    """

    if ex <= 0 or ey <= 0 or ez <= 0:
        return {
            "stable": False,
            "stability_value": None,
            "reason": "NON_POSITIVE_MODULUS",
        }

    nu_yx = nu_xy * ey / ex
    nu_zx = nu_xz * ez / ex
    nu_zy = nu_yz * ez / ey

    stability_value = (
        1
        - nu_xy * nu_yx
        - nu_yz * nu_zy
        - nu_xz * nu_zx
        - 2 * nu_yx * nu_zy * nu_xz
    )

    return {
        "stable": stability_value > 0,
        "stability_value": stability_value,
        "nu_yx": nu_yx,
        "nu_zx": nu_zx,
        "nu_zy": nu_zy,
        "reason": "PASS" if stability_value > 0 else "ORTHOTROPIC_STABILITY_CONDITION_FAILED",
    }


def validate_material_law(case_id: str):
    package_path = default_package_path(case_id)
    paths = output_paths(case_id)

    blockers = []
    warnings = []
    report_rows = []

    if not package_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "validation_status": "MATERIAL_LAW_PACKAGE_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "blockers": ["MATERIAL_LAW_PACKAGE_NOT_FOUND"],
            "warnings": [],
            "clinical_use": False,
        }
        save_json(paths["json"], result)
        return result

    package = load_json(package_path)

    if package.get("status") != "MATERIAL_LAW_STRUCTURED":
        blockers.append("MATERIAL_LAW_PACKAGE_STATUS_NOT_STRUCTURED")

    if package.get("ready_for_material_law_validation") is not True:
        blockers.append("PACKAGE_NOT_READY_FOR_MATERIAL_LAW_VALIDATION")

    law = package.get("structured_law", {})

    hu_density = law.get("hu_to_density", {})
    density_elastic = law.get("density_to_elastic_modulus", {})
    directional_relations = law.get("directional_modulus_relations", [])
    shear_relations = law.get("shear_modulus_relations", [])
    poisson_relations = law.get("poisson_relations", [])

    if not hu_density.get("found"):
        blockers.append("HU_TO_DENSITY_EQUATION_MISSING")

    if not density_elastic.get("found"):
        blockers.append("DENSITY_TO_ELASTIC_MODULUS_EQUATION_MISSING")

    if blockers:
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "validation_status": "MATERIAL_LAW_VALIDATION_FAIL",
            "next_agent": "USER_ACTION_REQUIRED",
            "source_material_law_package": str(package_path),
            "blockers": blockers,
            "warnings": warnings,
            "clinical_use": False,
        }
        save_json(paths["json"], result)
        export_csv(paths["csv"], report_rows)
        return result

    intercept = hu_density.get("intercept")
    slope = hu_density.get("slope")
    coefficient = density_elastic.get("coefficient")
    exponent = density_elastic.get("exponent")

    if intercept is None or slope is None:
        blockers.append("HU_TO_DENSITY_COEFFICIENTS_MISSING")

    if coefficient is None or exponent is None:
        blockers.append("DENSITY_TO_ELASTIC_COEFFICIENTS_MISSING")

    if slope is not None and slope <= 0:
        blockers.append("HU_TO_DENSITY_SLOPE_NOT_POSITIVE")

    if coefficient is not None and coefficient <= 0:
        blockers.append("ELASTIC_MODULUS_COEFFICIENT_NOT_POSITIVE")

    if exponent is not None and exponent <= 0:
        blockers.append("ELASTIC_MODULUS_EXPONENT_NOT_POSITIVE")

    directional_scales = parse_directional_scales(directional_relations)

    ex_scale = directional_scales.get("Ex")
    ey_scale = directional_scales.get("Ey")

    if ex_scale is None or ey_scale is None:
        warnings.append("EX_OR_EY_DIRECTIONAL_SCALE_MISSING")
    else:
        if ex_scale <= 0 or ey_scale <= 0:
            blockers.append("DIRECTIONAL_MODULUS_SCALE_NOT_POSITIVE")

    shear_scales, shear_warnings = parse_shear_scales(shear_relations)
    warnings.extend(shear_warnings)

    if not shear_scales:
        warnings.append("SHEAR_MODULUS_RELATIONS_MISSING_OR_NOT_PARSED")

    poisson_map = parse_poisson_map(poisson_relations)

    required_poisson = ["nu_xy", "nu_xz", "nu_yz"]
    for key in required_poisson:
        if key not in poisson_map:
            warnings.append(f"POISSON_VALUE_MISSING:{key}")
        else:
            value = poisson_map[key]
            if value is None or not (0 < float(value) < 0.5):
                blockers.append(f"POISSON_VALUE_OUT_OF_RANGE:{key}:{value}")

    sample_hu_values = [0, 100, 250, 500, 1000, 1500, 2000]

    sample_results = []

    for hu in sample_hu_values:
        density = compute_density(intercept, slope, hu)
        ez = compute_ez(coefficient, exponent, density)

        ex = ez * ex_scale if ez is not None and ex_scale is not None else None
        ey = ez * ey_scale if ez is not None and ey_scale is not None else None

        row = {
            "HU": hu,
            "apparent_density_g_cm3": density,
            "Ez_MPa": ez,
            "Ex_MPa": ex,
            "Ey_MPa": ey,
        }

        sample_results.append(row)

        if density <= 0:
            blockers.append(f"NON_POSITIVE_DENSITY_AT_HU:{hu}")

        if ez is None or ez <= 0:
            blockers.append(f"NON_POSITIVE_EZ_AT_HU:{hu}")

        if ez is not None and ez > 50000:
            warnings.append(f"VERY_HIGH_EZ_AT_HU:{hu}:{round(ez, 3)}")

        if ex is not None and ex <= 0:
            blockers.append(f"NON_POSITIVE_EX_AT_HU:{hu}")

        if ey is not None and ey <= 0:
            blockers.append(f"NON_POSITIVE_EY_AT_HU:{hu}")

        report_rows.append(row)

    stability_results = []

    if (
        ex_scale is not None
        and ey_scale is not None
        and all(k in poisson_map for k in required_poisson)
    ):
        for sample in sample_results:
            ez = sample.get("Ez_MPa")
            ex = sample.get("Ex_MPa")
            ey = sample.get("Ey_MPa")

            if ez is None or ex is None or ey is None:
                continue

            stability = orthotropic_stability_check(
                ex=ex,
                ey=ey,
                ez=ez,
                nu_xy=float(poisson_map["nu_xy"]),
                nu_xz=float(poisson_map["nu_xz"]),
                nu_yz=float(poisson_map["nu_yz"]),
            )

            stability_row = {
                "HU": sample["HU"],
                "orthotropic_stable": stability["stable"],
                "stability_value": stability["stability_value"],
                "nu_yx": stability.get("nu_yx"),
                "nu_zx": stability.get("nu_zx"),
                "nu_zy": stability.get("nu_zy"),
                "reason": stability["reason"],
            }

            stability_results.append(stability_row)

            if not stability["stable"]:
                blockers.append(f"ORTHOTROPIC_STABILITY_FAILED_AT_HU:{sample['HU']}")

    else:
        warnings.append("ORTHOTROPIC_STABILITY_CHECK_SKIPPED_DUE_TO_MISSING_CONSTANTS")

    # Remove duplicate messages while preserving order.
    blockers = list(dict.fromkeys(blockers))
    warnings = list(dict.fromkeys(warnings))

    if blockers:
        validation_status = "MATERIAL_LAW_VALIDATION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        approved_for_agent08 = False
    elif warnings:
        validation_status = "MATERIAL_LAW_VALIDATION_WARNING"
        next_agent = "HUMAN_REVIEW_GATE"
        approved_for_agent08 = False
    else:
        validation_status = "MATERIAL_LAW_VALIDATION_PASS"
        next_agent = "AGENT_08_GEOMETRY_MESH_PREPARATION"
        approved_for_agent08 = True

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "validation_status": validation_status,
        "next_agent": next_agent,
        "approved_for_agent08": approved_for_agent08,
        "source_material_law_package": str(package_path),
        "material_law_package_id": package.get("material_law_package_id", ""),
        "approved_law_candidate_id": package.get("approved_law_candidate_id", ""),
        "material_law_family": package.get("material_law_family", ""),
        "hu_to_density": hu_density,
        "density_to_elastic_modulus": density_elastic,
        "directional_scales": directional_scales,
        "shear_scales": shear_scales,
        "poisson_map": poisson_map,
        "sample_hu_validation": sample_results,
        "orthotropic_stability_results": stability_results,
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "No manual values were introduced during validation.",
            "Validation checks parsed agent-derived material-law coefficients only.",
            "If validation passes, Agent-08 may use the approved material-law package.",
            "If warnings exist, human review is required before Agent-08.",
            "Sensitivity analysis remains mandatory downstream."
        ],
    }

    save_json(paths["json"], result)
    export_csv(paths["csv"], report_rows + stability_results)

    return result
