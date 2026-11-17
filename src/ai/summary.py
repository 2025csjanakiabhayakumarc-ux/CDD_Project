"""AI-powered plain-English summary of validation findings.

Sends ONLY the findings (rule, row, column, message, severity) and column
names to the Gemini API — never the raw data rows.

Falls back to a rule-based summary when the API key is missing or the
call fails/times out.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.ai import gemini

if TYPE_CHECKING:
    from src.webapp.service import Report


def summarise(report: Report) -> dict:
    """Return {"summary": str, "top_fixes": list[str], "ai": bool}.

    ai=True means Gemini produced the text; ai=False means fallback.
    """
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return _fallback(report)

    prompt = _build_prompt(report)
    try:
        return _call_gemini(key, prompt)
    except Exception as exc:  # noqa: BLE001
        gemini.report_failure("Summary", exc)
        return _fallback(report)


def _build_prompt(report: Report) -> str:
    findings_text = []
    for f in report.findings[:50]:
        findings_text.append(
            f"- [{f.severity}] rule={f.rule} row={f.row} col={f.column}: {f.message}"
        )
    return (
        f"You are a data-quality assistant. A CSV file named '{report.filename}' "
        f"with {report.rows} rows and columns {report.columns} was validated.\n"
        f"Score: {report.score}/100. "
        f"Errors: {report.counts['error']}, Warnings: {report.counts['warning']}.\n\n"
        f"Findings:\n" + "\n".join(findings_text) + "\n\n"
        "Give a 3-4 sentence plain-English summary of the data quality, then list "
        "the top 3 things to fix first (one sentence each). "
        "Format: first the summary paragraph, then a blank line, then each fix on "
        "its own line starting with a number and period (1. 2. 3.)."
    )


def _call_gemini(key: str, prompt: str) -> dict:
    text = gemini.generate(key, prompt)

    parts = text.split("\n\n", 1)
    summary = parts[0].strip()
    fixes = []
    if len(parts) > 1:
        for line in parts[1].strip().splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                fixes.append(line.lstrip("0123456789.").strip())
    return {"summary": summary, "top_fixes": fixes[:3], "ai": True}


_RULE_PHRASES = {
    "required_columns": "Missing columns",
    "missing_values": "Blank cells in required fields",
    "duplicates": "Repeated rows",
    "range_and_format": "Badly formatted or out-of-range values",
    "india_formats": "Invalid Indian phone numbers or codes",
    "anomalies": "Unusual values",
    "near_duplicates": "Rows that look like near-copies",
}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _fallback(report: Report) -> dict:
    """Rule-based summary when AI is unavailable."""
    total = report.total
    errors = report.counts["error"]
    warnings = report.counts["warning"]
    score = report.score
    rows = _plural(report.rows, "row")

    found = " and ".join(p for p in (
        _plural(errors, "error") if errors else "",
        _plural(warnings, "warning") if warnings else "",
    ) if p) or _plural(total, "note")

    if total == 0:
        summary = f"Your file looks good. All {rows} passed every check."
    elif score >= 80:
        summary = f"Your file scored {score} out of 100, with {found}. Most of the {rows} are fine, but a few need attention."
    elif score >= 50:
        summary = (
            f"Your file scored {score} out of 100. There are {found} across {rows}. "
            "Several records need correcting before this data is reliable."
        )
    else:
        summary = (
            f"Your file scored {score} out of 100 and needs significant work. "
            f"There are {found} across {rows}."
        )

    rule_counts: dict[str, int] = {}
    for f in report.findings:
        rule_counts[f.rule] = rule_counts.get(f.rule, 0) + 1

    fixes = []
    for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1])[:3]:
        what = _RULE_PHRASES.get(rule, rule.replace("_", " ").capitalize())
        fixes.append(f"{what}: {count} to fix")

    return {"summary": summary, "top_fixes": fixes, "ai": False}
