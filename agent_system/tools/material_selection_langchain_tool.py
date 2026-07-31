from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool

from agent_system.schemas.material_selection_schema import MaterialSelectionInput
from agent_system.agents.material_selection_agent import run_material_selection


def material_selection_tool_func(
    case_id: str,
    target_understanding_json: str = None,
    segmentation_validation_json: str = None,
    human_review_json: str = None,
    max_records_per_source: int = 3,
):
    user_input = MaterialSelectionInput(
        case_id=case_id,
        target_understanding_json=target_understanding_json,
        segmentation_validation_json=segmentation_validation_json,
        human_review_json=human_review_json,
        max_records_per_source=max_records_per_source,
    )

    result = run_material_selection(user_input)
    return result.model_dump()


material_selection_tool = StructuredTool.from_function(
    name="material_selection_tool",
    description=(
        "Segmentasyonu doğrulanmış anatomik yapı için aktif akademik/literatür taraması yapar. "
        "Kaynak destekli elastisite modülü ve Poisson oranı çıkarılamazsa otomatik malzeme değeri atamaz. "
        "Literatür yetersizliğinde HUMAN_REVIEW_GATE kararı üretir."
    ),
    func=material_selection_tool_func,
    args_schema=MaterialSelectionInput,
)
