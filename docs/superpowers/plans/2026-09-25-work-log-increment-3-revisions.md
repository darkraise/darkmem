# Work-log lane, increment 3: document revisions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep every content a filing writes as a `document_revisions` row, and serve a document's revisions on both doors.

**Architecture:** The baseline gives the inert `document_revisions` table `actor` and `api_key_id` columns. `document_ingest`'s filing body, inside the filing's own SAVEPOINT, writes a post-image revision whenever a filing creates a document or changes its `content_hash`. A new read module, `app/services/document_revisions.py`, pages revisions newest first without content and fetches one with content; two keyed REST routes and one MCP tool call it.

**Tech Stack:** FastAPI, SQLAlchemy 2 async over asyncpg, Postgres 17, MCP SDK `mcp==2.1.1`, pytest (asyncio auto mode).

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** inline — `claude --model sonnet --effort high` — two of seven tasks are heavy (1, 2), two are four-band (4, 5; 3 × 2 ≤ 7, so both are delegated) and four carry a Codex Executor line, so every task is delegated and the controller only dispatches, reviews and records; delegation sets the effort to high.

**Plan review:** 2026-09-25 — dr-superpowers:judge-opus — executability 17 / coherence 16 / coverage 17 / assumptions 16 (round 2)

> **External executors:** codex

## Global Constraints

- Spec §9: increment 3 is "Document revisions. Table, write path, read verbs on both doors." Nothing here touches the memory-door warning, retention, the UI, `session_checkpoints` or block-first documents and pages (spec §11: block-verb edits write no revision).
- Spec §9 also says each increment is deployed on this host before the next one starts. As of 2026-09-25 increments 1 and 2 are merged but not deployed (register row 1). Executing this plan before increment 2 is deployed needs the owner's go-ahead; ask before Task 1 if it has not been given.
- This increment regenerates `backend/migrations/versions/0001_baseline.py` in place (never a `0002`). `app/schema_guard.py` hashes that file, so deploying it means dropping and recreating every deployed database and re-seeding it (`CLAUDE.md` → Commands → schema, `docs/runbook-deployment.md`). Increment 1's baseline change already obliges that for production, so one recreate can cover increments 1–3; the deploy is the owner's and is not a task here.
- `document_revisions` becomes `(id, document_id FK → documents ON DELETE CASCADE, content TEXT NOT NULL, content_hash TEXT NOT NULL, actor TEXT, api_key_id UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now())` with index `ix_document_revisions_document (document_id, created_at DESC, id DESC)`. `api_key_id` has no foreign key, as `events.api_key_id` has none.
- A revision is a post-image (spec §1 and §3, amended 2026-09-23): the content a filing wrote, so the newest revision equals `documents.content`. It is written when a filing creates a document or changes its `content_hash`, and never for an unchanged re-push, a stale `expected_hash`, a forced reparse of identical bytes, a bytes source (`content` NULL) or a block verb. It rolls back with the filing, so a refused put (`MAX_BLOCKS`, parse failure) leaves none.
- "Changes its `content_hash`" is decided against the row the filing resolved (`existing.content_hash`, which `put_document` reads under its row lock) when it resolved one, and against the document's newest revision when it resolved none. Two first filings of one uri race: the loser resolves no row, then its upsert waits for and updates the winner's row, so only the winner's committed revision tells it the content did not change. The upsert refuses a block-first row, so on that path no block edit (which moves the row's hash without a revision) can sit between the newest revision and the row.
- Revisions order newest first on `(created_at, id)`. The writer stamps `created_at` with `clock_timestamp()`, because two puts on one document serialise on its row lock and the later writer can hold the earlier transaction start.
- A page of revisions carries no content (`id, content_hash, actor, api_key_id, created_at`); one revision read by id carries `content`. Diffs are the caller's (spec §3).
- Scopes: every new door is `read`. The two REST routes declare the existing `_require_read` binding in `app/api/routes/documents.py`, so the file keeps exactly two `require_scope` call sites; the MCP tool joins `READ_TOOLS`.
- Tests run from `backend/` with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` against the dev-compose Postgres (`docker compose -f docker-compose.dev.yml up -d postgres` from the repo root when it is down). Every pytest command below carries that variable; without it conftest falls back to `darkmem_test`, the controller's database, and drops its schema. If pytest cannot connect because `darkmem_test_2` does not exist (a fresh dev volume creates only `darkmem`), create it once: `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test_2"`. Run pytest as `.venv/bin/python -m pytest`, never `uv run` (it writes an untracked `backend/uv.lock`). pytest-timeout is not installed; bound runs with `timeout`.
- Every `git` command runs from the repository root (`/root/repositories/darkmem`); every pytest command runs from `backend/`.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative. Never push; never `--no-verify`.
- Done means all seven tasks committed with the full backend suite and the `CLAUDE.md` guard leg green on the branch. The CHANGELOG entry is written at release (`scripts/next_version.py` writes the version heading), not here.

## Contracts

**Schema** (Task 1): `document_revisions` as in Global Constraints. `INERT_TABLES` in `backend/tests/test_inert_objects.py` becomes `{}`.

**Writer** (Task 2, `app/repositories/documents.py`): `async insert_revision(session, *, revision_id: UUID, document_id: UUID, content: str, content_hash: str, actor: str | None, api_key_id: UUID | None) -> None` and `async latest_revision_hash(session, document_id: UUID) -> str | None` (the newest revision's `content_hash`, `None` when there is none), both in `__all__`. `_file_document_without_savepoint` in `app/services/document_ingest.py` calls `insert_revision` after `insert_blocks` when `stored_content is not None` and the filing changed the hash: `existing.content_hash != content_hash` when `existing` is not None, else `await documents_repo.latest_revision_hash(session, resolved_id) != content_hash`; with `revision_id=new_id()`.

**Test helpers** (Task 2, `backend/tests/test_document_revisions.py`): `FINGERPRINT = "revisions-probe|3"`; `StubEmbedder()` (3-dim `embed` and `embed_batch_chunked`); `async _put(session, content, *, uri="superpowers/specs/a.md", **kwargs)` files through `put_document` under project `proj`; `async _revisions(session, document_id) -> list[tuple[content, content_hash, actor, api_key_id]]`, oldest first; `RACE_PROJECT = "revisions-race"` and the `committed` fixture (sessions on the test engine that commit for real, deleting the race project's documents afterwards).

**Read service** (Task 3, `app/services/document_revisions.py`): `DEFAULT_LIMIT = 50`, `MAX_LIMIT = 200`;
- `async list_revisions(session, *, document_id, before=None, limit=50) -> dict` answering `{"document_id": str, "items": [{"id", "content_hash", "actor", "api_key_id", "created_at"}], "next_before": str | None}`, newest first; `created_at` is an ISO 8601 string, `api_key_id` a string or `None`; `next_before` is the last item's id only when an older revision exists. Raises `ValueError` for a limit outside 1–200 (message contains `limit`), a `before` that is not a UUID (`not a revision id`) or names no revision of this document (`names no revision`).
- `async get_revision(session, *, document_id, revision_id) -> dict | None` answering the item fields plus `"document_id"` and `"content"`; `None` when the revision is not this document's. Raises `ValueError` for a malformed `revision_id`.
- Neither confirms the document exists; callers resolve it first with `document_door.resolve_document_target`.

**REST** (Task 4, `app/api/routes/documents.py`): `GET /api/v1/documents/{document_id}/revisions?before=&limit=` → 200 `DocumentRevisionListResponse` (`document_id`, `items: list[DocumentRevisionItem]`, `next_before`), 404 for an unknown document, 422 for a refused `before` or a limit outside 1–200; `GET /api/v1/documents/{document_id}/revisions/{revision_id}` → 200 `DocumentRevisionResponse` (`DocumentRevisionItem` plus `document_id`, `content`), 404 for an unknown document or a revision it does not own. `DocumentRevisionItem`: `id: str, content_hash: str, actor: str | None, api_key_id: str | None, created_at: datetime`. Both declare `_require_read`.

**MCP** (Task 5, `app/api/mcp/server.py`): `document_revisions(document_id=None, project=None, uri=None, revision_id=None, before=None, limit=50) -> str` — JSON of `list_revisions` (limit clamped to 1–200), or of `get_revision` when `revision_id` is given (`null` when not found); an unresolved document raises `DocumentTargetUnresolved`. In `READ_TOOLS`; the catalogue becomes 48 tools (15 capture, 30 read, 3 admin).

**Parity** (Task 6): row `documents.revisions`, two-door; `docs/two-door-parity.md` headline becomes 91 surfaces, 33 two-door, 58 single-door (51 REST-only, 7 MCP-only), 0 divergent.

## Assumptions (evidence)

- darkmem `master` is at `a587a39f` (increment 2 complete, 2026-09-25). Dry run on 2026-09-25: every task's code in this plan, applied verbatim to a scratch worktree of `a587a39f`, passed its targeted tests (`test_document_revisions.py`, `test_documents_keyed.py`, `test_api_keys.py`, `test_mcp.py`, `test_mcp_auth.py`, `test_prompt_agent_instructions.py`, `test_inert_objects.py`, `test_partition_templates.py`, `test_notes_schema.py` and the three enumeration guards) against `darkmem_test_3`, and the full backend suite on that worktree ran 7675 passed, 26 skipped, 0 failed; after the plan review round 1 fixes it ran 7679 passed, 26 skipped, 0 failed, and after the round 2 fixes 7680 passed, 26 skipped, 0 failed.
- `document_revisions` exists in the baseline as an inert table with `id, document_id, content, content_hash, created_at` (`backend/migrations/versions/0001_baseline.py:1553-1572`), listed in `INERT_TABLES` (`backend/tests/test_inert_objects.py:47-49`). `tests/test_notes_schema.py:94-107` inserts a row naming only those columns, so two nullable columns leave it green.
- The test database is dropped and rebuilt from the baseline at every session start (`backend/tests/conftest.py:33-66`), so a baseline edit reaches the tests with no manual step.
- `put_document` (`app/services/document_door.py:500-515`) and `file_document` (`app/services/document_ingest.py:191-206`) already take `actor` and `api_key_id`, and both doors pass them (`app/api/routes/documents.py:763-769`, `app/api/mcp/server.py:935-941`). Spec §3's "`put_document` gains an `api_key_id` parameter" is therefore already true; Task 7 amends that sentence.
- `_file_document_without_savepoint` knows `stored_content` (`None` for bytes) and `resolved_id` (`document_ingest.py:268-356`), and runs inside `file_document`'s SAVEPOINT (`:216`); `put_document` wraps the filing and the `MAX_BLOCKS` check in a second SAVEPOINT (`document_door.py:557-576`), so a refused put rolls the revision back with the row. By the revision write the filing holds the document row's lock in every path: `update_document`'s UPDATE, or `upsert_by_uri`'s INSERT … ON CONFLICT DO UPDATE, which waits for a concurrent first filing to commit. Under READ COMMITTED the newest-revision read that follows sees that filing's committed revision. Plan review round 1 (Codex, Critical) found that deciding on the pre-write `existing` wrote two revisions for two racing first filings of identical content; the dry run confirmed `test_two_first_filings_of_the_same_content_write_one_revision` fails under that rule (`['same', 'same'] == ['same']`). Round 2 (judge-opus, Important) found that deciding every filing on the newest revision diverges after a block edit, which moves `documents.content_hash` with no revision (`app/services/block_verbs.py:222,279`): `update_document` does not refuse a block-first row (`app/repositories/documents.py:123-135`), so a direct `file_document` caller can still re-file one, though `put_document` refuses it (`document_door.py:533-545`) and `scripts/reparse_documents.py` files through `put_document`. The hybrid rule in Contracts → Writer passes both race tests and `test_a_direct_filing_after_a_block_edit_compares_with_the_row`, which fails under the newest-revision-only rule (dry run, 2026-09-25).
- The race tests commit for real; their `document_filed` events stay under project `revisions-race` for the rest of the pytest session (the journal is append-only), as the work-log race tests leave theirs under `worklog-race`. The full suite stayed green with them (dry run above); a later test that counts every event would have to exclude that project.
- The only callers that file through `file_document` are `put_document`, `block_pipeline.ingest_documents` (no caller under `app/`), `scripts/reparse_documents.py` (via `put_document`, `force_reparse=True`) and `scripts/benchlib/span_harvest.py` (`rg 'ingest_document\(|file_document\('`, 2026-09-25). Block verbs write `documents.content` through `block_verbs`, never through the filing body, so they write no revision without any extra guard.
- Spec §10's revisions bullet ("unchanged, new and stale-hash puts write none") predates the post-image amendment of 2026-09-23 in §1 and §3, under which a new document's first revision equals its content. The plan follows §1 and §3; Task 7 amends §10 to match.
- Revision ids are minted by `app.utils.ids.new_id()` (UUIDv7); `(created_at, id)` is the keyset, and the cursor is a revision id looked up within the same document, so a cursor from another document is refused rather than silently paging someone else's history.
- `require_scope` call sites are pinned per file (`backend/tests/test_api_keys.py:962-985`: `documents.py` has 2), and the gated route set is pinned twice (`:1116-1130`, `:1181-1195`). The new routes reuse `_require_read`, so the count stays 2 and only the two sets grow.
- Register row 13 (open) asks for a manifest test of a uri equal to the prefix and for `documents.py`'s `require_scope` bindings to be pinned like `repos.py` and `memories.py`; Task 4 touches both files, so it discharges the row.
- Register row 40 (deferred to this increment) is the downgrade's missing `worklog_embeddings\_\_%` pattern (`0001_baseline.py:1745-1753`). No test ties the downgrade's patterns to `_TABLE_TEMPLATES` (`rg -l downgrade tests`, 2026-09-25); Task 1 adds one to `tests/test_partition_templates.py`, and the dry run confirmed master's baseline lacks the pattern, so the test is red before Task 1's edit. Ruling on plan review round 1's request for a real downgrade run on a disposable database: declined. The row is about a missing pattern, which the source test pins; the `DROP TABLE … CASCADE` loop that consumes the patterns is shared by all ten families and unchanged here, and no downgrade has ever run against a deployed database (the policy is drop and recreate).
- `darkmem_test_2` and `darkmem_test_3` exist on the dev Postgres (`SELECT datname FROM pg_database`, 2026-09-25); `CLAUDE.md` (Commands → Host environment) reserves `darkmem_test_2..5` for parallel lanes. A fresh dev volume creates only `darkmem`; if a pytest run fails to connect, create the database first: `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_test_2"`.
- The vault wall (`tests/test_block_retrieval.py`) forbids every module in `BLOCK_CHANNEL_MODULES` from each vault writer's import closure and runs a per-module promote scan over the set (`:370-401`, `:531`); Task 3 classifies `app.services.document_revisions` there, as the file's own rule asks of every module that reads document content. `tests/test_block_pipeline.py`'s closure is seeded from the filing paths (`:786-796`); the read module files nothing and imports only SQLAlchemy, so it is not a seed.
- `events.api_key_id` is served on the events read (`app/schemas/event_log.py:23`), so serving a revision's `api_key_id` exposes nothing a read already does not; `api_keys.id` is not the credential's `key_id` half (`0001_baseline.py:1240-1256`).
- The registries a new document door joins are the ones increment 2's Tasks 6–9 and commit `b32c574c` edited: `tests/test_api_keys.py` (two sets), `app/api/mcp/scopes.py` (set and docstring counts), `tests/test_mcp.py`, `app/services/prompt.py` (`test_every_registered_tool_is_named_in_the_instructions`), `app/services/content_surfaces.py`, `tests/test_api/test_rest_conformance.py`, `tests/test_door_parity.py` plus `docs/two-door-parity.md`, `CLAUDE.md`, `docs/runbook-exposed-deployment.md`, `docs/design/12-api-and-mcp-contract.md`, `docs/design/18-security-auth-and-trust.md` and `docs/wiki/introduction.md`. The SDK generator binds chosen verbs only, and no frontend file names a document route (`rg` over `frontend/src`, 2026-09-25).
- MCP tool functions stay directly callable after `@mcp.tool` (`tests/test_documents_keyed.py:97` calls `mcp_server.document_put`), and patching `server.async_session_factory` puts a tool on the test session (`:89-92`).
- `docs/two-door-parity.md` reads 90 surfaces, 32 two-door, 51 REST-only, 7 MCP-only; one two-door row makes it 91 and 33.
- Between Task 4 and Task 6 the enumeration guards (`test_rest_conformance`, `test_door_parity`, `test_content_surface_scoping`) fail by design: the doors exist before they are classified. Tasks 4 and 5 run targeted tests; Task 6 turns them green.
- `DocumentTargetUnresolved` escapes the read tools as a tool error today (`document_outline`, `document_get`: `server.py:1015-1115`); `document_revisions` follows its read siblings rather than the envelopes of the write tools.

## Task index

1. Revision columns and the downgrade pattern
2. Revision writer
3. Revision read service
4. REST revision routes
5. MCP revision tool
6. Guard registries
7. CLAUDE.md, runbook, design docs and spec

---

### Task 1: Revision columns and the downgrade pattern

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py:1553-1572` (the `document_revisions` DDL) and `:1730-1760` (the downgrade's family patterns)
- Modify: `backend/tests/test_inert_objects.py:47-49` (`INERT_TABLES`)
- Modify: `backend/tests/test_partition_templates.py` (one test after `test_every_template_has_aux_indexes`)
- Modify: `backend/tests/test_notes_schema.py` (one test before `test_blocks_carry_a_search_vector_that_blanks_source_types`)

**Interfaces:**
- Consumes: nothing.
- Produces: Contracts → Schema.

**Items:** 40, 48

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_partition_templates.py`, insert after `test_every_template_has_aux_indexes`:

```python


def test_the_baseline_downgrade_drops_every_family():
    """The downgrade names each family's children by pattern, since the set of
    fingerprints is unknown at migration time. A family missing from the list
    keeps its children through a downgrade, stripped of their foreign keys by
    the parents' CASCADE."""
    baseline = (
        Path(__file__).resolve().parent.parent
        / "migrations" / "versions" / "0001_baseline.py"
    ).read_text(encoding="utf-8")
    downgrade = baseline.split("def downgrade() -> None:", 1)[1]
    missing = sorted(
        parent for parent in _TABLE_TEMPLATES
        if f"LIKE '{parent}\\\\_\\\\_%'" not in downgrade
    )
    assert missing == []
```

(`Path` and `_TABLE_TEMPLATES` are already imported at the top of the file.)

In `backend/tests/test_notes_schema.py`, insert directly before the `@pytest.mark.asyncio` line above `async def test_blocks_carry_a_search_vector_that_blanks_source_types(session):`:

```python
@pytest.mark.asyncio
async def test_document_revisions_record_who_filed_and_page_newest_first(session):
    columns = {
        name: (data_type, nullable)
        for name, data_type, nullable in (await session.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'document_revisions'"
        ))).all()
    }
    assert columns["actor"] == ("text", "YES")
    assert columns["api_key_id"] == ("uuid", "YES")
    index = await session.scalar(text(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_document_revisions_document'"
    ))
    assert index.endswith("(document_id, created_at DESC, id DESC)")


```

- [ ] **Step 2: Run them to verify they fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_partition_templates.py tests/test_notes_schema.py -q`
Expected: FAIL — `assert ['worklog_embeddings'] == []`, and `KeyError: 'actor'` in the schema test.

- [ ] **Step 3: Edit the baseline**

In `backend/migrations/versions/0001_baseline.py`, replace

```python
    # Version history: a full post-image snapshot per commit, not a delta --
    # the serialiser already produces exactly this string on every mutation,
    # and a delta format would be a second representation to keep faithful.
    op.execute(
        """
        CREATE TABLE document_revisions (
            id           UUID NOT NULL,
            document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content      TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT document_revisions_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_revisions_document "
        "ON document_revisions (document_id, created_at DESC)"
    )
```

with

```python
    # Version history: a full post-image snapshot per commit, not a delta --
    # the serialiser already produces exactly this string on every mutation,
    # and a delta format would be a second representation to keep faithful.
    # `api_key_id` carries no foreign key for the reason `events.api_key_id`
    # carries none: keys are revoked, never deleted.
    op.execute(
        """
        CREATE TABLE document_revisions (
            id           UUID NOT NULL,
            document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content      TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            actor        TEXT,
            api_key_id   UUID,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT document_revisions_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_revisions_document "
        "ON document_revisions (document_id, created_at DESC, id DESC)"
    )
```

In `downgrade()`, replace the comment lines

```python
    # not known at migration time, so walk pg_tables for all NINE parent
    # patterns — the four that exist today, the four target-new families
    # (inventory F-17: the pre-baseline sweep covered only four and would
    # strand the rest) and the page family.
```

with

```python
    # not known at migration time, so walk pg_tables for all TEN parent
    # patterns — the four that exist today, the four target-new families
    # (inventory F-17: the pre-baseline sweep covered only four and would
    # strand the rest), the page family and the work-log family.
```

and replace the last pattern line

```python
                       OR tablename LIKE 'triple_embeddings\\_\\_%')
```

with

```python
                       OR tablename LIKE 'triple_embeddings\\_\\_%'
                       OR tablename LIKE 'worklog_embeddings\\_\\_%')
```

- [ ] **Step 4: Retire the inert entry**

In `backend/tests/test_inert_objects.py`, replace

```python
INERT_TABLES: dict[str, str] = {
    "document_revisions": "the version-history lane",
}
```

with

```python
# `document_revisions` is no longer here: the work-log lane's increment 3
# landed its first writer, `document_ingest`'s filing body, which writes the
# filed content as a revision whenever a filing creates a document or changes
# its `content_hash`.
#
# The set is EMPTY again, so the loops below skip rather than pass vacuously.
INERT_TABLES: dict[str, str] = {}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_partition_templates.py tests/test_inert_objects.py tests/test_notes_schema.py -q`
Expected: PASS, with the inert-table loops reported as skipped.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/tests/test_inert_objects.py backend/tests/test_partition_templates.py backend/tests/test_notes_schema.py
git commit -m "feat(schema): stamp who filed a document revision" -m "Adds actor and api_key_id to document_revisions, keys its index for
paging on (created_at, id), and gives the downgrade the work-log
family's pattern (register row 40). Regenerates the baseline: a deploy
drops and recreates the database."
```

### Task 2: Revision writer

**Files:**
- Modify: `backend/app/repositories/documents.py` (`__all__`, a statement after `_STRIP_BLOCKS` at `:137`, a function before `_span_literal` at `:296`)
- Modify: `backend/app/services/document_ingest.py:357-359` (after `insert_blocks`)
- Create: `backend/tests/test_document_revisions.py`

**Interfaces:**
- Consumes: Contracts → Schema (Task 1).
- Produces: Contracts → Writer, Test helpers.

**Items:** 48

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_document_revisions.py`:

```python
"""Document revisions: the filing writes them, both doors read them (spec 2026-09-23 §3)."""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.services.document_door import DocumentTooLarge, MAX_BLOCKS, put_document
from app.services.document_ingest import DocumentHashConflict

FINGERPRINT = "revisions-probe|3"


class StubEmbedder:
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], FINGERPRINT


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def _put(session, content, *, uri="superpowers/specs/a.md", **kwargs):
    return await put_document(
        session, StubEmbedder(), project="proj", uri=uri, content=content, **kwargs,
    )


async def _revisions(session, document_id):
    rows = await session.execute(
        text(
            "SELECT content, content_hash, actor, api_key_id FROM document_revisions "
            "WHERE document_id = CAST(:d AS uuid) ORDER BY created_at, id"
        ),
        {"d": str(document_id)},
    )
    return [tuple(row) for row in rows]


async def test_a_created_document_writes_its_first_revision(session):
    key_id = uuid.uuid4()
    filed = await _put(session, "# A\n\nFirst.\n", actor="k-probe", api_key_id=key_id)
    assert await _revisions(session, filed.document_id) == [
        ("# A\n\nFirst.\n", filed.content_hash, "k-probe", key_id),
    ]


async def test_a_changed_put_writes_one_more_and_the_newest_is_current(session):
    first = await _put(session, "# A\n\nFirst.\n")
    second = await _put(session, "# A\n\nSecond.\n")
    revisions = await _revisions(session, first.document_id)
    assert [r[1] for r in revisions] == [first.content_hash, second.content_hash]
    current = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"),
        {"d": first.document_id},
    )).scalar_one()
    assert revisions[-1][0] == current


async def test_an_unchanged_put_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    again = await _put(session, "# A\n\nFirst.\n")
    assert again.outcome == "unchanged"
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_stale_expected_hash_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    with pytest.raises(DocumentHashConflict):
        await _put(session, "# A\n\nSecond.\n", expected_hash="0" * 64)
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_put_refused_for_max_blocks_leaves_no_revision(session):
    first = await _put(session, "# A\n\nFirst.\n")
    with pytest.raises(DocumentTooLarge):
        await _put(session, "\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)))
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_forced_reparse_of_identical_content_writes_none(session):
    first = await _put(session, "# A\n\nFirst.\n")
    forced = await _put(session, "# A\n\nFirst.\n", force_reparse=True)
    assert forced.outcome == "updated"
    assert len(await _revisions(session, first.document_id)) == 1


async def test_a_bytes_source_writes_none(session):
    from app.services.document_ingest import BlockDraft, file_document

    as_text = await file_document(
        session, project="proj", uri="raw.md", content="raw",
        parse=lambda: [BlockDraft(text="raw")],
    )
    as_bytes = await file_document(
        session, project="proj", uri="raw.bin", content=b"\x00\x01",
        parse=lambda: [BlockDraft(text="raw")],
    )
    assert len(await _revisions(session, as_text.document_id)) == 1
    assert await _revisions(session, as_bytes.document_id) == []


# The `session` fixture shares one connection, so it cannot show two filings
# waiting on each other. These use the test engine directly, commit for real,
# and delete their documents afterwards; the `document_filed` events they
# journal cannot be deleted and are left under the race project.
RACE_PROJECT = "revisions-race"


@pytest_asyncio.fixture
async def committed(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    async with factory() as cleanup:
        await cleanup.execute(text("DELETE FROM documents WHERE project = :p"), {"p": RACE_PROJECT})
        await cleanup.commit()


async def _race_first_filings(committed, first: str, second: str) -> list[str]:
    from app.services.document_ingest import BlockDraft, file_document

    def filing(session, content):
        return file_document(
            session, project=RACE_PROJECT, uri="race.md", content=content,
            parse=lambda: [BlockDraft(text=content)],
        )

    async with committed() as winner, committed() as loser:
        filed = await filing(winner, first)
        late = asyncio.create_task(filing(loser, second))
        await asyncio.sleep(0.3)
        assert not late.done(), "the second filing must wait on the first one's row"
        await winner.commit()
        await late
        await loser.commit()
    async with committed() as check:
        rows = await check.execute(
            text(
                "SELECT content FROM document_revisions WHERE document_id = CAST(:d AS uuid) "
                "ORDER BY created_at, id"
            ),
            {"d": str(filed.document_id)},
        )
        return [row[0] for row in rows]


async def test_two_first_filings_of_the_same_content_write_one_revision(committed):
    assert await _race_first_filings(committed, "same", "same") == ["same"]


async def test_two_first_filings_of_different_content_write_two(committed):
    assert await _race_first_filings(committed, "first", "second") == ["first", "second"]


async def test_a_block_verb_edit_writes_none(session):
    from app.services.block_verbs import update_block

    filed = await _put(session, "# A\n\nFirst.\n")
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()
    await update_block(session, StubEmbedder(), block_id=block_id, text="Edited")
    assert len(await _revisions(session, filed.document_id)) == 1


async def test_a_direct_filing_after_a_block_edit_compares_with_the_row(session):
    """A block edit moves the row's hash and writes no revision, so from then on
    the newest revision is not the row. `put_document` refuses a block-first
    document; a direct `file_document` caller does not, and its revision
    follows the row's hash, never the history's."""
    from app.services.block_verbs import update_block
    from app.services.document_ingest import BlockDraft, file_document

    filed = await _put(session, "# A\n\nFirst.\n")
    block_id = (await session.execute(
        text(
            "SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
            "ORDER BY order_index LIMIT 1"
        ),
        {"d": filed.document_id},
    )).scalar_one()
    await update_block(session, StubEmbedder(), block_id=block_id, text="Edited")
    edited = (await session.execute(
        text("SELECT content FROM documents WHERE id = CAST(:d AS uuid)"), {"d": filed.document_id},
    )).scalar_one()

    def refile(content, **kwargs):
        return file_document(
            session, project="proj", uri="superpowers/specs/a.md", content=content,
            parse=lambda: [BlockDraft(text=content)], properties={}, **kwargs,
        )

    await refile(edited, force_reparse=True)
    assert len(await _revisions(session, filed.document_id)) == 1
    await refile("# A\n\nFirst.\n")
    assert [r[0] for r in await _revisions(session, filed.document_id)] == [
        "# A\n\nFirst.\n", "# A\n\nFirst.\n",
    ]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_document_revisions.py -q`
Expected: FAIL — all eleven tests find no revision (the bytes test fails on its text-filing control, both race tests find an empty list, and the block-edit test finds none after the first put).

- [ ] **Step 3: Add the repository insert**

In `backend/app/repositories/documents.py`, add `"insert_revision",` and `"latest_revision_hash",` to `__all__`, in that order, directly after `"insert_blocks",`. Directly after the line

```python
_STRIP_BLOCKS = text("DELETE FROM blocks WHERE document_id = CAST(:document_id AS uuid)")
```

insert

```python

# `clock_timestamp()`, not the column's `now()` default: two puts on one
# document serialise on its row lock, so the later writer can hold the earlier
# transaction start, and revisions order by `created_at`.
_INSERT_REVISION = text(
    "INSERT INTO document_revisions "
    "(id, document_id, content, content_hash, actor, api_key_id, created_at) "
    "VALUES (CAST(:id AS uuid), CAST(:document_id AS uuid), CAST(:content AS text), "
    "CAST(:content_hash AS text), CAST(:actor AS text), CAST(:api_key_id AS uuid), "
    "clock_timestamp())"
)

_LATEST_REVISION_HASH = text(
    "SELECT content_hash FROM document_revisions "
    "WHERE document_id = CAST(:document_id AS uuid) "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)
```

and directly before `def _span_literal(` insert

```python
async def insert_revision(
    session: AsyncSession,
    *,
    revision_id: UUID,
    document_id: UUID,
    content: str,
    content_hash: str,
    actor: str | None,
    api_key_id: UUID | None,
) -> None:
    await session.execute(
        _INSERT_REVISION,
        {
            "id": str(revision_id),
            "document_id": str(document_id),
            "content": content,
            "content_hash": content_hash,
            "actor": actor,
            "api_key_id": None if api_key_id is None else str(api_key_id),
        },
    )


async def latest_revision_hash(session: AsyncSession, document_id: UUID) -> str | None:
    return (await session.execute(
        _LATEST_REVISION_HASH, {"document_id": str(document_id)}
    )).scalar_one_or_none()


```

- [ ] **Step 4: Write the revision from the filing body**

In `backend/app/services/document_ingest.py`, replace

```python
    stripped = await documents_repo.strip_blocks(session, resolved_id)
    rows = _resolve_tree(parse())
    await documents_repo.insert_blocks(session, resolved_id, rows)
```

with

```python
    stripped = await documents_repo.strip_blocks(session, resolved_id)
    rows = _resolve_tree(parse())
    await documents_repo.insert_blocks(session, resolved_id, rows)

    # A post-image: the content this filing wrote, written only when the
    # filing changed the row's hash. A forced reparse of identical bytes
    # changed nothing a reader can see, and a bytes source has no text to keep.
    # A filing that resolved no row may still have updated one: losing a
    # first-filing race folds it onto the winner's row, whose prior hash it
    # never read. By here it holds that row's lock, so the winner's revision
    # has committed and is the prior hash; the upsert refuses a block-first
    # row, so no block edit sits between that revision and the row.
    if existing is not None:
        changed = existing.content_hash != content_hash
    else:
        changed = await documents_repo.latest_revision_hash(session, resolved_id) != content_hash
    if stored_content is not None and changed:
        await documents_repo.insert_revision(
            session,
            revision_id=new_id(),
            document_id=resolved_id,
            content=stored_content,
            content_hash=content_hash,
            actor=actor,
            api_key_id=api_key_id,
        )
```

(`new_id` is already imported from `app.utils.ids`.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest tests/test_document_revisions.py tests/test_document_door.py tests/test_document_cas.py tests/test_documents.py tests/test_block_pipeline.py tests/test_inert_objects.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/documents.py backend/app/services/document_ingest.py backend/tests/test_document_revisions.py
git commit -m "feat(documents): keep each filed content as a revision"
```

### Task 3: Revision read service

**Files:**
- Create: `backend/app/services/document_revisions.py`
- Modify: `backend/tests/test_block_retrieval.py` (`BLOCK_CHANNEL_MODULES`)
- Test: `backend/tests/test_document_revisions.py` (append)

**Interfaces:**
- Consumes: Contracts → Schema (Task 1), Writer and Test helpers (Task 2).
- Produces: Contracts → Read service.

**Items:** 48

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_document_revisions.py`:

```python


async def test_a_page_lists_newest_first_without_content_and_pages_back(session):
    from app.services.document_revisions import list_revisions

    hashes = [
        (await _put(session, f"# A\n\nVersion {n}.\n", actor="k-probe")).content_hash
        for n in range(3)
    ]
    document_id = (await _put(session, "# A\n\nVersion 2.\n")).document_id

    first = await list_revisions(session, document_id=document_id, limit=2)
    assert first["document_id"] == document_id
    assert [item["content_hash"] for item in first["items"]] == [hashes[2], hashes[1]]
    assert set(first["items"][0]) == {"id", "content_hash", "actor", "api_key_id", "created_at"}
    assert first["items"][0]["actor"] == "k-probe"
    assert first["next_before"] == first["items"][1]["id"]

    rest = await list_revisions(
        session, document_id=document_id, before=first["next_before"], limit=2,
    )
    assert [item["content_hash"] for item in rest["items"]] == [hashes[0]]
    assert rest["next_before"] is None


async def test_a_full_last_page_answers_no_cursor(session):
    from app.services.document_revisions import list_revisions

    filed = await _put(session, "# A\n\nOnly.\n")
    page = await list_revisions(session, document_id=filed.document_id, limit=1)
    assert len(page["items"]) == 1
    assert page["next_before"] is None


async def test_a_cursor_from_another_document_is_refused(session):
    from app.services.document_revisions import list_revisions

    a = await _put(session, "# A\n\nA.\n")
    b = await _put(session, "# B\n\nB.\n", uri="superpowers/specs/b.md")
    other = (await list_revisions(session, document_id=b.document_id))["items"][0]["id"]
    with pytest.raises(ValueError, match="names no revision"):
        await list_revisions(session, document_id=a.document_id, before=other)
    with pytest.raises(ValueError, match="not a revision id"):
        await list_revisions(session, document_id=a.document_id, before="nope")


@pytest.mark.parametrize("limit", [0, 201])
async def test_a_limit_out_of_range_is_refused(session, limit):
    from app.services.document_revisions import list_revisions

    with pytest.raises(ValueError, match="limit"):
        await list_revisions(session, document_id=uuid.uuid4(), limit=limit)


async def test_one_revision_carries_its_content_and_only_under_its_document(session):
    from app.services.document_revisions import get_revision, list_revisions

    a = await _put(session, "# A\n\nFirst.\n")
    b = await _put(session, "# B\n\nB.\n", uri="superpowers/specs/b.md")
    revision_id = (await list_revisions(session, document_id=a.document_id))["items"][0]["id"]

    one = await get_revision(session, document_id=a.document_id, revision_id=revision_id)
    assert one["content"] == "# A\n\nFirst.\n"
    assert one["document_id"] == a.document_id
    assert one["content_hash"] == a.content_hash
    assert await get_revision(session, document_id=b.document_id, revision_id=revision_id) is None
```

- [ ] **Step 2: Run them to verify they fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_document_revisions.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.document_revisions'` in the five new tests.

- [ ] **Step 3: Write the service**

Create `backend/app/services/document_revisions.py`:

```python
"""A document's revisions, newest first: every content a filing wrote.

The writer is `document_ingest`'s filing body; this module only reads, and
both doors call it (`GET /api/v1/documents/{id}/revisions` and its
`/{revision_id}` read, and the MCP `document_revisions` tool). A page carries
no content because one revision can be a megabyte; a caller fetches the
revision it wants by id and computes any diff itself. Neither function
confirms the document exists: the doors resolve it first, through
`document_door.resolve_document_target`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["DEFAULT_LIMIT", "MAX_LIMIT", "get_revision", "list_revisions"]

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

_CURSOR = text(
    "SELECT created_at, id FROM document_revisions "
    "WHERE id = CAST(:id AS uuid) AND document_id = CAST(:document_id AS uuid)"
)

_PAGE = text(
    """
    SELECT CAST(id AS text) AS id, content_hash, actor,
           CAST(api_key_id AS text) AS api_key_id, created_at
    FROM document_revisions
    WHERE document_id = CAST(:document_id AS uuid)
      AND (CAST(:before_at AS timestamptz) IS NULL
           OR (created_at, id) < (CAST(:before_at AS timestamptz), CAST(:before_id AS uuid)))
    ORDER BY created_at DESC, id DESC
    LIMIT CAST(:limit AS integer)
    """
)

_ONE = text(
    """
    SELECT CAST(id AS text) AS id, content_hash, actor,
           CAST(api_key_id AS text) AS api_key_id, created_at, content
    FROM document_revisions
    WHERE id = CAST(:id AS uuid) AND document_id = CAST(:document_id AS uuid)
    """
)


def _serialize(row) -> dict[str, Any]:
    out = dict(row)
    out["created_at"] = row["created_at"].isoformat()
    return out


def _uuid(value: UUID | str, name: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValueError(f"{name} is not a revision id: {value!r}") from error


async def list_revisions(
    session: AsyncSession,
    *,
    document_id: UUID | str,
    before: UUID | str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """One page of revisions without content, newest first.

    `before` is the last revision of the previous page (its `next_before`).
    Raises `ValueError` for a limit outside 1-`MAX_LIMIT`, or for a `before`
    that names no revision of this document.
    """
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, not {limit}")
    before_at = before_id = None
    if before is not None:
        cursor = (await session.execute(
            _CURSOR,
            {"id": str(_uuid(before, "before")), "document_id": str(document_id)},
        )).first()
        if cursor is None:
            raise ValueError(f"before names no revision of this document: {before}")
        before_at, before_id = cursor.created_at, str(cursor.id)
    rows = (await session.execute(
        _PAGE,
        {
            "document_id": str(document_id),
            "before_at": before_at,
            "before_id": before_id,
            "limit": limit + 1,
        },
    )).mappings().all()
    items = [_serialize(row) for row in rows[:limit]]
    return {
        "document_id": str(document_id),
        "items": items,
        "next_before": items[-1]["id"] if len(rows) > limit else None,
    }


async def get_revision(
    session: AsyncSession, *, document_id: UUID | str, revision_id: UUID | str
) -> dict[str, Any] | None:
    """One revision with its content, or `None` when it is not this document's."""
    row = (await session.execute(
        _ONE,
        {"id": str(_uuid(revision_id, "revision_id")), "document_id": str(document_id)},
    )).mappings().first()
    if row is None:
        return None
    return {"document_id": str(document_id), **_serialize(row)}
```

In `backend/tests/test_block_retrieval.py`, add the new module to `BLOCK_CHANNEL_MODULES` by replacing

```python
    # Writes blocks through page_door._insert_page.
    "app.services.page_import",
})
```

with

```python
    # Writes blocks through page_door._insert_page.
    "app.services.page_import",
    # Reads the contents a document's filings wrote, which is document content
    # a vault writer must not reach any more than a block row.
    "app.services.document_revisions",
})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_document_revisions.py tests/test_block_retrieval.py tests/test_block_pipeline.py -q`
Expected: PASS. `test_block_retrieval.py` now forbids `app.services.document_revisions` from every vault writer's import closure and runs its per-module promote scan over it; the file's existing negative controls prove those scans can fail.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_revisions.py backend/tests/test_block_retrieval.py backend/tests/test_document_revisions.py
git commit -m "feat(documents): read a document's revisions"
```

### Task 4: REST revision routes

**Files:**
- Modify: `backend/app/api/routes/documents.py` (module docstring route list, the import at `:100`, the keyed-routes comment at `:114-117`, models and two routes before the list route at `:528`)
- Modify: `backend/tests/test_api_keys.py` (the two pinned route sets; the binding pins at `:982-984`)
- Test: `backend/tests/test_documents_keyed.py` (append)

**Interfaces:**
- Consumes: Contracts → Read service (Task 3).
- Produces: Contracts → REST.

**Items:** 13, 48

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_documents_keyed.py`:

```python


async def test_the_manifest_lists_a_document_filed_at_the_prefix_itself(client, session):
    read = await _key(session, "read")
    await _document(session, uri="superpowers")
    await _document(session, uri="superpowersx/a.md")
    listed = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": "superpowers"}, headers=read,
    )
    assert listed.status_code == 200
    assert [i["uri"] for i in listed.json()["items"]] == ["superpowers"]


async def test_a_read_key_lists_revisions_and_reads_one(client, session, scripted_embedder):
    capture_name = f"k-{uuid.uuid4().hex[:6]}"
    capture_row, capture_credential = await issue_key(session, name=capture_name, scopes=["capture"])
    capture = {"Authorization": f"Bearer {capture_credential}"}
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/plans/r.md", "content": "# R\n\nOne.\n"}
    first = (await client.post(V1, json=body, headers=capture)).json()
    second = (await client.post(V1, json={**body, "content": "# R\n\nTwo.\n"}, headers=capture)).json()
    document_id = first["document_id"]

    listed = await client.get(f"{V1}/{document_id}/revisions", headers=read)
    assert listed.status_code == 200, listed.text
    page = listed.json()
    assert [i["content_hash"] for i in page["items"]] == [second["content_hash"], first["content_hash"]]
    assert page["items"][0]["actor"] == capture_name
    assert page["items"][0]["api_key_id"] == str(capture_row.id)
    assert "content" not in page["items"][0]
    assert page["next_before"] is None

    older = await client.get(
        f"{V1}/{document_id}/revisions", params={"before": page["items"][0]["id"]}, headers=read,
    )
    assert [i["content_hash"] for i in older.json()["items"]] == [first["content_hash"]]

    one = await client.get(f"{V1}/{document_id}/revisions/{page['items'][1]['id']}", headers=read)
    assert one.status_code == 200
    assert one.json()["content"] == "# R\n\nOne.\n"
    assert one.json()["document_id"] == document_id


async def test_the_revision_routes_refuse_what_names_nothing(client, session, scripted_embedder):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    a = (await client.post(V1, json={"project": "proj", "uri": "a.md", "content": "# A\n"}, headers=capture)).json()
    b = (await client.post(V1, json={"project": "proj", "uri": "b.md", "content": "# B\n"}, headers=capture)).json()
    b_revision = (await client.get(f"{V1}/{b['document_id']}/revisions", headers=read)).json()["items"][0]["id"]

    assert (await client.get(f"{V1}/{uuid.uuid4()}/revisions", headers=read)).status_code == 404
    assert (await client.get(f"{V1}/{a['document_id']}/revisions/{b_revision}", headers=read)).status_code == 404
    assert (await client.get(
        f"{V1}/{a['document_id']}/revisions", params={"before": b_revision}, headers=read,
    )).status_code == 422
    assert (await client.get(
        f"{V1}/{a['document_id']}/revisions", params={"limit": 201}, headers=read,
    )).status_code == 422
    assert (await client.get(f"{V1}/{a['document_id']}/revisions", headers=capture)).status_code == 403
    assert (await client.get(f"{V1}/{a['document_id']}/revisions")).status_code == 401
```

In `backend/tests/test_api_keys.py`, in **both** pinned sets (`test_exactly_the_intended_routes_are_scope_gated` and `expected` in `test_the_assertion_catches_delete_repo_reusing_the_binding`), add directly after `("GET", "/api/v1/documents/manifest"),`:

```python
            ("GET", "/api/v1/documents/{document_id}/revisions"),
            ("GET", "/api/v1/documents/{document_id}/revisions/{revision_id}"),
```

and in `test_key_reach_is_pinned_to_the_call_sites_that_were_argued_for`, directly after the line `        assert '_require_read = require_scope("read")' in memories_source`, add:

```python
        documents_source = (APP_ROOT / "api" / "routes" / "documents.py").read_text(encoding="utf-8")
        assert '_require_capture = require_scope("capture")' in documents_source
        assert '_require_read = require_scope("read")' in documents_source
```

- [ ] **Step 2: Run them to verify they fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_documents_keyed.py tests/test_api_keys.py -q`
Expected: FAIL — the two revision tests get 404 from the missing routes, and the two pinned sets lack the new routes. The manifest test and the binding pins pass already (they pin current behaviour, register row 13).

- [ ] **Step 3: Add the routes**

In `backend/app/api/routes/documents.py`:

In the module docstring's route list, directly after the line `  - GET    /api/v1/documents/manifest`, add:

```text
  - GET    /api/v1/documents/{document_id}/revisions
  - GET    /api/v1/documents/{document_id}/revisions/{revision_id}
```

Directly after `from app.services.document_ingest import DocumentHashConflict`, add:

```python
from app.services import document_revisions
```

Replace the comment

```python
# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the by-uri read and the
# manifest. Every other document route stays login-only; widening one is a
# decision about what a leaked key can read or erase, made per route.
```

with

```python
# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the by-uri read, the
# manifest and the two revision reads. Every other document route stays
# login-only; widening one is a decision about what a leaked key can read or
# erase, made per route.
```

Directly before the line `@router.get("", response_model=DocumentListResponse)`, insert:

```python
class DocumentRevisionItem(BaseModel):
    id: str
    content_hash: str
    actor: str | None
    api_key_id: str | None
    created_at: datetime


class DocumentRevisionListResponse(BaseModel):
    document_id: str
    items: list[DocumentRevisionItem]
    next_before: str | None


class DocumentRevisionResponse(DocumentRevisionItem):
    document_id: str
    content: str


@router.get("/{document_id}/revisions", response_model=DocumentRevisionListResponse)
async def list_document_revisions_route(
    document_id: UUID,
    before: UUID | None = Query(None),
    limit: int = Query(
        document_revisions.DEFAULT_LIMIT, ge=1, le=document_revisions.MAX_LIMIT
    ),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentRevisionListResponse:
    """A document's revisions newest first, without content; page back with
    `next_before`. 404 when the document does not exist, 422 when `before`
    names no revision of it."""
    target = await _resolve_target(session, document_id=document_id, project=None, uri=None)
    try:
        page = await document_revisions.list_revisions(
            session, document_id=target, before=before, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return DocumentRevisionListResponse(**page)


@router.get(
    "/{document_id}/revisions/{revision_id}", response_model=DocumentRevisionResponse
)
async def get_document_revision_route(
    document_id: UUID,
    revision_id: UUID,
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentRevisionResponse:
    """One revision with the content it filed. 404 when the document does not
    exist or the revision is not one of its own."""
    target = await _resolve_target(session, document_id=document_id, project=None, uri=None)
    found = await document_revisions.get_revision(
        session, document_id=target, revision_id=revision_id,
    )
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no revision {revision_id} in document {target}"
        )
    return DocumentRevisionResponse(**found)


```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_documents_keyed.py tests/test_api_keys.py tests/test_document_routes.py tests/test_document_revisions.py -q`
Expected: PASS. (The enumeration guards stay red until Task 6.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_keyed.py backend/tests/test_api_keys.py
git commit -m "feat(documents): serve revisions over REST"
```

### Task 5: MCP revision tool

**Files:**
- Modify: `backend/app/api/mcp/server.py` (one tool between `document_get` and `document_delete`, before the `@mcp.tool` at `:1117`)
- Modify: `backend/app/api/mcp/scopes.py` (`READ_TOOLS` at `:88`; the two counts in the docstring at `:10` and `:21`)
- Modify: `backend/tests/test_mcp.py:46` (`EXPECTED_TOOLS`)
- Modify: `backend/app/services/prompt.py:731` (the documents tool list)
- Test: `backend/tests/test_document_revisions.py` (append)

**Interfaces:**
- Consumes: Contracts → Read service (Task 3), Test helpers (Task 2).
- Produces: Contracts → MCP.

**Items:** 48

**Implementer:** dr-superpowers:impl-opus-low
**Executor:** codex gpt-6-sol / high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_document_revisions.py`:

```python


@pytest.fixture
def mcp_server(session, monkeypatch):
    from contextlib import asynccontextmanager

    import app.api.mcp.server as server

    @asynccontextmanager
    async def _on_the_test_session():
        yield session

    monkeypatch.setattr(server, "async_session_factory", lambda: _on_the_test_session())
    return server


async def test_the_tool_lists_by_uri_pages_back_and_fetches_one(session, mcp_server):
    import json

    first = await _put(session, "# A\n\nOne.\n")
    second = await _put(session, "# A\n\nTwo.\n")

    page = json.loads(await mcp_server.document_revisions(
        project="proj", uri="superpowers/specs/a.md", limit=1,
    ))
    assert [i["content_hash"] for i in page["items"]] == [second.content_hash]
    older = json.loads(await mcp_server.document_revisions(
        document_id=first.document_id, before=page["next_before"], limit=500,
    ))
    assert [i["content_hash"] for i in older["items"]] == [first.content_hash]

    one = json.loads(await mcp_server.document_revisions(
        document_id=first.document_id, revision_id=older["items"][0]["id"],
    ))
    assert one["content"] == "# A\n\nOne.\n"
    missing = await mcp_server.document_revisions(
        document_id=first.document_id, revision_id=str(uuid.uuid4()),
    )
    assert json.loads(missing) is None


async def test_the_tool_refuses_a_document_that_does_not_exist(session, mcp_server):
    from app.services.document_door import DocumentTargetUnresolved

    with pytest.raises(DocumentTargetUnresolved):
        await mcp_server.document_revisions(project="proj", uri="nowhere.md")


async def test_both_doors_serve_the_same_page(client, auth_headers, session, mcp_server):
    import json

    filed = await _put(session, "# A\n\nOne.\n", actor="k-probe")
    await _put(session, "# A\n\nTwo.\n")
    rest = (await client.get(
        f"/api/v1/documents/{filed.document_id}/revisions", headers=auth_headers,
    )).json()
    tool = json.loads(await mcp_server.document_revisions(document_id=filed.document_id))
    assert [i["id"] for i in rest["items"]] == [i["id"] for i in tool["items"]]
    assert [i["actor"] for i in rest["items"]] == [None, "k-probe"]
    assert rest["next_before"] == tool["next_before"] is None
```

In `backend/tests/test_mcp.py`, add `    "document_revisions",` to `EXPECTED_TOOLS` directly after `    "document_put",`.

- [ ] **Step 2: Run them to verify they fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_document_revisions.py tests/test_mcp.py -q`
Expected: FAIL — `AttributeError: module 'app.api.mcp.server' has no attribute 'document_revisions'`, and the roster test names `document_revisions` as missing.

- [ ] **Step 3: Add the tool**

In `backend/app/api/mcp/server.py`, insert directly before the `@mcp.tool(` that decorates `document_delete` (its description begins `"Delete a document, its blocks and its vectors.`):

```python
@mcp.tool(
    description=(
        "List a document's revisions newest first -- each content a put filed, "
        "with its content_hash, who filed it and when, but no content -- or "
        "fetch one with its content by revision_id. Page back by passing the "
        "answer's next_before as before; limit 1-200. Name the document by "
        "document_id, or by the project and uri it was filed under. null when "
        "revision_id names no revision of that document."
    )
)
async def document_revisions(
    document_id: str | None = None,
    project: str | None = None,
    uri: str | None = None,
    revision_id: str | None = None,
    before: str | None = None,
    limit: int = 50,
) -> str:
    from app.services import document_revisions as revisions
    from app.services.document_door import resolve_document_target

    async with async_session_factory() as session:
        target = await resolve_document_target(
            session, document_id=document_id, project=project, uri=uri,
        )
        if revision_id is not None:
            found = await revisions.get_revision(
                session, document_id=target, revision_id=revision_id,
            )
            return json.dumps(found)
        page = await revisions.list_revisions(
            session,
            document_id=target,
            before=before,
            limit=max(1, min(limit, revisions.MAX_LIMIT)),
        )
    return json.dumps(page)


```

In `backend/app/api/mcp/scopes.py`, add `    "document_revisions",` to `READ_TOOLS` directly after `    "document_outline",`, and in the module docstring replace `statement of all 47 tools - is 47 chances` with `statement of all 48 tools - is 48 chances` and ``` ``TOOL_SCOPES`` names all 47 rather``` with ``` ``TOOL_SCOPES`` names all 48 rather```.

In `backend/app/services/prompt.py`, insert directly after the line

```python
        "- **document_get** — one document by id, or by `(project, uri)`.\n"
```

the lines

```python
        "- **document_revisions** — a document's filed versions, newest first; "
        "one with its content by `revision_id`.\n"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest tests/test_document_revisions.py tests/test_mcp.py tests/test_mcp_auth.py tests/test_prompt_agent_instructions.py -q`
Expected: PASS. (The enumeration guards stay red until Task 6.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/server.py backend/app/api/mcp/scopes.py backend/tests/test_mcp.py backend/app/services/prompt.py backend/tests/test_document_revisions.py
git commit -m "feat(documents): serve revisions over MCP"
```

### Task 6: Guard registries

**Files:**
- Modify: `backend/app/services/content_surfaces.py:644` (`ROUTES_WITHOUT_MEMORY_CONTENT`) and `:977` (`MCP_TOOLS_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`)
- Modify: `backend/tests/test_door_parity.py:593` (`PARITY_TABLE`)
- Modify: `docs/two-door-parity.md` (generated table and headline counts)

**Interfaces:**
- Consumes: Contracts → REST (Task 4), MCP (Task 5).
- Produces: Contracts → Parity.

**Items:** 48

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Run the guards to see them fail**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py -q`
Expected: FAIL — each names the two `/revisions` routes or `document_revisions` as unclassified.

- [ ] **Step 2: Classify the doors**

In `backend/app/services/content_surfaces.py`, insert directly after `    "GET /api/v1/documents/manifest",`:

```python
    # A document's revisions: the contents its filings wrote, with hash, actor
    # and time. Document content crosses, never a `memories` row.
    "GET /api/v1/documents/{document_id}/revisions",
    "GET /api/v1/documents/{document_id}/revisions/{revision_id}",
```

and insert `    "mcp:document_revisions",` directly after `    "mcp:document_get",`.

In `backend/tests/test_api/test_rest_conformance.py`, insert directly after `    ("GET", "/api/v1/documents/manifest"): 200,`:

```python
    ("GET", "/api/v1/documents/{document_id}/revisions"): 200,
    ("GET", "/api/v1/documents/{document_id}/revisions/{revision_id}"): 200,
```

In `backend/tests/test_door_parity.py`, insert this row into `PARITY_TABLE` directly before the `Surface(` whose `name="memory.capture"` (it follows the `documents.manifest` row):

```python
    Surface(
        name="documents.revisions",
        status=TWO_DOOR,
        rest=(
            ("GET", f"{V1}/documents/{{document_id}}/revisions"),
            ("GET", f"{V1}/documents/{{document_id}}/revisions/{{revision_id}}"),
        ),
        mcp=("document_revisions",),
        note=(
            "Both doors call one document_revisions service, so paging, the "
            "no-content page and the refusals cannot drift, and both admit a "
            "read-scoped key: the dr-superpowers mirror reads history over REST. "
            "Stated wire asymmetries: the routes name the document by id while "
            "the tool also takes (project, uri); REST serves the page and the "
            "single revision at two paths where the tool dispatches on "
            "revision_id; a revision the document does not own is a 404 on the "
            "route and null from the tool; and the route refuses a limit above "
            "200 with a 422 while the tool clamps it."
        ),
    ),
```

- [ ] **Step 3: Regenerate the parity doc**

From `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown
doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8")
EOF
sed -i 's/^\*\*90 surfaces: 32 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent\.\*\*$/**91 surfaces: 33 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent.**/' ../docs/two-door-parity.md
git -C /root/repositories/darkmem diff --stat -- docs/two-door-parity.md
```

Expected: the diff shows one added table row and the changed headline line, nothing else (`2 insertions(+), 1 deletion(-)`).

- [ ] **Step 4: Run the guards to verify they pass**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/content_surfaces.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "test(guards): classify the document revision doors"
```

### Task 7: CLAUDE.md, runbook, design docs and spec

**Files:**
- Modify: `CLAUDE.md` (MCP scopes counts, the keyed document-route sentence, the Documents section)
- Modify: `docs/runbook-exposed-deployment.md` (scope table and MCP counts)
- Modify: `docs/design/12-api-and-mcp-contract.md`, `docs/design/18-security-auth-and-trust.md`, `docs/wiki/introduction.md` (tool counts)
- Modify: `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` (status line, §3 and §10 amendments)

**Interfaces:**
- Consumes: Contracts → REST (Task 4), MCP (Task 5), Parity (Task 6).
- Produces: nothing later tasks consume.

**Items:** 48

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Apply the edits**

Save this script as `/tmp/inc3-docs.py` and run it from the repository root with `python3 /tmp/inc3-docs.py`. Each replacement asserts its text occurs exactly once, so a stale file fails loudly rather than being half-edited.

```python
from pathlib import Path


def edit(path, pairs):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60], s.count(old))
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


edit("CLAUDE.md", [
    ("(`app/api/mcp/scopes.py`, `TOOL_SCOPES`, 47 tools):",
     "(`app/api/mcp/scopes.py`, `TOOL_SCOPES`, 48 tools):"),
    ("- `read` (29).", "- `read` (30)."),
    ("""ordinary login auth, like every document route except the three a
dr-superpowers mirror syncs through (filing, the by-uri read and the
manifest, which admit a scoped key).""",
     """ordinary login auth, like every document route except the five a
dr-superpowers mirror syncs through (filing, the by-uri read, the manifest
and the two revision reads, which admit a scoped key)."""),
    ("""- **An edit re-embeds the whole document**: re-filing strips every block and
  inserts a fresh set with new ids. There is no diffing and no per-block
  identity across a re-file.
""",
     """- **An edit re-embeds the whole document**: re-filing strips every block and
  inserts a fresh set with new ids. There is no diffing and no per-block
  identity across a re-file.
- **Revisions** (`document_revisions`): `document_ingest`'s filing body, inside
  its SAVEPOINT, writes the filed `content` as a post-image row stamped with
  `actor`, `api_key_id` and `clock_timestamp()` whenever the filing changes
  the row's `content_hash` (a filing that resolved no row compares with the
  newest revision under the row lock, so two racing first filings of one
  content write one), so the newest revision equals `content` until a block
  verb edits it. An unchanged re-push, a stale `expected_hash`, a forced reparse
  of identical bytes, a bytes source and every block verb write none, and a
  refused put rolls its revision back. Reads come newest first, pages carry
  no content and page back through `before` (a revision id):
  `GET /api/v1/documents/{id}/revisions` and `.../revisions/{revision_id}`
  (both admit a read key) and MCP `document_revisions` (by id or
  `(project, uri)`; `revision_id` fetches one with its content). Revisions
  cascade with their document.
"""),
])

edit("docs/runbook-exposed-deployment.md", [
    ("`GET /documents/by-uri`, `GET /documents/manifest`, `GET /worklog/resume`",
     "`GET /documents/by-uri`, `GET /documents/manifest`, `GET /documents/{id}/revisions`, `GET /documents/{id}/revisions/{revision_id}`, `GET /worklog/resume`"),
    ("of its 47 tools, 15 require `capture`, 29 require",
     "of its 48 tools, 15 require `capture`, 30 require"),
    ("a `read`-scoped key reaches the 29 readers.",
     "a `read`-scoped key reaches the 30 readers."),
])

edit("docs/design/12-api-and-mcp-contract.md", [
    ("`read` covers 29 readers", "`read` covers 30 readers"),
    ("the full 47-tool catalogue", "the full 48-tool catalogue"),
])

edit("docs/design/18-security-auth-and-trust.md", [
    ("of the 47 tools, 15 require `capture`, 29 require `read`",
     "of the 48 tools, 15 require `capture`, 30 require `read`"),
])

edit("docs/wiki/introduction.md", [
    ("the agent-facing surface, 47 tools covering memory,",
     "the agent-facing surface, 48 tools covering memory,"),
])

edit("docs/superpowers/specs/2026-09-23-work-log-lane-design.md", [
    (""""Amended 2026-09-23" below. Increment 1 done; increment 2 planned
(`docs/superpowers/plans/2026-09-25-work-log-increment-2-search.md`).""",
     """"Amended 2026-09-23" below. Increments 1 and 2 done; increment 3 planned
(`docs/superpowers/plans/2026-09-25-work-log-increment-3-revisions.md`)."""),
    ("""revision rolls back with the filing, so a refused or failed put never leaves a
revision behind. Revisions live as long as their document.""",
     """revision rolls back with the filing, so a refused or failed put never leaves a
revision behind. Revisions live as long as their document. Amended 2026-09-25:
`put_document` and `file_document` already carry `api_key_id`, so the write
lands in `file_document`'s body, inside the filing's own savepoint. "Changes
its `content_hash`" is decided against the resolved row's hash, or, when the
filing resolved no row, against the document's newest revision read under the
row lock, so two racing first filings of one content write one revision; a
forced reparse of identical bytes writes none."""),
    ("""- **Revisions:** changed put writes one revision; unchanged, new and stale-hash
  puts write none; a put refused for `MAX_BLOCKS` leaves no revision.""",
     """- **Revisions:** a new put and a changed put each write one revision
  (amended 2026-09-25 to the post-image rule of §1 and §3); unchanged,
  stale-hash, forced-reparse and bytes filings and block verbs write none; a
  put refused for `MAX_BLOCKS` leaves no revision."""),
])
```

Then delete the script: `rm /tmp/inc3-docs.py`.

- [ ] **Step 2: Run the guard leg**

Run, from `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  timeout 1200 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS. Then, from the repository root (`cd /root/repositories/darkmem`), re-read by hand the prose counts the leg does not cover: `docs/two-door-parity.md`'s headline (91 / 33), `CLAUDE.md`'s tool count (48, read 30) and `rg -n '\b47\b' CLAUDE.md docs/runbook-exposed-deployment.md docs/design/12-api-and-mcp-contract.md docs/design/18-security-auth-and-trust.md docs/wiki/introduction.md backend/app/api/mcp/scopes.py` (expected: no tool count left at 47).

- [ ] **Step 3: Run the full backend suite**

Run, from `backend/`: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 2400 .venv/bin/python -m pytest -q`
Expected: PASS, with no failure.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/runbook-exposed-deployment.md docs/design/12-api-and-mcp-contract.md docs/design/18-security-auth-and-trust.md docs/wiki/introduction.md docs/superpowers/specs/2026-09-23-work-log-lane-design.md
git commit -m "docs(documents): document revisions and the counts"
```
