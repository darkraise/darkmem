from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService


async def test_create_memory(session):
    svc = MemoryService(session)
    data = MemoryCreate(content="Service test", tags=["project/test"], source="test")
    memory = await svc.create_memory(data, api_key_id=None)

    assert memory.content == "Service test"
    assert len(memory.tags) == 1
    assert memory.tags[0].name == "project/test"


async def test_get_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Get me", source="test"), api_key_id=None)
    fetched = await svc.get_memory(created.id)

    assert fetched is not None
    assert fetched.id == created.id


async def test_update_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Original", source="test"), api_key_id=None)
    updated = await svc.update_memory(created.id, MemoryUpdate(content="Updated"), api_key_id=None)

    assert updated.content == "Updated"


async def test_update_tags(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Tag test", tags=["tag-a"], source="test"), api_key_id=None)
    updated = await svc.update_memory(created.id, MemoryUpdate(tags=["tag-b", "tag-c"]), api_key_id=None)

    tag_names = [t.name for t in updated.tags]
    assert "tag-b" in tag_names
    assert "tag-c" in tag_names
    assert "tag-a" not in tag_names


async def test_delete_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Delete me", source="test"), api_key_id=None)

    assert await svc.delete_memory(created.id, api_key_id=None) is True
    assert await svc.get_memory(created.id) is None


async def test_delete_memory_prunes_orphaned_tags(session):
    from sqlalchemy import func, select
    from app.models.memory import Tag

    svc = MemoryService(session)
    created = await svc.create_memory(
        MemoryCreate(content="only memory", tags=["solo-tag"], source="test"),
        api_key_id=None,
    )

    await svc.delete_memory(created.id, api_key_id=None)

    tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
    assert tag_count == 0


async def test_delete_memory_keeps_tag_used_by_another_memory(session):
    from app.repositories.relational import PostgresTagRepository

    svc = MemoryService(session)
    m1 = await svc.create_memory(
        MemoryCreate(content="first", tags=["shared"], source="test"), api_key_id=None
    )
    await svc.create_memory(
        MemoryCreate(content="second", tags=["shared"], source="test"), api_key_id=None
    )

    await svc.delete_memory(m1.id, api_key_id=None)

    remaining = {t.name for t in await PostgresTagRepository(session).list_all()}
    assert "shared" in remaining


async def test_search_memories(session):
    svc = MemoryService(session)
    await svc.create_memory(MemoryCreate(content="Alpha", tags=["scope/a"], source="test"), api_key_id=None)
    await svc.create_memory(MemoryCreate(content="Beta", tags=["scope/b"], source="test"), api_key_id=None)

    results = await svc.search_memories(MemorySearchRequest(tags_any=["scope/a"]))
    assert len(results) == 1
    assert results[0].content == "Alpha"


async def test_search_by_text_query(session):
    svc = MemoryService(session)
    await svc.create_memory(MemoryCreate(content="PostgreSQL is the best database", source="test"), api_key_id=None)
    await svc.create_memory(MemoryCreate(content="Redis is a cache", source="test"), api_key_id=None)

    results = await svc.search_memories(MemorySearchRequest(query="PostgreSQL"))
    assert len(results) == 1
    assert "PostgreSQL" in results[0].content


async def test_list_memories(session):
    svc = MemoryService(session)
    for i in range(3):
        await svc.create_memory(MemoryCreate(content=f"Item {i}", source="test"), api_key_id=None)

    memories, total = await svc.list_memories(offset=0, limit=10)
    assert total == 3
    assert len(memories) == 3
