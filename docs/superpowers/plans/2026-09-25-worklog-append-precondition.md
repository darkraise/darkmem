# Work-log Append Precondition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a work-log append carry `expected_last_seq`, a compare-and-set on the newest entry of its kind, on both doors, and answer `last_seq`.

**Architecture:** `worklog.append` checks the precondition under the workstream row lock it already takes, inside its savepoint, and raises `WorklogSeqConflict` on a mismatch. The shared `WorklogAppendRequest` carries the field to both doors; the route maps the conflict to 409 and the MCP tool to a `seq_conflict` envelope.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 async, Postgres, pytest.

**Spec:** docs/superpowers/specs/2026-09-25-worklog-append-precondition-design.md

**Execution:** subagent — `claude --model sonnet --effort high` — both tasks are heavy: the service task carries concurrency risk and the door task changes a shared wire shape.

**Plan review:** 2026-09-25 — codex gpt-6-astra / xhigh — executability 16 / coherence 20 / coverage 20 / assumptions 15 (round 1)

## Global Constraints

- Both doors call `app/services/worklog.py` and hold no logic of their own (invariant 17).
- Greenfield until the schema freeze: no migration, no compatibility shim.
- Backend tests run from `backend/` as `.venv/bin/python -m pytest -q …`; conftest pins `DATABASE_URL` to `TEST_DATABASE_URL`. Bound every run with `timeout 900`.
- `docs/two-door-parity.md` is generated from `backend/tests/test_door_parity.py`; never edit its table by hand.
- When code a `CLAUDE.md` sentence describes changes, correct the sentence in place.

## Contracts

- C1 `app.services.worklog.WorklogSeqConflict(Exception)` with attributes `kind: str`, `expected: int`, `current: int`; message `expected the newest {kind} entry to be seq {expected}, but it is {current}`. Exported in `__all__`.
- C2 `worklog.append(..., expected_last_seq: int | None = None)`: `None` keeps today's behaviour; set, it requires one kind across `entries` (else `ValueError` containing `one kind`) and raises C1 on a mismatch with nothing kept.
- C3 `AppendResult.last_seq: int` — the seq of the last entry the append wrote.
- C4 `WorklogAppendRequest.expected_last_seq: int | None` (`ge=0`), refused with a mixed-kind `entries`; `WorklogAppendResponse.last_seq: int`.
- C5 REST: `POST /api/v1/worklog/entries` answers 409 with `detail` = C1's message; 201 bodies carry `last_seq`.
- C6 MCP: `worklog_append(..., expected_last_seq: int | None = None)` answers `{"status": "seq_conflict", "project", "workstream", "kind", "expected_last_seq", "current_last_seq"}` on C1; its success payload carries `last_seq`.

## Assumptions (evidence)

- The append already takes the workstream row lock inside `session.begin_nested()` before inserting: `backend/app/services/worklog.py:189-205` (read 2026-09-25).
- `ix_worklog_entries_kind_latest ON worklog_entries (workstream_id, kind, seq DESC)` exists: `backend/migrations/versions/0001_baseline.py:829-832` (read 2026-09-25).
- A second append to a workstream another open transaction is creating blocks on the unique index until that transaction ends, then locks the committed row (`_INSERT_IF_ABSENT … ON CONFLICT DO NOTHING` and the second `_SELECT_LOCKED` pass, `backend/app/services/worklog.py:108-164`): unverified — Task 1's `test_two_appends_expecting_the_same_seq_admit_exactly_one` verifies it.
- The SDKs bind only three verbs (`sdks/generate.py:123-140` `VERBS`: `capture` on `/api/v1/memories`, `search` on `/api/v1/memories/search/paginated`, and `declareContext`, a header) and hash only that surface (`sdks/generate.py:221` `_hash`), so a work-log schema change needs no `make generate` (read 2026-09-25).
- The MCP tool builds `WorklogAppendRequest` itself: `backend/app/api/mcp/server.py` `worklog_append` (read 2026-09-25).

## Task index

1. The service precondition
2. Both doors and the parity note

---

### Task 1: The service precondition

**Files:**
- Modify: `backend/app/services/worklog.py`
- Test: `backend/tests/test_worklog_service.py`

**Interfaces:**
- Consumes: none
- Produces: C1, C2, C3

**Items:** 26

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_worklog_service.py`, change the sqlalchemy import line

```python
from sqlalchemy import event, select, text
```

to

```python
from sqlalchemy import event, func, select, text
```

and append at the end of the file:

```python
async def _ledger(session, workstream_id):
    return (await session.execute(
        select(WorklogEntry.id, WorklogEntry.body, WorklogEntry.seq)
        .where(WorklogEntry.workstream_id == workstream_id, WorklogEntry.kind == "ledger")
        .order_by(WorklogEntry.seq)
    )).all()


async def test_append_reports_the_last_seq_it_wrote(session):
    result = await _append(session, entries=[
        {"kind": "ledger", "body": "a\n"}, {"kind": "ledger", "body": "b\n"},
    ])
    seqs = (await session.execute(
        select(WorklogEntry.seq).where(WorklogEntry.workstream_id == result.workstream.id)
    )).scalars().all()
    assert result.last_seq == max(seqs)


async def test_expected_last_seq_zero_opens_a_new_workstream(session):
    result = await _append(session, expected_last_seq=0)
    assert result.workstream.key == "plan-a"
    rows = await _ledger(session, result.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (result.entry_ids[0], "Task 1: complete\n", result.last_seq),
    ]


async def test_a_matching_expected_last_seq_appends(session):
    first = await _append(session)
    second = await _append(
        session, entries=[{"kind": "ledger", "body": "Task 2: complete\n"}],
        expected_last_seq=first.last_seq,
    )
    rows = await _ledger(session, first.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (first.entry_ids[0], "Task 1: complete\n", first.last_seq),
        (second.entry_ids[0], "Task 2: complete\n", second.last_seq),
    ]


async def test_a_stale_expected_last_seq_writes_nothing(session):
    first = await _append(session)
    with pytest.raises(worklog.WorklogSeqConflict) as caught:
        await _append(session, entries=[{"kind": "ledger", "body": "again\n"}], expected_last_seq=0)
    assert (caught.value.kind, caught.value.expected, caught.value.current) == (
        "ledger", 0, first.last_seq,
    )
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == first.workstream.id)
    )).scalar_one()
    assert count == 1


async def test_a_refused_precondition_creates_no_workstream(session):
    with pytest.raises(worklog.WorklogSeqConflict):
        await _append(session, expected_last_seq=5)
    assert (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one() == 0


async def test_a_refused_precondition_leaves_a_closed_workstream_closed(session):
    first = await _append(session)
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    with pytest.raises(worklog.WorklogSeqConflict):
        await _append(session, expected_last_seq=first.last_seq + 1000)
    state = (await session.execute(
        text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"),
        {"id": str(first.workstream.id)},
    )).scalar_one()
    assert state == "closed"


async def test_the_precondition_counts_only_its_own_kind(session):
    ledger = await _append(session)
    await _append(session, entries=[{"kind": "checkpoint", "body": "## State\nx"}])
    result = await _append(
        session, entries=[{"kind": "ledger", "body": "Task 2\n"}],
        expected_last_seq=ledger.last_seq,
    )
    rows = await _ledger(session, ledger.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (ledger.entry_ids[0], "Task 1: complete\n", ledger.last_seq),
        (result.entry_ids[0], "Task 2\n", result.last_seq),
    ]


async def test_the_precondition_refuses_a_mixed_kind_append(session):
    with pytest.raises(ValueError, match="one kind"):
        await _append(
            session,
            entries=[{"kind": "ledger", "body": "a\n"}, {"kind": "note", "body": "n"}],
            expected_last_seq=0,
        )


async def test_two_appends_expecting_the_same_seq_admit_exactly_one(committed):
    async with committed() as first, committed() as second:
        await worklog.append(
            first, project=RACE_PROJECT, key="cas", run_key="r",
            entries=[{"kind": "ledger", "body": "one\n"}], expected_last_seq=0,
        )
        racing = asyncio.create_task(worklog.append(
            second, project=RACE_PROJECT, key="cas", run_key="r",
            entries=[{"kind": "ledger", "body": "two\n"}], expected_last_seq=0,
        ))
        await asyncio.sleep(0.3)
        assert not racing.done(), "the second append must wait on the first's lock"
        await first.commit()
        with pytest.raises(worklog.WorklogSeqConflict):
            await racing
        await second.rollback()
    async with committed() as check:
        bodies = (await check.execute(
            text(
                "SELECT e.body FROM worklog_entries e JOIN workstreams w ON w.id = e.workstream_id "
                "WHERE w.project = :p AND w.key = 'cas'"
            ),
            {"p": RACE_PROJECT},
        )).scalars().all()
    assert bodies == ["one\n"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && timeout 900 .venv/bin/python -m pytest -q tests/test_worklog_service.py`
Expected: FAIL — the new tests error with `AttributeError: 'AppendResult' object has no attribute 'last_seq'`, `unexpected keyword argument 'expected_last_seq'` or `has no attribute 'WorklogSeqConflict'`; the existing tests pass.

- [ ] **Step 3: Implement the precondition**

In `backend/app/services/worklog.py`:

1. In `__all__`, after `"WorklogRejected",` add `"WorklogSeqConflict",`.

2. After the `WorklogRejected` class add:

```python
class WorklogSeqConflict(Exception):
    """expected_last_seq did not name the newest entry of its kind; nothing was kept."""

    def __init__(self, kind: str, expected: int, current: int) -> None:
        super().__init__(
            f"expected the newest {kind} entry to be seq {expected}, but it is {current}"
        )
        self.kind = kind
        self.expected = expected
        self.current = current
```

3. Replace the `AppendResult` dataclass with:

```python
@dataclass(frozen=True)
class AppendResult:
    workstream: Workstream
    entry_ids: list[UUID]
    last_seq: int
```

4. In `append`'s signature, after `api_key_id: UUID | None = None,` add `expected_last_seq: int | None = None,`, and change its docstring line to
`"""Append 1-100 entries to a workstream, creating or reopening it; optionally a compare-and-set."""`

5. Directly after the existing batch-size check (the `raise ValueError(f"an append carries 1 to …")` block) add:

```python
    kinds = {entry["kind"] for entry in entries}
    if expected_last_seq is not None and len(kinds) != 1:
        raise ValueError("expected_last_seq needs every entry of the append to share one kind")
```

6. Replace the body of `async with session.begin_nested():` — from `workstream_id, transition = await _lock_or_create(` through the closing `)` of the `session.execute(insert(WorklogEntry)…)` call — with:

```python
            workstream_id, transition = await _lock_or_create(
                session, project=project, key=key, title=title, client=client,
                properties=properties,
            )
            # Checked under the row lock and inside the savepoint: a mismatch
            # unwinds the creation or reopen above along with everything else.
            if expected_last_seq is not None:
                (kind,) = kinds
                current = (await session.execute(
                    select(func.coalesce(func.max(WorklogEntry.seq), 0)).where(
                        WorklogEntry.workstream_id == workstream_id,
                        WorklogEntry.kind == kind,
                    )
                )).scalar_one()
                if current != expected_last_seq:
                    raise WorklogSeqConflict(kind, expected_last_seq, current)
            # One multi-row statement, not executemany: the identity column
            # hands out `seq` in VALUES order, which keeps a ledger in order.
            seqs = (await session.execute(
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
                ]).returning(WorklogEntry.seq)
            )).scalars().all()
```

7. Replace the final `return AppendResult(workstream=workstream, entry_ids=entry_ids)` with:

```python
    return AppendResult(workstream=workstream, entry_ids=entry_ids, last_seq=max(seqs))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && timeout 900 .venv/bin/python -m pytest -q tests/test_worklog_service.py`
Expected: PASS, every test.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/worklog.py backend/tests/test_worklog_service.py
git commit -m "feat(worklog): add an append seq precondition"
```

### Task 2: Both doors and the parity note

**Files:**
- Modify: `backend/app/schemas/worklog.py`
- Modify: `backend/app/api/routes/worklog.py`
- Modify: `backend/app/api/mcp/server.py` (`worklog_append` and its `@mcp.tool` description)
- Modify: `backend/tests/test_door_parity.py` (the `worklog.append` `Surface`)
- Modify: `docs/two-door-parity.md` (regenerated)
- Modify: `CLAUDE.md` (the Work log section)
- Test: `backend/tests/test_worklog_rest.py`, `backend/tests/test_worklog_mcp.py`

**Interfaces:**
- Consumes: C1, C2, C3 (Task 1)
- Produces: C4, C5, C6

**Items:** 26

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing door tests**

Append to `backend/tests/test_worklog_rest.py`:

```python
async def test_append_answers_its_last_seq(client, auth_headers):
    response = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    assert response.status_code == 201, response.text
    body = response.json()
    resumed = await client.get(
        f"{V1}/resume", params={"project": "proj", "workstream": "plan-a"}, headers=auth_headers
    )
    # The default body's last entry is its ledger entry.
    [last] = resumed.json()["ledger"]
    assert last["id"] == body["entry_ids"][-1]
    assert body["last_seq"] == last["seq"]


async def test_a_stale_expected_last_seq_answers_409(client, auth_headers):
    headers = {**auth_headers, **RUN}
    ledger = [{"kind": "ledger", "body": "Task 1: complete\n"}]
    first = await client.post(
        f"{V1}/entries", json=_append_body(entries=ledger, expected_last_seq=0), headers=headers
    )
    assert first.status_code == 201, first.text
    stale = await client.post(
        f"{V1}/entries", json=_append_body(entries=ledger, expected_last_seq=0), headers=headers
    )
    assert stale.status_code == 409
    assert f"but it is {first.json()['last_seq']}" in stale.json()["detail"]
    fresh = await client.post(
        f"{V1}/entries",
        json=_append_body(entries=ledger, expected_last_seq=first.json()["last_seq"]),
        headers=headers,
    )
    assert fresh.status_code == 201, fresh.text


async def test_the_schema_refuses_a_negative_expected_last_seq(client, auth_headers):
    response = await client.post(
        f"{V1}/entries",
        json=_append_body(entries=[{"kind": "ledger", "body": "x\n"}], expected_last_seq=-1),
        headers={**auth_headers, **RUN},
    )
    assert response.status_code == 422
    assert "expected_last_seq" in response.text
    assert "one kind" not in response.text


async def test_the_schema_refuses_a_mixed_kind_precondition(client, auth_headers):
    # The default body mixes a checkpoint and a ledger entry.
    response = await client.post(
        f"{V1}/entries", json=_append_body(expected_last_seq=0), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422
    assert "one kind" in response.text
```

Append to `backend/tests/test_worklog_mcp.py`:

```python
async def test_append_answers_seq_conflict_where_the_route_answers_409(mcp_on_the_test_session):
    from app.api.mcp import server

    ledger = [{"kind": "ledger", "body": "Task 1\n"}]
    first = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a", entries=ledger, run_key="run-1", expected_last_seq=0,
    ))
    assert isinstance(first["last_seq"], int)
    stale = json.loads(await server.worklog_append(
        project="proj", workstream="plan-a", entries=ledger, run_key="run-1", expected_last_seq=0,
    ))
    assert stale == {
        "status": "seq_conflict",
        "project": "proj",
        "workstream": "plan-a",
        "kind": "ledger",
        "expected_last_seq": 0,
        "current_last_seq": first["last_seq"],
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && timeout 900 .venv/bin/python -m pytest -q tests/test_worklog_rest.py tests/test_worklog_mcp.py`
Expected: FAIL — `KeyError: 'last_seq'`, a 422 where 201 or 409 is expected, and `unexpected keyword argument 'expected_last_seq'` from the tool; the existing tests pass.

- [ ] **Step 3: Implement the schema, the route and the tool**

In `backend/app/schemas/worklog.py`, replace the `WorklogAppendRequest` class with:

```python
class WorklogAppendRequest(_Storable):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    expected_last_seq: int | None = Field(default=None, ge=0)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)

    @model_validator(mode="after")
    def _one_kind_under_a_precondition(self):
        if self.expected_last_seq is not None and len({entry.kind for entry in self.entries}) != 1:
            raise ValueError("expected_last_seq needs every entry of the append to share one kind")
        return self
```

and replace the `WorklogAppendResponse` class with:

```python
class WorklogAppendResponse(BaseModel):
    workstream: WorkstreamOut
    entry_ids: list[UUID]
    last_seq: int
```

In `backend/app/api/routes/worklog.py`, in `append_entries`, replace the `try:` block that calls `worklog.append` and the `payload = {…}` that follows with:

```python
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
            expected_last_seq=body.expected_last_seq,
        )
    except worklog.WorklogSeqConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except worklog.WorklogRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = {
        "workstream": worklog.serialize_workstream(result.workstream),
        "entry_ids": [str(entry_id) for entry_id in result.entry_ids],
        "last_seq": result.last_seq,
    }
```

In `backend/app/api/mcp/server.py`:

1. In the `@mcp.tool` description above `async def worklog_append`, replace the last line `"X-Darkmem-Origin header."` with:

```python
        "X-Darkmem-Origin header. expected_last_seq (optional, entries of one "
        "kind): append only if the workstream's newest entry of that kind has "
        "that seq, 0 when it has none; otherwise nothing is written and the "
        "answer is a seq_conflict naming the current seq. The answer's last_seq "
        "is the expectation for your next append."
```

2. In `worklog_append`'s parameters, after `run_key: str | None = None,` add `expected_last_seq: int | None = None,`.

3. In the `WorklogAppendRequest(` call inside it, after `run_key=run_key,` add `expected_last_seq=expected_last_seq,`.

4. Replace the `async with async_session_factory() as session:` block of `worklog_append` with:

```python
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
                expected_last_seq=body.expected_last_seq,
            )
            payload = {
                "workstream": worklog.serialize_workstream(result.workstream),
                "entry_ids": [str(entry_id) for entry_id in result.entry_ids],
                "last_seq": result.last_seq,
            }
            await session.commit()
        except worklog.WorklogSeqConflict as exc:
            # A structured refusal, as document_put's hash_conflict: the caller
            # re-reads the workstream and retries. Its REST twin is a 409.
            await session.rollback()
            return json.dumps({
                "status": "seq_conflict",
                "project": body.project,
                "workstream": body.workstream,
                "kind": exc.kind,
                "expected_last_seq": exc.expected,
                "current_last_seq": exc.current,
            })
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Run the door tests to verify they pass**

Run: `cd backend && timeout 900 .venv/bin/python -m pytest -q tests/test_worklog_rest.py tests/test_worklog_mcp.py tests/test_worklog_service.py`
Expected: PASS, every test.

- [ ] **Step 5: State the asymmetry in the parity table**

In `backend/tests/test_door_parity.py`, replace the `worklog.append` entry

```python
    Surface(
        name="worklog.append",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/worklog/entries"),),
        mcp=("worklog_append",),
    ),
```

with

```python
    Surface(
        name="worklog.append",
        status=TWO_DOOR,
        rest=(("POST", f"{V1}/worklog/entries"),),
        mcp=("worklog_append",),
        note=(
            "Stated wire asymmetry: the optional expected_last_seq compare-and-set "
            "answers 409 on the route and a seq_conflict envelope from the tool -- "
            "one refusal produced by WorklogSeqConflict on both doors, raised under "
            "the workstream row lock so nothing of the append is kept -- and both "
            "doors echo last_seq, the seq a caller preconditions its next append on."
        ),
    ),
```

Then regenerate the committed table:

Run from the repository root; the regeneration runs in a subshell so the
`git diff` that follows is still at the root:

```bash
(cd backend && timeout 120 .venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown
doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8")
EOF
)
git diff --stat -- docs/two-door-parity.md
```

Expected: `docs/two-door-parity.md | 2 +-` (only the `worklog.append` row changes).

- [ ] **Step 6: Correct CLAUDE.md**

In `CLAUDE.md`, section `## Work log (`app/services/worklog.py`)`, replace

```
(`SELECT … FOR UPDATE`, or the creating insert) first, serialising it
against purge and retention deletes.
```

with

```
(`SELECT … FOR UPDATE`, or the creating insert) first, serialising it
against purge and retention deletes. An optional `expected_last_seq` makes
the append a compare-and-set on the newest entry of its one kind (0 when
there is none), checked under that lock: a mismatch raises
`WorklogSeqConflict` inside the savepoint, so nothing is written, created or
reopened, and answers 409 / `seq_conflict`. Every append answers `last_seq`.
```

- [ ] **Step 7: Run the door guards and the work-log suites**

Run:

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py tests/test_worklog_service.py tests/test_worklog_rest.py \
    tests/test_worklog_mcp.py tests/test_worklog_schema.py tests/test_worklog_wall.py
```

Expected: PASS, every test.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/worklog.py backend/app/api/routes/worklog.py backend/app/api/mcp/server.py \
  backend/tests/test_worklog_rest.py backend/tests/test_worklog_mcp.py backend/tests/test_door_parity.py \
  docs/two-door-parity.md CLAUDE.md
git commit -m "feat(worklog): expose the seq precondition on both doors"
```
