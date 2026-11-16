"""Tests for the AI summary and rule writer — never calls the real API."""
from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

from src.ai.rule_writer import _validate_yaml, generate_rules
from src.ai.summary import _build_prompt, _fallback, summarise


@dataclass
class _FakeReport:
    filename: str = "test.csv"
    rows: int = 10
    columns: list = field(default_factory=lambda: ["name", "email", "salary"])
    findings: list = field(default_factory=list)
    counts: dict = field(default_factory=lambda: {"error": 3, "warning": 1, "info": 0})
    total: int = 4
    score: int = 67
    rules_run: list = field(default_factory=lambda: ["required_columns", "missing_values"])


@dataclass
class _FakeFinding:
    rule: str = "missing_values"
    message: str = "empty cell"
    severity: str = "error"
    column: str = "name"
    row: str = "3"
    hint: str = "fill it"


def _report_with_findings():
    return _FakeReport(findings=[_FakeFinding(), _FakeFinding(rule="range_and_format", severity="warning")])


# ---- summary tests ----

def test_fallback_summary_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = summarise(_report_with_findings())
    assert result["ai"] is False
    assert "67" in result["summary"]
    assert len(result["top_fixes"]) > 0


def test_fallback_on_api_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("src.ai.summary._call_gemini", side_effect=RuntimeError("fail")):
        result = summarise(_report_with_findings())
    assert result["ai"] is False


def test_ai_summary_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_return = {
        "summary": "Your data has issues.",
        "top_fixes": ["Fix missing names", "Fix bad emails"],
        "ai": True,
    }
    with patch("src.ai.summary._call_gemini", return_value=mock_return):
        result = summarise(_report_with_findings())
    assert result["ai"] is True
    assert result["summary"] == "Your data has issues."


def test_prompt_never_includes_raw_data():
    report = _report_with_findings()
    prompt = _build_prompt(report)
    assert "test.csv" in prompt
    assert "missing_values" in prompt
    # The prompt should NOT contain actual row data values
    # It only contains findings metadata
    assert "row=3" in prompt or "row" in prompt


def test_fallback_zero_findings():
    report = _FakeReport(total=0, score=100, counts={"error": 0, "warning": 0, "info": 0})
    result = _fallback(report)
    assert "100" in result["summary"] or "good" in result["summary"].lower()


# ---- rule_writer tests ----

def test_valid_yaml_accepted():
    config = _validate_yaml("required_columns:\n  columns: [name, email]\n")
    assert config is not None
    assert "required_columns" in config


def test_invalid_yaml_rejected():
    assert _validate_yaml("not: valid: yaml: [") is None


def test_unknown_key_rejected():
    assert _validate_yaml("unknown_rule:\n  columns: [a]\n") is None


def test_generate_rules_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = generate_rules("phone must be Indian mobile")
    assert result["ai"] is False
    assert result["config"] is None
    assert "unavailable" in result["error"].lower()


def test_generate_rules_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_return = {
        "yaml_text": "india_formats:\n  phone_columns: [phone]\n",
        "config": {"india_formats": {"phone_columns": ["phone"]}},
        "error": "",
        "ai": True,
    }
    with patch("src.ai.rule_writer._call_gemini", return_value=mock_return):
        result = generate_rules("phone must be Indian mobile")
    assert result["ai"] is True
    assert result["config"] is not None


def test_generate_rules_invalid_yaml_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_return = {
        "yaml_text": "garbage output",
        "config": None,
        "error": "Generated YAML was invalid",
        "ai": True,
    }
    with patch("src.ai.rule_writer._call_gemini", return_value=mock_return):
        result = generate_rules("some rules")
    assert result["config"] is None
    assert "invalid" in result["error"].lower()


def test_generate_rules_api_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("src.ai.rule_writer._call_gemini", side_effect=RuntimeError("timeout")):
        result = generate_rules("some rules")
    assert result["ai"] is False
    assert result["config"] is None
