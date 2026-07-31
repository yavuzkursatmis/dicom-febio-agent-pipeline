from pathlib import Path
import json
import re
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_agent07b_json(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "AGENT07B_MATERIAL_CANDIDATES.json"


def output_json(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "AGENT07B_CANDIDATE_SET_RELEVANCE_RESULT.json"


def normalize(text: str):
    if not text:
        return ""
    text = str(text).lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str):
    text = normalize(text)
    return [x for x in re.split(r"[^a-z0-9]+", text) if len(x) >= 2]


def infer_target_family(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)

    if any(x in t for x in ["vertebra", "spine", "spinal", "omur"]) or re.search(r"\b[c,t,l,s]\d+\b", t):
        return "spine_vertebra"

    if any(x in t for x in ["femur", "femoral", "hip"]):
        return "femur_hip"

    if any(x in t for x in ["tibia", "tibial"]):
        return "tibia"

    if any(x in t for x in ["humerus", "humeral"]):
        return "humerus"

    if any(x in t for x in ["mandible", "jaw"]):
        return "mandible"

    if any(x in t for x in ["cartilage", "kikirdak", "meniscus", "meniskus"]):
        return "cartilage"

    if "tendon" in t:
        return "tendon"

    if "ligament" in t or "acl" in t or "pcl" in t or "mcl" in t or "lcl" in t:
        return "ligament"

    if "muscle" in t or "kas" in t:
        return "muscle"

    if material_domain:
        return normalize(material_domain)

    return "unknown"


def positive_terms_for_target(anatomical_region: str, material_domain: str):
    t = normalize(anatomical_region)
    family = infer_target_family(anatomical_region, material_domain)

    terms = set(tokenize(t))

    domain_terms = {
        "bone": ["bone", "cortical", "cancellous", "trabecular"],
        "cartilage": ["cartilage", "articular cartilage", "meniscus"],
        "tendon": ["tendon"],
        "ligament": ["ligament", "acl", "pcl", "mcl", "lcl"],
        "muscle": ["muscle", "skeletal muscle"],
        "soft_tissue": ["soft tissue"],
        "implant_material": ["implant", "titanium", "tantalum", "ti6al4v"],
    }

    for term in domain_terms.get(material_domain, []):
        terms.add(term)

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
            "cervicothoracic",
        ],
        "femur_hip": ["femur", "femoral", "femoral head", "hip"],
        "tibia": ["tibia", "tibial"],
        "humerus": ["humerus", "humeral"],
        "mandible": ["mandible", "jaw"],
        "cartilage": ["cartilage", "articular cartilage"],
        "tendon": ["tendon"],
        "ligament": ["ligament"],
        "muscle": ["muscle"],
    }

    for term in family_terms.get(family, []):
        terms.add(term)

    return sorted(x for x in terms if x)


def negative_terms_for_target(anatomical_region: str, material_domain: str):
    family = infer_target_family(anatomical_region, material_domain)

    all_anatomy_groups = {
        "spine_vertebra": ["vertebra", "vertebral", "spine", "spinal", "thoracic", "cervical", "lumbar"],
        "femur_hip": ["femur", "femoral", "femoral head", "hip"],
        "tibia": ["tibia", "tibial"],
        "humerus": ["humerus", "humeral"],
        "mandible": ["mandible", "jaw"],
        "skull": ["skull", "cranial"],
        "rib": ["rib"],
    }

    negative = []

    for group, terms in all_anatomy_groups.items():
        if group != family:
            negative.extend(terms)

    # Klinik/hasta-özgül insan modeli hedeflenirken hayvan türleri doğrudan geçmemeli.
    animal_terms = [
        "beagle",
        "canine",
        "dog",
        "ovine",
        "sheep",
        "bovine",
        "cow",
        "porcine",
        "pig",
        "rat",
        "rabbit",
        "mouse",
        "murine",
        "goat",
        "equine",
        "horse",
    ]

    negative.extend(animal_terms)

    return sorted(set(negative))


def build_candidate_text(candidate_set: dict, candidate_map: dict):
    text_parts = [
        candidate_set.get("source_title", ""),
        candidate_set.get("source_doi", ""),
        candidate_set.get("source_url", ""),
    ]

    for cid_key in [
        "elastic_modulus_candidate_id",
        "poisson_ratio_candidate_id",
        "density_candidate_id",
    ]:
        cid = candidate_set.get(cid_key)
        if cid and cid in candidate_map:
            c = candidate_map[cid]
            text_parts.extend([
                c.get("source_title", ""),
                c.get("source_doi", ""),
                c.get("source_url", ""),
                c.get("context_excerpt", ""),
                c.get("material_domain", ""),
                c.get("anatomical_region", ""),
            ])

    return normalize(" ".join(text_parts))


def contains_term(text: str, term: str):
    term = normalize(term)
    if not term:
        return False

    # Çok kısa hedef kodları için kelime sınırı kullan.
    if len(term) <= 3:
        return re.search(rf"\b{re.escape(term)}\b", text) is not None

    return term in text


def score_candidate_set(candidate_set: dict, candidate_map: dict):
    anatomical_region = candidate_set.get("anatomical_region", "")
    material_domain = candidate_set.get("material_domain", "")

    text = build_candidate_text(candidate_set, candidate_map)

    positive_terms = positive_terms_for_target(anatomical_region, material_domain)
    negative_terms = negative_terms_for_target(anatomical_region, material_domain)

    matched_positive = [term for term in positive_terms if contains_term(text, term)]
    matched_negative = [term for term in negative_terms if contains_term(text, term)]

    family = infer_target_family(anatomical_region, material_domain)

    anatomical_match = False
    if family == "spine_vertebra":
        anatomical_match = any(
            contains_term(text, term)
            for term in ["vertebra", "vertebral", "spine", "spinal", "thoracic", "cervical", "lumbar", "t1"]
        )
    elif family != "unknown":
        anatomical_match = any(
            contains_term(text, term)
            for term in positive_terms
            if term not in ["bone", "cortical", "cancellous", "trabecular"]
        )

    domain_match = material_domain and contains_term(text, material_domain)

    score = 0

    if domain_match:
        score += 2

    if anatomical_match:
        score += 6

    score += min(len(matched_positive), 5)

    if candidate_set.get("source_doi") or candidate_set.get("source_url"):
        score += 1

    score -= 5 * len(matched_negative)

    if anatomical_match and not matched_negative and score >= 8:
        decision = "TARGET_RELEVANCE_PASS"
        acceptable = True
        blocker = ""
    elif anatomical_match and matched_negative:
        decision = "TARGET_RELEVANCE_CONFLICT"
        acceptable = False
        blocker = "TARGET_RELEVANCE_CONFLICT_WITH_NEGATIVE_MATCHES"
    elif score >= 4 and not matched_negative:
        decision = "TARGET_RELEVANCE_WEAK"
        acceptable = False
        blocker = "TARGET_SPECIFICITY_INSUFFICIENT"
    else:
        decision = "TARGET_RELEVANCE_FAIL"
        acceptable = False
        blocker = "ANATOMICAL_OR_SPECIES_MISMATCH"

    return {
        "candidate_set_id": candidate_set.get("candidate_set_id", ""),
        "decision": decision,
        "acceptable_for_human_review": acceptable,
        "target_relevance_score": score,
        "target_family": family,
        "matched_positive_terms": matched_positive,
        "matched_negative_terms": matched_negative,
        "anatomical_match": anatomical_match,
        "domain_match": bool(domain_match),
        "blocker": blocker,
        "candidate_set": candidate_set,
    }


def validate_candidate_set_relevance(case_id: str, agent07b_json: str = None):
    source_path = Path(agent07b_json) if agent07b_json else default_agent07b_json(case_id)
    out_path = output_json(case_id)

    if not source_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "AGENT07B_CANDIDATES_NOT_FOUND",
            "next_agent": "USER_ACTION_REQUIRED",
            "candidate_sets_count": 0,
            "acceptable_candidate_sets_count": 0,
            "clinical_use": False,
            "warnings": [],
            "blockers": ["AGENT07B_MATERIAL_CANDIDATES_JSON_NOT_FOUND"],
        }
        save_json(out_path, result)
        return result

    data = load_json(source_path)
    candidate_sets = data.get("candidate_sets", [])
    candidates = data.get("agent07b_candidates", [])

    candidate_map = {
        c.get("candidate_id"): c
        for c in candidates
        if c.get("candidate_id")
    }

    evaluated = [
        score_candidate_set(candidate_set, candidate_map)
        for candidate_set in candidate_sets
    ]

    acceptable = [
        item for item in evaluated
        if item.get("acceptable_for_human_review", False)
    ]

    if acceptable:
        status = "TARGET_RELEVANT_CANDIDATE_SETS_AVAILABLE"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    elif candidate_sets:
        status = "CANDIDATE_SETS_FOUND_BUT_TARGET_RELEVANCE_FAILED"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_TARGET_RELEVANT_CANDIDATE_SET"]
    else:
        status = "NO_CANDIDATE_SETS_TO_VALIDATE"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_CANDIDATE_SETS"]

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "next_agent": next_agent,
        "source_agent07b_json": str(source_path),
        "candidate_sets_count": len(candidate_sets),
        "acceptable_candidate_sets_count": len(acceptable),
        "evaluated_candidate_sets": evaluated,
        "acceptable_candidate_sets": acceptable,
        "clinical_use": False,
        "warnings": [],
        "blockers": blockers,
        "rules": [
            "Candidate set must match the requested anatomical target, not only broad material domain.",
            "Animal or non-target anatomical data must not pass silently.",
            "Weak candidate sets may be logged as comparator evidence but cannot open GEOMETRY_AGENT.",
            "Human review can only approve target-relevant agent-derived candidate sets."
        ],
    }

    save_json(out_path, result)
    return result
