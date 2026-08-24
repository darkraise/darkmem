import inspect

import pytest
from sqlalchemy import select

from app.models.llm_usage import LLMUsage
from app.services.usage_recorder import UsageRecorder, UsageSubject, subject_scope


@pytest.mark.asyncio
async def test_a_failed_call_is_recorded(session_factory, session):
    """Failed work is pure waste and is exactly what this feature is for. Every
    error path in the orchestrator raises before the old log line, which is why
    the recorder wraps the request cycle rather than living there."""
    rec = UsageRecorder(session_factory, price_overrides={})
    await rec.record(purpose="extraction", model="deepseek-v4-flash",
                     provider="p", api_kind="deepseek", payload=None,
                     subject=UsageSubject("memory", "m1", "default"),
                     duration_ms=90, ok=False, error_kind="ReadTimeout")

    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.ok is False and row.error_kind == "ReadTimeout"
    assert row.tokens_measured is False
    assert row.prompt_tokens is None


def test_it_takes_no_caller_session():
    """Structural, not transactional. The property that matters is that the
    recorder cannot be handed the caller's session: the pipeline's savepoints
    would roll back the failed-work rows along with the failed work, the
    evidence deleting itself. Proving that transactionally needs a connection
    outside the test's own rolled-back transaction, so assert the shape."""
    assert "session" not in inspect.signature(UsageRecorder.record).parameters
    assert "session_factory" in inspect.signature(UsageRecorder.__init__).parameters


@pytest.mark.asyncio
async def test_it_never_raises_into_the_call_path():
    """Mirrors record_event: degrade loudly, never kill the work it describes."""
    def exploding_factory():
        raise RuntimeError("database is gone")

    rec = UsageRecorder(exploding_factory, price_overrides={})
    await rec.record(purpose="extraction", model="m", provider="p",
                     api_kind="openai", payload=None, subject=None,
                     duration_ms=1, ok=True, error_kind=None)


@pytest.mark.asyncio
async def test_subject_scope_supplies_an_ambient_subject(session_factory, session):
    rec = UsageRecorder(session_factory, price_overrides={})
    with subject_scope(UsageSubject("job_run", "buffer_flush@2026-08-23T00:00:00", None)):
        await rec.record(purpose="extraction", model="m", provider="p",
                         api_kind="openai", payload=None, subject=None,
                         duration_ms=1, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.subject_type == "job_run"


@pytest.mark.asyncio
async def test_an_explicit_subject_beats_the_ambient_one(session_factory, session):
    """Innermost wins: ingest inside buffer_flush attributes to the memory."""
    rec = UsageRecorder(session_factory, price_overrides={})
    with subject_scope(UsageSubject("job_run", "buffer_flush@t", None)):
        await rec.record(purpose="extraction", model="m", provider="p",
                         api_kind="openai", payload=None,
                         subject=UsageSubject("memory", "m1", "default"),
                         duration_ms=1, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert (row.subject_type, row.subject_id) == ("memory", "m1")


@pytest.mark.asyncio
async def test_an_unattributed_call_is_still_counted(session_factory, session):
    rec = UsageRecorder(session_factory, price_overrides={})
    await rec.record(purpose="reranker", model="m", provider="p",
                     api_kind="openai", payload=None, subject=None,
                     duration_ms=1, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.subject_type == "unattributed"


@pytest.mark.asyncio
async def test_a_priced_call_stores_the_rates_it_used(session_factory, session):
    """So the arithmetic can be audited later without knowing what the price
    table said that day."""
    rec = UsageRecorder(session_factory, price_overrides={})
    await rec.record(
        purpose="extraction", model="deepseek-v4-flash", provider="p",
        api_kind="deepseek",
        payload={"usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0}},
        subject=UsageSubject("memory", "m1", "default"),
        duration_ms=5, ok=True, error_kind=None)
    row = (await session.execute(select(LLMUsage))).scalar_one()
    assert row.tokens_measured is True
    assert row.cost_micros == 270_000
    assert row.rates_used["input"] == 270_000
