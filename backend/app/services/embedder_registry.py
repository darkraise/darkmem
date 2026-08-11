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
import hashlib
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
    # ── The four target-new families (doc 04 §5.3), landed as templates by
    # T0.13. Three are still inert. `article_embeddings` is **no longer** —
    # T3.23 shipped its writer (`article_synthesis.write_article_embedding`)
    # and its reader (`articles_channel`), and it was the last of the four
    # *mainline* templates to gain one: `block_embeddings` waits for the EH1
    # documents horizon, `relation_embeddings` has T2.49's refresh job, and
    # `triple_embeddings` may never ship at all (its writer is deferred behind
    # a measured pg_trgm-on-fact undercount, T2.33).
    "block_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " block_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (block_id, fingerprint)"
        ")"
    ),
    # Keys on the REAL entity_relations.id — no synthetic ids — so
    # strip-before-rewrite and the self-healing delete kill the vector with
    # the relation instead of orphaning it. Carries no project predicate of
    # its own, because entity_relations is global.
    "relation_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " relation_id UUID NOT NULL REFERENCES entity_relations(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (relation_id, fingerprint)"
        ")"
    ),
    "article_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " article_id UUID NOT NULL REFERENCES knowledge_articles(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{{}}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (article_id, fingerprint)"
        ")"
    ),
    # Template ships now; the WRITER is deferred behind a measured
    # pg_trgm-on-fact undercount (T2.33) and may never ship. Deliberately NO
    # cascade: facts are invalidate-not-delete, so a cascade would destroy
    # the history the fact layer exists to keep.
    "triple_embeddings": (
        "CREATE TABLE IF NOT EXISTS {name} ("
        " fact_id UUID NOT NULL REFERENCES knowledge_triples(id),"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector({dims}) NOT NULL,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (fact_id, fingerprint)"
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
    "block_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_block_id ON {name} (block_id)",
    ],
    "relation_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_relation_id ON {name} (relation_id)",
    ],
    "article_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_article_id ON {name} (article_id)",
    ],
    "triple_embeddings": [
        "CREATE INDEX IF NOT EXISTS ix_{name}_fact_id ON {name} (fact_id)",
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

            # Reject a fingerprint that folds to an empty (or all-separator)
            # slug HERE, at registration, rather than letting the DDL run and
            # create a ``memory_embeddings__`` table nothing can address. The
            # embedders row above is rolled back with the failed transaction.
            if not slug:
                raise RuntimeError(
                    f"Malformed embedder fingerprint {info.fingerprint!r}: it folds to an "
                    f"empty partition slug, so its child tables would be unaddressable. "
                    f"Give the model an alphanumeric id."
                )

            # Refuse to share a child table with a different fingerprint that
            # folds to the same slug (e.g. 'm-a|512' vs 'm.a|512'): they'd write
            # incompatible vectors into one vector(N) column. Fail loud rather
            # than silently corrupting cosine distances. (CREATE TABLE IF NOT
            # EXISTS below would otherwise no-op onto the existing table.)
            existing = (
                await session.execute(
                    text("SELECT fingerprint FROM embedders WHERE fingerprint != :fp"),
                    {"fp": info.fingerprint},
                )
            ).scalars().all()
            for other in existing:
                if _partition_slug(other) == slug:
                    raise RuntimeError(
                        f"Partition slug collision: fingerprint {info.fingerprint!r} and "
                        f"{other!r} both map to table suffix {slug!r}. Refusing to share a "
                        f"vector column; rename the model so the fingerprints differ in more "
                        f"than separator characters."
                    )

            await _ensure_children(session, info.fingerprint, info.dims)

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

    async def reconcile(self, session: AsyncSession) -> dict[str, int]:
        """Guarantee every live fingerprint has every template's child table.

        The permanent boot-time reconciliation doc 19 §2 puts in place of the
        old one-time creation sweep. ``register`` only ever creates children
        for a fingerprint it is registering, so a fingerprint registered
        BEFORE a new template was added would be missing that parent forever.
        Looping the live rows at every startup dissolves that: adding a
        template is a template edit, and an existing deployment gains the new
        parent for its current fingerprint at next boot with no re-register
        and no migration.

        Idempotent by construction — every statement is ``IF NOT EXISTS`` — so
        a second boot is a no-op, and a restored dump missing a child table
        regrows exactly that one. It replays mechanically in the deferred .NET
        port because it is a loop over rows running parameterised plain SQL.
        """
        rows = (await session.execute(
            text("SELECT fingerprint, dims FROM embedders WHERE retired_at IS NULL")
        )).all()
        for fingerprint, dims in rows:
            await _ensure_children(session, fingerprint, dims)
        await session.commit()
        result = {"fingerprints": len(rows), "parents": len(_TABLE_TEMPLATES)}
        if rows:
            logger.info(
                "EmbedderRegistry: reconciled %d fingerprint(s) x %d parent(s)",
                result["fingerprints"], result["parents"],
            )
        return result


# Module-level singleton — shared across all sessions in the process.
embedder_registry = EmbedderRegistry()


async def _ensure_children(session: AsyncSession, fingerprint: str, dims: int) -> None:
    """Run every template's idempotent DDL for one fingerprint.

    The single place child-table DDL is emitted, shared by ``register`` and
    ``reconcile`` so the two can never drift. Child tables are named ONLY
    through ``child_table`` (invariant 2); no literal slug appears here.
    """
    for parent, ddl_template in _TABLE_TEMPLATES.items():
        child = child_table(parent, fingerprint)
        await session.execute(text(ddl_template.format(name=child, dims=dims)))
        # HNSW index: cosine ops match the application query plans. The index
        # NAME is a short hash of the child table so it cannot blow past
        # Postgres' 63-char NAMEDATALEN limit — the naive ``ix_{child}_hnsw``
        # would, for the longest parent plus a 48-char slug, silently truncate
        # and could collide across two partitions. The table name is unchanged.
        hnsw_idx = _hnsw_index_name(child)
        await session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {hnsw_idx} "
                f"ON {child} USING hnsw (embedding vector_cosine_ops) "
                f"WITH (m = 16, ef_construction = 128)"
            )
        )
        for aux_template in _AUX_INDEXES.get(parent, []):
            await session.execute(text(aux_template.format(name=child)))


def _partition_slug(fingerprint: str) -> str:
    """Convert a fingerprint to a Postgres-safe identifier suffix.

    Fingerprints look like ``qwen3-embedding:0.6b|1024``; per-fingerprint
    table names need to be ASCII identifiers, so we map non-word characters
    to ``_`` and lower-case the result.

    KNOWN LIMITATION (kept backward-compatible deliberately): the slug is
    capped at 48 chars, so two fingerprints sharing a long common prefix — or
    two models differing only by a folded separator character (``m-a|512`` vs
    ``m.a|512``) — fold to the same child-table suffix. A truly collision-proof
    scheme (e.g. a hash suffix on the TABLE name) would rename every existing
    partition and orphan stored embeddings, so it is deferred to a future data
    migration. In the meantime ``register`` rejects a fingerprint whose slug
    collides with a different already-registered one, turning silent
    vector-column corruption into a loud failure. (The derived HNSW INDEX name
    is separately hashed in ``_hnsw_index_name`` so it can't overrun NAMEDATALEN
    even for the longest parent + a full-length slug.)
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "_", fingerprint).strip("_").lower()
    return slug[:48]


def _hnsw_index_name(child_table: str) -> str:
    """Derive a NAMEDATALEN-safe HNSW index name for ``child_table``.

    ``ix_<child_table>_hnsw`` can exceed Postgres' 63-char identifier limit for
    the longest parent plus a 48-char slug, where the server silently truncates
    and two distinct partitions could collide on one index name. Anchor on a
    short blake2b digest of the full child-table name so the name stays unique
    and bounded (``ix_hnsw_`` + 16 hex chars = 24 chars) regardless of slug
    length. The table name itself is unchanged.
    """
    digest = hashlib.blake2b(child_table.encode("utf-8"), digest_size=8).hexdigest()
    return f"ix_hnsw_{digest}"


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
