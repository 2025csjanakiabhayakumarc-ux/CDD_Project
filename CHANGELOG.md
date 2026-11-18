# Changelog

## Unreleased

### Changed
- **Blank numbers are left blank, not averaged** — a filled-in salary looks like real data, so auto-fix no longer estimates blank numbers (KNN). They stay blank and the checks flag them for a person.
- **Blank names are rebuilt from the email** — `anita.hegde164@company.com` gives "Anita Hegde", marked "filled" in the change list. Addresses with no name in them (`12345@…`) are left for a person.
- **Mistyped copies of a record are removed** — when one ID (e.g. `emp_id`) appears more than once and only some rows have the name the email spells (`Anitaa Hegde` next to `Anita Hegde`, both `anita.hegde164@…`), the others are dropped. If no row or every row matches, nothing is removed.
- **"Needs a person" in the After auto-fix view** — every problem auto-fix leaves is tagged, next to the "Fixed by auto-fix" ones.

On `employees_23mb.csv` (228,461 rows): duplicates 722 → 0 and blank names 668 → 0. Left for a person: 705 impossible dates, 694 wrong phones, 1,083 blank salaries, 906 emails with no `@`, and 326 salaries far outside the usual range.

## 1.2.1 (2026-11-18)

### Changed
- **Upload limit is 25 MB** (was 20). Still set with `DATAGUARD_MAX_UPLOAD_MB`.
- **Large files say they take longer** — after choosing a file over 5 MB, the upload page says checking can take up to a minute (a 24 MB file takes about 40 seconds), so the wait doesn't look frozen.

### Fixed
- **Auto-fix skipped any text column with a blank cell** — pandas does not count a text column with an empty cell as text, so trimming never ran on it: `"  Asha  "` stayed as it was whenever the name column had one blank. Every text column is trimmed now.
- **Dates written several ways were never fixed** — "Choose for me" only counted dates already in one format, so a column mixing `15/01/2005`, `2005.06.01` and `15 Jan 2005` was not treated as dates and auto-fix left it alone. It now counts any format auto-fix can read and rewrites them in the column's most common one. Auto-fix also reads `2005.06.01`, `01.08.2005`, `15 Jan 2005`, `15 January 2005`, `15-Jan-2005` and `Jan 15, 2005` (numeric dates day first).
- **Large files took minutes or seemed to hang** — a realistic 10 MB file (128,000 rows, some blank salaries, mixed date formats) took 118 s to check; it now takes 11 s, and a 24 MB file takes 24 s. Building the cleaned copy was the cost:
  - Filling blank numbers (KNN) compared every row with a blank against every row in the file. It now uses a fixed random sample of 2,000 rows as neighbours and only works on rows that have a blank.
  - Dates, emails and blank text cells were checked one cell at a time. Each is now one pass over the column, and dates already in the right format are skipped; each other date is parsed once.

## 1.2.0 (2026-11-17)

### New features
- **Landing page** — a home page at `/` with a layered 3D sheet in the hero (your file, what is wrong, the cleaned copy), what each check catches, and how it works. The upload page moved to `/check`.
- **Marked-up sheet report** — the report shows your data as a sheet with each problem marked on its cell and a numbered note beside it, a row map to jump to any row, and an Original / After auto-fix switch. Burgundy theme with dark mode.
- **Gemini summary and plain-English rules work again** — on Google's current SDK and Flash-Lite model, with real errors shown in the terminal (details under Fixed).

### Changed
- **Upload page is one card** — the file, how to check it, and the button, top to bottom. How to check it is three choices side by side: "Choose for me" (auto-detect, the default), "A ready-made rule set", and "Describe it" with Gemini, so the AI option is no longer hidden behind a link. The side panel lists the checks for whatever is chosen, including the two machine-learning checks.
- **Report opens with one summary panel** — the verdict and row map, a health-score ring, and every check as a badge (passed, how many found, or not run), with "In short" in its own card beside it. Cards, buttons and the notes list have softer corners and layered shadows.
- **Skipped checks are one quiet line, not warning banners** — the page used to show a yellow banner for every check the chosen rules had no settings for, repeating what the checks row already said.
- **"Choose for me" runs the machine-learning checks** — number columns are checked for unusual values and name columns (with email) for near-duplicate rows. Before, auto-detect never ran either.
- **Report puts the summary beside the verdict** — "In short" sits next to the row map instead of floating between the verdict and the data, and is labelled "Written by Gemini" or "Written from the checks". The rule results are one tidy row.
- **Plain-English fallback summary** — "4 errors and 1 warning" instead of "4 error(s) and 1 warning(s)", and fixes named by what is wrong ("Blank cells in required fields: 1 to fix").
- **Upload limit raised from 5 MB to 20 MB** — set with `DATAGUARD_MAX_UPLOAD_MB`. A 20 MB file (about 256,000 rows) takes about 30 seconds to check.

### Fixed
- **"After auto-fix" view still showed fixed problems as broken** — a cell auto-fix had changed kept its red numbered mark and its column still said "1 to fix", and the removed duplicate kept its mark. In that view, problems auto-fix takes care of now lose their marks, column headings say "1 fixed" or "1 left to fix", and their notes are tagged "Fixed by auto-fix".
- **Auto-fix never fixed emails or dates** — the app called it with no settings, so it did not know which columns held them: `Priya@Company.COM` stayed as it was and `15/01/2022` was never rewritten as `2022-01-15`. The report and both downloads now pass the email and date columns from the rules that were checked.
- **Estimated values were wrong-looking** — the estimate for a blank salary used phone numbers to find "similar" rows, and came out as 51333.33 in a column of whole numbers, which also made the cleaned CSV write every other salary as `55000.0`. Code columns (phone, pincode, IDs) are now left out, and whole-number columns get whole-number estimates.
- **"Choose for me" missed problems the Employees rule set catches** — on `samples/employees.csv` it found 3 of the 5. A column was only required when at most 5% of it was blank, so one blank name in 15 rows (6.7%) switched the check off; it is now 20%. Phone numbers were never detected, so the Indian-formats check never ran; columns named like phone/mobile/contact, or full of Indian mobile numbers, now turn it on, and so do pincode columns. An ID column had to be 95% unique, so the duplicate it should catch (E001 twice, 93%) stopped it counting as an ID; it is now 90%.
- **Every phone number was "invalid" when the column had a blank** — pandas reads such a column as decimals, so 9123456780 became 9123456780.0. The Indian-formats check now drops that `.0` for phones and pincodes.
- **AI summary and rule writer could never work** — they asked for `gemini-2.0-flash`, which Google shut down on 2026-06-01, through the unmaintained `google-generativeai` package, and every failure fell back silently, so a valid key still showed "Rule-based". They now use the `google-genai` SDK and Google's `gemini-flash-lite-latest` alias on the v1beta API with a 15 s timeout (override with `GEMINI_MODEL`), and print the real error to the terminal before falling back.
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
