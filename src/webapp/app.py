"""Flask app for DataGuard.

Run from the repo root:
    flask --app src.webapp.app run --debug
or:
    python -m src.webapp.app
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, Response, render_template, request, session

from . import service

ALLOWED_SUFFIXES = (".csv", ".tsv", ".txt", ".xlsx")
_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _ROOT / "templates_rules"
# One-click sample files on the upload page: name -> (file in samples/, rule template)
SAMPLES = {
    "employees": ("employees.csv", "employees"),
    "employees_clean": ("employees_clean.csv", "employees"),
}


def _describe(config_path: Path) -> dict:
    """Columns and rules a settings file asks for, for the upload page's preview."""
    data, _note = service._load_config_from(str(config_path))
    required = data.get("required_columns") or {}
    columns = required.get("columns", []) if isinstance(required, dict) else []
    return {
        "columns": [str(c) for c in columns],
        "rules": [name for name in service.RULE_NAMES if data.get(name)],
    }


def _rule_sets() -> list[dict]:
    """The choices in the "Rule template" menu. The first one is selected by default."""
    sets = [{"value": "default", "label": "Default (rules.yaml)", "source": "rules.yaml",
             **_describe(service._config_path())}]
    if _TEMPLATES_DIR.is_dir():
        for path in sorted(_TEMPLATES_DIR.glob("*.yaml")):
            label = path.stem.replace("_", " ").title()
            sets.append({"value": path.stem, "label": label, "source": f"the {label} template",
                         "path": str(path), **_describe(path)})
    sets.append({"value": "auto", "label": "Auto-detect from my file",
                 "source": "rules picked from your file's columns",
                 "columns": [], "rules": list(service.RULE_NAMES)})
    return sets


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
    app.secret_key = os.environ.get("SECRET_KEY", "dataguard-dev-key")

    def upload_page(error: str = "", status: int = 200):
        # Leave out "path" so server file paths are not written into the page.
        rule_sets = [{k: v for k, v in s.items() if k != "path"} for s in _rule_sets()]
        return render_template("index.html", rule_sets=rule_sets, error=error), status

    @app.get("/")
    def index():
        return upload_page()

    @app.post("/validate")
    def validate():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return upload_page("Please choose a CSV file first.", 400)
        if not upload.filename.lower().endswith(ALLOWED_SUFFIXES):
            return upload_page("That file type is not supported. Please upload a .csv or .xlsx file.", 400)

        choice = request.form.get("template", "default")
        if request.form.get("rule_mode") == "auto":  # older form field, still honoured
            choice = "auto"
        required = [c.strip() for c in request.form.get("required", "").split(",") if c.strip()]
        return check(upload.filename, upload.read(), choice, required)

    @app.get("/try/<name>")
    def try_sample(name: str):
        if name not in SAMPLES:
            return upload_page("That sample file does not exist.", 404)
        filename, template = SAMPLES[name]
        path = _ROOT / "samples" / filename
        if not path.is_file():
            return upload_page("That sample file is missing from the samples folder.", 404)
        return check(filename, path.read_bytes(), template, [])

    def check(filename: str, file_data: bytes, choice: str, required: list[str]):
        sets = {s["value"]: s for s in _rule_sets()}
        rule_set = sets.get(choice, sets["default"])
        report = service.analyze_upload(
            filename, file_data, required,
            config_path=rule_set.get("path"), auto_detect=rule_set["value"] == "auto",
        )
        if report.error:
            return render_template("error.html", message=report.error, filename=report.filename), 422

        session["last_upload"] = file_data
        session["last_filename"] = filename
        return render_template("report.html", report=report, rule_source=rule_set["source"],
                               rule_label=rule_set["label"], all_rules=service.RULE_NAMES)

    @app.errorhandler(413)
    def too_big(_error):
        return upload_page("That file is bigger than 5 MB. Please upload a smaller file.", 413)

    @app.get("/download-cleaned")
    def download_cleaned():
        file_data = session.get("last_upload")
        filename = session.get("last_filename", "data.csv")
        if not file_data:
            return upload_page("No file to clean. Please upload a file first.", 400)
        cleaned_csv, _summary = service.get_cleaned_csv(file_data)
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        return Response(
            cleaned_csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={stem}_cleaned.csv"},
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    create_app().run(
        # Inside Docker the app must listen on all addresses, or the browser cannot reach it.
        host=os.environ.get("HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
