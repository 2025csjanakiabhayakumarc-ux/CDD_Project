# DataGuard web app (Member 5)

## Run it (from the repo root)

```bash
pip install flask
flask --app src.webapp.app run --debug
```

Open http://127.0.0.1:5000 and upload a CSV.

Inside Docker, start it with `HOST=0.0.0.0 python -m src.webapp.app` (port 5000, change with `PORT`).

## Test it

```bash
python -m pytest tests/test_webapp.py
```

## How it connects to the rest of the team

All the connection code is in `service.py`. The pages only call `analyze_upload()`.

| Needs | From | What happens today |
|---|---|---|
| `src/loader.py` with `load_csv()` | Member 1 | Used if found, otherwise demo checker |
| Rule modules in `src/rules/` with `check()` | Members 1, 2, 4 | Each rule found is run and shown |
| Findings with `rule`, `message`, `column`, `row`, `severity`, `hint` | Everyone | Missing fields get safe defaults |
| A "run all rules" function | Member 3 | Not needed yet. When it exists, change `_run_engine()` in `service.py` |

If a rule needs different inputs, the page shows a yellow note naming it, and you adjust `_call_rule()` in `service.py`. Nothing else changes.
