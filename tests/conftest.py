"""Shared test setup."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_real_gemini_calls(monkeypatch):
    """Tests never call the real Gemini API.

    src/webapp/app.py loads .env when it is imported, so once a developer puts a real
    key in .env, every test that opens a report would send sample data to Google: slow
    (a full run went from 13 s to 90 s), flaky when Google is busy, and not something a
    test should do. Tests that need a key set a fake one with monkeypatch and mock the call.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
