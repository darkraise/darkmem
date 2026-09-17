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
async def test_create_with_unrepresentable_content_is_422(
    client, auth_headers, stub_llm,
):
    response = await client.post(
        f"{V1}/pages",
        json={"project": "p", "title": "t",
              "content": "[ref]: https://example.com/spec\n"},
        headers=auth_headers,
    )
    assert response.status_code == 422


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


async def _insert(client, auth_headers, page, **body):
    return await client.post(
        f"{V1}/pages/{page}/blocks", json=body, headers=auth_headers,
    )


@pytest.mark.asyncio
async def test_a_page_block_insert_refuses_an_unknown_field(client, auth_headers, create):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", bogus=1)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "type_, properties",
    [("todo", {"checked": False}), ("toggle", None), ("callout", {"variant": "warning"})],
)
@pytest.mark.asyncio
async def test_each_page_only_type_is_accepted(
    client, auth_headers, create, type_, properties,
):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type=type_, text="x", properties=properties)
    assert response.status_code == 201, response.text
    block = next(b for b in await _blocks_of(client, auth_headers, page)
                 if b["id"] == response.json()["block_id"])
    assert block["type"] == type_


@pytest.mark.parametrize(
    "type_, properties",
    [("todo", None), ("todo", {"checked": "yes"}), ("callout", {"variant": "loud"})],
)
@pytest.mark.asyncio
async def test_a_page_only_type_with_invalid_properties_is_422(
    client, auth_headers, create, type_, properties,
):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type=type_, text="x", properties=properties)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_type_change_leaving_a_required_property_missing_is_422(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    block = (await _blocks_of(client, auth_headers, page))[0]
    response = await client.patch(
        f"{V1}/pages/{page}/blocks/{block['id']}",
        json={"text": "para", "type": "todo"}, headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_nesting_under_a_paragraph_is_422_on_insert_and_move(
    client, auth_headers, create,
):
    page = await create(content="alpha\n\nbeta\n")
    alpha, beta = await _blocks_of(client, auth_headers, page)

    inserted = await _insert(client, auth_headers, page, type="paragraph",
                             text="child", parent_id=alpha["id"])
    moved = await client.post(
        f"{V1}/pages/{page}/blocks/{beta['id']}/move",
        json={"new_parent_id": alpha["id"]}, headers=auth_headers,
    )

    assert inserted.status_code == 422
    assert moved.status_code == 422


@pytest.mark.asyncio
async def test_a_client_block_id_becomes_the_block_id(client, auth_headers, create):
    page = await create(content="para\n")
    chosen = str(uuid4())
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", block_id=chosen)
    assert response.status_code == 201, response.text
    assert response.json()["block_id"] == chosen


@pytest.mark.asyncio
async def test_a_taken_block_id_is_409(client, auth_headers, create):
    page = await create(content="para\n")
    existing = (await _blocks_of(client, auth_headers, page))[0]["id"]
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", block_id=existing)
    assert response.status_code == 409
    assert response.json()["detail"] == f"block id {existing} already exists"


@pytest.mark.asyncio
async def test_a_page_block_delete_answers_the_new_hash_in_a_header(
    client, auth_headers, create,
):
    page = await create(content="alpha\n\nbeta\n")
    alpha = (await _blocks_of(client, auth_headers, page))[0]

    response = await client.delete(
        f"{V1}/pages/{page}/blocks/{alpha['id']}", headers=auth_headers,
    )

    assert response.status_code == 204
    current = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()
    assert response.headers["x-content-hash"] == current["content_hash"]


@pytest.mark.asyncio
async def test_a_batch_inserts_in_order_with_intra_batch_references(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    prose = (await _blocks_of(client, auth_headers, page))[0]["id"]
    toggle, inside, task = (str(uuid4()) for _ in range(3))

    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": toggle, "type": "toggle", "text": "T", "after_block_id": prose},
            {"block_id": inside, "type": "paragraph", "text": "inside", "parent_id": toggle},
            {"block_id": task, "type": "todo", "text": "task",
             "properties": {"checked": False}, "after_block_id": toggle},
        ]},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["block_ids"] == [toggle, inside, task]
    assert body["outcome"] == "inserted"
    assert set(body) == {"page_id", "block_ids", "outcome", "content_hash",
                         "blocks_total", "blocks_embedded"}
    blocks = await _blocks_of(client, auth_headers, page)
    assert [b["id"] for b in blocks] == [prose, toggle, inside, task]
    assert next(b for b in blocks if b["id"] == inside)["parent_id"] == toggle


@pytest.mark.asyncio
async def test_a_batch_with_an_invalid_item_writes_nothing(client, auth_headers, create):
    page = await create(content="para\n")
    before = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()

    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": str(uuid4()), "type": "paragraph", "text": "fine"},
            {"block_id": str(uuid4()), "type": "todo", "text": "no checked"},
        ]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    after = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()
    assert after["content_hash"] == before["content_hash"]
    assert len(after["blocks"]) == len(before["blocks"])


@pytest.mark.asyncio
async def test_a_batch_repeating_a_block_id_is_422(client, auth_headers, create):
    page = await create(content="para\n")
    repeated = str(uuid4())
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": repeated, "type": "paragraph", "text": "a"},
            {"block_id": repeated, "type": "paragraph", "text": "b"},
        ]},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_batch_naming_a_taken_block_id_is_409(client, auth_headers, create):
    page = await create(content="para\n")
    existing = (await _blocks_of(client, auth_headers, page))[0]["id"]
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [{"block_id": existing, "type": "paragraph", "text": "a"}]},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_an_empty_batch_is_422(client, auth_headers, create):
    page = await create(content="para\n")
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch", json={"blocks": []}, headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_the_trash_route_resolves_before_the_page_id_route(
    client, auth_headers, create,
):
    """Registered below `/{page_id}`, `trash` would fail UUID parsing as 422."""
    root = await create(title="gone")
    await create(parent_id=root)
    await client.delete(f"{V1}/pages/{root}", headers=auth_headers)

    response = await client.get(
        f"{V1}/pages/trash", params={"project": "p"}, headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["id"] for row in body] == [root]
    assert set(body[0]) == {"id", "title", "parent_id", "deleted_at"}


@pytest.mark.asyncio
async def test_the_page_read_serves_block_source(client, auth_headers, create):
    """Regression pin: passes on arrival once Task 10 lands `PageBlock.source`."""
    page = await create(content="## Sub\n\n- item\n")
    blocks = await _blocks_of(client, auth_headers, page)
    assert [b["source"] for b in blocks] == ["## Sub", "- item"]
