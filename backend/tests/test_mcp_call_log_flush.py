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


class _InsertFailsOnce:
    """A factory whose session's call-log INSERT raises the first time."""

    def __init__(self, factory):
        self.factory = factory
        self.failed = False

    def __call__(self):
        session = self.factory()
        real_execute = session.execute

        async def execute(statement, *args, **kwargs):
            if statement is mcp_call_log._INSERT_SQL and not self.failed:
                self.failed = True
                raise ConnectionResetError("database unreachable")
            return await real_execute(statement, *args, **kwargs)

        session.execute = execute
        return session


async def _count(factory, tool: str) -> int:
    async with factory() as s:
        return (await s.execute(
            text("SELECT count(*) FROM mcp_tool_calls WHERE tool = :t"), {"t": tool},
        )).scalar_one()


@pytest.mark.asyncio
async def test_failed_flush_keeps_its_batch(committed, monkeypatch):
    tool = f"flush-probe-{uuid.uuid4().hex[:8]}"
    _queue(10, tool=tool)
    factory = _InsertFailsOnce(committed)

    assert await mcp_call_log.flush_once(factory) == 0
    assert factory.failed
    assert len(mcp_call_log._buffer) == 10
    assert await mcp_call_log.flush_once(factory) == 10
    assert await _count(committed, tool) == 10
    assert mcp_call_log.dropped_calls() == 0


@pytest.mark.asyncio
async def test_a_row_the_database_refuses_is_dropped_alone(committed):
    tool = f"flush-probe-{uuid.uuid4().hex[:8]}"
    _queue(4, tool=tool)
    _queue(1, tool="refused\x00tool")
    _queue(5, tool=tool)

    await mcp_call_log.flush_once(committed)

    assert await _count(committed, tool) == 9
    assert not mcp_call_log._buffer
    assert mcp_call_log.dropped_calls() == 1


@pytest.mark.asyncio
async def test_an_entry_that_cannot_become_a_row_is_dropped_alone(committed, monkeypatch):
    tool = f"flush-probe-{uuid.uuid4().hex[:8]}"
    _queue(3, tool=tool)
    _queue(1, tool="unbuildable")
    real = mcp_call_log._to_row

    def to_row(pending, *, log_query_text):
        if pending.tool == "unbuildable":
            raise TypeError("an argument json cannot carry")
        return real(pending, log_query_text=log_query_text)

    monkeypatch.setattr(mcp_call_log, "_to_row", to_row)
    assert await mcp_call_log.flush_once(committed) == 3
    assert await _count(committed, tool) == 3
    assert not mcp_call_log._buffer
    assert mcp_call_log.dropped_calls() == 1


@pytest.mark.asyncio
async def test_a_statement_error_is_settled_not_retried_for_ever(committed):
    tool = f"flush-probe-{uuid.uuid4().hex[:8]}"
    _queue(2, tool=tool)
    _queue(1, tool="refused\x00tool")

    class StatementFailsInBulk(_InsertFailsOnce):
        def __call__(self):
            session = self.factory()
            real_execute = session.execute

            async def execute(statement, *args, **kwargs):
                if statement is mcp_call_log._INSERT_SQL and len(args[0]) > 1:
                    raise ValueError("driver could not encode a parameter")
                return await real_execute(statement, *args, **kwargs)

            session.execute = execute
            return session

    assert await mcp_call_log.flush_once(StatementFailsInBulk(committed)) == 2
    assert await _count(committed, tool) == 2
    assert not mcp_call_log._buffer
    assert mcp_call_log.dropped_calls() == 1


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
    assert len(mcp_call_log._buffer) == 8
    assert mcp_call_log.dropped_calls() == 0

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
