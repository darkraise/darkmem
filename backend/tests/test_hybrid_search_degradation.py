"""Hybrid search must not mask a total backend outage as 'no results'.

If BOTH the semantic and keyword sides error, returning an empty list is
indistinguishable from a genuine no-match — the caller (and the agent) sees
'nothing found' while the search backend is actually down. The service should
raise so the failure is loud. A one-sided failure still degrades gracefully.

The sides fail here *in Python*, before any statement reaches a database, so
these stubs pin the pre-SQL half of the contract only. A failure the database
itself raises aborts the transaction and is a different path, pinned against
the live database in ``test_hybrid_search.py``.
"""
from __future__ import annotations

import contextlib

import pytest

from app.services import hybrid_search
from app.services.hybrid_search import HybridSearchService


class _FakeLLM:
    async def embed(self, query):
        return [0.1, 0.2, 0.3], "model|3"


class _StubSession:
    """The part of ``AsyncSession`` the service reaches for.

    ``begin_nested`` is a no-op here and has to be: these stubs never open a
    transaction, so there is nothing for a savepoint to roll back to. It must
    not swallow the exception either, or the degradation under test would stop
    being observable.
    """

    @contextlib.asynccontextmanager
    async def begin_nested(self):
        yield


class _BoomSession(_StubSession):
    """Every query raises — simulates the DB / partition being unavailable."""

    async def execute(self, *args, **kwargs):
        raise RuntimeError("backend down")


class _SemanticOnlyBoomSession(_StubSession):
    """Semantic query raises; keyword query returns no rows."""

    def __init__(self):
        self._calls = 0

    async def execute(self, *args, **kwargs):
        self._calls += 1
        if self._calls == 1:  # _semantic_search runs first
            raise RuntimeError("partition missing")
        return _EmptyResult()


class _EmptyResult:
    def __iter__(self):
        return iter(())


async def test_search_raises_when_both_sides_fail():
    svc = HybridSearchService(_FakeLLM(), _BoomSession())
    with pytest.raises(Exception):
        await svc.search("anything")


async def test_search_degrades_gracefully_when_only_one_side_fails():
    svc = HybridSearchService(_FakeLLM(), _SemanticOnlyBoomSession())
    # Keyword side returned no rows, but the call must not raise — a one-sided
    # failure is acceptable degradation, just an empty (not errored) result.
    assert await svc.search("anything") == []


class _DownLLM:
    """The embedder is unreachable: every query embed raises, and is counted."""

    def __init__(self):
        self.calls = 0

    async def embed(self, query):
        self.calls += 1
        raise ConnectionError("All connection attempts failed")


class _KeywordRow:
    memory_id = "018f0000-0000-7000-8000-000000000001"
    rank = 0.5
    content = "ollama moved hosts"
    project = "default"
    status = "active"


class _KeywordOnlySession(_StubSession):
    """Only the keyword statement ever arrives, and it matches one row."""

    def __init__(self):
        self.statements = 0

    async def execute(self, *args, **kwargs):
        self.statements += 1
        return [_KeywordRow()]


@pytest.fixture
def quiet_search(monkeypatch):
    """No access-counter flush and no cooldown carried between tests."""
    monkeypatch.setattr(HybridSearchService, "_record_access", staticmethod(lambda rows: None))
    monkeypatch.setattr(hybrid_search, "_embedder_retry_at", 0.0)


async def test_search_answers_on_keyword_when_the_embedder_is_unreachable(quiet_search):
    session = _KeywordOnlySession()
    rows = await HybridSearchService(_DownLLM(), session).search("ollama")

    assert [row["memory_id"] for row in rows] == [_KeywordRow.memory_id]
    assert session.statements == 1


async def test_trace_names_the_semantic_arm_failed_when_the_embedder_is_unreachable(quiet_search):
    trace = await HybridSearchService(_DownLLM(), _KeywordOnlySession()).search_with_trace("ollama")

    assert [row["memory_id"] for row in trace.results] == [_KeywordRow.memory_id]
    assert trace.semantic_ran is True
    assert trace.semantic_failed is True
    assert trace.keyword_failed is False


async def test_search_raises_when_the_embedder_and_the_keyword_side_are_both_down(quiet_search):
    with pytest.raises(RuntimeError, match="both semantic and keyword"):
        await HybridSearchService(_DownLLM(), _BoomSession()).search("anything")


async def test_an_unreachable_embedder_is_not_dialled_again_inside_the_cooldown(
    quiet_search, monkeypatch,
):
    clock = [1000.0]
    monkeypatch.setattr(hybrid_search.time, "monotonic", lambda: clock[0])
    llm = _DownLLM()
    svc = HybridSearchService(llm, _KeywordOnlySession())

    await svc.search("first")
    trace = await svc.search_with_trace("second")
    assert llm.calls == 1
    assert trace.semantic_failed is True

    clock[0] += hybrid_search.EMBEDDER_RETRY_COOLDOWN_SECONDS
    await svc.search("third")
    assert llm.calls == 2
