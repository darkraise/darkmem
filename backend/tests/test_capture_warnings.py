"""The memory-door warning (work-log spec §5) on all four capture doors."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from sqlalchemy import func, select, text

from app.models.memory import MemoryBuffer
from app.schemas.memory import MemoryCreate
from app.services import capture_lint
from app.services.memory import MemoryService
from app.services.events import EVENT_TYPES

LOG = "Task 5 complete: 7708 passed after merging e4363418."
FACT = "Postgres must listen on all addresses because the API connects across the stack network."


def test_the_vocabulary_carries_capture_flagged():
    from tests.test_event_taxonomy_map import _parse_frontend_map

    assert "capture_flagged" in EVENT_TYPES
    tabbed, _untabbed = _parse_frontend_map()
    assert "capture_flagged" in tabbed


async def _flagged(session):
    rows = await session.execute(text(
        "SELECT object_type, object_id, project, source, payload FROM events "
        "WHERE event_type = 'capture_flagged' ORDER BY created_at, id"
    ))
    return rows.all()


@asynccontextmanager
async def _on_the_test_session(session):
    yield session


def _mcp_on(session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _on_the_test_session(session))
    mcp_server.set_pipeline(None)
    return mcp_server


async def test_a_flagged_capture_is_buffered_answered_and_journalled(session):
    found, warnings = capture_lint.lint(LOG)
    result = await MemoryService(session).create_memory(
        MemoryCreate(content=LOG, source="test", project="proj"), api_key_id=None,
    )
    assert warnings and result.ack.warnings == warnings
    assert (await session.execute(select(func.count()).select_from(MemoryBuffer))).scalar() == 1
    [(object_type, object_id, project, source, payload)] = await _flagged(session)
    assert (object_type, object_id, project, source) == ("memory", result.ack.id, "proj", "test")
    assert payload == {"signals": found}


async def test_a_clean_capture_has_no_warning_and_no_row(session):
    result = await MemoryService(session).create_memory(
        MemoryCreate(content=FACT, source="test"), api_key_id=None,
    )
    assert result.ack.warnings == []
    assert await _flagged(session) == []


async def test_a_batch_answers_warnings_per_entry(session):
    results = await MemoryService(session).batch_create_memories(
        [MemoryCreate(content=FACT, source="test"), MemoryCreate(content=LOG, source="test")],
        api_key_id=None,
    )
    assert [r.ack.warnings for r in results] == [[], capture_lint.lint(LOG)[1]]
    assert [row.object_id for row in await _flagged(session)] == [results[1].ack.id]


async def test_the_rest_doors_answer_warnings_on_the_ack(client, auth_headers, session):
    flagged = await client.post("/api/v1/memories", json={"content": LOG}, headers=auth_headers)
    assert flagged.status_code == 202
    assert flagged.json()["warnings"] == capture_lint.lint(LOG)[1]

    clean = await client.post("/api/v1/memories", json={"content": FACT}, headers=auth_headers)
    assert clean.json()["warnings"] == []

    batch = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": LOG}, {"content": FACT}]}, headers=auth_headers,
    )
    assert batch.status_code == 202
    assert [entry["warnings"] for entry in batch.json()] == [capture_lint.lint(LOG)[1], []]


async def test_the_mcp_doors_answer_warnings_on_the_ack(session, monkeypatch):
    mcp_server = _mcp_on(session, monkeypatch)

    ack = json.loads(await mcp_server.memory_add(content=LOG))
    assert ack["status"] == "accepted"
    assert ack["warnings"] == capture_lint.lint(LOG)[1]

    acks = json.loads(await mcp_server.memory_batch_add(entries=[{"content": FACT}, {"content": LOG}]))
    assert [a["warnings"] for a in acks] == [[], capture_lint.lint(LOG)[1]]
