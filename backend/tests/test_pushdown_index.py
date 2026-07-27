"""The SQL filter-pushdown's one required index (doc 04 §10, inventory §3.2).

Honest caveat recorded with it: the SEMANTIC channel cannot use this index —
an HNSW scan applies the predicate as a post-scan filter over its candidate
stream — so this serves the keyword and direct-scan sides. The pushdown still
closes the isolation leak on every channel; only the plan differs.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_pushdown_index_exists_and_is_partial(session):
    row = (
        await session.execute(
            text("SELECT indexdef FROM pg_indexes "
                 "WHERE schemaname = 'public' AND indexname = 'ix_memories_project_live'")
        )
    ).scalar_one_or_none()
    assert row is not None, "the pushdown support index is missing"
    assert "project" in row
    assert "status = 'active'" in row
    assert "is_archived = false" in row
