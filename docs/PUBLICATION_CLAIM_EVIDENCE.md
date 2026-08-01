\# Publication Claim Evidence



This document records the evidence boundaries for the validated clean-T1

publication checkpoint.



The public repository contains source code and data-free documentation only.

Patient-derived inputs, geometry, meshes, FEBio models, solver logs, and XPLT

files are not redistributed.



\## Validated workflow boundary



The validated workflow consists of:



```text

reviewed upstream DICOM and segmentation evidence

→ geometry preparation

→ tetrahedral volume-mesh generation

→ heterogeneous FEBio model construction

→ human-reviewed axial-compression boundary conditions

→ FEBio solver execution

→ solver-result validation

→ limited academic reporting

## Geometry and volume-mesh evidence

| Parameter | Verified value |
|---|---:|
| Active segmentation-mask voxel count | 235260 |
| Mask-derived object volume | 29.4075 cm3 |
| Surface vertex count | 51847 |
| Surface face count | 103698 |
| Surface area | 11620.36957 mm2 |
| Watertight surface reported | Yes |
| Volume-mesh node count | 104140 |
| Tetrahedral element count | 456957 |
| Boundary triangle count | 103698 |
| Total tetrahedral volume | 29.376671875 cm3 |
| Minimum tetrahedral volume | 0.00206710 mm3 |
| Maximum tetrahedral volume | 1.27470945 mm3 |
| Mean simple aspect ratio | 1.62615245 |
| Maximum simple aspect ratio | 5.25931262 |

The difference between the mask-derived object volume and the summed
tetrahedral volume is approximately 0.105%.

This close volume agreement supports numerical consistency between the surface
geometry and generated tetrahedral mesh. It does not independently establish
anatomical accuracy, segmentation validity, mesh convergence, or predictive
biomechanical validity.

The watertight-surface result is recorded as a geometry-processing check only.
It must not be interpreted as proof of anatomical correctness.