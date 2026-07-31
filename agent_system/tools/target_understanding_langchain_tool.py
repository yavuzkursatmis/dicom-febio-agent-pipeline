from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.target_understanding_schema import TargetUnderstandingInput
from agent_system.agents.target_understanding_agent import run_target_understanding


def target_understanding_tool_func(
    case_id: str,
    data_intake_json: str = None,
    image_quality_json: str = None,
):
    user_input = TargetUnderstandingInput(
        case_id=case_id,
        data_intake_json=data_intake_json,
        image_quality_json=image_quality_json,
    )

    result = run_target_understanding(user_input)
    return result.model_dump()


target_understanding_tool = StructuredTool.from_function(
    name="target_understanding_tool",
    description=(
        "Kullanıcının anatomik hedef, analiz tipi ve test uygulanacak bölge bilgisini "
        "biyomekanik analiz hattı için standart teknik forma çevirir. "
        "Örn: L1 vertebra, axial_compression, superior_endplate."
    ),
    func=target_understanding_tool_func,
    args_schema=TargetUnderstandingInput,
)
