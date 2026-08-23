import pytest

from tests.test_document_door import FINGERPRINT, StubEmbedder

V1 = "/api/v1"
DOC = "# Title\n\nFirst para.\n\n## Section\n\nSecond para.\n"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def stub_llm():
    """Point the app at a stub embedder for the write door.

    The test app has no orchestrator configured, and `get_llm` reads
    `request.app.state.llm`, so the route under test needs one — the same
    way `test_documents_api.py`'s `scripted_llm` wires the Q&A door.
    """
    from app.main import app

    llm = StubEmbedder()
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


@pytest.mark.asyncio
async def test_put_creates_and_reports_both_counts(client, auth_headers, stub_llm):
    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "created"
    assert body["blocks_filed"] > 0
    assert body["blocks_embedded"] == body["blocks_filed"]
    assert body["horizon"] is True
    assert body["title_applied"] is True


@pytest.mark.asyncio
async def test_oversized_content_is_refused_with_the_limit_named(
    client, auth_headers, stub_llm
):
    from app.services.document_door import MAX_CONTENT_CHARS

    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/big.md", "content": "x" * (MAX_CONTENT_CHARS + 1)},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert str(MAX_CONTENT_CHARS) in response.text


@pytest.mark.asyncio
async def test_delete_removes_the_document_and_answers_204(client, auth_headers, stub_llm):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    before = await client.get(f"{V1}/documents", params={"project": "p"}, headers=auth_headers)
    assert any(item["id"] == document_id for item in before.json()["items"])

    deleted = await client.delete(f"{V1}/documents/{document_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = await client.get(f"{V1}/documents", params={"project": "p"}, headers=auth_headers)
    assert all(item["id"] != document_id for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_delete_unknown_document_is_404(client, auth_headers):
    response = await client.delete(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_pdf_uri_with_string_content_is_refused_with_422(
    client, auth_headers, stub_llm
):
    """`parse_pdf` takes bytes; `DocumentPutRequest.content` is always `str`,
    so a `.pdf` uri (source_type inferred from the suffix) routes to a
    parser that cannot accept what this door can carry. This door is
    text-only by design, and the door must say so rather than 500.
    """
    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/report.pdf", "content": "not actually pdf bytes"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    # Pinned to the parse failure specifically, not merely to "422 somehow":
    # UnsupportedSource also answers 422, and its message never says "pdf
    # parse failed" -- only DocumentParseError's does.
    assert "pdf parse failed" in response.text


@pytest.mark.asyncio
async def test_put_requires_auth(client):
    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refiling_unchanged_content_with_a_new_title_reports_it_was_not_applied(
    client, auth_headers, stub_llm
):
    """Carried finding from Task 1's review (M6): re-filing UNCHANGED content
    with a new explicit `title` silently drops the title, because
    `file_document`'s content-hash gate short-circuits before `update_document`
    ever runs. The response must let a caller tell that happened.
    """
    first = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC},
        headers=auth_headers,
    )
    assert first.json()["outcome"] == "created"

    again = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC, "title": "New Title"},
        headers=auth_headers,
    )
    body = again.json()
    assert body["outcome"] == "unchanged"
    assert body["title_applied"] is False


NESTED = (
    "# Guide\n\nIntro para.\n\n"
    "## Setup\n\nRun the installer.\n\n"
    "### Windows\n\nUse the msi.\n\n"
    "## Teardown\n\nDelete the folder.\n"
)


@pytest.mark.asyncio
async def test_search_serves_the_heading_path_on_the_wire(client, auth_headers, stub_llm):
    await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )

    response = await client.post(
        f"{V1}/documents/search",
        json={"query": "installer", "project": "p"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["horizon"] is True
    deepest = next(item for item in body["items"] if item["text"].strip() == "Use the msi.")
    assert deepest["heading_path"] == ["Guide", "Setup", "Windows"]
    assert deepest["path_truncated"] is False
    assert deepest["title"] == "Guide"
    assert deepest["id_kind"] == "block"
    assert deepest["layer"] == "document"


@pytest.mark.asyncio
async def test_search_with_no_hits_returns_an_empty_list(client, auth_headers, stub_llm):
    response = await client.post(
        f"{V1}/documents/search",
        json={"query": "anything", "project": "an-empty-project"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_search_requires_auth(client):
    response = await client.post(
        f"{V1}/documents/search", json={"query": "installer", "project": "p"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_rejects_a_blank_query(client, auth_headers, stub_llm):
    response = await client.post(
        f"{V1}/documents/search", json={"query": "", "project": "p"}, headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_outline_returns_headings_with_levels_and_no_body(client, auth_headers, stub_llm):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    response = await client.get(f"{V1}/documents/{document_id}/outline", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["horizon"] is True
    assert body["document_id"] == document_id
    items = body["items"]
    assert [(i["level"], i["text"]) for i in items] == [
        (1, "Guide"), (2, "Setup"), (3, "Windows"), (2, "Teardown"),
    ]
    # Presence of the headings alone would also pass against an
    # implementation that leaked every paragraph into the outline too, so
    # this asserts the body text's absence explicitly rather than only the
    # headings' presence.
    for body_text in ("Intro para.", "Run the installer.", "Use the msi.", "Delete the folder."):
        assert body_text not in response.text


@pytest.mark.asyncio
async def test_outline_requires_auth(client):
    response = await client.get(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000/outline"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_outline_of_a_missing_document_is_404(client, auth_headers):
    """A made-up id must not be answered with a fabricated 200 -- the same
    distinction `get_document_summary` draws between "no summary yet" and an
    empty one, and the same condition the delete route already 404s on for
    this exact id (Task 4 review, I1)."""
    response = await client.get(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000/outline",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_returns_every_block_in_document_order_by_default(
    client, auth_headers, stub_llm
):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    response = await client.get(f"{V1}/documents/{document_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["horizon"] is True
    assert body["document_id"] == document_id
    blocks = body["blocks"]
    assert len(blocks) >= 6
    order_indices = [b["order_index"] for b in blocks]
    assert order_indices == sorted(order_indices)

    # char_span is a citation anchor into the SOURCE, not the retrievable
    # text (document_parsers.py's own rule) -- for a plain paragraph with no
    # markdown decoration to strip, the two must agree exactly, which
    # actually proves the bounds rather than merely their presence/shape.
    installer = next(b for b in blocks if b["text"].strip() == "Run the installer.")
    start, end = installer["char_span"]
    assert NESTED[start:end] == "Run the installer."


@pytest.mark.asyncio
async def test_get_of_a_missing_document_is_404(client, auth_headers):
    response = await client.get(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_with_a_malformed_block_id_is_422(client, auth_headers, stub_llm):
    """`block_ids` is `list[UUID]`, so a caller's typo fails FastAPI's own
    validation instead of reaching `CAST(:ids AS uuid[])` and surfacing as an
    unhandled 500 (Task 4 review, I2)."""
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    response = await client.get(
        f"{V1}/documents/{document_id}",
        params={"block_ids": "not-a-uuid"},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_returns_only_the_blocks_named(client, auth_headers, stub_llm):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    full = await client.get(f"{V1}/documents/{document_id}", headers=auth_headers)
    all_blocks = full.json()["blocks"]
    assert len(all_blocks) >= 4

    # A strict subset -- not a single element, not "all of them" -- named in
    # an order that is NOT document order, so a passing test cannot be
    # explained by an implementation that just echoes the request order back
    # or that ignores block_ids and returns everything.
    first, second = all_blocks[1], all_blocks[3]
    response = await client.get(
        f"{V1}/documents/{document_id}",
        params={"block_ids": [second["block_id"], first["block_id"]]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["horizon"] is True
    blocks = body["blocks"]
    assert [b["block_id"] for b in blocks] == [first["block_id"], second["block_id"]]


@pytest.mark.asyncio
async def test_get_excludes_a_block_from_another_document(client, auth_headers, stub_llm):
    """The `document_id` predicate must apply even when `block_ids` is given,
    so a caller cannot pull a block out of a document it does not belong to
    by naming it alongside one that does. Not exercised by any other test:
    a single-document `block_ids` set can pass this whole suite even if the
    predicate moved into an `else` branch that only ran when `block_ids` was
    absent (Task 4 review, I3)."""
    doc_a = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": NESTED},
        headers=auth_headers,
    )
    document_a_id = doc_a.json()["document_id"]
    doc_b = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/b.md", "content": "# Other\n\nUnrelated text.\n"},
        headers=auth_headers,
    )
    document_b_id = doc_b.json()["document_id"]

    a_blocks = (await client.get(
        f"{V1}/documents/{document_a_id}", headers=auth_headers
    )).json()["blocks"]
    b_blocks = (await client.get(
        f"{V1}/documents/{document_b_id}", headers=auth_headers
    )).json()["blocks"]
    a_block_id = a_blocks[0]["block_id"]
    b_block_id = b_blocks[0]["block_id"]

    response = await client.get(
        f"{V1}/documents/{document_a_id}",
        params={"block_ids": [b_block_id, a_block_id]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    blocks = response.json()["blocks"]
    assert [b["block_id"] for b in blocks] == [a_block_id]


@pytest.mark.asyncio
async def test_get_requires_auth(client):
    response = await client.get(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 401
