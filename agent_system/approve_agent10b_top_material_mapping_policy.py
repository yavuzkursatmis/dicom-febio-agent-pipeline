from pathlib import Path
import json

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
case_id = "real_dicom_check_001_anon_T1"

gate_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_GATE_RESULT.json"
review_path = ROOT / "cases" / case_id / "11_febio_model_generation" / "AGENT10B_MATERIAL_MAPPING_POLICY_REVIEW_INPUT.json"

gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
review = json.loads(review_path.read_text(encoding="utf-8-sig"))

candidate = gate["allowed_policy_candidates"][0]

review["reviewer_decision"] = "APPROVED"
review["approved_policy_candidate_id"] = candidate["policy_candidate_id"]
review["approved_for_agent10_retry"] = True
review["approved_next_agent"] = "AGENT_10_FEBIO_MODEL_GENERATION_RETRY"
review["clinical_use"] = False
review["reviewer_notes"] = "Pipeline development için agent-derived material mapping policy onaylandı. Manuel değer girilmedi."

review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")

print("AGENT10B_TOP_MAPPING_POLICY_APPROVED_IN_REVIEW_INPUT=True")
print("APPROVED_POLICY_CANDIDATE_ID=" + candidate["policy_candidate_id"])
print("POLICY_TYPE=" + candidate["policy_type"])
print("DENSITY_FLOOR_G_CM3=" + str(candidate["density_floor_g_cm3"]))
print("INVALID_DENSITY_COUNT=" + str(candidate["invalid_density_count"]))
print("INVALID_DENSITY_FRACTION=" + str(candidate["invalid_density_fraction"]))
