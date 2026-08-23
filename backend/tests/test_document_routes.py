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
