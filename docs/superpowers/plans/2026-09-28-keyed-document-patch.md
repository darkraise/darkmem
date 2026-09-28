# Keyed, hash-guarded document PATCH Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PATCH /api/v1/documents/{document_id}` admits a `capture`-scoped key and takes an optional `expected_hash`, and MCP `document_update`'s id mode takes the same, so the dr-superpowers mirror can archive a deleted document by moving it without losing its revisions.

**Architecture:** The compare-and-set lives in `document_door.update_document_metadata`, carried in the writer's own `UPDATE` (the pattern `put` uses, never read-then-compare), with one follow-up read that tells a missing document from a stale hash. The REST route swaps `require_auth` for `require_scope("capture")` (which still admits a login session) and maps the new refusal to 409; the MCP tool maps it to a `hash_conflict` envelope. Both doors stamp the caller's identity on the `document_updated` event.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy async (raw `text()` SQL), pytest with the repository's `session` / `client` fixtures.

**Spec:** ../darkraise-ai-plugins/docs/superpowers/specs/2026-09-28-darkmem-mirror-wiring-design.md

**Execution:** subagent — `claude --model sonnet --effort high` — two of the three tasks are heavy (totals 5 and 6)

**Plan review:** 2026-09-28 — dr-superpowers:judge-opus — executability 17 / coherence 18 / coverage 18 / assumptions 16 (round 2)

## Global Constraints

- Run everything from `backend/` with `.venv/bin/python`; there is no `python` on PATH.
- Tests run against a lane database of their own: prefix every pytest command with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2`. Never point a test at `darkmem_test` from a subagent, and never at production (`:5432`).
- Raw-SQL parameters whose type Postgres cannot infer carry an explicit `CAST(... AS ...)`.
- A stale `expected_hash` writes nothing: no row change, no tag change, no `document_updated` event.
- `expected_hash` is not a metadata field. A call naming only `expected_hash` is still `DocumentNothingToChange` (422 / `no_change`).
- Commit messages: `<type>(<scope>): <subject>`, subject at most 50 characters, imperative, no period, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- No new comments that describe what code does; a comment states a non-obvious reason only.

## Contracts

- `app.services.document_door.update_document_metadata(session, *, document_id, title=None, uri=None, pinned=None, tags=None, expected_hash: str | None = None, actor: str | None = None, api_key_id: UUID | None = None) -> None`. Raises `DocumentNothingToChange`, `DocumentTargetUnresolved`, `DocumentUriConflict` (as today) and `app.services.document_ingest.DocumentHashConflict(document_id=<UUID>, expected_hash=<str>, current_hash=<str | None>)` when `expected_hash` does not equal the row's `content_hash`. Produced by Task 1, consumed by Tasks 2 and 3.
- REST: `DocumentPatchRequest` gains `expected_hash: str | None = None`. A stale hash answers `409` with detail `expected_hash <e> does not match the document's current content_hash <c>` (the put route's wording). Task 2.
- MCP: `document_update(..., expected_hash: str | None = None)` answers `{"status": "hash_conflict", "document_id": <str>, "expected_hash": <str>, "current_hash": <str | None>}` on a stale hash; in the subtree mode `expected_hash` is a stray field answered by the existing `invalid_mode` envelope. Task 3.

## Assumptions (evidence)

- `require_scope` falls back to `require_auth` when no key is presented, so a browser session still reaches the route: `backend/app/api/auth.py:186-215`, read 2026-09-28.
- `events.api_key_id` carries no foreign key, so a service test can stamp a made-up UUID: `tests/test_document_update.py:504-521` already does, read 2026-09-28.
- The manifest serves each document's `id`, so the mirror can address this route: `app/api/routes/documents.py:475-479`, read 2026-09-28.
- The spec's §4 also names "the SDK generator's contract check". It does not apply: the SDK's three verbs never call this route (`sdks/generate.py` names no document route; checked 2026-09-28), so nothing there changes.
- An MCP refusal calls `session.rollback()`, which under the test fixture ends the test's outer transaction (`tests/conftest.py:72-90`). MCP tests therefore run the successful call before the refusal and write nothing to the database after it; the service tests in Task 1 prove that a refusal moves nothing.
- `current_key_name` and `current_api_key_id` are module-level imports in `app/api/mcp/server.py:13`, read 2026-09-28.
- The spec lives in the sibling checkout `../darkraise-ai-plugins`; this plan implements its §4 (the server half) only. §1-§3 are the plugin's own plan.
- Deploying is not a task: `CLAUDE.md` makes every landed backend change a redeploy (gate, build with `DARKMEM_PUSH=0`, `docker compose up -d`, confirm the new route shape with `curl -s localhost:8000/openapi.json | python3 -c "import json,sys; print('expected_hash' in json.load(sys.stdin)['components']['schemas']['DocumentPatchRequest']['properties'])"`, which must print `True`), done at finishing. The baseline is untouched, so no schema step applies.
- A full-list guard enumerates every key-gated route: `tests/test_api_keys.py` pins the set twice (`test_exactly_the_intended_routes_are_scope_gated` at line 1116 and the `expected` set at line 1183; read 2026-09-28), and the guards leg does not run it. Task 2 adds the PATCH route to both sets and runs the file.
- Task 2's documentation (parity note, `CLAUDE.md`) already names the MCP `hash_conflict` envelope that Task 3 builds. The three tasks land on one branch before any deploy, so the intermediate commit is never served.
- The Codex executor lane is off (`scripts/codex-gate`: `usable=false reason=free-plan lane=false`, 2026-09-28), so no task carries an `**Executor:**` line.

## Task index

1. Hash precondition in the metadata writer
2. Keyed, hash-guarded REST PATCH
3. MCP document_update hash precondition and changelog

---

### Task 1: Hash precondition in the metadata writer

**Files:**
- Modify: `backend/app/services/document_door.py` (the `document_ingest` import near line 37; `update_document_metadata` at lines 700-800)
- Test: `backend/tests/test_document_update.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the `update_document_metadata` signature and `DocumentHashConflict` behaviour in Contracts.

**Items:** 84

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_document_update.py`, add `from app.services.document_ingest import DocumentHashConflict` below the existing `from app.services.document_door import (...)` block, then append:

```python
async def _content_hash(session, document_id):
    return (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(document_id)},
    )).scalar_one()


async def _updated_events(session, document_id) -> int:
    return (await session.execute(
        text(
            "SELECT count(*) FROM events WHERE event_type = 'document_updated' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_matching_expected_hash_moves_the_document(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h1.md")
    await update_document_metadata(
        session, document_id=doc, uri="archive/notes/h1.md",
        expected_hash=await _content_hash(session, doc),
    )
    assert (await _read(session, doc))["uri"] == "archive/notes/h1.md"
    assert await _updated_events(session, doc) == 1


@pytest.mark.asyncio
async def test_a_stale_expected_hash_refuses_and_moves_nothing(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h2.md")
    current = await _content_hash(session, doc)
    with pytest.raises(DocumentHashConflict) as refused:
        await update_document_metadata(
            session, document_id=doc, uri="archive/notes/h2.md",
            expected_hash="stale",
        )
    assert refused.value.current_hash == current
    assert refused.value.expected_hash == "stale"
    assert (await _read(session, doc))["uri"] == "notes/h2.md"
    assert await _updated_events(session, doc) == 0


@pytest.mark.asyncio
async def test_an_expected_hash_against_a_missing_id_is_unresolved(session):
    with pytest.raises(DocumentTargetUnresolved):
        await update_document_metadata(
            session, document_id=uuid4(), uri="x.md", expected_hash="h",
        )


@pytest.mark.asyncio
async def test_a_tags_only_call_checks_the_hash_under_its_lock(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h3.md")
    with pytest.raises(DocumentHashConflict):
        await update_document_metadata(
            session, document_id=doc, tags=["topic/x"], expected_hash="stale",
        )
    assert await _tags(session, doc) == set()
    assert await _updated_events(session, doc) == 0


@pytest.mark.asyncio
async def test_a_tags_only_call_with_a_matching_hash_writes(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h4.md")
    await update_document_metadata(
        session, document_id=doc, tags=["topic/x"],
        expected_hash=await _content_hash(session, doc),
    )
    assert await _tags(session, doc) == {"topic/x"}


@pytest.mark.asyncio
async def test_an_expected_hash_alone_names_nothing_to_change(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h5.md")
    with pytest.raises(DocumentNothingToChange):
        await update_document_metadata(
            session, document_id=doc,
            expected_hash=await _content_hash(session, doc),
        )


@pytest.mark.asyncio
async def test_the_update_journals_the_caller_identity(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h6.md")
    key_id = uuid4()
    await update_document_metadata(
        session, document_id=doc, title="New", actor="sync-key", api_key_id=key_id,
    )
    row = (await session.execute(
        text(
            "SELECT actor, CAST(api_key_id AS text) AS api_key_id FROM events "
            "WHERE event_type = 'document_updated' AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(doc)},
    )).mappings().one()
    assert (row["actor"], row["api_key_id"]) == ("sync-key", str(key_id))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_document_update.py -k "expected_hash or hash_under or matching_hash or caller_identity"`
Expected: FAIL with `TypeError: update_document_metadata() got an unexpected keyword argument 'expected_hash'` (and `'actor'` for the identity test). `test_a_subtree_delete_journals_the_caller_identity` already exists and passes; it is matched by `-k` and must stay green.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/document_door.py`, change the import

```python
from app.services.document_ingest import UNCHANGED, DocumentUriConflict
```

to

```python
from app.services.document_ingest import UNCHANGED, DocumentHashConflict, DocumentUriConflict
```

Replace `update_document_metadata`, from its `async def` line down to (not including) the `if tags is not None:` line, with:

```python
async def update_document_metadata(
    session: AsyncSession,
    *,
    document_id: UUID | str,
    title: str | None = None,
    uri: str | None = None,
    pinned: bool | None = None,
    tags: list[str] | None = None,
    expected_hash: str | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> None:
    """Write only the fields the caller named.

    An unnamed field emits no assignment at all rather than writing NULL over
    its column, so renaming a document cannot silently unpin it or strip its
    tags.

    `project` is deliberately not a field: moving a document between spaces is
    not a rename, and allowing it here would let one call cross the boundary
    the personal space rests on.

    A call naming no field at all is refused rather than journalled: `events`
    is append-only, so it would leave a permanent `{"fields": []}` row saying
    an edit happened when none did. `expected_hash` is a precondition, not a
    field, so a call naming only it is refused the same way.

    `expected_hash` is a compare-and-set on `content_hash`, carried in the
    writer's own statement (the UPDATE's WHERE, or the tags-only path's
    locked read), never read and compared first: a filing landing between a
    separate check and the move would be silently carried along.
    """
    if title is None and uri is None and pinned is None and tags is None:
        raise DocumentNothingToChange(
            "name at least one of title, uri, pinned or tags"
        )
    doc_id = document_id if isinstance(document_id, UUID) else UUID(str(document_id))
    assignments: list[str] = []
    params: dict = {"id": str(doc_id)}
    if title is not None:
        assignments.append("title = CAST(:title AS text)")
        params["title"] = title
    if uri is not None:
        assignments.append("uri = CAST(:uri AS text)")
        params["uri"] = uri
    if pinned is not None:
        assignments.append(_PIN_ASSIGNMENT[pinned])

    if assignments:
        hash_guard = ""
        if expected_hash is not None:
            hash_guard = (
                " AND content_hash IS NOT DISTINCT FROM CAST(:expected_hash AS text)"
            )
            params["expected_hash"] = expected_hash
        try:
            # ux_documents_project_uri is what refuses a collision, and a
            # failed statement aborts the transaction it runs in -- so this
            # runs in a SAVEPOINT, leaving the caller's transaction usable
            # after the refusal rather than poisoned by it. RETURNING folds
            # the rowcount check and the project lookup into the same round
            # trip, and the UPDATE's own row lock is what serialises this
            # against a concurrent _set_document_tags on the same document.
            async with session.begin_nested():
                project = (await session.execute(
                    text(
                        f"UPDATE documents SET {', '.join(assignments)} "
                        f"WHERE id = CAST(:id AS uuid){hash_guard} RETURNING project"
                    ),
                    params,
                )).scalar_one_or_none()
        except IntegrityError as exc:
            raise DocumentUriConflict(uri) from exc
        if project is None:
            await _refuse_unmatched_update(session, doc_id, expected_hash)
    else:
        # No column assignment means a tags-only or entirely empty call, so
        # nothing above confirmed the row exists or locked it. Both matter
        # here: the lock is what makes a concurrent _set_document_tags
        # replace rather than race (`put_document` and `block_verbs._mutate`
        # already serialise on this row the same way), and the existence
        # check is what stops a phantom `document_updated` event for an id
        # nobody ever filed -- `events` is append-only, so that row would
        # never be undone.
        row = (await session.execute(
            text(
                "SELECT project, content_hash FROM documents "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(doc_id)},
        )).first()
        if row is None:
            raise DocumentTargetUnresolved(f"document not found: {doc_id}")
        project = row.project
        if expected_hash is not None and row.content_hash != expected_hash:
            raise DocumentHashConflict(
                document_id=doc_id, expected_hash=expected_hash,
                current_hash=row.content_hash,
            )

```

In the same function, change the trailing `record_event(` call so it passes the caller's identity (the payload is unchanged):

```python
    await record_event(
        session,
        event_type=DOCUMENT_UPDATED_EVENT,
        object_type="document",
        object_id=doc_id,
        project=project,
        actor=actor,
        api_key_id=api_key_id,
        payload={
            "fields": sorted(
                name for name, value in (
                    ("title", title), ("uri", uri),
                    ("pinned", pinned), ("tags", tags),
                )
                if value is not None
            )
        },
    )
```

Add this helper directly above `update_document_metadata`:

```python
async def _refuse_unmatched_update(
    session: AsyncSession, doc_id: UUID, expected_hash: str | None
) -> None:
    """An UPDATE that matched no row named a missing document or lost its hash
    precondition; one read tells which. The hash it reports may have moved
    again since, which only makes the refusal name the newer winner."""
    current = (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(doc_id)},
    )).first()
    if current is None or expected_hash is None:
        raise DocumentTargetUnresolved(f"document not found: {doc_id}")
    raise DocumentHashConflict(
        document_id=doc_id, expected_hash=expected_hash, current_hash=current[0],
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_document_update.py tests/test_document_routes.py`
Expected: PASS, every test in both files (the existing metadata tests prove the unguarded path is unchanged).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_door.py backend/tests/test_document_update.py
git commit -m "feat(documents): guard metadata edits by hash" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Keyed, hash-guarded REST PATCH

**Files:**
- Modify: `backend/app/api/routes/documents.py` (the keyed-routes comment at lines 116-120; `DocumentPatchRequest` at lines 278-296; `patch_document_route` at lines 925-956)
- Modify: `backend/tests/test_api_keys.py` (the two exact sets of key-gated routes, lines 1116-1134 and 1183-1201)
- Modify: `backend/tests/test_door_parity.py` (the `documents.metadata` `Surface` note, lines 436-472)
- Modify: `docs/two-door-parity.md` (regenerated block)
- Modify: `CLAUDE.md` (two sentences)
- Modify: `docs/runbook-exposed-deployment.md` (the `capture` row of the scope table, line 101)
- Test: `backend/tests/test_documents_keyed.py`

**Interfaces:**
- Consumes: `update_document_metadata`'s `expected_hash`, `actor`, `api_key_id` and `DocumentHashConflict` (Contracts).
- Produces: the REST contract in Contracts.

**Items:** 84

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 3 = 6

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_documents_keyed.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_documents_keyed.py`
Expected: four FAIL, one PASS. The capture-key move, the stale-hash test and the missing-document test each answer 401 (the route takes a login only and all three present a key); the read-key test answers 401 instead of 403. `test_a_login_session_still_moves_a_document` already passes and must stay green.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/routes/documents.py`, replace the comment above `_require_capture`

```python
# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the by-uri read, the
# manifest and the two revision reads. Every other document route stays
# login-only; widening one is a decision about what a leaked key can read or
# erase, made per route.
```

with

```python
# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the single-document
# metadata PATCH, the by-uri read, the manifest and the two revision reads.
# Every other document route stays login-only; widening one is a decision
# about what a leaked key can read or erase, made per route.
```

Add the field to `DocumentPatchRequest` directly below `tags: list[str] | None = None`:

```python
    expected_hash: str | None = None
```

Replace `patch_document_route` (its decorator line through its `return`) with:

```python
@router.patch("/{document_id}", response_model=DocumentPatchResponse)
async def patch_document_route(
    document_id: UUID,
    body: DocumentPatchRequest,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
) -> DocumentPatchResponse:
    """Write only the metadata fields the caller named.

    A capture-scoped key reaches this route as it reaches filing, so a
    client can retire a document by moving it under `expected_hash`: a move
    keeps the document's revisions, where a delete would cascade them away.
    The subtree rename stays login-only.
    """
    try:
        await update_document_metadata(
            session,
            document_id=document_id,
            title=body.title,
            uri=body.uri,
            pinned=body.pinned,
            tags=body.tags,
            expected_hash=body.expected_hash,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
        )
    except DocumentTargetUnresolved as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DocumentUriConflict as exc:
        # 409, the same shape the content-hash CAS and the block-first
        # refusal use: the caller made no mistake, the path is taken.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except DocumentHashConflict as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        ) from exc
    except DocumentNothingToChange as exc:
        # 422 rather than 200: the body is well formed and names nothing to
        # do, which is the same class as a body pydantic would reject.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc
    await session.commit()
    return DocumentPatchResponse(document_id=str(document_id))
```

(`Principal`, `_require_capture` and `DocumentHashConflict` are already imported in this module: lines 75, 122 and 102.)

In `backend/tests/test_api_keys.py`, the line

```python
            ("POST", "/api/v1/documents"),
```

appears exactly twice (once in each exact set). Replace both occurrences with

```python
            ("POST", "/api/v1/documents"),
            ("PATCH", "/api/v1/documents/{document_id}"),
```

In `backend/tests/test_door_parity.py`, in the `documents.metadata` `Surface`'s `note=(...)`, replace

```python
            "refusals map the same two service errors the routes do: "
```

with

```python
            "refusals map the same service errors the routes do: "
```

and replace the final string piece

```python
            "content-hash CAS already uses."
```

with

```python
            "content-hash CAS already uses. The single-document PATCH also "
            "admits a capture-scoped key and takes an optional expected_hash, "
            "the metadata twin of the filing's compare-and-set: a stale hash "
            "is a 409 against a `hash_conflict` envelope and moves nothing. "
            "The dr-superpowers mirror archives a deleted document through it, "
            "which keeps the document's revisions; the subtree rename stays "
            "login-only."
```

Regenerate the committed table: from `backend/`, run
`.venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())"`
and replace everything between `<!-- BEGIN GENERATED PARITY TABLE -->` and `<!-- END GENERATED PARITY TABLE -->` in `docs/two-door-parity.md` with its output (keep both marker lines).

In `CLAUDE.md` (MCP endpoint section), replace

```
ordinary login auth, like every document route except the five a
dr-superpowers mirror syncs through (filing, the by-uri read, the manifest
and the two revision reads, which admit a scoped key). That asymmetry is
```

with

```
ordinary login auth, like every document route except the six a
dr-superpowers mirror syncs through (filing, the single-document metadata
PATCH, the by-uri read, the manifest and the two revision reads, which admit
a scoped key). That asymmetry is
```

and in its Documents section, replace

```
  taken `(project, uri)` is refused: 409, or a `uri_conflict` envelope. Tags
```

with

```
  taken `(project, uri)` is refused: 409, or a `uri_conflict` envelope. The
  single-document mode takes an optional `expected_hash`, carried in the
  writer's own UPDATE (a stale hash answers 409, or a `hash_conflict`
  envelope, and moves nothing), and its PATCH admits a `capture` key: the
  dr-superpowers mirror archives a deleted document that way. Tags
```

In `docs/runbook-exposed-deployment.md`, in the scope table's `capture` row, replace

```
`POST /documents`, `POST /worklog/entries`
```

with

```
`POST /documents`, `PATCH /documents/{id}`, `POST /worklog/entries`
```

No test pins that table; it is what an operator reads to learn what a leaked `capture` key can do.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_documents_keyed.py tests/test_document_routes.py tests/test_api_keys.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py`
Expected: PASS (including `test_the_committed_table_is_the_enforced_table`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_keyed.py backend/tests/test_api_keys.py backend/tests/test_door_parity.py docs/two-door-parity.md docs/runbook-exposed-deployment.md CLAUDE.md
git commit -m "feat(documents): admit a key on the metadata PATCH" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: MCP document_update hash precondition and changelog

**Files:**
- Modify: `backend/app/api/mcp/server.py` (`document_update`, lines 1193-1328)
- Modify: `CHANGELOG.md` (`## v1.13.0` → `### Added`)
- Test: `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: `update_document_metadata`'s `expected_hash`, `actor`, `api_key_id` and `DocumentHashConflict` (Contracts).
- Produces: the MCP contract in Contracts.

**Items:** 84

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_mcp.py`:

```python
async def test_document_update_guards_a_move_by_hash(session, monkeypatch):
    """The success runs first: the refusal rolls the shared test session back,
    so nothing after it may write to the database (see tests/conftest.py)."""
    import json
    import uuid
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.services.document_door import put_document

    class Stub:
        def __init__(self):
            self.fingerprint = "test-fp-mcp-dochash|3"

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

        async def embed(self, value):
            return [1.0, 0.0, 0.0], self.fingerprint

        def llm_fingerprint(self):
            return self.fingerprint

    embedder_registry.forget("test-fp-mcp-dochash|3")
    llm = Stub()

    @asynccontextmanager
    async def _ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=llm))

    filed = await put_document(
        session, llm, project="mcp-dochash", uri="superpowers/notes/a.md", content="# A\n",
    )
    await session.commit()
    document_id = str(filed.document_id)

    moved = json.loads(await mcp_server.document_update(
        document_id=document_id,
        uri="superpowers/archive/20260928T000000Z/notes/a.md",
        expected_hash=filed.content_hash,
    ))
    assert moved == {"status": "ok", "document_id": document_id}

    stale = json.loads(await mcp_server.document_update(
        document_id=document_id, uri="superpowers/notes/a.md", expected_hash="stale",
    ))
    assert stale == {
        "status": "hash_conflict",
        "document_id": document_id,
        "expected_hash": "stale",
        "current_hash": filed.content_hash,
    }
    missing = json.loads(await mcp_server.document_update(
        document_id=str(uuid.uuid4()), uri="x.md", expected_hash="h",
    ))
    assert missing["status"] == "unresolved"
    embedder_registry.forget("test-fp-mcp-dochash|3")


async def test_a_keyed_document_update_stamps_its_key(session, monkeypatch):
    import json
    from contextlib import asynccontextmanager

    from mcp.server.auth.middleware.auth_context import auth_context_var
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
    from sqlalchemy import text

    import app.api.mcp.auth as mcp_auth
    from app.api.mcp import server as mcp_server
    from app.services.api_keys import issue_key

    @asynccontextmanager
    async def _on_the_test_session():
        yield session

    monkeypatch.setattr(mcp_auth, "async_session_factory", lambda: _on_the_test_session())
    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _on_the_test_session())
    document_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO documents (id, project, uri, title, source_type, content_hash) "
            "VALUES (CAST(:id AS uuid), 'mcp-stamp', 'superpowers/notes/s.md', 't', 'markdown', 'h1')"
        ),
        {"id": str(document_id)},
    )
    name = f"k-{uuid.uuid4().hex[:6]}"
    row, credential = await issue_key(session, name=name, scopes=["capture"])
    token = await mcp_auth.ApiKeyTokenVerifier().verify_token(credential)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        moved = json.loads(await mcp_server.document_update(
            document_id=str(document_id),
            uri="superpowers/archive/20260928T000000Z/notes/s.md",
            expected_hash="h1",
        ))
    finally:
        auth_context_var.reset(reset)
    assert moved == {"status": "ok", "document_id": str(document_id)}
    stamped = (await session.execute(
        text(
            "SELECT actor, api_key_id FROM events WHERE event_type = 'document_updated' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).all()
    assert [tuple(stamp) for stamp in stamped] == [(name, row.id)]


async def test_document_update_refuses_a_hash_in_the_subtree_mode():
    import json

    from app.api.mcp import server as mcp_server

    answer = json.loads(await mcp_server.document_update(
        project="p", uri_prefix="a", new_uri_prefix="b", expected_hash="h",
    ))
    assert answer["status"] == "invalid_mode"
    assert "expected_hash" in answer["reason"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_mcp.py -k "guards_a_move_by_hash or hash_in_the_subtree or stamps_its_key"`
Expected: FAIL, all three, with `TypeError: document_update() got an unexpected keyword argument 'expected_hash'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/mcp/server.py`, `document_update`:

1. Add the parameter after `tags`:

```python
    tags: list[str] | None = None,
    expected_hash: str | None = None,
```

2. In the docstring's `Args:`, below the `tags:` line, add:

```
        expected_hash: Optional, single-document mode only: edit only if the
            document still holds this content_hash. A mismatch answers a
            `hash_conflict` envelope naming both hashes and moves nothing.
```

3. Replace the local import block

```python
    from app.services.document_door import (
        DocumentNothingToChange, DocumentTargetUnresolved,
        DocumentUriConflict, rename_documents, update_document_metadata,
    )
```

with

```python
    from app.services.document_door import (
        DocumentNothingToChange, DocumentTargetUnresolved,
        DocumentUriConflict, rename_documents, update_document_metadata,
    )
    from app.services.document_ingest import DocumentHashConflict
```

4. In the `stray = sorted(...)` expression, replace the single-mode field tuple

```python
            (("title", title), ("uri", uri), ("pinned", pinned), ("tags", tags))
```

with

```python
            (("title", title), ("uri", uri), ("pinned", pinned), ("tags", tags),
             ("expected_hash", expected_hash))
```

5. Replace the single-document call

```python
                await update_document_metadata(
                    session, document_id=document_id, title=title, uri=uri,
                    pinned=pinned, tags=tags,
                )
```

with

```python
                await update_document_metadata(
                    session, document_id=document_id, title=title, uri=uri,
                    pinned=pinned, tags=tags, expected_hash=expected_hash,
                    actor=current_key_name(), api_key_id=current_api_key_id(),
                )
```

6. Add this handler directly after the `except DocumentUriConflict as exc:` block (before `except DocumentTargetUnresolved`):

```python
        except DocumentHashConflict as exc:
            # Its REST twin is a 409 carrying the same two hashes.
            await session.rollback()
            return json.dumps({
                "status": "hash_conflict",
                "document_id": document_id,
                "expected_hash": exc.expected_hash,
                "current_hash": exc.current_hash,
            })
```

In `CHANGELOG.md`, under `## v1.13.0 — unreleased` → `### Added`, append after the last `Added` bullet (before `### Removed`):

```markdown
- **Hash-guarded document moves over a key.** `PATCH
  /api/v1/documents/{document_id}` admits a `capture`-scoped key and takes an
  optional `expected_hash`; a stale hash answers 409 and moves nothing. MCP
  `document_update` takes the same parameter and answers a `hash_conflict`
  envelope. The dr-superpowers mirror uses it to archive a deleted document
  without losing its revisions.
```

- [ ] **Step 4: Run the tests and the guards leg**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_mcp.py tests/test_document_update.py`
Expected: PASS.

Then the guards leg (a changed MCP tool signature):

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py CHANGELOG.md
git commit -m "feat(mcp): guard document_update by hash" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
