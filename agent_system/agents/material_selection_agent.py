from pathlib import Path
import argparse
import csv
import json
import sys
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.material_selection_schema import (
    MaterialSelectionInput,
    MaterialSelectionResult,
)
from agent_system.tools.material_selection_tools import (
    load_config,
    infer_material_domain,
    generate_literature_queries,
    active_literature_search,
    extract_numeric_material_candidates,
    summarize_literature_support,
    select_values_only_if_source_backed,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    keys = sorted(set(k for row in rows for k in row.keys()))

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def default_target_json(case_id: str):
    return ROOT / "cases" / case_id / "03_target_understanding" / "TARGET_UNDERSTANDING_RESULT.json"


def default_segmentation_validation_json(case_id: str):
    return ROOT / "cases" / case_id / "05_segmentation_validation" / "SEGMENTATION_VALIDATION_RESULT.json"


def default_human_review_json(case_id: str):
    return ROOT / "cases" / case_id / "06_human_review" / "HUMAN_REVIEW_RESULT.json"


def blocked_result(case_id: str, output_json: Path, property_csv: Path, literature_json: Path, blocker: str):
    result = MaterialSelectionResult(
        case_id=case_id,
        material_selection_status="BLOCKED_BY_HUMAN_REVIEW",
        active_literature_search_required=True,
        literature_search_performed=False,
        literature_search_success=False,
        material_model="",
        selected_material_name="",
        anatomical_region="",
        material_domain="",
        tissue_assumption="",
        elastic_modulus_MPa=None,
        poisson_ratio=None,
        density_kg_m3=None,
        literature_query=[],
        literature_support_level="not_evaluated",
        literature_records_count=0,
        selected_sources=[],
        selected_value_rationale="Material selection was blocked before literature search.",
        uncertainty_level="high",
        human_review_required=True,
        next_agent="USER_ACTION_REQUIRED",
        warnings=[],
        blockers=[blocker],
        output_json=str(output_json),
        property_table_csv=str(property_csv),
        literature_candidates_json=str(literature_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False

    save_json(output_json, data)
    save_json(literature_json, {"records": [], "source_errors": []})
    write_csv(property_csv, [])

    return result


def run_material_selection(user_input: MaterialSelectionInput) -> MaterialSelectionResult:
    case_id = user_input.case_id

    target_path = Path(user_input.target_understanding_json) if user_input.target_understanding_json else default_target_json(case_id)
    validation_path = Path(user_input.segmentation_validation_json) if user_input.segmentation_validation_json else default_segmentation_validation_json(case_id)
    review_path = Path(user_input.human_review_json) if user_input.human_review_json else default_human_review_json(case_id)

    output_dir = ROOT / "cases" / case_id / "07_material_selection"
    output_json = output_dir / "MATERIAL_SELECTION_RESULT.json"
    property_csv = output_dir / "MATERIAL_PROPERTY_TABLE.csv"
    literature_json = output_dir / "MATERIAL_LITERATURE_CANDIDATES.json"

    if not target_path.exists():
        return blocked_result(case_id, output_json, property_csv, literature_json, "TARGET_UNDERSTANDING_RESULT_NOT_FOUND")

    if not validation_path.exists():
        return blocked_result(case_id, output_json, property_csv, literature_json, "SEGMENTATION_VALIDATION_RESULT_NOT_FOUND")

    if not review_path.exists():
        return blocked_result(case_id, output_json, property_csv, literature_json, "HUMAN_REVIEW_RESULT_NOT_FOUND")

    target = load_json(target_path)
    validation = load_json(validation_path)
    review = load_json(review_path)

    if not bool(review.get("approved", False)):
        return blocked_result(case_id, output_json, property_csv, literature_json, "HUMAN_REVIEW_NOT_APPROVED")

    if review.get("approved_next_agent", "") != "MATERIAL_SELECTION_AGENT":
        return blocked_result(case_id, output_json, property_csv, literature_json, "HUMAN_REVIEW_NEXT_AGENT_NOT_MATERIAL_SELECTION")

    if validation.get("segmentation_validation_status", "") not in [
        "SEGMENTATION_VALIDATION_PASS",
        "SEGMENTATION_VALIDATION_WARNING",
    ]:
        return blocked_result(case_id, output_json, property_csv, literature_json, "SEGMENTATION_VALIDATION_NOT_ACCEPTABLE")

    config = load_config()

    anatomical_region = target.get("segmentation_target", "") or target.get("standardized_anatomical_target", "")
    analysis_type = target.get("standardized_analysis_type", "")
    material_domain = infer_material_domain(anatomical_region)

    warnings = []
    blockers = []

    if material_domain == "unknown_requires_review":
        warnings.append("MATERIAL_DOMAIN_UNKNOWN_REQUIRES_REVIEW")

    active_required = bool(config.get("active_literature_search_required", True))
    if not active_required:
        blockers.append("ACTIVE_LITERATURE_SEARCH_POLICY_DISABLED")

    queries = generate_literature_queries(
        target=anatomical_region,
        analysis_type=analysis_type,
        material_domain=material_domain,
        config=config,
    )

    literature_search_performed = False
    literature_search_success = False
    literature_records = []
    source_errors = []

    if active_required and queries:
        literature_search_performed = True
        search_result = active_literature_search(
            queries=queries,
            limit_per_source=user_input.max_records_per_source,
        )
        literature_records = search_result["records"]
        source_errors = search_result["source_errors"]
        literature_search_success = len(literature_records) > 0

    candidates = extract_numeric_material_candidates(literature_records)
    selection = select_values_only_if_source_backed(
        candidates=candidates,
        records_count=len(literature_records),
        config=config,
    )

    literature_support_level = summarize_literature_support(
        records_count=len(literature_records),
        config=config,
    )

    save_json(literature_json, {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "queries": queries,
        "records_count": len(literature_records),
        "records": literature_records,
        "source_errors": source_errors,
        "numeric_material_candidates": candidates,
        "clinical_use": False,
    })

    write_csv(property_csv, candidates)

    if source_errors:
        warnings.append("LITERATURE_SOURCE_ERRORS_PRESENT")

    if not literature_search_performed:
        blockers.append("LITERATURE_SEARCH_NOT_PERFORMED")

    if not literature_search_success:
        warnings.append("LITERATURE_SEARCH_EMPTY_OR_FAILED")

    if len(literature_records) == 0:
        status = "MATERIAL_SELECTION_NEEDS_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        human_review_required = True
        rationale = "Active literature search returned no records; no material value was selected."
    elif not selection["can_pass"]:
        status = "MATERIAL_SELECTION_NEEDS_REVIEW"
        next_agent = "HUMAN_REVIEW_GATE"
        human_review_required = True
        rationale = selection["selected_value_rationale"]
        warnings.append("SOURCE_BACKED_NUMERICAL_PARAMETERS_INSUFFICIENT")
    elif blockers:
        status = "MATERIAL_SELECTION_FAIL"
        next_agent = "USER_ACTION_REQUIRED"
        human_review_required = True
        rationale = "Material selection failed due to blocking policy violations."
    else:
        status = "MATERIAL_SELECTION_PASS"
        next_agent = "GEOMETRY_AGENT"
        human_review_required = bool(config.get("review_policy", {}).get("human_review_required_if_literature_range_wide", True))
        if human_review_required:
            status = "MATERIAL_SELECTION_NEEDS_REVIEW"
            next_agent = "HUMAN_REVIEW_GATE"
        rationale = selection["selected_value_rationale"]

    selected_material_name = (
        f"{anatomical_region} literature-derived material candidate"
        if selection["elastic_modulus_MPa"] is not None
        else "no_final_material_selected"
    )

    result = MaterialSelectionResult(
        case_id=case_id,
        material_selection_status=status,
        active_literature_search_required=active_required,
        literature_search_performed=literature_search_performed,
        literature_search_success=literature_search_success,
        material_model="linear_elastic_isotropic" if selection["elastic_modulus_MPa"] is not None else "not_selected",
        selected_material_name=selected_material_name,
        anatomical_region=anatomical_region,
        material_domain=material_domain,
        tissue_assumption="literature_required_no_patient_specific_claim",
        elastic_modulus_MPa=selection["elastic_modulus_MPa"],
        poisson_ratio=selection["poisson_ratio"],
        density_kg_m3=selection["density_kg_m3"],
        literature_query=queries,
        literature_support_level=literature_support_level,
        literature_records_count=len(literature_records),
        selected_sources=selection["selected_sources"],
        selected_value_rationale=rationale,
        uncertainty_level=selection["uncertainty_level"],
        human_review_required=human_review_required,
        next_agent=next_agent,
        warnings=warnings,
        blockers=blockers,
        output_json=str(output_json),
        property_table_csv=str(property_csv),
        literature_candidates_json=str(literature_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_target_understanding_json"] = str(target_path)
    data["source_segmentation_validation_json"] = str(validation_path)
    data["source_human_review_json"] = str(review_path)

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "material_selection_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Durum: {status}\n"
        f"- Anatomik hedef: {anatomical_region}\n"
        f"- Material domain: {material_domain}\n"
        f"- Literature search performed: {literature_search_performed}\n"
        f"- Literature records count: {len(literature_records)}\n"
        f"- Elastic modulus MPa: {selection['elastic_modulus_MPa']}\n"
        f"- Poisson ratio: {selection['poisson_ratio']}\n"
        f"- Next agent: {next_agent}\n"
        f"- Rationale: {rationale}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-07 Material Selection Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--target-understanding-json", default=None)
    parser.add_argument("--segmentation-validation-json", default=None)
    parser.add_argument("--human-review-json", default=None)
    parser.add_argument("--max-records-per-source", type=int, default=5)

    args = parser.parse_args()

    result = run_material_selection(MaterialSelectionInput(
        case_id=args.case_id,
        target_understanding_json=args.target_understanding_json,
        segmentation_validation_json=args.segmentation_validation_json,
        human_review_json=args.human_review_json,
        max_records_per_source=args.max_records_per_source,
    ))

    print("AGENT_07_MATERIAL_SELECTION_COMPLETED=True")
    print(f"MATERIAL_SELECTION_STATUS={result.material_selection_status}")
    print(f"ACTIVE_LITERATURE_SEARCH_REQUIRED={result.active_literature_search_required}")
    print(f"LITERATURE_SEARCH_PERFORMED={result.literature_search_performed}")
    print(f"LITERATURE_SEARCH_SUCCESS={result.literature_search_success}")
    print(f"LITERATURE_RECORDS_COUNT={result.literature_records_count}")
    print(f"MATERIAL_DOMAIN={result.material_domain}")
    print(f"MATERIAL_MODEL={result.material_model}")
    print(f"ELASTIC_MODULUS_MPA={result.elastic_modulus_MPa}")
    print(f"POISSON_RATIO={result.poisson_ratio}")
    print(f"UNCERTAINTY_LEVEL={result.uncertainty_level}")
    print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"WARNINGS={result.warnings}")
    print(f"BLOCKERS={result.blockers}")
    print(f"OUTPUT_JSON={result.output_json}")
    print(f"LITERATURE_CANDIDATES_JSON={result.literature_candidates_json}")


if __name__ == "__main__":
    main()
