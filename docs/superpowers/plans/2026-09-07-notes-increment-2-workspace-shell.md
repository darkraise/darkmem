# Notes Workspace Shell (increment 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Make the personal notes space reachable and usable — a `/notes` route with a tree you can create, rename, move, pin and delete in — and fix `/documents`, which renders empty today.

**Architecture:** `/notes` reuses `ProjectWorkspace` behind a `treeManagement` capability prop rather than forking a second workspace. The backend gains one new capability (a subtree delete, journaled, with its own admin-scoped MCP tool) and one new served field (`pinned_at` on the list item). Drag-to-move is `@dnd-kit/core` over a pure `moveTarget` function, dispatching the `PATCH` and `POST /rename` verbs that shipped in increment 1e.

**Tech Stack:** FastAPI + SQLAlchemy async + asyncpg (backend), React + TanStack Router/Query + darkraise-ui + vitest (frontend), `@dnd-kit/core` (new).

**Spec:** `docs/superpowers/specs/2026-09-07-notes-increment-2-workspace-shell-design.md`

## Global Constraints

- **Greenfield until the freeze.** No backward compatibility, no migration, no compatibility shim. This increment adds no schema objects, so no baseline regeneration is involved.
- **Taxonomy is closed.** `documents_deleted` must land in `EVENT_TYPES` *before* its emitter ships (Task 2 precedes Task 3).
- **darkraise-ui first.** Never re-implement a library component. A local component written against a library gap must record which gap.
- **Single worker.** Nothing here may assume more than one uvicorn worker.
- **English only** in code, comments, docs, commits, tests.
- **Commits:** `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period.
- **Backend tests** run from `backend/` as `.venv/bin/python -m pytest -q`, with `TEST_DATABASE_URL` pointed at a lane database (`darkmem_test_2`..`darkmem_test_5`), never at `darkmem_test` if another lane is running. Example:
  `TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" .venv/bin/python -m pytest -q <paths>`
- **Frontend tests** run from `frontend/` as `npm test` (vitest), typecheck as `npm run typecheck` (`tsc -b`, not bare `tsc`).
- **The guards leg is mandatory after Tasks 4, 5 and 11.** It is recorded in CLAUDE.md's Commands section. A new route, a new tool and a new frontend route each trip full-list enumeration guards that live outside the module the work was in.
- **`ORDER BY id FOR UPDATE`** is the lock order every multi-row document write in `document_door.py` takes. Do not change it in one place only.

---

### Task 1: Serve `pinned_at` on the document list item

`pinned_at` is written by `document_update` and read by nothing — `_PIN_ASSIGNMENT` (`document_door.py:80`) is its only mention in `backend/app`. The tree reads pin state from the list, so this is what makes a pin control renderable.

Served on the **list item only**. The keyed reads are TWO_DOOR and MCP `document_get` has no metadata slot, so a field there would be a wire divergence; the list route is `documents.reads`, REST-only already, so this costs no parity.

**Files:**
- Modify: `backend/app/api/routes/documents.py:131-137` (`DocumentListItem`), `:426-439` (`_LIST_SQL`)
- Modify: `frontend/src/hooks/api/use-documents-api.ts:12-19` (`DocumentListItem`)
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `DocumentListItem.pinned_at: str | None` (backend, ISO-8601 or null) and `pinned_at?: string | null` (frontend). Tasks 8 and 10 read it.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3
**Approach:** inline - skip 3: the spec fixed the list-item-only placement and its parity reasoning

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_document_routes.py`, beside the other list tests:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" \
  .venv/bin/python -m pytest -q tests/test_document_routes.py::test_the_list_serves_pinned_at
```

Expected: FAIL with `KeyError: 'pinned_at'`.

- [ ] **Step 3: Add the field to the response model**

`backend/app/api/routes/documents.py`, in `DocumentListItem`:

```python
class DocumentListItem(BaseModel):
    id: str
    title: str | None
    uri: str | None
    source_type: str | None
    project: str
    block_count: int
    # Served here and NOT on the keyed reads: those are TWO_DOOR and MCP
    # `document_get` has no metadata slot, so a REST-only field there would
    # be a wire divergence. This route is `documents.reads`, REST-only
    # already, so the field costs no parity.
    pinned_at: datetime | None = None
```

`datetime` is already imported in this module; confirm before adding an import.

- [ ] **Step 4: Select it**

In `_LIST_SQL`, add `d.pinned_at` to both the select list and the `GROUP BY`:

```python
_LIST_SQL = text(
    """
    SELECT CAST(d.id AS text) AS id, d.title, d.uri, d.source_type, d.project,
           d.pinned_at, count(b.id) AS block_count
    FROM documents d
    LEFT JOIN blocks b ON b.document_id = d.id
    -- CAST because asyncpg cannot infer a bare parameter's type in an
    -- IS NULL comparison (the cross-cutting invariant on raw-SQL params).
    WHERE (CAST(:project AS text) IS NULL OR d.project = CAST(:project AS text))
    GROUP BY d.id, d.title, d.uri, d.source_type, d.project, d.pinned_at
    ORDER BY d.created_at DESC
    LIMIT :limit OFFSET :offset
    """
)
```

- [ ] **Step 5: Run the test — it should pass**

Same command as Step 2. Expected: PASS.

- [ ] **Step 6: Add the frontend field as OPTIONAL**

`frontend/src/hooks/api/use-documents-api.ts`:

```ts
export interface DocumentListItem {
  id: string
  title: string | null
  uri: string | null
  source_type: string | null
  project: string
  block_count: number
  /** Optional so the four existing test fixtures that build this shape by
   *  hand keep typechecking. The API always sends it. */
  pinned_at?: string | null
}
```

Optional is load-bearing: four fixture files construct `DocumentListItem` literals and a required field breaks `tsc -b` in all of them.

- [ ] **Step 7: Typecheck**

```
cd frontend && npm run typecheck
```

Expected: clean. If it reports errors in `document-tree.test.tsx`, `uri-tree.test.ts`, `document-actions.test.tsx` or `project-workspace.test.tsx`, the field was not made optional.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_document_routes.py frontend/src/hooks/api/use-documents-api.ts
git commit -m "feat(documents): serve pinned_at on the list item"
```

---

### Task 2: Admit `documents_deleted` to the event vocabulary

Taxonomy-first, as CLAUDE.md requires: the value lands in the vocabulary and in the frontend tab map **before** its emitter (Task 3) ships. Landing it after would make `test_event_taxonomy_map` red, which is the guard this epic tripped most recently.

**Files:**
- Modify: `backend/app/services/events.py:172-179` (`EVENT_TYPES`)
- Modify: `frontend/src/features/activity/event-taxonomy.ts:31-38` (`EVENT_TYPE_CATEGORY`)
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the literal string `"documents_deleted"` in `EVENT_TYPES`. Task 3 emits it.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2
**Approach:** inline - skip 2: the repository already answers this; four sibling document event types were added the same way

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_events.py`:

```python
def test_documents_deleted_is_in_the_vocabulary():
    """Taxonomy-first: the value lands before its emitter, so the subtree
    delete cannot ship as the one document mutation with no journal row."""
    from app.services.events import EVENT_TYPES

    assert "documents_deleted" in EVENT_TYPES
```

- [ ] **Step 2: Run it and watch it fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" \
  .venv/bin/python -m pytest -q tests/test_events.py::test_documents_deleted_is_in_the_vocabulary
```

Expected: FAIL on the assertion.

- [ ] **Step 3: Add the value**

`backend/app/services/events.py`, immediately after `"blocks_edited"`:

```python
    # The subtree delete's journal row, one per deleted document (increment 2).
    # `delete_document` journals nothing and that is right for one note; a
    # bulk delete is unrecoverable and, over MCP, the event's `api_key_id` is
    # the only record of who ran it. Carries ids and the prefix, no content.
    "documents_deleted",
```

- [ ] **Step 4: Classify it in the frontend map**

`frontend/src/features/activity/event-taxonomy.ts`, after `document_updated`:

```ts
  // The subtree delete (increment 2). Capture, the same tab its three
  // document siblings land on: it is a write to filed documents.
  documents_deleted: "capture",
```

- [ ] **Step 5: Run both guards**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" \
  .venv/bin/python -m pytest -q tests/test_events.py tests/test_event_taxonomy_map.py
```

Expected: PASS. `test_event_taxonomy_map` passes because the value has no emitter yet *and* is classified; it would also pass unclassified-with-no-emitter, which is why Task 3 must not land first.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/events.py backend/tests/test_events.py frontend/src/features/activity/event-taxonomy.ts
git commit -m "feat(events): admit the documents_deleted type"
```

---

### Task 3: `delete_documents` — the subtree delete service

The only genuinely new backend capability. Mirrors `rename_documents` deliberately: same prefix match, same lock order, one transaction, a count back.

**Files:**
- Modify: `backend/app/services/document_door.py` (add after `rename_documents`, ~line 880; add to `__all__`)
- Test: `backend/tests/test_document_update.py`

**Interfaces:**
- Consumes: `DocumentNothingToChange` (already in this module), `record_event` (already imported), `"documents_deleted"` from Task 2.
- Produces: `async def delete_documents(session, *, project: str, uri_prefix: str) -> int`. Tasks 4 and 5 call it.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5
**Approach:** inline - skip 3: the spec fixed the two-step lock, the prefix match and the per-row journal

Risk is 3 and irreducible: this deletes data, cascades blocks and their vectors, and takes row locks that can deadlock against a concurrent rename.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_document_update.py`, after the rename tests. `_file`, `_uris` and `_event_count` already exist in this module.

```python
@pytest.mark.asyncio
async def test_a_subtree_delete_removes_every_descendant(session):
    for uri in ("notes/a", "notes/a/one.md", "notes/a/two.md", "notes/b.md"):
        await _file(session, "body", uri)
    assert await delete_documents(session, project="p", uri_prefix="notes/a") == 3
    assert await _uris(session, "p") == {"notes/b.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_does_not_over_match_a_wildcard(session):
    """`_` and `%` are LIKE metacharacters; the match must not use LIKE."""
    await _file(session, "body", "notes/a_b/one.md")
    await _file(session, "body", "notes/axb/two.md")
    assert await delete_documents(session, project="p", uri_prefix="notes/a_b") == 1
    assert await _uris(session, "p") == {"notes/axb/two.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_is_scoped_to_its_project(session):
    await _file(session, "body", "notes/a/one.md")
    llm = StubEmbedder()
    await put_document(session, llm, project="q", uri="notes/a/one.md",
                       content="body", source_type="md")
    await session.commit()
    assert await delete_documents(session, project="p", uri_prefix="notes/a") == 1
    assert await _uris(session, "q") == {"notes/a/one.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_journals_one_row_per_document(session):
    _, first = await _file(session, "body", "notes/a/one.md")
    _, second = await _file(session, "body", "notes/a/two.md")
    await delete_documents(session, project="p", uri_prefix="notes/a")
    for doc in (first, second):
        assert await _event_count(session, doc) >= 1
        row = await _latest_event(session, doc)
        assert row["event_type"] == "documents_deleted"
        assert row["payload"]["uri_prefix"] == "notes/a"
        # Write-time minimization: ids and the prefix, never content.
        assert "content" not in row["payload"]


@pytest.mark.asyncio
async def test_an_empty_prefix_is_refused(session):
    """At the SQL an empty prefix degenerates to `left(uri, 1) = '/'` and
    matches nothing, which would report a successful delete of zero rows."""
    await _file(session, "body", "notes/a/one.md")
    with pytest.raises(DocumentNothingToChange):
        await delete_documents(session, project="p", uri_prefix="")
    assert await _uris(session, "p") == {"notes/a/one.md"}
```

Add `delete_documents` to this file's import from `app.services.document_door`.

- [ ] **Step 2: Run them and watch them fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" \
  .venv/bin/python -m pytest -q tests/test_document_update.py -k subtree_delete
```

Expected: FAIL with `ImportError: cannot import name 'delete_documents'`.

- [ ] **Step 3: Implement it**

`backend/app/services/document_door.py`, immediately after `rename_documents`:

```python
async def delete_documents(
    session: AsyncSession,
    *,
    project: str,
    uri_prefix: str,
) -> int:
    """Delete a whole uri subtree in one transaction, journaling each row.

    Shaped after `rename_documents` on purpose: the same prefix match, which
    avoids LIKE because `_` and `%` are metacharacters there and a prefix of
    `notes/a_b` would over-match `notes/axb`, and the same `ORDER BY id FOR
    UPDATE` lock order, so a subtree delete and a concurrent subtree rename
    take the rows in one order and cannot deadlock against each other.

    Unlike the rename this needs no depth ordering: deletes cannot collide
    through `ux_documents_project_uri`, so the order rows leave in is free.
    The lock is still taken in id order for the cross-verb reason above.

    Journals one `documents_deleted` row per deleted document rather than one
    row for "a subtree", which would need an object type no vocabulary has.
    `delete_document` journals nothing and that is right for a single note;
    a bulk delete is unrecoverable, cascades blocks and their vectors, and
    over MCP the event's `api_key_id` is the only record of who ran it.
    """
    if not uri_prefix:
        # `left(uri, 0 + 1) = '/'` matches nothing, so an unrefused empty
        # prefix reports a successful delete of zero rows.
        raise DocumentNothingToChange("uri_prefix must not be empty")

    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, uri, project FROM documents "
            "WHERE project = CAST(:p AS text) "
            "  AND (uri = CAST(:u AS text) "
            "       OR left(uri, length(CAST(:u AS text)) + 1) "
            "          = CAST(:u AS text) || '/') "
            "ORDER BY id FOR UPDATE"
        ),
        {"p": project, "u": uri_prefix},
    )).mappings().all()

    if not rows:
        return 0

    # Journal BEFORE the delete: `record_event` takes the document id as its
    # object id, and writing after the row is gone would journal against an
    # id nothing resolves. The events table holds no foreign key to
    # `documents`, so the rows outlive their subject by design -- that is
    # what makes this an audit trail rather than a cache.
    for row in rows:
        await record_event(
            session,
            event_type="documents_deleted",
            object_type="document",
            object_id=UUID(row["id"]),
            project=row["project"],
            payload={"uri": row["uri"], "uri_prefix": uri_prefix},
        )

    await session.execute(
        text("DELETE FROM documents WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": [row["id"] for row in rows]},
    )
    return len(rows)
```

Add `"delete_documents"` to `__all__`, in alphabetical position (after `"delete_document"`).

- [ ] **Step 4: Run the tests — they should pass**

Same command as Step 2. Expected: 5 passed.

- [ ] **Step 5: Run the whole document suite for regressions**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2" \
  .venv/bin/python -m pytest -q tests/test_document_update.py tests/test_document_door.py tests/test_document_routes.py tests/test_block_verbs.py
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_door.py backend/tests/test_document_update.py
git commit -m "feat(documents): delete a document subtree"
```

---

### Task 4: The REST route, with every backend guard it moves

**The route, its parity row, its content-surfaces entry, the conformance map and the regenerated `docs/two-door-parity.md` land in ONE commit.** Each guard fails the instant the route exists without its entry, so a partial commit leaves the tree red.

POST rather than DELETE: `DELETE`-with-body is poorly supported by clients and proxies, and the reply is a count. The precedent is `POST /memories/delete`, named as the bulk delete in `docs/api-rest-conventions.md`.

**Files:**
- Modify: `backend/app/api/routes/documents.py` (import, request/response models, route)
- Modify: `backend/app/services/content_surfaces.py` (`ROUTES_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/tests/test_door_parity.py` (`PARITY_TABLE`, the `documents.write` surface)
- Modify: `docs/two-door-parity.md` (regenerated, headline counts by hand)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (the EXPECTED map)
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: `delete_documents` from Task 3, `DocumentNothingToChange` (already imported in this route module).
- Produces: `POST /api/v1/documents/delete` taking `{project, uri_prefix}` and answering `{deleted: int}`. Task 7's hook calls it.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5
**Approach:** inline - skip 3: the spec fixed POST-with-count, the route name and the `/memories/delete` precedent

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_document_routes.py`:

```python
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
```

- [ ] **Step 2: Run them and watch them fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" \
  .venv/bin/python -m pytest -q tests/test_document_routes.py -k subtree_delete
```

Expected: FAIL with 404 (route does not exist).

- [ ] **Step 3: Add the models and the route**

`backend/app/api/routes/documents.py`. Add `delete_documents` to the `document_door` import. Then, beside `DocumentRenameRequest`:

```python
class DocumentSubtreeDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=200)
    uri_prefix: str = Field(min_length=1, max_length=500)


class DocumentSubtreeDeleteResponse(BaseModel):
    deleted: int
```

`min_length=1` on `uri_prefix` is what makes the empty-prefix case a 422 before the handler runs; the service refuses it again for callers that do not come through this model.

And the route, beside `rename_documents_route`:

```python
@router.post("/delete", response_model=DocumentSubtreeDeleteResponse)
async def delete_subtree_route(
    body: DocumentSubtreeDeleteRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentSubtreeDeleteResponse:
    """Delete every document under a uri prefix.

    POST rather than DELETE, and 200 rather than 204: `DELETE`-with-body is
    poorly supported by clients and proxies, and the reply is a count. The
    conventions name `POST /memories/delete` as the bulk-delete precedent.
    """
    try:
        deleted = await delete_documents(
            session, project=body.project, uri_prefix=body.uri_prefix,
        )
    except DocumentNothingToChange as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
        ) from exc
    await session.commit()
    return DocumentSubtreeDeleteResponse(deleted=deleted)
```

- [ ] **Step 4: Classify the route in content surfaces**

`backend/app/services/content_surfaces.py`, in `ROUTES_WITHOUT_MEMORY_CONTENT`, beside the other document writes:

```python
    # The subtree delete (increment 2). Same classification and reason as the
    # write door above -- it removes documents and answers a count, and no
    # `memories` row crosses it.
    "POST /api/v1/documents/delete",
```

- [ ] **Step 5: Add it to the parity table and regenerate the doc**

`backend/tests/test_door_parity.py`, in the `documents.write` surface's `rest` tuple:

```python
            ("POST", f"{V1}/documents/delete"),
```

Leave `mcp=("document_put", "document_delete")` alone for now — Task 5 adds the tool. Between Task 4 and Task 5 the surface is momentarily asymmetric; that is why the parity `note` must not yet claim the tool exists.

Then regenerate `docs/two-door-parity.md` by the mechanism `test_door_parity` enforces (the test names it when it fails), and **hand-edit the headline counts sentence**, which sits outside the generated block and no regeneration touches.

- [ ] **Step 6: Add the route to the conformance map**

`backend/tests/test_api/test_rest_conformance.py`, in the EXPECTED map: `POST /api/v1/documents/delete` returning 200.

- [ ] **Step 7: Run the route tests and the full guards leg**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" \
  .venv/bin/python -m pytest -q tests/test_document_routes.py tests/test_content_surface_scoping.py \
    tests/test_door_parity.py tests/test_prompt_agent_instructions.py \
    tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py \
    tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: all pass. A failure here names which enumeration guard was missed.

- [ ] **Step 8: Commit — everything together**

```bash
git add backend/app/api/routes/documents.py backend/app/services/content_surfaces.py \
        backend/tests/test_door_parity.py backend/tests/test_api/test_rest_conformance.py \
        backend/tests/test_document_routes.py docs/two-door-parity.md
git commit -m "feat(documents): add the subtree delete route"
```

---

### Task 5: The MCP tool, at `admin` scope

A **separate tool**, not a mode on `document_delete`. Scopes are per tool, so a mode would inherit `capture` and let any capture key erase a project's corpus. This is the second tool ever held at `admin`, on the same principle as `code_reindex`: repository-scale control, not memory writing.

Settle a deferred minor while here: `document_delete` raises `DocumentTargetUnresolved` as a tool error where `document_update` answers a structured envelope. Both become envelopes.

**Files:**
- Modify: `backend/app/api/mcp/server.py` (new tool; `document_delete`'s refusal shape)
- Modify: `backend/app/api/mcp/scopes.py:95-97` (`ADMIN_TOOLS`)
- Modify: `backend/app/services/content_surfaces.py` (`MCP_TOOLS_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/app/services/prompt.py:693` (the roster)
- Modify: `backend/tests/test_door_parity.py` (the `documents.write` mcp tuple), `docs/two-door-parity.md`
- Modify: `CLAUDE.md` (39 → 40 catalogue, the `admin` sentence, the writer count)
- Test: `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: `delete_documents` from Task 3.
- Produces: MCP tool `document_delete_subtree(project, uri_prefix) -> {"status": "ok", "project", "deleted"}`, held at `admin`.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5
**Approach:** inline - skip 3: the owner chose the separate-tool/admin-scope shape over a capture-scoped mode

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_mcp.py`. **Note the ordering hazard recorded in `backend/tests/conftest.py`:** MCP tool tests commit, so do every write before the first refusal, and use fixture names unique to this module (`mcp-subtree`, `mcpgone/*`) so they cannot collide with `test_document_update.py`'s rows.

```python
def test_document_delete_subtree_is_admin_scoped():
    """A capture key can delete one note it can name. Erasing a subtree is
    repository-scale control, so it sits with code_reindex."""
    from app.api.mcp.scopes import ADMIN_TOOLS, CAPTURE_TOOLS, READ_TOOLS

    assert "document_delete_subtree" in ADMIN_TOOLS
    assert "document_delete_subtree" not in CAPTURE_TOOLS
    assert "document_delete_subtree" not in READ_TOOLS
    # The single-document verb keeps the scope it has.
    assert "document_delete" in CAPTURE_TOOLS


@pytest.mark.asyncio
async def test_document_delete_subtree_removes_the_tree(session, monkeypatch):
    import json
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-subtree|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    embedder_registry.forget("test-fp-mcp-subtree|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))

    # Every write before the first refusal -- see the fixture note.
    await put_document(session, llm, project="mcp-subtree",
                       uri="mcpgone/a.md", content="# A\n")
    await put_document(session, llm, project="mcp-subtree",
                       uri="mcpgone/deep/b.md", content="# B\n")
    await put_document(session, llm, project="mcp-subtree",
                       uri="mcpkept/c.md", content="# C\n")
    await session.commit()

    result = json.loads(await mcp_server.document_delete_subtree(
        project="mcp-subtree", uri_prefix="mcpgone",
    ))
    assert result["status"] == "ok"
    assert result["deleted"] == 2

    embedder_registry.forget("test-fp-mcp-subtree|3")


@pytest.mark.asyncio
async def test_document_delete_subtree_refuses_an_empty_prefix(session, monkeypatch):
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    refused = json.loads(await mcp_server.document_delete_subtree(
        project="mcp-subtree", uri_prefix="",
    ))
    assert refused["status"] == "no_change"


@pytest.mark.asyncio
async def test_document_delete_answers_an_envelope_for_a_missing_target(
    session, monkeypatch,
):
    """Its sibling document_update answers an envelope; these two disagreed."""
    import json
    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())

    missing = json.loads(await mcp_server.document_delete(
        document_id="00000000-0000-0000-0000-000000000000",
    ))
    assert missing["status"] == "unresolved"
```

- [ ] **Step 2: Run them and watch them fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_4" \
  .venv/bin/python -m pytest -q tests/test_mcp.py -k delete_subtree
```

Expected: FAIL — the tool does not exist.

- [ ] **Step 3: Add the tool**

`backend/app/api/mcp/server.py`, after `document_delete`:

```python
@mcp.tool(
    description=(
        "Delete every document under a uri prefix, in one transaction. "
        "Names a project and a uri_prefix; answers the count removed. This "
        "is repository-scale control and requires an admin-scoped key -- a "
        "capture key can delete one document it names, not a whole subtree."
    )
)
async def document_delete_subtree(
    project: str | None = None,
    uri_prefix: str | None = None,
) -> str:
    """
    Args:
        project: Scope. Required.
        uri_prefix: The subtree to remove. Required; an empty prefix refuses.
    """
    from app.services.document_door import (
        DocumentNothingToChange, delete_documents,
    )

    if not project or not uri_prefix:
        return json.dumps({
            "status": "invalid_mode",
            "reason": "name both project and uri_prefix",
        })

    async with async_session_factory() as session:
        try:
            deleted = await delete_documents(
                session, project=project, uri_prefix=uri_prefix,
            )
            await session.commit()
        except DocumentNothingToChange as exc:
            # The REST twin answers 422 for the same shape.
            await session.rollback()
            return json.dumps({"status": "no_change", "reason": str(exc)})
        except Exception:
            await session.rollback()
            raise

    return json.dumps({
        "status": "ok", "project": project, "deleted": deleted,
    })
```

- [ ] **Step 4: Make `document_delete`'s refusal an envelope**

In `document_delete`, replace the raise-through with the envelope its sibling uses:

```python
    async with async_session_factory() as session:
        try:
            target = await resolve_document_target(
                session, document_id=document_id, project=project, uri=uri,
            )
        except DocumentTargetUnresolved as exc:
            # An envelope, matching document_update: two sibling document
            # writers must not disagree on the same exception.
            return json.dumps({"status": "unresolved", "reason": str(exc)})
        try:
            if not await delete_document(session, document_id=target):
                return json.dumps({
                    "status": "unresolved", "reason": "document not found",
                })
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps({"document_id": target, "deleted": True})
```

Keep the existing success shape unchanged — callers depend on `{"document_id", "deleted"}`.

- [ ] **Step 5: Scope, classify, roster**

`backend/app/api/mcp/scopes.py`:

```python
ADMIN_TOOLS: frozenset[str] = frozenset({
    "code_reindex",
    # Erasing a whole uri subtree is repository-scale control, not memory
    # writing: a capture key deletes one document it can name.
    "document_delete_subtree",
})
```

`backend/app/services/content_surfaces.py`, in `MCP_TOOLS_WITHOUT_MEMORY_CONTENT`, beside `mcp:document_delete`:

```python
    # The subtree delete's MCP half. Same reason as its REST twin: it removes
    # documents and answers a count, and no `memories` row crosses it.
    "mcp:document_delete_subtree",
```

`backend/app/services/prompt.py`, after the `document_update` roster line:

```python
        "- **document_delete_subtree** — delete every document under a uri "
        "prefix, in one transaction; needs an admin-scoped key.\n"
```

- [ ] **Step 6: Parity, doc regen, CLAUDE.md counts**

Add `"document_delete_subtree"` to the `documents.write` surface's `mcp` tuple in `test_door_parity.py`, regenerate `docs/two-door-parity.md`, and hand-edit its headline counts.

In `CLAUDE.md`'s MCP section: the catalogue moves **39 → 40**, the writer count **13 → 14**, and the `admin` sentence stops saying the scope "reaches exactly one tool" — it now reaches two, and the sentence must name both and keep its point that a `capture` key reaches neither.

- [ ] **Step 7: Regenerate the SDKs and run the guards leg**

```
cd sdks && make generate && cd .. && git status --porcelain
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_4" \
  .venv/bin/python -m pytest -q tests/test_mcp.py tests/test_content_surface_scoping.py \
    tests/test_door_parity.py tests/test_prompt_agent_instructions.py \
    tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py \
    tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: all pass; `make generate` reports no drift (the three-verb SDK does not serve this route).

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/mcp/server.py backend/app/api/mcp/scopes.py \
        backend/app/services/content_surfaces.py backend/app/services/prompt.py \
        backend/tests/test_door_parity.py backend/tests/test_mcp.py \
        docs/two-door-parity.md CLAUDE.md
git commit -m "feat(mcp): add the admin-scoped subtree delete"
```

---

### Task 6: Hold the selection by id, not as a snapshot

**This is the ordering constraint.** `ProjectWorkspace` stores the selected `DocumentListItem` *object*. Every mutation Tasks 7–15 add invalidates it: after a move the breadcrumbs render the old uri and the reveal effect never expands the new folder; after a folder delete the reader 404s and the detail panel fires reads against a dead id.

A pure refactor with no behaviour change, landed before anything can depend on the stale shape.

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx:107`, `:171-191`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: `selectedId: string | null` state inside `ProjectWorkspace`, with `selected` derived as `items.find((d) => d.id === selectedId) ?? null`. Tasks 9, 10 and 15 rely on the derived value tracking `items`.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 2 = 3
**Approach:** inline - skip 3: the spec fixed this as a precondition, not an option

- [ ] **Step 1: Write the failing test**

In `frontend/src/features/documents/__tests__/project-workspace.test.tsx`:

```tsx
it("follows the selected document when its uri changes under it", async () => {
  // The selection used to be a snapshot object, so a move left the
  // breadcrumbs rendering the path the document no longer had.
  const first = [
    { id: "d1", title: "A", uri: "old/a.md", source_type: "md",
      project: "p", block_count: 1 },
  ]
  const moved = [
    { id: "d1", title: "A", uri: "new/a.md", source_type: "md",
      project: "p", block_count: 1 },
  ]

  const { rerender } = renderWorkspace(first)
  await userEvent.click(await screen.findByText("a.md"))
  expect(screen.getByText(/old/)).toBeInTheDocument()

  rerender(renderWorkspace.withItems(moved))

  expect(await screen.findByText(/new/)).toBeInTheDocument()
  expect(screen.queryByText(/old/)).not.toBeInTheDocument()
})
```

Match the file's existing render helper rather than inventing `renderWorkspace`; read the top of the file and reuse what is there.

- [ ] **Step 2: Run it and watch it fail**

```
cd frontend && npm test -- project-workspace
```

Expected: FAIL — the breadcrumb still shows `old`.

- [ ] **Step 3: Replace the state with an id**

In `project-workspace.tsx`:

```tsx
  // The id, never the row. A stored `DocumentListItem` is a snapshot: after
  // a rename, move or delete it describes a document that no longer exists
  // in that shape, and the breadcrumbs, the reveal effect and the reader all
  // read it. Deriving from `items` makes the selection track the list.
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = useMemo(
    () => items.find((d) => d.id === selectedId) ?? null,
    [items, selectedId],
  )
```

- [ ] **Step 4: Update the writer**

```tsx
  const handleSelectDocument = useCallback((doc: DocumentListItem) => {
    setSelectedId(doc.id)
    setFocusBlockId(null)
    setMode("read")
  }, [])
```

The reveal effect at `:171-180` already keys on `selected.id` and needs no change; confirm it still reads `selected`, which is now derived.

- [ ] **Step 5: Run the tests**

```
cd frontend && npm test -- project-workspace document-tree && npm run typecheck
```

Expected: PASS, including every pre-existing test in the file — this is a refactor and none of them should need editing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "refactor(documents): hold the selection by id"
```

---

### Task 7: The document mutation hooks

All five call verbs that already ship and are deployed. `useDocumentDelete` already exists at `use-documents-api.ts:137-147`; follow its invalidation pattern exactly.

**Files:**
- Modify: `frontend/src/hooks/api/use-documents-api.ts`
- Test: `frontend/src/hooks/api/__tests__/use-documents-mutations.test.tsx` (create)

**Interfaces:**
- Consumes: `POST /api/v1/documents/delete` from Task 4.
- Produces: `useDocumentCreate()`, `useDocumentMetadataUpdate()`, `useDocumentSubtreeRename()`, `useDocumentSubtreeDelete()`. Tasks 10 and 15 call them.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: `useDocumentDelete` in the same file is the established pattern

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/api/__tests__/use-documents-mutations.test.tsx`, following `use-documents-all.test.tsx`'s harness:

```tsx
it("creates a note at the uri it was given", async () => {
  const calls: Array<{ path: string; body: unknown }> = []
  mockApiFetch((path, init) => {
    calls.push({ path, body: init?.body ? JSON.parse(String(init.body)) : null })
    return { document_id: "d1", outcome: "created" }
  })

  const { result } = renderHook(() => useDocumentCreate(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      project: "notes", uri: "untitled.md", title: "Untitled",
    })
  })

  expect(calls[0].path).toBe("/documents")
  expect(calls[0].body).toMatchObject({
    project: "notes", uri: "untitled.md", content: "# Untitled\n",
  })
})

it("renames a subtree through the rename route", async () => {
  const calls: string[] = []
  mockApiFetch((path) => { calls.push(path); return { renamed: 2 } })

  const { result } = renderHook(() => useDocumentSubtreeRename(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      project: "notes", uri_prefix: "a", new_uri_prefix: "b",
    })
  })

  expect(calls[0]).toBe("/documents/rename")
})

it("deletes a subtree through the bulk route", async () => {
  const calls: string[] = []
  mockApiFetch((path) => { calls.push(path); return { deleted: 3 } })

  const { result } = renderHook(() => useDocumentSubtreeDelete(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({ project: "notes", uri_prefix: "gone" })
  })

  expect(calls[0]).toBe("/documents/delete")
})
```

- [ ] **Step 2: Run it and watch it fail**

```
cd frontend && npm test -- use-documents-mutations
```

Expected: FAIL — the hooks do not exist.

- [ ] **Step 3: Add the hooks**

`frontend/src/hooks/api/use-documents-api.ts`:

```ts
/** Both list keys, the pair `useDocumentDelete` already invalidates. Every
 *  mutation below changes what the tree renders, so they all invalidate the
 *  same two. */
function invalidateDocumentLists(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["documentsAll"] })
  void qc.invalidateQueries({ queryKey: ["documents"] })
}

export interface DocumentCreateParams {
  project: string
  uri: string
  title?: string
}

export function useDocumentCreate() {
  const qc = useQueryClient()
  return useMutation<{ document_id: string }, Error, DocumentCreateParams>({
    // Seeded content, never empty: `DocumentPutRequest.content` is
    // `min_length=1`, so an empty body is a 422. And note `document_put` is
    // an UPSERT on `(project, uri)` -- the caller mints a uri no document
    // holds, or this silently returns the existing document's id.
    mutationFn: ({ project, uri, title }) =>
      apiFetch(`/documents`, {
        method: "POST",
        body: JSON.stringify({
          project,
          uri,
          content: `# ${title ?? "Untitled"}\n`,
          title: title ?? "Untitled",
        }),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export interface DocumentMetadataParams {
  documentId: string
  title?: string
  uri?: string
  pinned?: boolean
  tags?: string[]
}

export function useDocumentMetadataUpdate() {
  const qc = useQueryClient()
  return useMutation<{ document_id: string }, Error, DocumentMetadataParams>({
    mutationFn: ({ documentId, ...fields }) =>
      apiFetch(`/documents/${documentId}`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export interface SubtreeRenameParams {
  project: string
  uri_prefix: string
  new_uri_prefix: string
}

export function useDocumentSubtreeRename() {
  const qc = useQueryClient()
  return useMutation<{ renamed: number }, Error, SubtreeRenameParams>({
    mutationFn: (body) =>
      apiFetch(`/documents/rename`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}

export interface SubtreeDeleteParams {
  project: string
  uri_prefix: string
}

export function useDocumentSubtreeDelete() {
  const qc = useQueryClient()
  return useMutation<{ deleted: number }, Error, SubtreeDeleteParams>({
    mutationFn: (body) =>
      apiFetch(`/documents/delete`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateDocumentLists(qc),
  })
}
```

Export all four from `frontend/src/hooks/api/index.ts` alongside the existing document hooks.

- [ ] **Step 4: Run the tests and the query-key guard**

```
cd frontend && npm test -- use-documents-mutations query-keys && npm run typecheck
```

Expected: PASS. The query-key guard scans `queryKey:` literals in queries; these are mutations and add none, so it should stay green without a `QUERY_KEY_SCOPE` entry.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-documents-api.ts frontend/src/hooks/api/index.ts \
        frontend/src/hooks/api/__tests__/use-documents-mutations.test.tsx
git commit -m "feat(documents): add the note mutation hooks"
```

---

### Task 8: Tree row actions and the empty-space affordance

`DocumentTree` already declares a `nodeActions?: (node: UriTreeNode) => ReactNode` slot (`document-tree.tsx:122`) whose comment says it exists so "the editor extends this component rather than rewriting it". Use it rather than changing the tree's structure.

**The empty state must also change.** `document-tree.tsx:163-172` returns the `EmptyState` *before* any row renders, so an empty notes space — which is exactly the state `/notes` opens in — has no create affordance at all. That is the first thing a user sees.

**Files:**
- Create: `frontend/src/features/documents/components/note-tree-actions.tsx`
- Modify: `frontend/src/features/documents/components/document-tree.tsx:163-172`
- Test: `frontend/src/features/documents/__tests__/note-tree-actions.test.tsx`

**Interfaces:**
- Consumes: `UriTreeNode` from `../uri-tree`; `pinned_at` from Task 1.
- Produces: `NoteTreeActions` (props below) and `DocumentTree`'s new `emptyAction?: ReactNode` prop. Task 10 supplies both.

```tsx
export interface NoteTreeActionsProps {
  node: UriTreeNode
  onNewNote: (folderPath: string) => void
  onRename: (node: UriTreeNode) => void
  onTogglePin: (node: UriTreeNode) => void
  onDelete: (node: UriTreeNode) => void
}
```

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 2: `nodeActions` is the slot the tree already declares for exactly this

- [ ] **Step 1: Write the failing tests**

```tsx
it("offers folder actions on a folder and document actions on a leaf", async () => {
  const folder: UriTreeNode = {
    name: "a", path: "notes/a", document: null, children: [],
  }
  const leaf: UriTreeNode = {
    name: "b.md", path: "notes/a/b.md",
    document: { id: "d1", title: "B", uri: "notes/a/b.md",
                source_type: "md", project: "p", block_count: 1 },
    children: [],
  }
  const noop = () => {}

  const { rerender } = render(
    <NoteTreeActions node={folder} onNewNote={noop} onRename={noop}
                     onTogglePin={noop} onDelete={noop} />,
  )
  await userEvent.click(screen.getByRole("button", { name: /actions/i }))
  expect(screen.getByText(/new note/i)).toBeInTheDocument()
  // A folder has no pin: `pinned_at` is a document column.
  expect(screen.queryByText(/pin/i)).not.toBeInTheDocument()

  rerender(
    <NoteTreeActions node={leaf} onNewNote={noop} onRename={noop}
                     onTogglePin={noop} onDelete={noop} />,
  )
  await userEvent.click(screen.getByRole("button", { name: /actions/i }))
  expect(screen.getByText(/pin/i)).toBeInTheDocument()
})

it("offers no folder actions on the orphan bucket", async () => {
  // `(no path)` is a synthesised node with no uri; a folder op on it would
  // send `uri_prefix="(no path)"` and match nothing.
  const orphans: UriTreeNode = {
    name: NO_PATH, path: NO_PATH, document: null, children: [],
  }
  render(<NoteTreeActions node={orphans} onNewNote={() => {}} onRename={() => {}}
                          onTogglePin={() => {}} onDelete={() => {}} />)
  expect(screen.queryByRole("button", { name: /actions/i })).toBeNull()
})

it("renders an action in the empty state so an empty space can be filled", () => {
  render(
    <DocumentTree items={[]} selectedId={null} onSelect={() => {}}
                  truncated={false}
                  emptyAction={<button>New note</button>} />,
  )
  expect(screen.getByText("New note")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- note-tree-actions
```

Expected: FAIL — the component does not exist.

- [ ] **Step 3: Build `NoteTreeActions`**

Use darkraise-ui's `menu` component (`ls frontend/node_modules/darkraise-ui/dist/components/ | grep menu`, then read its `.d.ts` for props). Do not hand-roll a dropdown. Render nothing when `node.path === NO_PATH`. A node with `document === null` is a folder: offer New note, Rename, Delete. A node with a document: offer Rename, Pin/Unpin (label from `node.document.pinned_at`), Delete.

Stop propagation on the trigger's click so opening the menu does not also select the row.

- [ ] **Step 4: Give the tree an empty-state action**

`document-tree.tsx` — add the prop and render it inside the existing `EmptyState`:

```tsx
  /** Rendered inside the empty state. Without it an empty space has no
   *  affordance at all: this branch returns before any row, and `nodeActions`
   *  only ever hangs off a row. */
  emptyAction?: ReactNode
```

```tsx
  if (items.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No documents filed in this project"
        description="A document appears here the moment it is filed — over REST or over MCP."
      >
        {emptyAction}
      </EmptyState>
    )
  }
```

Check `EmptyState`'s own props first; if it takes no children, pass the node through whatever slot it does declare rather than changing that component.

- [ ] **Step 5: Run the tests**

```
cd frontend && npm test -- note-tree-actions document-tree && npm run typecheck
```

Expected: PASS, with the pre-existing `document-tree` tests untouched.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/documents/components/note-tree-actions.tsx \
        frontend/src/features/documents/components/document-tree.tsx \
        frontend/src/features/documents/__tests__/note-tree-actions.test.tsx
git commit -m "feat(documents): add tree row actions"
```

---

### Task 9: The `treeManagement` capability prop

Named for what it gates. `/projects/$project` is already editable — it has the block editor and delete — so `editable` would conflate two things.

Four branch points beyond the menu, all rendered unconditionally today. Getting these wrong is what would make `/notes` show a permanently-empty Progress tab and run a ledger scan for nothing on every mount.

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: Task 6's `selectedId`/derived `selected`.
- Produces: `ProjectWorkspace`'s `treeManagement?: boolean` prop. Tasks 10 and 11 set it.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: the spec named the four branch points and ruled the Progress tab off for /notes

- [ ] **Step 1: Write the failing tests**

```tsx
it("renders the workspace unchanged when tree management is off", () => {
  renderWorkspace(items)   // no treeManagement prop
  expect(screen.getByRole("tab", { name: /progress/i })).toBeInTheDocument()
})

it("hides the tab strip and the progress scan when tree management is on", () => {
  const scan = vi.fn()
  renderWorkspace(items, { treeManagement: true, onProgressScan: scan })
  // A progress ledger is a project artifact; the personal space has no
  // sessions, so the tab would be permanently empty and the scan wasted.
  expect(screen.queryByRole("tab", { name: /progress/i })).toBeNull()
  expect(scan).not.toHaveBeenCalled()
})

it("shows a notes empty state rather than the progress-ledger one", () => {
  renderWorkspace([], { treeManagement: true })
  expect(screen.queryByText(/planning\/progress\.md/)).toBeNull()
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- project-workspace
```

Expected: FAIL on the second and third.

- [ ] **Step 3: Add the prop and gate the four branch points**

```tsx
export function ProjectWorkspace({
  project,
  tab,
  onTabChange,
  treeManagement = false,
}: {
  project: string
  tab: WorkspaceTab
  onTabChange: (tab: WorkspaceTab) => void
  /** Tree management: create, rename, move, pin, delete. Off is the corpus
   *  browser at /projects/$project, which is unchanged. Named for what it
   *  gates rather than `editable`, because that surface is already editable
   *  -- it has the block editor and delete. */
  treeManagement?: boolean
}) {
```

Gate, in order:
1. The Artifacts/Progress tab strip and the `CheckpointsTab` — not rendered when `treeManagement`.
2. `useProgressCorpus(items)` — pass an empty array when `treeManagement`, so no ledger contents are fetched. Read the hook first; if it cannot be made inert by its argument, guard the call site instead.
3. The `planning/progress.md` empty state (`:400-419`) — replaced by a notes-appropriate one.
4. The tree's empty state action slot — supplied in Task 10; leave the prop threading in place here.

- [ ] **Step 4: Run the tests**

```
cd frontend && npm test -- project-workspace && npm run typecheck
```

Expected: PASS, including every existing test, since the default is off.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(documents): gate tree management behind a prop"
```

---

### Task 10: Wire the actions into the workspace

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: Task 7's four hooks, Task 8's `NoteTreeActions` and `emptyAction`, Task 9's `treeManagement`.
- Produces: nothing further.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: every verb and component this wires was fixed by Tasks 7-9

- [ ] **Step 1: Write the failing tests**

```tsx
it("mints a uri no document holds when creating a note", async () => {
  const created: Array<{ uri: string }> = []
  renderWorkspace(
    [{ id: "d1", title: "Untitled", uri: "untitled.md", source_type: "md",
       project: "notes", block_count: 1 }],
    { treeManagement: true, onCreate: (p) => created.push(p) },
  )
  await userEvent.click(screen.getByRole("button", { name: /new note/i }))
  // `document_put` upserts on (project, uri): reusing `untitled.md` would
  // return the existing document's id and create nothing.
  expect(created[0].uri).toBe("untitled-2.md")
})

it("renames a note by its uri, not its title", async () => {
  const patched: Array<Record<string, unknown>> = []
  renderWorkspace(items, { treeManagement: true, onPatch: (p) => patched.push(p) })
  await userEvent.click(screen.getByRole("button", { name: /actions/i }))
  await userEvent.click(screen.getByText(/rename/i))
  await userEvent.clear(screen.getByRole("textbox"))
  await userEvent.type(screen.getByRole("textbox"), "renamed.md{Enter}")
  // The tree renders the uri's last segment; a title PATCH changes nothing
  // the user can see.
  expect(patched[0]).toMatchObject({ uri: expect.stringContaining("renamed.md") })
})

it("deletes a folder through the subtree route", async () => {
  const deleted: Array<{ uri_prefix: string }> = []
  renderWorkspace(items, { treeManagement: true, onSubtreeDelete: (p) => deleted.push(p) })
  await userEvent.click(screen.getAllByRole("button", { name: /actions/i })[0])
  await userEvent.click(screen.getByText(/delete/i))
  await userEvent.click(screen.getByRole("button", { name: /confirm/i }))
  expect(deleted[0].uri_prefix).toBe("notes/a")
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- project-workspace
```

- [ ] **Step 3: Wire it**

Pass `nodeActions={(node) => <NoteTreeActions … />}` and `emptyAction={…}` to `DocumentTree` when `treeManagement`. Add a header create button. Implement uri minting against the loaded `items`:

```tsx
/** `document_put` upserts on `(project, uri)`, so a create at a uri that
 *  already exists returns that document's id and files nothing. Mint a free
 *  one against the tree we already hold. */
function freeUri(items: DocumentListItem[], folder: string, base = "untitled") {
  const taken = new Set(items.map((d) => d.uri).filter(Boolean) as string[])
  const at = (n: number) =>
    `${folder ? `${folder}/` : ""}${base}${n === 1 ? "" : `-${n}`}.md`
  let n = 1
  while (taken.has(at(n))) n += 1
  return at(n)
}
```

Rename PATCHes `uri` (rebuilding the parent path and replacing the last segment) for a document, and calls the subtree rename for a folder. Delete confirms first; a folder delete goes to `useDocumentSubtreeDelete`, a document delete to the existing `useDocumentDelete`. After a delete that removed the selection, clear `selectedId`.

- [ ] **Step 4: Run the tests**

```
cd frontend && npm test -- project-workspace note-tree-actions && npm run typecheck
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(documents): wire the note tree actions"
```

---

### Task 11: The `/notes` route

**Files:**
- Create: `frontend/src/routes/_authenticated/notes.tsx`
- Modify: `frontend/src/routes/_authenticated.tsx:62-70` (nav), `:151` (`FULL_HEIGHT_ROUTES`)
- Modify: `frontend/tests/demo-makes-no-api-calls.spec.ts:19-32` (`DEMO_ROUTES`)
- Test: `frontend/src/routes/_authenticated/__tests__/notes.test.tsx`

**Interfaces:**
- Consumes: `ProjectWorkspace` with `treeManagement` from Task 9.
- Produces: the `/notes` route.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec fixed resolving the project from the catalogue over hardcoding `notes`

- [ ] **Step 1: Write the failing test**

```tsx
it("resolves its project from the catalogue rather than a hardcoded name", async () => {
  mockProjects([
    { name: "darkmem", kind: "project", document_count: 475 },
    { name: "my-notes", kind: "personal", document_count: 0 },
  ])
  renderRoute("/notes")
  // The singleton index guarantees at most one personal row; the route must
  // follow `kind`, not the seeded name.
  expect(await screen.findByTestId("workspace-project")).toHaveTextContent("my-notes")
})

it("is registered as a full-height route", () => {
  // Without this the resizable split falls back to the 60vh floor.
  expect(FULL_HEIGHT_ROUTES).toContain("/notes")
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- notes
```

- [ ] **Step 3: Create the route**

```tsx
import { createFileRoute } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/notes")({
  component: NotesPage,
})

function NotesPage() {
  const projects = useProjects()
  // Resolved from the catalogue, not hardcoded: `ux_projects_one_personal`
  // guarantees at most one row of this kind, and following `kind` keeps the
  // route correct if the seeded name ever changes.
  const personal = projects.data?.find((p) => p.kind === "personal")

  if (!personal) return null

  return (
    <div className="flex flex-col lg:h-full">
      <PageChrome
        icon={NotebookPen}
        title="Notes"
        description="Your personal workspace. Nothing here is a project artifact."
      />
      <ProjectWorkspace
        key={personal.name}
        project={personal.name}
        tab="artifacts"
        onTabChange={() => {}}
        treeManagement
      />
    </div>
  )
}
```

Match `projects_.$project.tsx:26-42` for the surrounding layout classes; read it rather than guessing.

- [ ] **Step 4: Register nav, full-height and demo**

`_authenticated.tsx`, in the `Projects` group:

```tsx
      { label: "Notes", href: "/notes", icon: NotebookPen },
```

```tsx
const FULL_HEIGHT_ROUTES = ["/chat", "/projects/", "/notes"] as const
```

Add `/notes` to `DEMO_ROUTES` in `frontend/tests/demo-makes-no-api-calls.spec.ts`.

- [ ] **Step 5: Run the tests, typecheck and build**

```
cd frontend && npm test && npm run typecheck && npm run build
```

Expected: all pass. `routeTree.gen.ts` regenerates itself — never hand-edit it.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/_authenticated/notes.tsx frontend/src/routes/_authenticated.tsx \
        frontend/src/routeTree.gen.ts frontend/tests/demo-makes-no-api-calls.spec.ts \
        frontend/src/routes/_authenticated/__tests__/notes.test.tsx
git commit -m "feat(notes): add the notes workspace route"
```

---

### Task 12: Give `/documents` a project picker

The route pins `project="default"`, which holds zero documents, so the page renders empty. The epic spec's §14 reversal — `/documents` stops being the personal surface and becomes the corpus browser — was never applied here.

**Files:**
- Modify: `frontend/src/routes/_authenticated/documents.tsx`
- Test: `frontend/src/features/documents/__tests__/documents.real.test.tsx`

**Interfaces:**
- Consumes: `useProjects()`; `DocumentsView`'s existing `project` prop.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: the owner chose the picker over a one-line repoint

- [ ] **Step 1: Write the failing test**

```tsx
it("defaults to a project that actually holds documents", async () => {
  mockProjects([
    { name: "empty", kind: "project", document_count: 0 },
    { name: "darkmem", kind: "project", document_count: 475 },
    { name: "notes", kind: "personal", document_count: 3 },
  ])
  renderRoute("/documents")
  // `useProjects` orders busiest-first by a different measure, so the
  // default needs its own document_count filter.
  expect(await screen.findByRole("combobox")).toHaveTextContent("darkmem")
})

it("keeps the personal space out of the picker", async () => {
  mockProjects([
    { name: "darkmem", kind: "project", document_count: 475 },
    { name: "notes", kind: "personal", document_count: 3 },
  ])
  renderRoute("/documents")
  await userEvent.click(await screen.findByRole("combobox"))
  expect(screen.queryByText("notes")).toBeNull()
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- documents.real
```

- [ ] **Step 3: Add the picker**

Use darkraise-ui's `select` (read its `.d.ts` first). Filter `kind !== "personal"`, default to the first entry with `document_count > 0`, and hold the choice in route state. Replace the hardcoded prop and delete the stale comment calling this "the personal one".

If `ProjectSummary` carries no document count, use whatever count field it does serve and say so in a comment; do not add a backend field for this.

- [ ] **Step 4: Run the tests**

```
cd frontend && npm test -- documents && npm run typecheck
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/_authenticated/documents.tsx \
        frontend/src/features/documents/__tests__/documents.real.test.tsx
git commit -m "feat(documents): pick the project on the corpus browser"
```

---

### Task 13: `moveTarget` — the drop resolution

A pure function, so the interesting logic is testable without a DOM drag.

**Files:**
- Create: `frontend/src/features/documents/move-target.ts`
- Test: `frontend/src/features/documents/__tests__/move-target.test.ts`

**Interfaces:**
- Consumes: `UriTreeNode` from `./uri-tree`.
- Produces:

```ts
export type MoveTarget =
  | { kind: "document"; documentId: string; uri: string }
  | { kind: "subtree"; uriPrefix: string; newUriPrefix: string }

export function moveTarget(
  dragged: UriTreeNode,
  dropTarget: UriTreeNode | null,   // null means the tree root
): MoveTarget | null
```

Task 15 dispatches on it.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 4: one new file, no consumers yet, trivially reversible

- [ ] **Step 1: Write the failing tests**

```ts
const folder = (path: string): UriTreeNode =>
  ({ name: path.split("/").pop()!, path, document: null, children: [] })

const doc = (path: string, id = "d1"): UriTreeNode => ({
  name: path.split("/").pop()!,
  path,
  document: { id, title: null, uri: path, source_type: "md",
              project: "p", block_count: 1 },
  children: [],
})

it("moves a document into a folder", () => {
  expect(moveTarget(doc("a/one.md"), folder("b"))).toEqual({
    kind: "document", documentId: "d1", uri: "b/one.md",
  })
})

it("moves a document to the root", () => {
  expect(moveTarget(doc("a/one.md"), null)).toEqual({
    kind: "document", documentId: "d1", uri: "one.md",
  })
})

it("moves a folder as a subtree rename", () => {
  expect(moveTarget(folder("a/inner"), folder("b"))).toEqual({
    kind: "subtree", uriPrefix: "a/inner", newUriPrefix: "b/inner",
  })
})

it("refuses to drop a folder into its own descendant", () => {
  expect(moveTarget(folder("a"), folder("a/deep"))).toBeNull()
})

it("refuses a no-op drop into the folder it already sits in", () => {
  expect(moveTarget(doc("a/one.md"), folder("a"))).toBeNull()
})

it("refuses to drop a node onto itself", () => {
  expect(moveTarget(folder("a"), folder("a"))).toBeNull()
})

it("refuses anything involving the orphan bucket", () => {
  expect(moveTarget(doc("a/one.md"), folder(NO_PATH))).toBeNull()
  expect(moveTarget(folder(NO_PATH), folder("a"))).toBeNull()
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- move-target
```

- [ ] **Step 3: Implement it**

```ts
import { NO_PATH, type UriTreeNode } from "./uri-tree"

export type MoveTarget =
  | { kind: "document"; documentId: string; uri: string }
  | { kind: "subtree"; uriPrefix: string; newUriPrefix: string }

/** Where a drop lands, or `null` when the drop is refused.
 *
 *  Refused rather than clamped, because every refusal here is a case the
 *  backend would otherwise have to disambiguate: a folder into its own
 *  descendant is the rename whose ordering `rename_documents` had to be
 *  taught, and the `(no path)` bucket is a synthesised node with no uri at
 *  all, so a subtree verb against it matches nothing. */
export function moveTarget(
  dragged: UriTreeNode,
  dropTarget: UriTreeNode | null,
): MoveTarget | null {
  const targetPath = dropTarget?.path ?? ""
  if (dragged.path === NO_PATH || targetPath === NO_PATH) return null
  if (dropTarget && dropTarget.path === dragged.path) return null
  // Into its own subtree: the `/` guard stops `a` matching `ab`.
  if (targetPath === dragged.path || targetPath.startsWith(`${dragged.path}/`)) {
    return null
  }

  const leaf = dragged.path.split("/").pop()!
  const parent = dragged.path.slice(0, Math.max(0, dragged.path.length - leaf.length - 1))
  if (parent === targetPath) return null   // already there

  const destination = targetPath ? `${targetPath}/${leaf}` : leaf

  if (dragged.document) {
    return { kind: "document", documentId: dragged.document.id, uri: destination }
  }
  return { kind: "subtree", uriPrefix: dragged.path, newUriPrefix: destination }
}
```

- [ ] **Step 4: Run the tests**

```
cd frontend && npm test -- move-target && npm run typecheck
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/move-target.ts \
        frontend/src/features/documents/__tests__/move-target.test.ts
git commit -m "feat(documents): resolve a tree drop to a move"
```

---

### Task 14: dnd-kit over the tree rows

**The listeners must not be spread onto the library's rows.** `TreeViewItem` and `TreeViewBranchControl` do spread `...props` onto their DOM elements, but that spread lands *after* `ref` (which registers the row for the tree's focus management), `role="treeitem"`, the roving `tabIndex` and the `aria-*` attributes. Spreading `useDraggable().attributes` (`role="button"`, `tabIndex=0`) and `listeners` over those breaks the accessible tree and the arrow-key traversal `TreeViewTree` handles by bubbling — and `ref` is not in the typed props, so `setNodeRef` would not typecheck there anyway.

Use an inner wrapper for `setNodeRef` and the listeners, a `PointerSensor` with an activation distance so a click still selects, and do not spread `attributes`.

**Files:**
- Modify: `frontend/package.json` (add `@dnd-kit/core`)
- Modify: `frontend/src/features/documents/components/document-tree.tsx`
- Test: `frontend/src/features/documents/__tests__/document-tree-drag.test.tsx`

**Interfaces:**
- Consumes: `moveTarget` from Task 13.
- Produces: `DocumentTree`'s `onMove?: (target: MoveTarget) => void` prop. Task 15 supplies it.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the owner chose dnd-kit, and the spec fixed the inner-handle constraint

- [ ] **Step 1: Install the dependency**

```
cd frontend && npm install @dnd-kit/core
```

`@dnd-kit/sortable` is deliberately NOT installed: `buildUriTree` derives order from the uri path, so there is no user-defined ordering to persist.

- [ ] **Step 2: Write the failing tests**

```tsx
it("keeps the tree's own row semantics intact under drag", () => {
  render(<DocumentTree items={items} selectedId={null} onSelect={() => {}}
                       truncated={false} onMove={() => {}} />)
  // dnd-kit's `attributes` carry role="button" and tabIndex=0. Spreading
  // them onto the row would replace the treeitem role and the roving
  // tabIndex the library manages.
  const rows = screen.getAllByRole("treeitem")
  expect(rows.length).toBeGreaterThan(0)
  expect(screen.queryAllByRole("button", { name: /a\.md/i })).toHaveLength(0)
})

it("still selects on a plain click", async () => {
  const onSelect = vi.fn()
  render(<DocumentTree items={items} selectedId={null} onSelect={onSelect}
                       truncated={false} onMove={() => {}} />)
  await userEvent.click(screen.getByText("a.md"))
  // A PointerSensor with an activation distance is what keeps a click a
  // click rather than a zero-distance drag.
  expect(onSelect).toHaveBeenCalled()
})
```

- [ ] **Step 3: Run and watch fail**

```
cd frontend && npm test -- document-tree-drag
```

- [ ] **Step 4: Wire dnd-kit**

Wrap the tree in `<DndContext>` with:

```tsx
const sensors = useSensors(
  useSensor(PointerSensor, {
    // Without a distance every click is a zero-length drag and the row
    // never selects.
    activationConstraint: { distance: 6 },
  }),
)
```

Inside each row, render an inner `<span>` carrying `setNodeRef` and `{...listeners}` — never `{...attributes}`, and never on `TreeViewItem`/`TreeViewBranchControl` themselves. Register folder rows and the tree root as droppables via `useDroppable`, disabling any droppable for which `moveTarget(dragged, target)` returns `null` during the drag.

Add the library-gap note required by CLAUDE.md:

```tsx
/** darkraise-ui's TreeView ships no drag support (checked in its .d.ts:
 *  no drag props, and no drag or sortable component in the package). This
 *  local drag layer exists for that gap and should be retired if a later
 *  version closes it. */
```

- [ ] **Step 5: Run the tests**

```
cd frontend && npm test -- document-tree && npm run typecheck && npm run build
```

Expected: PASS, with every pre-existing `document-tree` test green — `onMove` is optional and `/projects/$project` passes nothing.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json \
        frontend/src/features/documents/components/document-tree.tsx \
        frontend/src/features/documents/__tests__/document-tree-drag.test.tsx
git commit -m "feat(documents): make tree rows draggable"
```

---

### Task 15: Dispatch a drop to the move verbs

**Files:**
- Modify: `frontend/src/features/documents/components/project-workspace.tsx`
- Test: `frontend/src/features/documents/__tests__/project-workspace.test.tsx`

**Interfaces:**
- Consumes: `moveTarget`/`MoveTarget` (Task 13), `DocumentTree`'s `onMove` (Task 14), `useDocumentMetadataUpdate` and `useDocumentSubtreeRename` (Task 7), `treeManagement` (Task 9).
- Produces: nothing further.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: both verbs and the resolution function were fixed by earlier tasks

- [ ] **Step 1: Write the failing tests**

```tsx
it("moves a dropped document with a uri PATCH", async () => {
  const patched: Array<Record<string, unknown>> = []
  const view = renderWorkspace(items, {
    treeManagement: true, onPatch: (p) => patched.push(p),
  })
  view.dropOn("a/one.md", "b")
  expect(patched[0]).toMatchObject({ uri: "b/one.md" })
})

it("moves a dropped folder with the subtree rename", async () => {
  const renamed: Array<Record<string, unknown>> = []
  const view = renderWorkspace(items, {
    treeManagement: true, onSubtreeRename: (p) => renamed.push(p),
  })
  view.dropOn("a", "b")
  expect(renamed[0]).toMatchObject({ uri_prefix: "a", new_uri_prefix: "b/a" })
})

it("surfaces a 409 without losing the tree", async () => {
  // A move onto an occupied path is a real refusal, not a bug: the target
  // uri is another document's identity.
  const view = renderWorkspace(items, {
    treeManagement: true, onPatch: () => { throw new HttpError(409) },
  })
  view.dropOn("a/one.md", "b")
  expect(await screen.findByText(/already/i)).toBeInTheDocument()
  expect(screen.getByText("one.md")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run and watch fail**

```
cd frontend && npm test -- project-workspace
```

- [ ] **Step 3: Dispatch**

```tsx
const handleMove = useCallback((target: MoveTarget) => {
  if (target.kind === "document") {
    metadataUpdate.mutate({ documentId: target.documentId, uri: target.uri })
  } else {
    subtreeRename.mutate({
      project,
      uri_prefix: target.uriPrefix,
      new_uri_prefix: target.newUriPrefix,
    })
  }
}, [metadataUpdate, subtreeRename, project])
```

Pass `onMove={treeManagement ? handleMove : undefined}` to `DocumentTree`. On a 409 show a toast (darkraise-ui's `sonner`) naming the occupied path; the list invalidation the hooks already do restores the tree.

- [ ] **Step 4: Run the full frontend suite**

```
cd frontend && npm test && npm run typecheck && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/components/project-workspace.tsx \
        frontend/src/features/documents/__tests__/project-workspace.test.tsx
git commit -m "feat(documents): move a note by dragging it"
```

---

## Closing out the increment

- [ ] **Run the backend suite in four chunks.** The full suite cannot complete in one process on this host — an `earlyoom` daemon kills it at ~80% swap and exit 143 is a SIGTERM, not a failure. Split `tests/*.py tests/test_api/*.py` into four and run each against its own lane database (`darkmem_test_2`..`darkmem_test_5`), sequentially.
- [ ] **Run the guards leg** from CLAUDE.md's Commands section, plus `test_event_taxonomy_map.py`.
- [ ] **Frontend:** `npm run typecheck && npm test && npm run build`.
- [ ] **SDKs:** `cd sdks && make generate`, then confirm `git status --porcelain` is clean.
- [ ] **Add a `## vN.N.N` section to `CHANGELOG.md`.** Run `git fetch --tags` first — CI writes the tags, so local ones go stale — then `backend/.venv/bin/python scripts/next_version.py plan` for the version. A push to master with no matching heading fails the release guard before the suite runs.
- [ ] **Redeploy.** `DARKMEM_PUSH=0 ./scripts/build-push.sh` → `docker compose up -d` → wait for `healthy` → confirm the change is in the running image, not just the tree. Note this host's database was rebuilt on 2026-09-07 for the v1.7.0 baseline; this increment adds no schema objects, so `schema_guard` should admit without a recreate.
- [ ] **Then** `superpowers:finishing-a-development-branch`.
