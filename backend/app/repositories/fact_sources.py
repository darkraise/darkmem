"""Provenance rows, and the corroboration arithmetic they feed.

Corroboration counts ``COUNT(DISTINCT origin_key)`` over a fact's
``fact_sources`` — **never rows** (doc 08 §4.1, doc 04 §8.3). Row-counting
manufactures agreement out of one chatty source: an agent that re-saves the same
claim ten times, or a repository re-derived across a hundred commits, is one
origin and must count as one. Every number this module produces is read by the
verification ladder, so its direction of error is fixed: it may **undercount**,
never overcount. Undercounting only delays a promotion; overcounting fabricates
one, and every article citing that fact inherits the lie.

Four rules, all enforced here rather than left to callers:

1. **Distinct origins, never rows** — ``count_distinct_origins`` and every count
   inside ``origin_profile`` group by origin.
2. **The threshold N is diversity-sensitive** — ``OriginProfile`` exposes
   ``required_origin_count``: ``CORROBORATION_N_DIVERSE`` when the origins
   differ in ``source_kind`` or lie ``CORROBORATION_TIME_GAP_DAYS`` apart across
   two distinct origins, else ``CORROBORATION_N_DEFAULT``. Both gates need two
   *distinct* origins, so one origin can never lower its own bar. This module
   computes N; it never compares it to anything and never writes
   ``verification_status`` — the ladder is T2.03's.
3. **Derived rows are a structural exclusion** — a Layer-2 fact or a Layer-3
   article is never a source, so ``add_source`` rejects any ``source_kind``
   outside ``SOURCE_KINDS`` instead of trusting callers to remember. An agent
   re-saving an article must not be able to inflate the count of the fact that
   article cites.
4. **Unknown origin identity merges to ONE origin.** Every row whose
   ``origin_key`` is NULL, blank, or carries the capture layer's ``unknown:``
   marker folds into a single reserved bucket **per fact**, so ten anonymous
   rows are one origin, never ten.

**The collapsing scheme for rule 4, and why this one.** The normalised origin is
``lower(btrim(origin_key))``, except that NULL, whitespace-only, the bare word
``unknown`` and anything prefixed ``unknown:`` all map to one reserved sentinel.
Two properties make that defensible. First, it is *strictly* merge-only: a
sentinel collision (a real key that happens to equal the sentinel, or two real
keys differing only in case or padding) merges two origins into one, which
undercounts — the safe direction — and no input can ever split one origin into
two. Second, it is deliberately coarser than the capture layer it reads from:
``app.api.mcp.client_identity.resolve_origin_key`` already merges unattributed
captures to ``unknown:<source>:<project>``, which is one origin *per door and
project*, so an unattributed MCP capture and an unattributed REST capture of the
same claim would arrive as two keys. They are not two witnesses — nothing about
either identifies a distinct session — so this layer folds all of them into one
bucket. That closes the one path by which unknown identity could still reach the
``N = 2`` bar on its own (two anonymous memory captures seven days apart), which
is exactly the counterfeit corroboration rule 4 exists to forbid. The cost is a
fact sourced only by anonymous captures never promoting; that is a delayed
label, which the design accepts, and it is repaired by attributing the capture,
not by loosening the count.

**The bucket counts, but it never lowers the bar.** Merging unknown identity to
one origin protects the *count*; leaving that one origin free to satisfy the
gates would re-open the same door one level up, because a gate that fires drops
N from 3 to 2. One attributable witness plus one anonymous capture would then be
promotion-ready — the same chatty source manufacturing its own corroboration,
through the threshold rather than through the count. So the bucket contributes
to ``origin_count`` and to nothing else: ``kinds_are_diverse`` and
``max_cross_origin_gap`` both read ``attributable_origins``. Doc 08 §4.1's own
wording is the warrant — assertions "≥ 7 days apart across distinct sessions",
and origins that "differ in source-kind" — and the bucket is the absence of
session identity, not a session that happens to be unnamed. This changes the
outcome in exactly one shape of profile: one known origin plus anonymous rows.
With two known origins the count is already ≥ 2 with or without the bucket, and
the known pair supplies the gate on its own.

Provenance writes are not journalled here. ``fact_lift`` (T2.10) is the producer
and owns the ``sources_changed`` event that feeds the recompute; a second
emitter under it would double-count the same provenance change.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_triples import OPEN_BELIEF_PREDICATE
from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# "Currently open", as distinct from "live". ``LIVE_PREDICATE``
# (``expired_at IS NULL``) answers *what is retained as history*, and a
# window-closed row is still live under it; this one answers *what is currently
# believed* and is exactly ``ux_knowledge_triples_open``'s scope. The two are
# not interchangeable in either direction, and confusing them here is not a
# margin error but a total one: stale-on-arrival closes the older row's window
# on every legitimate correction, so a memory whose fact was ever replaced
# permanently holds a window-closed row and would read as still asserting an
# open belief forever.
#
# Imported rather than re-declared: T2.42 and T2.45 each minted this string in
# their own lane, same name and same value in different files, so git merged
# both without a conflict to force the collapse. Two copies would have drifted
# silently, and a guard 2 whose predicate no longer matches the unique index's
# scope fails in exactly the total direction described above.

# The kinds that may assert a fact today. Doc 04 §8.3's vocabulary is
# {memory, block, code, human}; `block` is held in _RESERVED_SOURCE_KINDS below
# because no producer writes one yet.
SOURCE_KINDS = frozenset({"memory", "code", "human"})

_RESERVED_SOURCE_KINDS = {
    "block": "no producer writes one yet",
    # Doc 08 §4.1 names a `document` origin ("document -> document_id"); doc 04
    # §8.3's column vocabulary has no such value, so document content arrives
    # under the `block` kind. A caller following the former deserves to be told.
    "document": "document content arrives under the 'block' kind, which has no producer yet",
}

# Named only to make the refusal legible. Anything outside SOURCE_KINDS is
# refused regardless of whether it appears here.
_DERIVED_SOURCE_KINDS = frozenset({"fact", "triple", "knowledge_triple", "article",
                                   "knowledge_article"})

# The diversity/time gate's parameters. Doc 08 §4.1 flags all three as future
# `config` rows tuned from the measured promotion rate; T2.03 owns that lift, so
# they are named constants here rather than configuration built ahead of a
# consumer.
CORROBORATION_TIME_GAP_DAYS = 7
CORROBORATION_N_DIVERSE = 2
CORROBORATION_N_DEFAULT = 3

# One bucket for every row of unknown origin identity. The \x1f prefix keeps it
# out of the range of a real key; a collision would merge, which undercounts.
_UNKNOWN_ORIGIN_BUCKET = "\x1funknown-origin"

# Mirrors app.api.mcp.client_identity.UNKNOWN_ORIGIN_PREFIX; test_fact_sources
# pins the two together so a rename there fails loudly here.
_UNKNOWN_ORIGIN_MATCH = {
    "unknown_exact": "unknown",
    "unknown_like": "unknown:%",
    "unknown_bucket": _UNKNOWN_ORIGIN_BUCKET,
}

_NORMALIZED_ORIGIN = """
        CASE
            WHEN origin_key IS NULL
              OR btrim(origin_key) = ''
              OR lower(btrim(origin_key)) = CAST(:unknown_exact AS text)
              OR lower(btrim(origin_key)) LIKE CAST(:unknown_like AS text)
            THEN CAST(:unknown_bucket AS text)
            ELSE lower(btrim(origin_key))
        END
"""

_COLUMNS = "id, fact_id, source_kind, source_ref, origin_key, detail, created_at"


@dataclass(frozen=True)
class OriginObservation:
    """One origin's whole contribution to a fact, however many rows it wrote.

    ``origin_key`` is the **normalised** identity (lowercased, trimmed), not the
    raw ``fact_sources.origin_key`` any one row stores, and it is ``None`` for
    the merged unknown-identity bucket. A consumer matching these back to raw
    stored values must normalise the same way or it will miss on case variants.
    """

    origin_key: str | None
    source_kinds: tuple[str, ...]
    first_seen: datetime
    last_seen: datetime
    row_count: int

    @property
    def is_unknown(self) -> bool:
        """True for the merged unknown-identity bucket, which has no key."""
        return self.origin_key is None


@dataclass(frozen=True)
class OriginProfile:
    """What the ladder needs to pick its threshold, and nothing more.

    Every derived property is computed over *origins*, never rows, and every
    gate that could lower the threshold requires two distinct origins.
    """

    fact_id: str
    origins: tuple[OriginObservation, ...]

    @property
    def origin_count(self) -> int:
        return len(self.origins)

    @property
    def source_kinds(self) -> tuple[str, ...]:
        return tuple(sorted({kind for o in self.origins for kind in o.source_kinds}))

    @property
    def has_unknown_origin(self) -> bool:
        return any(o.is_unknown for o in self.origins)

    @property
    def attributable_origins(self) -> tuple[OriginObservation, ...]:
        """The origins that identify a witness — the only ones a gate may use.

        The unknown-identity bucket counts toward ``origin_count``, but it is
        the *absence* of session identity, not a session. Doc 08 §4.1 gates on
        origins that "differ in source-kind" and on assertions "≥ 7 days apart
        across distinct sessions"; neither predicate has a truth value for a
        bucket that names no session, so both gates read this instead.
        """
        return tuple(o for o in self.origins if not o.is_unknown)

    @property
    def kinds_are_diverse(self) -> bool:
        """Two *distinct, attributable* origins carrying two different kinds.

        An origin cannot differ from itself, so a lone origin asserting under
        several kinds does not make the set diverse.
        """
        origins = self.attributable_origins
        if len(origins) < 2:
            return False
        if any(len(o.source_kinds) > 1 for o in origins):
            return True
        return len({o.source_kinds[0] for o in origins if o.source_kinds}) > 1

    @property
    def max_cross_origin_gap(self) -> timedelta:
        """The widest span between assertions from two *attributable* origins.

        One origin asserting the same fact over a year is still one origin
        re-stating itself, so a span within a single origin never counts — and
        neither does a span measured against the unknown bucket.
        """
        origins = self.attributable_origins
        if len(origins) < 2:
            return timedelta(0)
        by_first = sorted(range(len(origins)), key=lambda i: origins[i].first_seen)
        earliest, runner_up = by_first[0], by_first[1]
        widest = timedelta(0)
        for index, origin in enumerate(origins):
            other = origins[runner_up if index == earliest else earliest]
            gap = origin.last_seen - other.first_seen
            if gap > widest:
                widest = gap
        return widest

    def required_origin_count_for(
        self,
        *,
        n_diverse: int,
        n_default: int,
        time_gap_days: int,
    ) -> int:
        """N under caller-supplied thresholds, and which gate produced it.

        The rule itself lives here — one spelling, next to the
        ``attributable_origins`` semantics it depends on — while the three
        numbers come from the caller. T2.03's ladder passes values merged from
        the ``verification_ladder`` config row; ``required_origin_count`` below
        passes this module's constants. Neither restates the rule.
        """
        if self.kinds_are_diverse:
            return n_diverse
        if self.max_cross_origin_gap >= timedelta(days=time_gap_days):
            return n_diverse
        return n_default

    def gate_fired_for(self, *, time_gap_days: int) -> str:
        """Which threshold gate fires — ``diversity``, ``time_gap`` or ``none``.

        Diversity is checked first and wins a tie, matching
        ``required_origin_count_for``'s order, so the reported gate is always
        the one that actually determined N rather than merely one that would
        have.
        """
        if self.kinds_are_diverse:
            return "diversity"
        if self.max_cross_origin_gap >= timedelta(days=time_gap_days):
            return "time_gap"
        return "none"

    @property
    def required_origin_count(self) -> int:
        """N — the distinct-origin count promotion would require."""
        return self.required_origin_count_for(
            n_diverse=CORROBORATION_N_DIVERSE,
            n_default=CORROBORATION_N_DEFAULT,
            time_gap_days=CORROBORATION_TIME_GAP_DAYS,
        )


@dataclass(frozen=True)
class OriginGroup:
    """One origin's rows, kept rather than summarised away.

    ``OriginObservation`` answers "how many origins, asserting under which
    kinds"; this answers "which rows, and what does each one point at" — the
    audit a human performs against a badge that claims a count. Same
    normalised ``origin_key``, ``None`` for the merged unknown-identity
    bucket.
    """

    origin_key: str | None
    source_kinds: tuple[str, ...]
    first_seen: datetime
    last_seen: datetime
    sources: tuple[dict, ...]

    @property
    def is_unknown(self) -> bool:
        return self.origin_key is None


@dataclass(frozen=True)
class MemorySource:
    """One memory that asserts a fact, carrying what a status decision reads.

    ``memory_id`` is the canonical text spelling ``memory_source_ref`` mints, so
    it lines up with the ``source_ref`` the provenance rows store and with the
    refs the withdrawal sweep emits. ``status`` and ``created_at`` ride along
    because the consumers that pick a successor out of these rows need to order
    them and to report what they saw; the row's mere presence is what
    establishes the memory still exists.
    """

    memory_id: str
    project: str
    status: str
    created_at: datetime


def _row_to_dict(row: Any) -> dict:
    out = dict(row)
    for key in ("id", "fact_id"):
        value = out.get(key)
        out[key] = str(value) if value is not None else None
    return out


def _clean_identity(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"fact_sources.{field} must be a non-empty string; the dedupe key "
            f"(fact_id, source_kind, source_ref) cannot deduplicate NULLs"
        )
    return value.strip()


def _validate_source_kind(source_kind: str) -> str:
    kind = _clean_identity(source_kind, "source_kind")
    if kind in SOURCE_KINDS:
        return kind
    if kind in _DERIVED_SOURCE_KINDS:
        raise ValueError(
            f"source_kind {kind!r} is a derived layer and can never be a fact "
            f"source: a fact or article re-asserting a claim would inflate the "
            f"corroboration count of the very fact it cites"
        )
    if kind in _RESERVED_SOURCE_KINDS:
        raise ValueError(
            f"source_kind {kind!r} is reserved: {_RESERVED_SOURCE_KINDS[kind]}; "
            f"permitted kinds are {sorted(SOURCE_KINDS)}"
        )
    raise ValueError(
        f"unknown source_kind {kind!r}; permitted kinds are {sorted(SOURCE_KINDS)}"
    )


class FactSourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_source(
        self,
        *,
        fact_id: UUID | str,
        source_kind: str,
        source_ref: str,
        origin_key: str | None,
        detail: dict | None = None,
    ) -> dict:
        """Record that a source asserts a fact. Idempotent on the dedupe key.

        Re-asserting the same ``(fact_id, source_kind, source_ref)`` returns the
        existing row and changes nothing — not ``origin_key``, not ``detail``.
        First assertion wins on purpose: letting a later call rewrite the origin
        of a row already counted would let a re-save move a row between origin
        buckets, which can raise the count. Provenance is a record of what was
        asserted, not a mutable cache.

        ``origin_key`` is required but nullable: a caller that does not know the
        origin must say so explicitly, and NULL folds into the single
        unknown-identity bucket rather than counting as its own origin.
        """
        kind = _validate_source_kind(source_kind)
        ref = _clean_identity(source_ref, "source_ref")
        params = {
            "id": str(new_id()),
            "fact_id": str(fact_id),
            "source_kind": kind,
            "source_ref": ref,
            "origin_key": origin_key,
            "detail": json.dumps(detail) if detail is not None else None,
        }
        result = await self.session.execute(
            text(f"""
                INSERT INTO fact_sources (
                    id, fact_id, source_kind, source_ref, origin_key, detail
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:fact_id AS uuid),
                    CAST(:source_kind AS text),
                    CAST(:source_ref AS text),
                    CAST(:origin_key AS text),
                    CAST(:detail AS jsonb)
                )
                ON CONFLICT (fact_id, source_kind, source_ref) DO NOTHING
                RETURNING {_COLUMNS}
            """),
            params,
        )
        row = result.mappings().first()
        if row is not None:
            return _row_to_dict(row)

        existing = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM fact_sources
                WHERE fact_id = CAST(:fact_id AS uuid)
                  AND source_kind = CAST(:source_kind AS text)
                  AND source_ref = CAST(:source_ref AS text)
            """),
            {"fact_id": params["fact_id"], "source_kind": kind, "source_ref": ref},
        )
        return _row_to_dict(existing.mappings().one())

    async def count_distinct_origins(self, fact_id: UUID | str) -> int:
        """``COUNT(DISTINCT origin_key)`` — the corroboration signal itself.

        Rows are not the unit and never can be: the count groups by normalised
        origin, so ten rows from one origin are 1 and every row of unknown
        identity joins one shared bucket.
        """
        result = await self.session.execute(
            text(f"""
                SELECT COUNT(DISTINCT {_NORMALIZED_ORIGIN}) AS origin_count
                FROM fact_sources
                WHERE fact_id = CAST(:fact_id AS uuid)
            """),
            {"fact_id": str(fact_id), **_UNKNOWN_ORIGIN_MATCH},
        )
        return int(result.scalar_one())

    async def origin_profile(self, fact_id: UUID | str) -> OriginProfile:
        """The per-origin view the threshold rule reads.

        One row per distinct origin, carrying the kinds that origin asserted
        under and the first/last time it did — the timestamps the time-gap gate
        needs. The aggregation happens in SQL so the "never rows" rule cannot be
        lost by a caller iterating the wrong thing.

        A thin wrapper over the batched form rather than its own statement:
        one grouping means one count, and rule 1's "never rows" cannot hold on
        one path while a second path drifts off it.
        """
        key = str(fact_id)
        return (await self.origin_profiles([key]))[key]

    async def origin_profiles(
        self, fact_ids: Sequence[UUID | str]
    ) -> dict[str, OriginProfile]:
        """``origin_profile`` for a bounded page, in one round trip.

        Every requested id appears in the result, including one with no
        provenance at all — an empty profile is the honest answer for a fact
        nothing has sourced yet, and a missing key would make a caller's
        ``KeyError`` indistinguishable from a fetch that failed.
        """
        keys = [str(fact_id) for fact_id in fact_ids]
        profiles = {key: OriginProfile(fact_id=key, origins=()) for key in keys}
        if not keys:
            return profiles

        result = await self.session.execute(
            text(f"""
                SELECT
                    CAST(fact_id AS text) AS fact_id,
                    {_NORMALIZED_ORIGIN} AS origin,
                    array_agg(DISTINCT source_kind)
                        FILTER (WHERE source_kind IS NOT NULL) AS source_kinds,
                    MIN(created_at) AS first_seen,
                    MAX(created_at) AS last_seen,
                    COUNT(*) AS row_count
                FROM fact_sources
                WHERE fact_id = ANY(CAST(:fact_ids AS uuid[]))
                GROUP BY 1, 2
                ORDER BY 1, MIN(created_at), 2
            """),
            {"fact_ids": keys, **_UNKNOWN_ORIGIN_MATCH},
        )
        observed: dict[str, list[OriginObservation]] = {}
        for row in result.mappings().all():
            observed.setdefault(row["fact_id"], []).append(
                OriginObservation(
                    origin_key=(
                        None if row["origin"] == _UNKNOWN_ORIGIN_BUCKET else row["origin"]
                    ),
                    source_kinds=tuple(sorted(row["source_kinds"] or ())),
                    first_seen=row["first_seen"],
                    last_seen=row["last_seen"],
                    row_count=int(row["row_count"]),
                )
            )
        for key, origins in observed.items():
            profiles[key] = OriginProfile(fact_id=key, origins=tuple(origins))
        return profiles

    async def sources_by_origin(self, fact_id: UUID | str) -> tuple[OriginGroup, ...]:
        """Every provenance row, grouped under the origin that wrote it.

        This is what makes the badge's ``origin_count`` auditable rather than
        asserted: a reader counts the groups and gets the number the badge
        claims. The grouping expression is ``_NORMALIZED_ORIGIN`` — the same
        one ``origin_profiles`` counts on, referenced rather than restated, so
        the audit cannot disagree with the claim it audits.
        """
        result = await self.session.execute(
            text(f"""
                SELECT {_NORMALIZED_ORIGIN} AS origin, {_COLUMNS}
                FROM fact_sources
                WHERE fact_id = CAST(:fact_id AS uuid)
                ORDER BY 1, created_at, id
            """),
            {"fact_id": str(fact_id), **_UNKNOWN_ORIGIN_MATCH},
        )
        grouped: dict[str, list[dict]] = {}
        for row in result.mappings().all():
            source = _row_to_dict(row)
            source.pop("origin", None)
            grouped.setdefault(row["origin"], []).append(source)
        return tuple(
            OriginGroup(
                origin_key=None if origin == _UNKNOWN_ORIGIN_BUCKET else origin,
                source_kinds=tuple(sorted({r["source_kind"] for r in rows})),
                first_seen=min(r["created_at"] for r in rows),
                last_seen=max(r["created_at"] for r in rows),
                sources=tuple(rows),
            )
            for origin, rows in grouped.items()
        )

    async def memory_sources_for_fact(
        self, fact_id: UUID | str
    ) -> tuple[MemorySource, ...]:
        """The memories that assert a fact — the provenance reverse lookup.

        A memory appears here iff a ``memories`` row still matches its
        ``source_ref``. That existence test is the whole liveness condition:
        ``fact_sources.source_ref`` is a soft reference with no FK, so the
        memory analogue of belief withdrawal is deletion, and a withdrawn
        memory leaves a dangling ref that this join simply does not find. It is
        the same test ``_ORPHANED_PROVENANCE`` applies to orphanhood.

        Deliberately **not** filtered by ``status``. A memory that asserted a
        newer belief may itself have been superseded moments later, and
        excluding it would strand the lineage a supersession pointer exists to
        record — the lineage reads walk pointers status-blind, and the self-FK
        requires existence and nothing else.

        The join casts ``memories.id`` to text rather than the ref to uuid:
        ``source_ref`` holds every kind's spelling, and a planner free to hoist
        ``CAST(source_ref AS uuid)`` above the kind filter would abort on the
        first non-uuid ref.
        """
        result = await self.session.execute(
            text("""
                SELECT DISTINCT CAST(m.id AS text) AS memory_id,
                       m.project, m.status, m.created_at
                FROM fact_sources fs
                JOIN memories m ON CAST(m.id AS text) = fs.source_ref
                WHERE fs.fact_id = CAST(:fact_id AS uuid)
                  AND fs.source_kind = CAST(:kind AS text)
                ORDER BY 1
            """),
            {"fact_id": str(fact_id), "kind": MEMORY_SOURCE_KIND},
        )
        return tuple(
            MemorySource(
                memory_id=row["memory_id"],
                project=row["project"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in result.mappings().all()
        )

    async def memory_refs_for_facts(
        self, fact_ids: Sequence[UUID | str]
    ) -> dict[str, tuple[str, ...]]:
        """Which memories assert each of several facts — one bounded lookup.

        Doc 07 §5's grouping pass needs the provenance of a whole result set at
        once, so this takes the set rather than one fact: a per-fact call would
        put a round trip behind every returned fact. The scan is bounded by the
        ids handed in and rides ``ix_fact_sources_fact``.

        **This is a provenance read and never a count.** It returns refs so a
        caller can intersect them with rows it already holds; corroboration
        arithmetic stays ``count_distinct_origins`` / ``origin_profile``, which
        group by origin. Counting the refs here — or letting a caller count the
        tuple — is exactly the row-counting this module exists to forbid, and
        the two questions are different: several rows of one origin are several
        supporting memories and one witness.

        Refs come back **as stored**, with no join against ``memories``.
        ``source_ref`` is a soft reference with no FK, so a ref naming a deleted
        memory is representable; joining to filter it out would be work the
        caller's own intersection already does, since nothing in a result set
        can match a memory that does not exist.
        """
        if not fact_ids:
            return {}
        result = await self.session.execute(
            text("""
                SELECT CAST(fact_id AS text) AS fact_id, source_ref
                FROM fact_sources
                WHERE source_kind = CAST(:kind AS text)
                  AND fact_id = ANY(CAST(:fact_ids AS uuid[]))
                ORDER BY 1, 2
            """),
            {
                "kind": MEMORY_SOURCE_KIND,
                "fact_ids": [str(fact_id) for fact_id in fact_ids],
            },
        )
        out: dict[str, list[str]] = {}
        for row in result.mappings().all():
            out.setdefault(row["fact_id"], []).append(row["source_ref"])
        return {fact_id: tuple(refs) for fact_id, refs in out.items()}

    async def sourced_triples(self, memory_id: UUID | str) -> tuple[int, int]:
        """``(total, open)`` over the triples a memory sources — both, always.

        One method returning one tuple rather than an openness test beside a
        count, because the two numbers are only meaningful together. A caller
        asking "does this memory still assert an open belief?" and getting
        ``False`` cannot tell a **spent** memory from an **unlifted** one: fact
        lifting runs on a cadence, so a young memory has no provenance at all,
        and the withdrawal sweep deletes a provenance row before expiring the
        fact it orphans. Both read as zero open triples, and only ``total``
        separates them. Splitting this into two methods is precisely the shape
        in which the second number gets dropped.

        The ``source_kind`` filter is required, not tidiness: ``source_ref``
        carries no type discriminator, so a human reviewer's ref or a repo id
        would otherwise be counted as this memory's evidence.

        The ref is minted, never stringified as given — a braced or upper-cased
        id would match no stored row, and zero rows is exactly what a spent
        memory looks like.
        """
        result = await self.session.execute(
            text(f"""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE {OPEN_BELIEF_PREDICATE}) AS open
                FROM fact_sources fs
                JOIN knowledge_triples kt ON kt.id = fs.fact_id
                WHERE fs.source_kind = CAST(:kind AS text)
                  AND fs.source_ref = CAST(:ref AS text)
            """),
            {"kind": MEMORY_SOURCE_KIND, "ref": memory_source_ref(memory_id)},
        )
        row = result.mappings().one()
        return int(row["total"]), int(row["open"])

    async def facts_for_source(
        self,
        source_kind: str,
        source_ref: str,
        *,
        project: str,
    ) -> list[str]:
        """Which facts a given source asserts — the reverse lookup.

        ``project`` is required, not an optional filter, for the reason T2.01
        made ``get_live`` and ``as_of`` require it: the scope belongs in the
        repository, not at the front door. It is load-bearing here rather than
        merely tidy, because ``source_ref`` is a **soft** reference with no FK —
        one human reviewer, or one repository shared between projects, is the
        same ``source_ref`` across several project scopes.

        Deliberately unbounded and not filtered by the belief axis: the callers
        are the withdrawal sweep and the recompute enqueue, and a truncated or
        liveness-filtered answer would silently leave provenance behind. The
        kind is validated for the same reason: a kind no ``add_source`` could
        have written would return an empty list, and a withdrawal sweep with a
        typo would find nothing to withdraw and report no error.
        """
        kind = _validate_source_kind(source_kind)
        result = await self.session.execute(
            text("""
                SELECT DISTINCT fs.fact_id
                FROM fact_sources fs
                JOIN knowledge_triples kt ON kt.id = fs.fact_id
                WHERE fs.source_kind = CAST(:source_kind AS text)
                  AND fs.source_ref = CAST(:source_ref AS text)
                  AND kt.project = CAST(:project AS text)
                ORDER BY fs.fact_id
            """),
            {"source_kind": kind, "source_ref": source_ref, "project": project},
        )
        return [str(row["fact_id"]) for row in result.mappings().all()]
