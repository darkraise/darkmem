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
