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


def test_only_the_first_500_pairs_are_listed():
    import src.fuzzy_duplicates as fd
    df = pd.DataFrame({"name": [f"Rahul Verma{'a' * (i % 2)}" for i in range(80)]})
    findings = check(df, key_columns=["name"])
    pairs = [f for f in findings if f.row is not None]
    assert len(pairs) == fd.MAX_FINDINGS
    assert findings[-1].severity == "info"
    assert "more possible near-duplicates" in findings[-1].message


def test_long_values_that_differ_by_one_letter_are_still_reported():
    """Scores are whole numbers, so 99.6% rounds to 100; that must not count as identical."""
    long = "x" * 240
    df = pd.DataFrame({"name": [long + "a", long + "b"]})
    assert len(check(df, key_columns=["name"])) == 1


def test_big_files_compare_neighbours_and_say_so(monkeypatch):
    import src.fuzzy_duplicates as fd
    monkeypatch.setattr(fd, "FULL_COMPARE_ROWS", 10)
    names = [f"Unique Person {i:03d} {chr(97 + i % 26) * 3}" for i in range(40)]
    names[25] = "Rahul Verma"
    names[3] = "rahul  verma"
    findings = check(pd.DataFrame({"name": names}), key_columns=["name"])
    assert any(f.row == 25 and "row 3" in f.message for f in findings)
    assert findings[-1].severity == "info" and "nearest to it" in findings[-1].message
