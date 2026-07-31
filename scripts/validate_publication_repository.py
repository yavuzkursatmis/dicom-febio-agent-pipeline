from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "README_TR.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "DATA_AVAILABILITY.md",
    "ETHICS_AND_PRIVACY.md",
    "AI_USAGE_DISCLOSURE.md",
    "LICENSE",
    "CITATION.cff.template",
    ".env.example",
    ".gitignore",
    "requirements-publication.in",
    "docs/CONFIGURATION.md",
    "docs/WORKFLOW.md",
    "docs/WORKFLOW_TR.md",
    "docs/provenance/RECOVERED_UNTRACKED_SOURCES.csv",
]

FORBIDDEN_SUFFIXES = {
    ".dcm",
    ".dicom",
    ".nii",
    ".nrrd",
    ".mha",
    ".mhd",
    ".stl",
    ".obj",
    ".ply",
    ".vtk",
    ".vtu",
    ".msh",
    ".feb",
    ".xplt",
    ".pfx",
    ".p12",
    ".pem",
    ".key",
}

FORBIDDEN_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".xml",
    ".csv",
    ".cff",
    ".example",
    ".ps1",
}

SECRET_PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "OpenAI-style key": re.compile(r"\bsk-[0-9A-Za-z_-]{20,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[0-9A-Za-z]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
}

PRIVATE_ROOT = "\\".join(
    (
        "C:",
        "dicom_febio_agent_research",
    )
)

errors: list[str] = []
warnings: list[str] = []


for relative_path in REQUIRED:
    if not (ROOT / relative_path).is_file():
        errors.append(f"Missing required file: {relative_path}")


for path in ROOT.rglob("*"):
    if "_publication_audit" in path.parts:
        continue

    if ".git" in path.parts:
        continue

    if not path.is_file():
        continue

    relative_path = path.relative_to(ROOT)

    if path.name.lower() in FORBIDDEN_NAMES:
        errors.append(f"Forbidden file name: {relative_path}")

    if (
        path.suffix.lower() in FORBIDDEN_SUFFIXES
        or path.name.lower().endswith(".nii.gz")
    ):
        errors.append(f"Forbidden data/binary file: {relative_path}")

    if path.stat().st_size >= 5 * 1024 * 1024:
        warnings.append(f"File is at least 5 MB: {relative_path}")

    if path.suffix.lower() not in TEXT_SUFFIXES:
        continue

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        continue

    if PRIVATE_ROOT.lower() in text.lower():
        errors.append(f"Private hardcoded path: {relative_path}")

    for category, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{category}: {relative_path}")


compile_pass = 0
compile_fail = 0

agent_root = ROOT / "agent_system"

if not agent_root.is_dir():
    errors.append("Missing agent_system directory.")
else:
    for path in agent_root.rglob("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_fail += 1
            errors.append(
                f"Compile failed: {path.relative_to(ROOT)}: {exc}"
            )
        else:
            compile_pass += 1


for cache in sorted(
    ROOT.rglob("__pycache__"),
    key=lambda item: len(item.parts),
    reverse=True,
):
    if not cache.is_dir():
        continue

    for child in cache.iterdir():
        if child.is_file():
            child.unlink()

    try:
        cache.rmdir()
    except OSError:
        pass


workflow_path = (
    ROOT
    / "agent_system"
    / "integration"
    / "langgraph_supervisor_workflow.py"
)

if not workflow_path.is_file():
    errors.append("Missing LangGraph supervisor workflow.")
else:
    workflow_text = workflow_path.read_text(encoding="utf-8-sig")

    expected_metadata = (
        '"live_graph_entry_point": '
        '"AGENT_08_GEOMETRY_PREPARATION"'
    )

    if expected_metadata not in workflow_text:
        errors.append(
            "Corrected Agent08 live-graph metadata not found."
        )

    misleading_metadata = (
        '"entry_point": "AGENT_01_DATA_INTAKE"'
    )

    if misleading_metadata in workflow_text:
        errors.append(
            "Misleading Agent01 live-graph entry metadata remains."
        )


summary = {
    "status": "PASS" if not errors else "FAIL",
    "python_compile_pass": compile_pass,
    "python_compile_fail": compile_fail,
    "errors": errors,
    "warnings": warnings,
    "license_active": (ROOT / "LICENSE").is_file(),
    "citation_active": (ROOT / "CITATION.cff").is_file(),
}

print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    )
)

report_path = (
    ROOT
    / "_publication_audit"
    / "repository_structure"
    / "REPOSITORY_VALIDATION.json"
)

report_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

report_path.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

sys.exit(0 if not errors else 1)

