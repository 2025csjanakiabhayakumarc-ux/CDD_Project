"""Rule: india_formats

Validates Indian data formats: phone numbers, pincodes, PAN, GSTIN, and IFSC codes.
"""
from __future__ import annotations

import re

import pandas as pd

from src.rules._base import Finding

RULE_ID = "india_formats"

_PHONE_RE = re.compile(r"^(?:\+91[\s-]?|91[\s-]?|0)?[6-9]\d{9}$")
_PINCODE_RE = re.compile(r"^[1-9]\d{5}$")
_PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$", re.IGNORECASE)
_GSTIN_RE = re.compile(
    r"^(0[1-9]|[12]\d|3[0-8])[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z\d]$",
    re.IGNORECASE,
)
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$", re.IGNORECASE)


def check(
    df: pd.DataFrame,
    phone_columns: list[str] | None = None,
    pincode_columns: list[str] | None = None,
    pan_columns: list[str] | None = None,
    gstin_columns: list[str] | None = None,
    ifsc_columns: list[str] | None = None,
    **_,
) -> list[Finding]:
    """Return one Finding per invalid Indian-format cell."""
    if df.empty:
        return []

    findings: list[Finding] = []

    for col in phone_columns or []:
        if col not in df.columns:
            continue
        for row_idx, value in df[col].items():
            if _is_empty(value):
                continue
            raw = re.sub(r"[\s-]", "", str(value).strip())
            if not _PHONE_RE.fullmatch(raw):
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        row=int(row_idx),
                        column=col,
                        message=f"Invalid phone number at row {row_idx}, column '{col}': {value}",
                        hint=f"Phone must be 10 digits starting 6-9, with optional +91/91/0 prefix; got '{value}'.",
                        severity="error",
                    )
                )

    for col in pincode_columns or []:
        if col not in df.columns:
            continue
        for row_idx, value in df[col].items():
            if _is_empty(value):
                continue
            raw = str(value).strip()
            if not _PINCODE_RE.fullmatch(raw):
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        row=int(row_idx),
                        column=col,
                        message=f"Invalid pincode at row {row_idx}, column '{col}': {value}",
                        hint=f"Pincode must be exactly 6 digits with first digit 1-9; got '{value}'.",
                        severity="error",
                    )
                )

    for col in pan_columns or []:
        if col not in df.columns:
            continue
        for row_idx, value in df[col].items():
            if _is_empty(value):
                continue
            raw = str(value).strip()
            if not _PAN_RE.fullmatch(raw):
                n = len(raw)
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        row=int(row_idx),
                        column=col,
                        message=f"Invalid PAN at row {row_idx}, column '{col}': {value}",
                        hint=f"PAN must be 10 chars like ABCDE1234F; got {n} chars.",
                        severity="error",
                    )
                )

    for col in gstin_columns or []:
        if col not in df.columns:
            continue
        for row_idx, value in df[col].items():
            if _is_empty(value):
                continue
            raw = str(value).strip()
            if not _GSTIN_RE.fullmatch(raw):
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        row=int(row_idx),
                        column=col,
                        message=f"Invalid GSTIN at row {row_idx}, column '{col}': {value}",
                        hint=f"GSTIN must be 15 chars: 2-digit state code (01-38) + PAN + entity + 'Z' + check; got '{value}'.",
                        severity="error",
                    )
                )

    for col in ifsc_columns or []:
        if col not in df.columns:
            continue
        for row_idx, value in df[col].items():
            if _is_empty(value):
                continue
            raw = str(value).strip()
            if not _IFSC_RE.fullmatch(raw):
                findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        row=int(row_idx),
                        column=col,
                        message=f"Invalid IFSC at row {row_idx}, column '{col}': {value}",
                        hint=f"IFSC must be 4 letters + '0' + 6 alphanumerics (e.g. SBIN0001234); got '{value}'.",
                        severity="error",
                    )
                )

    return findings


def _is_empty(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""
