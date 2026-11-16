"""Tests for the auto-fix module."""
from __future__ import annotations

import pandas as pd

from src.autofix import fix


def test_strip_whitespace():
    df = pd.DataFrame({"name": [" Alice ", "Bob"], "city": ["  Delhi", "Mumbai "]})
    fixed, log = fix(df)
    assert fixed.at[0, "name"] == "Alice"
    assert fixed.at[1, "city"] == "Mumbai"
    assert any(e["fix"] == "trim whitespace" for e in log)


def test_lowercase_emails():
    df = pd.DataFrame({"email": ["Alice@Example.COM", "bob@test.org"]})
    fixed, log = fix(df, email_columns=["email"])
    assert fixed.at[0, "email"] == "alice@example.com"
    assert fixed.at[1, "email"] == "bob@test.org"
    assert any(e["fix"] == "lowercase" for e in log)


def test_trim_and_lowercase_email():
    df = pd.DataFrame({"email": [" A@X.COM "]})
    fixed, log = fix(df, email_columns=["email"])
    assert fixed.at[0, "email"] == "a@x.com"
    fixes = {e["fix"] for e in log if e["column"] == "email"}
    assert "trim whitespace" in fixes
    assert "lowercase" in fixes


def test_normalize_dates():
    df = pd.DataFrame({"dob": ["15-01-2024", "20/06/2024", "2024-03-10"]})
    fixed, _log = fix(df, date_columns=["dob"], date_format="%Y-%m-%d")
    assert fixed.at[0, "dob"] == "2024-01-15"
    assert fixed.at[1, "dob"] == "2024-06-20"
    assert fixed.at[2, "dob"] == "2024-03-10"


def test_unparseable_date_left_as_is():
    df = pd.DataFrame({"dob": ["not-a-date"]})
    fixed, log = fix(df, date_columns=["dob"])
    assert fixed.at[0, "dob"] == "not-a-date"
    assert not any(e["column"] == "dob" for e in log)


def test_drop_exact_duplicates():
    df = pd.DataFrame({"a": [1, 2, 1], "b": ["x", "y", "x"]})
    fixed, log = fix(df)
    assert len(fixed) == 2
    assert any(e["fix"] == "drop duplicate" for e in log)


def test_input_df_unchanged():
    df = pd.DataFrame({"email": [" A@X.COM "], "name": [" Bob "]})
    original_email = df.at[0, "email"]
    original_name = df.at[0, "name"]
    fix(df, email_columns=["email"])
    assert df.at[0, "email"] == original_email
    assert df.at[0, "name"] == original_name


def test_empty_dataframe():
    df = pd.DataFrame()
    fixed, log = fix(df)
    assert fixed.empty
    assert log == []


def test_no_changes_returns_empty_log():
    df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
    fixed, log = fix(df)
    assert log == []
    assert len(fixed) == 2


def test_knn_imputes_blank_salary():
    import numpy as np
    df = pd.DataFrame({
        "emp_id": [f"E{i}" for i in range(10)],
        "salary": [50000, 55000, 60000, np.nan, 52000, 58000, 61000, 54000, 57000, 59000],
    })
    fixed, log = fix(df)
    assert pd.notna(fixed.at[3, "salary"])
    knn_entries = [e for e in log if e["fix"] == "KNN imputation"]
    assert len(knn_entries) == 1
    assert knn_entries[0]["row"] == 3
    assert knn_entries[0]["column"] == "salary"
    assert knn_entries[0]["estimated"] is True


def test_dd_mm_yyyy_date_converted():
    df = pd.DataFrame({"join_date": ["15/01/2024", "2024-03-10"]})
    fixed, log = fix(df, date_columns=["join_date"], date_format="%Y-%m-%d")
    assert fixed.at[0, "join_date"] == "2024-01-15"
    date_entries = [e for e in log if e["fix"] == "normalize date"]
    assert len(date_entries) == 1


def test_id_columns_never_filled():
    import numpy as np
    df = pd.DataFrame({
        "emp_id": ["E001", np.nan, "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"],
        "name": ["Alice", np.nan, "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"],
        "email": ["a@co.com", np.nan, "c@co.com", "d@co.com", "e@co.com", "f@co.com", "g@co.com", "h@co.com", "i@co.com", "j@co.com"],
        "salary": [50000, 55000, 60000, 52000, 58000, 61000, 54000, 57000, 59000, 53000],
    })
    fixed, log = fix(df)
    assert pd.isna(fixed.at[1, "emp_id"])
    assert pd.isna(fixed.at[1, "name"])
    assert pd.isna(fixed.at[1, "email"])
    imputed_cols = {e["column"] for e in log if e.get("estimated")}
    assert "emp_id" not in imputed_cols
    assert "name" not in imputed_cols
    assert "email" not in imputed_cols


def test_change_log_marks_estimated():
    import numpy as np
    df = pd.DataFrame({
        "category": ["A", "A", "A", "", "A", "B", "A", "A", "A", "A"],
        "value": [10, 20, 30, np.nan, 50, 60, 70, 80, 90, 100],
    })
    _fixed, log = fix(df)
    estimated_entries = [e for e in log if e.get("estimated")]
    assert len(estimated_entries) >= 1
    for entry in estimated_entries:
        assert entry["estimated"] is True
