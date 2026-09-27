"""Log-shaped content at the memory door: named signals, no model, no database.

A capture is flagged when two or more content signals match, or when it is
longer than LENGTH_LIMIT alone. A flag never refuses a capture; the doors
answer it as a warning and journal `capture_flagged` with the signal names.

The patterns and both thresholds were calibrated on 2026-09-27 against the
2026-09-23 migration lineage (user data, kept outside the repository): they
flag 81.0% of the 785 original memories and 0.16% of the 6,234 cleaned
pieces. Change one only with a new measurement over the same lineage.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

LENGTH_LIMIT = 1500
MIN_SIGNALS = 2

_PATTERNS: dict[str, re.Pattern[str]] = {
    # A hex token with at least one letter and one digit, not a fragment of a
    # longer word or of a UUID (whose segments sit between hyphens); or a
    # `<sha>..<sha>` range.
    "commit_ref": re.compile(
        r"(?<![0-9A-Za-z-])(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,40}(?![0-9A-Za-z-])"
        r"|\b[0-9a-f]{7,40}\.\.\.?[0-9a-f]{7,40}\b"
    ),
    "tally": re.compile(
        r"\b\d+ (?:passed|failed)\b|\b\d+/\d+\b|\b\d+ commits?\b|\b\d+ of \d+ tasks\b",
        re.IGNORECASE,
    ),
    "progress": re.compile(
        r"\b(?:task|phase|wave) \d+\b[^.\n]{0,40}?\b(?:complete|completed|done|started)\b"
        r"|\ball green\b",
        re.IGNORECASE,
    ),
    "vcs_event": re.compile(
        r"\b(?:merged|pushed|fast-forwarded|fast forwarded)\b"
        r"|\bbranch (?:was )?deleted\b|\bdeleted (?:the )?branch\b",
        re.IGNORECASE,
    ),
    "file_line": re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,6}:\d+\b"),
    "trace": re.compile(r"^Traceback|\bat [\w.$]+\.[\w$<>]+\(|\b\w*Exception:", re.MULTILINE),
    "narration": re.compile(r"(?i:\bthis session\b|\bnext steps\b)|\bTODO\b"),
}

SIGNAL_NAMES: tuple[str, ...] = (*_PATTERNS, "length")


def signals(content: str) -> list[str]:
    """Every signal the content matches, in SIGNAL_NAMES order."""
    found = [name for name, pattern in _PATTERNS.items() if pattern.search(content)]
    if len(content) > LENGTH_LIMIT:
        found.append("length")
    return found


def is_flagged(found: Sequence[str]) -> bool:
    """Two or more content signals, or the length signal on its own."""
    return "length" in found or len(found) >= MIN_SIGNALS


def warning(found: Sequence[str]) -> str:
    """The answer's warning for a flagged capture."""
    return (
        f"This capture looks like working data ({', '.join(found)}). It was stored, "
        "but a memory should hold one durable fact: send checkpoints, progress and "
        "logs to worklog_append and long write-ups to document_put."
    )


def lint(content: str) -> tuple[list[str], list[str]]:
    """The content's signals and the warnings a capture door answers for it.

    Warnings are empty when the capture is not flagged; the signals are
    returned either way.
    """
    found = signals(content)
    return found, [warning(found)] if is_flagged(found) else []
