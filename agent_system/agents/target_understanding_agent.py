from pathlib import Path
import argparse
import json
import sys
from datetime import datetime

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.schemas.target_understanding_schema import (
    TargetUnderstandingInput,
    TargetUnderstandingResult,
)
from agent_system.tools.target_understanding_tools import try_gemini_target_understanding


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def append_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def default_data_intake_json(case_id: str):
    return ROOT / "cases" / case_id / "00_input_manifest" / "DATA_INTAKE_RESULT.json"


def default_image_quality_json(case_id: str):
    return ROOT / "cases" / case_id / "02_image_quality" / "IMAGE_QUALITY_RESULT.json"


def blocked_result(case_id: str, output_json: Path, blocker: str):
    result = TargetUnderstandingResult(
        case_id=case_id,
        target_understanding_status="BLOCKED_BY_IMAGE_QUALITY",
        standardized_anatomical_target="",
        segmentation_target="",
        standardized_analysis_type="",
        standardized_test_application_region="",
        load_region="",
        boundary_condition_hint="",
        confidence_level="low",
        llm_confidence_level="not_used",
        llm_human_review_required=True,
        human_review_required=True,
        llm_used=False,
        canonicalization_applied=False,
        reasoning_summary="Target understanding was blocked by previous pipeline stage.",
        validation_notes=["Previous pipeline stage blocked target understanding."],
        next_agent="USER_ACTION_REQUIRED",
        warnings=[],
        blockers=[blocker],
        output_json=str(output_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    save_json(output_json, data)

    return result


def run_target_understanding(user_input: TargetUnderstandingInput) -> TargetUnderstandingResult:
    case_id = user_input.case_id

    data_intake_path = Path(user_input.data_intake_json) if user_input.data_intake_json else default_data_intake_json(case_id)
    image_quality_path = Path(user_input.image_quality_json) if user_input.image_quality_json else default_image_quality_json(case_id)

    output_dir = ROOT / "cases" / case_id / "03_target_understanding"
    output_json = output_dir / "TARGET_UNDERSTANDING_RESULT.json"

    if not data_intake_path.exists():
        return blocked_result(case_id, output_json, "DATA_INTAKE_RESULT_NOT_FOUND")

    if not image_quality_path.exists():
        return blocked_result(case_id, output_json, "IMAGE_QUALITY_RESULT_NOT_FOUND")

    data_intake = load_json(data_intake_path)
    image_quality = load_json(image_quality_path)

    image_quality_status = image_quality.get("image_quality_status", "")
    if image_quality_status not in ["IMAGE_QUALITY_PASS", "IMAGE_QUALITY_WARNING"]:
        return blocked_result(case_id, output_json, "IMAGE_QUALITY_NOT_PASSED")

    anatomical_target = data_intake.get("anatomical_target", "")
    analysis_type = data_intake.get("analysis_type", "")
    test_application_region = data_intake.get("test_application_region", "")

    interpreted = try_gemini_target_understanding(
        anatomical_target=anatomical_target,
        analysis_type=analysis_type,
        test_application_region=test_application_region,
        image_quality_status=image_quality_status,
        warnings=image_quality.get("warnings", []),
    )

    result = TargetUnderstandingResult(
        case_id=case_id,
        target_understanding_status=interpreted["target_understanding_status"],
        standardized_anatomical_target=interpreted["standardized_anatomical_target"],
        segmentation_target=interpreted["segmentation_target"],
        standardized_analysis_type=interpreted["standardized_analysis_type"],
        standardized_test_application_region=interpreted["standardized_test_application_region"],
        load_region=interpreted["load_region"],
        boundary_condition_hint=interpreted["boundary_condition_hint"],
        confidence_level=interpreted["confidence_level"],
        llm_confidence_level=interpreted["llm_confidence_level"],
        llm_human_review_required=interpreted["llm_human_review_required"],
        human_review_required=interpreted["human_review_required"],
        llm_used=interpreted["llm_used"],
        canonicalization_applied=interpreted["canonicalization_applied"],
        reasoning_summary=interpreted["reasoning_summary"],
        validation_notes=interpreted["validation_notes"],
        next_agent=interpreted["next_agent"],
        warnings=interpreted["warnings"],
        blockers=interpreted["blockers"],
        output_json=str(output_json),
    )

    data = result.model_dump()
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    data["clinical_use"] = False
    data["source_data_intake_json"] = str(data_intake_path)
    data["source_image_quality_json"] = str(image_quality_path)

    save_json(output_json, data)

    append_text(
        ROOT / "paper_notes" / "target_understanding_notes.md",
        f"\n## Case: {case_id}\n"
        f"- Tarih: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Durum: {result.target_understanding_status}\n"
        f"- Anatomik hedef: {result.standardized_anatomical_target}\n"
        f"- Segmentasyon hedefi: {result.segmentation_target}\n"
        f"- Analiz tipi: {result.standardized_analysis_type}\n"
        f"- Test bölgesi: {result.standardized_test_application_region}\n"
        f"- Load region: {result.load_region}\n"
        f"- System confidence: {result.confidence_level}\n"
        f"- LLM confidence: {result.llm_confidence_level}\n"
        f"- LLM kullanıldı: {result.llm_used}\n"
        f"- Canonicalization: {result.canonicalization_applied}\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Agent-04 Target Understanding Agent")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-intake-json", default=None)
    parser.add_argument("--image-quality-json", default=None)

    args = parser.parse_args()

    result = run_target_understanding(TargetUnderstandingInput(
        case_id=args.case_id,
        data_intake_json=args.data_intake_json,
        image_quality_json=args.image_quality_json,
    ))

    print("AGENT_04_TARGET_UNDERSTANDING_COMPLETED=True")
    print(f"TARGET_UNDERSTANDING_STATUS={result.target_understanding_status}")
    print(f"STANDARDIZED_ANATOMICAL_TARGET={result.standardized_anatomical_target}")
    print(f"SEGMENTATION_TARGET={result.segmentation_target}")
    print(f"STANDARDIZED_ANALYSIS_TYPE={result.standardized_analysis_type}")
    print(f"LOAD_REGION={result.load_region}")
    print(f"CONFIDENCE_LEVEL={result.confidence_level}")
    print(f"LLM_CONFIDENCE_LEVEL={result.llm_confidence_level}")
    print(f"LLM_HUMAN_REVIEW_REQUIRED={result.llm_human_review_required}")
    print(f"HUMAN_REVIEW_REQUIRED={result.human_review_required}")
    print(f"LLM_USED={result.llm_used}")
    print(f"CANONICALIZATION_APPLIED={result.canonicalization_applied}")
    print(f"NEXT_AGENT={result.next_agent}")
    print(f"WARNINGS={result.warnings}")
    print(f"BLOCKERS={result.blockers}")
    print(f"OUTPUT_JSON={result.output_json}")


if __name__ == "__main__":
    main()
