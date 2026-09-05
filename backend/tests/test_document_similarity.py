"""The fingerprint a relatedness read compares under (spec §3.5)."""
import pytest
from sqlalchemy import text

from app.services.document_similarity import resolve_shared_fingerprint


@pytest.mark.asyncio
async def test_returns_none_when_no_embedder_is_registered(session):
    result = await resolve_shared_fingerprint(
        session, document_id="00000000-0000-0000-0000-000000000000",
        project="default", counterpart="memory",
    )
    assert result is None


@pytest.mark.asyncio
async def test_rejects_an_unknown_counterpart(session):
    with pytest.raises(ValueError):
        await resolve_shared_fingerprint(
            session, document_id="00000000-0000-0000-0000-000000000000",
            project="default", counterpart="article",
        )


@pytest.mark.asyncio
async def test_skips_a_retired_embedder(session):
    """A retired fingerprint is never a comparison basis, even holding rows."""
    await session.execute(text(
        "INSERT INTO embedders (fingerprint, model_id, dims, source, retired_at) "
        "VALUES ('retired_fp', 'm', 4, 'llm', now())"
    ))
    result = await resolve_shared_fingerprint(
        session, document_id="00000000-0000-0000-0000-000000000000",
        project="default", counterpart="memory",
    )
    assert result is None
