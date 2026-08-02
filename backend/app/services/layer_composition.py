"""Doc 07 §5's four-layer composition — steps 1 to 4 (T2.43).

One ordered, total, deterministic list of rows drawn from more than one
epistemic layer, each labelled with where it came from and how well it is
believed. Steps 1 to 4 live here: merge the channel lists in their own key
spaces, label and order them, optionally re-band by a rerank, and apply the
deterministic multipliers. **Step 5 — grouping supporting memories under a
returned fact — is T2.55's**, and this module deliberately emits no
``grouping`` key: emitting one would claim a grouping pass ran. The sectioned
and fused output shapes are T2.56's; Chat's convergence onto this entry point
is T2.58's. Nothing here has a productive caller yet, and the envelope says so
rather than reporting deferred arms as if they had run.

**Three properties the layers below are built on, none of them incidental.**

*Keys are namespaced.* The merge key is ``"<id_kind>:<raw_id>"``, minted by
:func:`composition_key`. ``rank_fusion.normalize_row_id`` reads ``memory_id``
**or** ``id`` and returns a bare string, so a fact and a memory that happen to
share a UUID land on one key in one flat space with nothing marking which
table each came from — and ``rrf_fuse`` has no notion of an unexpected merge,
so it would sum their mass in silence. The likelier accident is the reverse: a
caller reshapes a fact row as ``{"memory_id": ...}`` to make an existing helper
work and the fact becomes indistinguishable from a memory downstream. A
namespaced key makes both unrepresentable, and gives T2.55's ``grouped_under``
something that can name one object in one space.

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

**L1 is absent from :data:`LAYERS` on purpose** (doc 07 §8: "L1 candidate graph
is not directly served"). A vocabulary admitting ``L1`` would let a
candidate-graph row be served as a composed result.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import MemoryFilter
from app.schemas.retrieval_trace import ChannelStatus, RetrievalEnvelope
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


@dataclass(frozen=True)
class ComposedRow:
    """One served row, labelled with where it came from and how it ranked.

    Carries **both** key spellings on purpose: ``key`` is the internal
    namespaced merge key, and ``id`` + ``id_kind`` are doc 07 §8's wire pair,
    so a client is handed a bare id it can look up. ``key ==
    f"{id_kind}:{id}"`` always.

    There is deliberately **no** ``grouping`` key. Emitting
    ``{grouped_under: None}`` would claim a grouping pass ran; T2.55 adds the
    key when it adds the pass.
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


@dataclass(frozen=True)
class CompositionResult:
    """``compose()``'s ordered output plus the counts the envelope owes.

    ``excluded_by_context_conflict`` is doc 07 §8's ``by_context_conflict``
    and is reported unconditionally, including when it is zero — a suppressed
    count hides exactly the case a reader needs.
    """

    rows: list[ComposedRow]
    excluded_by_context_conflict: int = 0
    reranked: bool = False


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


def compose(
    candidates,
    *,
    weights: Mapping[str, object] | None = None,
    declared_context: DeclaredContext | None = None,
    evidence: Mapping[str, Mapping] | None = None,
    rerank_scores: Mapping[str, float] | None = None,
) -> CompositionResult:
    """Doc 07 §5 steps 1 to 4, as a pure function.

    No session, no clock, no LLM — the same split the verification ladder
    keeps between its decision and its applier, and for the same reason: it
    makes every ordering, tier and keyspace property a fast test that can be
    mutated cheaply and often.

    **The order is ascending on ``(band, -tier, key)``.** ``key`` is the sole
    tie-break because it is input-independent: an insertion-order tie-break
    would make the served order depend on the order a caller happened to list
    its channels. A weighted score is deliberately *not* a sort term —
    comparing two channels' weighted magnitudes directly is the
    cross-modality comparison doc 07 §3 rejects.

    **Nothing is dropped for its verification status.** An all-``candidate``
    input composes to a full, labelled result, which is the floor T2.56's
    cold start inherits rather than a rule it has to unpick.
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
            "names one object in one space, and T2.55's grouping map keys on it"
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
                labels=_labels(candidate),
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

    return CompositionResult(
        rows=sorted(rows, key=lambda r: (r.band, -r.tier, r.key)),
        excluded_by_context_conflict=excluded_by_context_conflict,
        reranked=reranked,
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
    not Chat-aware, and it has no productive caller today: T2.56 and T2.58 are
    its consumers and both are behind this task.

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
                logger.warning(
                    "Layer composition: %s carries no text to rerank; it will "
                    "be scored against an empty document",
                    row.key,
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

        provisional = compose(
            candidates,
            weights=weights,
            declared_context=declared_context,
            evidence=evidence,
        )
        rerank_scores = await self.derive_rerank_scores(query, provisional.rows)
        result = (
            provisional
            if rerank_scores is None
            else compose(
                candidates,
                weights=weights,
                declared_context=declared_context,
                evidence=evidence,
                rerank_scores=rerank_scores,
            )
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
            excluded={"by_context_conflict": result.excluded_by_context_conflict},
        )
        # Each channel fetches up to ``limit`` of its own, so the union is up
        # to one limit per layer. ``limit`` is the caller's answer budget, not
        # a per-channel quota, so the composed order is cut here — after the
        # ordering, by rank, never by label. Nothing is dropped for its
        # verification status; this drops the tail of a total order.
        return ComposedResult(rows=result.rows[:limit], envelope=envelope)
