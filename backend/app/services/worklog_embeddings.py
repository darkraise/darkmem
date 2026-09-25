"""Vectors for work-log entries: the ``worklog_embeddings__<slug>`` family.

Appends never embed, so a write never waits on the LAN embedder; the hourly
``block_embedding_refresh`` job fills this family through its work-log arm
(docs/superpowers/specs/2026-09-23-work-log-lane-design.md §1). ``project`` is
copied onto every vector row so ``worklog.search`` scans one project's rows
exactly.

The caller owns the transaction, with one exception shared with
``block_embeddings.embed_blocks``: registering a fingerprint this process has
not seen commits the session.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import (
    EmbedderInfo,
    child_table,
    embedder_registry,
    parse_fingerprint,
)

__all__ = ["EMBED_CHARS", "MISSING_SQL", "PARENT_TABLE", "WriteResult", "embed_entries"]

PARENT_TABLE = "worklog_embeddings"
# nomic-embed-text reads 2,048 tokens, so a longer body would be truncated by
# the embedder without a word. The keyword arm indexes the whole body.
EMBED_CHARS = 8_000
DEFAULT_EMBED_CHUNK = 32
DEFAULT_EMBED_CONCURRENCY = 2

MISSING_SQL = """
    SELECT CAST(e.id AS text) AS entry_id
    FROM worklog_entries e
    LEFT JOIN {table} v
           ON v.entry_id = e.id
          AND v.fingerprint = CAST(:fp AS text)
    WHERE v.entry_id IS NULL
    ORDER BY e.id
    LIMIT CAST(:limit AS int)
"""

_ENTRY_TEXTS = text(
    """
    SELECT CAST(e.id AS text) AS entry_id, w.project AS project,
           left(e.body, CAST(:chars AS int)) AS text
    FROM worklog_entries e
    JOIN workstreams w ON w.id = e.workstream_id
    WHERE e.id = ANY(CAST(:ids AS uuid[]))
    ORDER BY e.id
    """
)


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


async def _ensure_partition(session: AsyncSession, fingerprint: str) -> None:
    if embedder_registry.is_known(fingerprint):
        return
    model_id, dims = parse_fingerprint(fingerprint)
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"),
    )


async def embed_entries(
    session: AsyncSession,
    llm,
    *,
    entry_ids: Sequence[str],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed each entry's first EMBED_CHARS characters under the active fingerprint.

    ``None`` means no id named a surviving entry (a purge may have taken them
    since the caller listed them), so no fingerprint was measured.
    Re-embedding an entry replaces its vector.
    """
    ids = [str(entry_id) for entry_id in entry_ids]
    if not ids:
        return None
    rows = (await session.execute(
        _ENTRY_TEXTS, {"ids": ids, "chars": EMBED_CHARS}
    )).mappings().all()
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["text"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"worklog_embeddings: the embedder returned {len(vectors)} vectors "
            f"for {len(rows)} entries; refusing to write vectors under ids "
            "they may not belong to"
        )

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (entry_id, fingerprint, project, embedding)
                VALUES (CAST(:eid AS uuid), CAST(:fp AS text), CAST(:project AS text),
                        CAST(:embedding AS vector))
                ON CONFLICT (entry_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "eid": row["entry_id"],
                "fp": fingerprint,
                "project": row["project"],
                "embedding": str(list(vector)),
            },
        )
    return WriteResult(fingerprint=fingerprint, written=len(rows))
