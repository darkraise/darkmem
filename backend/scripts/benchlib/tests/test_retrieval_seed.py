"""DB-backed determinism checks for the fixed-id retrieval corpus.

The gold's whole premise is that ``relevant_memory_ids`` survive a
``DROP SCHEMA`` reseed cycle -- these tests prove the mechanism against the
real bench DB and the real pipeline, so the 100+ pairs in gold.json rest on
verified behaviour, not on the brief's claim.

Pure-parsing gold validation lives in test_retrieval_gold.py, which does
NOT opt into ``_bench_db``.
"""
import uuid

import pytest
from sqlalchemy import select

from benchlib import bench_db, ingest, retrieval_gold
from benchlib.caching_llm import CachingLLMOrchestrator

pytestmark = pytest.mark.usefixtures("_bench_db")

_STUB_EXTRACTION = (
    '{"entities": [], "relationships": [], "memory_type": "fact", '
    '"importance": 0.5, "summary": "stub summary", "emotions": [], "flags": []}'
)


class _StubLLM(CachingLLMOrchestrator):
    async def _live_embed_batch(self, texts):
        return ([[0.1, 0.2, 0.3] for _ in texts], "stub-embed|3")

    async def _live_chat(self, purpose, messages, **kwargs):
        return _STUB_EXTRACTION


_PROBE_ENTRIES = [
    {
        "key": "probe-a",
        "memory_id": "11111111-1111-4111-8111-111111111111",
        "content": "The weather was mild on the first day of the probe.",
        "memory_type": "fact",
        "created_at": "2026-01-02T00:00:00+00:00",
    },
    {
        "key": "probe-b",
        "memory_id": "22222222-2222-4222-8222-222222222222",
        "content": "The weather was cold on the second day of the probe.",
        "memory_type": "fact",
        "created_at": "2026-03-05T12:30:00+00:00",
    },
]


async def _stored_rows():
    from app.models.memory import Memory

    async with bench_db.session_factory() as session:
        rows = (await session.execute(select(Memory))).scalars().all()
    return {str(r.id): r for r in rows}


@pytest.mark.asyncio
async def test_seeded_rows_carry_the_declared_ids_and_dates():
    await bench_db.reset_bench_db()
    prepared = await retrieval_gold.seed_memory_rows(
        bench_db.session_factory, _PROBE_ENTRIES
    )

    assert [str(p["memory_id"]) for p in prepared] == [
        e["memory_id"] for e in _PROBE_ENTRIES
    ]
    rows = await _stored_rows()
    assert set(rows) == {e["memory_id"] for e in _PROBE_ENTRIES}
    assert rows[_PROBE_ENTRIES[0]["memory_id"]].created_at.isoformat() == (
        "2026-01-02T00:00:00+00:00"
    )
    assert rows[_PROBE_ENTRIES[1]["memory_id"]].created_at.isoformat() == (
        "2026-03-05T12:30:00+00:00"
    )


@pytest.mark.asyncio
async def test_reseed_after_drop_schema_yields_identical_ids():
    await bench_db.reset_bench_db()
    await retrieval_gold.seed_memory_rows(bench_db.session_factory, _PROBE_ENTRIES)
    first = set(await _stored_rows())

    await bench_db.reset_bench_db()
    await retrieval_gold.seed_memory_rows(bench_db.session_factory, _PROBE_ENTRIES)
    second = set(await _stored_rows())

    assert first == second == {e["memory_id"] for e in _PROBE_ENTRIES}


@pytest.mark.asyncio
async def test_run_ingest_enriches_the_fixed_ids_not_fresh_ones(tmp_path):
    await bench_db.reset_bench_db()
    prepared = await retrieval_gold.seed_memory_rows(
        bench_db.session_factory, _PROBE_ENTRIES
    )

    llm = _StubLLM({}, cache_dir=str(tmp_path))
    result = await ingest.run_ingest(llm, prepared, ingest.GateConfig())

    assert {o["memory_id"] for o in result.outcomes} == {
        e["memory_id"] for e in _PROBE_ENTRIES
    }
    for outcome in result.outcomes:
        assert outcome["embed"] == "ok"
        assert outcome["vector"] == "ok"


@pytest.mark.asyncio
async def test_reseeding_without_a_reset_fails_loud():
    await bench_db.reset_bench_db()
    await retrieval_gold.seed_memory_rows(bench_db.session_factory, _PROBE_ENTRIES)
    with pytest.raises(Exception, match="(?i)duplicate|unique"):
        await retrieval_gold.seed_memory_rows(
            bench_db.session_factory, _PROBE_ENTRIES
        )


@pytest.mark.asyncio
async def test_the_shipped_corpus_seeds_and_ingests_on_its_fixed_ids(tmp_path):
    """The real corpus.json, end to end: seed every declared row, drive the
    real pipeline over it, and confirm enrichment landed on the declared ids
    -- the exact lifecycle T0.07's scorer will run."""
    entries = retrieval_gold.load_retrieval_corpus()

    await bench_db.reset_bench_db()
    prepared = await retrieval_gold.seed_memory_rows(bench_db.session_factory, entries)

    llm = _StubLLM({}, cache_dir=str(tmp_path))
    result = await ingest.run_ingest(llm, prepared, ingest.GateConfig())

    declared = {str(e["memory_id"]) for e in entries}
    assert {o["memory_id"] for o in result.outcomes} == declared
    failures = [
        o for o in result.outcomes
        if o["embed"] != "ok" or o["vector"] != "ok"
    ]
    assert failures == []

    rows = await _stored_rows()
    assert set(rows) == declared
    by_id = {str(e["memory_id"]): e for e in entries}
    for rid, row in rows.items():
        assert row.created_at.isoformat() == by_id[rid]["created_at"]
