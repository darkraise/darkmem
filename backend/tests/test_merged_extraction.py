"""Merged extraction+classification rides one LLM call.

When the classifier is the LLM-backed one and classification_mode is 'simple',
the pipeline asks the extraction call to also return summary/emotions/flags
instead of paying a second round-trip. These tests pin the extraction-service
half of that contract: the schema toggle, the enrichment passthrough, and the
prompt only asking for enrichment when requested.
"""
from __future__ import annotations

import json

import httpx

from app.config import LLMPurposeConfig
from app.services.extraction import ExtractionService
from app.services.extraction_clean import _build_extraction_schema
from app.services.llm import LLMOrchestrator


def test_schema_toggle_adds_only_enrichment_fields():
    base = _build_extraction_schema()
    merged = _build_extraction_schema(with_classification=True)
    for field in ('"summary"', '"emotions"', '"flags"'):
        assert field not in base
        assert field in merged
    # memory_type stays the single type field in both — no second type column.
    assert '"memory_type"' in base
    assert '"memory_type"' in merged
    assert merged.count('"memory_type"') == 1


_MERGED = {
    "entities": [{"name": "PostgreSQL", "type": "technology", "properties": {}}],
    "relationships": [],
    "memory_type": "decision",
    "importance": 0.7,
    "summary": "Chose PostgreSQL for ACID guarantees.",
    "emotions": ["proud"],
    "flags": [],
}


def _service_capturing(raw_content: str, captured: list) -> ExtractionService:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": raw_content}}]}
        )

    config = {
        p: LLMPurposeConfig(base_url="http://mock", model="test")
        for p in ("embedding", "extraction", "reasoning", "summarization")
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExtractionService(llm)


async def test_merged_extract_passes_enrichment_through():
    result = await _service_capturing(json.dumps(_MERGED), []).extract(
        "we chose postgres", with_classification=True,
    )
    assert not result.get("_error")
    assert any(e["name"] == "PostgreSQL" for e in result["entities"])
    assert result["memory_type"] == "decision"
    assert result["summary"] == "Chose PostgreSQL for ACID guarantees."
    assert result["emotions"] == ["proud"]
    assert result["flags"] == []


async def test_default_extract_does_not_request_enrichment():
    cap_merged: list = []
    cap_base: list = []
    await _service_capturing(json.dumps(_MERGED), cap_merged).extract(
        "x", with_classification=True,
    )
    await _service_capturing(json.dumps(_MERGED), cap_base).extract("x")

    merged_prompt = cap_merged[0]["messages"][-1]["content"]
    base_prompt = cap_base[0]["messages"][-1]["content"]
    assert "summary" in merged_prompt
    assert "emotions" in merged_prompt
    assert "summary" not in base_prompt
    assert "emotions" not in base_prompt


# ── pipeline-level gate (drives process_batch against the test DB) ─────────

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine


class _FakeLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, contents, chunk, conc):
        return [[0.1, 0.2, 0.3, 0.4] for _ in contents], self.fingerprint


async def _seed_memory(factory, mem_id, content):
    async with factory() as s:
        s.add(Memory(id=mem_id, content=content, source="api",
                     importance=0.5, metadata_={}))
        await s.commit()


async def _read_memory(factory, mem_id):
    async with factory() as s:
        row = (await s.execute(
            text("SELECT memory_type, classified_type, summary, emotions "
                 "FROM memories WHERE id = :id"), {"id": str(mem_id)},
        )).first()
    return row


@pytest.mark.asyncio
async def test_simple_llm_mode_merges_to_one_call(setup_database, monkeypatch):
    _flag_cache_reset()
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    mem_id = uuid.uuid4()
    await _seed_memory(factory, mem_id, "we chose postgres over mongo")

    pipe = ProcessingPipeline(_FakeLLM("mergeone|4"), factory)

    extract_calls: list[bool] = []
    classify_calls: list[str] = []

    async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                           with_classification=False, usage_subject=None):
        extract_calls.append(with_classification)
        return {"entities": [], "relationships": [], "memory_type": "decision",
                "importance": 0.7, "summary": "Chose Postgres.",
                "emotions": ["proud"], "flags": []}

    async def fake_classify(content, areas, prompt, mode="simple", usage_subject=None):
        classify_calls.append(content)
        return {"hall": "fact", "summary": None, "emotions": [], "flags": []}

    monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
    monkeypatch.setattr(pipe.classification, "classify", fake_classify)

    try:
        await pipe.process_batch([{"memory_id": mem_id,
                                   "content": "we chose postgres over mongo",
                                   "source": "api"}])
        # One merged extraction call carrying enrichment; no separate classify.
        assert extract_calls == [True]
        assert classify_calls == []

        row = await _read_memory(factory, mem_id)
        assert row.memory_type == "decision"
        # classified_type is the SAME normalized label extraction produced.
        assert row.classified_type == "decision"
        assert row.summary == "Chose Postgres."
        assert row.emotions == ["proud"]
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"),
                            {"id": str(mem_id)})
            await s.commit()


@pytest.mark.asyncio
async def test_ml_classifier_keeps_two_calls(setup_database, monkeypatch):
    _flag_cache_reset()
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    mem_id = uuid.uuid4()
    await _seed_memory(factory, mem_id, "the auth service kept crashing")

    pipe = ProcessingPipeline(_FakeLLM("mergetwo|4"), factory)

    extract_calls: list[bool] = []
    ml_calls: list[str] = []

    async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                           with_classification=False, usage_subject=None):
        extract_calls.append(with_classification)
        return {"entities": [], "relationships": [], "memory_type": "problem",
                "importance": 0.7}

    class _FakeML:
        async def classify(self, content, areas, prompt, mode="simple", usage_subject=None):
            ml_calls.append(content)
            return {"hall": "problem", "summary": None, "emotions": [], "flags": []}

    async def resolve_ml():
        return _FakeML()

    monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
    monkeypatch.setattr(pipe, "_resolve_classifier", resolve_ml)

    try:
        await pipe.process_batch([{"memory_id": mem_id,
                                   "content": "the auth service kept crashing",
                                   "source": "api"}])
        # Non-LLM classifier disables the merge: extraction runs without
        # enrichment and the classifier runs as a separate second call.
        assert extract_calls == [False]
        assert ml_calls == ["the auth service kept crashing"]

        row = await _read_memory(factory, mem_id)
        assert row.memory_type == "problem"
        assert row.classified_type == "problem"
        assert row.summary is None
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"),
                            {"id": str(mem_id)})
            await s.commit()
