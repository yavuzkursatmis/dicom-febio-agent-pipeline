# Publication Source Provenance

This clean staging tree was created from:

- Historical checkpoint: b58acf034
- Branch used as reference: publication-v1
- Original checkpoint date: 2026-07-20 20:14:08 +03:00
- Original checkpoint subject: Pass LangGraph clean T1 limited live run

The clean staging repository does not inherit the original Git history
because that history contained secrets, medical-image files, case outputs,
and large solver artifacts.

Ten source files used by the successful run but absent from the historical
commit were recovered from the private working repository. Their paths,
timestamps, sizes, and SHA-256 hashes are recorded in:

docs/provenance/RECOVERED_UNTRACKED_SOURCES.csv

No raw DICOM, NIfTI, STL, mesh, FEBio XPLT, PHI, user data, or secret values
are intended to be distributed through the public repository.
