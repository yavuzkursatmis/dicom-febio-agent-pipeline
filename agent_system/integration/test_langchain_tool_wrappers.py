from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.integration.langchain_tool_wrappers import get_tool_names, get_langchain_agent_tools


def main():
    tools = get_langchain_agent_tools()
    names = get_tool_names()

    print("LANGCHAIN_TOOL_WRAPPERS_IMPORT_OK=True")
    print("LANGCHAIN_TOOL_COUNT=" + str(len(tools)))
    print("LANGCHAIN_TOOL_NAMES=" + str(names))

    required = [
        "agent08_geometry_preparation",
        "agent09_volume_mesh_generation",
        "agent10_febio_model_generation",
        "agent11_boundary_load_configuration",
        "agent11_review_validation",
        "agent12_febio_solver_execution",
        "agent13_solver_result_validation",
        "agent14_result_extraction",
        "agent15_result_interpretation_precheck",
        "agent16_academic_report_draft",
        "agent17_full_pipeline_audit",
    ]

    missing = [x for x in required if x not in names]

    print("MISSING_LANGCHAIN_TOOLS=" + str(missing))
    print("LANGCHAIN_TOOL_WRAPPERS_READY=" + str(len(missing) == 0))


if __name__ == "__main__":
    main()
