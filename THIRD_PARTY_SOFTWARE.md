# Third-Party Software

This repository interoperates with independently distributed scientific
software and Python packages. Those components are not relicensed by this
repository and retain their respective licenses.

No third-party executable, installer, model weight, clinical dataset, or
patient-derived binary artifact is redistributed through this repository.

## External scientific software

| Component | Validated version | License or distribution terms | Repository use |
|---|---:|---|---|
| 3D Slicer | 5.12.0 | 3D Slicer Software License, BSD-style | Human segmentation review, editing, and visual quality assurance |
| TotalSegmentator | 2.15.0 | Core source code under Apache-2.0; some optional tasks or model weights may require separate licenses | Automated segmentation through a locally installed package |
| Gmsh | 4.15.2 | GNU GPL version 2 or later, with a linking exception | External tetrahedral volume-mesh executable |
| FEBio | 4.12.0 | MIT License for the open-source solver code | External finite-element solver executable |
| FEBioStudio | 3.1 | MIT License for the open-source application code | Installation environment and model inspection interface |

## Redistribution boundary

The repository contains integration code, configuration templates,
documentation, and data-free examples only.

The following are not included:

- 3D Slicer binaries or extensions;
- TotalSegmentator model weights;
- Gmsh binaries or source code;
- FEBio or FEBioStudio binaries or source code;
- patient-derived DICOM, NIfTI, geometry, mesh, FEB, or XPLT files.

Users must obtain and install all external scientific software independently
and must comply with the applicable upstream license and distribution terms.

## Python dependencies

Exact validated Python package versions are listed in
`requirements-core-lock.txt`.

Optional external-AI connectivity is isolated in
`requirements-optional-ai-lock.txt`.

Python packages retain their respective upstream licenses. A package-level
license inventory remains required before the `v1.0.0-publication` release.

## TotalSegmentator licensing note

The publication repository does not redistribute TotalSegmentator source code,
model weights, or license-restricted tasks.

The presence of an Apache-2.0 license in the upstream source repository must
not be interpreted as applying automatically to every optional model weight or
licensed task distributed through the wider TotalSegmentator ecosystem.