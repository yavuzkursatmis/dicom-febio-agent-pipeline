from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.dicom_safety_schema import DicomSafetyInput
from agent_system.agents.dicom_safety_agent import run_dicom_safety


def dicom_safety_tool_func(
    case_id: str,
    data_intake_json: str = None,
):
    user_input = DicomSafetyInput(
        case_id=case_id,
        data_intake_json=data_intake_json,
    )

    result = run_dicom_safety(user_input)
    return result.model_dump()


dicom_safety_tool = StructuredTool.from_function(
    name="dicom_safety_tool",
    description=(
        "DICOM verisinin güvenli ve işlenebilir olup olmadığını kontrol eder. "
        "DICOM header taraması yapar, CT olup olmadığını kontrol eder, "
        "PHI ve burned-in annotation risklerini değerlendirir."
    ),
    func=dicom_safety_tool_func,
    args_schema=DicomSafetyInput,
)
