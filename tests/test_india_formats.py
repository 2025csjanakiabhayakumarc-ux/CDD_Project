"""Tests for India-specific format validators."""
from __future__ import annotations

import pandas as pd

from src.rules.india_formats import check

# --- Phone ---

def test_valid_phone_10_digits():
    df = pd.DataFrame({"phone": ["9876543210"]})
    assert check(df, phone_columns=["phone"]) == []


def test_valid_phone_with_plus91():
    df = pd.DataFrame({"phone": ["+91 9876543210"]})
    assert check(df, phone_columns=["phone"]) == []


def test_valid_phone_with_zero_prefix():
    df = pd.DataFrame({"phone": ["09876543210"]})
    assert check(df, phone_columns=["phone"]) == []


def test_invalid_phone_starts_with_5():
    df = pd.DataFrame({"phone": ["5876543210"]})
    findings = check(df, phone_columns=["phone"])
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert "Phone" in findings[0].hint


def test_invalid_phone_too_short():
    df = pd.DataFrame({"phone": ["98765"]})
    findings = check(df, phone_columns=["phone"])
    assert len(findings) == 1


# --- Pincode ---

def test_valid_pincode():
    df = pd.DataFrame({"pincode": ["110001"]})
    assert check(df, pincode_columns=["pincode"]) == []


def test_invalid_pincode_starts_with_zero():
    df = pd.DataFrame({"pincode": ["010001"]})
    findings = check(df, pincode_columns=["pincode"])
    assert len(findings) == 1
    assert "6 digits" in findings[0].hint


def test_invalid_pincode_too_long():
    df = pd.DataFrame({"pincode": ["1100012"]})
    findings = check(df, pincode_columns=["pincode"])
    assert len(findings) == 1


# --- PAN ---

def test_valid_pan():
    df = pd.DataFrame({"pan": ["ABCDE1234F"]})
    assert check(df, pan_columns=["pan"]) == []


def test_valid_pan_lowercase():
    df = pd.DataFrame({"pan": ["abcde1234f"]})
    assert check(df, pan_columns=["pan"]) == []


def test_invalid_pan_wrong_length():
    df = pd.DataFrame({"pan": ["ABCDE123"]})
    findings = check(df, pan_columns=["pan"])
    assert len(findings) == 1
    assert "8 chars" in findings[0].hint


def test_invalid_pan_wrong_pattern():
    df = pd.DataFrame({"pan": ["12345ABCDE"]})
    findings = check(df, pan_columns=["pan"])
    assert len(findings) == 1


# --- GSTIN ---

def test_valid_gstin():
    df = pd.DataFrame({"gstin": ["27ABCDE1234F1Z5"]})
    assert check(df, gstin_columns=["gstin"]) == []


def test_invalid_gstin_bad_state_code():
    df = pd.DataFrame({"gstin": ["99ABCDE1234F1Z5"]})
    findings = check(df, gstin_columns=["gstin"])
    assert len(findings) == 1
    assert "state code" in findings[0].hint


def test_invalid_gstin_too_short():
    df = pd.DataFrame({"gstin": ["27ABCDE"]})
    findings = check(df, gstin_columns=["gstin"])
    assert len(findings) == 1


# --- IFSC ---

def test_valid_ifsc():
    df = pd.DataFrame({"ifsc": ["SBIN0001234"]})
    assert check(df, ifsc_columns=["ifsc"]) == []


def test_invalid_ifsc_no_zero():
    df = pd.DataFrame({"ifsc": ["SBIN1001234"]})
    findings = check(df, ifsc_columns=["ifsc"])
    assert len(findings) == 1
    assert "SBIN0001234" in findings[0].hint


def test_invalid_ifsc_too_short():
    df = pd.DataFrame({"ifsc": ["SBIN0"]})
    findings = check(df, ifsc_columns=["ifsc"])
    assert len(findings) == 1


# --- General ---

def test_empty_cells_skipped():
    df = pd.DataFrame({"phone": [None, "", "  "], "pan": [None, "", "  "]})
    findings = check(df, phone_columns=["phone"], pan_columns=["pan"])
    assert findings == []


def test_row_is_1_indexed():
    df = pd.DataFrame({"phone": ["bad"]})
    findings = check(df, phone_columns=["phone"])
    assert findings[0].row == 0  # 0-indexed like other rules


def test_empty_dataframe():
    df = pd.DataFrame()
    assert check(df, phone_columns=["phone"]) == []


def test_nonexistent_column_skipped():
    df = pd.DataFrame({"x": [1]})
    assert check(df, phone_columns=["phone"]) == []
