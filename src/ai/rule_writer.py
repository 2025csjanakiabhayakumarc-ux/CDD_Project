"""Generate YAML rules from plain-English descriptions using Gemini.

Validates the generated YAML against the existing rules loader before
using it. Falls back to the chosen template if the YAML is invalid.
"""
from __future__ import annotations

import os
from typing import Any

from src.ai import gemini

VALID_RULE_KEYS = {
    "required_columns", "missing_values", "duplicates",
    "range_and_format", "india_formats", "anomalies", "near_duplicates",
}


def generate_rules(description: str) -> dict:
    """Return {"yaml_text": str, "config": dict|None, "error": str, "ai": bool}.

    config is the parsed dict if valid, None if parsing/validation failed.
    """
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {"yaml_text": "", "config": None, "error": "AI unavailable, using template", "ai": False}

    try:
        return _call_gemini(key, description)
    except Exception as exc:  # noqa: BLE001
        gemini.report_failure("Rule writer", exc)
        return {"yaml_text": "", "config": None,
                "error": "AI could not write rules (details in the terminal), using the template", "ai": False}


def _call_gemini(key: str, description: str) -> dict:
    prompt = (
        "You are a data-quality rules generator for DataGuard. "
        "Convert the following plain-English rules into YAML config.\n\n"
        f"User says: \"{description}\"\n\n"
        "Available rule sections (use only these top-level keys):\n"
        "- required_columns:  columns: [list of column names]\n"
        "- missing_values:    columns: [list of column names]\n"
        "- duplicates:        subset: [list of column names]\n"
        "- range_and_format:  percentage_columns, date_columns, email_columns, date_format\n"
        "- india_formats:     phone_columns, pincode_columns, pan_columns\n"
        "- anomalies:         numeric_columns: [list], contamination: float\n"
        "- near_duplicates:   key_columns: [list], threshold: int\n\n"
        "Output ONLY valid YAML, no markdown fences, no explanation."
    )

    yaml_text = gemini.generate(key, prompt)
    yaml_text = yaml_text.removeprefix("```yaml").removeprefix("```").removesuffix("```").strip()

    config = _validate_yaml(yaml_text)
    if config is None:
        return {"yaml_text": yaml_text, "config": None, "error": "Generated YAML was invalid", "ai": True}

    return {"yaml_text": yaml_text, "config": config, "error": "", "ai": True}


def _validate_yaml(yaml_text: str) -> dict[str, Any] | None:
    """Parse YAML and check that all top-level keys are known rule names."""
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(data, dict):
        return None

    for key in data:
        if key not in VALID_RULE_KEYS:
            return None

    return data
