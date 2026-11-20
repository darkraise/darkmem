"""Document doors: what a malformed block id answers, and who a subtree
rename is attributed to."""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.services.document_door import put_document

FINGERPRINT = "door-inputs-probe|3"


class StubEmbedder:
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
def mcp_server(session, monkeypatch):
    import app.api.mcp.server as server

    @asynccontextmanager
    async def _on_the_test_session():
        yield session

    monkeypatch.setattr(server, "async_session_factory", lambda: _on_the_test_session())
    monkeypatch.setattr(server, "_pipeline", SimpleNamespace(llm=StubEmbedder()))
    return server


@pytest.fixture
def route_llm():
    from app.api.deps import get_llm
    from app.main import app

    app.dependency_overrides[get_llm] = lambda: StubEmbedder()
    yield
    app.dependency_overrides.pop(get_llm, None)


async def test_malformed_block_ids_answer_422(
    client, auth_headers, session, mcp_server, route_llm,
):
    filed = await put_document(
        session, StubEmbedder(), project="door-inputs", uri="a.md", content="# A\n\nBody.\n",
    )
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()
    base = f"/api/v1/documents/{filed.document_id}/blocks"

    for field in ("parent_id", "after_block_id"):
        answer = await client.post(
            base, json={"type": "paragraph", "text": "x", field: "nope"}, headers=auth_headers,
        )
        assert answer.status_code == 422, (field, answer.text)
    answer = await client.post(
        f"{base}/{block_id}/move", json={"new_parent_id": "nope"}, headers=auth_headers,
    )
    assert answer.status_code == 422, answer.text

    for field in ("parent_id", "after_block_id"):
        with pytest.raises(ValueError, match=f"{field} is not a uuid"):
            await mcp_server.block_insert(
                document_id=filed.document_id, type="paragraph", text="x", **{field: "nope"},
            )
    with pytest.raises(ValueError, match="new_parent_id is not a uuid"):
        await mcp_server.block_move(block_id=block_id, new_parent_id="nope")


async def _updated_rows(session, project):
    rows = await session.execute(
        text(
            "SELECT e.actor, CAST(e.api_key_id AS text) FROM events e "
            "JOIN documents d ON d.id = e.object_id "
            "WHERE e.event_type = 'document_updated' AND d.project = :p"
        ),
        {"p": project},
    )
    return [tuple(row) for row in rows]


async def test_subtree_rename_journals_its_actor(
    client, auth_headers, session, mcp_server, monkeypatch,
):
    for uri in ("rest/a.md", "rest/b.md"):
        await put_document(
            session, StubEmbedder(), project="rename-rest", uri=uri, content="# A\n",
        )
    answer = await client.post(
        "/api/v1/documents/rename",
        json={"project": "rename-rest", "uri_prefix": "rest", "new_uri_prefix": "moved"},
        headers=auth_headers,
    )
    assert answer.status_code == 200, answer.text
    assert await _updated_rows(session, "rename-rest") == [("admin", None), ("admin", None)]

    key_id = uuid.uuid4()
    monkeypatch.setattr(mcp_server, "current_key_name", lambda: "rename-key")
    monkeypatch.setattr(mcp_server, "current_api_key_id", lambda: key_id)
    for uri in ("mcp/a.md", "mcp/b.md"):
        await put_document(
            session, StubEmbedder(), project="rename-mcp", uri=uri, content="# A\n",
        )
    result = json.loads(await mcp_server.document_update(
        project="rename-mcp", uri_prefix="mcp", new_uri_prefix="moved",
    ))
    assert result.get("renamed") == 2, result
    assert await _updated_rows(session, "rename-mcp") == [
        ("rename-key", str(key_id)), ("rename-key", str(key_id)),
    ]
