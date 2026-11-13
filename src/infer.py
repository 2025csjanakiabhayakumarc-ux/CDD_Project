"""Infer a validation config from the shape of a DataFrame.

Scans column names and a sample of values to build a rules.yaml-compatible
dict so DataGuard can validate ANY CSV without hand-written config.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$"
)

_DATE_FORMATS = [
    ("%Y-%m-%d", "YYYY-MM-DD"),
    ("%d-%m-%Y", "DD-MM-YYYY"),
    ("%d/%m/%Y", "DD/MM/YYYY"),
]

_PCT_KEYWORDS = {"percent", "pct", "%", "attendance", "score"}
_ID_KEYWORDS = {"id", "no", "code", "roll"}

MATCH_THRESHOLD = 0.90
ID_UNIQUE_THRESHOLD = 0.95
MISSING_THRESHOLD = 0.05
SAMPLE_SIZE = 500


def infer_config(df: pd.DataFrame) -> tuple[dict, dict[str, str]]:
    """Infer a validation config dict and per-column explanations.

    Returns
    -------
    (config, explanations)
        config uses the same keys as rules.yaml so run_all() works unchanged.
        explanations maps column name -> human-readable reason.
    """
    if df.empty or len(df.columns) == 0:
        return {
            "required_columns": {"columns": []},
            "missing_values": {"columns": []},
            "duplicates": {"subset": []},
            "range_and_format": {},
        }, {}

    explanations: dict[str, str] = {}
    email_cols: list[str] = []
    date_cols: list[str] = []
    date_format: str = "%Y-%m-%d"
    pct_cols: list[str] = []
    id_cols: list[str] = []
    missing_cols: list[str] = []

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue

        sample = series.head(SAMPLE_SIZE).astype(str).str.strip()
        non_empty = sample[sample != ""]
        if non_empty.empty:
            continue

        total = len(non_empty)

        if _detect_email(non_empty, total, col, explanations):
            email_cols.append(col)
            continue

        fmt = _detect_date(non_empty, total, col, explanations)
        if fmt:
            date_cols.append(col)
            date_format = fmt
            continue

        if _detect_percentage(non_empty, total, col, explanations):
            pct_cols.append(col)
            continue

        if _detect_id(series, col, explanations):
            id_cols.append(col)
            continue

        explanations[col] = "no specific format detected"

    for col in df.columns:
        n_total = len(df[col])
        n_missing = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
        if n_total > 0 and (n_missing / n_total) <= MISSING_THRESHOLD:
            missing_cols.append(col)

    config = {
        "required_columns": {"columns": list(df.columns)},
        "missing_values": {"columns": missing_cols},
        "duplicates": {"subset": id_cols} if id_cols else {"subset": []},
        "range_and_format": {},
    }

    rf = config["range_and_format"]
    if email_cols:
        rf["email_columns"] = email_cols
    if date_cols:
        rf["date_columns"] = date_cols
        rf["date_format"] = date_format
    if pct_cols:
        rf["percentage_columns"] = pct_cols

    return config, explanations


def _detect_email(
    sample: pd.Series, total: int, col: str, explanations: dict[str, str]
) -> bool:
    matches = sample.apply(lambda v: bool(_EMAIL_RE.fullmatch(v))).sum()
    ratio = matches / total
    if ratio >= MATCH_THRESHOLD:
        explanations[col] = f"detected as email ({ratio:.0%} match)"
        return True
    return False


def _detect_date(
    sample: pd.Series, total: int, col: str, explanations: dict[str, str]
) -> str | None:
    for fmt, label in _DATE_FORMATS:
        matches = sample.apply(lambda v, f=fmt: _try_parse_date(v, f)).sum()
        ratio = matches / total
        if ratio >= MATCH_THRESHOLD:
            explanations[col] = f"detected as date {label} ({ratio:.0%} match)"
            return fmt
    return None


def _try_parse_date(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except (ValueError, TypeError):
        return False


def _detect_percentage(
    sample: pd.Series, total: int, col: str, explanations: dict[str, str]
) -> bool:
    col_lower = col.lower()
    if not any(kw in col_lower for kw in _PCT_KEYWORDS):
        return False

    numeric = pd.to_numeric(sample.str.rstrip("%"), errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return False

    in_range = ((valid >= 0) & (valid <= 100)).sum()
    ratio = in_range / total
    if ratio >= MATCH_THRESHOLD:
        explanations[col] = f"detected as percentage ({ratio:.0%} in 0-100 range)"
        return True
    return False


def _detect_id(
    series: pd.Series, col: str, explanations: dict[str, str]
) -> bool:
    col_lower = col.lower()
    if not any(kw in col_lower for kw in _ID_KEYWORDS):
        return False

    n_unique = series.nunique()
    n_total = len(series)
    if n_total == 0:
        return False

    ratio = n_unique / n_total
    if ratio >= ID_UNIQUE_THRESHOLD:
        explanations[col] = f"detected as id-like ({ratio:.0%} unique)"
        return True
    return False
