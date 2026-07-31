from pathlib import Path
import json
import csv
import re
from collections import Counter, defaultdict

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
    text = str(text)
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("ρ", "rho")
    text = text.replace("×", "*")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def lower(text: str):
    return norm(text).lower()


def source_key(candidate: dict):
    doi = lower(candidate.get("source_doi", ""))
    if doi:
        return "doi:" + doi

    pmid = lower(candidate.get("source_pmid", ""))
    if pmid:
        return "pmid:" + pmid

    url = lower(candidate.get("source_url", ""))
    if url:
        return "url:" + url

    return "title:" + lower(candidate.get("source_title", ""))


def extract_nearby_equation_text(text: str):
    text = norm(text)

    pieces = re.split(r"(?<=[.;:])\s+|\n+", text)

    selected = []
    equation_triggers = [
        "=", "rho", "density", "hounsfield", " hu ", "ρ",
        "elastic modulus", "young", "modulus", "eapp", "esi", "etr"
    ]

    for piece in pieces:
        p_low = lower(piece)

        if not any(t in p_low for t in equation_triggers):
            continue

        if len(piece) < 10:
            continue

        if len(piece) > 700:
            # Keep local equation-like windows from long paragraphs.
            for m in re.finditer(r"(.{0,180}=.{0,260})", piece):
                selected.append(norm(m.group(1)))
        else:
            selected.append(piece)

    unique = []
    seen = set()

    for s in selected:
        key = lower(s[:250])
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    return unique[:20]


def is_usable_equation(text: str):
    t = lower(text)

    # Required components:
    # 1. left/right relation with equal sign
    # 2. modulus variable or explicit modulus term
    # 3. density/HU variable
    # 4. numeric coefficient
    has_equal = "=" in text

    has_modulus = bool(re.search(
        r"\b(e|eapp|esi|etr)\b|elastic modulus|young'?s modulus|modulus of elasticity",
        t,
        flags=re.I
    ))

    has_density = bool(re.search(
        r"\b(rho|rhoct|density|apparent density|ash density|bmd|hu|hounsfield)\b",
        t,
        flags=re.I
    ))

    has_number = bool(re.search(
        r"[-+]?\d+(?:\.\d+)?(?:\s*[eE]\s*[-+]?\d+)?",
        text
    ))

    has_formula_operator = bool(re.search(r"[\*\^/+-]", text))

    # Avoid equations that are clearly not material laws.
    wrong_context = bool(re.search(
        r"strain|yield strength|angle|ratio|height|width|distance|score|index",
        t,
        flags=re.I
    )) and not bool(re.search(r"elastic modulus|young|eapp|esi|etr", t, flags=re.I))

    usable = (
        has_equal
        and has_modulus
        and has_density
        and has_number
        and has_formula_operator
        and not wrong_context
    )

    return usable, {
        "has_equal": has_equal,
        "has_modulus": has_modulus,
        "has_density_or_hu": has_density,
        "has_number": has_number,
        "has_formula_operator": has_formula_operator,
        "wrong_context": wrong_context,
    }


def classify_candidate(candidate: dict):
    text = " ".join([
        candidate.get("source_title", ""),
        candidate.get("context_excerpt", ""),
        " ".join(candidate.get("formula_snippets", [])),
    ])

    equations = extract_nearby_equation_text(text)

    usable_equations = []
    flags_list = []

    for eq in equations:
        usable, flags = is_usable_equation(eq)
        flags_list.append(flags)

        if usable:
            usable_equations.append(eq)

    claim_text = lower(text)

    has_density_claim = any(x in claim_text for x in [
        "density", "qct", "ct-based", "ct based", "hounsfield", "hu", "rho"
    ])

    has_modulus_claim = any(x in claim_text for x in [
        "elastic modulus", "young", "modulus", "linear elastic", "material properties"
    ])

    has_target_claim = any(x in claim_text for x in [
        "vertebra", "vertebral", "spine", "spinal", "trabecular bone", "cancellous bone"
    ])

    if usable_equations:
        decision = "USABLE_EQUATION_CANDIDATE"
        reason = "EXPLICIT_DENSITY_HU_MODULUS_EQUATION_EXTRACTED"
    elif has_density_claim and has_modulus_claim and has_target_claim:
        decision = "SOURCE_REVIEW_REQUIRED"
        reason = "SOURCE_CLAIMS_DENSITY_HU_LAW_BUT_EQUATION_NOT_EXTRACTED"
    else:
        decision = "REJECT"
        reason = "NO_USABLE_DENSITY_HU_MODULUS_LAW_EVIDENCE"

    return {
        "decision": decision,
        "reason": reason,
        "equation_candidates": equations,
        "usable_equations": usable_equations,
        "flags_list": flags_list,
    }


def main():
    case_id = "real_dicom_check_001_anon_T1"

    source_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_DENSITY_HU_LAW_CANDIDATES.json"

    out_json = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_EQUATION_NORMALIZATION_RESULT.json"
    out_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_EQUATION_NORMALIZATION.csv"
    out_source_csv = ROOT / "cases" / case_id / "08_material_review" / "AGENT07E_SOURCE_LEVEL_LAW_REVIEW.csv"

    data = load_json(source_json)
    candidates = data.get("law_candidates", [])

    normalized_rows = []

    for c in candidates:
        classification = classify_candidate(c)

        row = {
            "law_candidate_id": c.get("law_candidate_id", ""),
            "decision": classification["decision"],
            "reason": classification["reason"],
            "source_key": source_key(c),
            "source_title": c.get("source_title", ""),
            "source_url": c.get("source_url", ""),
            "source_doi": c.get("source_doi", ""),
            "source_pmid": c.get("source_pmid", ""),
            "source_pmcid": c.get("source_pmcid", ""),
            "law_status_original": c.get("law_status", ""),
            "complete_law_candidate_original": c.get("complete_law_candidate", ""),
            "context_score": c.get("context_score", ""),
            "usable_equations_count": len(classification["usable_equations"]),
            "usable_equations": " || ".join(classification["usable_equations"]),
            "equation_candidates": " || ".join(classification["equation_candidates"]),
            "formula_snippets": " || ".join(c.get("formula_snippets", [])),
            "context_excerpt": c.get("context_excerpt", "")[:2500],
        }

        normalized_rows.append(row)

    # Source-level consolidation.
    by_source = defaultdict(list)
    for row in normalized_rows:
        by_source[row["source_key"]].append(row)

    source_rows = []

    for key, rows in by_source.items():
        usable = [r for r in rows if r["decision"] == "USABLE_EQUATION_CANDIDATE"]
        review = [r for r in rows if r["decision"] == "SOURCE_REVIEW_REQUIRED"]
        reject = [r for r in rows if r["decision"] == "REJECT"]

        if usable:
            source_decision = "SOURCE_HAS_USABLE_EQUATION"
            representative = usable[0]
        elif review:
            source_decision = "SOURCE_REVIEW_REQUIRED"
            representative = review[0]
        else:
            source_decision = "SOURCE_REJECTED"
            representative = reject[0]

        source_rows.append({
            "source_key": key,
            "source_decision": source_decision,
            "candidate_count": len(rows),
            "usable_candidate_count": len(usable),
            "source_review_candidate_count": len(review),
            "rejected_candidate_count": len(reject),
            "representative_law_candidate_id": representative.get("law_candidate_id", ""),
            "source_title": representative.get("source_title", ""),
            "source_url": representative.get("source_url", ""),
            "source_doi": representative.get("source_doi", ""),
            "source_pmid": representative.get("source_pmid", ""),
            "usable_equations": representative.get("usable_equations", ""),
            "equation_candidates": representative.get("equation_candidates", ""),
            "formula_snippets": representative.get("formula_snippets", ""),
        })

    source_rows = sorted(
        source_rows,
        key=lambda x: (
            0 if x["source_decision"] == "SOURCE_HAS_USABLE_EQUATION" else
            1 if x["source_decision"] == "SOURCE_REVIEW_REQUIRED" else
            2,
            -int(x["candidate_count"])
        )
    )

    usable_sources = [x for x in source_rows if x["source_decision"] == "SOURCE_HAS_USABLE_EQUATION"]
    review_sources = [x for x in source_rows if x["source_decision"] == "SOURCE_REVIEW_REQUIRED"]

    if usable_sources:
        status = "USABLE_DENSITY_HU_EQUATION_SOURCES_AVAILABLE"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = []
    elif review_sources:
        status = "SOURCE_REVIEW_REQUIRED_FOR_DENSITY_HU_EQUATIONS"
        next_agent = "HUMAN_REVIEW_GATE"
        blockers = ["NO_USABLE_EQUATION_EXTRACTED_BUT_REVIEWABLE_SOURCES_EXIST"]
    else:
        status = "NO_USABLE_DENSITY_HU_EQUATION_SOURCES"
        next_agent = "USER_ACTION_REQUIRED"
        blockers = ["NO_USABLE_DENSITY_HU_EQUATION_SOURCES"]

    result = {
        "case_id": case_id,
        "status": status,
        "next_agent": next_agent,
        "total_candidates": len(candidates),
        "normalized_candidate_rows": len(normalized_rows),
        "unique_source_count": len(source_rows),
        "usable_equation_sources_count": len(usable_sources),
        "source_review_required_count": len(review_sources),
        "decision_counts": dict(Counter(x["decision"] for x in normalized_rows)),
        "source_decision_counts": dict(Counter(x["source_decision"] for x in source_rows)),
        "top_usable_sources": usable_sources[:10],
        "top_review_sources": review_sources[:10],
        "clinical_use": False,
        "rules": [
            "This step consolidates duplicate law candidates by source.",
            "A usable equation must explicitly link modulus and density/HU with numeric coefficients.",
            "Source-review candidates cannot directly open GEOMETRY_AGENT.",
            "Manual equations or manual values remain forbidden."
        ],
        "blockers": blockers,
    }

    save_json(out_json, result)
    write_csv(out_csv, normalized_rows)
    write_csv(out_source_csv, source_rows)

    print("AGENT07E_EQUATION_NORMALIZATION_COMPLETED=True")
    print("STATUS=" + status)
    print("NEXT_AGENT=" + next_agent)
    print("TOTAL_CANDIDATES=" + str(len(candidates)))
    print("UNIQUE_SOURCE_COUNT=" + str(len(source_rows)))
    print("USABLE_EQUATION_SOURCES_COUNT=" + str(len(usable_sources)))
    print("SOURCE_REVIEW_REQUIRED_COUNT=" + str(len(review_sources)))
    print("DECISION_COUNTS=" + str(result["decision_counts"]))
    print("SOURCE_DECISION_COUNTS=" + str(result["source_decision_counts"]))
    print("BLOCKERS=" + str(blockers))

    print("\nTOP_USABLE_SOURCES")
    for row in usable_sources[:5]:
        print("-" * 80)
        print("SOURCE_TITLE=" + row["source_title"][:220])
        print("REPRESENTATIVE_LAW_CANDIDATE_ID=" + row["representative_law_candidate_id"])
        print("USABLE_EQUATIONS=" + row["usable_equations"][:900])
        print("SOURCE_URL=" + row["source_url"][:220])

    print("\nTOP_REVIEW_SOURCES")
    for row in review_sources[:5]:
        print("-" * 80)
        print("SOURCE_TITLE=" + row["source_title"][:220])
        print("REPRESENTATIVE_LAW_CANDIDATE_ID=" + row["representative_law_candidate_id"])
        print("EQUATION_CANDIDATES=" + row["equation_candidates"][:900])
        print("SOURCE_URL=" + row["source_url"][:220])


if __name__ == "__main__":
    main()
