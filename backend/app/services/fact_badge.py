"""Doc 12's ``badge`` object — the one producer of the honest claim string.

Doc 12 §4 fixes the field and the sentence; doc 13 §5.3 restates the sentence
verbatim and forbids any screen from paraphrasing it. Until this module there
was **no producer**: the canonical sentence existed only inside
``verification_ladder.compute_confidence``'s docstring, so "render the badge
verbatim from the backend" named a string nothing emitted. Everything a
consumer shows comes from here, and no consumer recomputes any part of it
(invariant 15 — this module reads the rows the ladder wrote and journalled,
and adjudicates nothing).

**The three forms doc 12 fixes**, and the two degradations it does not.

1. Plain — ``asserted by K distinct origins of kinds [X, Y], no known
   contradiction, as of T``.
2. ``disputed`` swaps in a two-sided form — ``disputed: 2 origins assert X,
   1 origin asserts not-X, as of T`` — never a picked winner. Both sides are
   rendered in the *same* shape, the subject/rel/object triple, for the reason
   ``layer_composition.dispute_label`` renders them that way: flattening one
   side while structuring the other picks a winner in the layout. ``not-X`` is
   a placeholder for the competing claim, not a literal negation of the
   fact's own text — the counterpart asserts its own triple, and rendering
   ``not-<subject> <rel> <object>`` would be a claim nothing made.
3. ``confirmed`` gains a trailing ``, human-ratified``.

**Degradation 1 — no verification transition to be "as of".** Doc 12 defines
``as_of`` as *when verification was last recomputed (the events transition)*,
so it is read from the latest ``verified`` event and from nowhere else. A fact
with no such row is one the recompute has never reached, or one it reached and
held: an ordinary hold journals nothing, so a ``candidate`` that stays a
candidate never gets a row. No timestamp on the fact row means what ``as_of``
means. ``updated_at``, ``created_at`` and ``reference_time`` are all *nearby*
and all answer a different question, so substituting one would put a
plausible-looking lie in the product's most repeated honesty surface. The badge
carries ``as_of: None`` either way.

The claim's tail tells the two apart from the recompute's own progress, read
as data. The job's state row (``config`` key ``verification_recompute_state``)
holds its drain watermark: the ``(created_at, id)`` of the last
``sources_changed`` event it drained, saved in the same transaction as the
rungs it recomputed. When that watermark has reached the fact's latest
``sources_changed`` event, every recorded change to the fact's evidence has
been drained and the tail reads ``checked as of`` the watermark's day — a day
at or after that change, by which the rung accounts for all of it. An old
watermark under-claims; it never dates a check later than the drain got.
Otherwise the tail is ``verification not yet recomputed``. Cold start reaches
that on every fact, which is exactly why it is a stated form rather than an
exception.

"Checked" means the drain reached the fact's evidence, not that the fact's
own recompute succeeded: a per-fact failure advances the watermark too (one
poisonous fact must not stall the queue), and the job's slow arm re-reaches
it. The state is read through SQL and nothing of the job is imported, because
a read path reaching a dream-job module breaches invariant 15.

**Degradation 2 — a dispute whose counterpart was never journalled.** The
two-sided form needs the other side, and the only thing that ever knows it is
the veto's finding, carried on the ``verified`` payload's ``contradiction``
block (T2.64) and read here through the one reader,
``verified_evidence.latest_verified_evidence``. That block is **absent** on a
recovery, on a caller-overridden verdict, and on any dispute predating it, and
those three are not distinguishable from the journal. Re-deriving it is
forbidden by construction: the deterministic scan's sole legitimate caller is
the ladder's applier, enforced tree-wide, and a read path owning a second scan
would breach invariant 15. So the claim says the contradicting claim was not
recorded. It never falls back to the plain one-sided form, because "no known
contradiction" on a fact we know is disputed is the one sentence this module
exists to make unwritable.

**Zero origins is a sentence, not a special case.** ``asserted by 0 distinct
origins of kinds []`` renders, and is pinned by a vector like every other form.
The state is reachable in production rather than only in a fixture: the
withdrawal sweep deletes a fact's provenance rows before expiring the fact they
orphan, so a fact with no sources at all exists between those two writes. The
sentence is also the honest one — it says nothing currently asserts this, which
is exactly what a reader of a row whose evidence has just been withdrawn most
needs to know. Suppressing the badge or refusing to build one would hide that,
and refusing would put a read-path failure on a legitimate transient state.

**The forbidden words are guarded on the badge's own vocabulary, not on the
data.** The rule is that the *badge* never says "true" or "verified"; a fact
whose object is literally the word ``verified`` is the badge quoting evidence,
not claiming certainty, and refusing to serve that row would be a read-path
failure invented by a lint. ``_render`` therefore strips the interpolated
values out of the rendered sentence and guards the residue — the module's own
words — so a template that acquires a certainty word fails, and no user string
can. The fixed vocabulary is guarded again at import, so the failure is a
build failure and not a per-row one.

**Number agreement.** Doc 12's templates carry ``K distinct origins`` and, in
the ``disputed`` form, both ``2 origins assert`` and ``1 origin asserts`` — the
doc pluralises its own verb, so the singular of the noun is the doc's
convention rather than a liberty taken here. One origin reads ``1 distinct
origin``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository, OriginProfile
from app.services.claim_gates import ClaimGate, served_status
from app.services.verified_evidence import (
    CONTRADICTION_EVIDENCE_KEY,
    latest_verified_evidence,
)

DISPUTED = "disputed"
CONFIRMED = "confirmed"

HUMAN_SOURCE_KIND = "human"

# The mechanical predicate behind doc 07 §5's cold-start label (T2.56). A row
# is "unverified" exactly when it has not reached one of the two rungs a human
# or multiple distinct origins actually backed; every candidate and disputed
# fact is unverified, and so is every L0 row by construction — a memory
# carries no verification status at all, never having been put on the ladder.
# This reads the tier the ladder already wrote rather than adjudicating one:
# it is a plain restatement of ``TIER_BY_VERIFICATION_STATUS``'s top two
# rungs, not a second opinion about where a row sits on it.
VERIFIED_TIER_STATUSES = frozenset({"corroborated", CONFIRMED})

# doc 12 §4: the badge is present on L2/L3 rows and null on L0. The id_kind
# vocabulary is doc 12's own (`memory | fact | article`).
BADGE_BEARING_ID_KINDS = frozenset({"fact", "article"})
LIFECYCLE_ID_KINDS = frozenset({"memory"})

# Word boundaries rather than substrings: a longer word that merely contains
# one of these — `construe`, or the noun form of the second — is not the badge
# claiming certainty.
_CERTAINTY_WORDS = re.compile(r"\b(?:true|verified)\b", re.IGNORECASE)

# Every fixed fragment the sentences below are built from, named once so the
# import-time guard and the templates cannot drift apart.
_ASSERTED_BY = "asserted by"
_DISTINCT_ORIGIN = "distinct origin"
_DISTINCT_ORIGINS = "distinct origins"
_OF_KINDS = "of kinds"
_NO_CONTRADICTION = "no known contradiction"
_DISPUTED_PREFIX = "disputed:"
_ORIGIN_ASSERTS = "origin asserts"
_ORIGINS_ASSERT = "origins assert"
_AS_OF = "as of"
_CHECKED_AS_OF = "checked as of"
_NOT_RECOMPUTED = "verification not yet recomputed"
_HUMAN_RATIFIED = "human-ratified"
_COUNTERPART_UNRECORDED = "the contradicting claim was not recorded"
# The L3 claim's own words (doc 12 §4, article semantics ruled 2026-08-12).
# An article's provenance is its cited facts — never an origin count rolled up
# from them, which would assert corroboration strength for prose nobody
# corroborated — and its own measurement is claim-support coverage.
_GROUNDED_BY = "grounded by"
_CITED_FACT = "cited fact"
_CITED_FACTS = "cited facts"
_COVERAGE = "claim-support coverage"
_COVERAGE_UNMEASURED = "claim-support coverage not measured"

CLAIM_VOCABULARY: tuple[str, ...] = (
    _ASSERTED_BY,
    _DISTINCT_ORIGIN,
    _DISTINCT_ORIGINS,
    _OF_KINDS,
    _NO_CONTRADICTION,
    _DISPUTED_PREFIX,
    _ORIGIN_ASSERTS,
    _ORIGINS_ASSERT,
    _AS_OF,
    _CHECKED_AS_OF,
    _NOT_RECOMPUTED,
    _HUMAN_RATIFIED,
    _COUNTERPART_UNRECORDED,
)

# **The L3 fragments are deliberately not registered above**, and the reason is
# what registration *does*: two second-producer scans — one over `app/`, one
# over the frontend — forbid any module outside this one from spelling a
# registered fragment, so registering a phrase reserves it across the whole
# tree. That is right for the L2 sentence, whose wording exists only to be
# rendered verbatim. It is wrong for these:
#
# * "claim-support coverage" is what doc 13 §5.2 *requires* the surface to call
#   the number ("the surface labels it claim-support coverage, not a vague
#   score"), so reserving it would outlaw the label the design mandates.
# * "grounded by" and "cited facts" are ordinary domain English that the UI and
#   this codebase's own prose already use about citations.
#
# Nothing is lost by leaving them out. The L3 sentence is assembled in exactly
# one place — :func:`build_article_claim` — and that function renders through
# `_render`, so the certainty-word guard still runs over the whole sentence.
# What the scan protects is that no *second* module composes a claim; the L2
# fragments still carry that, and a module that assembled an L3 claim would
# have to reimplement this function to do it.


class CertaintyWordError(ValueError):
    """A claim string said "true" or "verified" in the badge's own voice."""


def assert_no_certainty_words(text: str) -> str:
    """Refuse a sentence that claims certainty (doc 12 §4, invariant 14)."""
    found = _CERTAINTY_WORDS.search(text)
    if found is not None:
        raise CertaintyWordError(
            f"the badge claim may never contain the word {found.group(0)!r}; "
            f"the machine's ceiling is corroboration, and the sentence "
            f"under-claims by contract: {text!r}"
        )
    return text


for _fragment in CLAIM_VOCABULARY:
    assert_no_certainty_words(_fragment)
del _fragment


@dataclass(frozen=True)
class Badge:
    """Doc 12 §4's badge object, field for field."""

    verification_status: str | None
    origin_count: int
    origin_kinds: tuple[str, ...]
    as_of: datetime | None
    contradiction: bool
    human_ratified: bool
    stale: bool
    claim: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "verification_status": self.verification_status,
            "origin_count": self.origin_count,
            "origin_kinds": list(self.origin_kinds),
            "as_of": self.as_of,
            "contradiction": self.contradiction,
            "human_ratified": self.human_ratified,
            "stale": self.stale,
            "claim": self.claim,
        }


def _render(sentence: str, data: Iterable[str | None]) -> str:
    """Guard the badge's own words, having removed the interpolated values."""
    residue = sentence
    for value in data:
        if value:
            residue = residue.replace(value, " ")
    assert_no_certainty_words(residue)
    return sentence


def _as_of_date(as_of: datetime | None) -> str | None:
    """The calendar day the claim names, in UTC.

    Normalised before the date is taken: ``events.created_at`` is a
    ``timestamptz``, and a connection returning it at another offset would
    otherwise move the claimed day by one.
    """
    if as_of is None:
        return None
    moment = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).date().isoformat()


def _tail(as_of: datetime | None, checked_as_of: datetime | None = None) -> str:
    day = _as_of_date(as_of)
    if day is not None:
        return f", {_AS_OF} {day}"
    checked = _as_of_date(checked_as_of)
    if checked is not None:
        return f", {_CHECKED_AS_OF} {checked}"
    return f", {_NOT_RECOMPUTED}"


def _triple_text(subject: Any, rel_type: Any, obj: Any) -> str | None:
    parts = [str(part).strip() for part in (subject, rel_type, obj) if part is not None]
    if len(parts) != 3 or not all(parts):
        return None
    return " ".join(parts)


def _origins_phrase(count: int, *, singular: str, plural: str) -> str:
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def build_claim(
    *,
    verification_status: str | None,
    origin_count: int,
    origin_kinds: Sequence[str],
    as_of: datetime | None,
    claim_text: str | None = None,
    counterpart_text: str | None = None,
    counterpart_origin_count: int | None = None,
    checked_as_of: datetime | None = None,
) -> str:
    """The exact sentence doc 12 fixes, in whichever of its forms applies.

    ``checked_as_of`` is consulted only when there is no transition to be
    "as of" (Degradation 1): a journalled transition always names its own day.
    """
    tail = _tail(as_of, checked_as_of)

    if verification_status == DISPUTED:
        mine = _origins_phrase(
            origin_count, singular=_ORIGIN_ASSERTS, plural=_ORIGINS_ASSERT
        )
        if claim_text is None:
            raise ValueError(
                "a disputed badge needs the fact's own triple; the two-sided "
                "form has no one-sided fallback"
            )
        if counterpart_text is None or counterpart_origin_count is None:
            sentence = (
                f"{_DISPUTED_PREFIX} {mine} {claim_text}, "
                f"{_COUNTERPART_UNRECORDED}{tail}"
            )
            return _render(sentence, (claim_text,))
        theirs = _origins_phrase(
            counterpart_origin_count, singular=_ORIGIN_ASSERTS, plural=_ORIGINS_ASSERT
        )
        sentence = (
            f"{_DISPUTED_PREFIX} {mine} {claim_text}, {theirs} {counterpart_text}{tail}"
        )
        return _render(sentence, (claim_text, counterpart_text))

    noun = _DISTINCT_ORIGIN if origin_count == 1 else _DISTINCT_ORIGINS
    kinds = ", ".join(origin_kinds)
    sentence = (
        f"{_ASSERTED_BY} {origin_count} {noun} {_OF_KINDS} [{kinds}], "
        f"{_NO_CONTRADICTION}{tail}"
    )
    if verification_status == CONFIRMED:
        sentence = f"{sentence}, {_HUMAN_RATIFIED}"
    return _render(sentence, origin_kinds)


def build_article_claim(
    *,
    cited_facts: int,
    coverage: float | None,
    as_of: datetime | None,
) -> str:
    """The L3 sentence, in the shape doc 12 fixes for L2 and the semantics
    ruled for L3 on 2026-08-12.

    Two things it deliberately does not say. It never rolls its cited facts'
    origins into an origin count: an article is prose *about* corroborated
    facts, and borrowing their corroboration strength would assert that
    something adjudicated the article itself. And an unmeasured coverage is
    said as unmeasured rather than omitted — while the groundedness judge is
    unqualified that is every article, and a sentence that simply left the
    number out would read as though grounding were not the point.
    """
    noun = _CITED_FACT if cited_facts == 1 else _CITED_FACTS
    measured = (
        _COVERAGE_UNMEASURED if coverage is None else f"{_COVERAGE} {coverage:.2f}"
    )
    sentence = f"{_GROUNDED_BY} {cited_facts} {noun}, {measured}{_tail(as_of)}"
    return _render(sentence, ())


def counterpart_claim(block: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    """``(counterpart_id, counterpart triple text)`` from the journal block.

    ``(None, None)`` whenever the block is missing or does not carry a whole
    triple. The three causes of a missing block are indistinguishable from the
    journal (see ``verified_evidence``), so this reports absence and never
    guesses which one it is.

    An id that is blank or whitespace reports as absent rather than as a
    lookup key. ``events`` is append-only, so a malformed historical row
    cannot be pruned once written and every reader has to survive one
    forever; the id it yields is either ``None`` or usable, never something
    in between that one caller filters and the next dereferences.
    """
    if not isinstance(block, Mapping):
        return None, None
    text = _triple_text(
        block.get("counterpart_subject"),
        block.get("counterpart_rel_type"),
        block.get("counterpart_object"),
    )
    raw_id = block.get("counterpart_id")
    counterpart_id = str(raw_id).strip() if raw_id is not None else ""
    return (counterpart_id or None), text


def _names_a_counterpart(counterpart_id: str | None, counterpart_text: str | None) -> bool:
    """The one predicate deciding whether the two-sided form has both sides.

    Spelled once and called from both the id-gathering pass and the per-row
    build. Two spellings of "we have a counterpart" is how the gathering pass
    skips a key the build then looks up.
    """
    return bool(counterpart_id) and bool(counterpart_text)


def build_badge(
    *,
    verification_status: str | None,
    profile: OriginProfile,
    as_of: datetime | None,
    subject_name: Any,
    rel_type: Any,
    object_name: Any,
    counterpart_text: str | None = None,
    counterpart_origin_count: int | None = None,
    stale: bool = False,
    checked_as_of: datetime | None = None,
) -> Badge:
    """One row's badge.

    ``origin_count`` and ``origin_kinds`` are read off the profile
    ``fact_sources`` produces and are never counted here: that module owns
    ``COUNT(DISTINCT origin_key)`` and opens by saying "never rows", so a
    second count beside it is how the two acquire different answers.

    ``human_ratified`` is doc 12's stated definition — a ``human``-kind source
    exists — widened so ``confirmed`` can never report ``False``, since doc 12
    also makes that rung set the flag. The two coincide in practice because
    ``confirmed`` is only reachable through a human ratification that writes
    such a source; the widening is what keeps the field honest if they ever
    do not. The trailing ``, human-ratified`` on the sentence rides the rung,
    not the flag: a human source on a fact the ladder has not promoted is
    evidence, not a ratification, and the sentence under-claims.
    """
    origin_kinds = profile.source_kinds
    claim_text = _triple_text(subject_name, rel_type, object_name)
    claim = build_claim(
        verification_status=verification_status,
        origin_count=profile.origin_count,
        origin_kinds=origin_kinds,
        as_of=as_of,
        claim_text=claim_text,
        counterpart_text=counterpart_text,
        counterpart_origin_count=counterpart_origin_count,
        checked_as_of=checked_as_of,
    )
    return Badge(
        verification_status=verification_status,
        origin_count=profile.origin_count,
        origin_kinds=origin_kinds,
        as_of=as_of,
        contradiction=verification_status == DISPUTED,
        human_ratified=(
            HUMAN_SOURCE_KIND in origin_kinds or verification_status == CONFIRMED
        ),
        stale=stale,
        claim=claim,
    )


_CITATION_COUNTS_SQL = text(
    """
    SELECT article_id, COUNT(DISTINCT fact_id) AS cited_facts
    FROM article_citations
    WHERE article_id = ANY(CAST(:ids AS uuid[]))
    GROUP BY article_id
    """
)


async def badges_for_articles(
    session: AsyncSession, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Badge]:
    """One badge per article row, in **one** batched query however long the page.

    Everything but the citation count is already on the channel's own row —
    status, coverage, `synthesized_at`, the stale flag — so the only thing this
    reads is how many distinct facts ground the article. Per-row fan-out here
    would put a query behind every article a search returns.

    `origin_count` counts **cited facts**, and `origin_kinds` is `("fact",)`:
    an article's provenance is its citations, and doc 09 says so in terms —
    "its provenance is only its cited facts". Rolling its citations' own
    origins into the count was considered and rejected when the semantics were
    ruled (2026-08-12): it would assert corroboration strength for prose that
    nothing corroborated, and it costs a provenance query per article on a read
    path.

    `contradiction` is False and `human_ratified` follows the rung, because
    there is no article-level contradiction detector and `confirmed` is the
    human-only rung on this axis exactly as on the fact axis.
    """
    if not rows:
        return {}
    ids = [str(row.get("article_id") or row.get("id")) for row in rows]
    counts = {
        str(r["article_id"]): int(r["cited_facts"])
        for r in (
            await session.execute(_CITATION_COUNTS_SQL, {"ids": ids})
        ).mappings().all()
    }

    badges: dict[str, Badge] = {}
    for row in rows:
        article_id = str(row.get("article_id") or row.get("id"))
        status = row.get("verification_status")
        cited = counts.get(article_id, 0)
        coverage = row.get("confidence")
        as_of = row.get("synthesized_at")
        badges[article_id] = Badge(
            verification_status=status,
            origin_count=cited,
            origin_kinds=("fact",),
            as_of=as_of,
            contradiction=False,
            human_ratified=status == CONFIRMED,
            stale=bool(row.get("stale")),
            claim=build_article_claim(
                cited_facts=cited,
                coverage=float(coverage) if coverage is not None else None,
                as_of=as_of,
            ),
        )
    return badges


# The recompute's progress, read as data (Degradation 1). The key names the
# job's own state row and is spelled here rather than imported: the job is a
# dream-job module and this is a read path (invariant 15). The badge tests pin
# this spelling to the job's.
RECOMPUTE_STATE_KEY = "verification_recompute_state"

# A fact's latest `sources_changed` event is drained when it sits at or behind
# the watermark in the drain's own `(created_at, id)` order. The same tuple
# compare the drain uses, so a same-transaction tie reads the way the drain
# read it.
_CHECKED_BY_RECOMPUTE_SQL = text(
    """
    WITH progress AS (
        SELECT CAST(value ->> 'watermark_created_at' AS timestamptz) AS wm_ts,
               CAST(value ->> 'watermark_id' AS bigint) AS wm_id
        FROM config
        WHERE key = :state_key
    ),
    latest AS (
        SELECT DISTINCT ON (object_id) object_id, id, created_at
        FROM events
        WHERE object_type = 'fact'
          AND event_type = 'sources_changed'
          AND object_id = ANY(CAST(:ids AS uuid[]))
        ORDER BY object_id, created_at DESC, id DESC
    )
    SELECT latest.object_id, progress.wm_ts
    FROM latest CROSS JOIN progress
    WHERE progress.wm_id IS NOT NULL
      AND (latest.created_at < progress.wm_ts
           OR (latest.created_at = progress.wm_ts AND latest.id <= progress.wm_id))
    """
)


async def checked_by_recompute(
    session: AsyncSession, fact_ids: Sequence[str]
) -> dict[str, datetime]:
    """The watermark's ``created_at`` for each fact the drain has reached.

    A fact is present when its latest ``sources_changed`` event is at or
    behind the recompute's watermark, so every recorded change to its evidence
    has been drained. Absent: a fact with no such event, any fact on a vault
    whose recompute has never drained, and a fact with evidence newer than the
    watermark.
    """
    if not fact_ids:
        return {}
    result = await session.execute(
        _CHECKED_BY_RECOMPUTE_SQL,
        {"ids": list(fact_ids), "state_key": RECOMPUTE_STATE_KEY},
    )
    return {str(row["object_id"]): row["wm_ts"] for row in result.mappings().all()}


async def badges_for_facts(
    session: AsyncSession,
    rows: Sequence[Mapping[str, Any]],
    *,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Badge]:
    """One badge per fact row, in at most four batched queries however long
    the page.

    The queries are the provenance profiles, the latest ``verified`` event per
    fact, the recompute's progress (Degradation 1), and — only when something
    on the page is disputed — the profiles of the counterparts those disputes
    name. A per-row fan-out would put a page's worth of round trips behind a
    browsing list. A caller that already read the ``verified`` evidence for
    these rows passes it as ``evidence``.
    """
    if not rows:
        return {}
    fact_ids = [str(row["id"]) for row in rows]
    sources = FactSourceRepository(session)
    profiles = await sources.origin_profiles(fact_ids)
    if evidence is None:
        evidence = await latest_verified_evidence(session, fact_ids)
    checked = await checked_by_recompute(session, fact_ids)

    counterpart_by_fact: dict[str, tuple[str | None, str | None]] = {}
    for row in rows:
        if row.get("verification_status") != DISPUTED:
            continue
        fid = str(row["id"])
        payload = (evidence.get(fid) or {}).get("payload")
        block = (
            payload.get(CONTRADICTION_EVIDENCE_KEY)
            if isinstance(payload, Mapping)
            else None
        )
        counterpart_by_fact[fid] = counterpart_claim(block)

    counterpart_ids = sorted(
        {
            cid
            for cid, text in counterpart_by_fact.values()
            if _names_a_counterpart(cid, text)
        }
    )
    counterpart_profiles = (
        await sources.origin_profiles(counterpart_ids) if counterpart_ids else {}
    )

    badges: dict[str, Badge] = {}
    for row in rows:
        fid = str(row["id"])
        counterpart_id, counterpart_text = counterpart_by_fact.get(fid, (None, None))
        counterpart_count = None
        if _names_a_counterpart(counterpart_id, counterpart_text):
            counterpart_count = counterpart_profiles[counterpart_id].origin_count
        badges[fid] = build_badge(
            verification_status=row.get("verification_status"),
            profile=profiles[fid],
            as_of=(evidence.get(fid) or {}).get("recorded_at"),
            subject_name=row.get("subject_name"),
            rel_type=row.get("rel_type"),
            object_name=row.get("object_name"),
            counterpart_text=counterpart_text,
            counterpart_origin_count=counterpart_count,
            checked_as_of=checked.get(fid),
        )
    return badges


async def badge_for_fact(
    session: AsyncSession, row: Mapping[str, Any]
) -> Badge:
    return (await badges_for_facts(session, [row]))[str(row["id"])]


def row_labels(
    *,
    id_kind: str,
    verification_status: str | None = None,
    lifecycle: str | None = None,
    badge: Badge | None = None,
    gate: "ClaimGate | None" = None,
) -> dict[str, Any]:
    """Doc 12 §4's label triplet, with the L0 rule made unrepresentable.

    A memory row carries ``badge: null`` and ``verification_status: null`` and
    its lifecycle label instead — L0 is episodic recall, not a verified claim,
    so a badge on one would assert corroboration of a thing that was never
    adjudicated. Refusing the badge here rather than dropping it silently is
    the point: a caller that built one for a memory has a bug upstream, and a
    silent drop would hide it.

    ``unverified`` (T2.56) is doc 07 §5's cold-start label, spelled plainly
    rather than left for a consumer to infer from the tier. It is ``True`` on
    every L0 row unconditionally and on an L2/L3 row whenever
    :data:`VERIFIED_TIER_STATUSES` does not name its rung — so a fresh
    ``candidate`` and a live ``disputed`` fact both read as unverified, and
    only ``corroborated``/``confirmed`` read otherwise. The word itself is
    safe under :func:`assert_no_certainty_words`: the guard matches
    ``\\bverified\\b`` on a word boundary, and there is none between the
    ``un`` prefix and ``verified``.
    """
    if id_kind in LIFECYCLE_ID_KINDS:
        if badge is not None:
            raise ValueError(
                f"an L0 {id_kind} row carries no badge: it has a lifecycle, "
                "not a verification status, and nothing adjudicated it"
            )
        if verification_status is not None:
            raise ValueError(
                f"an L0 {id_kind} row carries no verification_status; "
                f"{verification_status!r} is the vocabulary of a vault row"
            )
        return {
            "verification_status": None,
            "lifecycle": lifecycle,
            "badge": None,
            "unverified": True,
        }
    if id_kind not in BADGE_BEARING_ID_KINDS:
        raise ValueError(
            f"unknown id_kind {id_kind!r}; doc 12 fixes "
            f"{sorted(BADGE_BEARING_ID_KINDS | LIFECYCLE_ID_KINDS)}"
        )
    if lifecycle is not None:
        raise ValueError(
            f"an L2/L3 {id_kind} row carries no lifecycle label; the belief "
            "axis and the verification axis are not a memory's status column"
        )
    # T2.95: the label is gated on evidence, the derivation is not. Without
    # G-C's promotion record a promoted status is withheld and the row is
    # served as `candidate` — the status on disk is untouched, and minting the
    # record restores the label with no code change.
    #
    # Enforced here because this module is doc 12's *one* producer of the claim
    # surface. A gate applied at each consumer would be a convention; applied
    # at the producer it is a property, and the scan in the test suite keeps it
    # one.
    #
    # `id_kind` rides through because the evidence does: a fact's promoted rung
    # is certified by G-C's promotion audit and an article's by G-D's judge
    # qualification. Gating both against one record would let the fact record
    # light an article's label.
    # `gate` is forwarded rather than resolved here (T3.02). `served_status`
    # has always taken one; nothing passed it, so every caller fell through to
    # the module's own default -- for articles, an unconditionally closed
    # groundedness gate. That made opening the label a *code* change, which is
    # exactly the code-gated label T2.95 forbids. The gate now comes from the
    # judge's single door and rides in; a caller that passes none still gets
    # the fail-closed default, so an unwired path cannot serve a promoted
    # status by omission.
    served, suppression = served_status(
        verification_status, id_kind=id_kind, gate=gate
    )
    return {
        "verification_status": served,
        "lifecycle": None,
        # A withheld status must not carry a badge asserting the corroboration
        # it was withheld for: the sentence names the origin count and the
        # absence of contradiction, which is precisely the claim under gate.
        "badge": badge.as_dict() if badge is not None and suppression is None else None,
        "unverified": served not in VERIFIED_TIER_STATUSES,
        # Suppressed and genuinely-candidate must not read alike, or a missing
        # measurement becomes an apparent property of the corpus.
        "label_suppressed": suppression,
    }


__all__ = [
    "BADGE_BEARING_ID_KINDS",
    "Badge",
    "CLAIM_VOCABULARY",
    "badges_for_articles",
    "build_article_claim",
    "CertaintyWordError",
    "LIFECYCLE_ID_KINDS",
    "RECOMPUTE_STATE_KEY",
    "VERIFIED_TIER_STATUSES",
    "assert_no_certainty_words",
    "badge_for_fact",
    "badges_for_facts",
    "build_badge",
    "build_claim",
    "checked_by_recompute",
    "counterpart_claim",
    "row_labels",
]
