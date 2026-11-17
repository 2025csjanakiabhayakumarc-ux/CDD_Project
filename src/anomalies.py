from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.rules._base import Finding

RULE_ID = "anomalies"
MIN_ROWS = 10
MAD_THRESHOLD = 3.5


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
        cols = [c for c in numeric_columns if c in df.columns]
    else:
        cols = [c for c in df.select_dtypes(include=[np.number]).columns]

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
        lo = int(valid_values.quantile(0.05))
        hi = int(valid_values.quantile(0.95))

        outlier_positions = np.where(preds == -1)[0]
        for pos in outlier_positions:
            original_idx = valid_values.index[pos]
            val = valid_values.iloc[pos]

            if mad > 0 and 0.6745 * abs(val - median) / mad < MAD_THRESHOLD:
                continue

            val_display = f"{val:,.0f}" if abs(val) >= 1000 else str(val)
            findings.append(Finding(
                rule_id=RULE_ID,
                row=int(original_idx),
                column=col,
                message=f"{col} {val_display} is unusual for this column (typical range {lo:,}–{hi:,})",
                hint=f"Check whether {val_display} is correct for {col}. The typical range is {lo:,} to {hi:,}.",
                severity="warning",
            ))
    return findings
