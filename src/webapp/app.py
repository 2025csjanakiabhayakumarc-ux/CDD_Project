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
_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates_rules"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
    app.secret_key = os.environ.get("SECRET_KEY", "dataguard-dev-key")

    def _list_templates() -> list[str]:
        if _TEMPLATES_DIR.is_dir():
            return sorted(p.stem for p in _TEMPLATES_DIR.glob("*.yaml"))
        return []

    @app.get("/")
    def index():
        return render_template("index.html", templates=_list_templates())

    @app.post("/validate")
    def validate():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return render_template("index.html", error="Please choose a CSV file first."), 400
        if not upload.filename.lower().endswith(ALLOWED_SUFFIXES):
            return render_template(
                "index.html",
                templates=_list_templates(),
                error="That file type is not supported. Please upload a .csv or .xlsx file.",
            ), 400

        template_name = request.form.get("template", "")
        config_path = None
        if template_name and template_name != "default":
            candidate = _TEMPLATES_DIR / f"{template_name}.yaml"
            if candidate.is_file():
                config_path = str(candidate)

        file_data = upload.read()
        required = [c.strip() for c in request.form.get("required", "").split(",") if c.strip()]
        auto_detect = request.form.get("rule_mode") == "auto"
        report = service.analyze_upload(
            upload.filename, file_data, required,
            config_path=config_path, auto_detect=auto_detect,
        )
        if report.error:
            return render_template("error.html", message=report.error, filename=report.filename), 422

        session["last_upload"] = file_data
        session["last_filename"] = upload.filename
        return render_template("report.html", report=report)

    @app.get("/download-cleaned")
    def download_cleaned():
        file_data = session.get("last_upload")
        filename = session.get("last_filename", "data.csv")
        if not file_data:
            return render_template("index.html", error="No file to clean. Please upload a file first."), 400
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

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("index.html", error="That file is too big. The limit is 5 MB."), 413

    return app


if __name__ == "__main__":
    create_app().run(
        # Inside Docker the app must listen on all addresses, or the browser cannot reach it.
        host=os.environ.get("HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )
