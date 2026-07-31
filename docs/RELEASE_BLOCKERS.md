# Release Blockers

The public repository is active, but a publication release must not be
declared complete until the remaining blocking items are resolved.

## Resolved publication metadata

- software author metadata;
- active `CITATION.cff`;
- public GitHub repository URL;
- Apache License 2.0;
- clean publication repository history.

## Blocking publication metadata

- release version;
- release date;
- immutable release commit hash;
- `v1.0.0-publication` release URL;
- Zenodo DOI;
- preferred citation for the associated scientific article.

## Blocking ethics and data-governance metadata

- ethics committee or institutional review body;
- approval date and decision or protocol number;
- informed-consent status or consent-waiver basis;
- hospital-archive access authorization;
- exact DICOM de-identification or anonymization procedure;
- data-retention and access-control description.

## Blocking third-party review

- confirm licenses of Python dependencies and external tools;
- confirm that no third-party binary or restricted dataset is redistributed;
- document any third-party source code incorporated into this repository.

## Resolved security item

The historical Gemini API credential was revoked before public repository
initialization. The revoked value is not part of the clean repository.
