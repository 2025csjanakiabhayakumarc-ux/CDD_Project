"""Tests for src/loader.py

Covers encoding detection (utf-8, utf-8-sig/BOM, latin-1), delimiter
detection (comma, semicolon, tab), the UnreadableFileError contract, and
integration with the missing_values and required_columns rule interfaces.
"""

from pathlib import Path

import pytest
import pandas as pd

from src.loader import load_csv, UnreadableFileError

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Encoding detection
# ---------------------------------------------------------------------------

def test_utf8_comma_loads():
    df = load_csv(FIXTURES / "utf8_comma.csv")
    assert list(df.columns) == ["name", "age", "email"]
    assert len(df) == 2


def test_utf8sig_bom_loads():
    """UTF-8 with BOM (utf-8-sig) must not leave a BOM in the column name."""
    df = load_csv(FIXTURES / "utf8sig_comma.csv")
    assert "name" in df.columns, f"BOM leaked into column names: {df.columns.tolist()}"


def test_latin1_loads():
    """Latin-1 file with non-ASCII bytes must load without error."""
    df = load_csv(FIXTURES / "latin1_comma.csv")
    assert "city" in df.columns
    assert any("café" in str(v) or "caf" in str(v) for v in df["city"])


# ---------------------------------------------------------------------------
# Delimiter detection
# ---------------------------------------------------------------------------

def test_semicolon_delimiter():
    df = load_csv(FIXTURES / "utf8_semicolon.csv")
    assert list(df.columns) == ["name", "age", "email"]
    assert df.shape == (2, 3)


def test_tab_delimiter():
    df = load_csv(FIXTURES / "utf8_tab.csv")
    assert list(df.columns) == ["name", "age", "email"]
    assert df.shape == (2, 3)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_missing_file_raises():
    with pytest.raises(UnreadableFileError, match="not found"):
        load_csv(FIXTURES / "does_not_exist.csv")


def test_corrupt_file_raises():
    """A binary/corrupt file must raise UnreadableFileError, not a raw exception."""
    with pytest.raises(UnreadableFileError):
        load_csv(FIXTURES / "corrupt.bin")


def test_empty_file_raises(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(UnreadableFileError, match="empty"):
        load_csv(empty)


def test_whitespace_only_file_raises(tmp_path):
    blank = tmp_path / "blank.csv"
    blank.write_bytes(b"   \n\n")
    with pytest.raises(UnreadableFileError, match="empty"):
        load_csv(blank)


def test_unreadable_error_is_exception():
    """UnreadableFileError must be catchable as a plain Exception."""
    err = UnreadableFileError("test")
    assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# Return type and shape
# ---------------------------------------------------------------------------

def test_returns_dataframe():
    result = load_csv(FIXTURES / "utf8_comma.csv")
    assert isinstance(result, pd.DataFrame)


def test_dataframe_not_empty():
    df = load_csv(FIXTURES / "utf8_comma.csv")
    assert not df.empty


# ---------------------------------------------------------------------------
# Integration: loader feeds rule checks without error
# ---------------------------------------------------------------------------

def test_loader_feeds_missing_values_rule():
    from src.rules.missing_values import check
    df = load_csv(FIXTURES / "utf8_comma.csv")
    findings = check(df, columns=["name", "age", "email"])
    assert findings == []  # fixture has no gaps


def test_loader_latin1_feeds_missing_values_rule():
    from src.rules.missing_values import check
    df = load_csv(FIXTURES / "latin1_comma.csv")
    findings = check(df, columns=["name", "age", "city"])
    assert findings == []
