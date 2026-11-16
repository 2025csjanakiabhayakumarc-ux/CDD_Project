from __future__ import annotations

import pandas as pd

from src.anomalies import check


def _employees_df():
    return pd.DataFrame({
        "emp_id": [f"E{i:03d}" for i in range(1, 21)],
        "name": [f"Person {i}" for i in range(1, 21)],
        "salary": [
            55000, 62000, 48000, 51000, 59000,
            67000, 54000, 71000, 60000, 58000,
            63000, 52000, 66000, 49000, 57000,
            61000, 53000, 68000, 56000, 64000,
        ],
    })


def test_planted_outlier_is_caught():
    df = _employees_df()
    df.loc[5, "salary"] = 9_500_000
    findings = check(df, numeric_columns=["salary"])
    flagged_rows = {f.row for f in findings}
    assert 5 in flagged_rows, "The planted outlier at row 5 should be flagged"
    assert all(f.severity == "warning" for f in findings)
    assert all(f.rule_id == "anomalies" for f in findings)


def test_normal_data_gives_no_findings():
    df = _employees_df()
    findings = check(df, numeric_columns=["salary"])
    assert len(findings) == 0


def test_too_few_rows_skipped():
    df = pd.DataFrame({"value": [10, 20, 30, 40, 50]})
    findings = check(df, numeric_columns=["value"])
    assert findings == []


def test_blanks_not_flagged():
    df = _employees_df()
    df.loc[0, "salary"] = None
    df.loc[1, "salary"] = None
    findings = check(df, numeric_columns=["salary"])
    flagged_rows = {f.row for f in findings}
    assert 0 not in flagged_rows
    assert 1 not in flagged_rows


def test_auto_detect_numeric_columns():
    df = _employees_df()
    df.loc[5, "salary"] = 9_500_000
    findings = check(df)
    flagged_rows = {f.row for f in findings}
    assert 5 in flagged_rows


def test_empty_df():
    df = pd.DataFrame()
    assert check(df) == []
