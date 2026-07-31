# Publication Refactor Log

## Historical source
- checkpoint: `b58acf034`
- subject: `Pass LangGraph clean T1 limited live run`

## Security and privacy
- original Git history was not inherited;
- secrets and `.env` were excluded;
- medical data and patient-derived binaries were excluded;
- private local paths were removed;
- large solver outputs were excluded.

## Recovered untracked source
Ten files used by the successful run but absent from the historical commit were recovered. Their metadata and SHA-256 values are in `RECOVERED_UNTRACKED_SOURCES.csv`.

## Scope corrections
- live graph entry point corrected to Agent08;
- Agents01–07 described as previously completed upstream evidence;
- Streamlit-specific next-stage labels removed;
- explicit tissue-agnostic future-work artifacts removed.
