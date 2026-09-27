# Work-log increment 4: the memory-door warning — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A capture that looks like working data is still stored, but all four capture doors answer `warnings` naming the signals it matched, and each flagged capture journals `capture_flagged`.

**Architecture:** A pure detector, `app/services/capture_lint.py`, returns a capture's signal names and its warnings. `MemoryService._capture_batch`, which all four doors already call, puts the warnings on each `CaptureAck` and journals `capture_flagged` in the capture's own transaction. The 201 (`wait_process`) answers carry the ack's warnings beside the processed memory: `CapturedMemoryResponse` on REST, a `warnings` key on the MCP tool's memory object.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy async, pytest; TypeScript for two one-line frontend mirrors.

**Spec:** docs/superpowers/specs/2026-09-23-work-log-lane-design.md

**Execution:** inline — `claude --model sonnet --effort high` — two of six tasks are delegated (Task 3 heavy at 5, Task 4 four-band at 4, one four-band task in six is within a third); the self-implemented tasks top out at 2 (medium), raised to high because tasks are delegated.

**Plan review:** 2026-09-27 — dr-superpowers:judge-opus — executability 15 / coherence 14 / coverage 15 / assumptions 16 (round 1)

## Global Constraints

- A flag never refuses a capture: every flagged capture is buffered and answered exactly as today, plus `warnings` (spec §5, "A flag never refuses").
- The detector is a pure function over the content: no LLM, no database (spec §5).
- Signal patterns and thresholds are module constants pinned by fixtures, not configuration (spec §5).
- `warnings: list[str]` — empty when clean; per entry for batches (spec §5).
- `MemoryResponse` itself gains no field; only the capture routes serve `CapturedMemoryResponse` (spec §5).
- The `capture_flagged` journal row has `object_type='memory'` and a payload of signal names only — never content (spec §5; CLAUDE.md "Write-time minimisation is the standing rule").
- `record_event` stays non-raising; the capture must survive a journal failure (CLAUDE.md, Events journal).
- Run backend tests from `backend/` as `.venv/bin/python -m pytest`, always with `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2` and a Bash timeout. Never point pytest at production, and never run it without that variable: conftest drops the `public` schema of whatever test database it resolves, and the default is the controller's `darkmem_test`.
- If the dev Postgres is stopped, start only its service: `docker compose -f docker-compose.dev.yml up -d postgres` (repo root). Stop it again when the plan is done.
- `rg` is a shell function on this host: never pipe a file list into `xargs rg`.
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Contracts

- **`app/services/capture_lint.py`** (Task 1):
  - `LENGTH_LIMIT: int = 1500`, `MIN_SIGNALS: int = 2`
  - `SIGNAL_NAMES: tuple[str, ...] = ("commit_ref", "tally", "progress", "vcs_event", "file_line", "trace", "narration", "length")`
  - `signals(content: str) -> list[str]` — matched names in `SIGNAL_NAMES` order.
  - `is_flagged(found: Sequence[str]) -> bool` — `"length" in found or len(found) >= MIN_SIGNALS`.
  - `warning(found: Sequence[str]) -> str` — names the signals and points at `worklog_append` and `document_put`.
  - `lint(content: str) -> tuple[list[str], list[str]]` — `(signals, warnings)`; warnings is `[]` or `[warning(signals)]`.
- **Event type `capture_flagged`** (Task 2): a member of `EVENT_TYPES` in `app/services/events.py`, classified under the `capture` tab in `frontend/src/features/activity/event-taxonomy.ts`. Row shape (written in Task 3): `object_type="memory"`, `object_id=<pre-minted memory id>`, `project=<capture project>`, `actor`, `api_key_id`, `source=<capture source>`, `payload={"signals": <signals list>}`.
- **`CaptureAck.warnings: list[str]`** (Task 3), default empty, in `app/schemas/memory.py`. Every `CaptureResult` carries it on `result.ack.warnings`, including results that also carry a processed `memory`.
- **`CapturedMemoryResponse(MemoryResponse)`** (Task 4), in `app/schemas/memory.py`: one extra field, `warnings: list[str]`. Served only by `POST /api/v1/memories` and `POST /api/v1/memories/batch` on their 201 path.
- **MCP 201 answer** (Task 4): `memory_add` / `memory_batch_add` return `{**memory_to_dict(memory), "warnings": [...]}` for a processed memory.
- **Test module `backend/tests/test_capture_warnings.py`** (created in Task 2, extended in Tasks 3 and 4) with shared constants `LOG = "Task 5 complete: 7708 passed after merging e4363418."` and `FACT = "Postgres must listen on all addresses because the API connects across the stack network."` (Task 2), and the helpers `_flagged(session)` and `_mcp_on(session, monkeypatch)` (Task 3; `_mcp_on` returns the MCP server module wired to the test session with no pipeline).

## Assumptions (evidence)

- Calibration (spec §5's first-task requirement) ran on 2026-09-27 during planning with the exact Task 1 code, over `/root/darkmem-migration-195/lineage.jsonl` (785 originals, 6,234 cleaned atoms; user data outside the repository; the spec's 787 counts the two exact duplicates `clean-report.json` lists under `dropped_exact_duplicates`, which have no lineage row): **636 / 785 originals flagged (81.0%)**, **10 / 6,234 cleaned pieces flagged (0.16%)**. The spec's constants (two signals, 1,500 characters) were kept: `MIN_SIGNALS=3` drops originals to 77.6%, and `LENGTH_LIMIT=1000` flags atoms longer than 1,000 characters. All 10 flagged atoms carry a `file:line` or a commit reference, which the no-log rule also excludes. Task 1 Step 5 re-runs the measurement.
- The Task 1 fixtures pass against the Task 1 code: 31 passed on 2026-09-27 (scratch run of the exact test file below).
- All four doors reach `MemoryService._capture_batch`: REST single and batch via `create_memory` / `batch_create_memories` (`backend/app/api/routes/memories.py:145`, `:346`), MCP `memory_add` (`backend/app/api/mcp/server.py:217`) and `memory_batch_add` (`server.py:396`). `create_memory` delegates to `_capture_batch` (`backend/app/services/memory.py:107`).
- The MCP ack is serialised from the schema (`_ack_to_dict`, `server.py:143`), so `CaptureAck.warnings` reaches the MCP 202 answer with no MCP change.
- `tests/test_envelope.py:909` compares the REST ack's keys with `CaptureAck.model_fields` (it follows the new field on its own); `tests/test_envelope.py:922` compares the 201 keys with `MemoryResponse.model_fields` and must move to `CapturedMemoryResponse` (Task 4). `tests/test_envelope.py:891` covers `memory_get` and must keep `MemoryResponse`.
- `tests/test_event_taxonomy_map.py:230` fails when an `EVENT_TYPES` value with a live emitter has no frontend classification, so Task 2 lands the classification before Task 3 emits.
- `events` has `project`, `source`, `object_id` and `payload` columns (`backend/migrations/versions/0001_baseline.py:1594-1606`); no schema change is needed.
- `RecordingPipeline` (`backend/tests/test_buffer_flush.py`) settles `wait_process` captures in tests, used as `app.state.pipeline` for REST and `mcp_server.set_pipeline(...)` for MCP (`backend/tests/test_wait_process.py:119-151`).
- The agent instructions already carry the work-log section and the promotion rule (checked 2026-09-27: `prompt.PROMPTS["agent_instructions"]` contains "Work log" and "After a checkpoint, file the durable facts"), so Task 5 adds only the warnings sentence.
- The TypeScript SDK's `CaptureAck` type (`sdks/generate.py:344`) is left without `warnings`: the SDK's verbs read only `id`, and the field still arrives at runtime.
- The next release derived from `feat` commits is v1.13.0: after `git fetch --tags` on 2026-09-27 the newest tag is `v1.12.0`, and `scripts/next_version.py plan` reports `previous_tag: v1.12.0` with no releasable commit yet, so this plan's `feat` commits make a minor bump. Task 6 opens a `## v1.13.0` CHANGELOG section.
- plan-lint's `placeholder` warning on Task 1 is the `narration` signal's fixture `"TODO: rewrite the importer."`: the literal word is the input under test, not an unfinished step.
- `app/services/auto_research.py:567` (`research_run`) is a fifth caller of `batch_create_memories`. Research filings are linted and journal `capture_flagged` like any capture, but the `research_run` answer does not surface `warnings`; that is accepted, because the tool files evidence the caller gathered and its answer names the filed ids only.
- Finishing is the executing skill's, not a task's: after Task 6 the controller runs `./scripts/gate.sh`, merges, redeploys this host (CLAUDE.md's redeploy sequence; no schema change, so no database step), stops the dev Postgres it started, and sets register row 61. Register row 23 stays parked: its trigger is thin memories appearing, which this increment does not measure.
- The Codex executor lane is closed on this account (`codex-gate usable=false reason=free-plan lane=false`, 2026-09-27), so no task carries an `**Executor:**` line.

## Task index

1. The detector
2. The capture_flagged vocabulary
3. Warnings on the buffered ack, and the journal row
4. Warnings on the processed answers
5. Agent guidance and the parity record
6. Records, the frontend mirror, and the full run

---

### Task 1: The detector

**Files:**
- Create: `backend/app/services/capture_lint.py`
- Test: `backend/tests/test_capture_lint.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `app/services/capture_lint.py` exactly as in Contracts.

**Items:** 61

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_capture_lint.py`:

```python
"""The memory-door detector: each signal, both thresholds, the answer."""
from __future__ import annotations

import pytest

from app.services import capture_lint

ONE_SIGNAL = [
    ("commit_ref", "The fix landed in e4363418 on master's tip."),
    ("commit_ref", "Compare a6937345..fd8d2865 for the change."),
    ("tally", "The suite reported 7708 passed."),
    ("tally", "Three shards, 3/4 finished."),
    ("tally", "The branch carries 76 commits."),
    ("tally", "Finished 5 of 12 tasks."),
    ("progress", "Task 5 complete."),
    ("progress", "Phase 2 has started."),
    ("progress", "Everything is all green."),
    ("vcs_event", "The fix was merged into master."),
    ("vcs_event", "The tag was pushed."),
    ("vcs_event", "The feature branch was deleted."),
    ("file_line", "The handler lives at backend/app/main.py:1005 now."),
    ("trace", "Traceback (most recent call last):\n  boom"),
    ("trace", "failed at com.example.Worker.run( with nothing"),
    ("trace", "RuntimeException: boom"),
    ("narration", "In this session the importer was rewritten."),
    ("narration", "Next steps: rewrite the importer."),
    ("narration", "TODO: rewrite the importer."),
]

NO_SIGNAL = [
    "Postgres must listen on all addresses because the API connects across the stack network.",
    "Row 3f2a1c9e-1b2c-4d5e-8f90-123456789abc is a UUID, not a commit.",
    "The value deadbeefcafe has no digit and 1234567 has no letter.",
    "The merge queue passed the check.",
    "The task runner completes jobs on time.",
    "An exception handler maps the error.",
    "A todo list app stores items.",
    "The handler lives in backend/app/main.py.",
]


@pytest.mark.parametrize("name,text", ONE_SIGNAL)
def test_each_signal_matches_alone_and_does_not_flag(name, text):
    found, warnings = capture_lint.lint(text)
    assert found == [name]
    assert warnings == []


@pytest.mark.parametrize("text", NO_SIGNAL)
def test_a_durable_fact_matches_nothing(text):
    assert capture_lint.lint(text) == ([], [])


def test_two_signals_flag():
    found, warnings = capture_lint.lint("Task 5 complete: 7708 passed.")
    assert found == ["tally", "progress"]
    assert capture_lint.is_flagged(found)
    assert warnings == [capture_lint.warning(found)]


def test_the_length_bound_is_exclusive_and_flags_alone():
    at_limit = "x" * capture_lint.LENGTH_LIMIT
    assert capture_lint.lint(at_limit) == ([], [])
    found, warnings = capture_lint.lint(at_limit + "x")
    assert found == ["length"]
    assert len(warnings) == 1


def test_the_constants_are_the_calibrated_ones():
    assert capture_lint.LENGTH_LIMIT == 1500
    assert capture_lint.MIN_SIGNALS == 2
    assert capture_lint.SIGNAL_NAMES == (
        "commit_ref", "tally", "progress", "vcs_event", "file_line", "trace", "narration", "length",
    )


def test_the_warning_names_the_signals_and_where_the_content_belongs():
    text = capture_lint.warning(["commit_ref", "vcs_event"])
    assert "commit_ref, vcs_event" in text
    assert "worklog_append" in text
    assert "document_put" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_lint.py`
Expected: collection error, `ImportError: cannot import name 'capture_lint'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/capture_lint.py`:

```python
"""Log-shaped content at the memory door: named signals, no model, no database.

A capture is flagged when two or more content signals match, or when it is
longer than LENGTH_LIMIT alone. A flag never refuses a capture; the doors
answer it as a warning and journal `capture_flagged` with the signal names.

The patterns and both thresholds were calibrated on 2026-09-27 against the
2026-09-23 migration lineage (user data, kept outside the repository): they
flag 81.0% of the 785 original memories and 0.16% of the 6,234 cleaned
pieces. Change one only with a new measurement over the same lineage.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

LENGTH_LIMIT = 1500
MIN_SIGNALS = 2

_PATTERNS: dict[str, re.Pattern[str]] = {
    # A hex token with at least one letter and one digit, not a fragment of a
    # longer word or of a UUID (whose segments sit between hyphens); or a
    # `<sha>..<sha>` range.
    "commit_ref": re.compile(
        r"(?<![0-9A-Za-z-])(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,40}(?![0-9A-Za-z-])"
        r"|\b[0-9a-f]{7,40}\.\.\.?[0-9a-f]{7,40}\b"
    ),
    "tally": re.compile(
        r"\b\d+ (?:passed|failed)\b|\b\d+/\d+\b|\b\d+ commits?\b|\b\d+ of \d+ tasks\b",
        re.IGNORECASE,
    ),
    "progress": re.compile(
        r"\b(?:task|phase|wave) \d+\b[^.\n]{0,40}?\b(?:complete|completed|done|started)\b"
        r"|\ball green\b",
        re.IGNORECASE,
    ),
    "vcs_event": re.compile(
        r"\b(?:merged|pushed|fast-forwarded|fast forwarded)\b"
        r"|\bbranch (?:was )?deleted\b|\bdeleted (?:the )?branch\b",
        re.IGNORECASE,
    ),
    "file_line": re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,6}:\d+\b"),
    "trace": re.compile(r"^Traceback|\bat [\w.$]+\.[\w$<>]+\(|\b\w*Exception:", re.MULTILINE),
    "narration": re.compile(r"(?i:\bthis session\b|\bnext steps\b)|\bTODO\b"),
}

SIGNAL_NAMES: tuple[str, ...] = (*_PATTERNS, "length")


def signals(content: str) -> list[str]:
    """Every signal the content matches, in SIGNAL_NAMES order."""
    found = [name for name, pattern in _PATTERNS.items() if pattern.search(content)]
    if len(content) > LENGTH_LIMIT:
        found.append("length")
    return found


def is_flagged(found: Sequence[str]) -> bool:
    """Two or more content signals, or the length signal on its own."""
    return "length" in found or len(found) >= MIN_SIGNALS


def warning(found: Sequence[str]) -> str:
    """The answer's warning for a flagged capture."""
    return (
        f"This capture looks like working data ({', '.join(found)}). It was stored, "
        "but a memory should hold one durable fact: send checkpoints, progress and "
        "logs to worklog_append and long write-ups to document_put."
    )


def lint(content: str) -> tuple[list[str], list[str]]:
    """The content's signals and the warnings a capture door answers for it.

    Warnings are empty when the capture is not flagged; the signals are
    returned either way.
    """
    found = signals(content)
    return found, [warning(found)] if is_flagged(found) else []
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_lint.py`
Expected: `31 passed`.

- [ ] **Step 5: Re-measure the calibration**

Run (from `backend/`; reads user data outside the repository and writes nothing):

```bash
.venv/bin/python - <<'EOF'
import json
from app.services import capture_lint
rows = [json.loads(line) for line in open("/root/darkmem-migration-195/lineage.jsonl")]
originals = [r["original"] for r in rows]
atoms = [a["content"] for r in rows for a in r["atoms"]]
flag = lambda xs: sum(bool(capture_lint.lint(x)[1]) for x in xs)
print(f"originals {flag(originals)}/{len(originals)}  atoms {flag(atoms)}/{len(atoms)}")
EOF
```

Expected: `originals 636/785  atoms 10/6234`. If the file is missing, say so in the task report and continue; the numbers are already recorded in the module docstring and this plan's Assumptions.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/capture_lint.py backend/tests/test_capture_lint.py
git commit -m "feat(capture): flag log-shaped memory content

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The capture_flagged vocabulary

**Files:**
- Modify: `backend/app/services/events.py` (the `EVENT_TYPES` list, after `"workstream_purged",`)
- Modify: `frontend/src/features/activity/event-taxonomy.ts` (the `EVENT_TYPE_CATEGORY` object, after `pages_imported: "capture",`)
- Modify: `frontend/src/features/activity/use-feed.ts` (`fromEventLog`, lines 44-61)
- Create: `backend/tests/test_capture_warnings.py`
- Test: `frontend/src/features/activity/__tests__/use-feed.real.test.tsx`

**Interfaces:**
- Consumes: nothing.
- Produces: the event type `capture_flagged` and the test module with `LOG` / `FACT`, as in Contracts; Activity feed rows that name a payload's `signals`.

**Items:** 61

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_capture_warnings.py`:

```python
"""The memory-door warning (work-log spec §5) on all four capture doors."""
from __future__ import annotations

from app.services.events import EVENT_TYPES

LOG = "Task 5 complete: 7708 passed after merging e4363418."
FACT = "Postgres must listen on all addresses because the API connects across the stack network."


def test_the_vocabulary_carries_capture_flagged():
    from tests.test_event_taxonomy_map import _parse_frontend_map

    assert "capture_flagged" in EVENT_TYPES
    tabbed, _untabbed = _parse_frontend_map()
    assert "capture_flagged" in tabbed
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_warnings.py`
Expected: FAIL, `assert 'capture_flagged' in [...]`.

- [ ] **Step 3: Add the event type**

In `backend/app/services/events.py`, inside `EVENT_TYPES`, directly after the line `"workstream_purged",` insert:

```python
    # The memory-door warning (spec 2026-09-23 §5): a capture capture_lint
    # flagged. The payload carries signal names only, never the content.
    "capture_flagged",
```

- [ ] **Step 4: Classify it in the frontend map**

In `frontend/src/features/activity/event-taxonomy.ts`, inside `EVENT_TYPE_CATEGORY`, directly after the line `pages_imported: "capture",` insert:

```ts
  // The memory-door warning (work-log spec §5). Capture, beside the `created`
  // row the same capture journals: it annotates that capture.
  capture_flagged: "capture",
```

- [ ] **Step 5: Write the failing feed test**

Spec §8 asks that flagged captures show in the Activity feed with their signal names. In `frontend/src/features/activity/__tests__/use-feed.real.test.tsx`, inside the `describe` block, after the first `it(...)`, add:

```tsx
  it("names a capture_flagged row's signals", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: 2,
          created_at: "2026-09-27T18:55:00Z",
          event_type: "capture_flagged",
          object_type: "memory",
          object_id: "11111111-2222-3333-4444-555555555555",
          project: "darkmem",
          actor: null,
          api_key_id: null,
          source: null,
          payload: { signals: ["commit_ref", "tally"] },
        },
      ],
      total: 1,
    })
    const { result } = renderHook(() => useFeed(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.events[0]!.category).toBe("capture")
    expect(result.current.events[0]!.text).toContain("signals: commit_ref, tally")
  })
```

Run (from `frontend/`): `timeout 600 npm test -- src/features/activity/__tests__/use-feed.real.test.tsx`
Expected: the new case FAILS on the `signals:` assertion.

- [ ] **Step 6: Name the signals in the feed row**

In `frontend/src/features/activity/use-feed.ts`, in `fromEventLog`, replace:

```ts
  const text = [object, entry.project ? `· project ${entry.project}` : null, outcome]
```

with:

```ts
  const raw = entry.payload.signals
  const signals =
    Array.isArray(raw) && raw.every((s) => typeof s === "string")
      ? `signals: ${raw.join(", ")}`
      : null
  const text = [object, entry.project ? `· project ${entry.project}` : null, outcome, signals]
```

- [ ] **Step 7: Run the tests**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_warnings.py tests/test_event_taxonomy_map.py tests/test_events.py`
Expected: all pass.

Run (from `frontend/`): `timeout 600 npm run typecheck && timeout 900 npm test -- src/features/activity`
Expected: typecheck exit 0; the activity tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/events.py frontend/src/features/activity/event-taxonomy.ts frontend/src/features/activity/use-feed.ts frontend/src/features/activity/__tests__/use-feed.real.test.tsx backend/tests/test_capture_warnings.py
git commit -m "feat(events): add the capture_flagged event type

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Warnings on the buffered ack, and the journal row

**Files:**
- Modify: `backend/app/schemas/memory.py` (`class CaptureAck`, line 70)
- Modify: `backend/app/services/memory.py` (imports; `_capture_batch`, lines 129-230)
- Test: `backend/tests/test_capture_warnings.py`

**Interfaces:**
- Consumes: `capture_lint.lint` (Task 1); event type `capture_flagged` and the test module's `LOG` / `FACT` (Task 2).
- Produces: `CaptureAck.warnings` and the `capture_flagged` row shape, as in Contracts.

**Items:** 61

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_capture_warnings.py`, and add these imports below `from __future__ import annotations` (keep the existing `EVENT_TYPES` import):

```python
import json
from contextlib import asynccontextmanager

from sqlalchemy import func, select, text

from app.models.memory import MemoryBuffer
from app.schemas.memory import MemoryCreate
from app.services import capture_lint
from app.services.memory import MemoryService
```

Tests to append:

```python
async def _flagged(session):
    rows = await session.execute(text(
        "SELECT object_type, object_id, project, source, payload FROM events "
        "WHERE event_type = 'capture_flagged' ORDER BY created_at, id"
    ))
    return rows.all()


@asynccontextmanager
async def _on_the_test_session(session):
    yield session


def _mcp_on(session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _on_the_test_session(session))
    mcp_server.set_pipeline(None)
    return mcp_server


async def test_a_flagged_capture_is_buffered_answered_and_journalled(session):
    found, warnings = capture_lint.lint(LOG)
    result = await MemoryService(session).create_memory(
        MemoryCreate(content=LOG, source="test", project="proj"), api_key_id=None,
    )
    assert warnings and result.ack.warnings == warnings
    assert (await session.execute(select(func.count()).select_from(MemoryBuffer))).scalar() == 1
    [(object_type, object_id, project, source, payload)] = await _flagged(session)
    assert (object_type, object_id, project, source) == ("memory", result.ack.id, "proj", "test")
    assert payload == {"signals": found}


async def test_a_clean_capture_has_no_warning_and_no_row(session):
    result = await MemoryService(session).create_memory(
        MemoryCreate(content=FACT, source="test"), api_key_id=None,
    )
    assert result.ack.warnings == []
    assert await _flagged(session) == []


async def test_a_batch_answers_warnings_per_entry(session):
    results = await MemoryService(session).batch_create_memories(
        [MemoryCreate(content=FACT, source="test"), MemoryCreate(content=LOG, source="test")],
        api_key_id=None,
    )
    assert [r.ack.warnings for r in results] == [[], capture_lint.lint(LOG)[1]]
    assert [row.object_id for row in await _flagged(session)] == [results[1].ack.id]


async def test_the_rest_doors_answer_warnings_on_the_ack(client, auth_headers, session):
    flagged = await client.post("/api/v1/memories", json={"content": LOG}, headers=auth_headers)
    assert flagged.status_code == 202
    assert flagged.json()["warnings"] == capture_lint.lint(LOG)[1]

    clean = await client.post("/api/v1/memories", json={"content": FACT}, headers=auth_headers)
    assert clean.json()["warnings"] == []

    batch = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": LOG}, {"content": FACT}]}, headers=auth_headers,
    )
    assert batch.status_code == 202
    assert [entry["warnings"] for entry in batch.json()] == [capture_lint.lint(LOG)[1], []]


async def test_the_mcp_doors_answer_warnings_on_the_ack(session, monkeypatch):
    mcp_server = _mcp_on(session, monkeypatch)

    ack = json.loads(await mcp_server.memory_add(content=LOG))
    assert ack["status"] == "accepted"
    assert ack["warnings"] == capture_lint.lint(LOG)[1]

    acks = json.loads(await mcp_server.memory_batch_add(entries=[{"content": FACT}, {"content": LOG}]))
    assert [a["warnings"] for a in acks] == [[], capture_lint.lint(LOG)[1]]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_warnings.py`
Expected: the five new tests FAIL (`AttributeError: 'CaptureAck' object has no attribute 'warnings'` or `KeyError: 'warnings'`); the vocabulary test passes.

- [ ] **Step 3: Add the field**

In `backend/app/schemas/memory.py`, replace the `CaptureAck` class with:

```python
class CaptureAck(BaseModel):
    """Tier-A accept response (doc 05 §2.2).

    ``id`` is the pre-minted **memory** id — the caller's durable reference,
    resolvable once the buffer flush (T1.13) runs. It is deliberately not the
    internal `memory_buffer` row's own id, which is a tracking handle the
    caller never sees (`memory_buffer.buffered_memory_id`).

    ``warnings`` is empty unless ``capture_lint`` flagged the content as
    working data. A flag never refuses: the capture is buffered either way.
    """

    schema_version: int = ENVELOPE_SCHEMA_VERSION
    id: uuid.UUID
    status: Literal["accepted"] = "accepted"
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Lint, journal and answer in `_capture_batch`**

In `backend/app/services/memory.py`:

1. Change the import line `from app.services import buffer_flush, memory_buffer, project_registry, repo_provision` to:

```python
from app.services import (
    buffer_flush,
    capture_lint,
    memory_buffer,
    project_registry,
    repo_provision,
)
from app.services.events import record_event
```

2. In `_capture_batch`, directly before the line `rows: list[MemoryBuffer] = []`, insert:

```python
        linted = [capture_lint.lint(data.content) for data in entries]
```

3. Directly after the loop that calls `self.audit_repo.log(...)` for each row (and before `await self._handoff_repo_hints(rows, entries)`), insert:

```python
        # A flag never refuses (spec 2026-09-23 §5); it journals which signals
        # matched, never the content, in the capture's own transaction.
        # `record_event` does not raise, so a journal failure costs the row,
        # not the capture.
        for row, data, (found, warnings) in zip(rows, entries, linted):
            if warnings:
                await record_event(
                    self.session,
                    event_type="capture_flagged",
                    object_type="memory",
                    object_id=buffered_memory_id(row),
                    project=data.project or "default",
                    actor=actor,
                    api_key_id=api_key_id,
                    source=data.source,
                    payload={"signals": found},
                )
```

4. Replace the line `acks = [CaptureAck(id=buffered_memory_id(row)) for row in rows]` with:

```python
        acks = [
            CaptureAck(id=buffered_memory_id(row), warnings=warnings)
            for row, (_found, warnings) in zip(rows, linted)
        ]
```

- [ ] **Step 5: Run the tests**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_capture_warnings.py tests/test_api/test_capture.py tests/test_envelope.py tests/test_wait_process.py tests/test_events.py tests/test_event_taxonomy_map.py tests/test_auto_research.py tests/test_mcp_batch.py`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/memory.py backend/app/services/memory.py backend/tests/test_capture_warnings.py
git commit -m "feat(capture): warn on log-shaped memory captures

A capture capture_lint flags is still buffered; its ack carries
warnings naming the signals, and it journals capture_flagged with the
signal names only.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Warnings on the processed answers

**Files:**
- Modify: `backend/app/schemas/memory.py` (add `CapturedMemoryResponse` directly after `class MemoryResponse`)
- Modify: `backend/app/api/routes/memories.py` (import line 18; `create_memory`'s return, lines 148-150; `batch_create`'s returned list, lines 354-357)
- Modify: `backend/app/api/mcp/server.py` (`memory_add` line 228; `memory_batch_add` lines 403-407)
- Modify: `backend/tests/test_envelope.py` (lines 916-922)
- Test: `backend/tests/test_capture_warnings.py`

**Interfaces:**
- Consumes: `CaptureAck.warnings` on `result.ack` (Task 3); the test module's `LOG`, `FACT`, `_mcp_on` (Tasks 2-3).
- Produces: `CapturedMemoryResponse` and the MCP 201 answer shape, as in Contracts.

**Items:** 61

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_capture_warnings.py`:

```python
async def test_the_rest_doors_answer_warnings_beside_the_processed_memory(client, auth_headers):
    from app.main import app
    from app.schemas.memory import CapturedMemoryResponse
    from tests.test_buffer_flush import RecordingPipeline

    app.state.pipeline = RecordingPipeline()
    try:
        single = await client.post(
            "/api/v1/memories?wait_process=true", json={"content": LOG}, headers=auth_headers,
        )
        batch = await client.post(
            "/api/v1/memories/batch?wait_process=true",
            json={"entries": [{"content": FACT}, {"content": LOG}]}, headers=auth_headers,
        )
    finally:
        app.state.pipeline = None

    assert single.status_code == 201
    body = single.json()
    assert set(body) == set(CapturedMemoryResponse.model_fields)
    assert body["content"] == LOG
    assert body["warnings"] == capture_lint.lint(LOG)[1]

    assert batch.status_code == 201
    assert [entry["warnings"] for entry in batch.json()] == [[], capture_lint.lint(LOG)[1]]

    # A read serves MemoryResponse, which has no warnings field.
    read = await client.get(f"/api/v1/memories/{body['id']}", headers=auth_headers)
    assert "warnings" not in read.json()


async def test_the_mcp_doors_answer_warnings_beside_the_processed_memory(session, monkeypatch):
    from tests.test_buffer_flush import RecordingPipeline

    mcp_server = _mcp_on(session, monkeypatch)
    mcp_server.set_pipeline(RecordingPipeline())
    try:
        single = json.loads(await mcp_server.memory_add(content=LOG, wait_process=True))
        batch = json.loads(await mcp_server.memory_batch_add(
            entries=[{"content": LOG}, {"content": FACT}], wait_process=True,
        ))
    finally:
        mcp_server.set_pipeline(None)

    assert single["content"] == LOG
    assert single["warnings"] == capture_lint.lint(LOG)[1]
    assert [(entry["content"], entry["warnings"]) for entry in batch] == [
        (LOG, capture_lint.lint(LOG)[1]), (FACT, []),
    ]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_capture_warnings.py -k processed_memory`
Expected: both FAIL (`ImportError: cannot import name 'CapturedMemoryResponse'`, and `KeyError: 'warnings'` on the MCP test).

- [ ] **Step 3: Add the schema**

In `backend/app/schemas/memory.py`, directly after the end of `class MemoryResponse` (it starts at line 154), add:

```python
class CapturedMemoryResponse(MemoryResponse):
    """A capture door's 201 answer: the processed memory plus the capture's warnings.

    Only the capture routes serve it. ``MemoryResponse`` is what every memory
    read serves, and a ``warnings`` field there would sit empty on every read.
    """

    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Serve it on the REST 201 path**

In `backend/app/api/routes/memories.py`:

1. Add `CapturedMemoryResponse` to the `from app.schemas.memory import ...` line (line 18), keeping the other names.
2. Directly after the `_to_response` function, add:

```python
def _captured(memory: Memory, warnings: list[str]) -> CapturedMemoryResponse:
    return CapturedMemoryResponse(**_to_response(memory).model_dump(), warnings=warnings)
```

3. In `create_memory`, replace `return _to_response(result.memory)` with `return _captured(result.memory, result.ack.warnings)`.
4. In `batch_create`, replace the returned list with:

```python
    return [
        _captured(r.memory, r.ack.warnings) if r.memory is not None else r.ack
        for r in results
    ]
```

- [ ] **Step 5: Serve it on the MCP 201 path**

In `backend/app/api/mcp/server.py`:

1. In `memory_add`, replace `return json.dumps(_memory_to_dict(result.memory))` with:

```python
            return json.dumps({**_memory_to_dict(result.memory), "warnings": result.ack.warnings})
```

2. In `memory_batch_add`, replace the returned list with:

```python
        return json.dumps([
            {**_memory_to_dict(r.memory), "warnings": r.ack.warnings} if r.memory is not None
            else _ack_to_dict(r.ack)
            for r in results
        ])
```

- [ ] **Step 6: Move the envelope test to the new 201 shape**

In `backend/tests/test_envelope.py`, in `test_the_ack_wire_shape_the_frontend_must_bind_to`, replace:

```python
    # `wait_process=true` still returns the settled memory, not the ack, so
    # the frontend's union is CaptureAck | MemoryResponse keyed on the status
    # code, never one or the other alone.
    from app.schemas.memory import MemoryResponse
```

with:

```python
    # `wait_process=true` still returns the settled memory, not the ack, so
    # the frontend's union is CaptureAck | CapturedMemoryResponse keyed on the
    # status code, never one or the other alone.
    from app.schemas.memory import CapturedMemoryResponse
```

and replace `assert set(settled.json()) == set(MemoryResponse.model_fields)` with `assert set(settled.json()) == set(CapturedMemoryResponse.model_fields)`. Leave `test_the_two_doors_return_the_same_memory_row_keys` (it reads `memory_get`) on `MemoryResponse`.

- [ ] **Step 7: Run the tests**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_capture_warnings.py tests/test_envelope.py tests/test_wait_process.py tests/test_api/test_memories.py tests/test_api/test_capture.py tests/test_mcp_batch.py tests/test_mcp_surface_parity.py tests/test_serialization_parity.py tests/test_api/test_rest_conformance.py tests/test_origin_key.py tests/test_services.py`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/memory.py backend/app/api/routes/memories.py backend/app/api/mcp/server.py backend/tests/test_envelope.py backend/tests/test_capture_warnings.py
git commit -m "feat(capture): carry warnings on the processed answer

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Agent guidance and the parity record

**Files:**
- Modify: `backend/app/services/prompt.py` (lines 666-668, the "Working data … never here." sentence)
- Modify: `backend/app/api/mcp/server.py` (the `memory_add` and `memory_batch_add` `description=` strings, lines 179 and 370)
- Modify: `backend/tests/test_prompt_agent_instructions.py` (append one test)
- Modify: `backend/tests/test_door_parity.py` (the `memory.capture` and `memory.capture_batch` `Surface` entries, around lines 615-627)
- Modify: `docs/two-door-parity.md` (regenerated, never hand-edited)

**Interfaces:**
- Consumes: the warnings behaviour of Tasks 3-4 (described, not called).
- Produces: nothing another task consumes.

**Items:** 61

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_prompt_agent_instructions.py`:

```python
def test_the_instructions_explain_capture_warnings():
    """A flagged capture is stored, so the agent must know what the warning asks."""
    import asyncio

    from app.api.mcp.server import mcp

    text = prompt.PROMPTS["agent_instructions"]
    assert "`warnings`" in text
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name in ("memory_add", "memory_batch_add"):
        assert "warnings" in (tools[name].description or ""), f"{name} must name its warnings"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 300 .venv/bin/python -m pytest -q tests/test_prompt_agent_instructions.py -k capture_warnings`
Expected: FAIL on `assert "`warnings`" in text`.

- [ ] **Step 3: Extend the instructions**

In `backend/app/services/prompt.py`, replace:

```python
        "progress line, a note to your next session — goes to the work log "
        "(below), never here.\n"
```

with:

```python
        "progress line, a note to your next session — goes to the work log "
        "(below), never here. A capture that looks like working data is still "
        "stored, but its answer carries `warnings` naming what matched: move "
        "that content to the work log or a document, and keep only the fact "
        "here.\n"
```

- [ ] **Step 4: Name the warnings in both tool descriptions**

In `backend/app/api/mcp/server.py`:

1. In the `memory_add` `description=` string, replace `A memory is not a log: store the durable fact, never commit hashes or ranges, test or commit counts, task progress, file:line references, stack traces, raw command output or session narrative.` with `A memory is not a log: store the durable fact, never commit hashes or ranges, test or commit counts, task progress, file:line references, stack traces, raw command output or session narrative. Content that looks like a log is still stored, and the answer's warnings name the signals it matched.`
2. In the `memory_batch_add` `description=` string, replace `and is not a log: no commit hashes, test counts, task progress, file:line references or stack traces;` with `and is not a log: no commit hashes, test counts, task progress, file:line references or stack traces (a log-like entry is still stored, with warnings naming what it matched);`

- [ ] **Step 5: Record the warnings on the parity surfaces**

In `backend/tests/test_door_parity.py`:

1. Give the `memory.capture` `Surface` (it has no `note=` today) this argument after `mcp=("memory_add",),`:

```python
        note=(
            "Both doors answer capture_lint's warnings: on the buffered ack, and "
            "beside the processed memory on the wait_process path "
            "(CapturedMemoryResponse on the route, a warnings key from the "
            "tool). A flag never refuses."
        ),
```

2. In the `memory.capture_batch` `Surface`, replace its note with:

```python
        note=(
            "Both doors resolve identity on the raw entry dicts before "
            "MemoryCreate validation, and both mirror the 1-100 cap. Both "
            "answer capture_lint's warnings per entry."
        ),
```

- [ ] **Step 6: Regenerate the parity document**

Run (from `backend/`):

```bash
.venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown
doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8")
EOF
git diff --stat ../docs/two-door-parity.md
```

Expected: `docs/two-door-parity.md` changes on exactly the two `memory.capture` rows (`git diff ../docs/two-door-parity.md` shows only those lines).

- [ ] **Step 7: Run the tests**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_prompt_agent_instructions.py tests/test_door_parity.py`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/prompt.py backend/app/api/mcp/server.py backend/tests/test_prompt_agent_instructions.py backend/tests/test_door_parity.py docs/two-door-parity.md
git commit -m "docs(mcp): tell agents what a capture warning means

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Records, the frontend mirror, and the full run

**Files:**
- Modify: `frontend/src/hooks/api/use-memory-api.ts` (`interface CaptureAck`, lines 114-122)
- Modify: `CLAUDE.md` (the "Capture is buffered" section, after the sentence ending "degrading to the plain ack after `buffer_wait_timeout_seconds`.")
- Modify: `CHANGELOG.md` (a new section above `## v1.12.0 — 2026-09-27`)
- Modify: `docs/superpowers/specs/2026-09-23-work-log-lane-design.md` (the header's status sentence)

**Interfaces:**
- Consumes: `CaptureAck.warnings`, `CapturedMemoryResponse`, `capture_flagged` (Tasks 2-4).
- Produces: nothing another task consumes.

**Items:** 61

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 0 = 2

- [ ] **Step 1: Mirror the field in the frontend type**

In `frontend/src/hooks/api/use-memory-api.ts`, replace:

```ts
export interface CaptureAck {
  schema_version: number
  id: string
  status: "accepted"
}
```

with:

```ts
export interface CaptureAck {
  schema_version: number
  id: string
  status: "accepted"
  // One warning line naming the signals capture_lint matched; empty for a
  // clean capture. A flagged capture is stored all the same.
  warnings: string[]
}
```

Run (from `frontend/`): `timeout 600 npm run typecheck && timeout 900 npm test -- src/features/memories`
Expected: typecheck exit 0; the memories tests pass. If a test builds a `CaptureAck` literal without `warnings` and typecheck fails on it, add `warnings: []` to that literal.

- [ ] **Step 2: State the rule in CLAUDE.md**

In `CLAUDE.md`, section "## Capture is buffered (`memory_buffer`, doc 05 §2)", directly after the sentence ending "degrading to the plain ack after `buffer_wait_timeout_seconds`.", insert:

```markdown
Every capture runs through `capture_lint` (a pure function: named signals,
two or more of them or over 1,500 characters flags). **A flag never
refuses**: the ack carries `warnings`, the 201 path answers
`CapturedMemoryResponse` (`MemoryResponse` plus `warnings`, served only by
the capture routes) or a `warnings` key from the tool, and the capture
journals `capture_flagged` with signal names only.
```

Reflow the paragraph to the file's existing line width (about 76 characters).

- [ ] **Step 3: Write the CHANGELOG section**

In `CHANGELOG.md`, directly above the line `## v1.12.0 — 2026-09-27`, insert:

```markdown
## v1.13.0 — unreleased

**The memory door warns about working data.** A capture that looks like a
log is still stored, but its answer now says so.

### Added

- **Capture warnings.** Every capture door (`POST /api/v1/memories`, its
  batch twin, `memory_add`, `memory_batch_add`) answers `warnings`: empty for
  a clean capture, and one line naming the matched signals (commit
  references, tallies, task progress, VCS events, `file:line`, stack traces,
  session narration, or over 1,500 characters) when two or more match or the
  content is over the length limit. The line points at `worklog_append` and
  `document_put`. Batches answer per entry, and the `wait_process` path
  answers the processed memory plus `warnings`.
- **`capture_flagged` events.** Each flagged capture journals the signal
  names it matched, never its content, on the Activity feed's capture tab.

```

Leave the heading's `unreleased` in place: the release cut dates it.

- [ ] **Step 4: Update the spec's status sentence**

In `docs/superpowers/specs/2026-09-23-work-log-lane-design.md`, replace:

```markdown
"Amended 2026-09-23" below. Increments 1-3 done and deployed on this host as
v1.12.0 (2026-09-27); increment 3's plan is
`docs/superpowers/plans/2026-09-25-work-log-increment-3-revisions.md`.
```

with:

```markdown
"Amended 2026-09-23" below. Increments 1-3 done and deployed on this host as
v1.12.0 (2026-09-27); increment 4 is planned in
`docs/superpowers/plans/2026-09-27-work-log-increment-4-capture-warning.md`.
```

- [ ] **Step 5: Run the guard leg and the full backend suite**

Run (from `backend/`; about one minute):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: all pass.

Then the full backend suite (about six minutes; check `free -h` first — swap above 80% means the OOM killer may end the run with exit 143, which is a kill, not a failure). Start it as a Bash call with `run_in_background: true`, writing to the session scratchpad directory (`$SCRATCH` below), and wait for its completion notification before reading the log:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  timeout 3000 .venv/bin/python -m pytest -q -p no:warnings > "$SCRATCH/inc4-full.log" 2>&1; echo "EXIT $?" >> "$SCRATCH/inc4-full.log"
```

Expected: the log ends `EXIT 0` after a `passed` line with no failures.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/api/use-memory-api.ts CLAUDE.md CHANGELOG.md docs/superpowers/specs/2026-09-23-work-log-lane-design.md
git commit -m "docs(capture): record the memory-door warning

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
