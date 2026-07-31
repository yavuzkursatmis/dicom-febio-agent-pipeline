# Human-in-the-Loop Agent Workflow from CT/DICOM to FEBio

> **Publication status:** pre-release scientific software repository.  
> **Clinical status:** research use only; not a medical device and not for diagnosis, treatment planning, or clinical decision support.

## Purpose

This repository contains the publication-scope source code and technical documentation for a modular autonomous/semi-autonomous workflow that transforms retrospective hospital-archive CT/DICOM data into a finite-element biomechanics model.

The validated technical case concerns T1 vertebral axial compression.

## Verified workflow boundary

The publication does **not** claim that a single LangGraph execution ran Agents 01–17 from raw DICOM input.

The verified sequence is:

1. Agents 01–07 were completed and reviewed upstream: data intake, DICOM safety, image-quality assessment, target definition, segmentation/preprocessing, segmentation validation, and material review.
2. The successful live LangGraph run began at Agent 08.
3. The graph orchestrated geometry preparation, volume meshing, FEBio model generation, boundary/load configuration and review, solver execution, solver validation, limited extraction, interpretation precheck, report drafting, full-pipeline audit, and upstream-evidence audit.

Historical publication checkpoint:

```text
b58acf034 — Pass LangGraph clean T1 limited live run
```

## Scientific claim boundary

The repository supports:

- technical feasibility from validated upstream evidence to FEBio execution;
- traceable human-review gates;
- solver normal-termination checking;
- limited, safety-constrained reporting.

It does not establish:

- clinical diagnostic performance;
- experimental validation of the T1 model;
- patient-specific clinical prediction;
- validated spatial stress/strain/displacement field interpretation;
- unrestricted autonomous operation.

## High-level workflow

```text
Retrospective CT/DICOM
→ safety and quality checks
→ target definition
→ TotalSegmentator-assisted segmentation
→ human review in 3D Slicer
→ surface geometry
→ tetrahedral volume mesh
→ CT/HU-informed material assignment
→ FEBio model and axial-compression protocol
→ solver execution and termination validation
→ limited scientific reporting
```

## Repository layout

```text
agent_system/       Publication-scope source code
docs/               Architecture, installation, workflow, ethics, provenance
scripts/            Repository validation and maintenance utilities
examples/           Data-free examples and expected-output descriptions
tests/              Test strategy and externally constrained tests
.github/workflows/  Static publication checks
```

## Data and privacy

Raw DICOM, NIfTI/NRRD volumes, patient-derived geometry, meshes, FEBio binary outputs, PHI, credentials, and private local paths are excluded from the public repository.

See `DATA_AVAILABILITY.md`, `ETHICS_AND_PRIVACY.md`, and `SECURITY.md`.

## Installation

See:

- `docs/INSTALLATION.md`
- `docs/CONFIGURATION.md`
- `docs/WORKFLOW.md`

Exact verified software and build versions are recorded in
`docs/SOFTWARE_VERSIONS.csv`. Exact Python dependencies are recorded in
`requirements-core-lock.txt`; optional external-AI connectivity is isolated in
`requirements-optional-ai-lock.txt`.

## Reproducibility

The repository preserves source-code provenance, recovered-source hashes, human-review boundaries, and publication-scope limitations. Because the retrospective clinical CT dataset cannot be distributed publicly, independent execution requires an appropriately authorized and de-identified input dataset.

## Citation and release

Software citation metadata is active in `CITATION.cff`.

The current software citation records:

- Yavuz Kürşat MİS;
- Kocaeli Üniversitesi Tıp Fakültesi Anatomi Ana Bilim Dalı;
- ORCID: https://orcid.org/0009-0007-7601-8628;
- the public source-code repository;
- the Apache-2.0 license.

The associated scientific article has a separately managed author list and may
change independently of the software-author record.

The following fields remain pending until the publication release:

- software version;
- release date;
- immutable release commit hash;
- `v1.0.0-publication` release URL;
- Zenodo DOI;
- preferred citation for the associated scientific article.

## License

This repository is licensed under the Apache License, Version 2.0. See
`LICENSE`.

Third-party software and libraries retain their own licenses. No third-party
scientific software binary is redistributed through this repository.
