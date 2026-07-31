from pathlib import Path
import sys
import json

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.integration.langgraph_supervisor_workflow import (
    run_dry_graph,
    graph_metadata,
)


def main():
    case_id = "real_dicom_check_001_anon_T1"

    metadata = graph_metadata()
    result = run_dry_graph(case_id)

    out_dir = ROOT / "agent_system" / "integration"
    out_json = out_dir / "LANGGRAPH_SUPERVISOR_DRY_RUN_RESULT.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("LANGGRAPH_SUPERVISOR_IMPORT_OK=True")
    print("LANGGRAPH_AGENT_COUNT=" + str(metadata["agent_count"]))
    print("LANGGRAPH_ENTRY_POINT=" + metadata["entry_point"])
    print("LANGGRAPH_FINAL_STATUS=" + str(result.get("final_status")))
    print("LANGGRAPH_NEXT_STAGE=" + str(result.get("next_stage")))
    print("LANGGRAPH_COMPLETED_AGENT_COUNT=" + str(len(result.get("completed_agents", []))))
    print("LANGGRAPH_BLOCKERS=" + str(result.get("blockers", [])))
    print("LANGGRAPH_WARNINGS=" + str(result.get("warnings", [])))
    print("DRY_RUN_RESULT_JSON=" + str(out_json))


if __name__ == "__main__":
    main()
