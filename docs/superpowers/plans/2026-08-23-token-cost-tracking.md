# Token and Cost Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record what every LLM call costs, attribute it to the memory, job run, search, chat or maintenance operation that caused it, and surface totals plus outliers so wasted spend can be found and removed.

**Architecture:** A `UsageRecorder` wraps the six vendor request paths inside `LLMOrchestrator` — the only module in `backend/app` that spends tokens — capturing successes and failures alike onto a dedicated `llm_usage` table on its own session. Attribution is an explicit subject passed by whoever owns the work, with an ambient contextvar only where one scope genuinely wraps many calls. Cost is computed from a shipped-and-overridable price table at call time and stored with the rates used.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0 async, Alembic, Postgres 17, pytest; React 19 + TanStack Query + darkraise-ui on the frontend.

**Spec:** `docs/superpowers/specs/2026-08-23-token-cost-tracking-design.md`

## Global Constraints

- **The schema is ONE revision.** A schema change regenerates `backend/migrations/versions/0001_baseline.py` in place and never appends `0002`. `scripts/gate.sh` asserts exactly one revision.
- **No vendor literals outside `llm_quirks.py`.** `tests/test_api_kind_dispatch.py:264` walks every module under `app/` and fails the build on any `ast.Compare` containing a vendor-name string.
- **Money is an integer.** `cost_micros` is micro-USD as `BigInteger`. Never float.
- **`tokens_measured=false` is not zero**, and a local model's measured `$0` is not "unpriced". Four distinct states: priced, free, unpriced, unmeasured.
- **Usage rows commit on their own session**, never the caller's — the pipeline's savepoints would roll back the failed-work rows.
- **The recorder never raises into the LLM path.** Degrade loudly, mirroring `record_event`.
- **Run the gate before every commit that touches `backend/` or `frontend/`:** `./scripts/gate.sh` from the repo root.
- Backend tests: `cd backend && python -m pytest -q`. Frontend: `cd frontend && npm run typecheck && npm test`.

---

## File Structure

**Created**
- `backend/app/models/llm_usage.py` — the ORM row. One responsibility: the shape.
- `backend/app/services/usage_pricing.py` — pure price/cost arithmetic. No I/O, no session.
- `backend/app/services/usage_recorder.py` — the recorder: subject contextvar, row construction, independent-session write.
- `backend/app/repositories/usage_repository.py` — all aggregation SQL for the read API.
- `backend/app/api/routes/usage.py` — the four read endpoints.
- `backend/app/schemas/usage.py` — response models.
- `frontend/src/features/usage/` — overview surface, per-subject panel, prices settings panel.
- Tests mirroring each of the above under `backend/tests/` and `frontend/src/features/usage/__tests__/`.

**Modified**
- `backend/app/services/llm_quirks.py` — two new `VendorQuirks` fields.
- `backend/app/services/llm.py` — read the discarded usage envelopes; wrap six paths.
- `backend/app/services/pipeline.py` — thread the memory id into the Phase-2 closures.
- `backend/app/services/job_registry.py` — set the ambient job subject around a run.
- `backend/app/services/chat.py`, retrieval request scope, `api/routes/reembed.py`, `api/routes/repos.py` — set their subjects.
- `backend/app/main.py` — register `llm_usage_cleanup`; mount the usage router.
- `backend/migrations/versions/0001_baseline.py` — regenerated.
- `backend/tests/test_code_deriver.py` — roster pin.
- `CLAUDE.md` — registered-job count.

---

### Task 1: The `llm_usage` row and the regenerated baseline

**Files:**
- Create: `backend/app/models/llm_usage.py`
- Modify: `backend/migrations/versions/0001_baseline.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_llm_usage_model.py`

**Interfaces:**
- Produces: `LLMUsage` ORM class, table `llm_usage`, columns exactly as listed in step 3.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm_usage_model.py
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select

from app.models.llm_usage import LLMUsage


@pytest.mark.asyncio
async def test_row_round_trips_with_unmeasured_tokens(session):
    """An unmeasured call stores NULL tokens, not zeros: a vendor that stops
    reporting usage must never render as a free model."""
    row = LLMUsage(
        occurred_at=datetime.now(timezone.utc),
        purpose="extraction",
        model="deepseek-v4-flash",
        provider="deepseek-main",
        api_kind="deepseek",
        subject_type="memory",
        subject_id=str(uuid.uuid4()),
        project="default",
        tokens_measured=False,
        ok=True,
        duration_ms=120,
        usage_raw={},
        rates_used={},
    )
    session.add(row)
    await session.commit()

    got = (await session.execute(select(LLMUsage))).scalar_one()
    assert got.tokens_measured is False
    assert got.prompt_tokens is None
    assert got.cost_micros is None


@pytest.mark.asyncio
async def test_cost_is_an_integer_column(session):
    """Money is micro-USD as BigInteger. `memories.confidence` being REAL is
    not a precedent for currency."""
    col = inspect(LLMUsage).columns["cost_micros"]
    assert col.type.python_type is int
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_llm_usage_model.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.llm_usage'`

- [ ] **Step 3: Write the model**

```python
# backend/app/models/llm_usage.py
"""One row per LLM vendor call: what it cost and what caused it.

Deliberately **not** the ``events`` table, for the reason
``JobRun``'s own docstring already gives: that substrate is append-only by
trigger and permanent by ruling, and doc 17 §5.1's metrics are SQL over it
alone. Token metering is high-volume telemetry that wants pruning, so it goes
where DELETE is ordinary and ``llm_usage_cleanup`` can hold it to a ceiling.

``subject_id`` is Text rather than UUID because two of the six subject kinds
are not uuids: a job run is ``{job_key}@{started_at}`` (the ``job_runs`` row is
written after the runner returns, and for a run reporting nothing it is never
written at all), and search/chat subjects are request ids.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    api_kind: Mapped[str] = mapped_column(String(32), nullable=False)

    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: NULL, never 0, when the vendor reported no envelope.
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Hidden chain-of-thought, billed inside completion_tokens by reasoning
    #: models. Broken out because it is a prime candidate for wasted spend.
    reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_measured: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    #: Micro-USD. NULL means "no rate for this model", which is not zero.
    cost_micros: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    #: The three rates actually applied, so the arithmetic can be audited
    #: without knowing what the price table said that day.
    rates_used: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    #: The whole envelope. Flattening to four integers would make a question
    #: nobody has thought of yet unanswerable against history already paid for.
    usage_raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    ok: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    error_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        Index("ix_llm_usage_subject", "subject_type", "subject_id"),
        Index("ix_llm_usage_occurred", "occurred_at"),
        Index("ix_llm_usage_purpose_occurred", "purpose", "occurred_at"),
    )
```

- [ ] **Step 4: Export it so Alembic's metadata sees it**

Add to `backend/app/models/__init__.py`, following the existing import list:

```python
from .llm_usage import LLMUsage  # noqa: F401
```

- [ ] **Step 5: Regenerate the baseline in place**

The baseline is regenerated, never appended to. Drop the local test schema and autogenerate:

```bash
cd backend
export DATABASE_URL='postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test'
psql -h localhost -p 5433 -U darkmem -d darkmem_test -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
python -m alembic revision --autogenerate -m baseline --rev-id 0001
```

Autogenerate writes a *new* file. Move its `llm_usage` `op.create_table` and
`op.create_index` calls into the existing `0001_baseline.py` (upgrade, beside
the other table creations; and the matching `op.drop_table` in downgrade), then
delete the generated file. **`migrations/versions/` must contain exactly
`0001_baseline.py` when you are done.**

- [ ] **Step 6: Verify the single-revision assertion and the tests**

```bash
ls backend/migrations/versions/          # must show only 0001_baseline.py
cd backend && python -m pytest tests/test_llm_usage_model.py -q
```
Expected: one file; tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/llm_usage.py backend/app/models/__init__.py \
        backend/migrations/versions/0001_baseline.py backend/tests/test_llm_usage_model.py
git commit -m "feat(usage): add the llm_usage table"
```

---

### Task 2: Price table and cost arithmetic

**Files:**
- Create: `backend/app/services/usage_pricing.py`
- Test: `backend/tests/test_usage_pricing.py`

**Interfaces:**
- Produces: `ModelRates` dataclass with `input_micros_per_mtok: int`, `cached_micros_per_mtok: int`, `output_micros_per_mtok: int`; `DEFAULT_MODEL_PRICES: dict[str, ModelRates]`; `resolve_rates(model: str, overrides: dict) -> ModelRates | None`; `compute_cost_micros(rates: ModelRates | None, prompt: int | None, cached: int | None, completion: int | None) -> int | None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_pricing.py
from app.services.usage_pricing import (
    DEFAULT_MODEL_PRICES,
    ModelRates,
    compute_cost_micros,
    resolve_rates,
)

RATES = ModelRates(input_micros_per_mtok=270_000,
                   cached_micros_per_mtok=14_000,
                   output_micros_per_mtok=1_100_000)


def test_cached_tokens_are_billed_at_the_cached_rate():
    """A cached input token bills at ~5% on DeepSeek. Charging it at the input
    rate would overstate a cache hit by twentyfold -- and cache-hit rate is the
    single biggest lever this feature exists to expose."""
    all_fresh = compute_cost_micros(RATES, prompt=1_000_000, cached=0, completion=0)
    all_cached = compute_cost_micros(RATES, prompt=1_000_000, cached=1_000_000, completion=0)
    assert all_fresh == 270_000
    assert all_cached == 14_000


def test_cached_is_a_subset_of_prompt_not_an_addition():
    """Vendors report cached_tokens as part of prompt_tokens, not beside it."""
    half = compute_cost_micros(RATES, prompt=1_000_000, cached=500_000, completion=0)
    assert half == 135_000 + 7_000


def test_unmeasured_tokens_price_to_none_never_zero():
    assert compute_cost_micros(RATES, prompt=None, cached=None, completion=None) is None


def test_unknown_model_has_no_rates():
    assert resolve_rates("some-model-we-never-shipped", {}) is None


def test_operator_override_wins_over_the_shipped_default():
    """Prices follow the feature_flags pattern: a DB row merged over defaults."""
    model = next(iter(DEFAULT_MODEL_PRICES))
    over = {model: {"input_micros_per_mtok": 1, "cached_micros_per_mtok": 1,
                    "output_micros_per_mtok": 1}}
    assert resolve_rates(model, over).input_micros_per_mtok == 1
    assert resolve_rates(model, {}) == DEFAULT_MODEL_PRICES[model]


def test_a_local_model_is_priced_at_a_measured_zero():
    """Free is a measured value and must not read as 'unpriced'."""
    rates = resolve_rates("qwen3-embedding:0.6b", {})
    assert rates is not None
    assert compute_cost_micros(rates, prompt=5_000, cached=0, completion=0) == 0
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_usage_pricing.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.usage_pricing'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/usage_pricing.py
"""Model prices and the arithmetic that turns tokens into money.

Pure: no session, no I/O, no clock. The caller resolves the override dict from
the ``model_prices`` config row and passes it in, exactly as
``get_feature_flags_dict`` merges a DB row over ``FEATURE_FLAGS_DEFAULTS``.

**Three rates, not two.** A cached input token bills at roughly 5% of input on
DeepSeek and 50% on OpenAI, so a single input rate would be wrong by up to
twentyfold on the one axis most worth optimising. Anthropic carries no cache
discount here at all: its caching requires the native ``/v1/messages`` path with
explicit ``cache_control`` markers, and this orchestrator dispatches it over the
OpenAI-compat path where it never fires.

Rates are micro-USD per million tokens, so a whole-cent price is an exact
integer and no float ever touches money.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ModelRates:
    input_micros_per_mtok: int
    cached_micros_per_mtok: int
    output_micros_per_mtok: int


#: Shipped defaults for the models this deployment actually resolves. A model
#: absent here prices to None -- surfaced as "not priced" with the model named,
#: never as free.
DEFAULT_MODEL_PRICES: dict[str, ModelRates] = {
    "deepseek-v4-flash": ModelRates(270_000, 14_000, 1_100_000),
    "deepseek-v4-pro": ModelRates(550_000, 28_000, 2_190_000),
    "gpt-5.5": ModelRates(1_250_000, 625_000, 10_000_000),
    # Local Ollama: a measured zero, not an absent price.
    "qwen3-embedding:0.6b": ModelRates(0, 0, 0),
    "nomic-embed-text:latest": ModelRates(0, 0, 0),
}


def resolve_rates(model: str, overrides: dict) -> ModelRates | None:
    """The operator's row merged over the shipped default, per model."""
    base = DEFAULT_MODEL_PRICES.get(model)
    over = overrides.get(model)
    if over is None:
        return base
    fields = {k: int(v) for k, v in over.items()
              if k in ("input_micros_per_mtok", "cached_micros_per_mtok",
                       "output_micros_per_mtok")}
    if base is None:
        try:
            return ModelRates(**fields)
        except TypeError:
            return None
    return replace(base, **fields)


def compute_cost_micros(
    rates: ModelRates | None,
    prompt: int | None,
    cached: int | None,
    completion: int | None,
) -> int | None:
    """Micro-USD for one call, or None when it cannot be priced.

    ``cached`` is a *subset* of ``prompt`` as every vendor reports it, so the
    fresh portion is ``prompt - cached``. Treating it as an addition would
    double-count the cache hit it is supposed to celebrate.
    """
    if rates is None or prompt is None:
        return None
    cached_t = cached or 0
    fresh = max(0, prompt - cached_t)
    out = completion or 0
    total = (
        fresh * rates.input_micros_per_mtok
        + cached_t * rates.cached_micros_per_mtok
        + out * rates.output_micros_per_mtok
    )
    return total // 1_000_000
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_usage_pricing.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/usage_pricing.py backend/tests/test_usage_pricing.py
git commit -m "feat(usage): model price table and cost arithmetic"
```

---

### Task 3: Surface the usage envelopes the orchestrator throws away

**Files:**
- Modify: `backend/app/services/llm_quirks.py`
- Modify: `backend/app/services/llm.py:159-274` (embeds), `:566+` (streams)
- Test: `backend/tests/test_llm_usage_extraction.py`

**Interfaces:**
- Produces: `VendorQuirks.stream_usage_option: bool`, `VendorQuirks.cache_hit_fields: tuple[str, ...]`; `extract_usage(payload: dict, quirks: VendorQuirks) -> dict | None` in `app/services/llm.py`.
- Consumes: nothing from earlier tasks.

**Why this task exists:** two of the four required cost sources cannot be measured at all today. `embed`/`embed_batch` read only the vectors; the compat stream never asks for usage; and the native stream breaks on the `done` chunk, which is the one chunk carrying the counts.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm_usage_extraction.py
import ast
from pathlib import Path

from app.services.llm import extract_usage
from app.services.llm_quirks import quirks_for


def test_cache_hit_field_is_read_from_the_quirk_row_not_a_vendor_branch():
    """Vendors put the cached count in different places. A call site comparing
    api_kind to a vendor name fails tests/test_api_kind_dispatch.py, so the
    field names live on the quirk row."""
    ds = quirks_for("deepseek")
    oa = quirks_for("openai")
    assert "prompt_cache_hit_tokens" in ds.cache_hit_fields
    assert any("cached_tokens" in f for f in oa.cache_hit_fields)


def test_extracts_the_openai_nested_cache_field():
    q = quirks_for("openai")
    got = extract_usage(
        {"usage": {"prompt_tokens": 100,
                   "completion_tokens": 10,
                   "prompt_tokens_details": {"cached_tokens": 80}}}, q)
    assert got["prompt_tokens"] == 100
    assert got["cached_tokens"] == 80
    assert got["completion_tokens"] == 10


def test_extracts_ollama_native_counts_from_the_done_chunk():
    q = quirks_for("ollama")
    got = extract_usage({"prompt_eval_count": 42, "eval_count": 7, "done": True}, q)
    assert got["prompt_tokens"] == 42
    assert got["completion_tokens"] == 7


def test_a_missing_envelope_is_none_not_zeros():
    """The doctrine benchlib/twin.py sets: a number nobody observed is not 0."""
    assert extract_usage({"choices": []}, quirks_for("openai")) is None


def test_reasoning_tokens_are_broken_out_when_present():
    got = extract_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 500,
                   "completion_tokens_details": {"reasoning_tokens": 480}}},
        quirks_for("openai"))
    assert got["reasoning_tokens"] == 480


def test_no_vendor_literal_was_introduced_in_llm_py():
    """tests/test_api_kind_dispatch.py enforces this build-wide; assert it here
    too so a regression names this task."""
    tree = ast.parse(Path("app/services/llm.py").read_text())
    vendors = {"openai", "ollama", "anthropic", "deepseek", "google", "zai"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and sub.value in vendors:
                    raise AssertionError(f"vendor literal in a comparison at line {node.lineno}")
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_llm_usage_extraction.py -q`
Expected: FAIL — `ImportError: cannot import name 'extract_usage'`

- [ ] **Step 3: Add the two quirk fields**

In `backend/app/services/llm_quirks.py`, add to the `VendorQuirks` dataclass beside `output_cap_key`:

```python
    #: Whether the compat streaming body accepts
    #: ``stream_options: {"include_usage": true}``. Without it a streamed
    #: response carries no usage envelope at all and chat cost is unmeasurable.
    stream_usage_option: bool = False
    #: Where this vendor reports the cached-input count, in the order to try.
    #: Dotted paths descend into nested objects. Empty for vendors that
    #: surface none -- z.ai through the compat path, and Anthropic, whose
    #: caching never fires on the path this orchestrator dispatches it over.
    cache_hit_fields: tuple[str, ...] = ()
```

Then set them per row in `_QUIRKS`: `openai` gets
`stream_usage_option=True, cache_hit_fields=("prompt_tokens_details.cached_tokens",)`;
`deepseek` gets `stream_usage_option=True, cache_hit_fields=("prompt_cache_hit_tokens",)`;
`ollama` gets `stream_usage_option=False, cache_hit_fields=()`;
leave the reserved vendors at the defaults.

- [ ] **Step 4: Add `extract_usage` to `llm.py`**

```python
def _dig(payload: dict, dotted: str):
    node = payload
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def extract_usage(payload: dict, quirks) -> dict | None:
    """Normalise one vendor response into the four counts, or None.

    None means "this vendor told us nothing", which is not zero -- see
    ``benchlib/twin.py``'s doctrine. Handles the OpenAI-compat ``usage``
    envelope and Ollama's native ``prompt_eval_count``/``eval_count``, which
    ride the ``done`` chunk on the streaming path.
    """
    usage = payload.get("usage")
    if isinstance(usage, dict) and (
        usage.get("prompt_tokens") is not None or usage.get("completion_tokens") is not None
    ):
        cached = 0
        for field in quirks.cache_hit_fields:
            value = _dig(usage, field)
            if value:
                cached = int(value)
                break
        reasoning = _dig(usage, "completion_tokens_details.reasoning_tokens")
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "cached_tokens": cached,
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": int(reasoning) if reasoning else None,
            "raw": usage,
        }
    if payload.get("prompt_eval_count") is not None or payload.get("eval_count") is not None:
        return {
            "prompt_tokens": payload.get("prompt_eval_count"),
            "cached_tokens": 0,
            "completion_tokens": payload.get("eval_count"),
            "reasoning_tokens": None,
            "raw": {k: payload.get(k) for k in ("prompt_eval_count", "eval_count")},
        }
    return None
```

- [ ] **Step 5: Stop discarding the envelopes**

Three edits in `backend/app/services/llm.py`:

1. `embed` (:159) and `embed_batch` (:196): keep the parsed `response.json()` in a local and pass it to the recorder in Task 4 rather than indexing straight into the vector. No behaviour change yet — just stop dropping the object on the floor.
2. `chat_completion_stream` native branch (:602): read the `done` chunk **before** breaking:

```python
                    if chunk.get("done"):
                        final_chunk = chunk       # carries the counts
                        break
```

3. `chat_completion_stream` compat branch: when `quirks.stream_usage_option`, add `stream_options={"include_usage": True}` to the body built by `_build_openai_chat_body`, and capture the final SSE frame's `usage` (OpenAI sends it as a last chunk with an empty `choices` list) before `[DONE]`.

- [ ] **Step 6: Run the tests and the vendor-literal scan**

```bash
cd backend && python -m pytest tests/test_llm_usage_extraction.py tests/test_api_kind_dispatch.py -q
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/llm_quirks.py backend/app/services/llm.py \
        backend/tests/test_llm_usage_extraction.py
git commit -m "feat(usage): surface the usage envelopes the orchestrator discarded"
```

---

### Task 4: The recorder, on its own session

**Files:**
- Create: `backend/app/services/usage_recorder.py`
- Modify: `backend/app/services/llm.py` (six call paths)
- Test: `backend/tests/test_usage_recorder.py`

**Interfaces:**
- Consumes: `extract_usage` (Task 3), `resolve_rates`/`compute_cost_micros` (Task 2), `LLMUsage` (Task 1).
- Produces: `UsageSubject` NamedTuple `(subject_type: str, subject_id: str | None, project: str | None)`; `current_subject: ContextVar[UsageSubject | None]`; `subject_scope(subject)` context manager; `UsageRecorder.record(...) -> None`.

- [ ] **Step 1: Add the `session_factory` fixture**

`tests/conftest.py` exposes `session`, which runs inside an outer transaction
rolled back after each test. A recorder opening a genuinely independent session
would write on a different connection — invisible to the test and *not* rolled
back, leaking rows across the suite. Bind the factory to the same connection so
writes are both visible and undone:

```python
# backend/tests/conftest.py
@pytest_asyncio.fixture
async def session_factory(session):
    """Sessions on the test's own connection, so recorder writes are visible
    and still roll back. Production binds the real engine; this fixture is the
    only place the two differ."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        nested = AsyncSession(bind=session.get_bind(), expire_on_commit=False)
        try:
            yield nested
        finally:
            await nested.close()

    return factory
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_usage_recorder.py
import pytest
from sqlalchemy import select

from app.models.llm_usage import LLMUsage
from app.services.usage_recorder import UsageRecorder, UsageSubject, subject_scope


@pytest.mark.asyncio
async def test_a_failed_call_is_recorded(session_factory, session):
    """Failed work is pure waste and is exactly what this feature is for.
    Every error path in the orchestrator raises before the old log line, which
    is why the recorder wraps the request cycle rather than living there."""
    rec = UsageRecorder(session_factory, price_overrides={})
    await rec.record(purpose="extraction", model="deepseek-v4-flash",
                     provider="p", api_kind="deepseek", payload=None,
                     subject=UsageSubject("memory", "m1", "default"),
                     duration_ms=90, ok=False, error_kind="ReadTimeout")

    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.ok is False and row.error_kind == "ReadTimeout"
    assert row.tokens_measured is False


def test_it_takes_no_caller_session():
    """Structural, not transactional. The property that matters is that the
    recorder cannot be handed the caller's session: the pipeline's savepoints
    would roll back the failed-work rows along with the failed work, the
    evidence deleting itself. Proving that transactionally needs a connection
    outside the test's own rolled-back transaction, so assert the shape --
    `record` has no session parameter and the factory is the only way in."""
    import inspect

    assert "session" not in inspect.signature(UsageRecorder.record).parameters
    assert "session_factory" in inspect.signature(UsageRecorder.__init__).parameters


@pytest.mark.asyncio
async def test_it_never_raises_into_the_call_path(session):
    """Mirrors record_event: degrade loudly, never kill the work it describes."""
    def exploding_factory():
        raise RuntimeError("database is gone")

    rec = UsageRecorder(exploding_factory, price_overrides={})
    await rec.record(purpose="extraction", model="m", provider="p",
                     api_kind="openai", payload=None, subject=None,
                     duration_ms=1, ok=True, error_kind=None)   # must not raise


@pytest.mark.asyncio
async def test_subject_scope_supplies_an_ambient_subject(session_factory, session):
    rec = UsageRecorder(session_factory, price_overrides={})
    with subject_scope(UsageSubject("job_run", "buffer_flush@2026-08-23T00:00:00", None)):
        await rec.record(purpose="extraction", model="m", provider="p",
                         api_kind="openai", payload=None, subject=None,
                         duration_ms=1, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.subject_type == "job_run"


@pytest.mark.asyncio
async def test_an_explicit_subject_beats_the_ambient_one(session_factory, session):
    """Innermost wins: ingest inside buffer_flush attributes to the memory."""
    rec = UsageRecorder(session_factory, price_overrides={})
    with subject_scope(UsageSubject("job_run", "buffer_flush@t", None)):
        await rec.record(purpose="extraction", model="m", provider="p",
                         api_kind="openai", payload=None,
                         subject=UsageSubject("memory", "m1", "default"),
                         duration_ms=1, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert (row.subject_type, row.subject_id) == ("memory", "m1")
```

- [ ] **Step 3: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_usage_recorder.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.usage_recorder'`

- [ ] **Step 4: Implement the recorder**

```python
# backend/app/services/usage_recorder.py
"""Writes one ``llm_usage`` row per vendor call.

**Its own session, always.** The pipeline runs Phase 5 in two savepoints and an
extraction failure never enters savepoint B at all; a usage row on the caller's
session is rolled back with the work it describes, so the failed-work rows --
the ones this feature exists to surface -- would delete their own evidence.

**Never raises.** Same contract as ``record_event``: a metering failure must not
kill the work it is metering. It logs at ERROR and returns.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import NamedTuple

from app.models.llm_usage import LLMUsage
from app.services.llm import extract_usage
from app.services.llm_quirks import quirks_for
from app.services.usage_pricing import compute_cost_micros, resolve_rates

logger = logging.getLogger(__name__)


class UsageSubject(NamedTuple):
    subject_type: str
    subject_id: str | None
    project: str | None


#: The ambient subject, for scopes that genuinely wrap many calls -- a job run,
#: an HTTP request. Ingest does NOT rely on this: asyncio.gather's tasks all
#: copy the same parent context, so a per-entry value has to be passed
#: explicitly or every call in a batch attributes to the batch.
current_subject: ContextVar[UsageSubject | None] = ContextVar("current_subject", default=None)


@contextmanager
def subject_scope(subject: UsageSubject):
    token = current_subject.set(subject)
    try:
        yield
    finally:
        current_subject.reset(token)


class UsageRecorder:
    def __init__(self, session_factory, price_overrides: dict):
        self._session_factory = session_factory
        self._price_overrides = price_overrides

    async def record(
        self, *, purpose: str, model: str, provider: str | None, api_kind: str,
        payload: dict | None, subject: UsageSubject | None, duration_ms: int,
        ok: bool, error_kind: str | None,
    ) -> None:
        try:
            subj = subject or current_subject.get() or UsageSubject("unattributed", None, None)
            usage = extract_usage(payload, quirks_for(api_kind)) if payload else None
            rates = resolve_rates(model, self._price_overrides)
            cost = compute_cost_micros(
                rates,
                usage["prompt_tokens"] if usage else None,
                usage["cached_tokens"] if usage else None,
                usage["completion_tokens"] if usage else None,
            )
            row = LLMUsage(
                purpose=purpose, model=model, provider=provider, api_kind=api_kind,
                subject_type=subj.subject_type, subject_id=subj.subject_id,
                project=subj.project,
                prompt_tokens=usage["prompt_tokens"] if usage else None,
                cached_tokens=usage["cached_tokens"] if usage else None,
                completion_tokens=usage["completion_tokens"] if usage else None,
                reasoning_tokens=usage["reasoning_tokens"] if usage else None,
                tokens_measured=usage is not None,
                cost_micros=cost,
                rates_used=(
                    {"input": rates.input_micros_per_mtok,
                     "cached": rates.cached_micros_per_mtok,
                     "output": rates.output_micros_per_mtok} if rates else {}
                ),
                usage_raw=(usage or {}).get("raw", {}),
                ok=ok, error_kind=error_kind, duration_ms=duration_ms,
            )
            async with self._session_factory() as session:
                session.add(row)
                await session.commit()
        except Exception:
            logger.exception("usage recording failed for purpose=%s model=%s", purpose, model)
```

- [ ] **Step 5: Wire the six orchestrator paths**

In `backend/app/services/llm.py`, wrap each of `chat_completion` compat, `chat_completion` native, both `chat_completion_stream` branches, `embed`, and `embed_batch` in a `time.perf_counter()` span with `try/except`, calling `self._recorder.record(...)` on both the success and the failure path (re-raising the exception afterwards). `embed_batch_chunked` composes `embed_batch` and is **not** wrapped separately — wrapping both would double-count. The recorder is constructed with the orchestrator and is optional (`None` in tests that do not want it).

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_usage_recorder.py tests/test_llm*.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/usage_recorder.py backend/tests/conftest.py backend/app/services/llm.py \
        backend/tests/test_usage_recorder.py
git commit -m "feat(usage): record every vendor call on an independent session"
```

---

### Task 5: Attribution — ingest, jobs, requests, maintenance

**Files:**
- Modify: `backend/app/services/pipeline.py:967,983,1004-1027`
- Modify: `backend/app/services/job_registry.py:380-414`
- Modify: `backend/app/services/chat.py`, `backend/app/api/routes/reembed.py`, `backend/app/api/routes/repos.py`
- Test: `backend/tests/test_usage_attribution.py`

**Interfaces:**
- Consumes: `UsageSubject`, `subject_scope` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_attribution.py
import pytest
from sqlalchemy import select

from app.models.llm_usage import LLMUsage


@pytest.mark.asyncio
async def test_each_memory_in_a_batch_gets_its_own_subject(pipeline_with_recorder, session):
    """The trap this pins: asyncio.gather wraps each coroutine in a Task, and
    every Task copies the SAME parent context. Without an explicit per-entry
    value, all three memories attribute to whatever the batch scope held."""
    await pipeline_with_recorder.process_batch([
        {"content": "alpha", "id": "11111111-1111-1111-1111-111111111111"},
        {"content": "beta", "id": "22222222-2222-2222-2222-222222222222"},
        {"content": "gamma", "id": "33333333-3333-3333-3333-333333333333"},
    ])
    rows = (await session.execute(
        select(LLMUsage).where(LLMUsage.subject_type == "memory"))).scalars().all()
    assert len({r.subject_id for r in rows}) == 3


@pytest.mark.asyncio
async def test_batched_embeds_attribute_to_the_batch_not_a_memory(
    pipeline_with_recorder, session
):
    """One embed call covers the whole batch, and entity-name embeds are
    deduped and cache-hit across memories, so a per-memory share is undefined,
    not merely imprecise."""
    await pipeline_with_recorder.process_batch([
        {"content": "alpha", "id": "11111111-1111-1111-1111-111111111111"},
        {"content": "beta", "id": "22222222-2222-2222-2222-222222222222"},
    ])
    embeds = (await session.execute(
        select(LLMUsage).where(LLMUsage.purpose == "embedding"))).scalars().all()
    assert embeds and all(r.subject_type == "batch" for r in embeds)


@pytest.mark.asyncio
async def test_a_job_run_subject_needs_no_job_runs_row(job_registry_with_recorder, session):
    """job_runs.id is minted server-side AFTER the runner returns, and a run
    reporting nothing writes no row at all -- so it cannot be the subject."""
    await job_registry_with_recorder.trigger("noop_job_that_returns_zero")
    rows = (await session.execute(
        select(LLMUsage).where(LLMUsage.subject_type == "job_run"))).scalars().all()
    assert rows and "@" in rows[0].subject_id
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_usage_attribution.py -q`
Expected: FAIL — every memory row carries the same `subject_id`.

- [ ] **Step 3: Thread the memory id through Phase 2**

`run_extract`/`run_classify` (`pipeline.py:967,983`) take `content` only. Give them the entry's pre-minted id (available at `pipeline.py:889`) and pass an explicit `UsageSubject("memory", memory_id, project)` to the orchestrator call. Wrap the Phase-1 and Phase-3 embed calls in `subject_scope(UsageSubject("batch", batch_id, project))`.

The merged call (`pipeline.py:1004`, `can_merge`) records **once**, `purpose="extraction"`, with `merged_classification: true` written into `usage_raw`. Splitting the tokens across two purposes would be invention.

- [ ] **Step 4: Set the ambient scopes**

`job_registry.py`: wrap the runner call (around `:380-414`) in
`subject_scope(UsageSubject("job_run", f"{key}@{started_at.isoformat()}", None))`.
`chat.py` and the retrieval path: wrap the request in a `chat`/`search` subject with a request id.
`reembed.py`, `repos.py` (reindex, `enrich_symbols`, `generate_wiki`): wrap in `maintenance` with `f"{kind}:{target_id}"`.

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_usage_attribution.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/pipeline.py backend/app/services/job_registry.py \
        backend/app/services/chat.py backend/app/api/routes/reembed.py \
        backend/app/api/routes/repos.py backend/tests/test_usage_attribution.py
git commit -m "feat(usage): attribute calls to memory, job, request and maintenance"
```

---

### Task 6: Read API

**Files:**
- Create: `backend/app/repositories/usage_repository.py`, `backend/app/api/routes/usage.py`, `backend/app/schemas/usage.py`
- Modify: `backend/app/main.py` (mount the router)
- Test: `backend/tests/test_usage_api.py`

**Interfaces:**
- Produces: `GET /api/v1/usage/overview`, `/usage/series`, `/usage/by-subject/{type}/{id}`, `/usage/top`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_api.py
import pytest


@pytest.mark.asyncio
async def test_overview_reports_unmeasured_and_unpriced_counts(client, seeded_usage):
    """Every aggregate carries its own confidence: a total that silently
    excluded unmeasured calls would read as complete when it is a floor."""
    r = await client.get("/api/v1/usage/overview?window=30d")
    assert r.status_code == 200
    body = r.json()
    assert "unmeasured_calls" in body and "unpriced_calls" in body
    assert body["total_cost_micros"] >= 0


@pytest.mark.asyncio
async def test_overview_flags_the_merged_classification_caveat(client, seeded_merged_usage):
    """Under the default config classification's total reads near zero because
    it is folded into extraction. Unflagged, an operator 'optimising the wasted
    part' would draw exactly the wrong conclusion."""
    body = (await client.get("/api/v1/usage/overview?window=30d")).json()
    assert body["merged_classification_present"] is True


@pytest.mark.asyncio
async def test_by_subject_returns_that_memory_only(client, seeded_usage):
    body = (await client.get(
        "/api/v1/usage/by-subject/memory/11111111-1111-1111-1111-111111111111")).json()
    assert all(r["subject_id"] == "11111111-1111-1111-1111-111111111111" for r in body["calls"])


@pytest.mark.asyncio
async def test_top_ranks_by_cost_descending(client, seeded_usage):
    body = (await client.get("/api/v1/usage/top?window=30d&by=cost&limit=5")).json()
    costs = [r["cost_micros"] for r in body["items"]]
    assert costs == sorted(costs, reverse=True)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_usage_api.py -q`
Expected: FAIL — 404 on every route.

- [ ] **Step 3: Implement repository, schemas and routes**

All aggregation is SQL — `GROUP BY purpose`, `GROUP BY model`, `GROUP BY subject_type`, `date_trunc` for the series, `SUM(cost_micros) FILTER (WHERE ok)`, `COUNT(*) FILTER (WHERE NOT tokens_measured)`. No post-fetch Python filtering, matching how `list_events` builds its predicates. Follow `docs/api-rest-conventions.md`. Mount under `/api/v1/usage` in `main.py` beside the other routers.

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_usage_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/usage_repository.py backend/app/api/routes/usage.py \
        backend/app/schemas/usage.py backend/app/main.py backend/tests/test_usage_api.py
git commit -m "feat(usage): read API for overview, series, subject and outliers"
```

---

### Task 7: Retention job

**Files:**
- Modify: `backend/app/main.py`, `backend/tests/test_code_deriver.py`, `CLAUDE.md`
- Create: the runner beside the other cleanup jobs
- Test: `backend/tests/test_usage_cleanup.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_cleanup.py
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models.llm_usage import LLMUsage


@pytest.mark.asyncio
async def test_prunes_beyond_the_retention_window(session, run_usage_cleanup):
    old = LLMUsage(occurred_at=datetime.now(timezone.utc) - timedelta(days=400),
                   purpose="extraction", model="m", api_kind="openai",
                   subject_type="memory", tokens_measured=False, duration_ms=1)
    fresh = LLMUsage(occurred_at=datetime.now(timezone.utc),
                     purpose="extraction", model="m", api_kind="openai",
                     subject_type="memory", tokens_measured=False, duration_ms=1)
    session.add_all([old, fresh]); await session.commit()

    await run_usage_cleanup(retention_days=90)

    left = (await session.execute(select(LLMUsage))).scalars().all()
    assert len(left) == 1
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd backend && python -m pytest tests/test_usage_cleanup.py -q`
Expected: FAIL — fixture/job missing.

- [ ] **Step 3: Register the job**

Add `llm_usage_cleanup` in `app/main.py` on the `job_run_cleanup` pattern, with a `config_schema` carrying `retention_days`. Register via a `LLM_USAGE_CLEANUP_JOB_KEY` constant, matching how the other keyed jobs are registered.

- [ ] **Step 4: Update the two pins that will otherwise fail**

`tests/test_code_deriver.py` derives the roster from `app/main.py`'s AST against a literal expected set — add the new key. Then update CLAUDE.md's registered-job count (currently "Twenty-two") and its live-jobs list. This count has gone stale three times before; it is exactly the invariant-23 shape that file warns about.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_usage_cleanup.py \
        backend/tests/test_code_deriver.py CLAUDE.md
git commit -m "feat(usage): retention job for llm_usage"
```

---

### Task 8: Frontend — overview, detail, prices

**Files:**
- Create: `frontend/src/features/usage/components/usage-overview.tsx`, `usage-subject-panel.tsx`, `prices-panel.tsx`; `frontend/src/hooks/api/use-usage-api.ts`; route under `frontend/src/routes/_authenticated/`
- Modify: the memory detail view, the job history dialog, the settings tab list
- Test: `frontend/src/features/usage/__tests__/usage-overview.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/usage/__tests__/usage-overview.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { UsageOverview } from "../components/usage-overview"

const BASE = {
  total_cost_micros: 3_410_000, total_calls: 120,
  unmeasured_calls: 0, unpriced_calls: 0,
  merged_classification_present: false,
  by_purpose: [{ purpose: "extraction", cost_micros: 2_100_000, calls: 60 }],
  by_model: [], by_subject_type: [], cache_hit_ratio: 0.42,
  failed_calls: 0, failed_cost_micros: 0,
}

describe("UsageOverview", () => {
  it("renders spend as currency, not micros", () => {
    render(<UsageOverview data={BASE} />)
    expect(screen.getByText("$3.41")).toBeInTheDocument()
  })

  it("says when classification is folded into extraction", () => {
    // Under the default config classification reads near zero. Unflagged, an
    // operator optimises a purpose that only looks free.
    render(<UsageOverview data={{ ...BASE, merged_classification_present: true }} />)
    expect(screen.getByText(/includes folded classification/i)).toBeInTheDocument()
  })

  it("never renders an unmeasured call as free", () => {
    render(<UsageOverview data={{ ...BASE, unmeasured_calls: 7 }} />)
    expect(screen.getByText(/7 calls not measured/i)).toBeInTheDocument()
  })

  it("names unpriced models rather than counting them as zero", () => {
    render(<UsageOverview data={{ ...BASE, unpriced_calls: 3 }} />)
    expect(screen.getByText(/3 calls not priced/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd frontend && npx vitest run src/features/usage -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Build the surfaces**

Use `darkraise-ui` components and the shared `features/graph/components/settings-rows.tsx` primitives; a new local component needs a stated library gap. Currency renders from `cost_micros / 1_000_000`. The per-memory panel shows embedding as *batched*, never a fabricated share.

- [ ] **Step 4: Run typecheck and tests**

```bash
cd frontend && npm run typecheck && npx vitest run src/features/usage -q
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/usage frontend/src/hooks/api/use-usage-api.ts \
        frontend/src/routes/_authenticated
git commit -m "feat(usage): overview, per-subject detail and price settings"
```

---

### Task 9: Rehearse the cutover on the dev database

**Files:** none — this task produces confidence, not code.

**Why:** the production drop destroys the `events` journal that G-C's metrics were measured on and the G-E corpus clock armed 2026-08-17, plus `knowledge_triples`, research origins and every `config` row. Rehearse the exact sequence somewhere disposable first.

- [ ] **Step 1: Dump the dev database (port 5433)**

```bash
docker compose -f docker-compose.dev.yml exec -T postgres \
  pg_dump -U darkmem -d darkmem --data-only > /tmp/dev-data.sql
```

- [ ] **Step 2: Drop, recreate, migrate**

```bash
docker compose -f docker-compose.dev.yml exec -T postgres \
  psql -U darkmem -d darkmem -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
cd backend && DATABASE_URL='postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem' \
  python -m alembic upgrade head
```

- [ ] **Step 3: Restore data and confirm `llm_usage` exists and is empty**

A data-only restore needs the historical monthly `events` partitions to exist — boot only ensures current-and-next month. Call `events_ensure_partition` for each month present in the dump before restoring.

- [ ] **Step 4: Record the exact command sequence that worked** into `docs/runbook-deployment.md` as the additive-table cutover procedure.

- [ ] **Step 5: Commit the runbook addition**

```bash
git add docs/runbook-deployment.md
git commit -m "docs(runbook): additive-table cutover procedure"
```

---

### Task 10: Production cutover and deploy

- [ ] **Step 1: Full gate**

Run: `./scripts/gate.sh` from the repo root. Expected: `GATE GREEN`.

- [ ] **Step 2: Two dumps, verified non-empty**

```bash
./scripts/backup.sh /root/darkmem-backups                     # full, --clean
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem --data-only \
  > /root/darkmem-backups/pre-llm-usage-$(date +%Y%m%d-%H%M%S)-data.sql
```
Confirm both files are non-empty and that the data dump contains `COPY public.memories` and `COPY public.events`.

- [ ] **Step 3: Build the image**

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
```

- [ ] **Step 4: Stop the app, drop, recreate, migrate, restore**

Follow the sequence recorded in Task 9 step 4.

- [ ] **Step 5: Re-seed the two rows a restore does not reproduce**

`admin_password_hash`, and the `verification` purpose row at the qualified judge identity `gpt-5.5` on OpenAI — `llm_seed.py:196` seeds it at a local Ollama model, so G-D's minted qualification stops resolving unless this row is restored by hand.

- [ ] **Step 6: Boot and verify**

```bash
docker compose -p darkmem-prod up -d
```
`schema_guard` adopts the new hash automatically against a recreated database. Confirm the container reports `healthy`, that memory and event counts match the pre-cutover numbers, and that `llm_usage` starts accumulating rows after one capture.

- [ ] **Step 7: Confirm the change is in the running image, not just the tree**

```bash
docker exec darkmem-prod-darkmem-1 grep -c llm_usage /app/web/assets/*.js
curl -s localhost:8000/openapi.json | grep -c '/usage/overview'
```

- [ ] **Step 8: Commit any cutover notes and report the numbers.**
