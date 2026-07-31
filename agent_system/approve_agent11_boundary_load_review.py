from pathlib import Path
import json

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
case_id = "case_real_001_20260716_170655"

review_path = ROOT / "cases" / case_id / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_INPUT.json"
review = json.loads(review_path.read_text(encoding="utf-8-sig"))

review["reviewer_decision"] = "APPROVED"
review["approved_boundary_load_candidate"] = True
review["approved_for_solver_configuration"] = True
review["approved_next_agent"] = "AGENT_12_FEBIO_SOLVER_EXECUTION"
review["clinical_use"] = False
review["reviewer_notes"] = "Protocol-derived axial compression boundary/load candidate onaylandı. Kullanıcı manuel kuvvet, displacement, moment, torque veya FEBio düzenlemesi yapmadı."

review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")

print("AGENT11_BOUNDARY_LOAD_REVIEW_INPUT_APPROVED=True")
print("APPROVED_NEXT_AGENT=AGENT_12_FEBIO_SOLVER_EXECUTION")

