"""Tests for src/rules/missing_values.py"""

from pathlib import Path

import pandas as pd
import pytest

from src.rules.missing_values import check, RULE_ID

DATA = Path(__file__).parent.parent / "sample_data"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def good_df():
    return pd.read_csv(DATA / "good.csv")


@pytest.fixture
def gaps_df():
    """CSV with NaN, empty string, and whitespace-only cells."""
    return pd.read_csv(DATA / "bad_missing_values.csv")


@pytest.fixture
def all_null_df():
    return pd.DataFrame({"x": [None, None], "y": [None, None]})


# ---------------------------------------------------------------------------
# Passing cases
# ---------------------------------------------------------------------------

def test_no_gaps_returns_empty(good_df):
    findings = check(good_df, columns=["name", "age", "email"])
    assert findings == []


def test_no_columns_configured_returns_empty(gaps_df):
    findings = check(gaps_df, columns=[])
    assert findings == []


def test_columns_kwarg_omitted_returns_empty(gaps_df):
    findings = check(gaps_df)
    assert findings == []


def test_empty_dataframe_returns_empty():
    findings = check(pd.DataFrame(), columns=["name"])
    assert findings == []


def test_column_not_in_df_is_skipped_silently(good_df):
    # missing_values silently skips absent columns (required_columns handles that)
    findings = check(good_df, columns=["nonexistent"])
    assert findings == []


# ---------------------------------------------------------------------------
# Failing cases
# ---------------------------------------------------------------------------

def test_nan_cell_reported(gaps_df):
    # Row 1 has NaN age
    findings = check(gaps_df, columns=["age"])
    row_indices = [f.message for f in findings]
    assert any("row 1" in m for m in row_indices)


def test_empty_string_cell_reported(gaps_df):
    # Row 2 has empty-string name
    findings = check(gaps_df, columns=["name"])
    assert any("row 2" in f.message for f in findings)


def test_whitespace_only_cell_reported(gaps_df):
    # Row 4 has whitespace-only age ("  ")
    findings = check(gaps_df, columns=["age"])
    assert any("row 4" in f.message for f in findings)


def test_multiple_columns_all_gaps_found(gaps_df):
    findings = check(gaps_df, columns=["name", "age", "email"])
    # Rows 1-4 each have at least one gap across the three columns
    reported_messages = [f.message for f in findings]
    assert len(findings) >= 4


def test_one_finding_per_cell_not_per_column(gaps_df):
    # Row 4 is missing both age and email — should give 2 findings
    findings = check(gaps_df, columns=["age", "email"])
    row4 = [f for f in findings if "row 4" in f.message]
    assert len(row4) == 2


def test_all_null_column_reports_every_row(all_null_df):
    findings = check(all_null_df, columns=["x"])
    assert len(findings) == 2


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------

def test_finding_has_correct_rule_id(gaps_df):
    findings = check(gaps_df, columns=["age"])
    assert all(f.rule == RULE_ID for f in findings)


def test_finding_includes_column_name_in_message(gaps_df):
    findings = check(gaps_df, columns=["email"])
    assert all("email" in f.message for f in findings)


def test_finding_hint_is_populated(gaps_df):
    findings = check(gaps_df, columns=["age"])
    assert all(f.hint != "" for f in findings)
