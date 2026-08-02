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

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.services.rank_fusion import (
    RRF_K,
    RowContext,
    row_context_from_applies_when,
)
from app.services.verified_evidence import CONTRADICTION_EVIDENCE_KEY

__all__ = [
    "COUNTERPART_ABSENT_NO_FINDING",
    "DISPUTED",
    "ID_KINDS",
    "LAYERS",
    "LAYER_BY_ID_KIND",
    "LayerCandidate",
    "article_candidate",
    "composition_key",
    "cross_layer_rrf",
    "dispute_label",
    "fact_candidate",
    "memory_candidate",
]

LAYERS: frozenset[str] = frozenset({"L0", "L2", "L3"})
ID_KINDS: frozenset[str] = frozenset({"memory", "fact", "article"})
LAYER_BY_ID_KIND: dict[str, str] = {"memory": "L0", "fact": "L2", "article": "L3"}

# Per-channel list weights, equal and deliberately **constants rather than
# config rows**. Doc 07 §11 permits tuning a ranking multiplier only against
# the harness, and no task owns measuring a cross-layer channel weight — so a
# config row here would be an operator-visible claim that tuning is sanctioned
# when no measurement path exists to sanction it. Constants say the true
# thing: these are equal, and nobody has measured otherwise. Promoting them
# once a task owns the measurement is a one-line change.
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
