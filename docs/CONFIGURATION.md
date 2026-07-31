# Runtime Configuration

## Project root

The public source tree does not depend on the original private Windows path.

By default, each Python module derives the repository root from its own
file location. The root can be overridden in PowerShell:

```powershell
$env:DICOM_FEBIO_PROJECT_ROOT = "D:\research\dicom_febio"
```

For a persistent user-level variable:

```powershell
[Environment]::SetEnvironmentVariable(
    "DICOM_FEBIO_PROJECT_ROOT",
    "D:\research\dicom_febio",
    "User"
)
```

Open a new PowerShell session after setting a persistent variable.

## External executables

Computer-specific executable paths must be supplied locally:

```text
FEBIO_EXECUTABLE
SLICER_EXECUTABLE
GMSH_EXECUTABLE
TETGEN_EXECUTABLE
GEMINI_API_KEY
```

Copy `.env.example` to `.env` for local use. Never commit the real `.env`.

## Validated publication environment

The publication checkpoint was validated with:

`	ext
3D Slicer 5.12.0
TotalSegmentator 2.15.0
Gmsh 4.15.2
FEBio 4.12.0
FEBioStudio 3.1
Python Python 3.11.1
`

Exact Python package versions are stored in
equirements-core-lock.txt. Optional external-AI connectivity is isolated
in equirements-optional-ai-lock.txt. Executable hashes are stored in
docs/EXECUTABLE_HASHES.csv.

The paths recorded in the hash table describe the validated workstation.
Other installations may use different local paths through the environment
variables defined in .env.example.
