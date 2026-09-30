# Work-log lane, increment 1: store and verbs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the work-log store (workstreams and their append-only entries) with append, resume, list, update and purge on both doors, plus the keyed document routes and manifest the dr-superpowers mirror needs.

**Architecture:** Two new baseline tables behind one service module, `app/services/worklog.py`, which a REST router and six MCP tools call without logic of their own. Entries are ordered by an identity column, journaled only at workstream lifecycle, and firewalled from memories. Document put/get opt into API keys through `require_scope`, and a manifest route serves `{uri, content_hash}` for sync.

**Tech Stack:** FastAPI, SQLAlchemy 2 async over asyncpg, Postgres 17, Alembic (single regenerated baseline), MCP SDK `mcp==2.1.1`, pytest (asyncio auto mode), TypeScript (one frontend map).

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** inline — `claude --model sonnet --effort high` — every task is delegated (four heavy, one four-band, four on the Codex lane), so the controller implements nothing itself; no task is heavy by majority.

**Plan review:** 2026-09-23 — dr-superpowers:judge-opus — executability 15 / coherence 17 / coverage 16 / assumptions 15 (round 2)

> **External executors:** codex

## Global Constraints

- Entry kinds are exactly `checkpoint`, `ledger`, `note`; workstream states are exactly `open`, `closed`.
- `worklog_entries.body`: 1 to 65,536 characters. `properties` on both tables: `pg_column_size <= 16384` in the database, and at most 12,288 bytes of encoded JSON at the schema layer.
- An append carries 1 to 100 entries in one transaction. Resume answers the latest checkpoint, the 50 newest notes (with `notes_truncated`), and the last 20 ledger entries.
- `workstreams.key`: 1 to 200 characters; `title`: at most 500. `UNIQUE (project, key)` is the constraint `ux_workstreams_project_key`.
- A `ledger` entry's body is the exact text the client appended, newlines included; the server never re-splits it.
- Entry order is `seq` (a `BIGINT GENERATED ALWAYS AS IDENTITY`), never `created_at`.
- The run key resolves exactly as checkpoints resolve it (`resolve_checkpoint_origin`, client-source fallback `"worklog"`); an undeclared run is refused (422 on REST, an error from the tool).
- No entry body and no properties value ever enter an `events` payload; lifecycle events carry `{"key": <key>}` (purge adds `"entries": <count>`).
- Scopes: capture = `worklog_append`, `worklog_update`; read = `worklog_resume`, `worklog_workstreams`, `worklog_entries`; admin = `worklog_purge`. REST uses the same scopes through `require_scope`.
- Purge is strict-journal: `workstream_purged` must land (the `record_event` return is `True`) before the `DELETE`, or the delete is refused with `WorklogJournalWriteFailed`.
- Nothing in the lane is extracted, embedded into memory retrieval, or imported by `app.services.pipeline`.
- `session_checkpoints`, `checkpoint_save` and `checkpoint_latest` stay untouched in this increment; their removal is increment 6's (spec §9, amended 2026-09-23).
- Tests run from `backend/` with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` against the dev-compose Postgres (`docker compose -f docker-compose.dev.yml up -d postgres` from the repo root when it is down).
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative. Never push; never `--no-verify`.

## Contracts

**Tables** (Task 1): `workstreams (id, project, key, title, client, state, closed_at, retain, properties, last_entry_at, created_at, updated_at)`; `worklog_entries (id, seq, workstream_id, run_key, kind, body, properties, search_vector, created_at)`.

**Models** (Task 1, `app/models/worklog.py`): `Workstream`, `WorklogEntry` (`search_vector` is `Computed`, `seq` is `Identity(always=True)`).

**Events** (Task 2, `app/services/events.py`): event types `workstream_opened`, `workstream_closed`, `workstream_reopened`, `workstream_purged`; object type `workstream`.

**Service** (Tasks 3–4, `app/services/worklog.py`):

- Constants: `KINDS`, `MAX_BODY_CHARS = 65_536`, `MAX_PROPERTIES_BYTES = 12_288`, `MAX_ENTRIES_PER_APPEND = 100`, `RESUME_LEDGER_TAIL = 20`, `RESUME_NOTES_CAP = 50`, `DOOR_SOURCE = "worklog"`. Every `record_event` call passes its event type as a string literal (`event_type="workstream_opened"`, ...), so the taxonomy scan resolves it.
- Exceptions: `WorkstreamNotFound(LookupError)`, `WorklogRejected(ValueError)` (a database CHECK refused the write; nothing kept), `WorklogJournalWriteFailed(RuntimeError)`.
- `properties_size(value: dict) -> int`
- `AppendResult(workstream: Workstream, entry_ids: list[UUID])`
- `async append(session, *, project, key, run_key, entries: list[dict], title=None, client=None, properties=None, actor=None, api_key_id=None) -> AppendResult` — each entry dict has `kind`, `body`, optional `properties`.
- `async get_workstream(session, *, project, key, for_update=False) -> Workstream | None`
- `async get_workstream_by_id(session, workstream_id, *, for_update=False) -> Workstream | None`
- `async update_workstream(session, workstream_id, *, state=None, retain=None, title=None, properties=None, actor=None, api_key_id=None) -> Workstream` — raises `WorkstreamNotFound`.
- `async purge_workstream(session, workstream_id, *, actor=None, api_key_id=None) -> int` — returns the entry count; raises `WorkstreamNotFound`, `WorklogJournalWriteFailed`.
- `serialize_workstream(ws) -> dict`, `serialize_entry(entry) -> dict` — JSON-safe (ids as strings, datetimes ISO 8601).
- `async resume(session, *, project, key) -> dict | None` — `{workstream, checkpoint, notes, notes_truncated, ledger}`.
- `async list_workstreams(session, *, project, state=None, before=None, limit=50) -> dict` — `{items, next_before}`, newest-created first, keyset on `(created_at, id)`; `before` is an opaque cursor string; a malformed one raises `ValueError`.
- `async list_entries(session, *, workstream_id, kind=None, since=None, after=None, limit=100) -> dict` — `{items, next_after}`; `since` is a datetime (`created_at >= since`), `after` a `seq`.
- None of them commits.

**Test helpers** (Task 3, `backend/tests/test_worklog_service.py`): `_append(session, key="plan-a", entries=None, **kwargs)` appends to project `"proj"` with run key `"claude:run-1"`; `entries=None` means one ledger entry `"Task 1: complete\n"`, and an explicit `[]` is passed through. `_events(session, workstream_id)` returns `[(event_type, payload), ...]` in journal order.

**Schemas** (Task 5, `app/schemas/worklog.py`): `WorklogEntryIn`, `WorklogAppendRequest` (`project, workstream, title, client, properties, run_key, entries`), `WorkstreamUpdateRequest` (`state, retain, title, properties`), `WorkstreamOut`, `WorklogEntryOut`, `WorklogAppendResponse`, `WorklogResumeResponse`, `WorkstreamListResponse`, `WorklogEntryListResponse`.

**REST** (Task 5, prefix `/api/v1/worklog`): `POST /entries` 201 (capture); `GET /resume?project=&workstream=` 200/404 (read); `GET /workstreams?project=&state=&before=&limit=` 200/422 (read); `GET /workstreams/{workstream_id}/entries?kind=&since=&after=&limit=` 200/404 (read); `PATCH /workstreams/{workstream_id}` 200/404 (capture); `DELETE /workstreams/{workstream_id}` 204/404/503 (admin).

**MCP** (Task 6): `worklog_append(project, workstream, entries, title=None, client=None, properties=None, run_key=None)`, `worklog_resume(project, workstream)`, `worklog_workstreams(project, state=None, before=None, limit=50)`, `worklog_entries(project, workstream, kind=None, since=None, after=None, limit=100)` (`since` an ISO 8601 string), `worklog_update(project, workstream, state=None, retain=None, title=None, properties=None)`, `worklog_purge(project, workstream)`. Each returns a JSON string; an unknown workstream answers `null`.

**Documents** (Task 7): `POST /api/v1/documents` requires scope `capture`; `GET /api/v1/documents/by-uri` requires `read` (its own handler, `document_blocks_by_uri_route`); `GET /api/v1/documents/{document_id}` stays login-only; new `GET /api/v1/documents/manifest?project=&uri_prefix=&after=&limit=` (read) answers `{items: [{id, uri, content_hash, updated_at}], next_after}`.

## Assumptions (evidence)

- The checkpoint origin resolver is reusable as-is: `resolve_checkpoint_origin(declared, *, source, project)` at `backend/app/services/checkpoints.py:130`, raising `UndeclaredOrigin(ValueError)` (`:120`). Read 2026-09-23. Increment 6 moves it into `worklog.py` when checkpoints are removed.
- REST reaches a key only through `require_scope` (`backend/app/api/auth.py:156`), whose `Principal` carries `actor` and `api_key_id` (`:137-153`); memories already use module-level `_require_capture = require_scope("capture")` (`backend/app/api/routes/memories.py:110`). Read 2026-09-23.
- MCP tools read the key through `current_api_key_id()` / `current_key_name()` (`backend/app/api/mcp/server.py:13`) and scopes through `TOOL_SCOPES` built from the three sets in `backend/app/api/mcp/scopes.py:47-104`. Read 2026-09-23. `TOOL_SCOPES` counts today: read 25, capture 13, admin 2 (ran `python -c` over it 2026-09-23).
- `document_blocks_route` serves both `GET /{document_id}` and `GET /by-uri` through two stacked decorators (`backend/app/api/routes/documents.py:922-923`). Task 7 gives `/by-uri` its own handler so only it is keyed, as spec §2 lists.
- `tests/test_api_keys.py` pins the exact set of scope-gated routes twice — `test_exactly_the_intended_routes_are_scope_gated` and the mutation drill's `expected` (`:1111-1117`, `:1165-1171`). Tasks 5 and 7 add their routes to both.
- The event-taxonomy scan pins unresolved `event_type=` call sites (`backend/tests/test_event_taxonomy_map.py:76, 221`); passing literals keeps the set unchanged.
- Independent committed connections come from `tests.conftest.test_engine`, as `backend/tests/test_usage_cleanup.py:26, 48` does; Task 3's race tests clean up their workstream and project rows, and leave their events rows because the journal is append-only.
- `record_event` returns whether the row landed (`backend/app/services/events.py:285-296`); `page_door._journal_each` (`backend/app/services/page_door.py:767`) is the strict-journal pattern purge copies.
- Pytest runs in `asyncio_mode = "auto"` (`backend/pyproject.toml:104`); the `client` fixture overrides `get_session` with the test session (`backend/tests/conftest.py:158`); `issue_key(session, name=, scopes=)` mints a key (`backend/tests/test_mcp_auth.py:40`).
- The REST conformance test requires every route in `EXPECTED_STATUS` (`backend/tests/test_api/test_rest_conformance.py:338`); the parity doc is generated from `PARITY_TABLE` (`backend/tests/test_door_parity.py:2140-2152`); the content-surface inventory classifies every front door (`backend/app/services/content_surfaces.py:603, 917`).
- The spec was amended on 2026-09-23, while this plan was written, for four findings: entries order by a `seq` identity; `search_vector` is a generated column; the work-log doors are classified `WITHOUT_MEMORY_CONTENT` as the checkpoint doors are; checkpoint removal moves to increment 6. `workstreams.last_entry_at` is `NOT NULL DEFAULT now()` since a workstream is only ever created by an append.
- `document_revisions` already exists as an inert baseline table storing post-images (`backend/migrations/versions/0001_baseline.py:1484`). Increment 3 reuses it; this plan does not touch it.
- The baseline regeneration here means every deployed database must be dropped and recreated before this build runs (`CLAUDE.md`, Migrations; `app/schema_guard.py` refuses to boot otherwise). Deploying is the finishing step's, and it needs the owner's go-ahead because it replaces production data.
- Race interleavings with a concurrent close, and two appends reopening one workstream, are not given their own two-session tests: the lock-then-decide read makes both a consequence of the row lock the two append-versus-delete races already exercise.
- Between Task 5 and Task 8 the enumeration guards (`test_rest_conformance`, `test_door_parity`, `test_content_surface_scoping`, `test_prompt_agent_instructions`) fail by design: the doors exist before they are classified. Tasks 5–7 run targeted tests; Task 8 and Task 9 turn the guard leg green.
- The 2026-09-23 MCP instruction change ("A memory is not a log") is committed as `116fb6f8` on this branch; Task 9 extends it.

## Task index

1. Work-log tables and models
2. Lifecycle event vocabulary
3. Service write verbs
4. Service read verbs
5. REST routes
6. MCP tools and scopes
7. Keyed document routes and manifest
8. Guard registries
9. Instructions and CLAUDE.md counts

---

### Task 1: Work-log tables and models

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py` (after the `ix_session_checkpoints_latest` index; the downgrade table list)
- Create: `backend/app/models/worklog.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_worklog_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the tables and models in Contracts → Tables, Models.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_worklog_schema.py`:

```python
"""The work-log tables. Their CHECKs are the guarantee behind both doors."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.worklog import WorklogEntry, Workstream


async def _workstream(session, *, key="plan-a"):
    wid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO workstreams (id, project, key) "
            "VALUES (CAST(:id AS uuid), 'proj', CAST(:key AS text))"
        ),
        {"id": str(wid), "key": key},
    )
    return wid


async def _entry(session, wid, *, kind="ledger", body="line\n"):
    await session.execute(
        text(
            "INSERT INTO worklog_entries (id, workstream_id, run_key, kind, body) "
            "VALUES (CAST(:id AS uuid), CAST(:w AS uuid), 'run:1', "
            "CAST(:k AS text), CAST(:b AS text))"
        ),
        {"id": str(uuid.uuid4()), "w": str(wid), "k": kind, "b": body},
    )


async def test_an_entry_is_keyword_searchable(session):
    wid = await _workstream(session)
    await _entry(session, wid, body="the gate went red on the alembic check")
    hit = (await session.execute(text(
        "SELECT count(*) FROM worklog_entries "
        "WHERE search_vector @@ plainto_tsquery('english', 'alembic')"
    ))).scalar_one()
    assert hit == 1


async def test_seq_keeps_one_statement_s_rows_in_order(session):
    wid = await _workstream(session)
    await session.execute(
        text(
            "INSERT INTO worklog_entries (id, workstream_id, run_key, kind, body) VALUES "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'a'), "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'b'), "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'c')"
        ),
        {"w": str(wid)},
    )
    bodies = (await session.execute(text(
        "SELECT body FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid) ORDER BY seq"
    ), {"w": str(wid)})).scalars().all()
    assert bodies == ["a", "b", "c"]


@pytest.mark.parametrize("kind,body", [
    ("log", "x"),
    ("ledger", ""),
    ("ledger", "x" * 65_537),
])
async def test_the_entry_checks_refuse(session, kind, body):
    wid = await _workstream(session)
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _entry(session, wid, kind=kind, body=body)


async def test_the_body_bound_is_inclusive(session):
    wid = await _workstream(session)
    await _entry(session, wid, body="x" * 65_536)


@pytest.mark.parametrize("state,closed", [("closed", False), ("open", True), ("done", False)])
async def test_the_state_checks_refuse(session, state, closed):
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO workstreams (id, project, key, state, closed_at) VALUES "
                    "(gen_random_uuid(), 'proj', 'k', CAST(:s AS text), "
                    "CASE WHEN CAST(:c AS boolean) THEN now() ELSE NULL END)"
                ),
                {"s": state, "c": closed},
            )


async def test_one_key_per_project(session):
    await _workstream(session, key="dup")
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _workstream(session, key="dup")


async def test_deleting_a_workstream_cascades_its_entries(session):
    wid = await _workstream(session)
    await _entry(session, wid)
    await session.execute(text("DELETE FROM workstreams WHERE id = CAST(:w AS uuid)"), {"w": str(wid)})
    left = (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one()
    assert left == 0


async def test_the_models_map_the_tables(session):
    ws = Workstream(project="proj", key="orm")
    session.add(ws)
    await session.flush()
    entry = WorklogEntry(workstream_id=ws.id, run_key="r", kind="note", body="remember this")
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    assert entry.seq is not None
    assert entry.search_vector is not None
    await session.refresh(ws)
    assert ws.state == "open" and ws.retain is False and ws.last_entry_at is not None
    found = (await session.execute(select(WorklogEntry).where(WorklogEntry.workstream_id == ws.id))).scalar_one()
    assert found.body == "remember this"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_schema.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.worklog'`.

- [ ] **Step 3: Add the tables to the baseline**

In `backend/migrations/versions/0001_baseline.py`, immediately after the block that ends with

```python
    op.execute(
        "CREATE INDEX ix_session_checkpoints_latest "
        "ON session_checkpoints (project, origin_key, created_at DESC, id DESC)"
    )
```

insert:

```python

    # ------------------------------------------------------------------
    # workstreams + worklog_entries — the work-log lane
    # (docs/superpowers/specs/2026-09-23-work-log-lane-design.md §1)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE workstreams (
            id            UUID NOT NULL,
            project       TEXT NOT NULL,
            key           TEXT NOT NULL,
            title         TEXT,
            client        TEXT,
            state         TEXT NOT NULL DEFAULT 'open',
            closed_at     TIMESTAMPTZ,
            retain        BOOLEAN NOT NULL DEFAULT false,
            properties    JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_entry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT workstreams_pkey PRIMARY KEY (id),
            CONSTRAINT ux_workstreams_project_key UNIQUE (project, key),
            CONSTRAINT chk_workstreams_state CHECK (state IN ('open', 'closed')),
            CONSTRAINT chk_workstreams_closed_at
                CHECK ((state = 'closed') = (closed_at IS NOT NULL)),
            CONSTRAINT chk_workstreams_key_len CHECK (char_length(key) BETWEEN 1 AND 200),
            CONSTRAINT chk_workstreams_title_len CHECK (char_length(title) <= 500),
            CONSTRAINT chk_workstreams_properties_size
                CHECK (pg_column_size(properties) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER workstreams_touch_updated_at BEFORE UPDATE "
        "ON workstreams FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )
    op.execute(
        "CREATE INDEX ix_workstreams_project_created "
        "ON workstreams (project, created_at DESC, id DESC)"
    )
    # `seq`, not created_at, orders entries: every entry of one append shares
    # the transaction's now(), and a ledger's chunks must concatenate back in
    # the order they were written.
    op.execute(
        """
        CREATE TABLE worklog_entries (
            id            UUID NOT NULL,
            seq           BIGINT GENERATED ALWAYS AS IDENTITY,
            workstream_id UUID NOT NULL REFERENCES workstreams(id) ON DELETE CASCADE,
            run_key       TEXT NOT NULL,
            kind          TEXT NOT NULL,
            body          TEXT NOT NULL,
            properties    JSONB NOT NULL DEFAULT '{}'::jsonb,
            search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT worklog_entries_pkey PRIMARY KEY (id),
            CONSTRAINT chk_worklog_entries_kind
                CHECK (kind IN ('checkpoint', 'ledger', 'note')),
            CONSTRAINT chk_worklog_entries_body_len
                CHECK (char_length(body) BETWEEN 1 AND 65536),
            CONSTRAINT chk_worklog_entries_properties_size
                CHECK (pg_column_size(properties) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_kind_latest "
        "ON worklog_entries (workstream_id, kind, seq DESC)"
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_order ON worklog_entries (workstream_id, seq)"
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_fts ON worklog_entries USING gin (search_vector)"
    )
```

In `downgrade()`, in the table list, replace the line

```python
        "session_checkpoints",
```

with

```python
        "worklog_entries",
        "workstreams",
        "session_checkpoints",
```

- [ ] **Step 4: Add the models**

Create `backend/app/models/worklog.py`:

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Computed, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Workstream(Base):
    """One piece of a client's work in a project: a plan, a design, a task.

    Operational state, not knowledge: nothing here is extracted, ranked with
    memories, or verified (spec 2026-09-23 §7).
    """

    __tablename__ = "workstreams"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    project: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    client: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retain: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_entry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorklogEntry(Base):
    """One append-only entry: a checkpoint, a ledger chunk or a note."""

    __tablename__ = "worklog_entries"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    workstream_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("workstreams.id", ondelete="CASCADE"), nullable=False
    )
    run_key: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', body)", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

In `backend/app/models/__init__.py`, after the line `from .project import Project` add:

```python
from .worklog import Workstream, WorklogEntry
```

and in `__all__`, after `"SessionCheckpoint",` add:

```python
    "Workstream",
    "WorklogEntry",
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_schema.py tests/test_schema_guard.py tests/test_models.py tests/test_inert_objects.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/app/models/worklog.py backend/app/models/__init__.py backend/tests/test_worklog_schema.py
git commit -m "feat(worklog): add workstream and entry tables"
```

### Task 2: Lifecycle event vocabulary

**Files:**
- Modify: `backend/app/services/events.py` (`EVENT_TYPES`, `OBJECT_TYPES`)
- Modify: `frontend/src/features/activity/event-taxonomy.ts` (`EVENT_TYPES_WITHOUT_TAB`)
- Test: `backend/tests/test_worklog_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces: Contracts → Events.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_worklog_schema.py`:

```python


def test_the_vocabulary_carries_the_workstream_lifecycle():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    for event_type in (
        "workstream_opened",
        "workstream_closed",
        "workstream_reopened",
        "workstream_purged",
    ):
        assert event_type in EVENT_TYPES
    assert "workstream" in OBJECT_TYPES


def _members(source: str) -> set[str]:
    """The string members of EVENT_TYPES_WITHOUT_TAB in `source`, comments stripped."""
    import re

    block = source.split("const EVENT_TYPES_WITHOUT_TAB = new Set<string>([", 1)[1].split("])", 1)[0]
    code = "\n".join(line.split("//", 1)[0] for line in block.splitlines())
    return set(re.findall(r'"([a-z_]+)"', code))


def _without_tab_members() -> set[str]:
    from pathlib import Path

    return _members((
        Path(__file__).resolve().parents[2]
        / "frontend" / "src" / "features" / "activity" / "event-taxonomy.ts"
    ).read_text(encoding="utf-8"))


def test_the_frontend_map_classifies_the_workstream_lifecycle():
    members = _without_tab_members()
    for event_type in (
        "workstream_opened",
        "workstream_closed",
        "workstream_reopened",
        "workstream_purged",
    ):
        assert event_type in members


def test_the_member_scan_ignores_names_that_only_appear_in_comments():
    block = (
        "const EVENT_TYPES_WITHOUT_TAB = new Set<string>([\n"
        '  "kept",\n'
        '  // "commented_out" is only mentioned\n'
        "])"
    )
    assert _members(block) == {"kept"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_schema.py -k "vocabulary or frontend_map"`
Expected: FAIL — `assert 'workstream_opened' in [...]`.

- [ ] **Step 3: Add the values**

In `backend/app/services/events.py`, inside `EVENT_TYPES`, immediately after the line `    "resumed",` insert:

```python
    # The work-log lane (spec 2026-09-23 §1). Lifecycle only: no entry body
    # or properties value reaches a payload, because the entries table is
    # the history and this journal is unpurgeable by ruling (T2.59).
    "workstream_opened",
    "workstream_closed",
    "workstream_reopened",
    "workstream_purged",
```

Inside `OBJECT_TYPES`, immediately after the line `    "checkpoint",` insert:

```python
    "workstream",
```

In `frontend/src/features/activity/event-taxonomy.ts`, inside `EVENT_TYPES_WITHOUT_TAB`, immediately after the line `  "resumed",` insert:

```ts
  // The work-log lane's lifecycle (spec 2026-09-23). Operational state like
  // the checkpoint pair above: a client's own work, not a memory, fact or
  // repo lifecycle step, so none of the five tabs models it. Its surface is
  // the project workspace's Work log view.
  "workstream_opened",
  "workstream_closed",
  "workstream_reopened",
  "workstream_purged",
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_schema.py tests/test_events.py tests/test_event_taxonomy_map.py && cd ../frontend && timeout 600 npm run typecheck`
Expected: PASS; typecheck exits 0.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/events.py frontend/src/features/activity/event-taxonomy.ts backend/tests/test_worklog_schema.py
git commit -m "feat(events): add the workstream lifecycle"
```

### Task 3: Service write verbs

**Files:**
- Create: `backend/app/services/worklog.py`
- Test: `backend/tests/test_worklog_service.py`
- Test: `backend/tests/test_worklog_wall.py`

**Interfaces:**
- Consumes: Contracts → Models (Task 1), Events (Task 2).
- Produces: Contracts → Service: constants, exceptions, `properties_size`, `AppendResult`, `append`, `get_workstream`, `get_workstream_by_id`, `update_workstream`, `purge_workstream`, `serialize_workstream`, `serialize_entry`; Contracts → Test helpers.

**Items:** 1, 2

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_worklog_service.py`:

```python
"""The work-log service: the one implementation behind both doors."""
from __future__ import annotations

import asyncio
import secrets
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.worklog import WorklogEntry, Workstream
from app.services import worklog


async def _events(session, workstream_id):
    rows = await session.execute(
        text(
            "SELECT event_type, payload FROM events "
            "WHERE object_type = 'workstream' AND object_id = CAST(:w AS uuid) "
            "ORDER BY id"
        ),
        {"w": str(workstream_id)},
    )
    return [(r.event_type, r.payload) for r in rows]


async def _append(session, key="plan-a", entries=None, **kwargs):
    return await worklog.append(
        session,
        project="proj",
        key=key,
        run_key="claude:run-1",
        entries=entries if entries is not None else [{"kind": "ledger", "body": "Task 1: complete\n"}],
        **kwargs,
    )


async def test_append_creates_the_workstream_and_journals_it(session):
    result = await _append(
        session,
        entries=[
            {"kind": "checkpoint", "body": "## State\nplan saved"},
            {"kind": "ledger", "body": "Task 1: complete\n", "properties": {"task": 1}},
        ],
        title="Plan A",
        client="dr-superpowers",
        properties={"plan_uri": "superpowers/plans/a.md"},
    )
    ws = result.workstream
    assert (ws.project, ws.key, ws.title, ws.client, ws.state) == (
        "proj", "plan-a", "Plan A", "dr-superpowers", "open",
    )
    assert ws.properties == {"plan_uri": "superpowers/plans/a.md"}
    rows = (await session.execute(
        select(WorklogEntry).where(WorklogEntry.workstream_id == ws.id).order_by(WorklogEntry.seq)
    )).scalars().all()
    assert [r.id for r in rows] == result.entry_ids
    assert [r.kind for r in rows] == ["checkpoint", "ledger"]
    assert rows[1].properties == {"task": 1}
    assert all(r.run_key == "claude:run-1" for r in rows)
    assert await _events(session, ws.id) == [("workstream_opened", {"key": "plan-a"})]


async def test_a_full_batch_of_one_hundred_lands_in_order(session):
    result = await _append(session, entries=[{"kind": "ledger", "body": f"{i}\n"} for i in range(100)])
    bodies = (await session.execute(
        select(WorklogEntry.body).where(WorklogEntry.workstream_id == result.workstream.id)
        .order_by(WorklogEntry.seq)
    )).scalars().all()
    assert bodies == [f"{i}\n" for i in range(100)]


async def test_a_refused_batch_leaves_no_workstream_and_no_entry(session):
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, entries=[
            {"kind": "ledger", "body": "fine\n"},
            {"kind": "ledger", "body": "x" * 65_537},
        ])
    assert (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one() == 0
    assert (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one() == 0


async def test_merged_properties_over_the_database_bound_are_rejected(session):
    first = await _append(session, properties={"a": secrets.token_hex(4500)})
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream(session, project="proj", key="plan-a")
    assert set(kept.properties) == {"a"}
    assert kept.id == first.workstream.id


async def test_a_second_append_reuses_and_merges(session):
    first = await _append(session, properties={"plan_uri": "a"})
    second = await _append(session, properties={"spec_uri": "b"}, title="Titled later")
    assert second.workstream.id == first.workstream.id
    assert second.workstream.properties == {"plan_uri": "a", "spec_uri": "b"}
    assert second.workstream.title == "Titled later"
    count = (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one()
    assert count == 1
    assert [e for e, _ in await _events(session, first.workstream.id)] == ["workstream_opened"]


async def test_append_registers_the_project(session):
    await _append(session)
    found = (await session.execute(
        text("SELECT count(*) FROM projects WHERE name = 'proj'")
    )).scalar_one()
    assert found == 1


async def test_append_to_a_closed_workstream_reopens_it(session):
    first = await _append(session)
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    again = await _append(session)
    assert again.workstream.state == "open"
    assert again.workstream.closed_at is None
    assert [e for e, _ in await _events(session, first.workstream.id)] == [
        "workstream_opened", "workstream_closed", "workstream_reopened",
    ]


@pytest.mark.parametrize("count", [0, 101])
async def test_append_refuses_a_batch_outside_1_to_100(session, count):
    with pytest.raises(ValueError):
        await _append(session, entries=[{"kind": "note", "body": "n"}] * count)


async def test_close_sets_closed_at_and_reopen_clears_it(session):
    ws = (await _append(session)).workstream
    closed = await worklog.update_workstream(session, ws.id, state="closed")
    assert closed.state == "closed" and closed.closed_at is not None
    reopened = await worklog.update_workstream(session, ws.id, state="open")
    assert reopened.state == "open" and reopened.closed_at is None


async def test_update_moves_retain_title_and_merges_properties(session):
    ws = (await _append(session, properties={"a": 1})).workstream
    updated = await worklog.update_workstream(
        session, ws.id, retain=True, title="T", properties={"b": 2}
    )
    assert updated.retain is True
    assert updated.title == "T"
    assert updated.properties == {"a": 1, "b": 2}
    assert [e for e, _ in await _events(session, ws.id)] == ["workstream_opened"]


async def test_the_lock_refreshes_a_stale_loaded_row(session):
    ws = (await _append(session)).workstream
    await session.execute(
        text("UPDATE workstreams SET state = 'closed', closed_at = now() WHERE id = CAST(:w AS uuid)"),
        {"w": str(ws.id)},
    )
    assert ws.state == "open"
    reopened = await worklog.update_workstream(session, ws.id, state="open")
    assert reopened.state == "open" and reopened.closed_at is None
    assert [e for e, _ in await _events(session, ws.id)][-1] == "workstream_reopened"


async def test_update_and_purge_refuse_an_unknown_workstream(session):
    with pytest.raises(worklog.WorkstreamNotFound):
        await worklog.update_workstream(session, uuid.uuid4(), state="closed")
    with pytest.raises(worklog.WorkstreamNotFound):
        await worklog.purge_workstream(session, uuid.uuid4())


async def test_purge_journals_then_deletes_everything(session):
    ws = (await _append(session, entries=[
        {"kind": "ledger", "body": "a\n"}, {"kind": "note", "body": "b"},
    ])).workstream
    workstream_id = ws.id
    removed = await worklog.purge_workstream(session, workstream_id, actor="admin")
    assert removed == 2
    assert (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one() == 0
    assert (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one() == 0
    assert (await _events(session, workstream_id))[-1] == (
        "workstream_purged", {"key": "plan-a", "entries": 2},
    )


@pytest.mark.parametrize("reported", [False, True])
async def test_purge_refuses_unless_the_journal_row_is_really_there(session, monkeypatch, reported):
    ws = (await _append(session)).workstream

    async def writes_nothing(*args, **kwargs):
        return reported

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await worklog.purge_workstream(session, ws.id)
    still = (await session.execute(select(Workstream).where(Workstream.id == ws.id))).scalar_one_or_none()
    assert still is not None
    entries = (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(ws.id)},
    )).scalar_one()
    assert entries == 1


async def test_no_entry_text_reaches_the_journal(session):
    secret = "body text that must never be journaled"
    ws = (await _append(session, entries=[{"kind": "note", "body": secret, "properties": {"x": secret}}])).workstream
    await worklog.update_workstream(session, ws.id, state="closed")
    for _, payload in await _events(session, ws.id):
        assert secret not in str(payload)


def test_serializers_are_json_safe():
    import json
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    ws = Workstream(
        id=uuid.uuid4(), project="p", key="k", title=None, client=None, state="open",
        closed_at=None, retain=False, properties={}, last_entry_at=now,
        created_at=now, updated_at=now,
    )
    entry = WorklogEntry(
        id=uuid.uuid4(), seq=7, workstream_id=ws.id, run_key="r", kind="note",
        body="b", properties={}, created_at=now,
    )
    json.dumps(worklog.serialize_workstream(ws))
    json.dumps(worklog.serialize_entry(entry))
    assert worklog.serialize_entry(entry)["seq"] == 7


# ── Races, on independent committed connections ──────────────────────────
#
# The `session` fixture shares one connection, so it cannot show two
# transactions waiting on each other. These use the test engine directly,
# commit for real, and delete their own rows afterwards. The events rows they
# journal cannot be deleted (the journal is append-only) and are left under
# the `worklog-race` project.

RACE_PROJECT = "worklog-race"
_RETENTION_DELETE = text(
    "DELETE FROM workstreams WHERE id = CAST(:id AS uuid) "
    "AND state = 'closed' AND NOT retain RETURNING id"
)


@pytest_asyncio.fixture
async def committed(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    async with factory() as cleanup:
        await cleanup.execute(text("DELETE FROM workstreams WHERE project = :p"), {"p": RACE_PROJECT})
        await cleanup.execute(text("DELETE FROM projects WHERE name = :p"), {"p": RACE_PROJECT})
        await cleanup.commit()


async def _closed_race_workstream(factory) -> uuid.UUID:
    async with factory() as setup:
        result = await worklog.append(
            setup, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "n"}],
        )
        await worklog.update_workstream(setup, result.workstream.id, state="closed")
        await setup.commit()
        return result.workstream.id


async def test_an_append_holding_the_lock_survives_a_retention_delete(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as appender, committed() as deleter:
        await worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        )
        delete_task = asyncio.create_task(deleter.execute(_RETENTION_DELETE, {"id": str(ws_id)}))
        await asyncio.sleep(0.3)
        assert not delete_task.done(), "the delete must wait on the append's row lock"
        await appender.commit()
        deleted = (await delete_task).fetchall()
        await deleter.commit()
    assert deleted == []
    async with committed() as check:
        state = (await check.execute(
            text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"), {"id": str(ws_id)}
        )).scalar_one()
    assert state == "open"


async def test_an_append_behind_a_committed_delete_recreates_the_workstream(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as deleter, committed() as appender:
        removed = (await deleter.execute(_RETENTION_DELETE, {"id": str(ws_id)})).fetchall()
        assert len(removed) == 1
        append_task = asyncio.create_task(worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        ))
        await asyncio.sleep(0.3)
        assert not append_task.done(), "the append must wait on the delete's row lock"
        await deleter.commit()
        result = await append_task
        await appender.commit()
    assert result.workstream.id != ws_id
    async with committed() as check:
        counts = [
            (await check.execute(
                text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:id AS uuid)"),
                {"id": str(workstream_id)},
            )).scalar_one()
            for workstream_id in (ws_id, result.workstream.id)
        ]
    assert counts == [0, 1]
```

Create `backend/tests/test_worklog_wall.py`:

```python
"""Spec §7's wall, structurally: the work log and the memory side never import each other."""
from __future__ import annotations

from pathlib import Path

import pytest

import re

from tests._reachability_scan import import_closure, module_path
from tests.test_block_retrieval import VAULT_WRITERS, _attributes_named, _promoting_vault_methods

BACKEND = Path(__file__).resolve().parent.parent

WORKLOG_MODULES = frozenset({
    "app.services.worklog",
    "app.models.worklog",
    "app.schemas.worklog",
    "app.api.routes.worklog",
})

MEMORY_SIDE = (
    "app.services.pipeline",
    "app.services.hybrid_search",
    "app.services.layer_composition",
    "app.services.chat",
)


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_reaches_the_work_log(seed):
    reached = import_closure(BACKEND, seed) & WORKLOG_MODULES
    assert not reached, f"{seed} reaches {sorted(reached)} — the work log is walled off (spec §7)"


def test_the_work_log_reaches_neither_the_pipeline_nor_the_vault():
    reached = import_closure(BACKEND, "app.services.worklog")
    forbidden = {"app.services.pipeline", *VAULT_WRITERS} & reached
    assert not forbidden, f"app.services.worklog reaches {sorted(forbidden)}"


WORKLOG_TABLES = ("workstreams", "worklog_entries")


def _names_a_worklog_table(source: str) -> bool:
    return any(re.search(rf"\b{table}\b", source) for table in WORKLOG_TABLES)


def test_every_scan_seed_resolves_to_a_file():
    """import_closure returns an unresolvable seed alone, which would pass every scan."""
    for seed in (*MEMORY_SIDE, *VAULT_WRITERS, *WORKLOG_MODULES):
        assert module_path(seed, BACKEND) is not None, f"{seed} moved — re-point the wall"


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_names_a_work_log_table(seed):
    """Raw SQL is invisible to the import scan, so the table names are scanned too."""
    for module in sorted(import_closure(BACKEND, seed) - WORKLOG_MODULES):
        path = module_path(module, BACKEND)
        if path is not None:
            assert not _names_a_worklog_table(path.read_text(encoding="utf-8")), (
                f"{module}, reached from {seed}, names a work-log table"
            )


def test_the_table_scan_sees_a_planted_query():
    assert _names_a_worklog_table("text('SELECT body FROM worklog_entries')")
    assert not _names_a_worklog_table("object_type = 'workstream'")


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_can_write_or_promote_a_fact(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    named = _attributes_named(source) & _promoting_vault_methods()
    assert not named, f"{module} names vault methods {sorted(named)}"


def test_the_method_scan_sees_a_planted_call():
    promoting = _promoting_vault_methods()
    planted = next(iter(sorted(promoting)))
    assert _attributes_named(f"repository.{planted}(fact)") & promoting == {planted}


def test_the_scan_sees_an_import_hidden_in_a_function(tmp_path):
    """Negative control: a function-level import must count, or the wall is decorative."""
    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "alpha.py").write_text("def later():\n    from app.services import beta\n")
    (services / "beta.py").write_text("")
    assert "app.services.beta" in import_closure(tmp_path, "app.services.alpha")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_wall.py`
Expected: FAIL — `tests/test_worklog_service.py` errors with `ImportError: cannot import name 'worklog' from 'app.services'`, and in `tests/test_worklog_wall.py` the seed-resolution and method-scan tests fail on the missing `app.services.worklog`, `app.schemas.worklog` and `app.api.routes.worklog`. The other wall tests pass already; they are regression guards. The seed and method scans go green only once Task 5 creates the schema and route modules — until then run the wall file with `-k "not seed and not can_write"` in Tasks 3 and 4, and in full from Task 5 on.

- [ ] **Step 3: Write the service**

Create `backend/app/services/worklog.py`:

```python
"""The work-log lane: workstreams and their append-only entries.

A coding client's operational state — checkpoints it summarised itself, ledger
chunks, notes to its next session — kept apart from memories so none of it
reaches extraction, memory retrieval or the fact vault
(docs/superpowers/specs/2026-09-23-work-log-lane-design.md §7). Both doors call
this module and hold no logic of their own (invariant 17).

Nothing here commits: the caller owns the transaction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worklog import WorklogEntry, Workstream
from app.services import project_registry
from app.services.events import record_event

__all__ = [
    "AppendResult",
    "DOOR_SOURCE",
    "KINDS",
    "MAX_BODY_CHARS",
    "MAX_ENTRIES_PER_APPEND",
    "MAX_PROPERTIES_BYTES",
    "RESUME_LEDGER_TAIL",
    "RESUME_NOTES_CAP",
    "WorklogJournalWriteFailed",
    "WorklogRejected",
    "WorkstreamNotFound",
    "append",
    "get_workstream",
    "get_workstream_by_id",
    "properties_size",
    "purge_workstream",
    "serialize_entry",
    "serialize_workstream",
    "update_workstream",
]

KINDS = ("checkpoint", "ledger", "note")
MAX_BODY_CHARS = 65_536
# The database bounds properties with pg_column_size(...) <= 16384; the door
# measures encoded JSON text, which is not jsonb's size, so it sits below the
# CHECK. The CHECK stays the guarantee: a merge or a numeric-heavy value that
# still exceeds it surfaces as WorklogRejected, never as a 500.
MAX_PROPERTIES_BYTES = 12_288
MAX_ENTRIES_PER_APPEND = 100
RESUME_LEDGER_TAIL = 20
RESUME_NOTES_CAP = 50
DOOR_SOURCE = "worklog"


class WorkstreamNotFound(LookupError):
    """No workstream under that id or (project, key)."""


class WorklogRejected(ValueError):
    """The database's CHECKs refused the write; nothing of it was kept."""


class WorklogJournalWriteFailed(RuntimeError):
    """The purge journal row is not there, so nothing was deleted.

    Local rather than the vault's `JournalWriteFailed`: this lane stays off
    the vault's modules (spec §7).
    """


@dataclass(frozen=True)
class AppendResult:
    workstream: Workstream
    entry_ids: list[UUID]


def properties_size(value: dict) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


_SELECT_LOCKED = text(
    "SELECT id, state FROM workstreams "
    "WHERE project = CAST(:project AS text) AND key = CAST(:key AS text) FOR UPDATE"
)
_REOPEN = text(
    """
    UPDATE workstreams SET
        state = 'open',
        closed_at = NULL,
        last_entry_at = now(),
        title = COALESCE(CAST(:title AS text), title),
        client = COALESCE(CAST(:client AS text), client),
        properties = properties || CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
    """
)
_INSERT_IF_ABSENT = text(
    """
    INSERT INTO workstreams (id, project, key, title, client, properties)
    VALUES (CAST(:id AS uuid), CAST(:project AS text), CAST(:key AS text),
            CAST(:title AS text), CAST(:client AS text), CAST(:properties AS jsonb))
    ON CONFLICT ON CONSTRAINT ux_workstreams_project_key DO NOTHING
    RETURNING id
    """
)
# Rows journaled inside this transaction carry created_at = now(), so the
# predicate reads back exactly this purge's row and prunes to one partition.
_PURGE_JOURNALED = text(
    """
    SELECT count(*) FROM events
    WHERE event_type = 'workstream_purged' AND object_type = 'workstream'
      AND object_id = CAST(:id AS uuid) AND created_at >= now()
    """
)


async def _lock_or_create(
    session: AsyncSession,
    *,
    project: str,
    key: str,
    title: str | None,
    client: str | None,
    properties: dict | None,
) -> tuple[UUID, str]:
    """The workstream under its row lock, and whether it was opened, reopened or continued.

    Lock first, then decide: the transition is read from the row as locked, so
    a concurrent close is seen rather than raced. The lock is what serialises
    an append against a purge or a retention delete of the same workstream —
    whichever commits second sees the first's result, so no entry lands in a
    deleted parent. An insert that loses a creation race does nothing, and the
    second pass locks the winner's row.
    """
    params = {
        "project": project,
        "key": key,
        "title": title,
        "client": client,
        "properties": json.dumps(properties or {}),
    }
    for _ in range(2):
        found = (await session.execute(_SELECT_LOCKED, params)).mappings().one_or_none()
        if found is not None:
            await session.execute(_REOPEN, {**params, "id": str(found["id"])})
            return found["id"], "reopened" if found["state"] == "closed" else "continued"
        created = (await session.execute(
            _INSERT_IF_ABSENT, {**params, "id": str(uuid4())}
        )).scalar_one_or_none()
        if created is not None:
            return created, "opened"
    raise RuntimeError(f"workstream {project}/{key} could be neither locked nor created")


async def append(
    session: AsyncSession,
    *,
    project: str,
    key: str,
    run_key: str,
    entries: list[dict[str, Any]],
    title: str | None = None,
    client: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> AppendResult:
    """Append 1-100 entries to a workstream, creating or reopening it."""
    if not 1 <= len(entries) <= MAX_ENTRIES_PER_APPEND:
        raise ValueError(
            f"an append carries 1 to {MAX_ENTRIES_PER_APPEND} entries, not {len(entries)}"
        )
    entry_ids = [uuid4() for _ in entries]
    try:
        async with session.begin_nested():
            workstream_id, transition = await _lock_or_create(
                session, project=project, key=key, title=title, client=client,
                properties=properties,
            )
            # One multi-row statement, not executemany: the identity column
            # hands out `seq` in VALUES order, which keeps a ledger in order.
            await session.execute(
                insert(WorklogEntry).values([
                    {
                        "id": entry_id,
                        "workstream_id": workstream_id,
                        "run_key": run_key,
                        "kind": entry["kind"],
                        "body": entry["body"],
                        "properties": entry.get("properties") or {},
                    }
                    for entry_id, entry in zip(entry_ids, entries)
                ])
            )
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
    await project_registry.register(session, project)

    if transition == "opened":
        await record_event(
            session, event_type="workstream_opened", object_type="workstream",
            object_id=workstream_id, project=project, actor=actor,
            api_key_id=api_key_id, payload={"key": key},
        )
    elif transition == "reopened":
        await record_event(
            session, event_type="workstream_reopened", object_type="workstream",
            object_id=workstream_id, project=project, actor=actor,
            api_key_id=api_key_id, payload={"key": key},
        )

    workstream = await session.get(Workstream, workstream_id, populate_existing=True)
    return AppendResult(workstream=workstream, entry_ids=entry_ids)


async def get_workstream(
    session: AsyncSession, *, project: str, key: str, for_update: bool = False
) -> Workstream | None:
    statement = select(Workstream).where(Workstream.project == project, Workstream.key == key)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def get_workstream_by_id(
    session: AsyncSession, workstream_id: UUID, *, for_update: bool = False
) -> Workstream | None:
    statement = select(Workstream).where(Workstream.id == workstream_id)
    if for_update:
        # Without populate_existing an instance already in the identity map
        # keeps its pre-lock attributes, and every decision below would be
        # made on state another transaction has since changed.
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def update_workstream(
    session: AsyncSession,
    workstream_id: UUID,
    *,
    state: str | None = None,
    retain: bool | None = None,
    title: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> Workstream:
    """Move state, retain, title; merge properties. Journals close and reopen."""
    if state is not None and state not in ("open", "closed"):
        raise ValueError(f"state must be 'open' or 'closed', not {state!r}")
    workstream = await get_workstream_by_id(session, workstream_id, for_update=True)
    if workstream is None:
        raise WorkstreamNotFound(str(workstream_id))
    transition = None
    if state is not None and state != workstream.state:
        workstream.state = state
        workstream.closed_at = func.now() if state == "closed" else None
        transition = state
    if retain is not None:
        workstream.retain = retain
    if title is not None:
        workstream.title = title
    if properties:
        workstream.properties = {**(workstream.properties or {}), **properties}
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
    if transition == "closed":
        await record_event(
            session, event_type="workstream_closed", object_type="workstream",
            object_id=workstream.id, project=workstream.project, actor=actor,
            api_key_id=api_key_id, payload={"key": workstream.key},
        )
    elif transition == "open":
        await record_event(
            session, event_type="workstream_reopened", object_type="workstream",
            object_id=workstream.id, project=workstream.project, actor=actor,
            api_key_id=api_key_id, payload={"key": workstream.key},
        )
    await session.refresh(workstream)
    return workstream


async def purge_workstream(
    session: AsyncSession,
    workstream_id: UUID,
    *,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> int:
    """Erase a workstream with its entries. Journals first and reads it back, or refuses.

    A purge is irrecoverable and, over MCP, the event's api_key_id is the only
    record of who ran it; failing closed costs a retry where failing open
    loses the audit for good.
    """
    workstream = await get_workstream_by_id(session, workstream_id, for_update=True)
    if workstream is None:
        raise WorkstreamNotFound(str(workstream_id))
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == workstream.id)
    )).scalar_one()
    landed = await record_event(
        session, event_type="workstream_purged", object_type="workstream",
        object_id=workstream.id, project=workstream.project, actor=actor,
        api_key_id=api_key_id, payload={"key": workstream.key, "entries": count},
    )
    journaled = (await session.execute(
        _PURGE_JOURNALED, {"id": str(workstream.id)}
    )).scalar_one()
    if not landed or journaled == 0:
        raise WorklogJournalWriteFailed(
            f"workstream_purged is not journaled for workstream {workstream.id}; "
            "refusing to delete unaudited"
        )
    await session.execute(delete(Workstream).where(Workstream.id == workstream.id))
    session.expunge(workstream)
    return count


def serialize_workstream(workstream: Workstream) -> dict[str, Any]:
    return {
        "id": str(workstream.id),
        "project": workstream.project,
        "key": workstream.key,
        "title": workstream.title,
        "client": workstream.client,
        "state": workstream.state,
        "closed_at": workstream.closed_at.isoformat() if workstream.closed_at else None,
        "retain": workstream.retain,
        "properties": workstream.properties or {},
        "last_entry_at": workstream.last_entry_at.isoformat(),
        "created_at": workstream.created_at.isoformat(),
        "updated_at": workstream.updated_at.isoformat(),
    }


def serialize_entry(entry: WorklogEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "workstream_id": str(entry.workstream_id),
        "seq": entry.seq,
        "run_key": entry.run_key,
        "kind": entry.kind,
        "body": entry.body,
        "properties": entry.properties or {},
        "created_at": entry.created_at.isoformat(),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_schema.py tests/test_event_taxonomy_map.py tests/test_events.py tests/test_block_pipeline.py && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_wall.py -k "not seed and not can_write"`
Expected: PASS. `test_event_taxonomy_map.py` now sees the four lifecycle literals as live emitters and finds them in the frontend map Task 2 added; the literal `event_type=` keywords add no unresolved call site.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog.py backend/tests/test_worklog_service.py backend/tests/test_worklog_wall.py
git commit -m "feat(worklog): add append, update and purge"
```

### Task 4: Service read verbs

**Files:**
- Modify: `backend/app/services/worklog.py` (imports; `__all__`; three functions appended)
- Test: `backend/tests/test_worklog_service.py`

**Interfaces:**
- Consumes: Contracts → Service write verbs (Task 3); Contracts → Test helpers (`_append` in `backend/tests/test_worklog_service.py`).
- Produces: Contracts → Service `resume`, `list_workstreams`, `list_entries`.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-medium
**Executor:** codex gpt-6-sol / low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_worklog_service.py` (it already defines `_append(session, key="plan-a", entries=None, **kwargs)`, which appends to project `"proj"` with run key `"claude:run-1"` and, when `entries` is None, one ledger entry `"Task 1: complete\n"`):

```python


async def test_resume_is_none_for_an_unknown_workstream(session):
    assert await worklog.resume(session, project="proj", key="nope") is None


async def test_resume_answers_latest_checkpoint_notes_and_ledger_tail(session):
    await _append(session, entries=[{"kind": "checkpoint", "body": "old"}])
    await _append(session, entries=[{"kind": "ledger", "body": f"line {i}\n"} for i in range(25)])
    await _append(session, entries=[
        {"kind": "note", "body": "gotcha"},
        {"kind": "checkpoint", "body": "new"},
    ])
    answer = await worklog.resume(session, project="proj", key="plan-a")
    assert answer["workstream"]["key"] == "plan-a"
    assert answer["checkpoint"]["body"] == "new"
    assert [n["body"] for n in answer["notes"]] == ["gotcha"]
    assert answer["notes_truncated"] is False
    assert [e["body"] for e in answer["ledger"]] == [f"line {i}\n" for i in range(5, 25)]


async def test_resume_caps_notes_at_fifty_newest(session):
    await _append(session, entries=[{"kind": "note", "body": f"n{i}"} for i in range(51)])
    answer = await worklog.resume(session, project="proj", key="plan-a")
    assert len(answer["notes"]) == 50
    assert answer["notes"][0]["body"] == "n1"
    assert answer["notes"][-1]["body"] == "n50"
    assert answer["notes_truncated"] is True


async def test_ledger_chunks_concatenate_back_to_the_appended_text(session):
    chunks = ["# Ledger\n\n", "Task 1: complete\n", "| a | b |\n|---|---|\n\n", "Task 2: complete\n"]
    for chunk in chunks:
        await _append(session, entries=[{"kind": "ledger", "body": chunk}])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    page = await worklog.list_entries(session, workstream_id=ws.id, kind="ledger")
    assert "".join(e["body"] for e in page["items"]) == "".join(chunks)


async def test_list_workstreams_pages_by_creation_and_ignores_later_appends(session):
    for key in ("w1", "w2", "w3"):
        await _append(session, key=key)
    # w1 was created most recently, w3 longest ago; activity starts in the same order.
    await session.execute(text(
        "UPDATE workstreams SET "
        "created_at = now() - CAST(substr(key, 2) AS int) * interval '1 hour', "
        "last_entry_at = now() - CAST(substr(key, 2) AS int) * interval '1 hour'"
    ))
    session.expire_all()
    first = await worklog.list_workstreams(session, project="proj", limit=2)
    assert [w["key"] for w in first["items"]] == ["w1", "w2"]
    # w3 becomes the most active; a list keyed on activity would now repeat or skip.
    await session.execute(text(
        "UPDATE workstreams SET last_entry_at = now() + interval '1 hour' WHERE key = 'w3'"
    ))
    session.expire_all()
    rest = await worklog.list_workstreams(session, project="proj", before=first["next_before"], limit=2)
    assert [w["key"] for w in rest["items"]] == ["w3"]
    assert rest["next_before"] is None


async def test_list_workstreams_filters_by_state_and_project(session):
    await _append(session, key="open-one")
    closing = (await _append(session, key="closed-one")).workstream
    await worklog.update_workstream(session, closing.id, state="closed")
    closed = await worklog.list_workstreams(session, project="proj", state="closed")
    assert [w["key"] for w in closed["items"]] == ["closed-one"]
    other = await worklog.list_workstreams(session, project="elsewhere")
    assert other == {"items": [], "next_before": None}


async def test_list_workstreams_refuses_a_malformed_cursor(session):
    with pytest.raises(ValueError):
        await worklog.list_workstreams(session, project="proj", before="not-a-cursor")


async def test_list_entries_pages_forward_by_seq(session):
    await _append(session, entries=[{"kind": "ledger", "body": f"{i}\n"} for i in range(5)])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    first = await worklog.list_entries(session, workstream_id=ws.id, limit=2)
    assert [e["body"] for e in first["items"]] == ["0\n", "1\n"]
    assert first["next_after"] == first["items"][-1]["seq"]
    second = await worklog.list_entries(session, workstream_id=ws.id, after=first["next_after"], limit=2)
    assert [e["body"] for e in second["items"]] == ["2\n", "3\n"]
    last = await worklog.list_entries(session, workstream_id=ws.id, after=second["next_after"], limit=2)
    assert [e["body"] for e in last["items"]] == ["4\n"]
    assert last["next_after"] is None


async def test_list_entries_filters_by_since(session):
    from datetime import UTC, datetime, timedelta

    await _append(session, entries=[{"kind": "note", "body": "n"}])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    past = await worklog.list_entries(session, workstream_id=ws.id, since=datetime.now(UTC) - timedelta(days=1))
    future = await worklog.list_entries(session, workstream_id=ws.id, since=datetime.now(UTC) + timedelta(days=1))
    assert [e["body"] for e in past["items"]] == ["n"]
    assert future["items"] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_service.py -k "resume or concatenate or list_"`
Expected: FAIL — `AttributeError: module 'app.services.worklog' has no attribute 'resume'`.

- [ ] **Step 3: Add the read verbs**

In `backend/app/services/worklog.py`:

Replace

```python
from sqlalchemy import delete, func, insert, select, text
```

with

```python
from sqlalchemy import and_, delete, func, insert, or_, select, text
```

and add `from datetime import datetime` beside `import json`.

Add `"list_entries"`, `"list_workstreams"` and `"resume"` to `__all__`, keeping it sorted.

Append at the end of the module:

```python


def _cursor(workstream: Workstream) -> str:
    return f"{workstream.created_at.isoformat()}|{workstream.id}"


def _parse_cursor(value: str) -> tuple[datetime, UUID]:
    stamp, _, ident = value.partition("|")
    try:
        return datetime.fromisoformat(stamp), UUID(ident)
    except ValueError as error:
        raise ValueError(f"not a workstream cursor: {value!r}") from error


async def resume(session: AsyncSession, *, project: str, key: str) -> dict[str, Any] | None:
    """What a new session loads: the latest checkpoint, notes, the ledger tail."""
    workstream = await get_workstream(session, project=project, key=key)
    if workstream is None:
        return None

    def newest(kind: str, limit: int):
        return (
            select(WorklogEntry)
            .where(WorklogEntry.workstream_id == workstream.id, WorklogEntry.kind == kind)
            .order_by(WorklogEntry.seq.desc())
            .limit(limit)
        )

    checkpoint = (await session.execute(newest("checkpoint", 1))).scalar_one_or_none()
    notes = (await session.execute(newest("note", RESUME_NOTES_CAP + 1))).scalars().all()
    ledger = (await session.execute(newest("ledger", RESUME_LEDGER_TAIL))).scalars().all()
    return {
        "workstream": serialize_workstream(workstream),
        "checkpoint": serialize_entry(checkpoint) if checkpoint is not None else None,
        "notes": [serialize_entry(n) for n in reversed(notes[:RESUME_NOTES_CAP])],
        "notes_truncated": len(notes) > RESUME_NOTES_CAP,
        "ledger": [serialize_entry(e) for e in reversed(ledger)],
    }


async def list_workstreams(
    session: AsyncSession,
    *,
    project: str,
    state: str | None = None,
    before: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Newest-created first, keyset-paged on the immutable (created_at, id).

    Not last_entry_at: an append moves that, and a page boundary on a moving
    key skips or repeats workstreams between pages.
    """
    conditions = [Workstream.project == project]
    if state is not None:
        conditions.append(Workstream.state == state)
    if before is not None:
        stamp, ident = _parse_cursor(before)
        conditions.append(or_(
            Workstream.created_at < stamp,
            and_(Workstream.created_at == stamp, Workstream.id < ident),
        ))
    rows = (await session.execute(
        select(Workstream)
        .where(*conditions)
        .order_by(Workstream.created_at.desc(), Workstream.id.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_workstream(w) for w in rows],
        "next_before": _cursor(rows[-1]) if len(rows) == limit else None,
    }


async def list_entries(
    session: AsyncSession,
    *,
    workstream_id: UUID,
    kind: str | None = None,
    since: datetime | None = None,
    after: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Entries oldest first, paged forward on `seq`; `since` keeps created_at >= since."""
    conditions = [WorklogEntry.workstream_id == workstream_id]
    if kind is not None:
        conditions.append(WorklogEntry.kind == kind)
    if since is not None:
        conditions.append(WorklogEntry.created_at >= since)
    if after is not None:
        conditions.append(WorklogEntry.seq > after)
    rows = (await session.execute(
        select(WorklogEntry).where(*conditions).order_by(WorklogEntry.seq).limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_entry(e) for e in rows],
        "next_after": rows[-1].seq if len(rows) == limit else None,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_wall.py -k "not seed and not can_write"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog.py backend/tests/test_worklog_service.py
git commit -m "feat(worklog): add resume and list reads"
```

### Task 5: REST routes

**Files:**
- Create: `backend/app/schemas/worklog.py`
- Create: `backend/app/api/routes/worklog.py`
- Modify: `backend/app/main.py` (router registration)
- Modify: `backend/tests/test_api_keys.py` (the two pinned scope-gated route sets)
- Test: `backend/tests/test_worklog_rest.py`

**Interfaces:**
- Consumes: Contracts → Service (Tasks 3–4).
- Produces: Contracts → Schemas, REST.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_worklog_rest.py`:

```python
"""The work-log lane over REST, including which keys reach which verb."""
from __future__ import annotations

import pytest

from app.api.mcp.client_identity import ORIGIN_HEADER
from app.services.api_keys import issue_key

V1 = "/api/v1/worklog"
RUN = {ORIGIN_HEADER: "run-1"}


def _append_body(**overrides):
    body = {
        "project": "proj",
        "workstream": "plan-a",
        "entries": [
            {"kind": "checkpoint", "body": "## State\nsaved"},
            {"kind": "ledger", "body": "Task 1: complete\n"},
        ],
    }
    body.update(overrides)
    return body


async def _key(session, *scopes):
    _row, credential = await issue_key(session, name=f"k-{'-'.join(scopes)}", scopes=list(scopes))
    return {"Authorization": f"Bearer {credential}", **RUN}


async def test_append_answers_201_with_the_workstream(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workstream"]["key"] == "plan-a"
    assert body["workstream"]["state"] == "open"
    assert len(body["entry_ids"]) == 2


async def test_an_undeclared_run_is_refused(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("entries", [
    [],
    [{"kind": "log", "body": "x"}],
    [{"kind": "ledger", "body": ""}],
    [{"kind": "note", "body": "x" * 65_537}],
    [{"kind": "note", "body": "n"}] * 101,
    [{"kind": "note", "body": "n", "properties": {"p": "x" * 13_000}}],
])
async def test_the_schema_refuses_out_of_bounds_entries(client, auth_headers, entries):
    response = await client.post(
        f"{V1}/entries", json=_append_body(entries=entries), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422


async def test_resume_is_404_then_the_checkpoint(client, auth_headers):
    missing = await client.get(f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers)
    assert missing.status_code == 404
    await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    found = await client.get(f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers)
    assert found.status_code == 200
    body = found.json()
    assert body["checkpoint"]["body"] == "## State\nsaved"
    assert [e["body"] for e in body["ledger"]] == ["Task 1: complete\n"]
    assert body["notes"] == [] and body["notes_truncated"] is False


async def test_lists_page_and_filter(client, auth_headers):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    listing = await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=auth_headers)
    assert listing.status_code == 200
    assert [w["key"] for w in listing.json()["items"]] == ["plan-a"]
    assert listing.json()["next_before"] is None
    bad_cursor = await client.get(f"{V1}/workstreams", params={"project": "proj", "before": "x"}, headers=auth_headers)
    assert bad_cursor.status_code == 422
    entries = await client.get(f"{V1}/workstreams/{workstream_id}/entries", params={"kind": "ledger"}, headers=auth_headers)
    assert entries.status_code == 200
    assert [e["kind"] for e in entries.json()["items"]] == ["ledger"]
    assert entries.json()["next_after"] is None
    unknown = await client.get(f"{V1}/workstreams/00000000-0000-0000-0000-000000000000/entries", headers=auth_headers)
    assert unknown.status_code == 404


async def test_patch_closes_and_delete_purges(client, auth_headers):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    closed = await client.patch(f"{V1}/workstreams/{workstream_id}", json={"state": "closed", "retain": True}, headers=auth_headers)
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed" and closed.json()["retain"] is True
    bad = await client.patch(f"{V1}/workstreams/{workstream_id}", json={"state": "done"}, headers=auth_headers)
    assert bad.status_code == 422
    deleted = await client.delete(f"{V1}/workstreams/{workstream_id}", headers=auth_headers)
    assert deleted.status_code == 204
    gone = await client.delete(f"{V1}/workstreams/{workstream_id}", headers=auth_headers)
    assert gone.status_code == 404


async def test_keys_reach_exactly_their_scopes(client, session):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    admin = await _key(session, "admin")

    assert (await client.post(f"{V1}/entries", json=_append_body(), headers=read)).status_code == 403
    created = await client.post(f"{V1}/entries", json=_append_body(), headers=capture)
    assert created.status_code == 201
    workstream_id = created.json()["workstream"]["id"]
    assert (await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=read)).status_code == 200
    assert (await client.delete(f"{V1}/workstreams/{workstream_id}", headers=capture)).status_code == 403
    assert (await client.delete(f"{V1}/workstreams/{workstream_id}", headers=admin)).status_code == 204


async def test_no_credential_is_401(client):
    response = await client.get(f"{V1}/workstreams", params={"project": "proj"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_rest.py`
Expected: FAIL — the first request answers 404 (no route).

- [ ] **Step 3: Write the schemas**

Create `backend/app/schemas/worklog.py`:

```python
"""Wire shapes for the work-log lane. Both doors validate through these."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]


def _bounded(value: dict | None) -> dict | None:
    if value is not None and properties_size(value) > MAX_PROPERTIES_BYTES:
        raise ValueError(f"properties encode to more than {MAX_PROPERTIES_BYTES} bytes")
    return value


class WorklogEntryIn(BaseModel):
    kind: Kind
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    properties: dict = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorklogAppendRequest(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorkstreamUpdateRequest(BaseModel):
    state: State | None = None
    retain: bool | None = None
    title: str | None = Field(default=None, max_length=500)
    properties: dict | None = None

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict | None) -> dict | None:
        return _bounded(value)


class WorkstreamOut(BaseModel):
    id: UUID
    project: str
    key: str
    title: str | None
    client: str | None
    state: State
    closed_at: datetime | None
    retain: bool
    properties: dict
    last_entry_at: datetime
    created_at: datetime
    updated_at: datetime


class WorklogEntryOut(BaseModel):
    id: UUID
    workstream_id: UUID
    seq: int
    run_key: str
    kind: Kind
    body: str
    properties: dict
    created_at: datetime


class WorklogAppendResponse(BaseModel):
    workstream: WorkstreamOut
    entry_ids: list[UUID]


class WorklogResumeResponse(BaseModel):
    workstream: WorkstreamOut
    checkpoint: WorklogEntryOut | None
    notes: list[WorklogEntryOut]
    notes_truncated: bool
    ledger: list[WorklogEntryOut]


class WorkstreamListResponse(BaseModel):
    items: list[WorkstreamOut]
    next_before: str | None


class WorklogEntryListResponse(BaseModel):
    items: list[WorklogEntryOut]
    next_after: int | None
```

- [ ] **Step 4: Write the routes**

Create `backend/app/api/routes/worklog.py`:

```python
"""The work-log lane over REST (spec 2026-09-23 §2).

Every route declares `require_scope`, so a `dmk_` key reaches the verbs its
scope names and a login session reaches all of them. The MCP tools are the
same verbs over the same service; neither door holds logic of its own.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import Principal, require_scope
from app.api.mcp.client_identity import ORIGIN_HEADER, resolve_client_source
from app.database import get_session
from app.schemas.worklog import (
    Kind,
    State,
    WorklogAppendRequest,
    WorklogAppendResponse,
    WorklogEntryListResponse,
    WorklogResumeResponse,
    WorkstreamListResponse,
    WorkstreamOut,
    WorkstreamUpdateRequest,
)
from app.services import worklog
from app.services.checkpoints import resolve_checkpoint_origin

router = APIRouter(prefix="/api/v1/worklog", tags=["worklog"])

# Module-level for the reason `routes/repos.py:31` records: an inline
# require_scope(...) builds a fresh dependency per import, which
# `app.dependency_overrides` cannot address.
_require_capture = require_scope("capture")
_require_read = require_scope("read")
_require_admin = require_scope("admin")


@router.post("/entries", response_model=WorklogAppendResponse, status_code=status.HTTP_201_CREATED)
async def append_entries(
    body: WorklogAppendRequest,
    request: Request,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
):
    source = resolve_client_source(None, headers=request.headers, fallback=worklog.DOOR_SOURCE)
    try:
        run_key = resolve_checkpoint_origin(
            body.run_key or request.headers.get(ORIGIN_HEADER),
            source=source,
            project=body.project,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    try:
        result = await worklog.append(
            session,
            project=body.project,
            key=body.workstream,
            run_key=run_key,
            entries=[entry.model_dump() for entry in body.entries],
            title=body.title,
            client=body.client,
            properties=body.properties,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
        )
    except worklog.WorklogRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = {
        "workstream": worklog.serialize_workstream(result.workstream),
        "entry_ids": [str(entry_id) for entry_id in result.entry_ids],
    }
    await session.commit()
    return payload


@router.get("/resume", response_model=WorklogResumeResponse)
async def resume(
    project: str = Query(min_length=1),
    workstream: str = Query(min_length=1),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    answer = await worklog.resume(session, project=project, key=workstream)
    if answer is None:
        raise HTTPException(status_code=404, detail="No workstream with that key in that project")
    return answer


@router.get("/workstreams", response_model=WorkstreamListResponse)
async def list_workstreams(
    project: str = Query(min_length=1),
    state: State | None = Query(default=None),
    before: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await worklog.list_workstreams(
            session, project=project, state=state, before=before, limit=limit
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/workstreams/{workstream_id}/entries", response_model=WorklogEntryListResponse)
async def list_entries(
    workstream_id: UUID,
    kind: Kind | None = Query(default=None),
    since: datetime | None = Query(default=None),
    after: int | None = Query(default=None, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    if await worklog.get_workstream_by_id(session, workstream_id) is None:
        raise HTTPException(status_code=404, detail="No such workstream")
    return await worklog.list_entries(
        session, workstream_id=workstream_id, kind=kind, since=since, after=after, limit=limit
    )


@router.patch("/workstreams/{workstream_id}", response_model=WorkstreamOut)
async def update_workstream(
    workstream_id: UUID,
    body: WorkstreamUpdateRequest,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
):
    try:
        workstream = await worklog.update_workstream(
            session,
            workstream_id,
            state=body.state,
            retain=body.retain,
            title=body.title,
            properties=body.properties,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
        )
    except worklog.WorkstreamNotFound as error:
        raise HTTPException(status_code=404, detail="No such workstream") from error
    except worklog.WorklogRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = worklog.serialize_workstream(workstream)
    await session.commit()
    return payload


@router.delete("/workstreams/{workstream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge_workstream(
    workstream_id: UUID,
    principal: Principal = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        await worklog.purge_workstream(
            session, workstream_id, actor=principal.actor, api_key_id=principal.api_key_id
        )
    except worklog.WorkstreamNotFound as error:
        raise HTTPException(status_code=404, detail="No such workstream") from error
    except worklog.WorklogJournalWriteFailed as error:
        await session.rollback()
        raise HTTPException(status_code=503, detail=str(error)) from error
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Register the router**

In `backend/app/main.py`, immediately after the line `app.include_router(checkpoint_routes.router)` add:

```python
from app.api.routes import worklog as worklog_routes  # noqa: E402

app.include_router(worklog_routes.router)
```

In `backend/tests/test_api_keys.py` the scope-gated route set is pinned twice, once in `test_exactly_the_intended_routes_are_scope_gated` and once as `expected` in `test_the_assertion_catches_delete_repo_reusing_the_binding`. In **both** places, immediately after the line

```python
            ("POST", "/api/v1/memories/search/paginated"),
```

insert:

```python
            ("POST", "/api/v1/worklog/entries"),
            ("GET", "/api/v1/worklog/resume"),
            ("GET", "/api/v1/worklog/workstreams"),
            ("GET", "/api/v1/worklog/workstreams/{workstream_id}/entries"),
            ("PATCH", "/api/v1/worklog/workstreams/{workstream_id}"),
            ("DELETE", "/api/v1/worklog/workstreams/{workstream_id}"),
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_rest.py tests/test_worklog_service.py tests/test_worklog_wall.py tests/test_api_keys.py`
Expected: PASS. (`test_rest_conformance.py` and `test_content_surface_scoping.py` fail until Task 8 classifies the routes; do not run them here.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/worklog.py backend/app/api/routes/worklog.py backend/app/main.py backend/tests/test_worklog_rest.py backend/tests/test_api_keys.py
git commit -m "feat(worklog): serve the work log over REST"
```

### Task 6: MCP tools and scopes

**Files:**
- Modify: `backend/app/api/mcp/server.py` (six tools after `checkpoint_latest`)
- Modify: `backend/app/api/mcp/scopes.py` (the three tool sets)
- Modify: `backend/tests/test_mcp.py` (the pinned `EXPECTED_TOOLS` roster)
- Test: `backend/tests/test_worklog_mcp.py`

**Interfaces:**
- Consumes: Contracts → Service (Tasks 3–4), Schemas (Task 5).
- Produces: Contracts → MCP.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_worklog_mcp.py`:

```python
"""The work-log lane over MCP: the same verbs, the same service, the same keys."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest

from app.api.mcp.client_identity import ORIGIN_HEADER
from app.api.mcp.scopes import TOOL_SCOPES


@pytest.fixture
def mcp_on_the_test_session(session, monkeypatch):
    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _ctx_manager():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _ctx_manager())


def _ctx(headers):
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=Headers(headers)))
    )


def test_each_tool_has_the_scope_the_spec_names():
    assert {name: TOOL_SCOPES[name] for name in (
        "worklog_append", "worklog_update", "worklog_resume",
        "worklog_workstreams", "worklog_entries", "worklog_purge",
    )} == {
        "worklog_append": "capture",
        "worklog_update": "capture",
        "worklog_resume": "read",
        "worklog_workstreams": "read",
        "worklog_entries": "read",
        "worklog_purge": "admin",
    }


async def test_append_then_resume_then_list(mcp_on_the_test_session):
    from app.api.mcp import server

    appended = json.loads(await server.worklog_append(
        project="proj",
        workstream="plan-a",
        entries=[{"kind": "checkpoint", "body": "state"}, {"kind": "ledger", "body": "Task 1\n"}],
        run_key="run-1",
    ))
    assert appended["workstream"]["key"] == "plan-a"
    assert len(appended["entry_ids"]) == 2

    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["checkpoint"]["body"] == "state"

    listed = json.loads(await server.worklog_workstreams(project="proj"))
    assert [w["key"] for w in listed["items"]] == ["plan-a"]

    entries = json.loads(await server.worklog_entries(project="proj", workstream="plan-a", kind="ledger"))
    assert [e["body"] for e in entries["items"]] == ["Task 1\n"]


async def test_the_run_can_come_from_the_origin_header(mcp_on_the_test_session):
    from app.api.mcp import server

    appended = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a",
        entries=[{"kind": "note", "body": "n"}],
        ctx=_ctx({ORIGIN_HEADER: "boot-7"}),
    ))
    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["notes"][0]["run_key"].endswith("boot-7")
    assert appended["entry_ids"] == [resumed["notes"][0]["id"]]


async def test_an_undeclared_run_is_refused(mcp_on_the_test_session):
    from app.api.mcp import server

    with pytest.raises(ValueError):
        await server.worklog_append(project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}])


async def test_unknown_workstreams_answer_null(mcp_on_the_test_session):
    from app.api.mcp import server

    assert json.loads(await server.worklog_resume(project="proj", workstream="nope")) is None
    assert json.loads(await server.worklog_entries(project="proj", workstream="nope")) is None
    assert json.loads(await server.worklog_update(project="proj", workstream="nope", state="closed")) is None
    assert json.loads(await server.worklog_purge(project="proj", workstream="nope")) is None


async def test_update_then_purge(mcp_on_the_test_session):
    from app.api.mcp import server

    await server.worklog_append(
        project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}], run_key="r"
    )
    closed = json.loads(await server.worklog_update(project="proj", workstream="plan-a", state="closed", retain=True))
    assert closed["state"] == "closed" and closed["retain"] is True
    purged = json.loads(await server.worklog_purge(project="proj", workstream="plan-a"))
    assert purged == {"purged": "plan-a", "entries": 1}


async def test_a_rest_write_is_readable_over_mcp(client, auth_headers, mcp_on_the_test_session):
    from app.api.mcp import server

    response = await client.post(
        "/api/v1/worklog/entries",
        json={"project": "proj", "workstream": "plan-a", "entries": [{"kind": "checkpoint", "body": "from rest"}]},
        headers={**auth_headers, ORIGIN_HEADER: "run-1"},
    )
    assert response.status_code == 201
    resumed = json.loads(await server.worklog_resume(project="proj", workstream="plan-a"))
    assert resumed["checkpoint"]["body"] == "from rest"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_mcp.py`
Expected: FAIL — `KeyError: 'worklog_append'`.

- [ ] **Step 3: Classify the tools**

In `backend/app/api/mcp/scopes.py`:

In `CAPTURE_TOOLS`, immediately after the line `    "checkpoint_save",` insert:

```python
    # The work log's writers: appending to a workstream and moving its state.
    "worklog_append",
    "worklog_update",
```

In `READ_TOOLS`, immediately after the line `    "checkpoint_latest",` insert:

```python
    "worklog_resume",
    "worklog_workstreams",
    "worklog_entries",
```

In `ADMIN_TOOLS`, immediately after the line `    "document_delete_subtree",` insert:

```python
    # Erasing a workstream and its history is irrecoverable, which is the
    # subtree delete's argument again: a capture key appends, it does not erase.
    "worklog_purge",
```

- [ ] **Step 4: Add the tools**

In `backend/app/api/mcp/server.py`, immediately before the comment block that begins `# Document tools -- the MCP half of the document door`, insert:

```python
# ---------------------------------------------------------------------------
# Work-log tools (spec 2026-09-23 §2). Every one calls app.services.worklog,
# the same functions app/api/routes/worklog.py serves. An unknown workstream
# answers null, matching the REST door's 404.
# ---------------------------------------------------------------------------


def _worklog_limit(value: int, ceiling: int) -> int:
    return max(1, min(value, ceiling))


@mcp.tool(
    description=(
        "Append entries to a work-log workstream: where a coding session keeps "
        "its working data. kind 'checkpoint' is your own summary of where the "
        "work stands, 'ledger' is progress text stored exactly as written, "
        "'note' is a constraint or gotcha for the next session. Never extracted "
        "into memories and never returned by memory_search. Creates the "
        "workstream on first use and reopens a closed one. entries: 1-100 of "
        "{kind, body, properties?}. Needs a run identity: run_key or the "
        "X-Darkmem-Origin header."
    )
)
async def worklog_append(
    project: str,
    workstream: str,
    entries: list[dict],
    title: str | None = None,
    client: str | None = None,
    properties: dict | None = None,
    run_key: str | None = None,
    ctx: Context | None = None,
) -> str:
    from app.schemas.worklog import WorklogAppendRequest
    from app.services import worklog
    from app.services.checkpoints import resolve_checkpoint_origin

    body = WorklogAppendRequest(
        project=project,
        workstream=workstream,
        entries=entries,
        title=title,
        client=client,
        properties=properties or {},
        run_key=run_key,
    )
    source = resolve_client_source(None, ctx, fallback=worklog.DOOR_SOURCE)
    resolved = resolve_checkpoint_origin(
        body.run_key or declared_origin(ctx), source=source, project=body.project
    )
    async with async_session_factory() as session:
        try:
            result = await worklog.append(
                session,
                project=body.project,
                key=body.workstream,
                run_key=resolved,
                entries=[entry.model_dump() for entry in body.entries],
                title=body.title,
                client=body.client,
                properties=body.properties,
                actor=current_key_name() or source,
                api_key_id=current_api_key_id(),
            )
            payload = {
                "workstream": worklog.serialize_workstream(result.workstream),
                "entry_ids": [str(entry_id) for entry_id in result.entry_ids],
            }
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps(payload)


@mcp.tool(
    description=(
        "Resume a work-log workstream at session start: its latest checkpoint "
        "verbatim, its 50 newest notes (notes_truncated when there are more) "
        "and its last 20 ledger entries in order, plus the workstream's "
        "properties naming the plan and spec to read. null when it does not exist."
    )
)
async def worklog_resume(project: str, workstream: str) -> str:
    from app.services import worklog

    async with async_session_factory() as session:
        answer = await worklog.resume(session, project=project, key=workstream)
    return json.dumps(answer)


@mcp.tool(
    description=(
        "List a project's work-log workstreams, newest-created first, "
        "optionally only 'open' or 'closed' ones. Page with limit (1-200) and "
        "by passing the answer's next_before as before; answers items and next_before."
    )
)
async def worklog_workstreams(
    project: str, state: str | None = None, before: str | None = None, limit: int = 50
) -> str:
    from app.services import worklog

    async with async_session_factory() as session:
        page = await worklog.list_workstreams(
            session,
            project=project,
            state=state,
            before=before,
            limit=_worklog_limit(limit, 200),
        )
    return json.dumps(page)


@mcp.tool(
    description=(
        "Read one workstream's work-log entries oldest first, optionally one "
        "kind (checkpoint, ledger, note) and only those written since an ISO "
        "8601 time. Page forward by passing the answer's next_after as after; "
        "limit 1-500. null when the workstream does not exist."
    )
)
async def worklog_entries(
    project: str,
    workstream: str,
    kind: str | None = None,
    since: str | None = None,
    after: int | None = None,
    limit: int = 100,
) -> str:
    from datetime import datetime

    from app.services import worklog

    since_at = datetime.fromisoformat(since) if since else None
    async with async_session_factory() as session:
        found = await worklog.get_workstream(session, project=project, key=workstream)
        if found is None:
            return json.dumps(None)
        page = await worklog.list_entries(
            session,
            workstream_id=found.id,
            kind=kind,
            since=since_at,
            after=after,
            limit=_worklog_limit(limit, 500),
        )
    return json.dumps(page)


@mcp.tool(
    description=(
        "Update a work-log workstream: state 'closed' when the work is finished "
        "(or 'open' to reopen), retain true to exempt it from retention, a new "
        "title, or properties to merge in. null when it does not exist."
    )
)
async def worklog_update(
    project: str,
    workstream: str,
    state: str | None = None,
    retain: bool | None = None,
    title: str | None = None,
    properties: dict | None = None,
) -> str:
    from app.schemas.worklog import WorkstreamUpdateRequest
    from app.services import worklog

    body = WorkstreamUpdateRequest(state=state, retain=retain, title=title, properties=properties)
    async with async_session_factory() as session:
        try:
            found = await worklog.get_workstream(session, project=project, key=workstream)
            if found is None:
                return json.dumps(None)
            updated = await worklog.update_workstream(
                session,
                found.id,
                state=body.state,
                retain=body.retain,
                title=body.title,
                properties=body.properties,
                actor=current_key_name(),
                api_key_id=current_api_key_id(),
            )
            payload = worklog.serialize_workstream(updated)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps(payload)


@mcp.tool(
    description=(
        "Erase a work-log workstream and every entry in it, irrecoverably. The "
        "erase is journaled before it runs and refused if the journal row does "
        "not land. Needs an admin-scoped key. null when it does not exist."
    )
)
async def worklog_purge(project: str, workstream: str) -> str:
    from app.services import worklog

    async with async_session_factory() as session:
        try:
            found = await worklog.get_workstream(session, project=project, key=workstream)
            if found is None:
                return json.dumps(None)
            removed = await worklog.purge_workstream(
                session, found.id, actor=current_key_name(), api_key_id=current_api_key_id()
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps({"purged": workstream, "entries": removed})
```

In `backend/tests/test_mcp.py`, the pinned roster `EXPECTED_TOOLS` must name the new tools. Replace

```python
    "research_run",
})
```

with

```python
    "research_run",
    # The work log (spec 2026-09-23).
    "worklog_append",
    "worklog_entries",
    "worklog_purge",
    "worklog_resume",
    "worklog_update",
    "worklog_workstreams",
})
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_mcp.py tests/test_mcp.py tests/test_mcp_auth.py tests/test_prompt_agent_instructions.py::test_every_tool_carries_a_usable_description tests/test_prompt_agent_instructions.py::test_scopes_and_instructions_agree_on_the_roster`
Expected: PASS. (`test_every_registered_tool_is_named_in_the_instructions` fails until Task 9; do not run it here.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mcp/server.py backend/app/api/mcp/scopes.py backend/tests/test_mcp.py backend/tests/test_worklog_mcp.py
git commit -m "feat(mcp): add the work-log tools"
```

### Task 7: Keyed document routes and manifest

**Files:**
- Modify: `backend/app/api/routes/documents.py` (import; module-level scope dependencies; `put_document_route`; a separate `/by-uri` handler; the manifest route and models)
- Modify: `backend/tests/test_api_keys.py` (the two pinned scope-gated route sets)
- Test: `backend/tests/test_documents_keyed.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: Contracts → Documents.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_documents_keyed.py`:

```python
"""Which document doors a `dmk_` key reaches, and the sync manifest."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services.api_keys import issue_key

V1 = "/api/v1/documents"
FINGERPRINT = "keyed-probe|4"


class _ScriptedEmbedder:
    """Enough of the orchestrator for put_document to embed without a network."""

    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0, 0.0] for _ in texts], FINGERPRINT)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0, 0.0], FINGERPRINT


@pytest.fixture
def scripted_embedder(client):
    from app.main import app
    from app.services.embedder_registry import embedder_registry

    previous = getattr(app.state, "llm", None)
    app.state.llm = _ScriptedEmbedder()
    embedder_registry.forget(FINGERPRINT)
    yield
    app.state.llm = previous
    embedder_registry.forget(FINGERPRINT)


async def _key(session, *scopes):
    _row, credential = await issue_key(session, name=f"k-{uuid.uuid4().hex[:6]}", scopes=list(scopes))
    return {"Authorization": f"Bearer {credential}"}


async def _document(session, *, project="proj", uri, content_hash="h1"):
    document_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO documents (id, project, uri, title, source_type, content_hash) "
            "VALUES (CAST(:id AS uuid), CAST(:p AS text), CAST(:u AS text), 't', 'markdown', CAST(:h AS text))"
        ),
        {"id": str(document_id), "p": project, "u": uri, "h": content_hash},
    )
    return document_id


async def test_a_capture_key_files_and_a_read_key_reads_it_back(client, session, scripted_embedder):
    capture = await _key(session, "capture")
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/specs/b.md", "content": "# B\n\nThe design.\n"}
    filed = await client.post(V1, json=body, headers=capture)
    assert filed.status_code == 201, filed.text
    assert filed.json()["outcome"] == "created"
    back = await client.get(
        f"{V1}/by-uri",
        params={"project": "proj", "uri": "superpowers/specs/b.md", "include_content": "true"},
        headers=read,
    )
    assert back.status_code == 200
    assert back.json()["content"] == body["content"]


async def test_a_read_key_cannot_file(client, session):
    read = await _key(session, "read")
    body = {"project": "proj", "uri": "superpowers/specs/b.md", "content": "# B\n"}
    assert (await client.post(V1, json=body, headers=read)).status_code == 403


async def test_the_rest_of_the_document_surface_stays_login_only(client, session):
    every_scope = await _key(session, "read", "capture", "admin")
    document_id = await _document(session, uri="superpowers/specs/a.md")
    assert (await client.get(f"{V1}/{document_id}", headers=every_scope)).status_code == 401
    assert (await client.get(V1, params={"project": "proj"}, headers=every_scope)).status_code == 401
    assert (await client.post(f"{V1}/search", json={"project": "proj", "query": "x"}, headers=every_scope)).status_code == 401


async def test_the_manifest_lists_a_prefix_in_uri_order_and_pages(client, session):
    read = await _key(session, "read")
    for uri in ("superpowers/specs/b.md", "superpowers/specs/a.md", "superpowers/plans/p.md", "other/x.md"):
        await _document(session, uri=uri, content_hash=f"hash-{uri}")
    await _document(session, project="elsewhere", uri="superpowers/specs/z.md")

    first = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": "superpowers", "limit": 2}, headers=read,
    )
    assert first.status_code == 200
    body = first.json()
    assert [i["uri"] for i in body["items"]] == ["superpowers/plans/p.md", "superpowers/specs/a.md"]
    assert body["items"][1]["content_hash"] == "hash-superpowers/specs/a.md"
    assert body["next_after"] == "superpowers/specs/a.md"

    rest = await client.get(
        f"{V1}/manifest",
        params={"project": "proj", "uri_prefix": "superpowers", "after": body["next_after"], "limit": 2},
        headers=read,
    )
    assert [i["uri"] for i in rest.json()["items"]] == ["superpowers/specs/b.md"]
    assert rest.json()["next_after"] is None

    everything = await client.get(f"{V1}/manifest", params={"project": "proj"}, headers=read)
    assert len(everything.json()["items"]) == 4


@pytest.mark.parametrize("prefix", ["superpowers", "superpowers/"])
async def test_a_prefix_matches_whole_segments_with_or_without_a_trailing_slash(client, session, auth_headers, prefix):
    await _document(session, uri="superpowers/specs/a.md")
    await _document(session, uri="superpowersx/a.md")
    response = await client.get(
        f"{V1}/manifest", params={"project": "proj", "uri_prefix": prefix}, headers=auth_headers
    )
    assert [i["uri"] for i in response.json()["items"]] == ["superpowers/specs/a.md"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_documents_keyed.py`
Expected: FAIL — the keyed filing answers 401.

- [ ] **Step 3: Key the two sync routes**

In `backend/app/api/routes/documents.py`:

Replace the line

```python
from app.api.auth import require_auth
```

with

```python
from app.api.auth import Principal, require_auth, require_scope
```

Immediately after the line `router = APIRouter(prefix="/api/v1/documents", tags=["documents"])` add:

```python

# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the by-uri read and the
# manifest. Every other document route stays login-only; widening one is a
# decision about what a leaked key can read or erase, made per route.
_require_capture = require_scope("capture")
_require_read = require_scope("read")
```

In `put_document_route`, replace the parameter line

```python
    _user=Depends(require_auth),
```

(the one directly under `body: DocumentPutRequest,`) with

```python
    principal: Principal = Depends(_require_capture),
```

and in its `put_document(...)` call replace

```python
            title=body.title, source_type=body.source_type, source="api",
```

with

```python
            title=body.title, source_type=body.source_type, source="api",
            actor=principal.actor,
```

Give `/by-uri` its own handler. Delete the decorator line

```python
@router.get("/by-uri", response_model=DocumentBlocksResponse)
```

that sits directly under `@router.get("/{document_id}", response_model=DocumentBlocksResponse)` (leave `document_blocks_route` itself, with its `require_auth`, unchanged), and immediately **before** the line `@router.get("/{document_id}", response_model=DocumentBlocksResponse)` insert:

```python
@router.get("/by-uri", response_model=DocumentBlocksResponse)
async def document_blocks_by_uri_route(
    block_ids: list[UUID] | None = Query(default=None),
    project: str | None = Query(None),
    uri: str | None = Query(None),
    include_content: bool = Query(False),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentBlocksResponse:
    """The keyed twin of `GET /{document_id}`: same read, reachable by a read key.

    Registered before `/{document_id}` so the literal path wins the match.
    """
    return await document_blocks_route(
        document_id=None,
        block_ids=block_ids,
        project=project,
        uri=uri,
        include_content=include_content,
        _user=None,
        session=session,
    )
```

- [ ] **Step 4: Add the manifest**

Immediately before the line `@router.get("", response_model=DocumentListResponse)` insert:

```python
class DocumentManifestItem(BaseModel):
    id: str
    uri: str
    content_hash: str | None
    updated_at: datetime


class DocumentManifestResponse(BaseModel):
    items: list[DocumentManifestItem]
    next_after: str | None


# The whole-segment prefix predicate the subtree rename and delete use, so
# `superpowers` never matches `superpowersx/`. An empty prefix lists the whole
# project. Keyset on uri, which is unique within a project.
_MANIFEST_SQL = text(
    """
    SELECT CAST(id AS text) AS id, uri, content_hash, updated_at
    FROM documents
    WHERE project = CAST(:project AS text)
      AND uri IS NOT NULL
      AND (CAST(:prefix AS text) = ''
           OR uri = CAST(:prefix AS text)
           OR left(uri, length(CAST(:prefix AS text)) + 1) = CAST(:prefix AS text) || '/')
      AND (CAST(:after AS text) IS NULL OR uri > CAST(:after AS text))
    ORDER BY uri
    LIMIT :limit
    """
)


@router.get("/manifest", response_model=DocumentManifestResponse)
async def document_manifest(
    project: str = Query(min_length=1),
    uri_prefix: str = Query(""),
    after: str | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentManifestResponse:
    """`{uri, content_hash}` for a project's documents under a prefix, no content.

    What a mirror pull diffs against its recorded hashes, so it fetches only
    the documents that changed. A trailing slash on the prefix is dropped:
    `superpowers/` and `superpowers` name the same subtree.
    """
    rows = (await session.execute(
        _MANIFEST_SQL,
        {"project": project, "prefix": uri_prefix.rstrip("/"), "after": after, "limit": limit},
    )).mappings().all()
    items = [DocumentManifestItem(**dict(row)) for row in rows]
    return DocumentManifestResponse(
        items=items,
        next_after=items[-1].uri if len(items) == limit else None,
    )
```

`datetime`, `BaseModel` and `text` are already imported in `documents.py` (lines 62, 66, 67 on 2026-09-23).

- [ ] **Step 5: Pin the new scope-gated routes**

In `backend/tests/test_api_keys.py`, in **both** pinned sets (`test_exactly_the_intended_routes_are_scope_gated` and the mutation drill's `expected`), immediately after the line

```python
            ("DELETE", "/api/v1/worklog/workstreams/{workstream_id}"),
```

(which Task 5 added) insert:

```python
            ("POST", "/api/v1/documents"),
            ("GET", "/api/v1/documents/by-uri"),
            ("GET", "/api/v1/documents/manifest"),
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_documents_keyed.py tests/test_documents_api.py tests/test_document_door.py tests/test_read_only_doors.py tests/test_api_keys.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_keyed.py backend/tests/test_api_keys.py
git commit -m "feat(documents): key the sync routes, add manifest"
```

### Task 8: Guard registries

**Files:**
- Modify: `backend/app/services/content_surfaces.py` (`ROUTES_WITHOUT_MEMORY_CONTENT`, `MCP_TOOLS_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`)
- Modify: `backend/tests/test_door_parity.py` (`PARITY_TABLE`)
- Modify: `docs/two-door-parity.md` (generated table and headline counts)
- Modify: `backend/tests/test_door_parity.py` (`_WRITE_WIRE_SHAPE` prose)

**Interfaces:**
- Consumes: Contracts → REST (Task 5), MCP (Task 6), Documents (Task 7).
- Produces: nothing later tasks consume.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Run the guards to see them fail**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_api/test_rest_conformance.py::test_every_route_status_code_matches_the_convention tests/test_door_parity.py tests/test_content_surface_scoping.py`
Expected: FAIL — `POST /api/v1/worklog/entries has no conformance entry`, unclassified routes and tools in the parity and content-surface tests.

- [ ] **Step 2: Classify the content surfaces**

In `backend/app/services/content_surfaces.py`, inside `ROUTES_WITHOUT_MEMORY_CONTENT`, immediately after the line `    "GET /api/v1/checkpoints/latest",` insert:

```python
    # The work-log lane (spec 2026-09-23). No memory content crosses: a
    # workstream and its entries are a client's own notes about its work,
    # never derived from a `memories` row, and every read is scoped by the
    # project or the workstream id the caller names.
    "POST /api/v1/worklog/entries",
    "GET /api/v1/worklog/resume",
    "GET /api/v1/worklog/workstreams",
    "GET /api/v1/worklog/workstreams/{workstream_id}/entries",
    "PATCH /api/v1/worklog/workstreams/{workstream_id}",
    "DELETE /api/v1/worklog/workstreams/{workstream_id}",
```

In the same set, immediately after the line `    "GET /api/v1/documents",` insert:

```python
    # The sync manifest: uri, hash and time per document, no content at all.
    "GET /api/v1/documents/manifest",
```

Inside `MCP_TOOLS_WITHOUT_MEMORY_CONTENT`, immediately after the line `    "mcp:checkpoint_latest",` insert:

```python
    # The work-log tools, for the reason their REST twins carry above.
    "mcp:worklog_append",
    "mcp:worklog_resume",
    "mcp:worklog_workstreams",
    "mcp:worklog_entries",
    "mcp:worklog_update",
    "mcp:worklog_purge",
```

- [ ] **Step 3: Add the conformance entries**

In `backend/tests/test_api/test_rest_conformance.py`, inside `EXPECTED_STATUS`, immediately after the line `    ("GET", "/health"): 200,` insert:

```python
    ("POST", "/api/v1/worklog/entries"): 201,
    ("GET", "/api/v1/worklog/resume"): 200,
    ("GET", "/api/v1/worklog/workstreams"): 200,
    ("GET", "/api/v1/worklog/workstreams/{workstream_id}/entries"): 200,
    ("PATCH", "/api/v1/worklog/workstreams/{workstream_id}"): 200,
    ("DELETE", "/api/v1/worklog/workstreams/{workstream_id}"): 204,
    ("GET", "/api/v1/documents/manifest"): 200,
```

In the same table, replace the comment

```python
    # The by-uri half of the three document-keyed verbs: one handler each,
    # two paths, so the statuses are the id form's by construction.
```

with

```python
    # The by-uri half of the three document-keyed verbs. Outline and delete
    # share one handler with their id form; the blocks read has its own keyed
    # handler since the 2026-09-23 work-log increment. Same statuses either way.
```

- [ ] **Step 4: Add the parity rows**

In `backend/tests/test_door_parity.py`, inside `PARITY_TABLE`, immediately after this block:

```python
    Surface(
        name="checkpoint.latest",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/checkpoints/latest"),),
        mcp=("checkpoint_latest",),
    ),
```

insert:

```python
    Surface(
        name="worklog.append",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/worklog/entries"),),
        mcp=("worklog_append",),
    ),
    Surface(
        name="worklog.resume",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/worklog/resume"),),
        mcp=("worklog_resume",),
    ),
    Surface(
        name="worklog.workstreams",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/worklog/workstreams"),),
        mcp=("worklog_workstreams",),
    ),
    Surface(
        name="worklog.entries",
        status=TWO_DOOR,
        rest=(("GET", f"{V1}/worklog/workstreams/{{workstream_id}}/entries"),),
        mcp=("worklog_entries",),
        note=(
            "Stated wire asymmetry: the route names the workstream by id, the "
            "tool by (project, key), since an agent knows its key; both resolve "
            "to one workstream and call one list_entries."
        ),
    ),
    Surface(
        name="worklog.update",
        status=TWO_DOOR,
        rest=(("PATCH", f"{V1}/worklog/workstreams/{{workstream_id}}"),),
        mcp=("worklog_update",),
    ),
    Surface(
        name="worklog.purge",
        status=TWO_DOOR,
        rest=(("DELETE", f"{V1}/worklog/workstreams/{{workstream_id}}"),),
        mcp=("worklog_purge",),
        note=(
            "admin on both doors: the route declares require_scope('admin') and "
            "the tool sits in ADMIN_TOOLS. Both call one purge_workstream, which "
            "journals workstream_purged before the delete and refuses when the "
            "row does not land."
        ),
    ),
    Surface(
        name="documents.manifest",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/documents/manifest"),),
        mcp=(),
        reason=(
            "A sync read with one caller, the dr-superpowers mirror, which "
            "speaks REST with a dmk_ key: it serves uri, content_hash and "
            "updated_at so a pull fetches only what changed. An agent reading a "
            "document already has document_get and document_outline; a "
            "manifest tool would serve it nothing they do not."
        ),
    ),
```

In the same file, the `_WRITE_WIRE_SHAPE` prose states two things Task 6 and Task 7 made false. Replace

```python
    "POST /documents/delete sits behind the same ordinary auth every other "
    "route on this row does; the MCP twin `document_delete_subtree` is held "
    "at `admin`, the scope `code_reindex` has and the only other tool that "
    "holds it. That is deliberate and not a parity gap: MCP scopes are per "
```

with

```python
    "POST /documents/delete sits behind ordinary login auth, while POST "
    "/documents on the same row also admits a capture-scoped key (spec "
    "2026-09-23, the dr-superpowers mirror); the MCP twin "
    "`document_delete_subtree` is held at `admin`, the scope `code_reindex` "
    "and `worklog_purge` also hold. That is deliberate and not a parity gap: "
    "MCP scopes are per "
```

- [ ] **Step 5: Regenerate the parity document**

Run from `backend/`:

```bash
.venv/bin/python - <<'EOF'
from pathlib import Path
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown
doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8")
EOF
.venv/bin/python -c "
from collections import Counter
from tests.test_door_parity import PARITY_TABLE
c = Counter(s.status for s in PARITY_TABLE); print(len(PARITY_TABLE), dict(c))"
```

Expected: `89 {...}` with `two-door` 31, `rest-single-door` 51, `mcp-single-door` 7, and no `divergent`. Then in `docs/two-door-parity.md` replace the line

```markdown
**82 surfaces: 25 two-door, 57 single-door with a stated reason (50 REST-only, 7 MCP-only), 0 divergent.**
```

with

```markdown
**89 surfaces: 31 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent.**
```

If the printed counts differ from 89 / 31 / 51 / 7, write the printed numbers instead and note the difference in the commit body.

- [ ] **Step 6: Run the guards to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_api/test_rest_conformance.py tests/test_door_parity.py tests/test_content_surface_scoping.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/content_surfaces.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "test(guards): classify the work-log doors"
```

### Task 9: Instructions and CLAUDE.md counts

**Files:**
- Modify: `backend/app/services/prompt.py` (`agent_instructions`)
- Modify: `backend/tests/test_prompt_agent_instructions.py`
- Modify: `CLAUDE.md` (MCP scope paragraph; strict-journal callers; new Work log section)

**Interfaces:**
- Consumes: Contracts → MCP (Task 6).
- Produces: nothing later tasks consume.

**Items:** 4

**Implementer:** dr-superpowers:impl-sonnet-medium
**Executor:** codex gpt-6-sol / low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_prompt_agent_instructions.py`:

```python


def test_the_instructions_route_working_data_to_the_work_log():
    """The no-log rule has to say where the log goes, or agents drop it here."""
    text = prompt.PROMPTS["agent_instructions"]
    assert "worklog_append" in text
    assert "worklog_resume" in text
    assert "goes to the work log" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_prompt_agent_instructions.py`
Expected: FAIL — `test_the_instructions_route_working_data_to_the_work_log` and `test_every_registered_tool_is_named_in_the_instructions` (the six work-log tools are unnamed).

- [ ] **Step 3: Update the instructions**

In `backend/app/services/prompt.py`, inside `"agent_instructions"`, replace

```python
        "when when-it-became-true matters. If nothing durable is left once the "
        "log is removed, save nothing.\n"
```

with

```python
        "when when-it-became-true matters. Working data — a checkpoint, a "
        "progress line, a note to your next session — goes to the work log "
        "(below), never here.\n"
```

and replace

```python
        "### Session checkpoints\n"
        "- **checkpoint_save** — record where a working session got to.\n"
        "- **checkpoint_latest** — resume from the last checkpoint.\n"
```

with

```python
        "### Work log — working data, kept apart from memories\n"
        "A workstream is one piece of work in a project (a plan, a design, an "
        "ad-hoc task), named by a key you choose. Its entries are never "
        "extracted into memories and never returned by memory_search.\n"
        "- **worklog_resume** — at session start: the latest checkpoint, the "
        "notes and the last ledger entries of a workstream.\n"
        "- **worklog_append** — add entries: `checkpoint` (your own summary of "
        "where the work stands), `ledger` (progress text, stored exactly as "
        "written) or `note` (constraints and gotchas for the next session). "
        "Append a checkpoint at every stop.\n"
        "- **worklog_workstreams** / **worklog_entries** — list a project's "
        "workstreams, or read one workstream's entries in order.\n"
        "- **worklog_update** — close or reopen a workstream, retain it, or "
        "change its title or properties.\n"
        "- **worklog_purge** — erase a workstream and its entries; needs an "
        "admin-scoped key.\n"
        "- **checkpoint_save** / **checkpoint_latest** — the older single-run "
        "checkpoint pair, still served; prefer the work log.\n"
        "After a checkpoint, file the durable facts the run established with "
        "memory_add, one per entry: the work log keeps how the work went, "
        "memories keep what is now true.\n"
```

- [ ] **Step 4: Update CLAUDE.md**

In `CLAUDE.md`, make these exact replacements.

Replace

```markdown
Authorization is per tool, not per door: `capture` covers the 13 writers
```

with

```markdown
Authorization is per tool, not per door: `capture` covers the 15 writers
```

Replace

```markdown
`research_run`, and
increment 8's four block verbs
```

with

```markdown
`research_run`, the work log's `worklog_append` and `worklog_update`, and
increment 8's four block verbs
```

Replace

```markdown
`read` covers 25; `admin` covers the 2 repository-scale control tools
```

with

```markdown
`read` covers 28; `admin` covers the 3 repository-scale control tools
```

Replace

```markdown
increment 2's `document_delete_subtree`).
Scopes do not imply one another. `admin` reaches exactly those two
tools — a repository index and a whole-subtree erase, neither of them memory
writing — so a key holding only `admin` reaches nothing else, and a `capture`
key can trigger no index and delete no subtree.
```

with

```markdown
increment 2's `document_delete_subtree`, and the work log's `worklog_purge`).
Scopes do not imply one another. `admin` reaches exactly those three
tools — a repository index, a whole-subtree erase and a workstream erase, none
of them memory writing — so a key holding only `admin` reaches nothing else,
and a `capture` key can trigger no index, delete no subtree and purge no
workstream.
```

Replace

```markdown
`POST /api/v1/documents/delete`, sits behind ordinary auth with every other
document route — the scope asymmetry is real and is recorded on
```

with

```markdown
`POST /api/v1/documents/delete`, sits behind ordinary login auth like every
document route outside the three a dr-superpowers mirror syncs through (filing,
the by-uri read and the manifest, which admit a scoped key since the
2026-09-23 work-log increment) — the scope asymmetry is real and is recorded on
```

Replace

```markdown
authenticated key sees the full 40-tool catalogue, including writers it
```

with

```markdown
authenticated key sees the full 46-tool catalogue, including writers it
```

Replace the line containing `**denominator** — and under-power announces itself where that does not. **Six**` so that `**Six**` reads `**Seven**`, and replace

```markdown
`PageJournalWriteFailed` for the same firewall reason. **The strict contract is a shape, not a shared
```

with

```markdown
`PageJournalWriteFailed` for the same firewall reason. The seventh is
`worklog.purge_workstream`, which raises its own `WorklogJournalWriteFailed`
before erasing a workstream, for the same reason. **The strict contract is a shape, not a shared
```

Also replace `The six do **not** all` with `The seven do **not** all`.

Immediately before the line `## Cross-cutting invariants`, insert:

```markdown
## Work log (`app/services/worklog.py`)

A coding client's working data — checkpoints it summarised itself, ledger
chunks, notes to its next session — lives in `workstreams` /
`worklog_entries`, never in `memories`
(`docs/superpowers/specs/2026-09-23-work-log-lane-design.md`). Entries are
append-only from the API and ordered by `seq`, an identity column, never by
`created_at`: every entry of one append shares `now()`. A `ledger` entry's body
is the exact text the client appended, so concatenating a workstream's ledger
entries reproduces its file. The run key resolves exactly as checkpoints
resolve it, and an undeclared run is refused. An append locks the workstream
row (`SELECT … FOR UPDATE`, or the insert that creates it) before it decides
anything, which serialises it against a purge or a retention delete. `worklog_purge`
and its REST twin are `admin`-scoped and strict-journal. Journal payloads carry
the workstream key and counts, never entry text. Nothing in the lane is
extracted, ranked with memories or reachable from the vault.

```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_prompt_agent_instructions.py tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py tests/test_mcp.py tests/test_api_keys.py tests/test_worklog_wall.py`
Expected: PASS — this is `CLAUDE.md`'s mandatory guard leg, green for the first time since Task 5.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/prompt.py backend/tests/test_prompt_agent_instructions.py CLAUDE.md
git commit -m "feat(mcp): route working data to the work log"
```
