"""Re-lifting replaces, and withdrawal self-heals (TH1.13, doc 16 §5).

Two properties that are the same mechanism seen twice.

**Idempotent**, because a second lift of an unchanged document must leave one
set of propositions rather than two — and, more sharply, because a lift of a
*changed* document must not leave behind a claim its source no longer makes.
Strip-before-rewrite keyed on `document_id`, the same shape the block writer
uses on the same key.

**Self-healing through the ordinary sweep, not a bespoke one.** The strip is
`MemoryService.delete_memory` per row, so the graph contributions, the
fact-source provenance and the failure rows are withdrawn by the code path a
human deleting a memory takes. A bespoke sweep would be a second
implementation of each, and the second one is the one that drifts.

The strip keys on the provenance the lift wrote, never on `source` alone: every
lifted row in a project shares that literal, so a `source`-keyed strip would
delete a *different* document's propositions. That is the test below with two
documents, and it is the one a single-document suite cannot fail.
"""
from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.proposition_lift import (
    PROVENANCE_KEY,
    lift_document,
    lifted_memory_ids,
    strip_document_lift,
)

pytestmark = pytest.mark.asyncio

PROJECT = "th113-docs"


class ScriptedLlm:
    def __init__(self, texts):
        self.texts = list(texts)

    async def chat_completion(self, purpose, messages, **kwargs):
        body = self.texts.pop(0) if self.texts else "A claim."
        return json.dumps({"propositions": [{"text": body}]})


class RecordingService:
    """Writes memory rows for real, and records the deletes it was asked for.

    Real rows because the strip has to find them by provenance — a recording
    stub would let a strip that queried the wrong key pass.
    """

    def __init__(self, session):
        self.session = session
        self.deleted: list[str] = []

    async def batch_create_memories(self, entries, api_key_id, *, actor=None, **kwargs):
        acks = []
        for entry in entries:
            row = (await self.session.execute(
                text(
                    "INSERT INTO memories (id, content, source, project, metadata) "
                    "VALUES (CAST(:id AS uuid), :content, :source, :project, "
                    "CAST(:metadata AS jsonb)) "
                    "RETURNING CAST(id AS text) AS id"
                ),
                {
                    "id": str(uuid4()),
                    "content": entry.content, "source": entry.source,
                    "project": entry.project, "metadata": json.dumps(entry.metadata),
                },
            )).mappings().one()
            acks.append(type("Ack", (), {"id": row["id"]})())
        await self.session.flush()
        return acks

    async def delete_memory(self, memory_id, api_key_id, *, actor=None, **kwargs):
        self.deleted.append(str(memory_id))
        await self.session.execute(
            text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(memory_id)},
        )
        return True


async def _file(session, *texts: str, uri: str | None = None) -> str:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session, project=PROJECT, content="\n\n".join(texts),
        parse=lambda: drafts, title="doc", source_type="note", uri=uri,
    )
    await session.flush()
    return str(ingest.document_id)


# ── re-lifting replaces ──────────────────────────────────────────────


async def test_lifting_twice_leaves_one_set_not_two(session):
    document_id = await _file(session, "A body sentence.")
    service = RecordingService(session)

    first = await lift_document(
        session, ScriptedLlm(["First claim."]), service, document_id=document_id,
    )
    second = await lift_document(
        session, ScriptedLlm(["First claim."]), service, document_id=document_id,
    )

    assert first.stripped == 0, "the first lift had nothing to strip"
    assert second.stripped == 1, "the second lift stripped the first"
    assert len(await lifted_memory_ids(session, document_id=document_id)) == 1


async def test_a_changed_document_does_not_leave_its_old_claim_behind(session):
    """The sharper half: a stale proposition is worse than a duplicate, because
    it asserts something its source no longer says."""
    document_id = await _file(session, "A body sentence.")
    service = RecordingService(session)
    await lift_document(
        session, ScriptedLlm(["The sky is green."]), service, document_id=document_id,
    )

    await lift_document(
        session, ScriptedLlm(["The sky is blue."]), service, document_id=document_id,
    )

    contents = (await session.execute(
        text(
            "SELECT content FROM memories "
            "WHERE metadata -> :key ->> 'document_id' = :doc"
        ),
        {"key": PROVENANCE_KEY, "doc": document_id},
    )).scalars().all()
    assert contents == ["The sky is blue."]


async def _rows_for(session, document_id: str) -> list[str]:
    """Read provenance directly, never through `lifted_memory_ids`.

    The test below mutation-caught itself: keying the strip on `source` breaks
    that helper the same way, so an assertion built on it cancels the defect
    out and passes. The verification query has to be independent of the code
    under test.
    """
    return list((await session.execute(
        text(
            "SELECT content FROM memories "
            "WHERE metadata -> :key ->> 'document_id' = :doc"
        ),
        {"key": PROVENANCE_KEY, "doc": document_id},
    )).scalars().all())


async def test_the_strip_is_keyed_on_the_document_not_the_source_literal(session):
    """Every lifted row in a project shares `source='document'`. A strip keyed
    on it would delete another document's propositions, and this is the test a
    single-document suite cannot fail."""
    first_doc = await _file(session, "First doc body.", uri="file:///first")
    second_doc = await _file(session, "Second doc body.", uri="file:///second")
    service = RecordingService(session)

    await lift_document(session, ScriptedLlm(["From first."]), service, document_id=first_doc)
    await lift_document(session, ScriptedLlm(["From second."]), service, document_id=second_doc)

    await lift_document(session, ScriptedLlm(["From first again."]), service, document_id=first_doc)

    assert await _rows_for(session, second_doc) == ["From second."], (
        "re-lifting one document must not touch another's propositions"
    )
    assert await _rows_for(session, first_doc) == ["From first again."]


# ── withdrawal is the same call ──────────────────────────────────────


async def test_withdrawing_a_document_strips_its_lifted_rows(session):
    document_id = await _file(session, "A body sentence.")
    service = RecordingService(session)
    await lift_document(session, ScriptedLlm(["A claim."]), service, document_id=document_id)

    removed = await strip_document_lift(session, service, document_id=document_id)

    assert removed == 1
    assert await lifted_memory_ids(session, document_id=document_id) == []


async def test_the_strip_goes_through_the_ordinary_delete(session):
    """Not a bespoke sweep: the graph strip, the fact-source withdrawal and the
    failure-row cleanup are all things `delete_memory` already does, and a
    second implementation of each is the one that drifts."""
    document_id = await _file(session, "A body sentence.")
    service = RecordingService(session)
    result = await lift_document(
        session, ScriptedLlm(["A claim."]), service, document_id=document_id,
    )

    await strip_document_lift(session, service, document_id=document_id)

    assert service.deleted, "no delete_memory call was made"
    assert set(service.deleted) == set(result.memory_ids)
    for deleted in service.deleted:
        UUID(deleted)  # the ordinary door takes a UUID, not a string id


async def test_stripping_a_document_that_lifted_nothing_is_a_no_op(session):
    document_id = await _file(session, "A body sentence.")
    service = RecordingService(session)

    assert await strip_document_lift(session, service, document_id=document_id) == 0
    assert service.deleted == []
