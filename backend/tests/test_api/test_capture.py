"""Tier-A synchronous accept + 202 ack (T1.12, doc 05 §2).

Capture validates against `MemoryCreate`, writes a durable `memory_buffer`
row, journals a `created` event, and returns a 202-style ack carrying the
pre-minted **memory** id — never the buffer row's own id (doc 05 §2.2; T1.10
shipped this conflated once and review unwound it). No embedder, extractor,
or classifier call runs on this path; the buffer flush (T1.13) and the
`wait_process` bypass (T1.14) are what actually drain it later.

`POST /memories` and `memory_add` are deliberately left running their
existing inline pipeline in this task — see the T1.12 amendment log entry.
Cutting them over before the flush job exists would strand every capture
in `memory_buffer` forever (nothing drains it yet) and would break every
test across the floor that expects `create_memory`/`batch_create_memories`
to produce an immediately-queryable `memories` row, since the `wait_process`
opt-in bypass that would restore that capability doesn't exist until T1.14.
`POST /memories/capture` and `memory_capture` are the new, additive doors
this task lands instead.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.api.deps import get_memory_service
from app.api.mcp.client_identity import ORIGIN_HEADER
from app.main import app
from app.models.memory import Memory, MemoryBuffer
from app.services.memory import MemoryService
from app.services.memory_buffer import REPLAYED_METADATA_FIELDS, buffered_memory_id

pytestmark = pytest.mark.asyncio


async def _buffer_count(session) -> int:
    return (await session.execute(select(func.count()).select_from(MemoryBuffer))).scalar()


async def _memories_count(session) -> int:
    return (await session.execute(select(func.count()).select_from(Memory))).scalar()


async def _only_buffer_row(session) -> MemoryBuffer:
    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 1
    return rows[0]


# ── REST: the basic accept contract ─────────────────────────────────


async def test_capture_returns_202_with_pre_minted_memory_id(client, auth_headers, session):
    response = await client.post(
        "/api/v1/memories/capture",
        json={"content": "capture me"},
        headers=auth_headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    ack_id = UUID(body["id"])

    row = await _only_buffer_row(session)
    assert buffered_memory_id(row) == ack_id


async def test_capture_ack_id_is_not_the_buffer_rows_own_id(client, auth_headers, session):
    """Ruling 1: the two ids are deliberately distinct. Returning the buffer
    handle would hand the caller an id that never resolves to anything."""
    response = await client.post(
        "/api/v1/memories/capture", json={"content": "distinct ids"}, headers=auth_headers,
    )
    ack_id = UUID(response.json()["id"])

    row = await _only_buffer_row(session)
    assert row.id != ack_id
    assert buffered_memory_id(row) == ack_id


async def test_capture_writes_no_memories_row(client, auth_headers, session):
    """Tier-A never creates the `memories` row; that's the flush's job."""
    await client.post("/api/v1/memories/capture", json={"content": "buffered only"}, headers=auth_headers)
    assert await _memories_count(session) == 0
    assert await _buffer_count(session) == 1


async def test_capture_validation_failure_writes_nothing(client, auth_headers, session):
    response = await client.post(
        "/api/v1/memories/capture", json={"content": ""}, headers=auth_headers,
    )
    assert response.status_code == 422
    assert await _buffer_count(session) == 0


async def test_capture_requires_auth(client):
    response = await client.post("/api/v1/memories/capture", json={"content": "no auth"})
    assert response.status_code in (401, 403)


# ── No model call: proven structurally, not by timing ───────────────


class _ExplodingPipeline:
    """Any attribute access yields a coroutine that fails the test. Standing
    in for the LLM orchestrator: if `accept_capture` ever reaches it, the
    "no model call on this path" invariant is broken."""

    def __getattr__(self, name):
        async def _boom(*args, **kwargs):
            raise AssertionError(f"accept_capture must never call pipeline.{name}")
        return _boom


async def test_capture_never_touches_the_pipeline(client, auth_headers, session):
    async def _override():
        return MemoryService(session, pipeline=_ExplodingPipeline())

    app.dependency_overrides[get_memory_service] = _override
    try:
        response = await client.post(
            "/api/v1/memories/capture", json={"content": "no model calls here"}, headers=auth_headers,
        )
        assert response.status_code == 202
    finally:
        del app.dependency_overrides[get_memory_service]


# ── Every captured field replays, including `metadata` ──────────────


async def test_capture_replays_every_field(client, auth_headers, session):
    payload = {
        "content": "full field capture",
        "tags": ["project/darkmem"],
        "source": "test",
        "source_agent": "agent/1.0",
        "memory_type": "decision",
        "importance": 0.9,
        "metadata": {"repo_hint": "github.com/x/y"},
        "expires_at": "2027-01-01T00:00:00+00:00",
        "project": "proj-capture",
        "origin_key": "session-1",
    }
    response = await client.post("/api/v1/memories/capture", json=payload, headers=auth_headers)
    assert response.status_code == 202

    row = await _only_buffer_row(session)
    for field in REPLAYED_METADATA_FIELDS:
        assert field in row.metadata_, f"{field} was dropped by the accept path"
    assert row.metadata_["memory_type"] == "decision"
    assert row.metadata_["tags"] == ["project/darkmem"]
    assert row.metadata_["importance"] == 0.9
    assert row.metadata_["expires_at"] == "2027-01-01T00:00:00+00:00"
    assert row.metadata_["source_agent"] == "agent/1.0"
    assert row.metadata_["metadata"] == {"repo_hint": "github.com/x/y"}
    assert row.metadata_["origin_key"] == "test:session-1"
    assert row.project == "proj-capture"
    assert row.source == "test"


# ── origin_key resolution reuses T1.11, not a fresh implementation ──


async def test_capture_origin_key_from_header(client, auth_headers, session):
    response = await client.post(
        "/api/v1/memories/capture",
        json={"content": "header origin", "source": "test"},
        headers={**auth_headers, ORIGIN_HEADER: "boot-xyz"},
    )
    assert response.status_code == 202
    row = await _only_buffer_row(session)
    assert row.metadata_["origin_key"] == "test:boot-xyz"


async def test_capture_unknown_origin_collapses_to_one(client, auth_headers, session):
    """Doc 05 §2.1 / §12: a per-request random is forbidden. Two undeclared
    captures from the same source/project must produce the SAME origin_key,
    not two fresh ones."""
    await client.post(
        "/api/v1/memories/capture", json={"content": "first", "source": "test"}, headers=auth_headers,
    )
    await client.post(
        "/api/v1/memories/capture", json={"content": "second", "source": "test"}, headers=auth_headers,
    )
    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 2
    origins = {r.metadata_["origin_key"] for r in rows}
    assert origins == {"unknown:test:default"}


# ── Batch capture: one buffer row per entry ─────────────────────────


async def test_capture_batch_writes_one_row_per_entry(client, auth_headers, session):
    response = await client.post(
        "/api/v1/memories/capture/batch",
        json={"entries": [{"content": "b1"}, {"content": "b2"}, {"content": "b3"}]},
        headers=auth_headers,
    )
    assert response.status_code == 202
    acks = response.json()
    assert len(acks) == 3
    ids = {a["id"] for a in acks}
    assert len(ids) == 3  # every ack id is distinct

    assert await _buffer_count(session) == 3
    assert await _memories_count(session) == 0


async def test_capture_batch_rejects_over_the_cap(client, auth_headers, session):
    entries = [{"content": f"entry {i}"} for i in range(101)]
    response = await client.post(
        "/api/v1/memories/capture/batch", json={"entries": entries}, headers=auth_headers,
    )
    assert response.status_code == 422
    assert await _buffer_count(session) == 0


# ── Both front doors accept identically (invariant 17) ──────────────


@asynccontextmanager
async def _fake_mcp_session(session):
    yield session


async def test_mcp_capture_parity_with_rest(client, auth_headers, session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_mcp_session(session))
    mcp_server.set_pipeline(None)

    rest_response = await client.post(
        "/api/v1/memories/capture", json={"content": "rest door", "source": "test"}, headers=auth_headers,
    )
    assert rest_response.status_code == 202

    raw = await mcp_server.memory_capture(content="mcp door", source="test")
    mcp_ack = json.loads(raw)
    assert mcp_ack["status"] == "accepted"
    UUID(mcp_ack["id"])  # a real uuid, not the buffer row's own id

    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 2
    assert await _memories_count(session) == 0
    for row in rows:
        # Same invariant on both doors: the ack id is never the buffer id.
        assert buffered_memory_id(row) != row.id


async def test_mcp_capture_batch_mirrors_rest_cap(session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_mcp_session(session))
    mcp_server.set_pipeline(None)

    entries = [{"content": f"entry {i}"} for i in range(101)]
    with pytest.raises(Exception):
        await mcp_server.memory_capture_batch(entries=entries)
    assert await _buffer_count(session) == 0


async def test_mcp_capture_makes_no_model_call(session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_mcp_session(session))
    mcp_server.set_pipeline(_ExplodingPipeline())
    try:
        raw = await mcp_server.memory_capture(content="mcp no model call")
    finally:
        mcp_server.set_pipeline(None)

    ack = json.loads(raw)
    assert ack["status"] == "accepted"
    assert await _buffer_count(session) == 1
