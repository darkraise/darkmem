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


async def test_update_repo_interval_wakes_sync_loop(client, auth_headers, tmp_path):
    """Updating sync_interval_minutes must signal the periodic loop so the
    new cadence takes effect immediately instead of after the next tick."""
    from app.main import app

    repo_dir = tmp_path / "wake-test-repo"
    repo_dir.mkdir()
    create = await client.post(
        "/api/v1/repos",
        json={
            "name": "wake-test-repo",
            "local_path": str(repo_dir),
            "provider": "local",
            "sync_interval_minutes": 30,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    repo_id = create.json()["id"]

    # Drain any wake event the create handler may have set.
    app.state.repo_sync_wakeup.clear()

    # Updating an unrelated field (name) must NOT wake the loop.
    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"name": "wake-test-repo-renamed"},
        headers=auth_headers,
    )
    assert app.state.repo_sync_wakeup.is_set() is False

    # Changing sync_interval_minutes MUST wake the loop.
    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"sync_interval_minutes": 5},
        headers=auth_headers,
    )
    assert app.state.repo_sync_wakeup.is_set() is True

    app.state.repo_sync_wakeup.clear()

    # Toggling is_active MUST also wake the loop.
    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert app.state.repo_sync_wakeup.is_set() is True


async def test_update_repo_no_op_does_not_wake(client, auth_headers, tmp_path):
    """Re-PUTing the same interval value must not flip the wake event."""
    from app.main import app

    repo_dir = tmp_path / "noop-test-repo"
    repo_dir.mkdir()
    create = await client.post(
        "/api/v1/repos",
        json={
            "name": "noop-test-repo",
            "local_path": str(repo_dir),
            "provider": "local",
            "sync_interval_minutes": 15,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    repo_id = create.json()["id"]
    app.state.repo_sync_wakeup.clear()

    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"sync_interval_minutes": 15},
        headers=auth_headers,
    )
    assert app.state.repo_sync_wakeup.is_set() is False


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
