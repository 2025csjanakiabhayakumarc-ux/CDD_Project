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


# ---- large files: the same fixes, done column-at-a-time ----

def test_mixed_date_formats_are_normalised_and_correct_ones_left_alone():
    df = pd.DataFrame({"d": ["2024-01-05", "05/01/2024", "05-01-2024", "", "not a date", "05/01/2024"]})
    _, log = fix(df, date_columns=["d"])
    dates = [(e["row"], e["before"], e["after"]) for e in log if e["fix"] == "normalize date"]
    assert dates == [(1, "05/01/2024", "2024-01-05"), (2, "05-01-2024", "2024-01-05"), (5, "05/01/2024", "2024-01-05")]


def test_emails_lowercased_only_where_needed():
    df = pd.DataFrame({"email": ["a@x.com", "B@X.com", " c@x.com ", None]})
    fixed, log = fix(df, email_columns=["email"])
    assert fixed["email"].tolist()[:3] == ["a@x.com", "b@x.com", "c@x.com"]
    assert sorted(e["fix"] for e in log if e["column"] == "email") == ["lowercase", "trim whitespace"]


def test_text_columns_with_a_blank_are_still_trimmed():
    """pandas calls a text column with a None "not text", so it was never trimmed."""
    df = pd.DataFrame({"name": ["  Asha  ", None, "Ravi "]})
    fixed, log = fix(df)
    names = fixed["name"].tolist()
    # The blank stays blank. Older pandas keeps it as None, newer pandas (CI) as NaN.
    assert names[0] == "Asha" and names[2] == "Ravi" and pd.isna(names[1])
    assert [e["fix"] for e in log] == ["trim whitespace", "trim whitespace"]


def test_more_date_formats_are_rewritten():
    df = pd.DataFrame({"d": ["2005.06.01", "15 Jan 2005", "01.08.2005", "Feb 16, 2005", "17-Mar-2005"]})
    fixed, _ = fix(df, date_columns=["d"])
    assert fixed["d"].tolist() == ["2005-06-01", "2005-01-15", "2005-08-01", "2005-02-16", "2005-03-17"]



# ---- blanks: names rebuilt from the email, numbers left for a person ----

def test_blank_salaries_are_left_blank_not_averaged():
    """An average looks like real data; the checks flag the blank for a person instead."""
    df = pd.DataFrame({"emp_id": ["E1", "E2", "E3", "E4"], "salary": [50000, 60000, 70000, None]})
    fixed, log = fix(df)
    assert pd.isna(fixed.at[3, "salary"])
    assert not [e for e in log if e["column"] == "salary"]


def test_name_from_email():
    from src.autofix import name_from_email
    assert name_from_email("anita.hegde164@company.com") == "Anita Hegde"
    assert name_from_email("ravi_kumar@x.in") == "Ravi Kumar"
    assert name_from_email("12345@x.com") == ""
    assert name_from_email("j@x.com") == ""
    assert name_from_email(None) == ""


def test_blank_names_are_rebuilt_from_the_email_and_marked():
    df = pd.DataFrame({"name": ["Asha Rao", "", None], "email": ["asha.rao1@c.com", "anita.hegde164@c.com", "99@c.com"]})
    fixed, log = fix(df, email_columns=["email"])
    assert fixed["name"].tolist()[:2] == ["Asha Rao", "Anita Hegde"]
    assert pd.isna(fixed.at[2, "name"])  # nothing to go on: left for a person
    filled = [e for e in log if e["fix"] == "name from email"]
    assert [(e["row"], e["after"], e["estimated"]) for e in filled] == [(1, "Anita Hegde", True)]


def test_repeated_id_keeps_the_row_whose_name_matches_the_email():
    df = pd.DataFrame({
        "emp_id": ["E1", "E1", "E2", "E2", "E3", "E3"],
        "name": ["Anita Hegde", "Anitaa Hegde", "Priyaa Gowda", "Priya Gowda", "", "h"],
        "email": ["anita.hegde1@c.com"] * 2 + ["priya.gowda2@c.com"] * 2 + ["lakshmi.hegde3@c.com"] * 2,
    })
    fixed, log = fix(df, email_columns=["email"], key_columns=["emp_id"])
    assert fixed.to_dict("list") == {
        "emp_id": ["E1", "E2", "E3"],
        "name": ["Anita Hegde", "Priya Gowda", "Lakshmi Hegde"],
        "email": ["anita.hegde1@c.com", "priya.gowda2@c.com", "lakshmi.hegde3@c.com"],
    }
    assert sum(e["fix"] == "drop duplicate" for e in log) == 3


def test_repeated_id_is_left_alone_when_no_name_matches():
    """Nothing to choose by: the duplicate check leaves it to a person."""
    df = pd.DataFrame({"emp_id": ["E1", "E1"], "name": ["Asha", "Usha"], "email": ["x1@c.com", "x1@c.com"]})
    fixed, _ = fix(df, email_columns=["email"], key_columns=["emp_id"])
    assert len(fixed) == 2
