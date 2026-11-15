# Changelog

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
