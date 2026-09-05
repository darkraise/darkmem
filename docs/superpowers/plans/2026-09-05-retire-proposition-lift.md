# Retire Proposition Lifting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Remove proposition lifting entirely and re-base the two document
relatedness surfaces on cosine similarity over vectors both sides already
carry.

**Architecture:** Documents never enter the extraction pipeline. `document_related`
and `document_connections` stop walking lifted-memory provenance and instead
join the document's block vectors against, respectively, the project's memory
vectors and other documents' block vectors — max-aggregated per counterpart,
returning the argmax block as evidence, with no floor and no LLM call. A new
shared module resolves the fingerprint from data rather than through the
embedder.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Postgres + pgvector,
pytest; React + TanStack Query + TypeScript on the frontend.

**Spec:** `docs/superpowers/specs/2026-09-05-retire-proposition-lift-design.md`

## Global Constraints

- **Greenfield.** No backward compatibility, no migration, no compatibility
  shim. Data is disposable. Production was already rolled back to 50 memories.
- **No schema change.** This plan touches no migration and no table. If a task
  seems to need one, stop and report.
- **Language:** English only in code, comments, docs, commits, tests.
- **Commits:** `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no
  period. Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01V1jqL7Mx485MX5RQfnjDSj
  ```
- **Backend tests** run from `backend/` as `python -m pytest -q`. They need a
  `darkmem_test` database on 127.0.0.1:5433.
- **`pyproject.toml` sets `testpaths = ["tests"]`, so plain `pytest -q` does NOT
  collect `scripts/benchlib/tests`.** Task 9 must be run explicitly.
- **The full gate (`./scripts/gate.sh` from the repo root) is required before
  merge** — dropping a route trips enumeration guards and the benchlib leg that
  plain pytest does not collect.
- **Comments:** default to none. Add one only when the WHY is non-obvious.
  Never explain WHAT the code does. Never reference the task number.
- **No new RRF constant.** Two AST scans fail the build on a second `RRF_K`
  binding anywhere outside `rank_fusion.py`. Nothing in this plan needs one.
- **Do not reintroduce `origin_key` on any row this plan touches.**

---

### Task 1: Shared fingerprint resolution

**Files:**
- Create: `backend/app/services/document_similarity.py`
- Test: `backend/tests/test_document_similarity.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `resolve_shared_fingerprint(session, *, document_id: str, project: str, counterpart: str) -> str | None` where `counterpart` is `"memory"` or `"block"`. Returns the newest live fingerprint in which both sides hold vectors, or `None`.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 3: the spec §3.5 chose derive-from-data over both embedder resolvers and gives the reason

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_document_similarity.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest tests/test_document_similarity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.document_similarity'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/document_similarity.py`:

```python
"""The fingerprint a document relatedness read compares under (spec §3.5).

Two surfaces need this before they can compare anything — `document_related`
(a document's blocks against the project's memories) and `document_connections`
(a document's blocks against other documents' blocks) — and both need the same
guarantee: a fingerprint in which BOTH sides hold vectors. A cosine across
fingerprints has no defined value, so comparing under one side's fingerprint
alone is not a degraded answer, it is a meaningless one.

**Derived from the data, never resolved through the embedder.**
`block_embeddings.resolve_active_fingerprint` is a real embed call per caller —
a network call this read must not make, since it would oblige
`refuse_when_read_only` on the route and break the no-model-call pin these
surfaces carry. `resolve_read_fingerprint` is a data probe biased toward a
stale populated partition after a rotation, which would serve old-embedder rows
while search serves the active ones.

So: walk the live embedders newest first and take the first whose partitions
hold rows for both sides. It degrades correctly — during a rotation the panel
serves the old fingerprint's comparison until both sides finish re-embedding,
rather than serving a comparison that does not mean anything.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table

__all__ = ["COUNTERPARTS", "resolve_shared_fingerprint"]

COUNTERPARTS = ("memory", "block")

_LIVE_EMBEDDERS = text(
    "SELECT fingerprint FROM embedders "
    "WHERE retired_at IS NULL ORDER BY registered_at DESC"
)


async def resolve_shared_fingerprint(
    session: AsyncSession,
    *,
    document_id: str,
    project: str,
    counterpart: str,
) -> str | None:
    """The newest live fingerprint holding vectors for both sides, or None."""
    if counterpart not in COUNTERPARTS:
        raise ValueError(f"counterpart must be one of {COUNTERPARTS!r}")

    rows = (await session.execute(_LIVE_EMBEDDERS)).all()
    for (fingerprint,) in rows:
        # Interpolated, not bound: these are table identifiers, which no
        # driver parameterises. They come from `child_table` over a
        # fingerprint read out of `embedders`, never from a caller.
        blocks = child_table("block_embeddings", fingerprint)
        has_document = await session.scalar(
            text(
                f"SELECT EXISTS (SELECT 1 FROM {blocks} be "
                f"JOIN blocks b ON b.id = be.block_id "
                f"WHERE b.document_id = CAST(:document_id AS uuid))"
            ),
            {"document_id": document_id},
        )
        if not has_document:
            continue

        if counterpart == "memory":
            memories = child_table("memory_embeddings", fingerprint)
            has_counterpart = await session.scalar(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {memories} me "
                    f"JOIN memories m ON m.id = me.memory_id "
                    f"WHERE m.project = :project)"
                ),
                {"project": project},
            )
        else:
            has_counterpart = await session.scalar(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {blocks} be "
                    f"JOIN blocks b ON b.id = be.block_id "
                    f"JOIN documents d ON d.id = b.document_id "
                    f"WHERE d.project = :project "
                    f"AND d.id <> CAST(:document_id AS uuid))"
                ),
                {"project": project, "document_id": document_id},
            )

        if has_counterpart:
            return fingerprint
    return None
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest tests/test_document_similarity.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_similarity.py backend/tests/test_document_similarity.py
git commit -m "feat(documents): resolve a shared comparison fingerprint"
```

---

### Task 2: Re-base related-memories on cosine

**Files:**
- Modify: `backend/app/services/document_related.py` (whole file replaced)
- Test: `backend/tests/test_document_related.py` (rewritten)

**Interfaces:**
- Consumes: `resolve_shared_fingerprint` from Task 1.
- Produces: `RelatedMemory(memory_id: str, content: str, memory_type: str | None, status: str, source: str | None, score: float, block_id: str, block_text: str, span_start: int | None, span_end: int | None)`; `RelatedMemories(document_id: str, embedded: bool, comparable_memories: int, items: tuple[RelatedMemory, ...])`; `related_memories_for_document(session, *, document_id, limit=20) -> RelatedMemories`.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: spec §3.1-§3.5 fixes the aggregation, the absence of a floor, the query shape and the envelope

- [ ] **Step 1: Write the failing test**

Replace `backend/tests/test_document_related.py` entirely. Keep the existing
`_code_only()` AST helper and the no-model-call scan — they survive this change
unchanged — and replace the entity-walk tests:

```python
"""Memories nearest a document, by cosine (spec §3).

The no-model-call scan below is retained verbatim from the entity-walk version:
the basis changed, the rule that this surface generates no prose did not.
"""
import ast
from pathlib import Path

import pytest

from app.services.document_related import (
    RelatedMemories, related_memories_for_document,
)

MODULE = Path(__file__).resolve().parents[1] / "app/services/document_related.py"


def _code_only() -> str:
    """The module's source with every docstring removed.

    A raw-text scan would convict this module of the sentences in its own
    header explaining why it makes no model call -- the trap
    `test_document_summary.py` records and solves the same way.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            body.pop(0)
    return ast.unparse(tree)


def test_the_module_makes_no_model_call():
    code = _code_only()
    for forbidden in ("chat_completion", "llm", "embed", "generate"):
        assert forbidden not in code, f"{forbidden} reached document_related"


def test_the_module_does_not_resolve_a_fingerprint_through_the_embedder():
    """Spec §3.5: both embedder resolvers are network or stale; neither is
    permitted here."""
    code = _code_only()
    assert "resolve_active_fingerprint" not in code
    assert "resolve_read_fingerprint" not in code


def test_the_module_applies_no_score_floor():
    """Spec §3.3: the distribution is continuous, so a floor encodes a
    precision claim the data does not support."""
    code = _code_only()
    assert "MIN_SCORE" not in code


@pytest.mark.asyncio
async def test_an_unknown_document_is_not_embedded(session):
    from uuid import uuid4
    related = await related_memories_for_document(session, document_id=uuid4())
    assert isinstance(related, RelatedMemories)
    assert related.embedded is False
    assert related.comparable_memories == 0
    assert related.items == ()
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest tests/test_document_related.py -v`
Expected: FAIL — `ImportError: cannot import name 'RelatedMemories'` is satisfied
but `related.embedded` raises `AttributeError`, and the fingerprint/floor scans
fail because the old module still walks entities.

- [ ] **Step 3: Write the implementation**

Replace `backend/app/services/document_related.py` entirely:

```python
"""Memories nearest a document, by cosine over vectors both sides carry (§3).

The sibling of `document_connections`, one hop short of it: that module asks
which other *documents* resemble this one, this asks which *memories* do, which
is the maintenance question.

**No LLM call, at query time or ever.** Both sides are already embedded — the
blocks by the document pipeline, the memories by the ordinary one — so this is
a join, not a retrieval. The moment a relatedness feature writes prose about
what a document and a memory have in common it has become unbadged synthesis,
which doc 09 owns properly, with grounding and a ladder. A test pins the
absence.

**Max, not mean.** One row per memory, scored by its single best-matching
block. A large document is heterogeneous and a mean dilutes every real match
into noise, ranking the memory that matches one paragraph perfectly below one
vaguely near everything. The `LATERAL` carries the argmax block out with the
score, which is what lets the surface show the passage rather than only the
number.

**No floor.** Measured across all 475 filed documents the score distribution is
continuous -- p50 0.503, p90 0.612, p99 0.750, no seam -- and both error kinds
straddle any cut: at 0.724 a 28-character list item is noise, at 0.673 two
blocks make the same claim. A max over N blocks is also an order statistic, so
a fixed floor would encode "longer documents are more related". The surface
returns the nearest N with the score and the passage, and the reader judges.

**This is a scan, and the cost model is stated rather than implied.** It is
O(document blocks x project memories) and uses no index: the project predicate
defeats the HNSW path, and forcing the index yields a post-scan filter with no
over-fetch to compensate. Measured on the corpus's largest document (1,132
blocks against 50 memories): 89 ms. What keeps that viable is the owner's
ruling that documents are never extracted into memories -- a corpus that does
not absorb a hundred thousand machine-extracted propositions is a corpus small
enough to scan. The threshold to revisit is the project's *memory* count.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_similarity import resolve_shared_fingerprint
from app.services.embedder_registry import child_table

logger = logging.getLogger(__name__)

__all__ = ["RelatedMemory", "RelatedMemories", "related_memories_for_document"]


@dataclass(frozen=True)
class RelatedMemory:
    memory_id: str
    content: str
    memory_type: str | None
    status: str
    source: str | None
    score: float
    block_id: str
    block_text: str
    span_start: int | None
    span_end: int | None


@dataclass(frozen=True)
class RelatedMemories:
    """Four states, not two.

    `embedded` false says the comparison could not be made -- no shared
    fingerprint, because one side has not been embedded yet. That is different
    from `comparable_memories = 0` (the project holds no memory to compare
    against) and different again from an empty `items`. Rendering the three
    alike tells a reader "nothing relates to this" when the truth is "nothing
    could be compared yet", which is a different claim.
    """

    document_id: str
    embedded: bool
    comparable_memories: int
    items: tuple[RelatedMemory, ...]


_DOCUMENT_SQL = text(
    "SELECT project FROM documents WHERE id = CAST(:id AS uuid)"
)


def _related_sql(memories_table: str, blocks_table: str) -> str:
    """Interpolated, not bound: these are table identifiers, which no driver
    parameterises. Both come from `child_table` over a fingerprint read out of
    `embedders`, never from a caller."""
    return f"""
        SELECT m.id::text          AS memory_id,
               m.content           AS content,
               m.memory_type       AS memory_type,
               m.status            AS status,
               m.source            AS source,
               best.score          AS score,
               best.block_id::text AS block_id,
               best.block_text     AS block_text,
               lower(best.span)    AS span_start,
               upper(best.span)    AS span_end
        FROM memories m
        JOIN LATERAL (
            SELECT b.id        AS block_id,
                   b.text      AS block_text,
                   b.char_span AS span,
                   1 - (me.embedding <=> be.embedding) AS score
            FROM {memories_table} me
            JOIN {blocks_table} be ON true
            JOIN blocks b ON b.id = be.block_id
            WHERE me.memory_id = m.id
              AND b.document_id = CAST(:document_id AS uuid)
            ORDER BY score DESC
            LIMIT 1
        ) best ON true
        WHERE m.project = :project
        ORDER BY best.score DESC, m.id
        LIMIT :limit
    """


def _comparable_sql(memories_table: str) -> str:
    return (
        f"SELECT count(*) FROM {memories_table} me "
        f"JOIN memories m ON m.id = me.memory_id WHERE m.project = :project"
    )


async def related_memories_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> RelatedMemories:
    """Which memories are nearest this document, and which passage matched.

    Scoped to the document's own project in SQL, for the reason
    `connections_for_document` gives: a cross-project result would breach the
    isolation boundary doc 18 §8 calls a security one, in the surface whose
    whole purpose is to surface rows the reader had not thought of. Filtering
    the returned page instead would silently under-fill it.
    """
    key = str(document_id)
    project = (await session.execute(
        _DOCUMENT_SQL, {"id": key}
    )).scalar_one_or_none()
    if project is None:
        return RelatedMemories(
            document_id=key, embedded=False, comparable_memories=0, items=(),
        )

    fingerprint = await resolve_shared_fingerprint(
        session, document_id=key, project=project, counterpart="memory",
    )
    if fingerprint is None:
        return RelatedMemories(
            document_id=key, embedded=False, comparable_memories=0, items=(),
        )

    memories_table = child_table("memory_embeddings", fingerprint)
    blocks_table = child_table("block_embeddings", fingerprint)

    comparable = await session.scalar(
        text(_comparable_sql(memories_table)), {"project": project},
    )

    rows = (await session.execute(
        text(_related_sql(memories_table, blocks_table)),
        {"document_id": key, "project": project, "limit": limit},
    )).mappings().all()

    return RelatedMemories(
        document_id=key,
        embedded=True,
        comparable_memories=int(comparable or 0),
        items=tuple(
            RelatedMemory(
                memory_id=row["memory_id"],
                content=row["content"],
                memory_type=row["memory_type"],
                status=row["status"],
                source=row["source"],
                score=float(row["score"]),
                block_id=row["block_id"],
                block_text=row["block_text"],
                span_start=row["span_start"],
                span_end=row["span_end"],
            )
            for row in rows
        ),
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest tests/test_document_related.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_related.py backend/tests/test_document_related.py
git commit -m "feat(documents): re-base related memories on cosine"
```

---

### Task 3: Re-base document connections on cosine

**Files:**
- Modify: `backend/app/services/document_connections.py` (whole file replaced)
- Test: `backend/tests/test_document_connections.py` (rewritten)

**Interfaces:**
- Consumes: `resolve_shared_fingerprint` from Task 1.
- Produces: `DocumentConnection(document_id: str, title: str | None, score: float, block_id: str, block_text: str, other_block_id: str, other_block_text: str)`; `DocumentConnections(document_id: str, embedded: bool, comparable_documents: int, items: tuple[DocumentConnection, ...])`; `connections_for_document(session, *, document_id, limit=20) -> DocumentConnections`.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: spec §4 rules the re-base and states that everything §3 decides applies here

- [ ] **Step 1: Write the failing test**

Replace `backend/tests/test_document_connections.py` with the same four scans
Task 2 uses (no model call, no embedder-resolved fingerprint, no floor) plus:

```python
@pytest.mark.asyncio
async def test_an_unknown_document_is_not_embedded(session):
    from uuid import uuid4
    from app.services.document_connections import (
        DocumentConnections, connections_for_document,
    )
    result = await connections_for_document(session, document_id=uuid4())
    assert isinstance(result, DocumentConnections)
    assert result.embedded is False
    assert result.comparable_documents == 0
    assert result.items == ()
```

Copy the `_code_only()` helper verbatim from Task 2's test file, pointing
`MODULE` at `app/services/document_connections.py`. Repeat it rather than
importing it across test modules — these two scans must not fail together
because a shared helper moved.

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest tests/test_document_connections.py -v`
Expected: FAIL — `ImportError: cannot import name 'DocumentConnections'`

- [ ] **Step 3: Write the implementation**

Replace `backend/app/services/document_connections.py` entirely:

```python
"""Documents nearest this one, by cosine over block vectors (§4).

The sibling of `document_related`, one hop further out: that module asks which
*memories* resemble this document, this asks which other *documents* do.

Everything `document_related` decides applies here and for the same reasons --
no LLM call, max-aggregation over the argmax block pair, no floor, the
fingerprint derived from data, project scoping in SQL -- with one difference
that makes this the cheaper of the two: both sides are the *same* partition, so
this is a same-table join.

The former basis was `entities.memory_ids` over the memories a lift minted.
Nothing is lifted any more, so that walk would return an empty list forever.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_similarity import resolve_shared_fingerprint
from app.services.embedder_registry import child_table

logger = logging.getLogger(__name__)

__all__ = [
    "DocumentConnection", "DocumentConnections", "connections_for_document",
]


@dataclass(frozen=True)
class DocumentConnection:
    document_id: str
    title: str | None
    score: float
    block_id: str
    block_text: str
    other_block_id: str
    other_block_text: str


@dataclass(frozen=True)
class DocumentConnections:
    document_id: str
    embedded: bool
    comparable_documents: int
    items: tuple[DocumentConnection, ...]


_DOCUMENT_SQL = text(
    "SELECT project FROM documents WHERE id = CAST(:id AS uuid)"
)


def _connections_sql(blocks_table: str) -> str:
    """Interpolated, not bound: a table identifier from `child_table` over a
    fingerprint read out of `embedders`, never from a caller."""
    return f"""
        SELECT other.id::text      AS document_id,
               other.title         AS title,
               best.score          AS score,
               best.block_id::text AS block_id,
               best.block_text     AS block_text,
               best.other_block_id::text AS other_block_id,
               best.other_block_text     AS other_block_text
        FROM documents other
        JOIN LATERAL (
            SELECT mine_b.id    AS block_id,
                   mine_b.text  AS block_text,
                   their_b.id   AS other_block_id,
                   their_b.text AS other_block_text,
                   1 - (mine.embedding <=> theirs.embedding) AS score
            FROM {blocks_table} mine
            JOIN blocks mine_b ON mine_b.id = mine.block_id
            JOIN {blocks_table} theirs ON true
            JOIN blocks their_b ON their_b.id = theirs.block_id
            WHERE mine_b.document_id = CAST(:document_id AS uuid)
              AND their_b.document_id = other.id
            ORDER BY score DESC
            LIMIT 1
        ) best ON true
        WHERE other.project = :project
          AND other.id <> CAST(:document_id AS uuid)
        ORDER BY best.score DESC, other.id
        LIMIT :limit
    """


def _comparable_sql() -> str:
    return (
        "SELECT count(*) FROM documents "
        "WHERE project = :project AND id <> CAST(:document_id AS uuid)"
    )


async def connections_for_document(
    session: AsyncSession, *, document_id: UUID | str, limit: int = 20,
) -> DocumentConnections:
    """Which other documents are nearest this one, and which passages matched.

    Scoped to the document's own project in SQL. A connection across projects
    would cross the isolation boundary doc 18 §8 calls a security one — and it
    would do it in the surface whose whole purpose is to suggest things a
    reader has not thought of, which is the worst place to leak.
    """
    key = str(document_id)
    project = (await session.execute(
        _DOCUMENT_SQL, {"id": key}
    )).scalar_one_or_none()
    if project is None:
        return DocumentConnections(
            document_id=key, embedded=False, comparable_documents=0, items=(),
        )

    fingerprint = await resolve_shared_fingerprint(
        session, document_id=key, project=project, counterpart="block",
    )
    if fingerprint is None:
        return DocumentConnections(
            document_id=key, embedded=False, comparable_documents=0, items=(),
        )

    blocks_table = child_table("block_embeddings", fingerprint)

    comparable = await session.scalar(
        text(_comparable_sql()), {"project": project, "document_id": key},
    )

    rows = (await session.execute(
        text(_connections_sql(blocks_table)),
        {"document_id": key, "project": project, "limit": limit},
    )).mappings().all()

    return DocumentConnections(
        document_id=key,
        embedded=True,
        comparable_documents=int(comparable or 0),
        items=tuple(
            DocumentConnection(
                document_id=row["document_id"],
                title=row["title"],
                score=float(row["score"]),
                block_id=row["block_id"],
                block_text=row["block_text"],
                other_block_id=row["other_block_id"],
                other_block_text=row["other_block_text"],
            )
            for row in rows
        ),
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `backend/`: `python -m pytest tests/test_document_connections.py -v`
Expected: all passed

- [ ] **Step 5: Verify the connections query on real data**

This one is a same-table self-join and its cost is not measured anywhere yet.
Run against the live database (read-only):

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "
EXPLAIN (ANALYZE, TIMING OFF)
WITH d AS (SELECT id, project FROM documents WHERE uri LIKE '%E2-truth-core%' LIMIT 1)
SELECT other.id FROM documents other CROSS JOIN d
JOIN LATERAL (
  SELECT 1 - (mine.embedding <=> theirs.embedding) AS score
  FROM block_embeddings__qwen3_embedding_0_6b_1024 mine
  JOIN blocks mb ON mb.id = mine.block_id
  JOIN block_embeddings__qwen3_embedding_0_6b_1024 theirs ON true
  JOIN blocks tb ON tb.id = theirs.block_id
  WHERE mb.document_id = d.id AND tb.document_id = other.id
  ORDER BY score DESC LIMIT 1) best ON true
WHERE other.project = d.project AND other.id <> d.id
ORDER BY best.score DESC LIMIT 20;"
```

**If execution time exceeds 2 seconds, STOP and report.** The worst case here
is 1,132 blocks against 48,178 — three orders of magnitude above Task 2's
56,600 — and the spec's cost model was measured only for the memory side. A
slow result is a real finding about §4, not something to tune around.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/document_connections.py backend/tests/test_document_connections.py
git commit -m "feat(documents): re-base connections on cosine"
```

---

### Task 4: Route contracts, and remove the lift door

**Files:**
- Modify: `backend/app/api/routes/documents.py:40-45,62,64,160-180,480-520` and the connections route above it
- Test: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: `RelatedMemories` and `DocumentConnections` from Tasks 2 and 3.
- Produces: `RelatedMemoryItem`, `RelatedMemoriesResponse(items, embedded, comparable_memories)`, `DocumentConnectionItem`, `DocumentConnectionsResponse(items, embedded, comparable_documents)`. `DocumentLiftResponse` and the `POST /{document_id}/lift` route no longer exist.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: the response shape follows §3.5's state table

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_document_routes.py`. **There is no `filed_document`
fixture** — this file files documents inline through its own module-local
helpers. Follow that existing convention to obtain a filed document id; the
signatures below show what to assert, not a fixture to invent.

```python
@pytest.mark.asyncio
async def test_the_lift_route_is_gone(client):
    response = await client.post(f"/api/v1/documents/{uuid4()}/lift")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_related_memories_reports_its_comparison_state(client, filed_document):
    response = await client.get(
        f"/api/v1/documents/{filed_document}/related-memories"
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "embedded", "comparable_memories"}
    assert "lifted" not in body


@pytest.mark.asyncio
async def test_a_related_item_carries_its_matching_passage(client, filed_document):
    """Spec §3.4: the passage is the evidence, the score is an ordering key."""
    response = await client.get(
        f"/api/v1/documents/{filed_document}/related-memories"
    )
    for item in response.json()["items"]:
        assert set(item) >= {
            "memory_id", "content", "score",
            "block_id", "block_text", "span_start", "span_end",
        }
        assert "shared_entities" not in item
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`: `python -m pytest tests/test_document_routes.py -k "lift_route_is_gone or comparison_state or matching_passage" -v`
Expected: FAIL — the lift route answers 202/201, and the envelope still carries `lifted`.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/routes/documents.py`:

Remove the import at line 64 and the `refuse_when_read_only` / `get_memory_service`
dependencies if they become unused by this module:

```python
from app.services.proposition_lift import lift_document   # DELETE this line
```

Replace `RelatedMemoryItem`, `RelatedMemoriesResponse` and delete
`DocumentLiftResponse`:

```python
class RelatedMemoryItem(BaseModel):
    memory_id: str
    content: str
    memory_type: str | None = None
    status: str
    source: str | None = None
    # The passage is the evidence and the score is an ordering key -- never a
    # calibrated relevance measure. The distribution is continuous, so a client
    # rendering this as a percentage or a badge asserts a precision nobody
    # measured.
    score: float
    block_id: str
    block_text: str
    span_start: int | None = None
    span_end: int | None = None


class RelatedMemoriesResponse(BaseModel):
    items: list[RelatedMemoryItem]
    # False means the comparison could not be made -- one side is not embedded
    # under any shared fingerprint yet -- which is a different answer from an
    # empty list, and different again from a project holding no memory.
    embedded: bool
    comparable_memories: int


class DocumentConnectionItem(BaseModel):
    document_id: str
    title: str | None = None
    score: float
    block_id: str
    block_text: str
    other_block_id: str
    other_block_text: str


class DocumentConnectionsResponse(BaseModel):
    items: list[DocumentConnectionItem]
    embedded: bool
    comparable_documents: int
```

Delete the whole `@router.post("/{document_id}/lift", ...)` handler and its
`DocumentLiftResponse` usage. Update the module docstring's "**No lift door.**"
paragraph at lines 44-46 to say the door existed and was removed with the lift.

Replace the two read handlers' bodies:

```python
@router.get(
    "/{document_id}/related-memories", response_model=RelatedMemoriesResponse
)
async def get_related_memories(
    document_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> RelatedMemoriesResponse:
    """Memories nearest this document, with the passage that matched.

    No model call and no new table: both sides are already embedded, so this is
    a join. `embedded=false` says the comparison could not be made rather than
    that nothing relates.
    """
    related = await related_memories_for_document(
        session, document_id=document_id, limit=limit,
    )
    return RelatedMemoriesResponse(
        embedded=related.embedded,
        comparable_memories=related.comparable_memories,
        items=[
            RelatedMemoryItem(
                memory_id=m.memory_id,
                content=m.content,
                memory_type=m.memory_type,
                status=m.status,
                source=m.source,
                score=m.score,
                block_id=m.block_id,
                block_text=m.block_text,
                span_start=m.span_start,
                span_end=m.span_end,
            )
            for m in related.items
        ],
    )
```

Mirror the same shape for the connections handler, returning
`DocumentConnectionsResponse` with `comparable_documents`.

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`: `python -m pytest tests/test_document_routes.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/documents.py backend/tests/test_document_routes.py
git commit -m "feat(documents): drop the lift door, widen relatedness"
```

---

### Task 5: Delete the lift

**Files:**
- Delete: `backend/app/services/proposition_lift.py`, `backend/scripts/bulk_lift_documents.py`, `backend/tests/test_proposition_lift.py`, `backend/tests/test_document_lift_door.py`, `backend/tests/test_lift_idempotence.py`
- Modify: `backend/tests/test_prompt_hardening.py:117-123`

**Interfaces:**
- Consumes: nothing — Tasks 2, 3 and 4 removed every importer.
- Produces: nothing. `app.services.proposition_lift` no longer exists.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec's §5 inventory names every path

- [ ] **Step 1: Prove nothing still imports it**

```bash
cd /root/repositories/darkmem
rg -n "proposition_lift|PROVENANCE_KEY|lift_document|strip_document_lift|lifted_memory_ids" \
   backend/app backend/scripts frontend/src
```

Expected: hits only in the files this task deletes, plus
`backend/scripts/benchlib/isolation_probe.py` (Task 9) and
`backend/tests/test_prompt_hardening.py`. **If `backend/app` returns any hit,
STOP** — Tasks 2-4 did not land and deleting now breaks the boot.

- [ ] **Step 2: Delete the files**

```bash
git rm backend/app/services/proposition_lift.py \
       backend/scripts/bulk_lift_documents.py \
       backend/tests/test_proposition_lift.py \
       backend/tests/test_document_lift_door.py \
       backend/tests/test_lift_idempotence.py
```

- [ ] **Step 3: Remove the prompt-hardening case**

`backend/tests/test_prompt_hardening.py:117-123` parametrises the lift's system
prompt among the prompts it asserts are injection-resistant. Delete that entry
and its import. Leave every other prompt in the list untouched.

- [ ] **Step 4: Run the suite to verify nothing broke**

Run from `backend/`: `python -m pytest -q`
Expected: PASS, with the collected count down by the three deleted files'
tests. **A collection error naming `proposition_lift` means a reference was
missed** — find it with the Step 1 command rather than deleting the failing
test.

- [ ] **Step 5: Commit**

```bash
git commit -m "refactor(documents): delete proposition lifting"
```

---

### Task 6: Delete the block-to-fact bridge

**Files:**
- Delete: `backend/app/services/block_fact_sources.py`, `backend/tests/test_block_fact_sources.py`
- Modify: `backend/app/services/block_verbs.py:22`, `backend/app/services/document_door.py:29,614-642`, `backend/app/repositories/fact_sources.py:124-141`, `backend/tests/test_document_door.py:8,455-520`, `backend/tests/test_document_routes.py:748-750`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing. `BLOCK_SOURCE_KIND` is removed from `SOURCE_KINDS`, and `document_door.expire_facts_left_bare` is deleted with its last caller.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the owner ruled delete-not-keep, and §5 states the two shapes that go stale with it

- [ ] **Step 1: Confirm the bridge is inert in production**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c \
  "SELECT source_kind, count(*) FROM fact_sources GROUP BY 1;"
```

Expected: `memory` only. **If any `block` row exists, STOP and report** — the
spec's premise that this bridge never produced anything would be false.

- [ ] **Step 2: Write the failing test**

Add to `backend/tests/test_fact_sources.py`:

```python
def test_block_is_not_a_source_kind():
    """Spec §5: nothing mints a block-kind source, so a reserved value under a
    comment claiming its producer shipped is a stale claim, not an option."""
    from app.repositories.fact_sources import SOURCE_KINDS
    assert "block" not in SOURCE_KINDS
```

- [ ] **Step 3: Run it to verify it fails**

Run from `backend/`: `python -m pytest tests/test_fact_sources.py::test_block_is_not_a_source_kind -v`
Expected: FAIL — `assert 'block' not in SOURCE_KINDS`

- [ ] **Step 4: Delete the module and its call sites**

```bash
git rm backend/app/services/block_fact_sources.py backend/tests/test_block_fact_sources.py
```

Then:
- `block_verbs.py:22` — delete `from app.services.block_fact_sources import withdraw_blocks` and its call.
- `document_door.py:29` — delete `from app.services.block_fact_sources import withdraw_document` and its call inside `delete_document`.
- `document_door.py:614-642` — `delete_document` keeps its docstring claim that it "withdraws provenance before removing the row". Rewrite that paragraph: a document's blocks source no fact, so a delete removes the row and its blocks and journals, with nothing to withdraw. Delete `expire_facts_left_bare` (line 642), which loses its only caller.
- `fact_sources.py:124-141` — remove `BLOCK_SOURCE_KIND` from `SOURCE_KINDS` and delete the comment saying its producer shipped.
- `test_document_door.py:8,455-520` and `test_document_routes.py:748-750` — delete the tests that call `record_block_source` and assert the fact expiry. They assert behaviour that no longer exists; do not rewrite them to assert the absence, which Step 2's test already does.
- `tests/test_block_retrieval.py:359,367,408` — delete the comment explaining
  why `block_fact_sources` is absent from the forbidden set, the
  `SANCTIONED_LIFT = "app.services.block_fact_sources"` binding, and
  `test_the_sanctioned_lift_reaches_no_module_that_can_fetch_a_block`. **This
  is why it lands here and not in Task 8:** Step 5 below runs the full backend
  suite, which collects this file, and it cannot go green while these lines
  name a module this task deletes. The forbidden set becomes the complement
  with no exception.

- [ ] **Step 5: Run the suite**

Run from `backend/`: `python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A backend/app/services backend/tests
git commit -m "refactor(documents): delete the block-to-fact bridge"
```

---

### Task 7: Content surfaces and two-door parity

**Files:**
- Modify: `backend/app/services/content_surfaces.py:164-181,647`, `docs/two-door-parity.md:13,59`, `backend/tests/test_door_parity.py:285-322,1985-2005`, `backend/tests/test_api/test_rest_conformance.py:66`

**Interfaces:**
- Consumes: the route removal from Task 4.
- Produces: the corrected parity headline `77 surfaces: 24 two-door, 53 single-door (46 REST-only, 7 MCP-only), 0 divergent`.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: §5 fixes the counts and §2 gives related-memories' restated reason

- [ ] **Step 1: Run the guards to see them fail**

Run from `backend/`:
`python -m pytest tests/test_door_parity.py tests/test_content_surface_scoping.py tests/test_api/test_rest_conformance.py -v`
Expected: FAIL — `classified - live` is non-empty (the lift route is classified
but no longer served) and the headline count assertion reads 78.

- [ ] **Step 2: Update the classifications**

- `content_surfaces.py:647` — remove `"POST /api/v1/documents/{document_id}/lift"` from `ROUTES_WITHOUT_MEMORY_CONTENT`. Leave `GET .../connections` in place: it still returns documents, never a `memories` row.
- `content_surfaces.py:164-181` — `document_related_memories` keeps `kind=_R`, `Scoping.SCOPED` and `labels=("project", "status")`. Replace `decided_by` with `"spec 2026-09-05 §3"` and rewrite the reason: it still returns `m.content` for every related memory, and the scope is still derived from the document rather than accepted from the caller — the difference is that the derivation now runs through `document_similarity.resolve_shared_fingerprint` and the project predicate in `_related_sql`, not `_PROJECT_SQL` alone. Keep the single-door sentence: an MCP twin would hand an agent an L1-keyed memory list, which is `graph.candidate_read`'s own block. That reason survives the basis change because it is about what the surface *returns*, not what it ranks on.
- `docs/two-door-parity.md:59` — delete the `documents.lift` row.
- `docs/two-door-parity.md:13` — the headline becomes:
  `**77 surfaces: 24 two-door, 53 single-door with a stated reason (46 REST-only, 7 MCP-only), 0 divergent.**`
- `docs/two-door-parity.md` — in the `documents.write` and `documents.retrieval`
  rows, replace every clause naming "doc 16 section 5's on-demand lift is the
  only route from a block to a fact" with the stronger fact: there is no route
  from a block to a fact, so the firewall holds with no exception.
- `test_door_parity.py:304-322` — delete the `documents.lift` expectation.
- `test_door_parity.py:1985-2005` — update the asserted counts to 77 / 24 / 53 / 46 / 7.
- `test_door_parity.py:285-302` — `documents.related_memories`' reason text must match `content_surfaces.py`'s new one.
- `test_rest_conformance.py:66` — remove the lift route from the conformance list.

- [ ] **Step 3: Run the guards to verify they pass**

Run from `backend/`:
`python -m pytest tests/test_door_parity.py tests/test_content_surface_scoping.py tests/test_api/test_rest_conformance.py -v`
Expected: all passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/content_surfaces.py docs/two-door-parity.md backend/tests
git commit -m "docs(parity): drop the lift surface, restate relatedness"
```

---

### Task 8: Firewall classification

**Files:**
- Modify: `backend/tests/test_block_retrieval.py:345-357` and its vault-scan section

**Interfaces:**
- Consumes: the two rewritten modules from Tasks 2 and 3.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 0 = 1
**Approach:** inline - skip 3: §3.6 states the classification and what the pin must assert

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_block_retrieval.py`:

```python
def test_no_service_module_imports_the_relatedness_surfaces():
    """Spec §3.6: these read block vectors and rank memories by them. That is
    permitted on a per-document panel outside the composition and nowhere else,
    so the pin is structural -- a test asserting today's results hold no block
    cannot pin "cannot"."""
    paths = app_sources(BACKEND / "app/services")
    offenders = []
    for path in paths:
        if path.name in {"document_related.py", "document_connections.py"}:
            continue
        closure = import_closure(path, BACKEND)
        for surface in (
            "app.services.document_related", "app.services.document_connections",
        ):
            if surface in closure:
                offenders.append((path.name, surface))
    assert offenders == [], f"a service reached a relatedness surface: {offenders}"
```

- [ ] **Step 2: Run it**

Run from `backend/`: `python -m pytest tests/test_block_retrieval.py::test_no_service_module_imports_the_relatedness_surfaces -v`
Expected: PASS immediately — nothing under `app/services` imports either module
today. That is the point: the test pins a property that already holds, so it
fails the day someone breaks it. Confirm it can fail by temporarily adding
`from app.services import document_related` to `app/services/block_query.py`,
re-running (expect FAIL), then reverting.

- [ ] **Step 3: Add both modules to the block channel**

In `test_block_retrieval.py:345-357`, add to `BLOCK_CHANNEL_MODULES`:

```python
    # The relatedness surfaces (spec §3.6). They read block rows and block
    # vectors, so they are classified here in the change that gives them that
    # reach -- an unclassified module is a hole in the scan.
    "app.services.document_related",
    "app.services.document_connections",
```

`"app.services.document_similarity"` is already in this set — Task 1's review
found it missing and Task 1's fix round added it, since that module reads block
rows too and this set's own comment requires classification in the creating
task. Verify it is present; do not add it twice.

- [ ] **Step 4: Confirm the `block_fact_sources` exception is already gone**

Task 6 removed `SANCTIONED_LIFT`, its explanatory comment and
`test_the_sanctioned_lift_reaches_no_module_that_can_fetch_a_block`, because
that task deletes the module those lines name and its own full-suite run could
not otherwise pass. Verify rather than repeat:

```bash
rg -n "block_fact_sources|SANCTIONED_LIFT" backend/tests/test_block_retrieval.py
```
Expected: no output. **If anything is found, delete it here** — Task 6 left work
behind.

- [ ] **Step 5: Run the whole file**

Run from `backend/`: `python -m pytest tests/test_block_retrieval.py -v`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_block_retrieval.py
git commit -m "test(documents): classify the relatedness surfaces"
```

---

### Task 9: Rebuild the isolation probe's relatedness fixture

**Files:**
- Modify: `backend/scripts/benchlib/isolation_probe.py:470,541-570,1223-1257`
- Test: `backend/scripts/benchlib/tests/test_isolation_probe.py:600-636`

**Interfaces:**
- Consumes: `related_memories_for_document` from Task 2.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: §5 rules the fixture is redesigned rather than ported, and says why a port would be vacuous

- [ ] **Step 1: Understand why the old fixture cannot be ported**

Read `isolation_probe.py:541-570`. It seeds a memory carrying
`LIFT_PROVENANCE_KEY` so the entity walk links a document in the OBSERVER
project to a memory in the FOREIGN one, then asserts the surface does not
return it. The cosine surface has no entity walk, and **the probe seeds zero
block embeddings** — its stub embedder is `_hash_vector(text)`. Ported
literally, the surface returns nothing for any input and the test passes while
proving nothing.

- [ ] **Step 2: Write the failing test**

In `scripts/benchlib/tests/test_isolation_probe.py`, replace the
`_RELATED_SQL` string-replacement monkeypatch (lines 600-636) with a test that
mutates the *project predicate* in the new module and asserts the probe catches
it:

```python
def test_the_probe_catches_a_dropped_project_predicate(monkeypatch):
    """The predicate-mutation test, against the cosine surface.

    The old version string-replaced `"WHERE m.project = :project"` out of a
    module-level constant. The predicate now lives inside `_related_sql`, so
    the mutation targets the builder -- and the fixture must seed real block
    and memory vectors under one fingerprint, or the mutated surface returns
    nothing and the test passes vacuously.
    """
    from app.services import document_related

    original = document_related._related_sql

    def leaky(memories_table: str, blocks_table: str) -> str:
        return original(memories_table, blocks_table).replace(
            "WHERE m.project = :project", "WHERE true"
        )

    monkeypatch.setattr(document_related, "_related_sql", leaky)
    result = run_isolation_probe()
    assert result.failures, "a cross-project leak was not detected"
```

- [ ] **Step 3: Run it to verify it fails**

Run from `backend/`: `python -m pytest scripts/benchlib/tests/test_isolation_probe.py -v`
Expected: FAIL — the seeded fixture produces no vectors, so `leaky` returns
nothing and `result.failures` is empty. **This failure is the point: it is the
vacuity the spec warned about, made visible before the fixture is fixed.**

- [ ] **Step 4: Seed real vectors in the fixture**

In `isolation_probe.py:541-570`, replace the lifted-memory seed. The fixture
must, under one fingerprint registered in `embedders`:

1. Register a fingerprint and create both child partitions via
   `embedder_registry.register`.
2. File a document in the OBSERVER project with at least one block, and insert
   that block's vector into `block_embeddings__<fp>`.
3. Insert a memory in the FOREIGN project whose vector is **the same vector**,
   into `memory_embeddings__<fp>`.

Using an identical vector makes the cosine exactly 1.0, so the foreign memory
is guaranteed to be the top result if the project predicate is dropped. That is
what makes the mutation test non-vacuous: with the predicate intact the surface
returns nothing, with it removed it returns the foreign memory at rank 1.

Delete the `LIFT_PROVENANCE_KEY` import at line 470.

- [ ] **Step 5: Update the probe's driver**

At `isolation_probe.py:1223-1257`, the driver calls the surface and inspects
`related.items` for foreign rows. Update it for the new envelope: it must also
assert `related.embedded is True`, because an `embedded=False` answer means the
comparison never ran and a probe that accepts it proves nothing.

- [ ] **Step 6: Run the benchlib suite**

Run from `backend/`: `python -m pytest scripts/benchlib/tests/ -q`
Expected: all passed. Note `pyproject.toml` sets `testpaths = ["tests"]`, so
this path must be given explicitly — plain `pytest -q` does not collect it.

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/benchlib
git commit -m "test(bench): re-seed the isolation probe for cosine"
```

---

### Task 10: Frontend

**Files:**
- Modify: `frontend/src/hooks/api/use-documents-api.ts:255-300`, `frontend/src/features/documents/document-actions.tsx:172-262`, `frontend/src/features/documents/documents-view.tsx:233-247`, `frontend/src/lib/query-keys.ts:114-130`

**Interfaces:**
- Consumes: the route contracts from Task 4.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: §3.4 fixes the presentation rules and §3.5 the states

- [ ] **Step 1: Update the hooks**

In `use-documents-api.ts`, replace the `RelatedMemory` interface and
`useRelatedMemories`, and **delete `useDocumentLift` entirely**:

```ts
export interface RelatedMemory {
  memory_id: string
  content: string
  memory_type: string | null
  status: string
  source: string | null
  /** An ordering key, never a calibrated relevance measure -- the score
   * distribution is continuous, so rendering this as a percentage or a badge
   * would assert a precision nobody measured. Show the passage. */
  score: number
  block_id: string
  block_text: string
  span_start: number | null
  span_end: number | null
}

export interface RelatedMemoriesResponse {
  items: RelatedMemory[]
  /** False means the comparison could not be made -- one side is not embedded
   * under any shared fingerprint yet. Different from an empty list. */
  embedded: boolean
  comparable_memories: number
}

export function useRelatedMemories(documentId: string | null) {
  return useQuery<RelatedMemoriesResponse>({
    queryKey: ["documentRelatedMemories", documentId],
    enabled: !DEMO && Boolean(documentId),
    queryFn: () => apiFetch(`/documents/${documentId}/related-memories`),
  })
}
```

Mirror the same shape for the connections hook: `DocumentConnection` gains
`score`, `block_id`, `block_text`, `other_block_id`, `other_block_text` and
loses `shared_entities`; its response gains `embedded` and
`comparable_documents`.

**`enabled: !DEMO` must stay on every hook.** A hook without it 401-redirects
the whole demo to `/login`.

- [ ] **Step 2: Update the panels**

In `document-actions.tsx:220-262`, the related-memories panel currently renders
four branches off `lifted`. Replace with the spec §3.5 states, all four
distinct — artifacts spec §9 requires a failed read never render as an empty
one:

- `related.isLoading` → the existing skeleton.
- `related.isError` → the existing failure state.
- `!related.data?.embedded` → "Not comparable yet — this document's blocks or
  this project's memories are still being embedded." No action button: the
  hourly `block_embedding_refresh` resolves it. **Delete the Lift button and
  every reference to `useDocumentLift`.**
- `related.data.comparable_memories === 0` → "No memories in this project to
  compare against."
- otherwise → the list. Each row renders the memory content, the matching
  `block_text` as the evidence, and `score.toFixed(3)` as plain text. **No
  percentage, no progress bar, no badge, no adjective.**

In `document-actions.tsx:172-187` and `documents-view.tsx:233-247`, apply the
same five states to the connections panel and **change the caption** — "Emergent
from shared entities after lifting" describes a mechanism that no longer
exists. Use "Nearest documents in this project, by passage similarity."

- [ ] **Step 3: Update the query-key registry**

In `lib/query-keys.ts:114-130`, both `documentRelatedMemories` and
`documentConnections` keep `kind: "global"`. Rewrite each `reason` — the scope
is still derived server-side from the document, but through the fingerprint
resolution and the project predicate rather than an entity walk, so a
project-keyed cache entry would still key on something the request never sends.

- [ ] **Step 4: Verify**

Run from `frontend/`:
```bash
npm run typecheck && npm test && npm run build
```
Expected: all pass. `npm run typecheck` is `tsc -b`; plain `tsc` misses the
project references.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(documents): render relatedness by passage, not entities"
```

---

### Task 11: Amend the design docs

**Files:**
- Modify: `docs/design/16-documents-and-pkm.md` (§4, §5, §6), `docs/design/01-domain-model-and-business-flows.md:159`, `docs/design/05-ingestion-pipeline.md:29`, `docs/design/20-roadmap-and-sequencing.md` (H1), `backend/app/services/block_query.py:9-14`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 0 = 2
**Approach:** inline - skip 3: §6 of the spec lists every file and what each must now say

- [ ] **Step 1: Amend, never delete**

This repository's convention is that a superseded section is amended in place
with the ruling and its date, because the original reasoning is still why the
resulting shape is what it is. Do not delete a section.

- **doc 16 §5** — open with the retirement: owner ruling 2026-09-05, the lift is
  retired, and the block-to-fact route no longer exists. Keep the "on demand,
  never automatic" argument and note it now generalises to "not extracted at
  all". Record what the sample measured (2,058 memories from 7 documents,
  ~104,000 extrapolated) as the reason.
- **doc 16 §4** and **`block_query.py:9-14`** — both say document content reaches
  the four-layer composition "only as lifted facts (§5)". It now reaches it not
  at all. `block_query.py`'s three numbered reasons still stand; only that
  clause changes.
- **doc 16 §6** — commits to connections as an entity-derived surface. It is now
  cosine over block vectors (spec §4).
- **doc 01:159** — "the differentiator is proposition ingestion" is no longer
  true. Amend: documents and memory share one substrate, and the differentiator
  is that a document is retrievable signal while a memory is an asserted claim.
- **doc 05:29** — the table row `| Filed document | parse → blocks →
  propositions | deferred | horizon (doc 16) |` becomes
  `| Filed document | parse → blocks → embeddings | shipped | doc 16 |`.
- **doc 20 H1** — states the lift as horizon work. Mark it retired with the date.

- [ ] **Step 2: Verify no stale reference survives**

```bash
cd /root/repositories/darkmem
rg -n "proposition ingestion|lifted facts|on-demand lift|proposition lift" docs/design/
```
Expected: every remaining hit sits inside an amendment paragraph that names the
retirement. **A bare claim that the lift exists is a failure of this task.**

- [ ] **Step 3: Commit**

```bash
git add docs/design backend/app/services/block_query.py
git commit -m "docs(design): retire the lift across the design set"
```

---

### Task 12: Amend CLAUDE.md, the changelog and the artifacts spec

**Files:**
- Modify: `CLAUDE.md` (Documents section), `CHANGELOG.md:911`, `docs/superpowers/specs/2026-09-03-artifacts-workspace-revamp-design.md` (§6.1, §6.2, §6.3, §8, §9)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 3: §6 of the spec names each edit

- [ ] **Step 1: CLAUDE.md, Documents section**

Three paragraphs change:

- The block-firewall paragraph says "doc 16 §5's lift is left as the only route
  from a block to a fact" and explains `block_fact_sources`' exclusion from the
  forbidden set on a narrower ground. Both go: **there is no route from a block
  to a fact**, and the forbidden set is the complement with no exception. Say
  the change is an owner ruling of 2026-09-05, in this file's own correction
  style.
- The delete paragraph ("Delete withdraws provenance before removing the row")
  describes withdrawing `fact_sources` rows a block corroborated. No block
  sources a fact, so a delete removes the document, its blocks and its journal
  entries with nothing to withdraw.
- Add one sentence to the documents overview: documents are parsed, embedded and
  retrievable, and are never extracted into memories.

- [ ] **Step 2: CHANGELOG.md:911**

That entry describes the shipped lift. Do not rewrite history — add a new
`## Unreleased` entry recording the retirement, and leave line 911 as the record
of what shipped.

- [ ] **Step 3: The artifacts spec**

- **§6.1** — the lift door is removed. Amend with the ruling.
- **§6.2** — the entity basis is replaced by cosine; its "shared-entity count is
  evidence, not a score" bullet is what §8 pointed at, so it must name the
  reversal rather than quietly contradict it.
- **§6.3** — the pricing script is deleted. Record what the sample measured, and
  that the measurement is what retired the feature: the section priced calls and
  tokens when the binding constraint was corpus composition.
- **§8** — "A similarity score. See §6.2." is **reversed** by the owner ruling of
  2026-09-05. State the reversal in place, with the constraint that replaces it:
  the score is an ordering key rendered as a raw cosine, never a percentage, bar
  or badge.
- **§9** — the testing list names the lift route's job-reachability test. Remove
  that line; add the structural relatedness pin from Task 8.

- [ ] **Step 4: Verify**

```bash
cd /root/repositories/darkmem
rg -n "lift" CLAUDE.md | rg -v "fact_lift|uplift|forklift"
```
Expected: every hit sits in an amendment naming the retirement.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md CHANGELOG.md docs/superpowers/specs
git commit -m "docs: retire the lift in the contract and the spec"
```

---

### Task 13: Gate and deploy

**Files:**
- None — this task runs the gate and the redeploy.

**Interfaces:**
- Consumes: every prior task.
- Produces: nothing.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 0 - spec 0 - coupling 2 - risk 2 = 4
**Approach:** inline - skip 3: the standing deploy ruling in CLAUDE.md fixes the sequence

- [ ] **Step 1: Run the full gate**

```bash
cd /root/repositories/darkmem && ./scripts/gate.sh
```

This is required rather than optional: dropping a route trips enumeration
guards, and the benchlib leg is not collected by plain `pytest -q`.

`GATE BLOCKED` (exit 2) means a missing toolchain, not a red gate. **A red
Playwright leg is a kill before it is a regression** — an `earlyoom` daemon runs
on this host and the suite is already at `workers: 1`. Re-run it standalone
through `backend/scripts/e2e/run_playwright_e2e.py` before believing it, and
never invoke Playwright bare.

- [ ] **Step 2: Rebuild and redeploy**

The standing ruling: a merged-but-undeployed change leaves the owner reviewing
the previous build. This alters `backend/` and `frontend/`, so it is in scope.

```bash
cd /root/repositories/darkmem
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
```

`DARKMEM_PUSH=0` is not optional — the script's default pushes, and publishing
an image from this machine is forbidden. `.github/workflows/release.yml` is the
only path to a registry.

- [ ] **Step 3: Confirm the change is in the running image**

Compose reuses an image whose tag did not move, so a skipped or failed build
redeploys the old bits and still reports `Started`. Wait for `healthy`, then:

```bash
docker exec darkmem-prod-darkmem-1 ls /app/app/services/proposition_lift.py
```
Expected: **No such file or directory.** A hit means the old image is running.

```bash
curl -s localhost:8000/openapi.json | python -c \
  "import json,sys; p=json.load(sys.stdin)['paths']; \
   assert not [k for k in p if k.endswith('/lift')], 'lift route still served'; \
   print('lift route gone')"
```

- [ ] **Step 4: Verify the surfaces answer on real data**

```bash
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -t -A -c \
  "SELECT id FROM documents WHERE uri LIKE '%comprehensive-audit%' LIMIT 1;"
```

Call `GET /api/v1/documents/<id>/related-memories` with a valid token and
confirm the envelope carries `embedded`, `comparable_memories`, and items with
`block_text` and `score`. A `comparable_memories` of 20 with a populated list is
the expected shape against the current 50-memory corpus.

- [ ] **Step 5: Commit any gate fixes**

If the gate required changes, commit them with a message naming the guard that
caught them.

---

## Self-Review

**Spec coverage.** §1 → Task 11's doc 05/doc 01 amendments and Task 12's §6.3
record. §2 (the reversal) → Task 12 §8, and the presentation constraint lands in
Task 4's schema comment and Task 10's panel rules. §3.1-§3.3 → Task 2. §3.4 →
Tasks 4 and 10. §3.5 → Tasks 1, 2, 4, 10. §3.6 → Task 8. §4 → Task 3. §5 →
Tasks 5, 6, 7, 9, 10. §5.1 is already done. §6 → Tasks 11 and 12. §7 → Task 13
plus each task's own test steps. §8 is explicitly out of scope.

**Type consistency.** `resolve_shared_fingerprint(session, *, document_id,
project, counterpart)` is defined in Task 1 and called with exactly those
keywords in Tasks 2 and 3. `RelatedMemories.embedded` / `.comparable_memories`
are produced in Task 2, consumed in Task 4, and surfaced in Task 10 as
`embedded` / `comparable_memories`. `DocumentConnections.comparable_documents`
is the connections twin and is never called `comparable_memories`.
`_related_sql(memories_table, blocks_table)` is a two-argument builder in Task 2
and is monkeypatched with that same signature in Task 9.

**Known risk carried deliberately.** Task 3's connections query is the one shape
in this plan whose cost is unmeasured — its worst case is three orders of
magnitude above the memory-side query the spec measured. Step 5 of that task is
a hard stop rather than a benchmark, because a slow result is a finding about
§4's design rather than something to tune around.
