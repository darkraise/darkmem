# Work-log lane, increment 2: search — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the work log searchable: a `worklog_embeddings` vector family, a work-log arm of the hourly embedding refresh, and `worklog_search` on both doors fusing a keyword arm and an exact cosine arm by RRF.

**Architecture:** The registry gains one family with a `project` column and no HNSW index. A new writer module, `app/services/worklog_embeddings.py`, embeds each entry's first 8,000 characters; `block_embedding_refresh` calls it as a third arm on its own `worklog_batch` budget, and appends never embed inline. `worklog.search` ranks `search_vector` and the project's vectors, fuses them with `rank_fusion.rrf_fuse`, and the REST route and MCP tool both call it.

**Tech Stack:** FastAPI, SQLAlchemy 2 async over asyncpg, Postgres 17 with pgvector, MCP SDK `mcp==2.1.1`, pytest (asyncio auto mode).

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** inline — `claude --model sonnet --effort high` — three of nine tasks are heavy (1, 6, 7), two are four-band (3, 4; 3 × 2 ≤ 9, so both are delegated) and five carry a Codex Executor line, so every task is delegated and the controller only dispatches, reviews and records; delegation sets the effort to high.

**Plan review:** 2026-09-25 — codex gpt-6-astra / xhigh — executability 15 / coherence 18 / coverage 17 / assumptions 18 (round 1)

> **External executors:** codex

## Global Constraints

- Spec §9: increment 2 is "the embeddings family, the refresh-job arm, the search verb". Nothing here touches `session_checkpoints`, document revisions, the memory-door warning, retention or the UI.
- `backend/migrations/versions/0001_baseline.py` is not edited: `app/schema_guard.py` hashes that file, so any edit forces every deployed database to be dropped and recreated. Child tables are created by `embedder_registry` at registration and at boot (`reconcile`), never by a migration.
- The family is `worklog_embeddings__<slug>`: `(entry_id UUID FK → worklog_entries ON DELETE CASCADE, fingerprint, project TEXT NOT NULL, embedding vector(N), created_at)`, primary key `(entry_id, fingerprint)`, a btree index on `project`, and **no** HNSW index.
- Only the first 8,000 characters of a body are embedded (`EMBED_CHARS = 8_000`); the keyword arm indexes the whole body.
- Appends never embed. The only writer of the family is the refresh job's work-log arm, budgeted by `worklog_batch` (default 500, 0 disables it).
- Search: `project` is required; the keyword arm is `ts_rank(e.search_vector, q)` with `plainto_tsquery('english', :query)`; the semantic arm is exact cosine distance `v.embedding <=> :vec` over `v.project = :project`; both arms read `fusion_fetch_depth(limit)` rows and fuse with `rank_fusion.rrf_fuse` at equal list weights (1.0). `RRF_K` is never redeclared.
- The semantic arm is skipped, and the answer says `semantic_ran: false`, when the orchestrator is absent, `settings.read_only` is true, or the query embed raises. A missing child table (nothing embedded yet) is an arm that ran and found nothing.
- A hit is `{entry, workstream, rrf_score, arms}`: `entry` is `serialize_entry`'s shape, `workstream` the key, `arms` a subset of `["keyword", "semantic"]` in that order.
- Scopes: `worklog_search` is `read` on both doors (REST through `require_scope("read")`).
- Nothing in the lane is reachable from `app.services.pipeline`, `hybrid_search`, `layer_composition`, `chat` or the vault writers, and no work-log module reads a memory table (spec §7).
- Tests run from `backend/` with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` against the dev-compose Postgres (`docker compose -f docker-compose.dev.yml up -d postgres` from the repo root when it is down). Run pytest as `.venv/bin/python -m pytest`, never `uv run` (it writes an untracked `backend/uv.lock`).
- Every `git` command runs from the repository root (`/root/repositories/darkmem`); every pytest command runs from `backend/`.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative. Never push; never `--no-verify`.
- Done means all nine tasks committed with the full backend suite and the `CLAUDE.md` guard leg green on the branch. Spec §9 then requires the increment deployed on this host before increment 3 starts; that deploy is the finishing step's and needs the owner's go-ahead. It regenerates no baseline, so it is an image rebuild whose boot `reconcile` creates the new family, with no drop and recreate. Register row 1 stays `doing` until the deploy is verified.

## Contracts

**Family** (Task 1, `app/services/embedder_registry.py`): `_TABLE_TEMPLATES["worklog_embeddings"]` and `_AUX_INDEXES["worklog_embeddings"]` as in Global Constraints; `_EXACT_SCAN_PARENTS: frozenset[str] = frozenset({"worklog_embeddings"})`, the families `_ensure_children` creates no HNSW index for.

**Writer** (Task 2, `app/services/worklog_embeddings.py`):

- `PARENT_TABLE = "worklog_embeddings"`, `EMBED_CHARS = 8_000`.
- `MISSING_SQL`: a string with one `{table}` placeholder and binds `fp`, `limit`; selects one text column, the ids of entries with no vector under `fp`, ordered by id.
- `WriteResult(fingerprint: str, written: int)` (frozen dataclass).
- `async embed_entries(session, llm, *, entry_ids: Sequence[str], chunk_size=32, concurrency=2) -> WriteResult | None` — `None` when no id names a surviving entry. Registers the fingerprint (which creates every family's child table) before writing. It commits nothing itself, but `embedder_registry.register` commits the session the first time this process sees a fingerprint, exactly as `block_embeddings.embed_blocks` does; the refresh arm registers before it calls the writer, so on that path the writer never commits.

**Refresh** (Task 3, `app/services/block_embedding_refresh.py`): `DEFAULT_WORKLOG_BATCH = 500`; `BLOCK_EMBEDDING_CONFIG_SCHEMA` keys `batch`, `page_batch`, `worklog_batch`, in that order; `refresh_block_embeddings(session, llm, *, batch=500, page_batch=500, worklog_batch=500) -> RefreshOutcome`, short-circuiting to `fingerprint=None` only when all three budgets are ≤ 0.

**Service** (Task 4, `app/services/worklog.py`): `SEARCH_ARMS = ("keyword", "semantic")`, `SEARCH_DEFAULT_LIMIT = 20`, `MAX_SEARCH_LIMIT = 100`, `MAX_QUERY_CHARS = 2_000`; `async search(session, llm, *, project, query, workstream=None, kind=None, limit=20) -> dict` answering `{"items": [{"entry", "workstream", "rrf_score", "arms"}], "semantic_ran": bool}`; raises `ValueError` for a query with no non-space character or over `MAX_QUERY_CHARS`, an unknown kind, or a limit outside 1–100. Does not commit.

**Test helpers** (Task 4, `backend/tests/test_worklog_search.py`): `SEARCH_FINGERPRINT = "worklog-search-test|4"`; `TopicEmbedder()` (4-dim; `embed(text)` and `embed_batch_chunked(texts, chunk_size, concurrency)` map "deploy"/"release" to axis 0, "database"/"postgres" to axis 1, "login"/"password" to axis 2, anything else to axis 3; counts `embed` calls in `.calls`).

**Schemas** (Task 6, `app/schemas/worklog.py`): `WorklogSearchRequest(project, query, workstream=None, kind=None, limit=20)`, `WorklogSearchHit(entry: WorklogEntryOut, workstream: str, rrf_score: float, arms: list[Literal["keyword", "semantic"]])`, `WorklogSearchResponse(items, semantic_ran)`.

**REST** (Task 6): `POST /api/v1/worklog/search` → 200 `WorklogSearchResponse`, 422 on a refused request; `read` scope; the orchestrator is `getattr(request.app.state, "llm", None)`.

**MCP** (Task 7): `worklog_search(project, query, workstream=None, kind=None, limit=20) -> str` (JSON of the service answer; `limit` clamped to 1–100); in `READ_TOOLS`.

## Assumptions (evidence)

- darkmem `master` at `63e26e74` is green: the full backend suite ran 7574 passed, 23 skipped on 2026-09-25 against `darkmem_test_2` (after `5800b9a6` fixed the job-count guard, register row 30).
- `_ensure_children` creates one HNSW index per template (`backend/app/services/embedder_registry.py:326-343`), and `reconcile` gives every live fingerprint every template's child at boot (`:283-312`), so an existing deployment gains the new family on its next start with no migration.
- Tests enumerate the families: `tests/test_partition_templates.py:16-34` pins the exact set; `tests/test_boot_reconciliation.py:38,53,70` and `tests/test_pipeline_phase1.py:119` iterate `_TABLE_TEMPLATES` and need no edit. No test assumes every child carries an HNSW index (`rg -i hnsw tests`, 2026-09-25).
- `tests/test_block_embedding_refresh.py:382-399` imports `_DOCUMENT_ARM` and `_MISSING_SQL` and formats `_MISSING_SQL` with `owner=_DOCUMENT_ARM.owner_column`, so both names and that attribute stay; `:103-119` pins the all-budgets-zero short circuit, which Task 3 extends with `worklog_batch=0`. No test monkeypatches `embed_blocks` or asserts the isolation warning's text.
- The `session` fixture joins one outer transaction and drops `commit()` (`backend/tests/conftest.py:69-100`), so `embedder_registry.register`'s commit and the refresh's commits stay inside the test's rollback, as the existing refresh tests rely on.
- `import_closure` (run 2026-09-25): no seed in `MEMORY_SIDE` or `VAULT_WRITERS` (`tests/test_worklog_wall.py`) reaches `app.services.block_embedding_refresh`; `pipeline`, `hybrid_search`, `layer_composition` and `chat` reach `app.services.embedder_registry`, `app.services.rank_fusion` and `app.config`, none of which reaches `app.services.pipeline`. So the refresh job may import the writer, and the service may import `rank_fusion`, `embedder_registry` and `app.config`, without breaching the wall. `embedder_registry` must name every family, which is why Task 5's family scan exempts it.
- `rrf_fuse` keys rows on `id` (`backend/app/services/rank_fusion.py:109-122`) and a `RankedList` weight defaults to 0.0 (`:88-95`), so both lists pass `1.0`; `fusion_fetch_depth` is at `:98`. The spec names no arm weight; memory search's `semantic_weight` (0.7) is a memory-retrieval knob, not this lane's.
- The semantic arm has no distance floor, so every embedded entry of the project is a semantic candidate, as in memory hybrid search; `arms` lets a caller tell a keyword match from a nearest neighbour.
- `settings.read_only` skips a semantic arm before any embed in `hybrid_search.py:85` and `code_query.py:41`; tests flip it with `monkeypatch.setattr(settings, "read_only", True)` (`tests/test_read_only_doors.py:58`).
- `get_llm` answers 503 without an orchestrator (`backend/app/api/deps.py:45-58`), so the search route reads `app.state.llm` itself; MCP tools read `_pipeline.llm` (`backend/app/api/mcp/server.py:454`). Tests set `app.state.llm` directly (`tests/test_documents_keyed.py:32-36`) and patch `server._pipeline` (`tests/test_mcp_surface_parity.py:128`).
- `search_vector` is generated as `to_tsvector('english', body)` (spec §1, amended 2026-09-23), so the keyword arm parses the query with the same `'english'` configuration.
- `MAX_QUERY_CHARS = 2_000` and the 20 / 100 limit bounds are this plan's choices: the spec says only "optional limit" and bounds no query. `_Storable` refuses U+0000 in the query as it does in every other work-log request.
- The registries a new work-log door must join are the ones increment 1's Tasks 5, 6, 8 and 9 edited and that `rg worklog_resume` finds (2026-09-25): `tests/test_api_keys.py` (two pinned sets), `app/api/mcp/scopes.py`, `tests/test_mcp.py`, `app/services/content_surfaces.py`, `tests/test_api/test_rest_conformance.py`, `tests/test_door_parity.py` plus `docs/two-door-parity.md`, `app/services/prompt.py`, `CLAUDE.md` and `docs/runbook-exposed-deployment.md`. The SDK generator binds chosen verbs only, and increment 1 needed no SDK or frontend change for its routes.
- `agent_instructions` is 8,859 characters against the 20,000 cap (`tests/test_prompt_agent_instructions.py:39-40`, measured 2026-09-25), and every served tool description needs at least 80 characters (`:47-66`).
- `docs/two-door-parity.md` reads 89 surfaces, 31 two-door, 51 REST-only, 7 MCP-only; one two-door row makes it 90 and 32.
- Between Task 6 and Task 8 the enumeration guards (`test_rest_conformance`, `test_door_parity`, `test_content_surface_scoping`, `test_prompt_agent_instructions`) fail by design: the doors exist before they are classified. Tasks 6 and 7 run targeted tests; Tasks 8 and 9 turn the guard leg green.
- Register row 18 (spec §7 forbids naming any `KnowledgeTripleRepository` method; the shipped scan checks only write and promote methods) is ruled in Task 5: a scan for every method name cannot tell `session.get` (which `worklog.append` calls) from a repository's `get`, so the rule becomes "no work-log module names the repository class, its module or the `knowledge_triples` table, and no service-layer work-log module's import closure reaches a vault writer", and Task 5 amends the spec's sentence to match. `app.api.routes.worklog` reaches `app.repositories.knowledge_triples` through the auth layer every router shares (`import_closure`, 2026-09-25), so the closure rule excludes the route module.
- Dry run on 2026-09-25: every task's code in this plan's first draft, applied verbatim to a scratch worktree of `63e26e74`, gave a full backend suite of 7633 passed, 23 skipped, and the parity-doc diff was one row plus the headline. The tests added after plan review round 1 were dry-run separately (Tasks 2–5, same day).
- The baseline downgrade drops `*_embeddings__*` children by name and every base table `CASCADE` (`backend/migrations/versions/0001_baseline.py:1745-1753, 1810`), so after a downgrade the `worklog_embeddings__*` tables would survive without their foreign keys. Register row 40 defers adding the pattern to increment 3, which regenerates the baseline anyway.

## Task index

1. Work-log vector family
2. Entry embedding writer
3. Refresh job work-log arm
4. Search service verb
5. Wall scans
6. REST search route
7. MCP search tool and scope
8. Guard registries
9. Instructions, CLAUDE.md and runbook

---

### Task 1: Work-log vector family

**Files:**
- Modify: `backend/app/services/embedder_registry.py` (`_TABLE_TEMPLATES`, `_AUX_INDEXES`, a new `_EXACT_SCAN_PARENTS`, `_ensure_children`)
- Modify: `backend/tests/test_partition_templates.py`
- Create: `backend/tests/test_worklog_embeddings.py`

**Interfaces:**
- Consumes: nothing.
- Produces: Contracts → Family.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_worklog_embeddings.py`:

```python
"""The work-log vector family: its child table, and the writer that fills it."""
from __future__ import annotations

from sqlalchemy import text

from app.services.embedder_registry import EmbedderInfo, EmbedderRegistry, child_table

FAMILY_FP = "worklog-family-test|4"


async def _register_family_fingerprint(session) -> None:
    await EmbedderRegistry().register(
        session,
        EmbedderInfo(fingerprint=FAMILY_FP, model_id="worklog-family-test", dims=4, source="llm"),
    )


async def _indexes(session, table: str) -> list[str]:
    return list((await session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :t"),
        {"t": table},
    )).scalars().all())


async def test_registering_a_fingerprint_creates_the_family_without_an_ann_index(session):
    await _register_family_fingerprint(session)
    table = child_table("worklog_embeddings", FAMILY_FP)

    columns = set((await session.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema = 'public' AND table_name = :t"),
        {"t": table},
    )).scalars().all())
    assert columns == {"entry_id", "fingerprint", "project", "embedding", "created_at"}

    indexes = await _indexes(session, table)
    assert not [d for d in indexes if "hnsw" in d], indexes
    assert any("(project)" in d for d in indexes), indexes


async def test_every_other_family_keeps_its_ann_index(session):
    await _register_family_fingerprint(session)
    indexes = await _indexes(session, child_table("page_embeddings", FAMILY_FP))
    assert any("hnsw" in d for d in indexes), indexes
```

In `backend/tests/test_partition_templates.py`, replace the module docstring's first line

```python
"""The nine per-fingerprint parents exist as registry entries, not as DDL.
```

with

```python
"""The ten per-fingerprint parents exist as registry entries, not as DDL.
```

add `"worklog_embeddings",` as the last member of `EXPECTED_PARENTS` (after `"triple_embeddings",`), rename `test_all_nine_parents_have_templates` to `test_every_parent_has_a_template`, and append:

```python
def test_worklog_embeddings_cascades_on_the_entry_and_carries_its_project():
    # Purge and retention delete entries; the vectors must go with them, and
    # search filters one project's vectors through the project column.
    tmpl = _TABLE_TEMPLATES["worklog_embeddings"]
    assert "worklog_entries(id) ON DELETE CASCADE" in tmpl
    assert "project TEXT NOT NULL" in tmpl
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_worklog_embeddings.py tests/test_partition_templates.py -q`
Expected: FAIL — the two family tests raise `ValueError: Unknown embedding parent table: 'worklog_embeddings'` from `child_table`, the parent-set test sees nine parents, and the template test raises `KeyError: 'worklog_embeddings'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/embedder_registry.py`, insert after the `"triple_embeddings": (...)` entry, before the closing `}` of `_TABLE_TEMPLATES`:

```python
    # Work-log entries (spec 2026-09-23 §1). `project` is copied onto the row
    # so one project's vectors are found through a btree index and scanned
    # exactly; `_EXACT_SCAN_PARENTS` records why there is no HNSW index.
    "worklog_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " entry_id UUID NOT NULL REFERENCES worklog_entries(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " project TEXT NOT NULL,"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (entry_id, fingerprint)"
        ")"
    ),
```

Insert after the `"triple_embeddings": [...]` entry, before the closing `}` of `_AUX_INDEXES`:

```python
    "worklog_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_project ON {name} (project)",
    ],
```

Insert directly after the `_AUX_INDEXES` dict:

```python
# Families read only by an exact scan over one project's rows. An HNSW probe
# applies the project filter after the index scan, so other projects' rows
# would crowd the candidate stream; per-project work logs are small enough to
# scan, and an index here would only cost every write.
_EXACT_SCAN_PARENTS: frozenset[str] = frozenset({"worklog_embeddings"})
```

In `_ensure_children`, replace

```python
        hnsw_idx = _hnsw_index_name(child)
        await session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {hnsw_idx} "
                f"ON {child} USING hnsw (embedding vector_cosine_ops) "
                f"WITH (m = 16, ef_construction = 128)"
            )
        )
```

with

```python
        if parent not in _EXACT_SCAN_PARENTS:
            hnsw_idx = _hnsw_index_name(child)
            await session.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {hnsw_idx} "
                    f"ON {child} USING hnsw (embedding vector_cosine_ops) "
                    f"WITH (m = 16, ef_construction = 128)"
                )
            )
```

leaving the HNSW comment above it in place.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_worklog_embeddings.py tests/test_partition_templates.py tests/test_boot_reconciliation.py tests/test_inert_objects.py tests/test_checkpoint_isolation.py tests/test_worklog_wall.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/embedder_registry.py backend/tests/test_partition_templates.py backend/tests/test_worklog_embeddings.py
git commit -m "feat(worklog): add the worklog_embeddings family"
```

### Task 2: Entry embedding writer

**Files:**
- Create: `backend/app/services/worklog_embeddings.py`
- Modify: `backend/tests/test_worklog_embeddings.py` (append)

**Interfaces:**
- Consumes: Contracts → Family (Task 1).
- Produces: Contracts → Writer.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_worklog_embeddings.py`:

```python
import pytest

from app.services import worklog
from app.services.embedder_registry import embedder_registry
from app.services.worklog_embeddings import EMBED_CHARS, MISSING_SQL, PARENT_TABLE, embed_entries

WRITER_FP = "worklog-writer-test|3"


class RecordingEmbedder:
    """Answers a direction chosen from the text, or one fixed vector, so a
    test can tell which vector landed on which entry."""

    def __init__(self, fixed=None):
        self.fingerprint = WRITER_FP
        self.fixed = fixed
        self.texts: list[str] = []

    def _vector(self, value):
        if self.fixed is not None:
            return list(self.fixed)
        return [1.0, 0.0, 0.0] if "first" in value else [0.0, 1.0, 0.0]

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.texts.extend(texts)
        return [self._vector(t) for t in texts], self.fingerprint

    async def embed(self, value):
        return self._vector(value), self.fingerprint


@pytest.fixture(autouse=True)
def _forget_writer_fingerprint():
    embedder_registry.forget(WRITER_FP)
    yield
    embedder_registry.forget(WRITER_FP)


async def _append(session, *bodies, project="proj", key="plan-a"):
    result = await worklog.append(
        session, project=project, key=key, run_key="claude:run-1",
        entries=[{"kind": "note", "body": body} for body in bodies],
    )
    return result.workstream, [str(entry_id) for entry_id in result.entry_ids]


async def _vectors(session) -> dict[str, tuple[str, str]]:
    """entry id -> (project, the stored vector as pgvector prints it)."""
    table = child_table(PARENT_TABLE, WRITER_FP)
    rows = (await session.execute(
        text(f"SELECT CAST(entry_id AS text), project, CAST(embedding AS text) FROM {table}")
    )).all()
    return {row[0]: (row[1], row[2]) for row in rows}


async def test_embed_entries_writes_each_entrys_vector_with_its_project(session):
    _workstream, (first, second) = await _append(
        session, "first note", "second note", project="proj-x",
    )
    result = await embed_entries(session, RecordingEmbedder(), entry_ids=[first, second])
    assert result.written == 2
    assert result.fingerprint == WRITER_FP
    assert await _vectors(session) == {
        first: ("proj-x", "[1,0,0]"),
        second: ("proj-x", "[0,1,0]"),
    }


async def test_only_the_head_of_a_long_body_is_embedded(session):
    _workstream, ids = await _append(session, "a" * EMBED_CHARS + "b" * 1_000)
    llm = RecordingEmbedder()
    await embed_entries(session, llm, entry_ids=ids)
    assert llm.texts == ["a" * EMBED_CHARS]


async def test_nothing_to_embed_measures_no_fingerprint(session):
    llm = RecordingEmbedder()
    assert await embed_entries(session, llm, entry_ids=[]) is None
    assert await embed_entries(
        session, llm, entry_ids=["00000000-0000-0000-0000-000000000000"]
    ) is None
    assert llm.texts == []


async def test_re_embedding_replaces_the_vector(session):
    _workstream, ids = await _append(session, "note")
    await embed_entries(session, RecordingEmbedder(fixed=[1.0, 0.0, 0.0]), entry_ids=ids)
    await embed_entries(session, RecordingEmbedder(fixed=[0.0, 0.0, 1.0]), entry_ids=ids)
    assert await _vectors(session) == {ids[0]: ("proj", "[0,0,1]")}


async def test_the_missing_query_lists_only_unembedded_entries(session):
    _workstream, ids = await _append(session, "one", "two")
    await embed_entries(session, RecordingEmbedder(), entry_ids=ids[:1])
    missing = (await session.execute(
        text(MISSING_SQL.format(table=child_table(PARENT_TABLE, WRITER_FP))),
        {"fp": WRITER_FP, "limit": 100},
    )).scalars().all()
    assert ids[1] in missing
    assert ids[0] not in missing


async def test_purging_a_workstream_takes_its_vectors(session):
    workstream, ids = await _append(session, "note")
    await embed_entries(session, RecordingEmbedder(), entry_ids=ids)
    await worklog.purge_workstream(session, workstream.id)
    assert await _vectors(session) == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_worklog_embeddings.py -q`
Expected: ERROR collecting — `ModuleNotFoundError: No module named 'app.services.worklog_embeddings'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/worklog_embeddings.py`:

```python
"""Vectors for work-log entries: the ``worklog_embeddings__<slug>`` family.

Appends never embed, so a write never waits on the LAN embedder; the hourly
``block_embedding_refresh`` job fills this family through its work-log arm
(docs/superpowers/specs/2026-09-23-work-log-lane-design.md §1). ``project`` is
copied onto every vector row so ``worklog.search`` scans one project's rows
exactly.

The caller owns the transaction, with one exception shared with
``block_embeddings.embed_blocks``: registering a fingerprint this process has
not seen commits the session.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import (
    EmbedderInfo,
    child_table,
    embedder_registry,
    parse_fingerprint,
)

__all__ = ["EMBED_CHARS", "MISSING_SQL", "PARENT_TABLE", "WriteResult", "embed_entries"]

PARENT_TABLE = "worklog_embeddings"
# nomic-embed-text reads 2,048 tokens, so a longer body would be truncated by
# the embedder without a word. The keyword arm indexes the whole body.
EMBED_CHARS = 8_000
DEFAULT_EMBED_CHUNK = 32
DEFAULT_EMBED_CONCURRENCY = 2

MISSING_SQL = """
    SELECT CAST(e.id AS text) AS entry_id
    FROM worklog_entries e
    LEFT JOIN {table} v
           ON v.entry_id = e.id
          AND v.fingerprint = CAST(:fp AS text)
    WHERE v.entry_id IS NULL
    ORDER BY e.id
    LIMIT CAST(:limit AS int)
"""

_ENTRY_TEXTS = text(
    """
    SELECT CAST(e.id AS text) AS entry_id, w.project AS project,
           left(e.body, CAST(:chars AS int)) AS text
    FROM worklog_entries e
    JOIN workstreams w ON w.id = e.workstream_id
    WHERE e.id = ANY(CAST(:ids AS uuid[]))
    ORDER BY e.id
    """
)


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


async def _ensure_partition(session: AsyncSession, fingerprint: str) -> None:
    if embedder_registry.is_known(fingerprint):
        return
    model_id, dims = parse_fingerprint(fingerprint)
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"),
    )


async def embed_entries(
    session: AsyncSession,
    llm,
    *,
    entry_ids: Sequence[str],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed each entry's first EMBED_CHARS characters under the active fingerprint.

    ``None`` means no id named a surviving entry (a purge may have taken them
    since the caller listed them), so no fingerprint was measured.
    Re-embedding an entry replaces its vector.
    """
    ids = [str(entry_id) for entry_id in entry_ids]
    if not ids:
        return None
    rows = (await session.execute(
        _ENTRY_TEXTS, {"ids": ids, "chars": EMBED_CHARS}
    )).mappings().all()
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["text"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"worklog_embeddings: the embedder returned {len(vectors)} vectors "
            f"for {len(rows)} entries; refusing to write vectors under ids "
            "they may not belong to"
        )

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (entry_id, fingerprint, project, embedding)
                VALUES (CAST(:eid AS uuid), CAST(:fp AS text), CAST(:project AS text),
                        CAST(:embedding AS vector))
                ON CONFLICT (entry_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "eid": row["entry_id"],
                "fp": fingerprint,
                "project": row["project"],
                "embedding": str(list(vector)),
            },
        )
    return WriteResult(fingerprint=fingerprint, written=len(rows))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_worklog_embeddings.py tests/test_worklog_wall.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog_embeddings.py backend/tests/test_worklog_embeddings.py
git commit -m "feat(worklog): embed entries into their family"
```

### Task 3: Refresh job work-log arm

**Files:**
- Modify: `backend/app/services/block_embedding_refresh.py`
- Modify: `backend/app/services/job_runners.py:1005-1009` (the `refresh_block_embeddings` call)
- Test: `backend/tests/test_block_embedding_refresh.py`

**Interfaces:**
- Consumes: Contracts → Writer (Task 2).
- Produces: Contracts → Refresh.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_block_embedding_refresh.py`, in `test_refresh_batch_zero_disables_the_sweep`, replace

```python
    outcome = await refresh_block_embeddings(session, llm, batch=0, page_batch=0)
    assert outcome.embedded == 0
    assert outcome.fingerprint is None, (
        "both budgets at 0 must short-circuit before spending the probe embed call"
    )
```

with

```python
    outcome = await refresh_block_embeddings(
        session, llm, batch=0, page_batch=0, worklog_batch=0,
    )
    assert outcome.embedded == 0
    assert outcome.fingerprint is None, (
        "every budget at 0 must short-circuit before spending the probe embed call"
    )
```

Append to the same file:

```python
async def _worklog_entry(session, body="Task 1: complete\n", *, project="p"):
    from app.services import worklog

    result = await worklog.append(
        session, project=project, key="plan-a", run_key="claude:run-1",
        entries=[{"kind": "ledger", "body": body}],
    )
    return str(result.entry_ids[0])


def test_the_job_declares_a_work_log_budget():
    from app.services.block_embedding_refresh import BLOCK_EMBEDDING_CONFIG_SCHEMA

    assert [fd.key for fd in BLOCK_EMBEDDING_CONFIG_SCHEMA] == [
        "batch", "page_batch", "worklog_batch",
    ]


@pytest.mark.asyncio
async def test_the_worklog_arm_embeds_an_entry_on_its_own_budget(session):
    from app.services.embedder_registry import child_table
    from app.services.worklog_embeddings import PARENT_TABLE as WORKLOG_PARENT_TABLE

    llm = StubEmbedder()
    entry_id = await _worklog_entry(session, project="p")
    await session.commit()

    outcome = await refresh_block_embeddings(
        session, llm, batch=0, page_batch=0, worklog_batch=100,
    )
    assert outcome.embedded == 1
    assert outcome.fingerprint == FINGERPRINT
    assert outcome.converged is True
    rows = (await session.execute(text(
        f"SELECT CAST(entry_id AS text), project "
        f"FROM {child_table(WORKLOG_PARENT_TABLE, FINGERPRINT)}"
    ))).all()
    assert [tuple(row) for row in rows] == [(entry_id, "p")]

    again = await refresh_block_embeddings(
        session, llm, batch=0, page_batch=0, worklog_batch=100,
    )
    assert again.embedded == 0
    assert again.converged is True


@pytest.mark.asyncio
async def test_a_work_log_entry_does_not_consume_the_document_budget(session):
    from app.services.block_embeddings import PARENT_TABLE
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.worklog_embeddings import PARENT_TABLE as WORKLOG_PARENT_TABLE

    llm = StubEmbedder()
    filed = await put_document(
        session, llm, project="p", uri="docs/worklog-budget.md", content=DOC,
    )
    assert filed.blocks_filed > 0
    await session.execute(text(f"DELETE FROM {child_table(PARENT_TABLE, FINGERPRINT)}"))
    await _worklog_entry(session)
    await session.commit()

    outcome = await refresh_block_embeddings(
        session, llm, batch=1, page_batch=0, worklog_batch=0,
    )

    assert outcome.embedded == 1
    documents = (await session.execute(text(
        f"SELECT COUNT(*) FROM {child_table(PARENT_TABLE, FINGERPRINT)}"
    ))).scalar_one()
    entries = (await session.execute(text(
        f"SELECT COUNT(*) FROM {child_table(WORKLOG_PARENT_TABLE, FINGERPRINT)}"
    ))).scalar_one()
    assert documents == 1
    assert entries == 0, "worklog_batch=0 must leave the work-log family alone"


@pytest.mark.asyncio
async def test_the_worklog_arm_honours_its_budget_across_runs(session):
    llm = StubEmbedder()
    for n in range(3):
        await _worklog_entry(session, f"Task {n}: complete\n")
    await session.commit()

    first = await refresh_block_embeddings(
        session, llm, batch=0, page_batch=0, worklog_batch=2,
    )
    assert first.embedded == 2
    assert first.converged is False

    second = await refresh_block_embeddings(
        session, llm, batch=0, page_batch=0, worklog_batch=2,
    )
    assert second.embedded == 1
    assert second.converged is True


@pytest.mark.asyncio
async def test_the_runner_forwards_every_configured_budget(monkeypatch):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    import app.services.block_embedding_refresh as refresh_module
    from app.services.job_runners import make_block_embedding_runner

    seen: dict = {}

    async def fake_refresh(session, llm, **budgets):
        seen.update(budgets)
        return refresh_module.RefreshOutcome(
            embedded=0, fingerprint=None, failed=0, converged=True,
        )

    class _Registry:
        async def load_config(self, key):
            return SimpleNamespace(config={"worklog_batch": 7, "page_batch": 0})

    @asynccontextmanager
    async def _no_session():
        yield None

    monkeypatch.setattr(refresh_module, "refresh_block_embeddings", fake_refresh)
    fake_app = SimpleNamespace(state=SimpleNamespace(llm=object(), job_registry=_Registry()))
    await make_block_embedding_runner(fake_app, _no_session)()
    assert seen == {"batch": 500, "page_batch": 0, "worklog_batch": 7}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_block_embedding_refresh.py -q`
Expected: FAIL — `TypeError: refresh_block_embeddings() got an unexpected keyword argument 'worklog_batch'`, the schema test sees two keys, and the runner test raises `KeyError: 'worklog_batch'` or sees no `worklog_batch` forwarded.

- [ ] **Step 3: Write the implementation**

All edits are in `backend/app/services/block_embedding_refresh.py` unless named otherwise.

(a) In the module docstring, directly after the paragraph that ends `once per run rather than once per owner.`, insert this paragraph (with a blank line on each side):

```text
Work-log entries are a third arm on a third budget, ``worklog_batch``. Appends
never embed inline, so this sweep is the only writer of
``worklog_embeddings__<slug>``, and an agent's ledger cannot delay a document
any more than a note can.
```

(b) Replace the imports

```python
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import (
    PAGE_PARENT_TABLE, PARENT_TABLE, ensure_partition, embed_blocks,
    resolve_active_fingerprint,
)
from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor
```

with

```python
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import (
    PAGE_PARENT_TABLE, PARENT_TABLE, ensure_partition, embed_blocks,
    resolve_active_fingerprint,
)
from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor
from app.services.worklog_embeddings import (
    MISSING_SQL as WORKLOG_MISSING_SQL,
    PARENT_TABLE as WORKLOG_PARENT_TABLE,
    embed_entries,
)
```

(c) Replace `DEFAULT_PAGE_BATCH = 500` with

```python
DEFAULT_PAGE_BATCH = 500
DEFAULT_WORKLOG_BATCH = 500
```

(d) Replace the end of `BLOCK_EMBEDDING_CONFIG_SCHEMA`

```python
            "Page blocks embedded per run, budgeted independently of the "
            "document sweep. 0 disables the page sweep."
        ),
    ),
]
```

with

```python
            "Page blocks embedded per run, budgeted independently of the "
            "document sweep. 0 disables the page sweep."
        ),
    ),
    FieldDescriptor(
        key="worklog_batch",
        label="Work-log entries per run",
        default=DEFAULT_WORKLOG_BATCH,
        min=0,
        max=5_000,
        help=(
            "Work-log entries embedded per run, budgeted independently of "
            "both block sweeps. 0 disables the work-log sweep."
        ),
    ),
]
```

(e) Replace everything from `@dataclass(frozen=True)` above `class _Arm:` through the closing `"""` of `_MISSING_SQL` — that is, the `_Arm` class, its comment, `_DOCUMENT_ARM`, `_PAGE_ARM` and `_MISSING_SQL` — with

```python
_MISSING_SQL = """
    SELECT CAST(b.id AS text) AS block_id
    FROM blocks b
    LEFT JOIN {table} e
           ON e.block_id = b.id
          AND e.fingerprint = CAST(:fp AS text)
    WHERE e.block_id IS NULL AND b.{owner} IS NOT NULL
    ORDER BY b.id
    LIMIT CAST(:limit AS int)
"""


@dataclass(frozen=True)
class _Arm:
    """One owner's sweep: the partition family it fills, the anti-join that
    lists its rows with no vector (one text column; formatted with ``table``
    and, for blocks, ``owner``), and the writer that embeds a list of them."""
    parent: str
    missing_sql: str
    embed: Callable[[AsyncSession, Any, list[str]], Awaitable[Any]]
    owner_column: str | None = None


def _block_writer(parent: str) -> Callable[[AsyncSession, Any, list[str]], Awaitable[Any]]:
    async def write(session: AsyncSession, llm, ids: list[str]):
        return await embed_blocks(session, llm, block_ids=ids, parent=parent)
    return write


async def _write_entries(session: AsyncSession, llm, ids: list[str]):
    return await embed_entries(session, llm, entry_ids=ids)


# Separate arms rather than one unscoped sweep: page blocks and work-log
# entries are repaired on their own budgets, because sharing the document one
# would let a notes corpus or an agent's ledger consume the whole per-tick
# allowance and delay document embedding.
_DOCUMENT_ARM = _Arm(
    parent=PARENT_TABLE, missing_sql=_MISSING_SQL,
    embed=_block_writer(PARENT_TABLE), owner_column="document_id",
)
_PAGE_ARM = _Arm(
    parent=PAGE_PARENT_TABLE, missing_sql=_MISSING_SQL,
    embed=_block_writer(PAGE_PARENT_TABLE), owner_column="page_id",
)
_WORKLOG_ARM = _Arm(
    parent=WORKLOG_PARENT_TABLE, missing_sql=WORKLOG_MISSING_SQL, embed=_write_entries,
)
```

(f) In `_embed_isolating`, replace the signature line `    *, parent: str,` with `    *, arm: _Arm,`; replace

```python
            async with session.begin_nested():
                result = await embed_blocks(
                    session, llm, block_ids=[block_id], parent=parent,
                )
```

with

```python
            async with session.begin_nested():
                result = await arm.embed(session, llm, [block_id])
```

and replace

```python
        logger.warning(
            "block_embedding_refresh: %d of %d block(s) could not be embedded "
            "individually and stay in the backlog; the rest of the batch was "
            "written. Block ids: %s",
            len(failed), len(block_ids), ", ".join(failed),
        )
```

with

```python
        logger.warning(
            "block_embedding_refresh: %d of %d %s row(s) could not be embedded "
            "individually and stay in the backlog; the rest of the batch was "
            "written. Ids: %s",
            len(failed), len(block_ids), arm.parent, ", ".join(failed),
        )
```

(g) In `refresh_block_embeddings`, replace

```python
    batch: int = DEFAULT_BATCH,
    page_batch: int = DEFAULT_PAGE_BATCH,
) -> RefreshOutcome:
    """Sweep both owners' missing vectors, each on its own budget.

    Documents first, then pages, in one run over one resolved fingerprint —
    two arms rather than two jobs, because the fingerprint probe is an embed
    call and a second registered job would spend a second one per tick for
    nothing. The returned outcome sums both arms; `converged` holds only if
    both did.
```

with

```python
    batch: int = DEFAULT_BATCH,
    page_batch: int = DEFAULT_PAGE_BATCH,
    worklog_batch: int = DEFAULT_WORKLOG_BATCH,
) -> RefreshOutcome:
    """Sweep every owner's missing vectors, each on its own budget.

    Documents first, then pages, then work-log entries, in one run over one
    resolved fingerprint — arms rather than jobs, because the fingerprint
    probe is an embed call and a second registered job would spend a second
    one per tick for nothing. The returned outcome sums the arms; `converged`
    holds only if every arm did.
```

replace `    if batch <= 0 and page_batch <= 0:` with `    if batch <= 0 and page_batch <= 0 and worklog_batch <= 0:`, and replace

```python
    for arm, arm_batch in ((_DOCUMENT_ARM, batch), (_PAGE_ARM, page_batch)):
```

with

```python
    for arm, arm_batch in (
        (_DOCUMENT_ARM, batch), (_PAGE_ARM, page_batch), (_WORKLOG_ARM, worklog_batch),
    ):
```

(h) In `_refresh_arm`, replace

```python
    rows = (await session.execute(
        text(_MISSING_SQL.format(table=table, owner=arm.owner_column)),
        {"fp": fingerprint, "limit": batch},
    )).mappings().all()
    block_ids = [row["block_id"] for row in rows]
```

with

```python
    block_ids = list((await session.execute(
        text(arm.missing_sql.format(table=table, owner=arm.owner_column)),
        {"fp": fingerprint, "limit": batch},
    )).scalars().all())
```

and replace

```python
        async with session.begin_nested():
            result = await embed_blocks(
                session, llm, block_ids=block_ids, parent=arm.parent,
            )
    except Exception as batch_error:  # noqa: BLE001 - re-raised unless isolable
        embedded, written_fingerprint, failed = await _embed_isolating(
            session, llm, block_ids, batch_error, parent=arm.parent,
        )
```

with

```python
        async with session.begin_nested():
            result = await arm.embed(session, llm, block_ids)
    except Exception as batch_error:  # noqa: BLE001 - re-raised unless isolable
        embedded, written_fingerprint, failed = await _embed_isolating(
            session, llm, block_ids, batch_error, arm=arm,
        )
```

(i) In `backend/app/services/job_runners.py`, replace

```python
            outcome = await refresh_block_embeddings(
                session, llm,
                batch=int(knobs["batch"]),
                page_batch=int(knobs["page_batch"]),
            )
```

with

```python
            outcome = await refresh_block_embeddings(
                session, llm,
                batch=int(knobs["batch"]),
                page_batch=int(knobs["page_batch"]),
                worklog_batch=int(knobs["worklog_batch"]),
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_block_embedding_refresh.py tests/test_page_door.py tests/test_page_document_isolation.py tests/test_block_verbs.py tests/test_worklog_embeddings.py tests/test_worklog_wall.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/block_embedding_refresh.py backend/app/services/job_runners.py backend/tests/test_block_embedding_refresh.py
git commit -m "feat(worklog): sweep entries in the embedding refresh"
```

### Task 4: Search service verb

**Files:**
- Modify: `backend/app/services/worklog.py`
- Create: `backend/tests/test_worklog_search.py`

**Interfaces:**
- Consumes: Contracts → Writer (Task 2; the tests embed through `embed_entries`).
- Produces: Contracts → Service, Test helpers.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-low
**Executor:** codex gpt-6-sol / high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_worklog_search.py`:

```python
"""worklog.search: a keyword arm and a semantic arm, fused by RRF, scoped to one project in SQL."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services import worklog
from app.services.embedder_registry import embedder_registry
from app.services.worklog_embeddings import embed_entries

SEARCH_FINGERPRINT = "worklog-search-test|4"


class TopicEmbedder:
    """One axis per topic, so a query can match an entry by meaning while
    sharing no word with it: 'release' lands where 'deploy' does."""

    TOPICS = (("deploy", "release"), ("database", "postgres"), ("login", "password"))

    def __init__(self):
        self.fingerprint = SEARCH_FINGERPRINT
        self.calls = 0

    def _vector(self, value: str) -> list[float]:
        lowered = value.lower()
        vector = [0.0, 0.0, 0.0, 0.0]
        for axis, words in enumerate(self.TOPICS):
            if any(word in lowered for word in words):
                vector[axis] = 1.0
                return vector
        vector[3] = 1.0
        return vector

    async def embed(self, value: str):
        self.calls += 1
        return self._vector(value), self.fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return [self._vector(t) for t in texts], self.fingerprint


class DownEmbedder:
    async def embed(self, value: str):
        raise ConnectionError("embedder unreachable")

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        raise ConnectionError("embedder unreachable")


@pytest.fixture(autouse=True)
def _forget_search_fingerprint():
    embedder_registry.forget(SEARCH_FINGERPRINT)
    yield
    embedder_registry.forget(SEARCH_FINGERPRINT)


async def _note(session, body, *, project="proj", key="plan-a", kind="note"):
    result = await worklog.append(
        session, project=project, key=key, run_key="claude:run-1",
        entries=[{"kind": kind, "body": body}],
    )
    return str(result.entry_ids[0])


async def _embed(session, *entry_ids):
    await embed_entries(session, TopicEmbedder(), entry_ids=list(entry_ids))


def _ids(answer):
    return [item["entry"]["id"] for item in answer["items"]]


async def test_the_keyword_arm_answers_alone_without_an_orchestrator(session):
    hit = await _note(session, "Task 3 fixed the flaky migration test")
    await _note(session, "Unrelated housekeeping")
    answer = await worklog.search(session, None, project="proj", query="migration")
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]
    assert answer["items"][0]["arms"] == ["keyword"]
    assert answer["items"][0]["workstream"] == "plan-a"
    assert answer["items"][0]["entry"]["body"] == "Task 3 fixed the flaky migration test"


async def test_the_semantic_arm_finds_an_entry_that_shares_no_word(session):
    release = await _note(session, "The release pipeline broke overnight")
    rotated = await _note(session, "Rotated the postgres credentials")
    await _embed(session, release, rotated)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy failed")
    assert answer["semantic_ran"] is True
    assert _ids(answer) == [release, rotated]
    assert answer["items"][0]["arms"] == ["semantic"]


async def test_an_entry_both_arms_find_ranks_first(session):
    both = await _note(session, "The deploy script now retries")
    meaning = await _note(session, "Release notes drafted")
    other = await _note(session, "Database vacuum tuned")
    await _embed(session, both, meaning, other)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert _ids(answer) == [both, meaning, other]
    assert answer["items"][0]["arms"] == ["keyword", "semantic"]
    assert answer["items"][1]["arms"] == ["semantic"]
    # Semantic ties on distance fall back to newest first: meaning 1, both 2, other 3.
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx(
        [1 / 61 + 1 / 62, 1 / 61, 1 / 63]
    )


async def test_fusion_sums_each_arms_reciprocal_rank(session):
    dense = await _note(session, "deploy deploy deploy")
    plan = await _note(session, "Release plan for the deploy")
    notes = await _note(session, "Release notes drafted")
    await _embed(session, dense, plan, notes)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    # keyword: dense 1, plan 2; semantic (all one direction, newest first): notes 1, plan 2, dense 3
    assert _ids(answer) == [dense, plan, notes]
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx(
        [1 / 61 + 1 / 63, 1 / 62 + 1 / 62, 1 / 61]
    )


async def test_the_keyword_arm_ranks_by_ts_rank_not_recency(session):
    dense = await _note(session, "deploy deploy deploy checklist")
    sparse = await _note(session, "deploy checklist reviewed twice over")
    answer = await worklog.search(session, None, project="proj", query="deploy")
    assert _ids(answer) == [dense, sparse]
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx([1 / 61, 1 / 62])


async def test_a_hit_carries_the_entry_its_workstream_and_its_score(session):
    await _note(session, "deploy delta")
    (item,) = (await worklog.search(session, None, project="proj", query="deploy"))["items"]
    assert set(item) == {"entry", "workstream", "rrf_score", "arms"}
    assert set(item["entry"]) == {
        "id", "workstream_id", "seq", "run_key", "kind", "body", "properties", "created_at",
    }
    assert item["rrf_score"] == pytest.approx(1 / 61)


async def test_an_unreachable_embedder_leaves_the_keyword_arm_answering(session):
    hit = await _note(session, "deploy script retries")
    answer = await worklog.search(session, DownEmbedder(), project="proj", query="deploy")
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]


async def test_a_read_only_instance_never_calls_the_embedder(session, monkeypatch):
    hit = await _note(session, "deploy script retries")
    monkeypatch.setattr(settings, "read_only", True)
    llm = TopicEmbedder()
    answer = await worklog.search(session, llm, project="proj", query="deploy")
    assert llm.calls == 0
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]


async def test_an_unembedded_project_still_answers_by_keyword(session):
    hit = await _note(session, "deploy gamma")
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert answer["semantic_ran"] is True
    assert _ids(answer) == [hit]
    assert answer["items"][0]["arms"] == ["keyword"]


async def test_another_projects_entries_never_appear(session):
    mine = await _note(session, "deploy one", project="proj")
    theirs = await _note(session, "deploy two", project="other")
    await _embed(session, mine, theirs)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert _ids(answer) == [mine]


async def test_workstream_and_kind_narrow_the_search(session):
    alpha = await _note(session, "deploy alpha", key="plan-a", kind="note")
    beta = await _note(session, "deploy beta\n", key="plan-b", kind="ledger")
    by_key = await worklog.search(session, None, project="proj", query="deploy", workstream="plan-b")
    by_kind = await worklog.search(session, None, project="proj", query="deploy", kind="note")
    assert _ids(by_key) == [beta]
    assert _ids(by_kind) == [alpha]


async def test_filters_bind_the_semantic_arm_too(session):
    alpha = await _note(session, "Release alpha", key="plan-a", kind="note")
    beta = await _note(session, "Release beta\n", key="plan-b", kind="ledger")
    await _embed(session, alpha, beta)
    by_key = await worklog.search(
        session, TopicEmbedder(), project="proj", query="deploy", workstream="plan-b",
    )
    by_kind = await worklog.search(
        session, TopicEmbedder(), project="proj", query="deploy", kind="note",
    )
    assert _ids(by_key) == [beta]
    assert _ids(by_kind) == [alpha]
    assert by_key["items"][0]["arms"] == ["semantic"]


async def test_other_projects_cannot_crowd_the_fetch_depth(session):
    """300 newer, equally close vectors in another project fill the whole
    fusion_fetch_depth: a project filter applied after LIMIT would return nothing."""
    mine = await _note(session, "Release notes for this project")
    crowd: list[str] = []
    for batch in range(3):
        result = await worklog.append(
            session, project="other", key=f"crowd-{batch}", run_key="claude:run-1",
            entries=[{"kind": "note", "body": f"release {batch}-{n}"} for n in range(100)],
        )
        crowd.extend(str(entry_id) for entry_id in result.entry_ids)
    await _embed(session, mine, *crowd)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy", limit=1)
    assert _ids(answer) == [mine]


async def test_limit_caps_the_hits(session):
    for n in range(3):
        await _note(session, f"deploy attempt {n}")
    answer = await worklog.search(session, None, project="proj", query="deploy", limit=2)
    assert len(answer["items"]) == 2


@pytest.mark.parametrize("kwargs", [
    {"query": "   "},
    {"query": "x" * 2_001},
    {"query": "deploy", "kind": "log"},
    {"query": "deploy", "limit": 0},
    {"query": "deploy", "limit": 101},
])
async def test_out_of_bounds_arguments_are_refused(session, kwargs):
    with pytest.raises(ValueError):
        await worklog.search(session, None, project="proj", **kwargs)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_worklog_search.py -q`
Expected: FAIL — `AttributeError: module 'app.services.worklog' has no attribute 'search'`

- [ ] **Step 3: Write the implementation**

In `backend/app/services/worklog.py`:

(a) Replace the imports

```python
import json
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worklog import WorklogEntry, Workstream
from app.services import project_registry
from app.services.events import record_event
```

with

```python
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.worklog import WorklogEntry, Workstream
from app.services import project_registry
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.rank_fusion import RankedList, fusion_fetch_depth, rrf_fuse
from app.services.worklog_embeddings import PARENT_TABLE as EMBEDDING_PARENT

logger = logging.getLogger(__name__)
```

(b) In `__all__`, add `"MAX_QUERY_CHARS"`, `"MAX_SEARCH_LIMIT"`, `"SEARCH_ARMS"`, `"SEARCH_DEFAULT_LIMIT"` and `"search"`, keeping the list alphabetical (the constants after `"MAX_PROPERTIES_BYTES"` / `"RESUME_NOTES_CAP"`, `"search"` after `"resume"`).

(c) Replace `DOOR_SOURCE = "worklog"` with

```python
DOOR_SOURCE = "worklog"
SEARCH_ARMS = ("keyword", "semantic")
SEARCH_DEFAULT_LIMIT = 20
MAX_SEARCH_LIMIT = 100
MAX_QUERY_CHARS = 2_000
```

(d) Append to the end of the module:

```python
_HIT_COLUMNS = (
    "e.id, e.workstream_id, e.seq, e.run_key, e.kind, e.body, e.properties, "
    "e.created_at, w.key AS workstream_key"
)
_KEYWORD_SEARCH = """
    SELECT {columns}
    FROM worklog_entries e
    JOIN workstreams w ON w.id = e.workstream_id
    CROSS JOIN plainto_tsquery('english', CAST(:query AS text)) q
    WHERE w.project = CAST(:project AS text) AND e.search_vector @@ q{filters}
    ORDER BY ts_rank(e.search_vector, q) DESC, e.seq DESC
    LIMIT CAST(:depth AS integer)
"""
# Exact cosine distance over one project's vectors, reached through the
# project btree index: the family has no HNSW index
# (embedder_registry._EXACT_SCAN_PARENTS).
_SEMANTIC_SEARCH = """
    SELECT {columns}
    FROM {table} v
    JOIN worklog_entries e ON e.id = v.entry_id
    JOIN workstreams w ON w.id = e.workstream_id
    WHERE v.project = CAST(:project AS text){filters}
    ORDER BY v.embedding <=> CAST(:vec AS vector), e.seq DESC
    LIMIT CAST(:depth AS integer)
"""
_ENTRY_FIELDS = ("id", "workstream_id", "seq", "run_key", "kind", "body", "properties", "created_at")


async def search(
    session: AsyncSession,
    llm,
    *,
    project: str,
    query: str,
    workstream: str | None = None,
    kind: str | None = None,
    limit: int = SEARCH_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """One project's entries matching `query` by words, by meaning or both, fused by RRF.

    The keyword arm ranks the whole body; the semantic arm ranks the vectors
    of each body's first 8,000 characters. It is skipped, with semantic_ran
    false, when there is no orchestrator, the instance is read-only (a backup
    worker makes no external call) or the query embed fails, and the keyword
    arm answers alone. Each hit names the arms that found it.
    """
    if not query.strip():
        raise ValueError("query must contain a non-space character")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query is longer than {MAX_QUERY_CHARS} characters")
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    if not 1 <= limit <= MAX_SEARCH_LIMIT:
        raise ValueError(f"limit must be 1 to {MAX_SEARCH_LIMIT}, not {limit}")

    scope: dict[str, Any] = {"project": project, "depth": fusion_fetch_depth(limit)}
    filters = ""
    if workstream is not None:
        filters += " AND w.key = CAST(:workstream AS text)"
        scope["workstream"] = workstream
    if kind is not None:
        filters += " AND e.kind = CAST(:kind AS text)"
        scope["kind"] = kind

    keyword = (await session.execute(
        text(_KEYWORD_SEARCH.format(columns=_HIT_COLUMNS, filters=filters)),
        {**scope, "query": query},
    )).mappings().all()

    semantic: list = []
    semantic_ran = False
    if llm is not None and not settings.read_only:
        try:
            vector, fingerprint = await llm.embed(query)
        except Exception as error:  # noqa: BLE001 - the keyword arm still answers
            logger.warning("worklog.search: the query embed failed; keyword arm only: %s", error)
        else:
            semantic_ran = True
            table = child_table(EMBEDDING_PARENT, fingerprint)
            # No child table means nothing is embedded under this fingerprint
            # yet: an empty arm, not a fault.
            exists = (await session.execute(
                text("SELECT to_regclass(:name)"), {"name": table},
            )).scalar_one_or_none()
            if exists is not None:
                semantic = (await session.execute(
                    text(_SEMANTIC_SEARCH.format(columns=_HIT_COLUMNS, table=table, filters=filters)),
                    {**scope, "vec": str(list(vector))},
                )).mappings().all()

    rows = {str(row["id"]): row for row in (*keyword, *semantic)}
    found_by = {
        "keyword": {str(row["id"]) for row in keyword},
        "semantic": {str(row["id"]) for row in semantic},
    }
    fused = rrf_fuse(
        [
            RankedList("keyword", [{"id": str(row["id"])} for row in keyword], 1.0),
            RankedList("semantic", [{"id": str(row["id"])} for row in semantic], 1.0),
        ],
        limit,
    )
    items = []
    for hit in fused:
        row = rows[hit["id"]]
        items.append({
            "entry": serialize_entry(SimpleNamespace(**{name: row[name] for name in _ENTRY_FIELDS})),
            "workstream": row["workstream_key"],
            "rrf_score": hit["rrf_score"],
            "arms": [arm for arm in SEARCH_ARMS if hit["id"] in found_by[arm]],
        })
    return {"items": items, "semantic_ran": semantic_ran}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_worklog_search.py tests/test_worklog_service.py tests/test_worklog_wall.py tests/test_rrf_fusion.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog.py backend/tests/test_worklog_search.py
git commit -m "feat(worklog): add the search verb"
```

### Task 5: Wall scans

**Files:**
- Modify: `backend/tests/test_worklog_wall.py`
- Modify: `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` (§7, third bullet)

**Interfaces:**
- Consumes: Contracts → Writer (Task 2; the module name `app.services.worklog_embeddings`).
- Produces: nothing later tasks consume.

**Items:** 1, 18

**Implementer:** dr-superpowers:impl-sonnet-medium
**Executor:** codex gpt-6-sol / low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Write the new scans**

In `backend/tests/test_worklog_wall.py`, add `import ast` above `import re`, add `"app.services.worklog_embeddings",` to `WORKLOG_MODULES` after `"app.services.worklog",`, and replace

```python
def test_the_work_log_reaches_neither_the_pipeline_nor_the_vault():
    reached = import_closure(BACKEND, "app.services.worklog")
    forbidden = {"app.services.pipeline", *VAULT_WRITERS} & reached
    assert not forbidden, f"app.services.worklog reaches {sorted(forbidden)}"
```

with

```python
# The route module is transport: it reaches the fact repository only through
# the auth layer every router shares, and holds no logic of its own.
WORKLOG_SERVICE_LAYER = WORKLOG_MODULES - {"app.api.routes.worklog"}


@pytest.mark.parametrize("module", sorted(WORKLOG_SERVICE_LAYER))
def test_the_work_log_service_layer_reaches_neither_the_pipeline_nor_the_vault(module):
    forbidden = {"app.services.pipeline", *VAULT_WRITERS} & import_closure(BACKEND, module)
    assert not forbidden, f"{module} reaches {sorted(forbidden)}"
```

Then append:

```python
# The registry names every family because it creates every family's child
# tables; no other module on the memory side has a reason to.
_FAMILY_REGISTRY = "app.services.embedder_registry"


def _names_the_worklog_family(source: str) -> bool:
    return "worklog_embeddings" in source


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_names_the_work_log_vector_family(seed):
    for module in sorted(import_closure(BACKEND, seed) - WORKLOG_MODULES - {_FAMILY_REGISTRY}):
        path = module_path(module, BACKEND)
        if path is not None:
            assert not _names_the_worklog_family(path.read_text(encoding="utf-8")), (
                f"{module}, reached from {seed}, names the worklog_embeddings family"
            )


def test_the_family_scan_sees_a_planted_name():
    assert _names_the_worklog_family("child_table('worklog_embeddings', fingerprint)")
    assert not _names_the_worklog_family("child_table('page_embeddings', fingerprint)")


# worklog_search never returns a memory (spec §7). SQL lives in string
# literals; docstrings are excluded because they carry prose such as "kept
# apart from memories", which is not a query.
_MEMORY_TABLE_SQL = re.compile(
    r"\b(?:from|join|into|update|table)\s+(?:\w+\.)?memor(?:ies|y_\w+)\b", re.IGNORECASE
)


def _code_strings(source: str) -> list[str]:
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def _queries_a_memory_table(source: str) -> bool:
    return any(_MEMORY_TABLE_SQL.search(value) for value in _code_strings(source))


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_reads_a_memory_table(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    assert not _queries_a_memory_table(source), f"{module} queries a memory table"
    assert "memory_embeddings" not in source, f"{module} names the memory vector family"


def test_the_memory_scan_sees_a_planted_query():
    assert _queries_a_memory_table("q = 'select * from memories'")
    assert _queries_a_memory_table("q = 'SELECT * FROM public.memories'")
    assert _queries_a_memory_table("q = f'JOIN memory_tags mt ON mt.memory_id = {x}'")
    assert not _queries_a_memory_table('"""Kept apart from memories."""\nx = 1')


# Spec §7 as amended 2026-09-25: a scan for every repository method name
# cannot tell `session.get` from a repository's `get`, so the rule is stated
# on the names any fact read would need.
_FACT_STORE = re.compile(r"KnowledgeTripleRepository|knowledge_triples")


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_names_the_fact_store(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    assert not _FACT_STORE.search(source), f"{module} names the fact store"


def test_the_fact_store_scan_sees_a_planted_read():
    assert _FACT_STORE.search(
        "from app.repositories.knowledge_triples import KnowledgeTripleRepository"
    )
    assert _FACT_STORE.search("SELECT subject FROM knowledge_triples")
    assert not _FACT_STORE.search("await session.get(Workstream, workstream_id)")
```

In `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` §7, replace

```text
- the work-log modules may name no `KnowledgeTripleRepository` method at all.
```

with

```text
- the work-log modules name neither `KnowledgeTripleRepository`, its module
  nor the `knowledge_triples` table, and the import closure of every
  work-log module except the route module reaches no vault writer.
  Amended 2026-09-25: a scan for every repository method name cannot tell
  `session.get` from a repository's `get`, and the route module reaches the
  repository only through the auth layer every router shares.
```

- [ ] **Step 2: Run the scans**

Run: `.venv/bin/python -m pytest tests/test_worklog_wall.py -q`
Expected: PASS. Then prove the family scan can fail: temporarily add the line `# worklog_embeddings` to the end of `backend/app/services/hybrid_search.py`, rerun, and expect `test_no_memory_or_vault_module_names_the_work_log_vector_family[app.services.hybrid_search]` to FAIL; remove the line with `git checkout -- backend/app/services/hybrid_search.py` and rerun to PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_worklog_wall.py docs/superpowers/specs/2026-09-23-work-log-lane-design.md
git commit -m "test(worklog): wall off the vector family"
```

### Task 6: REST search route

**Files:**
- Modify: `backend/app/schemas/worklog.py`
- Modify: `backend/app/api/routes/worklog.py`
- Modify: `backend/tests/test_api_keys.py` (the two pinned scope-gated route sets)
- Test: `backend/tests/test_worklog_rest.py` (append)

**Interfaces:**
- Consumes: Contracts → Service, Test helpers (Task 4).
- Produces: Contracts → Schemas, REST.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_worklog_rest.py`:

```python
from app.services.worklog_embeddings import embed_entries
from tests.test_worklog_search import SEARCH_FINGERPRINT, TopicEmbedder


@pytest.fixture
def topic_llm():
    from app.main import app
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(SEARCH_FINGERPRINT)
    previous = getattr(app.state, "llm", None)
    app.state.llm = TopicEmbedder()
    yield app.state.llm
    app.state.llm = previous
    embedder_registry.forget(SEARCH_FINGERPRINT)


async def test_search_fuses_both_arms(client, auth_headers, session, topic_llm):
    created = await client.post(f"{V1}/entries", json=_append_body(entries=[
        {"kind": "note", "body": "The deploy script now retries"},
        {"kind": "note", "body": "Release notes drafted"},
    ]), headers={**auth_headers, **RUN})
    ids = created.json()["entry_ids"]
    await embed_entries(session, topic_llm, entry_ids=ids)

    response = await client.post(
        f"{V1}/search", json={"project": "proj", "query": "deploy"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["semantic_ran"] is True
    assert [item["entry"]["id"] for item in body["items"]] == ids
    assert body["items"][0]["arms"] == ["keyword", "semantic"]
    assert body["items"][1]["arms"] == ["semantic"]
    assert body["items"][0]["workstream"] == "plan-a"


async def test_search_answers_by_keyword_without_an_orchestrator(client, auth_headers, monkeypatch):
    from app.main import app

    monkeypatch.setattr(app.state, "llm", None, raising=False)
    await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    response = await client.post(
        f"{V1}/search", json={"project": "proj", "query": "saved"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["semantic_ran"] is False
    assert [item["entry"]["body"] for item in response.json()["items"]] == ["## State\nsaved"]


@pytest.mark.parametrize("body", [
    {"query": "deploy"},
    {"project": "proj", "query": ""},
    {"project": "proj", "query": "   "},
    {"project": "proj", "query": "deploy", "kind": "log"},
    {"project": "proj", "query": "deploy", "limit": 101},
    {"project": "proj", "query": "de\x00ploy"},
])
async def test_search_refuses_bad_requests(client, auth_headers, body):
    response = await client.post(f"{V1}/search", json=body, headers=auth_headers)
    assert response.status_code == 422


async def test_a_read_key_searches_and_a_capture_key_does_not(client, session):
    read = await _key(session, "read")
    capture = await _key(session, "capture")
    body = {"project": "proj", "query": "deploy"}
    assert (await client.post(f"{V1}/search", json=body, headers=read)).status_code == 200
    assert (await client.post(f"{V1}/search", json=body, headers=capture)).status_code == 403
```

In `backend/tests/test_api_keys.py`, add the line

```python
            ("POST", "/api/v1/worklog/search"),
```

directly after `("GET", "/api/v1/worklog/workstreams/{workstream_id}/entries"),` in **both** pinned sets (`test_exactly_the_intended_routes_are_scope_gated` and the mutation drill's `expected`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_worklog_rest.py tests/test_api_keys.py -q`
Expected: FAIL — the search route answers 404 or 405, and the pinned sets name a route that does not exist.

- [ ] **Step 3: Write the implementation**

In `backend/app/schemas/worklog.py`, replace

```python
from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]
```

with

```python
from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    MAX_QUERY_CHARS,
    MAX_SEARCH_LIMIT,
    SEARCH_DEFAULT_LIMIT,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]
Arm = Literal["keyword", "semantic"]
```

and append to the end of the module:

```python
class WorklogSearchRequest(_Storable):
    project: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    workstream: str | None = Field(default=None, min_length=1, max_length=200)
    kind: Kind | None = None
    limit: int = Field(default=SEARCH_DEFAULT_LIMIT, ge=1, le=MAX_SEARCH_LIMIT)


class WorklogSearchHit(BaseModel):
    entry: WorklogEntryOut
    workstream: str
    rrf_score: float
    arms: list[Arm]


class WorklogSearchResponse(BaseModel):
    items: list[WorklogSearchHit]
    semantic_ran: bool
```

In `backend/app/api/routes/worklog.py`, add `WorklogSearchRequest,` and `WorklogSearchResponse,` to the `from app.schemas.worklog import (...)` list (alphabetically, after `WorklogResumeResponse,`), and insert this route directly after the `list_entries` route:

```python
@router.post("/search", response_model=WorklogSearchResponse)
async def search_entries(
    body: WorklogSearchRequest,
    request: Request,
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
):
    # Not `get_llm`: it answers 503 without an orchestrator, and search still
    # has an answer then -- the keyword arm, with semantic_ran false.
    llm = getattr(request.app.state, "llm", None)
    try:
        return await worklog.search(
            session,
            llm,
            project=body.project,
            query=body.query,
            workstream=body.workstream,
            kind=body.kind,
            limit=body.limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_worklog_rest.py tests/test_api_keys.py tests/test_worklog_search.py -q`
Expected: PASS. (The enumeration guards stay red until Task 8.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/worklog.py backend/app/api/routes/worklog.py backend/tests/test_worklog_rest.py backend/tests/test_api_keys.py
git commit -m "feat(worklog): serve search over REST"
```

### Task 7: MCP search tool and scope

**Files:**
- Modify: `backend/app/api/mcp/server.py` (one tool after `worklog_entries`)
- Modify: `backend/app/api/mcp/scopes.py` (`READ_TOOLS`)
- Modify: `backend/tests/test_mcp.py` (the pinned tool roster)
- Test: `backend/tests/test_worklog_mcp.py`

**Interfaces:**
- Consumes: Contracts → Service, Test helpers (Task 4), Schemas (Task 6).
- Produces: Contracts → MCP.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_worklog_mcp.py`, replace the body of `test_each_tool_has_the_scope_the_spec_names` with

```python
    assert {name: TOOL_SCOPES[name] for name in (
        "worklog_append", "worklog_update", "worklog_resume",
        "worklog_workstreams", "worklog_entries", "worklog_search", "worklog_purge",
    )} == {
        "worklog_append": "capture",
        "worklog_update": "capture",
        "worklog_resume": "read",
        "worklog_workstreams": "read",
        "worklog_entries": "read",
        "worklog_search": "read",
        "worklog_purge": "admin",
    }
```

and append:

```python
async def test_search_over_mcp_fuses_both_arms(mcp_on_the_test_session, session, monkeypatch):
    from types import SimpleNamespace

    from app.api.mcp import server
    from app.services.embedder_registry import embedder_registry
    from app.services.worklog_embeddings import embed_entries
    from tests.test_worklog_search import SEARCH_FINGERPRINT, TopicEmbedder

    embedder_registry.forget(SEARCH_FINGERPRINT)
    llm = TopicEmbedder()
    monkeypatch.setattr(server, "_pipeline", SimpleNamespace(llm=llm))
    appended = json.loads(await server.worklog_append(
        project="proj",
        workstream="plan-a",
        entries=[
            {"kind": "note", "body": "The deploy script now retries"},
            {"kind": "note", "body": "Release notes drafted"},
        ],
        run_key="run-1",
    ))
    await embed_entries(session, llm, entry_ids=appended["entry_ids"])

    answer = json.loads(await server.worklog_search(project="proj", query="deploy"))
    assert answer["semantic_ran"] is True
    assert [item["entry"]["id"] for item in answer["items"]] == appended["entry_ids"]
    assert answer["items"][0]["arms"] == ["keyword", "semantic"]
    embedder_registry.forget(SEARCH_FINGERPRINT)


async def test_search_over_mcp_without_a_pipeline_is_keyword_only(mcp_on_the_test_session, monkeypatch):
    from app.api.mcp import server

    monkeypatch.setattr(server, "_pipeline", None)
    await server.worklog_append(
        project="proj",
        workstream="plan-a",
        entries=[{"kind": "note", "body": "Task 3 fixed the flaky migration test"}],
        run_key="run-1",
    )
    answer = json.loads(await server.worklog_search(project="proj", query="migration"))
    assert answer["semantic_ran"] is False
    assert [item["entry"]["body"] for item in answer["items"]] == [
        "Task 3 fixed the flaky migration test",
    ]


async def test_search_over_mcp_refuses_an_unknown_kind(mcp_on_the_test_session):
    from app.api.mcp import server

    with pytest.raises(ValueError):
        await server.worklog_search(project="proj", query="deploy", kind="log")
```

In `backend/tests/test_mcp.py`, add `"worklog_search",` to the pinned roster between `"worklog_resume",` and `"worklog_update",`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_worklog_mcp.py tests/test_mcp.py -q`
Expected: FAIL — `KeyError: 'worklog_search'` and `AttributeError: ... has no attribute 'worklog_search'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/mcp/scopes.py`, add `"worklog_search",` to `READ_TOOLS` directly after `"worklog_entries",`.

In `backend/app/api/mcp/server.py`, insert directly after the `worklog_entries` tool (after its `return json.dumps(page)` and before the `@mcp.tool(` of `worklog_update`):

```python
@mcp.tool(
    description=(
        "Search a project's work log by words and by meaning: entries whose "
        "text matches the query (the whole body) fused by rank with entries "
        "whose meaning is close (the first 8,000 characters), across every "
        "workstream unless workstream (a key) or kind narrows it; limit "
        "1-100. Never returns a memory. Each hit carries the entry, its "
        "workstream key, rrf_score and the arms that found it; semantic_ran "
        "is false when only the keyword arm could run."
    )
)
async def worklog_search(
    project: str,
    query: str,
    workstream: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> str:
    from app.schemas.worklog import WorklogSearchRequest
    from app.services import worklog

    body = WorklogSearchRequest(
        project=project,
        query=query,
        workstream=workstream,
        kind=kind,
        limit=_worklog_limit(limit, worklog.MAX_SEARCH_LIMIT),
    )
    llm = _pipeline.llm if _pipeline is not None else None
    async with async_session_factory() as session:
        answer = await worklog.search(
            session,
            llm,
            project=body.project,
            query=body.query,
            workstream=body.workstream,
            kind=body.kind,
            limit=body.limit,
        )
    return json.dumps(answer)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_worklog_mcp.py tests/test_mcp.py tests/test_mcp_auth.py -q`
Expected: PASS. (`test_prompt_agent_instructions.py` stays red until Task 9.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/server.py backend/app/api/mcp/scopes.py backend/tests/test_mcp.py backend/tests/test_worklog_mcp.py
git commit -m "feat(worklog): serve search over MCP"
```

### Task 8: Guard registries

**Files:**
- Modify: `backend/app/services/content_surfaces.py` (`ROUTES_WITHOUT_MEMORY_CONTENT`, `MCP_TOOLS_WITHOUT_MEMORY_CONTENT`)
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`)
- Modify: `backend/tests/test_door_parity.py` (`PARITY_TABLE`)
- Modify: `docs/two-door-parity.md` (generated table and headline counts)

**Interfaces:**
- Consumes: Contracts → REST (Task 6), MCP (Task 7).
- Produces: nothing later tasks consume.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Run the guards to see them fail**

Run: `.venv/bin/python -m pytest tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py -q`
Expected: FAIL — each names `POST /api/v1/worklog/search` or `worklog_search` as unclassified.

- [ ] **Step 2: Classify the doors**

In `backend/app/services/content_surfaces.py`, add `"POST /api/v1/worklog/search",` directly after `"GET /api/v1/worklog/workstreams/{workstream_id}/entries",`, and `"mcp:worklog_search",` directly after `"mcp:worklog_entries",`.

In `backend/tests/test_api/test_rest_conformance.py`, add `("POST", "/api/v1/worklog/search"): 200,` directly after `("GET", "/api/v1/worklog/workstreams/{workstream_id}/entries"): 200,`.

In `backend/tests/test_door_parity.py`, insert this row into `PARITY_TABLE` directly after the `worklog.entries` row:

```python
    Surface(
        name="worklog.search",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/worklog/search"),),
        mcp=("worklog_search",),
        note=(
            "Both doors call one worklog.search, so ranking, filtering and the "
            "semantic_ran fallback cannot drift. Stated wire asymmetry: the "
            "route refuses a limit above 100 with a 422 while the tool clamps "
            "it, as the other work-log list tools clamp theirs."
        ),
    ),
```

- [ ] **Step 3: Regenerate the parity doc**

From `backend/`:

```bash
.venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown
doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8")
EOF
sed -i 's/^\*\*89 surfaces: 31 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent\.\*\*$/**90 surfaces: 32 two-door, 58 single-door with a stated reason (51 REST-only, 7 MCP-only), 0 divergent.**/' ../docs/two-door-parity.md
git diff --stat -- ../docs/two-door-parity.md
```

Expected: the diff shows one added table row and the changed headline line, nothing else.

- [ ] **Step 4: Run the guards to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/content_surfaces.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "test(guards): classify the work-log search doors"
```

### Task 9: Instructions, CLAUDE.md and runbook

**Files:**
- Modify: `backend/app/services/prompt.py` (`agent_instructions`, the Work log list)
- Modify: `backend/tests/test_prompt_agent_instructions.py`
- Modify: `backend/app/main.py` (the `block_embedding_refresh` job description)
- Modify: `CLAUDE.md` (embedder families, jobs, MCP scopes, Work log)
- Modify: `docs/runbook-exposed-deployment.md` (scope table and MCP counts)

**Interfaces:**
- Consumes: Contracts → Refresh (Task 3), Service (Task 4), REST (Task 6), MCP (Task 7).
- Produces: nothing later tasks consume.

**Items:** 1

**Implementer:** dr-superpowers:impl-sonnet-high
**Executor:** codex gpt-6-sol / medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_prompt_agent_instructions.py`, in `test_the_instructions_route_working_data_to_the_work_log`, add `    assert "worklog_search" in text` after `    assert "worklog_resume" in text`.

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_prompt_agent_instructions.py -q`
Expected: FAIL — `worklog_search` is missing from the instructions (both the new assertion and `test_every_registered_tool_is_named_in_the_instructions`).

- [ ] **Step 3: Update the text**

In `backend/app/services/prompt.py`, insert after the two lines

```python
        "- **worklog_workstreams** / **worklog_entries** — list a project's "
        "workstreams, or read one workstream's entries in order.\n"
```

the lines

```python
        "- **worklog_search** — find entries across a project's workstreams "
        "by words or meaning; narrow by workstream or kind.\n"
```

In `backend/app/main.py`, replace the `block_embedding_refresh` job's description

```python
            "Embeds document blocks that have no vector under the active "
            "embedder: an embed that failed after its filing committed, an "
            "embedder rotation, or documents filed before the door shipped. "
            "Off the hot path. Each run spends embedding calls, so 0 disables "
            "it."
```

with

```python
            "Embeds document blocks, page blocks and work-log entries that "
            "have no vector under the active embedder, each on its own "
            "budget: an embed that failed after its filing committed, an "
            "embedder rotation, a page edit, or any work-log append (appends "
            "never embed inline). Off the hot path. Each run spends embedding "
            "calls, so a budget of 0 disables that sweep."
```

In `CLAUDE.md`:

(a) In "Embedders are partitioned by fingerprint", replace

```text
`block_embeddings`, `page_embeddings`, `relation_embeddings`,
`article_embeddings`, `triple_embeddings` (each `<family>__<slug>`). The
```

with

```text
`block_embeddings`, `page_embeddings`, `relation_embeddings`,
`article_embeddings`, `triple_embeddings`, `worklog_embeddings` (each
`<family>__<slug>`). `worklog_embeddings` alone gets no HNSW index
(`_EXACT_SCAN_PARENTS`): work-log search scans one project's rows exactly,
through a `project` column copied onto each vector row. The
```

(b) In "Jobs (`JobRegistry`)", replace

```text
  `block_embedding_refresh` also sweeps page blocks on its own `page_batch`
  budget.
```

with

```text
  `block_embedding_refresh` also sweeps page blocks on its own `page_batch`
  budget and work-log entries on `worklog_batch`, the only writer of
  `worklog_embeddings`.
```

(c) In the MCP section, replace

```text
**Scopes are per tool** (`app/api/mcp/scopes.py`, `TOOL_SCOPES`, 46 tools):
```

with

```text
**Scopes are per tool** (`app/api/mcp/scopes.py`, `TOOL_SCOPES`, 47 tools):
```

and replace the line `` - `read` (28). `` with `` - `read` (29). ``

(d) In "Work log (`app/services/worklog.py`)", insert before the sentence beginning `` `worklog_purge` and its REST twin are ``:

```text
`worklog_search` (REST `POST /api/v1/worklog/search`, `read`) takes a
required project and fuses, by RRF at equal weights, a `ts_rank` arm over
the whole body and an exact cosine arm over the first 8,000 characters
(`worklog_embeddings__<slug>`, filled only by `block_embedding_refresh`).
With no orchestrator, a read-only instance or a failed query embed the
keyword arm answers alone and the answer says `semantic_ran: false`.
```

In `docs/runbook-exposed-deployment.md`, replace the scope table's `read` row

```text
| `read` | `POST /memories/search/paginated`, `GET /documents/by-uri`, `GET /documents/manifest`, `GET /worklog/resume`, `GET /worklog/workstreams`, `GET /worklog/workstreams/{id}/entries` |
```

with

```text
| `read` | `POST /memories/search/paginated`, `GET /documents/by-uri`, `GET /documents/manifest`, `GET /worklog/resume`, `GET /worklog/workstreams`, `GET /worklog/workstreams/{id}/entries`, `POST /worklog/search` |
```

replace

```text
activation, 2026-08-26): of its 46 tools, 15 require `capture`, 28 require
```

with

```text
activation, 2026-08-26): of its 47 tools, 15 require `capture`, 29 require
```

and replace

```text
the REST routes above, and a `read`-scoped key reaches the 28 readers. The
```

with

```text
the REST routes above, and a `read`-scoped key reaches the 29 readers. The
```

- [ ] **Step 4: Run the guard leg**

Run, from `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS. Then re-read by hand the two prose counts the leg does not cover: `docs/two-door-parity.md`'s headline (90 / 32) and `CLAUDE.md`'s tool count (47, read 29) and job count (unchanged: twenty-five).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/prompt.py backend/tests/test_prompt_agent_instructions.py backend/app/main.py CLAUDE.md docs/runbook-exposed-deployment.md
git commit -m "docs(worklog): document search and its budget"
```
