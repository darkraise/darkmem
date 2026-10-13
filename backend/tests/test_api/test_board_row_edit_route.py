"""The board's register row edit route (spec 2026-10-13 §2.2-§2.4)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services.api_keys import issue_key
from app.services.document_door import put_document

PROJECT = "board-routes"
REGISTER_URI = "superpowers/registers/r.md"
REGISTER = """# Register — routes

| # | Item | Assigned | Acceptance | State | Note |
|---|---|---|---|---|---|
| 1 | first | - | - | open | - |
| 2 | dup | - | - | open | - |
| 2 | dup again | - | - | open | - |
| 3 | short | - | open | - |
"""


@pytest.fixture
def no_llm(client):
    """The edit must not need an embedder: leave the app without one."""
    from app.main import app

    previous = getattr(app.state, "llm", None)
    app.state.llm = None
    yield
    app.state.llm = previous


async def _file(session, uri=REGISTER_URI, content=REGISTER):
    return await put_document(
        session, None, project=PROJECT, uri=uri, content=content, embed_inline=False,
    )


async def _revisions(session, document_id):
    return (await session.execute(
        text("SELECT actor FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
             "ORDER BY created_at, id"),
        {"d": document_id},
    )).scalars().all()


def _patch(client, headers, document_id, number, **body):
    return client.patch(
        f"/api/v1/board/registers/{document_id}/rows/{number}", json=body, headers=headers,
    )


async def test_a_dmk_key_is_refused(client, session):
    _row, credential = await issue_key(session, name="k-board", scopes=["read", "capture", "admin"])
    response = await client.patch(
        "/api/v1/board/registers/00000000-0000-4000-8000-0000000000b1/rows/1",
        json={"expected_hash": "h", "state": "done"},
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert response.status_code == 401


async def test_an_edit_files_one_revision_by_the_login_and_needs_no_embedder(
    client, auth_headers, session, no_llm,
):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, state="doing")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["row"]["state"] == "doing"
    assert body["content_hash"] != filed.content_hash
    assert await _revisions(session, filed.document_id) == [None, "admin"]
    content = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": filed.document_id},
    )).scalar_one()
    assert content == REGISTER.replace("| 1 | first | - | - | open | - |",
                                       "| 1 | first | - | - | doing | - |")


async def test_a_stale_hash_is_a_409_naming_the_current_hash(client, auth_headers, session):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash="stale", state="done")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "hash_conflict"
    assert error["details"] == [{"current_hash": filed.content_hash}]


async def test_a_block_first_register_is_a_409(client, auth_headers, session):
    filed = await _file(session)
    await session.execute(
        text("UPDATE documents SET properties = "
             "coalesce(properties, CAST('{}' AS jsonb)) || CAST(:props AS jsonb) "
             "WHERE id = CAST(:id AS uuid)"),
        {"id": filed.document_id, "props": '{"ingest_direction": "blocks"}'},
    )
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, state="done")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "block_first"


@pytest.mark.parametrize("number, body, status, reason", [
    (9, {"state": "done"}, 404, "not_found"),
    (2, {"state": "done"}, 422, "duplicate_row"),
    (3, {"state": "done"}, 422, "malformed_row"),
    (1, {"state": "parked"}, 422, "unknown_state"),
    (1, {"state": "verify"}, 422, "note_required"),
    (1, {"note": "two\nlines"}, 422, "invalid_cell"),
    (1, {}, 422, "no_change"),
])
async def test_row_refusals(client, auth_headers, session, number, body, status, reason):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, number,
                            expected_hash=filed.content_hash, **body)
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == reason
    assert await _revisions(session, filed.document_id) == [None]


async def test_an_unknown_document_and_a_non_register_are_404(client, auth_headers, session):
    plan = await _file(session, "superpowers/plans/p.md", REGISTER)
    for document_id in (str(uuid.uuid4()), plan.document_id):
        response = await _patch(client, auth_headers, document_id, 1,
                                expected_hash=plan.content_hash, state="done")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


async def test_an_unknown_body_field_is_refused(client, auth_headers, session):
    filed = await _file(session)
    response = await _patch(client, auth_headers, filed.document_id, 1,
                            expected_hash=filed.content_hash, item="renamed")
    assert response.status_code == 422
