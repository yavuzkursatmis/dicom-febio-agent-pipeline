from pathlib import Path
import shutil
import subprocess
import sys

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

checks = []

def add_check(name, ok, detail=""):
    checks.append((name, ok, detail))

def check_import(module):
    try:
        __import__(module)
        return True
    except Exception as e:
        return False, str(e)

required_modules = [
    "langchain",
    "langgraph",
    "google.genai",
    "pydantic",
    "dotenv",
    "requests",
    "Bio",
    "habanero",
    "pandas",
    "pypdf",
    "semanticscholar",
    "chromadb",
    "sentence_transformers",
    "numpy",
    "scipy",
    "SimpleITK",
    "pydicom",
    "skimage",
    "trimesh",
    "meshio",
    "lxml",
    "torch",
    "totalsegmentator",
]

for module in required_modules:
    try:
        __import__(module)
        add_check(module, True, "OK")
    except Exception as e:
        add_check(module, False, str(e))

add_check("Gmsh", Path(r"C:\Tools\gmsh\gmsh.exe").exists(), r"C:\Tools\gmsh\gmsh.exe")
add_check("FEBio", Path(r"C:\Program Files\FEBioStudio\bin\febio4.exe").exists(), r"C:\Program Files\FEBioStudio\bin\febio4.exe")

slicer_found = list(Path.home().joinpath("AppData", "Local").rglob("Slicer.exe"))
add_check("3D Slicer", len(slicer_found) > 0, str(slicer_found[0]) if slicer_found else "Slicer.exe bulunamadı")

env_file = ROOT / "agent_system" / ".env"
add_check(".env", env_file.exists(), str(env_file))

ok_count = sum(1 for _, ok, _ in checks if ok)
fail_count = len(checks) - ok_count

report_lines = []
report_lines.append("KURULUM KONTROL RAPORU")
report_lines.append("")
report_lines.append(f"TOPLAM={len(checks)}")
report_lines.append(f"BASARILI={ok_count}")
report_lines.append(f"HATALI={fail_count}")
report_lines.append("")

for name, ok, detail in checks:
    status = "OK" if ok else "FAIL"
    report_lines.append(f"{status} | {name} | {detail}")

report_path = ROOT / "project_logs" / "installation_check_report.txt"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text("\n".join(report_lines), encoding="utf-8")

print("\n".join(report_lines))
print("")
print(f"Rapor yazıldı: {report_path}")
