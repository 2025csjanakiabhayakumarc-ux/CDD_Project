"""Flask app for DataGuard.

Run from the repo root:
    flask --app src.webapp.app run --debug
or:
    python -m src.webapp.app
"""
from __future__ import annotations

import os

from flask import Flask, render_template, request

from . import service

ALLOWED_SUFFIXES = (".csv", ".tsv", ".txt")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/validate")
    def validate():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return render_template("index.html", error="Please choose a CSV file first."), 400
        if not upload.filename.lower().endswith(ALLOWED_SUFFIXES):
            return render_template("index.html", error="That file type is not supported. Please upload a .csv file."), 400

        required = [c.strip() for c in request.form.get("required", "").split(",") if c.strip()]
        report = service.analyze_upload(upload.filename, upload.read(), required)
        if report.error:
            return render_template("error.html", message=report.error, filename=report.filename), 422
        return render_template("report.html", report=report)

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
