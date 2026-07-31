from pathlib import Path

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
case_id = "real_dicom_check_001_anon_T1"

target_dirs = [
    ROOT / "cases" / case_id / "12_boundary_load_configuration",
    ROOT / "cases" / case_id / "13_solver_execution",
]

patterns = [
    "febio_model_solver_ready_candidate.xplt",
    "febio_model_solver_ready_candidate.plt",
    "febio_model_solver_ready_candidate.log",
]

deleted = []

for folder in target_dirs:
    for pattern in patterns:
        path = folder / pattern
        if path.exists():
            path.unlink()
            deleted.append(str(path))

print("AGENT12_STALE_SOLVER_OUTPUTS_CLEANED=True")
print("DELETED_FILES=" + str(deleted))
