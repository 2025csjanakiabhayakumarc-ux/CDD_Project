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


def test_phone_style_columns_are_not_scored_by_default():
    """A phone number is not high or low; india_formats already checks it.

    Before this guard, samples/employees.csv reported its wrong-prefix phone
    number twice: once correctly by india_formats, and once here as
    "unusual for this column (typical range 8,676,543,211-9,876,543,223)".
    """
    df = _employees_df()
    df["phone"] = [9876543210 + i for i in range(len(df))]
    df.loc[4, "phone"] = 5876543215  # wrong prefix for an Indian mobile

    assert [f.column for f in check(df)] == []


def test_a_named_code_column_is_still_scored_when_asked_for():
    """Naming a column explicitly is the user's choice and must be honoured."""
    df = _employees_df()
    df["phone"] = [9876543210 + i for i in range(len(df))]
    df.loc[4, "phone"] = 1

    assert [f.row for f in check(df, numeric_columns=["phone"])] == [4]


def test_measurement_columns_are_still_scored_by_default():
    """Guard the guard: the code-word list must not swallow real measurements."""
    df = _employees_df()
    df.loc[5, "salary"] = 9_500_000

    assert 5 in {f.row for f in check(df)}


def test_small_decimal_values_keep_their_decimals_in_the_range():
    """int() truncation reported a 0.11-0.15 column as "typical range 0-0"."""
    rates = [0.11, 0.12, 0.13, 0.11, 0.14, 0.12, 0.13, 0.15,
             0.12, 0.11, 0.13, 0.14, 0.12, 0.13, 9.80]
    df = pd.DataFrame({"sku": [f"S{i}" for i in range(len(rates))], "rate": rates})

    message = check(df, numeric_columns=["rate"])[0].message
    assert "0.11" in message and "0.15" in message
    assert "range 0–0" not in message
