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


@pytest.fixture
def filed(client, auth_headers, stub_llm):
    """File a document over the route; return its id."""

    async def _filed(uri: str, content: str) -> str:
        response = await client.post(
            f"{V1}/documents",
            json={"project": "p", "uri": uri, "content": content},
            headers=auth_headers,
        )
        assert response.status_code == 201
        return response.json()["document_id"]

    return _filed


@pytest.fixture
def first_block(client, auth_headers):
    """Read a document's first block id."""

    async def _first_block(document_id: str) -> str:
        response = await client.get(
            f"{V1}/documents/{document_id}", headers=auth_headers
        )
        assert response.status_code == 200
        return response.json()["blocks"][0]["block_id"]

    return _first_block


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
async def test_a_document_with_zero_blocks_is_200_and_empty_not_404(
    client, auth_headers, stub_llm
):
    """A document that genuinely exists but parses to no blocks (whitespace
    -only content -- `parse_markdown` returns `[]` when `not text.strip()`,
    and `DocumentPutRequest.content` only requires `min_length=1`, so a
    single space clears validation) must still answer 200 with an empty
    list on both routes -- the 404 added for I1 is about the *document*
    existing, and `resolve_by_id` reads `documents` alone, so it must not
    also fire on a document that exists but has nothing under it."""
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/empty.md", "content": " "},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["blocks_filed"] == 0
    document_id = created.json()["document_id"]

    outline = await client.get(f"{V1}/documents/{document_id}/outline", headers=auth_headers)
    assert outline.status_code == 200
    assert outline.json()["items"] == []

    blocks = await client.get(f"{V1}/documents/{document_id}", headers=auth_headers)
    assert blocks.status_code == 200
    assert blocks.json()["blocks"] == []


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


# ── ?uri= resolution, and the MCP twins (Task 5) ──────────────────────


def _ctx(headers: dict[str, str] | None):
    """An MCP ``Context`` as far as identity resolution is concerned.

    An in-process call with `ctx=None` exercises the fallback rung and nothing
    above it, so the only way to see which source the door resolved is to drive
    it with a real header mapping.
    """
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    if headers is None:
        return None
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=Headers(headers)))
    )


class RankedStub(StubEmbedder):
    """A distinct unit vector per text, so a ranked order actually exists.

    `StubEmbedder` gives every text one direction, which ties every cosine:
    two doors would then "agree" on any order at all and comparing them
    would assert nothing. The angle here is a stable function of the text,
    so the ranking is real -- and the parity test asserts the scores are
    distinct, because a tie would quietly restore the vacuous version.
    """

    def _vector(self, value: str) -> list[float]:
        import hashlib
        import math

        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        angle = (int(digest, 16) % 10_000) / 10_000 * (math.pi / 2)
        return [math.cos(angle), math.sin(angle), 0.0]

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([self._vector(t) for t in texts], self.fingerprint)

    async def embed(self, value: str):
        return self._vector(value), self.fingerprint


@pytest.fixture
def both_doors(session, monkeypatch):
    """One embedder and one session behind both transports.

    The MCP tools open their own session through the module-level factory and
    read their embedder off `_pipeline`, neither of which the FastAPI
    dependency overrides reach -- so parity can only be measured once both
    are pointed at what the REST client already uses.
    """
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.main import app

    llm = RankedStub()

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


async def _put_nested(client, auth_headers, uri: str = "docs/g.md") -> str:
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": uri, "content": NESTED},
        headers=auth_headers,
    )
    assert created.status_code == 201
    return created.json()["document_id"]


@pytest.mark.asyncio
async def test_both_doors_answer_the_same_search(client, auth_headers, both_doors):
    """Two-door parity is asserted on the ranked order, not the shape: a
    shape comparison passes while orders diverge."""
    import json

    from app.api.mcp import server as mcp_server

    await _put_nested(client, auth_headers)

    rest = await client.post(
        f"{V1}/documents/search",
        json={"query": "installer", "project": "p"},
        headers=auth_headers,
    )
    tool = json.loads(await mcp_server.document_search(query="installer", project="p"))

    items = rest.json()["items"]
    scores = [item["score"] for item in items]
    assert len(items) > 2, "too few hits for an order comparison to mean anything"
    assert len(set(scores)) == len(scores), (
        "every hit scored the same, so this comparison would pass against any "
        "order at all -- the stub embedder must rank"
    )
    assert [i["block_id"] for i in items] == [i["block_id"] for i in tool]
    assert items == tool, "the two doors serve the same rows, not only the same ids"


@pytest.mark.asyncio
async def test_the_search_page_bound_is_one_constant_on_both_doors(
    client, auth_headers, both_doors, monkeypatch
):
    from app.services import document_door
    from app.api.mcp import server as mcp_server
    from app.services.document_door import SEARCH_MAX_LIMIT

    over = await client.post(
        f"{V1}/documents/search",
        json={"query": "installer", "project": "p", "limit": SEARCH_MAX_LIMIT + 1},
        headers=auth_headers,
    )
    assert over.status_code == 422

    # The tool clamps rather than refusing, as every MCP limit does -- but to
    # the same number. A second copy of the bound is what lets the two doors
    # page differently.
    calls: list[int] = []
    original = document_door.search_sections

    async def spy(*args, **kwargs):
        calls.append(kwargs["limit"])
        return await original(*args, **kwargs)

    monkeypatch.setattr(document_door, "search_sections", spy)
    await mcp_server.document_search(
        query="installer", project="p", limit=SEARCH_MAX_LIMIT + 1,
    )
    assert calls == [SEARCH_MAX_LIMIT]


@pytest.mark.asyncio
async def test_the_mcp_tools_answer_by_uri_with_no_id_in_hand(client, auth_headers, both_doors):
    """The path-not-id case: an agent resuming work knows the file it wrote."""
    import json

    from app.api.mcp import server as mcp_server

    document_id = await _put_nested(client, auth_headers)

    outline = json.loads(await mcp_server.document_outline(project="p", uri="docs/g.md"))
    by_id = json.loads(await mcp_server.document_outline(document_id=document_id))
    assert outline == by_id
    assert [node["text"] for node in outline] == ["Guide", "Setup", "Windows", "Teardown"]

    blocks = json.loads(await mcp_server.document_get(project="p", uri="docs/g.md"))
    assert blocks == json.loads(await mcp_server.document_get(document_id=document_id))
    assert any(row["text"].strip() == "Use the msi." for row in blocks)


@pytest.mark.asyncio
async def test_the_rest_door_answers_by_uri_too(client, auth_headers, both_doors):
    document_id = await _put_nested(client, auth_headers)

    outline = await client.get(
        f"{V1}/documents/by-uri/outline",
        params={"project": "p", "uri": "docs/g.md"},
        headers=auth_headers,
    )
    assert outline.status_code == 200
    assert outline.json()["document_id"] == document_id
    by_id = await client.get(f"{V1}/documents/{document_id}/outline", headers=auth_headers)
    assert outline.json() == by_id.json()

    blocks = await client.get(
        f"{V1}/documents/by-uri",
        params={"project": "p", "uri": "docs/g.md"},
        headers=auth_headers,
    )
    assert blocks.status_code == 200
    assert blocks.json() == (
        await client.get(f"{V1}/documents/{document_id}", headers=auth_headers)
    ).json()


@pytest.mark.asyncio
async def test_by_uri_is_not_shadowed_by_the_id_route(client, auth_headers, both_doors):
    """Registration order, pinned. `/{document_id}` matches the literal
    segment `by-uri` too, so a reversed decorator pair answers 422 `invalid
    uuid` for every by-uri call instead of resolving anything -- a failure
    that no other test in this file would see."""
    await _put_nested(client, auth_headers)

    for response in (
        await client.get(
            f"{V1}/documents/by-uri", params={"project": "p", "uri": "docs/g.md"},
            headers=auth_headers,
        ),
        await client.get(
            f"{V1}/documents/by-uri/outline", params={"project": "p", "uri": "docs/g.md"},
            headers=auth_headers,
        ),
        await client.delete(
            f"{V1}/documents/by-uri", params={"project": "p", "uri": "docs/g.md"},
            headers=auth_headers,
        ),
    ):
        assert response.status_code != 422, (
            "the by-uri route was shadowed by its {document_id} sibling"
        )


@pytest.mark.asyncio
async def test_naming_no_document_is_404_on_rest_and_an_error_on_the_tool(
    client, auth_headers, both_doors
):
    """Never a silent empty result. An outline of nothing and an outline with
    no headings are different answers, and the door that returned `[]` for
    both would report a document that does not exist as an empty one."""
    import json

    from app.api.mcp import server as mcp_server
    from app.services.document_door import DocumentTargetUnresolved

    for params in ({}, {"project": "p"}, {"uri": "docs/g.md"}):
        response = await client.get(
            f"{V1}/documents/by-uri/outline", params=params, headers=auth_headers,
        )
        assert response.status_code == 404, params

    unfiled = await client.get(
        f"{V1}/documents/by-uri/outline",
        params={"project": "p", "uri": "docs/never-filed.md"},
        headers=auth_headers,
    )
    assert unfiled.status_code == 404

    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_outline()
    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_outline(project="p", uri="docs/never-filed.md")
    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_get(project="p", uri="docs/never-filed.md")
    # The delete answers an envelope where the two reads raise: it is a
    # writer, and its sibling writer document_update already answers one.
    unresolved = json.loads(
        await mcp_server.document_delete(project="p", uri="docs/never-filed.md")
    )
    assert unresolved["status"] == "unresolved"


@pytest.mark.asyncio
async def test_a_vanished_id_is_refused_rather_than_answered_empty(
    client, auth_headers, both_doors
):
    import json
    import uuid

    from app.api.mcp import server as mcp_server
    from app.services.document_door import DocumentTargetUnresolved

    missing = str(uuid.uuid4())
    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_outline(document_id=missing)
    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_get(document_id=missing)
    with pytest.raises(ValueError):
        await mcp_server.document_get(document_id="not-a-uuid")

    document_id = await _put_nested(client, auth_headers)
    assert json.loads(await mcp_server.document_get(document_id=document_id))


@pytest.mark.asyncio
async def test_document_put_resolves_its_source_through_the_client_ladder(
    session, both_doors
):
    """The MCP door stamps `mcp`, not the REST door's `api`, and a declared
    client wins over both -- the same ladder every other capture tool
    resolves through. A constant here would be a second key space."""
    import json

    from sqlalchemy import text as _text

    from app.api.mcp import server as mcp_server

    filed = json.loads(await mcp_server.document_put(
        project="p", uri="docs/mcp.md", content=NESTED,
    ))
    assert filed["outcome"] == "created"
    assert filed["blocks_filed"] > 0
    assert filed["blocks_embedded"] == filed["blocks_filed"]

    declared = json.loads(await mcp_server.document_put(
        project="p", uri="docs/codex.md", content=DOC,
        ctx=_ctx({"x-darkmem-client": "codex"}),
    ))

    sources = dict((await session.execute(_text(
        "SELECT CAST(object_id AS text) AS id, source FROM events "
        "WHERE event_type = 'document_filed'"
    ))).all())
    assert sources[filed["document_id"]] == "mcp"
    assert sources[declared["document_id"]] == "codex"


@pytest.mark.asyncio
async def test_document_delete_by_uri_on_the_rest_door(client, auth_headers, both_doors):
    await _put_nested(client, auth_headers)

    deleted = await client.delete(
        f"{V1}/documents/by-uri",
        params={"project": "p", "uri": "docs/g.md"},
        headers=auth_headers,
    )
    assert deleted.status_code == 204

    gone = await client.get(
        f"{V1}/documents/by-uri/outline",
        params={"project": "p", "uri": "docs/g.md"},
        headers=auth_headers,
    )
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_the_tools_degrade_rather_than_raise_with_no_embedder(session, monkeypatch):
    """`_degraded` is for the server being unavailable, and an install with no
    embedder configured is exactly that -- unlike naming no document, which is
    the caller's mistake and raises."""
    import json

    from app.api.mcp import server as mcp_server

    monkeypatch.setattr(mcp_server, "_pipeline", None)
    put = json.loads(await mcp_server.document_put(project="p", uri="a.md", content=DOC))
    search = json.loads(await mcp_server.document_search(query="x", project="p"))
    assert put["status"] == "unavailable" and put["document_id"] is None
    assert search["status"] == "unavailable" and search["results"] == []


# ── fix round 1: the doors compared on every verb, not only search ────


@pytest.mark.asyncio
async def test_the_keyed_reads_serve_the_same_rows_on_both_doors(
    client, auth_headers, both_doors
):
    """Whole-payload comparison, the shape `test_fact_detail_doors_serve_the
    _same_row` established: comparing only that both doors answered leaves a
    door free to drop or reshape a field. What legitimately differs is the
    envelope, which the parity row records -- so the envelope is unwrapped
    here rather than ignored."""
    import json

    from app.api.mcp import server as mcp_server

    document_id = await _put_nested(client, auth_headers)

    rest_outline = await client.get(
        f"{V1}/documents/{document_id}/outline", headers=auth_headers,
    )
    tool_outline = json.loads(await mcp_server.document_outline(document_id=document_id))
    assert rest_outline.json()["items"] == tool_outline
    assert rest_outline.json()["document_id"] == document_id

    rest_blocks = await client.get(f"{V1}/documents/{document_id}", headers=auth_headers)
    tool_blocks = json.loads(await mcp_server.document_get(document_id=document_id))
    assert rest_blocks.json()["blocks"] == tool_blocks

    named = [row["block_id"] for row in tool_blocks[:2]]
    rest_named = await client.get(
        f"{V1}/documents/{document_id}",
        params=[("block_ids", block_id) for block_id in named],
        headers=auth_headers,
    )
    tool_named = json.loads(await mcp_server.document_get(
        document_id=document_id, block_ids=named,
    ))
    assert rest_named.json()["blocks"] == tool_named == [
        row for row in tool_blocks if row["block_id"] in named
    ]


@pytest.mark.asyncio
async def test_the_write_verbs_agree_on_both_doors(client, auth_headers, both_doors):
    """`title_applied`, `outcome` and both counts come from `PutResult`, so
    the tool cannot report a filing the route would describe differently.
    The delete side is compared on its effect: 204 carries no body."""
    import json

    from app.api.mcp import server as mcp_server

    rest = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/same.md", "content": NESTED},
        headers=auth_headers,
    )
    tool = json.loads(await mcp_server.document_put(
        project="p", uri="docs/same.md", content=NESTED,
    ))

    body = rest.json()
    # The second filing is the unchanged path, so only the fields that do not
    # describe *which* filing this was may be compared directly.
    assert tool["document_id"] == body["document_id"]
    assert tool["outcome"] == "unchanged" and body["outcome"] == "created"
    assert set(tool) == set(body) - {"horizon"}

    deleted = json.loads(await mcp_server.document_delete(project="p", uri="docs/same.md"))
    assert deleted == {"document_id": body["document_id"], "deleted": True}
    assert (await client.get(
        f"{V1}/documents/{body['document_id']}", headers=auth_headers,
    )).status_code == 404


@pytest.mark.asyncio
async def test_a_malformed_block_id_is_refused_by_name_not_by_a_database_error(
    client, auth_headers, both_doors
):
    """The REST twin declares `list[UUID]` and answers 422; the tool has to
    reach the same refusal by hand, because a tool argument carries no
    validation of its own and asyncpg's uuid cast raises a SQL traceback at a
    caller that is a machine."""
    from app.api.mcp import server as mcp_server

    document_id = await _put_nested(client, auth_headers)

    rest = await client.get(
        f"{V1}/documents/{document_id}",
        params={"block_ids": "not-a-uuid"},
        headers=auth_headers,
    )
    assert rest.status_code == 422

    with pytest.raises(ValueError) as caught:
        await mcp_server.document_get(document_id=document_id, block_ids=["not-a-uuid"])
    assert "not-a-uuid" in str(caught.value)


@pytest.mark.asyncio
async def test_search_refuses_a_document_id_that_names_nothing(
    client, auth_headers, both_doors
):
    """An empty page for a document that is gone is the one answer a caller
    cannot tell from a genuine no-match, which is the distinction every other
    verb keyed on a document already draws."""
    import uuid

    from app.api.mcp import server as mcp_server
    from app.services.document_door import DocumentTargetUnresolved

    document_id = await _put_nested(client, auth_headers)
    missing = str(uuid.uuid4())

    scoped = await client.post(
        f"{V1}/documents/search",
        json={"query": "installer", "project": "p", "document_id": document_id},
        headers=auth_headers,
    )
    assert scoped.status_code == 200 and scoped.json()["items"]

    for bad in (missing, "not-a-uuid"):
        response = await client.post(
            f"{V1}/documents/search",
            json={"query": "installer", "project": "p", "document_id": bad},
            headers=auth_headers,
        )
        assert response.status_code == 404, bad
        with pytest.raises(DocumentTargetUnresolved):
            await mcp_server.document_search(
                query="installer", project="p", document_id=bad,
            )


@pytest.mark.asyncio
async def test_put_reports_oversized_blocks_on_both_doors(
    client, auth_headers, both_doors
):
    """The degradation is real and is reported rather than prevented: an
    oversized block still files and still embeds, truncated. Both doors must
    say so identically -- one PutResult produces the fields for both."""
    import json

    from app.services.document_ingest import OVERSIZED_BLOCK_CHARS
    from app.api.mcp import server as mcp_server

    big = "x" * (OVERSIZED_BLOCK_CHARS + 1)
    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/big.md", "content": f"# H\n\n{big}\n"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["oversized_blocks"] == 1
    assert body["largest_block_chars"] == len(big)

    # The MCP door serialises whatever the dataclass carries, so asserting the
    # keys are actually present is what stops a rename dropping them silently.
    reply = json.loads(
        await mcp_server.document_put(
            project="p", uri="docs/big2.md", content=f"# H\n\n{big}\n"
        )
    )
    assert reply["oversized_blocks"] == 1
    assert reply["largest_block_chars"] == len(big)


@pytest.mark.asyncio
async def test_an_ordinary_document_reports_zero_not_null(
    client, auth_headers, stub_llm
):
    """0 and None are different claims: 0 is a clean bill this filing issued,
    None is a filing that measured nothing."""
    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/small.md", "content": DOC},
        headers=auth_headers,
    )
    assert response.json()["oversized_blocks"] == 0


@pytest.mark.asyncio
async def test_include_content_returns_the_filed_source_on_both_doors(
    client, auth_headers, both_doors
):
    """The round trip, asserted against the exact bytes that were PUT --
    frontmatter fence included, since that is what char_span indexes into."""
    import json

    from app.api.mcp import server as mcp_server

    source = "---\ntitle: RT\n---\n# H\n\nbody\n"
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/rt.md", "content": source},
        headers=auth_headers,
    )
    doc_id = created.json()["document_id"]

    off = await client.get(f"{V1}/documents/{doc_id}", headers=auth_headers)
    assert off.json()["content"] is None

    on = await client.get(
        f"{V1}/documents/{doc_id}?include_content=true", headers=auth_headers
    )
    assert on.json()["content"] == source

    by_uri = await client.get(
        f"{V1}/documents/by-uri?project=p&uri=docs/rt.md&include_content=true",
        headers=auth_headers,
    )
    assert by_uri.json()["content"] == source

    bare = json.loads(await mcp_server.document_get(document_id=doc_id))
    assert isinstance(bare, list)

    envelope = json.loads(
        await mcp_server.document_get(document_id=doc_id, include_content=True)
    )
    assert isinstance(envelope, dict)
    assert envelope["content"] == source
    assert envelope["blocks"] == bare


@pytest.mark.asyncio
async def test_expected_hash_refuses_a_stale_edit_on_both_doors(
    client, auth_headers, both_doors
):
    """One DocumentHashConflict, two wire shapes: 409 on the route, a
    hash_conflict envelope from the tool. Both name the hash that won, so a
    caller can re-read and retry without guessing."""
    import json

    from app.api.mcp import server as mcp_server

    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/cas.md", "content": "# One\n"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    first_hash = created.json()["content_hash"]
    assert first_hash

    # A matching precondition is accepted and echoes the new hash.
    ok = await client.post(
        f"{V1}/documents",
        json={
            "project": "p", "uri": "docs/cas.md", "content": "# Two\n",
            "expected_hash": first_hash,
        },
        headers=auth_headers,
    )
    assert ok.status_code == 201
    second_hash = ok.json()["content_hash"]
    assert second_hash != first_hash

    # The stale hash is now refused on the route.
    stale = await client.post(
        f"{V1}/documents",
        json={
            "project": "p", "uri": "docs/cas.md", "content": "# Three\n",
            "expected_hash": first_hash,
        },
        headers=auth_headers,
    )
    assert stale.status_code == 409
    assert first_hash in stale.json()["detail"]

    # The route's refusal wrote nothing: the document still holds the edit
    # that was accepted. Checked here, before the tool call below, on purpose
    # -- see the note on that call.
    current = await client.get(
        f"{V1}/documents/by-uri?project=p&uri=docs/cas.md&include_content=true",
        headers=auth_headers,
    )
    assert current.json()["content"] == "# Two\n"

    # ... and on the tool, as a structured envelope rather than an error.
    #
    # This call has to come last in this test. The conflict path rolls its
    # session back, and the `both_doors` fixture hands the tool the *same*
    # session the REST client is using, so the rollback discards this test's
    # own rows too. That is a property of the fixture, not of the door: in
    # production `document_put` opens its own session per call and the
    # rollback reaches nothing but its own failed filing.
    reply = json.loads(await mcp_server.document_put(
        project="p", uri="docs/cas.md", content="# Four\n",
        expected_hash=first_hash,
    ))
    assert reply["status"] == "hash_conflict"
    assert reply["expected_hash"] == first_hash
    assert reply["current_hash"] == second_hash


@pytest.mark.asyncio
async def test_the_block_read_serves_properties_and_source(
    client, auth_headers, both_doors
):
    """`text` is marker-stripped, so an editor holding it is editing a
    different string from the one stored. `source` is the stored one."""
    import json

    from app.api.mcp import server as mcp_server

    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/props.md",
              "content": "## Heading two\n\n- item one\n"},
        headers=auth_headers,
    )
    doc_id = created.json()["document_id"]

    body = (await client.get(f"{V1}/documents/{doc_id}", headers=auth_headers)).json()
    heading = next(b for b in body["blocks"] if b["type"] == "heading")
    assert heading["text"] == "Heading two"          # marker stripped
    assert heading["source"] == "## Heading two"     # marker intact
    assert heading["properties"] == {"level": 2}

    item = next(b for b in body["blocks"] if b["type"] == "list")
    assert item["source"] == "- item one"

    # Both doors, one service read.
    tool = json.loads(await mcp_server.document_get(document_id=doc_id))
    tool_heading = next(b for b in tool if b["type"] == "heading")
    assert tool_heading["source"] == "## Heading two"
    assert tool_heading["properties"] == {"level": 2}


# ── The block verbs over REST (increment 8, Task 5) ──────────────────


@pytest.mark.asyncio
async def test_the_four_block_routes_round_trip(client, auth_headers, stub_llm):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/edit.md",
              "content": "# T\n\nalpha\n\nbeta\n"},
        headers=auth_headers,
    )
    doc_id = created.json()["document_id"]
    blocks = (await client.get(f"{V1}/documents/{doc_id}", headers=auth_headers)).json()["blocks"]
    alpha = next(b for b in blocks if b["text"] == "alpha")
    heading = next(b for b in blocks if b["type"] == "heading")

    # insert -> 201 with the minted id
    inserted = await client.post(
        f"{V1}/documents/{doc_id}/blocks",
        json={"type": "paragraph", "text": "inserted", "parent_id": heading["block_id"]},
        headers=auth_headers,
    )
    assert inserted.status_code == 201
    assert inserted.json()["block_id"]

    # update -> 200 with a new content hash
    updated = await client.patch(
        f"{V1}/documents/{doc_id}/blocks/{alpha['block_id']}",
        json={"text": "alpha edited"}, headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["content_hash"] != created.json()["content_hash"]

    # move -> 200
    moved = await client.post(
        f"{V1}/documents/{doc_id}/blocks/{alpha['block_id']}/move",
        json={"new_parent_id": None}, headers=auth_headers,
    )
    assert moved.status_code == 200

    # delete -> 204, and the block is gone from the read
    deleted = await client.delete(
        f"{V1}/documents/{doc_id}/blocks/{alpha['block_id']}", headers=auth_headers,
    )
    assert deleted.status_code == 204
    after = (await client.get(f"{V1}/documents/{doc_id}", headers=auth_headers)).json()
    assert alpha["block_id"] not in [b["block_id"] for b in after["blocks"]]


@pytest.mark.asyncio
async def test_put_against_a_block_first_document_is_409(
    client, auth_headers, stub_llm
):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/owned2.md", "content": "# T\n\nbody\n"},
        headers=auth_headers,
    )
    doc_id = created.json()["document_id"]
    blocks = (await client.get(f"{V1}/documents/{doc_id}", headers=auth_headers)).json()["blocks"]

    # The first block verb converts the document.
    await client.patch(
        f"{V1}/documents/{doc_id}/blocks/{blocks[-1]['block_id']}",
        json={"text": "edited"}, headers=auth_headers,
    )

    conflict = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/owned2.md", "content": "# Overwrite\n"},
        headers=auth_headers,
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_a_block_of_another_document_404s_at_this_path(
    client, auth_headers, stub_llm
):
    """It exists, but not here. The same 404 as a missing block, deliberately:
    a 403 would confirm the id is real somewhere else."""
    first = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/one.md", "content": "# One\n\na\n"},
        headers=auth_headers,
    )
    second = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/two.md", "content": "# Two\n\nb\n"},
        headers=auth_headers,
    )
    other_id = second.json()["document_id"]
    other_blocks = (await client.get(
        f"{V1}/documents/{other_id}", headers=auth_headers
    )).json()["blocks"]

    resp = await client.patch(
        f"{V1}/documents/{first.json()['document_id']}/blocks/{other_blocks[0]['block_id']}",
        json={"text": "nope"}, headers=auth_headers,
    )
    assert resp.status_code == 404


# ── content_hash precondition on the block routes ─────────────────────


@pytest.mark.asyncio
async def test_the_blocks_read_serves_the_documents_hash(client, auth_headers, filed):
    doc = await filed("notes/h.md", "# T\n\npara")
    body = (await client.get(f"{V1}/documents/{doc}",
                             headers=auth_headers)).json()
    assert body["content_hash"], "a caller cannot precondition its first edit"


@pytest.mark.asyncio
async def test_a_stale_hash_answers_409_naming_both_hashes(
    client, auth_headers, filed, first_block,
):
    doc = await filed("notes/h2.md", "# T\n\npara")
    response = await client.patch(
        f"{V1}/documents/{doc}/blocks/{await first_block(doc)}",
        json={"text": "x", "expected_hash": "0" * 64},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "0" * 64 in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_takes_the_hash_as_a_query_parameter(
    client, auth_headers, filed, first_block,
):
    """DELETE carries no body in this API's conventions, so the precondition
    rides the query string. A body field here would be silently ignored."""
    doc = await filed("notes/h3.md", "# T\n\npara")
    response = await client.delete(
        f"{V1}/documents/{doc}/blocks/{await first_block(doc)}"
        f"?expected_hash={'0' * 64}",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_insert_route_forwards_the_hash_to_the_service(
    client, auth_headers, filed, first_block,
):
    doc = await filed("notes/h4.md", "# T\n\npara")
    parent = await first_block(doc)
    response = await client.post(
        f"{V1}/documents/{doc}/blocks",
        json={
            "type": "paragraph", "text": "inserted", "parent_id": parent,
            "expected_hash": "0" * 64,
        },
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "0" * 64 in response.json()["detail"]


@pytest.mark.asyncio
async def test_move_route_forwards_the_hash_to_the_service(
    client, auth_headers, filed, first_block,
):
    doc = await filed("notes/h5.md", "# T\n\npara")
    block = await first_block(doc)
    response = await client.post(
        f"{V1}/documents/{doc}/blocks/{block}/move",
        json={"new_parent_id": None, "expected_hash": "0" * 64},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert "0" * 64 in response.json()["detail"]


@pytest.mark.asyncio
async def test_a_served_hash_preconditions_the_next_two_writes(
    client, auth_headers, filed, first_block,
):
    """The chain the editor's queue is built on, end to end over the routes:
    the hash a read serves preconditions a write, and the hash that write
    answers preconditions the one after it, with no read in between. Asserted
    at the door because that is where a caller meets it -- a schema that
    dropped the field from the response, or a route that stopped forwarding
    it, breaks the chain without breaking the service."""
    doc = await filed("notes/chain.md", "# T\n\npara")
    block = await first_block(doc)

    served = (await client.get(
        f"{V1}/documents/{doc}", headers=auth_headers
    )).json()["content_hash"]
    assert served, "the read serves no hash, so the precondition below is a no-op"

    patched = await client.patch(
        f"{V1}/documents/{doc}/blocks/{block}",
        json={"text": "edited", "expected_hash": served},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    inserted = await client.post(
        f"{V1}/documents/{doc}/blocks",
        json={
            "type": "paragraph",
            "text": "appended",
            "expected_hash": patched.json()["content_hash"],
        },
        headers=auth_headers,
    )
    assert inserted.status_code == 201, inserted.text
    assert inserted.json()["content_hash"] != patched.json()["content_hash"]


async def _file_one(client, auth_headers, uri: str = "docs/rel.md") -> str:
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": uri, "content": DOC},
        headers=auth_headers,
    )
    assert created.status_code == 201
    return created.json()["document_id"]


@pytest.mark.asyncio
async def test_the_lift_route_is_gone(client, auth_headers, stub_llm):
    document_id = await _file_one(client, auth_headers, "docs/gone.md")

    response = await client.post(
        f"{V1}/documents/{document_id}/lift", headers=auth_headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_related_memories_reports_its_comparison_state(
    client, auth_headers, stub_llm
):
    document_id = await _file_one(client, auth_headers, "docs/state.md")

    response = await client.get(
        f"{V1}/documents/{document_id}/related-memories", headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "embedded", "comparable_memories"}
    assert isinstance(body["embedded"], bool)
    assert isinstance(body["comparable_memories"], int)


@pytest.mark.asyncio
async def test_connections_report_their_comparison_state(
    client, auth_headers, stub_llm
):
    document_id = await _file_one(client, auth_headers, "docs/conn.md")

    response = await client.get(
        f"{V1}/documents/{document_id}/connections", headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "embedded", "comparable_documents"}


@pytest.mark.asyncio
async def test_a_related_item_carries_its_matching_passage(
    client, auth_headers, stub_llm, session
):
    """Spec §3.4: the passage is the evidence, the score is an ordering key."""
    from app.models.memory import Memory
    from app.services.embedder_registry import child_table
    from sqlalchemy import text as sql_text

    document_id = await _file_one(client, auth_headers, "docs/passage.md")

    memory = Memory(content="First para.", project="p", source="api")
    session.add(memory)
    await session.flush()
    await session.execute(
        sql_text(
            f"INSERT INTO {child_table('memory_embeddings', FINGERPRINT)} "
            "(memory_id, fingerprint, embedding) VALUES (CAST(:mid AS uuid), :fp, CAST(:vec AS vector))"
        ),
        {"mid": str(memory.id), "fp": FINGERPRINT, "vec": "[1.0,0.0,0.0]"},
    )
    await session.commit()

    response = await client.get(
        f"{V1}/documents/{document_id}/related-memories", headers=auth_headers
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items, "the seeded memory should be comparable to the filed document"
    for item in items:
        assert set(item) == {
            # `project` rides the row because `content_surfaces` declares this
            # surface labels it; the declaration was true of nothing on the
            # wire until 2026-09-05.
            "memory_id", "content", "memory_type", "status", "source",
            "project", "score",
            "block_id", "block_text", "span_start", "span_end",
        }


# --- the metadata verb and the subtree rename -------------------------------


async def test_patch_updates_one_document(client, auth_headers, filed, session):
    doc = await filed("notes/p.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}",
        json={"title": "New", "pinned": True},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["document_id"] == doc

    # Read the row back: a 200 and an id echo alone would also be answered by
    # a handler that ignored the body. `pinned` is served by no read route,
    # so the assertion goes to the column.
    from sqlalchemy import text as sql_text

    row = (await session.execute(
        sql_text(
            "SELECT title, pinned_at FROM documents WHERE id = CAST(:id AS uuid)"
        ),
        {"id": doc},
    )).mappings().one()
    assert row["title"] == "New"
    assert row["pinned_at"] is not None


async def test_the_list_serves_pinned_at(client, auth_headers, filed):
    """The tree reads pin state from the list; a pin control with no readable
    state is not shippable."""
    from app.services.document_door import update_document_metadata

    doc = await filed("notes/pinme.md", "body")

    before = await client.get(
        f"{V1}/documents", params={"project": "p"}, headers=auth_headers
    )
    assert before.status_code == 200
    row = next(r for r in before.json()["items"] if r["id"] == doc)
    assert row["pinned_at"] is None

    await client.patch(
        f"{V1}/documents/{doc}", json={"pinned": True}, headers=auth_headers
    )

    after = await client.get(
        f"{V1}/documents", params={"project": "p"}, headers=auth_headers
    )
    pinned = next(r for r in after.json()["items"] if r["id"] == doc)
    assert pinned["pinned_at"] is not None


async def test_the_list_says_whether_a_summary_exists(
    client, auth_headers, filed, session
):
    """`has_summary` is what lets the reader skip `GET /{id}/summary` -- a 404
    for every unsummarised document -- so it must agree with `read_summary`
    on all three stored shapes, not only on the happy path."""
    import json

    from sqlalchemy import text as sql_text

    from app.services.document_summary import SUMMARY_PROPERTY_KEY, read_summary

    none = await filed("notes/none.md", "body")
    empty = await filed("notes/empty.md", "body")
    real = await filed("notes/real.md", "body")
    for doc, stored in (
        (empty, {"text": "", "generated_at": "2026-10-06T00:00:00Z"}),
        (real, {"text": "A report.", "generated_at": "2026-10-06T00:00:00Z"}),
    ):
        await session.execute(
            sql_text(
                "UPDATE documents SET properties = COALESCE(properties, '{}'::jsonb)"
                " || CAST(:patch AS jsonb) WHERE id = CAST(:id AS uuid)"
            ),
            {"id": doc, "patch": json.dumps({SUMMARY_PROPERTY_KEY: stored})},
        )
    await session.commit()

    listed = await client.get(
        f"{V1}/documents", params={"project": "p"}, headers=auth_headers
    )
    rows = {r["id"]: r for r in listed.json()["items"]}
    for doc in (none, empty, real):
        served = await read_summary(session, document_id=doc)
        assert rows[doc]["has_summary"] is (served is not None), doc
    assert rows[real]["has_summary"] is True
    assert rows[none]["has_summary"] is False


async def test_patch_refuses_a_project_field(client, auth_headers, filed):
    """Moving a document between spaces is not a rename. The field is absent
    from the model and extra keys are forbidden, so this is 422 rather than a
    silently dropped key."""
    doc = await filed("notes/q.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}", json={"project": "other"}, headers=auth_headers
    )

    assert response.status_code == 422


async def test_patch_refuses_an_over_long_tag(client, auth_headers, filed):
    """The column is the only length guard the service has, so an over-long
    name would reach the driver as a DataError with no savepoint under it."""
    from app.models.memory import TAG_NAME_MAX_LENGTH

    doc = await filed("notes/t.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}",
        json={"tags": ["x" * (TAG_NAME_MAX_LENGTH + 1)]},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_patch_refuses_a_tag_whose_category_is_over_long(
    client, auth_headers, filed,
):
    """`get_or_create` derives the category from everything before the first
    slash and writes it to a narrower column than the name's, so a tag can
    clear the name bound and still raise from the INSERT."""
    from app.models.memory import TAG_CATEGORY_MAX_LENGTH

    doc = await filed("notes/c.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}",
        json={"tags": ["x" * (TAG_CATEGORY_MAX_LENGTH + 1) + "/y"]},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_patch_of_a_missing_document_is_404(client, auth_headers):
    response = await client.patch(
        f"{V1}/documents/00000000-0000-0000-0000-000000000000",
        json={"title": "New"},
        headers=auth_headers,
    )

    assert response.status_code == 404


async def test_patch_refuses_an_empty_uri(client, auth_headers, filed):
    doc = await filed("notes/emptyuri.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}", json={"uri": ""}, headers=auth_headers
    )

    assert response.status_code == 422


async def test_patch_naming_no_field_is_422(client, auth_headers, filed):
    """An empty body is well formed and asks for nothing, and writing it would
    leave a permanent `{"fields": []}` row in an append-only table."""
    doc = await filed("notes/nofield.md", "body")

    response = await client.patch(
        f"{V1}/documents/{doc}", json={}, headers=auth_headers
    )

    assert response.status_code == 422


async def test_a_rename_onto_the_prefix_it_already_holds_is_422(
    client, auth_headers, filed,
):
    """One `document_updated` row per document for a call that moves nothing."""
    await filed("same/a.md", "one")

    response = await client.post(
        f"{V1}/documents/rename",
        json={"project": "p", "uri_prefix": "same", "new_uri_prefix": "same"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_a_rename_into_its_own_subtree_is_order_independent(
    client, auth_headers, filed,
):
    """`nest/a.md`'s target is `nest/deep/a.md`, which another row of the same
    set currently holds, so that row must move first. Iterating the locked
    rows in id order made which one went first a coin flip on UUID sort: the
    same call either answered 409 or produced this result."""
    await filed("nest/a.md", "one")
    await filed("nest/deep/a.md", "two")

    response = await client.post(
        f"{V1}/documents/rename",
        json={"project": "p", "uri_prefix": "nest", "new_uri_prefix": "nest/deep"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["renamed"] == 2
    for uri in ("nest/deep/a.md", "nest/deep/deep/a.md"):
        found = await client.get(
            f"{V1}/documents/by-uri", params={"project": "p", "uri": uri},
            headers=auth_headers,
        )
        assert found.status_code == 200, uri


async def test_patch_requires_auth(client, auth_headers, filed):
    doc = await filed("notes/auth.md", "body")

    response = await client.patch(f"{V1}/documents/{doc}", json={"title": "New"})

    assert response.status_code == 401


async def test_a_rename_onto_an_occupied_path_answers_409(
    client, auth_headers, filed,
):
    first = await filed("notes/r.md", "one")
    await filed("notes/s.md", "two")

    response = await client.patch(
        f"{V1}/documents/{first}", json={"uri": "notes/s.md"}, headers=auth_headers
    )

    assert response.status_code == 409


async def test_rename_rewrites_a_subtree_and_reports_the_count(
    client, auth_headers, filed,
):
    await filed("old/a.md", "one")
    await filed("old/nested/b.md", "two")
    await filed("other/c.md", "three")

    response = await client.post(
        f"{V1}/documents/rename",
        json={"project": "p", "uri_prefix": "old", "new_uri_prefix": "new"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["renamed"] == 2

    moved = await client.get(
        f"{V1}/documents/by-uri", params={"project": "p", "uri": "new/nested/b.md"},
        headers=auth_headers,
    )
    assert moved.status_code == 200


async def test_a_subtree_rename_onto_an_occupied_path_answers_409(
    client, auth_headers, filed,
):
    await filed("src/a.md", "one")
    await filed("dst/a.md", "two")

    response = await client.post(
        f"{V1}/documents/rename",
        json={"project": "p", "uri_prefix": "src", "new_uri_prefix": "dst"},
        headers=auth_headers,
    )

    assert response.status_code == 409


async def test_rename_requires_auth(client):
    response = await client.post(
        f"{V1}/documents/rename",
        json={"project": "p", "uri_prefix": "old", "new_uri_prefix": "new"},
    )

    assert response.status_code == 401


async def test_subtree_delete_removes_the_tree_and_reports_the_count(
    client, auth_headers, filed,
):
    await filed("gone/a.md", "one")
    await filed("gone/nested/b.md", "two")
    await filed("kept/c.md", "three")

    response = await client.post(
        f"{V1}/documents/delete",
        json={"project": "p", "uri_prefix": "gone"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == 2

    kept = await client.get(
        f"{V1}/documents/by-uri", params={"project": "p", "uri": "kept/c.md"},
        headers=auth_headers,
    )
    assert kept.status_code == 200


async def test_subtree_delete_of_nothing_reports_zero(client, auth_headers, filed):
    await filed("kept/c.md", "three")
    response = await client.post(
        f"{V1}/documents/delete",
        json={"project": "p", "uri_prefix": "absent"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["deleted"] == 0


async def test_subtree_delete_refuses_an_empty_prefix(client, auth_headers):
    response = await client.post(
        f"{V1}/documents/delete",
        json={"project": "p", "uri_prefix": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_subtree_delete_requires_auth(client):
    response = await client.post(
        f"{V1}/documents/delete",
        json={"project": "p", "uri_prefix": "gone"},
    )
    assert response.status_code == 401
