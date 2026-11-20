"""A long conversation keeps its most recent turns when the prompt budget runs out."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.chat import Message
from app.repositories.graph import PostgresGraphRepository
from app.services import hybrid_search
from app.services.chat import MAX_PROMPT_CHARS, ChatService

pytestmark = pytest.mark.asyncio


async def test_the_budget_is_spent_on_the_newest_turns(session, monkeypatch):
    async def _no_rows(self, query, **kwargs):
        return hybrid_search.ChannelTrace(results=[])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _no_rows)
    llm = AsyncMock()
    llm.embed = AsyncMock(return_value=([0.0], "fp"))
    svc = ChatService(session, llm, PostgresGraphRepository(session))
    conversation = await svc.create_conversation()

    bulk = "x" * MAX_PROMPT_CHARS
    turns = [
        ("user", "oldest question " + bulk),
        ("assistant", "oldest answer " + bulk),
        ("user", "the recent question"),
        ("assistant", "the recent answer"),
        ("user", "what now?"),
    ]
    start = datetime.now(timezone.utc) - timedelta(minutes=len(turns))
    for position, (role, content) in enumerate(turns):
        session.add(Message(
            conversation_id=conversation.id, role=role, content=content,
            created_at=start + timedelta(minutes=position),
        ))
    await session.flush()

    retrieval = await svc._retrieve("what now?", {})
    messages = await svc._build_prompt(conversation.id, "what now?", retrieval)
    history = [m["content"] for m in messages[1:]]

    assert history[-3:] == ["the recent question", "the recent answer", "what now?"]
    assert not any(content.startswith("oldest question") for content in history)
