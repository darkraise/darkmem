# Personal Notes Foundation (increment 1, lanes 1c-1e) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Give the block verbs a real compare-and-set, widen the tag sweep so a note-only tag survives the hour, and ship `document_update` so a converted note can be renamed, moved and pinned.

**Architecture:** Three lanes. **1c** threads an `expected_hash` precondition through `_mutate` and all four block verbs, serves `content_hash` on both doors' block reads, and serialises the editor's mutations. **1d** gives `document_tags` a mapped Table object and widens `prune_orphans` and the tag histogram to use it. **1e** adds the metadata verb in two shapes plus the MCP tool, and puts the block-first direction refusal on **both** the existing-row path and the upsert.

**Tech Stack:** FastAPI, SQLAlchemy async + raw SQL with asyncpg CASTs, Postgres 16, `mcp==2.1.1` (`MCPServer`), React + TanStack Query, vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-personal-notes-workspace-design.md` (1c is §5, 1d is §7, 1e is §4.2 and §4.3; sequencing is §12). **§4.3 was amended 2026-09-07** after review found its original instruction would cause data loss — see Task 8.

## Global Constraints

- **Lane order is forced: 1d (Task 5) must land before 1e (Tasks 7-12).** The first `document_tags` row the metadata verb writes is deleted within the hour by `tag_orphan_cleanup` if `prune_orphans` has not been widened first. Verified: `document_tags.tag_id` is `ON DELETE CASCADE` (`0001_baseline.py:1390`), `prune_orphans` deletes any tag lacking a `memory_tags` row, and the job is registered hourly at `app/main.py:458`.
- **Lane 1c (Tasks 1-4) is independent** of 1d/1e and may run in parallel.
- **No new schema.** `document_tags`, `documents.pinned_at`, `document_links` and `projects.kind` all exist in the baseline on master (1a-1b merged at `e1ae6589`). What does *not* exist is a **mapped Table object** for `document_tags` — Task 5 creates it.
- **Reuse `DocumentHashConflict`** (`app/services/document_ingest.py:101`). It carries `expected_hash` / `current_hash` and already has a 409 mapping and an MCP `hash_conflict` envelope. Do not add a second conflict exception. `block_verbs.py:34` already imports from `document_ingest`, so Task 1's import creates no cycle.
- **New exception classes go in `document_ingest.py`, not `document_door.py`.** `document_door` imports the repository; a repository raising a `document_door` class would close a cycle.
- **Teach the shared error mappers, never add a per-site `except`.** REST has `_block_write_error` (`app/api/routes/documents.py:819`); MCP has `_block_refusal` (`app/api/mcp/server.py:1930`).
- **Raw-SQL params need CASTs**, or asyncpg raises `IndeterminateDatatypeError`.
- **Commit messages:** `<type>(<scope>): <subject>`, subject <= 50 chars, imperative, no period.

### Test conventions this plan follows

There is **no** `filed_note`, `llm`, or `mcp` fixture in this repo. Do not invent one.

- Block/document service tests are `async def`, take `session`, and file through the local `_file(session, content, uri) -> (llm, document_id)` helper with the local `StubEmbedder` (`tests/test_block_verbs.py:41-68`).
- Route tests use the **async** `client` fixture (`tests/conftest.py:141`, an httpx `AsyncClient`) and must `await` and pass `auth_headers`, or they 401 on `require_auth`.
- MCP tests call the tool function directly — `mcp_server.block_update(...)` — with `monkeypatch` on `async_session_factory` and `_pipeline` (`tests/test_mcp.py:383-440`).
- Real test paths: `tests/test_document_routes.py` (not `test_documents_routes.py`), `tests/test_api/test_tags.py`, `tests/test_api/test_rest_conformance.py`, `tests/test_repositories.py` (holds the existing `prune_orphans` test at :78).

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `backend/app/services/block_verbs.py` | `_DOC_META` gains `content_hash`; `_mutate` and the four verbs gain `expected_hash` | 1 |
| `backend/app/api/routes/documents.py` | `expected_hash` on four block routes; `content_hash` on the blocks read; `_block_write_error` learns the conflict; new `PATCH` and `rename` routes | 2, 10 |
| `backend/app/api/mcp/server.py` | `expected_hash` on four block tools; `include_hash`; `_block_refusal` learns the conflict; `document_update` | 3, 11 |
| `frontend/src/features/documents/lib/mutation-queue.ts` | serialised queue with hash tracking and re-read | 4 |
| `backend/app/models/memory.py` | `document_tags` Table object beside `memory_tags` | 5 |
| `backend/app/repositories/relational.py`, `app/services/analytics.py` | sweep and histogram widen to `document_tags` | 5 |
| `backend/app/services/events.py` | `document_updated` joins `EVENT_TYPES` | 6 |
| `backend/app/services/document_door.py` | `update_document_metadata`, `set_document_tags`, `rename_documents` | 7, 9 |
| `backend/app/services/document_ingest.py` | `DocumentUriConflict`; the upsert-side direction guard | 7, 8 |
| `backend/app/api/mcp/scopes.py`, `app/services/prompt.py` | the new tool's scope and its place in the agent roster | 11, 12 |

---

### Task 1: Compare-and-set in the block verbs

**Files:**
- Modify: `backend/app/services/block_verbs.py:81-85` (`_DOC_META`), `:150-175` (`_mutate`), `:291`, `:318`, `:356`, `:403`
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: `DocumentHashConflict` from `app.services.document_ingest`
- Produces: each verb gains keyword-only `expected_hash: str | None = None`:
  - `update_block(session, llm, *, block_id: str, text: str, type: str | None = None, properties: dict | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `insert_block(session, llm, *, document_id: str, type: str, text: str, parent_id: str | None = None, after_block_id: str | None = None, properties: dict | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `move_block(session, llm, *, block_id: str, new_parent_id: str | None = None, after_block_id: str | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `delete_block(session, llm, *, block_id: str, expected_hash: str | None = None) -> BlockWriteResult`
- Note `BlockWriteResult.content_hash` already exists (`block_verbs.py:65-71`) and already carries the post-write hash. Nothing needs adding for a caller to chain edits.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: §5 fixes the design, and the lock is already `_mutate`'s first statement (`block_verbs.py:159`), so the compare is CAS-equivalent where it sits

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_block_verbs.py`. These use the file's own `_file` helper and `StubEmbedder` — there is no `filed_note` or `llm` fixture in this repo.

```python
async def _hash_of(session, document_id):
    return (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": document_id},
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_stale_expected_hash_refuses_every_verb(session):
    """All four verbs rewrite content_hash, so all four take the precondition.
    Insert and move rewrite it as much as update does, so a caller that
    preconditions only its updates still clobbers a concurrent insert."""
    llm, doc = await _file(session, "# T\n\npara", "notes/cas.md")
    block = (await _blocks(session, doc))[0]["id"]
    stale = "0" * 64

    for call in (
        lambda: update_block(session, llm, block_id=block, text="x",
                             expected_hash=stale),
        lambda: insert_block(session, llm, document_id=doc, type="paragraph",
                             text="x", expected_hash=stale),
        lambda: move_block(session, llm, block_id=block, expected_hash=stale),
        lambda: delete_block(session, llm, block_id=block, expected_hash=stale),
    ):
        with pytest.raises(DocumentHashConflict):
            await call()


@pytest.mark.asyncio
async def test_the_conflict_names_the_hash_that_actually_holds(session):
    llm, doc = await _file(session, "# T\n\npara", "notes/cas2.md")
    block = (await _blocks(session, doc))[0]["id"]
    live = await _hash_of(session, doc)

    with pytest.raises(DocumentHashConflict) as caught:
        await update_block(session, llm, block_id=block, text="x",
                           expected_hash="0" * 64)

    assert caught.value.expected_hash == "0" * 64
    assert caught.value.current_hash == live


@pytest.mark.asyncio
async def test_a_matching_expected_hash_applies_the_edit(session):
    llm, doc = await _file(session, "# T\n\npara", "notes/cas3.md")
    block = (await _blocks(session, doc))[0]["id"]

    result = await update_block(session, llm, block_id=block, text="edited",
                                expected_hash=await _hash_of(session, doc))

    assert result.content_hash == await _hash_of(session, doc)
    assert [b["text"] for b in await _blocks(session, doc)][0] == "edited"


@pytest.mark.asyncio
async def test_omitting_the_hash_stays_last_writer_wins(session):
    """The precondition is opt-in. Every shipped caller omits it today."""
    llm, doc = await _file(session, "# T\n\npara", "notes/cas4.md")
    block = (await _blocks(session, doc))[0]["id"]
    await update_block(session, llm, block_id=block, text="edited")
    assert [b["text"] for b in await _blocks(session, doc)][0] == "edited"
```

Add `DocumentHashConflict` to the file's existing `from app.services.document_ingest import compute_content_hash` line.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_block_verbs.py -k expected_hash -v`
Expected: FAIL with `TypeError: update_block() got an unexpected keyword argument 'expected_hash'`.

- [ ] **Step 3: Make `_DOC_META` read the hash**

```python
_DOC_META = text(
    "SELECT project, content, content_hash, "
    "       properties->>'ingest_direction' AS direction, "
    "       properties->>'frontmatter' AS frontmatter "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)
```

- [ ] **Step 4: Compare inside `_mutate`, after the lock**

```python
async def _mutate(session, llm, *, document_id, apply, touched_embed, verb,
                  block_id, expected_hash=None):
```

and immediately after the existing `if meta is None:` guard:

```python
    # After the lock, which is what makes this a compare-and-set rather than a
    # check-then-act: no writer can move content_hash between this read and
    # the write below, because both are inside one held row lock.
    if expected_hash is not None and meta["content_hash"] != expected_hash:
        raise DocumentHashConflict(
            document_id=document_id,
            expected_hash=expected_hash,
            current_hash=meta["content_hash"],
        )
```

Add `DocumentHashConflict` to the existing `document_ingest` import at `block_verbs.py:34`.

- [ ] **Step 5: Thread the parameter through all four verbs**

Each of `update_block`, `insert_block`, `move_block`, `delete_block` gains `expected_hash: str | None = None` as its last keyword-only parameter and passes `expected_hash=expected_hash` on its `_mutate(...)` call. Change nothing else in the four bodies.

- [ ] **Step 6: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_block_verbs.py -v`
Expected: PASS, including every pre-existing test — they all omit `expected_hash`.

- [ ] **Step 7: Prove the compare is load-bearing**

Comment out the `if expected_hash is not None ...` guard, re-run, confirm the refusal tests fail, restore it.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(documents): precondition the block verbs on a hash"
```

---

### Task 2: Serve and accept the hash on REST

**Files:**
- Modify: `backend/app/api/routes/documents.py:367-374` (`DocumentBlocksResponse`), `:768-808` (the blocks read), `:819-826` (`_block_write_error`), `:866`, `:886`, `:908` (the verb routes)
- Test: `backend/tests/test_document_routes.py`, `backend/tests/test_api/test_rest_conformance.py`

**Interfaces:**
- Consumes: `expected_hash` on the four verbs (Task 1)
- Produces: `DocumentBlocksResponse.content_hash: str | None`; `expected_hash` as a body field on `BlockUpdateRequest` / `BlockInsertRequest` / `BlockMoveRequest`, and a **query parameter** on delete

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: §5 fixes the field placement and the query-parameter exception for DELETE

> **The real routes are `/{document_id}/blocks/{block_id}`**, not `/blocks/{block_id}`. They take `document_id: UUID`, `_user=Depends(require_auth)`, and call `_assert_block_is_in` first. Do not register a new route path.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_the_blocks_read_serves_the_documents_hash(client, auth_headers, filed):
    doc = await filed("notes/h.md", "# T\n\npara")
    body = (await client.get(f"/api/v1/documents/{doc}",
                             headers=auth_headers)).json()
    assert body["content_hash"], "a caller cannot precondition its first edit"


@pytest.mark.asyncio
async def test_a_stale_hash_answers_409_naming_both_hashes(
    client, auth_headers, filed, first_block,
):
    doc = await filed("notes/h2.md", "# T\n\npara")
    response = await client.patch(
        f"/api/v1/documents/{doc}/blocks/{await first_block(doc)}",
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
        f"/api/v1/documents/{doc}/blocks/{await first_block(doc)}"
        f"?expected_hash={'0' * 64}",
        headers=auth_headers,
    )
    assert response.status_code == 409
```

Define `filed` and `first_block` as local helpers in this test module (file a document over the route, return its id; read its first block id) — they do not exist as shared fixtures.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_routes.py -k hash -v`
Expected: FAIL — the first on `KeyError: 'content_hash'`, the other two on `200`.

- [ ] **Step 3: Serve the hash**

```python
class DocumentBlocksResponse(BaseModel):
    document_id: str
    blocks: list[BlockRowModel]
    content: str | None = None
    # Served unconditionally: one short string, and without it a caller cannot
    # precondition its first edit at all (spec section 5).
    content_hash: str | None = None
    horizon: bool = True
```

Select `content_hash` in the read at `:768-808` and pass it to the constructor.

- [ ] **Step 4: Accept the precondition**

Add `expected_hash: str | None = None` to `BlockUpdateRequest`, `BlockInsertRequest` and `BlockMoveRequest`, and forward `expected_hash=body.expected_hash` on each verb call. For delete, add a parameter (`Query` is already imported in this module):

```python
async def delete_block_route(
    document_id: UUID,
    block_id: UUID,
    expected_hash: str | None = Query(
        None, description="Refuse unless the document's content_hash matches."
    ),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> None:
```

forwarding `expected_hash=expected_hash`.

- [ ] **Step 5: Teach the shared mapper**

All four routes already funnel through `_block_write_error`. Add one clause there rather than four `except` blocks:

```python
def _block_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BlockTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, BlockCycleError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, (DocumentTooLarge, DocumentNotConvertible)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, DocumentHashConflict):
        # 409, not 422: the caller made no mistake -- it lost a race, or the
        # document moved since it last read it. The detail names both hashes
        # so it can re-read and retry without a second round trip.
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        )
    raise exc
```

- [ ] **Step 6: Update the conformance map**

Run `tests/test_api/test_rest_conformance.py` and add exactly the rows it names as missing. Do not guess keys.

- [ ] **Step 7: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_routes.py tests/test_api/test_rest_conformance.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/
git commit -m "feat(documents): precondition the block routes"
```

---

### Task 3: Serve and accept the hash on MCP

**Files:**
- Modify: `backend/app/api/mcp/server.py:756-810` (`document_get`), `:1930-1940` (`_block_refusal`), `:1950`, `:1989`, `:2032`, `:2068`
- Modify: `docs/two-door-parity.md`
- Test: `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: `expected_hash` on the four verbs (Task 1)
- Produces: `document_get(..., include_hash: bool = False)` returning `{content_hash, blocks}` when set; `expected_hash` on all four block tools

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §5 decides the shape — an array cannot carry a hash, so it is a flag returning an object, the shape `include_content` already established

- [ ] **Step 1: Write the failing tests**

Follow `tests/test_mcp.py:383-440`: call the tool function directly with `monkeypatch` on `async_session_factory` and `_pipeline`. There is no `mcp` fixture.

```python
@pytest.mark.asyncio
async def test_document_get_answers_an_object_when_include_hash_is_set(
    monkeypatch, session_factory, filed_doc,
):
    """An array cannot carry a hash. Same object-under-a-flag shape
    include_content already uses, not a new convention."""
    _patch(monkeypatch, session_factory)
    bare = json.loads(await mcp_server.document_get(document_id=filed_doc))
    assert isinstance(bare, list)

    boxed = json.loads(
        await mcp_server.document_get(document_id=filed_doc, include_hash=True))
    assert set(boxed) == {"content_hash", "blocks"}
    assert boxed["blocks"] == bare


@pytest.mark.asyncio
async def test_a_stale_hash_answers_a_conflict_envelope(
    monkeypatch, session_factory, filed_doc, first_block_id,
):
    _patch(monkeypatch, session_factory)
    envelope = json.loads(await mcp_server.block_update(
        block_id=first_block_id, text="x", expected_hash="0" * 64))
    assert envelope["status"] == "hash_conflict"
    assert envelope["expected_hash"] == "0" * 64
    assert envelope["current_hash"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -k "include_hash or conflict_envelope" -v`
Expected: FAIL — unexpected argument, and `block_update` raises rather than returning an envelope.

- [ ] **Step 3: Add `include_hash`**

Mirror the existing `include_content` branch. With both flags set the object carries `content`, `content_hash` and `blocks`; with neither, the bare array is returned unchanged so no existing caller's parse breaks.

- [ ] **Step 4: Teach `_block_refusal`, then thread the parameter**

```python
def _block_refusal(exc: Exception, **fields) -> str | None:
    from app.services.block_verbs import BlockCycleError, BlockTargetUnresolved
    from app.services.document_door import DocumentNotConvertible
    from app.services.document_ingest import DocumentHashConflict

    if isinstance(exc, DocumentNotConvertible):
        return json.dumps({"status": "not_convertible", "reason": str(exc), **fields})
    if isinstance(exc, BlockCycleError):
        return json.dumps({"status": "cycle_refused", "reason": str(exc), **fields})
    if isinstance(exc, BlockTargetUnresolved):
        return json.dumps({"status": "unresolved", "reason": str(exc), **fields})
    if isinstance(exc, DocumentHashConflict):
        # A structured refusal rather than a tool error: the caller can
        # machine-read this, re-read and retry. Its REST twin is a 409.
        return json.dumps({
            "status": "hash_conflict",
            "expected_hash": exc.expected_hash,
            "current_hash": exc.current_hash,
            **fields,
        })
    return None
```

Each of the four tools gains `expected_hash: str | None = None` and forwards it. **Confirm each tool's `except` calling `_block_refusal` runs before any bare `except Exception`**, or the envelope is never reached.

- [ ] **Step 5: Record the flag in the parity table**

Add `include_hash` to `docs/two-door-parity.md` beside `include_content`, stating it is the same shape and why the array could not carry the field. `_MIN_REASON_CHARS` is 80 (`tests/test_door_parity.py:1565`) for any row needing a reason.

- [ ] **Step 6: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py tests/test_door_parity.py -q`
Expected: PASS. No tool was added, so `EXPECTED_TOOLS` must not move. If it does, a tool was added by accident.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py docs/two-door-parity.md
git commit -m "feat(mcp): precondition the block tools on a hash"
```

---

### Task 4: Serialise the editor's mutations

**Files:**
- Create: `frontend/src/features/documents/lib/mutation-queue.ts`
- Modify: `frontend/src/hooks/api/use-blocks-api.ts:36-105`, `frontend/src/hooks/api/use-documents-api.ts:323-325`
- Test: `frontend/src/features/documents/__tests__/mutation-queue.test.ts`

**Interfaces:**
- Consumes: `content_hash` on the blocks read (Task 2); `BlockWriteResponse.content_hash`, which already exists
- Produces: `createMutationQueue(initialHash: string | null, reread: () => Promise<string>)` with `enqueue<T>(fn: (hash: string) => Promise<{ result: T; content_hash: string | null }>): Promise<T>`

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5
**Approach:** inline - skip 3: §5 names the requirement and the failure it prevents

> **Two shapes the queue must survive**, both found in review. `DELETE .../blocks/{id}` answers **204 with no body** (`routes:908`, `use-blocks-api.ts:102` types it `apiFetch<void>`), so a delete yields no new hash. And after a rejection the tracked hash is stale forever unless something re-reads it. Both are handled by letting a mutation return `content_hash: null` and giving the queue a `reread`.

- [ ] **Step 1: Write the failing tests**

```typescript
import { describe, expect, it } from 'vitest'
import { createMutationQueue } from '../lib/mutation-queue'

const noReread = async () => 'unused'

describe('the mutation queue', () => {
  it('feeds each mutation the hash the previous one returned', async () => {
    const queue = createMutationQueue('hash-0', noReread)
    const seen: string[] = []
    const run = (next: string) => queue.enqueue(async (hash) => {
      seen.push(hash)
      return { result: null, content_hash: next }
    })

    // Fired synchronously, exactly as the editor fires a commit and an insert.
    await Promise.all([run('hash-1'), run('hash-2')])

    expect(seen).toEqual(['hash-0', 'hash-1'])
  })

  it('runs one mutation at a time', async () => {
    const queue = createMutationQueue('hash-0', noReread)
    let live = 0
    let peak = 0
    const run = () => queue.enqueue(async (hash) => {
      live += 1
      peak = Math.max(peak, live)
      await new Promise((r) => setTimeout(r, 5))
      live -= 1
      return { result: null, content_hash: hash }
    })

    await Promise.all([run(), run(), run()])

    expect(peak).toBe(1)
  })

  it('re-reads the hash after a mutation that returns none', async () => {
    // DELETE answers 204 with no body, so it yields no hash.
    const queue = createMutationQueue('hash-0', async () => 'hash-fresh')
    const seen: string[] = []
    await queue.enqueue(async () => ({ result: null, content_hash: null }))
    await queue.enqueue(async (hash) => {
      seen.push(hash)
      return { result: null, content_hash: hash }
    })
    expect(seen).toEqual(['hash-fresh'])
  })

  it('re-reads the hash after a rejection instead of wedging', async () => {
    const queue = createMutationQueue('hash-0', async () => 'hash-fresh')
    const seen: string[] = []
    await expect(queue.enqueue(async () => {
      throw new Error('409')
    })).rejects.toThrow('409')
    await queue.enqueue(async (hash) => {
      seen.push(hash)
      return { result: null, content_hash: hash }
    })
    expect(seen).toEqual(['hash-fresh'])
  })
})
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/mutation-queue.test.ts`
Expected: FAIL — the module does not exist.

- [ ] **Step 3: Write the queue**

```typescript
type Mutation<T> = (hash: string) => Promise<{ result: T; content_hash: string | null }>

export function createMutationQueue(
  initialHash: string | null,
  reread: () => Promise<string>,
) {
  let hash = initialHash
  // The tail of the chain. Each enqueue appends to it, so mutations run in
  // call order and each sees the hash its predecessor produced. Without this
  // the editor's synchronous commit-then-insert sends both with the same hash
  // and the second 409s against the first (spec section 5).
  let tail: Promise<unknown> = Promise.resolve()

  function enqueue<T>(fn: Mutation<T>): Promise<T> {
    const run = tail.then(async () => {
      // null after a delete (204, no body) or after a rejection dropped it.
      if (hash === null) hash = await reread()
      try {
        const { result, content_hash } = await fn(hash)
        hash = content_hash
        return result
      } catch (error) {
        // Drop the hash rather than keep a stale one: a 409 means the document
        // moved, and every later mutation would carry the losing hash forever.
        hash = null
        throw error
      }
    })
    // Keep the chain alive after a rejection, or one failure wedges the rest.
    tail = run.catch(() => undefined)
    return run as Promise<T>
  }

  return { enqueue }
}
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/mutation-queue.test.ts`
Expected: PASS, all four.

- [ ] **Step 5: Type the hash onto the blocks query**

`use-documents-api.ts:324` types the response as `{ document_id, blocks }`. Add `content_hash: string | null` so the queue's seed is typed rather than cast.

- [ ] **Step 6: Route the block hooks through the queue**

In `use-blocks-api.ts`, hold one queue per `documentId`, seeded from the blocks query's `content_hash` with `reread` refetching that query. Each of the four hooks sends its current hash as `expected_hash` and returns the response's `content_hash` — `null` for delete, which is `apiFetch<void>`.

- [ ] **Step 7: Run the frontend suite**

Run: `cd frontend && npm run typecheck && npm test`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat(documents): serialise the editor's mutations"
```

---

### Task 5: Map `document_tags` and widen the sweep

**Files:**
- Modify: `backend/app/models/memory.py:31` area (add the Table beside `memory_tags`)
- Modify: `backend/app/repositories/relational.py:239` (`get_with_counts`), `:249-267` (`prune_orphans`)
- Modify: `backend/app/services/analytics.py:266-272`
- Test: `backend/tests/test_repositories.py` (the existing `prune_orphans` test is at :78), `backend/tests/test_api/test_tags.py`

**Interfaces:**
- Produces: `document_tags` Table object importable from `app.models.memory`
- **Tasks 7-12 depend on this task having landed**, not on an interface it exports.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 3 = 5
**Approach:** inline - skip 3: §7 states both call sites and the widening exactly

> **The table exists in the baseline but has no mapped Table object** — `grep -rn document_tags backend/app/` finds nothing outside the migration. Both widenings need one, so this task creates it first.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_a_note_only_tag_survives_the_sweep(session, note_tagged):
    """tag_orphan_cleanup runs hourly. Before this widening it deleted every
    tag with no memory_tags row, so a tag carried only by a note -- and its
    document_tags links, under the cascade -- vanished within the hour."""
    repo = RelationalRepository(session)
    await repo.prune_orphans()
    assert "note-only" in {t.name for t in await repo.list_all()}


@pytest.mark.asyncio
async def test_the_histogram_counts_a_documents_tag(session, note_tagged):
    counts = {t.name: n for t, n in
              await RelationalRepository(session).get_with_counts()}
    assert counts["note-only"] == 1


@pytest.mark.asyncio
async def test_a_tag_referenced_by_neither_is_still_swept(session, orphan_tag):
    """The widening must not turn the sweep off."""
    repo = RelationalRepository(session)
    assert await repo.prune_orphans() >= 1
    assert "abandoned" not in {t.name for t in await repo.list_all()}


@pytest.mark.asyncio
async def test_the_count_sums_rather_than_multiplies(session, doubly_tagged):
    """Two memories and two documents is 4, not 8. A join across both link
    tables multiplies the rows and passes every single-reference test."""
    counts = {t.name: n for t, n in
              await RelationalRepository(session).get_with_counts()}
    assert counts["shared"] == 4
```

Write `note_tagged`, `orphan_tag` and `doubly_tagged` locally in the test module, inserting `tags` and `document_tags` rows with raw SQL — nothing writes `document_tags` until Task 7.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repositories.py -k "note_only or histogram or sums" -v`
Expected: FAIL — the tag is swept, and the counts report 0.

- [ ] **Step 3: Map the table**

Beside `memory_tags` in `backend/app/models/memory.py`:

```python
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", UUID(as_uuid=True),
           ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer,
           ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)
```

Match the baseline's column types exactly — read `0001_baseline.py`'s `document_tags` definition rather than trusting this snippet.

- [ ] **Step 4: Widen `prune_orphans`**

```python
    async def prune_orphans(self) -> int:
        """Delete tags nothing references any more, returning the count.

        Tags are linked from two tables since the notes workspace landed:
        ``memory_tags`` and ``document_tags``, both ON DELETE CASCADE. Checking
        only the first deletes a tag carried by a note alone -- and its links
        with it under the cascade -- within the hour ``tag_orphan_cleanup``
        next runs."""
        result = await self.session.execute(
            sa_text("""
                DELETE FROM tags t
                WHERE NOT EXISTS (
                    SELECT 1 FROM memory_tags mt WHERE mt.tag_id = t.id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM document_tags dt WHERE dt.tag_id = t.id
                )
                RETURNING t.id
            """)
        )
        return len(result.scalars().all())
```

- [ ] **Step 5: Widen both counts with correlated subqueries**

A join across two one-to-many tables multiplies the rows, so each side counts on its own:

```python
        memory_count = (
            select(func.count())
            .select_from(memory_tags)
            .where(memory_tags.c.tag_id == Tag.id)
            .scalar_subquery()
        )
        document_count = (
            select(func.count())
            .select_from(document_tags)
            .where(document_tags.c.tag_id == Tag.id)
            .scalar_subquery()
        )
        stmt = select(Tag, (memory_count + document_count).label("count"))
```

Apply the same shape in `analytics.py:266-272`, which orders by the count.

- [ ] **Step 6: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repositories.py tests/test_api/test_tags.py -q`
Expected: PASS, including the pre-existing prune test at :78 and the sums-rather-than-multiplies test.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/memory.py backend/app/repositories/relational.py backend/app/services/analytics.py backend/tests/
git commit -m "fix(tags): count and keep a document-only tag"
```

---

### Task 6: Add `document_updated` to the vocabulary

**Files:**
- Modify: `backend/app/services/events.py:138-180` (`EVENT_TYPES`)
- Test: `backend/tests/test_events.py`

**Interfaces:**
- Produces: the literal `"document_updated"` in `EVENT_TYPES`, which Task 7 emits

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 4: additive, one file, and a revert is the whole cost of being wrong

- [ ] **Step 1: Write the failing test**

```python
def test_document_updated_is_in_the_vocabulary():
    """Widening is taxonomy-first: the value lands before its emitter ships,
    or the first emission logs an unknown-type warning and misfiles the row."""
    assert "document_updated" in EVENT_TYPES
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_events.py -k document_updated -v`
Expected: FAIL on the assertion.

- [ ] **Step 3: Add the value**

Add `"document_updated"` beside `"document_filed"` and `"blocks_edited"`, with a comment noting it is the metadata verb's journal row and carries no document text.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_events.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/events.py backend/tests/test_events.py
git commit -m "feat(events): admit the document_updated type"
```

---

### Task 7: The single-document metadata writer

**Files:**
- Modify: `backend/app/services/document_door.py`
- Modify: `backend/app/services/document_ingest.py` (add `DocumentUriConflict` beside `DocumentHashConflict` at :101)
- Test: `backend/tests/test_document_update.py` (create)

**Interfaces:**
- Consumes: `"document_updated"` (Task 6); the mapped `document_tags` and widened sweep (Task 5)
- Produces:
  - `document_door.update_document_metadata(session, *, document_id: UUID, title: str | None = None, uri: str | None = None, pinned: bool | None = None, tags: list[str] | None = None) -> None`
  - `document_door.set_document_tags(session, document_id: UUID, names: list[str]) -> None`
  - `document_ingest.DocumentUriConflict(ValueError)` with `.uri`, re-exported from `document_door`

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: §4.2 fixes the field set and the refusals

> **The name is `update_document_metadata`, not `update_document`.** `app/repositories/documents.py:198` already defines `update_document` with an unrelated signature. **`DocumentUriConflict` lives in `document_ingest`**, because `document_door` imports the repository and a repository raising a door class would close a cycle.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_a_document_can_be_renamed_moved_and_pinned(session):
    _, doc = await _file(session, "# T\n\npara", "notes/a.md")
    await update_document_metadata(session, document_id=doc, title="New",
                                   uri="notes/new.md", pinned=True)
    row = await _read(session, doc)
    assert (row["title"], row["uri"]) == ("New", "notes/new.md")
    assert row["pinned_at"] is not None


@pytest.mark.asyncio
async def test_an_absent_field_leaves_its_column_untouched(session):
    _, doc = await _file(session, "# T\n\npara", "notes/b.md")
    before = await _read(session, doc)
    await update_document_metadata(session, document_id=doc, pinned=True)
    after = await _read(session, doc)
    assert (after["title"], after["uri"]) == (before["title"], before["uri"])


@pytest.mark.asyncio
async def test_present_tags_replace_rather_than_merge(session):
    """A merge-only verb cannot remove a tag, which is why this replaces."""
    _, doc = await _file(session, "# T\n\npara", "notes/c.md")
    await update_document_metadata(session, document_id=doc, tags=["a", "b"])
    await update_document_metadata(session, document_id=doc, tags=["b"])
    assert await _tags(session, doc) == {"b"}


@pytest.mark.asyncio
async def test_pinned_false_clears_the_column(session):
    _, doc = await _file(session, "# T\n\npara", "notes/d.md")
    await update_document_metadata(session, document_id=doc, pinned=True)
    await update_document_metadata(session, document_id=doc, pinned=False)
    assert (await _read(session, doc))["pinned_at"] is None


@pytest.mark.asyncio
async def test_renaming_onto_an_occupied_path_refuses(session):
    _, first = await _file(session, "one", "notes/e.md")
    await _file(session, "two", "notes/f.md")
    with pytest.raises(DocumentUriConflict):
        await update_document_metadata(session, document_id=first,
                                       uri="notes/f.md")


@pytest.mark.asyncio
async def test_the_update_journals_one_event_carrying_no_document_text(session):
    _, doc = await _file(session, "# T\n\nsecret prose", "notes/g.md")
    await update_document_metadata(session, document_id=doc, title="New")
    row = await _latest_event(session, doc)
    assert row["event_type"] == "document_updated"
    assert "secret prose" not in json.dumps(row["payload"])
```

Write `_read`, `_tags` and `_latest_event` locally, and reuse the `_file`/`StubEmbedder` pattern from `tests/test_block_verbs.py:41-68`.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py -v`
Expected: FAIL on the import — `update_document_metadata` does not exist.

- [ ] **Step 3: Write the writer**

Only the named fields are written, so an absent field emits no assignment rather than writing NULL over a column. Every user value is bound; only the `now()` / `NULL` constants are interpolated.

```python
_PIN = {True: "now()", False: "NULL"}


async def update_document_metadata(session, *, document_id, title=None,
                                   uri=None, pinned=None, tags=None):
    """Write only the fields the caller named.

    `project` is deliberately not a field: moving a document between spaces is
    not a rename, and allowing it here would let one call cross the boundary
    the personal space rests on (spec section 4.2).
    """
    sets, params = [], {"id": str(document_id)}
    if title is not None:
        sets.append("title = CAST(:title AS text)")
        params["title"] = title
    if uri is not None:
        sets.append("uri = CAST(:uri AS text)")
        params["uri"] = uri
    if pinned is not None:
        sets.append(f"pinned_at = {_PIN[pinned]}")
    if sets:
        try:
            await session.execute(
                text(f"UPDATE documents SET {', '.join(sets)} "
                     "WHERE id = CAST(:id AS uuid)"),
                params,
            )
            await session.flush()
        except IntegrityError as exc:
            raise DocumentUriConflict(uri) from exc
    if tags is not None:
        await set_document_tags(session, document_id, tags)
    await record_event(
        session, event_type="document_updated", object_type="document",
        object_id=str(document_id),
        payload={"fields": sorted(
            k for k, v in {"title": title, "uri": uri,
                           "pinned": pinned, "tags": tags}.items()
            if v is not None)},
    )
```

Add `from sqlalchemy.exc import IntegrityError` and the `record_event` import to this module — neither is there today (imports are at `document_door.py:15-31`).

- [ ] **Step 4: Write `set_document_tags` through the existing tag path**

Resolve each name through the existing `get_or_create` so `tag_category(name)` and `TAG_NAME_MAX_LENGTH` apply on both doors, then replace the link set: delete this document's `document_tags` rows and insert the resolved ids. Do not insert into `tags` directly.

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_door.py backend/app/services/document_ingest.py backend/tests/test_document_update.py
git commit -m "feat(documents): add the metadata writer"
```

---

### Task 8: Both direction guards

**Files:**
- Modify: `backend/app/repositories/documents.py:159-196` (`upsert_by_uri`)
- Test: `backend/tests/test_document_door.py`

**Interfaces:**
- Consumes: `DocumentIsBlockFirst` (today at `document_door.py:157`; move it to `document_ingest.py` in this task)
- Produces: no new symbol. Changes `upsert_by_uri` to refuse a predicate-excluded conflict.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: §4.3 as amended fixes both guards and names the path each covers

> **Read this before writing code — the spec was wrong and was amended on 2026-09-07.**
>
> §4.3 originally said the refusal should ride the upsert *rather than* preceding it, and that a pre-statement check is check-then-act. Both halves are false. `ingest_document` (`document_ingest.py:296-320`) branches: an **existing** `(project, uri)` is written through `update_document` / `_UPDATE_DOCUMENT`, and **`upsert_by_uri` runs only when the resolve found nothing**. Removing the pre-check would therefore leave every plain `document_put` over a converted note unguarded — writing `properties` wholesale and stripping its blocks, the exact loss §4.3 exists to prevent. The pre-check is also not check-then-act for an existing row: it runs *after* `_LOCK_DOCUMENT_BY_URI ... FOR UPDATE` (`document_door.py:481`), and `_mutate` locks the same row by id, so they serialise.
>
> **Keep the existing pre-check exactly as it is. Add the predicate as a second guard, for the vacated-path race only.**

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_the_upsert_refuses_a_block_first_row_it_collides_with(session):
    """The vacated-path race: a put resolves nothing, inserts, and collides
    with a block-first row whose uri a concurrent rename just freed. The
    ON CONFLICT predicate is what refuses it -- the pre-check saw no row."""
    llm, doc = await _file(session, "# T\n\npara", "notes/race.md")
    await update_block(session, llm, block_id=await _first(session, doc),
                       text="converted")           # now block-first
    await session.commit()

    with pytest.raises(DocumentIsBlockFirst):
        await documents_repo.upsert_by_uri(
            session, document_id=new_id(), project="p", uri="notes/race.md",
            title="t", source_type="markdown", content_hash="deadbeef",
            content="clobber", properties={},
        )


@pytest.mark.asyncio
async def test_a_first_time_insert_is_not_mistaken_for_a_refusal(session):
    """A non-conflicting INSERT returns its row, so zero rows means the
    predicate excluded a conflict and nothing else."""
    resolved = await documents_repo.upsert_by_uri(
        session, document_id=new_id(), project="p", uri="notes/fresh.md",
        title="t", source_type="markdown", content_hash="cafe",
        content="body", properties={},
    )
    assert resolved is not None


@pytest.mark.asyncio
async def test_the_ordinary_put_over_a_converted_note_is_still_refused(session):
    """The pre-check, not the predicate, is what fires here -- and it is the
    one that fires in practice. This test is what fails if someone follows
    the unamended spec and deletes it."""
    llm, doc = await _file(session, "# T\n\npara", "notes/ordinary.md")
    await update_block(session, llm, block_id=await _first(session, doc),
                       text="converted")
    with pytest.raises(DocumentIsBlockFirst):
        await put_document(session, llm, project="p", uri="notes/ordinary.md",
                           content="clobber")
```

- [ ] **Step 2: Run to verify the first fails and the third passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_door.py -k "upsert_refuses or first_time_insert or ordinary_put" -v`
Expected: the first FAILS (no predicate yet), the second PASSES, and **the third PASSES against unchanged code** — it is the regression guard for the pre-check, not a test of new behaviour. Do not "fix" it.

- [ ] **Step 3: Add the predicate**

In `upsert_by_uri`'s `ON CONFLICT (project, uri) DO UPDATE SET ...`:

```sql
    WHERE documents.properties->>'ingest_direction' IS DISTINCT FROM 'blocks'
```

- [ ] **Step 4: Handle the zero-row outcome**

The statement ends `RETURNING id` with `.scalar_one()`; a predicate-excluded conflict returns **zero rows**, and `scalar_one()` raises `NoResultFound` before any rowcount is read. Switch to `.scalar_one_or_none()`:

```python
    resolved = (await session.execute(_UPSERT_BY_URI, params)).scalar_one_or_none()
    if resolved is None:
        # The conflict target existed and the predicate excluded it: the row
        # at this uri is block-first. A non-conflicting INSERT returns its own
        # row, so zero rows means this and nothing else.
        raise DocumentIsBlockFirst(
            f"the document at uri {uri!r} in project {project!r} is "
            "block-first: its content is owned by the block verbs."
        )
    return resolved
```

Move `DocumentIsBlockFirst` from `document_door.py:157` to `document_ingest.py` and re-export it from the door, so the repository does not import the door.

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_door.py tests/test_block_verbs.py tests/test_mcp.py -q`
Expected: PASS, all three new tests plus every pre-existing door, verb and MCP test.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/documents.py backend/app/services/ backend/tests/test_document_door.py
git commit -m "fix(documents): guard both put paths on direction"
```

---

### Task 9: The subtree rename

**Files:**
- Modify: `backend/app/services/document_door.py`
- Test: `backend/tests/test_document_update.py`

**Interfaces:**
- Consumes: `update_document_metadata` and `DocumentUriConflict` (Task 7)
- Produces: `document_door.rename_documents(session, *, project: str, uri_prefix: str, new_uri_prefix: str) -> int` returning the count rewritten

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §4.2 fixes the selection, the lock order and the link rewrite

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_a_subtree_rename_rewrites_every_descendant(session):
    for uri in ("notes/a", "notes/a/one.md", "notes/a/two.md"):
        await _file(session, "body", uri)
    assert await rename_documents(session, project="p", uri_prefix="notes/a",
                                  new_uri_prefix="notes/b") == 3
    assert await _uris(session, "p") == {
        "notes/b", "notes/b/one.md", "notes/b/two.md"}


@pytest.mark.asyncio
async def test_a_prefix_containing_a_wildcard_does_not_over_match(session):
    """`_` and `%` are LIKE metacharacters. A prefix of `notes/a_b` must not
    match `notes/axb`."""
    await _file(session, "body", "notes/a_b/one.md")
    await _file(session, "body", "notes/axb/two.md")
    await rename_documents(session, project="p", uri_prefix="notes/a_b",
                           new_uri_prefix="notes/z")
    assert "notes/axb/two.md" in await _uris(session, "p")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py -k rename -v`
Expected: FAIL on the import.

- [ ] **Step 3: Write it, avoiding LIKE metacharacters**

```python
async def rename_documents(session, *, project, uri_prefix, new_uri_prefix):
    """Rewrite a prefix across a subtree in one transaction.

    Rows are locked in id order -- the same lock `_mutate` takes -- so two
    concurrent subtree renames cannot deadlock against each other. The match
    avoids LIKE because `_` and `%` in a uri would over-match.
    """
    rows = (await session.execute(
        text("SELECT CAST(id AS text) AS id, uri FROM documents "
             "WHERE project = CAST(:p AS text) "
             "  AND (uri = CAST(:u AS text) "
             "       OR left(uri, length(CAST(:u AS text)) + 1) "
             "          = CAST(:u AS text) || '/') "
             "ORDER BY id FOR UPDATE"),
        {"p": project, "u": uri_prefix},
    )).mappings().all()

    for row in rows:
        await update_document_metadata(
            session, document_id=row["id"],
            uri=new_uri_prefix + row["uri"][len(uri_prefix):],
        )
    return len(rows)
```

Routing each row through `update_document_metadata` gives every renamed document its own `document_updated` row and the same `DocumentUriConflict` mapping, rather than a second write path.

- [ ] **Step 4: Rewrite the links**

After the documents are updated, rewrite `document_links.target_uri` by `target_document_id` for resolved links, then re-resolve stubs whose `target_uri` now matches a live document. Nothing writes `document_links` yet, so assert the statements run and affect zero rows rather than inventing fixture data.

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_door.py backend/tests/test_document_update.py
git commit -m "feat(documents): rename a document subtree"
```

---

### Task 10: The REST metadata routes

**Files:**
- Modify: `backend/app/api/routes/documents.py`
- Modify: `docs/two-door-parity.md`
- Test: `backend/tests/test_document_routes.py`, `backend/tests/test_api/test_rest_conformance.py`, `backend/tests/test_door_parity.py`

**Interfaces:**
- Consumes: `update_document_metadata`, `rename_documents`, `DocumentUriConflict` (Tasks 7 and 9)
- Produces: `PATCH /api/v1/documents/{document_id}` → 200; `POST /api/v1/documents/rename` → 200

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §4.2 fixes both routes, their bodies and their statuses, and cites `docs/api-rest-conventions.md` for PATCH over PUT

> **A new REST route trips `tests/test_door_parity.py:1481 test_every_rest_route_is_classified`**, not only the conformance map. Both routes are single-door until Task 11 lands the MCP twin, and a single-door row must state a reason of at least `_MIN_REASON_CHARS` = 80 characters (`test_door_parity.py:1565`).

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_patch_updates_one_document(client, auth_headers, filed):
    doc = await filed("notes/p.md", "body")
    response = await client.patch(f"/api/v1/documents/{doc}",
                                  json={"title": "New", "pinned": True},
                                  headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_patch_refuses_a_project_field(client, auth_headers, filed):
    """Moving a document between spaces is not a rename. The field is absent
    from the model and extra keys are forbidden, so this is 422 rather than a
    silently dropped key."""
    doc = await filed("notes/q.md", "body")
    assert (await client.patch(f"/api/v1/documents/{doc}",
                               json={"project": "other"},
                               headers=auth_headers)).status_code == 422


@pytest.mark.asyncio
async def test_a_rename_onto_an_occupied_path_answers_409(
    client, auth_headers, filed,
):
    first = await filed("notes/r.md", "one")
    await filed("notes/s.md", "two")
    assert (await client.patch(f"/api/v1/documents/{first}",
                               json={"uri": "notes/s.md"},
                               headers=auth_headers)).status_code == 409
```

The occupied path is the uri the test filed, not one read back off `GET /documents/{id}` — `DocumentBlocksResponse` has no `uri` field.

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_routes.py -k "patch or rename" -v`
Expected: FAIL with 405 — the routes do not exist.

- [ ] **Step 3: Add the models and routes**

```python
class DocumentPatchRequest(BaseModel):
    # `project` is deliberately absent: moving a document between spaces is
    # not a rename (spec section 4.2). extra="forbid" makes that a 422 rather
    # than a silently dropped key.
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    uri: str | None = None
    pinned: bool | None = None
    tags: list[str] | None = None


class DocumentRenameRequest(BaseModel):
    project: str
    uri_prefix: str
    new_uri_prefix: str
```

Add `ConfigDict` to the module's pydantic import (line 62 imports only `BaseModel, Field`). Both routes take `_user=Depends(require_auth)` like every sibling, and map `DocumentUriConflict` to 409.

- [ ] **Step 4: Classify both routes and add the conformance rows**

Add both to `docs/two-door-parity.md` as single-door with a reason of 80+ characters saying the MCP twin lands in Task 11, and add their rows to the conformance status map.

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_routes.py tests/test_api/test_rest_conformance.py tests/test_door_parity.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/ docs/two-door-parity.md
git commit -m "feat(documents): add the metadata rest routes"
```

---

### Task 11: The MCP `document_update` tool

**Files:**
- Modify: `backend/app/api/mcp/server.py`, `backend/app/api/mcp/scopes.py:46` (`CAPTURE_TOOLS`)
- Test: `backend/tests/test_mcp.py:20` (`EXPECTED_TOOLS`)

**Interfaces:**
- Consumes: `update_document_metadata`, `rename_documents`, `DocumentUriConflict` (Tasks 7 and 9)
- Produces: MCP tool `document_update`, `capture`-scoped, carrying both shapes as modes

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §4.2 states that MCP carries both shapes as modes of one tool

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_document_update_carries_both_shapes_as_modes(
    monkeypatch, session_factory, filed_doc,
):
    _patch(monkeypatch, session_factory)
    single = json.loads(await mcp_server.document_update(
        document_id=filed_doc, title="New"))
    assert single["status"] == "ok"

    subtree = json.loads(await mcp_server.document_update(
        project="p", uri_prefix="notes/a", new_uri_prefix="notes/b"))
    assert subtree["renamed"] == 3


def test_document_update_is_capture_scoped():
    """A key that can rename a document holds capture power, not read power."""
    from app.api.mcp.scopes import CAPTURE_TOOLS, READ_TOOLS
    assert "document_update" in CAPTURE_TOOLS
    assert "document_update" not in READ_TOOLS


@pytest.mark.asyncio
async def test_naming_neither_mode_refuses_with_an_envelope(
    monkeypatch, session_factory,
):
    _patch(monkeypatch, session_factory)
    envelope = json.loads(await mcp_server.document_update(title="New"))
    assert envelope["status"] == "invalid_mode"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -k document_update -v`
Expected: FAIL — no such tool.

- [ ] **Step 3: Add the tool**

One tool, two modes, dispatched on whether `document_id` or `uri_prefix` was given. Refuse a call carrying both, or neither, with an `invalid_mode` envelope rather than a tool error. Map `DocumentUriConflict` to a `uri_conflict` envelope.

- [ ] **Step 4: Register the scope and the expected-tools set**

Add `"document_update"` to `CAPTURE_TOOLS` (`scopes.py:46`) and to `EXPECTED_TOOLS` (`tests/test_mcp.py:20`). Both are pinned **sets**, not counts.

- [ ] **Step 5: Run the MCP suites**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py tests/test_mcp_auth.py tests/test_mcp_reindex.py -q`
Expected: PASS. `test_mcp_auth.py:404-421` and `test_mcp_reindex.py:46` derive their partitions from `CAPTURE_TOOLS`, so they follow automatically once the scope is registered.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp/server.py backend/app/api/mcp/scopes.py backend/tests/
git commit -m "feat(mcp): add the document_update tool"
```

---

### Task 12: The enumeration sweep

**Files:**
- Modify: `backend/app/services/prompt.py:689` area (`PROMPTS["agent_instructions"]`)
- Modify: `CLAUDE.md`, `docs/two-door-parity.md`, `docs/runbook-exposed-deployment.md:106-110`
- Test: `backend/tests/test_prompt_agent_instructions.py:27-30`, `backend/tests/test_door_parity.py`

**Interfaces:**
- Consumes: the registered tool (Task 11)
- Produces: nothing. This task exists because the counts and rosters live in prose that no earlier task's tests read.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the guards are enumerable and each names its own required edit

> **`test_prompt_agent_instructions.py:27-30` requires every tool name to appear inside `PROMPTS["agent_instructions"]`.** It is the guard most easily missed, because nothing about adding a tool suggests editing a prompt.
>
> **CLAUDE.md and two docstrings carry literal counts that no test reads** (`scopes.py:21`, `test_mcp_auth.py:395`), so a "do not update a count until a test names it" rule never fires for them — update them by inspection. `docs/runbook-exposed-deployment.md:106-110` already says "34 tools, 8 capture" and was **stale before this plan started**; correct it to the true figure while here.

- [ ] **Step 1: Run the guards to see what is red**

Run: `cd backend && .venv/bin/python -m pytest tests/test_prompt_agent_instructions.py tests/test_door_parity.py -q`
Expected: FAIL, naming `document_update` as absent from the agent roster and the parity table.

- [ ] **Step 2: Add the tool to the agent instructions**

Add a `- **document_update** — rename, move, pin or re-tag a document.` line beside the existing `- **document_put**` entry at `prompt.py:689`.

- [ ] **Step 3: Flip both new REST rows to two-door**

Task 10 filed `PATCH /documents/{document_id}` and `POST /documents/rename` as single-door with a reason. Both now have an MCP twin, so change them to two-door and remove the exemption reason — `test_a_two_door_surface_states_no_exemption` (`test_door_parity.py:1611`) fails if a reason is left behind.

- [ ] **Step 4: Correct the prose counts**

Derive the true totals from the code rather than from this plan: `len(EXPECTED_TOOLS)` for the catalogue and `len(CAPTURE_TOOLS)` for the writers. Update `CLAUDE.md`'s MCP section, the docstrings at `scopes.py:21` and `test_mcp_auth.py:395`, and the stale figures in `docs/runbook-exposed-deployment.md:106-110`.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: PASS. This is the only step that catches every enumeration guard, which is why it is the whole suite.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/prompt.py backend/tests/ CLAUDE.md docs/
git commit -m "docs(mcp): record the document_update tool"
```

---

## After the lanes land

- **Run `./scripts/gate.sh`.** `--full` cannot complete on this host; run the legs individually per `CLAUDE.md`.
- **Add a changelog entry.** Check `python3 scripts/next_version.py plan` **after `git fetch`** — this repo's tags are written by CI, so a stale local tag list makes that command return a plausible wrong answer, and the release guard matches `## vN.N.N` and will not accept "Unreleased".
- **These lanes change the running artifact**, so the redeploy rule applies once the owner clears the cutover.

## What this plan does NOT do

`block_update`'s `source` mode and the retirement of `promote` (spec §4.1) are **not** in these lanes. §12 places them in increment 3, the editor increment, because the mode exists to serve per-block CodeMirror and has no caller until then.

**One question left open for Task 9's implementer to raise, not decide:** a single-document `uri` change does not rewrite `document_links`, while `rename_documents` does. §4.2 binds the link rewrite to the subtree verb only. Nothing writes `document_links` yet, so the stakes are currently zero — but the asymmetry should be settled before the links increment, not after.
