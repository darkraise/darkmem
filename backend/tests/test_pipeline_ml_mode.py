"""Tests for the ML extraction/classification dispatcher + flag cache."""

import asyncio

import pytest

from app.models.config import Config
from app.services import ml_models as ml_models_module
from app.services import pipeline as pipeline_mod
from app.services.pipeline import (
    _ClassificationDispatcher,
    _ExtractionDispatcher,
    _flag_cache_reset,
    _get_feature_flags_cached,
)


class _StubExtractionLLM:
    def __init__(self):
        self.calls = 0

    async def extract(self, content, system_prompt=None):
        self.calls += 1
        return {
            "memory_type": "fact",
            "importance": 0.5,
            "entities": [{"name": "LLM", "type": "concept", "properties": {}}],
            "relationships": [],
            "_path": "llm",
        }


class _StubExtractionML:
    def __init__(self):
        self.calls = 0

    async def extract(self, content, system_prompt=None):
        self.calls += 1
        return {
            "memory_type": "fact",
            "importance": 0.5,
            "entities": [{"name": "ML", "type": "concept", "properties": {}}],
            "relationships": [],
            "_path": "ml",
        }


class _StubClassificationLLM:
    async def classify(self, content, areas, prompt, mode="simple"):
        return {"hall": "fact", "summary": "llm", "emotions": [], "flags": []}


class _StubClassificationML:
    async def classify(self, content, areas, prompt, mode="simple"):
        return {"hall": "decision", "summary": None, "emotions": [], "flags": []}


class _FakePipeline:
    """Minimal stand-in for ProcessingPipeline holding services + session_factory."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._extraction_llm = _StubExtractionLLM()
        self._extraction_ml = _StubExtractionML()
        self._classification_llm = _StubClassificationLLM()
        self._classification_ml = _StubClassificationML()


async def _set_flag(session, name: str, value: bool):
    row = await session.get(Config, "feature_flags")
    if row is None:
        row = Config(key="feature_flags", value={name: value})
        session.add(row)
    else:
        current = dict(row.value or {})
        current[name] = value
        row.value = current
    await session.commit()


async def test_flag_cache_returns_db_value(session):
    _flag_cache_reset()

    def factory():
        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()

    await _set_flag(session, "ml_extraction", True)
    flags = await _get_feature_flags_cached(factory)
    assert flags["ml_extraction"] is True

    await _set_flag(session, "ml_extraction", False)
    # Still cached, so stale value returned
    flags_cached = await _get_feature_flags_cached(factory)
    assert flags_cached["ml_extraction"] is True

    _flag_cache_reset()
    flags_fresh = await _get_feature_flags_cached(factory)
    assert flags_fresh["ml_extraction"] is False


async def test_extraction_dispatcher_routes_llm_by_default(session, monkeypatch):
    _flag_cache_reset()
    monkeypatch.setattr("app.services.pipeline.models_available", lambda: True)

    def factory():
        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()

    pipeline = _FakePipeline(factory)
    await _set_flag(session, "ml_extraction", False)

    dispatcher = _ExtractionDispatcher(pipeline)
    result = await dispatcher.extract("hello")
    assert result["_path"] == "llm"
    assert pipeline._extraction_llm.calls == 1
    assert pipeline._extraction_ml.calls == 0


async def test_extraction_dispatcher_routes_ml_when_flag_on(session, monkeypatch):
    _flag_cache_reset()
    monkeypatch.setattr("app.services.pipeline.models_available", lambda: True)

    def factory():
        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()

    pipeline = _FakePipeline(factory)
    await _set_flag(session, "ml_extraction", True)

    dispatcher = _ExtractionDispatcher(pipeline)
    result = await dispatcher.extract("hello")
    assert result["_path"] == "ml"
    assert pipeline._extraction_ml.calls == 1
    assert pipeline._extraction_llm.calls == 0


async def test_extraction_dispatcher_falls_back_if_models_missing(session, monkeypatch):
    _flag_cache_reset()
    monkeypatch.setattr("app.services.pipeline.models_available", lambda: False)

    def factory():
        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()

    pipeline = _FakePipeline(factory)
    await _set_flag(session, "ml_extraction", True)

    dispatcher = _ExtractionDispatcher(pipeline)
    result = await dispatcher.extract("hello")
    assert result["_path"] == "llm"
    assert pipeline._extraction_ml.calls == 0


async def test_classification_dispatcher_routes_by_flag(session, monkeypatch):
    _flag_cache_reset()
    monkeypatch.setattr("app.services.pipeline.models_available", lambda: True)

    def factory():
        class _Ctx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()

    pipeline = _FakePipeline(factory)
    dispatcher = _ClassificationDispatcher(pipeline)

    await _set_flag(session, "ml_classification", False)
    res_llm = await dispatcher.classify("text", ["general"], "prompt")
    assert res_llm["hall"] == "fact"
    assert res_llm["summary"] == "llm"

    _flag_cache_reset()
    await _set_flag(session, "ml_classification", True)
    res_ml = await dispatcher.classify("text", ["general"], "prompt")
    assert res_ml["hall"] == "decision"
    assert res_ml["summary"] is None


async def test_health_endpoint_responds_when_models_not_loaded(client, monkeypatch):
    """/api/health/ml_models should return 200 even when models are absent."""
    monkeypatch.setattr(ml_models_module, "_INSTANCE", None)
    resp = await client.get("/api/health/ml_models")
    assert resp.status_code == 200
    body = resp.json()
    assert "enabled" in body
    assert "loaded" in body
    assert body["loaded"] is False
    assert "heads" in body
    assert set(body["heads"].keys()) == {
        "span", "typer", "relation", "classifier", "retriever",
    }
    assert "sources" in body
    assert set(body["sources"].keys()) == {
        "span", "typer", "relation", "classifier", "retriever",
    }
    for entry in body["sources"].values():
        assert entry == {"kind": None, "location": None, "revision": None}
