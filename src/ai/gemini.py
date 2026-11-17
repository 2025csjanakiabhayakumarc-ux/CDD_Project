"""One place that talks to Gemini, used by the summary and the rule writer.

Uses Google's current google-genai SDK. The older google-generativeai package is no
longer maintained, and the model it was pointed at (gemini-2.0-flash) was shut down
on 2026-06-01.
"""
from __future__ import annotations

import os
import sys

# Even a one-word reply took 6-7 s at busy times, so 8 s fell back to "Rule-based" too often.
TIMEOUT_SECONDS = 15
# Google's alias for its current Flash-Lite model, so the app keeps working when a numbered
# model is retired. Flash-Lite, not full Flash: summarising a list of problems is a light
# job, and on 2026-11-17 the full Flash models were answering "high demand" (503) or
# timing out while Flash-Lite replied. Set GEMINI_MODEL in .env to pin a model instead.
DEFAULT_MODEL = "gemini-flash-lite-latest"
# The -latest aliases exist only on v1beta; the SDK's default v1 answers 404 for them.
API_VERSION = "v1beta"


def model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def generate(key: str, prompt: str) -> str:
    """Send one prompt and return the reply text. Raises on any failure."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(
        api_version=API_VERSION, timeout=TIMEOUT_SECONDS * 1000))
    response = client.models.generate_content(model=model_name(), contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty reply")
    return text


def report_failure(feature: str, exc: Exception) -> None:
    """Print why a Gemini call failed, so a bad key or model name is visible.

    The callers fall back to the rule-based version after this, which on its own made
    a wrong key look exactly like no key at all.
    """
    message = str(exc)
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        message = message.replace(key, "<GEMINI_API_KEY>")
    print(
        f"[DataGuard AI] {feature} failed with model '{model_name()}': "
        f"{type(exc).__name__}: {message}. Using the rule-based version instead.",
        file=sys.stderr, flush=True,
    )
