"""Tests for the setup wizard router and the authenticated /system mirror."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text

from app.api.auth import hash_password
from app.models.code import Repository
from app.models.config import Config
from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow


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

    actions = set((await session.execute(
        text("SELECT event_type FROM events")
    )).scalars().all())
    assert "auth_setup" in actions and "setup_complete" in actions


@pytest.mark.asyncio
async def test_setup_finalize_with_llm(client, session):
    """The wizard now seeds the full default provider / profile menu, writes
    the user's declared providers, and overlays each purpose's chosen
    provider_name + model on top. Asserts cover (a) the six canonical
    purpose rows land, and (b) the user's model and provider (api_key, kind,
    base_url included) are overlaid inline on each — there is no profile row
    to resolve through any more (doc 04 §7), only the provider indirection
    (owner ruling 2026-08-20)."""
    payload = {
        "password": "test-pw-12345",
        "llm": {
            "providers": [
                {"name": "user-openai", "api_kind": "openai",
                 "base_url": "https://api.openai.com/v1", "api_key": "sk-test"},
            ],
            "purposes": {
                "embedding":      {"provider_name": "user-openai", "model": "text-embedding-3-small"},
                "extraction":     {"provider_name": "user-openai", "model": "gpt-4o-mini"},
                "classification": {"provider_name": "user-openai", "model": "gpt-4o-mini"},
                "reasoning":      {"provider_name": "user-openai", "model": "gpt-4o", "reasoning": True},
            },
        },
    }
    response = await client.post("/api/v1/setup", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["llm"]["ok"] is True

    # The profile/ml-profile indirection stays gone (doc 04 §7); the
    # provider indirection is back (owner ruling 2026-08-20), so the
    # connection details resolve through the referenced llm_providers row
    # rather than living inline on the purpose row.

    # (a) the six canonical purposes each landed a row.
    rows = (await session.execute(select(LLMPurposeConfigRow))).scalars().all()
    by_purpose = {r.purpose: r for r in rows}
    for purpose in (
        "embedding", "extraction", "classification",
        "reasoning", "summarization", "reranker",
    ):
        assert purpose in by_purpose, f"missing purpose row {purpose}"

    # (b) the user's choices are overlaid, api_key included, on the
    # provider row each purpose references.
    for purpose, expected_model in [
        ("embedding", "text-embedding-3-small"),
        ("extraction", "gpt-4o-mini"),
        ("classification", "gpt-4o-mini"),
        ("reasoning", "gpt-4o"),
    ]:
        row = by_purpose[purpose]
        assert row.model == expected_model
        assert row.provider_name == "user-openai"
        provider = (await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == row.provider_name)
        )).scalar_one()
        assert provider.api_kind == "openai"
        assert provider.api_key == "sk-test"
        assert provider.base_url


@pytest.mark.asyncio
async def test_setup_accepts_a_provider_list(client, session):
    resp = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {
            "providers": [
                {"name": "my-ds", "api_kind": "deepseek",
                 "base_url": "https://api.deepseek.com/v1", "api_key": "sk-x"},
            ],
            "purposes": {
                "extraction": {"provider_name": "my-ds", "model": "deepseek-v4-flash"},
            },
        },
    })
    assert resp.status_code == 200
    row = (await session.execute(text(
        "SELECT provider_name FROM llm_purpose_configs WHERE purpose='extraction'"
    ))).scalar_one()
    assert row == "my-ds"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider, field", [
    ({"name": "my/ds", "base_url": "https://api.deepseek.com/v1"}, "name"),
    ({"name": "my-ds", "base_url": "api.deepseek.com"}, "base_url"),
])
async def test_setup_refuses_unusable_provider_fields(client, session, provider, field):
    """The wizard writes the same rows the settings door does, under the same
    rules: a provider it created must stay editable there."""
    resp = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {
            "providers": [{"api_kind": "deepseek", "api_key": "sk-x", **provider}],
            "purposes": {
                "extraction": {"provider_name": provider["name"], "model": "m"},
            },
        },
    })
    assert resp.status_code == 422
    assert field in resp.json()["detail"]
    assert (await session.execute(text(
        "SELECT count(*) FROM config WHERE key = 'admin_password_hash'"
    ))).scalar_one() == 0


@pytest.mark.asyncio
async def test_setup_refuses_a_provider_named_after_a_seeded_one(client, session):
    """`verification-judge` is seeded by DEFAULT_PROVIDER_ROWS before the
    user's own providers are written. Without a name guard, a submitted
    provider sharing that name would resolve through `.get()` to the
    seeded row and overwrite its base_url/api_kind — the judge's frozen
    identity fields on the authenticated door — from this unauthenticated
    one. Reproduces the exposure the finding describes: a re-opened setup
    replaying a poisoned payload against a database that already carries
    the seeded row from an earlier run."""
    first = await client.post(
        "/api/v1/setup",
        json={"password": "correct-horse-battery-staple", "llm": {"purposes": {}}},
    )
    assert first.status_code == 200

    seeded_before = (await session.execute(
        select(LLMProviderRow).where(LLMProviderRow.name == "verification-judge")
    )).scalar_one()
    api_kind_before, base_url_before = seeded_before.api_kind, seeded_before.base_url

    admin_row = (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one()
    await session.delete(admin_row)
    await session.commit()

    resp = await client.post("/api/v1/setup", json={
        "password": "second-pw-1234567",
        "llm": {
            "providers": [
                {"name": "verification-judge", "api_kind": "deepseek",
                 "base_url": "https://api.deepseek.com/v1", "api_key": "sk-poison"},
            ],
            "purposes": {
                "extraction": {"provider_name": "verification-judge", "model": "deepseek-v4-flash"},
            },
        },
    })
    assert resp.status_code == 422
    assert "verification-judge" in resp.json()["detail"]

    seeded_after = (await session.execute(
        select(LLMProviderRow).where(LLMProviderRow.name == "verification-judge")
    )).scalar_one()
    assert seeded_after.api_kind == api_kind_before
    assert seeded_after.base_url == base_url_before


@pytest.mark.asyncio
async def test_a_refused_payload_leaves_setup_reachable(client, session):
    """The refusal has to land before the password commit.

    ``require_uninitialized`` closes every wizard endpoint the moment
    ``admin_password_hash`` exists, so a validation error raised after step 1
    would leave an honest operator who picked a colliding provider name with a
    half-finalized install, one 422 and a 403 on every retry.
    """
    refused = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {
            "providers": [
                {"name": "ollama-local", "api_kind": "openai",
                 "base_url": "http://localhost:11434/v1"},
            ],
            "purposes": {
                "extraction": {"provider_name": "ollama-local", "model": "m"},
            },
        },
    })
    assert refused.status_code == 422

    assert (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none() is None

    status = await client.get("/api/v1/setup/status")
    assert status.status_code == 200
    assert status.json()["initialized"] is False

    retry = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {"purposes": {
            "extraction": {"provider_name": "ollama-local", "model": "m"},
        }},
    })
    assert retry.status_code == 200, retry.text


@pytest.mark.asyncio
async def test_setup_refuses_pointing_a_purpose_at_the_judge_provider(
    client, session
):
    """The exclusivity ``POST /api/v1/config/llm`` enforces has to hold here too.

    The payload declares no provider by that name, so the reserved-name guard
    never sees it — yet finalize would happily write the purpose row, creating
    on the unauthenticated door the shared state the authenticated one answers
    409 to.
    """
    resp = await client.post("/api/v1/setup", json={
        "password": "correct-horse-battery-staple",
        "llm": {"purposes": {
            "extraction": {"provider_name": "verification-judge", "model": "m"},
        }},
    })
    assert resp.status_code == 409
    assert "verification-judge" in resp.json()["detail"]

    assert (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none() is None
    assert (await session.execute(select(LLMPurposeConfigRow))).scalars().all() == []


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
    # Wizard-imported repos must default to every indexing mode off so the
    # periodic loop doesn't immediately try to fetch or index every folder.
    # The user reviews and arms them per-repo from the Edit dialog.
    assert all(r.fetch_enabled is False for r in repos)
    assert all(r.index_on_commit_enabled is False for r in repos)


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
