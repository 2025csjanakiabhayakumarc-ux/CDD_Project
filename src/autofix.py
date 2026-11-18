"""Safe automatic fixes and smart imputation for CSV data issues."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from sklearn.impute import KNNImputer

from src.anomalies import _is_code_column

# Formats auto-fix can read and rewrite in the rules' date format. Numeric ones are read
# day first (01-08-2005 is 1 August), the convention in India. Only these three were read
# before, so 2005.06.01 or "15 Jan 2005" were left as they were.
DATE_PARSE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y",
]

# Rows used as neighbours when estimating a blank number. Enough to find close
# matches, small enough that a 25 MB file is filled in seconds.
KNN_DONORS = 2000

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
    # Code columns (phone, pincode, account numbers) are labels, not amounts: two people
    # with close phone numbers are not alike, so they must not steer the estimate.
    numeric_cols = [
        c for c in df.columns
        if c.lower() not in protected and pd.api.types.is_numeric_dtype(df[c])
        and not _is_code_column(c)
    ]
    if not numeric_cols:
        return

    subset = df[numeric_cols].copy()
    mask_before = subset.isna()
    if not mask_before.any().any():
        return

    # KNN compares each row with a blank to every donor row. On a large file that is
    # billions of distances (a 10 MB file took minutes), so the donors are a fixed
    # random sample of KNN_DONORS rows, and only rows that have a blank are filled.
    needs = mask_before.any(axis=1)
    donors = subset if len(subset) <= KNN_DONORS else subset.sample(KNN_DONORS, random_state=0)
    imputer = KNNImputer(n_neighbors=3)
    imputer.fit(donors)
    filled_df = pd.DataFrame(imputer.transform(subset[needs]), columns=numeric_cols, index=subset.index[needs])

    for col in numeric_cols:
        known = subset[col].dropna()
        # A column of whole numbers (salaries, marks) gets a whole-number estimate.
        # 51333.33 in a salary column looked wrong, and the decimal made the cleaned
        # CSV write every other salary as 55000.0.
        whole = bool(len(known)) and bool((known % 1 == 0).all())
        for idx in subset.index[mask_before[col]]:
            new_val = filled_df.at[idx, col]
            if pd.notna(new_val):
                rounded = round(float(new_val)) if whole else round(float(new_val), 2)
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
        values = df[col]
        blank = values.isna() | (values.astype(str).str.strip() == "")
        for idx, val in values[blank].items():
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
        # Not is_string_dtype: it says a text column with even one blank (None/NaN) is
        # not text, so any column with a blank cell was never trimmed. The isinstance
        # check below still leaves blanks and numbers alone.
        dtype = df[col].dtype
        if not (pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)):
            continue
        # One pass over the column, then only the cells that change are touched.
        # Reading every cell with df.at took seconds on files of a few MB.
        values = df[col]
        changed = values.map(lambda v: isinstance(v, str) and v != v.strip())
        for idx, val in values[changed.astype(bool)].items():
            stripped = val.strip()
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
        values = df[col]
        is_text = values.map(lambda v: isinstance(v, str)).astype(bool)
        lowered = values[is_text].str.strip().str.lower()
        for idx in lowered.index[lowered != values[is_text]]:
            val, new = values.at[idx], lowered.at[idx]
            log.append({
                "row": int(idx),
                "column": col,
                "before": val,
                "after": new,
                "fix": "trim+lowercase" if val != val.strip() else "lowercase",
            })
            df.at[idx, col] = new


def _normalize_dates(
    df: pd.DataFrame, columns: list[str], target_format: str, log: list[dict],
) -> None:
    for col in columns:
        if col not in df.columns:
            continue
        raw = df[col].map(lambda v: "" if pd.isna(v) else str(v).strip())
        # Most cells are already right. Checking the whole column at once and only
        # parsing the rest took a 10 MB file from minutes to seconds.
        ok = pd.to_datetime(raw, format=target_format, errors="coerce")
        already = ok.notna() & (ok.dt.strftime(target_format) == raw)
        todo = raw[~already & (raw != "")]
        cache: dict[str, str | None] = {}
        for idx, value in todo.items():
            if value not in cache:
                parsed = _try_parse(value)
                cache[value] = parsed.strftime(target_format) if parsed else None
            normalized = cache[value]
            if normalized is None or normalized == value:
                continue
            log.append({
                "row": int(idx),
                "column": col,
                "before": value,
                "after": normalized,
                "fix": "normalize date",
            })
            df.at[idx, col] = normalized


def parse_date(value: str) -> tuple[datetime, str] | None:
    """(date, format it was written in) for a value in any DATE_PARSE_FORMATS, else None."""
    for fmt in DATE_PARSE_FORMATS:
        try:
            return datetime.strptime(value, fmt), fmt
        except (ValueError, TypeError):
            continue
    return None


def _try_parse(value: str) -> datetime | None:
    parsed = parse_date(value)
    return parsed[0] if parsed else None


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
