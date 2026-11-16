"""Safe automatic fixes and smart imputation for CSV data issues."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from sklearn.impute import KNNImputer

_DATE_PARSE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]

ID_KEYWORDS = {"id", "name", "email", "student_id", "emp_id", "roll"}


def fix(
    df: pd.DataFrame,
    date_columns: list[str] | None = None,
    email_columns: list[str] | None = None,
    date_format: str = "%Y-%m-%d",
    id_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply safe fixes and smart imputation, return (fixed_df, change_log).

    The input df is never modified in place.
    """
    out = df.copy()
    log: list[dict] = []

    _strip_whitespace(out, log)
    _lowercase_emails(out, email_columns or [], log)
    _normalize_dates(out, date_columns or [], date_format, log)

    protected = _protected_columns(out, id_columns)
    _impute_numeric_knn(out, protected, log)
    _impute_categorical_mode(out, protected, log)

    out = _drop_exact_duplicates(out, log)

    return out, log


def _protected_columns(df: pd.DataFrame, id_columns: list[str] | None) -> set[str]:
    """Columns that should never be filled by imputation."""
    if id_columns is not None:
        return {c.lower() for c in id_columns}
    protected = set()
    for col in df.columns:
        if any(kw in col.lower() for kw in ID_KEYWORDS):
            protected.add(col.lower())
    return protected


def _impute_numeric_knn(
    df: pd.DataFrame, protected: set[str], log: list[dict],
) -> None:
    """Fill blank numeric cells using KNN imputation (k=3)."""
    numeric_cols = [
        c for c in df.columns
        if c.lower() not in protected and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not numeric_cols:
        return

    subset = df[numeric_cols].copy()
    mask_before = subset.isna()
    if not mask_before.any().any():
        return

    imputer = KNNImputer(n_neighbors=3)
    filled = imputer.fit_transform(subset)
    filled_df = pd.DataFrame(filled, columns=numeric_cols, index=df.index)

    for col in numeric_cols:
        for idx in df.index:
            if mask_before.at[idx, col]:
                new_val = filled_df.at[idx, col]
                if pd.notna(new_val):
                    rounded = round(new_val, 2)
                    log.append({
                        "row": int(idx),
                        "column": col,
                        "before": "",
                        "after": str(rounded),
                        "fix": "KNN imputation",
                        "estimated": True,
                    })
                    df.at[idx, col] = rounded


def _impute_categorical_mode(
    df: pd.DataFrame, protected: set[str], log: list[dict],
) -> None:
    """Fill blank categorical cells with the column's most frequent value."""
    for col in df.columns:
        if col.lower() in protected:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        mode_values = df[col].dropna()
        mode_values = mode_values[mode_values.astype(str).str.strip() != ""]
        if mode_values.empty:
            continue
        most_frequent = mode_values.mode().iloc[0]
        for idx in df.index:
            val = df.at[idx, col]
            if pd.isna(val) or (isinstance(val, str) and val.strip() == ""):
                log.append({
                    "row": int(idx),
                    "column": col,
                    "before": "" if pd.isna(val) else val,
                    "after": str(most_frequent),
                    "fix": "mode imputation",
                    "estimated": True,
                })
                df.at[idx, col] = most_frequent


def _strip_whitespace(df: pd.DataFrame, log: list[dict]) -> None:
    for col in df.columns:
        if not pd.api.types.is_string_dtype(df[col]):
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
    df: pd.DataFrame, columns: list[str], target_format: str, log: list[dict],
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


def _drop_exact_duplicates(df: pd.DataFrame, log: list[dict]) -> pd.DataFrame:
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
    return df.drop(index=dup_indices).reset_index(drop=True)
