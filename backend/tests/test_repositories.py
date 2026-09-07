import uuid

import pytest
from sqlalchemy import text as sa_text

from app.models.memory import Memory, Tag
from app.repositories.relational import PostgresMemoryRepository, PostgresTagRepository


async def test_create_and_get_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Test content", source="test", source_agent=None, memory_type="fact", importance=0.8, metadata={})

    assert memory.id is not None
    assert memory.content == "Test content"

    fetched = await repo.get(memory.id)
    assert fetched is not None
    assert fetched.content == "Test content"


async def test_update_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Original", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    updated = await repo.update(memory.id, content="Updated")
    assert updated.content == "Updated"


async def test_delete_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="To delete", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    assert await repo.delete(memory.id) is True
    assert await repo.get(memory.id) is None
    assert await repo.delete(memory.id) is False


async def test_list_memories(session):
    repo = PostgresMemoryRepository(session)
    for i in range(3):
        await repo.create(content=f"Memory {i}", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    memories, total = await repo.list_memories(offset=0, limit=10)
    assert total == 3
    assert len(memories) == 3


async def test_set_and_search_tags(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Tagged", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(memory.id, ["project/test", "infra/services"])

    await session.refresh(memory, ["tags"])
    assert len(memory.tags) == 2

    results = await repo.search_by_tags(tags_any=["project/test"])
    assert len(results) == 1
    assert results[0].id == memory.id


async def test_search_by_tags_all(session):
    repo = PostgresMemoryRepository(session)
    m1 = await repo.create(content="Has both", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(m1.id, ["tag-a", "tag-b"])

    m2 = await repo.create(content="Has one", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(m2.id, ["tag-a"])

    results = await repo.search_by_tags(tags_all=["tag-a", "tag-b"])
    assert len(results) == 1
    assert results[0].id == m1.id


async def test_tag_get_or_create(session):
    repo = PostgresTagRepository(session)
    tag1 = await repo.get_or_create("project/test")
    tag2 = await repo.get_or_create("project/test")
    assert tag1.id == tag2.id
    assert tag1.category == "project"


async def test_prune_orphans_removes_unreferenced_tags(session):
    mem_repo = PostgresMemoryRepository(session)
    tag_repo = PostgresTagRepository(session)

    memory = await mem_repo.create(
        content="kept", source="test", source_agent=None,
        memory_type=None, importance=0.5, metadata={},
    )
    await mem_repo.set_tags(memory.id, ["in-use"])
    await tag_repo.get_or_create("orphan-a")
    await tag_repo.get_or_create("orphan-b")
    await session.flush()

    removed = await tag_repo.prune_orphans()

    assert removed == 2
    remaining = {t.name for t in await tag_repo.list_all()}
    assert remaining == {"in-use"}


async def _file_document(session, uri: str) -> uuid.UUID:
    document_id = uuid.uuid4()
    await session.execute(
        sa_text(
            "INSERT INTO documents (id, project, uri, title) "
            "VALUES (CAST(:id AS uuid), :project, :uri, :title)"
        ),
        {"id": str(document_id), "project": "default", "uri": uri, "title": uri},
    )
    return document_id


async def _link_document_tag(session, document_id: uuid.UUID, tag_id: int) -> None:
    await session.execute(
        sa_text(
            "INSERT INTO document_tags (document_id, tag_id) "
            "VALUES (CAST(:document_id AS uuid), CAST(:tag_id AS integer))"
        ),
        {"document_id": str(document_id), "tag_id": tag_id},
    )


@pytest.fixture
async def note_tagged(session):
    """A tag carried by one document and by no memory at all."""
    tag = await PostgresTagRepository(session).get_or_create("note-only")
    document_id = await _file_document(session, "notes/only.md")
    await _link_document_tag(session, document_id, tag.id)
    await session.flush()


@pytest.fixture
async def orphan_tag(session):
    await PostgresTagRepository(session).get_or_create("abandoned")
    await session.flush()


@pytest.fixture
async def doubly_tagged(session):
    """One tag on three memories and two documents.

    The two counts are deliberately unequal. At 2 and 2 the sum and the product
    coincide at 4, so a joined count over both link tables reports the summed
    answer by accident and the test it was written to catch passes."""
    mem_repo = PostgresMemoryRepository(session)
    tag = await PostgresTagRepository(session).get_or_create("shared")
    for i in range(3):
        memory = await mem_repo.create(
            content=f"shared {i}", source="test", source_agent=None,
            memory_type=None, importance=0.5, metadata={},
        )
        await mem_repo.set_tags(memory.id, ["shared"])
    for i in range(2):
        document_id = await _file_document(session, f"notes/shared-{i}.md")
        await _link_document_tag(session, document_id, tag.id)
    await session.flush()


async def test_a_note_only_tag_survives_the_sweep(session, note_tagged):
    """tag_orphan_cleanup runs hourly. Before this widening it deleted every
    tag with no memory_tags row, so a tag carried only by a note -- and its
    document_tags links, under the cascade -- vanished within the hour."""
    repo = PostgresTagRepository(session)
    await repo.prune_orphans()
    assert "note-only" in {t.name for t in await repo.list_all()}


async def test_the_histogram_counts_a_documents_tag(session, note_tagged):
    counts = {t.name: n for t, n in
              await PostgresTagRepository(session).get_with_counts()}
    assert counts["note-only"] == 1


async def test_a_tag_referenced_by_neither_is_still_swept(session, orphan_tag):
    """The widening must not turn the sweep off."""
    repo = PostgresTagRepository(session)
    assert await repo.prune_orphans() >= 1
    assert "abandoned" not in {t.name for t in await repo.list_all()}


async def test_the_count_sums_rather_than_multiplies(session, doubly_tagged):
    """Three memories and two documents is 5. A join across both link tables
    yields six rows, which every join-based spelling then reports as 6 or 10 --
    and each of those passes every single-reference test."""
    counts = {t.name: n for t, n in
              await PostgresTagRepository(session).get_with_counts()}
    assert counts["shared"] == 5
