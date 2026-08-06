# Publication Claim Evidence

This document records the evidence boundaries for the validated clean-T1
publication checkpoint.

The public repository contains source code and data-free documentation only.
Patient-derived inputs, geometry, meshes, FEBio models, solver logs, and XPLT
files are not redistributed.

## Validated workflow boundary

The validated publication workflow is:

```text
reviewed upstream DICOM and segmentation evidence
-> geometry preparation
-> tetrahedral volume-mesh generation
-> heterogeneous FEBio model construction
-> human-reviewed axial-compression boundary/load configuration
-> FEBio solver execution
-> solver-result validation
-> limited result extraction
-> interpretation precheck
-> academic report drafting
-> full-pipeline audit
```

Agents01-07 were completed and reviewed upstream. The audited live LangGraph
run entered at Agent08, orchestrated Agents08-17, and then audited the
pre-existing clean-T1 upstream evidence.

The publication does not claim that one live LangGraph execution ran
Agents01-17 from raw DICOM input.

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
elastic bone law derived from:

> A novel personalized homogenous finite element model to predict the pull-out
> strength of cancellous bone screws. DOI: 10.1186/s13018-024-05169-x.

Use of this constitutive law in the clean-T1 axial-compression workflow is a
cross-context transfer from a cancellous-bone screw-pullout study. It is not
direct validation of the law for T1 vertebral axial compression.

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
```

The following counters refer to different sampling domains:

| Counter | Sampling domain | Verified count |
|---|---|---:|
| Policy-reference invalid-density count | Masked voxel domain | 4580 |
| Raw non-positive density count | Tetrahedral element-centroid domain | 15306 |
| Elements at the effective density floor | Tetrahedral element domain | 15500 |
| Total material assignments | Tetrahedral element domain | 456957 |

The historical warning
`MAPPING_POLICY_INVALID_COUNT_MISMATCH:4580_vs_15306` compared counts from
different sampling domains. It did not indicate missing material assignments.

The source implementation was subsequently changed so that voxel-domain and
element-centroid-domain counters are preserved separately as provenance. The
historical case outputs were not recomputed or edited.

The evidence does not establish why the total number of elements at the
effective density floor exceeds the raw non-positive element-centroid count by
194. No unsupported causal explanation is made.

### Orthotropic-stability evidence

The material-law validation was not stored in a separately named
orthotropic-stability file. The explicit results are contained in:

- `APPROVED_MATERIAL_LAW_VALIDATION_RESULT.json`
- `APPROVED_MATERIAL_LAW_VALIDATION_REPORT.csv`

The implemented validation evaluated the following determinant condition:

```text
1
- nu_xy * nu_yx
- nu_yz * nu_zy
- nu_xz * nu_zx
- 2 * nu_yx * nu_zy * nu_xz
> 0
```

The recorded validation status was `MATERIAL_LAW_VALIDATION_PASS`, and the
validated material package was approved for the downstream model-generation
stage.

This check is evidence for the implemented determinant criterion only. It is
not an independent full-tensor or eigenvalue-based proof of positive
definiteness over every possible parameter state.

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
| Inferior fixed-node count | 1541 |
| Superior loaded-node count | 1035 |
| Node-set CSV row count | 2576 |

The band thickness was calculated as:

```text
0.08 * 45.0 mm = 3.6 mm
```

### Prescribed axial-compression protocol

| Parameter | Verified value |
|---|---:|
| Analysis type | Axial compression |
| Apparent strain | 0.005 (0.5%) |
| Prescribed displacement | -0.225 mm |
| Loading direction | Negative Z |
| Load type | Prescribed superior Z displacement |
| Fixed region | Inferior end region |
| Loaded region | Superior end region |

The displacement was calculated as:

```text
displacement = -0.005 * 45.0 mm = -0.225 mm
```

The boundary/load candidate initially required review and was not solver-ready.
The recorded review result was `BOUNDARY_LOAD_REVIEW_APPROVED`, with approval
for solver execution, no warnings, no blockers, and `clinical_use = false`.

The live graph consumed and validated the existing approved review record. It
did not obtain a new interactive human approval during that live execution.

A superseded fragmented-mask workflow contained 772 fixed nodes and 855 loaded
nodes. Those values are excluded from the active publication evidence.

The prescribed development load is a literature-derived small-strain
compression protocol. It must not be represented as a validated physiological,
fracture, or patient-specific clinical load.

## FEBio solver-execution and output evidence

The active clean-T1 solver-ready FEBio model was executed using the recorded
FEBio 4 executable after approval of the boundary/load review gate.

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
| Solver-result validation status | `SOLVER_RESULT_VALIDATION_PASS` |

The FEBio solver log ends with:

```text
N O R M A L   T E R M I N A T I O N
```

### Solver-log execution metrics

| Metric | Verified value |
|---|---:|
| Completed time steps | 10 |
| Total equilibrium iterations | 20 |
| Average equilibrium iterations per step | 2 |
| Total right-hand evaluations | 30 |
| Total stiffness reformations | 10 |
| Total linear-solver calls | 20 |
| Average iterations per linear solve | 1 |
| Peak memory | 2581.2 MB |
| Solve time | 78.184 s |
| Total elapsed time | 79.0054 s |

These metrics establish convergence of the recorded nonlinear solver run. They
do not establish mesh convergence, anatomical accuracy, experimental
validation, or predictive biomechanical validity.

### Solver artifacts

| Artifact | Size | SHA-256 |
|---|---:|---|
| Solver-ready FEB | 31318305 bytes | `6F662C06BE29CFC97244BA5EB1FDBBDEC3393967F543F4BC809322A344D66C99` |
| Native solver log | 34781 bytes | `3B9E57B35FEBBB4C7181B892330B4B95C991901536D096B40C2571B53C5D8111` |
| Native XPLT | 171213357 bytes | `033A6F10FA6D2D5AF5AB3C0EA357594670A7216F329697C8E9BBED75A4B4CF5D` |

The boundary/load candidate FEB and solver-ready FEB had the same recorded size
and SHA-256 hash at the audited checkpoint. This supports byte-level identity
at that checkpoint only; it is not semantic model validation.

### XPLT extraction boundary

One non-empty XPLT file was found. The result-extraction stage recorded:

```text
xplt_binary_field_extraction_performed = false
```

The system verified XPLT existence and extracted solver-log metrics only. It
did not extract quantitative displacement, stress, strain, reaction-force, or
other spatial field values from the binary XPLT file.

Native XPLT generation must not be described as quantitative XPLT field
extraction.

## Downstream reporting and LangGraph orchestration evidence

### Downstream agent statuses

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

### Result-extraction and interpretation boundary

Agent14 verified:

- successful upstream solver validation
- normal solver termination
- existence of a non-empty XPLT file
- existence of the selected solver log
- availability of solver-log text metrics

The recorded XPLT file size was 171213357 bytes.

Agent15 recorded:

```text
solver completed = true
XPLT present = true
XPLT binary field extraction performed = false
quantitative field interpretation allowed = false
solver-log interpretation allowed = true
clinical interpretation allowed = false
academic pipeline reporting allowed = true
```

The permitted reporting scope was limited to solver completion, normal
termination, non-empty XPLT existence, solver-log metrics, and
pipeline-development limitations.

The prohibited scope included maximum displacement, maximum stress, strain
distribution, local field comparisons, clinical diagnosis, patient-specific
treatment support, validated clinical accuracy, and representation of the
development load as a physiological clinical load.

### Academic report and full-pipeline audit

Agent16 produced non-empty Markdown and text report artifacts and recorded:

```text
ACADEMIC_REPORT_DRAFT_PASS
quantitative field interpretation allowed = false
clinical interpretation allowed = false
```

The generated report covered scope, pipeline status, geometry and mesh,
material and FEBio model generation, boundary/load configuration, solver
validation, result extraction, interpretation precheck, limitations, next
steps, and conclusion.

Agent17 recorded `FULL_PIPELINE_AUDIT_LIMITED_PASS`, no blockers, and the
following retained limitations:

```text
QUANTITATIVE_FIELD_INTERPRETATION_NOT_ALLOWED_XPLT_MANUAL_OR_EXTERNAL_REVIEW_REQUIRED
XPLT_BINARY_FIELD_EXTRACTION_NOT_PERFORMED_BY_AGENT_SYSTEM
```

The limited-pass status is a scientific reporting boundary, not a solver or
graph execution failure.

### Clean-T1 live LangGraph scope

The audited live-run result recorded:

```text
run_live = true
entry_point = AGENT_08_GEOMETRY_PREPARATION
final_node = GRAPH_FINAL
completed_graph_nodes = 12
blockers = []
final_status = LANGGRAPH_PIPELINE_LIMITED_PASS
```

The completed graph sequence was:

1. `AGENT_08_GEOMETRY_PREPARATION`
2. `AGENT_09_VOLUME_MESH_GENERATION`
3. `AGENT_10_FEBIO_MODEL_GENERATION`
4. `AGENT_11_BOUNDARY_LOAD_CONFIGURATION`
5. `AGENT_11_REVIEW_VALIDATION`
6. `AGENT_12_FEBIO_SOLVER_EXECUTION`
7. `AGENT_13_SOLVER_RESULT_VALIDATION`
8. `AGENT_14_RESULT_EXTRACTION`
9. `AGENT_15_RESULT_INTERPRETATION_PRECHECK`
10. `AGENT_16_ACADEMIC_REPORT_DRAFT`
11. `AGENT_17_FULL_PIPELINE_AUDIT`
12. `CLEAN_T1_UPSTREAM_EVIDENCE_AUDIT`

Agents01-07 were not included in the live-run manifest or the live-run
`completed_agents` sequence. They were not re-executed during this audited live
run.

The final upstream-audit node checked pre-existing clean-T1 evidence, including
the active mask, activation record, superseded-mask provenance, voxel count,
geometry volume, mesh consistency, and FEBio tetrahedral-count consistency.

The supported orchestration claim is:

> Agents01-07 were completed and reviewed upstream. The audited live LangGraph
> run entered at Agent08, orchestrated Agents08-17, and subsequently audited
> the pre-existing clean-T1 upstream evidence.

The unsupported claim is:

> A single live LangGraph run executed Agents01-17 from raw DICOM input.

### Dry-run distinction

The supervisor dry-run used a different case identifier and recorded for every
node:

```text
Dry-run mode: tool was not executed.
```

The dry-run supports graph topology and routing validation only. It is not
evidence that the scientific tools or FEBio solver were executed.

## Solver-log parser correction provenance

A source-code audit identified a limitation in the historical Agent14
solver-log metric parser.

The historical parser used simple text-occurrence checks and counts:

```python
"normal_termination_detected": "normal termination" in lower
"time_step_count": lower.count("time step")
"stiffness_reformation_count": lower.count("stiffness reformation")
```

The resulting historical CSV recorded:

| Metric | Historical parser value |
|---|---:|
| Normal termination detected | False |
| Time-step count | 12 |
| Stiffness-reformation count | 1 |

Direct parsing of the native FEBio solver log established:

| Metric | Direct solver-log value |
|---|---:|
| Normal termination detected | True |
| Completed time steps | 10 |
| Total stiffness reformations | 10 |

The termination discrepancy resulted from the spaced FEBio heading:

```text
N O R M A L   T E R M I N A T I O N
```

The historical time-step and reformation values represented textual occurrence
counts rather than the numerical totals in the final solver summary.

The source parser was updated to:

- recognize compact and spaced normal-termination headings
- extract the final `Number of time steps completed` value
- extract the final `Total number of stiffness reformations` value
- use explicit event-pattern counts only as fallback behavior

An in-memory test of the corrected parser against the audited solver log
returned:

```text
normal termination detected = True
completed time steps = 10
convergence count = 10
stiffness reformation count = 10
fatal error count = 0
error count = 0
warning count = 0
```

The historical case JSON and CSV artifacts were not regenerated or edited.
They remain preserved as execution provenance.

The pipeline pass decision did not depend on the incorrect historical CSV
values. Solver success was independently supported by return code zero, the
Agent12 execution result, the Agent13 validation result, direct normal
termination, the native solver log, and generation of a non-empty XPLT file.

The parser correction applies to future result-extraction runs. It must not be
described as a retroactive rerun of the historical clean-T1 case.

## Claim and validation boundary

The evidence supports:

- successful reviewed upstream preparation through Agent07
- successful live orchestration of Agents08-17
- successful geometry and tetrahedral-mesh generation
- complete element-level material assignment
- human-approved boundary/load configuration
- FEBio execution with return code zero and normal termination
- solver-result validation
- non-empty native XPLT generation
- solver-log-level result extraction
- safety-constrained academic pipeline reporting
- preservation of quantitative and clinical interpretation restrictions

The evidence does not establish:

- one-run execution from raw DICOM through Agent17
- re-execution of Agents01-07 during the audited live run
- interactive human approval obtained during the live graph
- quantitative binary XPLT field extraction
- maximum displacement, stress, or strain values
- reaction-force or stiffness results
- mesh convergence
- experimental validation of the clean-T1 model
- anatomical ground truth
- predictive biomechanical validity
- clinical diagnostic or treatment-decision validity

## Release blocker

Ethics, data-governance, access-control, retention, and institutional approval
details remain outside this evidence file and must be completed from verified
project records before a publication release is created.

No ethics approval, consent, waiver, or institutional authorization is asserted
by this document.
