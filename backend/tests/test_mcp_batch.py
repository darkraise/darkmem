"""MCP memory_batch_add must preserve per-entry project.

project is the supersession scope, so dropping it (landing every batch-added
memory in 'default') silently breaks supersession for the primary agent
ingestion path. The single-memory memory_add already threads project; the
batch tool must too.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from pydantic import ValidationError
from sqlalchemy import select

import app.api.mcp.server as mcp_server
from app.api.mcp.server import memory_batch_add, set_pipeline
from app.models.memory import Memory


async def test_memory_batch_add_preserves_project(session, monkeypatch):
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    set_pipeline(None)  # skip pipeline processing (no embedder network calls)

    raw = await memory_batch_add(
        entries=[
            {"content": "alpha fact", "project": "proj-x"},
            {"content": "beta fact", "project": "proj-x"},
        ],
        wait_process=True,
    )
    assert len(json.loads(raw)) == 2

    rows = (
        await session.execute(select(Memory).where(Memory.project == "proj-x"))
    ).scalars().all()
    assert len(rows) == 2


@pytest.fixture
def mcp_session(session, monkeypatch):
    """Point the MCP tools' module-level session factory at the test session."""
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", None)
    return session


def _entries(n: int) -> list[dict]:
    return [{"content": f"cap probe {i}"} for i in range(n)]


@pytest.mark.parametrize("count", [0, 101])
async def test_batch_cap_rejects_both_ends(mcp_session, count):
    """The MCP batch cap mirrors HTTP's 1-100 exactly at both ends.

    The upper bound is the one that protects the box; the lower bound is what
    stops an empty batch being accepted as a successful no-op, which reads to
    an agent as "stored" (CLAUDE.md: memory_batch_add mirrors the HTTP 1-100
    batch cap).
    """
    with pytest.raises(ValidationError):
        await memory_batch_add(entries=_entries(count), wait_process=True)


@pytest.mark.parametrize("count", [1, 100])
async def test_batch_cap_accepts_both_bounds(mcp_session, count):
    """1 and 100 are inside the cap, so neither boundary is off by one."""
    results = json.loads(
        await memory_batch_add(entries=_entries(count), wait_process=True)
    )
    assert len(results) == count


async def test_batch_identity_resolves_on_the_raw_dicts_before_validation(
    mcp_http_client, monkeypatch,
):
    """Identity must be resolved on what the caller sent, not on what the
    schema decided it meant.

    This pins the ORDER, not just the outcome. Moving resolution after
    validation is the "simplification" that still passes on REST -- where
    `api` is REST's own sentinel, so absent and explicit resolve identically --
    and fails on MCP, where `api` is a foreign literal that dodges MCP's `mcp`
    sentinel. The entries reaching MemoryBatchCreate must already carry a
    resolved identity; if resolution moves after it, they arrive raw and this
    fails.
    """
    real = mcp_server.MemoryBatchCreate
    captured: dict = {}

    def _capture(*, entries):
        captured["entries"] = [dict(e) if isinstance(e, dict) else e for e in entries]
        return real(entries=entries)

    monkeypatch.setattr(mcp_server, "MemoryBatchCreate", _capture)

    response = await mcp_http_client.post(
        "/",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "memory_batch_add",
                "arguments": {
                    "wait_process": True,
                    "entries": [{"content": "raw dict ordering probe"}],
                },
            },
        },
        headers={"X-Darkmem-Client": "codex"},
    )
    assert response.status_code == 200, response.text

    entry = captured["entries"][0]
    assert entry["source"] == "codex"
    assert entry["source_agent"].startswith("python-httpx/")
    assert entry["origin_key"] == "unknown:codex:default"
