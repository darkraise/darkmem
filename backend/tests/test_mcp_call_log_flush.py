"""The MCP call log keeps what a failed flush popped, backs off, and never
stores the argument values a validation error echoes."""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio
from pydantic import ValidationError, create_model
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.services.mcp_call_log as mcp_call_log
from tests.conftest import test_engine


def _queue(n: int, *, tool: str = "memory_stats") -> None:
    for _ in range(n):
        mcp_call_log.record_call(
            tool=tool, scope="read", status="ok", duration_ms=1,
            api_key_id=None, key_name=None, client=None, arguments={},
        )


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setattr(mcp_call_log, "_auto_flush", False)
    mcp_call_log._reset_for_tests()
    yield
    mcp_call_log._reset_for_tests()


@pytest_asyncio.fixture
async def committed(setup_database):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _clean():
        async with factory() as s:
            await s.execute(text("DELETE FROM mcp_tool_calls"))
            await s.commit()

    await _clean()
    yield factory
    await _clean()


@pytest.mark.asyncio
async def test_failed_flush_keeps_its_batch(committed, monkeypatch):
    tool = f"flush-probe-{uuid.uuid4().hex[:8]}"
    _queue(10, tool=tool)
    real_insert = mcp_call_log._INSERT_SQL
    calls = {"n": 0}

    class FailOnce:
        def __init__(self):
            self.real = committed

        def __call__(self):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("database unreachable")
            return self.real()

    assert await mcp_call_log.flush_once(FailOnce()) == 0
    assert len(mcp_call_log._buffer) == 10
    assert await mcp_call_log.flush_once(FailOnce()) == 10
    async with committed() as s:
        count = (await s.execute(
            text("SELECT count(*) FROM mcp_tool_calls WHERE tool = :t"), {"t": tool},
        )).scalar_one()
    assert count == 10
    assert mcp_call_log._INSERT_SQL is real_insert


def test_buffer_overflow_is_counted(monkeypatch):
    monkeypatch.setattr(mcp_call_log, "_BUFFER_MAX", 10)
    _queue(6)
    batch = [mcp_call_log._buffer.popleft() for _ in range(6)]
    _queue(8)
    mcp_call_log._requeue(batch)
    assert len(mcp_call_log._buffer) == 10
    assert mcp_call_log.dropped_calls() == 4


@pytest.mark.asyncio
async def test_failed_flush_backs_off(monkeypatch):
    def broken():
        raise RuntimeError("database unreachable")

    delays = []
    for _ in range(8):
        _queue(1)
        await mcp_call_log.flush_once(broken)
        delays.append(mcp_call_log._backoff_seconds)
    assert delays == [1, 2, 4, 8, 16, 32, 60, 60]

    slept: list[float] = []
    outcomes = iter([0, 0, 1])

    async def fake_flush(session_factory=None):
        outcome = next(outcomes)
        if outcome:
            mcp_call_log._buffer.clear()
            mcp_call_log._backoff_seconds = 0
        else:
            mcp_call_log._backoff_seconds = min(60, mcp_call_log._backoff_seconds * 2 or 1)
        return outcome

    async def fake_sleep(seconds):
        slept.append(seconds)

    mcp_call_log._backoff_seconds = 0
    monkeypatch.setattr(mcp_call_log, "flush_once", fake_flush)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await mcp_call_log._flush_loop()
    assert slept == [mcp_call_log._FLUSH_DELAY_SECONDS, 1, 2]
    assert mcp_call_log._backoff_seconds == 0


def test_validation_error_text_carries_no_input():
    model = create_model("memory_addArguments", content=(str, ...))
    with pytest.raises(ValidationError) as caught:
        model(content={"body": "SECRET-MARK"})
    mcp_call_log.record_call(
        tool="memory_add", scope="capture", status="error", duration_ms=1,
        api_key_id=None, key_name=None, client=None,
        arguments={"content": {"body": "SECRET-MARK"}},
        error=f"Error executing tool memory_add: {caught.value}",
    )
    error = mcp_call_log._buffer[-1].error
    assert "SECRET-MARK" not in error
    assert "content" in error and "string_type" in error
