from __future__ import annotations

from src.rules._base import Finding

RULE_ID = "duplicates"


def find_duplicates(df, subset=None):
    """
    Find duplicate rows in a DataFrame.

    Args:
        df: Input pandas DataFrame.
        subset: Columns to check for duplicates.
               If None, all columns are checked.

    Returns:
        DataFrame containing duplicate rows.
    """

    if df.empty:
        return df.copy()

    duplicate_rows = df[df.duplicated(subset=subset, keep="first")]

    return duplicate_rows


def check(df, subset=None, **_) -> list[Finding]:
    """Return one Finding per duplicate row (keeping first occurrence)."""
    dup_df = find_duplicates(df, subset=subset)
    findings: list[Finding] = []
    for row_idx in dup_df.index:
        col_desc = ", ".join(subset) if subset else "all columns"
        findings.append(
            Finding(
                rule_id=RULE_ID,
                row=int(row_idx),
                column=None,
                message=f"Duplicate row at index {row_idx} (checked: {col_desc})",
                hint=f"Remove or merge the duplicate row at index {row_idx}.",
            )
        )
    return findings
