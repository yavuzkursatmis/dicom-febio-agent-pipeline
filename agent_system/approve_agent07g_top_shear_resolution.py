from pathlib import Path
import json

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
case_id = "real_dicom_check_001_anon_T1"

gate_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07G_SHEAR_WARNING_REVIEW_GATE_RESULT.json"
review_path = ROOT / "cases" / case_id / "08_material_review" / "AGENT07G_SHEAR_WARNING_REVIEW_INPUT.json"

gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
review = json.loads(review_path.read_text(encoding="utf-8-sig"))

candidate = gate["allowed_resolution_candidates"][0]

review["reviewer_decision"] = "APPROVED"
review["approved_resolution_candidate_id"] = candidate["resolution_candidate_id"]
review["approved_for_agent08"] = True
review["approved_next_agent"] = "AGENT_08_GEOMETRY_MESH_PREPARATION"
review["clinical_use"] = False
review["reviewer_notes"] = "Pipeline development için agent-derived shear warning resolution candidate onaylandı. Manuel değer girilmedi."

review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")

print("AGENT07G_TOP_RESOLUTION_CANDIDATE_APPROVED_IN_REVIEW_INPUT=True")
print("APPROVED_RESOLUTION_CANDIDATE_ID=" + candidate["resolution_candidate_id"])
print("RESOLVED_SHEAR_SCALES=" + str(candidate["resolved_shear_scales"]))
