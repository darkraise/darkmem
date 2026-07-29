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


# ── Clause 3: existing project strings backfill, idempotently ──────


async def test_backfill_inserts_every_distinct_memories_project(session):
    session.add_all([
        Memory(content="a", project="backfill-alpha"),
        Memory(content="b", project="backfill-beta"),
        Memory(content="c", project="backfill-alpha"),  # duplicate project
    ])
    await session.flush()

    inserted = await project_registry.backfill(session)
    assert inserted >= 2

    names = await _project_names(session)
    assert "backfill-alpha" in names
    assert "backfill-beta" in names


async def test_backfill_is_idempotent(session):
    session.add(Memory(content="a", project="backfill-idempotent"))
    await session.flush()

    first = await project_registry.backfill(session)
    assert first >= 1

    row = (await session.execute(
        select(Project).where(Project.name == "backfill-idempotent")
    )).scalar_one()
    created_at_before = row.created_at
    count_before = (await session.execute(
        select(func.count()).select_from(Project)
    )).scalar()

    second = await project_registry.backfill(session)
    assert second == 0

    row_again = (await session.execute(
        select(Project).where(Project.name == "backfill-idempotent")
    )).scalar_one()
    count_after = (await session.execute(
        select(func.count()).select_from(Project)
    )).scalar()

    assert row_again.created_at == created_at_before
    assert count_after == count_before


async def test_backfill_is_not_confused_by_the_default_project(session):
    """`memories.project` defaults to `'default'`; backfill must register it
    like any other value, not treat it specially."""
    session.add(Memory(content="uses the column default"))
    await session.flush()

    await project_registry.backfill(session)

    names = await _project_names(session)
    assert "default" in names
