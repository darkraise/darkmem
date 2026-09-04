"""Memories related to a document, through the entities its lift minted (§6.2).

The sibling of `test_document_connections.py` and pinned the same way: the
behavioural half is small, and the structural half is the task. Each "must not"
clause is checked against the parsed source rather than by example, because
every one of them is satisfied by a module that simply has not grown the thing
yet.

The distinction that matters and is easy to lose: an **unlifted** document is
not an empty result. A surface that renders both the same way tells a reader
"nothing relates to this document" when the truth is "nobody has asked yet".
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.document_related import related_memories_for_document
from app.services.proposition_lift import PROVENANCE_KEY

pytestmark = pytest.mark.asyncio

BACKEND = Path(__file__).resolve().parent.parent
MODULE = BACKEND / "app" / "services" / "document_related.py"
PROJECT = "rel-docs"
OTHER_PROJECT = "rel-other"


async def _document(session, title: str, *, project: str = PROJECT, uri: str) -> str:
    ingest = await file_document(
        session, project=project, content="body",
        parse=lambda: [BlockDraft(text="body", type="paragraph")],
        title=title, source_type="note", uri=uri,
    )
    await session.flush()
    return str(ingest.document_id)


async def _memory(
    session, *, content: str, project: str = PROJECT,
    document_id: str | None = None, status: str = "active",
) -> str:
    """A memory, optionally carrying a document's lift provenance."""
    memory_id = str(uuid4())
    metadata = (
        json.dumps({PROVENANCE_KEY: {"document_id": document_id}})
        if document_id else json.dumps({})
    )
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, status, metadata) "
            "VALUES (CAST(:id AS uuid), :content, 'document', :project, :status, "
            "CAST(:metadata AS jsonb))"
        ),
        {
            "id": memory_id, "content": content, "project": project,
            "status": status, "metadata": metadata,
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


# ── the relation is the shared graph ─────────────────────────────────


async def test_a_memory_asserting_the_same_entity_is_related(session):
    doc = await _document(session, "Doc", uri="file:///r/one")
    lifted = await _memory(session, content="a lifted proposition", document_id=doc)
    other = await _memory(session, content="an ordinary memory")
    await _entity(session, "postgres", [lifted, other])

    related = await related_memories_for_document(session, document_id=doc)

    assert related.lifted is True
    assert [m.memory_id for m in related.items] == [other]
    assert related.items[0].shared_entities == ("postgres",)
    assert related.items[0].content == "an ordinary memory"


async def test_the_documents_own_lift_is_never_related_to_itself(session):
    # Every lifted memory shares every entity with itself, so without the
    # exclusion this surface would return the document's own lift as its top
    # result -- every row and no information.
    doc = await _document(session, "Doc", uri="file:///r/self")
    one = await _memory(session, content="p one", document_id=doc)
    two = await _memory(session, content="p two", document_id=doc)
    await _entity(session, "postgres", [one, two])

    related = await related_memories_for_document(session, document_id=doc)

    assert related.lifted is True
    assert related.items == ()


async def test_more_shared_entities_rank_higher(session):
    doc = await _document(session, "Doc", uri="file:///r/rank")
    lifted = await _memory(session, content="p", document_id=doc)
    strong = await _memory(session, content="shares two")
    weak = await _memory(session, content="shares one")
    await _entity(session, "postgres", [lifted, strong, weak])
    await _entity(session, "pgvector", [lifted, strong])

    related = await related_memories_for_document(session, document_id=doc)

    assert [m.memory_id for m in related.items] == [strong, weak]
    assert related.items[0].shared_count == 2
    assert related.items[1].shared_count == 1


async def test_a_memory_in_another_project_is_never_related(session):
    # This surface exists to show a reader rows they had not thought of, which
    # is the worst place to cross an isolation boundary (doc 18 §8).
    doc = await _document(session, "Doc", uri="file:///r/scope")
    lifted = await _memory(session, content="p", document_id=doc)
    foreign = await _memory(session, content="foreign", project=OTHER_PROJECT)
    await _entity(session, "postgres", [lifted, foreign])

    related = await related_memories_for_document(session, document_id=doc)

    assert related.items == ()


async def test_a_superseded_memory_still_reports_its_status(session):
    # A maintenance surface that hid the status would invite an edit to a row
    # the pipeline has already retired.
    doc = await _document(session, "Doc", uri="file:///r/status")
    lifted = await _memory(session, content="p", document_id=doc)
    old = await _memory(session, content="retired", status="deprecated")
    await _entity(session, "postgres", [lifted, old])

    related = await related_memories_for_document(session, document_id=doc)

    assert [m.status for m in related.items] == ["deprecated"]


# ── unlifted is not empty ────────────────────────────────────────────


async def test_an_unlifted_document_says_so_rather_than_returning_empty(session):
    doc = await _document(session, "Doc", uri="file:///r/unlifted")
    other = await _memory(session, content="an ordinary memory")
    await _entity(session, "postgres", [other])

    related = await related_memories_for_document(session, document_id=doc)

    assert related.lifted is False
    assert related.items == ()


async def test_a_lifted_document_with_no_relations_is_lifted_and_empty(session):
    doc = await _document(session, "Doc", uri="file:///r/lonely")
    lifted = await _memory(session, content="p", document_id=doc)
    await _entity(session, "postgres", [lifted])

    related = await related_memories_for_document(session, document_id=doc)

    # The pair the UI must tell apart: lifted, and genuinely nothing related.
    assert related.lifted is True
    assert related.items == ()


async def test_an_unknown_document_is_not_an_error(session):
    related = await related_memories_for_document(session, document_id=uuid4())
    assert related.lifted is False
    assert related.items == ()


# ── structural: no engine, no synthesis, no block channel ────────────


def _code_only() -> str:
    """The module's source with every docstring removed.

    A raw-text scan would convict this module of the sentences in its own
    header explaining why it makes no model call and computes no score -- the
    trap `test_document_summary.py` records and solves the same way. What the
    scans below must read is the code.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)
    return ast.unparse(tree)


def test_the_module_makes_no_model_call():
    """The moment a relatedness feature writes prose about what a document and
    a memory share, it has become unbadged synthesis -- which doc 09 owns
    properly, with grounding and a ladder."""
    code = _code_only()
    for forbidden in ("llm", "chat_completion", "LLMOrchestrator", "purpose"):
        assert forbidden not in code, f"{forbidden} reached the related read"


def test_the_module_reads_no_block_row():
    """The path is document -> lifted memories -> entities -> memories. A
    block row crossing here would put the block channel into a memory-content
    surface, which `test_block_retrieval.py`'s firewall forbids."""
    code = _code_only()
    assert "blocks" not in code
    assert "block_embeddings" not in code


def test_the_module_creates_no_table():
    """Every relation it names already exists."""
    code = _code_only()
    for ddl in ("CREATE TABLE", "CREATE INDEX", "ALTER TABLE"):
        assert ddl not in code


def test_the_module_writes_nothing():
    """A read surface. An INSERT here would mean the act of looking at a
    document changed the corpus."""
    code = _code_only().upper()
    for write in ("INSERT INTO", "UPDATE ", "DELETE FROM"):
        assert write not in code


def test_nothing_normalises_the_shared_count_into_a_score():
    """Shared-entity count is evidence. A similarity number would read as a
    measurement nobody made -- the rule `document_connections` states for
    itself."""
    code = _code_only().lower()
    for scoring in ("similarity", "normalis", "normaliz", "/ total", "weight"):
        assert scoring not in code
