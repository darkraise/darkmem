"""The `projects` namespace registry: lazy registration + backfill (T2.07).

Doc 04 §7: `knowledge_triples.triple_key` embeds `project` verbatim, so a
typo'd project string silently opens a second, uncorroborated fact-identity
scope. The registry's whole job is to make that typo *visible* — a second row
an operator can see and merge — never to correct or fuzzy-match it, and never
to canonicalise `name` (E2 amendment log, 2026-07-29: `Foo` and `foo` are
distinct scopes and must stay distinct rows).

Every test here asserts a concrete database fact, not a response field —
capture doors ack with a bare id and never echo the registry back over the
wire.
"""
from __future__ import annotations

import pytest
from sqlalchemy import event, func, select, text

from app.models.memory import Memory, MemoryBuffer
from app.models.project import Project
from app.services import project_registry

pytestmark = pytest.mark.asyncio


class _QueryCounter:
    """Counts SQL statements issued on one session's connection (T1.01 idiom)."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def touching(self, table: str) -> list[str]:
        return [s for s in self.statements if table in s]


async def _capture(client, auth_headers, *, project: str, content: str = "hello"):
    return await client.post(
        "/api/v1/memories",
        json={"content": content, "project": project},
        headers=auth_headers,
    )


async def _project_names(session) -> set[str]:
    rows = await session.execute(select(Project.name))
    return set(rows.scalars().all())


# ── Clause 1: no round trip, no failure mode ────────────────────────


async def test_register_is_a_single_insert_no_select_round_trip(session):
    from tests.conftest import test_engine

    counter = _QueryCounter()
    target = test_engine.sync_engine
    event.listen(target, "before_cursor_execute", counter)
    try:
        await project_registry.register(session, "no-round-trip-project")
    finally:
        event.remove(target, "before_cursor_execute", counter)

    statements = counter.touching("projects")
    assert len(statements) == 1, (
        "register() must issue exactly one statement; got "
        f"{len(statements)}:\n" + "\n".join(statements)
    )
    stmt = statements[0].lstrip().upper()
    assert stmt.startswith("INSERT"), statements[0]
    assert "SELECT" not in stmt, "register() must not SELECT before INSERT"
    assert "ON CONFLICT" in stmt


async def test_capture_registers_an_unseen_project(client, auth_headers, session):
    response = await _capture(client, auth_headers, project="freshly-typed-project")
    assert response.status_code == 202

    names = await _project_names(session)
    assert "freshly-typed-project" in names


async def test_capturing_twice_leaves_exactly_one_row_and_does_not_error(
    client, auth_headers, session
):
    first = await _capture(client, auth_headers, project="repeat-project", content="one")
    second = await _capture(client, auth_headers, project="repeat-project", content="two")
    assert first.status_code == 202
    assert second.status_code == 202

    count = (await session.execute(
        select(func.count()).select_from(Project).where(Project.name == "repeat-project")
    )).scalar()
    assert count == 1


async def test_registry_write_failure_does_not_fail_the_capture(
    client, auth_headers, session, monkeypatch
):
    """Breaks the SQL execution *inside* `register`'s own try/except, rather
    than replacing `register` wholesale — the property under test is that
    `register`'s internal savepoint-and-swallow protects capture, not that a
    monkeypatched no-op does."""
    original_execute = session.execute

    async def _flaky_execute(clause, *args, **kwargs):
        if "INSERT INTO projects" in str(getattr(clause, "text", clause)):
            raise RuntimeError("projects registry write exploded")
        return await original_execute(clause, *args, **kwargs)

    monkeypatch.setattr(session, "execute", _flaky_execute)

    response = await _capture(client, auth_headers, project="doomed-registry-project")
    assert response.status_code == 202

    monkeypatch.setattr(session, "execute", original_execute)
    buffered = (await session.execute(
        select(func.count()).select_from(MemoryBuffer)
    )).scalar()
    assert buffered == 1
    names = await _project_names(session)
    assert "doomed-registry-project" not in names


# ── Clause 2: a typo is visible, never merged ───────────────────────


async def test_typo_creates_a_second_visible_row_not_a_merge(
    client, auth_headers, session
):
    real = await _capture(client, auth_headers, project="darkmem", content="real project")
    typo = await _capture(client, auth_headers, project="darkmen", content="typo'd project")
    assert real.status_code == 202
    assert typo.status_code == 202

    names = await _project_names(session)
    assert "darkmem" in names
    assert "darkmen" in names

    listing = (await session.execute(select(Project.name).order_by(Project.name))).scalars().all()
    assert {"darkmem", "darkmen"} <= set(listing)

    darkmem_memories = (await session.execute(
        select(func.count()).select_from(MemoryBuffer).where(MemoryBuffer.project == "darkmem")
    )).scalar()
    darkmen_memories = (await session.execute(
        select(func.count()).select_from(MemoryBuffer).where(MemoryBuffer.project == "darkmen")
    )).scalar()
    assert darkmem_memories == 1
    assert darkmen_memories == 1


async def test_case_differing_by_one_character_creates_two_rows(
    client, auth_headers, session
):
    lower = await _capture(client, auth_headers, project="foo", content="lowercase")
    upper = await _capture(client, auth_headers, project="Foo", content="capitalized")
    assert lower.status_code == 202
    assert upper.status_code == 202

    names = await _project_names(session)
    assert "foo" in names
    assert "Foo" in names
    assert len({"foo", "Foo"} & names) == 2


# ── The update door: a memory row can also change project ──────────


async def test_update_memory_registers_a_new_project(client, auth_headers, session):
    """I1 (adversarial review, 2026-07-29): `PUT /memories/{id}` writes
    `memories.project` without going through `_capture_batch`, so it is a
    second path onto a memory row's `project` column that the brief's
    binding sentence — "the registry must see every project string that
    reaches a memory row, by whichever path" — also covers. MCP's
    `memory_update` does not expose the field, so REST is the only door this
    needs proving against."""
    memory = Memory(content="moves between projects", project="pre-update-project")
    session.add(memory)
    await session.flush()
    memory_id = str(memory.id)

    names_before = await _project_names(session)
    assert "moved-via-update-project" not in names_before

    response = await client.put(
        f"/api/v1/memories/{memory_id}",
        json={"project": "moved-via-update-project"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["project"] == "moved-via-update-project"

    names_after = await _project_names(session)
    assert "moved-via-update-project" in names_after


async def test_update_memory_without_a_project_field_registers_nothing(
    client, auth_headers, session, monkeypatch
):
    """A negative control for the fix above: an update that never touches
    `project` must not call the registry at all."""
    memory = Memory(content="untouched project", project="already-registered-project")
    session.add(Project(name="already-registered-project"))
    session.add(memory)
    await session.flush()
    memory_id = str(memory.id)

    calls: list[str] = []
    original_register = project_registry.register

    async def _spy(session_, project):
        calls.append(project)
        return await original_register(session_, project)

    monkeypatch.setattr(project_registry, "register", _spy)

    response = await client.put(
        f"/api/v1/memories/{memory_id}",
        json={"importance": 0.9},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert calls == []


async def test_update_to_a_nonexistent_memory_registers_nothing(
    client, auth_headers, session
):
    """A `project` in the request body of an update that 404s never lands on
    any memory row, so it must not register either — registration happens
    after `update_memory`'s `not memory` guard, deliberately, not before it.
    Guards against a narrower failure mode than I1 itself: registering on
    every PUT attempt regardless of whether the target id exists would still
    close I1's bypass but would also register project names nothing ever
    actually carries."""
    from uuid import uuid4

    names_before = await _project_names(session)
    assert "phantom-update-project" not in names_before

    response = await client.put(
        f"/api/v1/memories/{uuid4()}",
        json={"project": "phantom-update-project"},
        headers=auth_headers,
    )
    assert response.status_code == 404

    names_after = await _project_names(session)
    assert "phantom-update-project" not in names_after


# ── Clause 3: existing project strings backfill, idempotently ──────


async def test_backfill_inserts_every_distinct_memories_project(session):
    session.add_all([
        Memory(content="a", project="backfill-alpha"),
        Memory(content="b", project="backfill-beta"),
        Memory(content="c", project="backfill-alpha"),  # duplicate project
    ])
    await session.flush()

    inserted = await project_registry.backfill(session)
    assert inserted == 2, "exactly backfill-alpha and backfill-beta; a >= would mask a double-insert"

    names = await _project_names(session)
    assert "backfill-alpha" in names
    assert "backfill-beta" in names


async def _created_at(session, name: str):
    """A plain scalar-column read, deliberately not `select(Project)`.

    Re-selecting the mapped entity returns the session's identity-mapped
    Python object unchanged, so a before/after comparison of `row.created_at`
    off two such selects can never fail regardless of what the database
    actually holds — that was the hollow assertion the reviewer caught
    (mutation-proven: a `backfill` that rewrote every row's `created_at` on
    every call still passed). Selecting the bare column is not subject to
    identity-map caching and always reflects the current row.
    """
    return (await session.execute(
        select(Project.created_at).where(Project.name == name)
    )).scalar_one()


async def test_backfill_is_idempotent(session):
    session.add(Memory(content="a", project="backfill-idempotent"))
    await session.flush()

    first = await project_registry.backfill(session)
    assert first >= 1

    created_at_before = await _created_at(session, "backfill-idempotent")
    count_before = (await session.execute(
        select(func.count()).select_from(Project)
    )).scalar()

    second = await project_registry.backfill(session)
    assert second == 0

    created_at_after = await _created_at(session, "backfill-idempotent")
    count_after = (await session.execute(
        select(func.count()).select_from(Project)
    )).scalar()

    assert created_at_after == created_at_before
    assert count_after == count_before


async def test_backfill_is_not_confused_by_the_default_project(session):
    """`memories.project` defaults to `'default'`; backfill must register it
    like any other value, not treat it specially."""
    session.add(Memory(content="uses the column default"))
    await session.flush()

    await project_registry.backfill(session)

    names = await _project_names(session)
    assert "default" in names


async def test_a_mixed_project_batch_registers_every_distinct_project(
    client, auth_headers, session
):
    """The per-batch dedup must dedup, not truncate.

    Registration is deduped once per batch rather than once per entry, so a
    100-entry batch to one project opens one savepoint instead of a hundred.
    The mutation that shape invites is registering only the batch's *first*
    distinct project — and every other capture test in this file sends a
    single-entry batch, so all of them would pass under it. Recorded as a
    coverage gap by the fix round's re-review; closed here.
    """
    response = await client.post(
        "/api/v1/memories/batch",
        json={
            "entries": [
                {"content": "one", "project": "mix-alpha"},
                {"content": "two", "project": "mix-beta"},
                {"content": "three", "project": "mix-alpha"},
                {"content": "four"},
            ]
        },
        headers=auth_headers,
    )
    assert response.status_code == 202

    names = await _project_names(session)
    assert {"mix-alpha", "mix-beta", "default"} <= names, (
        "every distinct project in the batch must register, including the "
        "omitted one folding to 'default'"
    )
    for project in ("mix-alpha", "mix-beta"):
        count = (await session.execute(
            select(func.count()).select_from(Project).where(Project.name == project)
        )).scalar()
        assert count == 1, f"{project} deduped to one row, not inserted twice"
