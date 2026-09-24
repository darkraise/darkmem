# Work-log increment 1 — plan amendments A1–A14

Applied during execution of `docs/superpowers/plans/2026-09-23-work-log-increment-1-store-and-verbs.md`; the plan file keeps its reviewed text.

## A1 — Task 3
Reason: begin_nested() flushes pending state before SAVEPOINT, so the savepoint around the flush contains nothing.
Cost if wrong: none; behaviour on success is identical.
### Old
````text
    transition = None
    if state is not None and state != workstream.state:
        workstream.state = state
        workstream.closed_at = func.now() if state == "closed" else None
        transition = state
    if retain is not None:
        workstream.retain = retain
    if title is not None:
        workstream.title = title
    if properties:
        workstream.properties = {**(workstream.properties or {}), **properties}
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
````
### New
````text
    transition = state if state is not None and state != workstream.state else None
    try:
        # The changes are made inside the savepoint on purpose: begin_nested()
        # flushes pending state before it emits SAVEPOINT, so an attribute set
        # above it would hit the CHECK outside the savepoint and abort the
        # caller's whole transaction.
        async with session.begin_nested():
            if transition is not None:
                workstream.state = state
                workstream.closed_at = func.now() if state == "closed" else None
            if retain is not None:
                workstream.retain = retain
            if title is not None:
                workstream.title = title
            if properties:
                workstream.properties = {**(workstream.properties or {}), **properties}
            await session.flush()
    except IntegrityError as error:
        raise WorklogRejected(str(error.orig)) from error
````

## A2 — Task 3
Reason: the tool worklog_entries shares the table's name, and prompt.py (in the pipeline and chat closures) must name every tool.
Cost if wrong: a table named outside a SQL clause keyword is not caught by this scan.
### Old
````text
WORKLOG_TABLES = ("workstreams", "worklog_entries")


def _names_a_worklog_table(source: str) -> bool:
    return any(re.search(rf"\b{table}\b", source) for table in WORKLOG_TABLES)
````
### New
````text
WORKLOG_TABLES = ("workstreams", "worklog_entries")

# SQL that touches a work-log table, not prose that names one: the MCP tool
# `worklog_entries` shares the table's name, and `app.services.prompt` -- in
# the pipeline's and chat's closure -- must name every tool.
_WORKLOG_TABLE_SQL = re.compile(
    rf"\b(?:from|join|into|update|table|truncate)\s+(?:{'|'.join(WORKLOG_TABLES)})\b",
    re.IGNORECASE,
)


def _names_a_worklog_table(source: str) -> bool:
    return _WORKLOG_TABLE_SQL.search(source) is not None


def test_the_table_scan_ignores_the_tool_that_shares_a_table_name():
    assert not _names_a_worklog_table(
        "- **worklog_workstreams** / **worklog_entries** — list a project's workstreams"
    )
    assert _names_a_worklog_table("DELETE FROM workstreams WHERE id = :id")
````

## A3 — Task 4
Reason: MCP passes kind/state unvalidated, so a typo answers an empty page instead of an error; REST refuses the same input.
Cost if wrong: an invalid filter raises instead of returning nothing.
### Old
````text
    conditions = [Workstream.project == project]
    if state is not None:
        conditions.append(Workstream.state == state)
    if before is not None:
        stamp, ident = _parse_cursor(before)
        conditions.append(or_(
            Workstream.created_at < stamp,
            and_(Workstream.created_at == stamp, Workstream.id < ident),
        ))
    rows = (await session.execute(
        select(Workstream)
        .where(*conditions)
        .order_by(Workstream.created_at.desc(), Workstream.id.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_workstream(w) for w in rows],
        "next_before": _cursor(rows[-1]) if len(rows) == limit else None,
    }


async def list_entries(
    session: AsyncSession,
    *,
    workstream_id: UUID,
    kind: str | None = None,
    since: datetime | None = None,
    after: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Entries oldest first, paged forward on `seq`; `since` keeps created_at >= since."""
    conditions = [WorklogEntry.workstream_id == workstream_id]
````
### New
````text
    if state is not None and state not in ("open", "closed"):
        raise ValueError(f"state must be 'open' or 'closed', not {state!r}")
    conditions = [Workstream.project == project]
    if state is not None:
        conditions.append(Workstream.state == state)
    if before is not None:
        stamp, ident = _parse_cursor(before)
        conditions.append(or_(
            Workstream.created_at < stamp,
            and_(Workstream.created_at == stamp, Workstream.id < ident),
        ))
    rows = (await session.execute(
        select(Workstream)
        .where(*conditions)
        .order_by(Workstream.created_at.desc(), Workstream.id.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [serialize_workstream(w) for w in rows],
        "next_before": _cursor(rows[-1]) if len(rows) == limit else None,
    }


async def list_entries(
    session: AsyncSession,
    *,
    workstream_id: UUID,
    kind: str | None = None,
    since: datetime | None = None,
    after: int | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Entries oldest first, paged forward on `seq`; `since` keeps created_at >= since."""
    if kind is not None and kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, not {kind!r}")
    conditions = [WorklogEntry.workstream_id == workstream_id]
````

## A4 — Task 9
Reason: a second CLAUDE.md sentence claims every other document route is login-only; Task 7 keys three.
Cost if wrong: CLAUDE.md contradicts the route table at a sentence readers treat as the contract.
### Old
````text
Replace

```markdown
authenticated key sees the full 40-tool catalogue, including writers it
```
````
### New
````text
Replace

```markdown
any capture key erase a project's whole corpus; on REST it sits behind
ordinary auth with every other document route, which has no per-verb grant
for a mode to inherit.
```

with

```markdown
any capture key erase a project's whole corpus; on REST it sits behind
ordinary login auth, which has no per-verb grant for a mode to inherit, as do
all but the three document routes a dr-superpowers mirror syncs through.
```

Replace

```markdown
authenticated key sees the full 40-tool catalogue, including writers it
```
````

## A5 — Task 3
Reason: worklog.py takes row locks and the tree-wide row-lock inventory is pinned by equality; no task updates or runs it.
Cost if wrong: one line added to a pinned set.
### Old
````text
**Files:**
- Create: `backend/app/services/worklog.py`
- Test: `backend/tests/test_worklog_service.py`
- Test: `backend/tests/test_worklog_wall.py`
````
### New
````text
**Files:**
- Create: `backend/app/services/worklog.py`
- Modify: `backend/tests/test_read_only_role.py` (`ROW_LOCK_WRITERS`: insert the line `    "services/worklog.py",` immediately after `    "services/verification_recompute.py",`, because `worklog.py` takes row locks and that set is pinned by equality; add `tests/test_read_only_role.py::test_every_row_lock_in_the_tree_is_on_a_writer_path` to Step 4's first pytest command and `backend/tests/test_read_only_role.py` to Step 5's `git add`)
- Test: `backend/tests/test_worklog_service.py`
- Test: `backend/tests/test_worklog_wall.py`
````

## A6 — Task 3
Reason: update_workstream's rejection path is untested; the savepoint defect it hides is invisible to every other test.
Cost if wrong: one redundant test.
### Old
````text
async def test_merged_properties_over_the_database_bound_are_rejected(session):
    first = await _append(session, properties={"a": secrets.token_hex(4500)})
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream(session, project="proj", key="plan-a")
    assert set(kept.properties) == {"a"}
    assert kept.id == first.workstream.id
````
### New
````text
async def test_merged_properties_over_the_database_bound_are_rejected(session):
    first = await _append(session, properties={"a": secrets.token_hex(4500)})
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream(session, project="proj", key="plan-a")
    assert set(kept.properties) == {"a"}
    assert kept.id == first.workstream.id


async def test_an_update_over_the_database_bound_is_rejected_and_the_session_survives(session):
    ws = (await _append(session, properties={"a": secrets.token_hex(4500)})).workstream
    with pytest.raises(worklog.WorklogRejected):
        await worklog.update_workstream(session, ws.id, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream_by_id(session, ws.id, for_update=True)
    assert set(kept.properties) == {"a"}
````

## A7 — Task 5
Reason: main.py imports every router on line 21; a mid-module import with noqa is a style defect a reviewer flags.
Cost if wrong: none functional.
### Old
````text
In `backend/app/main.py`, immediately after the line `app.include_router(checkpoint_routes.router)` add:

```python
from app.api.routes import worklog as worklog_routes  # noqa: E402

app.include_router(worklog_routes.router)
```
````
### New
````text
In `backend/app/main.py`, on the one-line `from app.api.routes import ...` statement (the line containing `checkpoints as checkpoint_routes`), append `, worklog as worklog_routes` after its last name, `vectors`. Then immediately after the line `app.include_router(checkpoint_routes.router)` add:

```python
app.include_router(worklog_routes.router)
```
````

## A8 — Task 9
Reason: worklog_purge is not a repository-scale tool; the sentence contradicts the replacement that follows it.
Cost if wrong: one adjective.
### Old
````text
`read` covers 28; `admin` covers the 3 repository-scale control tools
````
### New
````text
`read` covers 28; `admin` covers the 3 control tools
````

## A9 — Header
Reason: A fixed trailer names the wrong model on some tasks, because implementers are impl-opus, impl-sonnet and Codex.
Cost if wrong: Commit trailers name a different model than intended; nothing reads them.
### Old
````text
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push; never `--no-verify`.
````
### New
````text
- Commits: `<type>(<scope>): <subject>`, subject ≤ 50 characters, imperative. The trailer names the model that did the work, keyed on the task's **Implementer:** line: `dr-superpowers:impl-opus-*` ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the line each task's `git commit` command already spells); `dr-superpowers:impl-sonnet-*` ends with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` instead; a task run by the Codex executor carries no `Co-Authored-By` line; the controller's own commits carry `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. A reviewer checks the trailer against this mapping, not against the task's command text. Never push; never `--no-verify`.
````

## A10 — Task 5
Reason: Postgres text and jsonb refuse U+0000, and the service maps only IntegrityError, so a NUL in any stored string or properties value answers 500 on both doors.
Cost if wrong: a caller that goes around the shared schemas can still reach the database with a NUL and get a 500.
### Old
````text
async def test_no_credential_is_401(client):
    response = await client.get(f"{V1}/workstreams", params={"project": "proj"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_rest.py`
Expected: FAIL — the first request answers 404 (no route).

- [ ] **Step 3: Write the schemas**

Create `backend/app/schemas/worklog.py`:

```python
"""Wire shapes for the work-log lane. Both doors validate through these."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]


def _bounded(value: dict | None) -> dict | None:
    if value is not None and properties_size(value) > MAX_PROPERTIES_BYTES:
        raise ValueError(f"properties encode to more than {MAX_PROPERTIES_BYTES} bytes")
    return value


class WorklogEntryIn(BaseModel):
    kind: Kind
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    properties: dict = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorklogAppendRequest(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorkstreamUpdateRequest(BaseModel):
````
### New
````text
async def test_no_credential_is_401(client):
    response = await client.get(f"{V1}/workstreams", params={"project": "proj"})
    assert response.status_code == 401


@pytest.mark.parametrize("overrides", [
    {"entries": [{"kind": "ledger", "body": "Task 1\x00: complete\n"}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"p": "\x00"}}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"k\x00": 1}}]},
    {"entries": [{"kind": "note", "body": "n", "properties": {"p": [{"q": "\x00"}]}}]},
    {"properties": {"p": "\x00"}},
    {"project": "pr\x00j"},
    {"workstream": "plan\x00a"},
    {"title": "t\x00"},
    {"client": "c\x00"},
    {"run_key": "run\x00"},
])
async def test_a_nul_in_anything_stored_is_refused_not_stripped(client, auth_headers, overrides):
    response = await client.post(
        f"{V1}/entries", json=_append_body(**overrides), headers={**auth_headers, **RUN}
    )
    assert response.status_code == 422, response.text
    listing = await client.get(f"{V1}/workstreams", params={"project": "proj"}, headers=auth_headers)
    assert listing.json()["items"] == []


@pytest.mark.parametrize("update", [{"title": "t\x00"}, {"properties": {"p": ["\x00"]}}])
async def test_a_nul_in_an_update_is_refused(client, auth_headers, update):
    created = await client.post(f"{V1}/entries", json=_append_body(), headers={**auth_headers, **RUN})
    workstream_id = created.json()["workstream"]["id"]
    response = await client.patch(f"{V1}/workstreams/{workstream_id}", json=update, headers=auth_headers)
    assert response.status_code == 422, response.text


def test_the_schema_both_doors_share_refuses_a_nul():
    from pydantic import ValidationError

    from app.schemas.worklog import WorklogAppendRequest, WorkstreamUpdateRequest

    with pytest.raises(ValidationError):
        WorklogAppendRequest(project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "\x00"}])
    with pytest.raises(ValidationError):
        WorkstreamUpdateRequest(properties={"p": "\x00"})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_worklog_rest.py`
Expected: FAIL — the first request answers 404 (no route).

- [ ] **Step 3: Write the schemas**

Create `backend/app/schemas/worklog.py`:

```python
"""Wire shapes for the work-log lane. Both doors validate through these."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.worklog import (
    MAX_BODY_CHARS,
    MAX_ENTRIES_PER_APPEND,
    MAX_PROPERTIES_BYTES,
    properties_size,
)

Kind = Literal["checkpoint", "ledger", "note"]
State = Literal["open", "closed"]


def _bounded(value: dict | None) -> dict | None:
    if value is not None and properties_size(value) > MAX_PROPERTIES_BYTES:
        raise ValueError(f"properties encode to more than {MAX_PROPERTIES_BYTES} bytes")
    return value


def _holds_nul(value: object) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if "\x00" in item:
                return True
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


class _Storable(BaseModel):
    # Postgres text and jsonb cannot hold U+0000 and the service maps only
    # IntegrityError, so a NUL past this point answers 500 on either door.
    # Refused, never stripped: a ledger body is stored exactly as written.
    @model_validator(mode="after")
    def _no_nul(self):
        if _holds_nul(self.model_dump()):
            raise ValueError("a string or properties value contains U+0000, which cannot be stored")
        return self


class WorklogEntryIn(_Storable):
    kind: Kind
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    properties: dict = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorklogAppendRequest(_Storable):
    project: str = Field(min_length=1, max_length=200)
    workstream: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=500)
    client: str | None = Field(default=None, max_length=200)
    properties: dict = Field(default_factory=dict)
    run_key: str | None = Field(default=None, max_length=500)
    entries: list[WorklogEntryIn] = Field(min_length=1, max_length=MAX_ENTRIES_PER_APPEND)

    @field_validator("properties")
    @classmethod
    def _properties_fit(cls, value: dict) -> dict:
        return _bounded(value)


class WorkstreamUpdateRequest(_Storable):
````

## A11 — Task 7
Reason: test_key_reach_is_pinned_to_the_call_sites_that_were_argued_for counts require_scope calls per route file, and Step 3 adds two to documents.py.
Cost if wrong: Step 6's run of test_api_keys.py fails on a pin the task does not name.
### Old
````text
- [ ] **Step 6: Run the tests to verify they pass**
````
### New
````text
In the same file, `TestPostureIsUnchanged.test_key_reach_is_pinned_to_the_call_sites_that_were_argued_for` counts `require_scope(...)` calls per route file in path order, and Step 3's two module-level bindings are two calls. Replace

```python
        assert sites == [
            ("api/routes/memories.py", 2),
```

with

```python
        assert sites == [
            ("api/routes/documents.py", 2),
            ("api/routes/memories.py", 2),
```

- [ ] **Step 6: Run the tests to verify they pass**
````

## A12 — Task 6
Reason: A purge committing between the tools' unlocked lookup and the service's row lock raises WorkstreamNotFound instead of the documented null; REST already maps the same exception to 404.
Cost if wrong: none functional; nothing is written before the service's lock, so the rollback discards nothing.
### Old
````text
            payload = worklog.serialize_workstream(updated)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps(payload)


@mcp.tool(
    description=(
        "Erase a work-log workstream and every entry in it, irrecoverably. The "
        "erase is journaled before it runs and refused if the journal row does "
        "not land. Needs an admin-scoped key. null when it does not exist."
    )
)
async def worklog_purge(project: str, workstream: str) -> str:
    from app.services import worklog

    async with async_session_factory() as session:
        try:
            found = await worklog.get_workstream(session, project=project, key=workstream)
            if found is None:
                return json.dumps(None)
            removed = await worklog.purge_workstream(
                session, found.id, actor=current_key_name(), api_key_id=current_api_key_id()
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps({"purged": workstream, "entries": removed})
```
````
### New
````text
            payload = worklog.serialize_workstream(updated)
            await session.commit()
        except worklog.WorkstreamNotFound:
            # The lookup above is unlocked; a purge committing before the
            # service takes its row lock is the same unknown workstream.
            await session.rollback()
            return json.dumps(None)
        except Exception:
            await session.rollback()
            raise
    return json.dumps(payload)


@mcp.tool(
    description=(
        "Erase a work-log workstream and every entry in it, irrecoverably. The "
        "erase is journaled before it runs and refused if the journal row does "
        "not land. Needs an admin-scoped key. null when it does not exist."
    )
)
async def worklog_purge(project: str, workstream: str) -> str:
    from app.services import worklog

    async with async_session_factory() as session:
        try:
            found = await worklog.get_workstream(session, project=project, key=workstream)
            if found is None:
                return json.dumps(None)
            removed = await worklog.purge_workstream(
                session, found.id, actor=current_key_name(), api_key_id=current_api_key_id()
            )
            await session.commit()
        except worklog.WorkstreamNotFound:
            await session.rollback()
            return json.dumps(None)
        except Exception:
            await session.rollback()
            raise
    return json.dumps({"purged": workstream, "entries": removed})
```

Append to `backend/tests/test_worklog_mcp.py` (one workstream per parametrised run, refusal last, because the conftest `session` fixture's boundary ends at the first rollback):

```python
@pytest.mark.parametrize("tool,verb,arguments", [
    ("worklog_update", "update_workstream", {"state": "closed"}),
    ("worklog_purge", "purge_workstream", {}),
])
async def test_a_workstream_purged_after_the_lookup_answers_null(
    mcp_on_the_test_session, monkeypatch, tool, verb, arguments
):
    from app.api.mcp import server
    from app.services import worklog

    await server.worklog_append(
        project="proj", workstream="plan-a", entries=[{"kind": "note", "body": "n"}], run_key="r"
    )

    async def purged_meanwhile(session, workstream_id, **_):
        raise worklog.WorkstreamNotFound(str(workstream_id))

    monkeypatch.setattr(worklog, verb, purged_meanwhile)
    answer = await getattr(server, tool)(project="proj", workstream="plan-a", **arguments)
    assert json.loads(answer) is None
```
````

## A13 — Task 7
Reason: A keyed POST /documents journals document_filed with the key's name and a NULL api_key_id, which the Principal contract reads as a human session.
Cost if wrong: put_document gains the spec §3 api_key_id parameter one increment early, and increment 3 reuses it.
### Old
````text
- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_documents_keyed.py tests/test_documents_api.py tests/test_document_door.py tests/test_read_only_doors.py tests/test_api_keys.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_keyed.py backend/tests/test_api_keys.py
````
### New
````text
- [ ] **Step 5b: Stamp the key on a keyed filing**

This step also modifies `backend/app/services/document_door.py`, `backend/app/services/block_pipeline.py` and `backend/app/services/document_ingest.py`, beyond the Files list above. Spec §3 gives `put_document` an `api_key_id` beside `actor`. It lands here because this task is what makes the filing door keyed, and `Principal` reads a NULL `api_key_id` as a human session.

In `backend/tests/test_documents_keyed.py`, replace

```python
async def test_a_capture_key_files_and_a_read_key_reads_it_back(client, session, scripted_embedder):
    capture = await _key(session, "capture")
```

with

```python
async def test_a_capture_key_files_and_a_read_key_reads_it_back(client, session, scripted_embedder):
    capture_name = f"k-{uuid.uuid4().hex[:6]}"
    capture_row, capture_credential = await issue_key(session, name=capture_name, scopes=["capture"])
    capture = {"Authorization": f"Bearer {capture_credential}"}
```

and immediately after the line `    assert filed.json()["outcome"] == "created"` in that test insert

```python
    stamped = (await session.execute(
        text("SELECT actor, api_key_id FROM events WHERE event_type = 'document_filed' AND project = 'proj'")
    )).all()
    assert [tuple(row) for row in stamped] == [(capture_name, capture_row.id)]
```

Run `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 600 .venv/bin/python -m pytest -q tests/test_documents_keyed.py`. Expected: FAIL. The event's `api_key_id` is `None`.

Thread the key through, keyword-only, defaulting to `None`. `UUID` is already imported in all three modules:
- `backend/app/services/document_door.py`, `put_document`: immediately after its parameter line `    actor: str | None = None,` add `    api_key_id: UUID | None = None,`. In its `ingest_document(` call, immediately after `            actor=actor,` add `            api_key_id=api_key_id,`.
- `backend/app/services/block_pipeline.py`, `ingest_document`: immediately after its parameter line `    actor: str | None = None,` add `    api_key_id: UUID | None = None,`. In its `file_document(` call, immediately after `        actor=actor,` add `        api_key_id=api_key_id,`.
- `backend/app/services/document_ingest.py`, `file_document` and `_file_document_without_savepoint`: in each, immediately after the parameter line `    actor: str | None = None,` add `    api_key_id: UUID | None = None,`. In `file_document`'s call to `_file_document_without_savepoint`, immediately after `            actor=actor,` add `            api_key_id=api_key_id,`. In `_file_document_without_savepoint`'s `record_event(` call for `DOCUMENT_FILED_EVENT`, immediately after `        actor=actor,` add `        api_key_id=api_key_id,`.
- `backend/app/api/routes/documents.py`, `put_document_route`: immediately after `            actor=principal.actor,` add `            api_key_id=principal.api_key_id,`.

Leave everything else unchanged: the batch path (`DocumentSource`, `DocumentFileJob`, `file_documents_isolated`, `ingest_documents`), `scripts/reparse_documents.py`, `scripts/benchlib/span_harvest.py` and MCP `document_put`. MCP `document_put` is increment 3's, per spec §3.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 timeout 900 .venv/bin/python -m pytest -q tests/test_documents_keyed.py tests/test_documents_api.py tests/test_document_door.py tests/test_read_only_doors.py tests/test_api_keys.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_documents_keyed.py backend/tests/test_api_keys.py backend/app/services/document_door.py backend/app/services/block_pipeline.py backend/app/services/document_ingest.py
````

## A14 — Task 9
Reason: The strict-journal paragraph says seven callers, then "outside the six", and Step 4 never names that sentence.
Cost if wrong: none; the phrase occurs once in CLAUDE.md and the count is seven two lines above it.
### Old
````text
Also replace `The six do **not** all` with `The seven do **not** all`.
````
### New
````text
Also replace `The six do **not** all` with `The seven do **not** all`, and replace `outside the six and must not be added to it` with `outside the seven and must not be added to it`.
````
