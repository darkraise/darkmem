# Round-Trip Fidelity Implementation Plan (Increment 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Make the document store round-trip: `documents.content TEXT NULL` becomes the source of record (the ONLY baseline regeneration in the whole programme), `GET /documents/{id}` and MCP `document_get` return it behind an `include_content` flag defaulting to off, and `expected_hash` lands as a SQL compare-and-set (review finding M1) — the predicate rides the write, never a read-then-write, with 409 on REST and a structured refusal on MCP. The forgeable `properties["$content"]` bridge (M6) is cut, not implemented: nothing in this plan writes or reads a `$content` key.

**Architecture:** One column, written by the one writer (`file_document` → `repositories/documents`) and read by one new door function (`document_content`), so both doors stay on one service layer (invariant 17). The compare-and-set is a WHERE predicate on the repository's UPDATE statement with a rowcount check — the row lock plus predicate re-evaluation under READ COMMITTED is what closes M1's race, and Task 4 carries a deterministic two-session test that fails under the naive read-then-write implementation. `blocks.char_span` becomes meaningful for the first time: it has always indexed into a source the schema did not keep, and after Task 2 it indexes into the stored `content` byte-for-byte (frontmatter and fences included — spans point at the source, not the retrievable text, per `document_parsers.py`'s own contract).

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §5 as revised (the bridge is CUT; the column is taken now). **Review:** the 2026-08-31 adversarial review — M1 (compare-and-set, the race demonstration), M6 (retired by cutting the bridge), m3 (retired with it; the unchanged path is still re-checked here in Tasks 2 and 4).

**Amendments (2026-09-02, cross-plan adversarial review of all eight plans).** Five defects were found in this plan and are fixed in place, not appended: **B-3** — `content` now carries a `= None` default on both repository writers, because increment 4 calls the old signature and declares this plan not a prerequisite (Task 2 Step 1). **M-1** — Task 8's drop/recreate destroys the increment-0 API key, the armed `auto_research` row, feature flags, job configs and repositories; Step 2 now captures them and Step 6 probes `tools/list`. **M-5** — `docs/two-door-parity.md` is *generated* from `PARITY_TABLE`, the inverse of what the Global Constraints and Tasks 5-6 said; those now edit the module constant and regenerate. **m-13** — Task 7 gains a CLAUDE.md step, which increment 8 assumes has happened. **m-6** — the "stale `$content` references" note was itself stale and is withdrawn. Tasks 1-4 and Task 8's regeneration sequence were found sound.

**Sequencing that binds:** increment 3 **must land and deploy before increment 5** (`docs/superpowers/plans/2026-08-31-docs-corpus-import.md` line 25-30 already records "increment 2 deployed → increment 3 deployed → this plan"). The whole argument for taking the column now is that a regeneration is cheapest while `documents` holds 0 rows everywhere.

## Global Constraints

- **This is the programme's single baseline regeneration.** `0001_baseline.py` is regenerated **in place** — never a `0002`. `./scripts/gate.sh` asserts exactly one revision (`scripts/gate.sh:162-182`) and must stay green. Claim the baseline lane before Task 1: the baseline is a single shared mutable file and schema changes serialise through one owner per epic (CLAUDE.md, Migrations). The parallel increments (4, 6, 7, 8) carry **no** schema change per the spec's §6 table, so there is no contention to wait on — but say so in the task's commit message.
- **Backend tests:** from `backend/`, `.venv/bin/python -m pytest -q`. Needs `darkmem_test` on 127.0.0.1:5433. conftest runs `DROP SCHEMA public CASCADE` + `alembic upgrade head` per session (`backend/tests/conftest.py:34-57`), so **every baseline edit is picked up automatically by the next test run**. Never point it at a real database. The parallel lanes' databases (`darkmem_test_2..5`) self-reset the same way.
- **Merge gate:** `./scripts/gate.sh` from the repo root; green before the final commit. `--full` is unreliable on this host (earlyoom kills Chromium); never invoke Playwright bare — `backend/scripts/e2e/run_playwright_e2e.py`.
- **Greenfield ruling (CLAUDE.md, "Greenfield until the freeze"):** no compatibility shim, no dual-write, no import path for existing rows, no backfill machinery. Prod holds **0 documents**. The regeneration's deployed-database cost is Task 8's drop/recreate plus the three-artifact restore — nothing else.
- **Two doors, one service layer (invariant 17):** every behavior lands in `document_door` / `document_ingest` / `repositories.documents` once; REST and MCP only map it onto their wire. **`PARITY_TABLE` in `backend/tests/test_door_parity.py` is the audit of record, and `docs/two-door-parity.md` is GENERATED from it** — the module says so at `:9-11`, and `test_the_committed_table_is_the_enforced_table` (`:1834-1849`) compares the committed markdown byte-for-byte against `render_markdown()`. The rationale prose lives in the module-level constants `_RETRIEVAL_WIRE_SHAPE` and `_WRITE_WIRE_SHAPE` (`:83-116`), **not** in the markdown. So the sequence in Tasks 5 and 6 is: edit the constant, regenerate the doc, run the test. Hand-editing the markdown table produces a whitespace chase and a red gate. (Corrected 2026-09-02 by the cross-plan review; this constraint previously described the maintenance model backwards.)
- **The block-channel firewall is structural** (`tests/test_block_pipeline.py`, `tests/test_block_retrieval.py` import-closure scans). Nothing here adds an import into the memory pipeline or the vault; if a scan goes red, the change is wrong, not the scan.
- **No `$content` anywhere.** The bridge is cut (spec §5.1). If any task finds itself writing a reserved `properties` key, it has drifted into the retired design — stop.
- **SDK generator is a zero-diff check, not a regeneration:** `sdks/generate.py` binds only `capture`, `search`, `declareContext` — no document verb — so the additive REST fields regenerate nothing. Task 7 verifies `make generate` produces no diff.
- **Commits:** `<type>(<scope>): <subject>`, ≤50 chars, atomic per task. A `feat`/`fix` on master cuts a release; Task 7 writes the CHANGELOG section — coordinate the version number with any parallel increment landing in the same push.
- **Redeploy rule:** this epic touches `backend/`, so it must be redeployed after landing — and this particular deploy is the drop/recreate regeneration. Task 8 is that procedure, verbatim from `docs/runbook-deployment.md`; do not improvise around it.

## File Structure

```
backend/migrations/versions/0001_baseline.py   # Task 1: documents.content TEXT (regenerated in place)
backend/app/repositories/documents.py          # Task 2: content in both write statements; Task 3: CAS predicate + rowcount
backend/app/services/document_ingest.py        # Task 2: content pass-through; Task 4: expected_hash, DocumentHashConflict
backend/app/services/block_pipeline.py         # Task 4: expected_hash pass-through on ingest_document
backend/app/services/document_door.py          # Task 5: document_content; Task 6: expected_hash + PutResult.content_hash
backend/app/api/routes/documents.py            # Task 5: include_content; Task 6: expected_hash + 409 + content_hash
backend/app/api/mcp/server.py                  # Task 5: document_get flag; Task 6: document_put CAS + refusal
backend/tests/test_documents.py                # Tasks 2, 4: writer + ingest-level tests
backend/tests/test_document_cas.py             # Task 3 (new): repo CAS tests; Task 4: the two-session race proof
backend/tests/test_document_door.py            # Tasks 5, 6: door-level tests
backend/tests/test_document_routes.py          # Tasks 5, 6: REST wire tests
backend/tests/test_mcp.py                      # Tasks 5, 6: MCP wire tests
backend/tests/test_door_parity.py              # Tasks 5, 6: mirror text moves with the parity doc
docs/two-door-parity.md                        # Tasks 5, 6: rows 57-58 amended
CHANGELOG.md                                   # Task 7
```

---

### Task 1: Baseline regeneration — `documents.content TEXT`

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py:1276-1289` (the `CREATE TABLE documents` block)

**Interfaces:**
- Consumes: nothing.
- Produces: the `documents.content` column every later task writes or reads.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 0 - spec 0 - coupling 2 - risk 3 = 5
**Approach:** inline - skip 3: the spec (§5, revised) took the column-versus-bridge decision; only the transcription remains.

- [ ] **Step 1: Add the column**

In `0001_baseline.py`'s `CREATE TABLE documents` (lines 1276-1289), after the `content_hash TEXT,` line, add:

```sql
            content      TEXT,
```

so the block reads:

```sql
        CREATE TABLE documents (
            id           UUID NOT NULL,
            project      TEXT NOT NULL,
            title        TEXT,
            source_type  TEXT,
            uri          TEXT,
            content_hash TEXT,
            content      TEXT,
            properties   JSONB,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT documents_pkey PRIMARY KEY (id)
        )
```

Amend the comment block above the table (the one starting "Identity key:" is below; the header comment above `CREATE TABLE documents` at ~1265) — append one sentence: `content is the verbatim source of record (2026-08-31 spec §5, the round-trip column); content_hash is its change gate and blocks.char_span indexes into it.` NULLable on purpose: a source filed as bytes (the PDF drill path — no production caller can deliver one) has no text to store, and TEXT NULL is the honest shape for it.

No new index: nothing queries by content, and the column must never enter `_LIST_SQL` or the resolve statements (read amplification is the reason §5.1 gave for rejecting a jsonb bridge on this table).

- [ ] **Step 2: Verify**

```bash
ls backend/migrations/versions/            # exactly one file, still 0001_baseline.py
cd backend && .venv/bin/python -m pytest tests/test_documents.py tests/test_document_routes.py -q
```

conftest re-migrates the test database from the edited baseline; the suite must stay green (the column is additive and nothing reads it yet). Then run the gate's own assertion path: `./scripts/gate.sh` will assert the single revision at Task 7 — here it is enough that `alembic history` shows one revision.

Commit: `feat(documents): add content column to the baseline` — body notes this is the programme's only baseline edit and that the deployed-database cost is paid in this plan's final task.

---

### Task 2: The writer stores `content`

**Files:**
- Modify: `backend/app/repositories/documents.py` (`_UPSERT_BY_URI` :75, `_UPDATE_DOCUMENT` :90, `upsert_by_uri` :146, `update_document` :180)
- Modify: `backend/app/services/document_ingest.py` (`_file_document_without_savepoint` :176)
- Modify: `backend/tests/test_documents.py`

**Interfaces:**
- Consumes: Task 1's column.
- Produces: stored `content` that Task 5's read serves.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Widen the two write statements**

`_UPSERT_BY_URI` becomes:

```python
_UPSERT_BY_URI = text(
    """
    INSERT INTO documents (id, project, uri, title, source_type, content_hash,
                           content, properties)
    VALUES (CAST(:id AS uuid), CAST(:project AS text), CAST(:uri AS text),
            CAST(:title AS text), CAST(:source_type AS text),
            CAST(:content_hash AS text), CAST(:content AS text),
            CAST(:properties AS jsonb))
    ON CONFLICT (project, uri) WHERE uri IS NOT NULL DO UPDATE SET
        title = EXCLUDED.title,
        source_type = EXCLUDED.source_type,
        content_hash = EXCLUDED.content_hash,
        content = EXCLUDED.content,
        properties = EXCLUDED.properties
    RETURNING id
    """
)
```

`_UPDATE_DOCUMENT` becomes:

```python
_UPDATE_DOCUMENT = text(
    """
    UPDATE documents SET
        title = CAST(:title AS text),
        source_type = CAST(:source_type AS text),
        content_hash = CAST(:content_hash AS text),
        content = CAST(:content AS text),
        properties = CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
    """
)
```

Add `content: str | None = None` as a keyword-only parameter to `upsert_by_uri` and `update_document` (beside `content_hash`), passed straight into the bind params. **The `= None` default is load-bearing and not a style choice** (cross-plan review B-3, 2026-09-02): increment 4's `test_projects_endpoint.py` helper calls `upsert_by_uri` with today's seven keywords and declares increment 3 not a prerequisite, so a required eighth keyword turns that suite red whichever plan lands second. The default is also the honest one — the bytes-source path stores NULL anyway (Step 2). Do **not** add `content` to `_RESOLVE_BY_URI` / `_RESOLVE_BY_ID` or to `DocumentRow`: the resolve runs on every filing and must not drag a 1 MB text along — the read is Task 5's own statement.

- [ ] **Step 2: Pass it through the writer**

In `_file_document_without_savepoint` (`document_ingest.py:176`), after `content_hash = compute_content_hash(content)` add:

```python
    stored_content = content if isinstance(content, str) else None
```

and pass `content=stored_content` into both the `upsert_by_uri` and `update_document` calls. Rationale to carry in a one-line comment: text sources round-trip verbatim; a bytes source (the PDF drill path, unreachable from either door — `content` is `str` on both) has no text form, so it stores NULL rather than a lossy decode.

The `UNCHANGED` gate (`document_ingest.py:215-216`) stays exactly as it is — **no content write on the unchanged path, on purpose**. `compute_content_hash` is sha256 over the UTF-8 bytes (`document_ingest.py:131-135`), so hash equality means the stored `content` already equals the pushed content byte-for-byte; and a NULL-content row can never meet a str re-push in any deployed database, because Task 8 drops and recreates every deployed database and every writer from this task on stores content. This is the m3 re-check the review asked for: the residue m3 described existed only for the property bridge, and the regeneration is what retires it for the column.

- [ ] **Step 3: Tests** (in `backend/tests/test_documents.py`, following its existing `file_document` test style)

```python
async def test_filing_stores_the_verbatim_source(session):
    content = "---\ntitle: x\n---\n\n# H\n\nbody\n"
    filed = await file_document(
        session, project="default", uri="docs/rt.md",
        content=content, parse=_Parser(_drafts("body")),
    )
    stored = (await session.execute(
        text("SELECT content FROM documents WHERE id = :id"),
        {"id": filed.document_id},
    )).scalar_one()
    assert stored == content   # byte-for-byte, frontmatter and fences included


async def test_refiling_replaces_content_and_unchanged_keeps_it(session):
    # updated: content follows the new source
    # unchanged: hash equality proves the stored content already matches
    ...  # put v1, assert stored == v1; put v2, assert stored == v2;
         # put v2 again, assert outcome == UNCHANGED and stored == v2


async def test_a_bytes_source_stores_null_content(session):
    ...  # file_document(content=b"%PDF-1.4 ...", parse=...) -> content IS NULL
```

Write the elided bodies in the same shape as the first test. Run `cd backend && .venv/bin/python -m pytest tests/test_documents.py -q`.

Commit: `feat(documents): store the verbatim source in content`

---

### Task 3: The compare-and-set lives in the SQL

**Files:**
- Modify: `backend/app/repositories/documents.py` (`_UPDATE_DOCUMENT`, `update_document`)
- Create: `backend/tests/test_document_cas.py`

**Interfaces:**
- Consumes: Task 2's statement shape.
- Produces: the `expected_hash` predicate + rowcount return Task 4 drives.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: the spec (§5.3) chose compare-and-set-in-SQL. One deviation from its sketch, flagged per the trust-the-code rule: §5.3 sketches the predicate on the `ON CONFLICT ... DO UPDATE` arm of a single upsert, but the code's writer is split (`upsert_by_uri` only runs when no row resolved; `update_document` is the path an existing row takes — `document_ingest.py:218-244`), and the upsert shape would additionally *insert* when the precondition names a document that is gone, silently ignoring the caller's assertion. So the predicate rides `update_document`, and a passed `expected_hash` with no resolvable row is refused before any write (Task 4). Same guarantee, honest on the missing-row edge.

- [ ] **Step 1: The predicate rides the write**

`_UPDATE_DOCUMENT` becomes:

```python
# The `expected_hash` arm is M1's whole point and must stay IN this statement:
# a read-then-compare in Python passes for both of two racing lanes and the
# second still clobbers the first. Inside the UPDATE, the loser blocks on the
# winner's row lock, re-evaluates the predicate against the committed row, and
# matches zero rows — which the caller must treat as the conflict. NULL
# expected_hash disables the arm (last-writer-wins, the pre-CAS behaviour).
_UPDATE_DOCUMENT = text(
    """
    UPDATE documents SET
        title = CAST(:title AS text),
        source_type = CAST(:source_type AS text),
        content_hash = CAST(:content_hash AS text),
        content = CAST(:content AS text),
        properties = CAST(:properties AS jsonb)
    WHERE id = CAST(:id AS uuid)
      AND (CAST(:expected_hash AS text) IS NULL
           OR content_hash = CAST(:expected_hash AS text))
    """
)
```

`update_document` gains `expected_hash: str | None = None` (keyword-only, beside `content`) and **returns the matched-row count**:

```python
async def update_document(...) -> int:
    result = await session.execute(_UPDATE_DOCUMENT, {..., "expected_hash": expected_hash})
    return result.rowcount
```

Update its docstring: zero with an `expected_hash` means the precondition failed (or the row vanished); zero without one means the row vanished. The caller decides what either means — this module only reports.

- [ ] **Step 2: Repository-level tests** (new file `backend/tests/test_document_cas.py`, using the standard `session` fixture for this task's tests)

Three tests, driving `upsert_by_uri` once to seed and then `update_document` directly:

1. `test_matching_expected_hash_updates_and_reports_one_row` — seed a row, call `update_document(expected_hash=<seeded hash>, content_hash=<new>, ...)`, assert return `== 1` and the row moved.
2. `test_stale_expected_hash_matches_zero_rows_and_writes_nothing` — call with a wrong `expected_hash`, assert return `== 0` and a re-SELECT shows every column untouched.
3. `test_null_expected_hash_keeps_last_writer_wins` — call with `expected_hash=None`, assert return `== 1`.

Run `cd backend && .venv/bin/python -m pytest tests/test_document_cas.py -q`.

Commit: `feat(documents): compare-and-set predicate on the update`

---

### Task 4: `expected_hash` through the ingest chain, and the race shown closed

**Files:**
- Modify: `backend/app/services/document_ingest.py` (`DocumentHashConflict`, `file_document` :138, `_file_document_without_savepoint` :176, `__all__` :82)
- Modify: `backend/app/services/block_pipeline.py` (`ingest_document` :171)
- Modify: `backend/tests/test_document_cas.py` (the race proof), `backend/tests/test_documents.py` (semantics)

**Interfaces:**
- Consumes: Task 3's rowcount return.
- Produces: `DocumentHashConflict`, which Task 6's doors map to their wire shapes.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: The exception**

In `document_ingest.py`, beside the outcome constants:

```python
class DocumentHashConflict(Exception):
    """`expected_hash` did not match the document's current `content_hash`.

    Raised after the SAVEPOINT has rolled the filing back, like every other
    `file_document` failure: nothing was written. `current_hash` is the hash
    that actually holds (re-read after the compare-and-set matched zero rows,
    so under a race it names the winner), or None when the precondition named
    a document that does not exist.
    """

    def __init__(self, *, document_id, expected_hash: str, current_hash: str | None):
        self.document_id = document_id
        self.expected_hash = expected_hash
        self.current_hash = current_hash
        super().__init__(
            f"expected_hash {expected_hash} does not match the document's "
            f"current content_hash {current_hash}"
        )
```

Add `"DocumentHashConflict"` to `__all__`.

- [ ] **Step 2: Plumb and enforce**

`file_document` and `_file_document_without_savepoint` gain `expected_hash: str | None = None` (keyword-only). In `_file_document_without_savepoint`, immediately after the resolve (before the `UNCHANGED` gate at :215):

```python
    if expected_hash is not None:
        if existing is None:
            raise DocumentHashConflict(
                document_id=None, expected_hash=expected_hash, current_hash=None,
            )
        if existing.content_hash != expected_hash:
            # Fast-fail on the resolve's snapshot. This read-then-refuse only
            # ever refuses — the authority that closes the race is the SQL
            # predicate below, which re-checks under the row lock. A spurious
            # refusal here (the row moved TO expected after this read) is a
            # safe 409 the caller retries; the naive version of this feature
            # was a read-then-WRITE, which is the bug (review M1).
            raise DocumentHashConflict(
                document_id=existing.id,
                expected_hash=expected_hash,
                current_hash=existing.content_hash,
            )
```

Note what this ordering decides: a byte-identical re-push carrying a *stale* `expected_hash` is a conflict, not `UNCHANGED` — the precondition "the document is as I last saw it" failed, and refusing is the consistent contract even when the write would have been a no-op. A byte-identical re-push with a *matching* `expected_hash` still short-circuits to `UNCHANGED` exactly as today.

Then on the existing-row write path (:238-244), pass the predicate through and treat zero rows as the conflict:

```python
        matched = await documents_repo.update_document(
            session,
            document_id=resolved_id,
            title=title,
            source_type=source_type,
            content_hash=content_hash,
            content=stored_content,
            properties=properties,
            expected_hash=expected_hash,
        )
        if matched == 0:
            current = await documents_repo.resolve_by_id(session, resolved_id)
            raise DocumentHashConflict(
                document_id=resolved_id,
                expected_hash=expected_hash,
                current_hash=None if current is None else current.content_hash,
            )
```

(`expected_hash` is None on the no-precondition path, so `matched == 0` then means the row vanished mid-filing — the subsequent `insert_blocks` FK failure already handled that; raising the conflict with `expected_hash=None` never happens because the predicate arm is disabled. Guard the `raise` with `if expected_hash is not None` and let the vanished-row case fall through to today's behavior.)

In `block_pipeline.ingest_document` (:171), add `expected_hash: str | None = None` and forward it to `file_document`. **Do not** add it to `DocumentFileJob` / `ingest_documents` / `file_documents_isolated`: the batch path is the corpus import's, which is last-writer-wins re-runnable by design (`docs/superpowers/plans/2026-08-31-docs-corpus-import.md`).

- [ ] **Step 3: The race proof — a test that fails under the naive implementation**

Append to `backend/tests/test_document_cas.py`. This test drives `file_document` itself — the level where the naive read-then-write would live — on two genuinely independent connections (the `tests.conftest.test_engine` import pattern `test_expiry_sweep.py:34-38` already uses; the standard `session` fixture's single outer transaction cannot express two lanes). It commits real rows and cleans them up; the journalled `document_filed` events stay, which is the same residue every real-commit test in the suite leaves.

```python
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.document_ingest import (
    BlockDraft, DocumentHashConflict, file_document,
)
from tests.conftest import test_engine

PROJECT = "cas-race"
URI = "docs/cas-race.md"


def _parse(content: str):
    return lambda: [BlockDraft(text=content)]


@pytest.mark.asyncio
async def test_two_lanes_with_the_same_expected_hash_cannot_both_win(setup_database):
    """M1's race, deterministically interleaved and shown closed.

    Both lanes resolve the document at hash H0 before either commit lands —
    the exact window the review's naive read-then-write leaves open. Under
    that implementation lane B's own comparison passes (it read H0), its
    unconditional UPDATE blocks on lane A's row lock, then proceeds and
    clobbers: no exception, B's content survives, and this test FAILS on
    both assertions. Under the compare-and-set the blocked UPDATE
    re-evaluates its predicate against A's committed row, matches zero rows,
    and B gets DocumentHashConflict naming A's hash.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    seed, lane_a, lane_b = factory(), factory(), factory()
    try:
        first = await file_document(
            seed, project=PROJECT, uri=URI, content="v0", parse=_parse("v0"),
        )
        await seed.commit()
        h0 = first.content_hash

        # Lane A: passes the precondition and holds the row lock, uncommitted.
        res_a = await file_document(
            lane_a, project=PROJECT, uri=URI, content="lane A",
            parse=_parse("lane A"), expected_hash=h0,
        )

        # Lane B: resolves H0 (MVCC — the SELECT does not block), passes any
        # door-level comparison, and must now block on lane A's row lock.
        task_b = asyncio.create_task(asyncio.wait_for(
            file_document(
                lane_b, project=PROJECT, uri=URI, content="lane B",
                parse=_parse("lane B"), expected_hash=h0,
            ),
            timeout=15,
        ))
        await asyncio.sleep(0.3)
        assert not task_b.done(), (
            "lane B finished before lane A committed — it never entered the "
            "race window this test exists to exercise"
        )

        await lane_a.commit()

        with pytest.raises(DocumentHashConflict) as exc:
            await task_b
        assert exc.value.expected_hash == h0
        assert exc.value.current_hash == res_a.content_hash  # names the winner

        check = factory()
        try:
            row = (await check.execute(
                text(
                    "SELECT content_hash, content FROM documents "
                    "WHERE project = :p AND uri = :u"
                ),
                {"p": PROJECT, "u": URI},
            )).one()
            assert row.content_hash == res_a.content_hash
            assert row.content == "lane A"     # the loser wrote nothing
        finally:
            await check.close()
    finally:
        await lane_b.rollback()
        cleanup = factory()
        try:
            await cleanup.execute(
                text("DELETE FROM documents WHERE project = :p"), {"p": PROJECT},
            )
            await cleanup.commit()
        finally:
            await cleanup.close()
        await seed.close(); await lane_a.close(); await lane_b.close()
```

- [ ] **Step 4: Semantics tests** (in `test_documents.py`, single-session, standard fixture)

1. `test_matching_expected_hash_updates` — put v1, put v2 with `expected_hash=<v1 hash>` → outcome `updated`.
2. `test_stale_expected_hash_is_refused_and_nothing_is_written` — put v1, put v2 with a wrong hash → `pytest.raises(DocumentHashConflict)`; re-SELECT shows v1's hash, content and block set intact (the SAVEPOINT rolled the filing back).
3. `test_expected_hash_against_a_missing_document_is_refused` — no row filed → conflict with `current_hash is None`.
4. `test_unchanged_repush_with_matching_expected_hash_stays_unchanged` — put v1, put v1 again with `expected_hash=<v1 hash>` → outcome `unchanged`.
5. `test_unchanged_content_with_stale_expected_hash_is_still_a_conflict` — put v1, put v1 again with a wrong hash → conflict (the ordering decision in Step 2, pinned).
6. `test_omitting_expected_hash_keeps_last_writer_wins` — two sequential puts, no precondition → both succeed.

Run `cd backend && .venv/bin/python -m pytest tests/test_document_cas.py tests/test_documents.py -q`.

Commit: `feat(documents): expected_hash compare-and-set in the writer`

---

### Task 5: `include_content` on both doors

**Files:**
- Modify: `backend/app/services/document_door.py` (new `document_content`, `__all__`)
- Modify: `backend/app/api/routes/documents.py` (`DocumentBlocksResponse` :254, `document_blocks_route` :529)
- Modify: `backend/app/api/mcp/server.py` (`document_get` :725)
- Modify: `docs/two-door-parity.md:58` + `backend/tests/test_door_parity.py` (the mirrored retrieval-row text)
- Modify: `backend/tests/test_document_routes.py`, `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: Task 2's stored content.
- Produces: nothing later tasks consume.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3
**Approach:** inline - skip 4 (MCP wire shape): with the flag off the tool answers today's bare array unchanged — the spec's "no existing reader pays" — and with it on it answers `{"content": ..., "blocks": [...]}`; confined to `server.py` and trivially reversible before any consumer exists.

- [ ] **Step 1: One read in the service layer**

In `document_door.py`, beside `document_blocks`:

```python
_DOCUMENT_CONTENT = text(
    "SELECT content FROM documents WHERE id = CAST(:document_id AS uuid)"
)


async def document_content(session: AsyncSession, *, document_id: str) -> str | None:
    """The document's verbatim source of record — the exact text `put` filed,
    frontmatter and fences included, which is also what every block's
    `char_span` indexes into. None for a document filed from a non-text
    source. Read-only, same posture as `document_blocks`: commits nothing,
    opens no savepoint. Deliberately its own statement rather than a column
    on the list or resolve reads — the source can be 1 MB and only this
    caller asked for it.
    """
    return (await session.execute(
        _DOCUMENT_CONTENT, {"document_id": document_id}
    )).scalar_one_or_none()
```

Export it in `__all__`.

- [ ] **Step 2: REST**

`DocumentBlocksResponse` gains, after `blocks`:

```python
    # The verbatim filed source (blocks.char_span indexes into it), only when
    # the request opted in with include_content — absent-by-default so no
    # existing reader pays for a potentially 1 MB field (spec §5.2).
    content: str | None = None
```

`document_blocks_route` gains `include_content: bool = Query(False)`; after fetching `rows`:

```python
    content = (
        await document_content(session, document_id=target)
        if include_content else None
    )
    return DocumentBlocksResponse(
        document_id=target,
        blocks=[BlockRowModel(**vars(r)) for r in rows],
        content=content,
    )
```

Works identically on both decorators (`/{document_id}` and `/by-uri`).

- [ ] **Step 3: MCP**

`document_get` gains `include_content: bool = False` (documented in its Args block: "also return the document's verbatim source under `content`; the result becomes `{content, blocks}` instead of the bare block array"). After fetching `rows`:

```python
    if include_content:
        raw = await document_content(session, document_id=target)
        return json.dumps({"content": raw, "blocks": [vars(r) for r in rows]})
    return json.dumps([vars(r) for r in rows])
```

(the `document_content` call goes inside the existing `async with async_session_factory() as session:` block).

- [ ] **Step 4: Parity doc + mirror**

Append to the `_RETRIEVAL_WIRE_SHAPE` constant in `backend/tests/test_door_parity.py` (`:83-116`): `Since the 2026-08-31 round-trip increment both keyed reads take include_content (default off): on, the route adds the verbatim filed source as content on its envelope and the tool answers {content, blocks} in place of the bare array -- the one flag under which document_get answers an object, produced by the same document_content service read on both doors.` Then **regenerate** `docs/two-door-parity.md` from the table — never hand-edit it:

```bash
cd backend && .venv/bin/python -c \
  "from tests.test_door_parity import render_markdown; print(render_markdown())"
```

and paste the output between the doc's generated-table markers. No headline change: this task adds no surface, so the derived counts do not move. Run `pytest tests/test_door_parity.py -q` until `test_the_committed_table_is_the_enforced_table` agrees.

- [ ] **Step 5: Wire tests**

REST (`test_document_routes.py`): flag off → `content` is `None`; `?include_content=true` → `content` equals the filed source byte-for-byte (assert against the exact string that was PUT, frontmatter included); works on the `by-uri` twin. MCP (`test_mcp.py`, beside its existing `document_get` coverage): default → `json.loads` gives a `list`; `include_content=True` → a `dict` with `content` equal to the filed source and `blocks` equal to the default call's list.

Run `cd backend && .venv/bin/python -m pytest tests/test_document_routes.py tests/test_mcp.py tests/test_door_parity.py -q`.

Commit: `feat(documents): serve the source behind include_content`

---

### Task 6: `expected_hash` on both doors — 409 and the structured refusal

**Files:**
- Modify: `backend/app/services/document_door.py` (`PutResult` :137, `put_document` :409)
- Modify: `backend/app/api/routes/documents.py` (`DocumentPutRequest` :174, `DocumentPutResponse` :182, `put_document_route` :391)
- Modify: `backend/app/api/mcp/server.py` (`document_put` :614)
- Modify: `docs/two-door-parity.md:57` + `backend/tests/test_door_parity.py` (the write-row mirror)
- Modify: `backend/tests/test_document_door.py`, `backend/tests/test_document_routes.py`, `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: Task 4's `DocumentHashConflict` and `ingest_document(expected_hash=...)`.
- Produces: nothing later tasks consume.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Door service**

`put_document` gains `expected_hash: str | None = None`, forwarded to `ingest_document`. `DocumentHashConflict` propagates out of the inner `begin_nested` untouched — the filing is already rolled back, the same contract as `DocumentTooLarge`.

`PutResult` gains, after `outcome`:

```python
    # The hash of what is now stored — what a caller passes as expected_hash
    # on its next edit. Without this echo the compare-and-set is unusable: no
    # read on either door served the current hash before it existed here.
    content_hash: str
```

populated from `filed.content_hash` in the return. (This closes a gap the spec leaves open: §5.3's caller must know the current hash to precondition on, and until now no wire surface served one. Flagged in Notes on scope.)

- [ ] **Step 2: REST**

`DocumentPutRequest` gains `expected_hash: str | None = None` (with a Field description: "compare-and-set precondition: the content_hash from your last put or get; omit on a first filing"). `DocumentPutResponse` gains `content_hash: str` beside `outcome`. In `put_document_route`, pass `expected_hash=body.expected_hash` and add, before the generic handlers:

```python
    except DocumentHashConflict as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            (
                f"expected_hash {exc.expected_hash} does not match the "
                f"document's current content_hash {exc.current_hash}; "
                "re-read the document before writing"
                if exc.current_hash is not None
                else f"expected_hash {exc.expected_hash} names a document "
                     "that does not exist"
            ),
        ) from exc
```

(409 is the conventions doc's conflicting-state answer, `docs/api-rest-conventions.md:26-27`.) Import `DocumentHashConflict` from `app.services.document_ingest`. Add `content_hash=result.content_hash` to the response construction.

- [ ] **Step 3: MCP**

`document_put` gains `expected_hash: str | None = None` (Args: "compare-and-set precondition — pass the content_hash from your last put or get; a mismatch returns a hash_conflict result instead of writing"). Around the existing call:

```python
        try:
            result = await put_document(
                session, _pipeline.llm,
                project=project, uri=uri, content=content,
                title=title, source_type=source_type, source=source,
                expected_hash=expected_hash,
            )
        except DocumentHashConflict as exc:
            await session.rollback()
            # Neither _degraded (the server is not down) nor a raise (the
            # caller made no mistake — it lost a race): a structured refusal
            # the agent machine-reads and recovers from by re-reading.
            return json.dumps({
                "schema_version": ENVELOPE_SCHEMA_VERSION,
                "status": "hash_conflict",
                "document_id": None if exc.document_id is None else str(exc.document_id),
                "expected_hash": exc.expected_hash,
                "current_hash": exc.current_hash,
                "reason": str(exc),
            })
        except Exception:
            await session.rollback()
            raise
```

The success path (`json.dumps(vars(result))`) picks up `content_hash` from `PutResult` with no further change — the "same fields on both doors, produced once" property the parity doc records.

- [ ] **Step 4: Parity doc + mirror**

Append to the `_WRITE_WIRE_SHAPE` constant in `backend/tests/test_door_parity.py` (`:83-116`): `Since the 2026-08-31 round-trip increment put takes an optional expected_hash compare-and-set (spec section 5.3): the predicate rides the writer's own UPDATE, a stale hash answers 409 on the route and a hash_conflict envelope from the tool -- one refusal produced by DocumentHashConflict on both doors -- and PutResult now also carries content_hash, so both doors echo the hash a caller preconditions its next edit on.` Then regenerate `docs/two-door-parity.md` from `render_markdown()` exactly as in Task 5 Step 4 and re-run the parity test. The doc is generated; do not hand-edit the table.

- [ ] **Step 5: Wire tests**

- `test_document_door.py`: `put_document` with a matching `expected_hash` succeeds; with a stale one raises `DocumentHashConflict` and a re-read shows the prior content intact; `PutResult.content_hash` equals sha256 of the content (`compute_content_hash`).
- `test_document_routes.py`: stale `expected_hash` → 409 whose detail names both hashes; matching → 201 with the new `content_hash` on the body; omitted → today's behavior byte-for-byte.
- `test_mcp.py`: stale hash → the `hash_conflict` envelope (assert `status`, `expected_hash`, `current_hash` keys); success payload carries `content_hash`.

Run `cd backend && .venv/bin/python -m pytest tests/test_document_door.py tests/test_document_routes.py tests/test_mcp.py tests/test_door_parity.py -q`.

Commit: `feat(documents): expected_hash on both doors`

---

### Task 7: Gate, SDK zero-diff, CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything landed.
- Produces: the release section a master push requires.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 1 = 2

- [ ] **Step 1: SDK zero-diff check**

```bash
cd sdks && make generate && git diff --exit-code
```

Must produce no diff: the generator binds no document verb, so the additive fields regenerate nothing. A non-empty diff here means something unexpected moved — stop and investigate, do not commit generated churn.

- [ ] **Step 2: Full suite and gate**

```bash
cd backend && .venv/bin/python -m pytest -q     # full backend suite
cd .. && ./scripts/gate.sh                       # includes the single-revision assertion
```

Both green. The gate's alembic assertion is the proof the regeneration stayed one revision.

- [ ] **Step 3: CHANGELOG**

Add the round-trip entries under the next unreleased `## vN.N.N` section (create it if absent; **coordinate the version number with any parallel increment landing in the same master push** — the release workflow refuses a push whose derived version has no matching section): `documents.content` as the source of record (baseline regenerated), `include_content` on both get doors, `expected_hash` compare-and-set with 409/`hash_conflict`, `content_hash` echoed on put.

- [ ] **Step 4: CLAUDE.md** (cross-plan review m-13, 2026-09-02)

The Documents section (`CLAUDE.md`, "Documents (`app/services/document_door.py`, block channel)") is contract prose and this increment changes the contract: record that `documents.content` is the stored source of record, that both keyed reads take `include_content` (default off), that `put` takes an optional `expected_hash` compare-and-set answering 409 / `hash_conflict`, and that `PutResult` echoes `content_hash`. Increment 8's plan later edits this same section assuming these sentences are already there; without this step that edit lands on prose describing a store that cannot round-trip. Keep it to a few sentences in the section's existing voice — no new heading.

Commit: `docs(changelog): round-trip fidelity section` (chore-typed docs commits cut nothing on their own; the feat commits above are what derive the version). Fold the CLAUDE.md edit into the same commit or a `docs(claude):` one in the same push.

---

### Task 8: Deploy — the drop/recreate regeneration on this host

**Files:** none (operational; every command below is `docs/runbook-deployment.md`'s "Recovering from schema drift" procedure applied on purpose).

**Interfaces:**
- Consumes: the merged epic.
- Produces: the running instance increments 4-8 build on; the precondition increment 5's import states.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 3 = 4

**Do not deviate from this sequence.** The one silent failure this exists to prevent: `alembic upgrade head` on a database already stamped `0001` compares `0001` to `0001` and does nothing, so a deploy without the drop reports a clean migration against a schema missing the column — and `schema_guard` will then refuse every boot. There is no override flag, on purpose.

- [ ] **Step 1: Pre-flight — what is prod actually running?**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "SELECT value->>'sha' FROM config WHERE key='schema_baseline_sha';"
git show <pre-epic master ref>:backend/migrations/versions/0001_baseline.py | sha256sum
```

The two must match. A mismatch means prod is running a baseline that is not pre-epic master (this host has run unmerged branches before) — stop and reconcile what is deployed before dropping anything.

- [ ] **Step 2: Backup, then capture what a re-seed does NOT reproduce**

```bash
./scripts/backup.sh /root/darkmem-backups
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=llm_providers --column-inserts > /tmp/providers.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=llm_purpose_configs --column-inserts > /tmp/purposes.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=config --column-inserts | grep admin_password_hash > /tmp/admin.sql
```

**The runbook's three rows are NOT the full list for this deploy** (cross-plan review M-1, 2026-09-02). `docs/runbook-deployment.md:210-253` predates every row below, and this procedure drops the whole database, not just the schema. Capture these too, in the same step:

```bash
# The agent's MCP credential. api_keys is a table (0001_baseline.py:1166),
# so the drop destroys the row while /root/.claude.json keeps presenting the
# token -- every MCP call then answers 401 with nothing wrong on the client
# side. Increment 0 minted this key and no later task re-mints it.
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=api_keys --column-inserts > /tmp/api_keys.sql
# Operator-set config rows a re-seed does not reproduce: the armed research
# loop (armed on this host 2026-08-17 by owner ruling), feature flags, the
# verification ladder and its measurements, every per-job cron/config
# override, and -- if increment 6 landed first -- the backup destinations.
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=config --column-inserts \
  | grep -E "auto_research|feature_flags|verification_ladder|ladder_measurements|backup_destinations|'job:" \
  > /tmp/config_rows.sql
# Indexed repositories and their per-repo git tokens (git_token_<repo_id>).
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=repositories --column-inserts > /tmp/repos.sql
```

Restore these after the three LLM artifacts in Step 5. The greenfield ruling makes *data* disposable; it does not make this programme's own preconditions self-healing, and increment 0 is a manual owner procedure with no task that re-runs it. If any restore is judged not worth carrying, the alternative is explicit: re-run increment 0's mint-and-repoint procedure (`docs/superpowers/plans/2026-08-31-watchable-progress.md:31-51`) and re-arm `auto_research` through the settings door **after** Step 6, and say so in the deploy note. Silently losing the key is what this step exists to prevent.

Six artifacts, and the order below restores providers **before** purposes (`llm_purpose_configs.provider_name` is a NOT NULL FK). The full backup is the escape hatch: the drop discards every memory, event and research origin prod has accumulated (disposable by the greenfield ruling), and the runbook's "Restoring a data-only dump into a fresh database" section is the recorded route back if the owner ever wants that corpus — it is not part of this deploy.

- [ ] **Step 3: Build the new image BEFORE the drop**

```bash
./scripts/gate.sh && DARKMEM_PUSH=0 ./scripts/build-push.sh
```

`DARKMEM_PUSH=0` is not optional — publishing is CI's alone. Building first matters: if the *old* image were the one to boot against the recreated database, it would migrate the old baseline and stamp the old hash, and the new image would then refuse to start.

- [ ] **Step 4: Drop, recreate, boot the new image**

```bash
docker compose stop darkmem
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE darkmem;" -c "CREATE DATABASE darkmem OWNER darkmem;"
docker compose up -d
docker logs darkmem-prod-darkmem-1 2>&1 | grep -i 'schema baseline'   # expect "stamped"
```

The entrypoint migrates the regenerated baseline and `schema_guard` stamps its hash into the fresh database — the hash "moves" by construction, no code change involved.

- [ ] **Step 5: Restore the six artifacts, providers first, and verify both LLM invariants**

```bash
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/admin.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/providers.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/purposes.sql
# verification provider exclusivity — purposes_on_this_provider must be 1:
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "
  select p.purpose, p.model, v.api_kind, v.base_url,
         (select count(*) from llm_purpose_configs x
           where x.provider_name = v.name) as purposes_on_this_provider
    from llm_purpose_configs p join llm_providers v on v.name = p.provider_name
   where p.purpose = 'verification';"
# no purpose silently on vendor defaults — must return zero rows:
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "
  select purpose, params from llm_purpose_configs
   where params = '{}'::jsonb and purpose <> 'embedding';"
```

Then the three artifacts Step 2 added beyond the runbook's list (review M-1) — order does not matter among these, none carries a foreign key into the others:

```bash
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/api_keys.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/config_rows.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/repos.sql
```

Restoring — never re-seeding — is what keeps the qualified judge identity (`gpt-5.5` at `fd39e7b2c47fa375`, spanning both tables) and every purpose's `params`; `llm_seed.py` would overwrite all of it with Ollama presets, silently. The same logic is why `api_keys` is restored rather than re-minted: a re-mint means editing `/root/.claude.json` and every other client that holds the old token, and nothing reports that you forgot.

- [ ] **Step 6: Verify the deploy carried the change, not just started**

```bash
curl -s localhost:8000/health
curl -s localhost:8000/openapi.json | grep -o '"expected_hash"' | head -1   # the new field IS the proof
curl -s localhost:8000/openapi.json | grep -o '"include_content"' | head -1
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "\d documents" | grep ' content '
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "select key, value->>'last_status', value->>'last_error' from config
    where key like 'job:%' and value->>'last_status' <> 'ok';"
```

```bash
# Reachability, not just liveness (review M-1): the key the agent presents
# must still resolve. Anything other than 200 means the api_keys restore did
# not happen and every agent MCP call is answering 401.
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/mcp \
  -H "Authorization: Bearer $(grep -o 'dmk_[A-Za-z0-9_]*' /root/.claude.json | head -1)" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "select key from config where key in
     ('auto_research','feature_flags','verification_ladder');"
```

Compose reuses an image whose tag did not move, so a skipped build redeploys the old bits while reporting `Started` — the OpenAPI probe for the new fields is what rules that out. The job-status query is the one that would have caught the 2026-08-17 drift; run it. The `tools/list` probe is the one that would catch a lost API key, which no log or health check reports.

- [ ] **Step 7: The dev database**

The dev-compose Postgres (5433) `darkmem` database, if one exists there, is now behind the baseline: `schema_guard` will refuse the next dev-server start with the remedy in its message. That refusal is correct — drop and recreate it the same way when next needed (`psql -h localhost -p 5433 -U darkmem -d postgres -c "DROP DATABASE darkmem;" -c "CREATE DATABASE darkmem OWNER darkmem;"`, then `./scripts/start_dev_server.sh` migrates and stamps). Test databases self-reset via conftest; nothing to do.

---

## Rollback

- Tasks 1-6 are ordinary commits; revert in reverse order. Reverting Task 1 after any deploy means another drop/recreate (the stamp follows the file's content in both directions).
- Task 8 has no in-place rollback — that is what `schema_guard`'s no-override design means. The recovery from a bad deploy is the same procedure run again with the previous image: step 2's six `/tmp/*.sql` artifacts and the `scripts/backup.sh` dump are the materials. Keep all seven until the deploy is verified.
- The race-proof test (Task 4) is the tripwire against a future "simplification" of the CAS back into a read-then-write: it fails deterministically under that change. Do not weaken it to unblock a refactor; the refactor is what's wrong.

## Notes on scope

- **The spec's §5.3 SQL sketch is not what ships, and that is deliberate** (trust-the-code rule): the predicate rides `update_document`'s UPDATE rather than an `ON CONFLICT ... DO UPDATE` arm, because the writer resolves-then-splits (`document_ingest.py:210-244`) and the upsert shape would insert — not refuse — when a precondition names a vanished document. Same compare-and-set guarantee; honest missing-row edge. Recorded in Task 3's Approach line.
- **Gap the spec missed, closed here:** §5.3's caller must pass "the" current hash, but no wire surface served one — `content_hash` appears in no response model on either door. Task 6 adds it to `PutResult`/`DocumentPutResponse`/the MCP put payload. Without it the feature ships unusable (callers would have to client-side sha256 the content and know the algorithm).
- **m3 residue, resolved by construction, not by a backfill arm:** no deployed database can hold a NULL-content text document after Task 8, because every writer from Task 2 on stores content and the regeneration drops every database that predates it. The `UNCHANGED` path therefore repairs nothing and writes nothing (Task 2 Step 2 states the argument in the code). Bytes-filed drill documents store NULL deliberately.
- **~~Stale `$content` references in increment 5's plan~~ — withdrawn 2026-09-02 (cross-plan review m-6).** This note claimed `docs/superpowers/plans/2026-08-31-docs-corpus-import.md` lines 38, 226 and 318 still described the retired `$content` bridge. They do not: all three already read `documents.content` / `include_content`, and lines 27-32 record the bridge as cut. The note was stale and would have sent an increment-5 executor to read current text as historical. No `$content` reference exists in any plan; nothing to flag.
- **The batch ingest path (`ingest_documents` / `file_documents_isolated`) takes no `expected_hash`** on purpose: the corpus import is last-writer-wins re-runnable by design, which is §5.3's own "correct for a caller that genuinely owns the document" case.
- **`char_span` semantics:** now that the source is stored, spans index into `documents.content` exactly (they have always pointed at the original source, frontmatter and fences included — `document_parsers.py`'s contract, kept by increment 2's frontmatter task). Task 5's docstrings state it; no span code changes.
- **Not in scope:** version history (`document_revisions` — spec §5.4, deferred with the loss restated there), any UI (increment 4's), the project-index widening (M2, increment 4's), and any change to `documents.content_hash`'s role — it keeps being the change gate, unchanged.
