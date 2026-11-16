from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz

from src.rules._base import Finding

RULE_ID = "near_duplicates"
DEFAULT_THRESHOLD = 90


def check(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    **_,
) -> list[Finding]:
    """Find rows whose key columns are very similar but not identical."""
    if df.empty or not key_columns:
        return []

    cols = [c for c in key_columns if c in df.columns]
    if not cols:
        return []

    keys: list[tuple[int, str]] = []
    for idx in df.index:
        parts = []
        for col in cols:
            val = df.at[idx, col]
            parts.append(str(val).strip().lower() if pd.notna(val) else "")
        keys.append((int(idx), " | ".join(parts)))

    findings: list[Finding] = []
    seen_pairs: set[tuple[int, int]] = set()

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            idx_a, text_a = keys[i]
            idx_b, text_b = keys[j]
            if text_a == text_b:
                continue
            score = fuzz.ratio(text_a, text_b)
            if score >= threshold:
                pair = (min(idx_a, idx_b), max(idx_a, idx_b))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                col_desc = ", ".join(cols)
                findings.append(Finding(
                    rule_id=RULE_ID,
                    row=idx_b,
                    column=col_desc,
                    message=(
                        f"Row {idx_b} is {score}% similar to row {idx_a} "
                        f"on [{col_desc}] — possible near-duplicate"
                    ),
                    hint=f"Compare rows {idx_a} and {idx_b} and merge or correct them.",
                    severity="warning",
                ))
    return findings
