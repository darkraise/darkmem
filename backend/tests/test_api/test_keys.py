import pytest


pytestmark = pytest.mark.asyncio


async def test_create_api_key(client, auth_headers):
    response = await client.post(
        "/api/v1/keys",
        json={"name": "new-key", "scopes": ["read"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new-key"
    assert data["scopes"] == ["read"]
    assert data["raw_key"].startswith("dm_")


async def test_list_api_keys(client, auth_headers):
    response = await client.get("/api/v1/keys", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_delete_api_key(client, auth_headers):
    create = await client.post("/api/v1/keys", json={"name": "ephemeral"}, headers=auth_headers)
    key_id = create.json()["id"]

    response = await client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
    assert response.status_code == 204


async def test_keys_require_admin_scope(client, session):
    from app.api.auth import generate_api_key
    from app.models.api_key import ApiKey

    raw_key, key_hash = generate_api_key()
    key = ApiKey(name="non-admin", key_hash=key_hash, scopes=["read", "write"])
    session.add(key)
    await session.flush()

    headers = {"Authorization": f"Bearer {raw_key}"}
    response = await client.get("/api/v1/keys", headers=headers)
    assert response.status_code == 403
