\# Python Dependency License Inventory



This document records the package-level license metadata for the exact Python

versions used by the validated publication environment.



The inventory is based on exact-version package metadata and upstream license

declarations reviewed on 2026-07-31.



This repository does not redistribute these packages. Users install them

independently from their upstream distribution channels.



\## Core publication environment



| Package | Validated version | Recorded license metadata | Repository role |

|---|---:|---|---|

| TotalSegmentator | 2.15.0 | Apache-2.0 | Automated segmentation |

| SimpleITK | 2.5.5 | Apache-2.0 | Medical-image input, conversion, and processing |

| pydicom | 3.0.2 | MIT | DICOM reading and metadata handling |

| meshio | 5.3.5 | MIT | Mesh-format input and output |

| NumPy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Numerical array operations |

| Pydantic | 2.13.4 | MIT | Schema and data validation |

| langchain-core | 1.4.9 | MIT | Agent and tool abstractions |

| LangGraph | 1.2.9 | MIT | Human-in-the-loop workflow orchestration |

| scikit-image | 0.26.0 | BSD License | Image-processing utilities |

| trimesh | 4.12.2 | MIT | Surface-mesh inspection and processing |

| pypdf | 6.14.2 | BSD-3-Clause | Data-free report and PDF support |

| requests | 2.34.2 | Apache-2.0 | HTTP communication utilities |

| python-dotenv | 1.2.2 | BSD-3-Clause | Local environment-variable loading |



Exact versions are locked in `requirements-core-lock.txt`.



\## Optional external-AI dependency



| Package | Validated version | Recorded license metadata | Repository role |

|---|---:|---|---|

| google-genai | 2.11.0 | Apache-2.0 | Optional external-AI connectivity |



The optional dependency is isolated in

`requirements-optional-ai-lock.txt` and is not required for the primary

deterministic publication claim.



\## Scope and limitations



This table records direct dependencies explicitly preserved by the publication

repository.



It does not by itself constitute:



\- a complete transitive-dependency inventory;

\- a substitute for license files bundled inside installed wheels or source

&#x20; distributions;

\- a license grant for separately distributed model weights, datasets, hosted

&#x20; services, or optional commercial tasks;

\- legal advice.



TotalSegmentator model weights and optional tasks may have terms that are

separate from the Apache-2.0 license recorded for the Python source package.



Before `v1.0.0-publication`, the release environment should be checked again

for:



\- transitive dependency versions and license files;

\- package metadata changes;

\- model-weight and task-specific terms;

\- accidentally redistributed third-party source code or binaries.

