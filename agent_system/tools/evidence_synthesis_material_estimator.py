from pathlib import Path
import json
import csv
import re
import hashlib
from datetime import datetime
from statistics import median
from typing import List, Dict, Any, Optional

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_material_selection_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_SELECTION_RESULT.json"


def default_resolved_literature_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_RESOLVED.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "08_material_review"
    return {
        "result_json": out_dir / "AGENT07D_EVIDENCE_SYNTHESIS_RESULT.json",
        "property_candidates_csv": out_dir / "AGENT07D_PROPERTY_CANDIDATES.csv",
        "property_summary_csv": out_dir / "AGENT07D_PROPERTY_SUMMARY.csv",
        "review_json": out_dir / "AGENT07D_SYNTHESIS_REVIEW.json",
    }


def clean_text(text: str):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text: str):
    text = clean_text(text).lower()
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for a, b in repl.items():
        text = text.replace(a, b)
    return text


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if any(x in t for x in ["femur", "femoral", "hip"]):
        return "femur_hip"

    if any(x in t for x in ["tibia", "tibial"]):
        return "tibia"

    if "cartilage" in t or "meniscus" in t:
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t:
        return "ligament"

    if "muscle" in t:
        return "muscle"

    if "implant" in t or "ti6al4v" in t or "titanium" in t or "tantalum" in t:
        return "implant_material"

    return normalize(material_domain or "unknown")


def positive_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)
    terms = set()

    for token in re.split(r"[^a-zA-Z0-9]+", anatomical_region):
        if len(token) >= 2:
            terms.add(token.lower())

    domain_terms = {
        "bone": ["bone", "cortical", "cancellous", "trabecular"],
        "cartilage": ["cartilage", "articular cartilage", "meniscus"],
        "tendon": ["tendon"],
        "ligament": ["ligament", "acl", "pcl", "mcl", "lcl"],
        "muscle": ["muscle", "skeletal muscle"],
        "soft_tissue": ["soft tissue", "skin", "adipose"],
        "implant_material": ["implant", "titanium", "tantalum", "ti6al4v"],
    }

    family_terms = {
        "spine_vertebra": ["vertebra", "vertebral", "vertebral body", "spine", "spinal", "thoracic", "cervical", "lumbar", "t1"],
        "femur_hip": ["femur", "femoral", "femoral head", "hip"],
        "tibia": ["tibia", "tibial"],
        "cartilage": ["cartilage", "articular cartilage"],
        "tendon": ["tendon"],
        "ligament": ["ligament"],
        "muscle": ["muscle"],
        "implant_material": ["implant", "titanium", "tantalum", "ti6al4v"],
    }

    for t in domain_terms.get(material_domain, []):
        terms.add(t)

    for t in family_terms.get(family, []):
        terms.add(t)

    return sorted(terms)


def negative_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    animal_terms = [
        "beagle", "canine", "dog", "ovine", "sheep", "bovine", "cow",
        "porcine", "pig", "rat", "rabbit", "mouse", "mice", "murine",
        "goat", "equine", "horse"
    ]

    generic_wrong_engineering = [
        "steel",
        "stainless steel",
        "metal",
        "metals",
        "metallic",
        "aluminium",
        "aluminum",
        "titanium alloy",
        "concrete",
        "soil",
        "bentonite",
        "bridge",
        "overcrossing",
        "fatigue crack growth",
        "crack growth",
        "extended finite element",
        "xfem",
        "linear electric",
        "electric properties",
        "regular polygons"
    ]

    mismatch = []

    if family == "spine_vertebra":
        mismatch = [
            "femoral head", "femur", "femoral", "tibia", "tibial",
            "humerus", "mandible", "skull"
        ]

    return sorted(set(animal_terms + generic_wrong_engineering + mismatch))


def context_window(text: str, start: int, window: int = 800):
    a = max(0, start - window)
    b = min(len(text), start + window)
    return clean_text(text[a:b])


def count_matches(text: str, terms: List[str]):
    t = normalize(text)
    return [term for term in terms if normalize(term) in t]


def context_relevance_score(context: str, anatomical_region: str, material_domain: str):
    positives = count_matches(context, positive_terms(anatomical_region, material_domain))
    negatives = count_matches(context, negative_terms(anatomical_region, material_domain))

    score = 0

    if positives:
        score += min(len(positives), 6)

    if any(x in normalize(context) for x in ["young", "elastic modulus", "modulus of elasticity", "compressive modulus", "tensile modulus"]):
        score += 3

    if "poisson" in normalize(context) or "ν" in context:
        score += 3

    if any(x in normalize(context) for x in ["finite element", "material properties", "linear elastic"]):
        score += 2

    if negatives:
        score -= 6 * len(negatives)

    return score, positives, negatives


def normalize_modulus_to_mpa(value: float, unit: str):
    u = str(unit).replace(" ", "").lower()

    if u == "pa":
        return value / 1_000_000.0

    if u == "kpa":
        return value / 1000.0

    if u == "mpa":
        return value

    if u == "gpa":
        return value * 1000.0

    return value


def make_candidate_id(item: dict):
    raw = "|".join([
        str(item.get("case_id", "")),
        str(item.get("property_name", "")),
        str(item.get("normalized_value", "")),
        str(item.get("normalized_unit", "")),
        str(item.get("source_title", "")),
        str(item.get("source_doi", "")),
        str(item.get("context_excerpt", ""))[:300],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_synthesis_id(case_id: str, material_domain: str, anatomical_region: str, values: dict):
    raw = json.dumps({
        "case_id": case_id,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "values": values,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_property_candidate(
    case_id: str,
    record: dict,
    material_domain: str,
    anatomical_region: str,
    property_name: str,
    raw_value: float,
    raw_unit: str,
    normalized_value: float,
    normalized_unit: str,
    context: str,
    extraction_method: str,
    confidence_score: int,
):
    item = {
        "candidate_id": "",
        "case_id": case_id,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "material_model_family": "linear_elastic_isotropic",
        "property_name": property_name,
        "raw_value": raw_value,
        "raw_unit": raw_unit,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "source": record.get("source", ""),
        "source_title": record.get("title", ""),
        "source_year": record.get("year", ""),
        "source_doi": record.get("doi", ""),
        "source_url": record.get("url", ""),
        "source_pmid": record.get("pmid", ""),
        "source_pmcid": record.get("pmcid", ""),
        "context_excerpt": clean_text(context)[:1600],
        "extraction_method": extraction_method,
        "confidence_score": confidence_score,
        "uncertainty_level": "medium" if confidence_score >= 8 else "high",
        "clinical_use": False,
    }

    item["candidate_id"] = make_candidate_id(item)
    return item


def extract_individual_property_candidates(case_id: str, record: dict, material_domain: str, anatomical_region: str):
    text = clean_text(" ".join([
        record.get("title", ""),
        record.get("abstract", ""),
    ]))

    candidates = []

    if not text:
        return candidates

    e_terms = r"(young'?s modulus|young modulus|elastic modulus|modulus of elasticity|compressive modulus|tensile modulus)"
    number = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    unit = r"(Pa|kPa|MPa|GPa)"

    elastic_patterns = [
        rf"{e_terms}[^0-9]{{0,220}}{number}\s*{unit}",
        rf"{number}\s*{unit}[^.;:]{{0,220}}{e_terms}",
    ]

    for pattern in elastic_patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            ctx = context_window(text, m.start())
            score, positives, negatives = context_relevance_score(ctx, anatomical_region, material_domain)

            if negatives:
                continue

            # For bone-domain extraction, the numeric context must actually mention
            # bone/tissue material context, not only a generic engineering material.
            if material_domain == "bone":
                ctx_norm = normalize(ctx)
                has_bone_context = any(term in ctx_norm for term in [
                    "bone", "cortical", "cancellous", "trabecular",
                    "vertebra", "vertebral", "vertebral body",
                    "spine", "spinal"
                ])
                if not has_bone_context:
                    continue

            values = re.findall(rf"{number}\s*{unit}", m.group(0), flags=re.I)
            if not values:
                continue

            raw_value = float(values[0][0])
            raw_unit = values[0][1]
            mpa = normalize_modulus_to_mpa(raw_value, raw_unit)

            if not (0.0001 <= mpa <= 300000):
                continue

            candidates.append(
                build_property_candidate(
                    case_id=case_id,
                    record=record,
                    material_domain=material_domain,
                    anatomical_region=anatomical_region,
                    property_name="elastic_modulus",
                    raw_value=raw_value,
                    raw_unit=raw_unit,
                    normalized_value=round(mpa, 8),
                    normalized_unit="MPa",
                    context=ctx,
                    extraction_method="evidence_synthesis_individual_elastic_regex",
                    confidence_score=score,
                )
            )

    poisson_patterns = [
        r"(poisson'?s ratio|poisson ratio|ν|nu)[^0-9]{0,180}(0?\.\d+)",
        r"(0?\.\d+)[^.;]{0,180}(poisson'?s ratio|poisson ratio|ν|nu)",
    ]

    for pattern in poisson_patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            ctx = context_window(text, m.start())
            score, positives, negatives = context_relevance_score(ctx, anatomical_region, material_domain)

            if negatives:
                continue

            # For bone-domain extraction, Poisson evidence must also be tied to
            # bone/vertebral tissue context.
            if material_domain == "bone":
                ctx_norm = normalize(ctx)
                has_bone_context = any(term in ctx_norm for term in [
                    "bone", "cortical", "cancellous", "trabecular",
                    "vertebra", "vertebral", "vertebral body",
                    "spine", "spinal"
                ])
                if not has_bone_context:
                    continue

            values = re.findall(r"0?\.\d+", m.group(0))
            values = [float(x) for x in values if 0.0 < float(x) < 0.5]

            if not values:
                continue

            nu = values[0]

            candidates.append(
                build_property_candidate(
                    case_id=case_id,
                    record=record,
                    material_domain=material_domain,
                    anatomical_region=anatomical_region,
                    property_name="poisson_ratio",
                    raw_value=nu,
                    raw_unit="",
                    normalized_value=round(nu, 8),
                    normalized_unit="",
                    context=ctx,
                    extraction_method="evidence_synthesis_individual_poisson_regex",
                    confidence_score=score,
                )
            )

    return candidates


def deduplicate_candidates(candidates: List[Dict[str, Any]]):
    seen = set()
    unique = []

    for c in candidates:
        key = (
            c.get("property_name"),
            c.get("normalized_value"),
            c.get("normalized_unit"),
            c.get("source_doi") or c.get("source_pmid") or c.get("source_url") or c.get("source_title"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(c)

    return unique


def weighted_median(values: List[float], weights: List[float]):
    if not values:
        return None

    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total = sum(weights)

    if total <= 0:
        return median(values)

    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= total / 2:
            return value

    return pairs[-1][0]


def percentile(values: List[float], p: float):
    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)

    if f == c:
        return values[f]

    return values[f] + (values[c] - values[f]) * (k - f)


def summarize_property(candidates: List[Dict[str, Any]], property_name: str):
    selected = [c for c in candidates if c.get("property_name") == property_name]

    if not selected:
        return {
            "property_name": property_name,
            "available": False,
            "count": 0,
            "source_count": 0,
            "proposed_value": None,
            "lower_bound": None,
            "upper_bound": None,
            "q25": None,
            "q75": None,
            "unit": "MPa" if property_name == "elastic_modulus" else "",
            "uncertainty_level": "high",
            "candidate_ids": [],
            "sources": [],
        }

    values = [float(c["normalized_value"]) for c in selected]
    weights = [max(1.0, float(c.get("confidence_score", 1))) for c in selected]

    source_keys = set(
        c.get("source_doi") or c.get("source_pmid") or c.get("source_url") or c.get("source_title")
        for c in selected
    )

    v_min = min(values)
    v_max = max(values)

    if property_name == "elastic_modulus" and v_min > 0:
        range_ratio = v_max / v_min
    else:
        range_ratio = v_max - v_min

    if len(source_keys) < 2:
        uncertainty = "high"
    elif property_name == "elastic_modulus" and range_ratio > 10:
        uncertainty = "high"
    elif property_name == "poisson_ratio" and range_ratio > 0.2:
        uncertainty = "high"
    elif len(source_keys) >= 3:
        uncertainty = "medium"
    else:
        uncertainty = "high"

    proposed = weighted_median(values, weights)

    return {
        "property_name": property_name,
        "available": True,
        "count": len(selected),
        "source_count": len(source_keys),
        "proposed_value": round(float(proposed), 8) if proposed is not None else None,
        "lower_bound": round(float(v_min), 8),
        "upper_bound": round(float(v_max), 8),
        "q25": round(float(percentile(values, 0.25)), 8),
        "q75": round(float(percentile(values, 0.75)), 8),
        "unit": "MPa" if property_name == "elastic_modulus" else "",
        "uncertainty_level": uncertainty,
        "candidate_ids": [c.get("candidate_id") for c in selected],
        "sources": [
            {
                "title": c.get("source_title", ""),
                "doi": c.get("source_doi", ""),
                "url": c.get("source_url", ""),
                "pmid": c.get("source_pmid", ""),
                "pmcid": c.get("source_pmcid", ""),
                "value": c.get("normalized_value"),
                "unit": c.get("normalized_unit", ""),
                "confidence_score": c.get("confidence_score"),
            }
            for c in selected
        ],
    }


def export_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_evidence_synthesis_material_estimator(
    case_id: str,
    material_selection_json: Optional[str] = None,
    resolved_literature_json: Optional[str] = None,
    minimum_sources_per_required_property: int = 2,
):
    material_path = Path(material_selection_json) if material_selection_json else default_material_selection_json(case_id)
    literature_path = Path(resolved_literature_json) if resolved_literature_json else default_resolved_literature_json(case_id)

    paths = output_paths(case_id)

    if not material_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "MATERIAL_SELECTION_RESULT_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "blockers": ["MATERIAL_SELECTION_RESULT_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(paths["result_json"], result)
        return result

    if not literature_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "RESOLVED_LITERATURE_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "blockers": ["RESOLVED_LITERATURE_NOT_FOUND"],
            "clinical_use": False,
        }
        save_json(paths["result_json"], result)
        return result

    material = load_json(material_path)
    literature = load_json(literature_path)

    material_domain = material.get("material_domain", "unknown_requires_review")
    anatomical_region = material.get("anatomical_region", "")

    records = literature.get("records", [])

    all_candidates = []
    for record in records:
        extracted = extract_individual_property_candidates(
            case_id=case_id,
            record=record,
            material_domain=material_domain,
            anatomical_region=anatomical_region,
        )
        all_candidates.extend(extracted)

    all_candidates = deduplicate_candidates(all_candidates)
    all_candidates = sorted(all_candidates, key=lambda x: x.get("confidence_score", 0), reverse=True)

    elastic_summary = summarize_property(all_candidates, "elastic_modulus")
    poisson_summary = summarize_property(all_candidates, "poisson_ratio")

    summaries = [elastic_summary, poisson_summary]

    complete = (
        elastic_summary["available"]
        and poisson_summary["available"]
        and elastic_summary["source_count"] >= minimum_sources_per_required_property
        and poisson_summary["source_count"] >= minimum_sources_per_required_property
    )

    if complete:
        status = "EVIDENCE_SYNTHESIS_MATERIAL_CANDIDATE_AVAILABLE"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    else:
        status = "EVIDENCE_SYNTHESIS_NEEDS_MORE_EVIDENCE"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = []

        if not elastic_summary["available"]:
            blockers.append("ELASTIC_MODULUS_EVIDENCE_NOT_FOUND")
        elif elastic_summary["source_count"] < minimum_sources_per_required_property:
            blockers.append("ELASTIC_MODULUS_SOURCE_COUNT_BELOW_MINIMUM")

        if not poisson_summary["available"]:
            blockers.append("POISSON_RATIO_EVIDENCE_NOT_FOUND")
        elif poisson_summary["source_count"] < minimum_sources_per_required_property:
            blockers.append("POISSON_RATIO_SOURCE_COUNT_BELOW_MINIMUM")

    global_uncertainty = "high"
    if complete:
        if elastic_summary["uncertainty_level"] == "medium" and poisson_summary["uncertainty_level"] == "medium":
            global_uncertainty = "medium"
        else:
            global_uncertainty = "high"

    synthesized_parameters = {
        "material_model_family": "linear_elastic_isotropic",
        "elastic_modulus_MPa": elastic_summary,
        "poisson_ratio": poisson_summary,
        "density_kg_m3": {
            "available": False,
            "proposed_value": None,
            "unit": "kg/m3",
            "note": "Density was not required for the current quasi-static linear elastic candidate."
        },
    }

    synthesis_candidate_id = ""
    if complete:
        synthesis_candidate_id = make_synthesis_id(
            case_id=case_id,
            material_domain=material_domain,
            anatomical_region=anatomical_region,
            values={
                "elastic_modulus": elastic_summary,
                "poisson_ratio": poisson_summary,
            },
        )

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "synthesis_candidate_id": synthesis_candidate_id,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "source_literature_records_count": len(records),
        "property_candidates_count": len(all_candidates),
        "synthesized_parameters": synthesized_parameters,
        "global_uncertainty_level": global_uncertainty,
        "minimum_sources_per_required_property": minimum_sources_per_required_property,
        "source_material_selection_json": str(material_path),
        "source_resolved_literature_json": str(literature_path),
        "property_candidates_csv": str(paths["property_candidates_csv"]),
        "property_summary_csv": str(paths["property_summary_csv"]),
        "clinical_use": False,
        "warnings": [
            "Evidence synthesis produces a literature-derived candidate range, not a patient-specific final material law.",
            "Sensitivity analysis is required before interpreting FEBio results."
        ],
        "blockers": blockers,
        "rules": [
            "Manual material value entry is forbidden.",
            "Values must be source-linked and extracted by the agent.",
            "The proposed value is a synthesis candidate, not a clinical material assignment.",
            "Human review may approve or reject the synthesis_candidate_id.",
            "GEOMETRY_AGENT remains blocked unless the synthesis candidate is approved and validated."
        ],
    }

    save_json(paths["result_json"], result)

    export_csv(paths["property_candidates_csv"], all_candidates)

    summary_rows = []
    for summary in summaries:
        row = {
            "property_name": summary["property_name"],
            "available": summary["available"],
            "count": summary["count"],
            "source_count": summary["source_count"],
            "proposed_value": summary["proposed_value"],
            "lower_bound": summary["lower_bound"],
            "upper_bound": summary["upper_bound"],
            "q25": summary["q25"],
            "q75": summary["q75"],
            "unit": summary["unit"],
            "uncertainty_level": summary["uncertainty_level"],
        }
        summary_rows.append(row)

    export_csv(paths["property_summary_csv"], summary_rows)

    review = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "review_type": "AGENT07D_EVIDENCE_SYNTHESIS_APPROVAL",
        "reviewer_decision": "PENDING",
        "approved_synthesis_candidate_id": "",
        "approved_for_geometry_agent": False,
        "approved_next_agent": "USER_ACTION_REQUIRED",
        "clinical_use": False,
        "source_evidence_synthesis_json": str(paths["result_json"]),
        "rules": [
            "Do not manually enter material values.",
            "Approve only the synthesis_candidate_id produced by Agent-07D.",
            "If uncertainty is high, sensitivity analysis must be required.",
            "GEOMETRY_AGENT is allowed only after validation of the approved synthesis candidate."
        ],
    }

    if not paths["review_json"].exists():
        save_json(paths["review_json"], review)

    return result
