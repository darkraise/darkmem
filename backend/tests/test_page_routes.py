"""The page tree over REST."""
from __future__ import annotations

from uuid import uuid4

import pytest

from tests.test_page_door import FINGERPRINT, StubEmbedder

V1 = "/api/v1"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def stub_llm():
    from app.main import app

    llm = StubEmbedder()
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


@pytest.fixture
def create(client, auth_headers, stub_llm):
    async def _create(**body) -> str:
        body.setdefault("project", "p")
        body.setdefault("title", "t")
        response = await client.post(f"{V1}/pages", json=body, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    return _create


@pytest.mark.asyncio
async def test_create_get_and_list(client, auth_headers, create):
    root = await create(title="Root", content="# Hi\n\nbody\n")
    child = await create(parent_id=root)

    got = await client.get(f"{V1}/pages/{root}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["title"] == "Root"
    assert got.json()["blocks"]

    listed = await client.get(f"{V1}/pages", params={"project": "p"}, headers=auth_headers)
    assert listed.status_code == 200
    assert {row["id"] for row in listed.json()} == {root, child}


@pytest.mark.asyncio
async def test_create_under_a_missing_parent_is_404(client, auth_headers, stub_llm):
    response = await client.post(
        f"{V1}/pages",
        json={"project": "p", "title": "t", "parent_id": str(uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_is_404(client, auth_headers):
    response = await client.get(f"{V1}/pages/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_renames(client, auth_headers, create):
    page = await create()
    response = await client.patch(
        f"{V1}/pages/{page}", json={"title": "New"}, headers=auth_headers
    )
    assert response.status_code == 200
    got = await client.get(f"{V1}/pages/{page}", headers=auth_headers)
    assert got.json()["title"] == "New"


@pytest.mark.asyncio
async def test_a_refused_move_leaves_the_title_unrenamed(
    client, auth_headers, create, session
):
    from sqlalchemy import text

    page = await create(title="old")
    response = await client.patch(
        f"{V1}/pages/{page}",
        json={"title": "new", "parent_id": str(uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404
    got = await client.get(f"{V1}/pages/{page}", headers=auth_headers)
    assert got.json()["title"] == "old"
    count = (
        await session.execute(
            text(
                "SELECT count(*) FROM events WHERE event_type = 'page_updated' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": page},
        )
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_move_into_own_subtree_is_422(client, auth_headers, create):
    root = await create()
    child = await create(parent_id=root)
    response = await client.patch(
        f"{V1}/pages/{root}", json={"parent_id": child}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_move_to_root_with_null_parent(client, auth_headers, create):
    root = await create()
    child = await create(parent_id=root)
    response = await client.patch(
        f"{V1}/pages/{child}", json={"parent_id": None}, headers=auth_headers
    )
    assert response.status_code == 200
    got = await client.get(f"{V1}/pages/{child}", headers=auth_headers)
    assert got.json()["parent_id"] is None


@pytest.mark.asyncio
async def test_patch_naming_no_field_is_422(client, auth_headers, create):
    page = await create()
    response = await client.patch(f"{V1}/pages/{page}", json={}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_after_id_without_parent_id_is_422(client, auth_headers, create):
    page = await create()
    other = await create()
    response = await client.patch(
        f"{V1}/pages/{page}", json={"after_id": other}, headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_then_delete_again_is_404(client, auth_headers, create):
    page = await create()
    first = await client.delete(f"{V1}/pages/{page}", headers=auth_headers)
    assert first.status_code == 204
    second = await client.delete(f"{V1}/pages/{page}", headers=auth_headers)
    assert second.status_code == 404


@pytest.mark.asyncio
async def test_restore(client, auth_headers, create):
    page = await create()
    await client.delete(f"{V1}/pages/{page}", headers=auth_headers)
    response = await client.post(f"{V1}/pages/{page}/restore", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"restored": 1}


@pytest.mark.asyncio
async def test_restore_under_a_trashed_parent_is_409(client, auth_headers, create):
    root = await create()
    child = await create(parent_id=root)
    await client.delete(f"{V1}/pages/{child}", headers=auth_headers)
    await client.delete(f"{V1}/pages/{root}", headers=auth_headers)
    response = await client.post(f"{V1}/pages/{child}/restore", headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_empty_trash_answers_the_purged_count(client, auth_headers, create):
    root = await create()
    await create(parent_id=root)
    await client.delete(f"{V1}/pages/{root}", headers=auth_headers)
    response = await client.post(
        f"{V1}/pages/trash/empty", params={"project": "p"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"purged": 2}


async def _blocks_of(client, auth_headers, page):
    got = await client.get(f"{V1}/pages/{page}", headers=auth_headers)
    assert got.status_code == 200
    return got.json()["blocks"]


@pytest.mark.asyncio
async def test_block_verbs_round_trip_on_a_page(client, auth_headers, create):
    page = await create(content="# T\n\nalpha\n")
    blocks = await _blocks_of(client, auth_headers, page)
    alpha = next(b for b in blocks if b["text"] == "alpha")

    inserted = await client.post(
        f"{V1}/pages/{page}/blocks",
        json={"type": "paragraph", "text": "beta"}, headers=auth_headers,
    )
    assert inserted.status_code == 201, inserted.text
    assert inserted.json()["page_id"] == page

    updated = await client.patch(
        f"{V1}/pages/{page}/blocks/{alpha['id']}",
        json={"text": "alpha edited"}, headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["content_hash"] != inserted.json()["content_hash"]

    moved = await client.post(
        f"{V1}/pages/{page}/blocks/{alpha['id']}/move",
        json={"new_parent_id": None}, headers=auth_headers,
    )
    assert moved.status_code == 200, moved.text

    deleted = await client.delete(
        f"{V1}/pages/{page}/blocks/{alpha['id']}", headers=auth_headers,
    )
    assert deleted.status_code == 204
    after = await _blocks_of(client, auth_headers, page)
    assert alpha["id"] not in [b["id"] for b in after]
    assert "beta" in [b["text"] for b in after]


@pytest.mark.asyncio
async def test_a_block_of_another_page_is_refused(client, auth_headers, create):
    """The page-flavoured `_assert_block_is_in`. Without it, a block id from
    any page could be edited through any page's route."""
    first = await create(content="mine\n")
    other = await create(content="theirs\n")
    theirs = (await _blocks_of(client, auth_headers, other))[0]

    resp = await client.patch(
        f"{V1}/pages/{first}/blocks/{theirs['id']}",
        json={"text": "nope"}, headers=auth_headers,
    )
    assert resp.status_code == 404
    assert (await _blocks_of(client, auth_headers, other))[0]["text"] == "theirs"


@pytest.mark.asyncio
async def test_the_hash_precondition_holds_on_a_page(client, auth_headers, create):
    """`expected_hash` compares against `pages.content_hash`, which is why
    that column is NOT NULL with the create route seeding it."""
    page = await create(content="para\n")
    block = (await _blocks_of(client, auth_headers, page))[0]

    stale = await client.patch(
        f"{V1}/pages/{page}/blocks/{block['id']}",
        json={"text": "x", "expected_hash": "0" * 64}, headers=auth_headers,
    )
    assert stale.status_code == 409
    assert "0" * 64 in stale.json()["detail"]

    current = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()
    fresh = await client.patch(
        f"{V1}/pages/{page}/blocks/{block['id']}",
        json={"text": "x", "expected_hash": current["content_hash"]},
        headers=auth_headers,
    )
    assert fresh.status_code == 200, fresh.text


@pytest.mark.asyncio
async def test_delete_block_takes_the_hash_as_a_query_parameter(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    block = (await _blocks_of(client, auth_headers, page))[0]

    response = await client.delete(
        f"{V1}/pages/{page}/blocks/{block['id']}",
        params={"expected_hash": "0" * 64}, headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_a_document_block_is_refused_on_a_page_route(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    filed = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/x.md", "content": "# T\n\npara\n"},
        headers=auth_headers,
    )
    doc_block = (await client.get(
        f"{V1}/documents/{filed.json()['document_id']}", headers=auth_headers,
    )).json()["blocks"][0]["block_id"]

    resp = await client.patch(
        f"{V1}/pages/{page}/blocks/{doc_block}",
        json={"text": "nope"}, headers=auth_headers,
    )
    assert resp.status_code == 404
