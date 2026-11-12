# DataGuard web app (Member 5)

## Run it (from the repo root)

```bash
pip install flask pyyaml
flask --app src.webapp.app run --debug
```

Open http://127.0.0.1:5000 and upload a CSV.

Inside Docker the app finds out by itself that it must listen on all addresses, so the existing
`CMD ["python", "-m", "src.webapp.app"]` works as it is (port 5000, change with `PORT`).
The image must also contain `rules.yaml` at the repo root, because the checks read their settings from it.

## Test it

```bash
python -m pytest tests/test_webapp.py
```

## How it connects to the rest of the team

All the connection code is in `service.py`. The pages only call `analyze_upload()`.

| Needs | From | How the UI uses it |
|---|---|---|
| `src/loader.py` with `load_csv()` | Member 1 | Loads the upload. If missing, a demo checker is used |
| Rule modules with `check(df, **settings)` | Members 1, 2, 4 | Each rule found is run with its settings from `rules.yaml` |
| `rules.yaml` at the repo root | Members 3, 4 | One section per rule. A rule with no settings is skipped, and the report says so |
| Findings with `rule`, `message`, `hint` | Everyone | `row` and `column` are read from the message text if the rule gives no fields |

Two things to agree as a team (both are handled in `service.py` for now):
- Row numbers. `missing_values` counts rows from 0, so the UI adds 2 to show spreadsheet rows (`ROW_OFFSET` in `service.py`). Remove that entry if the rule is changed to use spreadsheet rows.
- If `Finding` gets optional `row` and `column` fields, the UI uses them automatically.
