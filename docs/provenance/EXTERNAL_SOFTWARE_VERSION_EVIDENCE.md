# External Software Version Evidence

The external scientific software used by the publication-scope workflow was
verified on the validated workstation as follows:

| Component | Version | Verification evidence |
|---|---:|---|
| 3D Slicer | 5.12.0 | Executable installation folder and Windows uninstall registry |
| Gmsh | 4.15.2 | gmsh.exe --version and gmsh.exe -version, exit code 0 |
| FEBio | 4.12.0 | ebio4.exe startup banner captured during a safe missing-input probe |
| FEBioStudio | 3.1 | Windows uninstall registry |

Executable SHA-256 values are recorded in docs/EXECUTABLE_HASHES.csv.

The FEBio probe intentionally used a nonexistent temporary input file. The
solver printed its version banner and then stopped with an expected input-file
error. No model was solved and no repository file was modified.
