""""Ask about selection" reaches the turn (audit O2b, 2026-10-05).

The memory graph's chat overlay sends the selected memory as
``selected_node_id`` and the selected entity as ``selected_entity_id``. Chat
took both and used neither, so asking about a selection answered exactly as if
nothing were selected. These tests pin what a selection now does to the
context a turn answers from, and what it must not do to the search itself.

The memory channel is stubbed to a fixed ranking, so every assertion compares
against an order the search produced without the selection.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.services import hybrid_search
from app.services.chat import CHAT_SELECTION_LIMIT, ChatService

pytestmark = pytest.mark.asyncio

PROJECT = "chat-selection"


def _service(session) -> ChatService:
    llm = AsyncMock()
    llm.embed = AsyncMock(return_value=([0.0], "fp"))
    return ChatService(session, llm, PostgresGraphRepository(session))


async def _memory(session, content: str, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(), content=content, source="api", importance=0.5,
        metadata_={}, project=PROJECT, status="active", is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()
    return memory


def _rank(monkeypatch, memories: list[Memory]) -> None:
    """The search ranks exactly these rows, in this order, whatever is selected."""
    rows = [
        {
            "memory_id": str(memory.id),
            "score": 0.9 - position / 100,
            "rrf_score": 0.03 - position / 1000,
            "payload": {"content": memory.content, "source": "api", "tags": []},
            "project": memory.project,
            "status": memory.status,
        }
        for position, memory in enumerate(memories)
    ]

    async def _search_with_trace(self, query, **kwargs):
        return hybrid_search.ChannelTrace(results=list(rows))

    monkeypatch.setattr(
        hybrid_search.HybridSearchService, "search_with_trace", _search_with_trace,
    )


async def _retrieved(session, monkeypatch) -> list[Memory]:
    first = await _memory(session, "pgbouncer runs in transaction mode")
    second = await _memory(session, "the homelab proxy sits on the LAN")
    _rank(monkeypatch, [first, second])
    return [first, second]


async def _system_prompt(svc: ChatService, retrieval: dict) -> str:
    conversation = await svc.create_conversation()
    return (await svc._build_prompt(conversation.id, "what is this?", retrieval))[0]["content"]


# ── a selected memory ────────────────────────────────────────────────


async def test_a_selected_memory_the_search_missed_comes_first(session, monkeypatch):
    first, second = await _retrieved(session, monkeypatch)
    selected = await _memory(session, "reciprocal rank fusion uses k=60")
    svc = _service(session)

    plain = await svc._retrieve("which pooler", {})
    retrieval = await svc._retrieve(
        "which pooler", {"selected_node_id": str(selected.id)},
    )

    assert [row["id"] for row in plain["memories"]] == [str(first.id), str(second.id)]
    assert [row["id"] for row in retrieval["memories"]] == [
        str(selected.id), str(first.id), str(second.id),
    ]
    assert [row["index"] for row in retrieval["memories"]] == [1, 2, 3]
    head = retrieval["memories"][0]
    assert head["selected"] is True
    assert head["content"] == selected.content
    # Nothing ranked it, so it carries no ranking: a zero would read as last.
    assert head["score"] is None and head["scores"] is None
    assert head["project"] == PROJECT and head["status"] == "active"
    assert "selected" not in retrieval["memories"][1]
    assert retrieval["selection"] == {"kind": "memory", "id": str(selected.id)}


async def test_a_selected_memory_the_search_found_moves_without_a_duplicate(
    session, monkeypatch,
):
    first, second = await _retrieved(session, monkeypatch)
    svc = _service(session)

    plain = await svc._retrieve("which pooler", {})
    retrieval = await svc._retrieve(
        "which pooler", {"selected_node_id": str(second.id)},
    )

    ids = [row["id"] for row in retrieval["memories"]]
    assert ids == [str(second.id), str(first.id)]
    head = retrieval["memories"][0]
    assert head["selected"] is True
    assert head["index"] == 1
    # It keeps the scores the search gave it.
    assert head["score"] == plain["memories"][1]["score"]
    assert head["scores"] == plain["memories"][1]["scores"]


async def test_the_model_is_told_which_memory_was_selected(session, monkeypatch):
    await _retrieved(session, monkeypatch)
    selected = await _memory(session, "reciprocal rank fusion uses k=60")
    svc = _service(session)

    retrieval = await svc._retrieve(
        "what is this?", {"selected_node_id": str(selected.id)},
    )
    system = await _system_prompt(svc, retrieval)

    assert "The user selected memory [1]" in system
    assert "[1] (source: api, tags: , selected by the user)\n" + selected.content in system
    assert "[2] (source: api, tags: , relevance: " in system


async def test_a_selection_outside_chats_scope_is_not_pinned(session, monkeypatch):
    first, second = await _retrieved(session, monkeypatch)
    newer = await _memory(session, "pgbouncer now runs in session mode")
    retired = await _memory(
        session, "pgbouncer ran in statement mode", status="superseded",
        superseded_by=newer.id,
    )
    foreign = await _memory(session, "someone else's pooler", project="elsewhere")
    svc = _service(session)

    for memory, context in (
        (retired, {}),
        (foreign, {"project": PROJECT}),
    ):
        retrieval = await svc._retrieve(
            "which pooler", {**context, "selected_node_id": str(memory.id)},
        )
        assert str(memory.id) not in {row["id"] for row in retrieval["memories"]}
        assert retrieval["selection"] is None


@pytest.mark.parametrize("bad", ["not-a-uuid", "entity:nope", "", 42])
async def test_a_malformed_selection_is_ignored(session, monkeypatch, bad):
    first, second = await _retrieved(session, monkeypatch)
    svc = _service(session)

    retrieval = await svc._retrieve(
        "which pooler", {"selected_node_id": bad, "selected_entity_id": bad},
    )

    assert [row["id"] for row in retrieval["memories"]] == [str(first.id), str(second.id)]
    assert retrieval["selection"] is None


# ── a selected entity ────────────────────────────────────────────────


async def _entity_asserted_by(session, *memories: Memory) -> str:
    graph = PostgresGraphRepository(session)
    entity = None
    for memory in memories:
        entity = await graph.create_entity("pgbouncer", "tool", {}, memory.id)
    await session.flush()
    return entity["id"]


@pytest.mark.parametrize("key", ["selected_entity_id", "selected_node_id"])
async def test_a_selected_entity_brings_the_memories_that_assert_it(
    session, monkeypatch, key,
):
    first, second = await _retrieved(session, monkeypatch)
    asserting = await _memory(session, "pgbouncer was chosen over pgcat")
    entity_id = await _entity_asserted_by(session, asserting, second)
    svc = _service(session)

    value = entity_id if key == "selected_entity_id" else f"entity:{entity_id}"
    retrieval = await svc._retrieve("which pooler", {key: value})

    # The retrieved assertion keeps its ranked place at the head, the one the
    # search missed follows it, and the rest of the retrieval comes after.
    assert [row["id"] for row in retrieval["memories"]] == [
        str(second.id), str(asserting.id), str(first.id),
    ]
    assert [row.get("selected", False) for row in retrieval["memories"]] == [
        True, True, False,
    ]
    assert retrieval["selection"] == {"kind": "entity", "id": entity_id}
    assert retrieval["entities"][0]["name"] == "pgbouncer"

    system = await _system_prompt(svc, retrieval)
    assert "[1], [2] are memories that assert it" in system


async def test_a_bare_node_id_naming_an_entity_is_read_as_one(session, monkeypatch):
    await _retrieved(session, monkeypatch)
    asserting = await _memory(session, "pgbouncer was chosen over pgcat")
    entity_id = await _entity_asserted_by(session, asserting)
    svc = _service(session)

    retrieval = await svc._retrieve("which pooler", {"selected_node_id": entity_id})

    assert retrieval["memories"][0]["id"] == str(asserting.id)
    assert retrieval["selection"] == {"kind": "entity", "id": entity_id}


async def test_a_selected_entity_pins_at_most_the_limit(session, monkeypatch):
    await _retrieved(session, monkeypatch)
    asserting = [
        await _memory(session, f"pgbouncer note {i}")
        for i in range(CHAT_SELECTION_LIMIT + 3)
    ]
    entity_id = await _entity_asserted_by(session, *asserting)
    svc = _service(session)

    retrieval = await svc._retrieve("which pooler", {"selected_entity_id": entity_id})

    pinned = [row for row in retrieval["memories"] if row.get("selected")]
    assert len(pinned) == CHAT_SELECTION_LIMIT
    assert len(retrieval["memories"]) == CHAT_SELECTION_LIMIT + 2


async def test_an_entity_asserted_only_outside_the_scope_pins_nothing(
    session, monkeypatch,
):
    first, second = await _retrieved(session, monkeypatch)
    foreign = await _memory(session, "pgbouncer elsewhere", project="elsewhere")
    entity_id = await _entity_asserted_by(session, foreign)
    svc = _service(session)

    retrieval = await svc._retrieve(
        "which pooler", {"project": PROJECT, "selected_entity_id": entity_id},
    )

    assert [row["id"] for row in retrieval["memories"]] == [str(first.id), str(second.id)]
    assert retrieval["selection"] is None
    assert retrieval["entities"] == [] or all(
        e.get("name") != "pgbouncer" for e in retrieval["entities"]
    )


async def test_the_persisted_turn_keeps_the_selection_mark(session, monkeypatch):
    """The panel renders history from the stored snapshot, so a selection that
    lived only on the live stream would vanish on reload."""
    await _retrieved(session, monkeypatch)
    selected = await _memory(session, "reciprocal rank fusion uses k=60")
    svc = _service(session)

    async def _stream(purpose, messages, **kwargs):
        yield "answer"

    svc.llm.chat_completion_stream = _stream

    sources = None
    message_id = None
    async for event in svc.send_message(
        None, "what is this?", {"selected_node_id": str(selected.id)},
    ):
        if event["type"] == "sources":
            sources = event
        if event["type"] == "done":
            message_id = uuid.UUID(event["message_id"])

    assert sources["memories"][0]["id"] == str(selected.id)
    assert sources["memories"][0]["selected"] is True

    from app.models.chat import Message
    stored = await session.get(Message, message_id)
    assert stored.context["memories"][0]["id"] == str(selected.id)
    assert stored.context["memories"][0]["selected"] is True


async def test_a_stream_that_breaks_mid_answer_reports_it_instead_of_finishing(
    session, monkeypatch,
):
    """Reached before only through an orchestrator another file left on
    app.state; asserted here in its own right."""
    await _retrieved(session, monkeypatch)
    svc = _service(session)

    async def _stream(purpose, messages, **kwargs):
        yield "partial"
        raise RuntimeError("provider dropped the connection")

    svc.llm.chat_completion_stream = _stream

    events = [event async for event in svc.send_message(None, "what is this?", {})]
    kinds = [event["type"] for event in events]

    assert "done" not in kinds
    assert events[-1] == {
        "type": "error",
        "message": "Stream interrupted: provider dropped the connection",
    }
