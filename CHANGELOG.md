# Changelog

## Unreleased

### Changed
- **Upload page is one card** — the file, how to check it, and the button, top to bottom. How to check it is three choices side by side: "Choose for me" (auto-detect, the default), "A ready-made rule set", and "Describe it" with Gemini, so the AI option is no longer hidden behind a link. The side panel lists the checks for whatever is chosen, including the two machine-learning checks.
- **Report puts the summary beside the verdict** — "In short" sits next to the row map instead of floating between the verdict and the data, and is labelled "Written by Gemini" or "Written from the checks". The rule results are one tidy row.
- **Plain-English fallback summary** — "4 errors and 1 warning" instead of "4 error(s) and 1 warning(s)", and fixes named by what is wrong ("Blank cells in required fields: 1 to fix").
- **Upload limit raised from 5 MB to 20 MB** — set with `DATAGUARD_MAX_UPLOAD_MB`. A 20 MB file (about 256,000 rows) takes about 30 seconds to check.

### Fixed
- **AI summary and rule writer could never work** — they asked for `gemini-2.0-flash`, which Google shut down on 2026-06-01, through the unmaintained `google-generativeai` package, and every failure fell back silently, so a valid key still showed "Rule-based". They now use the `google-genai` SDK and Google's `gemini-flash-latest` alias (override with `GEMINI_MODEL`), and print the real error to the terminal before falling back.
- **The API key could be baked into the Docker image** — the Dockerfile copies the whole folder. A `.dockerignore` now leaves out `.env`, `.git` and virtualenvs, and `docker-compose.yml` passes `.env` in at run time.
- **"Download cleaned CSV" failed for any real file** — the upload was kept in the session cookie, which browsers drop above about 4 KB, so the download said "No file to clean". The upload is now kept in a temporary folder for an hour and the cookie holds only a random id.
- **Near-duplicate check was too slow for large files** — it compared every pair of rows in Python (about 15 minutes for 5 MB). It now scores pairs in rapidfuzz's `cdist`, lists the first 500 and counts the rest, and above 20,000 rows compares each row with its 50 neighbours in sorted order, saying so in the report.
- **Whitespace auto-fix read every cell one at a time** — about 6 seconds on a 5 MB file; it now only touches cells it changes.
- **Anomaly detection no longer scores code columns** — phone numbers, pincodes, account and roll numbers are labels, not measurements, so `samples/employees.csv` reported its wrong-prefix phone twice: once by `india_formats` and once as "unusual for this column". Columns named explicitly in `numeric_columns` are still scored.
- **"Typical range" now reads correctly** — it is measured over the ordinary values instead of the whole column, and small decimals keep their decimal places. A column of rates between 0.11 and 0.15 with one 9.80 in it was described as a "typical range" reaching 3.04, and `int()` truncation turned that same column into "range 0-0".

## 1.1.0 (2026-11-16)

### New features
- **ML anomaly detection** — IsolationForest with MAD-based secondary gate flags statistical outliers in numeric columns (`anomalies` rule)
- **Near-duplicate detection** — rapidfuzz fuzzy string matching finds rows that are almost identical across key columns (`near_duplicates` rule)
- **Smart cleaned CSV** — KNN imputation (k=3) fills blank numeric cells; mode imputation fills blank categorical cells; protected columns (IDs, emails, names) are never imputed
- **Change log** — every auto-fix is recorded with row, column, before/after values, method, and an `estimated` flag for imputed values; downloadable as `changes.csv`
- **AI summary** — Gemini-powered plain-English summary of validation findings with top-fix suggestions; falls back to rule-based summary when no API key is set
- **AI rule generation** — describe your data in plain English and get a `rules.yaml` configuration back; works offline with graceful fallback
- **Laptop UI redesign** — 1440×900 sidebar layout with design tokens (Plus Jakarta Sans, JetBrains Mono), ML pill tags on findings, AI summary card, dark mode

### Quality
- 165 pytest tests; ruff clean; CI on Python 3.11–3.13

## 1.0.1 (2026-11-15)

- `employees` rule template now runs the India phone number check
- Cleaned CSV download keeps whole numbers as integers (`55000`, not `55000.0`) when a column has blank cells

## 1.0.0 (2026-11-15)

Initial release of the DataGuard CSV validation engine.

### Validators
- `required_columns`, `missing_values`, `duplicates`, `range_and_format`, `india_formats` (phone, PIN code, PAN, GSTIN, IFSC)
- `validation.max_errors` cap on reported findings
- Rules configured in `rules.yaml`, with auto-detection of applicable validators

### Web UI (Flask)
- Upload a CSV or XLSX file and get a validation report with fix hints
- Choose a preset rule template or auto-detect rules
- Download an auto-fixed (cleaned) CSV

### Changes since last develop snapshot
- Duplicate rows are reported as warnings instead of errors
- `india_formats` phone check enabled in `rules.yaml` and demoed on `samples/employees.csv`
- Mobile Figma screens exported to `docs/ux/exports/mobile-screens/`

### Quality
- 136 pytest tests, 85% coverage; ruff clean; CI on Python 3.11–3.13
