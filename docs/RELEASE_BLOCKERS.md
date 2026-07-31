# Release Blockers

The clean repository may be initialized locally before these fields are
completed, but a publication release must not be declared complete until all
blocking items are resolved.

## Blocking publication metadata

- final software author/contributor names;
- active and validated `CITATION.cff`;
- public GitHub repository URL;
- immutable publication commit hash;
- `v1.0.0-publication` release URL;
- Zenodo DOI.

## Blocking ethics and data-governance metadata

- ethics committee/institutional review body;
- approval date and decision/protocol number;
- informed-consent status or consent-waiver basis;
- hospital-archive access authorization;
- exact DICOM de-identification/anonymization procedure;
- data-retention and access-control description.

## Blocking third-party review

- confirm licenses of Python dependencies and external tools;
- confirm that no third-party binary or restricted dataset is redistributed;
- document any third-party source code incorporated into this repository.

## Resolved security item

The historical Gemini API credential was revoked before public repository
initialization. The revoked value is not part of the clean staging tree.
