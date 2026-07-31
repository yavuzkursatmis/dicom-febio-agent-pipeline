from pathlib import Path
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from langgraph.graph import StateGraph, START, END

from agent_system.state import CaseState
from agent_system.tools.data_intake_langchain_tool import data_intake_tool


def data_intake_node(state: CaseState) -> CaseState:
    result = data_intake_tool.invoke({
        "case_id": state["case_id"],
        "input_path": state["input_path"],
        "anatomical_target": state["anatomical_target"],
        "analysis_type": state["analysis_type"],
        "test_application_region": state["test_application_region"],
        "user_notes_optional": state.get("user_notes_optional", ""),
    })

    state["current_agent"] = "DATA_INTAKE_AGENT"
    state["next_agent"] = result["next_agent"]
    state["data_status"] = result["data_status"]
    state["detected_input_type"] = result["detected_input_type"]
    state["file_count"] = result["file_count"]
    state["supported_format"] = result["supported_format"]
    state["warnings"] = result["warnings"]
    state["blockers"] = result["blockers"]
    state["data_intake_result"] = result

    return state


def build_agent01_graph():
    graph = StateGraph(CaseState)

    graph.add_node("data_intake_agent", data_intake_node)

    graph.add_edge(START, "data_intake_agent")
    graph.add_edge("data_intake_agent", END)

    return graph.compile()


agent01_graph = build_agent01_graph()
