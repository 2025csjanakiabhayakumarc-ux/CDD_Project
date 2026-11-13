"""Safe automatic fixes for common CSV data issues.

Never guesses data — only applies reversible, deterministic transformations.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

_DATE_PARSE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]


def fix(
    df: pd.DataFrame,
    date_columns: list[str] | None = None,
    email_columns: list[str] | None = None,
    date_format: str = "%Y-%m-%d",
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply safe fixes and return (fixed_df, change_log).

    The input df is never modified in place.
    """
    out = df.copy()
    log: list[dict] = []

    _strip_whitespace(out, log)
    _lowercase_emails(out, email_columns or [], log)
    _normalize_dates(out, date_columns or [], date_format, log)
    _drop_exact_duplicates(out, log)

    return out, log


def _strip_whitespace(df: pd.DataFrame, log: list[dict]) -> None:
    for col in df.columns:
        if df[col].dtype != object:
            continue
        for idx in df.index:
            val = df.at[idx, col]
            if not isinstance(val, str):
                continue
            stripped = val.strip()
            if stripped != val:
                log.append({
                    "row": int(idx),
                    "column": col,
                    "before": val,
                    "after": stripped,
                    "fix": "trim whitespace",
                })
                df.at[idx, col] = stripped


def _lowercase_emails(df: pd.DataFrame, columns: list[str], log: list[dict]) -> None:
    for col in columns:
        if col not in df.columns:
            continue
        for idx in df.index:
            val = df.at[idx, col]
            if not isinstance(val, str):
                continue
            lowered = val.strip().lower()
            if lowered != val:
                fix_type = "trim+lowercase" if val != val.strip() else "lowercase"
                log.append({
                    "row": int(idx),
                    "column": col,
                    "before": val,
                    "after": lowered,
                    "fix": fix_type,
                })
                df.at[idx, col] = lowered


def _normalize_dates(
    df: pd.DataFrame, columns: list[str], target_format: str, log: list[dict]
) -> None:
    for col in columns:
        if col not in df.columns:
            continue
        for idx in df.index:
            val = df.at[idx, col]
            if pd.isna(val):
                continue
            raw = str(val).strip()
            if not raw:
                continue
            parsed = _try_parse(raw)
            if parsed is None:
                continue
            normalized = parsed.strftime(target_format)
            if normalized != raw:
                log.append({
                    "row": int(idx),
                    "column": col,
                    "before": raw,
                    "after": normalized,
                    "fix": "normalize date",
                })
                df.at[idx, col] = normalized


def _try_parse(value: str) -> datetime | None:
    for fmt in _DATE_PARSE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _drop_exact_duplicates(df: pd.DataFrame, log: list[dict]) -> int:
    mask = df.duplicated(keep="first")
    dup_indices = df.index[mask].tolist()
    for idx in dup_indices:
        log.append({
            "row": int(idx),
            "column": None,
            "before": "duplicate row",
            "after": "removed",
            "fix": "drop duplicate",
        })
    df.drop(index=dup_indices, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return len(dup_indices)
