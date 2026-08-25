"""Git forge accounts: CRUD, the default invariant, and repo token resolution."""
import uuid

import httpx
import pytest

from app.models.code import Repository
from app.models.config import Config
from app.models.git_account import GitAccount
from app.schemas.code import RepoCreate, RepoUpdate
from app.schemas.git_account import GitAccountCreate, GitAccountUpdate
from app.services import git_accounts as git_accounts_module
from app.services.git_accounts import (
    GitAccountError,
    GitAccountInUse,
    GitAccountService,
    token_hint,
    verify_token,
)
from app.services.repo_manager import RepoManager

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Verification is mocked at the transport, not at verify_token, so the header
# ladder, the identity field and the scope header are all exercised for real.
# --------------------------------------------------------------------------
def _stub_transport(handler):
    """Swap the module's AsyncClient for one bound to a MockTransport.

    The real class is captured before the swap and used to build the stub, so
    the replacement never re-enters itself.
    """
    real_client_cls = git_accounts_module.httpx.AsyncClient

    class _Patch:
        def __enter__(self):
            def _factory(*args, **kwargs):
                kwargs["transport"] = httpx.MockTransport(handler)
                return real_client_cls(*args, **kwargs)

            git_accounts_module.httpx.AsyncClient = _factory
            return self

        def __exit__(self, *exc):
            git_accounts_module.httpx.AsyncClient = real_client_cls
            return False

    return _Patch()


def _ok(username="octocat", scopes="repo, read:org", field=None):
    """A forge identity response.

    Carries both vendors' identity fields unless one is named, so the helper
    works for either provider without the caller knowing which key it reads.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {}
        if scopes is not None:
            headers["x-oauth-scopes"] = scopes
        body = {field: username} if field else {"login": username, "username": username}
        return httpx.Response(200, json=body, headers=headers)

    return handler


def _status(code: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, json={"message": "nope"})

    return handler


async def _make_account(session, label="personal", token="ghp_aaaabbbbcccc1234", **kw):
    with _stub_transport(_ok(username=kw.pop("username", "octocat"))):
        return await GitAccountService(session).create(
            GitAccountCreate(label=label, token=token, **kw)
        )


# --------------------------------------------------------------------------
# verify_token
# --------------------------------------------------------------------------
async def test_verify_token_reads_identity_and_scopes():
    with _stub_transport(_ok(username="alice", scopes="repo")):
        host, username, scopes = await verify_token("tok", "github")
    assert (host, username, scopes) == ("github.com", "alice", "repo")


async def test_verify_token_targets_the_enterprise_api_base():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"login": "alice"})

    with _stub_transport(handler):
        await verify_token("tok", "github", "git.example.com")
    assert seen["url"] == "https://git.example.com/api/v3/user"
    assert seen["auth"] == "Bearer tok"


async def test_verify_token_reads_gitlabs_own_identity_field():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"username": "bob", "login": "wrong"})

    with _stub_transport(handler):
        host, username, scopes = await verify_token("tok", "gitlab")
    assert seen["url"] == "https://gitlab.com/api/v4/user"
    assert (host, username, scopes) == ("gitlab.com", "bob", None)


@pytest.mark.parametrize("code,expected", [(401, 422), (403, 422), (500, 502)])
async def test_verify_token_maps_forge_rejection_to_a_status(code, expected):
    with _stub_transport(_status(code)):
        with pytest.raises(GitAccountError) as exc:
            await verify_token("tok", "github")
    assert exc.value.status_code == expected


async def test_verify_token_reports_an_unreachable_forge_as_502():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with _stub_transport(handler):
        with pytest.raises(GitAccountError) as exc:
            await verify_token("tok", "github")
    assert exc.value.status_code == 502


async def test_a_fine_grained_pat_leaves_scopes_null():
    """GitHub omits X-OAuth-Scopes for fine-grained PATs; that is not a failure."""
    with _stub_transport(_ok(scopes=None)):
        _, _, scopes = await verify_token("github_pat_x", "github")
    assert scopes is None


# --------------------------------------------------------------------------
# create / update / delete
# --------------------------------------------------------------------------
async def test_create_stores_the_forge_reported_username_not_the_label(session):
    account = await _make_account(session, label="Work", username="octocat")
    assert account.username == "octocat"
    assert account.label == "Work"
    assert account.last_verified_at is not None


async def test_create_refuses_a_token_the_forge_rejects(session):
    with _stub_transport(_status(401)):
        with pytest.raises(GitAccountError) as exc:
            await GitAccountService(session).create(
                GitAccountCreate(label="bad", token="nope")
            )
    assert exc.value.status_code == 422
    assert await GitAccountService(session).list() == []


async def test_the_first_account_for_a_forge_becomes_its_default(session):
    account = await _make_account(session, label="only")
    assert account.is_default is True


async def test_only_one_default_per_provider_and_host(session):
    first = await _make_account(session, label="one")
    second = await _make_account(session, label="two", is_default=True)
    await session.refresh(first)
    assert second.is_default is True
    assert first.is_default is False


async def test_a_second_host_carries_its_own_default(session):
    dotcom = await _make_account(session, label="cloud")
    enterprise = await _make_account(session, label="work", host="git.example.com")
    await session.refresh(dotcom)
    # Both are defaults; the partial unique index is scoped to (provider, host).
    assert dotcom.is_default is True
    assert enterprise.is_default is True

    service = GitAccountService(session)
    assert (await service.get_default("github", "git.example.com")).id == enterprise.id
    assert (await service.get_default("github", "github.com")).id == dotcom.id


async def test_get_default_without_a_host_prefers_the_vendors_own(session):
    await _make_account(session, label="work", host="git.example.com")
    dotcom = await _make_account(session, label="cloud")
    resolved = await GitAccountService(session).get_default("github")
    assert resolved.id == dotcom.id


async def test_duplicate_labels_on_one_host_are_refused(session):
    await _make_account(session, label="personal")
    with pytest.raises(GitAccountError) as exc:
        await _make_account(session, label="personal", token="ghp_other")
    assert exc.value.status_code == 409


async def test_two_tokens_for_one_username_are_allowed(session):
    """A read-only and a write token, or an overlap during rotation."""
    read = await _make_account(session, label="read-only", username="octocat")
    write = await _make_account(
        session, label="write", token="ghp_second", username="octocat",
    )
    assert read.username == write.username == "octocat"
    assert read.id != write.id


async def test_relabelling_does_not_re_verify(session):
    """A host with no outbound network must still be able to rename an account."""
    account = await _make_account(session, label="old")

    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError("update must not re-verify when the token is unchanged")

    with _stub_transport(explode):
        updated = await GitAccountService(session).update(
            account.id, GitAccountUpdate(label="new")
        )
    assert updated.label == "new"


async def test_a_token_change_re_verifies_and_refreshes_the_username(session):
    account = await _make_account(session, label="rotating", username="octocat")
    with _stub_transport(_ok(username="octocat-renamed", scopes="repo")):
        updated = await GitAccountService(session).update(
            account.id, GitAccountUpdate(token="ghp_rotated")
        )
    assert updated.token == "ghp_rotated"
    assert updated.username == "octocat-renamed"


async def test_a_rejected_rotation_leaves_the_old_token_in_place(session):
    account = await _make_account(session, label="rotating", token="ghp_original")
    with _stub_transport(_status(401)):
        with pytest.raises(GitAccountError):
            await GitAccountService(session).update(
                account.id, GitAccountUpdate(token="ghp_bad")
            )
    # Verification runs before any assignment, so the row is never mutated —
    # there is nothing for a rollback to undo.
    await session.refresh(account)
    assert account.token == "ghp_original"


async def test_delete_refuses_while_a_repo_still_uses_the_account(session):
    account = await _make_account(session, label="in-use")
    session.add(Repository(
        name="repo-a", url="https://github.com/o/a", provider="github",
        default_branch="main", auto_sync=True, status="ready",
        git_account_id=account.id,
    ))
    await session.flush()

    with pytest.raises(GitAccountInUse) as exc:
        await GitAccountService(session).delete(account.id)
    assert exc.value.status_code == 409
    assert [r["name"] for r in exc.value.repos] == ["repo-a"]


async def test_delete_with_reassign_moves_the_repos(session):
    doomed = await _make_account(session, label="doomed")
    keeper = await _make_account(session, label="keeper", token="ghp_keeper")
    repo = Repository(
        name="repo-a", url="https://github.com/o/a", provider="github",
        default_branch="main", auto_sync=True, status="ready",
        git_account_id=doomed.id,
    )
    session.add(repo)
    await session.flush()

    assert await GitAccountService(session).delete(doomed.id, reassign_to=keeper.id)
    await session.refresh(repo)
    assert repo.git_account_id == keeper.id


async def test_deleting_the_default_promotes_a_successor(session):
    first = await _make_account(session, label="first")
    second = await _make_account(session, label="second", token="ghp_second")
    assert first.is_default is True

    assert await GitAccountService(session).delete(first.id)
    await session.refresh(second)
    assert second.is_default is True


async def test_token_hint_is_the_last_four_characters():
    assert token_hint("ghp_abcdefgh1234") == "1234"
    assert token_hint("ab") == "**"


async def test_the_wire_shape_carries_no_token(session):
    account = await _make_account(session, token="ghp_supersecret9999")
    out = GitAccountService.to_out(account)
    assert out.token_hint == "9999"
    assert "token" not in out.model_dump()
    assert "supersecret" not in out.model_dump_json()


# --------------------------------------------------------------------------
# Repo token resolution
# --------------------------------------------------------------------------
async def test_an_omitted_account_falls_back_to_the_forge_default(session):
    account = await _make_account(session, label="default-one")
    repo = await RepoManager(session).create(
        RepoCreate(name="r1", url="https://github.com/o/r1", provider="github")
    )
    assert repo.git_account_id == account.id


async def test_an_explicit_null_account_opts_out_of_the_default(session):
    await _make_account(session, label="default-one")
    repo = await RepoManager(session).create(
        RepoCreate(
            name="r2", url="https://github.com/o/r2", provider="github",
            git_account_id=None,
        )
    )
    assert repo.git_account_id is None


async def test_an_explicit_account_wins_over_the_default(session):
    await _make_account(session, label="default-one")
    chosen = await _make_account(session, label="other", token="ghp_other")
    repo = await RepoManager(session).create(
        RepoCreate(
            name="r3", url="https://github.com/o/r3", provider="github",
            git_account_id=chosen.id,
        )
    )
    assert repo.git_account_id == chosen.id


async def test_the_default_is_scoped_to_the_repos_host(session):
    await _make_account(session, label="cloud")
    enterprise = await _make_account(session, label="work", host="git.example.com")
    repo = await RepoManager(session).create(
        RepoCreate(
            name="r4", url="https://git.example.com/o/r4", provider="github",
        )
    )
    assert repo.git_account_id == enterprise.id


async def test_a_custom_token_bypasses_the_default(session):
    await _make_account(session, label="default-one")
    manager = RepoManager(session)
    repo = await manager.create(
        RepoCreate(
            name="r5", url="https://github.com/o/r5", provider="github",
            auth_token="ghp_repo_local",
        )
    )
    assert repo.git_account_id is None
    assert await manager.get_auth_token(repo) == "ghp_repo_local"


async def test_resolution_prefers_the_account_over_a_stale_config_row(session):
    account = await _make_account(session, label="acct", token="ghp_from_account")
    repo = Repository(
        name="r6", url="https://github.com/o/r6", provider="github",
        default_branch="main", auto_sync=True, status="ready",
        git_account_id=account.id, auth_token_ref="git_token_stale",
    )
    session.add(repo)
    session.add(Config(key="git_token_stale", value={"token": "ghp_stale"}))
    await session.flush()

    assert await RepoManager(session).get_auth_token(repo) == "ghp_from_account"


async def test_selecting_an_account_retires_the_repos_own_token(session):
    manager = RepoManager(session)
    repo = await manager.create(
        RepoCreate(
            name="r7", url="https://github.com/o/r7", provider="github",
            auth_token="ghp_repo_local", git_account_id=None,
        )
    )
    token_key = repo.auth_token_ref
    assert await session.get(Config, token_key) is not None

    account = await _make_account(session, label="acct", token="ghp_from_account")
    updated = await manager.update(repo.id, RepoUpdate(git_account_id=account.id))

    assert updated.auth_token_ref is None
    assert await session.get(Config, token_key) is None
    assert await manager.get_auth_token(updated) == "ghp_from_account"


async def test_get_credential_reports_the_accounts_provider(session):
    account = await _make_account(
        session, label="gl", token="glpat_x", provider="gitlab",
    )
    repo = Repository(
        name="r8", url="https://gitlab.com/o/r8", provider="gitlab",
        default_branch="main", auto_sync=True, status="ready",
        git_account_id=account.id,
    )
    session.add(repo)
    await session.flush()

    assert await RepoManager(session).get_credential(repo) == ("glpat_x", "gitlab")


def test_auth_url_uses_the_forges_own_git_username():
    assert RepoManager._auth_url("https://github.com/o/r", "T", "github") == (
        "https://x-access-token:T@github.com/o/r"
    )
    # GitLab accepts only `oauth2` (or gitlab-ci-token); GitHub's spelling
    # authenticates as nobody there.
    assert RepoManager._auth_url("https://gitlab.com/o/r", "T", "gitlab") == (
        "https://oauth2:T@gitlab.com/o/r"
    )
    assert RepoManager._auth_url("https://host:8443/o/r", "T", "github") == (
        "https://x-access-token:T@host:8443/o/r"
    )


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
async def test_route_create_list_and_delete(client, auth_headers, session):
    with _stub_transport(_ok(username="octocat")):
        created = await client.post(
            "/api/v1/git-accounts",
            json={"label": "personal", "token": "ghp_aaaabbbb1234"},
            headers=auth_headers,
        )
    assert created.status_code == 201
    body = created.json()
    assert body["username"] == "octocat"
    assert body["token_hint"] == "1234"
    assert "token" not in body

    listed = await client.get("/api/v1/git-accounts", headers=auth_headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert [a["label"] for a in payload["accounts"]] == ["personal"]
    assert {p["provider"] for p in payload["providers"]} == {"github", "gitlab"}

    deleted = await client.delete(
        f"/api/v1/git-accounts/{body['id']}", headers=auth_headers,
    )
    assert deleted.status_code == 204


async def test_route_verify_does_not_store(client, auth_headers, session):
    with _stub_transport(_ok(username="alice", scopes="repo")):
        response = await client.post(
            "/api/v1/git-accounts/verify",
            json={"token": "ghp_x", "provider": "github"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert await GitAccountService(session).list() == []


async def test_route_delete_in_use_returns_409_naming_the_repos(
    client, auth_headers, session,
):
    account = await _make_account(session, label="in-use")
    session.add(Repository(
        name="repo-a", url="https://github.com/o/a", provider="github",
        default_branch="main", auto_sync=True, status="ready",
        git_account_id=account.id,
    ))
    await session.flush()

    response = await client.delete(
        f"/api/v1/git-accounts/{account.id}", headers=auth_headers,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["details"][0]["name"] == "repo-a"
    assert "in-use" in body["error"]["message"]


async def test_route_404s_on_an_unknown_account(client, auth_headers):
    response = await client.put(
        f"/api/v1/git-accounts/{uuid.uuid4()}",
        json={"label": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_route_requires_auth(client):
    assert (await client.get("/api/v1/git-accounts")).status_code in (401, 403)


async def test_repo_response_carries_the_account_label(client, auth_headers, session):
    account = await _make_account(session, label="personal")
    response = await client.post(
        "/api/v1/repos",
        json={
            "name": "labelled",
            "provider": "github",
            "git_account_id": str(account.id),
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["git_account_id"] == str(account.id)
    assert body["git_account_label"] == "personal"
    assert body["has_custom_token"] is False
