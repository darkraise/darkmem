async def test_create_repo_local(client, session, auth_headers, tmp_path):
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    resp = await client.post(
        "/api/v1/repos",
        json={"name": "test-repo", "local_path": str(repo_dir), "provider": "local"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-repo"
    assert data["provider"] == "local"
    assert data["is_active"] is True


async def test_list_repos(client, session, auth_headers, tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()
    await client.post("/api/v1/repos", json={"name": "repo-a", "local_path": str(a)}, headers=auth_headers)
    await client.post("/api/v1/repos", json={"name": "repo-b", "local_path": str(b)}, headers=auth_headers)
    resp = await client.get("/api/v1/repos", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_delete_repo(client, session, auth_headers, tmp_path):
    repo_dir = tmp_path / "del"
    repo_dir.mkdir()
    create_resp = await client.post(
        "/api/v1/repos",
        json={"name": "to-delete", "local_path": str(repo_dir)},
        headers=auth_headers,
    )
    repo_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert del_resp.status_code == 204
    get_resp = await client.get(f"/api/v1/repos/{repo_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_validate_local_path_rejects_blocked_tree(tmp_path):
    """Blocklist check is unit-tested directly so it works cross-platform.

    The HTTP route's existence check fires before the blocklist (the
    validator resolves and stat()s the path first), and ``/etc`` doesn't
    exist on Windows, so we bypass HTTP and exercise the validator.
    """
    import sys
    import pytest
    from app.services.repo_manager import validate_local_path

    if sys.platform.startswith("win"):
        pytest.skip("blocklist tree paths are POSIX-specific")
    with pytest.raises(ValueError, match="blocked"):
        validate_local_path("/etc")


def test_validate_local_path_rejects_missing(tmp_path):
    """Resolved path must exist; rejects typos before the indexer runs."""
    import pytest
    from app.services.repo_manager import validate_local_path

    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="does not exist"):
        validate_local_path(str(missing))


async def test_repos_require_auth(client):
    resp = await client.get("/api/v1/repos")
    assert resp.status_code in (401, 403)


def test_validate_local_path_rejects_git_repo_when_must_not_be_repo(tmp_path):
    """``must_not_be_repo`` blocks the chosen path itself being a repo."""
    import pytest
    from app.services.repo_manager import validate_local_path

    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    # Default behaviour still accepts repo paths (existing callers rely on it).
    result = validate_local_path(str(repo_dir))
    assert result == repo_dir.resolve()

    with pytest.raises(ValueError, match="is itself a git repository"):
        validate_local_path(str(repo_dir), must_not_be_repo=True)


def test_validate_local_path_accepts_parent_of_repos_when_must_not_be_repo(tmp_path):
    """``must_not_be_repo`` allows parents that contain child repos."""
    from app.services.repo_manager import validate_local_path

    parent = tmp_path / "workspace"
    parent.mkdir()
    (parent / "child-repo").mkdir()
    (parent / "child-repo" / ".git").mkdir()

    result = validate_local_path(str(parent), must_not_be_repo=True)
    assert result == parent.resolve()
