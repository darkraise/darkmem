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


