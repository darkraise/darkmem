# Pages, Increment A — backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Ship a `pages` object — a Notion-model note tree with `parent_id` and explicit sibling ordering — behind eleven REST routes, sharing the `blocks` table with `documents` while provably not affecting any document surface.

**Architecture:** `pages` is a new table whose `parent_id` self-FK is composite on `(id, project)`, so a child's parent must exist and must be in the same project. Blocks gain a nullable `page_id` beside a now-nullable `document_id` under a `num_nonnulls(...) = 1` CHECK, so a page block's `document_id` is NULL and every existing document query excludes it by NULL semantics without changing. Page vectors get their own `page_embeddings__<slug>` partition family so they never dilute the document HNSW candidate stream. The four block verbs are parameterised on a `BlockOwner` descriptor whose document instance carries today's SQL verbatim.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy Core with raw `text()` SQL, asyncpg, Postgres 16 with pgvector, Alembic (single regenerated baseline), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-pages-notion-model-design.md`

## Global Constraints

- **Greenfield until the freeze.** No backward compatibility, no migration, no compatibility shim, no import path for existing rows. The schema is ONE revision, `0001_baseline.py`, **regenerated in place** — never a `0002`. After regenerating, drop and recreate every database yourself.
- **`documents` must not change in behaviour.** This is the owner's stated requirement. Two edits to existing document-owned structures are permitted and no others: `blocks.document_id` losing `NOT NULL`, and `ix_blocks_document_order` gaining `WHERE document_id IS NOT NULL`. The second is safe because every document predicate is an equality on `document_id`, which the planner proves implies `IS NOT NULL`, so no document query loses its index. No document SQL statement changes, and no document code path may get slower.
- **Taxonomy is closed and taxonomy-first.** A value lands in `EVENT_TYPES` / `OBJECT_TYPES` before its emitter ships.
- **Single worker (invariant 13).** Exactly one uvicorn worker. Nothing may assume otherwise; in-process locks do not serialise across requests that interleave at an `await`.
- **asyncpg needs explicit CAST** on any raw-SQL param whose type Postgres cannot infer: `CAST(:id AS uuid)`, `CAST(:vec AS vector)`, `CAST(:props AS jsonb)`.
- **Child embedding tables are named ONLY through `child_table(parent, fingerprint)`** (invariant 2). No literal slug in application code.
- **The block channel is firewalled from the fact vault.** Any new module that reads a block row joins `BLOCK_CHANNEL_MODULES` in `tests/test_block_retrieval.py` in the same change that gives it that reach — an unclassified module is a hole in the scan.
- **REST conventions** (`docs/api-rest-conventions.md`): 201 create, 204 delete, 202 async-accepted, POST `.../search` for complex queries.
- **Comments:** default to none. Only where the WHY is non-obvious. Never reference the task, increment or a review finding.
- **English only** in code, comments, docs, commits, tests.
- **Commits:** `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period.
- **Backend tests** run from `backend/` on a lane database of your own:
  `TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" .venv/bin/python -m pytest -q <paths>`
  Lanes `darkmem_test_2` through `darkmem_test_5` exist. **Never use `darkmem_test`** — the controller keeps it.
- **Host hazard:** an `earlyoom` daemon kills memory-heavy runs at ~80% swap. **Exit 143 is a SIGTERM, not a failure** — check `free -h` before believing a red. Give every command an explicit timeout. Never run the full suite in one process.

---

### Task 1: Admit `page` and the page events to the closed vocabularies

Taxonomy-first: these values must exist before any emitter ships. Nothing emits them in this task, which is the point.

**Files:**
- Modify: `backend/app/services/events.py` (`EVENT_TYPES` list, `OBJECT_TYPES` list)
- Test: `backend/tests/test_events.py`
- Modify: `frontend/src/features/activity/event-taxonomy.ts` (the frontend classification map, whose completeness `backend/tests/test_event_taxonomy_map.py` asserts against `EVENT_TYPES`)

**Interfaces:**
- Consumes: nothing.
- Produces: the string literals `"page"` in `OBJECT_TYPES`, and `"page_created"`, `"page_updated"`, `"page_moved"`, `"page_deleted"`, `"page_restored"`, `"page_purged"` in `EVENT_TYPES`. Tasks 6, 7 and 8 emit them.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 2: adding a value to a closed vocabulary is an established pattern with eight precedents in this file

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_events.py`, beside the other vocabulary tests:

```python
def test_the_page_vocabulary_is_admitted_before_its_emitters():
    """Taxonomy-first: an emitter shipping ahead of its vocabulary logs a
    warning and writes an unclassified row, which is the failure this
    ordering exists to prevent."""
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert "page" in OBJECT_TYPES
    for event in (
        "page_created",
        "page_updated",
        "page_moved",
        "page_deleted",
        "page_restored",
        "page_purged",
    ):
        assert event in EVENT_TYPES, f"{event} is not admitted"
```

- [ ] **Step 2: Run it and watch it fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 300 .venv/bin/python -m pytest -q tests/test_events.py::test_the_page_vocabulary_is_admitted_before_its_emitters
```

Expected: FAIL on `assert "page" in OBJECT_TYPES`.

- [ ] **Step 3: Add the object type**

In `backend/app/services/events.py`, append to the `OBJECT_TYPES` list (currently ten values, ending `"system"`). Put `"page"` directly after `"document"` so the two content objects read together:

```python
    "document",
    "page",
```

- [ ] **Step 4: Add the event types**

In the same file, in `EVENT_TYPES`, directly after the `documents_deleted` entry, add:

```python
    # The page tree's lifecycle. `page_updated` is a title or property edit;
    # a block edit journals `blocks_edited` like a document's does. Deletion
    # is a `deleted_at` stamp, so `page_deleted` and `page_purged` are
    # different events: the first is reversible by `page_restored` and the
    # second is not.
    "page_created",
    "page_updated",
    "page_moved",
    "page_deleted",
    "page_restored",
    "page_purged",
```

- [ ] **Step 5: Classify the six events on the frontend**

`backend/tests/test_event_taxonomy_map.py` derives the live event set from the backend and fails when the frontend map omits one. Read the file first to find the map's location and the tab vocabulary it uses, then add the six with the same tab the document lifecycle events use.

- [ ] **Step 6: Run the covering tests**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_events.py tests/test_event_taxonomy_map.py
cd frontend && timeout 900 npm test -- event-taxonomy
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/events.py backend/tests/test_events.py \
        frontend/src/features/activity/event-taxonomy.ts
git commit -m "feat(events): admit the page vocabulary"
```

---

### Task 2: Regenerate the baseline with `pages`, block ownership, and the page partition family

One baseline regeneration covering every schema change this increment needs, because `0001_baseline.py` is a single shared mutable file and two tasks editing it means two drop-and-recreate cycles.

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py` (the `blocks` CREATE TABLE and its indexes; a new `pages` CREATE TABLE)
- Modify: `backend/app/services/embedder_registry.py` (`_TABLE_TEMPLATES`, `_AUX_INDEXES`)
- Test: `backend/tests/test_pages_schema.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: the `pages` table; `blocks.page_id`; the `blocks_exactly_one_owner` CHECK; `page_embeddings__<slug>` child tables reachable through `child_table("page_embeddings", fingerprint)`. Every later task consumes these.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** best-of-3 - two nullable FKs beat a polymorphic owner pair and a `content_owners` supertype in a ring pass; see the spec's §3 and appendix

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_pages_schema.py`:

```python
"""The schema half of the isolation guarantee.

`documents` must be unaffected by pages existing. These assertions are about
the shape that makes that true, not about behaviour -- behaviour is Task 13.
"""
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_a_block_must_have_exactly_one_owner(db_session):
    """Dropping NOT NULL from document_id does not weaken documents: a block
    with no owner is still refused, now by the CHECK rather than by NOT NULL."""
    with pytest.raises(Exception):
        await db_session.execute(
            text("INSERT INTO blocks (id, type, text) "
                 "VALUES (gen_random_uuid(), 'paragraph', 'orphan')")
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_a_block_cannot_have_both_owners(db_session):
    await db_session.execute(text(
        "INSERT INTO documents (id, project, uri, content_hash) "
        "VALUES ('11111111-1111-1111-1111-111111111111', 'p', 'a.md', 'h')"
    ))
    await db_session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        "VALUES ('22222222-2222-2222-2222-222222222222', 'p', 0, 'h')"
    ))
    with pytest.raises(Exception):
        await db_session.execute(text(
            "INSERT INTO blocks (id, document_id, page_id, type, text) VALUES ("
            "gen_random_uuid(), "
            "'11111111-1111-1111-1111-111111111111', "
            "'22222222-2222-2222-2222-222222222222', 'paragraph', 'both')"
        ))
    await db_session.rollback()


@pytest.mark.asyncio
async def test_a_page_parent_must_be_in_the_same_project(db_session):
    """The composite FK is what makes a cross-project reparent impossible in
    the schema rather than merely refused at the door."""
    await db_session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        "VALUES ('33333333-3333-3333-3333-333333333333', 'alpha', 0, 'h')"
    ))
    with pytest.raises(Exception):
        await db_session.execute(text(
            "INSERT INTO pages (id, project, parent_id, order_index, content_hash) "
            "VALUES (gen_random_uuid(), 'beta', "
            "'33333333-3333-3333-3333-333333333333', 0, 'h')"
        ))
    await db_session.rollback()


@pytest.mark.asyncio
async def test_the_document_block_indexes_survive(db_session):
    """An earlier draft of the spec showed the CREATE TABLE without these two,
    which would have seq-scanned every subtree delete and dropped keyword
    search's index."""
    rows = (await db_session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'blocks'"
    ))).scalars().all()
    for name in (
        "ix_blocks_document_order",
        "ix_blocks_page_order",
        "ix_blocks_parent",
        "ix_blocks_search_vector",
    ):
        assert name in rows, f"{name} is missing"
```

- [ ] **Step 2: Run it and watch it fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_pages_schema.py
```

Expected: FAIL — `relation "pages" does not exist`.

- [ ] **Step 3: Add the `pages` table to the baseline**

In `backend/migrations/versions/0001_baseline.py`, immediately after the `documents` table and before `blocks`:

```python
    op.execute(
        """
        CREATE TABLE pages (
            id           UUID NOT NULL,
            project      TEXT NOT NULL,
            parent_id    UUID,
            order_index  INTEGER NOT NULL,
            title        TEXT,
            content      TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL,
            properties   JSONB,
            deleted_at   TIMESTAMPTZ,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pages_pkey PRIMARY KEY (id),
            CONSTRAINT ux_pages_id_project UNIQUE (id, project),
            CONSTRAINT fk_pages_parent FOREIGN KEY (parent_id, project)
                REFERENCES pages (id, project) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_pages_project_parent_order "
        "ON pages (project, parent_id, order_index)"
    )
    op.execute(
        "CREATE TRIGGER pages_touch_updated_at BEFORE UPDATE "
        "ON pages FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )
```

The composite FK carries two invariants at once: a parent must exist, and it must be in the same project. `MATCH SIMPLE` semantics mean a NULL `parent_id` skips the check, so root pages work. `ON DELETE CASCADE` is the purge path only — Task 8's ordinary delete never removes a row.

- [ ] **Step 4: Change the `blocks` table**

Replace the existing `blocks` CREATE TABLE and its three index statements with:

```python
    op.execute(
        """
        CREATE TABLE blocks (
            id          UUID NOT NULL,
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            page_id     UUID REFERENCES pages(id) ON DELETE CASCADE,
            parent_id   UUID REFERENCES blocks(id) ON DELETE CASCADE,
            order_index INTEGER,
            type        TEXT,
            text        TEXT,
            properties  JSONB,
            char_span   INT4RANGE,
            search_vector TSVECTOR GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END
                )
            ) STORED,
            CONSTRAINT blocks_pkey PRIMARY KEY (id),
            -- Dropping NOT NULL from document_id does not weaken documents:
            -- a block with no owner at all is still refused, just by this
            -- rather than by the column. The only new permitted state is a
            -- block owned by a page.
            CONSTRAINT blocks_exactly_one_owner
                CHECK (num_nonnulls(document_id, page_id) = 1)
        )
        """
    )
    # Partial rather than plain: the page half of the table will be denser and
    # more update-heavy than the document half, and each index stays out of
    # the other owner's pages entirely.
    op.execute(
        "CREATE INDEX ix_blocks_document_order ON blocks (document_id, order_index) "
        "WHERE document_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_blocks_page_order ON blocks (page_id, order_index) "
        "WHERE page_id IS NOT NULL"
    )
    op.execute("CREATE INDEX ix_blocks_parent ON blocks (parent_id)")
    op.execute("CREATE INDEX ix_blocks_search_vector ON blocks USING GIN (search_vector)")
```

`pages` must be created before `blocks`, because `blocks.page_id` references it.

- [ ] **Step 5: Add the page embedding partition family**

In `backend/app/services/embedder_registry.py`, add an entry to `_TABLE_TEMPLATES` directly after `"block_embeddings"`:

```python
    # Pages do NOT share the block partition. That family carries one HNSW
    # index per child and every document ANN read filters the owner *after*
    # the index scan, so a growing notes corpus would starve document
    # connections and search of candidates -- the failure
    # `document_connections`' own docstring records. Same key, same cascade,
    # separate index.
    "page_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " block_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (block_id, fingerprint)"
        ")"
    ),
```

and to `_AUX_INDEXES`, after its `"block_embeddings"` entry:

```python
    "page_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_block_id ON {name} (block_id)",
    ],
```

`_ensure_children` iterates `_TABLE_TEMPLATES`, so both `register` and `reconcile` create the new children for every fingerprint with no further wiring, and each child gets its own HNSW index from the shared loop.

- [ ] **Step 6: Drop and recreate the databases**

The revision id does not move, so `alembic upgrade head` finds current == head and does nothing on an already-stamped database. The drop is not optional.

```bash
docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c \
  "DROP DATABASE IF EXISTS darkmem_test_3; CREATE DATABASE darkmem_test_3;"
```

The pytest fixture runs `DROP SCHEMA public CASCADE` and `alembic upgrade head` itself, so recreating the lane database is enough for the tests.

- [ ] **Step 7: Run the covering tests**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_pages_schema.py tests/test_block_pipeline.py tests/test_document_routes.py tests/test_document_update.py
```

Expected: PASS. The three document suites are the regression check that dropping `NOT NULL` changed nothing.

- [ ] **Step 8: Prove the tests discriminate**

Temporarily remove the `blocks_exactly_one_owner` CHECK, recreate the lane database, and confirm `test_a_block_must_have_exactly_one_owner` and `test_a_block_cannot_have_both_owners` both go red. Restore. Then remove `ix_blocks_parent` and confirm `test_the_document_block_indexes_survive` goes red. Restore. Paste the red output in your report.

- [ ] **Step 9: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py \
        backend/app/services/embedder_registry.py \
        backend/tests/test_pages_schema.py
git commit -m "feat(pages): add the page tree and block ownership"
```

---

### Task 3: Scope the embedding sweep to documents and give pages their own arm

`block_embedding_refresh._MISSING_SQL` has **no owner predicate at all**, so without this change page blocks enter the hourly job's 500-per-tick budget and its `ORDER BY b.id` full scan, delaying document embedding by N/500 hours on a large notes corpus. This is one of the three isolation breaches the design review found.

**Files:**
- Modify: `backend/app/services/block_embedding_refresh.py`
- Modify: `backend/app/services/block_embeddings.py` (`embed_blocks` and `ensure_partition` gain a `parent` argument)
- Test: `backend/tests/test_block_embedding_refresh.py`

**Interfaces:**
- Consumes: `page_embeddings` from Task 2.
- Produces: `block_embeddings.PAGE_PARENT_TABLE`, and `embed_blocks(..., parent=...)` / `ensure_partition(..., parent=...)`. Tasks 6 and 10 consume them.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5
**Approach:** inline - skip 3: the spec's §4 fixed both the predicate and the separate-arm shape

- [ ] **Step 1: Write the failing test**

Read `backend/tests/test_block_embedding_refresh.py` for the existing fixture shape first, then add:

```python
@pytest.mark.asyncio
async def test_the_sweep_does_not_claim_page_blocks(db_session, ...):
    """The sweep's budget belongs to documents. A page block entering it
    delays document embedding by one slot per page block, and the query had
    no owner predicate at all before this."""
    # Arrange: one document block and one page block, both unembedded.
    # Act: run the missing-blocks query.
    # Assert: the document block is returned and the page block is not.
```

Fill in the arrange and act using the file's existing fixture conventions — do not invent a new harness.

- [ ] **Step 2: Run it and watch it fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_block_embedding_refresh.py
```

Expected: FAIL — the page block is returned.

- [ ] **Step 3: Scope the sweep**

In `backend/app/services/block_embedding_refresh.py`, add the predicate to `_MISSING_SQL` (around line 120):

```sql
WHERE e.block_id IS NULL AND b.document_id IS NOT NULL
```

Add a comment giving the WHY, which is not obvious from the line:

```python
# Documents only. Page blocks are repaired by the page arm below, on its own
# budget: sharing this one would let a notes corpus consume the whole
# per-tick allowance and delay document embedding.
```

- [ ] **Step 4: Add the page arm**

Give the job a second query, identical but for `b.page_id IS NOT NULL` and the `page_embeddings` child table, with its own budget drawn from the same `config_schema` field. Read how the job resolves its fingerprint and child table and mirror it exactly.

- [ ] **Step 5: Parameterise the two embedding functions**

In `backend/app/services/block_embeddings.py`, add beside `PARENT_TABLE`:

```python
PAGE_PARENT_TABLE = "page_embeddings"
```

and give `embed_blocks` and `ensure_partition` a keyword-only `parent: str = PARENT_TABLE`, passing it to `child_table(parent, fingerprint)` in place of the module constant. Leave `search_blocks` and `block_vectors` alone — they join `documents`, and page search is out of scope for this increment.

- [ ] **Step 6: Run the covering tests and prove discrimination**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_embedding_refresh.py tests/test_block_pipeline.py tests/test_block_retrieval.py
```

Then remove the `AND b.document_id IS NOT NULL` and confirm the new test goes red. Restore. Paste both outputs.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/block_embedding_refresh.py \
        backend/app/services/block_embeddings.py \
        backend/tests/test_block_embedding_refresh.py
git commit -m "fix(embeddings): keep page blocks out of the doc sweep"
```

---

### Task 4: Parameterise the block verbs on a `BlockOwner`, document instance only

A pure refactor with no behaviour change and no page support yet. Splitting it this way means a reviewer can reject the abstraction while approving the page instance, or the reverse.

**Files:**
- Modify: `backend/app/services/block_verbs.py`
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `BlockOwner` (frozen dataclass) and `DOCUMENT_OWNER`. Task 5 adds the page instance.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: the spec's §6 fixed the descriptor shape and enumerated all six statements plus the hardcoded `object_type`

- [ ] **Step 1: Add the descriptor**

In `backend/app/services/block_verbs.py`, directly above `_LOCK_DOCUMENT`:

```python
@dataclass(frozen=True)
class BlockOwner:
    """What `_mutate` needs to know about the thing a block belongs to.

    The six statements below are the complete set that names `documents`;
    `_PLACE`, `_UPDATE_BLOCK` and `_DELETE_BLOCK` key on `blocks.id` and are
    owner-agnostic already. `object_type` is here because it was a hardcoded
    literal at the journal call, which would have filed a page edit as a
    document.
    """
    kind: str
    object_type: str
    lock: Any
    meta: Any
    load_tree: Any
    insert_block: Any
    write_owner: Any
    resolve_block_column: str


DOCUMENT_OWNER = BlockOwner(
    kind="document",
    object_type="document",
    lock=_LOCK_DOCUMENT,
    meta=_DOC_META,
    load_tree=_LOAD_TREE,
    insert_block=_INSERT_BLOCK,
    write_owner=_WRITE_DOC,
    resolve_block_column="document_id",
)
```

Keep every existing module-level statement constant exactly as it is — `DOCUMENT_OWNER` references them rather than replacing them, so the document SQL is provably byte-identical.

- [ ] **Step 2: Thread it through `_mutate`**

Give `_mutate` a keyword-only `owner: BlockOwner = DOCUMENT_OWNER` and replace each of its six direct constant uses with the descriptor's field. Replace the hardcoded `object_type="document"` at the journal call with `owner.object_type`.

Keep the parameter named `document_id` for now — renaming it is Task 5's, and doing both at once makes this diff unreviewable.

- [ ] **Step 3: Run the full document block suite**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_block_pipeline.py tests/test_document_update.py tests/test_document_routes.py
```

Expected: PASS with no test changed. **A refactor that needed a test edited is not a refactor** — if one fails, the descriptor is not byte-identical to what it replaced. Report rather than editing the test.

- [ ] **Step 4: Prove the `object_type` fix is real**

Add a test asserting a document block edit journals `object_type == "document"`, then temporarily set `DOCUMENT_OWNER.object_type` to `"page"` and confirm it goes red. Restore. This is the assertion that will catch Task 5 misfiling a page edit.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "refactor(blocks): parameterise the verbs on an owner"
```

---

### Task 5: Add the page owner and make block resolution owner-aware

**Files:**
- Modify: `backend/app/services/block_verbs.py`
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: `BlockOwner`, `DOCUMENT_OWNER` (Task 4); the `pages` table (Task 2).
- Produces: `PAGE_OWNER`, and `_owner_of(session, block_id) -> tuple[BlockOwner, str]`. Task 10's routes consume both.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: the spec's §6 table gives every page-side statement

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_a_page_block_resolves_to_the_page_owner(db_session, ...):
    """`_document_of` read one column, so a page block resolved to None and
    every verb built on it silently targeted nothing."""
    # Arrange: a page with one block.
    owner, owner_id = await _owner_of(db_session, str(block_id))
    assert owner.kind == "page"
    assert owner_id == str(page_id)
```

- [ ] **Step 2: Run it and watch it fail**

Expected: `ImportError` on `_owner_of`, or a `None` owner id.

- [ ] **Step 3: Add the page statements and the instance**

```python
_LOCK_PAGE = text(
    "SELECT id FROM pages WHERE id = CAST(:id AS uuid) "
    "AND deleted_at IS NULL FOR UPDATE"
)
_PAGE_META = text(
    "SELECT project, content, content_hash, "
    "       NULL AS direction, NULL AS frontmatter "
    "FROM pages WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL"
)
_LOAD_PAGE_TREE = text(
    "SELECT id, parent_id, order_index, type, text, properties, "
    "       lower(char_span) AS lo, upper(char_span) AS hi "
    "FROM blocks WHERE page_id = CAST(:id AS uuid) ORDER BY order_index"
)
_INSERT_PAGE_BLOCK = text(
    "INSERT INTO blocks (id, page_id, parent_id, order_index, type, text, properties) "
    "VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), CAST(:parent AS uuid), "
    "        :ord, CAST(:type AS text), CAST(:text AS text), CAST(:props AS jsonb))"
)
_WRITE_PAGE = text(
    "UPDATE pages SET content = CAST(:content AS text), "
    "content_hash = CAST(:hash AS text) WHERE id = CAST(:id AS uuid)"
)

PAGE_OWNER = BlockOwner(
    kind="page",
    object_type="page",
    lock=_LOCK_PAGE,
    meta=_PAGE_META,
    load_tree=_LOAD_PAGE_TREE,
    insert_block=_INSERT_PAGE_BLOCK,
    write_owner=_WRITE_PAGE,
    resolve_block_column="page_id",
)
```

`_PAGE_META` selects literal NULLs for `direction` and `frontmatter` so `_mutate`'s conversion branch is skipped without a second code path: a page is block-first by construction and never had an authored source to reproduce. `_WRITE_PAGE` writes no `ingest_direction` for the same reason. Both lock and meta filter `deleted_at IS NULL`, so a block verb against a trashed page resolves to nothing rather than editing it.

- [ ] **Step 4: Make resolution owner-aware**

Replace `_RESOLVE_BLOCK` and `_document_of`:

```python
_RESOLVE_BLOCK = text(
    "SELECT CAST(document_id AS text) AS document_id, "
    "       CAST(page_id AS text) AS page_id "
    "FROM blocks WHERE id = CAST(:id AS uuid)"
)


async def _owner_of(session: AsyncSession, block_id: str) -> tuple[BlockOwner, str]:
    row = (await session.execute(_RESOLVE_BLOCK, {"id": block_id})).mappings().first()
    if row is None:
        raise BlockTargetUnresolved(f"no block with id {block_id}")
    if row["document_id"] is not None:
        return DOCUMENT_OWNER, row["document_id"]
    return PAGE_OWNER, row["page_id"]
```

The CHECK guarantees exactly one is set, so the `else` needs no third case.

Update `update_block`, `move_block` and `delete_block` to call `_owner_of` and pass the owner to `_mutate`. Give `insert_block` a keyword-only `owner: BlockOwner = DOCUMENT_OWNER`, since it takes an owner id rather than a block id.

- [ ] **Step 5: Add `owner_kind` and `owner_id` to the result**

`BlockWriteResult` **keeps its `document_id` field** — renaming it changes the document door's wire shape through `BlockWriteResponse(**vars(result))` at `routes/documents.py:1028`. Add `owner_kind: str` and `owner_id: str` beside it, and set `document_id` to the owner id for the document instance and to `None` for a page.

- [ ] **Step 6: Run and prove discrimination**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_document_update.py tests/test_document_routes.py tests/test_block_pipeline.py
```

Then point `PAGE_OWNER.object_type` at `"document"` and confirm Task 4's journal test goes red for a page edit. Restore. Paste both outputs.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(blocks): teach the verbs about page owners"
```

---

### Task 6: The page door — create, get, list

**Files:**
- Create: `backend/app/services/page_door.py`
- Test: `backend/tests/test_page_door.py`

**Interfaces:**
- Consumes: the `pages` table (Task 2); `embed_blocks(..., parent=PAGE_PARENT_TABLE)` (Task 3); `PAGE_OWNER` (Task 5).
- Produces: `create_page(session, llm, *, project, title, parent_id=None, after_id=None, content=None) -> PageResult`, `get_page(session, page_id, *, include_content=False)`, `list_pages(session, project)`. Task 9's routes consume all three.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec's §7 fixed the create-with-content shape, the `after_id` contract and the `order_index` semantics

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_a_child_requires_its_parent_to_exist(db_session, llm):
    """The Notion invariant, and the reason pages are not documents: a
    document files to any path unconditionally, a page does not."""
    with pytest.raises(PageTargetUnresolved):
        await create_page(db_session, llm, project="p", title="orphan",
                          parent_id=str(uuid4()))


@pytest.mark.asyncio
async def test_creating_with_content_parses_it_into_blocks(db_session, llm):
    """Without this path the first caller writes `content` straight onto the
    row and recreates content-first state on an object with no conversion
    pass."""
    page = await create_page(db_session, llm, project="p", title="n",
                             content="# Title\n\nA paragraph.\n")
    blocks = await _blocks_of(db_session, page.id)
    assert [b["type"] for b in blocks] == ["heading", "paragraph"]


@pytest.mark.asyncio
async def test_the_stored_content_is_the_serialiser_output(db_session, llm):
    """`content` is regenerated rather than stored verbatim, which is what
    keeps a page block-first and means no conversion is ever owed."""
    page = await create_page(db_session, llm, project="p", title="n",
                             content="#   Title\n")
    row = await _page_row(db_session, page.id)
    assert row["content"] == "# Title\n"


@pytest.mark.asyncio
async def test_siblings_are_appended_in_dense_order(db_session, llm):
    a = await create_page(db_session, llm, project="p", title="a")
    b = await create_page(db_session, llm, project="p", title="b")
    assert [p.order_index for p in (a, b)] == [0, 1]


@pytest.mark.asyncio
async def test_an_empty_page_has_a_hash_to_precondition_against(db_session, llm):
    """NOT NULL with the create route writing compute_content_hash(''): a NULL
    would leave the first `expected_hash` a client sends nothing to compare
    against."""
    page = await create_page(db_session, llm, project="p", title="n")
    row = await _page_row(db_session, page.id)
    assert row["content"] == ""
    assert row["content_hash"] == compute_content_hash("")


@pytest.mark.asyncio
async def test_the_list_excludes_trashed_pages_and_content(db_session, llm):
    rows = await list_pages(db_session, "p")
    assert all("content" not in r for r in rows)
```

- [ ] **Step 2: Run and watch them fail**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_page_door.py
```

Expected: `ModuleNotFoundError: app.services.page_door`.

- [ ] **Step 3: Implement**

Create `backend/app/services/page_door.py`. Follow `document_door.py`'s conventions — raw `text()` SQL with explicit CASTs, a `SAVEPOINT` around the filing, `MAX_BLOCKS` checked inside it.

- `create_page` mints the id, appends at `max(order_index) + 1` for `(project, parent_id)` **under a `SELECT … FOR UPDATE` on the parent row** (or an advisory lock on `(project, parent_id)` for roots) — without it two browser tabs mint the same index. When `content` is given, parse it with the document parser, write the blocks, serialise the tree back, and store the serialiser's output as `content`. Journal `page_created`.
- `get_page` returns the row plus its blocks in `order_index` order, `content` only when `include_content`, and refuses a page whose `deleted_at` is set.
- `list_pages` is one `SELECT … WHERE project = :p AND deleted_at IS NULL ORDER BY parent_id, order_index`, **excluding `content`**. It returns flat rows; the client nests them.

Define `PageTargetUnresolved` locally rather than importing a document exception — the two doors are separate objects. `compute_content_hash` is at `app/services/document_ingest.py:184` and is shared, not duplicated: it hashes a string and knows nothing about documents.

- [ ] **Step 4: Run, then prove each test discriminates**

Break each behaviour deliberately, one at a time, and confirm the matching test goes red. Paste the output.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_door.py backend/tests/test_page_door.py
git commit -m "feat(pages): add create, get and list"
```

---

### Task 7: The move, with a cycle guard that holds under concurrency

**Files:**
- Modify: `backend/app/services/page_door.py`
- Test: `backend/tests/test_page_door.py`

**Interfaces:**
- Consumes: `create_page`, `list_pages` (Task 6).
- Produces: `move_page(session, page_id, *, parent_id, after_id=None)` and `rename_page(session, page_id, *, title)`. Task 9's `PATCH` route consumes both.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 3 = 6
**Approach:** inline - skip 3: the spec's §7 fixed the `after_id` contract, the dense renumber and the lock

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_a_page_cannot_be_moved_into_its_own_subtree(db_session, llm):
    root = await create_page(db_session, llm, project="p", title="root")
    child = await create_page(db_session, llm, project="p", title="child",
                              parent_id=root.id)
    with pytest.raises(PageCycleError):
        await move_page(db_session, root.id, parent_id=child.id)


@pytest.mark.asyncio
async def test_two_concurrent_moves_cannot_orphan_a_subtree(db_session_factory, llm):
    """Each move walks ancestors against the committed tree, so without a lock
    both pass their own check and both commit, leaving A under B and B under A
    -- unreachable from every root. Invariant 13's single worker does not help:
    the two requests interleave across awaits."""
    # Two sessions, A-under-B and B-under-A, started before either commits.
    # Exactly one must succeed.


@pytest.mark.asyncio
async def test_a_move_renumbers_both_sibling_sets_densely(db_session, llm):
    # Three children of X, one moved to Y after its first child.
    # Assert X's survivors are 0,1 and Y's are 0,1,2 with the mover placed.


@pytest.mark.asyncio
async def test_after_id_null_places_first(db_session, llm):
    ...
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

`move_page` takes `parent_id` plus `after_id` (null = first) and **never a raw `order_index`** — mirroring `move_block`'s existing `after_block_id`. Taking an index would ship a contract Increment B breaks the moment it implements drag-to-reorder.

Order of operations, and the order matters:

1. `SELECT … FOR UPDATE` on the moved page **and on the new parent's whole ancestor chain**, in one recursive CTE with `FOR UPDATE` on the base. Locking before the walk is what makes this a compare-and-set rather than a check-then-act.
2. Walk ancestors of the new parent; raise `PageCycleError` if the moved page is among them or is the new parent itself.
3. Renumber the old and new sibling sets densely, 0-based, in one `UPDATE … FROM unnest(…)`.
4. Journal `page_moved`.

The composite FK already refuses a cross-project parent, so no application check is owed for that — let the database raise and translate it.

`rename_page` is a title UPDATE journalling `page_updated`. It is last-writer-wins and carries no `expected_hash`; state that in its docstring so the omission reads as a decision.

- [ ] **Step 4: Prove the concurrency test discriminates**

Remove the `FOR UPDATE` and confirm `test_two_concurrent_moves_cannot_orphan_a_subtree` goes red. This is the single most important discrimination proof in the plan — a cycle guard that passes only because the test is serial is worth nothing. Paste the red output.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_door.py backend/tests/test_page_door.py
git commit -m "feat(pages): move a page under a cycle guard"
```

---

### Task 8: Soft delete, restore, and purge

**Files:**
- Modify: `backend/app/services/page_door.py`
- Test: `backend/tests/test_page_door.py`

**Interfaces:**
- Consumes: `create_page` (Task 6).
- Produces: `delete_page(session, page_id)`, `restore_page(session, page_id)`, `purge_trash(session, project)`. Task 9's routes consume all three.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 3 = 6
**Approach:** inline - skip 3: the spec's §9 fixed soft-delete over cascade and §8 fixed the journal contract

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_deleting_a_page_stamps_its_whole_subtree(db_session, llm):
    """A page's only copy is the row -- unlike a document, which the agent
    that filed it can re-file. That asymmetry is why this is a stamp."""


@pytest.mark.asyncio
async def test_a_trashed_subtree_restores_whole(db_session, llm):
    ...


@pytest.mark.asyncio
async def test_a_delete_journals_one_row_per_page_before_it_writes(db_session, llm):
    """The strict journal contract `delete_documents` already holds: an erase
    with no audit trail is worse than a refused one."""


@pytest.mark.asyncio
async def test_a_delete_refuses_when_a_journal_row_does_not_land(db_session, llm, monkeypatch):
    # record_event patched to return False; assert the raise and that nothing
    # was stamped.


@pytest.mark.asyncio
async def test_purge_removes_rows_blocks_and_vectors(db_session, llm):
    ...


@pytest.mark.asyncio
async def test_purge_leaves_live_pages_alone(db_session, llm):
    """The positive control. A purge that deleted everything would pass the
    test above."""
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

`delete_page` enumerates the subtree with a recursive CTE **first**, journals one `page_deleted` row per page **before** stamping, and **raises when `record_event` returns `False`** — the strict contract `delete_documents` holds (`document_door.py:955-979`). Constrain the exception to a locally defined class rather than importing the vault repository's `JournalWriteFailed`; the reason is firewall hygiene, and no test forces it.

Then one recursive `UPDATE … SET deleted_at = now()` over the subtree.

`restore_page` clears the stamp over the same subtree and journals `page_restored`. `purge_trash` runs the real `DELETE` for a project's stamped pages, which cascades through `fk_pages_parent` to descendants and through `blocks.page_id` to blocks and their vectors, journalling `page_purged`.

Every read path added in Task 6 already filters `deleted_at IS NULL`; confirm rather than assume.

- [ ] **Step 4: Prove discrimination on the journal refusal and the positive control**

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_door.py backend/tests/test_page_door.py
git commit -m "feat(pages): trash a page instead of erasing it"
```

---

### Task 9: The seven page routes and their schemas

**Files:**
- Create: `backend/app/api/routes/pages.py`
- Create: `backend/app/schemas/page.py`
- Modify: `backend/app/main.py` (router registration)
- Test: `backend/tests/test_page_routes.py`

**Interfaces:**
- Consumes: every `page_door` function from Tasks 6-8.
- Produces: `POST /api/v1/pages`, `GET /api/v1/pages`, `GET /api/v1/pages/{id}`, `PATCH /api/v1/pages/{id}`, `DELETE /api/v1/pages/{id}`, `POST /api/v1/pages/{id}/restore`, `POST /api/v1/pages/trash/empty`. Task 11 classifies them.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 2: follows `routes/documents.py`'s established route, schema and error-translation pattern

- [ ] **Step 1: Write the failing tests**

Cover each route's happy path and its refusal: a create under a missing parent is 404; a move into its own subtree is 409; a `PATCH` naming no field is 422; a `DELETE` of an already-trashed page is 404; `POST /pages/trash/empty` answers the purge count.

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

Follow `routes/documents.py` exactly for structure, dependency injection and exception translation. Status codes per `docs/api-rest-conventions.md`: **201** on create, **204** on delete, 200 elsewhere.

`PATCH` dispatches on which of `title`, `parent_id`/`after_id` is present and refuses a body naming none — an edit that changes nothing must not journal, the rule the document metadata verb already follows.

Register the router in `main.py` beside the documents router.

- [ ] **Step 4: Run the covering tests**

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/pages.py backend/app/schemas/page.py \
        backend/app/main.py backend/tests/test_page_routes.py
git commit -m "feat(pages): serve the page tree over REST"
```

---

### Task 10: The four page block routes

Without these, Increment A ends with a page that is a titled empty row. The document block routes cannot serve pages: each runs `_assert_block_is_in`, which 404s a page block, and `insert_block` takes an owner id rather than a block id.

**Files:**
- Modify: `backend/app/api/routes/pages.py`
- Test: `backend/tests/test_page_routes.py`

**Interfaces:**
- Consumes: `PAGE_OWNER`, `_owner_of` (Task 5); the page routes module (Task 9).
- Produces: `POST /api/v1/pages/{id}/blocks`, `PATCH /api/v1/pages/{id}/blocks/{block_id}`, `POST /api/v1/pages/{id}/blocks/{block_id}/move`, `DELETE /api/v1/pages/{id}/blocks/{block_id}`. Task 11 classifies them.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: mirrors the four document block routes at `routes/documents.py:1005-1076`

- [ ] **Step 1: Write the failing tests**

Mirror the document block route tests. Add two that are specific to this door:

```python
async def test_a_block_of_another_page_is_refused(client, auth_headers):
    """The page-flavoured `_assert_block_is_in`. Without it, a block id from
    any page could be edited through any page's route."""


async def test_the_hash_precondition_holds_on_a_page(client, auth_headers):
    """`expected_hash` compares against `pages.content_hash`, which is why
    that column is NOT NULL with the create route seeding it."""
```

- [ ] **Step 2: Run and watch them fail**

- [ ] **Step 3: Implement**

Mirror `routes/documents.py:1005-1076`. Write a page-flavoured `_assert_block_is_in` reading `page_id`, and pass `owner=PAGE_OWNER` to `insert_block`. The other three verbs resolve their owner from the block id through `_owner_of`, so they need no owner argument — but they must still assert the block belongs to the page named in the path, or the path segment is decorative.

- [ ] **Step 4: Prove the cross-page test discriminates**

Remove the `_assert_block_is_in` call and confirm `test_a_block_of_another_page_is_refused` goes red.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/pages.py backend/tests/test_page_routes.py
git commit -m "feat(pages): edit a page's blocks over REST"
```

---

### Task 11: Classify the eleven routes in the three enumeration guards

Every one of these guards enumerates `app.routes` and fails on any route it does not know. One new door trips a spread of them, and they live outside the module the work was in — the failure CLAUDE.md records leaving the 2026-09-07 branch red for eight tasks.

**Files:**
- Modify: `backend/tests/test_door_parity.py` (`PARITY_TABLE`)
- Modify: `backend/app/services/content_surfaces.py` (`ROUTES_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`)
- Modify: `docs/two-door-parity.md` (regenerated, not hand-edited)

**Interfaces:**
- Consumes: all eleven routes (Tasks 9 and 10).
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2
**Approach:** inline - skip 2: each registry has dozens of existing entries to pattern-match

- [ ] **Step 1: Run the guards and read the failures**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_door_parity.py tests/test_content_surface_scoping.py tests/test_api/test_rest_conformance.py
```

Each failure names the route it could not classify. That list is your work list — do not derive it from this plan, derive it from the run.

- [ ] **Step 2: Add the parity surfaces**

`PARITY_TABLE` holds `Surface` rows, and **one row carries many routes** in its `rest` tuple — so this is two or three surfaces, not eleven rows. Split them the way the documents surfaces are split: a `pages.write` surface for the mutating routes and a `pages.reads` surface for the reads.

Each needs `status=REST_ONLY` and a `reason` of at least 80 characters saying **why** it is single-door, not that it is. The real reason: pages are a human authoring surface, agents reach context through memories and documents, and widening later is additive — an agent that could rewrite the operator's notes is a capability nobody asked for.

- [ ] **Step 3: Add the content-surface and conformance entries**

Add each route to `ROUTES_WITHOUT_MEMORY_CONTENT` with a comment matching the neighbouring documents entry's reasoning: page content crosses these, but no `memories` row does. Add each `(METHOD, path)` to `EXPECTED_STATUS` with 201 for the create, 204 for the delete, 200 elsewhere.

- [ ] **Step 4: Regenerate the parity document**

`docs/two-door-parity.md`'s table is generated from `PARITY_TABLE`. Find the generator and run it; do not hand-edit the file. Its headline counts sentence sits outside the generated block — check by hand whether adding a surface moves it.

- [ ] **Step 5: Run the full guards leg**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_door_parity.py backend/app/services/content_surfaces.py \
        backend/tests/test_api/test_rest_conformance.py docs/two-door-parity.md
git commit -m "docs(pages): classify the page routes as REST-only"
```

---

### Task 12: Put pages in the project catalogue

`GET /api/v1/projects` unions `memories`, `documents` and `session_checkpoints`, so a project holding only pages is invisible to its own catalogue.

**Files:**
- Modify: `backend/app/api/routes/projects.py:42-58`
- Modify: `frontend/src/hooks/api/use-projects-api.ts` (the `ProjectSummary` interface)
- Test: `backend/tests/test_projects_endpoint.py`

**Interfaces:**
- Consumes: the `pages` table (Task 2).
- Produces: `ProjectSummary.page_count`. Increment B's project picker sorts on it.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: a fourth arm beside three existing ones in the same union

- [ ] **Step 1: Write the failing test**

```python
async def test_a_project_holding_only_pages_is_listed(client, auth_headers, db_session):
    """The catalogue is a union, and a project absent from it cannot be
    selected in any UI that reads it."""
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Add the arm**

Add `pages` to the union and `page_count` to the summary, mirroring `document_count` exactly — including whether trashed pages count. They should not: a project whose only pages are in the trash reads as empty, which is what it is.

- [ ] **Step 4: Add the frontend field**

`page_count: number` beside `document_count` in `ProjectSummary`. Optional is wrong here — the backend always serves it.

- [ ] **Step 5: Run and commit**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 600 .venv/bin/python -m pytest -q tests/test_projects_endpoint.py
cd frontend && timeout 900 npm run typecheck
```

```bash
git add backend/app/api/routes/projects.py backend/tests/test_projects_endpoint.py \
        frontend/src/hooks/api/use-projects-api.ts
git commit -m "feat(projects): count pages in the catalogue"
```

---

### Task 13: The isolation test

The whole increment's correctness for documents rests on NULL semantics rather than on written filters, so a future `COALESCE` or `LEFT JOIN` could reopen the channel with no test failing. This is the test that makes the owner's requirement checkable.

**Files:**
- Create: `backend/tests/test_page_document_isolation.py`

**Interfaces:**
- Consumes: everything.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3
**Approach:** inline - skip 3: the spec's §5 enumerates every assertion

- [ ] **Step 1: Write the test**

One fixture: a project holding one document with blocks and one page with blocks, both embedded. Then assert, each as its own test with its own name:

```python
async def test_a_page_is_absent_from_document_search(...):
    """`block_embeddings.py:326` inner-joins documents, so a page row drops.
    Pinned because that is NULL semantics, not a written filter."""

async def test_a_page_is_absent_from_document_connections(...):
    """`document_connections.py:184` filters `tb.document_id <> :document_id`,
    and `NULL <> x` is never true."""

async def test_a_page_is_absent_from_a_document_outline(...): ...

async def test_a_page_block_is_not_addressable_through_a_document_route(...):
    """`_assert_block_is_in` at routes/documents.py:993-1002 404s it."""

async def test_a_page_block_is_not_claimed_by_the_document_embedding_sweep(...):
    """Task 3's predicate. Without it the sweep has no owner predicate at all."""

async def test_page_vectors_live_in_their_own_partition(...):
    """The one that matters most: sharing block_embeddings would put page
    vectors in an HNSW index whose owner filter runs after the scan, starving
    document connections of candidates as the notes corpus grows."""
```

- [ ] **Step 2: Prove every one discriminates**

For each: break the mechanism it covers, watch it go red, restore. For the partition test, point the page embed path at `PARENT_TABLE` and confirm it fails. Paste all six red outputs — a test that passes against broken code is worse than no test, and this file is the guarantee.

- [ ] **Step 3: Run the whole document surface as the regression check**

```
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 1200 .venv/bin/python -m pytest -q tests/test_page_document_isolation.py tests/test_document_routes.py tests/test_document_update.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_block_verbs.py
```

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_page_document_isolation.py
git commit -m "test(pages): pin that pages cannot reach documents"
```

---

## Closing out Increment A

- [ ] **Run the backend suite in four chunks.** The full suite cannot complete in one process on this host — an `earlyoom` daemon kills it at ~80% swap and exit 143 is a SIGTERM, not a failure. Split `tests/*.py tests/test_api/*.py` into four and run each against its own lane database (`darkmem_test_2`..`darkmem_test_5`), sequentially.
- [ ] **Run the guards leg** from CLAUDE.md's Commands section, plus `test_event_taxonomy_map.py`.
- [ ] **Frontend:** `npm run typecheck && npm test && npm run build`.
- [ ] **SDKs:** `cd sdks && make generate`, then confirm `git status --porcelain` is clean. The page routes are REST-only and the generator reads the live OpenAPI document, so this will change the emitted clients — that is expected, and the generated files are committed, never hand-edited.
- [ ] **Update `CLAUDE.md`.** The Documents section gains a paragraph on pages as a separate object; the Events journal section gains the six event types; the Layout section gains `page_door.py` and `routes/pages.py`. Keep the file's voice — it argues, it does not list.
- [ ] **Add a `## vN.N.N` section to `CHANGELOG.md`.** Run `git fetch --tags` first, then `backend/.venv/bin/python scripts/next_version.py plan` for the version.
- [ ] **Redeploy.** This increment regenerates the baseline, so the deploy is a drop-and-recreate: `DARKMEM_PUSH=0 ./scripts/build-push.sh` → drop and recreate the production database → `docker compose up -d` → wait for `healthy` → **re-seed `admin_password_hash` and all eight `llm_purpose_configs` rows** per `docs/runbook-deployment.md` → confirm the change is in the running image, not just the tree.
- [ ] **Then** `superpowers:finishing-a-development-branch`.
