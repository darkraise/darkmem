# Personal Notes Foundation (increment 1, lanes 1c-1e) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Give the block verbs a real compare-and-set, widen the tag sweep so a note-only tag survives the hour, and ship `document_update` so a converted note can be renamed, moved and pinned.

**Architecture:** Three lanes. **1c** threads an `expected_hash` precondition through `_mutate` and all four block verbs, serves `content_hash` on both doors' block reads, and serialises the editor's client-side mutations so a burst cannot 409 against itself. **1d** widens `prune_orphans` and the tag histogram to consider `document_tags`, which must land before any code writes such a row. **1e** adds the metadata verb in two shapes (`PATCH` for one document, `POST .../rename` for a subtree) plus the MCP tool, and moves the block-first direction refusal onto the upsert predicate so it cannot be raced.

**Tech Stack:** FastAPI, SQLAlchemy async + raw SQL with asyncpg CASTs, Postgres 16, `mcp==2.1.1` (`MCPServer`), React + TanStack Router, vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-personal-notes-workspace-design.md` (1c is §5, 1d is §7, 1e is §4.2 and §4.3; the sequencing and its two ordering constraints are §12)

## Global Constraints

- **Lane order is forced: 1d must land before 1e.** The first `document_tags` row `document_update` writes is deleted within the hour by `tag_orphan_cleanup` if `prune_orphans` has not been widened first. Tasks 5 precedes tasks 7-9 for this reason and no other.
- **Lane 1c is independent of the 1b baseline** and may proceed in parallel with 1d/1e. It touches no schema.
- **No new schema.** Every column and table these lanes use was created by the 1b baseline regeneration (`document_tags`, `documents.pinned_at`, `projects.kind`). If a task finds one missing, stop — the branch is not on the regenerated baseline.
- **Reuse `DocumentHashConflict`** (`app/services/document_ingest.py`), which already carries `expected_hash` / `current_hash` and already has a 409 mapping on REST and a `hash_conflict` envelope on MCP. Do not define a second conflict exception.
- **`EVENT_TYPES` is widened taxonomy-first**: the value lands in the vocabulary in its own commit, before any code emits it.
- **Raw-SQL params need CASTs** (`CAST(:id AS uuid)`, `CAST(:hash AS text)`), or asyncpg raises `IndeterminateDatatypeError`.
- **One new MCP tool trips several full-list guards.** `document_update` moves the catalogue from 38 tools to 39 and the `capture` scope from 12 writers to 13. Both counts appear in `CLAUDE.md` and in test assertions; the task that adds the tool updates every one of them.
- **Commit messages:** `<type>(<scope>): <subject>`, subject <= 50 chars, imperative, no period.

---

## File Structure

| File | Responsibility | Lane |
|---|---|---|
| `backend/app/services/block_verbs.py` | `_DOC_META` gains `content_hash`; `_mutate` and the four verbs gain `expected_hash` | 1c |
| `backend/app/api/routes/documents.py` | `expected_hash` on four block routes; `content_hash` on `DocumentBlocksResponse`; new `PATCH` and `rename` routes | 1c, 1e |
| `backend/app/api/mcp/server.py` | `expected_hash` on four block tools; `include_hash` on `document_get`; new `document_update` tool | 1c, 1e |
| `frontend/src/features/documents/components/block-editor.tsx` | serialised mutation queue | 1c |
| `backend/app/repositories/relational.py` | `prune_orphans` and `get_with_counts` widen to `document_tags` | 1d |
| `backend/app/services/analytics.py` | tag histogram widens to `document_tags` | 1d |
| `backend/app/services/events.py` | `document_updated` joins `EVENT_TYPES` | 1e |
| `backend/app/repositories/documents.py` | the direction predicate on `upsert_by_uri`; the existing `update_document` is untouched | 1e |
| `backend/app/services/document_door.py` | `update_document_metadata` / `rename_documents` service verbs, `DocumentUriConflict` | 1e |

---

### Task 1: Compare-and-set in the block verbs

**Files:**
- Modify: `backend/app/services/block_verbs.py:81-85` (`_DOC_META`), `:150-175` (`_mutate`), `:291`, `:318`, `:356`, `:403` (the four verb signatures)
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: `DocumentHashConflict(document_id=, expected_hash=, current_hash=)` from `app.services.document_ingest`
- Produces: every verb gains a keyword-only `expected_hash: str | None = None`. Signatures after this task:
  - `update_block(session, llm, *, block_id: str, text: str, type: str | None = None, properties: dict | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `insert_block(session, llm, *, document_id: str, type: str, text: str, parent_id: str | None = None, after_block_id: str | None = None, properties: dict | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `move_block(session, llm, *, block_id: str, new_parent_id: str | None = None, after_block_id: str | None = None, expected_hash: str | None = None) -> BlockWriteResult`
  - `delete_block(session, llm, *, block_id: str, expected_hash: str | None = None) -> BlockWriteResult`

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: the spec fixes the design (§5 says the compare goes after the existing lock, which is already the transaction's first statement, so it is CAS-equivalent with no restructuring)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_block_verbs.py`:

```python
import pytest
from app.services.block_verbs import (
    delete_block, insert_block, move_block, update_block,
)
from app.services.document_ingest import DocumentHashConflict


@pytest.mark.asyncio
async def test_a_stale_expected_hash_refuses_every_verb(session, llm, filed_note):
    """All four verbs rewrite content_hash, so all four take the precondition.

    The spec is explicit that this is four verbs and not two: insert and move
    rewrite the document's content exactly as update does, so a caller that
    preconditions only its updates still clobbers a concurrent insert.
    """
    doc_id, block_id = filed_note
    stale = "0" * 64

    with pytest.raises(DocumentHashConflict):
        await update_block(session, llm, block_id=block_id, text="x",
                           expected_hash=stale)
    with pytest.raises(DocumentHashConflict):
        await insert_block(session, llm, document_id=doc_id, type="paragraph",
                           text="x", expected_hash=stale)
    with pytest.raises(DocumentHashConflict):
        await move_block(session, llm, block_id=block_id, expected_hash=stale)
    with pytest.raises(DocumentHashConflict):
        await delete_block(session, llm, block_id=block_id, expected_hash=stale)


@pytest.mark.asyncio
async def test_the_conflict_names_the_hash_that_actually_holds(
    session, llm, filed_note, current_hash_of,
):
    doc_id, block_id = filed_note
    live = await current_hash_of(doc_id)

    with pytest.raises(DocumentHashConflict) as caught:
        await update_block(session, llm, block_id=block_id, text="x",
                           expected_hash="0" * 64)

    assert caught.value.expected_hash == "0" * 64
    assert caught.value.current_hash == live


@pytest.mark.asyncio
async def test_a_matching_expected_hash_applies_the_edit(
    session, llm, filed_note, current_hash_of, text_of,
):
    doc_id, block_id = filed_note
    await update_block(session, llm, block_id=block_id, text="edited",
                       expected_hash=await current_hash_of(doc_id))
    assert await text_of(block_id) == "edited"


@pytest.mark.asyncio
async def test_omitting_the_hash_stays_last_writer_wins(
    session, llm, filed_note, text_of,
):
    """The precondition is opt-in. Every shipped caller omits it today, and
    making it mandatory would break them all at once."""
    _, block_id = filed_note
    await update_block(session, llm, block_id=block_id, text="edited")
    assert await text_of(block_id) == "edited"
```

Add these fixtures to the same file if they are not already present:

```python
import pytest_asyncio
from sqlalchemy import text as sa_text


@pytest_asyncio.fixture
async def current_hash_of(session):
    async def read(document_id: str) -> str:
        row = (await session.execute(
            sa_text("SELECT content_hash FROM documents "
                    "WHERE id = CAST(:id AS uuid)"),
            {"id": document_id},
        )).scalar_one()
        return row
    return read


@pytest_asyncio.fixture
async def text_of(session):
    async def read(block_id: str) -> str:
        return (await session.execute(
            sa_text("SELECT text FROM blocks WHERE id = CAST(:id AS uuid)"),
            {"id": block_id},
        )).scalar_one()
    return read
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_block_verbs.py -k expected_hash -v`
Expected: FAIL with `TypeError: update_block() got an unexpected keyword argument 'expected_hash'`. If instead they fail on a missing fixture, fix the fixture and re-run until the failure is the missing keyword — a fixture error proves nothing about the feature.

- [ ] **Step 3: Make `_DOC_META` read the hash**

The compare has nothing to read otherwise. In `backend/app/services/block_verbs.py`:

```python
_DOC_META = text(
    "SELECT project, content, content_hash, "
    "       properties->>'ingest_direction' AS direction, "
    "       properties->>'frontmatter' AS frontmatter "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)
```

- [ ] **Step 4: Compare inside `_mutate`, after the lock**

Change the signature and add the compare immediately after the `meta is None` guard:

```python
async def _mutate(session, llm, *, document_id, apply, touched_embed, verb,
                  block_id, expected_hash=None):
    """Lock, load, mutate in memory, serialise, write, journal, embed.

    Review M-3: the lock is the first statement, before anything is read off
    the row. The whole pass is a read-modify-write that crosses several
    awaits, and `put_document` takes the same lock, so the two serialise
    instead of interleaving into a tree whose blocks were stripped underneath
    it.

    The compare sits after that lock, which is what makes it a compare-and-set
    rather than a check-then-act: no writer can move `content_hash` between
    the read and the write, because they are inside one held row lock.
    """
    await session.execute(_LOCK_DOCUMENT, {"id": document_id})

    meta = (await session.execute(_DOC_META, {"id": document_id})).mappings().first()
    if meta is None:
        raise BlockTargetUnresolved(f"no document with id {document_id}")
    if expected_hash is not None and meta["content_hash"] != expected_hash:
        raise DocumentHashConflict(
            document_id=document_id,
            expected_hash=expected_hash,
            current_hash=meta["content_hash"],
        )
```

Add the import at the top of the module:

```python
from app.services.document_ingest import DocumentHashConflict
```

- [ ] **Step 5: Thread the parameter through all four verbs**

Each verb gains the keyword-only parameter and forwards it. `update_block`:

```python
async def update_block(
    session: AsyncSession, llm, *, block_id: str,
    text: str, type: str | None = None, properties: dict | None = None,
    expected_hash: str | None = None,
) -> BlockWriteResult:
```

and its `_mutate(...)` call gains `expected_hash=expected_hash`. Repeat verbatim for `insert_block`, `move_block` and `delete_block` — each adds the same keyword-only parameter with the same default and forwards it on its own `_mutate` call. Change nothing else in the four bodies.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_block_verbs.py -v`
Expected: PASS, including every pre-existing test in the file — they all omit `expected_hash` and must keep working unchanged.

- [ ] **Step 7: Prove the compare is load-bearing**

Comment out the two-line `if expected_hash is not None ...` guard, re-run, and confirm the three refusal tests fail. Restore it. A precondition that passes with the check removed is testing nothing.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(documents): precondition the block verbs on a hash"
```

---

### Task 2: Serve and accept the hash on REST

**Files:**
- Modify: `backend/app/api/routes/documents.py:367-374` (`DocumentBlocksResponse`), `:768-805` (the blocks read), and the four block-verb routes
- Test: `backend/tests/test_documents_routes.py`, `backend/tests/test_rest_conformance.py`

**Interfaces:**
- Consumes: `expected_hash` on the four verbs from Task 1
- Produces: `DocumentBlocksResponse.content_hash: str | None`; `expected_hash` as a body field on the update/insert/move routes and a **query parameter** on the delete route

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: §5 fixes both the field placement and the query-parameter exception for DELETE

- [ ] **Step 1: Write the failing test**

```python
def test_the_blocks_read_serves_the_documents_hash(client, filed_note):
    doc_id, _ = filed_note
    body = client.get(f"/api/v1/documents/{doc_id}").json()
    assert body["content_hash"], "a caller cannot precondition its first edit"


def test_a_stale_hash_answers_409_naming_both_hashes(client, filed_note):
    doc_id, block_id = filed_note
    response = client.patch(
        f"/api/v1/documents/blocks/{block_id}",
        json={"text": "x", "expected_hash": "0" * 64},
    )
    assert response.status_code == 409
    assert "0" * 64 in response.json()["detail"]


def test_delete_takes_the_hash_as_a_query_parameter(client, filed_note):
    """DELETE carries no body in this API's conventions, so the precondition
    rides the query string. A body field here would be silently ignored."""
    _, block_id = filed_note
    response = client.delete(
        f"/api/v1/documents/blocks/{block_id}?expected_hash={'0' * 64}"
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_documents_routes.py -k hash -v`
Expected: FAIL — the first on `KeyError: 'content_hash'`, the other two on `200` instead of `409`.

- [ ] **Step 3: Add the field to the response model**

```python
class DocumentBlocksResponse(BaseModel):
    document_id: str
    blocks: list[BlockRowModel]
    # The verbatim filed source, which blocks.char_span indexes into. Present
    # only when the request opted in with include_content -- absent by default
    # so no existing reader pays for a potentially megabyte field (spec §5.2).
    content: str | None = None
    # Served unconditionally: it is one short string, and without it a caller
    # cannot precondition its first edit at all (spec §5).
    content_hash: str | None = None
    horizon: bool = True
```

Populate it in the `DocumentBlocksResponse(...)` construction at `:804` by selecting `content_hash` alongside the fields the read already loads.

- [ ] **Step 4: Accept the precondition on the four routes**

Add `expected_hash: str | None = None` to the request body models for update, insert and move, and forward it to the verb call. For delete, add it as a query parameter:

```python
@router.delete("/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_block_route(
    block_id: str,
    expected_hash: str | None = Query(
        None,
        description="Refuse unless the document's content_hash still matches.",
    ),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> None:
    ...
    await delete_block(session, llm, block_id=block_id,
                       expected_hash=expected_hash)
```

- [ ] **Step 5: Map the conflict to 409**

Wrap each of the four route bodies, reusing the existing handler's wording so the two conflict sites read identically:

```python
    except DocumentHashConflict as exc:
        # 409, not 422: the caller made no mistake -- it lost a race, or the
        # document moved since it last read it. The detail names both hashes
        # so the caller can re-read and retry without a second round trip.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        ) from exc
```

- [ ] **Step 6: Update the conformance status map**

`tests/test_rest_conformance.py` pins a per-route status map. The four block routes gain 409 as a documented outcome. Run the suite and add exactly the rows it names as missing — do not guess the keys.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_documents_routes.py tests/test_rest_conformance.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_routes.py backend/tests/test_rest_conformance.py
git commit -m "feat(documents): precondition the block routes"
```

---

### Task 3: Serve and accept the hash on MCP

**Files:**
- Modify: `backend/app/api/mcp/server.py:756-810` (`document_get`), `:1950`, `:1989`, `:2032`, `:2068` (the four block tools)
- Test: `backend/tests/test_mcp.py`
- Modify: `docs/two-door-parity.md`

**Interfaces:**
- Consumes: `expected_hash` on the four verbs from Task 1
- Produces: `document_get(..., include_hash: bool = False)` returning `{content_hash, blocks}` when set; `expected_hash: str | None = None` on all four block tools

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §5 decides the shape explicitly — an array cannot carry a hash, so it is a flag returning an object, the same shape `include_content` already established

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_document_get_answers_an_object_when_include_hash_is_set(mcp):
    """An array cannot carry a hash. This is the same object-under-a-flag
    shape include_content already uses, not a new convention."""
    bare = json.loads(await mcp.call("document_get", {"document_id": DOC}))
    assert isinstance(bare, list)

    with_hash = json.loads(await mcp.call(
        "document_get", {"document_id": DOC, "include_hash": True}))
    assert set(with_hash) == {"content_hash", "blocks"}
    assert with_hash["blocks"] == bare


@pytest.mark.asyncio
async def test_a_stale_hash_answers_a_conflict_envelope_not_a_tool_error(mcp):
    envelope = json.loads(await mcp.call(
        "block_update", {"block_id": BLOCK, "text": "x",
                         "expected_hash": "0" * 64}))
    assert envelope["status"] == "hash_conflict"
    assert envelope["expected_hash"] == "0" * 64
    assert envelope["current_hash"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -k "include_hash or conflict_envelope" -v`
Expected: FAIL — `include_hash` is an unexpected argument, and `block_update` raises rather than returning an envelope.

- [ ] **Step 3: Add `include_hash` to `document_get`**

Mirror the `include_content` branch exactly. When both flags are set the object carries `content`, `content_hash` and `blocks`; when neither is set the bare array is returned unchanged, so no existing caller's parse breaks.

- [ ] **Step 4: Add `expected_hash` to the four block tools**

Each tool gains `expected_hash: str | None = None`, forwards it, and catches the conflict into the established envelope:

```python
        except DocumentHashConflict as exc:
            # A structured refusal rather than a tool error: the caller can
            # machine-read this, re-read the document and retry. Its REST twin
            # is a 409 carrying the same two hashes.
            await session.rollback()
            return json.dumps({
                "status": "hash_conflict",
                "expected_hash": exc.expected_hash,
                "current_hash": exc.current_hash,
            })
```

- [ ] **Step 5: Record the flag in the parity table**

`docs/two-door-parity.md` records `include_content` as an object-under-a-flag. Add `include_hash` beside it, stating that it is the same shape and why the array could not carry the field.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -q`
Expected: PASS. The tool count is unchanged by this task — no tool was added, so no catalogue guard should move. If one does, stop: it means a tool was added by accident.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py docs/two-door-parity.md
git commit -m "feat(mcp): precondition the block tools on a hash"
```

---

### Task 4: Serialise the editor's mutations

**Files:**
- Create: `frontend/src/features/documents/lib/mutation-queue.ts`
- Modify: `frontend/src/features/documents/components/block-editor.tsx`
- Test: `frontend/src/features/documents/__tests__/mutation-queue.test.ts`

**Interfaces:**
- Consumes: `content_hash` from the REST blocks read (Task 2)
- Produces: `createMutationQueue(): { enqueue<T>(fn: (hash: string) => Promise<{result: T, content_hash: string}>): Promise<T> }` — runs one mutation at a time and feeds each the hash the previous one returned

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5
**Approach:** inline - skip 3: §5 names the requirement (a serialised client queue) and the failure it prevents (a synchronous commit-then-insert carrying a stale hash and 409ing against its own predecessor)

- [ ] **Step 1: Write the failing test**

```typescript
import { describe, expect, it } from 'vitest'
import { createMutationQueue } from '../lib/mutation-queue'

describe('the mutation queue', () => {
  it('feeds each mutation the hash the previous one returned', async () => {
    const queue = createMutationQueue('hash-0')
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
    const queue = createMutationQueue('hash-0')
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
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/mutation-queue.test.ts`
Expected: FAIL — the module does not exist.

- [ ] **Step 3: Write the queue**

```typescript
type Mutation<T> = (hash: string) => Promise<{ result: T; content_hash: string }>

export function createMutationQueue(initialHash: string) {
  let hash = initialHash
  // The tail of the chain. Each enqueue appends to it, so mutations run in
  // call order and each one sees the hash its predecessor produced. Without
  // this the editor's synchronous commit-then-insert sends both with the same
  // hash and the second 409s against the first (spec section 5).
  let tail: Promise<unknown> = Promise.resolve()

  function enqueue<T>(fn: Mutation<T>): Promise<T> {
    const run = tail.then(async () => {
      const { result, content_hash } = await fn(hash)
      hash = content_hash
      return result
    })
    // Keep the chain alive after a rejection, or one failed mutation would
    // wedge every later one.
    tail = run.catch(() => undefined)
    return run as Promise<T>
  }

  return { enqueue }
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/mutation-queue.test.ts`
Expected: PASS.

- [ ] **Step 5: Route the editor's writes through it**

In `block-editor.tsx`, construct the queue from the `content_hash` the blocks read returned and send every block mutation through `enqueue`, passing the hash as `expected_hash` and returning the response's new `content_hash`. Do not change what the editor sends otherwise.

- [ ] **Step 6: Run the frontend suite**

Run: `cd frontend && npm run typecheck && npm test`
Expected: PASS, all files.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/documents
git commit -m "feat(documents): serialise the editor's mutations"
```

---

### Task 5: Widen the tag sweep and the histogram

**Files:**
- Modify: `backend/app/repositories/relational.py:241` (`get_with_counts`), `:249-267` (`prune_orphans`)
- Modify: `backend/app/services/analytics.py:267-270`
- Test: `backend/tests/test_tags.py`

**Interfaces:**
- Consumes: the `document_tags` table from the 1b baseline
- Produces: nothing other tasks call. **Tasks 7-9 depend on this task having landed**, not on an interface it exports.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 3 = 4
**Approach:** inline - skip 3: §7 states both call sites and the widening exactly

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_a_note_only_tag_survives_the_sweep(session, tagged_document):
    """tag_orphan_cleanup runs hourly. Before this widening it deleted every
    tag with no memory_tags row, so a tag carried only by a note -- and its
    document_tags links, under the cascade -- vanished within the hour."""
    repo = RelationalRepository(session)
    await repo.prune_orphans()

    survivors = {t.name for t in await repo.list_all()}
    assert "note-only" in survivors


@pytest.mark.asyncio
async def test_the_histogram_counts_a_documents_tag(session, tagged_document):
    counts = dict(
        (tag.name, n) for tag, n in
        await RelationalRepository(session).get_with_counts()
    )
    assert counts["note-only"] == 1


@pytest.mark.asyncio
async def test_a_tag_with_no_reference_of_either_kind_is_still_swept(
    session, orphan_tag,
):
    """The widening must not turn the sweep off."""
    repo = RelationalRepository(session)
    assert await repo.prune_orphans() >= 1
    assert "abandoned" not in {t.name for t in await repo.list_all()}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_tags.py -k "note_only or histogram" -v`
Expected: FAIL — the tag is deleted by the sweep, and the histogram reports 0.

- [ ] **Step 3: Widen `prune_orphans`**

```python
    async def prune_orphans(self) -> int:
        """Delete tags nothing references any more, returning the count.

        Tags are linked from two tables since the notes workspace landed:
        ``memory_tags`` and ``document_tags``, both ON DELETE CASCADE. Checking
        only the first deletes a tag carried by a note alone -- and its links
        with it under the cascade -- within the hour ``tag_orphan_cleanup``
        next runs. Mirrors ``PostgresGraphRepository.prune_orphan_entities``
        for the graph."""
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

- [ ] **Step 4: Widen both counts**

`get_with_counts` and the `analytics.py` histogram each count `memory_tags` rows only. Both become the sum of the two link tables. Use a correlated subquery per table rather than joining both — joining two one-to-many tables multiplies the rows and inflates every count:

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

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_tags.py -q`
Expected: PASS, including the third test — the sweep must still delete a genuinely unreferenced tag.

- [ ] **Step 6: Prove the join was not used**

Create a tag carried by two memories and two documents and assert its count is 4, not 8. A join-based widening passes the single-reference tests and fails this one.

- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/relational.py backend/app/services/analytics.py backend/tests/test_tags.py
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

Add `"document_updated"` beside `"document_filed"` and `"blocks_edited"` in `EVENT_TYPES`, with a comment noting it is the metadata verb's journal row and carries no document text.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_events.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/events.py backend/tests/test_events.py
git commit -m "feat(events): admit the document_updated type"
```

---

### Task 7: The metadata and rename writers

**Files:**
- Modify: `backend/app/repositories/documents.py:100-130` (`_UPDATE_DOCUMENT` area), `:159-197` (`upsert_by_uri`)
- Modify: `backend/app/services/document_door.py`
- Test: `backend/tests/test_document_update.py` (create)

**Interfaces:**
- Consumes: `"document_updated"` from Task 6; the widened sweep from Task 5
- Produces:
  - `document_door.update_document_metadata(session, *, document_id: UUID, title: str | None = None, uri: str | None = None, pinned: bool | None = None, tags: list[str] | None = None) -> DocumentUpdateResult`
  - `document_door.rename_documents(session, *, project: str, uri_prefix: str, new_uri_prefix: str) -> int` (returns rows rewritten)
  - `class DocumentUriConflict(ValueError)` with `.uri`
  - `document_door.set_document_tags(session, document_id: UUID, names: list[str]) -> None`, which writes through the existing `get_or_create` tag path

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: §4.2 fixes the field set, the lock order and the refusals; §4.3 fixes the direction predicate and says explicitly why it must ride the upsert

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_a_document_can_be_renamed_moved_and_pinned(session, filed_note):
    doc_id, _ = filed_note
    await update_document_metadata(session, document_id=doc_id, title="New",
                          uri="notes/new.md", pinned=True)
    row = await read_document(session, doc_id)
    assert (row.title, row.uri) == ("New", "notes/new.md")
    assert row.pinned_at is not None


@pytest.mark.asyncio
async def test_an_absent_field_leaves_its_column_untouched(session, filed_note):
    doc_id, _ = filed_note
    before = await read_document(session, doc_id)
    await update_document_metadata(session, document_id=doc_id, pinned=True)
    after = await read_document(session, doc_id)
    assert after.title == before.title and after.uri == before.uri


@pytest.mark.asyncio
async def test_present_tags_replace_rather_than_merge(session, filed_note):
    """A merge-only verb cannot remove a tag, which is why this replaces."""
    doc_id, _ = filed_note
    await update_document_metadata(session, document_id=doc_id, tags=["a", "b"])
    await update_document_metadata(session, document_id=doc_id, tags=["b"])
    assert await tags_of(session, doc_id) == {"b"}


@pytest.mark.asyncio
async def test_pinned_false_clears_the_column(session, filed_note):
    doc_id, _ = filed_note
    await update_document_metadata(session, document_id=doc_id, pinned=True)
    await update_document_metadata(session, document_id=doc_id, pinned=False)
    assert (await read_document(session, doc_id)).pinned_at is None


@pytest.mark.asyncio
async def test_renaming_onto_an_occupied_path_refuses(session, two_notes):
    first, second = two_notes
    with pytest.raises(DocumentUriConflict):
        await update_document_metadata(session, document_id=first,
                              uri=(await read_document(session, second)).uri)


@pytest.mark.asyncio
async def test_a_subtree_rename_rewrites_every_descendant(session, subtree):
    rewritten = await rename_documents(
        session, project="notes", uri_prefix="notes/a",
        new_uri_prefix="notes/b",
    )
    assert rewritten == 3          # the prefix itself and two descendants
    assert await uris_in(session, "notes") == {
        "notes/b", "notes/b/one.md", "notes/b/two.md",
    }


@pytest.mark.asyncio
async def test_a_put_at_a_vacated_path_cannot_strip_a_block_first_row(
    session, filed_note,
):
    """Spec section 4.3. The direction refusal rides the upsert predicate, so a
    put racing a rename fires against the renamed row and is refused rather
    than writing properties wholesale and erasing its blocks."""
    doc_id, _ = filed_note
    with pytest.raises(DocumentIsBlockFirst):
        await put_document(session, project="notes",
                           uri=(await read_document(session, doc_id)).uri,
                           content="clobber")
    assert await block_count(session, doc_id) > 0


@pytest.mark.asyncio
async def test_the_update_journals_one_event_carrying_no_document_text(
    session, filed_note,
):
    doc_id, _ = filed_note
    await update_document_metadata(session, document_id=doc_id, title="New")
    row = await latest_event(session, object_id=doc_id)
    assert row["event_type"] == "document_updated"
    assert "clobber" not in json.dumps(row["payload"])
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py -v`
Expected: FAIL on the import — `update_document_metadata` and `rename_documents` do not exist.

- [ ] **Step 3: Write the single-document writer**

A partial update: build the SET list from the fields that were actually passed, so an absent field emits no assignment at all rather than writing NULL over a column.

```python
_PIN = {True: "now()", False: "NULL"}


async def update_document_metadata(session, *, document_id, title=None, uri=None,
                          pinned=None, tags=None):
    """Write only the fields the caller named.

    `project` is deliberately not a field: moving a document between spaces is
    not a rename, and allowing it here would let one call cross the boundary
    the personal space rests on (spec section 4.2).
    """
    sets, params = [], {"id": str(document_id)}
    if title is not None:
        sets.append("title = CAST(:title AS text)"); params["title"] = title
    if uri is not None:
        sets.append("uri = CAST(:uri AS text)"); params["uri"] = uri
    if pinned is not None:
        sets.append(f"pinned_at = {_PIN[pinned]}")
    if sets:
        try:
            await session.execute(
                text(f"UPDATE documents SET {', '.join(sets)} "
                     "WHERE id = CAST(:id AS uuid)"),
                params,
            )
        except IntegrityError as exc:
            await session.rollback()
            raise DocumentUriConflict(uri) from exc
    if tags is not None:
        await set_document_tags(session, document_id, tags)
    await record_event(session, event_type="document_updated",
                       object_type="document", object_id=str(document_id),
                       payload={"fields": sorted(
                           k for k, v in
                           {"title": title, "uri": uri,
                            "pinned": pinned, "tags": tags}.items()
                           if v is not None)})
```

Write `set_document_tags` to go through the existing `get_or_create` writer path so `tag_category(name)` and `TAG_NAME_MAX_LENGTH` apply — do not insert into `tags` directly.

- [ ] **Step 4: Write the subtree rename with a deterministic lock order**

```python
async def rename_documents(session, *, project, uri_prefix, new_uri_prefix):
    """Rewrite a prefix across a subtree in one transaction.

    Rows are locked in id order -- the same lock `_mutate` takes -- so two
    concurrent subtree renames cannot deadlock against each other.
    """
    ids = (await session.execute(
        text("SELECT id FROM documents "
             "WHERE project = CAST(:p AS text) "
             "  AND (uri = CAST(:u AS text) OR uri LIKE CAST(:u AS text) || '/%') "
             "ORDER BY id FOR UPDATE"),
        {"p": project, "u": uri_prefix},
    )).scalars().all()
    ...
```

Then `UPDATE documents`, then `document_links`: rewrite `target_uri` by `target_document_id` for resolved links, and re-resolve stubs whose `target_uri` now matches a live document. Journal one `document_updated` row per renamed document.

- [ ] **Step 5: Move the direction refusal onto the upsert**

In `upsert_by_uri`, add the predicate to the conflict clause and treat a zero rowcount as the refusal:

```sql
    ON CONFLICT (project, uri) DO UPDATE SET ...
    WHERE documents.properties->>'ingest_direction' IS DISTINCT FROM 'blocks'
```

```python
    if result.rowcount == 0:
        raise DocumentIsBlockFirst(uri)
```

Remove the pre-statement direction check this replaces. A check before the statement is check-then-act, which is the shape the race is made of — leaving both is not belt-and-braces, it reintroduces the window.

- [ ] **Step 6: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_document_update.py tests/test_document_door.py -q`
Expected: PASS, including every pre-existing document-door test.

- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/documents.py backend/app/services/document_door.py backend/tests/test_document_update.py
git commit -m "feat(documents): add the metadata and rename verbs"
```

---

### Task 8: The REST metadata routes

**Files:**
- Modify: `backend/app/api/routes/documents.py`
- Test: `backend/tests/test_documents_routes.py`, `backend/tests/test_rest_conformance.py`

**Interfaces:**
- Consumes: `update_document_metadata`, `rename_documents`, `DocumentUriConflict` from Task 7
- Produces: `PATCH /api/v1/documents/{document_id}` → 200; `POST /api/v1/documents/rename` → 200

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §4.2 fixes both routes, their bodies and their statuses, and cites `docs/api-rest-conventions.md` for PATCH over PUT

- [ ] **Step 1: Write the failing test**

```python
def test_patch_updates_one_document(client, filed_note):
    doc_id, _ = filed_note
    response = client.patch(f"/api/v1/documents/{doc_id}",
                            json={"title": "New", "pinned": True})
    assert response.status_code == 200


def test_patch_refuses_a_project_field(client, filed_note):
    """Moving a document between spaces is not a rename. The field is absent
    from the model, so an extra key is rejected rather than ignored."""
    doc_id, _ = filed_note
    assert client.patch(f"/api/v1/documents/{doc_id}",
                        json={"project": "other"}).status_code == 422


def test_a_rename_onto_an_occupied_path_answers_409(client, two_notes):
    first, second = two_notes
    taken = client.get(f"/api/v1/documents/{second}").json()["uri"]
    assert client.patch(f"/api/v1/documents/{first}",
                        json={"uri": taken}).status_code == 409


def test_the_subtree_rename_route_rewrites_descendants(client, subtree):
    response = client.post("/api/v1/documents/rename", json={
        "project": "notes", "uri_prefix": "notes/a",
        "new_uri_prefix": "notes/b",
    })
    assert response.status_code == 200
    assert response.json()["renamed"] == 3
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_documents_routes.py -k "patch or rename" -v`
Expected: FAIL with 405 — the routes do not exist.

- [ ] **Step 3: Add both routes**

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

Map `DocumentUriConflict` to 409 in both routes, reusing the conflict wording already used for `DocumentIsBlockFirst`.

- [ ] **Step 4: Add both rows to the conformance status map**

`tests/test_rest_conformance.py` pins a per-route status map, and a new route with no row fails it. Add `PATCH /documents/{document_id}` → 200 and `POST /documents/rename` → 200, each with 409.

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_documents_routes.py tests/test_rest_conformance.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/
git commit -m "feat(documents): add the metadata rest routes"
```

---

### Task 9: The MCP `document_update` tool

**Files:**
- Modify: `backend/app/api/mcp/server.py`
- Modify: `CLAUDE.md` (the tool count and the `capture` writer count), `docs/two-door-parity.md`
- Test: `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: `update_document_metadata`, `rename_documents`, `DocumentUriConflict` from Task 7
- Produces: MCP tool `document_update`, `capture` scope, carrying both shapes as modes

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: §4.2 states that MCP carries both shapes as modes of one tool

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_document_update_carries_both_shapes_as_modes(mcp):
    single = json.loads(await mcp.call(
        "document_update", {"document_id": DOC, "title": "New"}))
    assert single["status"] == "ok"

    subtree = json.loads(await mcp.call("document_update", {
        "project": "notes", "uri_prefix": "notes/a",
        "new_uri_prefix": "notes/b",
    }))
    assert subtree["renamed"] == 3


@pytest.mark.asyncio
async def test_document_update_needs_the_capture_scope(mcp_read_only_key):
    """A key that can edit a document's metadata can rename it, which is
    capture power, not read power."""
    with pytest.raises(PermissionError):
        await mcp_read_only_key.call(
            "document_update", {"document_id": DOC, "title": "New"})


@pytest.mark.asyncio
async def test_a_uri_conflict_is_an_envelope_not_a_tool_error(mcp, two_notes):
    envelope = json.loads(await mcp.call(
        "document_update", {"document_id": two_notes[0], "uri": TAKEN_URI}))
    assert envelope["status"] == "uri_conflict"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_mcp.py -k document_update -v`
Expected: FAIL — no such tool.

- [ ] **Step 3: Add the tool**

One tool, two modes, dispatched on whether `document_id` or `uri_prefix` was given. Refuse a call carrying both, and a call carrying neither, with an envelope rather than a tool error. Register it under the `capture` scope.

- [ ] **Step 4: Update every enumeration guard the new tool moves**

Run the full backend suite, not just `test_mcp.py`. One new tool trips several full-list assertions — the catalogue count (38 → 39), the `capture` writer count (12 → 13), the scope map, and the parity table. Update `CLAUDE.md`'s MCP section for both counts and add the row to `docs/two-door-parity.md`. Do not update a count until a test names it: a guessed count that happens to match hides the guard that should have caught it.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: PASS. This is the only step that catches the enumeration guards, which is why it is the whole suite rather than one file.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py CLAUDE.md docs/two-door-parity.md
git commit -m "feat(mcp): add the document_update tool"
```

---

## After the lanes land

- **Run `./scripts/gate.sh`.** Note it cannot complete `--full` on this host; run the legs individually per `CLAUDE.md`.
- **Add a `## Unreleased` changelog entry** — or fold into the section for the version the next push derives. Check `python3 scripts/next_version.py plan` **after a `git fetch`**: this repo's tags are written by CI, so a stale local tag list makes that command return a plausible wrong answer.
- **Lanes 1c-1e change the running artifact**, so the redeploy rule applies once the owner clears the cutover.

## What this plan does NOT do

`block_update`'s `source` mode and the retirement of `promote` (spec §4.1) are **not** in these lanes. §12 places them in increment 3, the editor increment, because the mode exists to serve per-block CodeMirror and has no caller until then. Landing it here would ship an untested-in-anger parser path behind a flag nothing sets.
