"""`classifier_kind=local` on an install without torch and transformers.

The shipped image does not carry the `[ml]` extra, so a `local` row used to
fall back to the LLM classifier with nothing but an info line. Now the save is
refused, a row already stored keeps classifying through the LLM classifier
with one error per process, and `/health` says so.
"""
from __future__ import annotations

import logging
import uuid

import pytest
from sqlalchemy import text

import app.services.ml_runtime as ml_runtime
import app.services.pipeline as pipeline_mod
from app.main import app
from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
from tests.test_classifier_kind import (
    _FakeLLM,
    _clear_classification_row,
    _factory,
    _seed_memory,
    _set_classifier_kind,
)


@pytest.fixture
def torch_missing(monkeypatch):
    monkeypatch.setattr(ml_runtime, "ml_extra_available", lambda: False)
    monkeypatch.setattr(pipeline_mod, "_local_classifier_unavailable_logged", False)


async def _classification_row(session, kind: str | None = None) -> None:
    session.add(LLMProviderRow(
        name="classification-vendor", api_kind="openai",
        base_url="https://api.example.invalid/v1",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="classification", model="a-model",
        provider_name="classification-vendor", classifier_kind=kind,
    ))
    await session.flush()


@pytest.mark.asyncio
async def test_saving_local_without_torch_is_refused(
    client, auth_headers, session, monkeypatch, torch_missing,
):
    await _classification_row(session)

    response = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"classification": {"classifier_kind": "local"}},
    )
    assert response.status_code == 422
    assert "torch" in response.text
    stored = (await client.get("/api/v1/config/llm", headers=auth_headers)).json()
    assert stored["classification"]["classifier_kind"] != "local"

    monkeypatch.setattr(ml_runtime, "ml_extra_available", lambda: True)
    response = await client.post(
        "/api/v1/config/llm",
        headers=auth_headers,
        json={"classification": {"classifier_kind": "local"}},
    )
    assert response.status_code == 200
    assert response.json()["classification"]["classifier_kind"] == "local"


@pytest.mark.asyncio
async def test_stored_local_row_classifies_with_the_llm(
    setup_database, monkeypatch, caplog, torch_missing,
):
    _flag_cache_reset()
    factory = _factory()
    mem_ids = [uuid.uuid4(), uuid.uuid4()]
    try:
        await _set_classifier_kind(factory, "local")
        for mem_id in mem_ids:
            await _seed_memory(factory, mem_id, f"we chose redis {mem_id}")

        pipe = ProcessingPipeline(_FakeLLM("local-no-torch|4"), factory)
        pipe._classifier_cache_ttl = 0
        extract_calls: list[bool] = []

        async def fake_extract(content, *, system_prompt=None, relation_rescue=True,
                               with_classification=False, usage_subject=None):
            extract_calls.append(with_classification)
            return {"entities": [], "relationships": [], "memory_type": "decision",
                    "importance": 0.7, "summary": "Chose Redis.",
                    "emotions": ["relief"], "flags": ["milestone"]}

        async def classify_must_not_be_called(*args, **kwargs):
            raise AssertionError("the single-call merge folds classification in")

        monkeypatch.setattr(pipe.extraction, "extract", fake_extract)
        monkeypatch.setattr(pipe.classification, "classify", classify_must_not_be_called)

        with caplog.at_level(logging.ERROR, logger=pipeline_mod.logger.name):
            for mem_id in mem_ids:
                await pipe.process_batch([{
                    "memory_id": mem_id, "content": f"we chose redis {mem_id}",
                    "source": "api",
                }])

        assert extract_calls == [True, True]
        async with factory() as s:
            rows = (await s.execute(
                text("SELECT classified_type, summary, emotions, flags FROM memories "
                     "WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in mem_ids]},
            )).all()
        assert len(rows) == 2
        for row in rows:
            assert row.classified_type == "decision"
            assert row.summary == "Chose Redis."
            assert list(row.emotions) == ["relief"]
            assert list(row.flags) == ["milestone"]
        errors = [r for r in caplog.records
                  if r.levelno == logging.ERROR and "classifier_kind=local" in r.getMessage()]
        assert len(errors) == 1
    finally:
        async with factory() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in mem_ids]},
            )
            await s.commit()
        await _clear_classification_row(factory)


@pytest.mark.asyncio
async def test_health_reports_classifier_unavailable(
    client, session, torch_missing,
):
    original_llm = getattr(app.state, "llm", None)
    app.state.llm = None
    try:
        await _classification_row(session, kind="local")
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["classifier_unavailable"] is True

        await session.execute(text(
            "UPDATE llm_purpose_configs SET classifier_kind = 'llm' "
            "WHERE purpose = 'classification'"
        ))
        await session.flush()
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["classifier_unavailable"] is False
    finally:
        app.state.llm = original_llm
