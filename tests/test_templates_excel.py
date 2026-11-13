"""Tests for template configs and Excel upload support."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.engine import load_config, run_all
from src.loader import UnreadableFileError, load_file

TEMPLATES_DIR = Path(__file__).parent.parent / "templates_rules"
SAMPLES_DIR = Path(__file__).parent.parent / "samples"


# --- Excel loading ---

def test_load_xlsx(tmp_path):
    xlsx = tmp_path / "test.xlsx"
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    df.to_excel(xlsx, index=False, engine="openpyxl")
    result = load_file(str(xlsx))
    assert list(result.columns) == ["name", "age"]
    assert len(result) == 2


def test_load_xlsx_nonexistent(tmp_path):
    with pytest.raises(UnreadableFileError, match="not found"):
        load_file(str(tmp_path / "nope.xlsx"))


def test_load_csv_via_load_file(tmp_path):
    csv = tmp_path / "test.csv"
    csv.write_text("a,b\n1,2\n")
    result = load_file(str(csv))
    assert list(result.columns) == ["a", "b"]


# --- Template loading and validation ---

def _template_paths():
    return sorted(TEMPLATES_DIR.glob("*.yaml"))


@pytest.mark.parametrize("template_path", _template_paths(), ids=lambda p: p.stem)
def test_template_loads_as_valid_yaml(template_path):
    config = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    assert isinstance(config, dict)
    assert "required_columns" in config


@pytest.mark.parametrize(
    "template_name",
    ["sales_orders", "employees", "event_registrations", "inventory"],
)
def test_template_validates_sample_with_findings(template_name):
    template_path = TEMPLATES_DIR / f"{template_name}.yaml"
    sample_path = SAMPLES_DIR / f"{template_name}.csv"
    assert template_path.exists(), f"Template {template_name}.yaml missing"
    assert sample_path.exists(), f"Sample {template_name}.csv missing"

    config = load_config(template_path)
    df = pd.read_csv(sample_path)
    findings = run_all(df, config)
    assert len(findings) >= 1, f"Expected at least one finding for {template_name}"
