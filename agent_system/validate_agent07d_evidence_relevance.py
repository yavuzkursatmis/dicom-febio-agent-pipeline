from pathlib import Path
import json
import csv
import re
from collections import Counter

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return

    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def norm(text: str):
    if not text:
        return ""
    text = str(text).lower()
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_target_family(anatomical_region: str, material_domain: str):
    t = norm(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if "cartilage" in t:
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t:
        return "ligament"

    if "muscle" in t:
        return "muscle"

    return norm(material_domain)


def get_positive_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    terms = set()

    for token in re.split(r"[^A-Za-z0-9]+", anatomical_region):
        if len(token) >= 2:
            terms.add(token.lower())

    domain_terms = {
        "bone": ["bone", "cortical", "cancellous", "trabecular"],
        "cartilage": ["cartilage", "articular cartilage", "meniscus"],
        "tendon": ["tendon"],
        "ligament": ["ligament", "acl", "pcl", "mcl", "lcl"],
        "muscle": ["muscle", "skeletal muscle"],
        "soft_tissue": ["soft tissue"],
        "implant_material": ["implant", "titanium", "tantalum", "ti6al4v"],
    }

    family_terms = {
        "spine_vertebra": [
            "vertebra",
            "vertebral",
            "vertebral body",
            "spine",
            "spinal",
            "thoracic",
            "cervical",
            "lumbar",
            "t1",
        ],
        "cartilage": ["cartilage"],
        "tendon": ["tendon"],
        "ligament": ["ligament"],
        "muscle": ["muscle"],
    }

    for x in domain_terms.get(material_domain, []):
        terms.add(x)

    for x in family_terms.get(family, []):
        terms.add(x)

    return sorted(terms)


def get_negative_terms(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    animal_terms = [
        "beagle", "canine", "dog", "ovine", "sheep", "bovine", "cow",
        "porcine", "pig", "rat", "rabbit", "mouse", "mice", "murine",
        "goat", "equine", "horse"
    ]

    generic_wrong_engineering = [
        "bentonite",
        "bridge",
        "overcrossing",
        "linear electric",
        "electric properties",
        "fatigue crack growth",
        "crack growth",
        "extended finite element",
        "xfem",
        "steel",
        "aluminium",
        "aluminum",
        "metal alloy",
        "metals",
        "concrete",
        "soil",
        "regular polygons",
    ]

    mismatch = []

    if family == "spine_vertebra":
        mismatch = [
            "femoral head",
            "femur",
            "femoral",
            "tibia",
            "tibial",
            "humerus",
            "mandible",
            "skull",
        ]

    return sorted(set(animal_terms + generic_wrong_engineering + mismatch))


def has_any(text: str, terms):
    t = norm(text)
    return [term for term in terms if norm(term) in t]


def classify_candidate(candidate: dict, anatomical_region: str, material_domain: str):
    text = " ".join([
        candidate.get("source_title", ""),
        candidate.get("context_excerpt", ""),
        candidate.get("source_url", ""),
        candidate.get("source_doi", ""),
    ])

    positive_matches = has_any(text, get_positive_terms(anatomical_region, material_domain))
    negative_matches = has_any(text, get_negative_terms(anatomical_region, material_domain))

    property_name = candidate.get("property_name", "")
    value_raw = candidate.get("normalized_value", "")

    try:
        value = float(value_raw)
    except Exception:
        return {
            "decision": "REJECT",
            "reason": "VALUE_NOT_NUMERIC",
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
            "relevance_tier": "none",
        }

    if negative_matches:
        return {
            "decision": "REJECT",
            "reason": "NEGATIVE_CONTEXT_MATCH",
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
            "relevance_tier": "none",
        }

    if not positive_matches:
        return {
            "decision": "REJECT",
            "reason": "NO_TARGET_OR_TISSUE_CONTEXT",
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
            "relevance_tier": "none",
        }

    if property_name == "elastic_modulus":
        if material_domain == "bone" and not (0.001 <= value <= 40000):
            return {
                "decision": "REJECT",
                "reason": "ELASTIC_MODULUS_OUT_OF_BONE_SANITY_RANGE",
                "positive_matches": positive_matches,
                "negative_matches": negative_matches,
                "relevance_tier": "none",
            }

    if property_name == "poisson_ratio":
        if not (0.01 <= value < 0.5):
            return {
                "decision": "REJECT",
                "reason": "POISSON_OUT_OF_RANGE",
                "positive_matches": positive_matches,
                "negative_matches": negative_matches,
                "relevance_tier": "none",
            }

    family = infer_target_family(anatomical_region, material_domain)
    t = norm(" ".join(positive_matches))

    if family == "spine_vertebra" and any(x in t for x in ["vertebra", "vertebral", "spine", "spinal", "thoracic", "cervical", "lumbar", "t1"]):
        tier = "target_specific"
    else:
        tier = "domain_general"

    # For a spine/vertebra target, domain-general bone context alone is not enough
    # to support material synthesis for the requested target.
    if family == "spine_vertebra" and tier != "target_specific":
        return {
            "decision": "REJECT",
            "reason": "DOMAIN_GENERAL_NOT_TARGET_SPECIFIC",
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
            "relevance_tier": tier,
        }

    return {
        "decision": "ACCEPT",
        "reason": "TARGET_OR_TISSUE_CONTEXT_CONFIRMED",
        "positive_matches": positive_matches,
        "negative_matches": negative_matches,
        "relevance_tier": tier,
    }


def main():
    case_id = "real_dicom_check_001_anon_T1"

    result_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07D_EVIDENCE_SYNTHESIS_RESULT.json"
    candidates_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07D_PROPERTY_CANDIDATES.csv"

    audit_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07D_EVIDENCE_AUDIT.csv"
    validation_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07D_EVIDENCE_RELEVANCE_VALIDATION.json"

    result = load_json(result_path)
    candidates = read_csv(candidates_csv)

    material_domain = result.get("material_domain", "")
    anatomical_region = result.get("anatomical_region", "")

    audited = []

    for c in candidates:
        verdict = classify_candidate(c, anatomical_region, material_domain)

        row = dict(c)
        row["evidence_decision"] = verdict["decision"]
        row["evidence_reject_reason"] = verdict["reason"]
        row["positive_matches"] = "; ".join(verdict["positive_matches"])
        row["negative_matches"] = "; ".join(verdict["negative_matches"])
        row["relevance_tier"] = verdict["relevance_tier"]

        audited.append(row)

    accepted = [x for x in audited if x["evidence_decision"] == "ACCEPT"]
    rejected = [x for x in audited if x["evidence_decision"] == "REJECT"]

    accepted_elastic = [x for x in accepted if x.get("property_name") == "elastic_modulus"]
    accepted_poisson = [x for x in accepted if x.get("property_name") == "poisson_ratio"]

    elastic_sources = set(
        x.get("source_doi") or x.get("source_pmid") or x.get("source_url") or x.get("source_title")
        for x in accepted_elastic
    )

    poisson_sources = set(
        x.get("source_doi") or x.get("source_pmid") or x.get("source_url") or x.get("source_title")
        for x in accepted_poisson
    )

    can_synthesize = len(elastic_sources) >= 2 and len(poisson_sources) >= 2

    validation = {
        "case_id": case_id,
        "material_domain": material_domain,
        "anatomical_region": anatomical_region,
        "status": "AGENT07D_EVIDENCE_RELEVANCE_VALIDATED",
        "total_candidates": len(candidates),
        "accepted_candidates": len(accepted),
        "rejected_candidates": len(rejected),
        "accepted_elastic_count": len(accepted_elastic),
        "accepted_elastic_source_count": len(elastic_sources),
        "accepted_poisson_count": len(accepted_poisson),
        "accepted_poisson_source_count": len(poisson_sources),
        "can_synthesize_after_audit": can_synthesize,
        "next_agent": "HUMAN_REVIEW_GATE" if can_synthesize else "USER_ACTION_REQUIRED",
        "decision_counts": dict(Counter(x["evidence_decision"] for x in audited)),
        "reject_reason_counts": dict(Counter(x["evidence_reject_reason"] for x in rejected)),
        "rules": [
            "Manual material values are not allowed.",
            "A candidate must have target or tissue context in the extracted source context.",
            "Negative non-target, animal, or unrelated engineering contexts are rejected.",
            "GEOMETRY_AGENT remains blocked unless audited evidence supports both elastic modulus and Poisson ratio."
        ],
        "blockers": [] if can_synthesize else [
            "AUDITED_EVIDENCE_INSUFFICIENT_FOR_SYNTHESIS"
        ],
    }

    write_csv(audit_csv, audited)
    save_json(validation_json, validation)

    print("AGENT07D_EVIDENCE_AUDIT_COMPLETED=True")
    print("STATUS=" + validation["status"])
    print("TOTAL_CANDIDATES=" + str(validation["total_candidates"]))
    print("ACCEPTED_CANDIDATES=" + str(validation["accepted_candidates"]))
    print("REJECTED_CANDIDATES=" + str(validation["rejected_candidates"]))
    print("ACCEPTED_ELASTIC_COUNT=" + str(validation["accepted_elastic_count"]))
    print("ACCEPTED_ELASTIC_SOURCE_COUNT=" + str(validation["accepted_elastic_source_count"]))
    print("ACCEPTED_POISSON_COUNT=" + str(validation["accepted_poisson_count"]))
    print("ACCEPTED_POISSON_SOURCE_COUNT=" + str(validation["accepted_poisson_source_count"]))
    print("CAN_SYNTHESIZE_AFTER_AUDIT=" + str(validation["can_synthesize_after_audit"]))
    print("NEXT_AGENT=" + validation["next_agent"])
    print("REJECT_REASON_COUNTS=" + str(validation["reject_reason_counts"]))
    print("BLOCKERS=" + str(validation["blockers"]))

    print("\nTOP_AUDITED_CANDIDATES")
    for row in audited[:10]:
        print("-" * 80)
        print("PROPERTY=" + str(row.get("property_name", "")))
        print("VALUE=" + str(row.get("normalized_value", "")) + " " + str(row.get("normalized_unit", "")))
        print("DECISION=" + str(row.get("evidence_decision", "")))
        print("REASON=" + str(row.get("evidence_reject_reason", "")))
        print("TIER=" + str(row.get("relevance_tier", "")))
        print("TITLE=" + str(row.get("source_title", ""))[:220])
        print("POSITIVE=" + str(row.get("positive_matches", "")))
        print("NEGATIVE=" + str(row.get("negative_matches", "")))


if __name__ == "__main__":
    main()
