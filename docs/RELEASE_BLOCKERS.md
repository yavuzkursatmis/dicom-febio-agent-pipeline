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

## Resolved third-party review

- external scientific software licenses and distribution boundaries are
  documented in `THIRD_PARTY_SOFTWARE.md`;
- exact-version direct Python dependency licenses are documented in
  `docs/PYTHON_DEPENDENCY_LICENSES.md`;
- repository audits found no redistributed third-party executable, installer,
  clinical dataset, patient-derived binary artifact, or model weight;
- external software is obtained and installed independently by users.

## Remaining release-time third-party checks

- verify transitive dependency versions and bundled license files;
- recheck package metadata against the release environment;
- confirm task-specific and model-weight-specific TotalSegmentator terms;
- verify whether any third-party source-code fragments require attribution or
  inclusion in a `NOTICE` file;
- repeat the forbidden-binary, restricted-data, and secret scan against the
  immutable release commit.

## Resolved security item

The historical Gemini API credential was revoked before public repository
initialization. The revoked value is not part of the clean repository.
