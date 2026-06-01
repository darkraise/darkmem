# Centralize Workers into the Jobs Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Settings → Workers tab and make the Jobs page the single surface for every background job and its settings, via a generic per-job config mechanism (`code_enrichment` exposes `batch_size`).

**Architecture:** Add an optional `config: dict` to each job's persisted `JobConfig` and a static `config_schema` (list of typed field descriptors) to `Job`. A new `PUT /api/v1/jobs/{key}/config` validates against the schema and merges into the `job:<key>` row. The runner reads `batch_size` from job config. The frontend opens a per-row "Configure" Dialog (the darkraise-ui `DataTable` has no expandable-row API). The legacy `/config/enrichment` routes and the Settings Workers tab are deleted; `batch_size` is migrated into job config on startup.

**Tech Stack:** Backend FastAPI + SQLAlchemy async + pytest; frontend React + TanStack Query/Table + darkraise-ui + vitest. The full design is in `docs/superpowers/specs/2026-06-01-centralize-workers-into-jobs-design.md` (rev 3).

---

## File Structure

**Backend**
- `backend/app/services/job_registry.py` — add `FieldDescriptor` (Pydantic), `JobConfig.config`, `Job.config_schema` + `default_config`, `set_config`, `config_schema` injection in `list_with_config`.
- `backend/app/api/routes/jobs.py` — `JobItem` gains `config`/`config_schema`; new `PUT /{key}/config`; module docstring.
- `backend/app/services/job_runners.py` — `make_code_enrichment_runner` reads `batch_size` from job config (lazy `app.state.job_registry`).
- `backend/app/main.py` — `code_enrichment` `config_schema`, description text, startup `batch_size` migration.
- `backend/app/api/routes/config.py` — delete the `/enrichment` routes + `EnrichmentConfigUpdate` + the enabled-mirror.
- `backend/app/services/enrichment_worker.py` — remove dead `run_loop`/`stop`/`_running`/`interval`.
- `docs/e2e/scripts/02_config_flow.py` — drop the enrichment assertion + docstring mention.
- Tests: `backend/tests/test_job_registry.py`, `backend/tests/test_jobs_route.py`.

**Frontend**
- `frontend/src/hooks/api/use-jobs-api.ts` — `FieldDescriptor` type, `Job.config`/`config_schema`, `useUpdateJobConfig`.
- `frontend/src/routes/_authenticated/jobs.tsx` — `JobConfigForm` + `ConfigCell` (gear Dialog) in the actions cell.
- `frontend/src/routes/_authenticated/settings.tsx` — remove `EnrichmentCard`, the `workers` tab, PageHeader copy, enrichment-hook imports.
- `frontend/src/lib/settings-tab.ts` — remove `"workers"`.
- `frontend/src/lib/__tests__/settings-tab.test.ts` — `workers → flags` assertion.
- `frontend/src/routes/_authenticated/repos.tsx` — repoint Run Enrichment to `useTriggerJob`.
- `frontend/src/hooks/api/use-config-api.ts` — remove the 3 enrichment hooks + `EnrichmentConfig`.

**Sequence:** backend (Tasks 1–8) lands and stays green first, then frontend (Tasks 9–15).

---

## Phase 1 — Backend

### Task 1: `JobConfig.config` round-trips

**Files:**
- Modify: `backend/app/services/job_registry.py` (`JobConfig`, lines 75-104)
- Test: `backend/tests/test_job_registry.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_job_registry.py`:

```python
def test_job_config_round_trips_config_dict():
    from app.services.job_registry import JobConfig

    cfg = JobConfig(enabled=True, cron="*/5 * * * *", min_interval_seconds=1,
                    config={"batch_size": 17})
    assert cfg.to_dict()["config"] == {"batch_size": 17}
    assert JobConfig.from_dict(cfg.to_dict()).config == {"batch_size": 17}


def test_job_config_from_dict_defaults_config_to_empty():
    from app.services.job_registry import JobConfig

    cfg = JobConfig.from_dict({"enabled": True, "cron": "*/5 * * * *",
                               "min_interval_seconds": 1})
    assert cfg.config == {}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_job_registry.py::test_job_config_round_trips_config_dict -v`
Expected: FAIL (`JobConfig` has no `config` argument).

- [ ] **Step 3: Add the field + serialization**

In `JobConfig` add a field after `last_error` and include it in both methods:

```python
@dataclass
class JobConfig:
    enabled: bool
    cron: str
    min_interval_seconds: int
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "cron": self.cron,
            "min_interval_seconds": self.min_interval_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobConfig":
        last_run = data.get("last_run_at")
        return cls(
            enabled=bool(data.get("enabled", False)),
            cron=str(data.get("cron", "*/5 * * * *")),
            min_interval_seconds=int(data.get("min_interval_seconds", 1)),
            last_run_at=datetime.fromisoformat(last_run) if last_run else None,
            last_status=data.get("last_status"),
            last_error=data.get("last_error"),
            config=data.get("config") or {},
        )
```

`field` is already imported (`from dataclasses import dataclass, field`); confirm at the top of the file and add `field` to the import if missing.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_job_registry.py -k job_config -v`
Expected: PASS (the two new tests plus the existing ones at lines 51-67).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_registry.py backend/tests/test_job_registry.py
git commit -m "feat(jobs): add config dict to JobConfig with round-trip"
```

---

### Task 2: `FieldDescriptor` + `Job.config_schema` / `default_config`

**Files:**
- Modify: `backend/app/services/job_registry.py` (imports; `Job` dataclass, lines 107-118)
- Test: `backend/tests/test_job_registry.py`

- [ ] **Step 1: Write the failing test**

```python
def test_job_default_config_from_schema():
    from app.services.job_registry import Job, FieldDescriptor

    async def _noop():
        return None

    job = Job(
        key="x", display_name="X", description="d",
        default_cron="*/5 * * * *", min_interval_seconds=1, runner=_noop,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    )
    assert job.default_config == {"batch_size": 5}
    assert job.config_schema[0].type == "int"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_job_registry.py::test_job_default_config_from_schema -v`
Expected: FAIL (no `FieldDescriptor`, no `config_schema`).

- [ ] **Step 3: Implement**

Add a Pydantic import near the top of `job_registry.py`:

```python
from pydantic import BaseModel
```

Define `FieldDescriptor` just above the `JobConfig` dataclass:

```python
class FieldDescriptor(BaseModel):
    """A single per-job config field the UI renders generically."""
    key: str
    type: str = "int"
    label: str
    default: int
    min: int | None = None
    max: int | None = None
    step: int | None = 1
    help: str | None = None
```

Extend the `Job` dataclass (add the field before the live-wiring fields and add the property):

```python
@dataclass
class Job:
    key: str
    display_name: str
    description: str
    default_cron: str
    min_interval_seconds: int
    runner: JobRunner
    config_schema: list[FieldDescriptor] = field(default_factory=list)
    # Live wiring filled in by the registry at start().
    task: asyncio.Task | None = field(default=None, init=False, repr=False)
    wakeup: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @property
    def default_config(self) -> dict:
        return {fd.key: fd.default for fd in self.config_schema}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_job_registry.py::test_job_default_config_from_schema -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_registry.py backend/tests/test_job_registry.py
git commit -m "feat(jobs): add FieldDescriptor and Job.config_schema/default_config"
```

---

### Task 3: `set_config` (lock + validate + merge)

**Files:**
- Modify: `backend/app/services/job_registry.py` (new method in the operations section, after `update_config`)
- Test: `backend/tests/test_job_registry.py`

- [ ] **Step 1: Write the failing tests**

Add a fixture-free async test using an in-memory-ish registry against the test DB. Reuse the existing test harness pattern (the file already constructs registries against `settings.test_database_url`; if a helper exists, follow it). Minimal version:

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.config import settings


def _schema_registry():
    from app.services.job_registry import Job, JobRegistry, FieldDescriptor
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    reg = JobRegistry(factory)

    async def _noop():
        return None

    reg.register(Job(
        key="cfgjob", display_name="Cfg", description="d",
        default_cron="*/5 * * * *", min_interval_seconds=1, runner=_noop,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    ))
    return reg, engine


@pytest.mark.asyncio
async def test_set_config_merges_and_validates():
    reg, engine = _schema_registry()
    try:
        cfg = await reg.set_config("cfgjob", {"batch_size": 20})
        assert cfg.config["batch_size"] == 20
        # unknown key rejected
        with pytest.raises(ValueError):
            await reg.set_config("cfgjob", {"nope": 1})
        # out-of-range rejected
        with pytest.raises(ValueError):
            await reg.set_config("cfgjob", {"batch_size": 999})
    finally:
        await reg.stop_all()
        await engine.dispose()


@pytest.mark.asyncio
async def test_config_survives_trigger_and_toggle():
    reg, engine = _schema_registry()
    try:
        await reg.set_config("cfgjob", {"batch_size": 33})
        await reg.trigger("cfgjob")                       # load->mutate->save path
        assert (await reg.load_config("cfgjob")).config["batch_size"] == 33
        await reg.update_config("cfgjob", enabled=False)  # enabled toggle path
        assert (await reg.load_config("cfgjob")).config["batch_size"] == 33
        await reg.update_config("cfgjob", cron="*/2 * * * *")  # cron save path
        assert (await reg.load_config("cfgjob")).config["batch_size"] == 33
    finally:
        await reg.stop_all()
        await engine.dispose()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_job_registry.py -k set_config -v`
Expected: FAIL (`set_config` not defined).

- [ ] **Step 3: Implement `set_config`**

Add after `update_config` in `JobRegistry`:

```python
async def set_config(self, key: str, partial: dict) -> JobConfig:
    if key not in self._jobs:
        raise KeyError(key)
    job = self._jobs[key]
    schema = {fd.key: fd for fd in job.config_schema}
    for field_key, value in partial.items():
        fd = schema.get(field_key)
        if fd is None:
            raise ValueError(f"Unknown config key {field_key!r} for job {key!r}")
        if fd.type == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"Config {field_key!r} must be an integer")
            if fd.min is not None and value < fd.min:
                raise ValueError(f"Config {field_key!r} must be >= {fd.min}")
            if fd.max is not None and value > fd.max:
                raise ValueError(f"Config {field_key!r} must be <= {fd.max}")
    # Share the per-job lock with _run_once so a save can't be clobbered
    # by a concurrent scheduled run.
    async with job.lock:
        cfg = await self.load_config(key)
        cfg.config = {**cfg.config, **partial}
        await self.save_config(key, cfg)
    return cfg
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_job_registry.py -k "set_config or survives" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_registry.py backend/tests/test_job_registry.py
git commit -m "feat(jobs): registry set_config with schema validation under job.lock"
```

---

### Task 4: `list_with_config` emits `config` (merged over defaults) + `config_schema`

**Files:**
- Modify: `backend/app/services/job_registry.py` (`list_with_config`, lines 187-208)
- Test: `backend/tests/test_job_registry.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_list_with_config_emits_schema_and_merged_config():
    reg, engine = _schema_registry()
    try:
        items = await reg.list_with_config()
        item = next(i for i in items if i["key"] == "cfgjob")
        # schema descriptors present
        assert item["config_schema"][0]["key"] == "batch_size"
        # config defaults applied even with no saved row
        assert item["config"] == {"batch_size": 5}
        await reg.set_config("cfgjob", {"batch_size": 42})
        item = next(i for i in (await reg.list_with_config()) if i["key"] == "cfgjob")
        assert item["config"] == {"batch_size": 42}
    finally:
        await reg.stop_all()
        await engine.dispose()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_job_registry.py::test_list_with_config_emits_schema_and_merged_config -v`
Expected: FAIL (`KeyError: 'config_schema'`).

- [ ] **Step 3: Implement**

Replace the `out.append({...})` block in `list_with_config` with one that adds `config_schema` and overrides `config` with the defaults-merged value (since `**cfg.to_dict()` already carries the raw `config`):

```python
            running = job.task is not None and not job.task.done()
            item = {
                "key": job.key,
                "display_name": job.display_name,
                "description": job.description,
                "default_cron": job.default_cron,
                "min_interval_seconds": job.min_interval_seconds,
                "running": running,
                "config_schema": [fd.model_dump() for fd in job.config_schema],
                **cfg.to_dict(),
            }
            item["config"] = {**job.default_config, **cfg.config}
            out.append(item)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_job_registry.py -k list_with_config -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_registry.py backend/tests/test_job_registry.py
git commit -m "feat(jobs): list_with_config emits config_schema and merged config"
```

---

### Task 5: `JobItem` fields + `PUT /api/v1/jobs/{key}/config`

**Files:**
- Modify: `backend/app/api/routes/jobs.py` (docstring; `JobItem`; new route)
- Test: `backend/tests/test_jobs_route.py`

- [ ] **Step 1: Add a schema-bearing job to the route-test fixture, then write failing tests**

In `backend/tests/test_jobs_route.py`, register a third job inside the `stubbed_jobs` fixture (after the `beta` registration, before `prev_registry = ...`):

```python
    from app.services.job_registry import FieldDescriptor

    async def gamma_runner():
        calls.setdefault("gamma", 0)
        calls["gamma"] += 1

    registry.register(Job(
        key="gamma",
        display_name="Gamma",
        description="Has config.",
        default_cron="*/10 * * * *",
        min_interval_seconds=10,
        runner=gamma_runner,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    ))
```

Add tests:

```python
@pytest.mark.asyncio
async def test_list_jobs_includes_config_schema(stubbed_jobs, client, auth_headers):
    response = await client.get("/api/v1/jobs", headers=auth_headers)
    gamma = next(j for j in response.json()["jobs"] if j["key"] == "gamma")
    assert gamma["config"] == {"batch_size": 5}
    assert gamma["config_schema"][0]["key"] == "batch_size"


@pytest.mark.asyncio
async def test_update_job_config_saves_value(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"batch_size": 25}}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["config"]["batch_size"] == 25


@pytest.mark.asyncio
async def test_update_job_config_rejects_unknown_key(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"nope": 1}}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_job_config_rejects_out_of_range(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"batch_size": 999}}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_job_config_unknown_job_404(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/missing/config",
                         json={"config": {"batch_size": 5}}, headers=auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && pytest tests/test_jobs_route.py -k config -v`
Expected: FAIL (404/422 route missing → 405 or KeyError; list lacks `config_schema`).

- [ ] **Step 3: Implement the route + model**

In `backend/app/api/routes/jobs.py`: import `FieldDescriptor`, extend `JobItem`, add `JobConfigUpdate`, add the route, and update the module docstring to list four endpoints.

```python
from app.services.job_registry import FieldDescriptor
```

```python
class JobItem(BaseModel):
    key: str
    display_name: str
    description: str
    enabled: bool
    cron: str
    min_interval_seconds: int
    default_cron: str
    last_run_at: str | None = None
    last_status: str | None = None
    last_error: str | None = None
    running: bool
    config: dict = {}
    config_schema: list[FieldDescriptor] = []


class JobConfigUpdate(BaseModel):
    config: dict
```

```python
@router.put("/{key}/config", response_model=JobItem)
async def update_job_config(
    key: str,
    body: JobConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
) -> JobItem:
    registry = _get_registry(request)
    if registry.get(key) is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {key!r}")
    try:
        await registry.set_config(key, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    items = await registry.list_with_config()
    item = next((i for i in items if i["key"] == key), None)
    if item is None:
        raise HTTPException(status_code=500, detail=f"Job {key!r} disappeared mid-update")
    return JobItem(**item)
```

Update the docstring at the top (line 3-7) to add:

```python
* ``PUT  /api/v1/jobs/{key}/config`` — update per-job config values.
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd backend && pytest tests/test_jobs_route.py -v`
Expected: PASS (new config tests + the existing alpha/beta tests stay green).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/jobs.py backend/tests/test_jobs_route.py
git commit -m "feat(jobs): PUT /jobs/{key}/config endpoint + config in JobItem"
```

---

### Task 6: Runner reads `batch_size` from job config

**Files:**
- Modify: `backend/app/services/job_runners.py` (`make_code_enrichment_runner`, lines 105-131)

- [ ] **Step 1: Update the runner to read job config lazily**

Replace the `enrichment_config` read block (lines 122-130) with a lazy registry read:

```python
    async def run() -> None:
        from app.services.enrichment_worker import EnrichmentWorker
        from app.api.websocket import event_manager

        llm = getattr(app.state, "llm", None)
        if not llm:
            logger.info("code_enrichment skipped: no LLM orchestrator")
            return

        # app.state.job_registry is wired after this runner is constructed,
        # so read it lazily here, not at construction time.
        registry = getattr(app.state, "job_registry", None)
        batch_size = 5
        if registry is not None:
            cfg = await registry.load_config("code_enrichment")
            batch_size = int(cfg.config.get("batch_size", 5))

        worker = EnrichmentWorker(llm, broadcast=event_manager.broadcast)
        await worker.process_batch(batch_size=batch_size)
    return run
```

Update the docstring of `make_code_enrichment_runner` to say it reads `batch_size` from the `code_enrichment` job config (drop the "legacy enrichment_config row" mention). Remove the now-unused `ConfigModel`/`select` imports inside the function if they are no longer referenced.

- [ ] **Step 2: Verify backend still imports/builds**

Run: `cd backend && python -c "import app.services.job_runners"`
Expected: no ImportError.

- [ ] **Step 3: Run the registry + route suites**

Run: `cd backend && pytest tests/test_job_registry.py tests/test_jobs_route.py -q`
Expected: PASS (no regressions).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/job_runners.py
git commit -m "feat(jobs): code_enrichment runner reads batch_size from job config"
```

---

### Task 7: Register `code_enrichment` config_schema + startup migration

**Files:**
- Modify: `backend/app/main.py` (lines 179-190 registration; add migration before `start_all`)

- [ ] **Step 1: Declare the schema on the job**

Add the import near the other registry imports and update the `code_enrichment` registration:

```python
    from app.services.job_registry import FieldDescriptor
```

```python
    job_registry.register(Job(
        key="code_enrichment",
        display_name="Code Symbol Enrichment",
        description=(
            "Runs one batch of LLM summarisation against pending code "
            "symbols (function / class / method docs)."
        ),
        default_cron="*/10 * * * * *",
        min_interval_seconds=1,
        runner=make_code_enrichment_runner(app, async_session_factory),
        config_schema=[FieldDescriptor(
            key="batch_size", label="Batch Size", default=5,
            min=1, max=100,
            help="Code symbols summarised per scheduled run.",
        )],
    ))
```

- [ ] **Step 2: Add the idempotent startup migration**

Just before `app.state.job_registry = job_registry` (line 221), add:

```python
    # One-time copy of the legacy enrichment_config.batch_size into the
    # code_enrichment job config, if not already set. Tolerates an absent
    # enrichment_config row (it was created lazily by the removed
    # PUT /config/enrichment, so most installs never had it).
    _ce_cfg = await job_registry.load_config("code_enrichment")
    if "batch_size" not in _ce_cfg.config:
        from app.models.config import Config as _Config
        from sqlalchemy import select as _select
        async with async_session_factory() as _s:
            _row = (await _s.execute(
                _select(_Config).where(_Config.key == "enrichment_config")
            )).scalar_one_or_none()
        _legacy = _row.value if _row and isinstance(_row.value, dict) else {}
        await job_registry.set_config(
            "code_enrichment", {"batch_size": int(_legacy.get("batch_size", 5))}
        )
```

- [ ] **Step 3: Smoke-test app import + startup**

Run: `cd backend && python -c "import app.main"`
Expected: no ImportError.
Run the backend test suite: `cd backend && pytest -q`
Expected: PASS (no test asserts the old description text; if one does, update it).

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(jobs): code_enrichment config_schema + batch_size startup migration"
```

---

### Task 8: Delete the `/config/enrichment` surface + worker dead code + e2e

**Files:**
- Modify: `backend/app/api/routes/config.py` (delete `EnrichmentConfigUpdate` ~908-910; `GET` ~913-926; `PUT` ~929-960 incl. the `job_registry.update_config("code_enrichment", enabled=...)` mirror ~951; `POST /enrichment/trigger` ~1085-1112)
- Modify: `backend/app/services/enrichment_worker.py` (remove `run_loop` 98-113, `stop` 115-116, `_running` 24, `interval` 26)
- Modify: `docs/e2e/scripts/02_config_flow.py` (remove the `GET /config/enrichment` block ~104-111; fix the docstring at line 3)

- [ ] **Step 1: Delete the enrichment routes + model**

Remove the `EnrichmentConfigUpdate` Pydantic model and the three route handlers (`get_enrichment_config`, `update_enrichment_config`, `trigger_enrichment`) from `config.py`. Grep to confirm nothing else references them:

Run: `cd backend && rg -n "enrichment_config|EnrichmentConfigUpdate|/enrichment" app`
Expected: only `job_runners.py` historical comments (now updated) and no route definitions remain. Confirm `from app...config import EnrichmentConfigUpdate` has no importers.

- [ ] **Step 2: Remove the worker dead code**

In `enrichment_worker.py` delete `run_loop` (lines 98-113) and `stop` (115-116); in `__init__` remove `self._running = False` and `self.interval = 10`. Keep `self.batch_size = 5` (used by `process_batch` line 34) and `self._broadcast`.

- [ ] **Step 3: Fix the e2e script**

In `docs/e2e/scripts/02_config_flow.py` remove the block that does `client.get("/api/v1/config/enrichment")` and its assertion (lines 104-111), and edit the module docstring (line 3) to drop "enrichment config".

- [ ] **Step 4: Verify backend green**

Run: `cd backend && pytest -q`
Expected: PASS. Run `cd backend && python -c "import app.main"` — no ImportError.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/config.py backend/app/services/enrichment_worker.py docs/e2e/scripts/02_config_flow.py
git commit -m "refactor(jobs): delete /config/enrichment surface and worker dead code"
```

---

## Phase 2 — Frontend

### Task 9: Job type + `FieldDescriptor` + `useUpdateJobConfig`

**Files:**
- Modify: `frontend/src/hooks/api/use-jobs-api.ts`

- [ ] **Step 1: Add the types and hook**

Add `FieldDescriptor`, extend `Job` (optional fields so a pre-deploy backend can't crash the table), and add the mutation:

```typescript
export interface FieldDescriptor {
  key: string
  type: "int"
  label: string
  default: number
  min?: number
  max?: number
  step?: number
  help?: string
}
```

Add to the `Job` interface (after `running`):

```typescript
  config?: Record<string, number>
  config_schema?: FieldDescriptor[]
```

Add the hook after `useTriggerJob`:

```typescript
export function useUpdateJobConfig() {
  const qc = useQueryClient()
  return useMutation<Job, Error, { key: string; config: Record<string, number> }>({
    mutationFn: ({ key, config }) =>
      apiFetch<Job>(`/jobs/${key}/config`, {
        method: "PUT",
        body: JSON.stringify({ config }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}
```

- [ ] **Step 2: Verify typecheck**

Run: `cd frontend && npm run typecheck`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-jobs-api.ts
git commit -m "feat(jobs): Job config types and useUpdateJobConfig hook"
```

---

### Task 10: `JobConfigForm` + `ConfigCell` (gear Dialog) on the Jobs page

**Files:**
- Modify: `frontend/src/routes/_authenticated/jobs.tsx`

- [ ] **Step 1: Add imports**

Add to the existing imports:

```typescript
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "darkraise-ui/components/dialog"
import {
  NumberInput,
  NumberInputControl,
  NumberInputField,
  NumberInputTriggerGroup,
  NumberInputIncrementTrigger,
  NumberInputDecrementTrigger,
} from "darkraise-ui/components/number-input"
import { Label } from "darkraise-ui/components/label"
import {
  useJobs,
  useUpdateJob,
  useTriggerJob,
  useUpdateJobConfig,
  type Job,
  type FieldDescriptor,
} from "@/hooks/api"
```

Replace the existing `useJobs/useUpdateJob/useTriggerJob/Job` import line with the expanded one above, and **merge** `Settings` into the existing lucide import (so there is no duplicate module import):

```typescript
import { Play, Save, Settings } from "lucide-react"
```

- [ ] **Step 2: Add `JobConfigForm` + `ConfigCell` components**

Add above the `columns` definition. `ConfigCell` is keyed by `open` so the draft re-seeds each time the Dialog opens (re-mounts `JobConfigForm`), mirroring NumericRow's re-sync:

```typescript
function JobConfigForm({
  job,
  schema,
  onClose,
}: {
  job: Job
  schema: FieldDescriptor[]
  onClose: () => void
}) {
  const updateConfig = useUpdateJobConfig()
  const [draft, setDraft] = useState<Record<string, number>>(() =>
    Object.fromEntries(
      schema.map((f) => [f.key, (job.config?.[f.key] as number) ?? f.default]),
    ),
  )

  const handleSave = () => {
    updateConfig.mutate(
      { key: job.key, config: draft },
      {
        onSuccess: () => {
          toast.success(`${job.display_name} settings saved`)
          onClose()
        },
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  return (
    <div className="space-y-4">
      {schema.map((field) => (
        <div key={field.key} className="space-y-1">
          <Label className="text-base">{field.label}</Label>
          <NumberInput
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
            value={draft[field.key]}
            onValueChange={(d) =>
              setDraft((prev) => ({ ...prev, [field.key]: d.valueAsNumber }))
            }
          >
            <NumberInputControl>
              <NumberInputField />
              <NumberInputTriggerGroup>
                <NumberInputIncrementTrigger />
                <NumberInputDecrementTrigger />
              </NumberInputTriggerGroup>
            </NumberInputControl>
          </NumberInput>
          {field.help && (
            <p className="text-muted-foreground text-sm">{field.help}</p>
          )}
        </div>
      ))}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={updateConfig.isPending}>
          {updateConfig.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  )
}

function ConfigCell({ job }: { job: Job }) {
  const [open, setOpen] = useState(false)
  const schema = job.config_schema ?? []
  if (schema.length === 0) return null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label={`Configure ${job.display_name}`}
        >
          <Settings className="h-3.5 w-3.5" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configure {job.display_name}</DialogTitle>
        </DialogHeader>
        {open && (
          <JobConfigForm job={job} schema={schema} onClose={() => setOpen(false)} />
        )}
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 3: Render the gear in the actions cell (keep 8 columns)**

Replace the `actions` column cell so it hosts both the gear and the trigger:

```typescript
  {
    id: "actions",
    header: "",
    size: 110,
    cell: ({ row }) => (
      <div className="flex items-center justify-end gap-1">
        <ConfigCell job={row.original} />
        <TriggerCell job={row.original} />
      </div>
    ),
  },
```

Leave `DataTableSkeleton columnCount={8}` unchanged.

- [ ] **Step 4: Verify typecheck + build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: PASS / built.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/_authenticated/jobs.tsx
git commit -m "feat(jobs): per-row Configure dialog with generic JobConfigForm"
```

---

### Task 11: Repoint the Repositories "Run Enrichment" button

**Files:**
- Modify: `frontend/src/routes/_authenticated/repos.tsx` (import line 11; hook at 259; button at 451-464)

- [ ] **Step 1: Swap the hook + mutate call + toast**

Remove `useTriggerEnrichment` from the imports. Add `useTriggerJob` (from `@/hooks/api`) and `useQueryClient` (from `@tanstack/react-query`) if not already imported. Replace the hook instantiation:

```typescript
  const triggerJob = useTriggerJob()
  const qc = useQueryClient()
```

Replace the button's `onClick` body (the `triggerEnrichment.mutate(...)` call):

```typescript
  const handleRunEnrichment = () => {
    triggerJob.mutate("code_enrichment", {
      onSuccess: () => {
        toast.success("Enrichment run started")
        qc.invalidateQueries({ queryKey: ["repoStats"] })
      },
      onError: (err) => toast.error(`Failed: ${err.message}`),
    })
  }
```

Update the button to use `triggerJob.isPending` instead of `triggerEnrichment.isPending`.

- [ ] **Step 2: Verify typecheck**

Run: `cd frontend && npm run typecheck`
Expected: PASS (no remaining `useTriggerEnrichment` reference).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_authenticated/repos.tsx
git commit -m "refactor(repos): repoint Run Enrichment to the code_enrichment job trigger"
```

---

### Task 12: Remove the Settings Workers tab + EnrichmentCard

**Files:**
- Modify: `frontend/src/routes/_authenticated/settings.tsx` (EnrichmentCard 69-156; imports 4-6; SETTINGS_TABS 667; TabsContent 714-716; PageHeader 693)

- [ ] **Step 1: Delete the card, tab, and copy**

- Delete the inline `EnrichmentCard` function (lines 69-156) and the `useEnrichmentConfig` / `useUpdateEnrichmentConfig` / `useTriggerEnrichment` imports (lines 4-6). Keep the `NumberInput*` imports — `NumericRow` still uses them.
- Remove the `{ value: "workers", label: "Workers" }` entry from `SETTINGS_TABS` (line 667).
- Remove the `<TabsContent value="workers">...<EnrichmentCard /></TabsContent>` block (lines 714-716).
- Update the `PageHeader` description (line 693) to drop the word "workers".

- [ ] **Step 2: Verify typecheck + build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: PASS (no dangling `EnrichmentCard` / enrichment-hook references).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_authenticated/settings.tsx
git commit -m "refactor(settings): remove the Workers tab and EnrichmentCard"
```

---

### Task 13: Remove the `workers` SettingsTabValue + regression test

**Files:**
- Modify: `frontend/src/lib/settings-tab.ts`
- Test: `frontend/src/lib/__tests__/settings-tab.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `settings-tab.test.ts`:

```typescript
it("falls back to flags for the removed workers tab", () => {
  expect(resolveStoredTab("workers")).toBe("flags")
})
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/settings-tab.test.ts`
Expected: FAIL (`resolveStoredTab("workers")` returns `"workers"`).

- [ ] **Step 3: Remove `workers` from the union and KNOWN**

In `settings-tab.ts` delete `"workers"` from both the `SettingsTabValue` union (line 4) and the `KNOWN` array (line 12).

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/lib/__tests__/settings-tab.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/settings-tab.ts frontend/src/lib/__tests__/settings-tab.test.ts
git commit -m "refactor(settings): drop the workers tab value with fallback test"
```

---

### Task 14: Remove the enrichment hooks + type from the api layer

**Files:**
- Modify: `frontend/src/hooks/api/use-config-api.ts` (lines 281-315)

- [ ] **Step 1: Delete the dead exports**

Remove the `EnrichmentConfig` interface and the `useEnrichmentConfig`, `useUpdateEnrichmentConfig`, and `useTriggerEnrichment` functions (lines 281-315). Grep to confirm no importers remain:

Run: `cd frontend && rg -n "useEnrichmentConfig|useUpdateEnrichmentConfig|useTriggerEnrichment|EnrichmentConfig" src`
Expected: no matches.

- [ ] **Step 2: Verify typecheck + build + unit suite**

Run: `cd frontend && npm run typecheck && npm run build && npm run test`
Expected: PASS / built / all tests green.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-config-api.ts
git commit -m "refactor(api): remove the dead enrichment config hooks"
```

---

### Task 15: Full verification sweep

- [ ] **Step 1: Backend**

Run: `cd backend && pytest -q`
Expected: PASS.

- [ ] **Step 2: Frontend**

Run: `cd frontend && npm run typecheck && npm run build && npm run test`
Expected: PASS / built / unit suite green.

- [ ] **Step 3: Grep for leftovers**

Run: `cd backend && rg -n "enrichment_config|/config/enrichment" app && cd ../frontend && rg -n "Enrichment(Config|Card)|workers" src/routes/_authenticated/settings.tsx`
Expected: no live references (only updated comments, if any).

- [ ] **Step 4: Manual smoke (recommended, needs the running app)**

Open the Jobs page, click the gear on **Code Symbol Enrichment**, confirm the Batch Size dialog opens, change it, Save, and reopen to confirm persistence. Confirm Settings has no Workers tab and the Repositories "Run Enrichment" button toasts "Enrichment run started".

---

## Notes for the implementer

- Run backend commands from `backend/` and frontend commands from `frontend/`.
- Keep commits atomic per task; do not squash phases together.
- If a backend test fixture other than `stubbed_jobs` needs the new `config`/`config_schema` fields, default them (`config={}`, `config_schema=[]`) — both are optional on `JobConfig`/`Job`.
- The `enrichment_config` DB row is intentionally left in place (unused) after migration; no Alembic change is required.
