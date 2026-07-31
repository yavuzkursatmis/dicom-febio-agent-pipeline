from pathlib import Path
import sys
import json

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
sys.path.insert(0, str(ROOT))

from agent_system.integration.langgraph_supervisor_workflow import run_live_graph


def main():
    case_id = "case_real_001_20260716_170655"

    result = run_live_graph(
        case_id=case_id,
        timeout_seconds=1800,
    )

    out_dir = ROOT / "agent_system" / "integration"
    out_json = out_dir / "LANGGRAPH_SUPERVISOR_LIVE_RUN_RESULT.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("LANGGRAPH_LIVE_RUN_COMPLETED=True")
    print("LANGGRAPH_FINAL_STATUS=" + str(result.get("final_status")))
    print("LANGGRAPH_NEXT_STAGE=" + str(result.get("next_stage")))
    print("LANGGRAPH_COMPLETED_AGENT_COUNT=" + str(len(result.get("completed_agents", []))))
    print("LANGGRAPH_COMPLETED_AGENTS=" + str(result.get("completed_agents", [])))
    print("LANGGRAPH_BLOCKERS=" + str(result.get("blockers", [])))
    print("LANGGRAPH_WARNINGS=" + str(result.get("warnings", [])))
    print("LIVE_RESULT_JSON=" + str(out_json))


if __name__ == "__main__":
    main()

