# Document Door and Section Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give coding agents a door to file markdown documents into darkmem and retrieve them a section at a time, so a spec or plan costs a few blocks to consult instead of a whole file.

**Architecture:** Four verbs (`put`, `search`, `outline`, `get`, plus `delete`) on both transports, each a thin door over services that already exist — `block_pipeline.ingest_document`, `BlockQueryService.search`, the documents repository. The one new behaviour is embedding blocks after the filing commits, plus a backstop job that sweeps blocks left without a vector.

**Tech Stack:** FastAPI, SQLAlchemy async, asyncpg, pgvector, FastMCP, pytest.

**Spec:** `docs/superpowers/specs/2026-08-23-document-door-design.md`

## Global Constraints

- **Bounds:** document content ≤ 1,000,000 characters, ≤ 5,000 blocks. Refuse with 422 naming which limit was hit.
- **Embed after commit, never inside the filing transaction.** `embedder_registry.register` commits on the session, so a filing that embedded inline would stop being rollback-able.
- **`block_query` is not to be edited.** `backend/tests/test_block_retrieval.py` asserts no fusion module imports it and that `block` stays out of `layer_composition.ID_KINDS`. Heading-path resolution belongs in the door.
- **Every new REST route and MCP tool needs a `Surface` row** in `PARITY_TABLE` (`backend/tests/test_door_parity.py`), the doc regenerated from it, and the doc's headline counts updated. Two tests fail otherwise.
- **`EVENT_TYPES` is taxonomy-first:** land a new event value in `app/services/events.py` before its emitter ships.
- **REST conventions** (`docs/api-rest-conventions.md`): 201 create, 204 delete, POST `.../search` for complex queries.
- **Response models on this surface carry `horizon: bool = True`**, matching `DocumentListResponse`.
- **Tests:** `cd backend && python -m pytest -q <path>`. Full gate before finishing: `./scripts/gate.sh` from the repo root.
- **This changes the running artifact**, so the branch is redeployed after the gate: `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → confirm the change is in the running image.

---

### Task 1: The put service — file, commit, embed

**Files:**
- Create: `backend/app/services/document_door.py`
- Test: `backend/tests/test_document_door.py`

**Interfaces:**
- Consumes: `app.services.block_pipeline.ingest_document`, `app.services.block_embeddings.embed_blocks`, `app.services.document_ingest.UNCHANGED`
- Produces: `MAX_CONTENT_CHARS`, `MAX_BLOCKS`, `DocumentTooLarge`, `PutResult(document_id: str, outcome: str, blocks_filed: int, blocks_embedded: int)`, `async put_document(session, llm, *, project, uri, content, title=None, source_type=None, properties=None, actor=None, source=None) -> PutResult`; `_resolve_title` (caller's title → stored title → first heading)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_document_door.py
import pytest
from app.services.document_door import (
    DocumentTooLarge, MAX_BLOCKS, MAX_CONTENT_CHARS, put_document,
)

FINGERPRINT = "test-fp-doc-door"


class StubEmbedder:
    """One fixed direction per text, under one fingerprint."""

    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint
        self.batches: list[list[str]] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], self.fingerprint


DOC = "# Title\n\nFirst para.\n\n## Section\n\nSecond para.\n"


@pytest.mark.asyncio
async def test_put_files_and_embeds_every_block(session):
    llm = StubEmbedder()
    result = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert result.outcome == "created"
    assert result.blocks_filed > 0
    assert result.blocks_embedded == result.blocks_filed


@pytest.mark.asyncio
async def test_refiling_identical_content_is_unchanged(session):
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/a.md", content=DOC)
    again = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert again.outcome == "unchanged"
    assert again.blocks_filed == 0


@pytest.mark.asyncio
async def test_unchanged_repush_embeds_blocks_that_lack_a_vector(session):
    """The repair path: an embed that failed post-commit must be fixable by
    pushing the same file again, which files nothing."""
    llm = StubEmbedder()
    first = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    from sqlalchemy import text
    from app.services.block_embeddings import PARENT_TABLE
    from app.services.embedder_registry import child_table

    await session.execute(text(f"DELETE FROM {child_table(PARENT_TABLE, FINGERPRINT)}"))
    repair = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert repair.outcome == "unchanged"
    assert repair.blocks_filed == 0
    assert repair.blocks_embedded == first.blocks_filed


@pytest.mark.asyncio
async def test_refile_without_a_title_does_not_null_the_stored_one(session):
    llm = StubEmbedder()
    await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC, title="Kept",
    )
    await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC + "\nmore\n",
    )
    row = (await session.execute(
        __import__("sqlalchemy").text(
            "SELECT title FROM documents WHERE project='p' AND uri='docs/a.md'"
        )
    )).scalar_one()
    assert row == "Kept"


@pytest.mark.asyncio
async def test_title_falls_back_to_the_first_heading(session):
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/b.md", content=DOC)
    row = (await session.execute(
        __import__("sqlalchemy").text(
            "SELECT title FROM documents WHERE project='p' AND uri='docs/b.md'"
        )
    )).scalar_one()
    assert row == "Title"


@pytest.mark.asyncio
async def test_content_over_the_char_bound_is_refused(session):
    llm = StubEmbedder()
    with pytest.raises(DocumentTooLarge) as excinfo:
        await put_document(
            session, llm, project="p", uri="docs/big.md",
            content="x" * (MAX_CONTENT_CHARS + 1),
        )
    assert str(MAX_CONTENT_CHARS) in str(excinfo.value)


@pytest.mark.asyncio
async def test_block_count_over_the_bound_is_refused(session):
    llm = StubEmbedder()
    with pytest.raises(DocumentTooLarge) as excinfo:
        await put_document(
            session, llm, project="p", uri="docs/many.md",
            content="\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)),
        )
    assert "blocks" in str(excinfo.value)
```

Every partition name — in code and in tests — resolves through `child_table(PARENT_TABLE, fingerprint)`. Invariant 2 forbids naming a child table directly, and the slug rule is not string substitution you can assume.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_document_door.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.services.document_door'`

- [ ] **Step 3: Write the service**

```python
# backend/app/services/document_door.py
"""The document door's write half (spec 2026-08-23).

**Embed after commit, never inside the filing.** First contact with an unknown
fingerprint runs child-table DDL through `embedder_registry.register`, which
commits on this session; embedding inside the filing transaction would make the
filing non-rollback-able. So: file, commit, then embed.

**The `unchanged` path still embeds.** `file_document` returns UNCHANGED before
touching any block, so a re-push of an identical file files nothing — which is
exactly the state a caller is in after an embed failed post-commit. Stopping
there would make the agent's one natural repair a no-op.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import PARENT_TABLE, embed_blocks
from app.repositories import documents as documents_repo
from app.services.block_pipeline import ingest_document
from app.services.document_ingest import UNCHANGED
from app.services.embedder_registry import child_table

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "DocumentTooLarge",
    "PutResult",
    "put_document",
]

# An order of magnitude above any plan or ledger. These exist to refuse a
# pathological input, not to shape usage: an unbounded document drives a
# synchronous parse and embed before the call returns, with no analogue of
# `buffer_wait_timeout_seconds` to degrade against.
MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000


class DocumentTooLarge(ValueError):
    """Refused at the door. The message names which bound was hit."""


@dataclass(frozen=True)
class PutResult:
    document_id: str
    outcome: str
    blocks_filed: int
    blocks_embedded: int


_BLOCK_IDS = text(
    "SELECT CAST(id AS text) AS id FROM blocks "
    "WHERE document_id = CAST(:document_id AS uuid)"
)


def _unembedded_sql(fingerprint: str) -> "text":
    child = child_table(PARENT_TABLE, fingerprint)
    return text(
        f"SELECT CAST(b.id AS text) AS id FROM blocks b "
        f"LEFT JOIN {child} e ON e.block_id = b.id "
        f"WHERE b.document_id = CAST(:document_id AS uuid) AND e.block_id IS NULL"
    )


_FIRST_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


async def _resolve_title(
    session: AsyncSession, *, project: str, uri: str, title: str | None, content: str
) -> str | None:
    """The title to file, resolved so a re-file cannot null a stored one.

    `update_document` and the upsert overwrite `title` wholesale, NULLs
    included, so passing the caller's `None` straight through would erase a
    title a previous call established. Order: what the caller said, then what
    the row already holds, then the document's first heading.
    """
    if title:
        return title
    existing = await documents_repo.resolve_by_uri(session, project=project, uri=uri)
    if existing is not None and existing.title:
        return existing.title
    match = _FIRST_HEADING.search(content)
    return match.group(1) if match else None


async def put_document(
    session: AsyncSession,
    llm,
    *,
    project: str,
    uri: str,
    content: str,
    title: str | None = None,
    source_type: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    source: str | None = None,
) -> PutResult:
    if len(content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(
            f"content is {len(content)} characters; the bound is "
            f"{MAX_CONTENT_CHARS}"
        )

    resolved_title = await _resolve_title(
        session, project=project, uri=uri, title=title, content=content,
    )
    filed = await ingest_document(
        session,
        project=project,
        content=content,
        uri=uri,
        source_type=source_type,
        title=resolved_title,
        properties=properties,
        actor=actor,
        source=source,
    )
    if filed.blocks_written > MAX_BLOCKS:
        # Refused after the parse because the count is what the parse
        # produces; the SAVEPOINT in `file_document` has not committed yet,
        # so raising here leaves the document as it was.
        raise DocumentTooLarge(
            f"document parses to {filed.blocks_written} blocks; the bound is "
            f"{MAX_BLOCKS} blocks"
        )

    await session.commit()

    if filed.outcome == UNCHANGED:
        from app.repositories.vector import (
            EmbedderFingerprintUnresolved, resolve_read_fingerprint,
        )

        try:
            fingerprint = await resolve_read_fingerprint(session, llm)
        except EmbedderFingerprintUnresolved:
            # Nothing has ever been embedded on this install, so there is no
            # partition to find gaps in. The next real filing registers one.
            return PutResult(
                document_id=str(filed.document_id), outcome=filed.outcome,
                blocks_filed=filed.blocks_written, blocks_embedded=0,
            )
        rows = await session.execute(
            _unembedded_sql(fingerprint), {"document_id": str(filed.document_id)}
        )
    else:
        rows = await session.execute(
            _BLOCK_IDS, {"document_id": str(filed.document_id)}
        )
    block_ids = [r.id for r in rows]

    written = 0
    if block_ids:
        result = await embed_blocks(session, llm, block_ids=block_ids)
        # `None` means nothing was embedded and no fingerprint was measured.
        # Report it as zero rather than as success: the caller's whole reason
        # for reading this number is to learn its document is unfindable.
        written = result.written if result is not None else 0
        await session.commit()

    return PutResult(
        document_id=str(filed.document_id),
        outcome=filed.outcome,
        blocks_filed=filed.blocks_written,
        blocks_embedded=written,
    )
```

Check two names against the source before running: `PARENT_TABLE` and `child_table`'s signature in `app/services/block_embeddings.py` / `app/services/embedder_registry.py`, and the exact string values of the `outcome` constants in `app/services/document_ingest.py` (`CREATED` / `UPDATED` / `UNCHANGED`). Use the real constants; do not restate their literals.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_document_door.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_door.py backend/tests/test_document_door.py
git commit -m "feat(documents): put service that files, commits, then embeds"
```

---

### Task 2: The write door on REST

**Files:**
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/tests/test_door_parity.py` (add `documents.write` to `PARITY_TABLE`)
- Modify: `docs/two-door-parity.md` (regenerate the table, update headline counts)
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: `put_document`, `PutResult`, `DocumentTooLarge` from Task 1
- Produces: `POST /api/v1/documents` returning `DocumentPutResponse(document_id, outcome, blocks_filed, blocks_embedded, horizon=True)`; `DELETE /api/v1/documents/{document_id}` returning 204

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_document_routes.py
import pytest

V1 = "/api/v1"
DOC = "# Title\n\nFirst para.\n\n## Section\n\nSecond para.\n"


@pytest.mark.asyncio
async def test_put_creates_and_reports_both_counts(client, auth_headers):
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


@pytest.mark.asyncio
async def test_oversized_content_is_refused_with_the_limit_named(client, auth_headers):
    from app.services.document_door import MAX_CONTENT_CHARS

    response = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/big.md", "content": "x" * (MAX_CONTENT_CHARS + 1)},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert str(MAX_CONTENT_CHARS) in response.text


@pytest.mark.asyncio
async def test_delete_removes_the_document_and_answers_204(client, auth_headers):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/a.md", "content": DOC},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    deleted = await client.delete(f"{V1}/documents/{document_id}", headers=auth_headers)
    assert deleted.status_code == 204

    listed = await client.get(f"{V1}/documents", params={"project": "p"}, headers=auth_headers)
    assert all(item["id"] != document_id for item in listed.json()["items"])
```

Read `backend/tests/conftest.py` for the real fixture names (`client`, `auth_headers`, `session`) and the embedder the app under test is configured with — if the app has no orchestrator in tests, wire the stub from Task 1 through the `get_llm` dependency override the way an existing route test does.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_document_routes.py -q`
Expected: FAIL with 404 or 405 on `POST /api/v1/documents`

- [ ] **Step 3: Add the schemas and routes**

```python
# in backend/app/api/routes/documents.py, beside the existing response models

class DocumentPutRequest(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    uri: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    title: str | None = None
    source_type: str | None = None


class DocumentPutResponse(BaseModel):
    document_id: str
    # created | updated | unchanged. `unchanged` still reports an embedded
    # count: it is the repair path for a filing whose embed failed.
    outcome: str
    blocks_filed: int
    blocks_embedded: int
    horizon: bool = True


@router.post("", response_model=DocumentPutResponse, status_code=status.HTTP_201_CREATED)
async def put_document_route(
    body: DocumentPutRequest,
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
    _: None = Depends(require_auth),
) -> DocumentPutResponse:
    """File one document, then embed its blocks.

    201 on every outcome including `unchanged`: the document exists at a known
    id either way, and a caller distinguishing the cases reads `outcome`.
    """
    from app.services.document_door import DocumentTooLarge, put_document

    try:
        result = await put_document(
            session, llm,
            project=body.project, uri=body.uri, content=body.content,
            title=body.title, source_type=body.source_type, source="api",
        )
    except DocumentTooLarge as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except UnsupportedSource as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return DocumentPutResponse(
        document_id=result.document_id,
        outcome=result.outcome,
        blocks_filed=result.blocks_filed,
        blocks_embedded=result.blocks_embedded,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_route(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_auth),
) -> None:
    """Remove a document, its block subtree and its vectors.

    `blocks.document_id` cascades and `block_embeddings__<slug>` cascades from
    there, so one delete takes all three in every partition.
    """
    result = await session.execute(
        text("DELETE FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(document_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    await session.commit()
```

Import `UnsupportedSource` from `app.services.block_pipeline` at the top of the module.

- [ ] **Step 4: Add the parity row**

In `backend/tests/test_door_parity.py`, add to `PARITY_TABLE` (MCP tuple empty for now — Task 5 fills it):

```python
    Surface(
        name="documents.write",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/documents"),
            ("DELETE", f"{V1}/documents/{{document_id}}"),
        ),
        mcp=(),
        reason=(
            "The MCP twins land in the same epic; this row is REST-only only "
            "until they do."
        ),
    ),
```

- [ ] **Step 5: Regenerate the parity doc and its counts**

```bash
cd backend && python -c "from tests.test_door_parity import render_markdown; print(render_markdown())"
```

Paste the output between the `<!-- BEGIN GENERATED PARITY TABLE -->` and `<!-- END GENERATED PARITY TABLE -->` markers in `docs/two-door-parity.md`, then update the headline count sentence — `test_the_committed_table_reports_its_own_counts` prints the exact string it wants when it fails.

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_document_routes.py tests/test_door_parity.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_document_routes.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "feat(documents): REST write and delete doors"
```

---

### Task 3: Section search with heading paths

**Files:**
- Modify: `backend/app/services/document_door.py`
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/tests/test_door_parity.py`, `docs/two-door-parity.md`
- Test: `backend/tests/test_document_door.py`, `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: `BlockQueryService.search` returning `BlockHit(block_id, document_id, project, uri, type, text, order_index, char_span, score, id_kind, layer)`
- Produces: `async search_sections(session, llm, *, query, project, limit=20, document_id=None) -> list[SectionHit]` where `SectionHit` adds `title: str | None` and `heading_path: list[str]` to the `BlockHit` fields; `POST /api/v1/documents/search`

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_document_door.py
NESTED = (
    "# Guide\n\nIntro para.\n\n"
    "## Setup\n\nRun the installer.\n\n"
    "### Windows\n\nUse the msi.\n\n"
    "## Teardown\n\nDelete the folder.\n"
)


@pytest.mark.asyncio
async def test_search_returns_the_heading_path_of_each_hit(session):
    from app.services.document_door import put_document, search_sections

    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/g.md", content=NESTED)

    hits = await search_sections(session, llm, query="installer", project="p")
    assert hits, "the stub embedder ranks everything equally; expect all blocks"
    deepest = next(h for h in hits if h.text.strip() == "Use the msi.")
    assert deepest.heading_path == ["Guide", "Setup", "Windows"]
    assert deepest.uri == "docs/g.md"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_document_door.py -k heading_path -q`
Expected: FAIL, `cannot import name 'search_sections'`

- [ ] **Step 3: Implement the search wrapper**

Add to `backend/app/services/document_door.py`:

```python
_ANCESTORS = text(
    """
    WITH RECURSIVE up AS (
        SELECT id, parent_id, text, type, 0 AS depth
        FROM blocks WHERE id = ANY(CAST(:ids AS uuid[]))
        UNION ALL
        SELECT b.id, b.parent_id, b.text, b.type, up.depth + 1
        FROM blocks b JOIN up ON b.id = up.parent_id
    )
    SELECT CAST(id AS text) AS id, CAST(parent_id AS text) AS parent_id,
           text, type
    FROM up
    """
)


@dataclass(frozen=True)
class SectionHit:
    block_id: str
    document_id: str
    project: str
    uri: str | None
    title: str | None
    heading_path: list[str]
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    score: float


async def search_sections(
    session: AsyncSession,
    llm,
    *,
    query: str,
    project: str,
    limit: int = 20,
    document_id: str | None = None,
) -> list[SectionHit]:
    """Rank blocks, then resolve each hit's heading path.

    The path is walked here rather than in `block_query`: that module is under
    a structural test keeping the block channel out of the memory composition,
    and the cheapest way to keep it there is to not touch it.
    """
    from app.services.block_query import BlockQueryService

    hits = await BlockQueryService(session, llm).search(
        query, project=project, limit=limit, document_id=document_id,
    )
    if not hits:
        return []

    rows = (await session.execute(
        _ANCESTORS, {"ids": [h.block_id for h in hits]}
    )).mappings().all()
    by_id = {r["id"]: r for r in rows}

    titles = {
        r["id"]: r["title"]
        for r in (await session.execute(
            text(
                "SELECT CAST(id AS text) AS id, title FROM documents "
                "WHERE id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": list({h.document_id for h in hits})},
        )).mappings().all()
    }

    def path_for(block_id: str) -> list[str]:
        path: list[str] = []
        seen: set[str] = set()
        node = by_id.get(block_id)
        while node is not None and node["id"] not in seen:
            seen.add(node["id"])
            if node["type"] == "heading" and node["text"]:
                path.append(node["text"])
            parent = node["parent_id"]
            node = by_id.get(parent) if parent else None
        return list(reversed(path))

    return [
        SectionHit(
            block_id=h.block_id, document_id=h.document_id, project=h.project,
            uri=h.uri, title=titles.get(h.document_id),
            heading_path=path_for(h.block_id), type=h.type, text=h.text,
            order_index=h.order_index, char_span=h.char_span, score=h.score,
        )
        for h in hits
    ]
```

The `seen` set is a cycle guard: `blocks.parent_id` has no constraint forbidding one, and an infinite walk inside a request is worse than a truncated path.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_document_door.py -k heading_path -q`
Expected: PASS

- [ ] **Step 5: Add the REST route**

```python
# in backend/app/api/routes/documents.py

class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    project: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    document_id: str | None = None




class SectionHitModel(BaseModel):
    block_id: str
    document_id: str
    project: str
    uri: str | None
    title: str | None
    heading_path: list[str]
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    score: float


class DocumentSearchResponse(BaseModel):
    items: list[SectionHitModel]
    horizon: bool = True


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents_route(
    body: DocumentSearchRequest,
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
    _: None = Depends(require_auth),
) -> DocumentSearchResponse:
    """Rank this project's blocks. An empty list means no match, never a
    failure — the channel has one arm, so a failure raises."""
    from app.services.document_door import search_sections

    hits = await search_sections(
        session, llm, query=body.query, project=body.project,
        limit=body.limit, document_id=body.document_id,
    )
    return DocumentSearchResponse(items=[SectionHitModel(**vars(h)) for h in hits])
```

- [ ] **Step 6: Add the parity row and regenerate**

Add a `documents.retrieval` Surface with `("POST", f"{V1}/documents/search")` in `rest`, `mcp=()`, and the same "MCP twins land in the same epic" reason. Regenerate the doc and its counts exactly as in Task 2, Step 5.

- [ ] **Step 7: Run and commit**

Run: `cd backend && python -m pytest tests/test_document_door.py tests/test_document_routes.py tests/test_door_parity.py -q`
Expected: PASS

```bash
git add backend/app/services/document_door.py backend/app/api/routes/documents.py backend/tests/ docs/two-door-parity.md
git commit -m "feat(documents): section search with heading paths"
```

---

### Task 4: Outline and fetch

**Files:**
- Modify: `backend/app/services/document_door.py`, `backend/app/api/routes/documents.py`
- Modify: `backend/tests/test_door_parity.py`, `docs/two-door-parity.md`
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `async document_outline(session, *, document_id) -> list[OutlineNode]` with `OutlineNode(block_id: str, level: int, text: str, order_index: int | None)`; `async document_blocks(session, *, document_id, block_ids=None) -> list[BlockRow]`; `GET /api/v1/documents/{document_id}/outline`; `GET /api/v1/documents/{document_id}`

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_document_routes.py
NESTED = (
    "# Guide\n\nIntro para.\n\n"
    "## Setup\n\nRun the installer.\n\n"
    "### Windows\n\nUse the msi.\n\n"
)


@pytest.mark.asyncio
async def test_outline_returns_headings_with_levels_and_no_body(client, auth_headers):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]

    response = await client.get(f"{V1}/documents/{document_id}/outline", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert [(i["level"], i["text"]) for i in items] == [
        (1, "Guide"), (2, "Setup"), (3, "Windows"),
    ]
    assert "Run the installer." not in response.text


@pytest.mark.asyncio
async def test_get_returns_only_the_blocks_named(client, auth_headers):
    created = await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    document_id = created.json()["document_id"]
    outline = await client.get(f"{V1}/documents/{document_id}/outline", headers=auth_headers)
    target = outline.json()["items"][1]["block_id"]

    response = await client.get(
        f"{V1}/documents/{document_id}", params={"block_ids": target}, headers=auth_headers,
    )
    assert response.status_code == 200
    blocks = response.json()["blocks"]
    assert [b["block_id"] for b in blocks] == [target]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_document_routes.py -k "outline or blocks_named" -q`
Expected: FAIL with 404

- [ ] **Step 3: Implement the two service functions**

```python
# append to backend/app/services/document_door.py

@dataclass(frozen=True)
class OutlineNode:
    block_id: str
    level: int
    text: str
    order_index: int | None


@dataclass(frozen=True)
class BlockRow:
    block_id: str
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None


_OUTLINE = text(
    """
    SELECT CAST(id AS text) AS id, order_index, text,
           COALESCE((properties->>'level')::int, 1) AS level
    FROM blocks
    WHERE document_id = CAST(:document_id AS uuid) AND type = 'heading'
    ORDER BY order_index
    """
)


async def document_outline(
    session: AsyncSession, *, document_id: str
) -> list[OutlineNode]:
    """The heading tree, no body text. No model call: this reads the tree the
    parser already built, and is deliberately not `document_summary`."""
    rows = (await session.execute(
        _OUTLINE, {"document_id": document_id}
    )).mappings().all()
    return [
        OutlineNode(
            block_id=r["id"], level=r["level"], text=r["text"] or "",
            order_index=r["order_index"],
        )
        for r in rows
    ]


_BLOCKS = """
    SELECT CAST(id AS text) AS id, type, text, order_index,
           lower(char_span) AS span_start, upper(char_span) AS span_end
    FROM blocks
    WHERE document_id = CAST(:document_id AS uuid)
      {clause}
    ORDER BY order_index
"""


async def document_blocks(
    session: AsyncSession, *, document_id: str, block_ids: list[str] | None = None
) -> list[BlockRow]:
    clause = "AND id = ANY(CAST(:ids AS uuid[]))" if block_ids else ""
    params: dict = {"document_id": document_id}
    if block_ids:
        params["ids"] = block_ids
    rows = (await session.execute(
        text(_BLOCKS.format(clause=clause)), params
    )).mappings().all()
    return [
        BlockRow(
            block_id=r["id"], type=r["type"], text=r["text"] or "",
            order_index=r["order_index"],
            char_span=(
                (r["span_start"], r["span_end"])
                if r["span_start"] is not None else None
            ),
        )
        for r in rows
    ]
```

- [ ] **Step 4: Add the two routes**

```python
class OutlineNodeModel(BaseModel):
    block_id: str
    level: int
    text: str
    order_index: int | None


class DocumentOutlineResponse(BaseModel):
    document_id: str
    items: list[OutlineNodeModel]
    horizon: bool = True


class BlockRowModel(BaseModel):
    block_id: str
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None


class DocumentBlocksResponse(BaseModel):
    document_id: str
    blocks: list[BlockRowModel]
    horizon: bool = True


@router.get("/{document_id}/outline", response_model=DocumentOutlineResponse)
async def document_outline_route(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_auth),
) -> DocumentOutlineResponse:
    from app.services.document_door import document_outline

    nodes = await document_outline(session, document_id=str(document_id))
    return DocumentOutlineResponse(
        document_id=str(document_id),
        items=[OutlineNodeModel(**vars(n)) for n in nodes],
    )


@router.get("/{document_id}", response_model=DocumentBlocksResponse)
async def document_blocks_route(
    document_id: UUID,
    block_ids: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_auth),
) -> DocumentBlocksResponse:
    from app.services.document_door import document_blocks

    rows = await document_blocks(
        session, document_id=str(document_id), block_ids=block_ids,
    )
    return DocumentBlocksResponse(
        document_id=str(document_id),
        blocks=[BlockRowModel(**vars(r)) for r in rows],
    )
```

Route ordering matters: FastAPI matches in declaration order, so `GET /{document_id}/outline` must be declared before `GET /{document_id}` only if the latter's converter would swallow it — it will not, since the paths differ in segment count, but keep the more specific route first regardless.

- [ ] **Step 5: Extend the parity row**

Add both GET paths to the `documents.retrieval` Surface's `rest` tuple, regenerate the doc and counts.

- [ ] **Step 6: Run and commit**

Run: `cd backend && python -m pytest tests/test_document_routes.py tests/test_door_parity.py -q`
Expected: PASS

```bash
git add backend/app/services/document_door.py backend/app/api/routes/documents.py backend/tests/ docs/two-door-parity.md
git commit -m "feat(documents): outline and block fetch"
```

---

### Task 5: The MCP tools

**Files:**
- Modify: `backend/app/api/mcp/server.py`
- Modify: `backend/tests/test_door_parity.py`, `docs/two-door-parity.md`
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: every service function from Tasks 1, 3 and 4
- Produces: MCP tools `document_put`, `document_search`, `document_outline`, `document_get`, `document_delete`, each returning a JSON string

- [ ] **Step 1: Write the failing parity test**

```python
# append to backend/tests/test_document_routes.py
@pytest.mark.asyncio
async def test_both_doors_answer_the_same_search(client, auth_headers, session, monkeypatch):
    """Two-door parity is asserted on the ranked order, not the shape: a
    shape comparison passes while orders diverge."""
    import json
    from app.api.mcp import server as mcp_server

    await client.post(
        f"{V1}/documents",
        json={"project": "p", "uri": "docs/g.md", "content": NESTED},
        headers=auth_headers,
    )
    rest = await client.post(
        f"{V1}/documents/search",
        json={"query": "installer", "project": "p"},
        headers=auth_headers,
    )
    tool = json.loads(await mcp_server.document_search(query="installer", project="p"))

    assert [i["block_id"] for i in rest.json()["items"]] == [i["block_id"] for i in tool]
```

Follow the existing MCP-door tests in `tests/test_door_parity.py` for how they bind `mcp_server.async_session_factory` and the pipeline's `llm` to the test session — copy that fixture rather than inventing one.

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_document_routes.py -k both_doors -q`
Expected: FAIL, `module 'app.api.mcp.server' has no attribute 'document_search'`

- [ ] **Step 3: Add the tools**

```python
# in backend/app/api/mcp/server.py, after the checkpoint tools

@mcp.tool(
    description=(
        "File a markdown or plain-text document into darkmem, keyed on its "
        "repo-relative path. Re-filing the same path updates it in place. "
        "Returns the document id and how many blocks were filed and embedded."
    )
)
async def document_put(
    project: str,
    uri: str,
    content: str,
    title: str | None = None,
    source_type: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Args:
        project: Scope, the same key memory_add writes under.
        uri: Repo-relative path, e.g. "docs/plans/2026-08-23-thing.md".
        content: The file's text. The server never reads your filesystem.
        title: Optional; falls back to the document's first heading.
        source_type: Optional; inferred from the uri suffix.
    """
    from app.services.document_door import put_document

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))

    source = resolve_client_source(None, ctx, fallback="mcp")
    async with async_session_factory() as session:
        try:
            result = await put_document(
                session, _pipeline.llm,
                project=project, uri=uri, content=content,
                title=title, source_type=source_type, source=source,
            )
        except Exception:
            await session.rollback()
            raise
    return json.dumps(vars(result))


@mcp.tool(
    description=(
        "Search documents by meaning and get back the matching sections, not "
        "whole files. Each hit carries its document title, path and heading "
        "path. Use this before reading a spec or plan from disk."
    )
)
async def document_search(
    query: str,
    project: str,
    limit: int = 20,
    document_id: str | None = None,
) -> str:
    from app.services.document_door import search_sections

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", results=[]))

    limit = _clamp_limit(limit, default=20)
    async with async_session_factory() as session:
        hits = await search_sections(
            session, _pipeline.llm, query=query, project=project,
            limit=limit, document_id=document_id,
        )
    return json.dumps([vars(h) for h in hits])


@mcp.tool(description="List a document's headings with their levels and block ids. No body text.")
async def document_outline(document_id: str) -> str:
    from app.services.document_door import document_outline as _outline

    did = _validate_uuid(document_id)
    async with async_session_factory() as session:
        nodes = await _outline(session, document_id=str(did))
    return json.dumps([vars(n) for n in nodes])


@mcp.tool(description="Fetch a document's blocks, or only the block ids named.")
async def document_get(document_id: str, block_ids: list[str] | None = None) -> str:
    from app.services.document_door import document_blocks

    did = _validate_uuid(document_id)
    async with async_session_factory() as session:
        rows = await document_blocks(
            session, document_id=str(did), block_ids=block_ids,
        )
    return json.dumps([vars(r) for r in rows])


@mcp.tool(description="Delete a document, its blocks and its vectors. Use when its file is gone.")
async def document_delete(document_id: str) -> str:
    from sqlalchemy import text as _text

    did = _validate_uuid(document_id)
    async with async_session_factory() as session:
        result = await session.execute(
            _text("DELETE FROM documents WHERE id = CAST(:id AS uuid)"),
            {"id": str(did)},
        )
        if result.rowcount == 0:
            raise ValueError(f"Document not found: {document_id}")
        await session.commit()
    return json.dumps({"document_id": str(did), "deleted": True})
```

Note `document_outline` is imported under an alias because the tool function shares its name with the service function.

- [ ] **Step 4: Flip the parity rows to two-door and rewrite the reads row**

In `PARITY_TABLE`: give `documents.write` `mcp=("document_put", "document_delete")` and `documents.retrieval` `mcp=("document_search", "document_outline", "document_get")`, set both to `TWO_DOOR`, and replace their placeholder reasons with the ruling:

```python
        reason=(
            "Owner ruling 2026-08-23. G-F gates the faithfulness judge, which "
            "governs documents.grounded_qa -- an answer that is generated, "
            "labelled and served. These verbs generate nothing and label "
            "nothing: they file a document and return its own text with a "
            "cosine score, as code.search returns source. The doc 16 firewall "
            "is against block rows reaching the verified vault unlifted, and "
            "tests/test_block_retrieval.py bars that structurally. This does "
            "not clear G-F and no bar moved."
        ),
```

Then rewrite `documents.reads`' reason so the superseded clause does not sit beside the new rows:

```python
        reason=(
            "The list, summary and connection reads have no MCP twin yet -- "
            "scope, not gate. The 'single-door until G-F clears' clause that "
            "stood here was superseded by the owner ruling of 2026-08-23; see "
            "the documents.write and documents.retrieval rows. "
            "documents.grounded_qa below is the row G-F still governs."
        ),
```

- [ ] **Step 5: Regenerate the doc, its counts, and the hand-written prose above the table**

Regenerate as in Task 2 Step 5. Then read the prose paragraphs in `docs/two-door-parity.md` above and below the generated table and update any sentence that states the old documents ruling — that prose is hand-written and the generator does not touch it.

- [ ] **Step 6: Run and commit**

Run: `cd backend && python -m pytest tests/test_document_routes.py tests/test_door_parity.py -q`
Expected: PASS

```bash
git add backend/app/api/mcp/server.py backend/tests/ docs/two-door-parity.md
git commit -m "feat(documents): MCP document tools"
```

---

### Task 6: The backstop embedding job

**Files:**
- Modify: `backend/app/services/events.py` (add the event type)
- Create: `backend/app/services/block_embedding_refresh.py`
- Modify: `backend/app/services/job_runners.py`, `backend/app/main.py`
- Modify: `backend/tests/test_code_deriver.py` (expected roster), `CLAUDE.md` (job count)
- Test: `backend/tests/test_block_embedding_refresh.py`

**Interfaces:**
- Consumes: `embed_blocks`, `child_table`, `PARENT_TABLE`
- Produces: `BLOCK_EMBEDDING_JOB_KEY = "block_embedding_refresh"`, `BLOCK_EMBEDDING_CONFIG_SCHEMA`, `async refresh_block_embeddings(session, llm, *, batch: int) -> int`, `make_block_embedding_runner(app, session_factory)`

- [ ] **Step 1: Add the event type first**

In `backend/app/services/events.py`, add `"block_embeddings_refreshed"` to `EVENT_TYPES` beside `"document_filed"`. Taxonomy-first: the value lands before its emitter.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_block_embedding_refresh.py
import pytest
from sqlalchemy import text

from app.services.block_embedding_refresh import refresh_block_embeddings
from tests.test_document_door import DOC, FINGERPRINT, StubEmbedder


@pytest.mark.asyncio
async def test_refresh_embeds_blocks_that_have_no_vector(session):
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    filed = await put_document(session, llm, project="p", uri="docs/a.md", content=DOC)
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    embedded = await refresh_block_embeddings(session, llm, batch=100)
    assert embedded == filed.blocks_filed

    again = await refresh_block_embeddings(session, llm, batch=100)
    assert again == 0, "a second pass must find nothing left to do"
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_block_embedding_refresh.py -q`
Expected: FAIL, no module `app.services.block_embedding_refresh`

- [ ] **Step 4: Implement the sweep**

```python
# backend/app/services/block_embedding_refresh.py
"""Backstop for the document door's inline embed (spec 2026-08-23).

Inline embedding covers the common path. This covers what it cannot: an embed
that failed after its filing committed, an embedder rotation that leaves every
existing block in a dead partition, and documents filed before the door
shipped. Tier C -- never on the capture or retrieval hot path.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import (
    EmbedderFingerprintUnresolved,
    resolve_read_fingerprint,
)
from app.services.block_embeddings import PARENT_TABLE, embed_blocks
from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

__all__ = [
    "BLOCK_EMBEDDING_CONFIG_SCHEMA",
    "BLOCK_EMBEDDING_CRON",
    "BLOCK_EMBEDDING_JOB_KEY",
    "BLOCK_EMBEDDING_MAX_RUN_SECONDS",
    "BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS",
    "refresh_block_embeddings",
]

BLOCK_EMBEDDING_JOB_KEY = "block_embedding_refresh"
BLOCK_EMBEDDING_CRON = "35 * * * *"
BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS = 300
BLOCK_EMBEDDING_MAX_RUN_SECONDS = 900

BLOCK_EMBEDDING_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="batch",
        label="Blocks per run",
        type="int",
        default=500,
        minimum=0,
        maximum=5000,
        description=(
            "Blocks embedded per run. Each one spends an embedding call, so 0 "
            "disables the sweep."
        ),
    ),
]


async def refresh_block_embeddings(
    session: AsyncSession, llm, *, batch: int
) -> int:
    """Embed up to `batch` blocks lacking a vector under the active embedder.

    The fingerprint is resolved by data through `resolve_read_fingerprint`,
    the same way `refresh_relation_embeddings` does it.
    """
    if batch <= 0:
        return 0

    # Resolved by data, never from static config, and never by spending an
    # embed call: an install where nothing has been embedded has no
    # fingerprint to key on, and this arm has nothing to cover until one
    # exists. Same mechanism as `refresh_relation_embeddings`.
    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info("block_embedding_refresh: no fingerprint holds data yet")
        return 0
    await _ensure_partition(session, fingerprint)
    child = child_table(PARENT_TABLE, fingerprint)
    rows = (await session.execute(
        text(
            f"SELECT CAST(b.id AS text) AS id FROM blocks b "
            f"LEFT JOIN {child} e ON e.block_id = b.id "
            f"WHERE e.block_id IS NULL ORDER BY b.id LIMIT :limit"
        ),
        {"limit": batch},
    )).mappings().all()
    block_ids = [r["id"] for r in rows]
    if not block_ids:
        return 0

    result = await embed_blocks(session, llm, block_ids=block_ids)
    await session.commit()
    return result.written if result is not None else 0
```

`FieldDescriptor`'s real import path and field names must be checked against `app/services/job_registry.py` before running — copy the shape `RELATION_EMBEDDING_CONFIG_SCHEMA` uses in `app/services/relation_embeddings.py`. Likewise `_ensure_partition`: copy how `relation_embeddings` defines and calls its own.

- [ ] **Step 5: Add the runner and register the job**

In `backend/app/services/job_runners.py`, copy `make_relation_embedding_runner` (line 563) exactly, substituting the block constants and `refresh_block_embeddings`, keeping its two behaviours: a no-op with a log line when `app.state.llm` is None, and loading knobs from the registry over the schema defaults. Journal the run with `record_event` using `"block_embeddings_refreshed"`.

In `backend/app/main.py`, register beside `RELATION_EMBEDDING_JOB_KEY`:

```python
    job_registry.register(Job(
        key=BLOCK_EMBEDDING_JOB_KEY,
        display_name="Block Embedding Refresh",
        description=(
            "Embeds document blocks that have no vector under the active "
            "embedder: an embed that failed after its filing committed, an "
            "embedder rotation, or documents filed before the door shipped. "
            "Off the hot path. Each run spends embedding calls, so 0 disables "
            "it."
        ),
        default_cron=BLOCK_EMBEDDING_CRON,
        min_interval_seconds=BLOCK_EMBEDDING_MIN_INTERVAL_SECONDS,
        runner=make_block_embedding_runner(app, async_session_factory),
        max_run_seconds=BLOCK_EMBEDDING_MAX_RUN_SECONDS,
        config_schema=BLOCK_EMBEDDING_CONFIG_SCHEMA,
    ))
```

- [ ] **Step 6: Update the roster test and CLAUDE.md**

`tests/test_code_deriver.py` (around lines 1489-1533) holds a hardcoded expected set of job keys — add `block_embedding_refresh`. Then update CLAUDE.md's Jobs section: the count moves from twenty-three to twenty-four, the live list gains `block_embedding_refresh`, and it joins the sentence listing jobs that register via a `*_JOB_KEY` constant.

- [ ] **Step 7: Run and commit**

Run: `cd backend && python -m pytest tests/test_block_embedding_refresh.py tests/test_code_deriver.py -q`
Expected: PASS

```bash
git add backend/app/services/ backend/app/main.py backend/tests/ CLAUDE.md
git commit -m "feat(documents): block embedding refresh job"
```

---

### Task 7: Gate, deploy, and document the door

**Files:**
- Modify: `CLAUDE.md` (a Documents section)

- [ ] **Step 1: Run the full gate**

Run: `./scripts/gate.sh`
Expected: green. `GATE BLOCKED` (exit 2) means a missing toolchain, not a red gate.

- [ ] **Step 2: Add the CLAUDE.md section**

Document the door under a new heading: the five verbs, the `(project, uri)` identity, the bounds, that an edit re-embeds the whole document, that `unchanged` still repairs a missing embed, and the owner ruling of 2026-08-23 with a pointer to `docs/two-door-parity.md`.

- [ ] **Step 3: Commit the docs**

```bash
git add CLAUDE.md
git commit -m "docs: record the document door and its ruling"
```

- [ ] **Step 4: Build and deploy**

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
```

- [ ] **Step 5: Confirm the change is in the running image**

Wait for the container to report `healthy`, then verify the new route is actually served rather than only present in the tree:

```bash
curl -s localhost:8000/openapi.json | python3 -c "import json,sys; print('/api/v1/documents/search' in json.load(sys.stdin)['paths'])"
```

Expected: `True`. Compose reuses an image whose tag did not move, so a skipped or failed build redeploys the old bits and still reports `Started`.
