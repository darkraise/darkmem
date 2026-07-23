# darkmem Harness — `benchlib` Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared measurement foundation (`backend/scripts/benchlib/`) that every darkmem eval bench sits on — a dedicated bench database, an offline `process_batch` ingest driver, a content-hash LLM cache that makes a second run ~free, and an append-only results ledger — and prove it end-to-end on a 3-memory smoke corpus.

**Architecture:** `benchlib` is a set of small, single-responsibility modules under `backend/scripts/` (siblings of `extraction_bench`). It reuses darkmem's real ingestion pipeline unchanged: it constructs `ProcessingPipeline(caching_llm, bench_session_factory)` and calls `process_batch`. Isolation comes from a separate `darkmem_bench` Postgres database plus a `DATABASE_URL` override applied before any `app.*` import (the exact discipline `backend/tests/conftest.py` uses). Affordability comes from a `CachingLLMOrchestrator` subclass that memoises `embed` and `chat_completion` to disk keyed by a content hash, so the first run pays the LLM cost and every later run replays from cache.

**Tech Stack:** Python 3.14, async SQLAlchemy + asyncpg, Alembic, pytest + pytest-asyncio, stdlib `json`/`hashlib`/`time`. No new dependencies.

## Global Constraints

- **Bench DB is a DEDICATED database `darkmem_bench` on the dev-compose Postgres (127.0.0.1:5433) — NEVER the real database and NEVER `darkmem_test`.** Reset = `DROP SCHEMA IF EXISTS public CASCADE` + `CREATE SCHEMA public` + `alembic upgrade head`. Create it once: `psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_bench;"`.
- **`DATABASE_URL` must be overridden to the bench URL BEFORE the first `app.*` import** — `app/database.py` builds its engine at import time. Mirror `backend/tests/conftest.py:11-14`.
- **Alembic runs in a subprocess** (its `env.py` calls `asyncio.run`, which collides with an active event loop) — mirror `conftest.py:38-54`.
- **The LLM cache wraps BOTH `embed` and `chat_completion`.** The affordability gate (a second run makes zero live LLM calls) is the acceptance signal; if `process_batch` reaches the model through any other method, override that too — the gate will reveal it.
- **Run commands from `backend/`.** Bench unit tests live under `backend/scripts/benchlib/tests/` and are run explicitly with `python -m pytest scripts/benchlib/tests -q` (they must NOT inherit `backend/tests/conftest.py`, which pins the *test* DB).
- **`extraction_bench` stays green as a co-gate:** `python scripts/extraction_bench/run_bench.py --algo-only` must still pass after this work.
- **Ingestion granularity is frozen once** and recorded in `backend/scripts/benchlib/FROZEN.md` (Task 6). This plan's corpus is memory-per-entry.

## File Structure

```
backend/scripts/benchlib/
  __init__.py            # empty package marker
  bench_db.py            # DATABASE_URL override + bench engine + reset_bench_db()
  caching_llm.py         # CachingLLMOrchestrator(embed/chat_completion disk cache)
  ledger.py              # append-only JSONL run ledger (record + read_runs)
  corpus.py              # load_corpus(path) -> list[entry dict]
  ingest.py              # run_ingest(corpus, cache_dir) -> IngestResult
  run_smoke.py           # end-to-end gate: reset -> ingest x2 -> assert cache hit
  smoke/corpus.json      # 3 tiny memories
  FROZEN.md              # frozen ingestion-granularity decision
  tests/
    __init__.py
    conftest.py          # bench-DB session-scoped reset fixture (own, not tests/conftest)
    test_bench_db.py
    test_caching_llm.py
    test_ledger.py
    test_ingest.py
```

**Responsibilities:** `bench_db` owns DB lifecycle only. `caching_llm` owns memoisation only (no DB, no pipeline knowledge). `ledger` owns run-record persistence only. `corpus` owns file→entries parsing only. `ingest` composes the three plus the real pipeline. `run_smoke` is the human/CI entry point and the affordability gate.

---

### Task 1: Bench database lifecycle (`bench_db.py`)

**Files:**
- Create: `backend/scripts/benchlib/__init__.py` (empty)
- Create: `backend/scripts/benchlib/bench_db.py`
- Create: `backend/scripts/benchlib/tests/__init__.py` (empty)
- Create: `backend/scripts/benchlib/tests/conftest.py`
- Test: `backend/scripts/benchlib/tests/test_bench_db.py`

**Interfaces:**
- Produces: `BENCH_DATABASE_URL: str`; `engine` (AsyncEngine on the bench DB); `session_factory` (`async_sessionmaker`); `async reset_bench_db() -> None`.

- [ ] **Step 1: Write the failing test**

`backend/scripts/benchlib/tests/conftest.py`:
```python
import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bench_db():
    # reset_bench_db imports app modules, so importing bench_db here (which sets
    # DATABASE_URL first) must happen before anything touches app.database.
    from benchlib import bench_db
    await bench_db.reset_bench_db()
    yield
    await bench_db.engine.dispose()
```

`backend/scripts/benchlib/tests/test_bench_db.py`:
```python
import pytest
from sqlalchemy import text

from benchlib import bench_db


@pytest.mark.asyncio
async def test_reset_creates_empty_memories_table():
    await bench_db.reset_bench_db()
    async with bench_db.session_factory() as s:
        count = (await s.execute(text("SELECT count(*) FROM memories"))).scalar()
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest scripts/benchlib/tests/test_bench_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'benchlib'` (module not yet created).

- [ ] **Step 3: Write minimal implementation**

`backend/scripts/benchlib/__init__.py`: empty file.
`backend/scripts/benchlib/tests/__init__.py`: empty file.

`backend/scripts/benchlib/bench_db.py`:
```python
"""Dedicated bench-database lifecycle.

Mirrors backend/tests/conftest.py's reset discipline but against a SEPARATE
database (darkmem_bench) so bench runs never touch the real or darkmem_test
database. Importing this module overrides DATABASE_URL to the bench URL, so it
MUST be imported before any other app.* import in a bench process.

Create the database once:
  psql -h localhost -p 5433 -U darkmem -d darkmem -c "CREATE DATABASE darkmem_bench;"
"""
import os
import subprocess
import sys
from pathlib import Path

BENCH_DATABASE_URL = os.environ.get(
    "BENCH_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench",
)
# Override BEFORE importing app.database (it builds its engine at import time).
os.environ["DATABASE_URL"] = BENCH_DATABASE_URL

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend

engine = create_async_engine(BENCH_DATABASE_URL)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic_upgrade() -> None:
    env = {**os.environ, "DATABASE_URL": BENCH_DATABASE_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed for the bench database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


async def reset_bench_db() -> None:
    """Drop + recreate the public schema, then migrate to head."""
    await _reset_schema()
    _run_alembic_upgrade()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest scripts/benchlib/tests/test_bench_db.py -v`
Expected: PASS. (Requires `darkmem_bench` to exist — create it with the psql command in the module docstring if the run errors with `database "darkmem_bench" does not exist`.)

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/benchlib/__init__.py backend/scripts/benchlib/bench_db.py backend/scripts/benchlib/tests/
git commit -m "feat(harness): benchlib bench-database lifecycle"
```

---

### Task 2: Content-hash LLM cache (`caching_llm.py`)

**Files:**
- Create: `backend/scripts/benchlib/caching_llm.py`
- Test: `backend/scripts/benchlib/tests/test_caching_llm.py`

**Interfaces:**
- Consumes: `app.services.llm.LLMOrchestrator` (`async embed(text) -> (vector, fingerprint)`; `async chat_completion(purpose, messages, **kwargs) -> str`).
- Produces: `class CachingLLMOrchestrator(LLMOrchestrator)` with `__init__(self, config, cache_dir: str)`, a `live_calls: int` counter, and overridden `embed` / `chat_completion` that replay from disk on a hit.

- [ ] **Step 1: Write the failing test**

`backend/scripts/benchlib/tests/test_caching_llm.py`:
```python
import pytest

from benchlib.caching_llm import CachingLLMOrchestrator


class _Recorder(CachingLLMOrchestrator):
    """Stub the parent LLM calls so the test needs no live model."""
    async def _live_embed(self, text):
        return ([0.1, 0.2, 0.3], "stub-fp")

    async def _live_chat(self, purpose, messages, **kwargs):
        return '{"ok": true}'


@pytest.mark.asyncio
async def test_embed_is_cached_after_first_call(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    v1 = await llm.embed("hello")
    v2 = await llm.embed("hello")
    assert v1 == v2 == ([0.1, 0.2, 0.3], "stub-fp")
    assert llm.live_calls == 1  # second call served from disk


@pytest.mark.asyncio
async def test_chat_completion_is_cached(tmp_path):
    llm = _Recorder({}, cache_dir=str(tmp_path))
    m = [{"role": "user", "content": "hi"}]
    r1 = await llm.chat_completion("extraction", m, seed=7)
    r2 = await llm.chat_completion("extraction", m, seed=7)
    assert r1 == r2 == '{"ok": true}'
    assert llm.live_calls == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest scripts/benchlib/tests/test_caching_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'benchlib.caching_llm'`.

- [ ] **Step 3: Write minimal implementation**

`backend/scripts/benchlib/caching_llm.py`:
```python
"""LLM orchestrator that memoises embed + chat_completion to disk.

Keyed by a content hash so a second bench run replays every model call from
disk (self.live_calls stays 0). The parent calls are indirected through
_live_embed / _live_chat so tests can stub the model without a live backend.
"""
import hashlib
import json
import os

from benchlib import bench_db  # noqa: F401  (ensures DATABASE_URL override first)
from app.services.llm import LLMOrchestrator


def _key(kind: str, payload) -> str:
    blob = json.dumps([kind, payload], sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class CachingLLMOrchestrator(LLMOrchestrator):
    def __init__(self, config, cache_dir: str):
        super().__init__(config)
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.live_calls = 0

    def _read(self, key: str):
        path = os.path.join(self._cache_dir, key + ".json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        return None

    def _write(self, key: str, value) -> None:
        path = os.path.join(self._cache_dir, key + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False)

    async def _live_embed(self, text):
        return await super().embed(text)

    async def _live_chat(self, purpose, messages, **kwargs):
        return await super().chat_completion(purpose, messages, **kwargs)

    async def embed(self, text: str):
        key = _key("embed", text)
        hit = self._read(key)
        if hit is not None:
            return hit[0], hit[1]
        self.live_calls += 1
        vec, fp = await self._live_embed(text)
        self._write(key, [vec, fp])
        return vec, fp

    async def chat_completion(self, purpose, messages, **kwargs):
        key = _key("chat", [purpose, messages, sorted(kwargs.items())])
        hit = self._read(key)
        if hit is not None:
            return hit
        self.live_calls += 1
        result = await self._live_chat(purpose, messages, **kwargs)
        self._write(key, result)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest scripts/benchlib/tests/test_caching_llm.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/benchlib/caching_llm.py backend/scripts/benchlib/tests/test_caching_llm.py
git commit -m "feat(harness): content-hash LLM cache for embed + chat"
```

---

### Task 3: Run ledger (`ledger.py`)

**Files:**
- Create: `backend/scripts/benchlib/ledger.py`
- Test: `backend/scripts/benchlib/tests/test_ledger.py`

**Interfaces:**
- Produces: `record_run(path: str, run: dict) -> None` (append one JSON object per line); `read_runs(path: str) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

`backend/scripts/benchlib/tests/test_ledger.py`:
```python
from benchlib import ledger


def test_record_and_read_roundtrip(tmp_path):
    path = str(tmp_path / "runs.jsonl")
    ledger.record_run(path, {"bench": "smoke", "ingested": 3, "live_calls": 5, "wall_s": 1.2})
    ledger.record_run(path, {"bench": "smoke", "ingested": 3, "live_calls": 0, "wall_s": 0.3})
    runs = ledger.read_runs(path)
    assert len(runs) == 2
    assert runs[0]["live_calls"] == 5
    assert runs[1]["live_calls"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest scripts/benchlib/tests/test_ledger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'benchlib.ledger'`.

- [ ] **Step 3: Write minimal implementation**

`backend/scripts/benchlib/ledger.py`:
```python
"""Append-only JSONL run ledger. One JSON object per line, one line per run.

Timestamps are the caller's responsibility (Date.now-style calls are avoided in
harness code that must be reproducible); pass a stamped field in `run` if wanted.
"""
import json
import os


def record_run(path: str, run: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(run, ensure_ascii=False) + "\n")


def read_runs(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest scripts/benchlib/tests/test_ledger.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/benchlib/ledger.py backend/scripts/benchlib/tests/test_ledger.py
git commit -m "feat(harness): append-only run ledger"
```

---

### Task 4: Corpus loader + offline ingest driver (`corpus.py`, `ingest.py`)

**Files:**
- Create: `backend/scripts/benchlib/corpus.py`
- Create: `backend/scripts/benchlib/ingest.py`
- Test: `backend/scripts/benchlib/tests/test_ingest.py`

**Interfaces:**
- Consumes: `bench_db.session_factory`; `CachingLLMOrchestrator`; `app.services.pipeline.ProcessingPipeline(llm, session_factory).process_batch(entries)` where each entry is `{"memory_id": UUID, "content": str, "source": str, "tags": list[str], "memory_type": str, "created_at": isoformat str}` (shape per `app/services/analytics.py:39-49`).
- Produces: `load_corpus(path) -> list[dict]`; `@dataclass IngestResult(ingested: int, live_calls: int, wall_s: float, statuses: list[dict])`; `async run_ingest(corpus: list[dict], llm: CachingLLMOrchestrator) -> IngestResult`.

- [ ] **Step 1: Write the failing test**

`backend/scripts/benchlib/tests/test_ingest.py`:
```python
import json

import pytest
from sqlalchemy import text

from benchlib import bench_db, ingest
from benchlib.caching_llm import CachingLLMOrchestrator

# A stubbed orchestrator: valid extraction JSON + a fixed embedding, so
# process_batch runs fully offline and deterministically.
_EXTRACTION = json.dumps({
    "entities": [{"name": "postgres", "type": "database"}],
    "relationships": [],
    "memory_type": "fact",
    "summary": "test", "emotions": [], "flags": [],
})


class _StubLLM(CachingLLMOrchestrator):
    async def _live_embed(self, text):
        return ([0.05] * 32, "benchstub")

    async def _live_chat(self, purpose, messages, **kwargs):
        return _EXTRACTION


@pytest.mark.asyncio
async def test_ingest_writes_rows(tmp_path):
    await bench_db.reset_bench_db()
    corpus = [
        {"content": "We use postgres for storage.", "source": "bench",
         "tags": [], "memory_type": "fact"},
    ]
    llm = _StubLLM({}, cache_dir=str(tmp_path / "cache"))
    result = await ingest.run_ingest(corpus, llm)
    assert result.ingested == 1
    async with bench_db.session_factory() as s:
        n = (await s.execute(text("SELECT count(*) FROM memories"))).scalar()
    assert n == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest scripts/benchlib/tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'benchlib.ingest'`.

- [ ] **Step 3: Write minimal implementation**

`backend/scripts/benchlib/corpus.py`:
```python
"""Load a bench corpus from a JSON file: {"memories": [ {content, source, ...} ]}."""
import json


def load_corpus(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["memories"]
```

`backend/scripts/benchlib/ingest.py`:
```python
"""Offline ingest driver: push a corpus through the REAL ProcessingPipeline
against the bench DB, with a caching orchestrator so reruns are free.
"""
import time
import uuid
from dataclasses import dataclass, field

from benchlib import bench_db
from benchlib.caching_llm import CachingLLMOrchestrator
from app.services.pipeline import ProcessingPipeline


@dataclass
class IngestResult:
    ingested: int
    live_calls: int
    wall_s: float
    statuses: list = field(default_factory=list)


def _to_entry(item: dict) -> dict:
    # created_at is set per item so bench runs are date-stable if the corpus
    # supplies it; otherwise the pipeline stamps its own server-side value.
    entry = {
        "memory_id": item.get("memory_id") or uuid.uuid4(),
        "content": item["content"],
        "source": item.get("source", "bench"),
        "tags": item.get("tags", []),
        "memory_type": item.get("memory_type", "fact"),
    }
    if item.get("created_at"):
        entry["created_at"] = item["created_at"]
    return entry


async def run_ingest(corpus: list[dict], llm: CachingLLMOrchestrator) -> IngestResult:
    entries = [_to_entry(item) for item in corpus]
    pipeline = ProcessingPipeline(llm, bench_db.session_factory)
    start = time.perf_counter()
    statuses = await pipeline.process_batch(entries)
    wall_s = time.perf_counter() - start
    ingested = sum(1 for st in statuses if not st.get("error"))
    return IngestResult(
        ingested=ingested, live_calls=llm.live_calls, wall_s=wall_s, statuses=statuses,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest scripts/benchlib/tests/test_ingest.py -v`
Expected: PASS. If it fails because `process_batch` reached the model through a method other than `embed`/`chat_completion` (a batch-embed helper), add an override for that method to `CachingLLMOrchestrator` mirroring `embed`, then re-run — the stub forces every model path through the overridden methods.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/benchlib/corpus.py backend/scripts/benchlib/ingest.py backend/scripts/benchlib/tests/test_ingest.py
git commit -m "feat(harness): offline process_batch ingest driver"
```

---

### Task 5: End-to-end smoke gate (`run_smoke.py`, `smoke/corpus.json`)

**Files:**
- Create: `backend/scripts/benchlib/smoke/corpus.json`
- Create: `backend/scripts/benchlib/run_smoke.py`

**Interfaces:**
- Consumes: `bench_db.reset_bench_db`, `corpus.load_corpus`, `ingest.run_ingest`, `CachingLLMOrchestrator`, `ledger.record_run`, and `app.services.config.get_llm_config` (for the live LLM config on the first run).
- Produces: a CLI that ingests the smoke corpus twice and asserts the second run makes zero live LLM calls. This is the affordability gate; it needs a live LLM config (like `extraction_bench`) for the first run only.

- [ ] **Step 1: Write the smoke corpus**

`backend/scripts/benchlib/smoke/corpus.json`:
```json
{
  "memories": [
    {"content": "Darkmem stores memories in Postgres with pgvector for semantic search.", "source": "bench", "memory_type": "fact", "created_at": "2026-01-02T00:00:00+00:00"},
    {"content": "The ingestion pipeline runs five phases ending in a write step.", "source": "bench", "memory_type": "fact", "created_at": "2026-01-03T00:00:00+00:00"},
    {"content": "Retrieval fuses vector and full-text search with Reciprocal Rank Fusion.", "source": "bench", "memory_type": "fact", "created_at": "2026-01-04T00:00:00+00:00"}
  ]
}
```

- [ ] **Step 2: Write the gate script**

`backend/scripts/benchlib/run_smoke.py`:
```python
"""Walking-skeleton gate: reset the bench DB, ingest the smoke corpus twice, and
prove the second run replays entirely from cache (zero live LLM calls).

First run needs a live LLM config (reads the darkmem `llm_*` config rows via the
app default DATABASE_URL is NOT used — we read config from the bench DB, so seed
it once or point BENCH at a DB that has llm config; see FROZEN.md). Subsequent
runs are free. Exit non-zero if the affordability property fails.
"""
import asyncio
import os
import sys

from benchlib import bench_db  # sets DATABASE_URL to bench first
from benchlib import corpus as corpus_mod
from benchlib import ingest, ledger
from benchlib.caching_llm import CachingLLMOrchestrator
from app.database import async_session_factory
from app.services.config import get_llm_config

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".smoke_cache")
LEDGER = os.path.join(HERE, ".runs", "smoke.jsonl")


async def _one_run(corpus, tag) -> ingest.IngestResult:
    async with async_session_factory() as s:
        cfg = await get_llm_config(s)
    llm = CachingLLMOrchestrator(cfg, cache_dir=CACHE)
    result = await ingest.run_ingest(corpus, llm)
    ledger.record_run(LEDGER, {
        "bench": "smoke", "tag": tag, "ingested": result.ingested,
        "live_calls": result.live_calls, "wall_s": round(result.wall_s, 3),
    })
    return result


async def main() -> int:
    await bench_db.reset_bench_db()
    corpus = corpus_mod.load_corpus(os.path.join(HERE, "smoke", "corpus.json"))

    first = await _one_run(corpus, "first")
    print(f"first : ingested={first.ingested} live_calls={first.live_calls} wall={first.wall_s:.2f}s")

    await bench_db.reset_bench_db()  # clean DB, warm cache
    second = await _one_run(corpus, "second")
    print(f"second: ingested={second.ingested} live_calls={second.live_calls} wall={second.wall_s:.2f}s")

    ok = first.ingested == 3 and second.ingested == 3 and second.live_calls == 0
    print("GATE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 3: Run the gate (needs a live LLM config in the bench DB)**

Run (from `backend/`): `python scripts/benchlib/run_smoke.py`
Expected: prints a `first` line with `live_calls > 0`, a `second` line with `live_calls=0`, both `ingested=3`, and `GATE: PASS` (exit 0).
If the first run errors with no LLM config, seed the bench DB's `llm_*` rows once via the setup wizard's seed (see FROZEN.md) or copy them from the dev DB; this is a one-time bench-DB setup, recorded in Task 6.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/benchlib/smoke/corpus.json backend/scripts/benchlib/run_smoke.py
git commit -m "feat(harness): benchlib smoke gate proves cache-replay affordability"
```

---

### Task 6: Freeze decisions + wire the co-gate (`FROZEN.md`)

**Files:**
- Create: `backend/scripts/benchlib/FROZEN.md`

**Interfaces:** none (documentation + co-gate wiring).

- [ ] **Step 1: Write the frozen-decisions doc**

`backend/scripts/benchlib/FROZEN.md`:
```markdown
# benchlib — frozen decisions (do not change without re-baselining)

- **Ingestion granularity:** memory-per-corpus-entry (one `process_batch` entry per
  `memories[]` item). Changing this changes what every bench measures.
- **Bench database:** `darkmem_bench` on 127.0.0.1:5433, never the real or
  darkmem_test DB. Reset = DROP SCHEMA CASCADE + `alembic upgrade head`.
- **Bench-DB LLM config:** the bench DB needs `llm_*` config rows for a live first
  run. One-time setup: <record here the exact command used, e.g. copy the dev DB's
  llm_* config rows or run the setup seed against BENCH_DATABASE_URL>.
- **LLM cache key:** sha256 over (kind, purpose, messages, sorted kwargs) / (kind,
  text). Changing a prompt or the gate state changes the key automatically.
- **Co-gate:** `extraction_bench` must stay green; run it alongside benchlib.
```

- [ ] **Step 2: Verify the co-gate still passes**

Run (from `backend/`): `python scripts/extraction_bench/run_bench.py --algo-only`
Expected: PASS (aggregate F1 table prints; no `--algo-only but no cached LLM output` error). If it errors on a cold cache, run `python scripts/extraction_bench/run_bench.py` once first.

- [ ] **Step 3: Run the whole benchlib unit suite green**

Run (from `backend/`): `python -m pytest scripts/benchlib/tests -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/benchlib/FROZEN.md
git commit -m "docs(harness): freeze benchlib ingestion-granularity + bench-DB setup"
```

---

## Self-Review

- **Spec coverage** (against review §3.3 walking skeleton): shared bench-DB reset → Task 1; offline `process_batch` runner → Task 4; caching LLM wrapper → Task 2; results ledger → Task 3; "run twice, second run ~zero LLM calls" → Task 5 gate; `extraction_bench` co-gate → Task 6. `longmemeval_bench` fixtures + `curation_bench` are explicitly deferred to the next plan (they need the LongMemEval-source and judge-model decisions). `ui_fixtures` is a later plan.
- **Placeholder scan:** the only intentionally-open item is the bench-DB `llm_*` seeding command in FROZEN.md Task 6 Step 1, which is an environment fact to be filled at run time, not code — kept out of code paths. No `TODO`/`handle edge cases`/`similar to Task N` remain.
- **Type consistency:** `CachingLLMOrchestrator(config, cache_dir)` + `live_calls` used identically in Tasks 2/4/5; `run_ingest(corpus, llm) -> IngestResult(ingested, live_calls, wall_s, statuses)` consumed unchanged in Task 5; `record_run(path, run)` / `read_runs(path)` consistent in Tasks 3/5; entry dict keys match `analytics.py:39-49`.

## Known risks (surface during execution, not placeholders)
- If `ProcessingPipeline.process_batch` reaches the model via a batch-embed helper, Task 4 Step 4 fails the row-count/`live_calls` expectation → add the override (instruction is in Task 4 Step 4).
- The smoke gate's first run needs `llm_*` config in the bench DB; the one-time seeding is recorded in FROZEN.md and is a bench-DB setup step, not a code task.
