"""Rule: required_columns

Checks that every column listed in the config is present in the DataFrame.
Column name comparison is case-sensitive.

Interface (same for every rule module):
    check(df, **config) -> List[Finding]
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.rules._base import Finding

RULE_ID = "required_columns"


def check(df: pd.DataFrame, columns: List[str] | None = None, **_) -> List[Finding]:
    """Return one Finding per missing required column, or [] if all present."""
    if not columns:
        return []

    missing = [col for col in columns if col not in df.columns]
    if not missing:
        return []

    return [
        Finding(
            rule=RULE_ID,
            message=f"Missing required column(s): {', '.join(missing)}",
            hint=f"Add the following column(s) to your CSV: {', '.join(missing)}",
        )
    ]
