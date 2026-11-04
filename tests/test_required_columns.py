"""Tests for src/rules/required_columns.py"""

import pandas as pd
import pytest

from src.rules.required_columns import check, RULE_ID


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def good_df():
    return pd.read_csv("sample_data/good.csv")


@pytest.fixture
def bad_df():
    return pd.read_csv("sample_data/bad_missing_columns.csv")


@pytest.fixture
def empty_df():
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Passing cases
# ---------------------------------------------------------------------------

def test_all_columns_present_returns_no_findings(good_df):
    findings = check(good_df, columns=["name", "age", "email"])
    assert findings == []


def test_subset_of_columns_required_passes(good_df):
    findings = check(good_df, columns=["name"])
    assert findings == []


def test_no_required_columns_configured_passes(good_df):
    findings = check(good_df, columns=[])
    assert findings == []


def test_columns_kwarg_omitted_passes(good_df):
    findings = check(good_df)
    assert findings == []


# ---------------------------------------------------------------------------
# Failing cases
# ---------------------------------------------------------------------------

def test_one_missing_column_returns_finding(bad_df):
    findings = check(bad_df, columns=["name", "age", "email"])
    assert len(findings) == 1
    assert findings[0].rule == RULE_ID
    assert "email" in findings[0].message


def test_multiple_missing_columns_reported_in_one_finding(empty_df):
    findings = check(empty_df, columns=["id", "name", "value"])
    assert len(findings) == 1
    assert "id" in findings[0].message
    assert "name" in findings[0].message
    assert "value" in findings[0].message


def test_finding_includes_hint(bad_df):
    findings = check(bad_df, columns=["name", "email"])
    assert findings[0].hint != ""
    assert "email" in findings[0].hint


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_column_match_is_case_sensitive(good_df):
    # "Name" != "name" — should flag it
    findings = check(good_df, columns=["Name"])
    assert len(findings) == 1
    assert "Name" in findings[0].message


def test_extra_columns_in_csv_are_ignored(good_df):
    # CSV has name/age/email; we only require name/age — extra cols are fine
    findings = check(good_df, columns=["name", "age"])
    assert findings == []
