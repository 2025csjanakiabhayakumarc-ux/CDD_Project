"""Rule: missing_values

For each column in the config list, reports every cell that is NaN or
blank (empty string / whitespace-only). Returns one Finding per gap,
carrying the zero-based row index and column name so callers can pinpoint
exactly which cells need fixing.

Interface (same for every rule module):
    check(df, **config) -> List[Finding]
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.rules._base import Finding

RULE_ID = "missing_values"


def check(df: pd.DataFrame, columns: List[str] | None = None, **_) -> List[Finding]:
    """Return one Finding per empty/NaN cell in each watched column."""
    if not columns or df.empty:
        return []

    findings: List[Finding] = []
    for col in columns:
        if col not in df.columns:
            # Column absence is required_columns' job; skip silently here.
            continue

        series = df[col]
        # Treat NaN and whitespace-only strings as missing.
        is_blank = series.isna() | series.astype(str).str.strip().eq("")
        for row_idx in df.index[is_blank]:
            findings.append(
                Finding(
                    rule=RULE_ID,
                    message=f"Missing value at row {row_idx}, column '{col}'",
                    hint=f"Fill in a value for column '{col}' in row {row_idx}.",
                )
            )

    return findings
