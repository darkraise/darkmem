"""Doc 07 §5's four-layer composition — all five steps (T2.43, T2.55).

One ordered, total, deterministic list of rows drawn from more than one
epistemic layer, each labelled with where it came from and how well it is
believed. Merge the channel lists in their own key spaces, label and order
them, optionally re-band by a rerank, apply the deterministic multipliers, and
finally group each returned memory under the fact it sources. The sectioned and
fused output shapes are T2.56's; Chat's convergence onto this entry point is
T2.58's. MCP's ``knowledge_search`` is the live caller (T2.72); the article
channel and the reranker arm are still deferred, and the envelope says so
rather than reporting them as if they had run.

**Grouping is composition's last step, never a renderer's first.** Doc 07 §5
fixes the order and §11 records it as a resolved question rather than a
preference: the reranker scores individual rows for query-relevance, so it must
see a supporting memory *before* the provenance collapse hides it. So step 5
runs after the rerank and after the multipliers, inside :func:`compose`, and
both output shapes consume a list that is already grouped. A collapse
implemented in one renderer would be absent from the other, and the fused shape
— the one a token budget takes — is precisely where a triple count is least
affordable.

**Four properties the layers below are built on, none of them incidental.**

*Keys are namespaced.* The merge key is ``"<id_kind>:<raw_id>"``, minted by
:func:`composition_key`. ``rank_fusion.normalize_row_id`` reads ``memory_id``
**or** ``id`` and returns a bare string, so a fact and a memory that happen to
share a UUID land on one key in one flat space with nothing marking which
table each came from — and ``rrf_fuse`` has no notion of an unexpected merge,
so it would sum their mass in silence. The likelier accident is the reverse: a
caller reshapes a fact row as ``{"memory_id": ...}`` to make an existing helper
work and the fact becomes indistinguishable from a memory downstream. A
namespaced key makes both unrepresentable, and gives ``grouped_under``
something that can name one object in one space.

*Support is read, never inferred.* ``fact_sources`` is the sole authority for
which memories back a fact (doc 04 §8.3). Text overlap, embedding proximity and
a shared entity all look like support and none of them is; a composition
inferring it would nest — and so remove from view — a row nothing asserts a
link to.

*The badge is read, never rendered here.* Doc 12 §4 fixes the honest claim as
a structured field on every L2/L3 row and null on L0, and ``fact_badge`` is
its sole producer. This module maps that producer's ``row_labels`` over the
composed rows and spells no part of the sentence itself: a second claim string
is the drift doc 12 exists to prevent, and it would drift precisely where the
two copies disagree about what is known. Until this map existed the served
path emitted no badge at all, which satisfied "null on L0" by emitting nothing
anywhere.

*Invariant 9 is normalised at admission, not at the merge.* :func:`_admit_id`
is the single place ``str()`` is spelled; :func:`composition_key` refuses a
non-``str`` rather than absorbing the same normalisation a second time. Two
normalisation points would mean neither could be broken on its own, so neither
could be tested on its own.

*The cross-layer ordering signal is rank, never a comparison of two channels'
``rrf_score`` magnitudes.* Doc 07 §3 rejects folding raw magnitudes into one
weighted sum because it forces a per-modality normalisation that is brittle to
outliers and re-tunes whenever a channel is added. Two channels' ``rrf_score``
values are exactly such magnitudes, produced by two fusions under two different
weight splits. Rank is the one currency §3 recognises as comparable across
modalities, so the merge interleaves ``channel_rank`` and the multipliers act
*inside* a channel, where magnitudes are commensurable.

**Grouping and the answer budget settle together, at a fixpoint** (T2.70).
Doc 07 §5's grouping predicate is "a memory covered by a **returned** cited
fact", so a fact past the cut is not one a memory may be nested under. But the
two passes are mutually dependent — un-nesting a memory returns it to the
top-level ordering, which moves the cut, which changes which facts are
returned — so they cannot run in sequence. :func:`_grouped_page` iterates them
to stability and carries the termination argument.

**L1 is absent from :data:`LAYERS` on purpose** (doc 07 §8: "L1 candidate graph
is not directly served"). A vocabulary admitting ``L1`` would let a
candidate-graph row be served as a composed result.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.vector import MemoryFilter
from app.schemas.retrieval_trace import ChannelStatus, RetrievalEnvelope
from app.services.fact_badge import Badge, badges_for_facts, row_labels
from app.services.facts_channel import (
    KEYWORD_ARM,
    NAME_ARM,
    SEMANTIC_ARM,
    FactsChannel,
)
from app.services.feature_flags import get_feature_flags_dict
from app.services.hybrid_search import HybridSearchService

from app.services.rank_fusion import (
    RRF_K,
    ContextOutcome,
    DeclaredContext,
    RowContext,
    match_context,
    rank_fusion_factor,
    row_context_from_applies_when,
)
from app.services.verified_evidence import (
    CONTRADICTION_EVIDENCE_KEY,
    latest_verified_evidence,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ARTICLE_CHANNEL_OWNER",
    "COUNTERPART_ABSENT_NO_FINDING",
    "DISPUTED",
    "ID_KINDS",
    "LAYERS",
    "LAYER_BY_ID_KIND",
    "MEMORY_TIER",
    "SUPPORTS_FACT_RELATION",
    "TIER_BY_VERIFICATION_STATUS",
    "ComposedRow",
    "CompositionResult",
    "ComposedResult",
    "LayerCandidate",
    "LayerCompositionService",
    "RERANK_WINDOW",
    "article_candidate",
    "compose",
    "composition_key",
    "cross_layer_rrf",
    "dispute_label",
    "rerank_document_text",
    "fact_candidate",
    "memory_candidate",
    "support_map",
    "tier_for",
]

LAYERS: frozenset[str] = frozenset({"L0", "L2", "L3"})
ID_KINDS: frozenset[str] = frozenset({"memory", "fact", "article"})
LAYER_BY_ID_KIND: dict[str, str] = {"memory": "L0", "fact": "L2", "article": "L3"}

# Per-channel list weights — **order-inert at every magnitude, and that is a
# consequence of the design rather than a pending activation.**
#
# A channel-constant multiplier cancels inside the within-channel re-sort
# (every row of the channel scales by the same factor, so their relative order
# is untouched), and the cross-channel comparison is rank-only by construction
# (D2). So setting a channel to 1e6 or to 1e-9 changes nothing observable, at
# any value. This is *not* the ``RANK_ARMS`` situation: those are inert at
# weight 0 and become live the moment they are activated, whereas these cannot
# become live at all under the rank-authority geometry.
#
# They are kept rather than deleted because they are the per-channel arm of
# the closed vocabulary and they make the currency visible in the trace. **No
# measurement path is owed and none should be minted** — minting a task to
# tune a structurally dead knob is the same order-inert-knob mistake that
# sank an earlier revision of this design. Making them matter would mean
# giving a channel-constant score authority across channels, which is exactly
# the cross-modality magnitude comparison doc 07 §3 rejects.
CHANNEL_LIST_WEIGHTS: dict[str, float] = {"memory": 1.0, "fact": 1.0, "article": 1.0}

# The per-row scalars an arm may read. A signal this mapping does not carry
# makes its arm return exactly 1.0, so a channel with no counterpart for an
# arm (facts have no heat or recency counter until T2.65) needs no
# special-casing to be left alone by it.
SIGNAL_KEYS: tuple[str, ...] = ("confidence", "importance", "heat", "recency")

DISPUTED = "disputed"

# Doc 12's composed-row field table fixes this string verbatim. The trailing
# ``F`` is part of the literal and not a placeholder for the fact's own id or
# text: ``grouped_under`` already names the fact, and a consumer interpolating
# something there would render a relation no other consumer speaks.
SUPPORTS_FACT_RELATION = "supports fact F"

# What the composition says when a disputed fact has no counterpart block on
# its latest verified event. It says "no scan produced one here" and never
# "no counterpart exists" — the three causes of absence (a recovery, a
# caller-overridden verdict, a dispute predating the writer) are not
# distinguishable from the journal.
COUNTERPART_ABSENT_NO_FINDING = "no_finding_recorded"

# Doc 07 §5's ordering rule, as a lookup over the closed verification
# vocabulary. Four things this table is careful about:
#
# It is a lookup and **not** a computation — an unknown status raises rather
# than falling back, because a silent default would be the read path assigning
# a verification meaning, which is the line invariant 15 draws. The column's
# CHECK admits exactly these four values, so raising costs nothing.
#
# ``under-sourced`` is **not** a tier. Doc 08 §4.3 makes it a review-state
# overlay on a still-corroborated fact, so it rides through as a label and
# does not move the row; demoting it here would be recomputing a label.
#
# L0 sits at the bottom because doc 07 §5 puts it there: a verified fact
# outranks a raw candidate of equal query-relevance.
#
# ``disputed`` sits below ``candidate`` (ruled Tier-1, 2026-08-02). Doc 07 §5
# makes ``disputed`` a sub-state orthogonal to the three rungs rather than a
# fourth rung, so its sort position is unspecified rather than contradicted.
# Under-claiming is the corpus's posture, the cost is bounded because the row
# is still served labelled with both sides, and the natural alternative —
# retaining the pre-dispute rung — is unavailable to this layer: the prior
# rung is gone from the row, and reconstructing it would mean retrieval
# reading the verification journal to compute a label rather than read one.
TIER_BY_VERIFICATION_STATUS: dict[str, int] = {
    "confirmed": 4,
    "corroborated": 3,
    "candidate": 2,
    "disputed": 1,
}

MEMORY_TIER = 0


def tier_for(verification_status: str | None) -> int:
    """The ordering tier of one verification status.

    ``None`` is the memory layer, which carries a lifecycle status instead of
    a verification one and sits at :data:`MEMORY_TIER`.
    """
    if verification_status is None:
        return MEMORY_TIER
    try:
        return TIER_BY_VERIFICATION_STATUS[verification_status]
    except (KeyError, TypeError):
        raise ValueError(
            f"{verification_status!r} is not a verification status; the "
            f"composition orders {sorted(TIER_BY_VERIFICATION_STATUS)} and "
            "never invents a tier for a value it does not know"
        ) from None


def composition_key(id_kind: str, wire_id: str) -> str:
    """The merge key for one object in one space.

    Refuses a non-``str`` id rather than normalising one: normalisation
    belongs at admission (:func:`_admit_id`), where the id's space is still
    known, and spelling it twice would leave neither site independently
    breakable.
    """
    if id_kind not in ID_KINDS:
        raise ValueError(
            f"unknown id_kind {id_kind!r}; the composition vocabulary is closed "
            f"to {sorted(ID_KINDS)}"
        )
    if not isinstance(wire_id, str) or not wire_id:
        raise TypeError(
            f"composition_key needs a non-empty str id, got {wire_id!r} "
            f"({type(wire_id).__name__}); normalise at the adapter"
        )
    return f"{id_kind}:{wire_id}"


def cross_layer_rrf(channel_rank: int) -> float:
    """The channel-rank currency doc 07 §3 recognises across modalities.

    Derived from ``channel_rank`` alone and carried into the trace so the
    currency is visible; it is never an independent signal. ``RRF_K`` is
    imported rather than redeclared — ``code_query.py``'s private ``RRF_K``
    is the standing example of what a second declaration costs, and CLAUDE.md
    records that no task owns closing that drift.
    """
    return 1.0 / (RRF_K + channel_rank)


def _admit_id(raw: object) -> str:
    """Invariant 9's normalisation, spelled exactly once for all three adapters.

    A ``UUID`` and its ``str`` must mint the same key and merge into one row.
    CLAUDE.md puts that boundary at the merge; this puts it one step earlier,
    at admission, because here the id's own space is still known.
    """
    if raw is None:
        raise TypeError("a candidate row carries no id; the composition cannot key it")
    return str(raw)


def support_map(pairs: Iterable[tuple[object, object]]) -> dict[str, frozenset[str]]:
    """``(fact_id, memory_id)`` provenance pairs, in the composition's keyspace.

    The one place raw ``fact_sources`` identity becomes composition identity, so
    invariant 9's normalisation and the namespacing are each spelled once for
    the grouping pass. Keying this map on bare ids instead would reintroduce the
    exact drift :func:`composition_key` exists to close: the value side is
    matched against ``ComposedRow.key``, so a bare id matches nothing at all,
    and a fact and a memory that happen to share a UUID would collide into one
    entry the moment anything else keyed the same way.
    """
    out: dict[str, set[str]] = {}
    for fact_id, memory_id in pairs:
        fact_key = composition_key("fact", _admit_id(fact_id))
        out.setdefault(fact_key, set()).add(
            composition_key("memory", _admit_id(memory_id))
        )
    return {fact_key: frozenset(members) for fact_key, members in out.items()}


def _signals(row: Mapping) -> dict[str, float]:
    payload = row.get("payload")
    payload = payload if isinstance(payload, Mapping) else {}
    out: dict[str, float] = {}
    for name in SIGNAL_KEYS:
        value = row.get(name)
        if value is None:
            value = payload.get(name)
        if value is None:
            continue
        try:
            out[name] = float(value)
        except (TypeError, ValueError):
            continue
    return out


@dataclass(frozen=True)
class LayerCandidate:
    """One channel row admitted into the composition, in its own key space.

    The type itself is the first of the three mechanisms that make "code
    search cannot enter" an assertion rather than an omission: ``compose()``
    admits only these, and minting one goes through an adapter that knows the
    space. The raise matters more than the check — a live code row carries no
    ``id`` key at all, so an id-keyed merge would drop it *without a word* and
    its absence from the output would look exactly like correct behaviour.
    """

    id: str
    id_kind: str
    layer: str
    channel_rank: int
    row: Mapping[str, object]
    verification_status: str | None = None
    signals: Mapping[str, float] = field(default_factory=dict)
    row_context: RowContext | None = None
    key: str = field(init=False, default="")

    def __post_init__(self) -> None:
        if self.id_kind not in ID_KINDS:
            raise TypeError(
                f"{self.id_kind!r} is not a composition id_kind; the vocabulary "
                f"is closed to {sorted(ID_KINDS)}"
            )
        expected = LAYER_BY_ID_KIND[self.id_kind]
        if self.layer != expected:
            raise TypeError(
                f"id_kind {self.id_kind!r} belongs to layer {expected!r}, "
                f"not {self.layer!r}"
            )
        if not isinstance(self.channel_rank, int) or isinstance(self.channel_rank, bool):
            raise TypeError(f"channel_rank must be an int, got {self.channel_rank!r}")
        if self.channel_rank < 1:
            raise ValueError(f"channel_rank is 1-based, got {self.channel_rank}")
        object.__setattr__(self, "key", composition_key(self.id_kind, self.id))


def _triple(subject: object, rel_type: object, obj: object, ident: object) -> dict:
    """One claim, in the shape both sides of a dispute are rendered in."""
    return {
        "subject": subject,
        "rel_type": rel_type,
        "object": obj,
        "id": None if ident is None else str(ident),
    }


def dispute_label(row: Mapping, evidence: Mapping | None) -> dict | None:
    """A disputed fact's label, with both sides when the journal has both.

    Three shapes, and the three are distinguishable: ``None`` for a fact that
    is not disputed, a block naming the counterpart, and a block saying no
    finding was recorded. Collapsing the third into the first would make "we
    know of a contradiction but not which" read as "there is no contradiction".

    **Both sides are rendered in the same shape**, and neither is privileged
    by it. A rendering that flattened the counterpart to a string while
    keeping the fact's own triple structured would have silently picked a
    winner in the layout.

    ``enumeration`` is copied **verbatim** and never re-derived, and no count
    or total is emitted. The value exists to say the block names the
    counterpart the verdict turned on rather than every counterpart in the
    database; a ``contradiction_count`` beside it would let a renderer say
    "the only contradiction", which is the claim the value forbids.
    """
    if row.get("verification_status") != DISPUTED:
        return None

    claim = _triple(
        row.get("subject_name"),
        row.get("rel_type"),
        row.get("object_name"),
        row.get("fact_id") if row.get("fact_id") is not None else row.get("id"),
    )
    payload = (evidence or {}).get("payload")
    block = payload.get(CONTRADICTION_EVIDENCE_KEY) if isinstance(payload, Mapping) else None

    if not isinstance(block, Mapping):
        return {
            "review_state": row.get("review_state"),
            "claim": claim,
            "counterpart": None,
            "counterpart_absent": COUNTERPART_ABSENT_NO_FINDING,
        }

    return {
        "review_state": row.get("review_state"),
        "claim": claim,
        "counterpart": _triple(
            block.get("counterpart_subject"),
            block.get("counterpart_rel_type"),
            block.get("counterpart_object"),
            block.get("counterpart_id"),
        ),
        "rule": block.get("rule"),
        "witness_origin": block.get("witness_origin"),
        "enumeration": block.get("enumeration"),
    }


def memory_candidate(row: Mapping, *, channel_rank: int) -> LayerCandidate:
    """An L0 row from the memory hybrid.

    ``verification_status`` is ``None`` and is **not** read off the row. A
    memory carries a lifecycle ``status`` (``scope_labels`` stamps one on
    every hybrid row), which is a different vocabulary entirely; feeding it to
    the tier lookup would raise on every memory in the corpus.
    """
    return LayerCandidate(
        id=_admit_id(row.get("memory_id") if row.get("memory_id") is not None else row.get("id")),
        id_kind="memory",
        layer=LAYER_BY_ID_KIND["memory"],
        channel_rank=channel_rank,
        row=row,
        verification_status=None,
        signals=_signals(row),
        row_context=row_context_from_applies_when(row.get("applies_when")),
    )


def fact_candidate(row: Mapping, *, channel_rank: int) -> LayerCandidate:
    """An L2 row from the facts channel."""
    return LayerCandidate(
        id=_admit_id(row.get("fact_id") if row.get("fact_id") is not None else row.get("id")),
        id_kind="fact",
        layer=LAYER_BY_ID_KIND["fact"],
        channel_rank=channel_rank,
        row=row,
        verification_status=row.get("verification_status"),
        signals=_signals(row),
        row_context=row_context_from_applies_when(row.get("applies_when")),
    )


def article_candidate(row: Mapping, *, channel_rank: int) -> LayerCandidate:
    """An L3 row from the articles channel, whose producer is T3.02's.

    Built ahead of its channel because it is what makes the vocabulary a real
    closed vocabulary rather than a string set, and because it supplies the
    one cross-channel fixture where key-alphabetical order disagrees with
    tier order — see the ordering test.
    """
    return LayerCandidate(
        id=_admit_id(row.get("article_id") if row.get("article_id") is not None else row.get("id")),
        id_kind="article",
        layer=LAYER_BY_ID_KIND["article"],
        channel_rank=channel_rank,
        row=row,
        verification_status=row.get("verification_status"),
        signals=_signals(row),
        row_context=row_context_from_applies_when(row.get("applies_when")),
    )


def _labels(candidate: LayerCandidate) -> dict:
    """The labels a composed row carries about its own scope and belief.

    Read off the producer's row, never computed. ``review_state`` rides
    through on a fact for exactly the reason it does not move it: doc 08
    §4.3's under-sourced overlay is a label a consumer may render, not a rung
    this layer may re-derive.
    """
    row = candidate.row
    labels: dict = {"project": row.get("project")}
    if candidate.id_kind == "memory":
        labels["status"] = row.get("status")
    else:
        labels["verification_status"] = candidate.verification_status
        labels["review_state"] = row.get("review_state")
    return labels


def _badge_labels(candidate: LayerCandidate, badges: Mapping[str, Badge]) -> dict:
    """Doc 12 §4's ``{verification_status, lifecycle, badge}`` triplet.

    Emitted **whole, by the producer** — :func:`fact_badge.row_labels` — and
    never assembled here. That is what makes the L0 rule structural rather
    than repeated: the producer refuses a badge on a memory row and refuses a
    lifecycle on a vault row, so a composition that got either backwards
    raises instead of serving a mislabelled row. Splitting the triplet across
    two sites would give this module a second opinion about which rows are
    adjudicated.

    Nothing about the badge is recomputed and no part of the claim sentence is
    spelled in this file. The badge arrives built, from the one module that
    reads the rows the ladder wrote and journalled (invariant 15).

    **A badge-bearing row missing from a lookup that ran raises.** Doc 12
    fixes the badge as present on every L2/L3 row, so ``badge: null`` there is
    not a degradation the wire can express — it reads exactly like the L0
    rule firing on a row the L0 rule does not govern, which is the unlabelled
    fact this whole map exists to make unservable. An article reaching here
    raises for the same reason and by the same line: its channel is
    ``ARTICLE_CHANNEL_OWNER``'s, and whoever ships it owes the badge lookup
    the same way the facts channel does.
    """
    if candidate.id_kind == "memory":
        return row_labels(
            id_kind=candidate.id_kind,
            lifecycle=candidate.row.get("status"),
            badge=badges.get(candidate.key),
        )
    badge = badges.get(candidate.key)
    if badge is None:
        raise ValueError(
            f"the badge lookup ran and produced none for {candidate.key}; doc "
            "12 fixes the badge as present on every L2/L3 row, so serving this "
            "one unlabelled would under-report what is known about the claim"
        )
    return row_labels(
        id_kind=candidate.id_kind,
        verification_status=candidate.verification_status,
        badge=badge,
    )


@dataclass(frozen=True)
class ComposedRow:
    """One served row, labelled with where it came from and how it ranked.

    Carries **both** key spellings on purpose: ``key`` is the internal
    namespaced merge key, and ``id`` + ``id_kind`` are doc 07 §8's wire pair,
    so a client is handed a bare id it can look up. ``key ==
    f"{id_kind}:{id}"`` always.

    ``grouping`` is doc 12's ``{grouped_under, relation}`` object, and its
    **presence is the evidence that the grouping pass ran**. ``None`` means
    :func:`compose` was handed no provenance, so nothing was grouped and
    nothing could have been; ``{grouped_under: None, relation: None}`` means
    the pass ran and this row is nested under nothing. Collapsing the two would
    let a caller that never looked up provenance read exactly like one that
    looked and found none.

    ``supported_by`` carries the nested evidence, and carries it **whole**: a
    nested row is the identical ``ComposedRow`` it would have been at the top
    level, scores included, because doc 07 §5 requires a grouped memory to keep
    its own rrf/rerank scores in the trace. Nothing about the enclosing row
    moves in response — the group's rank is the fact's rank.
    """

    key: str
    id: str
    id_kind: str
    layer: str
    channel_rank: int
    verification_status: str | None
    tier: int
    band: int
    cross_layer_rrf: float
    rank_fusion_factor: float
    weighted_score: float
    context: ContextOutcome
    labels: Mapping[str, object]
    dispute: Mapping[str, object] | None
    row: Mapping[str, object]
    grouping: Mapping[str, object] | None = None
    supported_by: tuple["ComposedRow", ...] = ()


@dataclass(frozen=True)
class CompositionResult:
    """``compose()``'s ordered output plus the counts the envelope owes.

    ``excluded_by_context_conflict`` is doc 07 §8's ``by_context_conflict``
    and is reported unconditionally, including when it is zero — a suppressed
    count hides exactly the case a reader needs.

    ``rows`` is the **top level only** once grouping has run: a nested memory
    lives under its fact and nowhere else, so ``len(rows)`` counts a group as
    one. Every count a consumer takes off this list — the answer budget
    included — inherits that, which is the whole of the no-triple-count rule.

    ``excluded_by_result_limit`` is the answer budget's own tally and it is
    **counted from the served output, not from the arithmetic**: it is the
    number of composed rows reachable nowhere in ``rows``, neither as a
    top-level row nor nested under one. Deriving it as "rows minus limit"
    would have re-stated the assumption rather than measured it, and the
    assumption is exactly what T2.70 found to be false. It counts rows this
    request ordered and did not serve; it is **not** a count of further
    matches in the corpus, because each channel fetched at most ``limit`` of
    its own and nothing looked past that.
    """

    rows: list[ComposedRow]
    excluded_by_context_conflict: int = 0
    excluded_by_result_limit: int = 0
    reranked: bool = False
    grouped: bool = False
    badged: bool = False


def _rerank_bands(
    keys: list[str], rerank_scores: Mapping[str, float]
) -> dict[str, int]:
    """Dense rank over the rerank score, with one terminal band for the tail.

    A key **missing** from the mapping is a row the model never saw, and it
    lands below every scored band — including a genuine ``0.0``. The two are
    different facts about the world, and collapsing them would let a bounded
    budget masquerade as a verdict. ``RerankerService`` itself conflates them
    (it stamps its unscored tail ``0.0``), which is exactly why the mapping
    handed here is sliced by the caller rather than read off that return.
    """
    scored = {key: float(rerank_scores[key]) for key in keys if key in rerank_scores}
    distinct = sorted(set(scored.values()), reverse=True)
    dense = {value: position for position, value in enumerate(distinct, start=1)}
    terminal = len(distinct) + 1
    return {
        key: dense[scored[key]] if key in scored else terminal for key in keys
    }


def _reband_within_channels(rows: list[ComposedRow]) -> list[ComposedRow]:
    """Re-rank each channel by its own weighted score and re-derive the band.

    This is where the deterministic multipliers get **rank authority rather
    than score authority**. A band is unique within a channel, so a
    ``(band, tier)`` cell holds at most one row per channel — a per-row scalar
    sitting *beside* the band could therefore never move a row past a
    same-channel neighbour at any magnitude, which would leave every arm and
    the context boost order-inert on the default path and repeal doc 07 §6's
    rank boost. Re-ranking the channel by the weighted score implements the
    word §6 actually uses.

    The re-rank happens **inside one channel**, where the magnitudes are
    commensurable; the cross-channel comparison stays rank and only rank. Gaps
    left by an exclusion close here, so a channel that lost its rank-2 row
    does not leave a hole. The sort is **stable on the channel's prior
    order**, so rows with equal weighted scores — every row at the no-op
    default — keep the order their channel's own fusion gave them.
    """
    out: list[ComposedRow] = []
    by_channel: dict[str, list[ComposedRow]] = {}
    for row in rows:
        by_channel.setdefault(row.id_kind, []).append(row)
    for group in by_channel.values():
        ordered = sorted(group, key=lambda r: r.channel_rank)
        ordered = sorted(ordered, key=lambda r: -r.weighted_score)
        out.extend(
            replace(row, band=position) for position, row in enumerate(ordered, start=1)
        )
    return out


def _grouping(fact_id: str | None) -> dict:
    """Doc 12's ``grouping`` object, in the one shape both cases share.

    The two fields move together by construction: a row nested under a fact
    always names the relation, and a row nested under nothing never does. Split
    across two spellings they could drift into ``{grouped_under: None,
    relation: "supports fact F"}``, which asserts a support with no supported
    object.
    """
    return {
        "grouped_under": fact_id,
        "relation": SUPPORTS_FACT_RELATION if fact_id is not None else None,
    }


def _group_under_fact(
    rows: list[ComposedRow],
    support: Mapping[str, frozenset[str]],
    nestable_facts: frozenset[str],
) -> list[ComposedRow]:
    """Doc 07 §5 step 5 — nest each returned memory under the fact it sources.

    Four properties, and each of them is the no-triple-count rule seen from a
    different side.

    *A nested row leaves the top level entirely.* Keeping it in both places is
    the triple count with an indent: every count taken off the returned list
    would still see three hits where the system has one claim, and the answer
    budget would spend three slots on it.

    *Nothing about the enclosing fact moves.* Its band, tier and weighted score
    are the group's, unchanged. The nested rows keep their own scores for the
    trace and those scores are never summed, averaged or folded in — evidence
    re-entering the ranking through the row it is nested under would be counted
    twice by arithmetic rather than by row, which is the same inflation in a
    place no row count can see.

    *The nesting is scoped to what is being served.* A memory whose fact is
    absent from ``rows`` stays a top-level row, because nesting it under a fact
    the caller was never handed would remove it from view altogether. The same
    test is what makes a dangling ``source_ref`` inert rather than
    special-cased: ``fact_sources`` has no FK to ``memories``, so a ref naming a
    deleted memory is representable, and it simply matches no returned row.
    ``nestable_facts`` narrows "handed to the caller" from "in ``rows``" to
    "inside the answer budget" — being composed is not being returned, and
    :func:`_grouped_page` owns deciding which facts pass that second test.

    *A memory sourcing two returned facts nests once, under the higher-ranked
    one.* Splitting it across both would restore exactly the duplication the
    pass exists to remove, and the position tie-break keeps the choice
    deterministic rather than dictionary-ordered.

    **Only an L0 row may be nested, and that is checked here rather than
    assumed.** ``add_source`` already refuses a derived ``source_kind`` — a
    fact or an article re-asserting a claim must not inflate the very fact it
    cites — and :func:`support_map` can only mint ``memory:`` on the value
    side. Both of those sit upstream, so neither survives a caller assembling
    a map by hand. Nesting an article would remove an L3 row from the top level
    on the strength of provenance that cannot exist, so the last line of
    defence is spelled where the removal happens.
    """
    position = {row.key: index for index, row in enumerate(rows)}
    by_key = {row.key: row for row in rows}
    facts = {row.key for row in rows if row.id_kind == "fact"} & nestable_facts
    nestable = {row.key for row in rows if row.id_kind == "memory"}

    nest_under: dict[str, str] = {}
    for fact_key, memory_keys in support.items():
        if fact_key not in facts:
            continue
        for memory_key in memory_keys:
            if memory_key not in nestable:
                continue
            incumbent = nest_under.get(memory_key)
            if incumbent is None or position[fact_key] < position[incumbent]:
                nest_under[memory_key] = fact_key

    nested: dict[str, list[ComposedRow]] = {}
    for row in rows:
        fact_key = nest_under.get(row.key)
        if fact_key is None:
            continue
        nested.setdefault(fact_key, []).append(
            replace(row, grouping=_grouping(by_key[fact_key].id))
        )

    return [
        replace(row, grouping=_grouping(None), supported_by=tuple(nested.get(row.key, ())))
        for row in rows
        if row.key not in nest_under
    ]


def _grouped_page(
    rows: list[ComposedRow],
    support: Mapping[str, frozenset[str]],
    limit: int | None,
) -> list[ComposedRow]:
    """Doc 07 §5's grouping and the answer budget, settled together (T2.70).

    These are not two passes that can be run in sequence. Doc 07 §5's own
    predicate is "a memory covered by a **returned** cited fact", so the cut
    decides who may be nested under; and nesting decides how many top-level
    rows precede each fact, so it decides what the cut reaches. Grouping first
    and cutting afterwards is what let a memory that ranked above the cut leave
    the result under a fact that fell below it — served nowhere, counted
    nowhere.

    **The rule: nest only under a fact that survives the cut, at the fixpoint
    of that rule.** Write ``F(S)`` for the set of facts left inside the cut
    when only the facts in ``S`` may be nested under. Iterate ``S₀ = every
    fact in the ordering``, ``Sₙ₊₁ = F(Sₙ)``, and serve the page of the first
    ``S`` with ``F(S) = S``.

    **Why it terminates.** Shrinking ``S`` can only *un*-nest memories, never
    nest new ones, so the top-level list grows and no row's position in it can
    move earlier; a fact inside the cut under the smaller ``S`` was therefore
    inside it under the larger one. That makes ``F`` monotone. ``S₁ = F(S₀) ⊆
    S₀`` because ``S₀`` is everything, and monotonicity carries ``Sₙ₊₁ ⊆ Sₙ``
    by induction — a chain that strictly shrinks until it settles, over a
    finite set, so it settles within one iteration per fact. That is not
    trusted: a step that does not shrink ``S`` raises rather than spinning, so a
    later change to the nesting rule that broke monotonicity would fail loudly
    instead of hanging the read path. The loop's own bound is a second raise
    behind that one, and it is unreachable while the shrink check stands — a
    strictly shrinking chain of subsets of ``facts`` runs at most
    ``len(facts)+1`` steps and the loop allows one more. It is a backstop
    against that check being deleted, not the argument for termination.

    **Why iteration rather than the two alternatives.** *Over-fetching a
    bounded window before grouping* does not address this at all — it changes
    which rows exist, not whether a nested memory's fact survives the cut, so
    the same loss reappears at the new depth and the bound's exhaustion is
    silent. *Nesting only within a prefix known to survive* (the first
    ``limit`` rows of the ungrouped order, whose positions can only improve) is
    sound and single-pass, but it under-nests: it refuses a fact that the cut
    does in fact reach, and then serves that fact beside its own source memory
    as two top-level rows — the triple count this pass exists to remove. The
    descending iteration lands on the **greatest** consistent ``S``, so it
    nests as much as the budget allows and no such pair can be served.

    At the fixpoint every nesting target is inside the served window, so the
    only rows that leave are the top-level tail — which :func:`compose` counts
    off the served output for the envelope.
    """
    facts = frozenset(row.key for row in rows if row.id_kind == "fact")
    if limit is None:
        return _group_under_fact(rows, support, facts)

    allowed = facts
    for _ in range(len(facts) + 2):
        page = _group_under_fact(rows, support, allowed)[:limit]
        surviving = frozenset(row.key for row in page if row.id_kind == "fact")
        if surviving == allowed:
            return page
        if not surviving < allowed:
            raise RuntimeError(
                "the grouping fixpoint stopped decreasing: restricting the "
                f"nestable facts to {sorted(allowed)} left {sorted(surviving)} "
                "inside the cut, so the step is not monotone and the iteration "
                "has no termination argument"
            )
        allowed = surviving
    raise RuntimeError(
        f"the grouping fixpoint did not settle over {len(facts)} facts; the "
        "iteration is bounded rather than trusted, so this is a broken nesting "
        "rule and not a slow page"
    )


def compose(
    candidates,
    *,
    weights: Mapping[str, object] | None = None,
    declared_context: DeclaredContext | None = None,
    evidence: Mapping[str, Mapping] | None = None,
    rerank_scores: Mapping[str, float] | None = None,
    fact_sources: Mapping[str, frozenset[str]] | None = None,
    badges: Mapping[str, Badge] | None = None,
    limit: int | None = None,
) -> CompositionResult:
    """Doc 07 §5 steps 1 to 5, as a pure function.

    No session, no clock, no LLM — the same split the verification ladder
    keeps between its decision and its applier, and for the same reason: it
    makes every ordering, tier and keyspace property a fast test that can be
    mutated cheaply and often.

    **``fact_sources`` is a tri-state, exactly as ``rerank_scores`` is.**
    ``None`` says no provenance was looked up, so step 5 does not run and no
    row carries a ``grouping`` key; a mapping — **including an empty one** —
    says the lookup ran, so every row carries the key and an empty mapping
    honestly reports that nothing was found to group. A default that grouped
    unconditionally would make "never asked" indistinguishable from "asked and
    found none", which is the same collapse the terminal rerank band exists to
    prevent.

    **``badges`` is the same tri-state, and keyed the same way as the rows.**
    ``None`` says no badge lookup ran, so no row carries doc 12's label
    triplet at all; a mapping says it ran, so every row carries it and every
    badge-bearing row carries a real badge or the composition raises. The
    absent key is what keeps "never asked" distinguishable from "asked and
    the fact is unlabelled" — and the second of those is unservable, so it is
    a raise rather than a shape. The mapping is keyed by
    :func:`composition_key`, not by the bare fact id ``badges_for_facts``
    returns: a fact and an article sharing a UUID would otherwise trade
    badges, and this map is the one place the badge and the row are joined.

    **The order is ascending on ``(band, -tier, key)``.** ``key`` is the sole
    tie-break because it is input-independent: an insertion-order tie-break
    would make the served order depend on the order a caller happened to list
    its channels. A weighted score is deliberately *not* a sort term —
    comparing two channels' weighted magnitudes directly is the
    cross-modality comparison doc 07 §3 rejects.

    **Nothing is dropped for its verification status.** An all-``candidate``
    input composes to a full, labelled result, which is the floor T2.56's
    cold start inherits rather than a rule it has to unpick.

    **``limit`` is the caller's answer budget, and it is applied here rather
    than by the caller** (T2.70). It has to be: the cut and the grouping pass
    decide each other (:func:`_grouped_page`), so a caller slicing the returned
    list would be running the second half of one decision against a first half
    that never knew about it. ``None`` means no budget, every fact may be
    nested under, and nothing is cut.
    """
    weights = weights or {}
    evidence = evidence or {}
    candidates = list(candidates)

    for candidate in candidates:
        if not isinstance(candidate, LayerCandidate):
            raise TypeError(
                "compose() admits only LayerCandidate, minted by "
                "memory_candidate() / fact_candidate() / article_candidate(); "
                f"got {type(candidate).__name__}: {candidate!r}"
            )

    duplicated = sorted(
        key for key, count in Counter(c.key for c in candidates).items() if count > 1
    )
    if duplicated:
        raise ValueError(
            f"two candidates share the composition key(s) {duplicated}; a key "
            "names one object in one space, and the grouping map keys on it"
        )

    # The context map is keyed by the **namespaced** key, which is why
    # ``rank_fusion.partition_by_context`` cannot be reused here: it looks a
    # row's context up through ``normalize_row_id``, the bare-id key, so
    # handed cross-layer rows it would resolve a fact's context from a
    # memory's entry the moment the two ids coincided.
    row_contexts = {candidate.key: candidate.row_context for candidate in candidates}

    kept: list[tuple[LayerCandidate, ContextOutcome]] = []
    excluded_by_context_conflict = 0
    for candidate in candidates:
        outcome = match_context(declared_context, row_contexts.get(candidate.key), weights)
        if outcome.excluded:
            excluded_by_context_conflict += 1
            continue
        kept.append((candidate, outcome))

    rows: list[ComposedRow] = []
    for candidate, outcome in kept:
        factor = rank_fusion_factor(candidate.signals, weights)
        base = CHANNEL_LIST_WEIGHTS[candidate.id_kind] * cross_layer_rrf(candidate.channel_rank)
        rows.append(
            ComposedRow(
                key=candidate.key,
                id=candidate.id,
                id_kind=candidate.id_kind,
                layer=candidate.layer,
                channel_rank=candidate.channel_rank,
                verification_status=candidate.verification_status,
                tier=tier_for(candidate.verification_status),
                band=candidate.channel_rank,
                cross_layer_rrf=cross_layer_rrf(candidate.channel_rank),
                rank_fusion_factor=factor,
                # The boost is read off the stamped outcome and folded in
                # here, once. ``rank_fusion.apply_context_boost`` is not
                # called: it would multiply the same boost in a second time,
                # and it sorts on ``rrf_score``/``score``, keys this module
                # does not order by.
                weighted_score=base * factor * outcome.boost,
                context=outcome,
                labels=(
                    _labels(candidate)
                    if badges is None
                    else {**_labels(candidate), **_badge_labels(candidate, badges)}
                ),
                dispute=(
                    dispute_label(candidate.row, evidence.get(candidate.id))
                    if candidate.id_kind != "memory"
                    else None
                ),
                row=candidate.row,
            )
        )

    # The authoritative relevance signal is chosen **once per request**,
    # never per row: that single choice is what keeps the comparator a strict
    # weak ordering, so two rows in one response are never compared under
    # different signals.
    reranked = rerank_scores is not None
    if reranked:
        bands = _rerank_bands([row.key for row in rows], rerank_scores)
        rows = [replace(row, band=bands[row.key]) for row in rows]
    else:
        rows = _reband_within_channels(rows)

    # Step 5 is last, and last after the rerank specifically (doc 07 §11,
    # resolved). It reads the finished order rather than producing one: a
    # nested row keeps the band the rerank gave it, and the gaps grouping
    # leaves in the top-level bands are not closed, because renumbering the
    # survivors would be evidence re-entering the ranking it was just removed
    # from.
    ordered = sorted(rows, key=lambda r: (r.band, -r.tier, r.key))
    grouped = fact_sources is not None
    if grouped:
        ordered = _grouped_page(ordered, fact_sources, limit)
    elif limit is not None:
        ordered = ordered[:limit]

    # Counted off what is actually reachable in the output, top level and
    # nested, rather than derived from ``len`` arithmetic: the arithmetic
    # encodes the belief that nesting and the cut compose cleanly, which is the
    # belief T2.70 found to be false. Measuring the served set instead means a
    # future regression in the fixpoint shows up as a number the envelope
    # already carries rather than as rows nobody counts.
    served = {row.key for row in ordered}
    served |= {nested.key for row in ordered for nested in row.supported_by}

    return CompositionResult(
        rows=ordered,
        excluded_by_context_conflict=excluded_by_context_conflict,
        excluded_by_result_limit=len(rows) - len(served),
        reranked=reranked,
        grouped=grouped,
        badged=badges is not None,
    )


# ─────────────────── the impure half: one entry point ───────────────────

# The task that ships the article channel's producer, carried as a value the
# way ``RankArm.activation`` names an arm's activation task, so an envelope
# reporting a channel that never ran can never be mistaken for one that did.
ARTICLE_CHANNEL_OWNER = "T3.02"

# How many of the surviving, provisionally-ordered rows the reranker sees.
RERANK_WINDOW = 40

# The key the composition stamps on a document handed to the reranker, so the
# returned scores can be mapped back to composition keys rather than to
# whatever id the producer's row happened to carry.
RERANK_KEY_FIELD = "_composition_key"

# Where each layer keeps the text a reranker must actually read. A **closed
# dispatch**, not a fall-through chain, because the fall-through is what fails
# silently: ``RerankerService`` resolves ``content`` then ``payload.content``
# then ``chunk_content``, and a fact's text lives under ``fact``, so a fact
# reaching it unnormalised is scored against an empty string. The model then
# returns a real number rather than a zero, so neither the all-zero guard nor
# the terminal band can see it, and the band recompute re-ranks verified facts
# on noise while the envelope reports ``reranked`` as if the signal were
# sound. An id_kind this table does not know **raises**, for the same reason
# the tier lookup does: a layer added without teaching the resolver its text
# field would otherwise be scored on nothing at all.
RERANK_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "memory": ("content",),
    "fact": ("fact",),
    "article": ("content", "title"),
}


def rerank_document_text(row: ComposedRow) -> str:
    """The text a reranker scores this row against."""
    try:
        fields = RERANK_TEXT_FIELDS[row.id_kind]
    except KeyError:
        raise ValueError(
            f"no rerank text field is known for id_kind {row.id_kind!r}; "
            "a layer must name where its servable text lives before it can "
            "be reranked, or it is scored against an empty document"
        ) from None
    payload = row.row.get("payload")
    payload = payload if isinstance(payload, Mapping) else {}
    for name in fields:
        value = row.row.get(name)
        if value is None:
            value = payload.get(name)
        if value:
            return str(value)
    return ""


@dataclass(frozen=True)
class ComposedResult:
    """The single entry point's return: an ordered list and its envelope."""

    rows: list[ComposedRow]
    envelope: RetrievalEnvelope


def _namespaced(prefix: str, statuses: Mapping[str, ChannelStatus]) -> dict:
    """One channel's arm statuses, qualified by the layer that owns them.

    ``RetrievalEnvelope.channels`` is flat and the memory hybrid already
    populates ``keyword`` and ``semantic`` in it, so merging the facts
    channel's unqualified keys straight in overwrites the memory channel's
    entries — and a memory keyword outage then disappears from the envelope's
    ``partial`` flag, which is ``any(channel.failed …)``. That is a silent
    degradation of the no-silent-degradation flag itself.
    """
    return {f"{prefix}.{arm}": status for arm, status in statuses.items()}


class LayerCompositionService:
    """The impure half: run the channels, read the journal, assemble the envelope.

    ``compose()`` is pure — no session, no clock, no LLM — and this is
    everything that is not. The split is ``verification_ladder``'s own, kept
    for the same reason: it makes every ordering, tier and keyspace property a
    fast test that can be mutated cheaply.

    :meth:`search` is the single entry point T2.58 converges Chat onto. It is
    not Chat-aware. MCP's ``knowledge_search`` spends it today (T2.72); T2.56
    and T2.58 are the remaining consumers. **No caller constructs this with a
    ``reranker``**, so :meth:`derive_rerank_scores` returns before it looks at
    a row — which is why the empty-text raise in it is a guard against a
    future caller rather than a live path.

    **It deliberately takes no ``with_trace``**, which is a correction to the
    seam rather than an omission. On ``memory.py`` that flag chooses between
    two parallel paths and the off position returns no envelope at all. Here
    the envelope carries ``partial`` and doc 07 §8's unconditional
    ``by_context_conflict`` tally, so an off position would either return a
    result whose degradation cannot be seen — the one thing invariant 14
    forbids — or be a knob with no observable effect. Neither is worth
    shipping for symmetry with a method whose analogy does not hold, so
    T2.58 inherits this signature without the flag.
    """

    def __init__(self, llm, session: AsyncSession, *, reranker=None):
        self.llm = llm
        self.session = session
        self.reranker = reranker

    async def derive_rerank_scores(
        self, query: str, rows: list[ComposedRow]
    ) -> dict[str, float] | None:
        """The rerank mapping, over a window this module slices itself.

        Derived naively from ``RerankerService.rerank``'s return, no key could
        ever be missing: it stamps its own unscored tail through
        ``setdefault(…, 0.0)``, which is exactly the collapse of "never asked"
        into "rated 0" that the terminal band exists to prevent. It also
        truncates to ``top_k`` (defaulting to 10), which would silently drop
        rows and contradict the guarantee that nothing is dropped.

        So both bounds are pinned. ``top_k=len(window)`` makes the truncation
        a no-op. ``max_candidates=len(window)`` makes the reranker's **own**
        head the whole window: without it the tail is empty only because
        ``RERANK_WINDOW`` happens to equal that parameter's default, and
        raising the window would quietly let ``setdefault`` zeros into the
        mapping as scored rows while every length assertion still passed.

        A mapping that is empty, or all-zero, is **no usable signal**. The
        reranker's outer failure handler stamps every document ``0.0`` and
        returns them in input order, which is indistinguishable from a model
        that rated everything 0; serving that as a rerank would collapse the
        whole window into one band ordered by tier alone — a large silent
        behaviour change out of an outage.

        **A row with no text raises here rather than being logged past**
        (T2.81). The producer refuses an empty document (T2.69), so passing one
        through was a warning that promised a scoring that could not happen;
        the two had to move together, and the raise names the composed row
        instead of the producer's contract.
        """
        if self.reranker is None:
            return None
        window = list(rows)[:RERANK_WINDOW]
        if not window:
            return None

        documents = []
        for row in window:
            document_text = rerank_document_text(row)
            if not document_text:
                # Not a warning-and-carry-on. ``RerankerService`` refuses an
                # empty document rather than scoring one (T2.69), so passing
                # this through would raise a few lines later from inside the
                # producer, naming the producer's contract instead of the row
                # that broke it. Raising here says which composed row carries
                # no text, which is the only question a reader has.
                raise ValueError(
                    f"{row.key} resolves to no text under "
                    f"{RERANK_TEXT_FIELDS[row.id_kind]}, so it cannot be "
                    "reranked; a row is never scored against an empty document"
                )
            documents.append(
                {**dict(row.row), "content": document_text, RERANK_KEY_FIELD: row.key}
            )
        scored = await self.reranker.rerank(
            query,
            documents,
            top_k=len(window),
            max_candidates=len(window),
        )
        if len(scored) != len(window):
            raise RuntimeError(
                f"the reranker returned {len(scored)} rows for a window of "
                f"{len(window)}; the window must survive intact"
            )

        scores = {
            document[RERANK_KEY_FIELD]: float(document["rerank_score"])
            for document in scored
        }
        if not scores:
            return None
        if all(value == 0.0 for value in scores.values()):
            return None
        return scores

    async def derive_badges(
        self, candidates: list[LayerCandidate]
    ) -> dict[str, Badge]:
        """Doc 12's badge for every badge-bearing candidate, in the row keyspace.

        **Batched for the whole page, never per row.** ``badges_for_facts``
        owns that batching and its query count is fixed at three however long
        the page is; calling it once per fact would put the provenance profile,
        the journal read and the counterpart profiles behind every fact a query
        returns, on the hot read path.

        The row handed to the producer carries the **composition's** id rather
        than whatever spelling the channel put in ``id``, so the badge that
        comes back cannot belong to a different row than the key it is filed
        under. ``fact_candidate`` prefers ``fact_id`` and ``badges_for_facts``
        keys on ``id``; two spellings joined by hand is how a page ends up
        one badge short and silently unlabelled.

        Articles carry a badge too (doc 12 §4), and this returns none for them:
        their channel is ``ARTICLE_CHANNEL_OWNER``'s and nothing mints an L3
        candidate here yet. That is deliberately a raise in :func:`compose`
        rather than a shrug — an article served with ``badge: null`` would
        assert the L0 rule about a row the L0 rule does not govern.
        """
        facts = [c for c in candidates if c.id_kind == "fact"]
        if not facts:
            return {}
        rows = [{**dict(c.row), "id": c.id} for c in facts]
        badges = await badges_for_facts(self.session, rows)
        return {c.key: badges[c.id] for c in facts}

    async def derive_support_map(
        self, fact_ids: list[str]
    ) -> dict[str, frozenset[str]]:
        """Step 5's input: which memories source each fact in this result set.

        **One bounded lookup for the whole set**, never one per returned fact —
        a per-fact call would put a round trip behind every fact a query
        returns, on the hot read path.

        ``fact_sources`` is the sole authority (doc 07 §5, doc 04 §8.3). Nothing
        here derives support from text overlap, embedding proximity or a shared
        entity: those resemble support without asserting it, and a wrongly
        nested row is a row removed from view rather than merely mislabelled.

        An empty mapping is a real answer and is returned as one — the lookup
        ran and this result set has no provenance to group on.
        """
        if not fact_ids:
            return {}
        refs = await FactSourceRepository(self.session).memory_refs_for_facts(fact_ids)
        return support_map(
            (fact_id, ref) for fact_id, group in refs.items() for ref in group
        )

    async def search(
        self,
        query: str,
        *,
        project: str,
        limit: int = 20,
        declared_context: DeclaredContext | None = None,
        weights: Mapping[str, object] | None = None,
    ) -> ComposedResult:
        if weights is None:
            weights = await get_feature_flags_dict(self.session)

        channels: dict[str, ChannelStatus] = {}
        candidates: list[LayerCandidate] = []

        memory_failed = False
        try:
            memory_trace = await HybridSearchService(self.llm, self.session).search_with_trace(
                query, limit=limit, filters=MemoryFilter(project=project),
            )
        except Exception:
            logger.error("Layer composition: the memory channel failed outright")
            memory_failed = True
            channels.update(
                _namespaced("memory", {
                    "semantic": ChannelStatus(ran=True, failed=True),
                    "keyword": ChannelStatus(ran=True, failed=True),
                })
            )
        else:
            channels.update(
                _namespaced("memory", {
                    "semantic": ChannelStatus(ran=True, failed=memory_trace.semantic_failed),
                    "keyword": ChannelStatus(ran=True, failed=memory_trace.keyword_failed),
                })
            )
            candidates.extend(
                memory_candidate(row, channel_rank=rank)
                for rank, row in enumerate(memory_trace.results, start=1)
            )

        fact_failed = False
        try:
            fact_trace = await FactsChannel(self.session).search_with_trace(
                query, project=project, limit=limit,
            )
        except Exception:
            logger.error("Layer composition: the facts channel failed outright")
            fact_failed = True
            channels.update(
                _namespaced("fact", {
                    KEYWORD_ARM: ChannelStatus(ran=True, failed=True),
                    NAME_ARM: ChannelStatus(ran=True, failed=True),
                    SEMANTIC_ARM: ChannelStatus(ran=False),
                })
            )
        else:
            channels.update(_namespaced("fact", fact_trace.channel_status()))
            candidates.extend(
                fact_candidate(row, channel_rank=rank)
                for rank, row in enumerate(fact_trace.results, start=1)
            )

        # A one-sided outage degrades to the surviving layer and says so; both
        # sides down would make an empty result indistinguishable from a
        # genuine no-match, which is the one case invariant 14 forbids serving.
        if memory_failed and fact_failed:
            raise RuntimeError("Layer composition failed on both the memory and fact channels")

        # Present and ran=False, never omitted: an absent key makes "this layer
        # has no such modality" indistinguishable from "the composition never
        # asked", while marking a deferred writer failed would put it into
        # partial, which is a different lie.
        channels["article.semantic"] = ChannelStatus(ran=False)

        fact_ids = [c.id for c in candidates if c.id_kind == "fact"]
        evidence = await latest_verified_evidence(self.session, fact_ids)
        # Derived once and handed to both passes. The badge is a label and
        # never an ordering signal, so it cannot move a row between the
        # provisional pass and the final one; deriving it twice would only buy
        # a second round of the producer's queries.
        badges = await self.derive_badges(candidates)

        # The provisional pass is deliberately **ungrouped**, and that is what
        # implements doc 07 §11's resolved rerank-before-grouping order rather
        # than merely documenting it: the reranker is handed this list, so a
        # memory that will end up nested is still scored for query-relevance
        # here. Grouping it first would hide a highly-relevant supporting
        # memory from the model that was supposed to rate it, and the trace
        # would then carry a nested row with no rerank verdict at all.
        provisional = compose(
            candidates,
            weights=weights,
            declared_context=declared_context,
            evidence=evidence,
            badges=badges,
        )
        rerank_scores = await self.derive_rerank_scores(query, provisional.rows)
        result = compose(
            candidates,
            weights=weights,
            declared_context=declared_context,
            evidence=evidence,
            rerank_scores=rerank_scores,
            fact_sources=await self.derive_support_map(fact_ids),
            badges=badges,
            # Each channel fetches up to ``limit`` of its own, so the union is
            # up to one limit per layer. ``limit`` is the caller's answer
            # budget, not a per-channel quota, so the composed order is cut —
            # after the ordering, by rank, never by label. Nothing is dropped
            # for its verification status; this drops the tail of a total
            # order.
            #
            # The cut is **handed to compose() rather than applied to its
            # return** (T2.70). It spends the budget on ``limit`` distinct
            # claims rather than on ``limit`` rows that may restate one, and
            # grouping is scoped to the facts that budget actually reaches, so
            # a memory ranked above the cut is never carried out of the result
            # by a fact ranked below it. Slicing here instead would put the two
            # halves of that one decision in two places again.
            limit=limit,
        )

        envelope = RetrievalEnvelope(
            query=query,
            channels=channels,
            reranked=result.reranked,
            weights={
                key: float(value)
                for key, value in weights.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            },
            # Both tallies unconditionally, including at zero. ``by_result_limit``
            # is the answer budget's own: the number of rows this request
            # composed, ordered and then did not serve anywhere. It is bounded
            # by the over-fetch and says nothing about how many further matches
            # the corpus holds — no channel looked past its own ``limit``.
            excluded={
                "by_context_conflict": result.excluded_by_context_conflict,
                "by_result_limit": result.excluded_by_result_limit,
            },
        )
        return ComposedResult(rows=result.rows, envelope=envelope)
