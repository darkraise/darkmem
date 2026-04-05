async def test_create_repo_local(client, session, auth_headers):
    resp = await client.post(
        "/api/v1/repos",
        json={"name": "test-repo", "local_path": "/tmp/test-repo", "provider": "local"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-repo"
    assert data["provider"] == "local"
    assert data["is_active"] is True


async def test_list_repos(client, session, auth_headers):
    await client.post("/api/v1/repos", json={"name": "repo-a", "local_path": "/tmp/a"}, headers=auth_headers)
    await client.post("/api/v1/repos", json={"name": "repo-b", "local_path": "/tmp/b"}, headers=auth_headers)
    resp = await client.get("/api/v1/repos", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_delete_repo(client, session, auth_headers):
    create_resp = await client.post(
        "/api/v1/repos",
        json={"name": "to-delete", "local_path": "/tmp/del"},
        headers=auth_headers,
    )
    repo_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_repos_require_auth(client):
    resp = await client.get("/api/v1/repos")
    assert resp.status_code in (401, 403)
