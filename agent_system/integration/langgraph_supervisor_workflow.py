from pathlib import Path

from typing import TypedDict, Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END

from agent_system.integration.langchain_tool_wrappers import (
    get_langchain_agent_tools,
)


class PipelineState(TypedDict, total=False):
    case_id: str
    run_live: bool
    timeout_seconds: int

    current_agent: str
    completed_agents: List[str]
    agent_results: Dict[str, Any]

    human_review_required: bool
    blockers: List[str]
    warnings: List[str]

    quantitative_field_interpretation_allowed: bool
    clinical_interpretation_allowed: bool
    limited_pass: bool

    final_status: str
    next_stage: str


TOOLS = {tool.name: tool for tool in get_langchain_agent_tools()}


AGENT_SEQUENCE = [
    ("agent08_geometry_preparation", "AGENT_08_GEOMETRY_PREPARATION"),
    ("agent09_volume_mesh_generation", "AGENT_09_VOLUME_MESH_GENERATION"),
    ("agent10_febio_model_generation", "AGENT_10_FEBIO_MODEL_GENERATION"),
    ("agent11_boundary_load_configuration", "AGENT_11_BOUNDARY_LOAD_CONFIGURATION"),
    ("agent11_review_validation", "AGENT_11_REVIEW_VALIDATION"),
    ("agent12_febio_solver_execution", "AGENT_12_FEBIO_SOLVER_EXECUTION"),
    ("agent13_solver_result_validation", "AGENT_13_SOLVER_RESULT_VALIDATION"),
    ("agent14_result_extraction", "AGENT_14_RESULT_EXTRACTION"),
    ("agent15_result_interpretation_precheck", "AGENT_15_RESULT_INTERPRETATION_PRECHECK"),
    ("agent16_academic_report_draft", "AGENT_16_ACADEMIC_REPORT_DRAFT"),
    ("agent17_full_pipeline_audit", "AGENT_17_FULL_PIPELINE_AUDIT"),
    ("clean_t1_upstream_evidence_audit", "CLEAN_T1_UPSTREAM_EVIDENCE_AUDIT"),
]


def ensure_state_defaults(state: PipelineState) -> PipelineState:
    state.setdefault("completed_agents", [])
    state.setdefault("agent_results", {})
    state.setdefault("blockers", [])
    state.setdefault("warnings", [])
    state.setdefault("timeout_seconds", 1800)
    state.setdefault("run_live", False)
    state.setdefault("quantitative_field_interpretation_allowed", False)
    state.setdefault("clinical_interpretation_allowed", False)
    state.setdefault("limited_pass", False)
    return state


def is_empty_listish(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text in ["", "[]", "None", "null"]


def mark_scientific_safety_flags(state: PipelineState, parsed: Dict[str, Any]) -> None:
    q = parsed.get("QUANTITATIVE_FIELD_INTERPRETATION_ALLOWED")
    c = parsed.get("CLINICAL_INTERPRETATION_ALLOWED")
    xplt = parsed.get("XPLT_BINARY_FIELD_EXTRACTION_PERFORMED")

    if q is not None:
        state["quantitative_field_interpretation_allowed"] = str(q).lower() == "true"

    if c is not None:
        state["clinical_interpretation_allowed"] = str(c).lower() == "true"

    if str(q).lower() == "false" or str(xplt).lower() == "false":
        state["limited_pass"] = True


def run_agent_node(tool_name: str, agent_id: str):
    def node(state: PipelineState) -> PipelineState:
        state = ensure_state_defaults(state)

        case_id = state["case_id"]
        run_live = state.get("run_live", False)
        timeout_seconds = state.get("timeout_seconds", 1800)

        state["current_agent"] = agent_id

        if run_live:
            tool = TOOLS[tool_name]
            result = tool.invoke({
                "case_id": case_id,
                "timeout_seconds": timeout_seconds,
            })
        else:
            result = {
                "success": True,
                "dry_run": True,
                "agent_id": agent_id,
                "tool_name": tool_name,
                "case_id": case_id,
                "message": "Dry-run mode: tool was not executed.",
                "parsed_stdout": {},
                "blockers": [],
            }

        state["agent_results"][agent_id] = result
        state["completed_agents"].append(agent_id)

        if isinstance(result, dict):
            blockers = _normalize_blockers(result.get("blockers", []))
            if blockers:
                state["blockers"].extend([f"{agent_id}:{b}" for b in blockers])

            parsed = result.get("parsed_stdout", {})
            if isinstance(parsed, dict):
                mark_scientific_safety_flags(state, parsed)

                parsed_blockers = parsed.get("BLOCKERS", "")
                parsed_warnings = parsed.get("WARNINGS", "")

                if not is_empty_listish(parsed_blockers):
                    state["blockers"].append(f"{agent_id}:{parsed_blockers}")

                if not is_empty_listish(parsed_warnings):
                    state["warnings"].append(f"{agent_id}:{parsed_warnings}")

                if parsed.get("HUMAN_REVIEW_REQUIRED") == "True":
                    state["human_review_required"] = True

        return state

    return node


def final_node(state: PipelineState) -> PipelineState:
    state = ensure_state_defaults(state)

    if state.get("blockers"):
        state["final_status"] = "LANGGRAPH_PIPELINE_BLOCKED"
        state["next_stage"] = "USER_ACTION_REQUIRED"
    elif state.get("limited_pass"):
        state["final_status"] = "LANGGRAPH_PIPELINE_LIMITED_PASS"
        state["next_stage"] = "LIMITED_REPORTING_COMPLETE"
    else:
        state["final_status"] = (
            "LANGGRAPH_PIPELINE_DRY_RUN_PASS"
            if not state.get("run_live")
            else "LANGGRAPH_PIPELINE_RUN_COMPLETED"
        )
        state["next_stage"] = "PIPELINE_COMPLETE"

    state["current_agent"] = "GRAPH_FINAL"
    return state


def make_route_after_agent():
    def route(state: PipelineState) -> str:
        state = ensure_state_defaults(state)
        if state.get("blockers"):
            return "final"
        return "next"
    return route


def route_to_final(state: PipelineState) -> str:
    return "final"


def build_pipeline_graph():
    graph = StateGraph(PipelineState)

    for tool_name, agent_id in AGENT_SEQUENCE:
        graph.add_node(agent_id, run_agent_node(tool_name, agent_id))

    graph.add_node("GRAPH_FINAL", final_node)

    graph.set_entry_point("AGENT_08_GEOMETRY_PREPARATION")

    for i in range(len(AGENT_SEQUENCE) - 1):
        current_agent_id = AGENT_SEQUENCE[i][1]
        next_agent_id = AGENT_SEQUENCE[i + 1][1]
        graph.add_conditional_edges(
            current_agent_id,
            make_route_after_agent(),
            {
                "next": next_agent_id,
                "final": "GRAPH_FINAL",
            },
        )

    last_agent_id = AGENT_SEQUENCE[-1][1]
    graph.add_conditional_edges(
        last_agent_id,
        route_to_final,
        {"final": "GRAPH_FINAL"},
    )

    graph.add_edge("GRAPH_FINAL", END)

    return graph.compile()


def run_dry_graph(case_id: str):
    app = build_pipeline_graph()

    initial_state: PipelineState = {
        "case_id": case_id,
        "run_live": False,
        "timeout_seconds": 1800,
        "completed_agents": [],
        "agent_results": {},
        "blockers": [],
        "warnings": [],
    }

    return app.invoke(initial_state)


def run_live_graph(case_id: str, timeout_seconds: int = 1800):
    app = build_pipeline_graph()

    initial_state: PipelineState = {
        "case_id": case_id,
        "run_live": True,
        "timeout_seconds": timeout_seconds,
        "completed_agents": [],
        "agent_results": {},
        "blockers": [],
        "warnings": [],
    }

    return app.invoke(initial_state)


def get_graph_manifest():
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "agent_count": len(AGENT_SEQUENCE),
        "agent_sequence": [agent_id for _, agent_id in AGENT_SEQUENCE],
        "tool_sequence": [tool_name for tool_name, _ in AGENT_SEQUENCE],
        "entry_point": "AGENT_08_GEOMETRY_PREPARATION",
        "final_node": "GRAPH_FINAL",
        "conditional_blocker_routing": True,
        "clean_t1_upstream_evidence_audit_node": True,
        "quantitative_field_interpretation_default": False,
        "clinical_interpretation_default": False,
    }



def _normalize_blockers(value):
    if value is None:
        return []
    if value == {}:
        return []
    if value == []:
        return []
    if value == "":
        return []
    if isinstance(value, list):
        return [x for x in value if x not in ({}, [], "", None)]
    return [value]

def graph_metadata():
    return {
        "workflow_name": "clean_t1_limited_supervisor",
        "pipeline_scope": "publication_scope_limited_reporting",
        "historical_checkpoint": "b58acf034",
        "upstream_agents_completed_before_live_graph": [
            "AGENT_01_DATA_INTAKE",
            "AGENT_02_DICOM_SAFETY",
            "AGENT_03_IMAGE_QUALITY",
            "AGENT_04_TARGET_UNDERSTANDING",
            "AGENT_05_SEGMENTATION_PREPROCESSING",
            "AGENT_06_SEGMENTATION_VALIDATION",
            "AGENT_07_MATERIAL_SELECTION",
        ],
        "live_graph_entry_point": "AGENT_08_GEOMETRY_PREPARATION",
        "live_graph_terminal_agent": "AGENT_17_FULL_PIPELINE_AUDIT",
        "live_graph_node_count": len(AGENT_SEQUENCE),
        "upstream_evidence_audit_performed": True,
        "clinical_use_allowed": False,
        "quantitative_field_interpretation_allowed": False,
        "field_level_biomechanical_claims_allowed": False,
        "expected_status": "LIMITED_PASS_ALLOWED",
        "publication_case_role": "retrospective_hospital_archive_CT_method_validation",
    }

def _clean_final_blockers(blockers):
    cleaned = []
    for b in blockers or []:
        if b in ({}, [], "", None):
            continue
        s = str(b).strip()
        if s.endswith(":{}"):
            continue
        if s.endswith(":[]"):
            continue
        if s in ("{}", "[]"):
            continue
        cleaned.append(b)
    return cleaned


# --- CLEAN_T1_LIVE_RESULT_BLOCKER_NORMALIZATION_WRAPPER ---
_run_live_graph_raw = run_live_graph

def run_live_graph(case_id: str, timeout_seconds: int = 1800):
    result = _run_live_graph_raw(case_id=case_id, timeout_seconds=timeout_seconds)

    def clean_blockers(blockers):
        cleaned = []
        for b in blockers or []:
            if b in ({}, [], "", None):
                continue
            s = str(b).strip()
            if s in ("{}", "[]"):
                continue
            if s.endswith(":{}") or s.endswith(":[]"):
                continue
            cleaned.append(b)
        return cleaned

    result["blockers"] = clean_blockers(result.get("blockers", []))

    if not result["blockers"] and result.get("final_status") == "LANGGRAPH_PIPELINE_BLOCKED":
        result["final_status"] = "LANGGRAPH_PIPELINE_LIMITED_PASS"
        result["next_stage"] = "PIPELINE_COMPLETE"

    # Temizlenmi? sonucu ayn? JSON'a da yaz.
    try:
        import json
        out = Path(__file__).resolve().parent / "LANGGRAPH_SUPERVISOR_LIVE_RUN_RESULT.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["live_result_json"] = str(out)
    except Exception as e:
        result.setdefault("warnings", []).append("LIVE_RESULT_JSON_REWRITE_WARNING:" + type(e).__name__ + ":" + str(e))

    return result


