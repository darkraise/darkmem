from app.models.api_key import ApiKey
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag


async def test_create_memory(session):
    memory = Memory(content="Test memory", source="test")
    session.add(memory)
    await session.flush()

    assert memory.id is not None
    assert memory.content == "Test memory"
    assert memory.source == "test"
    assert memory.importance == 0.5
    assert memory.is_archived is False
    assert memory.metadata_ == {}


async def test_memory_with_tags(session):
    tag = Tag(name="project/test", category="project")
    session.add(tag)
    await session.flush()

    memory = Memory(content="Tagged memory", source="test", tags=[tag])
    session.add(memory)
    await session.flush()

    assert len(memory.tags) == 1
    assert memory.tags[0].name == "project/test"


async def test_create_api_key(session):
    key = ApiKey(name="my-key", key_hash="abc123", scopes=["read", "write"])
    session.add(key)
    await session.flush()

    assert key.id is not None
    assert key.scopes == ["read", "write"]


async def test_create_audit_log(session):
    entry = AuditLog(action="create", details={"test": True})
    session.add(entry)
    await session.flush()

    assert entry.id is not None
    assert entry.action == "create"
