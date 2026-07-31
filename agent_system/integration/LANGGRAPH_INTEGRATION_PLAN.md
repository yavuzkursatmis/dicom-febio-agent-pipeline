# LangChain / LangGraph Integration Plan

Created at: 2026-07-16T16:22:29
Case ID: `real_dicom_check_001_anon_T1`

## Current status

The deterministic scientific pipeline has reached `FULL_PIPELINE_AUDIT_LIMITED_PASS`.

## Integration rule

Existing deterministic tools will not be rewritten. They will be wrapped as LangChain tools and connected as LangGraph nodes.

## Agents

| Agent | Role | LangGraph Node | Human Review |
|---|---|---:|---:|
| `AGENT_01_DATA_INTAKE` | Input detection and case initialization | `True` | `False` |
| `AGENT_02_DICOM_SAFETY` | DICOM safety and PHI risk screening | `True` | `False` |
| `AGENT_03_IMAGE_QUALITY` | Image quality and spacing checks | `True` | `False` |
| `AGENT_04_TARGET_UNDERSTANDING` | Target/test understanding | `True` | `False` |
| `AGENT_05_SEGMENTATION` | Segmentation/preprocessing | `True` | `False` |
| `AGENT_06_SEGMENTATION_VALIDATION` | Segmentation validation | `True` | `True` |
| `AGENT_07_MATERIAL_SELECTION` | Literature-backed material law selection and validation | `True` | `True` |
| `AGENT_08_GEOMETRY_PREPARATION` | Mask to watertight STL geometry | `True` | `False` |
| `AGENT_09_VOLUME_MESH_GENERATION` | STL to tetrahedral volume mesh | `True` | `False` |
| `AGENT_10_FEBIO_MODEL_GENERATION` | Volume mesh and HU-density material law to FEBio base model | `True` | `False` |
| `AGENT_11_BOUNDARY_LOAD_CONFIGURATION` | Boundary/load candidate creation | `True` | `True` |
| `AGENT_11_REVIEW_VALIDATION` | Boundary/load human review validation | `True` | `True` |
| `AGENT_12_FEBIO_SOLVER_EXECUTION` | FEBio solver execution | `True` | `False` |
| `AGENT_13_SOLVER_RESULT_VALIDATION` | Solver result validation | `True` | `False` |
| `AGENT_14_RESULT_EXTRACTION` | Result extraction and solver-log metrics | `True` | `False` |
| `AGENT_15_RESULT_INTERPRETATION_PRECHECK` | Interpretation safety precheck | `True` | `False` |
| `AGENT_16_ACADEMIC_REPORT_DRAFT` | Academic report draft | `True` | `False` |
| `AGENT_17_FULL_PIPELINE_AUDIT` | Full scientific and workflow audit | `True` | `False` |

## Next implementation step

Create LangChain tool wrappers for deterministic agents, then build the first LangGraph supervisor workflow.