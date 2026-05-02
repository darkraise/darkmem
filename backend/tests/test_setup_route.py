"""Tests for the setup wizard router and the authenticated /system mirror."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.api.auth import hash_password
from app.models.audit import AuditLog
from app.models.code import Repository
from app.models.config import Config
from app.models.llm_config import LLMProfile, LLMProvider, LLMPurposeConfigRow


# ── status + require_uninitialized ────────────────────────────────────


@pytest.mark.asyncio
async def test_require_uninitialized_allows_when_no_password(client):
    response = await client.get("/api/v1/setup/status")
    assert response.status_code == 200
    assert response.json() == {"initialized": False}


@pytest.mark.asyncio
async def test_require_uninitialized_returns_403_after_setup(client, session):
    session.add(Config(
        key="admin_password_hash",
        value={"hash": hash_password("test-pw-12345")},
    ))
    await session.flush()

    response = await client.post(
        "/api/v1/setup/probe-models",
        json={"api_kind": "openai", "base_url": "https://api.example.com/v1", "api_key": "sk-x"},
    )
    assert response.status_code == 403


# ── probe-models ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_models_openai_uses_bearer_against_v1_models(client):
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json = lambda: {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
    mock_response.text = ""

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/setup/probe-models",
            json={
                "api_kind": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["models"] == ["gpt-4o", "gpt-4o-mini"]
    assert body["fetched_via"] == "openai_compat:/v1/models"
    assert body["error"] is None

    call = instance.get.await_args
    assert call.args[0] == "https://api.openai.com/v1/models"
    assert call.kwargs["headers"]["Authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
async def test_probe_models_anthropic_uses_x_api_key(client):
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json = lambda: {"data": [{"id": "claude-haiku-4-5"}]}
    mock_response.text = ""

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/setup/probe-models",
            json={
                "api_kind": "anthropic",
                "base_url": "https://api.anthropic.com/v1",
                "api_key": "sk-ant",
            },
        )

    assert response.status_code == 200
    headers = instance.get.await_args.kwargs["headers"]
    assert headers["x-api-key"] == "sk-ant"
    assert headers["anthropic-version"] == "2023-06-01"
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_probe_models_ollama_uses_native_tags(client):
    mock_response = AsyncMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json = lambda: {"models": [{"name": "qwen2.5:3b"}]}
    mock_response.text = ""

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/setup/probe-models",
            json={"api_kind": "ollama", "base_url": "http://localhost:11434/v1"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["models"] == ["qwen2.5:3b"]
    assert body["fetched_via"] == "ollama_native:/api/tags"
    call = instance.get.await_args
    assert call.args[0] == "http://localhost:11434/api/tags"


@pytest.mark.asyncio
async def test_probe_models_returns_error_on_http_failure(client):
    mock_response = AsyncMock()
    mock_response.is_success = False
    mock_response.status_code = 401
    mock_response.text = "invalid api key"

    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.get = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/setup/probe-models",
            json={
                "api_kind": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "wrong-key",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["models"] == []
    assert "401" in body["error"]


# ── filesystem browse ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fs_roots_returns_at_least_one_root(client):
    response = await client.get("/api/v1/setup/fs/roots")
    assert response.status_code == 200
    body = response.json()
    assert len(body["roots"]) >= 1
    assert all("path" in r and "label" in r for r in body["roots"])


@pytest.mark.asyncio
async def test_fs_list_returns_immediate_children(client, tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / "ignore.txt").write_text("not-a-dir")

    response = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(tmp_path)},
    )
    assert response.status_code == 200
    body = response.json()
    names = sorted(e["name"] for e in body["entries"])
    assert "alpha" in names and "beta" in names
    assert body["is_git"] is False
    assert body["blocked_reason"] is None


@pytest.mark.asyncio
async def test_fs_list_marks_git_directory(client, tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    (repo / ".git").mkdir()

    response = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(tmp_path), "detect_repos": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    repo_entry = next(e for e in body["entries"] if e["name"] == "myrepo")
    assert repo_entry["is_git"] is True


@pytest.mark.asyncio
async def test_fs_list_detect_repos_implies_must_not_be_repo(client, tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    (repo / ".git").mkdir()

    nav = await client.get("/api/v1/setup/fs/list", params={"path": str(repo)})
    assert nav.status_code == 200
    assert nav.json()["is_git"] is True

    confirm = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(repo), "detect_repos": "true"},
    )
    assert confirm.status_code == 422


@pytest.mark.asyncio
async def test_fs_list_rejects_blocklisted_paths(client, tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".ssh").mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

    response = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(fake_home / ".ssh")},
    )
    assert response.status_code == 422


# ── /api/v1/setup finalize ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_setup_finalize_password_only(client, session):
    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["password"]["ok"] is True
    assert body["llm"]["ok"] is True
    assert body["repos"]["ok"] is True

    set_cookie = response.headers.get("set-cookie", "")
    assert "darkmem_session=" in set_cookie

    config = (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none()
    assert config is not None

    audits = (await session.execute(select(AuditLog))).scalars().all()
    actions = {a.action for a in audits}
    assert "auth_setup" in actions and "setup_complete" in actions


@pytest.mark.asyncio
async def test_setup_finalize_with_llm(client, session):
    payload = {
        "password": "test-pw-12345",
        "llm": {
            "provider_name": "OpenAI",
            "api_kind": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "supports_embedding": True,
            "purposes": {
                "embedding":      {"model": "text-embedding-3-small"},
                "extraction":     {"model": "gpt-4o-mini"},
                "classification": {"model": "gpt-4o-mini"},
                "reasoning":      {"model": "gpt-4o", "reasoning": True},
            },
        },
    }
    response = await client.post("/api/v1/setup", json=payload)
    assert response.status_code == 200
    assert response.json()["llm"]["ok"] is True

    # Migrations seed default provider/profile/purpose rows; assert the
    # wizard's writes are present rather than that nothing else is.
    new_provider = (await session.execute(
        select(LLMProvider).where(LLMProvider.name == "OpenAI")
    )).scalar_one_or_none()
    assert new_provider is not None
    assert new_provider.api_key == "sk-test"
    assert new_provider.api_kind == "openai"

    profile_names = set((await session.execute(
        select(LLMProfile.name)
    )).scalars().all())
    for purpose in ("embedding", "extraction", "classification", "reasoning"):
        assert f"default-{purpose}" in profile_names

    # Each of the wizard's purposes should be linked to the new provider.
    for purpose in ("embedding", "extraction", "classification", "reasoning"):
        row = (await session.execute(
            select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == purpose)
        )).scalar_one_or_none()
        assert row is not None
        assert row.provider_id == new_provider.id


@pytest.mark.asyncio
async def test_setup_finalize_with_repos(client, session, tmp_path):
    base = tmp_path / "workspace"
    base.mkdir()
    repo_a = base / "repo-a"
    repo_a.mkdir()
    (repo_a / ".git").mkdir()
    repo_b = base / "repo-b"
    repo_b.mkdir()
    (repo_b / ".git").mkdir()

    payload = {
        "password": "test-pw-12345",
        "repos": {
            "base_path": str(base),
            "repos": [
                {"name": "repo-a", "sub_path": "repo-a"},
                {"name": "repo-b", "sub_path": "repo-b"},
            ],
        },
    }
    response = await client.post("/api/v1/setup", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["repos"]["ok"] is True
    assert sorted(body["repos_added"]) == ["repo-a", "repo-b"]
    assert body["repos_failed"] == []

    config = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    assert config is not None
    assert config.value["path"] == str(base.resolve())

    repos = (await session.execute(select(Repository))).scalars().all()
    assert len(repos) == 2
    assert all(r.provider == "local" for r in repos)
    # Wizard-imported repos must default to is_active=False so the
    # periodic loop doesn't immediately try to fetch every folder.
    # The user reviews and enables them per-repo from the Edit dialog.
    assert all(r.is_active is False for r in repos)


@pytest.mark.asyncio
async def test_setup_finalize_per_repo_failures_isolated(client, session, tmp_path):
    base = tmp_path / "workspace"
    base.mkdir()
    valid_repo = base / "valid"
    valid_repo.mkdir()
    (valid_repo / ".git").mkdir()

    payload = {
        "password": "test-pw-12345",
        "repos": {
            "base_path": str(base),
            "repos": [
                {"name": "valid", "sub_path": "valid"},
                {"name": "missing", "sub_path": "does-not-exist"},
            ],
        },
    }
    response = await client.post("/api/v1/setup", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["repos_added"] == ["valid"]
    assert len(body["repos_failed"]) == 1
    assert body["repos_failed"][0]["name"] == "missing"

    repos = (await session.execute(select(Repository))).scalars().all()
    assert len(repos) == 1


@pytest.mark.asyncio
async def test_setup_rejects_when_already_initialized(client, session):
    session.add(Config(
        key="admin_password_hash",
        value={"hash": hash_password("existing-pw")},
    ))
    await session.flush()

    response = await client.post(
        "/api/v1/setup",
        json={"password": "new-pw-12345"},
    )
    assert response.status_code == 403


# ── /api/v1/system/fs/* ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_system_fs_roots_requires_auth(client):
    response = await client.get("/api/v1/system/fs/roots")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_system_fs_list_works_with_auth(client, auth_headers, tmp_path):
    (tmp_path / "alpha").mkdir()
    response = await client.get(
        "/api/v1/system/fs/list",
        params={"path": str(tmp_path)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(e["name"] == "alpha" for e in response.json()["entries"])


# ── /api/v1/config/repos-path ────────────────────────────────────────


@pytest.mark.asyncio
async def test_repos_path_get_returns_null_when_unset(client, auth_headers):
    response = await client.get("/api/v1/config/repos-path", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"path": None}


@pytest.mark.asyncio
async def test_repos_path_put_persists(client, auth_headers, session, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    response = await client.put(
        "/api/v1/config/repos-path",
        json={"path": str(workspace)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["path"] == str(workspace.resolve())

    config = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    assert config is not None
    assert config.value["path"] == str(workspace.resolve())


@pytest.mark.asyncio
async def test_repos_path_put_rejects_repo_path(client, auth_headers, tmp_path):
    repo = tmp_path / "myrepo"
    repo.mkdir()
    (repo / ".git").mkdir()

    response = await client.put(
        "/api/v1/config/repos-path",
        json={"path": str(repo)},
        headers=auth_headers,
    )
    assert response.status_code == 422
