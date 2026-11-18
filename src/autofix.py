"""Safe automatic fixes and smart imputation for CSV data issues."""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

# Formats auto-fix can read and rewrite in the rules' date format. Numeric ones are read
# day first (01-08-2005 is 1 August), the convention in India. Only these three were read
# before, so 2005.06.01 or "15 Jan 2005" were left as they were.
DATE_PARSE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y.%m.%d", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y",
]

ID_KEYWORDS = {"id", "name", "email", "student_id", "emp_id", "roll"}


def fix(
    df: pd.DataFrame,
    date_columns: list[str] | None = None,
    email_columns: list[str] | None = None,
    date_format: str = "%Y-%m-%d",
    id_columns: list[str] | None = None,
    key_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    """Apply safe fixes, return (fixed_df, change_log).

    key_columns: the columns that identify a record (e.g. emp_id), from the
    duplicates rule. The input df is never modified in place.

    Blank numbers (salaries, marks) are left blank on purpose: an average is a guess
    that looks like real data, so the checks flag them for a person instead.
    """
    out = df.copy()
    log: list[dict] = []

    _strip_whitespace(out, log)
    _lowercase_emails(out, email_columns or [], log)
    _normalize_dates(out, date_columns or [], date_format, log)

    names, email = _name_columns(out), _email_column(out, email_columns)
    _names_from_email(out, names, email, log)

    protected = _protected_columns(out, id_columns)
    _impute_categorical_mode(out, protected, log)

    out = _drop_wrong_name_copies(out, key_columns or [], names, email, log)
    out = _drop_exact_duplicates(out, log)

    return out, log


def name_from_email(email: object) -> str:
    """The person's name an email address spells: anita.hegde164@x.com -> "Anita Hegde".

    Returns "" when the address has no letters to go on.
    """
    if not isinstance(email, str) or not email.strip():
        return ""
    local = email.strip().split("@")[0]
    # Digits, dots, underscores, hyphens and plus signs separate the words: anita.hegde164
    # -> ["anita", "hegde"].
    parts = re.split(r"[\d._+\-\s]+", local)
    parts = [p for p in parts if p]
    if not parts or not all(p.isalpha() for p in parts) or max(len(p) for p in parts) < 2:
        return ""
    return " ".join(p.capitalize() for p in parts)


def _name_columns(df: pd.DataFrame) -> list[str]:
    """Columns holding a person's full name: called "name", or ending in "name"/"_name"."""
    out = []
    for col in df.columns:
        c = str(col).lower().replace(" ", "_")
        if c in {"name", "full_name", "fullname", "student_name", "emp_name", "employee_name"}:
            out.append(col)
    return out


def _email_column(df: pd.DataFrame, email_columns: list[str] | None) -> str | None:
    for col in email_columns or []:
        if col in df.columns:
            return col
    for col in df.columns:
        if "email" in str(col).lower() or str(col).lower() in {"mail", "e_mail"}:
            return col
    return None


def _names_from_email(df: pd.DataFrame, names: list[str], email: str | None, log: list[dict]) -> None:
    """Fill a blank name from the email address on the same row, marked as filled."""
    if not names or email is None:
        return
    for col in names:
        values = df[col]
        blank = values.isna() | (values.astype(str).str.strip() == "")
        for idx in values.index[blank]:
            guess = name_from_email(df.at[idx, email])
            if not guess:
                continue  # nothing to go on: left blank for a person
            log.append({
                "row": int(idx),
                "column": col,
                "before": "",
                "after": guess,
                "fix": "name from email",
                "estimated": True,
            })
            df.at[idx, col] = guess


def _drop_wrong_name_copies(
    df: pd.DataFrame, keys: list[str], names: list[str], email: str | None, log: list[dict],
) -> pd.DataFrame:
    """For records repeated under one ID, keep the row whose name matches the email.

    E0000164 appears as "Anita Hegde" and as "Anitaa Hegde", both with
    anita.hegde164@company.com: the second is a mistyped copy. When some rows of a
    repeated ID match their email and others don't, the others are removed. If none
    or all match, nothing is removed and the duplicate check leaves it to a person.
    """
    keys = [k for k in keys if k in df.columns]
    if not keys or not names or email is None:
        return df
    name = names[0]
    repeated = df[df.duplicated(keys, keep=False)]
    if repeated.empty:
        return df
    norm = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()
    matches = repeated.apply(
        lambda r: bool(name_from_email(r[email])) and norm(r[name]) == norm(name_from_email(r[email])), axis=1)
    drop: list[int] = []
    for _, group in matches.groupby([repeated[k] for k in keys]):
        if group.any() and not group.all():
            drop.extend(group.index[~group])
    for idx in drop:
        log.append({
            "row": int(idx),
            "column": None,
            "before": f"copy of {df.loc[idx, keys[0]]} named \"{df.at[idx, name]}\"",
            "after": "removed",
            "fix": "drop duplicate",
        })
    return df.drop(index=drop)


def _protected_columns(df: pd.DataFrame, id_columns: list[str] | None) -> set[str]:
    """Columns that should never be filled by imputation."""
    if id_columns is not None:
        return {c.lower() for c in id_columns}
    protected = set()
    for col in df.columns:
        if any(kw in col.lower() for kw in ID_KEYWORDS):
            protected.add(col.lower())
    return protected


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
