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

## Material-law and element-mapping evidence

The validated material package records a density-based orthotropic linear
elastic bone law derived from the following source:

> A novel personalized homogenous finite element model to predict the pull-out
> strength of cancellous bone screws. DOI: 10.1186/s13018-024-05169-x.

### Recorded constitutive relations

| Parameter | Recorded relation |
|---|---|
| Apparent density | `rho_app = 0.047 + 0.001122 HU` g/cm3 |
| Longitudinal elastic modulus | `Ez = 4730 rho_app^1.56` MPa |
| Transverse elastic moduli | `Ex = Ey = 0.333 Ez` |
| In-plane shear modulus | `Gxy = 0.121 Ez` |
| Remaining shear moduli | `Gxz = Gyz = 0.157 Ez` |
| Poisson ratio | `nu_xy = 0.381` |
| Remaining Poisson ratios | `nu_xz = nu_yz = 0.104` |

The material package records that no manual material coefficients or equations
were entered. The structured coefficients originate from the approved
agent-derived source record.

### Element-level material assignment

| Parameter | Verified value |
|---|---:|
| Material-bin count | 20 |
| Tetrahedral element count | 456957 |
| Elements with a material assignment | 456957 |
| Element-centroid HU minimum | -773 |
| Element-centroid HU maximum | 1445 |
| Element-centroid HU mean | 294.417439715334 |
| Effective density minimum | 0.000998 g/cm3 |
| Effective density maximum | 1.66829 g/cm3 |
| Element-level Ez minimum | 0.09851555 MPa |
| Element-level Ez maximum | 10510.04930466 MPa |

The sum of the element counts in the 20 material bins equals the complete
tetrahedral element count. No unassigned tetrahedral element was identified.

### Density-domain mapping policy

The HU-density relation produced non-positive raw density values for part of
the sampled domain. A human-reviewed, case-derived policy clipped these values
to the minimum positive case-derived density:

```text
effective density floor = 0.000998 g/cm3

### Orthotropic-stability evidence

The material-law validation was not stored in a separately named
orthotropic-stability file. Instead, the explicit stability results are
contained in:

- `APPROVED_MATERIAL_LAW_VALIDATION_RESULT.json`;
- `APPROVED_MATERIAL_LAW_VALIDATION_REPORT.csv`.

The implemented validation evaluated the following determinant condition:

```text
1
- nu_xy * nu_yx
- nu_yz * nu_zy
- nu_xz * nu_zx
- 2 * nu_yx * nu_zy * nu_xz
> 0

## Boundary-condition and loading evidence

The active clean-T1 case used a protocol-derived axial-compression
configuration with coordinate-based inferior and superior end regions.

### Geometric selection parameters

| Parameter | Verified value |
|---|---:|
| Minimum model Z coordinate | 78.25 mm |
| Maximum model Z coordinate | 123.25 mm |
| Model height | 45.0 mm |
| End-region band fraction | 0.08 |
| End-region band thickness | 3.6 mm |
| Inferior selection threshold | Z <= 81.85 mm |
| Superior selection threshold | Z >= 119.65 mm |

The band thickness was calculated as:

```text
0.08 * 45.0 mm = 3.6 mm

## FEBio solver-execution and output evidence

The active clean-T1 solver-ready FEBio model was executed using the recorded
FEBio 4 executable after approval of the boundary/load human-review gate.

### Solver-execution status

| Parameter | Verified value |
|---|---:|
| Solver execution status | `SOLVER_EXECUTION_PASS` |
| Solver run attempted | Yes |
| Solver run success | Yes |
| Solver process return code | 0 |
| Normal termination detected | Yes |
| Solver error detected | No |
| Execution warnings | None |
| Execution blockers | None |

The FEBio solver log ends with:

```text
N O R M A L   T E R M I N A T I O N

## Downstream reporting and LangGraph orchestration evidence

### Downstream agent statuses

The active clean-T1 downstream workflow recorded the following statuses:

| Agent | Function | Recorded status |
|---|---|---|
| Agent14 | Result extraction | `RESULT_EXTRACTION_PASS` |
| Agent15 | Interpretation precheck | `INTERPRETATION_PRECHECK_LIMITED_PASS` |
| Agent16 | Academic report draft | `ACADEMIC_REPORT_DRAFT_PASS` |
| Agent17 | Full pipeline audit | `FULL_PIPELINE_AUDIT_LIMITED_PASS` |

The directory numbering is shifted relative to the agent identifiers:

| Directory | Agent |
|---|---|
| `15_result_extraction` | Agent14 |
| `16_result_interpretation_precheck` | Agent15 |
| `17_academic_report_draft` | Agent16 |
| `18_full_pipeline_audit` | Agent17 |

### Result-extraction boundary

Agent14 verified:

- successful upstream solver validation;
- normal solver termination;
- existence of a non-empty XPLT file;
- existence of the selected solver log;
- availability of solver-log text metrics.

The recorded XPLT file size was:

```text
171213357 bytes

## Solver-log parser correction provenance

A source-code audit identified a limitation in the historical Agent14
solver-log metric parser.

The historical parser used simple text-occurrence counts:

```python
"normal_termination_detected": "normal termination" in lower
"time_step_count": lower.count("time step")
"stiffness_reformation_count": lower.count("stiffness reformation")