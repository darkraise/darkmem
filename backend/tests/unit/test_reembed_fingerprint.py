"""Which partition the re-embed doors act on when ``dimensions`` is unset.

The setup wizard writes the embedding purpose without ``dimensions`` unless
the operator types one, and ``llm_fingerprint()`` then answers the
``model|0`` sentinel. The doors used to act on it directly: every memory
counted as "missing a vector" although all had one, every re-embed failed in
the background ("dims must be positive") and the cache prune refused.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import reembed as routes
from app.repositories.vector import EmbedderFingerprintUnresolved


class _StubLLM:
    def __init__(self, dimensions, embed_result=None, embed_error=None):
        self.config = {"embedding": SimpleNamespace(model="m", dimensions=dimensions)}
        self._embed_result = embed_result
        self._embed_error = embed_error
        self.embed_calls = 0

    def llm_fingerprint(self) -> str:
        return f"m|{self.config['embedding'].dimensions or 0}"

    async def embed(self, text: str):
        self.embed_calls += 1
        if self._embed_error:
            raise self._embed_error
        return self._embed_result


async def test_write_fingerprint_keeps_configured_dimensions_without_an_embed():
    llm = _StubLLM(1024)
    assert await routes._write_fingerprint(llm) == "m|1024"
    assert llm.embed_calls == 0


async def test_write_fingerprint_asks_the_embedder_when_dimensions_are_unset():
    llm = _StubLLM(None, embed_result=([0.0] * 4, "m|1024"))
    assert await routes._write_fingerprint(llm) == "m|1024"
    assert llm.embed_calls == 1


async def test_write_fingerprint_answers_503_when_the_embedder_is_down():
    llm = _StubLLM(None, embed_error=ConnectionError("refused"))
    with pytest.raises(HTTPException) as caught:
        await routes._write_fingerprint(llm)
    assert caught.value.status_code == 503


async def test_read_fingerprint_resolves_the_populated_partition(monkeypatch):
    async def resolve(self, llm):
        return "m|1024"

    monkeypatch.setattr(routes.PostgresVectorRepository, "resolve_read_fingerprint", resolve)
    assert await routes._read_fingerprint(_StubLLM(None), session=None) == "m|1024"


async def test_read_fingerprint_falls_back_to_the_sentinel_when_nothing_is_embedded(monkeypatch):
    async def resolve(self, llm):
        raise EmbedderFingerprintUnresolved("nothing registered")

    monkeypatch.setattr(routes.PostgresVectorRepository, "resolve_read_fingerprint", resolve)
    assert await routes._read_fingerprint(_StubLLM(None), session=None) == "m|0"


async def test_read_fingerprint_keeps_configured_dimensions(monkeypatch):
    async def resolve(self, llm):  # pragma: no cover - must not be reached
        raise AssertionError("configured dimensions need no probe")

    monkeypatch.setattr(routes.PostgresVectorRepository, "resolve_read_fingerprint", resolve)
    assert await routes._read_fingerprint(_StubLLM(768), session=None) == "m|768"
