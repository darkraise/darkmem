"""Embedder registry: fingerprint → per-fingerprint table lifecycle.

PostgreSQL declarative partitioning forbids per-partition column type
overrides, but pgvector requires a fixed-dim ``vector(N)`` column for HNSW
indexes. We resolve that by giving each embedder its own independent table
named ``<parent>__<slug>`` (no inheritance). The registry decides table names
and creates them on demand. Application code routes reads and writes by
asking the registry for the right table name.

Invariant: ``register`` is idempotent. The first caller inserts the row in
``embedders`` and creates the four child tables; later callers find the row,
hit the in-process cache, and return without DDL.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Each value is (logical_parent_name, child_table_template) where the template
# names ``{name}`` is the per-fingerprint table to create and ``{dims}`` is the
# pgvector typmod. Foreign keys cascade so deleting a memory/entity/repo row
# deletes its embeddings across every fingerprint.
_TABLE_TEMPLATES: dict[str, str] = {
    "memory_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint)"
        ")"
    ),
    "entity_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (entity_id, fingerprint)"
        ")"
    ),
    "code_chunk_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " id UUID NOT NULL DEFAULT gen_random_uuid(),"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " repo_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,"
        " file_path VARCHAR(1024) NOT NULL,"
        " language VARCHAR(50),"
        " symbol_name VARCHAR(500),"
        " chunk_content TEXT,"
        " line_start INTEGER,"
        " line_end INTEGER,"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (id, fingerprint)"
        ")"
    ),
    "entity_embedding_cache": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " name_lower VARCHAR(255) NOT NULL,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " hit_count INTEGER NOT NULL DEFAULT 1,"
        " PRIMARY KEY (name_lower, fingerprint)"
        ")"
    ),
}


# Aux indexes per child table. Keyed by the logical parent name.
_AUX_INDEXES: dict[str, list[str]] = {
    "memory_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_memory_id ON {name} (memory_id)",
    ],
    "entity_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_entity_id ON {name} (entity_id)",
    ],
    "code_chunk_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_repo ON {name} (repo_id)",
        "CREATE INDEX IF NOT EXISTS ix_{name}_file ON {name} (repo_id, file_path)",
    ],
    "entity_embedding_cache": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_last_used ON {name} (last_used_at)",
    ],
}


@dataclass(frozen=True)
class EmbedderInfo:
    fingerprint: str
    model_id: str
    dims: int
    # Always "llm" — kept as a free-form string so future embedder kinds
    # can be added without changing the dataclass.
    source: str


class EmbedderRegistry:
    """Process-wide cache of registered fingerprints + lazy per-table DDL."""

    def __init__(self) -> None:
        self._known: set[str] = set()
        self._lock = asyncio.Lock()

    def is_known(self, fingerprint: str) -> bool:
        return fingerprint in self._known

    def forget(self, fingerprint: str) -> None:
        """Drop a fingerprint from the in-process cache. Test helper only."""
        self._known.discard(fingerprint)

    async def register(self, session: AsyncSession, info: EmbedderInfo) -> None:
        """Idempotently register ``info`` and create its per-fingerprint tables."""
        if info.fingerprint in self._known:
            return

        async with self._lock:
            if info.fingerprint in self._known:
                return

            await session.execute(
                text(
                    """
                    INSERT INTO embedders (fingerprint, model_id, dims, source)
                    VALUES (:fp, :model_id, :dims, :source)
                    ON CONFLICT (fingerprint) DO NOTHING
                    """
                ),
                {
                    "fp": info.fingerprint,
                    "model_id": info.model_id,
                    "dims": info.dims,
                    "source": info.source,
                },
            )

            slug = _partition_slug(info.fingerprint)
            for parent, ddl_template in _TABLE_TEMPLATES.items():
                child = f"{parent}__{slug}"
                await session.execute(
                    text(ddl_template.format(name=child, dims=info.dims))
                )
                # HNSW index: cosine ops match the application query plans.
                hnsw_idx = f"ix_{child}_hnsw"
                await session.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS {hnsw_idx} "
                        f"ON {child} USING hnsw (embedding vector_cosine_ops) "
                        f"WITH (m = 16, ef_construction = 128)"
                    )
                )
                for aux_template in _AUX_INDEXES.get(parent, []):
                    await session.execute(text(aux_template.format(name=child)))

            await session.commit()
            self._known.add(info.fingerprint)
            logger.info(
                "EmbedderRegistry: registered %s (model_id=%s, dims=%d, source=%s)",
                info.fingerprint, info.model_id, info.dims, info.source,
            )

    async def warm_cache_from_db(self, session: AsyncSession) -> None:
        """Hydrate the cache from the registry table at startup."""
        rows = (
            await session.execute(text("SELECT fingerprint FROM embedders WHERE retired_at IS NULL"))
        ).scalars().all()
        self._known.update(rows)


# Module-level singleton — shared across all sessions in the process.
embedder_registry = EmbedderRegistry()


def _partition_slug(fingerprint: str) -> str:
    """Convert a fingerprint to a Postgres-safe identifier suffix.

    Fingerprints look like ``qwen3-embedding:0.6b|1024``; per-fingerprint
    table names need to be ASCII identifiers, so we map non-word characters
    to ``_`` and lower-case the result.

    KNOWN LIMITATION (kept backward-compatible deliberately): the slug is
    capped at 48 chars, but for the longest parent (``entity_embedding_cache``)
    the derived ``ix_<parent>__<slug>_hnsw`` index name can still exceed
    Postgres' 63-char NAMEDATALEN and is silently truncated, so two
    fingerprints sharing a long common prefix could collide on the same child
    table. In practice embedder fingerprints (``model|dims``) are well under
    the budget so this does not occur. A truly collision-proof scheme (e.g. a
    hash suffix) would rename every existing partition and orphan stored
    embeddings, so it is deferred to a future data migration rather than
    changed in place here.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "_", fingerprint).strip("_").lower()
    return slug[:48]


def child_table(parent: str, fingerprint: str) -> str:
    """Return the per-fingerprint child table name for ``parent``.

    ``parent`` must be one of ``memory_embeddings``, ``entity_embeddings``,
    ``code_chunk_embeddings``, ``entity_embedding_cache``.
    """
    if parent not in _TABLE_TEMPLATES:
        raise ValueError(f"Unknown embedding parent table: {parent!r}")
    return f"{parent}__{_partition_slug(fingerprint)}"


def parse_fingerprint(fingerprint: str) -> tuple[str, int]:
    """Split ``model_id|dims`` into ``(model_id, dims)``."""
    if "|" not in fingerprint:
        raise ValueError(f"Embedder fingerprint missing '|<dims>': {fingerprint!r}")
    model_id, dims_str = fingerprint.rsplit("|", 1)
    try:
        dims = int(dims_str)
    except ValueError as exc:
        raise ValueError(f"Embedder fingerprint has non-integer dims: {fingerprint!r}") from exc
    if dims <= 0:
        raise ValueError(f"Embedder fingerprint dims must be positive: {fingerprint!r}")
    return model_id, dims
