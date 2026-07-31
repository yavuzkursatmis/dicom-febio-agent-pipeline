import json
import re
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def normalize_text(text: str) -> str:
    if text is None:
        return ""

    text = str(text).strip().lower()

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }

    for tr, en in replacements.items():
        text = text.replace(tr, en)

    text = re.sub(r"\s+", " ", text)
    return text


def normalize_confidence(value: str) -> str:
    value = normalize_text(value)

    if value in ["high", "medium", "low"]:
        return value

    return "medium"


def classify_anatomical_target(anatomical_target: str) -> Dict[str, str]:
    t = normalize_text(anatomical_target)

    vertebra_match = re.search(r"\b(l[1-5]|t[1-9]|t1[0-2]|c[1-7])\b", t)

    if vertebra_match:
        vertebra = vertebra_match.group(1).upper()
        return {
            "standardized_anatomical_target": f"{vertebra} vertebra",
            "segmentation_target": f"{vertebra} vertebra",
        }

    if "vertebra" in t or "omur" in t:
        return {
            "standardized_anatomical_target": "unspecified vertebra",
            "segmentation_target": "vertebra",
        }

    cleaned = anatomical_target.strip()
    return {
        "standardized_anatomical_target": cleaned,
        "segmentation_target": cleaned,
    }


def classify_analysis_type(analysis_type: str) -> str:
    t = normalize_text(analysis_type)

    if any(x in t for x in ["aksiyel", "axial", "basma", "compression", "kompresyon"]):
        return "axial_compression"

    if any(x in t for x in ["cekme", "tension", "tensile"]):
        return "tension"

    if any(x in t for x in ["egilme", "bending", "fleksiyon", "flexion"]):
        return "bending"

    if any(x in t for x in ["burulma", "torsion", "torsiyon"]):
        return "torsion"

    return "unknown"


def classify_load_region(test_application_region: str) -> Dict[str, str]:
    t = normalize_text(test_application_region)

    if any(x in t for x in ["ust", "superior", "upper"]):
        return {
            "standardized_test_application_region": "superior endplate",
            "load_region": "superior_endplate",
            "boundary_condition_hint": "Apply axial load on superior endplate; constrain inferior endplate."
        }

    if any(x in t for x in ["alt", "inferior", "lower"]):
        return {
            "standardized_test_application_region": "inferior endplate",
            "load_region": "inferior_endplate",
            "boundary_condition_hint": "Apply load or constraint on inferior endplate depending on model setup."
        }

    if any(x in t for x in ["govde", "body", "centrum"]):
        return {
            "standardized_test_application_region": "vertebral body",
            "load_region": "vertebral_body",
            "boundary_condition_hint": "Define load region on vertebral body surface after segmentation."
        }

    return {
        "standardized_test_application_region": test_application_region.strip(),
        "load_region": "unknown",
        "boundary_condition_hint": "Human review required to define load and boundary regions."
    }


def deterministic_target_understanding(
    anatomical_target: str,
    analysis_type: str,
    test_application_region: str,
) -> Dict[str, Any]:

    anatomical = classify_anatomical_target(anatomical_target)
    standardized_analysis_type = classify_analysis_type(analysis_type)
    region = classify_load_region(test_application_region)

    warnings = []
    blockers = []
    validation_notes = []

    if anatomical["segmentation_target"] == "":
        blockers.append("SEGMENTATION_TARGET_EMPTY")

    if standardized_analysis_type == "unknown":
        warnings.append("ANALYSIS_TYPE_UNCLEAR")

    if region["load_region"] == "unknown":
        warnings.append("LOAD_REGION_UNCLEAR")

    if not blockers and not warnings:
        status = "TARGET_UNDERSTANDING_PASS"
        confidence = "high"
        human_review = False
        next_agent = "SEGMENTATION_AGENT"
        validation_notes.append(
            "Deterministic validation confirmed anatomical target, analysis type, and load region."
        )
    elif blockers:
        status = "TARGET_UNDERSTANDING_FAIL"
        confidence = "low"
        human_review = True
        next_agent = "USER_ACTION_REQUIRED"
        validation_notes.append("Deterministic validation failed because required target information is missing.")
    else:
        status = "TARGET_UNDERSTANDING_NEEDS_REVIEW"
        confidence = "medium"
        human_review = True
        next_agent = "HUMAN_REVIEW_GATE"
        validation_notes.append("Deterministic validation requires human review because at least one field is unclear.")

    return {
        "target_understanding_status": status,
        "standardized_anatomical_target": anatomical["standardized_anatomical_target"],
        "segmentation_target": anatomical["segmentation_target"],
        "standardized_analysis_type": standardized_analysis_type,
        "standardized_test_application_region": region["standardized_test_application_region"],
        "load_region": region["load_region"],
        "boundary_condition_hint": region["boundary_condition_hint"],
        "confidence_level": confidence,
        "human_review_required": human_review,
        "next_agent": next_agent,
        "warnings": warnings,
        "blockers": blockers,
        "validation_notes": validation_notes,
    }


def extract_json_from_text(text: str) -> Dict[str, Any]:
    if text is None:
        raise ValueError("Empty LLM response.")

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")

    return json.loads(match.group(0))


def try_gemini_target_understanding(
    anatomical_target: str,
    analysis_type: str,
    test_application_region: str,
    image_quality_status: str,
    warnings: list,
) -> Dict[str, Any]:

    deterministic = deterministic_target_understanding(
        anatomical_target,
        analysis_type,
        test_application_region,
    )

    try:
        load_dotenv(ROOT / "agent_system" / ".env")

        import os
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found.")

        prompt_path = ROOT / "agent_system" / "prompts" / "target_understanding_prompt.md"
        prompt_base = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        prompt = f"""
{prompt_base}

Aşağıdaki girdileri standart teknik forma çevir.

anatomical_target: {anatomical_target}
analysis_type: {analysis_type}
test_application_region: {test_application_region}
image_quality_status: {image_quality_status}
warnings: {warnings}

Sadece geçerli JSON döndür.
"""

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        data = extract_json_from_text(response.text)

        required = [
            "standardized_anatomical_target",
            "segmentation_target",
            "standardized_analysis_type",
            "standardized_test_application_region",
            "load_region",
            "boundary_condition_hint",
            "confidence_level",
            "human_review_required",
            "reasoning_summary",
        ]

        for key in required:
            if key not in data:
                raise ValueError(f"Missing key in LLM output: {key}")

        llm_confidence = normalize_confidence(str(data.get("confidence_level", "medium")))
        llm_human_review = bool(data.get("human_review_required", True))

        result_warnings = []
        result_blockers = []
        validation_notes = list(deterministic["validation_notes"])

        if llm_confidence in ["medium", "low"]:
            result_warnings.append(f"LLM_CONFIDENCE_{llm_confidence.upper()}_PRESERVED")
            validation_notes.append(
                "LLM confidence was preserved separately and was not overwritten."
            )

        if deterministic["target_understanding_status"] == "TARGET_UNDERSTANDING_PASS":
            validation_notes.append(
                "System confidence was set by deterministic validation, not by overwriting LLM confidence."
            )

            return {
                "target_understanding_status": "TARGET_UNDERSTANDING_PASS",
                "standardized_anatomical_target": deterministic["standardized_anatomical_target"],
                "segmentation_target": deterministic["segmentation_target"],
                "standardized_analysis_type": deterministic["standardized_analysis_type"],
                "standardized_test_application_region": deterministic["standardized_test_application_region"],
                "load_region": deterministic["load_region"],
                "boundary_condition_hint": deterministic["boundary_condition_hint"],
                "confidence_level": "high",
                "llm_confidence_level": llm_confidence,
                "llm_human_review_required": llm_human_review,
                "human_review_required": False,
                "llm_used": True,
                "canonicalization_applied": True,
                "reasoning_summary": str(data.get("reasoning_summary", "")),
                "validation_notes": validation_notes,
                "next_agent": "SEGMENTATION_AGENT",
                "warnings": result_warnings,
                "blockers": result_blockers,
            }

        validation_notes.append(
            "Deterministic validation did not pass; human review or user action is required."
        )

        return {
            "target_understanding_status": deterministic["target_understanding_status"],
            "standardized_anatomical_target": deterministic["standardized_anatomical_target"],
            "segmentation_target": deterministic["segmentation_target"],
            "standardized_analysis_type": deterministic["standardized_analysis_type"],
            "standardized_test_application_region": deterministic["standardized_test_application_region"],
            "load_region": deterministic["load_region"],
            "boundary_condition_hint": deterministic["boundary_condition_hint"],
            "confidence_level": deterministic["confidence_level"],
            "llm_confidence_level": llm_confidence,
            "llm_human_review_required": llm_human_review,
            "human_review_required": deterministic["human_review_required"],
            "llm_used": True,
            "canonicalization_applied": True,
            "reasoning_summary": str(data.get("reasoning_summary", "")),
            "validation_notes": validation_notes,
            "next_agent": deterministic["next_agent"],
            "warnings": deterministic["warnings"] + result_warnings,
            "blockers": deterministic["blockers"],
        }

    except Exception as e:
        deterministic["warnings"].append(f"GEMINI_FALLBACK_USED={type(e).__name__}")
        deterministic["validation_notes"].append(
            "Gemini interpretation failed or was unavailable; deterministic fallback was used."
        )

        return {
            "target_understanding_status": deterministic["target_understanding_status"],
            "standardized_anatomical_target": deterministic["standardized_anatomical_target"],
            "segmentation_target": deterministic["segmentation_target"],
            "standardized_analysis_type": deterministic["standardized_analysis_type"],
            "standardized_test_application_region": deterministic["standardized_test_application_region"],
            "load_region": deterministic["load_region"],
            "boundary_condition_hint": deterministic["boundary_condition_hint"],
            "confidence_level": deterministic["confidence_level"],
            "llm_confidence_level": "unavailable",
            "llm_human_review_required": True,
            "human_review_required": deterministic["human_review_required"],
            "llm_used": False,
            "canonicalization_applied": True,
            "reasoning_summary": "Gemini interpretation failed or was unavailable; deterministic fallback was used.",
            "validation_notes": deterministic["validation_notes"],
            "next_agent": deterministic["next_agent"],
            "warnings": deterministic["warnings"],
            "blockers": deterministic["blockers"],
        }
