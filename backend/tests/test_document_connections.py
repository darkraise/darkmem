"""Documents nearest this one, by cosine over block vectors (spec §4).

The no-model-call scan below carries the entity-walk version's rule -- this
surface generates no prose and reaches no model -- but not its exact wording:
the forbidden-marker tuple is Task 2's, repeated here rather than imported, so
these two scans cannot fail together because a shared helper moved.

The behavioural tests go past the brief's own minimal set: a stub that returns
an early `DocumentConnections(embedded=False, ...)` for every call would pass
the brief's one given test. The scoping predicate (`other.project = :project`),
the max-aggregation (the argmax block pair, not the mean or the first), and
the ordering are each pinned separately because each is a single-line mutation
a stub-shaped implementation would not fail on. Self-exclusion is not a single
predicate: it is enforced at two layers (the LATERAL's own
`tb.document_id <> :document_id` and the outer query's
`other.id <> :document_id`), pinned by two different tests --
`test_the_lateral_excludes_the_queried_documents_own_blocks` for the inner
layer, and `test_a_document_is_never_connected_to_itself` as the
both-layers-gone tripwire, which by design does not fail when only one layer
is removed.
"""
import ast
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.document_connections import (
    DocumentConnections, connections_for_document,
)
from app.services.document_ingest import BlockDraft, file_document
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry

MODULE = Path(__file__).resolve().parents[1] / "app/services/document_connections.py"

PROJECT = "t-document-connections"
OTHER_PROJECT = "t-document-connections-other"
FINGERPRINT = "docconnections_fp"
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
    for forbidden in ("chat_completion", "llm", "embed(", "embed_", "generate"):
        assert forbidden not in code, f"{forbidden} reached document_connections"


def test_the_module_does_not_resolve_a_fingerprint_through_the_embedder():
    """Spec §3.5 (inherited by §4): both embedder resolvers are network or
    stale; neither is permitted here."""
    code = _code_only()
    assert "resolve_active_fingerprint" not in code
    assert "resolve_read_fingerprint" not in code


def test_the_module_applies_no_score_floor():
    """Spec §3.3 (inherited by §4): the distribution is continuous, so a
    floor encodes a precision claim the data does not support."""
    code = _code_only()
    assert "MIN_SCORE" not in code


@pytest.mark.asyncio
async def test_an_unknown_document_is_not_embedded(session):
    from uuid import uuid4
    result = await connections_for_document(session, document_id=uuid4())
    assert isinstance(result, DocumentConnections)
    assert result.embedded is False
    assert result.comparable_documents == 0
    assert result.items == ()


@pytest.mark.asyncio
async def test_a_known_document_with_no_shared_fingerprint_is_not_embedded(session):
    """The four-state envelope's other `embedded=False` path: a document that
    exists and has blocks, but resolves no fingerprint holding vectors on
    both sides -- because nothing has embedded it yet. Distinct from the
    unknown-document path above; if `connections_for_document` special-cased
    "no matching document row" without a real fingerprint check, that path
    could report `embedded=True` here by accident."""
    await _register(session)
    document_id, _block_ids = await _file_blocks(session)

    result = await connections_for_document(session, document_id=document_id)

    assert result.embedded is False
    assert result.comparable_documents == 0
    assert result.items == ()


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


@pytest.mark.asyncio
async def test_the_best_matching_block_pair_wins_not_the_mean_or_the_first(session):
    """Max-aggregation: one row per other document, scored by its single
    best-matching block pair. Mine's first block (by order_index) is
    orthogonal to theirs' only block and mine's second block is identical --
    a mean would dilute the score and a "first block" bug would report 0.0."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(
        session, texts=("mine one", "mine two"),
    )
    await _embed_block(session, mine_blocks[0], DIRECTION_A)
    await _embed_block(session, mine_blocks[1], DIRECTION_B)
    theirs, theirs_blocks = await _file_blocks(session)
    await _embed_block(session, theirs_blocks[0], DIRECTION_B)

    result = await connections_for_document(session, document_id=mine)

    assert result.embedded is True
    assert len(result.items) == 1
    item = result.items[0]
    assert item.document_id == theirs
    assert item.block_id == mine_blocks[1]
    assert item.block_text == "mine two"
    assert item.other_block_id == theirs_blocks[0]
    assert item.other_block_text == "content"
    assert item.score == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_a_document_outside_the_project_is_excluded(session):
    """Doc 18 §8's isolation boundary: the same predicate must scope both the
    returned rows and the comparable-documents count, or a cross-project
    vector match would leak into one but not the other."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(session)
    await _embed_block(session, mine_blocks[0], DIRECTION_A)
    own, own_blocks = await _file_blocks(session)
    await _embed_block(session, own_blocks[0], DIRECTION_A)
    foreign, foreign_blocks = await _file_blocks(
        session, project=OTHER_PROJECT,
    )
    await _embed_block(session, foreign_blocks[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=mine)

    assert result.embedded is True
    assert [item.document_id for item in result.items] == [own]
    assert result.comparable_documents == 1


@pytest.mark.asyncio
async def test_a_document_is_never_connected_to_itself(session):
    """Self-exclusion is enforced at two layers now: the LATERAL's own
    `tb.document_id <> :document_id` (pinned separately by
    `test_the_lateral_excludes_the_queried_documents_own_blocks`) and this
    query's outer `other.id <> CAST(:document_id AS uuid)`. This test is the
    both-layers-gone tripwire, not a single-predicate pin: removing either
    layer alone still leaves the other one excluding mine's own document, so
    this test only fails when both are removed together. Kept anyway,
    because "both layers were silently deleted in the same change" is
    exactly the kind of regression a single test should still catch."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(session)
    await _embed_block(session, mine_blocks[0], DIRECTION_A)
    theirs, theirs_blocks = await _file_blocks(session)
    await _embed_block(session, theirs_blocks[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=mine)

    assert result.embedded is True
    assert [item.document_id for item in result.items] == [theirs]
    assert result.comparable_documents == 1


@pytest.mark.asyncio
async def test_the_lateral_excludes_the_queried_documents_own_blocks(session):
    """Fix round 2, finding I1: without `tb.document_id <> :document_id`
    inside the LATERAL, a document made of near-duplicate blocks can fill
    every one of its ten probe slots with copies of its own text before a
    single cross-document candidate is even considered -- silently starving
    the real match rather than merely wasting a slot the outer `WHERE` would
    have dropped anyway. Ten identical mine-blocks (all at cosine distance 0
    from each other) plus one, strictly farther, same-project target
    reproduces that shape exactly: with the exclusion in place only the
    target is ever a LATERAL candidate; without it the ten self-matches
    alone fill `_PROBE_LIMIT` and the target is never probed at all."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(
        session, texts=tuple(f"mine {i}" for i in range(10)),
    )
    for block_id in mine_blocks:
        await _embed_block(session, block_id, DIRECTION_A)
    target, target_blocks = await _file_blocks(session)
    await _embed_block(session, target_blocks[0], DIRECTION_BETWEEN)

    result = await connections_for_document(session, document_id=mine)

    assert result.embedded is True
    assert [item.document_id for item in result.items] == [target]


@pytest.mark.asyncio
async def test_the_probe_limit_above_one_survives_a_nearer_foreign_block(session):
    """M3: `_PROBE_LIMIT` must fetch more than the single nearest candidate,
    because the probe is not scoped to the calling project even after
    excluding the queried document's own blocks (finding I1's remaining
    truncation risk, named in the module docstring). A foreign-project block
    identical to mine's own direction scores 1.0 and sorts strictly ahead of
    the real, same-project target (0.7071); with `_PROBE_LIMIT` reduced to 1
    the foreign block alone fills the LATERAL's one slot, the outer project
    predicate then correctly drops it, and the real match never surfaces --
    proving the limit must stay above 1, not merely that it is a positive
    number."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(session)
    await _embed_block(session, mine_blocks[0], DIRECTION_A)
    target, target_blocks = await _file_blocks(session)
    await _embed_block(session, target_blocks[0], DIRECTION_BETWEEN)
    foreign, foreign_blocks = await _file_blocks(session, project=OTHER_PROJECT)
    await _embed_block(session, foreign_blocks[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=mine)

    assert result.embedded is True
    assert [item.document_id for item in result.items] == [target]
    assert result.items[0].score == pytest.approx(0.7071, abs=1e-3)


@pytest.mark.asyncio
async def test_items_are_ordered_by_score_descending(session):
    """Document ids are time-ordered UUIDv7, so creating the higher-scoring
    document first would let an id-ordered mutation pass by coincidence. The
    weaker match is created first here, decoupling id order from score
    order, so only an actual score sort satisfies the assertion."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(session)
    await _embed_block(session, mine_blocks[0], DIRECTION_A)

    weak, weak_blocks = await _file_blocks(session)
    await _embed_block(session, weak_blocks[0], DIRECTION_BETWEEN)
    strong, strong_blocks = await _file_blocks(session)
    await _embed_block(session, strong_blocks[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=mine)

    assert [item.document_id for item in result.items] == [strong, weak]
    assert result.items[0].score == pytest.approx(1.0)
    assert result.items[1].score == pytest.approx(0.7071, abs=1e-3)


@pytest.mark.asyncio
async def test_comparable_documents_counts_the_project_not_the_returned_page(session):
    """A `limit` narrower than the project's other-document count must not
    shrink `comparable_documents` to match -- that field answers "how many
    documents could this one be compared against", not "how many are on this
    page". The count is over `documents` at any fingerprint, so it is the
    project's other-document count, embedded or not -- the same meaning
    `document_related.comparable_memories` was corrected to on 2026-09-05."""
    await _register(session)
    mine, mine_blocks = await _file_blocks(session)
    await _embed_block(session, mine_blocks[0], DIRECTION_A)

    for i in range(3):
        other, other_blocks = await _file_blocks(session)
        await _embed_block(session, other_blocks[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=mine, limit=1)

    assert len(result.items) == 1
    assert result.comparable_documents == 3


@pytest.mark.asyncio
async def test_a_single_document_project_reports_zero_comparable(session):
    """A fully embedded document that is the project's only one resolves no
    shared fingerprint -- the counterpart side of the pair is empty -- so
    `embedded` is False and `comparable_documents` is 0. The pair means
    "nothing to compare against", and nothing will resolve it but filing a
    second document; the UI must read the count before it reads `embedded`."""
    await _register(session)
    document_id, block_ids = await _file_blocks(session)
    await _embed_block(session, block_ids[0], DIRECTION_A)

    result = await connections_for_document(session, document_id=document_id)

    assert result.embedded is False
    assert result.comparable_documents == 0
    assert result.items == ()


@pytest.mark.asyncio
async def test_an_unembedded_sibling_document_still_counts_as_comparable(session):
    """The genuinely-pending state: a sibling exists but carries no vector,
    so no fingerprint holds both sides and the comparison really is waiting
    on an embed."""
    await _register(session)
    document_id, block_ids = await _file_blocks(session)
    await _embed_block(session, block_ids[0], DIRECTION_A)
    await _file_blocks(session, texts=("unembedded sibling",))

    result = await connections_for_document(session, document_id=document_id)

    assert result.embedded is False
    assert result.comparable_documents == 1
    assert result.items == ()
