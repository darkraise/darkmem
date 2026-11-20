"""Every door that replays a stored memory hands `process_batch` the same entry.

A replay entry built in three places drifted: two of them dropped `project`, so
a retried ingest ran (and was billed) with no project. The replay also used to
let the extractor's guess overwrite an `importance` the caller had set.
"""
from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

import app.api.routes.pipeline_failures as failures_route
from app.main import app
from app.models.memory import Memory
from app.services.extraction import ExtractionService
from app.services.pipeline_failures import RETRY_HANDLERS, PipelineFailureService
from tests.test_pipeline_savepoints import EXTRACTION, VECTOR, savepoint_bed

FAILURES = "/api/v1/pipeline-failures"


class RecordingPipeline:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def process_batch(self, entries: list[dict]) -> list[dict]:
        self.entries.extend(entries)
        return [{"error": None} for _ in entries]


async def _alpha_memory_with_failure(session) -> uuid.UUID:
    memory_id = uuid.uuid4()
    session.add(Memory(
        id=memory_id, content="alpha's memory", source="api", project="alpha",
        importance=0.5, metadata_={},
    ))
    await session.flush()
    await PipelineFailureService(session).record(
        entity_type="memory", entity_id=memory_id, pipeline_name="memory_ingest",
        failed_step="extraction", error_message="boom",
    )
    await session.commit()
    return memory_id


@pytest.mark.asyncio
async def test_every_retry_door_carries_the_project(
    client, auth_headers, session, session_factory, monkeypatch,
):
    from app.services.pipeline import memory_retry_handler

    memory_id = await _alpha_memory_with_failure(session)
    pipeline = RecordingPipeline()
    spawned = []
    monkeypatch.setattr(failures_route, "spawn", lambda coro, **_: spawned.append(coro))
    monkeypatch.setattr(failures_route, "async_session_factory", session_factory)
    monkeypatch.setattr(app.state, "pipeline", pipeline, raising=False)

    # The failure-retry route's bulk path builds the entries itself.
    response = await client.post(
        f"{FAILURES}/retry-all", params={"pipeline_name": "memory_ingest"},
        headers=auth_headers,
    )
    assert response.status_code == 202
    for coro in spawned:
        await coro
    spawned.clear()

    # A single retry runs the handler the app registers at boot.
    monkeypatch.setitem(
        RETRY_HANDLERS, "memory_ingest", memory_retry_handler(pipeline, session_factory),
    )
    failure_id = (await session.execute(
        text("SELECT id FROM pipeline_failures WHERE entity_id = CAST(:m AS uuid)"),
        {"m": str(memory_id)},
    )).scalar_one()
    response = await client.post(f"{FAILURES}/{failure_id}/retry", headers=auth_headers)
    assert response.status_code == 202
    for coro in spawned:
        await coro

    response = await client.post("/api/v1/analytics/reprocess", headers=auth_headers)
    assert response.status_code == 200

    replayed = [e for e in pipeline.entries if e["memory_id"] == memory_id]
    assert len(replayed) == 3
    assert [e["project"] for e in replayed] == ["alpha", "alpha", "alpha"]


async def _importance(bed) -> float:
    async with bed.factory() as s:
        return (await s.execute(
            text("SELECT importance FROM memories WHERE id = CAST(:m AS uuid)"),
            {"m": str(bed.memory_id)},
        )).scalar_one()


async def _set_importance(bed, value: float) -> None:
    async with bed.factory() as s:
        await s.execute(
            text("UPDATE memories SET importance = :v WHERE id = CAST(:m AS uuid)"),
            {"v": value, "m": str(bed.memory_id)},
        )
        await s.commit()


@pytest.mark.asyncio
async def test_caller_importance_survives_extraction(setup_database):
    content = "pgvector replaces faiss"
    scored = {**EXTRACTION, "importance": 0.3}

    async with savepoint_bed([content], "entries-caller|4", extraction=scored) as bed:
        await _set_importance(bed, 0.9)
        await bed.pipe.process_batch([bed.entry(content=content)])
        assert await _importance(bed) == pytest.approx(0.9)

    failed = ExtractionService._error_result("Invalid JSON: boom")
    async with savepoint_bed([content], "entries-failed|4", extraction=failed) as bed:
        await _set_importance(bed, 0.9)
        await bed.pipe.process_batch([bed.entry(content=content)])
        assert await _importance(bed) == pytest.approx(0.9)

    async with savepoint_bed([content], "entries-default|4", extraction=scored) as bed:
        status = await bed.pipe._write_memory(
            bed.entry(content=content), VECTOR, bed.fingerprint, bed.fingerprint,
            dict(scored), None, {}, {},
        )
        assert status["vector"] == "ok"
        assert await _importance(bed) == pytest.approx(0.3)


def test_reasoning_budget_is_its_own_constant():
    from app.services import memory

    assert isinstance(memory.REASONING_CONTEXT_CHARS, int)

    services = Path(memory.__file__).parent
    declaring = []
    for path in sorted(services.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            targets = (
                node.targets if isinstance(node, ast.Assign)
                else [node.target] if isinstance(node, ast.AnnAssign) else []
            )
            if any(isinstance(t, ast.Name) and t.id == "_MAX_CONTENT_CHARS" for t in targets):
                declaring.append(path.name)
    assert declaring == ["extraction_clean.py"]
