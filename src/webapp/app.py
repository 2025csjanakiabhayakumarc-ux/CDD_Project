"""Flask app for DataGuard.

Run from the repo root:
    flask --app src.webapp.app run --debug
or:
    python -m src.webapp.app
"""
from __future__ import annotations

import os
import re
import secrets
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request, session

from . import service

load_dotenv()

ALLOWED_SUFFIXES = (".csv", ".tsv", ".txt", ".xlsx")
MAX_UPLOAD_MB = int(os.environ.get("DATAGUARD_MAX_UPLOAD_MB", "20"))
# The last upload is kept on disk so "Download cleaned CSV" can use it. It used to sit in
# the session cookie, but browsers drop cookies over about 4 KB, so downloads failed for
# any real file. Only a random id goes in the cookie now.
UPLOAD_DIR = Path(tempfile.gettempdir()) / "dataguard_uploads"
KEEP_SECONDS = 60 * 60
_UPLOAD_ID = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _ROOT / "templates_rules"
# One-click sample files on the upload page: name -> (file in samples/, rule template)
SAMPLES = {
    "employees": ("employees.csv", "employees"),
    "employees_clean": ("employees_clean.csv", "employees"),
}


def _keep_upload(file_data: bytes) -> str:
    """Save an upload for the download links and return its id. Old uploads are deleted."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - KEEP_SECONDS
    for old in UPLOAD_DIR.glob("*.bin"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass  # another request removed it first
    upload_id = secrets.token_urlsafe(24)
    (UPLOAD_DIR / f"{upload_id}.bin").write_bytes(file_data)
    return upload_id


def _kept_upload(upload_id: str | None) -> bytes | None:
    """The saved upload for this id, or None if it is missing, expired or the id is bad."""
    if not upload_id or not _UPLOAD_ID.match(upload_id):
        return None
    path = UPLOAD_DIR / f"{upload_id}.bin"
    try:
        if path.stat().st_mtime < time.time() - KEEP_SECONDS:
            return None
        return path.read_bytes()
    except OSError:
        return None


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
    """The choices in the "Pick the rules" menu. The upload page selects "auto" first."""
    sets = [{"value": "default", "label": "Student records (rules.yaml)", "source": "rules.yaml",
             **_describe(service._config_path())}]
    if _TEMPLATES_DIR.is_dir():
        for path in sorted(_TEMPLATES_DIR.glob("*.yaml")):
            label = path.stem.replace("_", " ").title()
            sets.append({"value": path.stem, "label": label, "source": f"the {label} template",
                         "path": str(path), **_describe(path)})
    sets.append({"value": "auto", "label": "Let DataGuard choose from my columns",
                 "source": "rules picked from your file's columns",
                 "columns": [], "rules": list(service.RULE_NAMES)})
    return sets


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
    app.secret_key = os.environ.get("SECRET_KEY", "dataguard-dev-key")

    @app.context_processor
    def ai_flag():
        # With a Gemini key, the summary sends column names and the problems found
        # (never the file itself), so the privacy wording on the pages changes.
        return {"ai_on": bool(os.environ.get("GEMINI_API_KEY")), "max_mb": MAX_UPLOAD_MB}

    def upload_page(error: str = "", status: int = 200):
        # Leave out "path" so server file paths are not written into the page.
        rule_sets = [{k: v for k, v in s.items() if k != "path"} for s in _rule_sets()]
        return render_template("index.html", rule_sets=rule_sets, error=error), status

    @app.get("/")
    def home():
        return render_template("landing.html")

    @app.get("/check")
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
        ai_rules_text = request.form.get("ai_rules", "").strip()
        return check(upload.filename, upload.read(), choice, required, ai_rules_text)

    @app.get("/try/<name>")
    def try_sample(name: str):
        if name not in SAMPLES:
            return upload_page("That sample file does not exist.", 404)
        filename, template = SAMPLES[name]
        path = _ROOT / "samples" / filename
        if not path.is_file():
            return upload_page("That sample file is missing from the samples folder.", 404)
        return check(filename, path.read_bytes(), template, [])

    def check(filename: str, file_data: bytes, choice: str, required: list[str], ai_rules_text: str = ""):
        sets = {s["value"]: s for s in _rule_sets()}
        rule_set = sets.get(choice, sets["default"])

        ai_config = None
        ai_rules_result = None
        if ai_rules_text:
            from src.ai.rule_writer import generate_rules
            ai_rules_result = generate_rules(ai_rules_text)
            if ai_rules_result["config"]:
                ai_config = ai_rules_result["config"]

        report = service.analyze_upload(
            filename, file_data, required,
            config_path=rule_set.get("path"), auto_detect=rule_set["value"] == "auto",
            ai_config=ai_config,
        )
        if report.error:
            return render_template("error.html", message=report.error, filename=report.filename), 422

        from src.ai.summary import summarise
        ai_summary = summarise(report)

        session.pop("last_upload", None)  # cookies from before this change held the whole file
        session["upload_id"] = _keep_upload(file_data)
        session["last_filename"] = filename
        rule_source = "your plain-English rules (AI)" if ai_config else rule_set["source"]
        return render_template("report.html", report=report, rule_source=rule_source,
                               rule_label=rule_set["label"], all_rules=service.RULE_NAMES,
                               ai_summary=ai_summary, ai_rules_result=ai_rules_result)

    @app.errorhandler(413)
    def too_big(_error):
        return upload_page(f"That file is bigger than {MAX_UPLOAD_MB} MB. Please upload a smaller file.", 413)

    no_file = "No file to clean. Files are kept for an hour after checking, so please check it again."

    @app.get("/download-cleaned")
    def download_cleaned():
        file_data = _kept_upload(session.get("upload_id"))
        filename = session.get("last_filename", "data.csv")
        if not file_data:
            return upload_page(no_file, 400)
        cleaned_csv, _summary, _log = service.get_cleaned_csv(file_data)
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        return Response(
            cleaned_csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={stem}_cleaned.csv"},
        )

    @app.get("/download-changes")
    def download_changes():
        file_data = _kept_upload(session.get("upload_id"))
        filename = session.get("last_filename", "data.csv")
        if not file_data:
            return upload_page(no_file, 400)
        _csv, _summary, log = service.get_cleaned_csv(file_data)
        changes_csv = service.get_changes_csv(log)
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        return Response(
            changes_csv,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={stem}_changes.csv"},
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
