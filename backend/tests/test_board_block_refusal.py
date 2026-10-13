"""Block verbs refuse registers and plans on both doors (spec 2026-10-13 §2.5)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.services.block_verbs import (
    delete_block,
    insert_block,
    move_block,
    update_block,
)
from app.services.document_door import DocumentMirrorOwned, put_document

FINGERPRINT = "board-refusal-probe|3"
CONTENT = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n"
OWNED = ("superpowers/registers/r.md", "superpowers/plans/p.md")


class StubEmbedder:
    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT

    def llm_fingerprint(self):
        return FINGERPRINT


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def stub_llm(client):
    from app.main import app

    previous = getattr(app.state, "llm", None)
    app.state.llm = StubEmbedder()
    yield app.state.llm
    app.state.llm = previous


async def _file(session, uri):
    filed = await put_document(
        session, None, project="p", uri=uri, content=CONTENT, embed_inline=False,
    )
    ids = [
        row[0] for row in await session.execute(
            text("SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
                 "ORDER BY order_index"),
            {"d": filed.document_id},
        )
    ]
    return filed.document_id, ids


async def _direction(session, document_id):
    return (await session.execute(
        text("SELECT properties->>'ingest_direction' FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": document_id},
    )).scalar_one()


def _verbs(document_id, ids):
    return {
        "update": lambda s, llm: update_block(s, llm, block_id=ids[1], text="changed"),
        "insert": lambda s, llm: insert_block(
            s, llm, document_id=document_id, type="paragraph", text="new",
        ),
        "move": lambda s, llm: move_block(s, llm, block_id=ids[2], after_block_id=None),
        "delete": lambda s, llm: delete_block(s, llm, block_id=ids[2]),
    }


@pytest.mark.parametrize("verb", ["update", "insert", "move", "delete"])
@pytest.mark.parametrize("uri", OWNED)
async def test_every_verb_refuses_a_mirror_owned_document(session, uri, verb):
    document_id, ids = await _file(session, uri)
    with pytest.raises(DocumentMirrorOwned):
        await _verbs(document_id, ids)[verb](session, StubEmbedder())
    assert await _direction(session, document_id) is None


@pytest.mark.parametrize("verb", ["update", "insert", "move", "delete"])
async def test_every_verb_still_accepts_any_other_document(session, verb):
    document_id, ids = await _file(session, "superpowers/specs/s.md")
    await _verbs(document_id, ids)[verb](session, StubEmbedder())
    assert await _direction(session, document_id) == "blocks"


@pytest.mark.parametrize("uri", OWNED)
async def test_rest_answers_422_on_each_block_route(client, auth_headers, session, stub_llm, uri):
    document_id, ids = await _file(session, uri)
    base = f"/api/v1/documents/{document_id}/blocks"
    responses = [
        await client.post(base, json={"type": "paragraph", "text": "new"}, headers=auth_headers),
        await client.patch(f"{base}/{ids[1]}", json={"text": "x"}, headers=auth_headers),
        await client.post(f"{base}/{ids[2]}/move", json={}, headers=auth_headers),
        await client.delete(f"{base}/{ids[2]}", headers=auth_headers),
    ]
    for response in responses:
        assert response.status_code == 422, response.text
        assert "mirror owns" in response.json()["detail"]
    assert await _direction(session, document_id) is None


# One tool per test: a refused tool rolls its session back, which ends the
# test's transaction and takes the filed document with it (conftest `session`).
@pytest.mark.parametrize("tool", ["update", "insert", "move", "delete"])
async def test_mcp_answers_not_convertible_on_each_block_tool(session, monkeypatch, tool):
    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=StubEmbedder()))
    document_id, ids = await _file(session, OWNED[0])
    call = {
        "update": lambda: mcp_server.block_update(block_id=ids[1], text="x"),
        "insert": lambda: mcp_server.block_insert(
            document_id=document_id, type="paragraph", text="new",
        ),
        "move": lambda: mcp_server.block_move(block_id=ids[2]),
        "delete": lambda: mcp_server.block_delete(block_id=ids[2]),
    }[tool]
    body = json.loads(await call())
    assert body["status"] == "not_convertible", body
    assert "mirror owns" in body["reason"]
