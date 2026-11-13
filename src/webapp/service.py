"""Bridge between the web pages and the DataGuard checking code.

The web pages never talk to the rules directly. They only call
analyze_upload() in this file. If a teammate changes what a rule takes in
or gives back, this is the ONLY file you need to edit.

Two modes:
  * DataGuard engine: used when src/loader.py and the rule modules exist.
    Every rule is called as check(df, **settings), where the settings come
    from that rule's section in rules.yaml.
  * Demo engine: a small built-in checker, so the UI works on its own
    while the rest of the team is still building.
"""
from __future__ import annotations

import csv
import dataclasses
import importlib
import io
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

MAX_FINDINGS_SHOWN = 500

# (rule name, modules to look in, function names to look for)
RULES = (
    ("required_columns", ("src.rules.required_columns",), ("check",)),
    ("missing_values", ("src.rules.missing_values",), ("check",)),
    ("duplicates", ("src.rules.duplicates", "src.duplicates"), ("check", "find_duplicates")),
    ("range_and_format", ("src.rules.range_and_format",), ("check",)),
    ("india_formats", ("src.rules.india_formats",), ("check",)),
)

# These rules still work with no settings (duplicates checks every column).
RUNS_WITHOUT_SETTINGS = {"duplicates"}

# The team's rules count rows from 0 (the first data row is "row 0"). Spreadsheet
# users see the heading as row 1 and the first data row as row 2, so we add 2.
# If the team ever changes the rules to use spreadsheet rows, set this to 0.
ROW_OFFSET = 2

# Plain-language tips used until a rule supplies its own hint (Member 4's job).
DEFAULT_HINTS = {
    "required_columns": "Add the missing column to your file, or fix the spelling of its heading.",
    "missing_values": "Fill in the empty cell, or delete the row if you do not need it.",
    "duplicates": "Keep one copy of the repeated row and delete the others.",
    "range_and_format": "Check the value against the allowed range or format, then correct it.",
}

_SEVERITY_WORDS = {
    "error": "error", "err": "error", "critical": "error", "fatal": "error", "high": "error",
    "warning": "warning", "warn": "warning", "medium": "warning",
    "info": "info", "information": "info", "notice": "info", "low": "info",
}

_LOCATION = re.compile(r"row\s+(\d+).*?column\s+'([^']+)'", re.IGNORECASE)
_ROW_WORD = re.compile(r"\b(row|index) (\d+)\b", re.IGNORECASE)


class UnreadableUpload(Exception):
    """The uploaded file could not be read as a table."""


@dataclass
class UiFinding:
    rule: str
    message: str
    severity: str = "error"
    column: str = ""
    row: str = ""
    hint: str = ""


@dataclass
class Report:
    filename: str
    rows: int = 0
    columns: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    counts: dict = field(default_factory=lambda: {"error": 0, "warning": 0, "info": 0})
    total: int = 0
    score: int = 100
    rules_run: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    engine: str = "demo"
    error: str = ""

    @property
    def truncated(self) -> bool:
        return self.total > len(self.findings)

    @property
    def band(self) -> str:
        if self.score >= 90:
            return "good"
        if self.score >= 70:
            return "ok"
        return "poor"


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------
def analyze_upload(
    filename: str,
    data: bytes,
    required: list[str] | None = None,
    config_path: str | None = None,
) -> Report:
    """Check an uploaded file and return a Report for the pages to show."""
    required = required or []
    report = Report(filename=filename)
    try:
        engine = _load_engine()
        if engine:
            report.engine = "dataguard"
            findings = _run_engine(engine, filename, data, required, report, config_path=config_path)
        else:
            report.engine = "demo"
            findings = _run_demo(data, required, report)
    except UnreadableUpload as exc:
        report.error = str(exc)
        return report

    _finish(report, findings)
    return report


# --------------------------------------------------------------------------
# Finishing touches shared by both engines
# --------------------------------------------------------------------------
def _finish(report: Report, findings: list[UiFinding]) -> None:
    for f in findings:
        if not f.hint:
            f.hint = DEFAULT_HINTS.get(f.rule, "Review this value and correct it.")
    counts = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.severity] += 1

    rows_hit = {f.row for f in findings if f.row}
    whole_file = sum(1 for f in findings if not f.row)
    penalty = round(100 * len(rows_hit) / max(report.rows, 1)) + 10 * whole_file
    report.score = max(0, min(100, 100 - penalty))

    report.counts = counts
    report.total = len(findings)
    report.findings = findings[:MAX_FINDINGS_SHOWN]


# --------------------------------------------------------------------------
# DataGuard engine (teammates' code)
# --------------------------------------------------------------------------
def _find_function(modules, names):
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for name in names:
            fn = getattr(module, name, None)
            if callable(fn):
                return fn
    return None


def _load_engine():
    if os.environ.get("DATAGUARD_UI_DEMO") == "1":
        return None
    try:
        loader = importlib.import_module("src.loader")
    except ImportError:
        return None
    load_csv = getattr(loader, "load_csv", None)
    if not callable(load_csv):
        return None
    rules = []
    for name, modules, names in RULES:
        fn = _find_function(modules, names)
        if fn:
            rules.append((name, fn))
    load_file = getattr(loader, "load_file", load_csv)
    return {
        "load_csv": load_csv,
        "load_file": load_file,
        "unreadable": getattr(loader, "UnreadableFileError", UnreadableUpload),
        "rules": rules,
    }


def _config_path() -> Path:
    override = os.environ.get("DATAGUARD_RULES")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "rules.yaml"  # the repo root


def _load_config_from(path_str: str) -> tuple[dict, str]:
    """Load a specific YAML config. Returns (settings, note)."""
    try:
        import yaml
    except ImportError:
        return {}, "PyYAML is not installed."
    path = Path(path_str)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}, f"Template file ({path.name}) not found."
    except yaml.YAMLError:
        return {}, f"Template file ({path.name}) could not be parsed."
    if not isinstance(data, dict):
        return {}, f"Template file ({path.name}) is not in the expected format."
    return data, ""


def _load_config() -> tuple[dict, str]:
    """Read rules.yaml. Returns (settings, note). The note is empty when all is well."""
    try:
        import yaml
    except ImportError:
        return {}, "PyYAML is not installed, so rules.yaml could not be read. Run: pip install pyyaml"
    path = _config_path()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}, f"The settings file ({path.name}) was not found, so most checks were skipped."
    except yaml.YAMLError:
        return {}, f"The settings file ({path.name}) could not be understood. Check its formatting."
    if not isinstance(data, dict):
        return {}, f"The settings file ({path.name}) is not in the expected format."
    return data, ""


def _tidy(finding: UiFinding) -> UiFinding:
    """Fill in row and column from the message text, and use spreadsheet row numbers."""
    match = _LOCATION.search(finding.message)
    if match:
        finding.row = finding.row or match.group(1)
        finding.column = finding.column or match.group(2)
    if ROW_OFFSET and finding.row.isdigit():
        def shift(text: str) -> str:
            return _ROW_WORD.sub(lambda m: f"row {int(m.group(2)) + ROW_OFFSET}", text)

        finding.row = str(int(finding.row) + ROW_OFFSET)
        finding.message = shift(finding.message)
        finding.hint = shift(finding.hint)
    return finding


def _normalise(item, rule: str) -> UiFinding:
    """Turn whatever a rule returns for one problem into a UiFinding."""
    if isinstance(item, dict):
        data = item
    elif dataclasses.is_dataclass(item) and not isinstance(item, type):
        data = dataclasses.asdict(item)
    elif hasattr(item, "__dict__"):
        data = vars(item)
    else:
        data = {"message": str(item)}

    def pick(*names):
        for name in names:
            value = data.get(name)
            if value not in (None, ""):
                return str(value)
        return ""

    severity = _SEVERITY_WORDS.get(pick("severity", "level").lower(), "error")
    return _tidy(
        UiFinding(
            rule=pick("rule_id", "rule", "rule_name", "name") or rule,
            message=pick("message", "msg", "description", "detail") or "A problem was found here.",
            severity=severity,
            column=pick("column", "col", "field"),
            row=pick("row", "row_number", "line", "index"),
            hint=pick("hint", "fix_hint", "suggestion", "fix"),
        )
    )


def _row_label(index) -> str:
    try:
        return str(int(index) + 2)  # +2: spreadsheet row, counting the heading line
    except (TypeError, ValueError):
        return str(index)


def _to_findings(result, rule: str) -> list[UiFinding]:
    if result is None:
        return []
    if hasattr(result, "iterrows") and hasattr(result, "index"):  # a pandas table of bad rows
        message = "This row repeats another row." if rule == "duplicates" else "A problem was found in this row."
        return [UiFinding(rule=rule, message=message, severity="warning", row=_row_label(i)) for i in result.index]
    if isinstance(result, dict):
        return [_normalise(result, rule)]
    if isinstance(result, (str, bytes, bool, int, float)):
        raise TypeError(f"unexpected result of type {type(result).__name__}")
    return [_normalise(item, rule) for item in result]


def _call_rule(fn, name, df, settings, required):
    """Call one rule as fn(df, **settings). Returns (findings, note); findings is None if skipped."""
    kwargs = dict(settings) if isinstance(settings, dict) else {}
    if name == "required_columns" and required:
        kwargs["columns"] = required  # columns typed on the upload page win
    if name in RUNS_WITHOUT_SETTINGS:
        if not kwargs.get("subset"):
            kwargs.pop("subset", None)  # an empty list means "check every column"
    elif not any(kwargs.values()):
        return None, f"The {name} check was skipped because rules.yaml has no settings for it."
    try:
        return _to_findings(fn(df, **kwargs), name), ""
    except KeyError:
        return None, f"The {name} check was skipped because a column named in rules.yaml is not in your file."
    except Exception as exc:  # noqa: BLE001 - a crashing rule must not break the page
        return None, f"The {name} check could not run: {exc}. Update service.py to match its inputs."


def _run_engine(engine, filename, data, required, report, config_path=None):
    folder = Path(tempfile.mkdtemp(prefix="dataguard_"))
    try:
        path = folder / ("upload" + (Path(filename).suffix or ".csv"))
        path.write_bytes(data)
        load_fn = engine.get("load_file", engine["load_csv"])
        try:
            df = load_fn(str(path))
        except engine["unreadable"] as exc:
            raise UnreadableUpload(str(exc) or "We could not read this file as a table.") from exc
        report.rows = len(df)
        report.columns = [str(c) for c in df.columns]

        if config_path:
            config, config_note = _load_config_from(config_path)
        else:
            config, config_note = _load_config()
        if config_note:
            report.notes.append(config_note)

        findings: list[UiFinding] = []
        for name, fn in engine["rules"]:
            found, note = _call_rule(fn, name, df, config.get(name), required)
            if note:
                report.notes.append(note)
            if found is None:
                continue
            report.rules_run.append(name)
            findings.extend(found)
        return findings
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# --------------------------------------------------------------------------
# Demo engine (works with no teammate code)
# --------------------------------------------------------------------------
_EMPTY = {"", "nan", "null", "none", "n/a", "na"}


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnreadableUpload("We could not read the text in this file.")


def _run_demo(data: bytes, required: list[str], report: Report) -> list[UiFinding]:
    text = _decode(data)
    if not text.strip():
        raise UnreadableUpload("This file is empty. Please choose a CSV that has a heading row and some data.")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    header, body = rows[0], rows[1:]
    report.columns = [h.strip() for h in header]
    report.rows = sum(1 for r in body if r)

    findings: list[UiFinding] = []

    have = {c.lower() for c in report.columns}
    for name in required:
        if name.lower() not in have:
            findings.append(UiFinding("required_columns", f'The column "{name}" is missing.', "error", column=name))
    report.rules_run.append("required_columns")

    for line, row in enumerate(body, start=2):
        for pos, cell in enumerate(row):
            if cell.strip().lower() in _EMPTY:
                col = report.columns[pos] if pos < len(report.columns) else f"column {pos + 1}"
                findings.append(UiFinding("missing_values", "This cell is empty.", "error", column=col, row=str(line)))
    report.rules_run.append("missing_values")

    seen: dict[tuple, int] = {}
    for line, row in enumerate(body, start=2):
        if not row:
            continue
        key = tuple(c.strip() for c in row)
        if key in seen:
            findings.append(UiFinding("duplicates", f"This row repeats row {seen[key]}.", "warning", row=str(line)))
        else:
            seen[key] = line
    report.rules_run.append("duplicates")

    return findings
