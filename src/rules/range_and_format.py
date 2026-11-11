
"""Rule: range_and_format

Validates percentage, date and email columns in a DataFrame.
Returns one Finding for each invalid cell.
"""

from __future__ import annotations

import math
import re
from datetime import datetime

import pandas as pd

from src.hints.fix_hints import (
    date_hint,
    email_hint,
    percentage_hint,
)
from src.rules._base import Finding

RULE_ID = "range_and_format"

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$"
)


def check(
    df: pd.DataFrame,
    percentage_columns: list[str] | None = None,
    date_columns: list[str] | None = None,
    email_columns: list[str] | None = None,
    date_format: str = "%Y-%m-%d",
    **_,
) -> list[Finding]:
    """Return findings for invalid percentages, dates and email addresses."""

    if df.empty:
        return []

    findings: list[Finding] = []

    # 1. Percentage validation
    for col in percentage_columns or []:
        if col not in df.columns:
            continue

        for row_idx, value in df[col].items():
            if pd.isna(value) or str(value).strip() == "":
                continue

            raw_value = str(value).strip().removesuffix("%").strip()

            try:
                number = float(raw_value)
                valid = math.isfinite(number) and 0 <= number <= 100
            except ValueError:
                valid = False

            if not valid:
                findings.append(
                    Finding(
                        rule=RULE_ID,
                        message=(
                            f"Invalid percentage at row {row_idx}, "
                            f"column '{col}': {value}"
                        ),
                        hint=percentage_hint(col),
                    )
                )

    # 2. Date validation
    for col in date_columns or []:
        if col not in df.columns:
            continue

        for row_idx, value in df[col].items():
            if pd.isna(value) or str(value).strip() == "":
                continue

            try:
                datetime.strptime(str(value).strip(), date_format)
                valid = True
            except (ValueError, TypeError):
                valid = False

            if not valid:
                findings.append(
                    Finding(
                        rule=RULE_ID,
                        message=(
                            f"Invalid date at row {row_idx}, "
                            f"column '{col}': {value}"
                        ),
                        hint=date_hint(col, date_format),
                    )
                )

    # 3. Email validation
    for col in email_columns or []:
        if col not in df.columns:
            continue

        for row_idx, value in df[col].items():
            if pd.isna(value) or str(value).strip() == "":
                continue

            email = str(value).strip()

            if not EMAIL_PATTERN.fullmatch(email):
                findings.append(
                    Finding(
                        rule=RULE_ID,
                        message=(
                            f"Invalid email at row {row_idx}, "
                            f"column '{col}': {value}"
                        ),
                        hint=email_hint(col),
                    )
                )

    return findings
