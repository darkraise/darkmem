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

    Copied from `tests/test_checkpoints.py`: an in-process call with
    `ctx=None` exercises the fallback rung and nothing above it, so the only
    way to see which source the door resolved is to drive it with a real
    header mapping.
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
    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_delete(project="p", uri="docs/never-filed.md")


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
async def test_document_delete_closes_the_provenance_window(session, both_doors):
    """The tool goes through `delete_document`, not a raw DELETE.

    `fact_sources.source_ref` carries no foreign key, so the cascade cannot
    reach it: a fact this document solely sourced would keep its origin count
    and its rung on evidence that no longer exists. This is the assertion a
    re-inlined `DELETE FROM documents` fails.
    """
    import json

    from sqlalchemy import text as _text

    from app.api.mcp import server as mcp_server
    from tests.test_document_door import _blocks_of, _fact, _sources_changed_count

    fact_id = await _fact(session)
    filed = json.loads(await mcp_server.document_put(
        project="p", uri="docs/sourced.md", content=DOC,
    ))
    blocks = await _blocks_of(session, filed["document_id"])
    from app.services.block_fact_sources import record_block_source

    await record_block_source(session, fact_id=fact_id, block_id=blocks[0])
    before = await _sources_changed_count(session, fact_id)

    result = json.loads(await mcp_server.document_delete(
        project="p", uri="docs/sourced.md",
    ))

    assert result == {"document_id": filed["document_id"], "deleted": True}
    assert (await session.execute(
        _text("SELECT count(*) FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": filed["document_id"]},
    )).scalar_one() == 0
    expired_at = (await session.execute(
        _text("SELECT expired_at FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
        {"f": fact_id},
    )).scalar_one()
    assert expired_at is not None, (
        "a fact left with no source must be expired -- the raw DELETE the plan "
        "sketched never reaches this"
    )
    assert await _sources_changed_count(session, fact_id) == before + 1


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
