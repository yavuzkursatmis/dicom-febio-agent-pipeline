from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.tools.material_selection_langchain_tool import material_selection_tool


result = material_selection_tool.invoke({
    "case_id": "real_dicom_check_001_anon_T1",
    "max_records_per_source": 3
})

print("AGENT_07_LANGCHAIN_TOOL_TEST=True")
print("MATERIAL_SELECTION_STATUS=" + result["material_selection_status"])
print("ACTIVE_LITERATURE_SEARCH_REQUIRED=" + str(result["active_literature_search_required"]))
print("LITERATURE_SEARCH_PERFORMED=" + str(result["literature_search_performed"]))
print("LITERATURE_SEARCH_SUCCESS=" + str(result["literature_search_success"]))
print("LITERATURE_RECORDS_COUNT=" + str(result["literature_records_count"]))
print("MATERIAL_DOMAIN=" + result["material_domain"])
print("MATERIAL_MODEL=" + result["material_model"])
print("ELASTIC_MODULUS_MPA=" + str(result["elastic_modulus_MPa"]))
print("POISSON_RATIO=" + str(result["poisson_ratio"]))
print("UNCERTAINTY_LEVEL=" + result["uncertainty_level"])
print("HUMAN_REVIEW_REQUIRED=" + str(result["human_review_required"]))
print("NEXT_AGENT=" + result["next_agent"])
print("WARNINGS=" + str(result["warnings"]))
print("BLOCKERS=" + str(result["blockers"]))
print("OUTPUT_JSON=" + result["output_json"])
