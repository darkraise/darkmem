"""T1.04 — ``classifier_kind`` inline on the classification purpose.

``_resolve_classifier`` used to try importing the deleted ``MLProfile`` model
and a ``ml_profile_ref`` field T1.01 also removed, both inside a bare
``except Exception`` — so it logged a full traceback on every resolution and
always fell back to the LLM classifier; ``classifier_kind='local'`` was
unreachable. These tests pin the replacement: the value lives on the
classification purpose row, ``local``/``llm``/absent select the right
classifier object, and the single-call merge (doc 11 §2) narrows to
extraction-only exactly when the local classifier is in play — never for a
new feature flag (CLAUDE.md: no generic ML on/off switch, no classification
on/off flag).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.llm_config import LLMPurposeConfigRow
from app.models.memory import Memory
from app.services.classification_ml import MLClassificationService
import app.services.pipeline as pipeline_mod
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.conftest import test_engine


def _factory():
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _set_classifier_kind(factory, kind: str | None) -> None:
    async with factory() as s:
        row = (await s.execute(
            select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "classification")
        )).scalar_one_or_none()
        if row is None:
            row = LLMPurposeConfigRow(purpose="classification", model="qwen2.5:3b")
            s.add(row)
        row.classifier_kind = kind
        await s.commit()


async def _clear_classification_row(factory) -> None:
    async with factory() as s:
        await s.execute(text("DELETE FROM llm_purpose_configs WHERE purpose = 'classification'"))
        await s.commit()


class _FakeLLM:
    def __init__(self, fingerprint: str):
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, contents, chunk, conc):
        return [[0.1, 0.2, 0.3, 0.4] for _ in contents], self.fingerprint


# --- _resolve_classifier: object selection from the DB row -----------------

@pytest.mark.asyncio
async def test_resolve_classifier_defaults_to_llm_when_row_absent(setup_database):
    factory = _factory()
    await _clear_classification_row(factory)
    pipe = ProcessingPipeline(_FakeLLM("resolve-absent|4"), factory)

    resolved = await pipe._resolve_classifier()

    assert resolved is pipe.classification


@pytest.mark.asyncio
async def test_resolve_classifier_uses_llm_when_kind_is_llm(setup_database):
    factory = _factory()
    try:
        await _set_classifier_kind(factory, "llm")
        pipe = ProcessingPipeline(_FakeLLM("resolve-llm|4"), factory)

        resolved = await pipe._resolve_classifier()

        assert resolved is pipe.classification
    finally:
        await _clear_classification_row(factory)


@pytest.mark.asyncio
async def test_resolve_classifier_uses_local_when_ml_available(setup_database, monkeypatch):
    factory = _factory()
    try:
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: True)
        pipe = ProcessingPipeline(_FakeLLM("resolve-local|4"), factory)

        resolved = await pipe._resolve_classifier()

        assert isinstance(resolved, MLClassificationService)
        assert resolved is not pipe.classification
    finally:
        await _clear_classification_row(factory)


@pytest.mark.asyncio
async def test_resolve_classifier_falls_back_to_llm_when_ml_unavailable(setup_database, monkeypatch):
    """``classifier_kind='local'`` without the optional ``[ml]`` extra must not
    crash a batch — it degrades to the LLM-backed classifier (doc 03 §3.3)."""
    factory = _factory()
    try:
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: False)
        pipe = ProcessingPipeline(_FakeLLM("resolve-no-ml|4"), factory)

        resolved = await pipe._resolve_classifier()

        assert resolved is pipe.classification
    finally:
        await _clear_classification_row(factory)


@pytest.mark.asyncio
async def test_resolve_classifier_is_cached_within_ttl(setup_database, monkeypatch):
    """A second resolution inside the TTL must not hit the DB again — this is
    what keeps ``process_batch`` from a per-batch config round-trip."""
    factory = _factory()
    try:
        await _set_classifier_kind(factory, "llm")
        pipe = ProcessingPipeline(_FakeLLM("resolve-cache|4"), factory)

        first = await pipe._resolve_classifier()

        # If the row disappeared and the cache were not honoured, a stale
        # implementation would still resolve correctly here by falling back
        # to the default, so flip to 'local' underneath the cache instead —
        # a cache-bypassing bug would then return the local classifier.
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: True)
        second = await pipe._resolve_classifier()

        assert first is pipe.classification
        assert second is pipe.classification
    finally:
        await _clear_classification_row(factory)


# --- end-to-end dispatch through process_batch (Ruling 4) ------------------

async def _seed_memory(factory, mem_id, content):
    async with factory() as s:
        s.add(Memory(id=mem_id, content=content, source="api",
                      importance=0.5, metadata_={}))
        await s.commit()


async def _read_classified_type(factory, mem_id):
    async with factory() as s:
        row = (await s.execute(
            text("SELECT classified_type FROM memories WHERE id = :id"),
            {"id": str(mem_id)},
        )).first()
    return row.classified_type


@pytest.mark.asyncio
async def test_classifier_kind_local_skips_the_llm_classification_call(setup_database, monkeypatch):
    """With classifier_kind='local', the in-process classifier runs and the
    LLM-backed ClassificationService.classify is never invoked."""
    _flag_cache_reset()
    factory = _factory()
    mem_id = uuid.uuid4()

    try:
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: True)
        await _seed_memory(factory, mem_id, "the payments worker kept restarting")

        pipe = ProcessingPipeline(_FakeLLM("kind-local|4"), factory)

        extract_calls: list[bool] = []

        async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                                with_classification=False):
            extract_calls.append(with_classification)
            return {"entities": [], "relationships": [], "memory_type": "problem",
                    "importance": 0.7}

        async def llm_classify_must_not_be_called(*args, **kwargs):
            raise AssertionError(
                "classifier_kind=local must not call the LLM-backed classifier"
            )

        monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
        monkeypatch.setattr(pipe.classification, "classify", llm_classify_must_not_be_called)

        await pipe.process_batch([{
            "memory_id": mem_id,
            "content": "the payments worker kept restarting",
            "source": "api",
        }])

        # The local classifier disables the merge: extraction runs without
        # enrichment, classification runs as a separate call against the
        # resolved (local) classifier — never the LLM one.
        assert extract_calls == [False]
        classified_type = await _read_classified_type(factory, mem_id)
        assert classified_type is not None
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(mem_id)})
            await s.commit()
        await _clear_classification_row(factory)


@pytest.mark.asyncio
async def test_classifier_kind_llm_still_merges_in_simple_mode(setup_database, monkeypatch):
    """Regression: classifier_kind='llm' (or absent) with classification_mode
    'simple' must still take the single-call merge path — T1.04's dispatch
    fix must not disturb the existing merge gate."""
    _flag_cache_reset()
    factory = _factory()
    mem_id = uuid.uuid4()

    try:
        await _set_classifier_kind(factory, "llm")
        await _seed_memory(factory, mem_id, "we chose redis for the cache layer")

        pipe = ProcessingPipeline(_FakeLLM("kind-llm-merge|4"), factory)

        extract_calls: list[bool] = []
        classify_calls: list[str] = []

        async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                                with_classification=False):
            extract_calls.append(with_classification)
            return {"entities": [], "relationships": [], "memory_type": "decision",
                    "importance": 0.7, "summary": "Chose Redis.",
                    "emotions": [], "flags": []}

        async def fake_classify(content, areas, prompt, mode="simple"):
            classify_calls.append(content)
            return {"hall": "fact", "summary": None, "emotions": [], "flags": []}

        monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
        monkeypatch.setattr(pipe.classification, "classify", fake_classify)

        await pipe.process_batch([{
            "memory_id": mem_id,
            "content": "we chose redis for the cache layer",
            "source": "api",
        }])

        assert extract_calls == [True]
        assert classify_calls == []
        classified_type = await _read_classified_type(factory, mem_id)
        assert classified_type == "decision"
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(mem_id)})
            await s.commit()
        await _clear_classification_row(factory)
