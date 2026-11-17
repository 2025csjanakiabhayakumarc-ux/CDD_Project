from __future__ import annotations

import pandas as pd

from src.fuzzy_duplicates import check


def test_near_duplicate_pair_is_caught():
    df = pd.DataFrame({
        "name": ["Rahul Verma", "rahul  verma", "Anita Desai"],
        "email": ["rahul@co.com", "rahul@co.com", "anita@co.com"],
    })
    findings = check(df, key_columns=["name", "email"])
    assert len(findings) >= 1
    assert any(f.row == 1 for f in findings)
    assert all(f.severity == "warning" for f in findings)
    assert all(f.rule_id == "near_duplicates" for f in findings)


def test_identical_rows_not_flagged():
    df = pd.DataFrame({
        "name": ["Rahul Verma", "Rahul Verma"],
        "email": ["rahul@co.com", "rahul@co.com"],
    })
    findings = check(df, key_columns=["name", "email"])
    assert len(findings) == 0


def test_distinct_rows_not_flagged():
    df = pd.DataFrame({
        "name": ["Priya Sharma", "Amit Patel", "Deepa Reddy"],
        "email": ["priya@co.com", "amit@co.com", "deepa@co.com"],
    })
    findings = check(df, key_columns=["name", "email"])
    assert len(findings) == 0


def test_no_key_columns_returns_empty():
    df = pd.DataFrame({"name": ["A", "B"]})
    assert check(df, key_columns=[]) == []
    assert check(df, key_columns=None) == []


def test_empty_df():
    df = pd.DataFrame()
    assert check(df, key_columns=["name"]) == []
