
"""Tests for the range_and_format validation rule."""

import pandas as pd

from src.rules.range_and_format import RULE_ID, check


def test_valid_data_returns_no_findings():
    df = pd.DataFrame({
        "marks": [75, 90],
        "date_of_birth": ["2005-03-23", "2006-05-10"],
        "email": ["a@gmail.com", "b@gmail.com"],
    })

    findings = check(
        df,
        percentage_columns=["marks"],
        date_columns=["date_of_birth"],
        email_columns=["email"],
    )

    assert findings == []


def test_invalid_percentage():
    df = pd.DataFrame({"marks": [120]})

    findings = check(df, percentage_columns=["marks"])

    assert len(findings) == 1
    assert findings[0].rule_id == RULE_ID
    assert "percentage" in findings[0].message.lower()


def test_invalid_date():
    df = pd.DataFrame({"dob": ["2026-02-31"]})

    findings = check(df, date_columns=["dob"])

    assert len(findings) == 1
    assert "date" in findings[0].message.lower()


def test_invalid_email():
    df = pd.DataFrame({"email": ["student@"]})

    findings = check(df, email_columns=["email"])

    assert len(findings) == 1
    assert "email" in findings[0].message.lower()


def test_hint_is_provided():
    df = pd.DataFrame({"marks": [150]})

    findings = check(df, percentage_columns=["marks"])

    assert findings[0].hint != ""


def test_missing_values_are_skipped():
    df = pd.DataFrame({"marks": [None, ""]})

    findings = check(df, percentage_columns=["marks"])

    assert findings == []
    

# ------------------------------------------------
# Additional percentage validation tests
# ------------------------------------------------

def test_zero_percentage_is_valid():
    df = pd.DataFrame({"marks": [0]})
    assert check(df, percentage_columns=["marks"]) == []


def test_hundred_percentage_is_valid():
    df = pd.DataFrame({"marks": [100]})
    assert check(df, percentage_columns=["marks"]) == []


def test_negative_percentage_is_invalid():
    df = pd.DataFrame({"marks": [-10]})
    findings = check(df, percentage_columns=["marks"])
    assert len(findings) == 1


def test_non_numeric_percentage_is_invalid():
    df = pd.DataFrame({"marks": ["abc"]})
    findings = check(df, percentage_columns=["marks"])
    assert len(findings) == 1


def test_infinite_percentage_is_invalid():
    df = pd.DataFrame({"marks": [float("inf")]})
    findings = check(df, percentage_columns=["marks"])
    assert len(findings) == 1


# ------------------------------------------------
# Additional date validation tests
# ------------------------------------------------

def test_leap_year_date_is_valid():
    df = pd.DataFrame({"dob": ["2024-02-29"]})
    assert check(df, date_columns=["dob"]) == []


def test_invalid_leap_year_date_is_rejected():
    df = pd.DataFrame({"dob": ["2025-02-29"]})
    findings = check(df, date_columns=["dob"])
    assert len(findings) == 1


def test_wrong_date_format_is_rejected():
    df = pd.DataFrame({"dob": ["23-03-2006"]})
    findings = check(df, date_columns=["dob"])
    assert len(findings) == 1


# ------------------------------------------------
# Additional email validation tests
# ------------------------------------------------

def test_email_without_at_symbol_is_invalid():
    df = pd.DataFrame({"email": ["studentgmail.com"]})
    findings = check(df, email_columns=["email"])
    assert len(findings) == 1


def test_email_without_domain_is_invalid():
    df = pd.DataFrame({"email": ["student@"]})
    findings = check(df, email_columns=["email"])
    assert len(findings) == 1


def test_multiple_invalid_emails_are_detected():
    df = pd.DataFrame({
        "email": ["student@", "invalid-email", "test.com"]
    })
    findings = check(df, email_columns=["email"])
    assert len(findings) == 3


# ------------------------------------------------
# General validation tests
# ------------------------------------------------

def test_nonexistent_column_is_skipped():
    df = pd.DataFrame({"marks": [80]})

    findings = check(
        df,
        percentage_columns=["unknown"]
    )

    assert findings == []


def test_empty_dataframe_returns_no_findings():
    df = pd.DataFrame()

    findings = check(
        df,
        percentage_columns=["marks"],
        date_columns=["dob"],
        email_columns=["email"],
    )

    assert findings == []


def test_percentage_string_with_percent_symbol():
    df = pd.DataFrame({"marks": ["85%"]})

    findings = check(df, percentage_columns=["marks"])

    assert findings == []

