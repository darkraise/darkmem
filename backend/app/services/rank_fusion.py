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
