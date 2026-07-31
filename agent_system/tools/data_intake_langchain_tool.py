from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.data_intake_schema import DataIntakeInput
from agent_system.agents.data_intake_agent import run_data_intake


def data_intake_tool_func(
    case_id: str,
    input_path: str,
    anatomical_target: str,
    analysis_type: str,
    test_application_region: str,
    user_notes_optional: str = "",
):
    """
    Kullanıcı verisini alır, veri türünü tanır, case klasörünü oluşturur
    ve bir sonraki ajanı belirler.
    """
    user_input = DataIntakeInput(
        case_id=case_id,
        input_path=input_path,
        anatomical_target=anatomical_target,
        analysis_type=analysis_type,
        test_application_region=test_application_region,
        user_notes_optional=user_notes_optional,
    )

    result = run_data_intake(user_input)
    return result.model_dump()


data_intake_tool = StructuredTool.from_function(
    name="data_intake_tool",
    description=(
        "Kullanıcının yüklediği DICOM, NIfTI veya manuel maske verisini tanır. "
        "Case klasörünü oluşturur, DATA_INTAKE_RESULT.json dosyasını yazar "
        "ve sonraki ajanı belirler."
    ),
    func=data_intake_tool_func,
    args_schema=DataIntakeInput,
)
