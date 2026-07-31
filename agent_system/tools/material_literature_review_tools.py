from pathlib import Path
import json
import csv
import re
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def default_candidates_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES.json"


def default_review_table_csv(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "MATERIAL_LITERATURE_REVIEW_TABLE.csv"


def default_review_summary_json(case_id: str):
    return ROOT / "cases" / case_id / "08_material_review" / "MATERIAL_LITERATURE_REVIEW_SUMMARY.json"


def clean_text(text: str):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_excerpt(text: str, max_len: int = 600):
    text = clean_text(text)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def keyword_flags(title: str, abstract: str):
    text = f"{title} {abstract}".lower()

    flags = {
        "mentions_elastic_modulus": any(k in text for k in [
            "elastic modulus", "young's modulus", "young modulus", "modulus of elasticity"
        ]),
        "mentions_poisson_ratio": any(k in text for k in [
            "poisson", "poisson's ratio"
        ]),
        "mentions_density": "density" in text,
        "mentions_finite_element": any(k in text for k in [
            "finite element", "fea", "finite-element"
        ]),
        "mentions_bone": "bone" in text,
        "mentions_vertebra": any(k in text for k in [
            "vertebra", "vertebral", "spine", "spinal"
        ]),
        "mentions_mechanical_properties": any(k in text for k in [
            "mechanical properties", "material properties", "biomechanical properties"
        ]),
    }

    score = sum(1 for v in flags.values() if v)

    return flags, score


def export_literature_review_table(case_id: str, candidates_json: str = None):
    candidates_path = Path(candidates_json) if candidates_json else default_candidates_json(case_id)
    review_csv = default_review_table_csv(case_id)
    summary_json = default_review_summary_json(case_id)

    review_csv.parent.mkdir(parents=True, exist_ok=True)

    if not candidates_path.exists():
        summary = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "CANDIDATES_JSON_NOT_FOUND",
            "source_candidates_json": str(candidates_path),
            "review_table_csv": str(review_csv),
            "records_count": 0,
            "blockers": ["MATERIAL_LITERATURE_CANDIDATES_JSON_NOT_FOUND"]
        }
        summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return summary

    data = load_json(candidates_path)
    records = data.get("records", [])

    rows = []
    for idx, r in enumerate(records, start=1):
        title = clean_text(r.get("title", ""))
        abstract = clean_text(r.get("abstract", ""))
        flags, score = keyword_flags(title, abstract)

        rows.append({
            "rank": idx,
            "relevance_flag_score": score,

            "source": r.get("source", ""),
            "year": r.get("year", ""),
            "title": title,
            "authors": "; ".join(r.get("authors", [])) if isinstance(r.get("authors", []), list) else str(r.get("authors", "")),
            "doi": r.get("doi", ""),
            "url": r.get("url", ""),
            "query": r.get("query", ""),

            "abstract_excerpt": make_excerpt(abstract),

            "mentions_elastic_modulus": flags["mentions_elastic_modulus"],
            "mentions_poisson_ratio": flags["mentions_poisson_ratio"],
            "mentions_density": flags["mentions_density"],
            "mentions_finite_element": flags["mentions_finite_element"],
            "mentions_bone": flags["mentions_bone"],
            "mentions_vertebra": flags["mentions_vertebra"],
            "mentions_mechanical_properties": flags["mentions_mechanical_properties"],

            "reviewer_use_this_source": "",
            "reviewer_parameter_supported": "",
            "reviewer_reported_value_or_range": "",
            "reviewer_selected_value": "",
            "reviewer_notes": "",
        })

    rows = sorted(rows, key=lambda x: x["relevance_flag_score"], reverse=True)

    fieldnames = [
        "rank",
        "relevance_flag_score",
        "source",
        "year",
        "title",
        "authors",
        "doi",
        "url",
        "query",
        "abstract_excerpt",
        "mentions_elastic_modulus",
        "mentions_poisson_ratio",
        "mentions_density",
        "mentions_finite_element",
        "mentions_bone",
        "mentions_vertebra",
        "mentions_mechanical_properties",
        "reviewer_use_this_source",
        "reviewer_parameter_supported",
        "reviewer_reported_value_or_range",
        "reviewer_selected_value",
        "reviewer_notes",
    ]

    with review_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    source_errors = data.get("source_errors", [])

    summary = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "LITERATURE_REVIEW_TABLE_CREATED",
        "source_candidates_json": str(candidates_path),
        "review_table_csv": str(review_csv),
        "records_count": len(records),
        "source_errors_count": len(source_errors),
        "top_ranked_titles": [
            {
                "title": row["title"],
                "source": row["source"],
                "year": row["year"],
                "doi": row["doi"],
                "url": row["url"],
                "relevance_flag_score": row["relevance_flag_score"]
            }
            for row in rows[:10]
        ],
        "clinical_use": False,
        "notes": [
            "This table is for human review only.",
            "The system does not assign material parameters from this table automatically.",
            "Reviewer-entered values must still pass Material Review Approval Validator."
        ]
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    return summary
