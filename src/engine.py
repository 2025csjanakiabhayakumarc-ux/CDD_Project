from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src import duplicates
from src.infer import infer_config
from src.loader import load_csv
from src.rules import india_formats, missing_values, range_and_format, required_columns
from src.rules._base import Finding

_DEFAULT_CONFIG = Path(__file__).parent.parent / "rules.yaml"


def load_config(path: str | Path = _DEFAULT_CONFIG) -> dict:
    """Read rules.yaml and return the config dict."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_all(df: pd.DataFrame, config: dict) -> list[Finding]:
    """Run every rule module with its settings and return all findings."""
    findings: list[Finding] = []

    findings += required_columns.check(
        df, columns=config.get("required_columns", {}).get("columns")
    )
    findings += missing_values.check(
        df, columns=config.get("missing_values", {}).get("columns")
    )
    findings += duplicates.check(
        df, subset=config.get("duplicates", {}).get("subset") or None
    )
    findings += range_and_format.check(
        df,
        percentage_columns=config.get("range_and_format", {}).get("percentage_columns"),
        date_columns=config.get("range_and_format", {}).get("date_columns"),
        email_columns=config.get("range_and_format", {}).get("email_columns"),
        date_format=config.get("range_and_format", {}).get("date_format", "%Y-%m-%d"),
    )

    india_cfg = config.get("india_formats", {})
    if india_cfg:
        findings += india_formats.check(
            df,
            phone_columns=india_cfg.get("phone_columns"),
            pincode_columns=india_cfg.get("pincode_columns"),
            pan_columns=india_cfg.get("pan_columns"),
            gstin_columns=india_cfg.get("gstin_columns"),
            ifsc_columns=india_cfg.get("ifsc_columns"),
        )

    return findings


def validate_file(path: str | Path, config_path: str | Path = _DEFAULT_CONFIG) -> list[Finding]:
    """Load a CSV and run all rules. Convenience wrapper for the Flask app."""
    df = load_csv(path)
    config = load_config(config_path)
    return run_all(df, config)


def validate_file_auto(path: str | Path) -> tuple[list[Finding], dict, dict[str, str]]:
    """Load a CSV, infer config from its contents, run all rules.

    Returns (findings, inferred_config, explanations).
    """
    df = load_csv(path)
    config, explanations = infer_config(df)
    findings = run_all(df, config)
    return findings, config, explanations
