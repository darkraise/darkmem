# T0.12c — Baseline Part 3: Step-Level Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the single baseline revision — the four target-new partition templates as registry entries, the `(project, status)` pushdown index — and bring the application read path onto the target schema so that `pytest -q` is **green against a database built from the baseline alone**, which is where the floor T0.12a and T0.12b were exempt from is finally asserted.

**Architecture:** The baseline DDL is already correct and verified; what is missing is that application code still reads schema the target deliberately changed. Measured on 2026-07-27 against the finished T0.12b baseline: **108 failed, 500 passed, 1 skipped, 6 errors**, and *every* failure is application code, not a DDL defect. The work is therefore mostly a read-path migration, sequenced highest-leverage first: the ORM model is fixed before its call sites, because `select(Memory)` emits every mapped column, so one wrong column in `models/memory.py` fails ~73 tests across twenty-odd files at once.

**Tech Stack:** Python 3.13, SQLAlchemy 2 async + asyncpg, Alembic, FastAPI, pytest/pytest-asyncio. No new dependency.

## Global Constraints

- **`python` is not on PATH.** Use `/root/repositories/darkmem/backend/.venv/bin/python`, and run backend commands from `backend/`.
- **`psql` is not on the host.** Reach Postgres through `docker exec darkmem-postgres-1 psql -U darkmem -d <db> -c "…"`. `darkmem` is **write-forbidden**; `darkmem_test` belongs to pytest; `darkmem_bench` belongs to benchlib. This plan uses `darkmem_baseline_check`, created and dropped inside the tasks that need it.
- **One revision, always.** Every task ends with `alembic heads` reporting exactly one head. The baseline is edited in place — **never** append a `0002` (doc 19 §2). A second head breaks `conftest.py` and `benchlib/bench_db.py`, which both shell out to `alembic upgrade head`.
- **Schema changes edit `backend/migrations/versions/0001_baseline.py`** and are re-verified by dropping and rebuilding a scratch database, never by an incremental `ALTER` applied by hand.
- **Plain SQL only in the migration.** Doc 19 §2 binds every table, constraint, index and trigger to stay expressible as plain SQL so the deferred .NET port replays it through DbUp mechanically. Use `op.execute` with SQL strings; do not introduce `op.create_table`.
- **The inventory is the work order.** `docs/planning/baseline-schema-inventory.md` fixes every object and its disposition. A divergence between this plan and that document is a defect in one of them — reconcile, do not improvise.
- **Kill every process you start.** Drop every scratch database in the task that created it.
- **Branch:** `feat/e0-lane-c-baseline`, off the epic branch. T0.12a–c merge as one atomic unit only once this task is green (runbook §6).

## Two scope decisions this plan makes, with their reasons

Both were located by measurement while scoping, and both are the kind of call that would otherwise be made silently by whoever hits it first.

**1. The `llm_` rename stops at the ORM attribute. The wire contract keeps its names.** Doc 04 §3.1 renames the *columns* (`llm_classified_type → classified_type`, and `summary`/`emotions`/`flags`). It says nothing about the REST payload, which is doc 12's. `MemoryResponse` and `serialize_memory` currently emit `llm_*` keys, and **`frontend/src` reads them in 61 places**. T0.12c's bar is the **backend** suite; renaming the wire fields would break the frontend build, which this task does not own and cannot verify. So the response builders map the new attribute onto the old wire key, and the API rename gets its own owner (Task 6 records it as a finding for the contract task, T1.42b).

**2. `audit_log` is retired by *moving* its writes to `events`, not by deleting them.** `audit_log` is not only a memory-operation log — `app/api/routes/auth.py` writes `auth_login_success`, `auth_logout`, `auth_password_change` and setup rows, and `GET /api/v1/auth/audit` reads them back as the operator's **security** audit trail (brute-force attempts, surprise password changes). Simply dropping the writer would delete a shipped security feature and leave a blind window until T1.07's events writer lands in E1 — a regression doc 18 would not sanction. `events` already exists as of T0.12b, and doc 04 §8.1 fixes it as "the sole audit substrate **from day one**", so this task lands a **narrow** auth-and-pipeline events writer. T1.07 still owns the general journaling convention and T1.09 still owns retiring the reads onto `/events`; this task only keeps the lights on. Task 6 records the overlap.

## File structure

| File | Responsibility | Task |
|---|---|---|
| `backend/app/models/memory.py` | ORM mirror of `memories` — the four renamed attributes | 1 |
| `backend/app/schemas/memory.py` | Wire contract — keeps `llm_*` field names | 1 |
| `backend/app/api/routes/memories.py`, `backend/app/utils/serialization.py` | Map new attribute → old wire key | 1 |
| `backend/app/services/pipeline.py` | Phase-5 enrichment writes | 1 |
| `backend/tests/test_merged_extraction.py` | Raw-SQL assertions on the renamed columns | 1 |
| `backend/app/services/events.py` *(new)* | The narrow `record_event` writer over `events` | 2 |
| `backend/app/repositories/relational.py` | `PostgresAuditRepository.log` → `events` | 2 |
| `backend/app/api/routes/auth.py`, `analytics.py`, `backend/app/services/analytics.py` | Audit reads → `events` / `pipeline_failures` | 2 |
| `backend/app/models/audit.py`, `backend/app/models/__init__.py` | Delete the `AuditLog` model | 2 |
| `backend/app/models/llm_config.py` | Drop `LLMProvider`/`LLMProfile`/`MLProfile` and the three FK columns | 3 |
| `backend/app/services/config.py`, `backend/app/api/routes/config.py`, `setup.py`, `config_llm_registry.py` | Retire the indirection read path | 3 |
| `backend/app/services/embedder_registry.py` | Four new `_TABLE_TEMPLATES` / `_AUX_INDEXES` entries | 4 |
| `backend/migrations/versions/0001_baseline.py` | The `(project, status)` pushdown index | 5 |

---

### Task 1: The `llm_` rename — ORM attribute in, wire contract unchanged

**Files:**
- Modify: `backend/app/models/memory.py:51-54`
- Modify: `backend/app/schemas/memory.py:49-52`
- Modify: `backend/app/api/routes/memories.py:29-32`
- Modify: `backend/app/utils/serialization.py:16-19`
- Modify: `backend/app/services/pipeline.py:360-363, 379-382`
- Test: `backend/tests/test_merged_extraction.py:119, 166-168, 216-217`

**Interfaces:**
- Consumes: the `memories` table as built by T0.12a — columns `classified_type`, `summary`, `emotions`, `flags`.
- Produces: `Memory.classified_type`, `Memory.summary`, `Memory.emotions`, `Memory.flags` as the ORM attribute names every later task uses. The **wire** keys stay `llm_classified_type`, `llm_summary`, `llm_emotions`, `llm_flags`.

**Why first:** `select(Memory)` emits every mapped column, so while `models/memory.py` names a column that no longer exists, *any* test touching a memory fails. This one file is ~73 of the 108 failures.

- [x] **Step 1: Run the targeted test to see the current failure**

```bash
cd /root/repositories/darkmem/backend
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_baseline_check;" -c "CREATE DATABASE darkmem_baseline_check;"
export CHECK_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_baseline_check
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_models.py -q
```

Expected: FAIL with `column memories.llm_classified_type does not exist`.

- [x] **Step 2: Rename the four ORM attributes**

In `backend/app/models/memory.py`, replace lines 51-54:

```python
    classified_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    flags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
```

`updated_at` keeps its `onupdate=func.now()` or loses it — either is correct now that `touch_updated_at` is authoritative in SQL (inventory F-20), and the model mirrors the SQL either way. Leave it; removing it is not this task's business.

- [x] **Step 3: Run the test to confirm the bulk failure is gone**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_models.py tests/test_repositories.py -q
```

Expected: PASS. If `test_repositories.py` still fails, read the error — it should no longer mention `llm_`.

- [x] **Step 4: Keep the wire contract stable at the response builders**

`backend/app/schemas/memory.py:49-52` is the **wire** shape and does **not** change — the field names stay `llm_classified_type`, `llm_summary`, `llm_emotions`, `llm_flags`. Only the values feeding them move. In `backend/app/api/routes/memories.py`, replace lines 29-32:

```python
        llm_classified_type=memory.classified_type,
        llm_summary=memory.summary,
        llm_emotions=memory.emotions,
        llm_flags=memory.flags,
```

and in `backend/app/utils/serialization.py`, replace lines 16-19:

```python
        "llm_classified_type": memory.classified_type,
        "llm_summary": memory.summary,
        "llm_emotions": memory.emotions,
        "llm_flags": memory.flags,
```

- [x] **Step 5: Move the pipeline's enrichment writes**

In `backend/app/services/pipeline.py`, the `payload[...]` keys at lines 360-363 feed the **websocket** payload, which is also a wire contract — leave those four keys named `llm_*`. Change only the ORM writes at lines 379-382:

```python
                                mem_record.classified_type = llm_classification.get("hall") or None
                                mem_record.summary = llm_classification.get("summary") or None
                                mem_record.emotions = llm_classification.get("emotions") or None
                                mem_record.flags = llm_classification.get("flags") or None
```

- [x] **Step 6: Update the raw-SQL test assertions**

`tests/test_merged_extraction.py` asserts on the columns directly. At line 119 the `text(...)` query selects the old names; change the projection and the attribute reads:

```python
            text("SELECT memory_type, classified_type, summary, emotions "
```

and at lines 166-168 and 216-217, `row.llm_classified_type` → `row.classified_type`, `row.llm_summary` → `row.summary`, `row.llm_emotions` → `row.emotions`.

- [x] **Step 7: Run the affected suites**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest \
  tests/test_models.py tests/test_repositories.py tests/test_merged_extraction.py \
  tests/test_api/test_memories.py tests/test_mcp.py tests/test_schema_v2_metadata.py -q
```

Expected: all pass. Then run the whole suite to see the remaining count:

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest -q 2>&1 | tail -3
```

Expected: roughly **35 failures remain** (was 108) — the `llm_providers` and `audit_log` groups, which Tasks 2 and 3 own. Record the real number; if it is materially different, stop and find out why before continuing.

- [x] **Step 8: Commit**

```bash
git add backend/app/models/memory.py backend/app/schemas/memory.py \
        backend/app/api/routes/memories.py backend/app/utils/serialization.py \
        backend/app/services/pipeline.py backend/tests/test_merged_extraction.py
git commit -m "refactor(memory): drop the llm_ prefix on the four enrichment columns

The ORM attribute and the DB column move to classified_type, summary,
emotions and flags per doc 04 s3.1. The REST and websocket payload keys
deliberately keep their llm_ names: frontend/src reads them in 61 places
and T0.12c's bar is the backend suite, so the wire rename needs its own
owner and its own frontend change.

Task: T0.12c"
```

---

### Task 2: Retire `audit_log` by moving its writes to `events`

**Files:**
- Create: `backend/app/services/events.py`
- Modify: `backend/app/repositories/relational.py:241-248`
- Modify: `backend/app/api/routes/auth.py:20, 40, 105, 120, 156, 209`
- Modify: `backend/app/api/routes/analytics.py:13, 90-92`
- Modify: `backend/app/services/analytics.py:8, 247-252`
- Delete: `backend/app/models/audit.py`; drop its two lines from `backend/app/models/__init__.py:3, 21`
- Test: `backend/tests/test_audit_endpoint.py`

**Interfaces:**
- Consumes: the `events` table from T0.12b — `(id, created_at, event_type, object_type, object_id, project, actor, api_key_id, source, payload)`, PK `(id, created_at)`, monthly `RANGE(created_at)` partitions.
- Produces: `async def record_event(session, *, event_type: str, object_type: str, object_id: uuid.UUID | None = None, project: str | None = None, actor: str | None = None, api_key_id: uuid.UUID | None = None, source: str | None = None, payload: dict | None = None) -> None` in `app/services/events.py`. **T1.07 generalises this**; it is deliberately narrow here.

**Scope note the implementer must not widen:** this task keeps an existing security feature alive on the new substrate. It does **not** build the journaling convention, the `/events` REST surface, or the calendar — those are T1.07 and T1.08.

- [x] **Step 1: Write the failing test for the writer**

Create `backend/tests/test_events_writer.py`:

```python
"""The narrow events writer that replaces audit_log's writes (T0.12c).

audit_log is dropped by the baseline (doc 04 §7/§8.1), but its rows were a
live security audit trail. This writer keeps that trail on the substrate
doc 04 §8.1 fixes as authoritative from day one.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.events import record_event


@pytest.mark.asyncio
async def test_record_event_writes_a_row(session):
    await record_event(
        session,
        event_type="auth_login_success",
        object_type="system",
        payload={"ip": "10.0.0.1"},
    )
    await session.commit()
    row = (
        await session.execute(
            text("SELECT event_type, object_type, payload FROM events "
                 "WHERE event_type = 'auth_login_success'")
        )
    ).one()
    assert row.event_type == "auth_login_success"
    assert row.object_type == "system"
    assert row.payload == {"ip": "10.0.0.1"}


@pytest.mark.asyncio
async def test_record_event_defaults_payload_to_empty_object(session):
    await record_event(session, event_type="auth_logout", object_type="system")
    await session.commit()
    payload = (
        await session.execute(
            text("SELECT payload FROM events WHERE event_type = 'auth_logout'")
        )
    ).scalar_one()
    assert payload == {}
```

- [x] **Step 2: Run it and confirm it fails**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_events_writer.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.events'`.

- [x] **Step 3: Write the writer**

Create `backend/app/services/events.py`:

```python
"""The append-only events writer.

Doc 04 §8.1 makes ``events`` the sole audit substrate from day one; this is
the narrow writer T0.12c needs to keep the security audit trail alive after
``audit_log`` is dropped. T1.07 owns the general journaling convention and
the rest of the event vocabulary.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    object_type: str,
    object_id: uuid.UUID | None = None,
    project: str | None = None,
    actor: str | None = None,
    api_key_id: uuid.UUID | None = None,
    source: str | None = None,
    payload: dict | None = None,
) -> None:
    # asyncpg cannot infer these parameter types through the partitioned
    # parent, so every one is cast explicitly (invariant 10).
    await session.execute(
        text(
            "INSERT INTO events "
            "(event_type, object_type, object_id, project, actor, api_key_id, source, payload) "
            "VALUES (:event_type, :object_type, CAST(:object_id AS uuid), :project, "
            ":actor, CAST(:api_key_id AS uuid), :source, CAST(:payload AS jsonb))"
        ),
        {
            "event_type": event_type,
            "object_type": object_type,
            "object_id": str(object_id) if object_id else None,
            "project": project,
            "actor": actor,
            "api_key_id": str(api_key_id) if api_key_id else None,
            "source": source,
            "payload": __import__("json").dumps(payload or {}),
        },
    )
```

Replace the `__import__("json")` with a module-level `import json` and `json.dumps(...)` — it is written inline here only to keep the snippet self-contained; the real file imports json at the top.

- [x] **Step 4: Run the test and confirm it passes**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_events_writer.py -q
```

Expected: 2 passed.

- [x] **Step 5: Point the audit repository at `events`**

In `backend/app/repositories/relational.py`, replace `PostgresAuditRepository.log` (lines 245-248):

```python
    async def log(self, action, memory_id=None, api_key_id=None, details=None):
        await record_event(
            self.session,
            event_type=action,
            object_type="memory" if memory_id else "system",
            object_id=memory_id,
            api_key_id=api_key_id,
            payload=details or {},
        )
```

Import `record_event` from `app.services.events` at the top of the file, and delete the now-unused `AuditLog` import.

- [x] **Step 6: Move the auth writes and the audit read**

In `backend/app/api/routes/auth.py`, replace each `session.add(AuditLog(action=..., details=...))` (lines 40, 105, 120, 156) with an awaited `record_event(session, event_type=..., object_type="system", payload=...)`, and rewrite the `select(AuditLog)` at line 209 as a select over `events` filtered on `event_type LIKE 'auth\\_%' OR event_type LIKE 'setup\\_%'`, ordered by `created_at DESC`. Keep the endpoint's response shape identical — it is an operator-facing contract and the tests assert on it. Delete the `AuditLog` import.

In `backend/app/api/routes/analytics.py:90-92` and `backend/app/services/analytics.py:247-252`, the two reads become:

```python
        # Unresolved pipeline failures are the honest count: pipeline_failures
        # is the per-memory failure substrate (invariant 14), which is strictly
        # better than counting audit rows that merely carried an error detail.
        error_stmt = (
            select(func.count())
            .select_from(PipelineFailure)
            .where(PipelineFailure.resolved_at.is_(None))
        )
```

- [x] **Step 7: Delete the model**

```bash
git rm backend/app/models/audit.py
```

Remove `from .audit import AuditLog` (line 3) and `"AuditLog",` (line 21) from `backend/app/models/__init__.py`. Update `tests/test_audit_endpoint.py` to import nothing from `app.models.audit` and to seed rows through `record_event` instead.

- [x] **Step 8: Run the affected suites**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest \
  tests/test_events_writer.py tests/test_audit_endpoint.py tests/test_auth_security.py \
  tests/test_api/test_analytics.py tests/test_login_rate_limit_route.py -q
```

Expected: all pass. `rg -n 'AuditLog|audit_log' backend/app/` must return **no matches**.

- [x] **Step 9: Commit**

```bash
git add -A backend/app backend/tests
git commit -m "refactor(audit): move audit_log's writes onto events

audit_log is dropped by the baseline (doc 04 s7/s8.1), but its rows were
a live security audit trail -- auth_login_success, auth_logout,
auth_password_change and the setup rows, read back by the admin-gated
GET /api/v1/auth/audit. Dropping the writer would have deleted a shipped
feature and left a blind window until T1.07.

Adds a narrow record_event writer over the events table T0.12b landed,
points the audit repository and the auth routes at it, and moves the
pipeline-error count onto pipeline_failures, which is the per-memory
failure substrate and a more honest source than counting audit rows.

T1.07 still owns the general journaling convention and T1.09 the read
retirement onto /events.

Task: T0.12c"
```

---

### Task 3: Retire the LLM provider/profile indirection from the read path

**Files:**
- Modify: `backend/app/models/llm_config.py` — delete the `LLMProvider`, `LLMProfile` and `MLProfile` classes and the three FK columns on `LLMPurposeConfigRow`; add `classifier_kind`
- Modify: `backend/app/services/config.py:8-9, 19-20, 46-80` — delete `get_llm_providers` / `get_llm_profiles`, resolve purposes inline
- Modify: `backend/app/api/routes/config.py:19, 128-185`
- Modify: `backend/app/api/routes/setup.py:36, 384-450`
- Delete: `backend/app/api/routes/config_llm_registry.py` and its router registration in `backend/app/main.py`
- Test: `backend/tests/test_llm_pipeline_config.py`, `backend/tests/test_setup_route.py`

**Interfaces:**
- Consumes: `llm_purpose_configs` as built by T0.12b — `(purpose PK, model, dimensions, reasoning, api_kind, base_url, api_key, params, classifier_kind, updated_at)`.
- Produces: purpose resolution that reads **one row and no joins**. `LLMPurposeConfigRow` gains `classifier_kind: Mapped[str | None]`.

**This is the task that most tempts scope creep.** T1.01 still owns the *designed* behaviour — one-query resolution asserted by a query-counting test, and the wizard's flattened finalize. This task only removes the dead indirection so the suite can run. If a step here starts designing purpose resolution, stop: that is T1.01.

- [x] **Step 1: Confirm the current failure**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_llm_pipeline_config.py -q 2>&1 | tail -5
```

Expected: errors mentioning `relation "llm_providers" does not exist`.

- [x] **Step 2: Cut the three model classes**

In `backend/app/models/llm_config.py`, delete the `LLMProvider`, `LLMProfile` and `MLProfile` classes entirely, and on `LLMPurposeConfigRow` delete the `provider_id`, `profile_id` and `ml_profile_id` columns and the `provider` column, then add:

```python
    classifier_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
```

Also delete the phantom `UniqueConstraint("purpose", name="uq_llm_purpose_configs_purpose")` from `__table_args__` — inventory §9.1 records that it was **never created in the database**, so removing it changes nothing and stops the next reader believing it exists.

- [x] **Step 3: Delete the registry route module**

```bash
git rm backend/app/api/routes/config_llm_registry.py
```

Remove its import and `include_router` call from `backend/app/main.py`. This is 630 lines of provider/profile/ml-profile management API whose backing tables no longer exist; doc 04 §7 removes "the profile-management UI" with them.

- [x] **Step 4: Collapse the service-layer resolution**

In `backend/app/services/config.py`, delete `get_llm_providers` and `get_llm_profiles` and the `LLMProvider` / `LLMProfileRow` imports, and make the purpose loader read `LLMPurposeConfigRow` alone — each row already carries `model`, `base_url`, `api_key`, `api_kind`, `params`, `dimensions` and `reasoning` inline. Update the module docstring at lines 8-9, which still advertises the two deleted functions.

- [x] **Step 5: Strip the indirection from the config and setup routes**

In `backend/app/api/routes/config.py`, delete the `provider_id_by_name` / `profile_id_by_name` / `ml_profile_id_by_name` lookups (lines 128-133) and the `ref` resolution that writes them onto the row (lines 163-185); a purpose update now assigns the inline fields directly. In `backend/app/api/routes/setup.py`, delete the provider and profile seeding loops (lines 384-416) and have the finalize step write the six purpose rows straight from `app/services/llm_seed.py`.

- [x] **Step 6: Update the two test modules**

`tests/test_llm_pipeline_config.py`'s `seeded_llm` fixture seeds `DEFAULT_PROVIDERS` + `DEFAULT_PROFILES`; delete the fixture and the six tests that exercise the providers/profiles UI (`test_llm_providers_seed_includes_known_vendors`, `test_llm_profiles_seed_covers_all_purposes`, `test_test_provider_rejects_embedding_when_unsupported`, `test_test_provider_ollama_strips_v1_for_native_path`, `test_provider_models_short_circuits_when_cloud_key_missing`, `test_test_provider_short_circuits_when_cloud_key_missing`) — they test a surface the target does not have. Keep every test that covers purpose settings, feature-flag toggles and the prompt override. In `tests/test_setup_route.py`, drop the provider/profile assertions from the four finalize tests and assert instead that six `llm_purpose_configs` rows exist with inline connection fields.

- [x] **Step 7: Run the affected suites**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest \
  tests/test_llm_pipeline_config.py tests/test_setup_route.py -q
```

Expected: all pass, no errors. Then `rg -n 'LLMProvider|MLProfile|provider_id|ml_profile_id' backend/app/` must return no matches outside comments.

- [x] **Step 8: Commit**

```bash
git add -A backend/app backend/tests
git commit -m "refactor(llm): retire the provider/profile/ml_profile indirection

darkmem is not an LLM proxy, so the *_ref indirection is gone from the
read path: the three model classes, the 630-line registry route module,
and the resolution helpers in services/config.py. Each purpose row
carries its connection inline and gains classifier_kind.

Also drops the ORM's uq_llm_purpose_configs_purpose, which inventory
s9.1 shows was never created in the database -- doc 04 s12 discusses
keeping or dropping a constraint that does not exist.

T1.01 still owns one-query resolution asserted by a query-counting test
and the wizard's flattened finalize.

Task: T0.12c"
```

---

### Task 4: The four target-new partition templates as registry entries

**Files:**
- Modify: `backend/app/services/embedder_registry.py:31-97`
- Test: `backend/tests/test_partition_templates.py` (create)

**Interfaces:**
- Consumes: `_TABLE_TEMPLATES: dict[str, str]` and `_AUX_INDEXES: dict[str, list[str]]`, keyed by logical parent name, with `{name}` and `{dims}` placeholders.
- Produces: eight parents in `_TABLE_TEMPLATES`. T0.14's boot-time reconciliation iterates them; T0.13 labels the four new ones inert.

**These are registry entries, not migration DDL** (inventory §6). Doc 19 §2 rejects static child-table DDL because the shape is fingerprint-parameterised. **Nothing in this task touches `0001_baseline.py`.**

- [x] **Step 1: Write the failing test**

Create `backend/tests/test_partition_templates.py`:

```python
"""The eight per-fingerprint parents exist as registry entries, not as DDL.

Inventory §6: doc 19 §2 rejects expressing child tables as static migrations
because their shape is parameterised by fingerprint. The four target-new
families land here as templates; T0.13 labels them inert and T0.14's
boot-time reconciliation creates them per registered fingerprint.
"""
from __future__ import annotations

from pathlib import Path

from app.services.embedder_registry import _AUX_INDEXES, _TABLE_TEMPLATES

EXPECTED_PARENTS = {
    "memory_embeddings",
    "entity_embeddings",
    "code_chunk_embeddings",
    "entity_embedding_cache",
    "block_embeddings",
    "relation_embeddings",
    "article_embeddings",
    "triple_embeddings",
}


def test_all_eight_parents_have_templates():
    assert set(_TABLE_TEMPLATES) == EXPECTED_PARENTS


def test_every_template_has_aux_indexes():
    assert set(_AUX_INDEXES) == EXPECTED_PARENTS


def test_every_template_is_parameterised_plain_sql():
    for parent, tmpl in _TABLE_TEMPLATES.items():
        assert "{name}" in tmpl, parent
        assert "{dims}" in tmpl, parent
        assert tmpl.lstrip().upper().startswith("CREATE TABLE IF NOT EXISTS"), parent


def test_triple_embeddings_does_not_cascade():
    # Facts are invalidate-not-delete (doc 04 §5.3/§8.3): a cascade would
    # destroy the history the fact layer exists to keep.
    tmpl = _TABLE_TEMPLATES["triple_embeddings"]
    assert "knowledge_triples(id)" in tmpl
    assert "ON DELETE CASCADE" not in tmpl


def test_relation_embeddings_cascades_on_the_real_relation_id():
    # No synthetic ids: strip-before-rewrite must kill the vector with the
    # relation rather than orphan it (doc 04 §5.3).
    tmpl = _TABLE_TEMPLATES["relation_embeddings"]
    assert "entity_relations(id) ON DELETE CASCADE" in tmpl


def test_no_migration_creates_a_child_table():
    root = Path(__file__).resolve().parent.parent / "migrations"
    for path in root.rglob("*.py"):
        src = path.read_text()
        for parent in EXPECTED_PARENTS:
            assert f"CREATE TABLE {parent}__" not in src
            assert f"CREATE TABLE IF NOT EXISTS {parent}__" not in src
```

- [x] **Step 2: Run it and confirm it fails**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_partition_templates.py -q
```

Expected: FAIL — `_TABLE_TEMPLATES` holds four parents, not eight.

- [x] **Step 3: Add the four templates**

In `backend/app/services/embedder_registry.py`, add to `_TABLE_TEMPLATES`:

```python
    "block_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " block_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (block_id, fingerprint)"
        ")"
    ),
    "relation_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " relation_id UUID NOT NULL REFERENCES entity_relations(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (relation_id, fingerprint)"
        ")"
    ),
    "article_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " article_id UUID NOT NULL REFERENCES knowledge_articles(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (article_id, fingerprint)"
        ")"
    ),
    # Template ships now; the WRITER is deferred behind a measured
    # pg_trgm-on-fact undercount (T2.33). No cascade: facts are
    # invalidate-not-delete, so a cascade would destroy history.
    "triple_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " fact_id UUID NOT NULL REFERENCES knowledge_triples(id),"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (fact_id, fingerprint)"
        ")"
    ),
```

and to `_AUX_INDEXES`:

```python
    "block_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_block_id ON {name} (block_id)",
    ],
    "relation_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_relation_id ON {name} (relation_id)",
    ],
    "article_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_article_id ON {name} (article_id)",
    ],
    "triple_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_fact_id ON {name} (fact_id)",
    ],
```

- [x] **Step 4: Run the test**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_partition_templates.py -q
```

Expected: 6 passed.

**Known consequence to check, not to fix here:** `block_embeddings` references `blocks(id)`, and `blocks` does not exist until T0.13. Registering a fingerprint before T0.13 will therefore fail on that one template. Run `tests/test_reembed_absent_partition.py` and `tests/test_embedder_registry*.py`; if they fail on a missing `blocks` relation, **stop and record it** — the fix is T0.13's ordering, not a template edit.

- [x] **Step 5: Commit**

```bash
git add backend/app/services/embedder_registry.py backend/tests/test_partition_templates.py
git commit -m "feat(registry): add the four target-new partition templates

block, relation, article and triple embeddings land as registry
entries, never as migration DDL -- doc 19 s2 rejects static child-table
DDL because the shape is parameterised by fingerprint. A test asserts
no migration creates a child table.

relation_embeddings keys on the real entity_relations.id with CASCADE
so strip-before-rewrite kills the vector with the relation;
triple_embeddings deliberately does NOT cascade, because facts are
invalidate-not-delete.

Task: T0.12c"
```

---

### Task 5: The `(project, status)` pushdown support index

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py` — add one index after the `memories` block
- Test: `backend/tests/test_pushdown_index.py` (create)

**Interfaces:**
- Consumes: `memories(project, status, is_archived)` from T0.12a.
- Produces: `ix_memories_project_live`, the one index change doc 04 §10 says the SQL filter-pushdown strictly requires.

Inventory §3.2 records the recommendation among doc 04 §10's three stated forms: the **partial** `WHERE status='active' AND is_archived=false`, because the pushed-down predicate's overwhelmingly common shape is "live rows in this project" and the partial index is the smallest of the three. The two full composites stay available if a later measurement wants `status` values other than `'active'`.

- [x] **Step 1: Write the failing test**

Create `backend/tests/test_pushdown_index.py`:

```python
"""The SQL filter-pushdown's one required index (doc 04 §10, inventory §3.2).

Honest caveat recorded with it: the SEMANTIC channel cannot use this index —
an HNSW scan applies the predicate as a post-scan filter over its candidate
stream — so this serves the keyword and direct-scan sides. The pushdown still
closes the isolation leak on every channel; only the plan differs.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_pushdown_index_exists_and_is_partial(session):
    row = (
        await session.execute(
            text("SELECT indexdef FROM pg_indexes "
                 "WHERE schemaname = 'public' AND indexname = 'ix_memories_project_live'")
        )
    ).scalar_one_or_none()
    assert row is not None, "the pushdown support index is missing"
    assert "project" in row
    assert "status = 'active'" in row
    assert "is_archived = false" in row
```

- [x] **Step 2: Run it and confirm it fails**

```bash
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_pushdown_index.py -q
```

Expected: FAIL on `the pushdown support index is missing`.

- [x] **Step 3: Add the index to the baseline**

In `backend/migrations/versions/0001_baseline.py`, immediately after the `ix_memories_fts` statement:

```python
    # The one index change the SQL filter-pushdown strictly requires
    # (doc 04 §10). Partial rather than a full composite: the pushed-down
    # predicate's common shape is "live rows in this project", and this is the
    # smallest of the three forms doc 04 offers. The semantic channel cannot
    # use it — an HNSW scan applies the predicate post-scan — so it serves the
    # keyword and direct-scan sides.
    op.execute(
        "CREATE INDEX ix_memories_project_live ON memories (project) "
        "WHERE status = 'active' AND is_archived = false"
    )
```

- [x] **Step 4: Rebuild the scratch database and run the test**

The baseline is edited in place, so it must be re-run from empty — never patched by hand:

```bash
cd /root/repositories/darkmem/backend
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_baseline_check;" -c "CREATE DATABASE darkmem_baseline_check;"
DATABASE_URL=$CHECK_URL ./.venv/bin/python -m alembic upgrade head
TEST_DATABASE_URL=$CHECK_URL ./.venv/bin/python -m pytest tests/test_pushdown_index.py -q
```

Expected: 1 passed.

- [x] **Step 5: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/tests/test_pushdown_index.py
git commit -m "feat(schema): add the (project, status) pushdown support index

Doc 04 s10 calls this the one index change the SQL filter-pushdown
strictly requires and leaves three forms open; the inventory recommends
the partial WHERE status='active' AND is_archived=false as the smallest
that serves the common 'live rows in this project' predicate.

Task: T0.12c"
```

---

### Task 6: Assert the floor, the single head, and reconcile the inventory

**Files:**
- Modify: `docs/planning/baseline-schema-inventory.md` — §10 findings this task produced
- No code changes; this task is the gate.

**Interfaces:**
- Consumes: everything above.
- Produces: the measured evidence T0.13, T0.14 and ultimately G-A depend on.

- [x] **Step 1: Rebuild from the baseline alone and run the whole suite**

```bash
cd /root/repositories/darkmem/backend
docker exec darkmem-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE IF EXISTS darkmem_baseline_check;" -c "CREATE DATABASE darkmem_baseline_check;"
export CHECK_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_baseline_check
DATABASE_URL=$CHECK_URL ./.venv/bin/python -m alembic upgrade head
TEST_DATABASE_URL=$CHECK_URL timeout 1500 ./.venv/bin/python -m pytest -q 2>&1 | tail -3
```

Expected: **0 failed**. The pre-work reading was `108 failed, 500 passed, 1 skipped, 6 errors`; the target is every one of those closed, with the passed count risen by roughly the failures fixed minus the tests Task 3 deliberately deleted. **Record the real numbers.** A task deleted a test only if this plan named it; if the passed count is lower than expected, find out which test vanished and why before claiming green.

- [x] **Step 2: Assert the single head**

```bash
cd /root/repositories/darkmem/backend
./.venv/bin/python -m alembic heads
./.venv/bin/python -m alembic history | wc -l
ls migrations/versions/
```

Expected: exactly one head (`0001 (head)`), one revision in the history, and `0001_baseline.py` as the only file. The six brownfield revisions went in T0.12a and nothing has re-chained behind the baseline since.

- [x] **Step 3: Re-verify the inventory's mechanical checks still hold**

```bash
cd /root/repositories/darkmem/docs/planning
/root/repositories/darkmem/backend/.venv/bin/python scripts/check_plan.py
```

Expected: `PLAN GREEN — 205 tasks, all structural claims verified`.

- [x] **Step 4: Record what this task discovered as findings**

Append to `docs/planning/baseline-schema-inventory.md` §10, tiered per runbook §5:

- **The REST/websocket `llm_*` field names outlive the column rename.** The wire contract keeps them while the columns do not, so the two now disagree by design. Needs an owner and a paired frontend change (61 hits in `frontend/src`) — recommend the contract task, T1.42b. **Tier 2.**
- **T0.12c landed a narrow `events` writer.** `record_event` in `app/services/events.py` exists so the security audit trail survives `audit_log`'s removal. T1.07's scope shrinks to generalising it and T1.09's to retiring the reads onto `/events`. **Tier 2.**
- **T0.12c deleted `config_llm_registry.py` and six provider/profile tests.** T1.01's remaining scope is one-query resolution plus the wizard finalize; T1.55's provider/profile UI has no backing surface. **Tier 2.**
- Any Task-4 finding about `block_embeddings` referencing `blocks` before T0.13 lands it.

- [x] **Step 5: Commit and hand off**

```bash
cd /root/repositories/darkmem
git add docs/planning/baseline-schema-inventory.md
git commit -m "docs(planning): record T0.12c's findings and the measured floor

Task: T0.12c"
```

The completion report states the **measured** floor numbers, not "green"; names every test this plan deliberately deleted and why; and carries the Tier-2 amendments the controller propagates to `E0-baseline-and-harness.md`, `E1-engine-core.md` and `progress.md`. T0.12a–c merge as one atomic unit only now (runbook §6).

---

## Self-Review

**Coverage against T0.12c's four acceptance checkboxes.**

| T0.12c "Done when" | Where it lands | How it is checked |
|---|---|---|
| All four templates present **as registry entries**, not as migration DDL | Task 4 | `test_partition_templates.py` asserts eight parents, plain-SQL shape, and that no migration creates a child table |
| The GIN index on `technologies` exists | Landed in T0.12a; re-asserted | Task 6 Step 1 rebuilds from the baseline alone; `ix_memories_technologies` is in `0001_baseline.py` |
| The **full backend suite passes** against a database built from the baseline alone | Tasks 1–3 close the 108 failures; Task 6 asserts | Task 6 Step 1, with the real numbers recorded |
| `alembic heads` still reports exactly one head | Task 6 Step 2 | `alembic heads` + one file in `migrations/versions/` |

**Placeholder scan.** No `TBD`, no "handle the rest", no "similar to Task N". The one inline shortcut — `__import__("json")` in Task 2 Step 3 — is called out in the same step with the correction. Every code step carries the actual code.

**Type consistency.** `record_event`'s signature is defined once in Task 2's Interfaces block and used unchanged in Steps 3, 5 and 6. The ORM attribute names introduced in Task 1 (`classified_type`, `summary`, `emotions`, `flags`) are the names Tasks 2–6 assume. `_TABLE_TEMPLATES` / `_AUX_INDEXES` keep their existing types (`dict[str, str]`, `dict[str, list[str]]`).

**Sizing.** Task 1 is S–M and closes ~73 of 108. Task 2 is M. Task 3 is the largest, M–L, and is the one with a named scope fence against absorbing T1.01. Tasks 4 and 5 are S. Task 6 is S and is verification only. No step is itself an `L`.

**Risk-first ordering.** The three risks judged largest: (1) *the ORM model failing everything at once* — Task 1, first, because one file is two-thirds of the failures; (2) *silently deleting a shipped security feature* — Task 2 moves `audit_log`'s writes to `events` rather than dropping them, which is why that task exists in this shape at all; (3) *Task 3 growing into T1.01* — fenced explicitly in its preamble and in its commit message.

**What this plan deliberately does not do.** It does not rename the REST or websocket field names (61 frontend hits, and T0.12c cannot verify the frontend). It does not build the `/events` REST surface, the journaling convention, or the calendar (T1.07, T1.08). It does not design purpose resolution (T1.01). It does not land `documents`/`blocks` or the `repo_ids[]` columns (T0.13), and it does not implement the boot-time reconciliation (T0.14).

## Known risks (surface during execution, not placeholders)

- **`block_embeddings` references `blocks`, which T0.13 has not created yet.** Registering a fingerprint between this task and T0.13 will fail on that template. Task 4 Step 4 says to detect it and stop rather than edit the template; the ordering fix belongs to T0.13.
- **Task 3's test deletions are irreversible judgement calls.** Six tests cover a provider/profile surface the target removes. If any of them turns out to cover behaviour the flattened config still needs, it must be rewritten against `llm_purpose_configs`, not deleted.
- **The auth audit endpoint's response shape is an operator contract.** Task 2 Step 6 rewrites its query but must keep the shape; `tests/test_audit_endpoint.py` is the guard, and it must be updated to seed through `record_event` without weakening its assertions.
- **The passed-count arithmetic in Task 6 is the honesty check.** "0 failed" is not sufficient evidence on its own — a deleted test also produces zero failures. The recorded passed count is what distinguishes fixing from hiding.
