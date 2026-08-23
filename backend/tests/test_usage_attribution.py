"""Every call is attributed to the work that caused it.

Three properties, each wrong by default. A batch's coroutines all inherit one
context, so per-memory attribution has to be passed rather than scoped. A
batched embed covers many memories at once, so a per-memory share of it would
be arithmetic presented as an observation. And a job run has no id until after
its runner returns -- a run that reports nothing writes no ``job_runs`` row at
all -- so the subject has to be mintable before the work starts.
"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import LLMPurposeConfig
from app.models.llm_usage import LLMUsage
from app.models.memory import Memory
from app.services.job_registry import Job, JobRegistry
from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from app.services.usage_recorder import UsageRecorder, current_subject
from tests.conftest import test_engine

_EXTRACTION = {
    "entities": [{"name": "PostgreSQL", "type": "technology", "properties": {}}],
    "relationships": [],
    "memory_type": "decision",
    "importance": 0.7,
    "summary": "Picked Postgres.",
    "emotions": [],
    "flags": [],
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/embeddings"):
        body = json.loads(request.content)
        texts = body["input"]
        if isinstance(texts, str):
            texts = [texts]
        return httpx.Response(200, json={
            "data": [{"embedding": [0.1, 0.2, 0.3, 0.4], "index": i}
                     for i in range(len(texts))],
            "usage": {"prompt_tokens": 7},
        })
    return httpx.Response(200, json={
        "choices": [{"message": {"content": json.dumps(_EXTRACTION)}}],
        "usage": {"prompt_tokens": 30, "completion_tokens": 10},
    })


def _orchestrator(factory) -> LLMOrchestrator:
    cfg = LLMPurposeConfig(base_url="http://mock/v1", model="m", dimensions=4)
    llm = LLMOrchestrator(
        {p: cfg for p in ("embedding", "extraction", "classification")},
        recorder=UsageRecorder(factory),
    )
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    return llm


async def _seed(factory, ids, project):
    async with factory() as s:
        for mem_id in ids:
            s.add(Memory(id=mem_id, content=f"content for {mem_id}", source="api",
                         project=project, importance=0.5, metadata_={}))
        await s.commit()


async def _cleanup(factory, ids):
    async with factory() as s:
        await s.execute(text("DELETE FROM llm_usage"))
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in ids]},
        )
        await s.commit()


async def _usage_rows(factory) -> list[LLMUsage]:
    async with factory() as s:
        return list((await s.execute(select(LLMUsage))).scalars().all())


async def _run_batch(monkeypatch, ids, project):
    _flag_cache_reset()
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    await _seed(factory, ids, project)
    llm = _orchestrator(factory)
    pipe = ProcessingPipeline(llm, factory)

    async def resolve_llm():
        return pipe.classification

    monkeypatch.setattr(pipe, "_resolve_classifier", resolve_llm)
    await pipe.process_batch([
        {"memory_id": mem_id, "content": f"content for {mem_id}",
         "source": "api", "project": project}
        for mem_id in ids
    ])
    await llm.close()
    return factory


@pytest.mark.asyncio
async def test_each_memory_in_a_batch_gets_its_own_subject(setup_database, monkeypatch):
    """The trap this pins: asyncio.gather wraps each coroutine in a Task, and
    every Task copies the SAME parent context. Without an explicit per-entry
    value, all three memories attribute to whatever the batch scope held."""
    ids = [uuid.uuid4() for _ in range(3)]
    factory = await _run_batch(monkeypatch, ids, "attr-a")
    try:
        rows = await _usage_rows(factory)
        memory_rows = [r for r in rows if r.subject_type == "memory"]
        assert len(memory_rows) == 3
        assert {r.subject_id for r in memory_rows} == {str(i) for i in ids}
        assert {r.project for r in memory_rows} == {"attr-a"}
        assert all(r.purpose == "extraction" for r in memory_rows)
    finally:
        await _cleanup(factory, ids)


@pytest.mark.asyncio
async def test_a_merged_call_records_once_and_says_it_was_merged(
    setup_database, monkeypatch
):
    """Splitting one call's tokens across two purposes would be invention, so
    the merged call stays one extraction row that declares the merge."""
    ids = [uuid.uuid4()]
    factory = await _run_batch(monkeypatch, ids, "attr-b")
    try:
        rows = await _usage_rows(factory)
        memory_rows = [r for r in rows if r.subject_type == "memory"]
        assert len(memory_rows) == 1
        assert memory_rows[0].usage_raw.get("merged_classification") is True
        assert not [r for r in rows if r.purpose == "classification"]
    finally:
        await _cleanup(factory, ids)


@pytest.mark.asyncio
async def test_batched_embeds_attribute_to_the_batch_not_a_memory(
    setup_database, monkeypatch
):
    """One embed call covers the whole batch, and entity-name embeds are
    deduped and cache-hit across memories, so a per-memory share is undefined,
    not merely imprecise."""
    ids = [uuid.uuid4() for _ in range(2)]
    factory = await _run_batch(monkeypatch, ids, "attr-c")
    try:
        rows = await _usage_rows(factory)
        embeds = [r for r in rows if r.purpose == "embedding"]
        assert embeds
        assert all(r.subject_type == "batch" for r in embeds)
        # One batch, one id -- Phase 1 and Phase 3 are the same unit of work.
        assert len({r.subject_id for r in embeds}) == 1
        assert {r.project for r in embeds} == {"attr-c"}
    finally:
        await _cleanup(factory, ids)


@pytest.mark.asyncio
async def test_a_mixed_project_batch_claims_no_project(setup_database, monkeypatch):
    """The per-memory rows still carry their own project; the batch-level embed
    has no single one, and guessing the first entry's would be a wrong answer
    rather than a missing one."""
    ids = [uuid.uuid4(), uuid.uuid4()]
    _flag_cache_reset()
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        s.add(Memory(id=ids[0], content="a", source="api", project="one",
                     importance=0.5, metadata_={}))
        s.add(Memory(id=ids[1], content="b", source="api", project="two",
                     importance=0.5, metadata_={}))
        await s.commit()
    llm = _orchestrator(factory)
    pipe = ProcessingPipeline(llm, factory)

    async def resolve_llm():
        return pipe.classification

    monkeypatch.setattr(pipe, "_resolve_classifier", resolve_llm)
    try:
        await pipe.process_batch([
            {"memory_id": ids[0], "content": "a", "source": "api", "project": "one"},
            {"memory_id": ids[1], "content": "b", "source": "api", "project": "two"},
        ])
        rows = await _usage_rows(factory)
        embeds = [r for r in rows if r.subject_type == "batch"]
        assert embeds and all(r.project is None for r in embeds)
        memory_rows = [r for r in rows if r.subject_type == "memory"]
        assert {r.project for r in memory_rows} == {"one", "two"}
    finally:
        await llm.close()
        await _cleanup(factory, ids)


@pytest.mark.asyncio
async def test_a_job_run_subject_needs_no_job_runs_row(setup_database):
    """job_runs.id is minted server-side AFTER the runner returns, and a run
    reporting nothing writes no row at all -- so it cannot be the subject."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    seen: list = []

    async def runner():
        seen.append(current_subject.get())
        # 0 is the no-op signal: explicitly nothing happened, so no job_runs
        # row is written at all and there is no id a subject could have used.
        return 0

    registry.register(Job(
        key="usage_attr_noop",
        display_name="Usage attribution probe",
        description="Returns nothing, so it writes no job_runs row.",
        default_cron="0 0 * * *",
        min_interval_seconds=60,
        runner=runner,
    ))
    try:
        await registry.trigger("usage_attr_noop")
        assert len(seen) == 1
        subject = seen[0]
        assert subject is not None
        assert subject.subject_type == "job_run"
        assert subject.subject_id.startswith("usage_attr_noop@")
        async with factory() as s:
            count = (await s.execute(text(
                "SELECT count(*) FROM job_runs WHERE job_key = 'usage_attr_noop'"
            ))).scalar()
        assert count == 0
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM config WHERE key = 'job:usage_attr_noop'"))
            await s.commit()


@pytest.mark.asyncio
async def test_the_scope_is_gone_once_the_run_ends(setup_database):
    """A leaked ambient subject would silently misattribute every later call in
    the process to a job run that finished."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    registry = JobRegistry(factory)

    async def runner():
        return None

    registry.register(Job(
        key="usage_attr_leak",
        display_name="Leak probe",
        description="Probe.",
        default_cron="0 0 * * *",
        min_interval_seconds=60,
        runner=runner,
    ))
    try:
        await registry.trigger("usage_attr_leak")
        assert current_subject.get() is None
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM config WHERE key = 'job:usage_attr_leak'"))
            await s.commit()
