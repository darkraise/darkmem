"""The usage read API reports totals with their confidence attached.

A currency figure alone is a floor, not a total: calls whose tokens the vendor
never reported and calls whose model has no price row both contribute nothing
to the sum, and an operator who cannot see them will read the floor as the
answer. Each of these tests pins one place that distinction has to survive.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.api.auth import require_auth
from app.main import app
from app.models.llm_usage import LLMUsage

_MEMORY_A = "11111111-1111-1111-1111-111111111111"
_MEMORY_B = "22222222-2222-2222-2222-222222222222"


def _row(**kw) -> LLMUsage:
    base = dict(
        occurred_at=datetime.now(timezone.utc),
        purpose="extraction",
        model="deepseek-v4-flash",
        provider="deepseek",
        api_kind="deepseek",
        subject_type="memory",
        subject_id=_MEMORY_A,
        project="usage-api",
        prompt_tokens=1000,
        cached_tokens=200,
        completion_tokens=100,
        reasoning_tokens=0,
        tokens_measured=True,
        cost_micros=1000,
        rates_used={"input": 270_000, "cached": 14_000, "output": 1_100_000},
        usage_raw={},
        ok=True,
        error_kind=None,
        duration_ms=120,
    )
    base.update(kw)
    return LLMUsage(**base)


@pytest_asyncio.fixture
async def authed(client):
    app.dependency_overrides[require_auth] = lambda: {"sub": "admin"}
    yield client
    app.dependency_overrides.pop(require_auth, None)


@pytest_asyncio.fixture
async def seeded_usage(session):
    session.add_all([
        _row(cost_micros=5000, subject_id=_MEMORY_A),
        _row(cost_micros=3000, subject_id=_MEMORY_B, duration_ms=90),
        # Measured, but the model carries no price row: this is not free.
        _row(model="mystery-model-9", cost_micros=None, rates_used={},
             subject_id=_MEMORY_B),
        # The vendor sent no envelope at all -- a different state again.
        _row(prompt_tokens=None, cached_tokens=None, completion_tokens=None,
             reasoning_tokens=None, tokens_measured=False, cost_micros=None,
             rates_used={}, subject_id=_MEMORY_A),
        # A local embedder's measured zero, which must not read as unpriced.
        _row(purpose="embedding", model="qwen3-embedding:0.6b", api_kind="ollama",
             provider="ollama", subject_type="batch", subject_id="batch-1",
             cost_micros=0, completion_tokens=0,
             rates_used={"input": 0, "cached": 0, "output": 0}),
        # A failed call still cost time, and may have cost money.
        _row(ok=False, error_kind="ReadTimeout", cost_micros=700,
             subject_id=_MEMORY_B),
    ])
    await session.commit()
    yield


@pytest_asyncio.fixture
async def seeded_merged_usage(session):
    session.add_all([
        _row(usage_raw={"merged_classification": True}),
        _row(purpose="reranker", subject_type="search", subject_id="s-1"),
    ])
    await session.commit()
    yield


@pytest.mark.asyncio
async def test_overview_reports_unmeasured_and_unpriced_counts(authed, seeded_usage):
    """Every aggregate carries its own confidence: a total that silently
    excluded unmeasured calls would read as complete when it is a floor."""
    r = await authed.get("/api/v1/usage/overview?window=30d")
    assert r.status_code == 200
    body = r.json()
    assert body["total_calls"] == 6
    assert body["total_cost_micros"] == 8700
    assert body["unmeasured_calls"] == 1
    assert body["unpriced_calls"] == 1
    assert body["unpriced_models"] == ["mystery-model-9"]
    assert body["failed_calls"] == 1
    assert body["failed_cost_micros"] == 700


@pytest.mark.asyncio
async def test_a_measured_zero_is_not_an_unpriced_call(authed, seeded_usage):
    """The local embedders bill nothing and say so. Counting that as 'no price
    known' would send an operator hunting for a rate that already exists."""
    body = (await authed.get("/api/v1/usage/overview?window=30d")).json()
    assert "qwen3-embedding:0.6b" not in body["unpriced_models"]


@pytest.mark.asyncio
async def test_overview_flags_the_merged_classification_caveat(
    authed, seeded_merged_usage
):
    """Under the default config classification's total reads near zero because
    it is folded into extraction. Unflagged, an operator 'optimising the wasted
    part' would draw exactly the wrong conclusion."""
    body = (await authed.get("/api/v1/usage/overview?window=30d")).json()
    assert body["merged_classification_present"] is True


@pytest.mark.asyncio
async def test_an_unmerged_window_does_not_raise_the_caveat(authed, seeded_usage):
    body = (await authed.get("/api/v1/usage/overview?window=30d")).json()
    assert body["merged_classification_present"] is False


@pytest.mark.asyncio
async def test_the_window_excludes_what_falls_outside_it(authed, session):
    session.add_all([
        _row(cost_micros=11, occurred_at=datetime.now(timezone.utc) - timedelta(days=2)),
        _row(cost_micros=22, occurred_at=datetime.now(timezone.utc) - timedelta(days=40)),
    ])
    await session.commit()
    recent = (await authed.get("/api/v1/usage/overview?window=7d")).json()
    everything = (await authed.get("/api/v1/usage/overview?window=all")).json()
    assert recent["total_cost_micros"] == 11
    assert everything["total_cost_micros"] == 33
    assert everything["window_start"] is None


@pytest.mark.asyncio
async def test_an_unparsable_window_is_refused(authed, seeded_usage):
    r = await authed.get("/api/v1/usage/overview?window=last-tuesday")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_breakdowns_group_on_their_own_axis(authed, seeded_usage):
    body = (await authed.get("/api/v1/usage/overview?window=30d")).json()
    purposes = {r["key"]: r for r in body["by_purpose"]}
    assert purposes["extraction"]["calls"] == 5
    assert purposes["embedding"]["calls"] == 1
    subjects = {r["key"]: r["calls"] for r in body["by_subject_type"]}
    assert subjects == {"memory": 5, "batch": 1}


@pytest.mark.asyncio
async def test_the_project_filter_narrows_every_number(authed, session):
    session.add_all([
        _row(cost_micros=100, project="alpha"),
        _row(cost_micros=900, project="beta"),
    ])
    await session.commit()
    body = (await authed.get("/api/v1/usage/overview?window=30d&project=alpha")).json()
    assert body["total_cost_micros"] == 100
    assert body["total_calls"] == 1


@pytest.mark.asyncio
async def test_by_subject_returns_that_memory_only(authed, seeded_usage):
    body = (await authed.get(f"/api/v1/usage/by-subject/memory/{_MEMORY_A}")).json()
    assert body["calls"]
    assert all(r["subject_id"] == _MEMORY_A for r in body["calls"])
    assert body["total_calls"] == len(body["calls"])


@pytest.mark.asyncio
async def test_by_subject_says_the_embedding_was_batched(authed, seeded_usage):
    """Rather than reporting the memory's embedding cost as zero, which is as
    wrong as inventing a share of the batch's."""
    body = (await authed.get(f"/api/v1/usage/by-subject/memory/{_MEMORY_A}")).json()
    assert body["batched_embedding"] is True


@pytest.mark.asyncio
async def test_top_ranks_by_cost_descending(authed, seeded_usage):
    body = (await authed.get("/api/v1/usage/top?window=30d&by=cost&limit=5")).json()
    costs = [r["cost_micros"] for r in body["items"]]
    assert costs == sorted(costs, reverse=True)
    assert len(costs) <= 5


@pytest.mark.asyncio
async def test_top_can_rank_by_calls_and_by_duration(authed, seeded_usage):
    for axis in ("calls", "duration"):
        body = (await authed.get(f"/api/v1/usage/top?window=30d&by={axis}")).json()
        values = [r[axis if axis == "calls" else "duration_ms"] for r in body["items"]]
        assert values == sorted(values, reverse=True)


@pytest.mark.asyncio
async def test_an_unknown_ordering_is_refused(authed, seeded_usage):
    r = await authed.get("/api/v1/usage/top?window=30d&by=vibes")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_series_buckets_in_order(authed, session):
    now = datetime.now(timezone.utc)
    session.add_all([
        _row(cost_micros=10, occurred_at=now - timedelta(days=3)),
        _row(cost_micros=20, occurred_at=now - timedelta(days=1)),
        _row(cost_micros=30, occurred_at=now - timedelta(days=1)),
    ])
    await session.commit()
    body = (await authed.get("/api/v1/usage/series?window=30d&bucket=day")).json()
    starts = [b["bucket_start"] for b in body["buckets"]]
    assert starts == sorted(starts)
    assert sum(b["cost_micros"] for b in body["buckets"]) == 60


@pytest.mark.asyncio
async def test_an_unknown_bucket_is_refused(authed, seeded_usage):
    r = await authed.get("/api/v1/usage/series?window=30d&bucket=fortnight")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_an_empty_window_is_zero_not_an_error(authed):
    body = (await authed.get("/api/v1/usage/overview?window=30d")).json()
    assert body["total_calls"] == 0
    assert body["total_cost_micros"] == 0
    assert body["cache_hit_ratio"] is None
