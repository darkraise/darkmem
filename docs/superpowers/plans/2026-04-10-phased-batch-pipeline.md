# Phased Batch Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `process_batch` into explicit phases so entity embeddings are batched and cached (DB + in-memory TTL), reducing ~77 HTTP calls per batch of 20 memories to ~2 on cache miss and ~1 on cache hit.

**Architecture:** Introduce `embed_batch_chunked` helper for controlled concurrency. Add a new `entity_embedding_cache` table plus an in-memory dict on the pipeline instance. Rewrite `process_batch` as five sequential phases: content embedding, extraction + LLM classification, entity embedding with cache lookup, dedup, per-memory writes. Add three new feature flags for chunk size, embedding concurrency, and cache TTL.

**Tech Stack:** Python (FastAPI, SQLAlchemy, pgvector, Alembic), TypeScript (React, TanStack Router, darkraise-ui)

**Spec:** `docs/superpowers/specs/2026-04-10-phased-batch-pipeline-design.md`

---

### Task 1: Add `embed_batch_chunked` to LLMOrchestrator

**Files:**
- Modify: `backend/app/services/llm.py`
- Test: `backend/tests/unit/test_llm.py` (create if missing) or `backend/tests/test_llm.py` (existing)

- [ ] **Step 1: Write the failing test**

Check if `backend/tests/test_llm.py` exists. If it does, add to it. Otherwise check `backend/tests/unit/`. The test should look like this — adjust the import and file location to match the project layout:

```python
import pytest
from unittest.mock import AsyncMock

from app.services.llm import LLMOrchestrator


@pytest.mark.asyncio
async def test_embed_batch_chunked_preserves_order():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock(side_effect=[
        [[0.1], [0.2], [0.3]],
        [[0.4], [0.5]],
    ])

    result = await llm.embed_batch_chunked(["a", "b", "c", "d", "e"], chunk_size=3, concurrency=2)

    assert result == [[0.1], [0.2], [0.3], [0.4], [0.5]]
    assert llm.embed_batch.await_count == 2


@pytest.mark.asyncio
async def test_embed_batch_chunked_empty():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock()

    result = await llm.embed_batch_chunked([], chunk_size=10, concurrency=1)

    assert result == []
    llm.embed_batch.assert_not_called()


@pytest.mark.asyncio
async def test_embed_batch_chunked_single_chunk():
    llm = LLMOrchestrator.__new__(LLMOrchestrator)
    llm.embed_batch = AsyncMock(return_value=[[0.1], [0.2]])

    result = await llm.embed_batch_chunked(["a", "b"], chunk_size=5, concurrency=1)

    assert result == [[0.1], [0.2]]
    llm.embed_batch.assert_awaited_once_with(["a", "b"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/ -k "embed_batch_chunked" -v 2>&1 | tail -20`

Expected: FAIL with `AttributeError: 'LLMOrchestrator' object has no attribute 'embed_batch_chunked'`.

- [ ] **Step 3: Implement embed_batch_chunked**

In `backend/app/services/llm.py`, find the `embed_batch` method (line 27). After it (before `chat_completion`), add:

```python
    async def embed_batch_chunked(
        self,
        texts: list[str],
        chunk_size: int,
        concurrency: int,
    ) -> list[list[float]]:
        """Embed many texts via multiple concurrent embed_batch calls.

        Preserves input order. Any chunk failure propagates.
        """
        if not texts:
            return []

        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        semaphore = asyncio.Semaphore(concurrency)

        async def run_chunk(chunk: list[str]) -> list[list[float]]:
            async with semaphore:
                return await self.embed_batch(chunk)

        results = await asyncio.gather(*[run_chunk(c) for c in chunks])
        return [vec for chunk_result in results for vec in chunk_result]
```

Verify `import asyncio` is already at the top of the file (it should be, since other methods use it).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/ -k "embed_batch_chunked" -v 2>&1 | tail -20`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm.py backend/tests/
git commit -m "feat(llm): add embed_batch_chunked with concurrent chunking"
```

---

### Task 2: Create migration for cache table and fingerprint columns

**Files:**
- Create: `backend/migrations/versions/0002_entity_embedding_cache.py`

- [ ] **Step 1: Create migration file**

Create `backend/migrations/versions/0002_entity_embedding_cache.py` with this content:

```python
"""entity embedding cache and model fingerprint columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-10

Adds:
  - entity_embedding_cache table (name_lower + model_fingerprint composite PK)
  - model_fingerprint column on memory_embeddings, code_chunk_embeddings, entities
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Entity embedding cache table (persistent layer)
    op.execute("""
        CREATE TABLE entity_embedding_cache (
            name_lower VARCHAR(255) NOT NULL,
            model_fingerprint VARCHAR(100) NOT NULL,
            embedding vector(1024) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            hit_count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (name_lower, model_fingerprint)
        )
    """)
    op.execute("CREATE INDEX ix_entity_embedding_cache_last_used ON entity_embedding_cache(last_used_at)")

    # Model fingerprint columns on existing embedding-carrying tables
    op.add_column('memory_embeddings', sa.Column('model_fingerprint', sa.String(100), nullable=True))
    op.add_column('code_chunk_embeddings', sa.Column('model_fingerprint', sa.String(100), nullable=True))
    op.execute("ALTER TABLE entities ADD COLUMN model_fingerprint VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE entities DROP COLUMN IF EXISTS model_fingerprint")
    op.drop_column('code_chunk_embeddings', 'model_fingerprint')
    op.drop_column('memory_embeddings', 'model_fingerprint')
    op.execute("DROP INDEX IF EXISTS ix_entity_embedding_cache_last_used")
    op.execute("DROP TABLE IF EXISTS entity_embedding_cache")
```

- [ ] **Step 2: Run the migration**

Run: `cd backend && alembic upgrade head 2>&1 | tail -20`

Expected: `INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, entity embedding cache and model fingerprint columns`.

- [ ] **Step 3: Verify schema**

Run: `cd backend && python -c "
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from sqlalchemy import text
from app.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        cols = (await s.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name = 'entity_embedding_cache' ORDER BY ordinal_position\"))).scalars().all()
        print('entity_embedding_cache:', cols)
        for table in ('memory_embeddings', 'code_chunk_embeddings', 'entities'):
            has_fp = (await s.execute(text(f\"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'model_fingerprint'\"))).scalar_one_or_none()
            print(f'{table}.model_fingerprint:', 'present' if has_fp else 'MISSING')
asyncio.run(check())
" 2>&1`

Expected: cache table has columns `['name_lower', 'model_fingerprint', 'embedding', 'created_at', 'last_used_at', 'hit_count']` and all three existing tables show `present`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0002_entity_embedding_cache.py
git commit -m "feat(db): add entity_embedding_cache table and model fingerprint columns"
```

---

### Task 3: Add EntityEmbeddingCache ORM model and fingerprint fields

**Files:**
- Modify: `backend/app/models/embedding.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Add EntityEmbeddingCache model and fingerprint columns**

Replace the contents of `backend/app/models/embedding.py` with:

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import settings
from .base import Base

_DIM = settings.embedding_dimensions


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    embedding = mapped_column(Vector(_DIM))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    model_fingerprint: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CodeChunkEmbedding(Base):
    __tablename__ = "code_chunk_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str | None] = mapped_column(String(50))
    symbol_name: Mapped[str | None] = mapped_column(String(500))
    chunk_content: Mapped[str | None] = mapped_column(Text)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector(_DIM))
    model_fingerprint: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityEmbeddingCache(Base):
    __tablename__ = "entity_embedding_cache"

    name_lower: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_fingerprint: Mapped[str] = mapped_column(String(100), primary_key=True)
    embedding = mapped_column(Vector(_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hit_count: Mapped[int] = mapped_column(Integer, default=1)
```

- [ ] **Step 2: Export the new model**

In `backend/app/models/__init__.py`, add `EntityEmbeddingCache` to the import from `.embedding` and to `__all__`:

Find:
```python
from .embedding import CodeChunkEmbedding, MemoryEmbedding
```
Change to:
```python
from .embedding import CodeChunkEmbedding, EntityEmbeddingCache, MemoryEmbedding
```

Find the `__all__` list and add `"EntityEmbeddingCache"` alongside the other embedding names (e.g., right after `"CodeChunkEmbedding"`).

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.models import EntityEmbeddingCache, MemoryEmbedding, CodeChunkEmbedding; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/embedding.py backend/app/models/__init__.py
git commit -m "feat(models): add EntityEmbeddingCache model and fingerprint fields"
```

---

### Task 4: Add repository methods for cache and entity embedding with fingerprint

**Files:**
- Modify: `backend/app/repositories/graph.py`

- [ ] **Step 1: Add cache lookup method**

In `backend/app/repositories/graph.py`, after the existing `upsert_entity_embedding` method (around line 36), add:

```python
    async def get_cached_entity_embeddings(
        self,
        name_lowers: list[str],
        model_fingerprint: str,
    ) -> dict[str, list[float]]:
        """Return {name_lower: embedding} for entries matching the fingerprint.

        Names not present in the cache (for this fingerprint) are omitted.
        """
        if not name_lowers:
            return {}
        result = await self.session.execute(
            text("""
                SELECT name_lower, embedding::text AS embedding_text
                FROM entity_embedding_cache
                WHERE name_lower = ANY(:names) AND model_fingerprint = :fp
            """),
            {"names": name_lowers, "fp": model_fingerprint},
        )
        out: dict[str, list[float]] = {}
        for row in result.mappings().all():
            text_vec = row["embedding_text"]
            out[row["name_lower"]] = [float(x) for x in text_vec.strip("[]").split(",")]
        return out

    async def upsert_entity_embeddings_cache(
        self,
        name_to_embedding: dict[str, list[float]],
        model_fingerprint: str,
    ) -> None:
        """Upsert cache entries. ON CONFLICT updates last_used_at and hit_count."""
        if not name_to_embedding:
            return
        for name_lower, embedding in name_to_embedding.items():
            await self.session.execute(
                text("""
                    INSERT INTO entity_embedding_cache
                        (name_lower, model_fingerprint, embedding, created_at, last_used_at, hit_count)
                    VALUES
                        (:name, :fp, CAST(:vec AS vector), NOW(), NOW(), 1)
                    ON CONFLICT (name_lower, model_fingerprint) DO UPDATE SET
                        last_used_at = NOW(),
                        hit_count = entity_embedding_cache.hit_count + 1
                """),
                {"name": name_lower, "fp": model_fingerprint, "vec": str(embedding)},
            )
```

- [ ] **Step 2: Update `upsert_entity_embedding` to include fingerprint**

Replace the existing `upsert_entity_embedding` method (around line 32-36) with:

```python
    async def upsert_entity_embedding(self, entity_id: str, embedding: list[float], model_fingerprint: str | None = None):
        await self.session.execute(
            text("""
                UPDATE entities
                SET embedding = CAST(:vec AS vector),
                    model_fingerprint = :fp
                WHERE id = CAST(:id AS uuid)
            """),
            {"id": entity_id, "vec": str(embedding), "fp": model_fingerprint},
        )
```

The `model_fingerprint` is defaulted to `None` to keep any unlikely existing callers working without a code change. New callers in the pipeline will pass it explicitly.

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.repositories.graph import PostgresGraphRepository; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/graph.py
git commit -m "feat(graph): add entity embedding cache repo methods and fingerprint param"
```

---

### Task 5: Add three new feature flags

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/routes/config.py`

- [ ] **Step 1: Add defaults in config.py**

In `backend/app/config.py`, the existing `FEATURE_FLAGS_DEFAULTS` dict looks like:

```python
FEATURE_FLAGS_DEFAULTS: dict[str, object] = {
    "llm_enrichment_enabled": False,
    "hybrid_search_enabled": True,
    "reranker_enabled": False,
    "pipeline_concurrency": 5,
    "classification_areas": ["general", "technical", "debugging", "infrastructure"],
    "classification_mode": "simple",
}
```

Add three new entries at the end:

```python
FEATURE_FLAGS_DEFAULTS: dict[str, object] = {
    "llm_enrichment_enabled": False,
    "hybrid_search_enabled": True,
    "reranker_enabled": False,
    "pipeline_concurrency": 5,
    "classification_areas": ["general", "technical", "debugging", "infrastructure"],
    "classification_mode": "simple",
    "embedding_batch_size": 20,
    "embedding_concurrency": 1,
    "entity_cache_ttl_minutes": 60,
}
```

- [ ] **Step 2: Update API schemas and validation**

In `backend/app/api/routes/config.py`, update `FeatureFlagsResponse`:

```python
class FeatureFlagsResponse(BaseModel):
    llm_enrichment_enabled: bool
    hybrid_search_enabled: bool
    reranker_enabled: bool
    pipeline_concurrency: int
    classification_areas: list[str]
    classification_mode: str
    embedding_batch_size: int
    embedding_concurrency: int
    entity_cache_ttl_minutes: int
```

Update `FeatureFlagsUpdate`:

```python
class FeatureFlagsUpdate(BaseModel):
    llm_enrichment_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = None
    classification_areas: list[str] | None = None
    classification_mode: str | None = None
    embedding_batch_size: int | None = None
    embedding_concurrency: int | None = None
    entity_cache_ttl_minutes: int | None = None
```

In the `update_feature_flags` handler, after the existing `classification_mode` validation block (it was added in the previous feature), add:

```python
    if "embedding_batch_size" in updates:
        v = updates["embedding_batch_size"]
        if not isinstance(v, int) or v < 1 or v > 200:
            raise HTTPException(status_code=422, detail="embedding_batch_size must be between 1 and 200")

    if "embedding_concurrency" in updates:
        v = updates["embedding_concurrency"]
        if not isinstance(v, int) or v < 1 or v > 10:
            raise HTTPException(status_code=422, detail="embedding_concurrency must be between 1 and 10")

    if "entity_cache_ttl_minutes" in updates:
        v = updates["entity_cache_ttl_minutes"]
        if not isinstance(v, int) or v < 1 or v > 1440:
            raise HTTPException(status_code=422, detail="entity_cache_ttl_minutes must be between 1 and 1440")
```

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.config import FEATURE_FLAGS_DEFAULTS; print({k: v for k, v in FEATURE_FLAGS_DEFAULTS.items() if 'embedding' in k or 'entity_cache' in k})"`

Expected: `{'embedding_batch_size': 20, 'embedding_concurrency': 1, 'entity_cache_ttl_minutes': 60}`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/app/api/routes/config.py
git commit -m "feat(config): add embedding_batch_size, embedding_concurrency, entity_cache_ttl_minutes flags"
```

---

### Task 6: Add pipeline cache state and helper methods

**Files:**
- Modify: `backend/app/services/pipeline.py`

- [ ] **Step 1: Add instance state in `__init__`**

In `backend/app/services/pipeline.py`, find `ProcessingPipeline.__init__` (around line 33-39). Add cache state at the end:

```python
    def __init__(self, llm: LLMOrchestrator, session_factory, embedding_dims: int, broadcast=None):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.classification = ClassificationService(llm)
        self.session_factory = session_factory
        self.embedding_dims = embedding_dims
        self._broadcast = broadcast
        self.embedding_fingerprint = f"{llm.config['embedding'].model}|{embedding_dims}"
        self._entity_cache: dict[tuple[str, str], tuple[list[float], float]] = {}
        self._entity_cache_lock = asyncio.Lock()
```

Key is `(name_lower, fingerprint)`, value is `(embedding, cached_at_monotonic_seconds)`.

- [ ] **Step 2: Add cache helper methods**

Add these two methods to `ProcessingPipeline` (place them near `__init__`, before `process_memory`):

```python
    async def _lookup_entity_embeddings(
        self,
        name_lowers: list[str],
        ttl_seconds: float,
        use_memory_cache: bool,
    ) -> tuple[dict[str, list[float]], list[str]]:
        """Return (hits, misses). Hits map name_lower to embedding.
        Misses are names needing fresh embedding."""
        import time as _time

        hits: dict[str, list[float]] = {}
        still_missing: list[str] = []
        now = _time.monotonic()
        fp = self.embedding_fingerprint

        if use_memory_cache:
            async with self._entity_cache_lock:
                for name in name_lowers:
                    entry = self._entity_cache.get((name, fp))
                    if entry is not None:
                        emb, cached_at = entry
                        if now - cached_at <= ttl_seconds:
                            hits[name] = emb
                            continue
                        else:
                            del self._entity_cache[(name, fp)]
                    still_missing.append(name)
        else:
            still_missing = list(name_lowers)

        if still_missing:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                db_hits = await repo.get_cached_entity_embeddings(still_missing, fp)
            if db_hits:
                if use_memory_cache:
                    async with self._entity_cache_lock:
                        for name, emb in db_hits.items():
                            self._entity_cache[(name, fp)] = (emb, now)
                hits.update(db_hits)
                still_missing = [n for n in still_missing if n not in db_hits]

        return hits, still_missing

    async def _store_entity_embeddings(
        self,
        name_to_embedding: dict[str, list[float]],
        use_memory_cache: bool,
    ) -> None:
        """Write new embeddings to DB cache and (optionally) in-memory cache."""
        import time as _time

        if not name_to_embedding:
            return
        fp = self.embedding_fingerprint

        async with self.session_factory() as session:
            repo = PostgresGraphRepository(session)
            await repo.upsert_entity_embeddings_cache(name_to_embedding, fp)
            await session.commit()

        if use_memory_cache:
            now = _time.monotonic()
            async with self._entity_cache_lock:
                for name, emb in name_to_embedding.items():
                    self._entity_cache[(name, fp)] = (emb, now)
```

- [ ] **Step 3: Verify imports work**

Run: `cd backend && python -c "from app.services.pipeline import ProcessingPipeline; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/pipeline.py
git commit -m "feat(pipeline): add entity embedding cache state and lookup/store helpers"
```

---

### Task 7: Rewrite process_batch as phased implementation

This is the largest task. It rewrites `process_batch` into the five-phase flow and refactors `process_memory` into a thin wrapper. Take it in sub-steps.

**Files:**
- Modify: `backend/app/services/pipeline.py`

- [ ] **Step 1: Add `_write_memory` method**

In `backend/app/services/pipeline.py`, add a new method to `ProcessingPipeline` that handles the per-memory write phase. Place it after the `_store_entity_embeddings` method from Task 6.

This method is the refactored tail of the current `process_memory` — it takes pre-computed vector, extraction, classification, entity embeddings, and canonical_map, and does the DB writes plus crossrefs plus broadcast. It does NOT call `embed`, `extract`, or `classify`:

```python
    async def _write_memory(
        self,
        entry: dict,
        vector: list[float] | None,
        extraction: dict | Exception,
        llm_classification: dict | None,
        name_to_embedding: dict[str, list[float]],
        canonical_map: dict[str, str],
        flags: dict,
    ) -> dict:
        memory_id = entry["memory_id"]
        content = entry["content"]
        source = entry.get("source", "mcp")
        tags = entry.get("tags", [])
        memory_type = entry.get("memory_type")
        created_at = entry.get("created_at", "")

        areas = flags.get("classification_areas", ["general"])
        mode = flags.get("classification_mode", "simple")

        status = {
            "memory_id": str(memory_id),
            "embed": "ok" if vector is not None else "error",
            "extract": "pending",
            "vector": "pending",
            "graph": "pending",
            "entities_count": 0,
            "relations_count": 0,
            "error": None,
        }

        if isinstance(extraction, Exception):
            status["extract"] = "error"
            status["error"] = f"Extraction failed: {extraction}"
            extraction = None
        elif isinstance(extraction, dict):
            status["extract"] = "ok"
            status["entities_count"] = len(extraction.get("entities", []))
            status["relations_count"] = len(extraction.get("relationships", []))
            if extraction.get("_error"):
                status["extract"] = "partial"
                status["error"] = status["error"] or f"Extraction degraded: {extraction['_error']}"

            # Apply canonical_map to entity names and relationship endpoints
            for entity in extraction.get("entities", []):
                low = entity["name"].lower()
                if low in canonical_map:
                    entity["name"] = canonical_map[low]
            for rel in extraction.get("relationships", []):
                src_low = rel.get("source", "").lower()
                tgt_low = rel.get("target", "").lower()
                if src_low in canonical_map:
                    rel["source"] = canonical_map[src_low]
                if tgt_low in canonical_map:
                    rel["target"] = canonical_map[tgt_low]
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"
            extraction = None

        async with self.session_factory() as session:
            vector_repo = PostgresVectorRepository(session, self.embedding_dims)
            graph_repo = PostgresGraphRepository(session)

            if status["embed"] == "ok":
                regex_result = regex_classify(content, enabled_areas=areas, mode=mode)

                try:
                    async with session.begin_nested():
                        payload = {
                            "memory_id": str(memory_id), "content": content,
                            "source": source, "tags": tags,
                            "memory_type": memory_type or (extraction.get("memory_type") if isinstance(extraction, dict) else None),
                            "created_at": created_at,
                            "classified_type": regex_result.get("hall", ""),
                            "classified_confidence": regex_result.get("confidence", 0.0),
                        }
                        if llm_classification:
                            payload["llm_classified_type"] = llm_classification.get("hall", "")
                            payload["llm_summary"] = llm_classification.get("summary", "")
                            payload["llm_emotions"] = llm_classification.get("emotions", [])
                            payload["llm_flags"] = llm_classification.get("flags", [])

                        await vector_repo.upsert(
                            memory_id=memory_id, vector=vector, payload=payload,
                        )
                        status["vector"] = "ok"

                        from sqlalchemy import select as sa_select
                        from app.models.memory import Memory
                        mem_result = await session.execute(
                            sa_select(Memory).where(Memory.id == memory_id)
                        )
                        mem_record = mem_result.scalar_one_or_none()
                        if mem_record:
                            mem_record.classified_type = regex_result.get("hall") or None
                            mem_record.classified_confidence = regex_result.get("confidence")
                            if llm_classification:
                                mem_record.llm_classified_type = llm_classification.get("hall") or None
                                mem_record.llm_summary = llm_classification.get("summary") or None
                                mem_record.llm_emotions = llm_classification.get("emotions") or None
                                mem_record.llm_flags = llm_classification.get("flags") or None

                        if status["extract"] in ("ok", "partial") and isinstance(extraction, dict):
                            for entity in extraction.get("entities", []):
                                created = await graph_repo.create_entity(
                                    name=entity["name"], entity_type=entity["type"],
                                    properties=entity.get("properties", {}), memory_id=memory_id,
                                )
                                emb = name_to_embedding.get(entity["name"].lower())
                                if emb and created:
                                    await graph_repo.upsert_entity_embedding(
                                        created["id"], emb, model_fingerprint=self.embedding_fingerprint,
                                    )
                            for rel in extraction.get("relationships", []):
                                await graph_repo.create_relationship(
                                    source_name=rel["source"], target_name=rel["target"],
                                    rel_type=rel["type"], properties=rel.get("properties", {}),
                                    weight=rel.get("weight", 0.5), memory_id=memory_id,
                                )
                            status["graph"] = "ok"
                        else:
                            status["graph"] = "skipped"

                except Exception as e:
                    status["vector"] = "error"
                    status["graph"] = "error"
                    status["error"] = status["error"] or f"Pipeline DB write failed: {e}"
                    logger.error(f"Pipeline DB write failed for {memory_id}: {e}")
            else:
                status["vector"] = "skipped"
                status["graph"] = "skipped"

            await session.commit()

        if status["vector"] == "ok":
            try:
                async with self.session_factory() as xref_session:
                    xref_repo = PostgresVectorRepository(xref_session, self.embedding_dims)
                    similar = await xref_repo.find_similar_memories(memory_id, top_k=5, min_score=0.4)
                    await xref_repo.store_crossrefs(memory_id, similar)
                    await xref_session.commit()
            except Exception as e:
                logger.warning(f"Crossref computation failed for {memory_id}: {e}")

        steps = [status["embed"], status["extract"], status["vector"], status["graph"]]
        active_steps = [s for s in steps if s != "skipped" and s != "pending"]
        if all(s == "ok" for s in active_steps):
            event_type = "pipeline.completed"
        elif any(s == "ok" for s in active_steps):
            event_type = "pipeline.partial"
        else:
            event_type = "pipeline.failed"

        if self._broadcast:
            try:
                await self._broadcast(event_type, status)
            except Exception as e:
                logger.warning(f"Pipeline broadcast failed: {e}")

        return status
```

- [ ] **Step 2: Rewrite `process_batch` as phased flow**

Find the existing `process_batch` method (around line 250-290). Replace it entirely with:

```python
    async def process_batch(self, entries: list[dict]) -> list[dict]:
        """Process multiple memories through phased pipeline.

        Phases:
          1. Content embedding (chunked, concurrent)
          2. Extraction and LLM classification (per-memory, concurrent)
          3. Entity embedding with cache
          4. Dedup lookup (per unique name)
          5. Per-memory writes (concurrent)
        """
        flags = await _get_feature_flags(self.session_factory)
        pipeline_concurrency = flags.get("pipeline_concurrency", 5)
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)
        ttl_seconds = flags.get("entity_cache_ttl_minutes", 60) * 60
        llm_enrichment = flags.get("llm_enrichment_enabled", False)

        logger.info(
            "Starting batch pipeline: %d memories, pipeline_concurrency=%d, embed_chunk_size=%d, embed_concurrency=%d",
            len(entries), pipeline_concurrency, embed_chunk_size, embed_concurrency,
        )

        # Phase 1: Content embedding
        contents = [e["content"] for e in entries]
        try:
            vectors = await self.llm.embed_batch_chunked(contents, embed_chunk_size, embed_concurrency)
            logger.info("Phase 1 complete: embedded %d contents", len(vectors))
        except Exception as e:
            logger.error("Phase 1 content embedding failed: %s: %s", type(e).__name__, e)
            vectors = [None] * len(entries)

        # Phase 2: Extraction and LLM classification
        ext_prompt = prompt.get("extraction")
        cls_prompt = prompt.get("classification") if llm_enrichment else ""
        semaphore = asyncio.Semaphore(pipeline_concurrency)

        async def run_extract(content: str):
            async with semaphore:
                try:
                    return await self.extraction.extract(content, system_prompt=ext_prompt)
                except Exception as exc:
                    return exc

        async def run_classify(content: str):
            async with semaphore:
                try:
                    areas = flags.get("classification_areas", ["general"])
                    mode = flags.get("classification_mode", "simple")
                    return await self.classification.classify(content, areas, cls_prompt, mode=mode)
                except Exception as exc:
                    logger.warning("LLM classification failed: %s", exc)
                    return None

        extract_tasks = [run_extract(e["content"]) for e in entries]
        classify_tasks = [run_classify(e["content"]) for e in entries] if llm_enrichment else None

        extractions = await asyncio.gather(*extract_tasks)
        classifications: list[dict | None] = (
            await asyncio.gather(*classify_tasks) if classify_tasks else [None] * len(entries)
        )
        logger.info("Phase 2 complete: extractions=%d, classifications=%s", len(extractions), "on" if llm_enrichment else "off")

        # Phase 3: Entity embedding with cache
        unique_names: set[str] = set()
        for ext in extractions:
            if isinstance(ext, dict):
                for entity in ext.get("entities", []):
                    name = entity.get("name")
                    if name:
                        unique_names.add(name.lower())

        unique_names_list = sorted(unique_names)
        name_to_embedding: dict[str, list[float]] = {}

        if unique_names_list:
            hits, misses = await self._lookup_entity_embeddings(
                unique_names_list, ttl_seconds, use_memory_cache=True,
            )
            name_to_embedding.update(hits)
            logger.info("Phase 3 cache lookup: %d hits, %d misses", len(hits), len(misses))

            if misses:
                try:
                    new_embeddings_list = await self.llm.embed_batch_chunked(
                        misses, embed_chunk_size, embed_concurrency,
                    )
                    new_map = dict(zip(misses, new_embeddings_list))
                    await self._store_entity_embeddings(new_map, use_memory_cache=True)
                    name_to_embedding.update(new_map)
                    logger.info("Phase 3 complete: embedded %d new entity names", len(new_map))
                except Exception as e:
                    logger.warning("Phase 3 entity embedding failed: %s: %s", type(e).__name__, e)
        else:
            logger.info("Phase 3 skipped: no entities to embed")

        # Phase 4: Dedup lookup (one call per unique name)
        canonical_map: dict[str, str] = {}
        if name_to_embedding:
            async with self.session_factory() as dedup_session:
                dedup_repo = PostgresGraphRepository(dedup_session)
                for lower_name, emb in name_to_embedding.items():
                    try:
                        match = await dedup_repo.find_similar_entity(emb, threshold=0.85)
                        if match and match["name"].lower() != lower_name:
                            canonical_map[lower_name] = match["name"]
                    except Exception as e:
                        logger.warning("Dedup lookup failed for %s: %s", lower_name, e)
            logger.info("Phase 4 complete: %d canonical remappings", len(canonical_map))

        # Phase 5: Per-memory writes
        async def run_write(entry: dict, vector: list[float] | None, extraction, classification):
            async with semaphore:
                return await self._write_memory(
                    entry, vector, extraction, classification,
                    name_to_embedding, canonical_map, flags,
                )

        results = await asyncio.gather(
            *[
                run_write(e, v, ext, cls)
                for e, v, ext, cls in zip(entries, vectors, extractions, classifications)
            ],
            return_exceptions=True,
        )
        logger.info("Phase 5 complete: wrote %d memories", len(results))

        # Normalize any exception returns into error dicts
        normalized: list[dict] = []
        for entry, result in zip(entries, results):
            if isinstance(result, Exception):
                logger.error("Memory %s write failed: %s", entry.get("memory_id"), result)
                normalized.append({
                    "memory_id": str(entry.get("memory_id")),
                    "embed": "unknown", "extract": "unknown",
                    "vector": "error", "graph": "error",
                    "entities_count": 0, "relations_count": 0,
                    "error": str(result),
                })
            else:
                normalized.append(result)
        return normalized
```

- [ ] **Step 3: Rewrite `process_memory` as a thin wrapper**

The current `process_memory` method (around line 41-244) should be replaced with a thin wrapper that delegates to `process_batch`. This preserves any remaining external callers that take the single-memory path:

```python
    async def process_memory(
        self,
        memory_id,
        content: str,
        source: str,
        tags: list[str],
        memory_type: str | None,
        created_at: str,
        vector: list[float] | None = None,
        flags: dict | None = None,
    ) -> dict:
        """Process a single memory. Delegates to process_batch for consistent phasing."""
        entry = {
            "memory_id": memory_id,
            "content": content,
            "source": source,
            "tags": tags,
            "memory_type": memory_type,
            "created_at": created_at,
        }
        results = await self.process_batch([entry])
        return results[0]
```

Note: The `vector` parameter is accepted but ignored in the wrapper — `process_batch` will recompute the content embedding. If the caller had a pre-computed vector, it would be redundant work; but no existing callers use this path with a vector, so it's acceptable.

Delete everything else that was in the old `process_memory` body. The old implementation is replaced entirely by the Phase 5 `_write_memory` method from Step 1 plus the new `process_batch` from Step 2.

- [ ] **Step 4: Verify imports and basic sanity**

Run: `cd backend && python -c "
from app.services.pipeline import ProcessingPipeline
import inspect
print('process_batch signature:', inspect.signature(ProcessingPipeline.process_batch))
print('process_memory signature:', inspect.signature(ProcessingPipeline.process_memory))
print('_write_memory present:', hasattr(ProcessingPipeline, '_write_memory'))
print('_lookup_entity_embeddings present:', hasattr(ProcessingPipeline, '_lookup_entity_embeddings'))
"`

Expected: all methods present, signatures match.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py
git commit -m "feat(pipeline): rewrite process_batch as phased pipeline with entity cache"
```

---

### Task 8: Switch code_pipeline to `embed_batch_chunked`

**Files:**
- Modify: `backend/app/services/code_pipeline.py`

- [ ] **Step 1: Read flags from the existing session**

`CodePipeline` has `self.session` (an `AsyncSession`) but no `session_factory`. Read the feature flags directly via the existing session before the embed loop, so the chunked helper can use the same flags as the memory pipeline.

In `backend/app/services/code_pipeline.py`, find the embed phase (around line 920-937). The relevant section looks like:

```python
        embed_results: dict[str, list[list[float]]] = {}

        async def _embed_one(fp: str, pr) -> None:
            texts = [c["content"][:2000] for c in pr.chunks]
            async with sem:
                try:
                    vectors = await self.llm.embed_batch(texts)
                    embed_results[fp] = vectors
                except Exception as exc:
                    logger.warning("Batch embedding failed for %s: %s", fp, exc)
                    self._stats["errors"].append(f"embed:{fp}:{exc}")

        await asyncio.gather(*[_embed_one(fp, pr) for fp, pr in file_items])
```

Just before this block (after `embed_results` is initialized and before `_embed_one` is defined), add a flag read:

```python
        from sqlalchemy import select as _sa_select
        from app.config import FEATURE_FLAGS_DEFAULTS
        from app.models.config import Config as _ConfigModel
        _flags_row = (await self.session.execute(
            _sa_select(_ConfigModel).where(_ConfigModel.key == "feature_flags")
        )).scalar_one_or_none()
        _merged_flags = dict(FEATURE_FLAGS_DEFAULTS)
        if _flags_row:
            _merged_flags.update(_flags_row.value)
        _embed_chunk_size = _merged_flags.get("embedding_batch_size", 20)
        _embed_concurrency = _merged_flags.get("embedding_concurrency", 1)
```

Then change the `_embed_one` body to use the chunked helper:

```python
        async def _embed_one(fp: str, pr) -> None:
            texts = [c["content"][:2000] for c in pr.chunks]
            async with sem:
                try:
                    vectors = await self.llm.embed_batch_chunked(texts, _embed_chunk_size, _embed_concurrency)
                    embed_results[fp] = vectors
                except Exception as exc:
                    logger.warning("Batch embedding failed for %s: %s", fp, exc)
                    self._stats["errors"].append(f"embed:{fp}:{exc}")
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && python -c "from app.services.code_pipeline import CodePipeline; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/code_pipeline.py
git commit -m "feat(code): use embed_batch_chunked for code chunk embedding"
```

---

### Task 9: Update frontend FeatureFlags type

**Files:**
- Modify: `frontend/src/hooks/api/use-config-api.ts`

- [ ] **Step 1: Add three new fields**

In `frontend/src/hooks/api/use-config-api.ts`, find the `FeatureFlags` interface (around line 39-46). Add three fields at the end:

```typescript
export interface FeatureFlags {
  llm_enrichment_enabled: boolean;
  hybrid_search_enabled: boolean;
  reranker_enabled: boolean;
  pipeline_concurrency: number;
  classification_areas: string[];
  classification_mode: "simple" | "expanded";
  embedding_batch_size: number;
  embedding_concurrency: number;
  entity_cache_ttl_minutes: number;
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`

Expected: No new errors related to this change.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-config-api.ts
git commit -m "feat(ui): add embedding and cache flags to FeatureFlags type"
```

---

### Task 10: Add "Embedding Pipeline" inputs to Settings UI

**Files:**
- Modify: `frontend/src/routes/_authenticated/settings.tsx`

- [ ] **Step 1: Add three number inputs to FeatureFlagsCard**

In `frontend/src/routes/_authenticated/settings.tsx`, find the `FeatureFlagsCard` function. It currently has a "Pipeline Concurrency" input (around line 227-253) that uses an `Input type="number"` next to a label inside a `flex items-center justify-between` row with a `border-t border-border` divider on top.

After that Pipeline Concurrency row, add three more rows using the same pattern. Place them before the closing `</CardContent>` of `FeatureFlagsCard`:

```tsx
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Embedding Batch Size</Label>
            <p className="text-muted-foreground text-xs">Texts per embedding HTTP call. Lower if you hit token limits.</p>
          </div>
          <Input
            type="number"
            min={1}
            max={200}
            value={flags.embedding_batch_size}
            onChange={(e) => {
              const v = Math.max(1, Math.min(200, Number(e.target.value) || 20))
              updateFlags.mutate(
                { embedding_batch_size: v },
                {
                  onSuccess: () => toast.success(`Embedding batch size set to ${v}`),
                  onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                },
              )
            }}
            className="w-16 h-8 text-sm text-center"
            disabled={updateFlags.isPending}
          />
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Embedding Concurrency</Label>
            <p className="text-muted-foreground text-xs">Parallel embedding requests. Set to 1 for Ollama with concurrent=1.</p>
          </div>
          <Input
            type="number"
            min={1}
            max={10}
            value={flags.embedding_concurrency}
            onChange={(e) => {
              const v = Math.max(1, Math.min(10, Number(e.target.value) || 1))
              updateFlags.mutate(
                { embedding_concurrency: v },
                {
                  onSuccess: () => toast.success(`Embedding concurrency set to ${v}`),
                  onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                },
              )
            }}
            className="w-16 h-8 text-sm text-center"
            disabled={updateFlags.isPending}
          />
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Entity Cache TTL (minutes)</Label>
            <p className="text-muted-foreground text-xs">How long entity embeddings stay in memory before rechecking the database.</p>
          </div>
          <Input
            type="number"
            min={1}
            max={1440}
            value={flags.entity_cache_ttl_minutes}
            onChange={(e) => {
              const v = Math.max(1, Math.min(1440, Number(e.target.value) || 60))
              updateFlags.mutate(
                { entity_cache_ttl_minutes: v },
                {
                  onSuccess: () => toast.success(`Entity cache TTL set to ${v} minutes`),
                  onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                },
              )
            }}
            className="w-16 h-8 text-sm text-center"
            disabled={updateFlags.isPending}
          />
        </div>
```

- [ ] **Step 2: Type-check and build**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -10`

Expected: Clean.

Run: `cd frontend && npx vite build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_authenticated/settings.tsx
git commit -m "feat(ui): add embedding pipeline controls to settings"
```

---

### Task 11: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Run existing tests**

Run: `cd backend && python -m pytest tests/unit/test_algorithms.py tests/ -k "embed_batch_chunked" -v 2>&1 | tail -40`

Expected: All tests pass (classification mode tests + new embed_batch_chunked tests).

- [ ] **Step 2: Restart the backend server**

The user needs to restart the backend for the new flags and migration to take effect. Ask them to do this if not already running the latest code.

- [ ] **Step 3: Clean the test database**

Run: `cd backend && python -c "
import asyncio
from sqlalchemy import text
from app.database import engine

async def clean():
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE memories, tags, memory_tags, memory_embeddings, entities, entity_relations, knowledge_triples, audit_log, token_blocklist, entity_embedding_cache CASCADE'))
    print('DB cleaned')

asyncio.run(clean())
" 2>&1`

Expected: `DB cleaned`.

- [ ] **Step 4: Run batch ingest script**

Run: `cd backend && python scripts/test_batch_100.py 2>&1 | tail -20`

Expected: 90 memories ingested across 5 batches, no extraction errors.

- [ ] **Step 5: Verify cache was populated and HTTP call count dropped**

Run: `cd backend && python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def check():
    async with async_session_factory() as s:
        cache_count = (await s.execute(text('SELECT count(*) FROM entity_embedding_cache'))).scalar()
        total_hits = (await s.execute(text('SELECT SUM(hit_count) FROM entity_embedding_cache'))).scalar()
        distinct_fingerprints = (await s.execute(text('SELECT DISTINCT model_fingerprint FROM entity_embedding_cache'))).fetchall()
        print(f'Cache entries: {cache_count}')
        print(f'Total cache hits (incl. insert): {total_hits}')
        print(f'Fingerprints present: {[r[0] for r in distinct_fingerprints]}')

        fp_count = (await s.execute(text('SELECT count(*) FROM entities WHERE model_fingerprint IS NOT NULL'))).scalar()
        total = (await s.execute(text('SELECT count(*) FROM entities'))).scalar()
        print(f'Entities with fingerprint: {fp_count}/{total}')

asyncio.run(check())
" 2>&1`

Expected: Cache has entries, all entities have a fingerprint set, only one fingerprint string present.

- [ ] **Step 6: Verify reduced HTTP call pattern in server logs**

Check the backend server logs (or the terminal where it runs) for the batch. Should see:
- "Starting batch pipeline: 20 memories"
- "Phase 1 complete: embedded 20 contents"
- "Phase 2 complete: extractions=20"
- "Phase 3 cache lookup: X hits, Y misses"
- "Phase 3 complete: embedded Y new entity names" (for first batch; later batches should have more hits, fewer misses)
- "Phase 5 complete: wrote 20 memories"

Count HTTP `/embeddings` POSTs per batch. Expected: at most 2 per batch on cold cache (content + entities), dropping toward 1 on warm cache.

- [ ] **Step 7: Run batch script a second time to verify cache hits**

Clean and re-run:

```bash
cd backend && python -c "
import asyncio
from sqlalchemy import text
from app.database import engine

async def clean():
    async with engine.begin() as conn:
        await conn.execute(text('TRUNCATE memories, tags, memory_tags, memory_embeddings, entities, entity_relations, knowledge_triples, audit_log, token_blocklist CASCADE'))
    print('Memories cleaned (cache preserved)')

asyncio.run(clean())
"
cd backend && python scripts/test_batch_100.py 2>&1 | tail -20
```

Second run should show Phase 3 lookup with mostly HITS (since the entity embeddings are already in the persistent cache from the first run), and 0 or very few new entity embedding HTTP calls.
