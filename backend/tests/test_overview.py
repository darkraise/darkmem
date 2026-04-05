from app.models.memory import Memory, Tag, memory_tags
from app.models.audit import AuditLog


async def test_overview_returns_counts(client, session, auth_headers):
    tag = Tag(name="test/overview")
    session.add(tag)
    await session.flush()

    m = Memory(content="overview test", source="api")
    m.tags.append(tag)
    session.add(m)
    await session.flush()

    resp = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["counts"]["memories"] >= 1
    assert data["counts"]["tags"] >= 1
    assert len(data["sources"]) >= 1
    assert len(data["top_tags"]) >= 1
    assert len(data["recent_memories"]) >= 1
    assert isinstance(data["activity"], list)
    assert isinstance(data["recent_errors"], int)

    mem = data["recent_memories"][0]
    assert "id" in mem
    assert "content" in mem
    assert "source" in mem
    assert "tags" in mem
    assert "created_at" in mem


async def test_overview_days_param(client, session, auth_headers):
    session.add(Memory(content="days test", source="api"))
    await session.flush()

    resp = await client.get("/api/v1/analytics/overview?days=30", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = await client.get("/api/v1/analytics/overview?days=999", headers=auth_headers)
    assert resp2.status_code == 200


async def test_overview_requires_auth(client):
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code in (401, 403)
