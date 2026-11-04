"""CSV loader with automatic encoding and delimiter detection.

Entry point for loading CSV files before rule checks. Tries encodings in
priority order (utf-8-sig, utf-8, latin-1) and sniffs the delimiter using
the standard-library csv.Sniffer. Raises UnreadableFileError when the file
cannot be decoded or parsed, so callers get a consistent, informative error
rather than a raw exception from pandas or the codec layer.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Union

import pandas as pd

# Tried in order; latin-1 never raises UnicodeDecodeError so it acts as fallback.
_ENCODINGS = ["utf-8-sig", "utf-8", "latin-1"]
_DELIMITERS = ",;\t"


class UnreadableFileError(Exception):
    """Raised when a CSV file cannot be decoded or parsed."""


def load_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Load a CSV file into a DataFrame with auto-detected encoding and delimiter.

    Parameters
    ----------
    path:
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    UnreadableFileError
        If the file does not exist, is empty, cannot be decoded with any
        supported encoding, or cannot be parsed as delimited text.
    """
    path = Path(path)

    if not path.exists():
        raise UnreadableFileError(f"File not found: {path}")

    raw = path.read_bytes()
    if not raw.strip():
        raise UnreadableFileError(f"File is empty: {path}")

    text, encoding = _decode(raw, path)
    delimiter = _sniff_delimiter(text)

    try:
        df = pd.read_csv(io.StringIO(text), sep=delimiter, engine="python")
    except Exception as exc:
        raise UnreadableFileError(
            f"Could not parse '{path}' as CSV (encoding={encoding}, delimiter={delimiter!r}): {exc}"
        ) from exc

    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _decode(raw: bytes, path: Path) -> tuple[str, str]:
    """Return (text, encoding) for the first encoding that succeeds.

    Null bytes in the decoded text indicate binary content and are rejected
    immediately, since they cannot appear in valid CSV files.
    """
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "\x00" in text:
            raise UnreadableFileError(
                f"'{path}' appears to be binary (contains null bytes)"
            )
        return text, enc
    # Should never reach here because latin-1 accepts all byte values.
    raise UnreadableFileError(
        f"Cannot decode '{path}' with any supported encoding ({', '.join(_ENCODINGS)})"
    )


def _sniff_delimiter(text: str) -> str:
    """Return the most likely delimiter character, defaulting to comma."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=_DELIMITERS)
        return dialect.delimiter
    except csv.Error:
        return ","
