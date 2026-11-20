"""What a chat turn holds while the answer streams, and what it leaves behind.

A stream can run for minutes. Whatever the turn's session still holds then — a
pooled connection inside an open transaction — is held for all of it, and a
client that walks away mid-answer must still leave the usage row the vendor
billed for.
"""
from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock

import anyio
import httpx
import pytest
from sqlalchemy import select, text

from app.config import LLMPurposeConfig
from app.models.chat import Message
from app.repositories.graph import PostgresGraphRepository
from app.services import hybrid_search
from app.services.chat import ChatService
from app.services.llm import LLMOrchestrator
from app.services.usage_recorder import UsageRecorder

pytestmark = pytest.mark.asyncio


async def _no_rows(self, query, **kwargs):
    return hybrid_search.ChannelTrace(results=[])


async def test_no_transaction_is_open_during_the_stream(session, monkeypatch):
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _no_rows)
    in_transaction: list[bool] = []

    async def _stream(purpose, messages, usage_subject=None):
        in_transaction.append(session.in_transaction())
        yield "an "
        await asyncio.sleep(0)
        in_transaction.append(session.in_transaction())
        yield "answer"

    llm = AsyncMock()
    llm.embed = AsyncMock(return_value=([0.0], "fp"))
    llm.chat_completion_stream = _stream
    svc = ChatService(session, llm, PostgresGraphRepository(session))

    events = [e async for e in svc.send_message(None, "what runs the cache?", {})]

    assert in_transaction == [False, False]
    assert events[-1]["type"] == "done"
    stored = (await session.execute(
        select(Message.content).where(Message.role == "assistant")
        .where(Message.conversation_id == uuid.UUID(events[-1]["conversation_id"]))
    )).scalars().all()
    assert stored == ["an answer"]


class _SignallingRecorder(UsageRecorder):
    def __init__(self, session_factory):
        super().__init__(session_factory, price_overrides={})
        self.recorded = asyncio.Event()

    async def record(self, **kwargs) -> None:
        await super().record(**kwargs)
        self.recorded.set()


async def test_usage_row_survives_a_client_disconnect(session, session_factory):
    first_token_sent = asyncio.Event()
    never = asyncio.Event()

    async def _body():
        yield b'data: {"choices":[{"delta":{"content":"he"}}]}\n'
        first_token_sent.set()
        await never.wait()

    recorder = _SignallingRecorder(session_factory)
    orchestrator = LLMOrchestrator(
        {"reasoning": LLMPurposeConfig(
            base_url="http://mock/v1", model="disconnect-model", dimensions=3,
        )},
        recorder=recorder,
    )
    orchestrator._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=_body()))
    )

    scope = anyio.CancelScope()

    async def _client_reads_then_leaves():
        # A cancel scope re-delivers cancellation at every await, as the ASGI
        # server's does when the client disconnects mid-response.
        with scope:
            async for _ in orchestrator.chat_completion_stream(
                "reasoning", [{"role": "user", "content": "q"}],
            ):
                pass

    reader = asyncio.create_task(_client_reads_then_leaves())
    await asyncio.wait_for(first_token_sent.wait(), timeout=5)
    scope.cancel()
    await reader

    await asyncio.wait_for(recorder.recorded.wait(), timeout=5)
    rows = (await session.execute(text(
        "SELECT ok, error_kind FROM llm_usage WHERE model = 'disconnect-model'"
    ))).all()
    assert [(r.ok, r.error_kind) for r in rows] == [(False, "cancelled")]
    await orchestrator.close()
