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
    assert data["fetch_enabled"] is False
    assert data["index_on_commit_enabled"] is False


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


async def test_update_repo_arming_wakes_sync_loop(client, auth_headers, tmp_path):
    """Arming a recurring lane must signal the repo_sync job's loop so the
    new state takes effect immediately instead of after the next tick."""
    from app.main import app

    repo_dir = tmp_path / "wake-test-repo"
    repo_dir.mkdir()
    create = await client.post(
        "/api/v1/repos",
        json={
            "name": "wake-test-repo",
            "local_path": str(repo_dir),
            "provider": "local",
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

    # Arming index_on_commit_enabled MUST wake the loop.
    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"index_on_commit_enabled": True},
        headers=auth_headers,
    )
    assert app.state.repo_sync_wakeup.is_set() is True


async def test_update_repo_rejects_an_explicit_null_on_a_not_null_field(
    client, auth_headers, tmp_path,
):
    """`RepoManager.update` dumps with `exclude_unset=True`, which counts an
    explicit null as set. Every field below is backed by a NOT NULL column, so
    without the schema guard the null reaches the database and the caller's bad
    request comes back as a 500."""
    repo_dir = tmp_path / "null-test-repo"
    repo_dir.mkdir()
    create = await client.post(
        "/api/v1/repos",
        json={"name": "null-test-repo", "local_path": str(repo_dir), "provider": "local"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    repo_id = create.json()["id"]

    for field in (
        "name", "default_branch", "fetch_enabled", "fetch_interval_seconds",
        "index_on_commit_enabled", "commit_poll_seconds", "index_uncommitted",
    ):
        resp = await client.put(
            f"/api/v1/repos/{repo_id}", json={field: None}, headers=auth_headers,
        )
        assert resp.status_code == 422, f"{field} -> {resp.status_code}"

    # git_account_id is the nullable one: an explicit null clears the account
    # and must stay a legal request.
    resp = await client.put(
        f"/api/v1/repos/{repo_id}", json={"git_account_id": None}, headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_mark_periodic_sync_failure_disables_index_on_commit(session, tmp_path):
    """A failed periodic sync must record the error AND set
    index_on_commit_enabled=False so the polling worker stops retrying every
    tick."""
    from app.services.repo_manager import RepoManager
    from app.schemas.code import RepoCreate
    from app.models.code import Repository

    repo_dir = tmp_path / "circuit-breaker-repo"
    repo_dir.mkdir()
    manager = RepoManager(session)
    repo = await manager.create(RepoCreate(
        name="circuit-breaker-repo",
        local_path=str(repo_dir),
        provider="local",
        index_on_commit_enabled=True,
    ))
    assert repo.index_on_commit_enabled is True
    assert repo.status == "ready"

    # Simulate a fetch failure with an error string that includes an
    # embedded auth token — the helper must sanitize before persisting.
    err = RuntimeError(
        "git fetch failed: https://x-access-token:ghp_secret123@github.com/me/x.git"
    )
    updated = await manager.mark_periodic_sync_failure(repo.id, err)

    assert updated is not None
    assert updated.index_on_commit_enabled is False
    assert updated.status == "error"
    assert "git fetch failed" in (updated.status_message or "")
    assert "ghp_secret123" not in (updated.status_message or "")
    assert "x-access-token:***@" in (updated.status_message or "")

    # Round-trip: the next loop iteration filters by
    # index_on_commit_enabled=True and this repo must now be excluded.
    from sqlalchemy import select as sa_select
    fresh = (await session.execute(
        sa_select(Repository).where(Repository.index_on_commit_enabled == True)  # noqa: E712
    )).scalars().all()
    assert all(r.id != repo.id for r in fresh)


async def test_add_git_safe_directory_runs_correct_command(tmp_path, monkeypatch):
    """Verify the helper invokes git config --global --add safe.directory <path>."""
    from app.services.repo_manager import add_git_safe_directory
    import subprocess

    captured = {}

    class FakeResult:
        returncode = 0
        stderr = b""
        stdout = b""

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["timeout"] = kwargs.get("timeout")
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    target = tmp_path / "some-repo"
    target.mkdir()
    ok = await add_git_safe_directory(target)

    assert ok is True
    assert captured["cmd"] == [
        "git", "config", "--global", "--add", "safe.directory", str(target),
    ]
    assert captured["timeout"] == 10


async def test_add_git_safe_directory_returns_false_on_failure(tmp_path, monkeypatch):
    """Subprocess errors must NOT crash the caller — best-effort only."""
    from app.services.repo_manager import add_git_safe_directory
    import subprocess

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git is not installed in this environment")

    monkeypatch.setattr(subprocess, "run", fake_run)

    target = tmp_path / "some-repo"
    target.mkdir()
    ok = await add_git_safe_directory(target)
    assert ok is False


async def test_mark_periodic_sync_failure_returns_none_for_missing(session):
    """Calling the helper with an unknown repo_id is a no-op, not a crash."""
    import uuid
    from app.services.repo_manager import RepoManager

    manager = RepoManager(session)
    result = await manager.mark_periodic_sync_failure(
        uuid.uuid4(), RuntimeError("anything"),
    )
    assert result is None


async def test_update_repo_no_op_does_not_wake(client, auth_headers, tmp_path):
    """Re-PUTing the same (unarmed) value must not flip the wake event."""
    from app.main import app

    repo_dir = tmp_path / "noop-test-repo"
    repo_dir.mkdir()
    create = await client.post(
        "/api/v1/repos",
        json={
            "name": "noop-test-repo",
            "local_path": str(repo_dir),
            "provider": "local",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    repo_id = create.json()["id"]
    app.state.repo_sync_wakeup.clear()

    await client.put(
        f"/api/v1/repos/{repo_id}",
        json={"index_on_commit_enabled": False},
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


def _git(cwd, *args) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=test@test.local", "-c", "user.name=Test", *args],
        cwd=str(cwd), check=True, capture_output=True,
    )


def _head(cwd) -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(cwd), capture_output=True, text=True,
    ).stdout.strip()


def _upstream_and_checkout(tmp_path):
    """An upstream repo one commit ahead of the operator's own clone of it.

    This is the shape the setup wizard's folder picker registers: a
    ``local_path`` repo whose ``origin`` remote resolves and fetches. The
    remote-less checkouts in ``test_code_reconcile.py`` never reach the
    fetch-succeeded branch of ``pull_repo`` at all.
    """
    import subprocess

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "app.py").write_text("VERSION = 1\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-q", "-m", "one")

    checkout = tmp_path / "checkout"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(checkout)],
        check=True, capture_output=True,
    )

    (upstream / "shipped.py").write_text("SHIPPED = True\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-q", "-m", "two")
    return upstream, checkout


async def test_pull_repo_never_rewinds_a_local_checkout(session, tmp_path):
    """`pull_repo` must not discard work in a tree the app does not own.

    `local_path` points at the operator's own checkout and `git reset --hard`
    moves the branch ref as well as the working tree, so a repo registered
    with a live `origin` lost both the uncommitted edit and the unpushed
    commit on the next `repo_sync` or `code_reconcile` tick -- the second of
    those being the job whose whole purpose is to notice that edit.
    """
    from app.models.code import Repository
    from app.services.repo_manager import RepoManager

    _, checkout = _upstream_and_checkout(tmp_path)

    (checkout / "wip.py").write_text("WIP = True\n", encoding="utf-8")
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "-q", "-m", "operator work, not pushed")
    operator_head = _head(checkout)
    edit = "VERSION = 1  # operator edit\n"
    (checkout / "app.py").write_text(edit, encoding="utf-8")

    repo = Repository(
        name="operator-checkout", local_path=str(checkout), default_branch="main",
    )
    session.add(repo)
    await session.flush()

    await RepoManager(session).pull_repo(repo)

    assert (checkout / "app.py").read_text(encoding="utf-8") == edit
    assert (checkout / "wip.py").exists()
    assert _head(checkout) == operator_head


async def test_pull_repo_fast_forwards_a_clean_local_checkout(session, tmp_path):
    """The other half of the same branch: a checkout holding nothing of its
    own still tracks its remote, so refusing to rewind must not turn a
    registered folder's auto-sync into a permanent no-op."""
    from app.models.code import Repository
    from app.services.repo_manager import RepoManager

    upstream, checkout = _upstream_and_checkout(tmp_path)

    repo = Repository(
        name="clean-checkout", local_path=str(checkout), default_branch="main",
    )
    session.add(repo)
    await session.flush()

    sha = await RepoManager(session).pull_repo(repo)

    assert sha == _head(upstream)
    assert (checkout / "shipped.py").exists()
