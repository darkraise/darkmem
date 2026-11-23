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

import math
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.confidence import CONFIDENCE_DEFAULT

RRF_K = 60

# How deep every ranked list is read before the fusion joins them, fixed here
# rather than derived from whatever page the caller wanted. RRF is **not
# truncation-consistent across depths**: a row inside one reader's arm window
# and outside another's earns a contribution on one side only, so two doors
# over one corpus produce two different orderings — invariant 17's divergence,
# arriving with no error and no symptom. At a fixed depth a shallow reader's
# list is the deep reader's list truncated, which is the property the doors
# are compared on. The value is the depth the search surface already read at
# its live page size (50 rows plus its 50-row exclusion over-fetch, times the
# vector repository's fetch multiplier), so the surface's own ordering is
# unchanged and every shallower reader converges onto it.
FUSION_FETCH_DEPTH = 300

IMPORTANCE_DEFAULT = 0.5

# Every weight that moves a ranked list's RRF contribution, and nothing that
# moves a per-row score. `w_ppr` and `w_dual` join here rather than as
# `RankArm`s deliberately: both name a *producer of candidates*, so their
# weight belongs to the fusion. Filed as arms they would have multiplied rows
# the graph never proposed.
LIST_WEIGHT_KEYS: frozenset[str] = frozenset(
    {"semantic_weight", "w_ppr", "w_dual"}
)


@dataclass(frozen=True)
class GraphChannel:
    """One doc 07 §4 graph-augmentation producer, and the weight it fuses under.

    Separate from ``RankArm`` for the same reason ``LIST_WEIGHT_KEYS`` is: these
    name *producers of candidates*, so a channel's weight belongs to the fusion
    rather than multiplying rows the graph never proposed.

    ``activation`` names the task that may turn the channel on, and lives here
    for the reason ``RankArm.activation`` does (T1.57 ruling 1): a settings
    surface must read the activation id off the backend's own registry rather
    than carry a second copy that drifts the first time a task is renumbered.
    """

    name: str
    flag: str
    weight_flag: str
    activation: str | None = None


# Both land inert (doc 07 §4) and T2.50 measures them before either moves.
GRAPH_CHANNELS: tuple[GraphChannel, ...] = (
    GraphChannel("ppr", "ppr_enabled", "w_ppr", activation="T2.50"),
    GraphChannel("dual_level", "dual_level_enabled", "w_dual", activation="T2.50"),
)


# ── class 1: ranked lists ────────────────────────────────────────────


@dataclass(frozen=True)
class RankedList:
    """One ranked candidate producer joining the fusion under its weight."""

    name: str
    rows: Sequence[Mapping] = field(default_factory=tuple)
    weight: float = 0.0


def fusion_fetch_depth(limit: int) -> int:
    """How many rows each ranked list is read to before it is fused.

    Never fewer than the fused rows the caller asked for: two arms that
    returned the same rows could not otherwise fill the request. Above that
    floor the depth is constant, which is what makes one door's ranking a
    truncation of another's rather than a different one.
    """
    return max(FUSION_FETCH_DEPTH, limit)


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


def rrf_fuse(
    lists: Sequence[RankedList],
    limit: int,
    key: Callable[[Mapping], Hashable | None] = normalize_row_id,
) -> list[dict]:
    """Fuse ranked lists into one ``rrf_score``-ordered result set.

    A row at rank *r* of a list contributes ``weight / (RRF_K + r)``; a row
    appearing in several lists sums its contributions. RRF is rank-based,
    so no per-modality score normalisation is needed and adding a producer
    never re-tunes an existing one.

    ``key`` names a row's identity across lists; a row it maps to ``None`` is
    dropped. The default keys on the normalised memory or row id and writes
    that normalised id back onto the fused row.

    The first-seen list's raw ``score`` survives on the fused row so a
    consumer can see which modality found it, but ``rrf_score`` is the
    ordering key, with equal scores ordered by row key.
    """
    fused: dict[Hashable, dict] = {}

    for ranked in lists:
        for rank, row in enumerate(ranked.rows, start=1):
            row_key = key(row)
            if row_key is None:
                continue
            contribution = ranked.weight / (RRF_K + rank)
            entry = fused.get(row_key)
            if entry is None:
                entry = dict(row)
                entry.pop("source", None)
                if key is normalize_row_id:
                    if entry.get("memory_id") is not None:
                        entry["memory_id"] = row_key
                    elif entry.get("id") is not None:
                        entry["id"] = row_key
                entry["rrf_score"] = contribution
                fused[row_key] = entry
            else:
                entry["rrf_score"] += contribution

    # Ties break on the key as a string so hybrid search's string ids and the
    # vector repository's UUIDs order alike.
    ordered = sorted(fused.items(), key=lambda item: (-item[1]["rrf_score"], str(item[0])))
    return [entry for _, entry in ordered[:limit]]


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


# ── the heat and recency signals (doc 07 §3, T2.29's substrate) ──────
#
# `memory_access_stats` stores raw counters and deliberately derives nothing
# (that module's own docstring says so). These are the derivations, and they
# live here beside the arm that spends them rather than beside the counter,
# so a second consumer cannot invent a second scale for the same signal.

# Accesses at which heat reaches ~63% of its ceiling. A *saturating* transform
# rather than a normalised one is the load-bearing choice: normalising by the
# corpus maximum (or by the page's) makes one row's signal depend on other
# rows, so the same memory scores differently in two result sets and the two
# doors can no longer be compared. Saturation is per-row and absolute.
HEAT_SCALE = 10.0

# Access recency, not content recency. T2.29 built `memory_access_stats` as
# "the substrate w_heat and w_recency will read", and `last_accessed` is the
# column it offers; `updated_at` means "content changed" and is moved by the
# `touch_updated_at` trigger, which is a different claim entirely.
RECENCY_HALFLIFE_DAYS = 30.0


def heat_signal(access_count: object) -> float | None:
    """Bounded [0, 1) heat from a raw access count.

    ``None`` when there is no counter row — which `arm_factor` already treats
    as "leave this row alone". A never-accessed memory and a zero-count one
    are the same claim, and both must be neutral rather than penalised: heat
    ranks *up* what is hot, and turning absence into a downward multiplier
    would demote every newly captured memory for as long as the arm is on.
    """
    if access_count is None:
        return None
    try:
        count = float(access_count)
    except (TypeError, ValueError):
        return None
    if count <= 0.0:
        return 0.0
    return 1.0 - math.exp(-count / HEAT_SCALE)


def recency_signal(last_accessed: object, now: datetime | None = None) -> float | None:
    """Bounded (0, 1] exponential decay on time since last access."""
    if not isinstance(last_accessed, datetime):
        return None
    reference = now or datetime.now(timezone.utc)
    if last_accessed.tzinfo is None:
        last_accessed = last_accessed.replace(tzinfo=timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    age_days = (reference - last_accessed).total_seconds() / 86400.0
    if age_days <= 0.0:
        return 1.0
    return math.exp(-age_days * math.log(2.0) / RECENCY_HALFLIFE_DAYS)


ACCESS_ARM_FLAGS: tuple[str, ...] = ("w_heat", "w_recency")


def access_arms_active(weights: Mapping[str, object]) -> bool:
    """Whether either access-fed arm carries weight.

    Lets the channel skip the `memory_access_stats` read entirely, so an
    install with both arms at zero pays nothing for a signal nothing spends —
    the same "inert must also mean free" property the PPR arm holds.
    """
    return any(_weight(weights, flag) != 0.0 for flag in ACCESS_ARM_FLAGS)


def ppr_list_weight(weights: Mapping[str, object]) -> float:
    """The PPR list's fusion weight — zero unless its flag is on.

    The flag-to-weight collapse lives here and is called by every door rather
    than spelled at each of them. Two doors reading `ppr_enabled` and `w_ppr`
    separately is exactly the shape that let chat and the search surface rank
    one corpus two ways before T2.58: identical while both were off, divergent
    the moment one was flipped, with no error on either side.
    """
    if not weights.get("ppr_enabled"):
        return 0.0
    return _weight(weights, "w_ppr")


def dual_list_weight(weights: Mapping[str, object]) -> float:
    """The dual-level list's fusion weight — zero unless its flag is on.

    Same collapse as :func:`ppr_list_weight`, and here for the same reason:
    two doors reading `dual_level_enabled` and `w_dual` separately are
    identical while the arm is off and divergent the moment it is flipped on.
    """
    if not weights.get("dual_level_enabled"):
        return 0.0
    return _weight(weights, "w_dual")


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
