"""The read path's two-class ranking model (doc 07 §3).

Two kinds of signal, and they never meet:

* A signal that produces a **ranked list** joins one reciprocal-rank fusion
  at ``k = 60`` as a weighted input. ``semantic_weight`` is a *list weight*
  here — it moves ``rrf_score`` and nothing else.
* A signal that produces a **per-row scalar** is a deterministic
  post-fusion multiplier, composed by :func:`rank_fusion_factor`.

Collapsing either class into the other passes most tests and makes both
untunable: a list weight would start moving per-row scores, and a per-row
scalar would start moving list ordering. ``LIST_WEIGHT_KEYS`` and the
``RankArm.flag`` set are asserted disjoint for exactly that reason.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

from app.services.confidence import CONFIDENCE_DEFAULT

RRF_K = 60

IMPORTANCE_DEFAULT = 0.5

LIST_WEIGHT_KEYS: frozenset[str] = frozenset({"semantic_weight"})


# ── class 1: ranked lists ────────────────────────────────────────────


@dataclass(frozen=True)
class RankedList:
    """One ranked candidate producer joining the fusion under its weight."""

    name: str
    rows: Sequence[Mapping] = field(default_factory=tuple)
    weight: float = 0.0


def normalize_row_id(row: Mapping) -> str | None:
    """The fusion key for a candidate row, normalised to ``str``.

    Invariant 9: the semantic side and the vector repo emit ``UUID`` while
    the keyword and hybrid sides emit ``str``. Keying the merge on the raw
    value silently splits one memory into two fused rows, each with half
    its RRF mass — a ranking quirk rather than an error. Normalise once,
    here, where the lists meet.
    """
    raw = row.get("memory_id") or row.get("id")
    if raw is None:
        return None
    key = str(raw)
    return key or None


def rrf_fuse(lists: Sequence[RankedList], limit: int) -> list[dict]:
    """Fuse ranked lists into one ``rrf_score``-ordered result set.

    A row at rank *r* of a list contributes ``weight / (RRF_K + r)``; a row
    appearing in several lists sums its contributions. RRF is rank-based,
    so no per-modality score normalisation is needed and adding a producer
    never re-tunes an existing one.

    The first-seen list's raw ``score`` survives on the fused row so a
    consumer can see which modality found it, but ``rrf_score`` is the sole
    ordering key.
    """
    fused: dict[str, dict] = {}

    for ranked in lists:
        for rank, row in enumerate(ranked.rows, start=1):
            key = normalize_row_id(row)
            if key is None:
                continue
            contribution = ranked.weight / (RRF_K + rank)
            entry = fused.get(key)
            if entry is None:
                entry = dict(row)
                entry.pop("source", None)
                if entry.get("memory_id") is not None:
                    entry["memory_id"] = key
                elif entry.get("id") is not None:
                    entry["id"] = key
                entry["rrf_score"] = contribution
                fused[key] = entry
            else:
                entry["rrf_score"] += contribution

    ordered = sorted(fused.values(), key=lambda r: r["rrf_score"], reverse=True)
    return ordered[:limit]


# ── class 2: per-row scalars ─────────────────────────────────────────


@dataclass(frozen=True)
class RankArm:
    """One arm of the post-fusion multiplier: ``1 + weight * (signal - baseline)``.

    ``activation`` names the task that turns the arm on, so an arm sitting
    at zero is never mistaken for a shipped signal.
    """

    name: str
    flag: str
    baseline: float
    activation: str | None = None


RANK_ARMS: tuple[RankArm, ...] = (
    RankArm("confidence", "confidence_rank_gamma", CONFIDENCE_DEFAULT),
    RankArm("importance", "w_importance", IMPORTANCE_DEFAULT, activation="T2.30"),
    RankArm("heat", "w_heat", 0.0, activation="T2.31"),
    RankArm("recency", "w_recency", 0.0, activation="T2.31"),
)


def _weight(weights: Mapping[str, object], flag: str) -> float:
    try:
        return float(weights.get(flag, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def arm_factor(arm: RankArm, signals: Mapping[str, float], weights: Mapping[str, object]) -> float:
    """This arm's multiplier, exactly ``1.0`` when its weight is zero or its
    signal is unavailable.

    Clamped per arm rather than on the product: two arms each driven
    negative by a pathological weight would otherwise multiply back to a
    positive factor and silently invert the order.
    """
    weight = _weight(weights, arm.flag)
    if weight == 0.0:
        return 1.0
    signal = signals.get(arm.name)
    if signal is None:
        return 1.0
    return max(0.0, 1.0 + weight * (float(signal) - arm.baseline))


def rank_fusion_breakdown(
    signals: Mapping[str, float],
    weights: Mapping[str, object],
) -> dict[str, float]:
    """Per-arm multipliers, in ``RANK_ARMS`` order."""
    return {arm.name: arm_factor(arm, signals, weights) for arm in RANK_ARMS}


def rank_fusion_factor(
    signals: Mapping[str, float],
    weights: Mapping[str, object],
) -> float:
    """The composed post-fusion multiplier: ``final = rrf_score * factor``.

    An arm at weight zero contributes exactly ``1.0``, and multiplying a
    float by ``1.0`` is exact, so the composed factor is bit-identical to
    the factor of whichever arms are actually spent.
    """
    factor = 1.0
    for arm_multiplier in rank_fusion_breakdown(signals, weights).values():
        factor *= arm_multiplier
    return factor


def any_arm_active(weights: Mapping[str, object]) -> bool:
    """Whether any arm carries a non-zero weight.

    Lets a caller skip the signal reads entirely when the whole factor
    would be identity.
    """
    return any(_weight(weights, arm.flag) != 0.0 for arm in RANK_ARMS)


# ── class 2, second member: the applies_when context boost (doc 07 §6) ──
#
# A declared context produces a per-row scalar, so it is a post-fusion
# multiplier and never a ranked-list arm. It is deliberately *not* a
# ``RankArm``: an arm reads a stored column through one formula, while a
# context outcome is a three-way verdict that also excludes rows and owes
# the reader a label. Composed as ``rank_fusion_factor x context boost``.

CONTEXT_BOOST_FLAG = "w_context_boost"

CONTEXT_AXES: tuple[str, ...] = ("env", "version", "situation")

# Only the closed-vocabulary axes can establish an *explicit* conflict.
# ``version`` is a free string compared app-side (doc 07 §6, doc 12 §5), so
# a difference there is "not the same version", never proof of
# incompatibility — and exclusion is the one direction where being wrong
# silently removes an answer.
CONFLICT_AXES: frozenset[str] = frozenset({"env", "situation"})

CONTEXT_OUTCOME_KEY = "context"


class ContextMatch(str, Enum):
    """The three outcomes of comparing a row's context to the declared one."""

    MATCHED = "matched"
    NEUTRAL = "neutral"
    CONFLICT = "conflict"


class ContextProvenance(str, Enum):
    """Who authored a context value. Only ``human`` may drive an exclusion."""

    HUMAN = "human"
    LLM_GUESSED = "llm_guessed"


def _normalize_axes(raw: Mapping[str, object] | None) -> dict[str, str]:
    if not raw:
        return {}
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        if value is None:
            continue
        text_value = str(value).strip().lower()
        if not text_value:
            continue
        normalized[str(key).strip().lower()] = text_value
    return normalized


@dataclass(frozen=True)
class _AxisSet:
    axes: Mapping[str, str]

    def __post_init__(self) -> None:
        # An all-empty declaration would be indistinguishable from no
        # declaration at all while still being a live object, which is the
        # exact "undeclared silently became a default" confusion T1.65
        # guards. ``None`` is the one representation of undeclared.
        if not self.axes:
            raise ValueError("a context with no stated axis is undeclared; use None")

    def value(self, axis: str) -> str | None:
        return self.axes.get(axis)


@dataclass(frozen=True)
class DeclaredContext(_AxisSet):
    """The caller's declared context — never derived from ``project``."""

    provenance: ContextProvenance = ContextProvenance.HUMAN


@dataclass(frozen=True)
class RowContext(_AxisSet):
    """A servable row's own ``applies_when``, with who authored it."""

    provenance: ContextProvenance = ContextProvenance.HUMAN


def declared_context_from_wire(
    raw: Mapping[str, object] | None,
    provenance: ContextProvenance = ContextProvenance.HUMAN,
) -> DeclaredContext | None:
    """Terminal step of doc 12 §5's precedence chain.

    The chain decides *which* declaration wins; this turns the winner into
    the value matching consumes, and returns ``None`` when nothing was
    declared so an absent context can never arrive as a default one.
    """
    axes = _normalize_axes(raw)
    if not axes:
        return None
    return DeclaredContext(axes, provenance)


def row_context_from_applies_when(
    applies_when: Mapping[str, object] | None,
    provenance: ContextProvenance = ContextProvenance.HUMAN,
) -> RowContext | None:
    axes = _normalize_axes(applies_when)
    if not axes:
        return None
    return RowContext(axes, provenance)


def context_boost_magnitude(weights: Mapping[str, object]) -> float:
    """The tunable half of this slot, read from the merged ``config`` row."""
    return _weight(weights, CONTEXT_BOOST_FLAG)


@dataclass(frozen=True)
class ContextOutcome:
    """One row's context verdict, with its boost *derived* from that verdict.

    ``boost`` is a property, not a field: there is no way to construct a
    boosted row that does not also carry the label explaining the boost,
    because the label is the only input the boost has. Storing the two side
    by side would let a later edit set one without the other.
    """

    match: ContextMatch
    applies_when: Mapping[str, str] | None = None
    provenance: ContextProvenance | None = None
    magnitude: float = 0.0

    @property
    def boost(self) -> float:
        if self.match is not ContextMatch.MATCHED:
            return 1.0
        # Clamped like the arms: a pathological negative magnitude must not
        # flip a boost into an order-inverting negative factor.
        return max(0.0, 1.0 + self.magnitude)

    @property
    def excluded(self) -> bool:
        return self.match is ContextMatch.CONFLICT

    def to_trace(self) -> dict:
        """The doc 07 §8 per-row ``context`` object, all four keys always."""
        return {
            "match": self.match.value,
            "boost": self.boost,
            "applies_when": dict(self.applies_when) if self.applies_when else None,
            "provenance": self.provenance.value if self.provenance else None,
        }


def match_context(
    declared: DeclaredContext | None,
    row: RowContext | None,
    weights: Mapping[str, object],
) -> ContextOutcome:
    """Compare one row's context to the declared one (doc 07 §6).

    Matched when a stated axis agrees, conflicting when a closed-vocabulary
    axis disagrees, neutral otherwise — including whenever the row's context
    is LLM-guessed, which is displayed provenance and never an exclusion
    basis until a human touches it (doc 01 §3.4).
    """
    magnitude = context_boost_magnitude(weights)
    applies_when = dict(row.axes) if row is not None else None
    provenance = row.provenance if row is not None else None

    def neutral() -> ContextOutcome:
        return ContextOutcome(ContextMatch.NEUTRAL, applies_when, provenance, magnitude)

    if declared is None or row is None:
        return neutral()
    if row.provenance is not ContextProvenance.HUMAN:
        return neutral()

    matched = False
    for axis in CONTEXT_AXES:
        declared_value = declared.value(axis)
        row_value = row.value(axis)
        if declared_value is None or row_value is None:
            continue
        if declared_value == row_value:
            matched = True
        elif axis in CONFLICT_AXES:
            return ContextOutcome(ContextMatch.CONFLICT, applies_when, provenance, magnitude)

    if matched:
        return ContextOutcome(ContextMatch.MATCHED, applies_when, provenance, magnitude)
    return neutral()


@dataclass(frozen=True)
class ContextComposition:
    """Surviving rows, the declaration they were judged against, and the tally.

    ``declared is None`` means no context was declared at all; a
    ``DeclaredContext`` with every row neutral means one was declared and
    matched nothing. The two are different facts about the request and the
    envelope must be able to say which happened.
    ``excluded_by_context_conflict`` is doc 07 §8's
    ``excluded.by_context_conflict``.
    """

    rows: list[dict]
    declared: DeclaredContext | None
    excluded_by_context_conflict: int


def partition_by_context(
    rows: Sequence[Mapping],
    declared: DeclaredContext | None,
    row_contexts: Mapping[str, RowContext | None],
    weights: Mapping[str, object],
) -> ContextComposition:
    """Composition step 2: stamp every row's outcome, drop and count conflicts.

    Runs before the reranker so no model call is spent scoring a row that
    will be excluded. The tally is unconditional — there is no flag and no
    dependence on the magnitude, because a suppressed count would hide the
    ambiguity precisely when no boost is compensating for it.
    """
    kept: list[dict] = []
    excluded = 0
    for row in rows:
        key = normalize_row_id(row)
        outcome = match_context(
            declared, row_contexts.get(key) if key is not None else None, weights,
        )
        if outcome.excluded:
            excluded += 1
            continue
        stamped = dict(row)
        stamped[CONTEXT_OUTCOME_KEY] = outcome
        kept.append(stamped)
    return ContextComposition(kept, declared, excluded)


def apply_context_boost(
    rows: Sequence[Mapping],
    *,
    preserve_order: bool = False,
) -> list[dict]:
    """Composition step 4: multiply each row's score by its stamped boost.

    The multiplier is read only off a :class:`ContextOutcome`, so a bare
    number cannot become a boost without a verdict to explain it. Rows must
    have passed :func:`partition_by_context` first.

    ``preserve_order`` keeps a reranked list's order while still rescaling,
    the same rule the ``rank_fusion_factor`` arms follow.
    """
    out = [dict(row) for row in rows]
    if not out:
        return out

    key = "rrf_score" if "rrf_score" in out[0] else "score"
    for row in out:
        outcome = row.get(CONTEXT_OUTCOME_KEY)
        if not isinstance(outcome, ContextOutcome):
            raise TypeError(
                f"row {normalize_row_id(row)!r} carries no ContextOutcome; "
                "run partition_by_context before boosting"
            )
        row[key] = float(row.get(key, 0.0) or 0.0) * outcome.boost

    if preserve_order:
        return out
    return sorted(out, key=lambda r: float(r.get(key, 0.0) or 0.0), reverse=True)
