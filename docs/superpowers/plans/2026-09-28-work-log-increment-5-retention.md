# Work-log increment 5: retention — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily `worklog_cleanup` job erases closed, unretained workstreams (with their entries and vectors) once they have been closed longer than `retention_days` (default 90), journalling each erase first under the purge verb's strict contract.

**Architecture:** `app/services/worklog.py` gains `expire_next`, which locks the longest-closed eligible workstream with `FOR UPDATE SKIP LOCKED` and erases it through the same journal-then-delete helper the purge verb now shares. A new `app/services/worklog_cleanup.py` holds the job constants and a runner that calls `expire_next` once per transaction until nothing is eligible. `app/main.py` registers the job; CLAUDE.md's job counts and the roster guards move with it.

**Tech Stack:** Python 3.13, SQLAlchemy async (asyncpg), PostgreSQL 16, pytest (asyncio_mode = auto).

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** subagent — `claude --model sonnet --effort high` — all three tasks are heavy (totals 6, 6 and 5), so more than half are heavy.

**Plan review:** 2026-09-28 — dr-superpowers:judge-opus — executability 17 / coherence 17 / coverage 18 / assumptions 16 (round 1)

## Global Constraints

- The job key is `worklog_cleanup`, registered through the `WORKLOG_CLEANUP_JOB_KEY` constant; the roster goes 25 → 26 (spec §6).
- `config_schema` has exactly one field: `retention_days` (int, default 90, min 1) (spec §6). The plan adds `max=3650`, matching `llm_usage_cleanup`'s `retention_days`.
- Eligible means `state='closed'`, `retain = false` and `closed_at < now() - retention_days`. Open workstreams are never pruned, however old; retained ones are never pruned (spec §6).
- Each erase journals one `workstream_purged` per workstream under the purge verb's strict contract: journal first, read the row back, refuse to delete if it is not there (spec §6, §2; CLAUDE.md "Strict callers").
- Journal payloads carry the workstream key and counts, never entry text (CLAUDE.md, Work log; "Write-time minimisation is the standing rule").
- An append racing a retention delete either keeps the workstream or recreates it, never writes into a deleted parent (spec §10).
- Nothing in `app/services/worklog.py` commits: the caller owns the transaction (module docstring).
- Every work-log module stays off the memory pipeline and the vault (spec §7, `backend/tests/test_worklog_wall.py`).
- No schema change: `chk_workstreams_closed_at` already ties `closed_at` to `state='closed'`, and the entry and vector FKs already cascade.
- Run backend tests from `backend/` as `.venv/bin/python -m pytest`, always with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` and a Bash timeout. Never point pytest at production, and never run it without that variable: conftest drops the `public` schema of whatever test database it resolves, and the default is the controller's `darkmem_test`.
- The sweep spans every project, so the Task 1 and Task 2 tests assume they hold the only eligible workstreams in the test database (no other suite leaves a committed, closed, unretained workstream closed over a day ago); the Task 2 `factory` fixture asserts it at setup.
- The merge gate (`./scripts/gate.sh`) and the redeploy CLAUDE.md requires after a backend change belong to the controller at finishing, not to any task.
- If the dev Postgres is stopped, start only its service: `docker compose -f docker-compose.dev.yml up -d postgres` (repo root). Stop it again when the plan is done.
- `rg` is a shell function on this host: never pipe a file list into `xargs rg`.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative.

## Contracts

- **`worklog.expire_next(session: AsyncSession, *, retention_days: int, actor: str | None = None) -> int | None`** (Task 1), in `backend/app/services/worklog.py`, listed in `__all__`. Erases the eligible workstream with the oldest `closed_at` (id tie-break) and answers the number of entries it held, or `None` when no workstream is eligible or every eligible one is locked by another transaction. It does not commit. On a missing journal row it raises `worklog.WorklogJournalWriteFailed` and deletes nothing.
- **Retention journal row** (Task 1): `event_type="workstream_purged"`, `object_type="workstream"`, `object_id=<workstream id>`, `project=<workstream project>`, `actor=<the actor argument>`, `api_key_id=None`, `payload={"key": <workstream key>, "entries": <entry count>, "retention_days": <retention_days>}`. The purge verb's payload stays `{"key", "entries"}`.
- **`backend/app/services/worklog_cleanup.py`** (Task 2):
  - `WORKLOG_CLEANUP_JOB_KEY = "worklog_cleanup"`
  - `WORKLOG_CLEANUP_CRON = "15 5 * * *"`
  - `RETENTION_DAYS_DEFAULT = 90`
  - `WORKLOG_CLEANUP_CONFIG_SCHEMA: list[FieldDescriptor]`, one field, key `retention_days`
  - `make_worklog_cleanup_runner(app, session_factory: async_sessionmaker[AsyncSession])` returns an async runner answering `0` when nothing was erased, else `{"workstreams": int, "entries": int, "retention_days": int}`. It passes `actor=WORKLOG_CLEANUP_JOB_KEY` to `expire_next`.

## Assumptions (evidence)

- The purge verb's journal-then-delete body is `backend/app/services/worklog.py:347-382`, and its read-back statement `_PURGE_JOURNALED` is at `worklog.py:149-157` (read 2026-09-28).
- `chk_workstreams_closed_at CHECK ((state = 'closed') = (closed_at IS NOT NULL))` is at `backend/migrations/versions/0001_baseline.py:787-788` (read 2026-09-28).
- The two race tests at `backend/tests/test_worklog_service.py:299-341` use a hand-written `_RETENTION_DELETE` stand-in (`:268-271`) that waits on the append's lock; Task 1 retargets them at the real `expire_next`, whose `SKIP LOCKED` passes over a held row instead of waiting (read 2026-09-28).
- `test_the_claude_md_job_count_matches_what_boots` (`backend/tests/test_citation_reverifier.py:1120-1148`) derives the counts from `app/main.py`, and its `_NUMBER_WORDS` table (`:1111-1117`) stops at `twenty-five`, so Task 3 extends it (read 2026-09-28).
- `test_main_registers_the_full_direct_job_roster` pins the direct roster as a literal set (`backend/tests/test_code_deriver.py:1519-1528`) (read 2026-09-28).
- `app.services.job_registry`'s import closure reaches neither `app.services.pipeline` nor any `VAULT_WRITERS` module (ran `import_closure` from `tests/_reachability_scan.py` on 2026-09-28: empty intersection), so `worklog_cleanup` can join the wall's `WORKLOG_MODULES`.
- `FieldDescriptor(key, type="int", label, default, min, max, step, help)` is at `backend/app/services/job_registry.py:89-98`; `JobRegistry.load_config` / `save_config` / `get` are at `:204`, `:221`, `:195` (read 2026-09-28).
- The runner-through-a-registry test pattern is `backend/tests/test_usage_cleanup.py:38-78` (read 2026-09-28).
- No other suite pins the job count: `rg "== 25|len(.*jobs.*) =="` over `backend/tests` and `frontend/src` found only an unrelated `batch_size == 25` (2026-09-28). The frontend demo's `jobs.json` lists a subset of jobs (it omits `page_attachment_cleanup`), so it is not extended; demo fixtures are increment 6's (spec §8).
- `workstream_purged` is already in `EVENT_TYPES` (`backend/app/services/events.py:256`) and classified on the frontend since increment 1, so no taxonomy change is needed.
- The cron `15 5 * * *` starts after both backup producers start (the 03:30 timer and the 04:30 `backup_ship`, CLAUDE.md Jobs). It can still overlap a long `backup_ship` run (`BACKUP_SHIP_MAX_RUN_SECONDS = 21600`, `backend/app/services/backup_ship.py:818`); that is harmless, because `pg_dump` reads one snapshot.
- The **Execution** line names the controller session; each task's **Implementer** line names the subagent that session dispatches for it.
- The external executor lane is not offered: its gate admits only tasks with risk ≤ 1, and every task here carries risk 2 or 3.
- The v1.13.0 CHANGELOG section is still `— unreleased` on 2026-09-28 (`CHANGELOG.md:7`; `origin/master` is 10 commits behind `master`). Task 3 Step 6 handles the case where it has been released by then.

## Task index

1. Retention sweep in the work-log service
2. The worklog_cleanup job runner
3. Register the job and move the roster

---

### Task 1: Retention sweep in the work-log service

**Files:**
- Modify: `backend/app/services/worklog.py:35-63` (`__all__`), `:145-157` (new statement beside `_PURGE_JOURNALED`), `:347-382` (`purge_workstream`)
- Test: `backend/tests/test_worklog_service.py` (new tests after `test_no_entry_text_reaches_the_journal`; race section `:267-341` retargeted)
- Test: `backend/tests/test_worklog_embeddings.py` (one test after `test_purging_a_workstream_takes_its_vectors`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `worklog.expire_next` and the retention journal row (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing service tests**

In `backend/tests/test_worklog_service.py`, add these after `test_no_entry_text_reaches_the_journal` (the file already imports `pytest`, `select`, `text`, `Workstream` and `worklog`, and defines `_append` and `_events`):

```python
async def _close(session, workstream_id, *, days_ago, retain=False):
    await worklog.update_workstream(session, workstream_id, state="closed", retain=retain)
    await session.execute(
        text(
            "UPDATE workstreams SET closed_at = now() - make_interval(days => CAST(:d AS integer)) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"d": days_ago, "id": str(workstream_id)},
    )


async def test_expire_next_erases_the_longest_closed_first_and_journals_it(session):
    older_id = (await _append(session, key="older", entries=[
        {"kind": "note", "body": "a"}, {"kind": "note", "body": "b"},
    ])).workstream.id
    newer_id = (await _append(session, key="newer")).workstream.id
    await _close(session, newer_id, days_ago=5)
    await _close(session, older_id, days_ago=10)

    assert await worklog.expire_next(session, retention_days=1, actor="worklog_cleanup") == 2
    assert (await session.execute(text("SELECT key FROM workstreams"))).scalars().all() == ["newer"]
    assert (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(older_id)},
    )).scalar_one() == 0
    row = (await session.execute(
        text(
            "SELECT actor, payload FROM events WHERE event_type = 'workstream_purged' "
            "AND object_type = 'workstream' AND object_id = CAST(:w AS uuid)"
        ),
        {"w": str(older_id)},
    )).one()
    assert row.actor == "worklog_cleanup"
    assert row.payload == {"key": "older", "entries": 2, "retention_days": 1}

    assert await worklog.expire_next(session, retention_days=1) == 1
    assert await worklog.expire_next(session, retention_days=1) is None


async def test_expire_next_keeps_open_retained_and_recent_workstreams(session):
    open_id = (await _append(session, key="open")).workstream.id
    retained_id = (await _append(session, key="retained")).workstream.id
    recent_id = (await _append(session, key="recent")).workstream.id
    await session.execute(
        text(
            "UPDATE workstreams SET created_at = now() - interval '400 days', "
            "last_entry_at = now() - interval '400 days' WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(open_id)},
    )
    await _close(session, retained_id, days_ago=400, retain=True)
    await _close(session, recent_id, days_ago=1)

    assert await worklog.expire_next(session, retention_days=2) is None
    assert sorted((await session.execute(text("SELECT key FROM workstreams"))).scalars().all()) == [
        "open", "recent", "retained",
    ]


@pytest.mark.parametrize("reported", [False, True])
async def test_expire_next_refuses_unless_the_journal_row_is_really_there(session, monkeypatch, reported):
    ws_id = (await _append(session)).workstream.id
    await _close(session, ws_id, days_ago=10)

    async def writes_nothing(*args, **kwargs):
        return reported

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await worklog.expire_next(session, retention_days=1)
    still = (await session.execute(select(Workstream).where(Workstream.id == ws_id))).scalar_one_or_none()
    assert still is not None
    entries = (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(ws_id)},
    )).scalar_one()
    assert entries == 1
```

- [ ] **Step 2: Retarget the two race tests at the real sweep**

In the race section of `backend/tests/test_worklog_service.py`, delete the `_RETENTION_DELETE = text(...)` statement (`:268-271`, the four lines after `RACE_PROJECT = "worklog-race"`), then replace `_closed_race_workstream` and the two tests `test_an_append_holding_the_lock_survives_a_retention_delete` and `test_an_append_behind_a_committed_delete_recreates_the_workstream` with:

```python
async def _closed_race_workstream(factory) -> uuid.UUID:
    async with factory() as setup:
        result = await worklog.append(
            setup, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "n"}],
        )
        await worklog.update_workstream(setup, result.workstream.id, state="closed")
        await setup.execute(
            text("UPDATE workstreams SET closed_at = now() - interval '2 days' WHERE id = CAST(:id AS uuid)"),
            {"id": str(result.workstream.id)},
        )
        await setup.commit()
        return result.workstream.id


async def test_the_sweep_passes_over_a_workstream_an_append_holds(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as appender, committed() as sweeper:
        await worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        )
        swept = await asyncio.wait_for(worklog.expire_next(sweeper, retention_days=1), timeout=5)
        assert swept is None, "the sweep must skip a row an append holds, neither waiting nor deleting"
        await sweeper.rollback()
        await appender.commit()
    async with committed() as check:
        state = (await check.execute(
            text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"), {"id": str(ws_id)}
        )).scalar_one()
    assert state == "open"


async def test_an_append_behind_a_committed_sweep_recreates_the_workstream(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as sweeper, committed() as appender:
        assert await worklog.expire_next(sweeper, retention_days=1) == 1
        append_task = asyncio.create_task(worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        ))
        await asyncio.sleep(0.3)
        assert not append_task.done(), "the append must wait on the sweep's row lock"
        await sweeper.commit()
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

Keep the section's header comment, `RACE_PROJECT`, and the `committed` fixture unchanged.

- [ ] **Step 3: Write the failing vector-cascade test**

In `backend/tests/test_worklog_embeddings.py`, add after `test_purging_a_workstream_takes_its_vectors`:

```python
async def test_the_retention_sweep_takes_a_workstreams_vectors(session):
    workstream, ids = await _append(session, "note")
    await embed_entries(session, RecordingEmbedder(), entry_ids=ids)
    assert set(await _vectors(session)) == set(ids)
    await worklog.update_workstream(session, workstream.id, state="closed")
    await session.execute(
        text("UPDATE workstreams SET closed_at = now() - interval '2 days' WHERE id = CAST(:id AS uuid)"),
        {"id": str(workstream.id)},
    )
    assert await worklog.expire_next(session, retention_days=1) == 1
    assert await _vectors(session) == {}
```

- [ ] **Step 4: Run the new tests to verify they fail**

Run (from `backend/`, Bash timeout 300000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_embeddings.py -k "expire_next or sweep"`
Expected: FAIL with `AttributeError: module 'app.services.worklog' has no attribute 'expire_next'` (7 tests, the parametrised one counting twice).

- [ ] **Step 5: Implement the shared helper and `expire_next`**

In `backend/app/services/worklog.py`:

(a) Add `"expire_next",` to `__all__`, between `"append",` and `"get_workstream",`.

(b) Directly after the `_PURGE_JOURNALED = text(...)` statement, add:

```python
# SKIP LOCKED: a workstream an append holds is being reopened, so the sweep
# passes it by rather than queueing behind the append and deleting nothing.
_NEXT_EXPIRED = text(
    """
    SELECT id FROM workstreams
    WHERE state = 'closed' AND NOT retain
      AND closed_at < now() - make_interval(days => CAST(:days AS integer))
    ORDER BY closed_at, id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
    """
)
```

(c) Replace the whole `purge_workstream` function (`:347-382`) with:

```python
async def _journal_then_delete(
    session: AsyncSession,
    workstream: Workstream,
    *,
    actor: str | None,
    api_key_id: UUID | None,
    extra: dict[str, Any] | None = None,
) -> int:
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == workstream.id)
    )).scalar_one()
    landed = await record_event(
        session, event_type="workstream_purged", object_type="workstream",
        object_id=workstream.id, project=workstream.project, actor=actor,
        api_key_id=api_key_id,
        payload={"key": workstream.key, "entries": count, **(extra or {})},
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
    return await _journal_then_delete(session, workstream, actor=actor, api_key_id=api_key_id)


async def expire_next(
    session: AsyncSession, *, retention_days: int, actor: str | None = None
) -> int | None:
    """Erase the longest-closed workstream past retention; None when none is eligible.

    Open and retained workstreams are never eligible, however old (spec §6).
    The erase keeps the purge verb's journal-first contract, and the caller
    commits one workstream at a time.
    """
    found = (await session.execute(
        _NEXT_EXPIRED, {"days": retention_days}
    )).scalar_one_or_none()
    if found is None:
        return None
    workstream = await get_workstream_by_id(session, found, for_update=True)
    return await _journal_then_delete(
        session, workstream, actor=actor, api_key_id=None,
        extra={"retention_days": retention_days},
    )
```

- [ ] **Step 6: Run the work-log suites to verify they pass**

Run (from `backend/`, Bash timeout 600000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_worklog_service.py tests/test_worklog_embeddings.py tests/test_worklog_rest.py tests/test_worklog_mcp.py tests/test_worklog_wall.py`
Expected: PASS, no failures (the purge tests prove the refactor kept the verb's behaviour).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/worklog.py backend/tests/test_worklog_service.py backend/tests/test_worklog_embeddings.py
git commit -m "feat(worklog): add the retention sweep

expire_next erases the longest-closed unretained workstream past the
window through the purge verb's journal-then-delete helper, skipping
a row an append holds. The race tests now drive the real sweep."
```

### Task 2: The worklog_cleanup job runner

**Files:**
- Create: `backend/app/services/worklog_cleanup.py`
- Create: `backend/tests/test_worklog_cleanup.py`
- Modify: `backend/tests/test_worklog_wall.py:15-21` (`WORKLOG_MODULES`)

**Interfaces:**
- Consumes: `worklog.expire_next` and the retention journal row (Contracts).
- Produces: `backend/app/services/worklog_cleanup.py` and its names (Contracts).

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing runner tests**

Create `backend/tests/test_worklog_cleanup.py`:

```python
"""worklog_cleanup: closed workstreams past the window go, journalled; open and retained ones stay.

The runner is reached through a JobRegistry rather than called bare: the
window lives in the job's config row, so a runner that read it from anywhere
else would pass a direct call and still ignore the operator in production.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.services import worklog
from app.services.job_registry import Job, JobRegistry
from app.services.worklog_cleanup import (
    RETENTION_DAYS_DEFAULT,
    WORKLOG_CLEANUP_CONFIG_SCHEMA,
    WORKLOG_CLEANUP_CRON,
    WORKLOG_CLEANUP_JOB_KEY,
    make_worklog_cleanup_runner,
)
from tests.conftest import test_engine

PROJECT = "worklog-cleanup"


@pytest_asyncio.fixture
async def factory(setup_database):
    made = async_sessionmaker(test_engine, expire_on_commit=False)
    async with made() as s:
        stray = (await s.execute(
            text(
                "SELECT count(*) FROM workstreams WHERE state = 'closed' AND NOT retain "
                "AND closed_at < now() - interval '1 day' AND project <> :p"
            ),
            {"p": PROJECT},
        )).scalar_one()
    assert stray == 0, "another suite left an eligible workstream committed; the sweep would erase it"
    yield made
    async with made() as cleanup:
        await cleanup.execute(text("DELETE FROM workstreams WHERE project = :p"), {"p": PROJECT})
        await cleanup.execute(text("DELETE FROM projects WHERE name = :p"), {"p": PROJECT})
        await cleanup.execute(
            text("DELETE FROM config WHERE key = :k"), {"k": f"job:{WORKLOG_CLEANUP_JOB_KEY}"}
        )
        await cleanup.commit()


@pytest_asyncio.fixture
async def run_cleanup(factory):
    registry = JobRegistry(factory)
    registry.register(Job(
        key=WORKLOG_CLEANUP_JOB_KEY,
        display_name="Work Log Retention",
        description="(test harness)",
        default_cron=WORKLOG_CLEANUP_CRON,
        min_interval_seconds=3600,
        runner=make_worklog_cleanup_runner(app, factory),
        config_schema=WORKLOG_CLEANUP_CONFIG_SCHEMA,
    ))
    previous = getattr(app.state, "job_registry", None)
    app.state.job_registry = registry

    async def run(retention_days: int | None = None):
        if retention_days is not None:
            cfg = await registry.load_config(WORKLOG_CLEANUP_JOB_KEY)
            cfg.config["retention_days"] = retention_days
            await registry.save_config(WORKLOG_CLEANUP_JOB_KEY, cfg)
        return await registry.get(WORKLOG_CLEANUP_JOB_KEY).runner()

    yield run

    app.state.job_registry = previous


async def _workstream(factory, key, *, closed_days_ago=None, retain=False, entries=1):
    """A committed workstream; closed that many days ago when closed_days_ago is given."""
    async with factory() as s:
        result = await worklog.append(
            s, project=PROJECT, key=key, run_key="r",
            entries=[{"kind": "note", "body": f"{key} {i}"} for i in range(entries)],
        )
        ws_id = result.workstream.id
        if closed_days_ago is not None:
            await worklog.update_workstream(s, ws_id, state="closed", retain=retain)
            await s.execute(
                text(
                    "UPDATE workstreams SET closed_at = now() - make_interval(days => CAST(:d AS integer)) "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"d": closed_days_ago, "id": str(ws_id)},
            )
        await s.commit()
        return ws_id


async def _keys(factory) -> list[str]:
    async with factory() as s:
        rows = await s.execute(
            text("SELECT key FROM workstreams WHERE project = :p ORDER BY key"), {"p": PROJECT}
        )
        return list(rows.scalars().all())


def test_the_schema_is_one_retention_window_defaulting_to_ninety_days():
    assert WORKLOG_CLEANUP_JOB_KEY == "worklog_cleanup"
    assert RETENTION_DAYS_DEFAULT == 90
    [field] = WORKLOG_CLEANUP_CONFIG_SCHEMA
    assert (field.key, field.default, field.min) == ("retention_days", 90, 1)


async def test_the_default_window_is_ninety_days(factory, run_cleanup):
    await _workstream(factory, "expired", closed_days_ago=91, entries=2)
    await _workstream(factory, "inside", closed_days_ago=89)
    assert await run_cleanup() == {"workstreams": 1, "entries": 2, "retention_days": 90}
    assert await _keys(factory) == ["inside"]


async def test_the_operator_window_is_honoured_not_the_default(factory, run_cleanup):
    await _workstream(factory, "three-days", closed_days_ago=3)
    await _workstream(factory, "one-day", closed_days_ago=1)
    result = await run_cleanup(retention_days=2)
    assert result["workstreams"] == 1
    assert result["retention_days"] == 2
    assert await _keys(factory) == ["one-day"]


async def test_one_sweep_takes_every_expired_workstream(factory, run_cleanup):
    for key in ("a", "b", "c"):
        await _workstream(factory, key, closed_days_ago=10)
    result = await run_cleanup(retention_days=1)
    assert (result["workstreams"], result["entries"]) == (3, 3)
    assert await _keys(factory) == []


async def test_open_and_retained_workstreams_are_never_swept(factory, run_cleanup):
    await _workstream(factory, "open")
    await _workstream(factory, "retained", closed_days_ago=400, retain=True)
    assert await run_cleanup(retention_days=1) == 0
    assert await _keys(factory) == ["open", "retained"]


async def test_each_erase_is_journalled_by_the_job(factory, run_cleanup):
    ws_id = await _workstream(factory, "journalled", closed_days_ago=91)
    await run_cleanup()
    async with factory() as s:
        row = (await s.execute(
            text(
                "SELECT actor, payload FROM events WHERE event_type = 'workstream_purged' "
                "AND object_type = 'workstream' AND object_id = CAST(:w AS uuid)"
            ),
            {"w": str(ws_id)},
        )).one()
    assert row.actor == WORKLOG_CLEANUP_JOB_KEY
    assert row.payload == {"key": "journalled", "entries": 1, "retention_days": 90}


async def test_a_journal_failure_stops_the_sweep_and_keeps_the_workstream(factory, run_cleanup, monkeypatch):
    await _workstream(factory, "kept", closed_days_ago=91)

    async def writes_nothing(*args, **kwargs):
        return False

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await run_cleanup()
    assert await _keys(factory) == ["kept"]
```

- [ ] **Step 2: Put the new module inside the wall**

In `backend/tests/test_worklog_wall.py`, add `"app.services.worklog_cleanup",` to `WORKLOG_MODULES`, after `"app.services.worklog_embeddings",`:

```python
WORKLOG_MODULES = frozenset({
    "app.services.worklog",
    "app.services.worklog_embeddings",
    "app.services.worklog_cleanup",
    "app.models.worklog",
    "app.schemas.worklog",
    "app.api.routes.worklog",
})
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (from `backend/`, Bash timeout 300000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_worklog_cleanup.py tests/test_worklog_wall.py`
Expected: FAIL — `test_worklog_cleanup.py` errors at collection with `ModuleNotFoundError: No module named 'app.services.worklog_cleanup'`, `test_every_scan_seed_resolves_to_a_file` fails with `app.services.worklog_cleanup moved — re-point the wall`, and the `app.services.worklog_cleanup` cases of `test_no_work_log_module_can_write_or_promote_a_fact`, `test_no_work_log_module_reads_a_memory_table` and `test_no_work_log_module_names_the_fact_store` fail with `AttributeError: 'NoneType' object has no attribute 'read_text'`.

- [ ] **Step 4: Write the runner module**

Create `backend/app/services/worklog_cleanup.py`:

```python
"""Daily retention for the work log (spec §6).

Closed workstreams past the window go, their entries and vectors with them
through the cascade; open and retained ones stay however old. One transaction
per workstream, so a journal failure stops the sweep with every earlier erase
journalled and committed and nothing of the failed one removed.
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services import worklog
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

WORKLOG_CLEANUP_JOB_KEY = "worklog_cleanup"
# Nightly, after both backup producers start (03:30 timer, 04:30 backup_ship).
# Overlapping a long backup_ship run is harmless: pg_dump reads one snapshot.
WORKLOG_CLEANUP_CRON = "15 5 * * *"
RETENTION_DAYS_DEFAULT = 90

WORKLOG_CLEANUP_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="retention_days", label="Retention (days)",
        default=RETENTION_DAYS_DEFAULT, min=1, max=3650,
        help="A closed workstream is deleted with its entries once it has been "
             "closed this long. Open workstreams and those marked retain are "
             "never deleted.",
    ),
]


def make_worklog_cleanup_runner(app, session_factory: async_sessionmaker[AsyncSession]):
    async def run() -> dict | int:
        registry = getattr(app.state, "job_registry", None)
        retention = RETENTION_DAYS_DEFAULT
        if registry is not None:
            cfg = await registry.load_config(WORKLOG_CLEANUP_JOB_KEY)
            retention = int(cfg.config.get("retention_days", RETENTION_DAYS_DEFAULT))

        workstreams = entries = 0
        while True:
            async with session_factory() as session:
                removed = await worklog.expire_next(
                    session, retention_days=retention, actor=WORKLOG_CLEANUP_JOB_KEY,
                )
                if removed is None:
                    break
                await session.commit()
            workstreams += 1
            entries += removed

        if not workstreams:
            # 0, not {}: a nightly sweep with nothing to erase writes no job_runs row.
            return 0
        logger.info(
            "worklog_cleanup: erased %s workstream(s), %s entr(ies), closed over %s days",
            workstreams, entries, retention,
        )
        return {"workstreams": workstreams, "entries": entries, "retention_days": retention}
    return run
```

- [ ] **Step 5: Run the tests to verify they pass**

Run (from `backend/`, Bash timeout 300000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_worklog_cleanup.py tests/test_worklog_wall.py`
Expected: PASS, no failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/worklog_cleanup.py backend/tests/test_worklog_cleanup.py backend/tests/test_worklog_wall.py
git commit -m "feat(worklog): add the worklog_cleanup runner

Calls expire_next one transaction at a time until nothing is eligible,
reading retention_days from the job's config row."
```

### Task 3: Register the job and move the roster

**Files:**
- Modify: `backend/app/main.py:388-389` (after the `page_attachment_cleanup` registration)
- Modify: `backend/tests/test_code_deriver.py:1519-1528` (expected roster)
- Modify: `backend/tests/test_citation_reverifier.py:1111-1117` (`_NUMBER_WORDS`)
- Modify: `CLAUDE.md` (Jobs counts and list; Events journal strict callers; Work log section)
- Modify: `CHANGELOG.md` (the unreleased section)
- Modify: `docs/superpowers/specs/2026-09-23-work-log-lane-design.md:214-217` (§2 race paragraph)
- Test: `backend/tests/test_worklog_cleanup.py` (one wiring test appended)

**Interfaces:**
- Consumes: `backend/app/services/worklog_cleanup.py` and its names (Contracts).
- Produces: nothing consumed by another task.

**Items:** 1

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Move the roster guards first**

In `backend/tests/test_code_deriver.py`, in `test_main_registers_the_full_direct_job_roster`, add `"WORKLOG_CLEANUP_JOB_KEY",` to `expected` after `"PAGE_ATTACHMENT_CLEANUP_JOB_KEY",`:

```python
        "LLM_USAGE_CLEANUP_JOB_KEY", "BACKUP_SHIP_JOB_KEY",
        "PAGE_ATTACHMENT_CLEANUP_JOB_KEY", "WORKLOG_CLEANUP_JOB_KEY",
    }
```

In `backend/tests/test_citation_reverifier.py`, extend `_NUMBER_WORDS`' word list to reach twenty-six:

```python
_NUMBER_WORDS = {
    word: value
    for value, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
        "twenty twenty-one twenty-two twenty-three twenty-four twenty-five "
        "twenty-six".split()
    )
}
```

Append to `backend/tests/test_worklog_cleanup.py` (created by Task 2):

```python
def test_the_job_is_registered_with_its_runner_and_schema():
    import ast
    from pathlib import Path

    tree = ast.parse((Path(__file__).resolve().parent.parent / "app" / "main.py").read_text())
    keywords = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Job":
            kw = {k.arg: k.value for k in node.keywords}
            key = kw.get("key")
            if isinstance(key, ast.Name) and key.id == "WORKLOG_CLEANUP_JOB_KEY":
                keywords = kw
                break

    assert keywords is not None, "worklog_cleanup is not wired at boot"
    assert isinstance(keywords["config_schema"], ast.Name)
    assert keywords["config_schema"].id == "WORKLOG_CLEANUP_CONFIG_SCHEMA"
    assert isinstance(keywords["default_cron"], ast.Name)
    assert keywords["default_cron"].id == "WORKLOG_CLEANUP_CRON"
    runner = keywords["runner"]
    assert isinstance(runner, ast.Call) and isinstance(runner.func, ast.Name)
    assert runner.func.id == "make_worklog_cleanup_runner"
```

- [ ] **Step 2: Run the guards to verify the roster test fails**

Run (from `backend/`, Bash timeout 300000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_code_deriver.py::test_main_registers_the_full_direct_job_roster tests/test_citation_reverifier.py::test_the_claude_md_job_count_matches_what_boots tests/test_worklog_cleanup.py::test_the_job_is_registered_with_its_runner_and_schema`
Expected: `test_main_registers_the_full_direct_job_roster` FAILS with `missing={'WORKLOG_CLEANUP_JOB_KEY'}` and the wiring test FAILS with `worklog_cleanup is not wired at boot`; the count test still passes (nothing registered yet).

- [ ] **Step 3: Register the job**

In `backend/app/main.py`, directly after the `job_registry.register(Job(key=PAGE_ATTACHMENT_CLEANUP_JOB_KEY, ...))` call (it ends with `config_schema=PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,` and `))`) and before the `job_registry.register(Job(key=BACKUP_SHIP_JOB_KEY, ...))` call, insert:

```python

    from app.services.worklog_cleanup import (
        WORKLOG_CLEANUP_CONFIG_SCHEMA,
        WORKLOG_CLEANUP_CRON,
        WORKLOG_CLEANUP_JOB_KEY,
        make_worklog_cleanup_runner,
    )
    job_registry.register(Job(
        key=WORKLOG_CLEANUP_JOB_KEY,
        display_name="Work Log Retention",
        description=(
            "Deletes closed work-log workstreams, with their entries, once they "
            "have been closed longer than the retention window. Open "
            "workstreams and those marked retain are never deleted, however "
            "old. Each deletion is journalled before it happens."
        ),
        default_cron=WORKLOG_CLEANUP_CRON,
        min_interval_seconds=3600,
        runner=make_worklog_cleanup_runner(app, async_session_factory),
        config_schema=WORKLOG_CLEANUP_CONFIG_SCHEMA,
    ))
```

- [ ] **Step 4: Move CLAUDE.md's counts and prose**

Make these five exact replacements (1-4 in `CLAUDE.md` at the repository root, 5 in the spec):

1. `**Twenty-five** registered jobs` → `**Twenty-six** registered jobs`
2. The live-jobs bullet's head and tail:
   - `- **Nineteen live jobs:** ` → `- **Twenty live jobs:** `
   - `  \`page_attachment_cleanup\`.` (the bullet's last line) → `  \`page_attachment_cleanup\`, \`worklog_cleanup\`.`
3. In **Strict callers**, replace
   ```
   `worklog.purge_workstream` (`WorklogJournalWriteFailed`). The contract is a
   shape, not a shared type: block-channel modules are firewalled from the
   vault and mint their own exception. `contradiction_scan._journal` (reads its
   ```
   with
   ```
   `worklog._journal_then_delete`, behind the purge verb and the
   `worklog_cleanup` retention sweep (`WorklogJournalWriteFailed`). The
   contract is a shape, not a shared type: block-channel modules are
   firewalled from the vault and mint their own exception.
   `contradiction_scan._journal` (reads its
   ```
4. In **Work log**, replace
   ```
   payloads carry the workstream key and counts, never entry text. Nothing in
   the lane is extracted, ranked with memories or reachable from the vault.
   ```
   with
   ```
   payloads carry the workstream key and counts, never entry text. The daily
   `worklog_cleanup` job (`retention_days`, default 90) erases each closed,
   unretained workstream closed longer than that, one transaction each,
   through the purge's journal-first helper (payload adds `retention_days`);
   open and `retain` workstreams are never swept, and `SKIP LOCKED` passes
   over one an append holds. Nothing in the lane is extracted, ranked with
   memories or reachable from the vault.
   ```

5. In `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` §2, replace
   ```
   serialises on that row: if the append commits first, the delete's re-checked
   `state = 'closed'` predicate no longer matches and the workstream survives; if
   ```
   with
   ```
   serialises on that row: if the append holds or has committed it, the
   retention sweep's `state = 'closed'` predicate no longer matches, and the
   sweep passes over a row an append holds (`FOR UPDATE SKIP LOCKED`; amended
   2026-09-28), so the workstream survives; if
   ```

- [ ] **Step 5: Run the guards to verify they pass**

Run (from `backend/`, Bash timeout 300000):
`TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_code_deriver.py tests/test_citation_reverifier.py tests/test_dream_jobs.py tests/test_jobs_route.py tests/test_job_registry.py tests/test_worklog_cleanup.py tests/test_worklog_wall.py`
Expected: PASS, no failures.

- [ ] **Step 6: Record the change in the changelog**

`git fetch --tags -q origin` (repo root), then read the top of `CHANGELOG.md`. If the newest `## v…` heading ends in `— unreleased`, add the bullet below as the last item of that section's `### Added` list, and append the sentence ` Closed work logs are now pruned after 90 days.` to that section's bold-summary paragraph (for v1.13.0, after `but its answer now says so.`). If the newest heading carries a date instead (it was released meanwhile), insert a new section directly above it headed `## v<that version with the minor part raised by one and the patch part 0> — unreleased` (for v1.13.0 that is `## v1.14.0 — unreleased`), with a one-line bold summary `**Old work logs are pruned.**`, then `### Added` and the bullet.

```markdown
- **Work-log retention.** A daily `worklog_cleanup` job deletes closed
  workstreams, with their entries and vectors, once they have been closed for
  90 days (`retention_days` on the Jobs page, minimum 1). Open workstreams
  and those marked `retain` are never deleted, however old. Each deletion
  journals `workstream_purged` first, with `retention_days` in its payload,
  and a journal failure stops the sweep without deleting.
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/tests/test_code_deriver.py backend/tests/test_citation_reverifier.py backend/tests/test_worklog_cleanup.py CLAUDE.md CHANGELOG.md docs/superpowers/specs/2026-09-23-work-log-lane-design.md
git commit -m "feat(jobs): register worklog_cleanup

The roster goes to twenty-six jobs, twenty of them live; CLAUDE.md and
the changelog record the retention rule."
```
