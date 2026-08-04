"""Deterministic stated-expiry detection for capture (doc 08 §2.3, T2.34).

A memory may state its own retention — "this note is valid until 2026-12-31" —
and doc 08 §2.3 activates `memories.expires_at` from it so a dated memory
self-expires without the caller setting a TTL. This module is that derivation.

**It is deliberate that this is a parser and not an LLM field.** Adding an
expiry to the extraction schema changes the system prompt, and the F1 bench
cache is keyed on ``sha256(content + system_prompt)`` — so it would invalidate
every cached entry, red the merge gate until a live re-warm, and force a
re-recorded F1 baseline. Nothing here adds an entity or a relation, so the
bench's entity/relation F1 is untouched and the cache stays valid.

**Why the patterns are narrow, and why that is the correct direction.**
``expired_memory_cleanup`` **deletes** the row: embeddings cascade, provenance
is withdrawn, and nothing brings it back. So a false positive here is silent,
irreversible data loss, and the tempting failure is one word wide — "the
licence is valid until 2026-12-31" is a claim *about a licence*, not an
instruction to forget the note on that date. A regex cannot tell those apart by
date proximity, so it does not try: it matches only a memory addressing **its
own** lifetime, through a closed set of self-referential subjects (``this
note``, ``this memory``, ``this entry``, ...) or an imperative addressed to the
system (``delete this after ...``, ``remember until ...``).

The asymmetry is the whole design. A missed expiry leaves a memory alive one
sweep longer and any caller can still set a TTL by hand; a false positive
destroys knowledge on a timer nobody set. Recall is the cheap side to lose.

**Two further refusals**, both structural rather than advisory:

- **Never past.** A derived instant at or before ``reference_time`` is refused.
  Otherwise capture could arm a sweep that deletes the memory it just wrote,
  which turns a typo into data loss between two job ticks.
- **Never a downgrade.** The caller's own ``expires_at`` always wins; this
  derivation only fills a NULL. An explicit TTL is an instruction, and a parser
  overriding an instruction is the same defect in the other direction.

Everything is UTC and end-exclusive at day granularity: "valid until
2026-12-31" means the memory is good *through* that day, so the instant
returned is the end of it (2027-01-01T00:00Z), not its midnight start.
"""

from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta, timezone

# The subjects a memory can use to mean *itself*. Closed on purpose: widening
# it is the one edit that can turn a claim about the world into this memory's
# own death date, so a new member belongs in review with a test beside it.
#
# A bare pronoun is exactly that edit and was caught here once: `it` shipped in
# this tuple briefly, and "The TLS cert expires soon. It is valid until
# 2026-12-31." then resolved to the *memory's* TTL and would have deleted the
# note recording the cert. A pronoun's referent is the previous clause, never
# the memory, so no pronoun belongs here — only a noun phrase that names the
# memory itself.
_SELF_SUBJECTS = (
    r"this\s+(?:memory|note|entry|record|reminder|item|fact)",
    r"the\s+above",
)

# "valid until X", "good through X", "applies until X".
_VALIDITY_VERBS = r"(?:is\s+|remains\s+|stays\s+)?(?:valid|good|current|accurate|applicable)"
_UNTIL = r"(?:until|through|thru|till|up\s+to)"

# "expires on X", "expires X".
_EXPIRY_VERBS = r"(?:expires?|expiry|expiration)"

_MONTHS = {name.lower(): index for index, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): index for index, name in enumerate(calendar.month_abbr) if name})
_MONTH_ALTERNATION = "|".join(sorted(_MONTHS, key=len, reverse=True))

# The three date shapes, each unambiguous on its own. Deliberately no bare
# "Q3", no "next spring", no "in six months": a quarter with no year has to
# guess which year is meant, and a guess here deletes a memory.
_DATE = (
    r"(?P<iso>\d{4}-\d{2}-\d{2})"
    rf"|(?:the\s+)?end\s+of\s+(?P<eom_month>{_MONTH_ALTERNATION})\s+(?P<eom_year>\d{{4}})"
    rf"|(?:the\s+)?end\s+of\s+Q(?P<eoq>[1-4])\s+(?P<eoq_year>\d{{4}})"
    rf"|(?P<month>{_MONTH_ALTERNATION})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<year>\d{{4}})"
    rf"|(?P<bare_month>{_MONTH_ALTERNATION})\s+(?P<bare_year>\d{{4}})"
)

_SELF_ALTERNATION = "|".join(_SELF_SUBJECTS)

# Every pattern anchors on a self-referential subject or an imperative to the
# system. There is no pattern that matches a date alone.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "this note is valid until 2026-12-31" / "this memory is good through March 2027"
    re.compile(
        rf"\b(?:{_SELF_ALTERNATION})\s+{_VALIDITY_VERBS}\s+{_UNTIL}\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "this entry expires on 2026-12-31"
    re.compile(
        rf"\b(?:{_SELF_ALTERNATION})\s+{_EXPIRY_VERBS}\s+(?:on|at|in)?\s*(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "delete this after 2026-12-31" / "discard this memory after March 2027"
    re.compile(
        rf"\b(?:delete|discard|drop|forget|remove|purge)\s+(?:this|the\s+above)"
        rf"(?:\s+(?:memory|note|entry|record|reminder|item|fact))?\s+"
        rf"(?:after|on|at|by)\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "remember this until 2026-12-31" / "keep until end of Q3 2026"
    re.compile(
        rf"\b(?:remember|keep|retain|hold)\s+(?:this|the\s+above)?"
        rf"(?:\s+(?:memory|note|entry|record|reminder|item|fact))?\s*"
        rf"{_UNTIL}\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
)

_QUARTER_END_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}


def _end_of_day(year: int, month: int, day: int) -> datetime | None:
    """The instant a stated day stops covering the memory.

    End-exclusive: "valid until 2026-12-31" means good *through* the 31st, so
    the memory expires when the 31st ends, not when it begins. A sweep using
    the day's own midnight would delete it a day early — for a one-day TTL,
    immediately.
    """
    try:
        start = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None
    return start + timedelta(days=1)


def _end_of_month(year: int, month: int) -> datetime | None:
    try:
        last = calendar.monthrange(year, month)[1]
    except (ValueError, calendar.IllegalMonthError):
        return None
    return _end_of_day(year, month, last)


def _instant_from(match: re.Match[str]) -> datetime | None:
    groups = match.groupdict()

    if groups.get("iso"):
        try:
            year, month, day = (int(part) for part in groups["iso"].split("-"))
        except ValueError:  # pragma: no cover - the regex fixes the shape
            return None
        return _end_of_day(year, month, day)

    if groups.get("eom_month"):
        month = _MONTHS.get(groups["eom_month"].lower())
        return _end_of_month(int(groups["eom_year"]), month) if month else None

    if groups.get("eoq"):
        month = _QUARTER_END_MONTH[int(groups["eoq"])]
        return _end_of_month(int(groups["eoq_year"]), month)

    if groups.get("month"):
        month = _MONTHS.get(groups["month"].lower())
        return _end_of_day(int(groups["year"]), month, int(groups["day"])) if month else None

    if groups.get("bare_month"):
        # A month with no day means the whole month, so it expires when the
        # month does. Reading it as the 1st would cut a stated month short by
        # its whole length.
        month = _MONTHS.get(groups["bare_month"].lower())
        return _end_of_month(int(groups["bare_year"]), month) if month else None

    return None  # pragma: no cover - every alternation sets one group


def derive_stated_expiry(content: str, *, reference_time: datetime) -> datetime | None:
    """The memory's own stated expiry, or ``None``.

    ``reference_time`` is the memory's ``created_at`` — the same anchor the
    extraction module's date rescue uses. It is not used to *resolve* a date
    (every pattern demands an explicit year, precisely so nothing is guessed);
    it is the floor a derived instant must clear.

    When a memory states more than one expiry, the **earliest** future one
    wins. Retention is a promise about when the memory stops being kept, so two
    stated dates are two promises and only the tighter one can be honoured.
    """
    if not content or not isinstance(content, str):
        return None
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    found: list[datetime] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(content):
            instant = _instant_from(match)
            # Strictly future: a derived expiry already spent would let capture
            # arm a sweep that deletes the memory it just wrote.
            if instant is not None and instant > reference_time:
                found.append(instant)
    return min(found) if found else None


__all__ = ["derive_stated_expiry"]
