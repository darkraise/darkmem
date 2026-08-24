import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select

from app.models.llm_usage import LLMUsage


@pytest.mark.asyncio
async def test_row_round_trips_with_unmeasured_tokens(clean_llm_usage, session):
    """An unmeasured call stores NULL tokens, not zeros: a vendor that stops
    reporting usage must never render as a free model."""
    row = LLMUsage(
        occurred_at=datetime.now(timezone.utc),
        purpose="extraction",
        model="deepseek-v4-flash",
        provider="deepseek-main",
        api_kind="deepseek",
        subject_type="memory",
        subject_id=str(uuid.uuid4()),
        project="default",
        tokens_measured=False,
        ok=True,
        duration_ms=120,
        usage_raw={},
        rates_used={},
    )
    session.add(row)
    await session.commit()

    got = (await session.execute(select(LLMUsage))).scalar_one()
    assert got.tokens_measured is False
    assert got.prompt_tokens is None
    assert got.cost_micros is None


@pytest.mark.asyncio
async def test_cost_is_an_integer_column(clean_llm_usage, session):
    """Money is micro-USD as BigInteger. `memories.confidence` being REAL is
    not a precedent for currency."""
    col = inspect(LLMUsage).columns["cost_micros"]
    assert col.type.python_type is int
