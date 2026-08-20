"""T1.18 — ``classifier_kind=local`` narrowing path.

T1.17 shipped the merged extract+classify call for the LLM-backed classifier
in ``simple`` mode. This is the opposite branch: when the classification
purpose resolves to the in-process ``MLClassificationService``, the
extraction call must narrow back to extraction-only (``with_classification=
False``) and classification runs out-of-band. T1.04 made ``classifier_kind``
the only switch and made this path reachable at all; these tests pin two
things that guarantee stay true:

1. The local classifier returns the same ``{hall, summary, emotions, flags}``
   surface the LLM-backed one does (doc 05 §6), so the pipeline's write step
   can treat both uniformly.
2. The narrowed extraction *request* — not merely the local classifier's
   return shape — omits ``summary``/``emotions``/``flags``. Requesting fields
   the local classifier will independently produce wastes tokens and invites
   the two to disagree; asserting only the response shape would miss a
   regression that re-widened the schema while the local classifier still
   produced the right output.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.models.memory import Memory
from app.services.classification_ml import MLClassificationService
from app.services.extraction import ExtractionService
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
            if (await s.execute(
                select(LLMProviderRow).where(LLMProviderRow.name == "t")
            )).scalar_one_or_none() is None:
                s.add(LLMProviderRow(name="t", api_kind="openai", base_url="http://x/v1"))
                await s.flush()
            row = LLMPurposeConfigRow(
                purpose="classification", model="qwen2.5:3b", provider_name="t",
                api_kind="openai", base_url="http://x/v1",
            )
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


class _StubModelManager:
    """Stands in for ``MLModelManager`` so the shape test never loads a real
    HF model — no torch/transformers dependency, no live inference."""

    def __init__(self, label: str, score: float = 0.9):
        self._label = label
        self._score = score
        self.calls: list[str] = []

    async def classify(self, model_repo: str, ttl_seconds: int, content: str) -> tuple[str, float]:
        self.calls.append(content)
        return self._label, self._score


# --- Done-when #1: local classifier surface ---------------------------------

@pytest.mark.asyncio
async def test_local_classifier_returns_shared_surface():
    manager = _StubModelManager("decision")
    svc = MLClassificationService(manager, "fake/local-model", ttl_seconds=0)

    result = await svc.classify("we chose redis for the cache layer", ["general"], "unused", mode="simple")

    assert set(result.keys()) == {"hall", "summary", "emotions", "flags"}
    assert result["hall"] == "decision"
    # ML inference produces only a label — no summary/emotions/flags source.
    assert result["summary"] is None
    assert result["emotions"] == []
    assert result["flags"] == []
    assert manager.calls == ["we chose redis for the cache layer"]


@pytest.mark.asyncio
async def test_local_classifier_falls_back_to_fact_on_unknown_label():
    manager = _StubModelManager("not_a_real_label")
    svc = MLClassificationService(manager, "fake/local-model", ttl_seconds=0)

    result = await svc.classify("some content", ["general"], "unused", mode="simple")

    assert result["hall"] == "fact"


# --- Done-when #2 / Ruling 2: the narrowed request omits dead fields --------

@pytest.mark.asyncio
async def test_classifier_kind_local_extraction_request_omits_classification_fields(
    setup_database, monkeypatch,
):
    """The measurable half: capture the actual extraction request built for a
    classifier_kind=local batch and assert it never asks for summary/
    emotions/flags — not merely that the local classifier's output has the
    right shape."""
    _flag_cache_reset()
    factory = _factory()
    mem_id = uuid.uuid4()

    try:
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: True)
        monkeypatch.setattr(
            "app.services.ml_runtime.ml_model_manager",
            _StubModelManager("problem"),
        )
        async with factory() as s:
            s.add(Memory(id=mem_id, content="the payments worker kept restarting",
                          source="api", importance=0.5, metadata_={}))
            await s.commit()

        pipe = ProcessingPipeline(_FakeLLM("local-narrow|4"), factory)

        captured_requests: list[str] = []

        async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                                with_classification=False):
            request = ExtractionService.build_extraction_request(
                content, system_prompt=system_prompt,
                with_classification=with_classification,
            )
            captured_requests.append(request.messages[-1]["content"])
            return {"entities": [], "relationships": [], "memory_type": "problem",
                    "importance": 0.7}

        async def llm_classify_must_not_be_called(*args, **kwargs):
            raise AssertionError(
                "classifier_kind=local must never call the LLM-backed classifier"
            )

        monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
        monkeypatch.setattr(pipe.classification, "classify", llm_classify_must_not_be_called)

        await pipe.process_batch([{
            "memory_id": mem_id,
            "content": "the payments worker kept restarting",
            "source": "api",
        }])

        assert len(captured_requests) == 1
        request_body = captured_requests[0]
        for dead_field in ('"summary"', '"emotions"', '"flags"'):
            assert dead_field not in request_body, (
                f"narrowed extraction request must omit {dead_field}"
            )
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(mem_id)})
            await s.commit()
        await _clear_classification_row(factory)


# --- Ruling 3: both branches still dispatch (T1.04's guarantee, kept here) --

@pytest.mark.asyncio
async def test_both_classifier_kinds_still_resolve_to_distinct_implementations(
    setup_database, monkeypatch,
):
    """Sanity check that the local and LLM branches remain reachable side by
    side — the full dispatch matrix (cache TTL, [ml]-absent fallback, etc.)
    is T1.04's ``tests/test_classifier_kind.py`` and is not re-litigated
    here; this only confirms T1.18 did not silently collapse the two."""
    factory = _factory()
    try:
        await _set_classifier_kind(factory, "local")
        monkeypatch.setattr(pipeline_mod, "_ml_extra_available", lambda: True)
        pipe_local = ProcessingPipeline(_FakeLLM("both-local|4"), factory)
        local_resolved = await pipe_local._resolve_classifier()
        assert isinstance(local_resolved, MLClassificationService)

        await _set_classifier_kind(factory, "llm")
        pipe_llm = ProcessingPipeline(_FakeLLM("both-llm|4"), factory)
        llm_resolved = await pipe_llm._resolve_classifier()
        assert llm_resolved is pipe_llm.classification
    finally:
        await _clear_classification_row(factory)
