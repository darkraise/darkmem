from app.models.memory import Memory


async def test_paginated_search_returns_structure(client, session, auth_headers):
    for i in range(3):
        session.add(Memory(content=f"paginated test {i}", source="api"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["total"] >= 3
    assert len(data["items"]) == 2


async def test_paginated_search_offset(client, session, auth_headers):
    for i in range(5):
        session.add(Memory(content=f"offset test {i}", source="api"))
    await session.flush()

    page1 = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 0},
        headers=auth_headers,
    )
    page2 = await client.post(
        "/api/v1/memories/search/paginated",
        json={"limit": 2, "offset": 2},
        headers=auth_headers,
    )
    ids1 = {m["id"] for m in page1.json()["items"]}
    ids2 = {m["id"] for m in page2.json()["items"]}
    assert ids1.isdisjoint(ids2)


async def test_paginated_search_filters(client, session, auth_headers):
    session.add(Memory(content="filter by source", source="dashboard"))
    session.add(Memory(content="filter by source other", source="api"))
    await session.flush()

    resp = await client.post(
        "/api/v1/memories/search/paginated",
        json={"source": "dashboard", "limit": 50},
        headers=auth_headers,
    )
    data = resp.json()
    assert all(m["source"] == "dashboard" for m in data["items"])


async def test_paginated_search_requires_auth(client):
    resp = await client.post("/api/v1/memories/search/paginated", json={})
    assert resp.status_code in (401, 403)
