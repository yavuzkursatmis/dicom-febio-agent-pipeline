from pathlib import Path
import json
import csv
import re
import hashlib
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean_text(text: str):
    if not text:
        return ""
    text = str(text)
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("×", "*")
    text = text.replace("ρ", "rho")
    text = text.replace("𝜈", "nu")
    text = text.replace("ν", "nu")

    # PDF text extraction may split words across line breaks:
    # "den- sity" -> "density"
    # "inferior" may also appear as "in- ferior", but here density is critical.
    text = re.sub(r"den\s*-\s*sity", "density", text, flags=re.I)
    text = re.sub(r"Apparent\s+den\s*-\s*sity", "Apparent density", text, flags=re.I)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def norm(text: str):
    return clean_text(text).lower()


def make_package_id(case_id: str, law_candidate_id: str, source_title: str):
    raw = "|".join([case_id, law_candidate_id, source_title])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def parse_density_hu_equation(text: str):
    """
    Example:
    Apparent density (g/cm3) 0.047 + 0.001122HU
    """
    t = clean_text(text)

    patterns = [
        r"apparent density\s*\(?g\s*/?\s*cm3\)?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*HU",
        r"apparent density\s*\(?g\s*/?\s*cm\^?3\)?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*HU",
        r"density\s*\(?g\s*/?\s*cm3\)?\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*HU",
        r"rho\s*=\s*([+-]?\d+(?:\.\d+)?)\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*HU",
    ]

    for p in patterns:
        m = re.search(p, t, flags=re.I)
        if m:
            return {
                "found": True,
                "equation_type": "linear_hu_to_apparent_density",
                "output_variable": "apparent_density",
                "output_unit": "g/cm3",
                "input_variable": "HU",
                "intercept": float(m.group(1)),
                "slope": float(m.group(2)),
                "formula_text": m.group(0),
            }

    return {
        "found": False,
        "equation_type": "",
        "formula_text": "",
    }


def parse_elastic_modulus_equation(text: str):
    """
    Examples:
    Ez=4730 (Apparent density)^1.56
    Ez=4730 (Apparent density)1.56
    Ez=4730 (Apparent den- sity)1.56
    """
    t = clean_text(text)

    density_token = r"(?:apparent\s*density|density|rho)"

    patterns = [
        rf"Ez\s*=\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*\(?\s*{density_token}\s*\)?\s*\^?\s*([+-]?\d+(?:\.\d+)?)",
        rf"E\s*=\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*\(?\s*{density_token}\s*\)?\s*\^?\s*([+-]?\d+(?:\.\d+)?)",
        rf"elastic\s*modulus\s*\(?\s*MPa\s*\)?\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*\(?\s*{density_token}\s*\)?\s*\^?\s*([+-]?\d+(?:\.\d+)?)",
        rf"\[\s*MPa\s*\]\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*\(?\s*{density_token}\s*\)?\s*\^?\s*([+-]?\d+(?:\.\d+)?)",
    ]

    for p in patterns:
        m = re.search(p, t, flags=re.I)
        if m:
            return {
                "found": True,
                "equation_type": "power_law_density_to_elastic_modulus",
                "output_variable": "Ez",
                "output_unit": "MPa",
                "input_variable": "apparent_density",
                "input_unit": "g/cm3",
                "coefficient": float(m.group(1)),
                "exponent": float(m.group(2)),
                "formula_text": m.group(0),
            }

    return {
        "found": False,
        "equation_type": "",
        "formula_text": "",
    }


def parse_directional_modulus_relations(text: str):
    t = clean_text(text)

    relations = []

    m = re.search(r"Ex\s*=\s*Ey\s*=\s*([+-]?\d+(?:\.\d+)?)\s*Ez", t, flags=re.I)
    if m:
        relations.append({
            "found": True,
            "relation_type": "directional_modulus_scaling",
            "variables": ["Ex", "Ey"],
            "reference_variable": "Ez",
            "scale_factor": float(m.group(1)),
            "formula_text": m.group(0),
        })

    return relations


def parse_shear_relations(text: str):
    t = clean_text(text)

    relations = []

    m1 = re.search(r"Gxy\s*=\s*([+-]?\d+(?:\.\d+)?)\s*Ez", t, flags=re.I)
    if m1:
        relations.append({
            "found": True,
            "relation_type": "shear_modulus_scaling",
            "variable": "Gxy",
            "reference_variable": "Ez",
            "scale_factor": float(m1.group(1)),
            "formula_text": m1.group(0),
        })

    m2 = re.search(r"Gx?z\s*=\s*Gy?z\s*=\s*([+-]?\d+(?:\.\d+)?)\s*Ez", t, flags=re.I)
    if m2:
        relations.append({
            "found": True,
            "relation_type": "shear_modulus_scaling",
            "variables": ["Gxz", "Gyz"],
            "reference_variable": "Ez",
            "scale_factor": float(m2.group(1)),
            "formula_text": m2.group(0),
        })

    # Some extracted text may incorrectly repeat Gxy=Gyz. Keep raw relation if detected.
    m3 = re.search(r"Gxy\s*=\s*Gyz\s*=\s*([+-]?\d+(?:\.\d+)?)\s*Ez", t, flags=re.I)
    if m3:
        relations.append({
            "found": True,
            "relation_type": "shear_modulus_scaling_raw_text",
            "variables": ["Gxy", "Gyz"],
            "reference_variable": "Ez",
            "scale_factor": float(m3.group(1)),
            "formula_text": m3.group(0),
            "warning": "Raw extracted relation may need source review because Gxy appears twice in the text."
        })

    return relations


def parse_poisson_relations(text: str):
    t = clean_text(text)

    relations = []

    m1 = re.search(r"nu\s*xy\s*=\s*([+-]?\d+(?:\.\d+)?)", t, flags=re.I)
    if m1:
        relations.append({
            "found": True,
            "variable": "nu_xy",
            "value": float(m1.group(1)),
            "formula_text": m1.group(0),
        })

    m2 = re.search(r"nu\s*xz\s*=\s*nu\s*yz\s*=\s*([+-]?\d+(?:\.\d+)?)", t, flags=re.I)
    if m2:
        relations.append({
            "found": True,
            "variables": ["nu_xz", "nu_yz"],
            "value": float(m2.group(1)),
            "formula_text": m2.group(0),
        })

    return relations


def structure_material_law(case_id: str):
    approval_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_LAW_REVIEW_VALIDATION_RESULT.json"
    source_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_SOURCE_LEVEL_LAW_REVIEW.csv"

    out_json = ROOT / "cases" / case_id / "08_material_review" / "APPROVED_MATERIAL_LAW_PACKAGE.json"

    if not approval_path.exists():
        result = {
            "case_id": case_id,
            "status": "LAW_REVIEW_VALIDATION_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "blockers": ["LAW_REVIEW_VALIDATION_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(out_json, result)
        return result

    approval = load_json(approval_path)

    if approval.get("approval_status") != "AGENT07E_LAW_REVIEW_APPROVED":
        result = {
            "case_id": case_id,
            "status": "LAW_REVIEW_NOT_APPROVED",
            "next_agent": "USER_ACTION_REQUIRED",
            "blockers": ["LAW_REVIEW_NOT_APPROVED"],
            "clinical_use": False,
        }
        save_json(out_json, result)
        return result

    approved_id = approval.get("approved_law_candidate_id", "")

    rows = read_csv(source_csv)

    matched = [
        row for row in rows
        if row.get("representative_law_candidate_id") == approved_id
        and row.get("source_decision") == "SOURCE_HAS_USABLE_EQUATION"
    ]

    if not matched:
        result = {
            "case_id": case_id,
            "status": "APPROVED_LAW_CANDIDATE_SOURCE_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "approved_law_candidate_id": approved_id,
            "blockers": ["APPROVED_LAW_CANDIDATE_SOURCE_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(out_json, result)
        return result

    source = matched[0]
    equation_text = clean_text(" ".join([
        source.get("usable_equations", ""),
        source.get("equation_candidates", ""),
        source.get("formula_snippets", ""),
    ]))

    density_eq = parse_density_hu_equation(equation_text)
    elastic_eq = parse_elastic_modulus_equation(equation_text)
    directional_relations = parse_directional_modulus_relations(equation_text)
    shear_relations = parse_shear_relations(equation_text)
    poisson_relations = parse_poisson_relations(equation_text)

    blockers = []
    warnings = []

    if not density_eq.get("found"):
        blockers.append("HU_TO_DENSITY_EQUATION_NOT_PARSED")

    if not elastic_eq.get("found"):
        blockers.append("DENSITY_TO_ELASTIC_MODULUS_EQUATION_NOT_PARSED")

    if not poisson_relations:
        warnings.append("POISSON_RELATIONS_NOT_PARSED_OR_REQUIRE_SOURCE_REVIEW")

    if not directional_relations:
        warnings.append("DIRECTIONAL_MODULUS_RELATIONS_NOT_PARSED_OR_REQUIRE_SOURCE_REVIEW")

    if not shear_relations:
        warnings.append("SHEAR_RELATIONS_NOT_PARSED_OR_REQUIRE_SOURCE_REVIEW")

    if blockers:
        status = "MATERIAL_LAW_STRUCTURING_INCOMPLETE"
        next_agent = "USER_ACTION_REQUIRED"
        ready_for_validation = False
    else:
        status = "MATERIAL_LAW_STRUCTURED"
        next_agent = "MATERIAL_LAW_VALIDATION_AGENT"
        ready_for_validation = True

    package_id = make_package_id(
        case_id=case_id,
        law_candidate_id=approved_id,
        source_title=source.get("source_title", "")
    )

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "material_law_package_id": package_id,
        "ready_for_material_law_validation": ready_for_validation,
        "approved_law_candidate_id": approved_id,
        "material_domain": "bone",
        "anatomical_region": "T1 vertebra",
        "target_family": "spine_vertebra",
        "material_law_family": "density_hu_based_orthotropic_linear_elastic",
        "source": {
            "source_title": source.get("source_title", ""),
            "source_url": source.get("source_url", ""),
            "source_doi": source.get("source_doi", ""),
            "source_pmid": source.get("source_pmid", ""),
            "source_key": source.get("source_key", ""),
        },
        "raw_equation_text": equation_text,
        "structured_law": {
            "hu_to_density": density_eq,
            "density_to_elastic_modulus": elastic_eq,
            "directional_modulus_relations": directional_relations,
            "shear_modulus_relations": shear_relations,
            "poisson_relations": poisson_relations,
        },
        "downstream_notes": [
            "This package is not yet a FEBio material file.",
            "This package must be validated before geometry/mesh/FEBio stages.",
            "HU calibration and patient-specific CT calibration limitations must be documented.",
            "Sensitivity analysis remains mandatory."
        ],
        "clinical_use": False,
        "warnings": warnings,
        "blockers": blockers,
        "rules": [
            "No manual material values were entered.",
            "No manual equations were entered.",
            "All parsed coefficients originate from the approved agent-derived source text.",
            "GEOMETRY_AGENT remains blocked until MATERIAL_LAW_VALIDATION_AGENT passes."
        ]
    }

    save_json(out_json, result)
    return result
