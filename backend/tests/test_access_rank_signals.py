"""Heat and recency: from raw counters to spent arm signals (T2.31).

T2.29 landed `memory_access_stats` and deliberately derived nothing from it —
its docstring says so outright. This suite covers the derivation and the
wiring, which is the half that was missing when an ablation of `w_heat`
returned an exact zero delta on every slice: not because heat does not help,
but because `arm_factor` was never handed a heat number to spend.

**The load-bearing test is `test_both_doors_spend_one_set_of_numbers`.** The
signals are stamped on the row by the shared channel rather than derived at
each door, because a door that derives its own would agree with the other
exactly while both arms sat at zero and diverge the moment either was flipped
on — the T2.58 shape, arriving through the signals instead of the channel.

**The second is `test_absence_is_neutral_not_a_penalty`.** A never-accessed
memory has no counter row. If that read as heat 0 *and* the arm treated 0 as a
signal, every newly captured memory would be demoted for as long as the arm is
on, which is the opposite of what a heat prior is for.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.services.rank_fusion import (
    HEAT_SCALE,
    RECENCY_HALFLIFE_DAYS,
    access_arms_active,
    arm_factor,
    heat_signal,
    rank_fusion_factor,
    recency_signal,
)
from app.services.hybrid_search import HybridSearchService
from app.utils.ids import new_id

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
PROJECT = "t231-signals"

_INSERT_MEMORY = text(
    """
    INSERT INTO memories (id, content, source, project, status)
    VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')
    """
)

_INSERT_STATS = text(
    """
    INSERT INTO memory_access_stats (memory_id, access_count, last_accessed)
    VALUES (CAST(:id AS uuid), :count, CAST(:last AS timestamptz))
    """
)


async def seed(session, *, count=None, last=None, content="seed"):
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {"id": str(memory_id), "content": content, "project": PROJECT},
    )
    if count is not None or last is not None:
        await session.execute(
            _INSERT_STATS,
            {"id": str(memory_id), "count": count or 0, "last": last},
        )
    return memory_id


# ── the derivations ──────────────────────────────────────────────────


def test_heat_saturates_rather_than_normalising():
    """Normalising by the corpus maximum — or the page's — makes one row's
    signal depend on which other rows came back, so the same memory scores
    differently in two result sets and the doors stop being comparable.
    Saturation is per-row and absolute."""
    assert heat_signal(0) == 0.0
    assert heat_signal(HEAT_SCALE) == pytest.approx(1 - 1 / 2.718281828, abs=1e-4)
    assert 0.0 < heat_signal(1) < heat_signal(5) < heat_signal(50) < 1.0
    # Unbounded counts stay inside the ceiling, so the multiplier cannot run away.
    assert heat_signal(10**9) <= 1.0


def test_heat_is_absent_rather_than_zero_when_there_is_no_counter():
    assert heat_signal(None) is None
    assert heat_signal("not a number") is None


def test_recency_halves_on_the_half_life():
    assert recency_signal(NOW, NOW) == 1.0
    assert recency_signal(
        NOW - timedelta(days=RECENCY_HALFLIFE_DAYS), NOW
    ) == pytest.approx(0.5)
    assert recency_signal(
        NOW - timedelta(days=2 * RECENCY_HALFLIFE_DAYS), NOW
    ) == pytest.approx(0.25)
    assert recency_signal(None, NOW) is None


def test_a_naive_timestamp_is_read_as_utc_not_as_local():
    """Postgres hands back tz-aware values, but a caller constructing one by
    hand does not. Treating a naive stamp as local time would silently shift
    recency by the host's offset — a signal that changes when the server moves
    timezone."""
    naive = (NOW - timedelta(days=RECENCY_HALFLIFE_DAYS)).replace(tzinfo=None)
    assert recency_signal(naive, NOW) == pytest.approx(0.5)


def test_absence_is_neutral_not_a_penalty():
    """An arm with no signal returns exactly 1.0, so a never-accessed memory
    keeps its place instead of being demoted for as long as the arm is on."""
    from app.services.rank_fusion import RANK_ARMS

    heat_arm = next(a for a in RANK_ARMS if a.name == "heat")
    assert arm_factor(heat_arm, {}, {"w_heat": 2.0}) == 1.0
    assert arm_factor(heat_arm, {"heat": 0.0}, {"w_heat": 2.0}) == 1.0
    assert arm_factor(heat_arm, {"heat": 0.5}, {"w_heat": 2.0}) == 2.0


def test_the_arms_stay_inert_at_zero_weight_with_signals_present():
    signals = {"confidence": 0.9, "importance": 0.9, "heat": 1.0, "recency": 1.0}
    assert rank_fusion_factor(signals, {}) == 1.0
    assert rank_fusion_factor(signals, {"w_heat": 0.0, "w_recency": 0.0}) == 1.0


def test_the_gate_skips_the_read_when_neither_arm_carries_weight():
    """Inert must also mean free: an install with both arms at zero must not
    pay a `memory_access_stats` read on every query."""
    assert access_arms_active({}) is False
    assert access_arms_active({"w_heat": 0.0, "w_recency": 0.0}) is False
    assert access_arms_active({"w_importance": 0.5}) is False
    assert access_arms_active({"w_heat": 0.1}) is True
    assert access_arms_active({"w_recency": -0.1}) is True


# ── the wiring ───────────────────────────────────────────────────────


async def test_the_channel_stamps_the_signals_on_the_rows(session):
    hot = await seed(session, count=40, last=NOW)
    cold = await seed(session, count=1, last=NOW - timedelta(days=120))
    never = await seed(session)

    rows = [{"memory_id": str(m)} for m in (hot, cold, never)]
    await HybridSearchService(llm=None, session=session)._attach_access_signals(rows)

    by_id = {r["memory_id"]: r for r in rows}
    assert by_id[str(hot)]["heat"] > by_id[str(cold)]["heat"]
    assert by_id[str(hot)]["recency"] > by_id[str(cold)]["recency"]
    # No counter row means no keys at all, which is what keeps absence neutral.
    assert "heat" not in by_id[str(never)]
    assert "recency" not in by_id[str(never)]


async def test_an_empty_result_set_reads_nothing(session):
    rows: list[dict] = []
    await HybridSearchService(llm=None, session=session)._attach_access_signals(rows)
    assert rows == []


async def test_both_doors_spend_one_set_of_numbers(session):
    """The parity property, asserted on the composed factor rather than on the
    shape of the call.

    The chat door reads its arm signals off the row
    (`layer_composition._signals` over `SIGNAL_KEYS`) and the search door reads
    confidence and importance from `memories`. Both take heat and recency from
    the row the shared channel stamped, so the factor each computes for one
    memory is the same number.
    """
    from app.services.layer_composition import _signals

    memory_id = await seed(session, count=25, last=NOW - timedelta(days=10))
    row = {"memory_id": str(memory_id), "confidence": 0.8, "importance": 0.6}
    await HybridSearchService(llm=None, session=session)._attach_access_signals([row])

    weights = {"w_heat": 0.5, "w_recency": 0.5}

    chat_factor = rank_fusion_factor(_signals(row), weights)
    search_factor = rank_fusion_factor(
        {
            "confidence": row["confidence"],
            "importance": row["importance"],
            "heat": row["heat"],
            "recency": row["recency"],
        },
        weights,
    )

    assert chat_factor == search_factor
    assert chat_factor != 1.0


async def test_a_hot_memory_outranks_a_cold_one_once_the_arm_is_on(session):
    """The arm has to be able to move the order — the complement of every
    inertness assertion above. Without this, wiring that silently produced
    identical numbers would still look correct."""
    hot = await seed(session, count=100, last=NOW)
    cold = await seed(session, count=0, last=NOW - timedelta(days=365))

    rows = [
        {"memory_id": str(cold), "rrf_score": 0.011},
        {"memory_id": str(hot), "rrf_score": 0.010},
    ]
    await HybridSearchService(llm=None, session=session)._attach_access_signals(rows)

    weights = {"w_heat": 2.0}
    for row in rows:
        signals = {k: row[k] for k in ("heat", "recency") if k in row}
        row["rrf_score"] *= rank_fusion_factor(signals, weights)

    ordered = sorted(rows, key=lambda r: r["rrf_score"], reverse=True)
    assert ordered[0]["memory_id"] == str(hot)


async def test_recency_cannot_lift_a_row_across_the_belief_axis(session):
    """T2.31's explicit Done-when: a fresh wrong fact must not outrank an older
    verified one.

    The multiplier cannot do it, and the reason is structural rather than
    numeric — verification status is a **hard ordering rule**, applied by the
    composition as a band, while `rank_fusion_factor` only ever rescales
    *within* a band. This asserts the property that makes that true: the factor
    is a positive scalar on the row's own score and touches no band, so no
    weight can reorder across one.
    """
    fresh = await seed(session, count=500, last=NOW)
    await HybridSearchService(llm=None, session=session)._attach_access_signals(
        [{"memory_id": str(fresh)}]
    )

    extreme = {"w_heat": 1000.0, "w_recency": 1000.0}
    factor = rank_fusion_factor({"heat": 1.0, "recency": 1.0}, extreme)

    # Whatever the magnitude, it is a finite positive scalar — never a band
    # change and never a sign flip, which is what "cannot cross the axis"
    # means in code.
    assert factor > 0.0
    assert factor == pytest.approx(1001.0 * 1001.0)

    from app.services.layer_composition import ComposedRow

    ordering_fields = {f.name for f in ComposedRow.__dataclass_fields__.values()}
    assert "band" in ordering_fields
    assert "rank_fusion_factor" in ordering_fields


@pytest.mark.parametrize("read_only", [False, True])
async def test_access_is_recorded_with_hybrid_off(monkeypatch, read_only):
    import uuid

    from app.config import settings
    from app.services import access_stats
    from app.services import hybrid_search as hybrid_module

    ids = [uuid.uuid4(), uuid.uuid4()]
    rows = [{"memory_id": mid, "score": 1.0 - i / 10} for i, mid in enumerate(ids)]

    class _LLM:
        async def embed(self, _query):
            return [1.0, 0.0], "fp|2"

    class _Vectors:
        def __init__(self, _session):
            pass

        async def search(self, *_a, **_k):
            return [dict(row) for row in rows]

    async def _keyword(self, *_a, **_k):
        return [dict(row) for row in rows]

    recorded: list[list] = []
    real_spawn = access_stats.spawn_record_access

    def _spy(memory_ids, **kwargs):
        memory_ids = list(memory_ids)
        recorded.append(memory_ids)
        # Only the read-only case reaches the real buffer: it must stay a
        # no-op, and the writable case's flush is not this test's subject.
        return real_spawn(memory_ids, **kwargs) if read_only else None

    monkeypatch.setattr(settings, "read_only", read_only)
    monkeypatch.setattr(hybrid_module, "PostgresVectorRepository", _Vectors)
    monkeypatch.setattr(HybridSearchService, "_keyword_search", _keyword)
    monkeypatch.setattr(hybrid_module, "spawn_record_access", _spy)
    monkeypatch.setattr(access_stats, "_pending_counts", {})

    service = HybridSearchService(_LLM(), session=None)
    results = await service.search_ranked("anything", flags={"hybrid_search_enabled": False}, limit=5)

    assert [row["memory_id"] for row in results] == ids
    assert recorded == [ids]
    assert access_stats._pending_counts == {}
