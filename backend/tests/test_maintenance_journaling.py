"""Maintenance operations journal to `events` (T1.63 ruling 2).

Covers the three JobRegistry cleanup runners graph_orphan_cleanup /
tag_orphan_cleanup / expired_memory_cleanup (job_runners.py) directly, and
the `POST /reembed/prune-cache` route (reembed.py) through the HTTP
surface. Every assertion below is a direct check that a `maintenance_run`
row landed with the right operation/outcome -- there is no way for these
to pass with the `record_event` call removed underneath
`record_maintenance_run`, which is the mutation-proof property ruling 2
asks for.

``events`` is append-only (DELETE is rejected at the DB level, doc 04
§8.1), so these tests never try to clean up rows they wrote -- each query
instead scopes to rows created after a timestamp captured at the start of
the test, so a leftover row from an earlier run can never be mistaken for
this run's own.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.services.events import EVENT_TYPES


def test_maintenance_run_is_in_the_closed_vocabulary():
    assert "maintenance_run" in EVENT_TYPES


def _fresh_session_factory():
    """A real engine bound to the test database, independent of the
    `session` fixture's rolled-back transaction -- `record_maintenance_run`
    deliberately opens its own session so a journal write survives whatever
    the caller's own transaction does, and this test proves that by reading
    it back through an entirely separate connection."""
    engine = create_async_engine(settings.test_database_url)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _maintenance_rows_since(factory, operation: str, since: datetime) -> list[dict]:
    async with factory() as session:
        rows = (await session.execute(
            text(
                "SELECT payload FROM events "
                "WHERE event_type = 'maintenance_run' "
                "AND payload->>'operation' = :op "
                "AND created_at >= :since "
                "ORDER BY created_at"
            ),
            {"op": operation, "since": since},
        )).scalars().all()
    return list(rows)


@pytest.mark.asyncio
async def test_graph_orphan_cleanup_journals_its_outcome():
    from app.services.job_runners import make_graph_orphan_cleanup_runner

    factory, engine = _fresh_session_factory()
    try:
        since = datetime.now(timezone.utc)
        # An idle run journals nothing, so give this one an orphan to prune.
        async with factory() as session:
            await session.execute(
                text(
                    "INSERT INTO entities (id, name, entity_type, properties, memory_ids, repo_ids) "
                    "VALUES (gen_random_uuid(), :n, 'concept', '{}', '{}', '{}')"
                ),
                {"n": f"orphan-{uuid.uuid4().hex[:8]}"},
            )
            await session.commit()
        runner = make_graph_orphan_cleanup_runner(factory)
        await runner()

        rows = await _maintenance_rows_since(factory, "graph_orphan_cleanup", since)
        assert rows, "graph_orphan_cleanup did not journal a maintenance_run event"
        last = rows[-1]
        assert last["outcome"] == "ok"
        assert "entities_pruned" in last["detail"]
        assert "relations_pruned" in last["detail"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tag_orphan_cleanup_journals_its_outcome():
    from app.services.job_runners import make_tag_orphan_cleanup_runner

    factory, engine = _fresh_session_factory()
    try:
        since = datetime.now(timezone.utc)
        # An idle run journals nothing, so give this one an orphan to prune.
        async with factory() as session:
            await session.execute(
                text("INSERT INTO tags (name) VALUES (:n)"),
                {"n": f"orphan-{uuid.uuid4().hex[:8]}"},
            )
            await session.commit()
        runner = make_tag_orphan_cleanup_runner(factory)
        await runner()

        rows = await _maintenance_rows_since(factory, "tag_orphan_cleanup", since)
        assert rows, "tag_orphan_cleanup did not journal a maintenance_run event"
        assert rows[-1]["outcome"] == "ok"
        assert "tags_removed" in rows[-1]["detail"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_memory_cleanup_journals_error_and_still_raises():
    """A failing run must journal outcome=error *and* let the original
    exception propagate -- JobRegistry._run_once's own last_status/last_error
    tracking must not be short-circuited by the journaling wrapper."""
    from app.services import supersession as supersession_module

    factory, engine = _fresh_session_factory()

    async def _boom(session, ids):
        raise RuntimeError("synthetic demote_dependents failure")

    original = supersession_module.demote_dependents
    try:
        since = datetime.now(timezone.utc)
        # Force the expired branch: seed one row past its TTL through the
        # SAME factory (a real, independent connection) so the runner's own
        # query sees it.
        async with factory() as seed_session:
            await seed_session.execute(text(
                "INSERT INTO memories (id, content, source, project, "
                "memory_type, status, expires_at) VALUES "
                "(gen_random_uuid(), 'ttl-journaling-test', 'test', 'default', "
                "'fact', 'active', now() - interval '1 hour')"
            ))
            await seed_session.commit()

        # The runner factory does `from app.services.supersession import
        # demote_dependents` at call time, so the patch must land on the
        # source module *before* the factory function runs.
        supersession_module.demote_dependents = _boom
        from app.services.job_runners import make_expired_memory_cleanup_runner
        runner = make_expired_memory_cleanup_runner(factory)
        with pytest.raises(RuntimeError, match="synthetic demote_dependents failure"):
            await runner()

        rows = await _maintenance_rows_since(factory, "expired_memory_cleanup", since)
        assert rows, "a failing run must still journal outcome=error"
        assert rows[-1]["outcome"] == "error"
    finally:
        supersession_module.demote_dependents = original
        async with factory() as cleanup_session:
            await cleanup_session.execute(text(
                "DELETE FROM memories WHERE content = 'ttl-journaling-test'"
            ))
            await cleanup_session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_prune_cache_journals_via_the_request_session(client, auth_headers, session):
    """Queries through the same `session` fixture the route wrote through,
    so this deliberately does NOT filter on `created_at` (the `session`
    fixture's whole test runs inside one outer transaction, and Postgres's
    NOW() is pinned to that transaction's start rather than the statement
    time -- a `created_at >= since` filter captured mid-test would exclude
    every row this test itself just wrote). The single-test transaction
    boundary is what keeps this scoped to this test's own write.

    The fingerprint is registered first because the prune refuses one that is
    not (T2.82) -- that refusal has its own journalling test in
    `test_reembed_prune_cache_guard.py`; this one is about the success path."""
    from app.services.embedder_registry import EmbedderInfo, embedder_registry

    fingerprint = "journaling-test-fp|4"
    await embedder_registry.register(
        session,
        EmbedderInfo(
            fingerprint=fingerprint, model_id="journaling-test-fp", dims=4, source="llm",
        ),
    )
    previous_pipeline = getattr(app.state, "pipeline", None)
    app.state.pipeline = SimpleNamespace(
        llm=SimpleNamespace(llm_fingerprint=lambda: fingerprint)
    )
    try:
        response = await client.post("/api/v1/reembed/prune-cache", headers=auth_headers)
        assert response.status_code == 200, response.text
    finally:
        app.state.pipeline = previous_pipeline
        embedder_registry.forget(fingerprint)

    rows = (await session.execute(
        text(
            "SELECT payload FROM events "
            "WHERE event_type = 'maintenance_run' "
            "AND payload->>'operation' = 'prune_caches' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
    )).scalars().all()
    assert rows, "POST /reembed/prune-cache did not journal a maintenance_run event"
    assert rows[0]["outcome"] == "ok"
    assert rows[0]["detail"]["deleted"] == response.json()["deleted"]


@pytest.mark.asyncio
async def test_reembed_memories_background_task_journals_its_outcome(
    client, auth_headers, monkeypatch,
):
    """POST /reembed/memories dispatches the actual embedding work as a
    background task (`spawn`), so the request returns 202 before the
    journal write happens. Replacing `spawn` with a synchronous variant
    that this test can await makes the background task's own journaling
    deterministic to assert against, without changing its behaviour."""
    import asyncio as asyncio_module
    import app.api.routes.reembed as reembed_module

    tasks: list[asyncio_module.Task] = []

    def _spawn_and_track(coro, *, name=None):
        task = asyncio_module.ensure_future(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr(reembed_module, "spawn", _spawn_and_track)

    previous_pipeline = getattr(app.state, "pipeline", None)
    app.state.pipeline = SimpleNamespace(
        llm=SimpleNamespace(llm_fingerprint=lambda: "journaling-reembed-fp|4")
    )
    since = datetime.now(timezone.utc)
    try:
        response = await client.post("/api/v1/reembed/memories", headers=auth_headers)
        assert response.status_code == 202, response.text
        await asyncio_module.wait_for(asyncio_module.gather(*tasks), timeout=10)
    finally:
        app.state.pipeline = previous_pipeline

    factory, engine = _fresh_session_factory()
    try:
        rows = await _maintenance_rows_since(factory, "reembed_memories", since)
        assert rows, "reembed_memories background task did not journal a maintenance_run event"
        assert rows[-1]["outcome"] in ("ok", "error")
        assert "processed" in rows[-1]["detail"]
        assert "errors" in rows[-1]["detail"]
    finally:
        await engine.dispose()
