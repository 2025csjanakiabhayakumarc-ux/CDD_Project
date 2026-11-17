from __future__ import annotations

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from src.rules._base import Finding

RULE_ID = "near_duplicates"
DEFAULT_THRESHOLD = 90
# Only this many pairs are written out. A large file can hold millions of similar
# pairs, and nobody reads past the first few hundred. The rest are only counted.
MAX_FINDINGS = 500
# Up to this many rows, every row is compared with every other row (a few seconds).
# That work grows with the square of the row count, so bigger files compare each row
# only with its WINDOW neighbours once the rows are sorted by their key.
FULL_COMPARE_ROWS = 20_000
WINDOW = 50
# Rows scored per batch. A batch holds a CHUNK x rows table of one-byte scores,
# so 500 x 20,000 rows is about 10 MB.
CHUNK = 500


def check(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    **_,
) -> list[Finding]:
    """Find rows whose key columns are very similar but not identical.

    Scoring runs in rapidfuzz's cdist, which is C code on all CPU cores, and the
    bookkeeping is done with numpy, so only the listed pairs touch Python.
    """
    if df.empty or not key_columns:
        return []

    cols = [c for c in key_columns if c in df.columns]
    if not cols:
        return []

    text = None
    for col in cols:
        part = df[col].astype("string").fillna("").str.strip().str.lower()
        text = part if text is None else text + " | " + part
    keys = text.tolist()
    # Same code means identical text: an exact duplicate, which the duplicates rule reports.
    codes = pd.factorize(text)[0]
    index = np.asarray(df.index)
    col_desc = ", ".join(cols)

    sampled = len(keys) > FULL_COMPARE_ROWS
    batches = _neighbour_pairs(keys, threshold) if sampled else _all_pairs(keys, threshold)

    findings: list[Finding] = []
    extra = 0
    for a, b, scores in batches:  # arrays of row positions, a before b in the file
        keep = codes[a] != codes[b]
        a, b, scores = a[keep], b[keep], scores[keep]
        room = MAX_FINDINGS - len(findings)
        extra += max(0, len(a) - room)
        for i, j, score in zip(a[:room], b[:room], scores[:room]):
            idx_a, idx_b = int(index[i]), int(index[j])
            findings.append(Finding(
                rule_id=RULE_ID,
                row=idx_b,
                column=col_desc,
                message=(
                    f"Row {idx_b} is {int(score)}% similar to row {idx_a} "
                    f"on [{col_desc}] — possible near-duplicate"
                ),
                hint=f"Compare rows {idx_a} and {idx_b} and merge or correct them.",
                severity="warning",
            ))

    if extra:
        findings.append(Finding(
            rule_id=RULE_ID, row=None, column=col_desc,
            message=f"{extra:,} more possible near-duplicates on [{col_desc}] were not listed.",
            hint=f"Only the first {MAX_FINDINGS} are shown. Fix those, then check the file again.",
            severity="info",
        ))
    if sampled:
        findings.append(Finding(
            rule_id=RULE_ID, row=None, column=col_desc,
            message=(f"This file has {len(keys):,} rows, so each row was compared with the "
                     f"{WINDOW} rows nearest to it in sorted order rather than with every row."),
            hint="Near-duplicates whose first letters differ may be missed. Split the file to check every pair.",
            severity="info",
        ))
    return findings


def _all_pairs(keys: list[str], threshold: int):
    """Batches of every pair (a, b, score) with a < b and score >= threshold, in file order."""
    for start in range(0, len(keys), CHUNK):
        block = keys[start:start + CHUNK]
        # Compare this batch with itself and every later row, so each pair is seen once.
        scores = process.cdist(block, keys[start:], scorer=fuzz.ratio, score_cutoff=threshold,
                               workers=-1, dtype=np.uint8)
        scores[np.tril_indices(len(block), m=scores.shape[1])] = 0  # self and earlier pairs
        a, b = np.nonzero(scores)
        yield start + a, start + b, scores[a, b]


def _neighbour_pairs(keys: list[str], threshold: int):
    """Batches of pairs among rows within WINDOW of each other once sorted by key."""
    order = np.argsort(np.array(keys, dtype=object), kind="stable")
    for start in range(0, len(order), CHUNK):
        rows = order[start:start + CHUNK + WINDOW]
        block = [keys[i] for i in rows]
        scores = process.cdist(block[:CHUNK], block, scorer=fuzz.ratio, score_cutoff=threshold,
                               workers=-1, dtype=np.uint8)
        a, b = np.nonzero(scores)
        near = (b > a) & (b - a <= WINDOW)  # each pair once, and only close neighbours
        a, b = a[near], b[near]
        first, second = rows[a], rows[b]
        yield np.minimum(first, second), np.maximum(first, second), scores[a, b]
