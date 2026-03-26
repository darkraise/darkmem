async def test_reason_without_pipeline(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/reason",
        json={"question": "What is darkmem?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert data["sources"] == []


async def test_reason_requires_auth(client):
    response = await client.post("/api/v1/memories/reason", json={"question": "test"})
    assert response.status_code in (401, 403)
