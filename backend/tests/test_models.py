from app.models.api_key import ApiKey
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
    # `write` was never a scope in doc 18 section 5's closed set and the model
    # no longer defaults to it; `capture` is the write half. Minting goes
    # through `app.services.api_keys.issue_key`, which is what validates the
    # scopes -- this stays an ORM smoke test of the row's shape.
    key = ApiKey(
        name="my-key", key_id="a" * 16, key_hash="abc123", scopes=["read", "capture"]
    )
    session.add(key)
    await session.flush()

    assert key.id is not None
    assert key.scopes == ["read", "capture"]
    assert key.revoked_at is None
