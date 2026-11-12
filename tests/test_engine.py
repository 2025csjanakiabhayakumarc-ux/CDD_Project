from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.engine import load_config, run_all, validate_file

RULES_YAML = Path(__file__).parent.parent / "rules.yaml"


def test_load_config_returns_dict():
    config = load_config(RULES_YAML)
    assert isinstance(config, dict)
    assert "required_columns" in config


def test_run_all_clean_df_returns_no_findings():
    df = pd.DataFrame({
        "name": ["Alice", "Bob"],
        "student_id": [1, 2],
        "attendance": [85, 90],
        "email": ["a@example.com", "b@example.com"],
        "dob": ["2000-01-01", "2001-06-15"],
    })
    config = load_config(RULES_YAML)
    findings = run_all(df, config)
    assert findings == []


def test_run_all_catches_bad_percentage():
    df = pd.DataFrame({
        "name": ["Alice"],
        "student_id": [1],
        "attendance": [150],
        "email": ["a@example.com"],
        "dob": ["2000-01-01"],
    })
    config = load_config(RULES_YAML)
    findings = run_all(df, config)
    assert any(f.rule_id == "range_and_format" for f in findings)


def test_run_all_catches_missing_value():
    df = pd.DataFrame({
        "name": [""],
        "student_id": [1],
        "attendance": [80],
        "email": ["a@example.com"],
        "dob": ["2000-01-01"],
    })
    config = load_config(RULES_YAML)
    findings = run_all(df, config)
    assert any(f.rule_id == "missing_values" for f in findings)


def test_validate_file_returns_findings_for_bad_csv(tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("name,student_id,attendance,email,dob\n,1,150,bad-email,2000-13-01\n")
    findings = validate_file(csv, RULES_YAML)
    assert len(findings) >= 3
