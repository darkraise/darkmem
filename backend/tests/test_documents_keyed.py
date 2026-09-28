"""Which document doors a `dmk_` key reaches, and the sync manifest."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services.api_keys import issue_key

V1 = "/api/v1/documents"
FINGERPRINT = "keyed-probe|4"


class _ScriptedEmbedder:
    """Enough of the orchestrator for put_document to embed without a network."""

    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0, 0.0], FINGERPRINT


@pytest.fixture
def scripted_embedder(client):
    from app.main import app
    from app.services.embedder_registry import embedder_registry

    previous = getattr(app.state, "llm", None)
    app.state.llm = _ScriptedEmbedder()
    embedder_registry.forget(FINGERPRINT)
    yield
    app.state.llm = previous
    embedder_registry.forget(FINGERPRINT)


async def _key(session, *scopes):
    _row, credential = await issue_key(session, name=f"k-{uuid.uuid4().hex[:6]}", scopes=list(scopes))
    return {"Authorization": f"Bearer {credential}"}


async def _document(session, *, project="proj", uri, content_hash="h1"):
    document_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO documents (id, project, uri, title, source_type, content_hash) "
            "VALUES (CAST(:id AS uuid), CAST(:p AS text), CAST(:u AS text), 't', 'markdown', CAST(:h AS text))"
        ),
        {"id": str(document_id), "p": project, "u": uri, "h": content_hash},
    )
    return document_id


async def test_a_capture_key_files_and_a_read_key_reads_it_back(client, session, scripted_embedder):
    capture_name = f"k-{uuid.uuid4().hex[:6]}"
    capture_row, capture_credential = await issue_key(session, name=capture_name, scopes=["capture"])
    capture = {"Authorization": f"Bearer {capture_credential}"}
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/specs/b.md", "content": "# B\n\nThe design.\n"}
    filed = await client.post(V1, json=body, headers=capture)
    assert filed.status_code == 201, filed.text
    assert filed.json()["outcome"] == "created"
    stamped = (await session.execute(
        text("SELECT actor, api_key_id FROM events WHERE event_type = 'document_filed' AND project = 'proj'")
    )).all()
    assert [tuple(row) for row in stamped] == [(capture_name, capture_row.id)]
    back = await client.get(
        f"{V1}/by-uri",
        params={"project": "proj", "uri": "superpowers/specs/b.md", "include_content": "true"},
        headers=read,
    )
    assert back.status_code == 200
    assert back.json()["content"] == body["content"]


async def test_a_keyed_mcp_filing_stamps_its_key(session, scripted_embedder, monkeypatch):
    """The REST filing above stamps the key; the MCP twin must journal the same."""
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from mcp.server.auth.middleware.auth_context import auth_context_var
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser

    import app.api.mcp.auth as mcp_auth
    import app.api.mcp.server as mcp_server

    @asynccontextmanager
    async def _on_the_test_session():
        yield session

    monkeypatch.setattr(mcp_auth, "async_session_factory", lambda: _on_the_test_session())
    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _on_the_test_session())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=_ScriptedEmbedder()))
    name = f"k-{uuid.uuid4().hex[:6]}"
    row, credential = await issue_key(session, name=name, scopes=["capture"])
    token = await mcp_auth.ApiKeyTokenVerifier().verify_token(credential)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        filed = json.loads(await mcp_server.document_put(
            project="proj", uri="superpowers/specs/m.md", content="# M\n\nOver MCP.\n",
        ))
    finally:
        auth_context_var.reset(reset)
    assert filed["outcome"] == "created"
    stamped = (await session.execute(
        text("SELECT actor, api_key_id FROM events WHERE event_type = 'document_filed' AND project = 'proj'")
    )).all()
    assert [tuple(stamp) for stamp in stamped] == [(name, row.id)]


async def test_a_read_key_cannot_file(client, session):
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/specs/b.md", "content": "# B\n"}
    assert (await client.post(V1, json=body, headers=read)).status_code == 403


async def test_the_rest_of_the_document_surface_stays_login_only(client, session):
    every_scope = await _key(session, "read", "capture", "admin")
    document_id = await _document(session, uri="superpowers/specs/a.md")
    assert (await client.get(f"{V1}/{document_id}", headers=every_scope)).status_code == 401
    assert (await client.get(V1, params={"project": "proj"}, headers=every_scope)).status_code == 401
    assert (await client.post(f"{V1}/search", json={"project": "proj", "query": "x"}, headers=every_scope)).status_code == 401


async def test_the_manifest_lists_a_prefix_in_uri_order_and_pages(client, session):
    read = await _key(session, "read")
    for uri in ("superpowers/specs/b.md", "superpowers/specs/a.md", "superpowers/plans/p.md", "other/x.md"):
        await _document(session, uri=uri, content_hash=f"hash-{uri}")
    await _document(session, project="elsewhere", uri="superpowers/specs/z.md")

    first = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": "superpowers", "limit": 2}, headers=read,
    )
    assert first.status_code == 200
    body = first.json()
    assert [i["uri"] for i in body["items"]] == ["superpowers/plans/p.md", "superpowers/specs/a.md"]
    assert body["items"][1]["content_hash"] == "hash-superpowers/specs/a.md"
    assert body["next_after"] == "superpowers/specs/a.md"

    rest = await client.get(
        f"{V1}/manifest",
        params={"project": "proj", "uri_prefix": "superpowers", "after": body["next_after"], "limit": 2},
        headers=read,
    )
    assert [i["uri"] for i in rest.json()["items"]] == ["superpowers/specs/b.md"]
    assert rest.json()["next_after"] is None

    everything = await client.get(f"{V1}/manifest", params={"project": "proj"}, headers=read)
    assert len(everything.json()["items"]) == 4


@pytest.mark.parametrize("prefix", ["superpowers", "superpowers/"])
async def test_a_prefix_matches_whole_segments_with_or_without_a_trailing_slash(client, session, auth_headers, prefix):
    await _document(session, uri="superpowers/specs/a.md")
    await _document(session, uri="superpowersx/a.md")
    response = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": prefix}, headers=auth_headers
    )
    assert [i["uri"] for i in response.json()["items"]] == ["superpowers/specs/a.md"]


async def test_the_manifest_lists_a_document_filed_at_the_prefix_itself(client, session):
    read = await _key(session, "read")
    await _document(session, uri="superpowers")
    await _document(session, uri="superpowersx/a.md")
    listed = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": "superpowers"}, headers=read,
    )
    assert listed.status_code == 200
    assert [i["uri"] for i in listed.json()["items"]] == ["superpowers"]


async def test_a_read_key_lists_revisions_and_reads_one(client, session, scripted_embedder):
    capture_name = f"k-{uuid.uuid4().hex[:6]}"
    capture_row, capture_credential = await issue_key(session, name=capture_name, scopes=["capture"])
    capture = {"Authorization": f"Bearer {capture_credential}"}
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/plans/r.md", "content": "# R\n\nOne.\n"}
    first = (await client.post(V1, json=body, headers=capture)).json()
    second = (await client.post(V1, json={**body, "content": "# R\n\nTwo.\n"}, headers=capture)).json()
    document_id = first["document_id"]

    listed = await client.get(f"{V1}/{document_id}/revisions", headers=read)
    assert listed.status_code == 200, listed.text
    page = listed.json()
    assert [i["content_hash"] for i in page["items"]] == [second["content_hash"], first["content_hash"]]
    assert page["items"][0]["actor"] == capture_name
    assert page["items"][0]["api_key_id"] == str(capture_row.id)
    assert "content" not in page["items"][0]
    assert page["next_before"] is None

    newest = (await client.get(
        f"{V1}/{document_id}/revisions", params={"limit": 1}, headers=read,
    )).json()
    assert newest["next_before"] == page["items"][0]["id"]

    older = await client.get(
        f"{V1}/{document_id}/revisions", params={"before": newest["next_before"]}, headers=read,
    )
    assert [i["content_hash"] for i in older.json()["items"]] == [first["content_hash"]]

    one = await client.get(f"{V1}/{document_id}/revisions/{page['items'][1]['id']}", headers=read)
    assert one.status_code == 200
    assert one.json()["content"] == "# R\n\nOne.\n"
    assert one.json()["document_id"] == document_id


async def test_the_revision_routes_refuse_what_names_nothing(client, session, scripted_embedder):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    a = (await client.post(V1, json={"project": "proj", "uri": "a.md", "content": "# A\n"}, headers=capture)).json()
    b = (await client.post(V1, json={"project": "proj", "uri": "b.md", "content": "# B\n"}, headers=capture)).json()
    b_revision = (await client.get(f"{V1}/{b['document_id']}/revisions", headers=read)).json()["items"][0]["id"]

    assert (await client.get(f"{V1}/{uuid.uuid4()}/revisions", headers=read)).status_code == 404
    assert (await client.get(f"{V1}/{uuid.uuid4()}/revisions/{b_revision}", headers=read)).status_code == 404
    assert (await client.get(f"{V1}/{a['document_id']}/revisions/{b_revision}", headers=read)).status_code == 404
    assert (await client.get(
        f"{V1}/{a['document_id']}/revisions", params={"before": b_revision}, headers=read,
    )).status_code == 422
    assert (await client.get(
        f"{V1}/{a['document_id']}/revisions", params={"limit": 201}, headers=read,
    )).status_code == 422
    assert (await client.get(f"{V1}/{a['document_id']}/revisions", headers=capture)).status_code == 403
    assert (await client.get(f"{V1}/{a['document_id']}/revisions")).status_code == 401


ARCHIVED = "superpowers/archive/20260928T000000Z/notes/a.md"


async def _uri(session, document_id):
    return (await session.execute(
        text("SELECT uri FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(document_id)},
    )).scalar_one()


async def test_a_capture_key_moves_a_document_under_its_hash(client, session):
    name = f"k-{uuid.uuid4().hex[:6]}"
    row, credential = await issue_key(session, name=name, scopes=["capture"])
    document_id = await _document(session, uri="superpowers/notes/a.md", content_hash="h1")
    moved = await client.patch(
        f"{V1}/{document_id}",
        json={"uri": ARCHIVED, "expected_hash": "h1"},
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json() == {"document_id": str(document_id)}
    assert await _uri(session, document_id) == ARCHIVED
    stamped = (await session.execute(
        text(
            "SELECT actor, api_key_id FROM events WHERE event_type = 'document_updated' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).all()
    assert [tuple(r) for r in stamped] == [(name, row.id)]


async def test_a_read_key_cannot_move_a_document(client, session):
    read = await _key(session, "read")
    document_id = await _document(session, uri="superpowers/notes/b.md")
    refused = await client.patch(f"{V1}/{document_id}", json={"uri": ARCHIVED}, headers=read)
    assert refused.status_code == 403


async def test_a_login_session_still_moves_a_document(client, session, auth_headers):
    document_id = await _document(session, uri="superpowers/notes/c.md")
    moved = await client.patch(f"{V1}/{document_id}", json={"title": "C"}, headers=auth_headers)
    assert moved.status_code == 200, moved.text


async def test_a_stale_expected_hash_answers_409_and_moves_nothing(client, session):
    capture = await _key(session, "capture")
    document_id = await _document(session, uri="superpowers/notes/d.md", content_hash="h1")
    refused = await client.patch(
        f"{V1}/{document_id}",
        json={"uri": ARCHIVED, "expected_hash": "stale"},
        headers=capture,
    )
    assert refused.status_code == 409
    assert refused.json()["detail"] == (
        "expected_hash stale does not match the document's current content_hash h1"
    )
    assert await _uri(session, document_id) == "superpowers/notes/d.md"


async def test_an_expected_hash_on_a_missing_document_answers_404(client, session):
    capture = await _key(session, "capture")
    refused = await client.patch(
        f"{V1}/{uuid.uuid4()}",
        json={"uri": ARCHIVED, "expected_hash": "h1"},
        headers=capture,
    )
    assert refused.status_code == 404
