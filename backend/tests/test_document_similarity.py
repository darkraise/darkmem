"""The fingerprint a relatedness read compares under (spec §3.5)."""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import text

from app.services.document_ingest import BlockDraft, file_document
from app.services.document_similarity import resolve_shared_fingerprint
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
from app.utils.ids import new_id

PROJECT = "t-document-similarity"
FINGERPRINT = "docsim_fp_a"
OTHER_FINGERPRINT = "docsim_fp_b"
DIMS = 4


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    """The registry cache is process-wide while the test database is rolled
    back; without this a later test finds the fingerprint "known", skips the
    DDL, and inserts into a child table its own transaction never created."""
    for fp in (FINGERPRINT, OTHER_FINGERPRINT, "retired_fp"):
        embedder_registry.forget(fp)
    yield
    for fp in (FINGERPRINT, OTHER_FINGERPRINT, "retired_fp"):
        embedder_registry.forget(fp)


async def _register(session, fingerprint: str) -> None:
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id="m", dims=DIMS, source="llm"),
    )


async def _set_registered_at(session, fingerprint: str, *, seconds_ago: int) -> None:
    await session.execute(
        text(
            "UPDATE embedders SET registered_at = now() - (:s * interval '1 second') "
            "WHERE fingerprint = :fp"
        ),
        {"s": seconds_ago, "fp": fingerprint},
    )


async def _file_blocks(session, *, project=PROJECT, texts=("content",)) -> tuple[str, list[str]]:
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session,
        project=project,
        content="\n\n".join(texts),
        parse=lambda: drafts,
        title="probe",
        source_type="note",
    )
    await session.flush()
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(ingest.document_id)},
    )).scalars().all()
    return str(ingest.document_id), [str(r) for r in rows]


async def _embed_blocks(session, fingerprint: str, block_ids: list[str]) -> None:
    table = child_table("block_embeddings", fingerprint)
    for block_id in block_ids:
        await session.execute(
            text(
                f"INSERT INTO {table} (block_id, fingerprint, embedding, created_at) "
                f"VALUES (CAST(:id AS uuid), :fp, CAST(:vec AS vector), now())"
            ),
            {"id": block_id, "fp": fingerprint, "vec": str([0.1] * DIMS)},
        )


async def _insert_memory(session, *, project=PROJECT) -> UUID:
    memory_id = new_id()
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, status) "
            "VALUES (CAST(:id AS uuid), 'seed', 'api', :project, 'active')"
        ),
        {"id": memory_id, "project": project},
    )
    return memory_id


async def _embed_memory(session, fingerprint: str, memory_id: str) -> None:
    table = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {table} (memory_id, fingerprint, embedding, created_at) "
            f"VALUES (CAST(:id AS uuid), :fp, CAST(:vec AS vector), now())"
        ),
        {"id": memory_id, "fp": fingerprint, "vec": str([0.1] * DIMS)},
    )


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
    await _register(session, "retired_fp")
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, "retired_fp", block_ids)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, "retired_fp", memory_id)
    await session.execute(
        text("UPDATE embedders SET retired_at = now() WHERE fingerprint = 'retired_fp'"),
    )

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result is None


@pytest.mark.asyncio
async def test_returns_a_fingerprint_holding_vectors_on_both_sides(session):
    await _register(session, FINGERPRINT)
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == FINGERPRINT


@pytest.mark.asyncio
async def test_the_newest_live_fingerprint_wins(session):
    await _register(session, FINGERPRINT)
    await _register(session, OTHER_FINGERPRINT)
    await _set_registered_at(session, FINGERPRINT, seconds_ago=20)
    await _set_registered_at(session, OTHER_FINGERPRINT, seconds_ago=10)

    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    await _embed_blocks(session, OTHER_FINGERPRINT, block_ids)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)
    await _embed_memory(session, OTHER_FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == OTHER_FINGERPRINT


@pytest.mark.asyncio
async def test_a_one_sided_fingerprint_is_skipped_in_favour_of_a_complete_one(session):
    await _register(session, FINGERPRINT)
    await _register(session, OTHER_FINGERPRINT)
    await _set_registered_at(session, FINGERPRINT, seconds_ago=20)
    await _set_registered_at(session, OTHER_FINGERPRINT, seconds_ago=10)

    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    await _embed_blocks(session, OTHER_FINGERPRINT, block_ids)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)
    # OTHER_FINGERPRINT (newer) never gets a memory vector: one-sided.

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == FINGERPRINT


@pytest.mark.asyncio
async def test_returns_none_when_every_live_fingerprint_is_one_sided(session):
    await _register(session, FINGERPRINT)

    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    # No memory embedded under FINGERPRINT at all.

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result is None


@pytest.mark.asyncio
async def test_a_memory_in_another_project_does_not_count(session):
    await _register(session, FINGERPRINT)
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    memory_id = await _insert_memory(session, project="t-document-similarity-other")
    await _embed_memory(session, FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result is None


@pytest.mark.asyncio
async def test_block_counterpart_excludes_the_queried_document_itself(session):
    await _register(session, FINGERPRINT)
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="block",
    )
    assert result is None


@pytest.mark.asyncio
async def test_block_counterpart_matches_another_documents_blocks(session):
    await _register(session, FINGERPRINT)
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    _other_document_id, other_block_ids = await _file_blocks(session, texts=("other content",))
    await _embed_blocks(session, FINGERPRINT, other_block_ids)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="block",
    )
    assert result == FINGERPRINT


@pytest.mark.asyncio
async def test_a_one_sided_fingerprint_missing_the_document_is_skipped(session):
    """The newer fingerprint has the counterpart but not the document itself;
    the older, complete fingerprint is returned instead — proving the
    zero-coverage guard skips rather than short-circuits."""
    await _register(session, FINGERPRINT)
    await _register(session, OTHER_FINGERPRINT)
    await _set_registered_at(session, FINGERPRINT, seconds_ago=20)
    await _set_registered_at(session, OTHER_FINGERPRINT, seconds_ago=10)

    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)
    # OTHER_FINGERPRINT (newer) gets a memory vector but never embeds the
    # queried document's own blocks.
    await _embed_memory(session, OTHER_FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == FINGERPRINT


@pytest.mark.asyncio
async def test_returns_none_when_the_only_live_fingerprint_misses_the_document(session):
    await _register(session, FINGERPRINT)
    document_id, _block_ids = await _file_blocks(session)
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)
    # The document's own blocks are never embedded under FINGERPRINT.

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result is None


@pytest.mark.asyncio
async def test_block_counterpart_does_not_cross_a_project_boundary(session):
    await _register(session, FINGERPRINT)
    document_id, block_ids = await _file_blocks(session)
    await _embed_blocks(session, FINGERPRINT, block_ids)
    _other_document_id, other_block_ids = await _file_blocks(
        session, project="t-document-similarity-other", texts=("other content",),
    )
    await _embed_blocks(session, FINGERPRINT, other_block_ids)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="block",
    )
    assert result is None


@pytest.mark.asyncio
async def test_full_document_coverage_beats_a_newer_partial_fingerprint(session):
    """The rotation case the docstring used to overclaim about.

    Both fingerprints hold a memory vector and at least one of this
    document's blocks, so the pre-2026-09-05 `EXISTS` resolver returned the
    newer one and compared against a third of the document. Coverage is
    counted now, so the older, complete partition wins.
    """
    await _register(session, FINGERPRINT)
    await _register(session, OTHER_FINGERPRINT)
    await _set_registered_at(session, FINGERPRINT, seconds_ago=20)
    await _set_registered_at(session, OTHER_FINGERPRINT, seconds_ago=10)

    document_id, block_ids = await _file_blocks(session, texts=("one", "two", "three"))
    await _embed_blocks(session, FINGERPRINT, block_ids)
    await _embed_blocks(session, OTHER_FINGERPRINT, block_ids[:1])
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)
    await _embed_memory(session, OTHER_FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == FINGERPRINT


@pytest.mark.asyncio
async def test_a_partial_fingerprint_is_still_served_when_none_is_complete(session):
    """Preference, not a requirement: half an answer under one defined basis
    beats no answer at all, which is what the fallback exists for."""
    await _register(session, FINGERPRINT)

    document_id, block_ids = await _file_blocks(session, texts=("one", "two", "three"))
    await _embed_blocks(session, FINGERPRINT, block_ids[:1])
    memory_id = await _insert_memory(session)
    await _embed_memory(session, FINGERPRINT, memory_id)

    result = await resolve_shared_fingerprint(
        session, document_id=document_id, project=PROJECT, counterpart="memory",
    )
    assert result == FINGERPRINT
