"""Connections are emergent, not computed by a new engine (TH1.15, doc 16 §6).

The behavioural half is small — two documents whose lifted propositions minted
the same entity are connected — and the structural half is the task. Three
"must not" clauses, each pinned against the parsed source rather than by
example, because each of them is satisfied by any module that simply has not
grown the thing yet:

- **no new table**: every relation the module names already exists;
- **no new job family**: nothing registers, schedules or is registered;
- **no synthesis**: the module makes no model call, so a "connections" feature
  cannot quietly become unbadged multi-document prose. That is doc 09's
  article, with grounding, citations and a ladder — and this reading blocks
  instead is exactly what doc 16 §6 puts out of scope.

Project scoping gets its own test because this surface suggests things a reader
has not thought of, which is the worst place to leak across an isolation
boundary.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.document_connections import connections_for_document
from app.services.document_ingest import BlockDraft, file_document
from app.services.proposition_lift import PROVENANCE_KEY

pytestmark = pytest.mark.asyncio

BACKEND = Path(__file__).resolve().parent.parent
MODULE = BACKEND / "app" / "services" / "document_connections.py"
PROJECT = "th115-docs"
OTHER_PROJECT = "th115-other"


async def _document(session, title: str, *, project: str = PROJECT, uri: str) -> str:
    ingest = await file_document(
        session, project=project, content="body",
        parse=lambda: [BlockDraft(text="body", type="paragraph")],
        title=title, source_type="note", uri=uri,
    )
    await session.flush()
    return str(ingest.document_id)


async def _lifted_memory(session, document_id: str, *, project: str = PROJECT) -> str:
    memory_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, metadata) "
            "VALUES (CAST(:id AS uuid), :content, 'document', :project, "
            "CAST(:metadata AS jsonb))"
        ),
        {
            "id": memory_id, "content": "a lifted proposition", "project": project,
            "metadata": json.dumps({PROVENANCE_KEY: {"document_id": document_id}}),
        },
    )
    return memory_id


async def _entity(session, name: str, memory_ids: list[str]) -> None:
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (CAST(:id AS uuid), :name, 'concept', CAST(:ids AS uuid[]))"
        ),
        {"id": str(uuid4()), "name": name, "ids": memory_ids},
    )
    await session.flush()


# ── the connection is the shared graph ───────────────────────────────


async def test_two_documents_sharing_an_entity_are_connected(session):
    first = await _document(session, "First", uri="file:///c/first")
    second = await _document(session, "Second", uri="file:///c/second")
    mine = await _lifted_memory(session, first)
    theirs = await _lifted_memory(session, second)
    await _entity(session, "postgres", [mine, theirs])

    connections = await connections_for_document(session, document_id=first)

    assert [c.document_id for c in connections] == [second]
    assert connections[0].title == "Second"
    assert connections[0].shared_entities == ("postgres",)


async def test_documents_sharing_nothing_are_not_connected(session):
    first = await _document(session, "First", uri="file:///c/a")
    second = await _document(session, "Second", uri="file:///c/b")
    mine = await _lifted_memory(session, first)
    theirs = await _lifted_memory(session, second)
    await _entity(session, "postgres", [mine])
    await _entity(session, "redis", [theirs])

    assert await connections_for_document(session, document_id=first) == []


async def test_a_document_is_never_connected_to_itself(session):
    first = await _document(session, "First", uri="file:///c/self")
    one = await _lifted_memory(session, first)
    two = await _lifted_memory(session, first)
    await _entity(session, "postgres", [one, two])

    assert await connections_for_document(session, document_id=first) == []


async def test_more_shared_entities_rank_higher(session):
    """`distant` is filed *before* `close` on purpose. Document ids are
    time-ordered, so ordering by id alone would put distant first — which
    makes a regression that dropped the count from the ORDER BY fail
    deterministically instead of half the time. The first version of this test
    filed them the other way round and the drill passed on luck."""
    first = await _document(session, "First", uri="file:///c/rank-a")
    distant = await _document(session, "Distant", uri="file:///c/rank-c")
    close = await _document(session, "Close", uri="file:///c/rank-b")
    assert distant < close, "the ids must sort opposite to the shared count"
    mine = await _lifted_memory(session, first)
    close_mem = await _lifted_memory(session, close)
    distant_mem = await _lifted_memory(session, distant)
    await _entity(session, "postgres", [mine, close_mem, distant_mem])
    await _entity(session, "linux", [mine, close_mem])

    connections = await connections_for_document(session, document_id=first)

    assert [c.document_id for c in connections] == [close, distant]
    assert connections[0].shared_count == 2 and connections[1].shared_count == 1


async def test_connections_do_not_cross_a_project_boundary(session):
    first = await _document(session, "First", uri="file:///c/scoped-a")
    foreign = await _document(
        session, "Foreign", project=OTHER_PROJECT, uri="file:///c/scoped-b",
    )
    mine = await _lifted_memory(session, first)
    theirs = await _lifted_memory(session, foreign, project=OTHER_PROJECT)
    await _entity(session, "postgres", [mine, theirs])

    assert await connections_for_document(session, document_id=first) == []


async def test_an_unknown_document_yields_nothing(session):
    assert await connections_for_document(
        session, document_id="33333333-3333-3333-3333-333333333333",
    ) == []


# ── no new engine: the three structural clauses ──────────────────────


def _module_code() -> str:
    return ast.unparse(ast.parse(MODULE.read_text(encoding="utf-8")))


def test_the_module_names_no_table_that_does_not_already_exist():
    """"No new table" is checked by naming the ones it may use: a module that
    later invented `document_connections` would name it here and fail."""
    code = _module_code()
    allowed = {"memories", "entities", "documents"}
    named = {
        word.strip(" ()\n,")
        for line in code.splitlines()
        for word in line.split()
    }
    tables = {
        candidate for candidate in named
        if candidate.endswith("_connections") or candidate.endswith("_links")
    }
    assert not tables, f"the module names a new table: {tables}"
    for table in allowed:
        assert table in code, f"the module stopped reading {table} — re-point this test"


def test_the_module_registers_no_job():
    code = _module_code()
    for marker in ("JobRegistry", "register_job", "cron", "job_registry"):
        assert marker not in code, f"a connections job family appeared: {marker}"


def test_the_module_makes_no_model_call():
    """The moment this generates prose about several documents it has become
    unbadged synthesis reading blocks — which is doc 09's article, with
    grounding and a ladder, and is out of scope here."""
    code = _module_code()
    for marker in ("chat_completion", "llm", "summarization", "reasoning"):
        assert marker not in code, f"the connections surface reached a model: {marker}"
