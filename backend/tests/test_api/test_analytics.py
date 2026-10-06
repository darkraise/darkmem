import uuid

import pytest

from app.services.events import EVENT_TYPES, record_event

pytestmark = pytest.mark.asyncio


async def test_get_stats(client, auth_headers):
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert "tags" in data
    assert isinstance(data["sources"], list)


async def test_get_stats_after_creating_memories(client, auth_headers):
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Test", "source": "pytest"}, headers=auth_headers,
    )
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    data = response.json()
    assert data["memories"] >= 1
    assert "pytest" in data["sources"]


async def test_pipeline_logs_reads_extracted_events(client, auth_headers, session):
    """GET /pipeline-logs used to filter on event_type='pipeline', a value

    outside EVENT_TYPES that nothing in the codebase ever wrote, so the
    endpoint returned empty forever regardless of how many batches actually
    ran. process_batch journals 'extracted' per memory (pipeline.py), so
    that is what the view must read to ever show anything.
    """
    assert "pipeline" not in EVENT_TYPES
    assert "extracted" in EVENT_TYPES

    memory_id = uuid.uuid4()
    await record_event(
        session,
        event_type="extracted",
        object_type="memory",
        object_id=memory_id,
        project="default",
        payload={
            "memory_id": str(memory_id),
            "embed": "ok", "extract": "ok", "vector": "ok", "graph": "partial",
            "outcome": "partial",
        },
    )
    await session.flush()

    response = await client.get("/api/v1/analytics/pipeline-logs", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert any(item["memory_id"] == str(memory_id) for item in items)
    matched = next(item for item in items if item["memory_id"] == str(memory_id))
    assert matched["details"]["outcome"] == "partial"


async def test_pipeline_logs_ignores_other_event_types(client, auth_headers, session):
    memory_id = uuid.uuid4()
    await record_event(
        session,
        event_type="created",
        object_type="memory",
        object_id=memory_id,
        project="default",
        payload={"unrelated": True},
    )
    await session.flush()

    response = await client.get("/api/v1/analytics/pipeline-logs", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert not any(item["memory_id"] == str(memory_id) for item in items)


async def test_pipeline_logs_follow_the_project_scope(client, auth_headers, session):
    """Activity -> Pipeline scoped to one project listed every project's runs."""
    scoped, other = uuid.uuid4(), uuid.uuid4()
    for memory_id, project in ((scoped, "webapp"), (other, "default")):
        await record_event(
            session,
            event_type="extracted",
            object_type="memory",
            object_id=memory_id,
            project=project,
            payload={"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok", "outcome": "completed"},
        )
    await session.flush()

    response = await client.get(
        "/api/v1/analytics/pipeline-logs", params={"project": "webapp", "limit": 500},
        headers=auth_headers,
    )
    assert response.status_code == 200
    ids = {item["memory_id"] for item in response.json()}
    assert str(scoped) in ids
    assert str(other) not in ids

    unscoped = await client.get(
        "/api/v1/analytics/pipeline-logs", params={"limit": 500}, headers=auth_headers,
    )
    assert {str(scoped), str(other)} <= {item["memory_id"] for item in unscoped.json()}
