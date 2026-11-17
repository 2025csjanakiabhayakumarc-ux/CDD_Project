from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.rules._base import Finding

RULE_ID = "anomalies"
MIN_ROWS = 10
MAD_THRESHOLD = 3.5

# Numbers that are labels rather than measurements. Scoring these produces
# nonsense: a phone number is not high or low, it is right or wrong, and
# india_formats already checks it. Matched against the words in a column name.
CODE_WORDS = {
    "id", "no", "num", "number", "code", "roll", "serial", "sl", "key", "ref",
    "phone", "mobile", "contact", "telephone", "whatsapp",
    "pin", "pincode", "zip", "postal", "aadhaar", "aadhar",
    "pan", "gstin", "ifsc", "account", "acct", "card", "otp",
}


def check(
    df: pd.DataFrame,
    numeric_columns: list[str] | None = None,
    contamination: float = 0.05,
    **_,
) -> list[Finding]:
    """Flag outlier rows using IsolationForest on numeric columns.

    A secondary modified-z-score gate (using median absolute deviation)
    prevents flagging values within the normal spread of the column.
    """
    if df.empty:
        return []

    if numeric_columns:
        # An explicit list is the user's choice: score exactly what was asked for.
        cols = [c for c in numeric_columns if c in df.columns]
    else:
        cols = [
            c for c in df.select_dtypes(include=[np.number]).columns
            if not _is_code_column(c)
        ]

    findings: list[Finding] = []
    for col in cols:
        series = pd.to_numeric(df[col], errors="coerce")
        valid_mask = series.notna()
        if valid_mask.sum() < MIN_ROWS:
            continue

        valid_values = series[valid_mask]
        values = valid_values.values.reshape(-1, 1)

        model = IsolationForest(
            contamination=contamination, random_state=42, n_estimators=100,
        )
        preds = model.fit_predict(values)

        median = valid_values.median()
        mad = np.median(np.abs(valid_values.values - median))
        lo, hi = _typical_range(valid_values, median, mad)

        outlier_positions = np.where(preds == -1)[0]
        for pos in outlier_positions:
            original_idx = valid_values.index[pos]
            val = valid_values.iloc[pos]

            if mad > 0 and 0.6745 * abs(val - median) / mad < MAD_THRESHOLD:
                continue

            val_display = _tidy(val)
            findings.append(Finding(
                rule_id=RULE_ID,
                row=int(original_idx),
                column=col,
                message=f"{col} {val_display} is unusual for this column (typical range {lo}–{hi})",
                hint=f"Check whether {val_display} is correct for {col}. The typical range is {lo} to {hi}.",
                severity="warning",
            ))
    return findings


def _typical_range(values: pd.Series, median: float, mad: float) -> tuple[str, str]:
    """The span the ordinary values cover, as two display strings.

    The outliers are left out of this calculation. Taking the 95th percentile
    of the whole column interpolates into the outlier itself on a short file:
    a column of rates between 0.11 and 0.15 with one 9.80 in it was being
    described as a "typical range" reaching 3.04, a value nothing is near.
    """
    ordinary = values
    if mad > 0:
        inliers = values[0.6745 * (values - median).abs() / mad < MAD_THRESHOLD]
        if len(inliers) >= 2:
            ordinary = inliers
    return _tidy(ordinary.min()), _tidy(ordinary.max())


def _is_code_column(name: str) -> bool:
    """True when the column name says the numbers are labels, not measurements."""
    words = {w for w in re.split(r"[^a-z0-9]+", str(name).lower()) if w}
    return bool(words & CODE_WORDS)


def _tidy(value: float) -> str:
    """Format a number for reading, keeping decimals only where they matter.

    int() truncation turned a column of rates between 0.11 and 0.15 into a
    "typical range 0-0", so small values keep two decimal places.
    """
    number = float(value)
    if number == int(number):
        return f"{int(number):,}"
    return f"{number:,.2f}" if abs(number) < 1000 else f"{number:,.0f}"
