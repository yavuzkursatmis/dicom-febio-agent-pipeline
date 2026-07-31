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


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def norm(text: str):
    if not text:
        return ""
    text = str(text).lower()
    repl = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
    for a, b in repl.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_any(text, terms):
    t = norm(text)
    return [x for x in terms if norm(x) in t]


def classify_law_candidate(candidate: dict):
    context = " ".join([
        candidate.get("source_title", ""),
        candidate.get("context_excerpt", ""),
        " ".join(candidate.get("formula_snippets", [])),
    ])

    target_terms = [
        "vertebra", "vertebral", "vertebral body",
        "spine", "spinal", "thoracic", "cervical", "lumbar"
    ]

    bone_terms = [
        "bone", "cortical", "cancellous", "trabecular"
    ]

    density_terms = [
        "density", "apparent density", "ash density",
        "bone mineral density", "bmd", "hounsfield", "hounsfield unit",
        "hu", "computed tomography", "ct"
    ]

    modulus_terms = [
        "elastic modulus", "young modulus", "young's modulus",
        "modulus of elasticity", "modulus", "linear elastic"
    ]

    negative_terms = [
        "steel", "metal", "metals", "aluminum", "aluminium",
        "concrete", "soil", "bentonite", "bridge", "overcrossing",
        "electric properties", "linear electric", "fatigue crack growth",
        "regular polygons", "silicone rubber"
    ]

    positive_target = has_any(context, target_terms)
    positive_bone = has_any(context, bone_terms)
    positive_density = has_any(context, density_terms)
    positive_modulus = has_any(context, modulus_terms)
    negative = has_any(context, negative_terms)

    snippets = " ".join(candidate.get("formula_snippets", []))
    ctx = candidate.get("context_excerpt", "")

    equation_text = " ".join([snippets, ctx])
    equation_norm = norm(equation_text)

    has_equal_sign = "=" in equation_text
    has_power = "^" in equation_text or "**" in equation_text
    has_numeric_coefficient = bool(re.search(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", equation_norm, flags=re.I))

    has_density_variable = bool(re.search(r"(rho|ρ|density|ash density|apparent density|bmd|hu|hounsfield)", equation_norm, flags=re.I))
    has_modulus_variable = bool(re.search(r"(\be\b|elastic modulus|young|modulus)", equation_norm, flags=re.I))

    explicit_equation_like = (
        has_numeric_coefficient
        and has_density_variable
        and has_modulus_variable
        and (has_equal_sign or has_power)
    )

    # Daha zayıf ama yine de incelemeye değer: açık denklem yok, ama HU/density-based assignment var.
    source_claim_only = (
        positive_target
        and positive_bone
        and positive_density
        and positive_modulus
        and not explicit_equation_like
    )

    if negative:
        decision = "REJECT"
        reason = "NEGATIVE_CONTEXT_MATCH"

    elif not positive_target:
        decision = "REJECT"
        reason = "NO_TARGET_CONTEXT"

    elif not positive_bone:
        decision = "REJECT"
        reason = "NO_BONE_CONTEXT"

    elif not positive_density:
        decision = "REJECT"
        reason = "NO_DENSITY_OR_HU_CONTEXT"

    elif not positive_modulus:
        decision = "REJECT"
        reason = "NO_MODULUS_CONTEXT"

    elif explicit_equation_like:
        decision = "ACCEPT_STRICT_EQUATION"
        reason = "EXPLICIT_DENSITY_HU_MODULUS_EQUATION"

    elif source_claim_only:
        decision = "NEEDS_SOURCE_REVIEW"
        reason = "LAW_CLAIM_WITHOUT_EXPLICIT_EQUATION"

    else:
        decision = "REJECT"
        reason = "INSUFFICIENT_LAW_EVIDENCE"

    return {
        "decision": decision,
        "reason": reason,
        "positive_target_terms": positive_target,
        "positive_bone_terms": positive_bone,
        "positive_density_terms": positive_density,
        "positive_modulus_terms": positive_modulus,
        "negative_terms": negative,
        "has_equal_sign": has_equal_sign,
        "has_power": has_power,
        "has_numeric_coefficient": has_numeric_coefficient,
        "has_density_variable": has_density_variable,
        "has_modulus_variable": has_modulus_variable,
        "explicit_equation_like": explicit_equation_like,
    }


def main():
    case_id = "real_dicom_check_001_anon_T1"

    source_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_DENSITY_HU_LAW_CANDIDATES.json"
    audit_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_DENSITY_HU_LAW_VALIDATION.json"
    audit_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_DENSITY_HU_LAW_VALIDATION.csv"

    data = load_json(source_json)
    candidates = data.get("law_candidates", [])

    audited = []

    for c in candidates:
        verdict = classify_law_candidate(c)

        row = {
            "law_candidate_id": c.get("law_candidate_id", ""),
            "decision": verdict["decision"],
            "reason": verdict["reason"],
            "source_title": c.get("source_title", ""),
            "source_url": c.get("source_url", ""),
            "source_doi": c.get("source_doi", ""),
            "law_status": c.get("law_status", ""),
            "complete_law_candidate_original": c.get("complete_law_candidate", ""),
            "context_score": c.get("context_score", ""),
            "explicit_equation_like": verdict["explicit_equation_like"],
            "has_equal_sign": verdict["has_equal_sign"],
            "has_power": verdict["has_power"],
            "has_numeric_coefficient": verdict["has_numeric_coefficient"],
            "has_density_variable": verdict["has_density_variable"],
            "has_modulus_variable": verdict["has_modulus_variable"],
            "positive_target_terms": "; ".join(verdict["positive_target_terms"]),
            "positive_bone_terms": "; ".join(verdict["positive_bone_terms"]),
            "positive_density_terms": "; ".join(verdict["positive_density_terms"]),
            "positive_modulus_terms": "; ".join(verdict["positive_modulus_terms"]),
            "negative_terms": "; ".join(verdict["negative_terms"]),
            "formula_snippets": " || ".join(c.get("formula_snippets", [])),
            "context_excerpt": c.get("context_excerpt", "")[:2200],
        }

        audited.append(row)

    strict = [x for x in audited if x["decision"] == "ACCEPT_STRICT_EQUATION"]
    needs_review = [x for x in audited if x["decision"] == "NEEDS_SOURCE_REVIEW"]
    rejected = [x for x in audited if x["decision"] == "REJECT"]

    if strict:
        status = "STRICT_DENSITY_HU_EQUATION_CANDIDATES_AVAILABLE"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    elif needs_review:
        status = "DENSITY_HU_LAW_CLAIMS_NEED_SOURCE_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = ["NO_EXPLICIT_EQUATION_EXTRACTED_BUT_SOURCE_CLAIMS_EXIST"]
    else:
        status = "NO_VALID_DENSITY_HU_LAW_CANDIDATES"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_VALID_DENSITY_HU_LAW_CANDIDATES"]

    validation = {
        "case_id": case_id,
        "status": status,
        "next_agent": next_agent,
        "total_law_candidates": len(candidates),
        "strict_equation_candidates_count": len(strict),
        "needs_source_review_count": len(needs_review),
        "rejected_candidates_count": len(rejected),
        "decision_counts": dict(Counter(x["decision"] for x in audited)),
        "reason_counts": dict(Counter(x["reason"] for x in audited)),
        "top_strict_candidates": strict[:10],
        "top_needs_review_candidates": needs_review[:10],
        "clinical_use": False,
        "rules": [
            "Strict accepted candidates must contain target, bone, density/HU, modulus and equation-like evidence.",
            "Source-claim-only candidates may go to human source review but cannot directly open GEOMETRY_AGENT.",
            "Manual equation or value entry remains forbidden.",
            "GEOMETRY_AGENT requires an approved, source-linked, validated law_candidate_id."
        ],
        "blockers": blockers,
    }

    save_json(audit_json, validation)
    write_csv(audit_csv, audited)

    print("AGENT07E_STRICT_LAW_VALIDATION_COMPLETED=True")
    print("STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("TOTAL_LAW_CANDIDATES=" + str(len(candidates)))
    print("STRICT_EQUATION_CANDIDATES_COUNT=" + str(len(strict)))
    print("NEEDS_SOURCE_REVIEW_COUNT=" + str(len(needs_review)))
    print("REJECTED_CANDIDATES_COUNT=" + str(len(rejected)))
    print("DECISION_COUNTS=" + str(validation["decision_counts"]))
    print("REASON_COUNTS=" + str(validation["reason_counts"]))
    print("BLOCKERS=" + str(blockers))

    print("\nTOP_STRICT_CANDIDATES")
    for row in strict[:5]:
        print("-" * 80)
        print("LAW_CANDIDATE_ID=" + row["law_candidate_id"])
        print("TITLE=" + row["source_title"][:220])
        print("FORMULA_SNIPPETS=" + row["formula_snippets"][:700])
        print("CONTEXT=" + row["context_excerpt"][:700])

    print("\nTOP_NEEDS_SOURCE_REVIEW")
    for row in needs_review[:5]:
        print("-" * 80)
        print("LAW_CANDIDATE_ID=" + row["law_candidate_id"])
        print("TITLE=" + row["source_title"][:220])
        print("FORMULA_SNIPPETS=" + row["formula_snippets"][:700])
        print("CONTEXT=" + row["context_excerpt"][:700])


if __name__ == "__main__":
    main()
