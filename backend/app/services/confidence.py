"""Rule-based confidence estimator for memory rows (v1 placeholder).

This is a deliberate placeholder. The goal of the column is to let retrieval
rank fusion dampen or boost a candidate; if the signal proves valuable, the
rule will be replaced by an ML classifier. If not, rank-fusion `gamma` can
stay at zero so the column is benign.

Markers are matched at word boundaries so "might" does not fire inside
"mighty" and "proven" does not fire inside "approvent". Multi-word phrases
like "not sure" continue to work — `\b` anchors the first and last tokens
of each phrase.

Known limitation: "I think X is definitely correct" trips both markers and
falls through to the default. Acceptable for v1.
"""
from __future__ import annotations

import re


HIGH_CONFIDENCE_MARKERS: frozenset[str] = frozenset({
    "definitely",
    "confirmed",
    "always",
    "verified",
    "proven",
})

LOW_CONFIDENCE_MARKERS: frozenset[str] = frozenset({
    "maybe",
    "perhaps",
    "not sure",
    "probably",
    "might",
    "would consider",
})

CONFIDENCE_DEFAULT: float = 0.75
CONFIDENCE_HIGH: float = 0.9
CONFIDENCE_LOW: float = 0.5
CONFIDENCE_AUTH_TYPES: float = 0.85

_AUTHORITATIVE_TYPES: frozenset[str] = frozenset({"fact", "decision", "reference"})


def _compile_marker_pattern(markers: frozenset[str]) -> re.Pattern[str]:
    # Longer phrases first so "not sure" wins over "sure" if the two ever
    # overlap in the alternation.
    parts = sorted((re.escape(m) for m in markers), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b", re.IGNORECASE)


_HIGH_RE = _compile_marker_pattern(HIGH_CONFIDENCE_MARKERS)
_LOW_RE = _compile_marker_pattern(LOW_CONFIDENCE_MARKERS)


def estimate_confidence(text: str | None, memory_type: str | None) -> float:
    """Score a memory's rough confidence in the [0.5, 0.9] band.

    Callers should treat the return value as ordinal, not calibrated.
    """
    if not text:
        return CONFIDENCE_DEFAULT
    low = bool(_LOW_RE.search(text))
    high = bool(_HIGH_RE.search(text))
    if low and not high:
        return CONFIDENCE_LOW
    if high and not low:
        return CONFIDENCE_HIGH
    if memory_type in _AUTHORITATIVE_TYPES:
        return CONFIDENCE_AUTH_TYPES
    return CONFIDENCE_DEFAULT
