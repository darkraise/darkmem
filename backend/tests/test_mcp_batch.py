"""MCP memory_batch_add must preserve per-entry project.

project is the supersession scope, so dropping it (landing every batch-added
memory in 'default') silently breaks supersession for the primary agent
ingestion path. The single-memory memory_add already threads project; the
batch tool must too.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

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
