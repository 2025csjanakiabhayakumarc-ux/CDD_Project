# Changelog

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
