"""Code-chunk reembed must surface the gap, not silently report success.

After an embedder rotation, code chunks live only under the old fingerprint and
the active partition is empty, so code search returns nothing. The counts must
report the obsolete chunks (so the operator sees the gap), and the re-embed
action must direct them to a full reindex instead of broadcasting a fake 'done'.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services.reembed import ReembedService


async def _seed_old_fingerprint_chunk(session):
    await session.execute(text("""
        CREATE TABLE code_chunk_embeddings__old_4 (
            id uuid NOT NULL DEFAULT gen_random_uuid(),
            fingerprint text NOT NULL,
            repo_id uuid NOT NULL,
            file_path varchar(1024) NOT NULL,
            language varchar(50),
            symbol_name varchar(500),
            chunk_content text,
            line_start integer,
            line_end integer,
            embedding vector(4)
        )
    """))
    await session.execute(
        text("""
            INSERT INTO code_chunk_embeddings__old_4
                (fingerprint, repo_id, file_path, chunk_content, line_start, line_end)
            VALUES ('old|4', :rid, 'a.py', 'def f(): pass', 1, 5)
        """),
        {"rid": str(uuid.uuid4())},
    )


@pytest.mark.asyncio
async def test_count_missing_reports_code_chunks_under_other_fingerprint(session):
    await _seed_old_fingerprint_chunk(session)
    counts = await ReembedService(session).count_missing("new|4")
    assert counts["code_chunks"] >= 1


@pytest.mark.asyncio
async def test_reembed_code_chunks_directs_to_reindex(session):
    await _seed_old_fingerprint_chunk(session)
    result = await ReembedService(session).reembed_code_chunks(
        "new|4", None, "batch-1", None, {},
    )
    assert result["processed"] == 0
    assert "reindex" in (result["last_error"] or "").lower()
