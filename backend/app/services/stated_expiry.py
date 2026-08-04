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
note``, ``this memory``, ``this reminder``) or an imperative addressed to the
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
_SELF_SUBJECTS = (r"this\s+(?:memory|note|reminder)",)

# The nouns that were here and are gone, because each is *anaphoric* far more
# often than self-referential in the content darkmem exists to store:
#
#   `record`  — "I created a TXT record for domain verification. This record
#               expires on 2026-06-01."
#   `entry`   — a cache entry, a calendar entry, a changelog entry
#   `item`    — an inventory item, a backlog item
#   `fact`    — a fact in the vault, not this note about it
#   `the above` — a pasted key, cert chain or quote, whose validity is the
#               *pasted thing's*, not the memory's: "API key for staging:
#               sk-… The above is valid until 2026-03-31."
#
# Each turned a claim about the world into the memory's own deletion date.
# `memory`, `note` and `reminder` survive because none of them has a competing
# world meaning in this corpus — nobody writes "this note expires" about a
# musical note.

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
    # `(?!\d)` on every date alternation, not just this one: `\b` does not
    # fire between two digits, so without it "2026-12-315" parses as
    # 2026-12-31 and "March 5, 20261" parses as 2026 — a TTL invented from a
    # typo or a longer identifier. The first fix bounded only the ISO branch
    # and left the four year groups open, which is the same defect surviving
    # in four of five places.
    r"(?P<iso>\d{4}-\d{2}-\d{2})(?!\d)"
    rf"|(?:the\s+)?end\s+of\s+(?P<eom_month>{_MONTH_ALTERNATION})\s+(?P<eom_year>\d{{4}})(?!\d)"
    rf"|(?:the\s+)?end\s+of\s+Q(?P<eoq>[1-4])\s+(?P<eoq_year>\d{{4}})(?!\d)"
    rf"|(?P<month>{_MONTH_ALTERNATION})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<year>\d{{4}})(?!\d)"
    rf"|(?P<bare_month>{_MONTH_ALTERNATION})\s+(?P<bare_year>\d{{4}})(?!\d)"
)

_SELF_ALTERNATION = "|".join(_SELF_SUBJECTS)

# The object an imperative must carry. **Mandatory, never optional** — the one
# `?` that used to sit here let pattern 4 degenerate to verb + until + date, so
# "Compliance says raw logs: keep until 2026-12-31, then purge" armed the TTL
# of the note recording the policy. A retention imperative with no object is
# not addressed to this memory; it is a sentence about something else.
_SELF_OBJECT = rf"(?:this(?:\s+(?:memory|note|reminder))?|{_SELF_ALTERNATION})"

# Every pattern anchors on a self-referential subject or an imperative to the
# system carrying a self-referential object. **There is no pattern that matches
# a date alone, and none whose anchor is optional** — a test asserts the second
# half by scanning the compiled patterns, because the failure it prevents is
# one `?` wide and silently deletes memories.
_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "this note is valid until 2026-12-31" / "this memory is good through March 2027"
    re.compile(
        rf"\b(?:{_SELF_ALTERNATION})\s+{_VALIDITY_VERBS}\s+{_UNTIL}\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "this reminder expires on 2026-12-31"
    re.compile(
        rf"\b(?:{_SELF_ALTERNATION})\s+{_EXPIRY_VERBS}\s+(?:on|at|in)?\s*(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "delete this after 2026-12-31" / "discard this memory after March 2027"
    re.compile(
        rf"\b(?:delete|discard|drop|forget|remove|purge)\s+{_SELF_OBJECT}\s+"
        rf"(?:after|on|at|by)\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
    # "remember this until 2026-12-31" / "keep this note until end of Q3 2026"
    re.compile(
        rf"\b(?:remember|keep|retain|hold)\s+{_SELF_OBJECT}\s+{_UNTIL}\s+(?:{_DATE})",
        re.IGNORECASE,
    ),
)

# Quote characters that mark text the memory is *reporting* rather than
# asserting. A retention instruction inside them belongs to whatever was
# quoted — a code comment, a policy document, another agent's message — so
# "config.py has a comment: \"remove this by 2026-06-30\"" is a note *about* a
# TODO, and arming its TTL deletes the documentation of the TODO. Apostrophes
# are deliberately absent: "doesn't" would open a spurious region and suppress
# every real match after it.
_QUOTE_CHARS = '"“”«»`'

# A negation immediately before a retention instruction inverts it, and the
# inverted reading is the dangerous one: "Do not delete this note after
# 2026-12-31" is someone *protecting* a memory, and matching the substring
# turns their protection into the deletion date. The person most likely to
# write it is the person least able to afford the failure.
#
# Scoped to the **current sentence**, not a fixed character count. A 40-char
# window was the first attempt and the finding's own example defeated it: "Do
# not, whatever the compliance team says on Friday about the retention ladder,
# delete this note after 2026-12-31." puts more than 40 characters between the
# negation and the verb, so the literal reported shape still armed. The regex
# already ends in `[^.;!?]*$`, which *is* the same-sentence requirement, so the
# character cap was the only thing losing the negation — the lookback now runs
# to the previous sentence terminator, which does the scoping on its own. The
# pattern carries no `[^.;!?]*$` tail any more: that tail duplicated the
# scoping and re-introduced the same defect one level down, stopping at the dot
# inside "v1.2" or "e.g." and losing the negation in front of it.
_NEGATED = re.compile(
    r"\b(?:do\s+not|don'?t|does\s+not|doesn'?t|did\s+not|didn'?t|never|"
    r"no\s+need\s+to|no\s+circumstances|under\s+no\b|on\s+no\s+account|"
    r"at\s+no\s+point|no\s+one\b|nobody|forbidden|avoid|refrain\s+from|"
    r"rather\s+than|instead\s+of|"
    r"must\s+not|mustn'?t|should\s+not|shouldn'?t|cannot|can'?t|"
    r"will\s+not|won'?t)\b",
    re.IGNORECASE,
)
# **Scope: the whole preceding text, not the sentence.** Five review rounds
# established that sentence-splitting cannot be made reliable enough to carry a
# delete decision. Each round fixed its exhibits and the mechanism armed one
# shape over: `v1.2`, then `e.g.`, then an ellipsis, then a mid-sentence bang,
# then any dotted proper noun off a closed list — `Do not, per Acme Corp.
# Policy, delete this note after 2026-12-31.` The reason no sixth heuristic
# ends it was named in review: "a terminator preceded by a multi-letter word"
# describes every *real* sentence end too, so nothing separates `Corp. Policy`
# from `plan. Delete`, and a closed abbreviation list can never enumerate
# proper nouns.
#
# So the ambiguity is resolved the way this module already resolves it for
# quotes: **toward suppression.** A negation anywhere earlier in the memory
# suppresses every match after it. That is this module's own stated doctrine —
# over-suppressing costs a missed TTL and the memory lives on, under-suppressing
# deletes it — finally applied to the one place still trying to be clever.
#
# **The scan covers the whole memory, not just the text before the match.**
# Scanning only the prefix left the doctrine applied in one direction: "Delete
# this note after 2026-12-31. Actually, don't — we still need it." armed and
# deleted. A retraction is a negation like any other, and "any negation
# anywhere suppresses" has to mean anywhere.
#
# The token list is open by construction and always will be — English lexical
# negation cannot be enumerated by an alternation, which is a consequence of
# the deterministic-parser constraint rather than of any one edit. The register
# is broadened here to the forms review actually found arming ("on no account",
# "at no point", "nobody", "forbidden", "avoid", "refrain from"); the honest
# statement is that a form outside it arms, and that no further round of
# enumeration would change that.
#
# The measured cost, over the extraction gold, its held-out set, and the
# benchlib retrieval and smoke corpora (133 memories): **3.8% carry any
# negation token at all**, and every one that fired was incidental ("never use
# a bare except", "cannot reach the VPN range"). A bounded ~4% recall cost
# against an unbounded false-positive surface is the cheap direction.
#
# The cost is real and stated: a memory carrying a negation *and* a later,
# unrelated genuine instruction now derives nothing. "Never mind the old plan.
# Delete this note after 2026-12-31." is exactly that case and used to be pinned
# as a recall test. The memory keeps living and any caller can still set the TTL
# by hand — the trade this module exists to make.

_QUARTER_END_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}


def _end_of_day(year: int, month: int, day: int) -> datetime | None:
    """The instant a stated day stops covering the memory.

    End-exclusive: "valid until 2026-12-31" means good *through* the 31st, so
    the memory expires when the 31st ends, not when it begins. A sweep using
    the day's own midnight would delete it a day early — for a one-day TTL,
    immediately.
    """
    try:
        # The addition is inside the try, not after it. `datetime(9999, 12, 31)`
        # constructs fine and only the +1 day overflows, so an `OverflowError`
        # escaping here reached savepoint A and took the vector upsert down with
        # it — losing every enrichment for that memory, misattributing the cause
        # as "Vector write failed", and failing identically on every retry
        # because it is deterministic. "Valid until 9999-12-31" is the ordinary
        # never-expires idiom, so the memory asking to be kept forever was the
        # one being made permanently unsearchable.
        return datetime(year, month, day, tzinfo=timezone.utc) + timedelta(days=1)
    except (ValueError, OverflowError):
        return None


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


def _quoted_spans(content: str) -> list[tuple[int, int]]:
    """Half-open ``[start, end)`` spans of quoted or fenced text.

    **An odd number of quotes is ambiguous, and the ambiguity is resolved
    toward suppression.** Strict first-to-next pairing is phase-fragile: one
    stray quote shifts every later pair, and an inch mark is ordinary in this
    system's infrastructure notes. `Mounted the 19" switch. The runbook says
    "keep this note until 2026-09-30" but ignore it.` paired the inch mark with
    the opening quote, left the real one unclosed, and un-quoted a reported
    instruction the quote guard exists to suppress — re-opening the data-loss
    path. So when a quote character appears an odd number of times, both
    phasings are computed and their spans unioned: a match suppressed under
    *either* reading is suppressed.

    That direction is deliberate. Over-suppressing costs a missed TTL and the
    memory simply lives on; under-suppressing deletes it.
    """
    spans: list[tuple[int, int]] = []
    # Only the symmetric quotes phase-guess. The directional pairs are handled
    # below, and including them here paired “ with “ and ” with ”, so two
    # balanced smart-quoted regions produced a span covering the *unquoted*
    # middle and swallowed a genuine instruction between them.
    for quote in ('"', "`"):
        positions = [i for i, char in enumerate(content) if char == quote]
        if len(positions) < 2:
            continue

        # An inch or foot mark is digit-preceded, and it is disqualified as an
        # **opener only** — never as a closer. `Rack has 19" rails.` was
        # consuming the real opening quote and un-quoting the reported
        # instruction after it, and a *pair* of stray marks preserves parity so
        # the odd-count union below could not see it either. Disqualifying it
        # as a closer as well is the mistake this comment exists to prevent: a
        # quoted string that *ends* in a date ("… by 2026-06-30") has a
        # perfectly ordinary digit-preceded closing quote, and dropping it
        # un-quotes the whole region.
        opener: int | None = None
        skipped = False
        for index in positions:
            if opener is None:
                if index and content[index - 1].isdigit():
                    skipped = True
                    continue
                opener = index
            else:
                spans.append((opener, index + 1))
                opener = None

        # **A skip is itself an ambiguity, and forgetting that was a bug.**
        # Ambiguity used to be detected as "odd raw count"; narrowing it to
        # "leftover opener" while *adding* a new ambiguity source nobody
        # counted let a whole quoted tail go bare. In `The runbook says "the
        # 42" rack: keep this note until 2026-09-30" but ignore it.` the real
        # opener pairs with the interior inch mark, and the real closer — which
        # is digit-preceded, because the quoted text ends in a date — is then
        # skipped as an opener candidate, leaving the instruction unquoted.
        #
        # So either a leftover opener or any skip marks the pairing ambiguous,
        # and both naive phasings are unioned in. A match suppressed under
        # *any* reading is suppressed: over-suppressing costs a missed TTL and
        # the memory lives on, under-suppressing deletes it.
        if opener is not None or skipped:
            for phase in (positions, positions[1:]):
                for first, second in zip(phase[::2], phase[1::2]):
                    spans.append((first, second + 1))

    # Smart-quote and guillemet pairs are directional, so they pair across
    # different characters and need no phase guessing.
    for open_char, close_char in (("“", "”"), ("«", "»")):
        opens = [i for i, char in enumerate(content) if char == open_char]
        closes = [i for i, char in enumerate(content) if char == close_char]
        for opener, closer in zip(opens, closes):
            if closer > opener:
                spans.append((opener, closer + 1))
    return spans


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

    quoted = _quoted_spans(content)
    found: list[datetime] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(content):
            # A match inside quoted text is the memory reporting someone else's
            # instruction, not issuing its own.
            if any(start <= match.start() < end for start, end in quoted):
                continue
            # A negated instruction means the opposite of what it matches, and
            # **any** negation anywhere in the memory suppresses. See `_NEGATED`
            # for why the scope is the whole text rather than the sentence.
            if _NEGATED.search(content):
                continue
            instant = _instant_from(match)
            # Strictly future: a derived expiry already spent would let capture
            # arm a sweep that deletes the memory it just wrote.
            if instant is not None and instant > reference_time:
                found.append(instant)
    return min(found) if found else None


__all__ = ["derive_stated_expiry"]
