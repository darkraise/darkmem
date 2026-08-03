"""T2.81 — the empty-text raise's live route, closed at the schema.

T2.69 made ``RerankerService`` raise rather than score a document against
``""``, and its review ruled that raise correct and its disclosure incomplete:
one route can still put an empty-texted row into the corpus. ``MemoryUpdate``
declared ``content: str | None`` with no length floor, so ``PUT
/memories/{id}`` with ``content: ""`` was accepted, the re-embed wrote
``payload.content = ""`` verbatim, and any later search that reranked that row
raised out of the request.

Every link of that chain is executed here rather than argued:

1. the wire accepts (before) and refuses (after) an empty ``content``;
2. the **real** pipeline, over the real database, writes ``payload.content``
   as the content it was handed — so an empty content really does produce an
   empty payload;
3. the **real** ``RerankerService`` raises on that row, and the raise leaves
   ``MemoryService``'s traced search path uncaught.

Residual, stated rather than implied: this closes the ``PUT`` door. It does not
make an empty-texted row unrepresentable — a row already in the corpus from
before this guard, or one written by a direct database write, still reaches the
same raise. Nothing here backfills those, and T2.69's raise is what surfaces
them.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.services.embedder_registry import child_table
from app.services.memory import MemoryService
from app.services.pipeline import _flag_cache_reset
from app.services.reranker import RerankerService
from app.schemas.memory import MemorySearchRequest
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import FakeEmbedder, cleanup, make_pipeline, seed_memories

EXTRACTION = {
    "entities": [],
    "relationships": [],
    "memory_type": "fact",
    "summary": "",
    "emotions": [],
    "flags": [],
}


# ─────────────── 1. the wire ───────────────


@pytest.mark.asyncio
async def test_an_empty_content_is_refused_at_the_update_door(client, session, auth_headers):
    """The one-line guard, asserted where the row would have been written.

    Before ``min_length=1`` this returned 200 and the row's content became
    ``""``. Validation is the right layer for it: the route's other content
    door, ``MemoryCreate``, already carries the same floor, so an empty memory
    was reachable through exactly one of the two.
    """
    memory_id = uuid.uuid4()
    session.add(Memory(id=memory_id, content="postgres runs on the homelab box",
                       source="api", importance=0.5, metadata_={}))
    await session.flush()

    response = await client.put(
        f"/api/v1/memories/{memory_id}", json={"content": ""}, headers=auth_headers,
    )

    assert response.status_code == 422, response.text
    refreshed = await session.get(Memory, memory_id)
    assert refreshed.content == "postgres runs on the homelab box"


@pytest.mark.asyncio
async def test_a_non_empty_content_still_updates(client, session, auth_headers):
    """The floor is a floor and not a ban: one character passes."""
    memory_id = uuid.uuid4()
    session.add(Memory(id=memory_id, content="old text", source="api",
                       importance=0.5, metadata_={}))
    await session.flush()

    response = await client.put(
        f"/api/v1/memories/{memory_id}", json={"content": "x"}, headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["content"] == "x"


def test_the_floor_sits_on_the_model_both_doors_construct():
    """Door parity, by construction rather than by a second route test.

    REST's ``PUT /memories/{id}`` and MCP's ``memory_update`` both build a
    ``MemoryUpdate`` — the MCP door assembles a dict of the fields the caller
    actually set and validates it — so the floor cannot hold on one door and
    not the other. What this asserts is the model's own behaviour; the wire
    test above is what proves the route surfaces it as a 422.

    ``None`` and "absent" stay legal and stay different: absent leaves content
    alone, ``None`` is the same for ``exclude_unset``, and only ``""`` is now
    unrepresentable.
    """
    from pydantic import ValidationError

    from app.schemas.memory import MemoryUpdate

    with pytest.raises(ValidationError):
        MemoryUpdate(content="")

    assert MemoryUpdate().model_dump(exclude_unset=True) == {}
    assert MemoryUpdate(content=None).content is None
    assert MemoryUpdate(content="x").content == "x"


# ─────────────── 2. what the re-embed writes ───────────────


@pytest.mark.asyncio
async def test_the_reembed_writes_the_content_it_was_handed(setup_database, monkeypatch):
    """The middle link, run rather than assumed.

    ``payload["content"]`` is the content verbatim, so the empty string the
    door used to accept became an empty payload on the partition — the row
    every later rerank then choked on. Driving the real pipeline is what makes
    this a measurement of the write rather than a restatement of the code.
    """
    fingerprint = "t2-81-empty|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    (memory_id,) = await seed_memories(factory, ["postgres runs on the homelab box"])

    try:
        pipe = make_pipeline(factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch)
        async with factory() as s:
            await s.execute(
                text("UPDATE memories SET content = '' WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory_id)},
            )
            await s.commit()
        await pipe.process_memory(
            memory_id=memory_id, content="", source="api", tags=[],
            memory_type=None, created_at="2026-08-04T00:00:00+00:00",
        )

        child = child_table("memory_embeddings", fingerprint)
        async with factory() as s:
            stored = (await s.execute(
                text(f"SELECT payload->>'content' FROM {child} "
                     "WHERE memory_id = CAST(:id AS uuid)"),
                {"id": str(memory_id)},
            )).scalar_one()
        assert stored == ""
    finally:
        await cleanup(factory, [memory_id], [fingerprint])
        _flag_cache_reset()


# ─────────────── 3. the raise, on the path that used to 500 ───────────────


class _StubPipeline:
    def __init__(self, llm):
        self.llm = llm


class _StubLLM:
    async def embed(self, query: str):
        return [0.1, 0.1, 0.1, 0.1], "t2-81-search|4"

    async def chat_completion(self, *args, **kwargs):  # pragma: no cover - never reached
        raise AssertionError("the rerank must raise before any LLM call")


@pytest.mark.asyncio
async def test_an_empty_texted_row_raises_out_of_the_traced_search(session, monkeypatch):
    """The uncaught raise T2.81 exists to prevent reaching a caller.

    ``_resolve_document_text`` refuses the row before any LLM call, and
    ``_search_memories_paginated_traced`` has no handler for it, so the
    ``ValueError`` leaves the service — which at the HTTP boundary is a 500. The
    stub orchestrator asserts if it is ever called, so a regression that scored
    the empty document instead of refusing it fails here too rather than
    passing quietly.
    """
    from app.services import hybrid_search

    empty_row = {
        "memory_id": str(uuid.uuid4()),
        "payload": {"content": ""},
        "content": "",
        "rrf_score": 0.1,
    }

    async def _fused(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[empty_row])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _fused)
    monkeypatch.setattr(
        "app.services.memory.get_feature_flags_dict",
        _flags := (lambda _session: _reranker_on()),
    )

    service = MemoryService(session, pipeline=_StubPipeline(_StubLLM()))

    with pytest.raises(ValueError, match="cannot resolve text"):
        await service.search_memories_paginated(
            MemorySearchRequest(query="postgres", with_trace=True)
        )


async def _reranker_on():
    return {"hybrid_search_enabled": True, "reranker_enabled": True}


def test_the_reranker_still_refuses_an_empty_document_directly():
    """T2.69's raise itself, so the guard above cannot pass on a stub's behalf."""
    from app.services.reranker import _resolve_document_text

    with pytest.raises(ValueError, match="cannot resolve text"):
        _resolve_document_text({"content": "", "payload": {"content": ""}}, "content")

    assert RerankerService is not None


# ─────────────── 4. the composition's own window ───────────────


class _NeverAskedReranker:
    async def rerank(self, *args, **kwargs):  # pragma: no cover - never reached
        raise AssertionError("the empty row must be refused before the reranker is called")


@pytest.mark.asyncio
async def test_the_composition_refuses_an_empty_row_before_the_reranker(session):
    """T2.81's second closure: the log-and-pass-through became a raise.

    ``derive_rerank_scores`` used to warn that a textless row "will be scored
    against an empty document" and hand it on — a promise the producer's own
    raise makes false. The two had to move together.

    **This path has no live caller.** ``LayerCompositionService`` is
    instantiated under ``app/`` (MCP's ``knowledge_search``), but nothing
    passes it a ``reranker``, so ``derive_rerank_scores`` returns before it
    reaches a row. The guard is for T2.56/T2.58, and the test drives it
    directly because no productive caller can reach it yet.
    """
    from app.services import layer_composition as lc

    service = lc.LayerCompositionService(None, session, reranker=_NeverAskedReranker())
    textless = lc.memory_candidate(
        {"memory_id": uuid.uuid4(), "payload": {}, "project": "p", "status": "active"},
        channel_rank=1,
    )
    rows = lc.compose([textless]).rows

    with pytest.raises(ValueError, match="resolves to no text"):
        await service.derive_rerank_scores("q", rows)
