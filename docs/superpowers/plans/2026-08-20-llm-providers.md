# LLM Provider Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the eight LLM purposes a shared, first-class `llm_providers` row for their connection details, so `api_kind` / `base_url` / `api_key` are configured once per vendor instead of eight times, and a credential rotation propagates with no re-apply step.

**Architecture:** A new `llm_providers` table keyed by name; `llm_purpose_configs` drops its three inline connection columns and gains a NOT NULL `provider_name` FK. `get_llm_config` becomes one SELECT with one JOIN and **returns the same flat `LLMPurposeConfig` it returns today**, so every consumer — orchestrator, quirks, judge, health check, benchlib — is untouched. The schema walks in additively across four tasks so the suite stays green at every commit.

**Tech Stack:** FastAPI + SQLAlchemy 2 async + Alembic + Postgres 16/pgvector (backend); React 19 + TanStack Router/Query + darkraise-ui + vitest (frontend); pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-08-20-llm-providers-design.md` — read it before Task 1. This plan implements it; where they disagree, the spec wins and the plan is wrong.

## Global Constraints

- **The schema is ONE revision, `backend/migrations/versions/0001_baseline.py`, regenerated in place.** Never append a `0002`. `./scripts/gate.sh` asserts exactly one revision.
- **Claim the baseline lane before Task 1.** `0001_baseline.py` is a single shared mutable file; two lanes editing it conflict every time (CLAUDE.md).
- Backend tests run from `backend/`: `python -m pytest -q`. conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` (default `postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test`), then runs `DROP SCHEMA public CASCADE` + `alembic upgrade head` — so **every baseline edit is picked up automatically by the next test run**. Never point it at a real database.
- Parallel lanes: `darkmem_test_2` … `darkmem_test_5` exist. Give each dispatched lane its own via `TEST_DATABASE_URL`; keep `darkmem_test` for the controller.
- Frontend from `frontend/`: `npm run typecheck` (= `tsc -b`; plain `tsc` misses project refs), `npm test` (vitest), `npm run build`. `npm run lint` is advisory.
- **The resolved `LLMPurposeConfig` object must not change shape.** `benchlib/caching_llm.py:32` and `verification_judge.py:200` both hash `model`, `base_url`, `api_kind`, `dimensions`, `reasoning`, `params` off it. A shape change silently invalidates every benchlib cache entry and un-qualifies the judge.
- `api_kind` stays the sole vendor axis. No call site may compare it to a vendor name — an AST scan (`tests/test_api_kind_dispatch.py:265`) fails the build if one does.
- Commit style: `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period. English only.
- Comments: only where the WHY is non-obvious. Never explain WHAT the code does. Never reference a task id in a code comment.
- **Do not run `./scripts/gate.sh --full`** during implementation (it makes live LLM calls and boots stacks). Plain `./scripts/gate.sh` at Task 12 only.

---

## File Structure

**Created**
- `backend/app/models/llm_provider.py` — the `LLMProviderRow` ORM model, one responsibility.
- `backend/app/api/routes/llm_providers.py` — provider CRUD + the two probe endpoints. A separate router module rather than growing `config.py` (already 914 lines).
- `backend/app/services/llm_provider_guard.py` — the §9 verification guard predicates, isolated so both the route and the wizard's finalize path call one implementation.
- `backend/app/services/model_probe.py` — shared probe-response parsing, extracted from `setup.py`.
- `backend/scripts/cutover/llm_providers_transition.py` — the one-time deploy transition.
- `frontend/src/features/settings/components/providers-panel.tsx` — the Providers sub-tab.
- `frontend/src/hooks/api/use-llm-providers-api.ts` — provider queries/mutations.
- `backend/tests/test_llm_providers.py` — provider table, CRUD, guard.
- `backend/tests/test_llm_seed_resolution_pin.py` — the resolved-seed and judge-identity pins.
- `backend/scripts/cutover/tests/test_llm_providers_transition.py`
- `frontend/src/features/settings/__tests__/settings-providers.real.test.tsx`

**Modified** — `0001_baseline.py`, `models/llm_config.py`, `models/__init__.py`, `services/config.py`, `services/llm_seed.py`, `schemas/config.py`, `api/routes/config.py`, `api/routes/setup.py`, `app/main.py` (router mount), `scripts/benchlib/run_smoke.py`, `scripts/benchlib/ingest.py`, `scripts/cutover/spec.py`, six test files, the settings and setup frontend features, and five docs.

**Deleted** — `frontend/src/features/llm/` (entire directory, including its `__tests__`).

---

### Task 1: The provider table, model, and seed rows

Purely additive. Nothing references `llm_providers` yet, so the suite stays green.

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py:1128` (insert before the `llm_purpose_configs` block)
- Create: `backend/app/models/llm_provider.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/services/llm_seed.py:86`
- Test: `backend/tests/test_llm_providers.py`

**Interfaces:**
- Produces: `LLMProviderRow` (ORM, `__tablename__ = "llm_providers"`, columns `name` PK, `api_kind`, `base_url`, `api_key`, `updated_at`); `llm_seed.DEFAULT_PROVIDER_ROWS: list[ProviderRowSeed]` with `.name/.api_kind/.base_url/.api_key`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_llm_providers.py`:

```python
"""The provider layer: one row per vendor connection, referenced by purpose.

Doc 04 §7's flattening is reversed by the owner ruling of 2026-08-20
(`docs/superpowers/specs/2026-08-20-llm-providers-design.md` §0). Connection
details live here; a purpose contributes only what varies per purpose.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.models.llm_provider import LLMProviderRow


@pytest.mark.asyncio
async def test_llm_providers_table_exists(session):
    exists = (
        await session.execute(
            text("SELECT to_regclass('public.llm_providers') IS NOT NULL")
        )
    ).scalar_one()
    assert exists is True


@pytest.mark.asyncio
async def test_provider_row_round_trips(session):
    session.add(
        LLMProviderRow(
            name="deepseek-prod",
            api_kind="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        )
    )
    await session.flush()

    row = (
        await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == "deepseek-prod")
        )
    ).scalar_one()
    assert row.api_kind == "deepseek"
    assert row.base_url == "https://api.deepseek.com/v1"
    assert row.api_key == "sk-test"
    assert row.updated_at is not None


@pytest.mark.asyncio
async def test_provider_name_is_unique(session):
    session.add(LLMProviderRow(name="dup", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMProviderRow(name="dup", api_kind="openai", base_url="http://b/v1"))
    with pytest.raises(Exception):
        await session.flush()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.llm_provider'`

- [ ] **Step 3: Add the table to the baseline**

In `backend/migrations/versions/0001_baseline.py`, immediately **before** the `CREATE TABLE llm_purpose_configs` block at line 1128, insert:

```python
    # ------------------------------------------------------------------
    # llm_providers — the connection layer under the purposes
    # ------------------------------------------------------------------
    # Reinstated by the owner ruling of 2026-08-20, reversing doc 04 §7's
    # flattening. A purpose references a provider by name; resolution is one
    # query with one join and still yields a flat LLMPurposeConfig, which is
    # what keeps the benchlib cache key and the judge identity hash stable.
    op.execute(
        """
        CREATE TABLE llm_providers (
            name       VARCHAR(64) PRIMARY KEY,
            api_kind   VARCHAR(32)  NOT NULL DEFAULT 'openai',
            base_url   VARCHAR(512) NOT NULL DEFAULT '',
            api_key    VARCHAR(1024),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
```

- [ ] **Step 4: Write the ORM model**

Create `backend/app/models/llm_provider.py`:

```python
"""ORM model for the LLM provider table.

One row per vendor connection. A purpose row references it by name and
contributes only what varies per purpose (model, params, dimensions,
reasoning, classifier_kind), so a credential rotation reaches every purpose
that uses the provider with no re-apply step.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMProviderRow(Base):
    __tablename__ = "llm_providers"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False,
    )
```

Then export it from `backend/app/models/__init__.py` beside `LLMPurposeConfigRow`, matching the existing import/`__all__` style in that file.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: 3 passed

- [ ] **Step 6: Add the seeded provider rows**

In `backend/app/services/llm_seed.py`, after the `DEFAULT_PROVIDERS` list (line 86–94), add:

```python
@dataclass(frozen=True)
class ProviderRowSeed:
    name: str
    api_kind: str
    base_url: str
    api_key: str | None = None


# The rows actually written to `llm_providers`. DEFAULT_PROVIDERS above stays a
# vendor *catalogue* keyed by api_kind, read by provider_seed_by_kind to supply
# the wizard's base-URL default — it is not this list, and conflating the two
# flips the wire protocol: its `ollama` entry is api_kind='ollama' (the native
# /api path) while every purpose below resolves api_kind='openai' against a
# /v1-suffixed URL (the compat path).
#
# `verification-judge` exists so the verification purpose does not share a
# provider by default: two of the judge's six identity fields (base_url,
# api_kind) live on the provider row, so a shared provider would put the
# qualification identity behind an unrelated edit.
DEFAULT_PROVIDER_ROWS: list[ProviderRowSeed] = [
    ProviderRowSeed("ollama-local", "openai", OLLAMA_BASE_URL),
    ProviderRowSeed("verification-judge", "openai", OLLAMA_BASE_URL),
]
```

- [ ] **Step 7: Test the seed list's coherence**

Append to `backend/tests/test_llm_providers.py`:

```python
def test_seeded_provider_rows_match_the_purpose_seed_connection():
    """The provider a purpose is seeded against must carry the api_kind and
    base_url that purpose resolves to today, or every fresh install silently
    changes wire protocol."""
    from app.services import llm_seed

    by_name = {p.name: p for p in llm_seed.DEFAULT_PROVIDER_ROWS}
    for pc in llm_seed.DEFAULT_PURPOSE_CONFIGS:
        expected = "verification-judge" if pc.purpose == "verification" else "ollama-local"
        provider = by_name[expected]
        assert provider.api_kind == pc.api_kind, pc.purpose
        assert provider.base_url == pc.base_url, pc.purpose
```

- [ ] **Step 8: Run the test**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: 4 passed. If the api_kind assertion fails, the seed lists disagree — fix `DEFAULT_PROVIDER_ROWS`, never the purpose seed.

- [ ] **Step 9: Confirm nothing else broke**

Run: `cd backend && python -m pytest -q`
Expected: all pass (the change is additive).

- [ ] **Step 10: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/app/models/llm_provider.py \
        backend/app/models/__init__.py backend/app/services/llm_seed.py \
        backend/tests/test_llm_providers.py
git commit -m "feat(llm): add the llm_providers table and its seed rows"
```

---

### Task 2: The `provider_name` column, nullable, with every writer populating it

Still green: resolution keeps reading the inline columns. This task's job is to make every writer produce a `provider_name` that **agrees** with the inline values it writes, so Task 4 can drop them safely.

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py` (the `llm_purpose_configs` block)
- Modify: `backend/app/models/llm_config.py`
- Modify: `backend/app/api/routes/setup.py:362-425`
- Modify: `backend/scripts/benchlib/run_smoke.py:104-183`
- Modify: `backend/scripts/benchlib/ingest.py:95-112`
- Modify: `backend/tests/test_classifier_kind.py:40`, `backend/tests/test_classifier_local.py:48`
- Test: `backend/tests/test_llm_providers.py`

**Interfaces:**
- Consumes: `LLMProviderRow`, `DEFAULT_PROVIDER_ROWS` (Task 1).
- Produces: `LLMPurposeConfigRow.provider_name: Mapped[str | None]`; `run_smoke.seed_llm_providers(session_factory, deepseek_api_key) -> None`; `run_smoke.purpose_config_specs()` entries gain a `provider_name` key and keep `api_kind`/`base_url`/`api_key`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm_providers.py`:

```python
@pytest.mark.asyncio
async def test_purpose_row_carries_a_provider_reference(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="p1", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(
        LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="p1")
    )
    await session.flush()

    row = (
        await session.execute(
            select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "extraction")
        )
    ).scalar_one()
    assert row.provider_name == "p1"


@pytest.mark.asyncio
async def test_purpose_provider_reference_must_resolve(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(
        LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="ghost")
    )
    with pytest.raises(Exception):
        await session.flush()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: FAIL — `TypeError: 'provider_name' is an invalid keyword argument`

- [ ] **Step 3: Add the column to the baseline**

In `0001_baseline.py`'s `CREATE TABLE llm_purpose_configs`, add as the second column (after `purpose`):

```sql
            provider_name   VARCHAR(64)
                REFERENCES llm_providers(name) ON UPDATE CASCADE ON DELETE RESTRICT,
```

Leave it nullable for now; Task 4 tightens it. Add the matching field to `backend/app/models/llm_config.py` after `purpose`:

```python
    provider_name: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("llm_providers.name", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=True,
    )
```

Import `ForeignKey` from `sqlalchemy` at the top of that module.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: 6 passed

- [ ] **Step 5: Make the wizard's finalize write providers first**

In `backend/app/api/routes/setup.py`, inside the `if body.llm is not None:` block, **before** the `DEFAULT_PURPOSE_CONFIGS` loop, insert:

```python
                from app.models.llm_provider import LLMProviderRow
                from app.services.llm_seed import DEFAULT_PROVIDER_ROWS

                existing_providers = {
                    r.name: r
                    for r in (await session.execute(select(LLMProviderRow))).scalars().all()
                }
                for ps in DEFAULT_PROVIDER_ROWS:
                    prow = existing_providers.get(ps.name)
                    if prow is None:
                        prow = LLMProviderRow(name=ps.name)
                        session.add(prow)
                        existing_providers[ps.name] = prow
                    prow.api_kind = ps.api_kind
                    prow.base_url = ps.base_url
                    prow.api_key = ps.api_key
                await session.flush()
```

Then in the `DEFAULT_PURPOSE_CONFIGS` loop, after `row.api_key = None`, add:

```python
                    row.provider_name = (
                        "verification-judge" if pc.purpose == "verification" else "ollama-local"
                    )
```

The user-overlay loop below writes the user's own vendor. Give it a provider row: after `user_base_url` is computed, insert:

```python
                user_provider_name = f"user-{body.llm.api_kind}"
                uprow = existing_providers.get(user_provider_name)
                if uprow is None:
                    uprow = LLMProviderRow(name=user_provider_name)
                    session.add(uprow)
                    existing_providers[user_provider_name] = uprow
                uprow.api_kind = body.llm.api_kind
                uprow.base_url = user_base_url
                uprow.api_key = body.llm.api_key
                await session.flush()
```

and inside the per-purpose overlay loop, alongside `pcfg.api_kind = body.llm.api_kind`, add `pcfg.provider_name = user_provider_name`.

- [ ] **Step 6: Give benchlib its providers**

In `backend/scripts/benchlib/run_smoke.py`, add above `seed_llm_purpose_configs`:

```python
BENCH_PROVIDERS = [
    {
        "name": "bench-ollama",
        "api_kind": "ollama",
        "base_url": OLLAMA_EMBEDDING_BASE_URL,
        "api_key": None,
    },
    {
        "name": "bench-deepseek",
        "api_kind": "deepseek",
        "base_url": DEEPSEEK_BASE_URL,
        "api_key": None,  # filled per run; never written to disk
    },
]


async def seed_llm_providers(session_factory, deepseek_api_key: str) -> None:
    """Write the two bench provider rows. Update-or-insert, like the purpose
    seeding below: one reset cycle serves two passes."""
    from app.models.llm_provider import LLMProviderRow

    async with session_factory() as session:
        for spec in BENCH_PROVIDERS:
            existing = (await session.execute(
                select(LLMProviderRow).where(LLMProviderRow.name == spec["name"])
            )).scalar_one_or_none()
            row = existing or LLMProviderRow(name=spec["name"])
            row.api_kind = spec["api_kind"]
            row.base_url = spec["base_url"]
            row.api_key = deepseek_api_key if spec["name"] == "bench-deepseek" else None
            if existing is None:
                session.add(row)
        await session.commit()
```

Add `"provider_name": "bench-ollama"` to the `embedding` entry of `purpose_config_specs`, and `"provider_name": "bench-deepseek"` to the other three. Then make `seed_llm_purpose_configs` call `await seed_llm_providers(session_factory, deepseek_api_key)` as its first statement, so all five harnesses get providers through the one function they already call.

- [ ] **Step 7: Fix the second benchlib writer**

In `backend/scripts/benchlib/ingest.py`, the `else:` branch at line ~102 constructs a purpose row from `settings.llm_classification`. It needs a provider. Replace the `session.add(LLMPurposeConfigRow(...))` call's argument list by adding, after `params=defaults.params,`:

```python
                provider_name="bench-deepseek",
```

and above the `session.add`, ensure the provider exists:

```python
            from app.models.llm_provider import LLMProviderRow

            if (await session.execute(
                select(LLMProviderRow).where(LLMProviderRow.name == "bench-deepseek")
            )).scalar_one_or_none() is None:
                session.add(LLMProviderRow(
                    name="bench-deepseek",
                    api_kind=defaults.api_kind,
                    base_url=defaults.base_url,
                    api_key=defaults.api_key,
                ))
                await session.flush()
```

- [ ] **Step 8: Fix the two classifier tests**

In `backend/tests/test_classifier_kind.py:40` and `backend/tests/test_classifier_local.py:48`, each constructs `LLMPurposeConfigRow(purpose="classification", model="qwen2.5:3b", ...)`. Before each, add a provider and reference it:

```python
    session.add(LLMProviderRow(name="t", api_kind="openai", base_url="http://x/v1"))
    await session.flush()
```

and add `provider_name="t"` to the `LLMPurposeConfigRow(...)` call. Import `LLMProviderRow` from `app.models.llm_provider` at the top of each file.

- [ ] **Step 9: Assert writer/inline agreement**

Append to `backend/tests/test_llm_providers.py`:

```python
@pytest.mark.asyncio
async def test_every_seeded_purpose_row_agrees_with_its_provider(session):
    """The invariant Task 4's column drop depends on: a purpose's inline
    connection and its provider's must be the same values, or dropping the
    inline copy changes behaviour."""
    from app.models.llm_config import LLMPurposeConfigRow
    from app.services.llm_seed import DEFAULT_PROVIDER_ROWS, DEFAULT_PURPOSE_CONFIGS

    for ps in DEFAULT_PROVIDER_ROWS:
        session.add(LLMProviderRow(name=ps.name, api_kind=ps.api_kind, base_url=ps.base_url))
    await session.flush()
    for pc in DEFAULT_PURPOSE_CONFIGS:
        session.add(LLMPurposeConfigRow(
            purpose=pc.purpose, model=pc.model, api_kind=pc.api_kind,
            base_url=pc.base_url, params=dict(pc.params),
            provider_name=("verification-judge" if pc.purpose == "verification" else "ollama-local"),
        ))
    await session.flush()

    rows = (await session.execute(select(LLMPurposeConfigRow))).scalars().all()
    providers = {p.name: p for p in (await session.execute(select(LLMProviderRow))).scalars().all()}
    for row in rows:
        provider = providers[row.provider_name]
        assert row.api_kind == provider.api_kind, row.purpose
        assert row.base_url == provider.base_url, row.purpose
```

- [ ] **Step 10: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 11: Run the benchlib harness suite**

Run: `cd backend && python -m pytest scripts/benchlib/tests -q`
Expected: all pass. (`pyproject.toml` sets `testpaths = ["tests"]`, so plain `pytest -q` does **not** collect these — run them explicitly.)

- [ ] **Step 12: Commit**

```bash
git add -A backend
git commit -m "feat(llm): reference a provider from every purpose row"
```

---

### Task 3: Flip resolution to the join, with the pins that prove nothing moved

The risky step, isolated. Resolution starts reading the provider; the inline columns are still present but ignored.

**Files:**
- Modify: `backend/app/services/config.py:49-83`
- Test: `backend/tests/test_llm_config.py`, `backend/tests/test_llm_seed_resolution_pin.py` (create)

**Interfaces:**
- Consumes: `LLMProviderRow`, `LLMPurposeConfigRow.provider_name`.
- Produces: `get_llm_config(session) -> dict[str, LLMPurposeConfig]` — signature and return shape **unchanged**.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm_config.py`:

```python
@pytest.mark.asyncio
async def test_resolution_reads_connection_from_the_provider(session):
    from app.models.llm_provider import LLMProviderRow

    session.add(LLMProviderRow(
        name="ds", api_kind="deepseek",
        base_url="https://api.deepseek.com/v1", api_key="sk-x",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="extraction", model="deepseek-v4-flash", provider_name="ds",
    ))
    await session.flush()

    cfg = (await get_llm_config(session))["extraction"]
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_kind == "deepseek"
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.api_key == "sk-x"


@pytest.mark.asyncio
async def test_resolution_is_one_query_with_one_join(session):
    _, counter = await _count_resolution_queries(session)
    sql = counter.selects[0].upper()
    assert sql.count("JOIN") == 1
    assert "LLM_PROVIDERS" in sql
    assert "LLM_PROFILES" not in sql
    assert "ML_PROFILES" not in sql
```

Delete `test_resolution_joins_nothing` (lines 98–105) — it is replaced by the above. In `test_indirection_tables_do_not_exist` and `test_ref_columns_are_gone_from_the_table`, drop the `"llm_providers"` and `"provider_id"` parametrize cases; keep the other two in each. Re-point `test_api_kind_survives_as_the_vendor_field` at `table_name = 'llm_providers'`.

Also update the module docstring's opening paragraph to state the 2026-08-20 reversal, so the file does not assert something its own tests now contradict.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_config.py -q`
Expected: FAIL — `test_resolution_reads_connection_from_the_provider` gets `api_kind == 'openai'` (the column default) rather than `'deepseek'`.

- [ ] **Step 3: Implement the join**

In `backend/app/services/config.py`, replace the `rows = ...` line and the merge loop body:

```python
    stmt = (
        select(LLMPurposeConfigRow, LLMProviderRow)
        .join(LLMProviderRow, LLMPurposeConfigRow.provider_name == LLMProviderRow.name)
    )
    by_purpose = {row.purpose: (row, provider) for row, provider in await session.execute(stmt)}

    merged: dict[str, LLMPurposeConfig] = {}
    for purpose in PURPOSES:
        pair = by_purpose.get(purpose)
        if pair is None:
            merged[purpose] = defaults[purpose]
            continue
        row, provider = pair
        merged[purpose] = LLMPurposeConfig(
            base_url=provider.base_url,
            model=row.model,
            api_key=provider.api_key,
            dimensions=row.dimensions,
            reasoning=row.reasoning,
            api_kind=provider.api_kind,
            params=row.params or {},
            classifier_kind=row.classifier_kind,
        )
    return merged
```

Import `LLMProviderRow` at the top. Update the module docstring: it currently says "Reads ONE table" and "no joins".

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_config.py -q`
Expected: all pass, including both query-count tests (an inner join over two tables is still one statement).

- [ ] **Step 5: Write the pin tests**

Create `backend/tests/test_llm_seed_resolution_pin.py`:

```python
"""Two hashes ride on the resolved config, so its values are pinned.

`benchlib/caching_llm.py` keys every cached LLM call on the resolved
`model/base_url/api_kind/dimensions/reasoning/params`, and
`verification_judge.IDENTITY_FIELDS` is the same six. A seed edit that
perturbs a resolved value silently invalidates every bench cache entry and
un-qualifies the judge, and neither failure announces itself.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.services.config import get_llm_config
from app.services.llm_seed import DEFAULT_PROVIDER_ROWS, DEFAULT_PURPOSE_CONFIGS

# What every purpose resolved to before the provider layer existed: the inline
# values carried by DEFAULT_PURPOSE_CONFIGS itself.
EXPECTED = {
    pc.purpose: {
        "model": pc.model,
        "api_kind": pc.api_kind,
        "base_url": pc.base_url,
        "dimensions": pc.dimensions,
        "params": dict(pc.params),
    }
    for pc in DEFAULT_PURPOSE_CONFIGS
}


async def _seed(session):
    for ps in DEFAULT_PROVIDER_ROWS:
        session.add(LLMProviderRow(
            name=ps.name, api_kind=ps.api_kind, base_url=ps.base_url, api_key=ps.api_key,
        ))
    await session.flush()
    for pc in DEFAULT_PURPOSE_CONFIGS:
        session.add(LLMPurposeConfigRow(
            purpose=pc.purpose,
            provider_name=("verification-judge" if pc.purpose == "verification" else "ollama-local"),
            model=pc.model,
            dimensions=pc.dimensions,
            params=dict(pc.params),
        ))
    await session.flush()


@pytest.mark.asyncio
async def test_fresh_install_resolves_to_the_pre_provider_values(session):
    await _seed(session)
    config = await get_llm_config(session)
    for purpose, expected in EXPECTED.items():
        cfg = config[purpose]
        assert cfg.model == expected["model"], purpose
        assert cfg.api_kind == expected["api_kind"], purpose
        assert cfg.base_url == expected["base_url"], purpose
        assert cfg.dimensions == expected["dimensions"], purpose
        assert cfg.params == expected["params"], purpose


@pytest.mark.asyncio
async def test_judge_identity_survives_the_split(session):
    """The qualified identity is computed off the resolved config. Split across
    a provider row and a purpose row, it must hash to the same value."""
    from app.services.verification_judge import judge_identity, judge_identity_hash

    session.add(LLMProviderRow(
        name="openai-judge", api_kind="openai",
        base_url="https://api.openai.com/v1", api_key="sk-x",
    ))
    await session.flush()
    session.add(LLMPurposeConfigRow(
        purpose="verification", provider_name="openai-judge",
        model="gpt-5.5", params={"reasoning_effort": "high"},
    ))
    await session.flush()

    cfg = (await get_llm_config(session))["verification"]
    assert judge_identity_hash(judge_identity(cfg)) == "fd39e7b2c47fa375"
```

- [ ] **Step 6: Run the pins**

Run: `cd backend && python -m pytest tests/test_llm_seed_resolution_pin.py -q`
Expected: 2 passed.

If `test_judge_identity_survives_the_split` fails, **stop and report** — do not adjust the expected hash. A mismatch means the resolved identity moved, which is the failure this whole design is built to prevent. Print `judge_identity(cfg)` and compare field by field against `app/services/verification_qualification.entailment.json`'s recorded identity.

- [ ] **Step 7: Run the full suite**

Run: `cd backend && python -m pytest -q && python -m pytest scripts/benchlib/tests -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add -A backend
git commit -m "feat(llm): resolve purpose connection through the provider"
```

---

### Task 4: Tighten to NOT NULL and drop the inline columns

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py`, `backend/app/models/llm_config.py`
- Modify: `backend/tests/test_llm_config.py`, `backend/tests/test_setup.py:42-112`, `backend/tests/test_setup_route.py:309`
- Modify: `backend/scripts/benchlib/run_smoke.py`, `backend/scripts/benchlib/ingest.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm_providers.py`:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("column", ["api_kind", "base_url", "api_key"])
async def test_connection_columns_left_the_purpose_table(session, column):
    present = (
        await session.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'llm_purpose_configs' AND column_name = :c"
            ),
            {"c": column},
        )
    ).scalar_one()
    assert present == 0


@pytest.mark.asyncio
async def test_provider_reference_is_required(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMPurposeConfigRow(purpose="extraction", model="m"))
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
async def test_a_referenced_provider_cannot_be_deleted(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="held", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="held"))
    await session.flush()

    await session.execute(text("DELETE FROM llm_providers WHERE name = 'held'"))
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
async def test_renaming_a_provider_carries_to_its_purposes(session):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name="old", api_kind="openai", base_url="http://a/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="old"))
    await session.flush()

    await session.execute(text("UPDATE llm_providers SET name = 'new' WHERE name = 'old'"))
    moved = (
        await session.execute(
            text("SELECT provider_name FROM llm_purpose_configs WHERE purpose = 'extraction'")
        )
    ).scalar_one()
    assert moved == "new"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: FAIL — the three column-absence cases fail (columns still present) and `test_provider_reference_is_required` fails (nullable).

- [ ] **Step 3: Tighten the baseline**

In `0001_baseline.py`'s `llm_purpose_configs` block: make `provider_name` `NOT NULL`, and delete the `api_kind`, `base_url` and `api_key` column lines together with the F-10 comment above `api_kind` (its subject is leaving; move the comment to `llm_providers.api_kind` in Task 1's block instead of deleting the reasoning).

In `backend/app/models/llm_config.py`: make `provider_name` `Mapped[str]` with `nullable=False`, and delete the `api_kind`, `base_url` and `api_key` fields. Update the module docstring — it currently opens by asserting the indirection is gone.

- [ ] **Step 4: Strip the inline writes from every writer**

Remove `api_kind=`, `base_url=` and `api_key=` from: `run_smoke.purpose_config_specs()`'s four dicts (keep `provider_name`); `ingest.py`'s `LLMPurposeConfigRow(...)` call; `setup.py`'s `DEFAULT_PURPOSE_CONFIGS` loop (`row.api_kind`, `row.base_url`, `row.api_key`) and its user-overlay loop (`pcfg.api_kind`, `pcfg.base_url`, `pcfg.api_key`).

Delete `test_every_seeded_purpose_row_agrees_with_its_provider` from `tests/test_llm_providers.py` — the columns it compares no longer exist, and its job (guaranteeing the drop is safe) is done.

- [ ] **Step 5: Fix the remaining asserting tests**

`tests/test_setup.py:42-112` and `tests/test_setup_route.py:309` assert `api_kind`/`api_key`/`base_url` on purpose rows. Re-point each assertion at the joined provider row, e.g.:

```python
    provider = (await session.execute(
        select(LLMProviderRow).where(LLMProviderRow.name == row.provider_name)
    )).scalar_one()
    assert provider.api_kind == "deepseek"
```

In `tests/test_llm_config.py`, rewrite the raw-SQL fixtures at `:87` and `:173` and the two POST tests (`test_post_config_llm_writes_synthesis`, `test_post_config_llm_ignores_verification_write`) to insert a provider first and reference it. Example for `:87`:

```python
    await session.execute(
        text(
            "INSERT INTO llm_providers (name, api_kind, base_url) "
            "VALUES ('t', 'openai', 'http://example.invalid/v1')"
        )
    )
    for purpose in PURPOSES:
        await session.execute(
            text(
                "INSERT INTO llm_purpose_configs (purpose, model, provider_name) "
                "VALUES (:p, 'a-model', 't')"
            ),
            {"p": purpose},
        )
```

- [ ] **Step 6: Run everything**

Run: `cd backend && python -m pytest -q && python -m pytest scripts/benchlib/tests -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add -A backend
git commit -m "refactor(llm): drop inline connection from purpose rows"
```

---

### Task 5: Provider CRUD and probe endpoints

**Files:**
- Create: `backend/app/api/routes/llm_providers.py`, `backend/app/services/model_probe.py`
- Modify: `backend/app/api/routes/config.py` (extract the swap helper), `backend/app/api/routes/setup.py` (use the shared parser), `backend/app/main.py` (mount the router)
- Test: `backend/tests/test_llm_providers.py`

**Interfaces:**
- Produces: `apply_llm_config_change(request, session) -> dict | None` in `config.py` — re-resolves config, rebuilds and installs the orchestrator, returns `obsolete_after_change` or `None`. Caller must already hold `app.state.llm_config_lock`. `parse_model_list(data: dict) -> list[str]` in `model_probe.py`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_llm_providers.py`:

```python
@pytest.mark.asyncio
async def test_provider_crud_round_trip(client, auth_headers):
    created = await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "ds", "api_kind": "deepseek",
              "base_url": "https://api.deepseek.com/v1", "api_key": "sk-secret"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    listed = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    assert listed.status_code == 200
    row = next(p for p in listed.json()["providers"] if p["name"] == "ds")
    assert row["api_key"] == "***"
    assert row["used_by"] == []
    assert row["serves_verification"] is False

    dup = await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "ds", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    assert dup.status_code == 409

    deleted = await client.delete("/api/v1/config/llm-providers/ds", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_masked_key_sentinel_does_not_rotate(client, auth_headers, session):
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "k", "api_kind": "openai", "base_url": "http://x/v1", "api_key": "real"},
        headers=auth_headers,
    )
    await client.put(
        "/api/v1/config/llm-providers/k",
        json={"api_kind": "openai", "base_url": "http://y/v1", "api_key": "***"},
        headers=auth_headers,
    )
    stored = (await session.execute(
        text("SELECT api_key, base_url FROM llm_providers WHERE name = 'k'")
    )).one()
    assert stored[0] == "real"
    assert stored[1] == "http://y/v1"


@pytest.mark.asyncio
async def test_delete_is_blocked_while_referenced(client, auth_headers, session):
    from app.models.llm_config import LLMPurposeConfigRow

    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "held", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="held"))
    await session.commit()

    blocked = await client.delete("/api/v1/config/llm-providers/held", headers=auth_headers)
    assert blocked.status_code == 409
    assert "extraction" in blocked.json()["detail"]
```

Match the existing `client` / `auth_headers` fixture names used by `backend/tests/test_setup_route.py`; if they differ, use that file's fixtures verbatim.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q -k crud`
Expected: FAIL — 404, the route does not exist.

- [ ] **Step 3: Extract the shared probe parser**

Create `backend/app/services/model_probe.py`:

```python
"""Parse a vendor's model-list response.

Shared by the wizard's probe and the authenticated provider probes. The two
wire shapes are OpenAI-compat (`{"data": [{"id": ...}]}`) and Ollama native
(`{"models": [{"name": ...}]}`); a vendor serving neither yields an empty
list rather than an error, because "no models listed" is a real answer.
"""
from __future__ import annotations


def parse_model_list(data: object) -> list[str]:
    models: list[str] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            for entry in data["data"]:
                mid = entry.get("id") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
        elif isinstance(data.get("models"), list):
            for entry in data["models"]:
                mid = entry.get("name") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
    return sorted(set(models))
```

Replace the inline parsing in `backend/app/api/routes/setup.py:probe_models` with `models = parse_model_list(data)`.

- [ ] **Step 4: Extract the orchestrator swap**

In `backend/app/api/routes/config.py`, extract from `update_llm_config` everything from `updated_config = await fetch_llm_config(session)` through the `obsolete_after_change` computation into:

```python
async def apply_llm_config_change(request: Request, session: AsyncSession) -> dict | None:
    """Re-resolve config, install a fresh orchestrator, and count re-embed work.

    The caller must already hold ``app.state.llm_config_lock``. Both the purpose
    route and the provider routes change connection details, so both go through
    this; two copies would drift and one of them would keep calling the old
    endpoint until restart.
    """
```

Have `update_llm_config` call it. Return `obsolete_after_change`.

- [ ] **Step 5: Write the router**

Create `backend/app/api/routes/llm_providers.py` with `router = APIRouter(prefix="/api/v1/config/llm-providers", tags=["config"])` and six operations matching the spec's §3.1 table. Requirements:

- All six take `Depends(require_auth)`.
- `GET` returns `{"providers": [...]}`; each entry masks `api_key` to `"***"` when non-null, and carries `used_by: list[str]` (purposes referencing it) and `serves_verification: bool`.
- `POST` returns **201**; duplicate name → **409**.
- `PUT` honours the `"***"` sentinel by omitting `api_key` from the write.
- `DELETE` returns **204**; if `used_by` is non-empty, **409** whose `detail` names the purposes.
- `POST`, `PUT` and `DELETE` each wrap their work in `async with request.app.state.llm_config_lock:` and call `apply_llm_config_change` before returning, so a connection change goes live immediately and a concurrent purpose write cannot see a half-applied state.
- Both probe endpoints build their target with `llm_quirks.models_probe`, call `httpx.AsyncClient(timeout=15.0).get(...)`, parse with `parse_model_list`, and return `LLMProviderModelsResponse` (already defined in `app/schemas/config.py:33`) with **200 and `error` set** on any vendor failure — never a raise.
- `PUT` response includes `no_embedding_purposes: list[str]` naming any purpose using this provider for embeddings when `quirks_for(api_kind).supports_embedding` is false.

Mount it in `backend/app/main.py` beside the existing config router import.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: all pass.

- [ ] **Step 7: Test the orchestrator actually swaps**

```python
@pytest.mark.asyncio
async def test_provider_edit_swaps_the_live_orchestrator(client, auth_headers, app):
    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "sw", "api_kind": "openai", "base_url": "http://before/v1"},
        headers=auth_headers,
    )
    before = app.state.llm
    await client.put(
        "/api/v1/config/llm-providers/sw",
        json={"api_kind": "openai", "base_url": "http://after/v1", "api_key": "***"},
        headers=auth_headers,
    )
    assert app.state.llm is not before
```

Run it. Expected: PASS.

- [ ] **Step 8: Test the no-embeddings warning**

Spec §3.3 requires the PUT to name affected purposes when a provider is flipped to a vendor with no embeddings endpoint — the purposes panel's own warning cannot see a provider-side edit.

```python
@pytest.mark.asyncio
async def test_flipping_to_a_no_embeddings_vendor_names_the_purpose(
    client, auth_headers, session
):
    from app.models.llm_config import LLMPurposeConfigRow

    await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "emb", "api_kind": "openai", "base_url": "http://x/v1"},
        headers=auth_headers,
    )
    session.add(LLMPurposeConfigRow(purpose="embedding", model="e", provider_name="emb"))
    await session.commit()

    resp = await client.put(
        "/api/v1/config/llm-providers/emb",
        json={"api_kind": "deepseek", "base_url": "https://api.deepseek.com/v1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["no_embedding_purposes"] == ["embedding"]
```

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q`
Expected: all pass. If `deepseek` reports as embedding-capable, read `quirks_for("deepseek").supports_embedding` in `app/services/llm_quirks.py` and use whichever vendor that table marks false — the quirk row is the authority, not this plan.

- [ ] **Step 9: Commit**

```bash
git add -A backend
git commit -m "feat(api): add provider CRUD and model probes"
```

---

### Task 6: Move `/config/llm` onto `provider_name`

**Files:**
- Modify: `backend/app/schemas/config.py:21-31`, `backend/app/api/routes/config.py:128-215`, `backend/app/config.py:48-54`, `backend/app/services/config.py:23-25`
- Test: `backend/tests/test_llm_config.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_purpose_write_takes_a_provider_name(client, auth_headers, session):
    await session.execute(text(
        "INSERT INTO llm_providers (name, api_kind, base_url) VALUES ('p2','openai','http://b/v1')"
    ))
    await session.commit()

    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "p2", "model": "m2"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["extraction"]["base_url"] == "http://b/v1"


@pytest.mark.asyncio
async def test_unknown_provider_is_a_422(client, auth_headers):
    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "ghost", "model": "m"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_creating_a_rowless_purpose_requires_a_provider(client, auth_headers):
    resp = await client.post(
        "/api/v1/config/llm",
        json={"reranker": {"model": "only-a-model"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "provider_name" in resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_config.py -q -k provider`
Expected: FAIL — `provider_name` is not a declared field, so it is ignored and the write is a no-op.

- [ ] **Step 3: Change the schemas**

In `app/schemas/config.py`, `LLMPurposeConfigUpdate`: delete `base_url`, `api_key`, `api_kind`; add `provider_name: str | None = None`. Leave `LLMPurposeConfigSchema` (the read side) **unchanged** — it is the resolved view.

In `app/config.py`, delete `provider_ref`, `profile_ref` and `ml_profile_ref` from `LLMPurposeConfig` (lines 48–54) along with their comment.

In `app/services/config.py`, delete the `LLM_PROVIDERS_KEY` and `LLM_PROFILES_KEY` constants and their comment — a `config`-row key sharing a name with a real table is a grep hazard. Check for readers first: `rg -n "LLM_PROVIDERS_KEY|LLM_PROFILES_KEY" backend` must come back empty apart from the definitions.

- [ ] **Step 4: Change the route**

In `update_llm_config`, replace the field list

```python
            for field in (
                "model", "dimensions", "reasoning", "api_kind",
                "base_url", "api_key", "params", "classifier_kind",
            ):
```

with

```python
            for field in (
                "model", "provider_name", "dimensions", "reasoning",
                "params", "classifier_kind",
            ):
```

Delete the `"***"` sentinel pop (the key no longer arrives here). Before the row lookup, validate the reference:

```python
            if "provider_name" in incoming:
                known = (await session.execute(
                    select(LLMProviderRow.name)
                    .where(LLMProviderRow.name == incoming["provider_name"])
                )).scalar_one_or_none()
                if known is None:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown provider_name {incoming['provider_name']!r}",
                    )
```

and replace the rowless-purpose branch:

```python
            if row is None:
                if "provider_name" not in incoming:
                    raise HTTPException(
                        status_code=422,
                        detail=f"purpose {purpose!r} has no row yet; provider_name is required",
                    )
                row = LLMPurposeConfigRow(
                    purpose=purpose, model="", provider_name=incoming["provider_name"],
                )
                session.add(row)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_config.py -q`
Expected: all pass.

- [ ] **Step 6: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add -A backend
git commit -m "feat(api): write purpose connection via provider_name"
```

---

### Task 7: The verification guard

**Files:**
- Create: `backend/app/services/llm_provider_guard.py`
- Modify: `backend/app/api/routes/llm_providers.py`, `backend/app/api/routes/config.py`, `backend/app/api/routes/setup.py`
- Test: `backend/tests/test_llm_providers.py`

**Interfaces:**
- Produces: `verification_provider(session) -> str | None`; `assert_identity_fields_unchanged(provider_name, current, incoming, verification_provider_name)` raising `HTTPException(409)`; `assert_not_verification_provider(provider_name, verification_provider_name, purpose)` raising `HTTPException(409)`.

- [ ] **Step 1: Write the failing test**

```python
async def _point_verification_at(session, name: str):
    from app.models.llm_config import LLMPurposeConfigRow

    session.add(LLMProviderRow(name=name, api_kind="openai", base_url="https://api.openai.com/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="verification", model="gpt-5.5", provider_name=name))
    await session.commit()


@pytest.mark.asyncio
async def test_identity_fields_are_frozen_on_the_judge_provider(client, auth_headers, session):
    await _point_verification_at(session, "judge")
    for field, value in (("base_url", "http://elsewhere/v1"), ("api_kind", "deepseek")):
        payload = {"api_kind": "openai", "base_url": "https://api.openai.com/v1", field: value}
        resp = await client.put(
            "/api/v1/config/llm-providers/judge", json=payload, headers=auth_headers
        )
        assert resp.status_code == 409, field
        assert "verification" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_the_judge_key_still_rotates(client, auth_headers, session):
    """api_key is not an identity field — its own comment in verification_judge
    says rotating a credential is not a model swap — and the owner ruling of
    2026-08-20 requires this key to be rotatable."""
    await _point_verification_at(session, "judge2")
    resp = await client.put(
        "/api/v1/config/llm-providers/judge2",
        json={"api_kind": "openai", "base_url": "https://api.openai.com/v1",
              "api_key": "sk-rotated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    stored = (await session.execute(
        text("SELECT api_key FROM llm_providers WHERE name = 'judge2'")
    )).scalar_one()
    assert stored == "sk-rotated"


@pytest.mark.asyncio
async def test_no_other_purpose_may_join_the_judge_provider(client, auth_headers, session):
    await _point_verification_at(session, "judge3")
    resp = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "judge3", "model": "m"}},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_a_shared_judge_provider_is_reported_not_deadlocked(client, auth_headers, session):
    """A direct-SQL restore can produce sharing the API would refuse. The
    remedy must stay reachable: repoint the *other* purpose off it."""
    from app.models.llm_config import LLMPurposeConfigRow

    await _point_verification_at(session, "shared")
    session.add(LLMPurposeConfigRow(purpose="extraction", model="m", provider_name="shared"))
    await session.commit()

    listed = await client.get("/api/v1/config/llm-providers", headers=auth_headers)
    row = next(p for p in listed.json()["providers"] if p["name"] == "shared")
    assert row["serves_verification"] is True
    assert set(row["used_by"]) == {"verification", "extraction"}

    await session.execute(text(
        "INSERT INTO llm_providers (name, api_kind, base_url) VALUES ('other','openai','http://o/v1')"
    ))
    await session.commit()
    freed = await client.post(
        "/api/v1/config/llm",
        json={"extraction": {"provider_name": "other"}},
        headers=auth_headers,
    )
    assert freed.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_providers.py -q -k judge`
Expected: FAIL — the PUT returns 200; nothing guards it.

- [ ] **Step 3: Write the guard**

Create `backend/app/services/llm_provider_guard.py`:

```python
"""Keep the verification judge's identity off the provider form.

`LLMConfigUpdate` deliberately omits the `verification` purpose: repointing the
qualified judge from a settings form is a capability whose write-time safety
half was scoped out as later ladder work. Two of the judge's six identity
fields — `base_url` and `api_kind` — now live on a provider row, so the same
refusal has to hold on the provider door or the restriction is decorative.

`api_key` is deliberately NOT frozen. It is absent from `IDENTITY_FIELDS`
("rotating a credential is not a model swap"), so freezing it would protect
nothing while blocking the rotation the owner ruling of 2026-08-20 requires.

Exclusivity is a default with a reachable remedy, not an enforced invariant: a
direct-SQL restore writes purpose rows without passing any API check, so the
shared state can exist. When it does, the escape is to repoint the *other*
purposes off the provider, which stays permitted.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LLMPurposeConfigRow

FROZEN_FIELDS = ("base_url", "api_kind")


async def verification_provider(session: AsyncSession) -> str | None:
    return (
        await session.execute(
            select(LLMPurposeConfigRow.provider_name)
            .where(LLMPurposeConfigRow.purpose == "verification")
        )
    ).scalar_one_or_none()


def assert_identity_fields_unchanged(
    provider_name: str, current, incoming: dict, verification_provider_name: str | None,
) -> None:
    if provider_name != verification_provider_name:
        return
    for field in FROZEN_FIELDS:
        if field in incoming and incoming[field] != getattr(current, field):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{field!r} is frozen on {provider_name!r}: it serves the "
                    "verification purpose, and this field is part of the judge's "
                    "qualification identity. The API key may still be rotated."
                ),
            )


def assert_not_verification_provider(
    provider_name: str, verification_provider_name: str | None, purpose: str,
) -> None:
    if provider_name == verification_provider_name and purpose != "verification":
        raise HTTPException(
            status_code=409,
            detail=(
                f"provider {provider_name!r} serves the verification purpose and is "
                f"exclusive to it; point {purpose!r} at a different provider."
            ),
        )
```

Call `assert_identity_fields_unchanged` from the provider `PUT` before writing, and `assert_not_verification_provider` from `update_llm_config`'s per-purpose loop when `provider_name` is in `incoming`.

- [ ] **Step 4: Enforce it in the wizard too**

In `backend/app/api/routes/setup.py`'s finalize block, the user-overlay loop iterates `body.llm.purposes`, whose `PURPOSE_LITERAL` covers only the six live purposes — so it cannot assign `verification`. Add an assertion that this stays true, in `backend/tests/test_setup.py`:

```python
def test_the_wizard_cannot_assign_the_tier_c_purposes():
    """Widening PURPOSE_LITERAL would make the judge wizard-writable, which is
    the capability T2.106 refused."""
    from app.api.routes.setup import PURPOSE_LITERAL
    from typing import get_args

    assert set(get_args(PURPOSE_LITERAL)) == {
        "embedding", "extraction", "classification",
        "reasoning", "summarization", "reranker",
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_providers.py tests/test_setup.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A backend
git commit -m "feat(llm): freeze the judge's identity fields on its provider"
```

---

### Task 8: Frontend — the Providers panel

**Files:**
- Create: `frontend/src/hooks/api/use-llm-providers-api.ts`, `frontend/src/features/settings/components/providers-panel.tsx`
- Modify: `frontend/src/features/settings/components/llm-tab.tsx`, `frontend/src/hooks/api/index.ts`
- Test: `frontend/src/features/settings/__tests__/settings-providers.real.test.tsx`

**Interfaces:**
- Produces: `LlmProvider { name, api_kind, base_url, api_key, used_by: string[], serves_verification: boolean }`; hooks `useLlmProviders()`, `useCreateLlmProvider()`, `useUpdateLlmProvider()`, `useDeleteLlmProvider()`, `useProbeProviderModels()`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/settings/__tests__/settings-providers.real.test.tsx`. The sibling `settings-llm.real.test.tsx` tests the binding with `renderHook` plus a mocked `apiFetch` rather than rendering DOM — mirror that harness exactly:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useLlmProviders,
  useDeleteLlmProvider,
} from "@/hooks/api/use-llm-providers-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PROVIDERS = {
  providers: [
    {
      name: "ollama-local",
      api_kind: "openai",
      base_url: "http://localhost:11434/v1",
      api_key: null,
      used_by: ["embedding", "extraction"],
      serves_verification: false,
    },
    {
      name: "verification-judge",
      api_kind: "openai",
      base_url: "https://api.openai.com/v1",
      api_key: "***",
      used_by: ["verification"],
      serves_verification: true,
    },
  ],
}

describe("useLlmProviders (DEMO off — real /config/llm-providers)", () => {
  afterEach(() => vi.clearAllMocks())

  it("lists providers with the key masked and a usage count", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    const { result } = renderHook(() => useLlmProviders(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith("/config/llm-providers")
    const local = result.current.data!.providers.find(
      (p) => p.name === "ollama-local",
    )!
    expect(local.used_by).toEqual(["embedding", "extraction"])
    const judge = result.current.data!.providers.find(
      (p) => p.name === "verification-judge",
    )!
    expect(judge.api_key).toBe("***")
    expect(judge.serves_verification).toBe(true)
  })

  it("surfaces the 409 when delete is blocked by a reference", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new Error("409: provider is used by extraction"),
    )
    const { result } = renderHook(() => useDeleteLlmProvider(), { wrapper })

    result.current.mutate("ollama-local")
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toContain("extraction")
  })
})
```

Then a component-level test for the read-only rendering, using `@testing-library/react`'s `render` (check whether any sibling test in `frontend/src/features/settings/__tests__/` already renders DOM and copy its setup; `settings-flags.test.tsx` is the likely model):

```tsx
it("freezes base_url and api_kind on the verification provider but not its key", async () => {
  vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
  render(<ProvidersPanel />, { wrapper })
  await waitFor(() =>
    expect(screen.getByLabelText("verification-judge base_url")).toBeDisabled(),
  )
  expect(screen.getByLabelText("verification-judge api_kind")).toBeDisabled()
  expect(screen.getByLabelText("verification-judge api_key")).toBeEnabled()
})
```

Give every provider input an `aria-label` of `` `${provider.name} ${field}` `` in Step 4 so these queries resolve.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- settings-providers`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the API hooks**

Create `frontend/src/hooks/api/use-llm-providers-api.ts` mirroring `use-config-api.ts`'s structure: `useQuery` on `["llmProviders"]` hitting `/config/llm-providers`, three mutations invalidating both `["llmProviders"]` and `["llmConfig"]` (a provider edit changes what every purpose resolves to), and a probe mutation posting to `/config/llm-providers/{name}/probe-models`. Export the types and re-export from `frontend/src/hooks/api/index.ts` beside the existing config exports.

- [ ] **Step 4: Write the panel**

Create `providers-panel.tsx`. Use darkraise-ui's `Card`, `Input`, `Select`, `Button`, `Badge`, and `EmptyState` for the no-providers case — check `ls frontend/node_modules/darkraise-ui/dist/components/` and read the `.d.ts` beside anything you are unsure of. Per card: name, `api_kind` `Select` over `API_KINDS` from `@/demo/settings`, base URL `Input`, masked key `Input`, a `used_by.length` badge, a "Test connection" `Button` calling the probe mutation and rendering `models.length` or `error`, and a delete `Button` disabled while `used_by.length > 0` with a tooltip naming the purposes.

When `serves_verification`, render `base_url` and `api_kind` disabled with a `HelpTip` explaining that they are the judge's qualification identity and that the key is still rotatable.

- [ ] **Step 5: Add the sub-tabs**

In `llm-tab.tsx`, wrap the existing content in a darkraise-ui `Tabs` with `TabsTrigger` values `"providers"` and `"purposes"`, defaulting to `"purposes"` so the tab opens where it does today. Put `<ProvidersPanel />` in the first and the existing grid in the second.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm test -- settings-providers`
Expected: PASS.

- [ ] **Step 7: Typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both clean.

- [ ] **Step 8: Commit**

```bash
git add -A frontend
git commit -m "feat(settings): add the LLM providers panel"
```

---

### Task 9: Frontend — purposes panel, combobox, and dead-surface removal

**Files:**
- Modify: `frontend/src/features/settings/components/llm-tab.tsx`, `frontend/src/features/settings/use-llm-tab-binding.ts`, `frontend/src/features/settings/types.ts`, `frontend/src/hooks/api/use-config-api.ts`, `frontend/src/demo/settings.ts`, `frontend/src/demo/data/knowledge-curated.ts:409-1324`
- Delete: `frontend/src/features/llm/` (whole directory)
- Test: `frontend/src/features/settings/__tests__/settings-llm.real.test.tsx`

- [ ] **Step 1: Write the failing test**

Extend `settings-llm.real.test.tsx`, keeping its existing `wrapper` and `apiFetch` mock:

```tsx
it("carries provider_name through the binding instead of connection fields", async () => {
  vi.mocked(apiFetch).mockResolvedValue({
    extraction: {
      provider_name: "ollama-local",
      base_url: "http://localhost:11434/v1",
      model: "qwen2.5:3b",
      api_key: null,
      dimensions: null,
      reasoning: false,
      api_kind: "openai",
      params: {},
    },
  })
  const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
  await waitFor(() => expect(result.current.isLoading).toBe(false))

  const extraction = result.current.purposes.find((p) => p.purpose === "extraction")
  expect(extraction?.provider_name).toBe("ollama-local")
})

it("saves a provider change and never sends a connection field", async () => {
  vi.mocked(apiFetch).mockResolvedValue({})
  const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
  await waitFor(() => expect(result.current.isLoading).toBe(false))

  result.current.savePurpose("extraction", { provider_name: "my-ds", model: "m" })

  await waitFor(() => {
    const body = JSON.parse(
      vi.mocked(apiFetch).mock.calls.at(-1)![1]!.body as string,
    )
    expect(body.extraction).toEqual({ provider_name: "my-ds", model: "m" })
    expect(body.extraction).not.toHaveProperty("base_url")
    expect(body.extraction).not.toHaveProperty("api_kind")
    expect(body.extraction).not.toHaveProperty("api_key")
  })
})
```

And a component-level pair for the combobox, in the same file as Task 8's DOM test:

```tsx
it("offers probed models but accepts one the probe never returned", async () => {
  vi.mocked(apiFetch).mockImplementation(async (path: string) =>
    path.endsWith("/probe-models")
      ? { models: ["a", "b"], fetched_via: "openai_compat:/v1/models", error: null }
      : PURPOSES_FIXTURE,
  )
  render(<LLMTab />, { wrapper })
  const field = await screen.findByLabelText("extraction model")
  await userEvent.clear(field)
  await userEvent.type(field, "c")
  expect(field).toHaveValue("c")
})

it("keeps the model field usable when the probe fails", async () => {
  vi.mocked(apiFetch).mockImplementation(async (path: string) =>
    path.endsWith("/probe-models")
      ? { models: [], fetched_via: "openai_compat:/v1/models", error: "HTTP 401" }
      : PURPOSES_FIXTURE,
  )
  render(<LLMTab />, { wrapper })
  expect(await screen.findByText(/HTTP 401/)).toBeInTheDocument()
  expect(screen.getByLabelText("extraction model")).toBeEnabled()
})
```

Define `PURPOSES_FIXTURE` as the eight-purpose response shape used in the first test above.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- settings-llm`
Expected: FAIL — the connection inputs still render.

- [ ] **Step 3: Change the wire types**

In `use-config-api.ts`: add `provider_name: string` to `LlmPurposeConfig`; keep `base_url`/`api_kind`/`api_key` (still served on the read side) and comment that they are resolved and read-only. In `features/settings/types.ts`, mirror the change on `DemoLLMPurpose`.

- [ ] **Step 4: Rework the purpose card**

In `llm-tab.tsx`: delete the `api_kind`, `base_url` and `api_key` `Field` blocks and their `Draft` keys; add `provider_name` to `Draft` with a `Select` over `useLlmProviders()`; replace the model `Input` with darkraise-ui's `Combobox` fed by `useProbeProviderModels()` for the selected provider, keeping `inputValue` bound so free text survives. Change `embeddingKindWarning`'s argument to the selected provider's `api_kind`, looked up from the provider list.

Delete `RemovedChrome` (lines ~441–480) and its render site — it announces the provider tab as "deleted, not disabled", which stops being true here.

- [ ] **Step 5: Retire the dead feature directory and stale demo copy**

```bash
git rm -r frontend/src/features/llm
```

Then `rg -n "features/llm" frontend/src` and fix any import that surfaces. Update the narration in `frontend/src/demo/data/knowledge-curated.ts` that describes resolution "through a provider_ref or profile_ref", and the demo fixtures in `use-llm-tab-binding.ts` and `frontend/src/demo/settings.ts` to carry `provider_name`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: full vitest suite passes.

- [ ] **Step 7: Typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both clean.

- [ ] **Step 8: Commit**

```bash
git add -A frontend
git commit -m "feat(settings): pick a provider and probe models per purpose"
```

---

### Task 10: Provider-first setup wizard

**Files:**
- Modify: `frontend/src/features/setup/components/StepLLM.tsx`, `frontend/src/features/setup/setupWizardStore.ts`, `frontend/src/features/setup/schemas.ts`, `backend/app/api/routes/setup.py`
- Test: `frontend/src/features/setup/__tests__/`, `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_setup_route.py`, add:

```python
@pytest.mark.asyncio
async def test_setup_accepts_a_provider_list(client, session):
    resp = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {
            "providers": [
                {"name": "my-ds", "api_kind": "deepseek",
                 "base_url": "https://api.deepseek.com/v1", "api_key": "sk-x"},
            ],
            "purposes": {
                "extraction": {"provider_name": "my-ds", "model": "deepseek-v4-flash"},
            },
        },
    })
    assert resp.status_code == 200
    row = (await session.execute(text(
        "SELECT provider_name FROM llm_purpose_configs WHERE purpose='extraction'"
    ))).scalar_one()
    assert row == "my-ds"
```

Match the existing setup-route test's request shape for the non-LLM fields.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_setup_route.py -q -k provider_list`
Expected: FAIL — `providers` is not a declared field.

- [ ] **Step 3: Widen the request schema**

In `setup.py`, add `providers: list[SetupProvider] = []` to the LLM block model, with

```python
class SetupProvider(BaseModel):
    name: str
    api_kind: Literal["openai", "anthropic", "ollama", "google", "deepseek", "zai"]
    base_url: str
    api_key: str | None = None
```

and give `SetupLLMPurpose` a `provider_name: str` field. Keep `PURPOSE_LITERAL` at six purposes — Task 7's test pins that.

In finalize, write `body.llm.providers` as `LLMProviderRow`s after the `DEFAULT_PROVIDER_ROWS` seed and before the purpose overlay, then set `pcfg.provider_name = spec.provider_name` in the overlay loop, replacing the `user_provider_name` block Task 2 added.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_setup_route.py tests/test_setup.py -q`
Expected: all pass.

- [ ] **Step 5: Rebuild StepLLM**

Add a `providers` array to `setupWizardStore.ts` and its zod schema in `schemas.ts`. In `StepLLM.tsx`, split into two sections: a provider editor (add/remove, with a "Test" button hitting `/api/v1/setup/probe-models` — the unauthenticated wizard probe, not the new authenticated one), and a purpose assignment grid where each of the six purposes picks a provider and a model from that provider's probed list. Submit both in the finalize payload.

- [ ] **Step 6: Run the frontend suite**

Run: `cd frontend && npm test && npm run typecheck && npm run build`
Expected: all clean.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(setup): define providers before assigning purposes"
```

---

### Task 11: The one-time deployment transition script

**Files:**
- Create: `backend/scripts/cutover/llm_providers_transition.py`, `backend/scripts/cutover/tests/test_llm_providers_transition.py`

**Interfaces:**
- Produces: `derive(rows: list[dict]) -> tuple[list[dict], list[dict]]` returning `(providers, purposes)`.

- [ ] **Step 1: Write the failing test**

```python
from scripts.cutover.llm_providers_transition import derive

OLD = [
    {"purpose": "embedding", "model": "qwen3-embedding:0.6b", "api_kind": "openai",
     "base_url": "http://192.168.0.196:11434/v1", "api_key": None,
     "dimensions": 1024, "reasoning": False, "params": {}, "classifier_kind": None},
    {"purpose": "extraction", "model": "deepseek-v4-flash", "api_kind": "deepseek",
     "base_url": "https://api.deepseek.com/v1", "api_key": "sk-a",
     "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
    {"purpose": "verification", "model": "gpt-5.5", "api_kind": "deepseek",
     "base_url": "https://api.deepseek.com/v1", "api_key": "sk-a",
     "dimensions": None, "reasoning": False, "params": {}, "classifier_kind": None},
]


def test_distinct_triples_become_distinct_providers():
    providers, _ = derive(OLD)
    assert len({p["name"] for p in providers}) == len(providers)


def test_verification_is_split_onto_its_own_provider():
    """Its base_url and api_kind are the judge's identity; sharing the row puts
    them behind an unrelated edit."""
    providers, purposes = derive(OLD)
    vp = next(p["provider_name"] for p in purposes if p["purpose"] == "verification")
    others = {p["provider_name"] for p in purposes if p["purpose"] != "verification"}
    assert vp not in others


def test_connection_values_are_carried_verbatim():
    providers, purposes = derive(OLD)
    by_name = {p["name"]: p for p in providers}
    for old in OLD:
        new = next(p for p in purposes if p["purpose"] == old["purpose"])
        provider = by_name[new["provider_name"]]
        assert provider["api_kind"] == old["api_kind"]
        assert provider["base_url"] == old["base_url"]
        assert provider["api_key"] == old["api_key"]


def test_derivation_is_deterministic():
    assert derive(OLD) == derive(OLD)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest scripts/cutover/tests/test_llm_providers_transition.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `backend/scripts/cutover/llm_providers_transition.py`. `derive` groups rows by `(api_kind, base_url, api_key)`, names each group `f"{api_kind}-{urlparse(base_url).hostname or 'local'}"` de-duplicated with a numeric suffix in sorted-triple order (so it is deterministic), splits `verification` onto its own group named with a `-judge` suffix even when its triple matches another, and returns provider dicts plus purpose dicts carrying `provider_name` and every non-connection field. Add a `main()` reading a JSON dump on stdin and emitting SQL `INSERT`s, printing to stderr what it derived.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest scripts/cutover/tests/test_llm_providers_transition.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add -A backend/scripts/cutover
git commit -m "feat(cutover): derive providers from inline purpose rows"
```

---

### Task 12: Documentation, cutover inventory, and the gate

Every doc listed here currently asserts something this change makes false. Leaving one is worse than not writing it — a future reader consults them first.

**Files:** `CLAUDE.md`, `backend/scripts/benchlib/FROZEN.md`, `backend/scripts/cutover/spec.py`, `backend/tests/test_cutover_transform.py:163-165`, `docs/runbook-deployment.md`, plus doc 04 §7 and doc 19 §3 under `docs/`.

- [ ] **Step 1: Amend CLAUDE.md**

In the "LLM configuration" section, replace "Each purpose is **one inline `llm_purpose_configs` row** … resolution is one row read and no joins" with the provider layer, the 2026-08-20 ruling, and the §9 freeze. Note explicitly that `api_key` on the judge's provider still rotates — that is the detail most likely to be lost.

- [ ] **Step 2: Amend FROZEN.md**

In "Bench-DB LLM seeding", replace the stale "(`provider_id`/`profile_id` left `NULL`)" sentence, add the two `BENCH_PROVIDERS` rows to the table it already carries, and state that the pinned model values did not move so no gate re-measurement is implied.

- [ ] **Step 3: Fix the cutover inventory**

In `backend/scripts/cutover/spec.py`, `llm_providers` already appears in `SOURCE_TABLES_A1` and in `DROPPED_TABLES` with the rationale "never exists in the baseline; the flattening is greenfield". Keep the historical source-table entry, but correct that rationale — the table now exists in the baseline with a different shape. Register the new target table separately. Update `test_cutover_transform.py:163-165` accordingly.

- [ ] **Step 4: Amend the deployment runbook**

In `docs/runbook-deployment.md`: add `--table=llm_providers` to the step-2 dump; retitle "Two rows a re-seed does not reproduce" to three and add the judge's provider row; add a subsection for the one-time transition pointing at `scripts/cutover/llm_providers_transition.py` and stating plainly that the existing step-6 restore **cannot** carry this deploy (old-schema dump into new schema, zero provider rows); and record that the restored `verification` purpose must point at a provider no other purpose references.

- [ ] **Step 5: Amend the design docs**

Update doc 04 §7 and doc 19 §3 to record the reversal with its date and the spec path, rather than deleting the original argument — the reasoning for the flattening is still why the resolved object stayed flat.

- [ ] **Step 6: Run the merge gate**

Run: `cd /root/repositories/darkmem && ./scripts/gate.sh`
Expected: exit 0. `GATE BLOCKED` (exit 2) means a missing toolchain, not a red gate. Do **not** pass `--full` — it makes live LLM calls.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs(llm): record the provider layer and its deploy path"
```

---

## Notes for the executor

- **If the judge-identity pin (Task 3 Step 6) fails, stop and report.** Do not adjust the expected hash to make it pass. It is the instrument, not the subject.
- **Never seed a real API key into a test, fixture, or doc.** `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` come from the environment; `.claude/local-credentials.md` holds them and is gitignored.
- Tasks 1–4 each edit `0001_baseline.py`. Confirm `./scripts/gate.sh`'s single-revision assertion still holds by checking `ls backend/migrations/versions/` shows exactly one file.
- Give every test and build command an explicit timeout, and kill anything long-lived you start.
