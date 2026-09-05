"""Memories nearest a document, by cosine (spec §3).

The no-model-call scan below is retained verbatim from the entity-walk version:
the basis changed, the rule that this surface generates no prose did not.

The behavioural tests below go past the brief's own minimal set: a stub that
returns an early `RelatedMemories(embedded=False, ...)` for every call would
pass every test the brief gave verbatim. The scoping predicate
(`m.project = :project`), the max-aggregation (the argmax block, not the mean
or the first), and the ordering are pinned separately because each is a
single-line mutation a stub-shaped implementation would not fail on.
"""
import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.document_related import (
    RelatedMemories, related_memories_for_document,
)
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
from app.utils.ids import new_id

MODULE = Path(__file__).resolve().parents[1] / "app/services/document_related.py"

PROJECT = "t-document-related"
OTHER_PROJECT = "t-document-related-other"
FINGERPRINT = "docrelated_fp"
DIMS = 4

# Orthogonal unit directions so cosine similarity is exact and decidable:
# identical direction scores 1.0, orthogonal scores 0.0, and a 45-degree
# vector scores exactly 1/sqrt(2) -- no ambiguity from a parallel or a
# zero-vector edge case.
DIRECTION_A = [1.0, 0.0, 0.0, 0.0]
DIRECTION_B = [0.0, 1.0, 0.0, 0.0]
DIRECTION_BETWEEN = [1.0, 1.0, 0.0, 0.0]


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
    # "embed(" / "embed_batch" catch an actual embed call; the bare word
    # "embed" would also convict `embedder_registry` and the
    # `memory_embeddings` / `block_embeddings` table names this module reads
    # by identifier, which are not model calls.
    for forbidden in ("chat_completion", "llm", "embed(", "embed_batch", "generate"):
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


# ── behavioural: the query shape, not just the early returns ─────────


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """The registry cache is process-wide while the test database is rolled
    back; without this a later test finds the fingerprint "known", skips the
    DDL, and inserts into a child table its own transaction never created."""
    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


async def _register(session) -> None:
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=FINGERPRINT, model_id="m", dims=DIMS, source="llm"),
    )


async def _file_blocks(session, *, project=PROJECT, texts=("content",)) -> tuple[str, list[str]]:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session, project=project, content="\n\n".join(texts),
        parse=lambda: drafts, title="probe", source_type="note",
    )
    await session.flush()
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(ingest.document_id)},
    )).scalars().all()
    return str(ingest.document_id), [str(r) for r in rows]


async def _embed_block(session, block_id: str, vector: list[float]) -> None:
    table = child_table("block_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {table} (block_id, fingerprint, embedding, created_at) "
            f"VALUES (CAST(:id AS uuid), :fp, CAST(:vec AS vector), now())"
        ),
        {"id": block_id, "fp": FINGERPRINT, "vec": str(vector)},
    )


async def _memory(session, *, project=PROJECT) -> str:
    memory_id = new_id()
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, status) "
            "VALUES (CAST(:id AS uuid), 'seed', 'api', :project, 'active')"
        ),
        {"id": memory_id, "project": project},
    )
    return str(memory_id)


async def _embed_memory(session, memory_id: str, vector: list[float]) -> None:
    table = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {table} (memory_id, fingerprint, embedding, created_at) "
            f"VALUES (CAST(:id AS uuid), :fp, CAST(:vec AS vector), now())"
        ),
        {"id": memory_id, "fp": FINGERPRINT, "vec": str(vector)},
    )


@pytest.mark.asyncio
async def test_the_best_matching_block_wins_not_the_mean_or_the_first(session):
    """Spec §3's max-aggregation: one row per memory, scored by its single
    best-matching block. Block one (first by order_index) is orthogonal to
    the memory and block two is identical to it -- a mean would score 0.5
    and a "first block" bug would report block one's score of 0.0."""
    await _register(session)
    document_id, block_ids = await _file_blocks(
        session, texts=("block one", "block two"),
    )
    await _embed_block(session, block_ids[0], DIRECTION_A)
    await _embed_block(session, block_ids[1], DIRECTION_B)
    memory_id = await _memory(session)
    await _embed_memory(session, memory_id, DIRECTION_B)

    related = await related_memories_for_document(session, document_id=document_id)

    assert related.embedded is True
    assert len(related.items) == 1
    item = related.items[0]
    assert item.memory_id == memory_id
    assert item.block_id == block_ids[1]
    assert item.block_text == "block two"
    assert item.score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_a_memory_outside_the_documents_project_is_excluded(session):
    """Doc 18 §8's isolation boundary: the same predicate must scope both the
    returned rows and the comparable-memories count, or a cross-project
    vector match would leak into one but not the other. An in-project memory
    is also embedded so the comparison is possible at all (with none, the
    fingerprint resolver correctly reports `embedded=False`, which would
    make this test pass for the wrong reason)."""
    await _register(session)
    document_id, block_ids = await _file_blocks(session)
    await _embed_block(session, block_ids[0], DIRECTION_A)
    own_memory = await _memory(session)
    await _embed_memory(session, own_memory, DIRECTION_A)
    foreign_memory = await _memory(session, project=OTHER_PROJECT)
    await _embed_memory(session, foreign_memory, DIRECTION_A)

    related = await related_memories_for_document(session, document_id=document_id)

    assert related.embedded is True
    assert [item.memory_id for item in related.items] == [own_memory]
    assert related.comparable_memories == 1


@pytest.mark.asyncio
async def test_items_are_ordered_by_score_descending(session):
    """`memory_id` is a time-ordered UUIDv7, so creating the higher-scoring
    memory first would let an id-ordered mutation pass by coincidence. The
    weaker match is created first here, decoupling id order from score
    order, so only an actual score sort satisfies the assertion."""
    await _register(session)
    document_id, block_ids = await _file_blocks(session)
    await _embed_block(session, block_ids[0], DIRECTION_A)

    weak = await _memory(session)
    await _embed_memory(session, weak, DIRECTION_BETWEEN)
    strong = await _memory(session)
    await _embed_memory(session, strong, DIRECTION_A)

    related = await related_memories_for_document(session, document_id=document_id)

    assert [item.memory_id for item in related.items] == [strong, weak]
    assert related.items[0].score == pytest.approx(1.0)
    assert related.items[1].score == pytest.approx(0.7071, abs=1e-3)


@pytest.mark.asyncio
async def test_comparable_memories_counts_the_project_not_the_returned_page(session):
    """A `limit` narrower than the project's embedded-memory count must not
    shrink `comparable_memories` to match -- that field answers "how many
    memories could this document be compared against", not "how many are on
    this page"."""
    await _register(session)
    document_id, block_ids = await _file_blocks(session)
    await _embed_block(session, block_ids[0], DIRECTION_A)

    for _ in range(3):
        memory_id = await _memory(session)
        await _embed_memory(session, memory_id, DIRECTION_A)

    related = await related_memories_for_document(
        session, document_id=document_id, limit=1,
    )

    assert len(related.items) == 1
    assert related.comparable_memories == 3
