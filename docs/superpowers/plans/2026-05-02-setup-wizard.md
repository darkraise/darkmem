# Setup Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-page admin password form at `/setup` with a four-step wizard (password, default LLM provider, default code repo path, finish) that finalises everything in one POST and auto-logs the user in.

**Architecture:** New `/api/v1/setup/*` router gated by a single `require_uninitialized` dependency. The old `POST /api/v1/auth/setup` and `GET /api/v1/auth/status` endpoints are removed. Frontend state lives in a Zustand store; there are no per-step routes, so manual URL bypass is impossible. Finalize uses an outer transaction with `session.begin_nested` savepoints around the optional LLM and repos blocks so partial failures never roll back the password commit.

**Tech Stack:** Backend FastAPI + SQLAlchemy async + Pydantic v2 + httpx. Frontend React + TanStack Router + TanStack Query + Zustand + darkraise-ui components. Testing: pytest-asyncio + httpx ASGITransport for backend; manual Playwright sweep for frontend.

**Reference spec:** `docs/superpowers/specs/2026-05-02-setup-wizard-design.md`

---

## Phase 1 — Backend Foundation

### Task 1: Add `require_uninitialized` dependency

**Files:**
- Modify: `backend/app/api/auth.py`
- Test: `backend/tests/test_setup_route.py` (new)

- [ ] **Step 1: Write failing test for require_uninitialized**

Create `backend/tests/test_setup_route.py`:

```python
import pytest
from sqlalchemy import select

from app.models.config import Config
from app.api.auth import hash_password


@pytest.mark.asyncio
async def test_require_uninitialized_allows_when_no_password(client):
    response = await client.get("/api/v1/setup/status")
    assert response.status_code == 200
    assert response.json() == {"initialized": False}


@pytest.mark.asyncio
async def test_require_uninitialized_returns_403_after_setup(client, session):
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("test-pw-12345")}))
    await session.flush()

    response = await client.post(
        "/api/v1/setup/probe-models",
        json={"api_kind": "openai", "base_url": "https://api.example.com/v1"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v
```

Expected: FAIL — both tests error because `/api/v1/setup/*` routes do not exist yet.

- [ ] **Step 3: Add the dependency**

Append to `backend/app/api/auth.py` (after `require_auth`):

```python
async def require_uninitialized(
    session: AsyncSession = Depends(get_session),
) -> None:
    from app.models.config import Config

    result = await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        )
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/auth.py backend/tests/test_setup_route.py
git commit -m "feat(setup): add require_uninitialized dependency"
```

---

### Task 2: Extend `validate_local_path` with `must_not_be_repo`

**Files:**
- Modify: `backend/app/services/repo_manager.py:39-64`
- Test: `backend/tests/test_repos.py` (append new test)

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_repos.py`:

```python
import pytest
from pathlib import Path

from app.services.repo_manager import validate_local_path


def test_validate_local_path_rejects_git_repo_when_must_not_be_repo(tmp_path):
    repo_dir = tmp_path / "myrepo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    # Default: passes (existing callers like RepoManager.create accept repo paths)
    result = validate_local_path(str(repo_dir))
    assert result == repo_dir.resolve()

    with pytest.raises(ValueError, match="is itself a git repository"):
        validate_local_path(str(repo_dir), must_not_be_repo=True)


def test_validate_local_path_accepts_parent_of_repos_when_must_not_be_repo(tmp_path):
    parent = tmp_path / "workspace"
    parent.mkdir()
    (parent / "child-repo").mkdir()
    (parent / "child-repo" / ".git").mkdir()

    result = validate_local_path(str(parent), must_not_be_repo=True)
    assert result == parent.resolve()
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
cd backend && python -m pytest tests/test_repos.py -v -k validate_local_path
```

Expected: FAIL — `must_not_be_repo` argument unknown.

- [ ] **Step 3: Update the helper**

Edit `backend/app/services/repo_manager.py`, replacing the `validate_local_path` body:

```python
def validate_local_path(raw: str, *, must_not_be_repo: bool = False) -> Path:
    """Resolve ``raw`` and reject it if the indexer shouldn't read from there.

    Raises ``ValueError`` with a single sentence explaining the reason.
    Returns the resolved ``Path`` so callers can use it directly.

    When ``must_not_be_repo=True``, also rejects paths whose immediate
    contents include a ``.git`` directory — used by the setup wizard's
    "Use this folder" guard so the chosen base path is never itself a
    repository (which would clash with detect-children-as-repos logic).
    """
    if not raw or not raw.strip():
        raise ValueError("local_path must not be empty")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"local_path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"local_path is not a directory: {resolved}")
    posix = resolved.as_posix()
    for blocked in _LOCAL_PATH_BLOCKLIST:
        if posix == blocked or posix.startswith(blocked + "/"):
            raise ValueError(f"local_path is inside a blocked system tree: {blocked}")
    home = Path.home().resolve().as_posix()
    if posix.startswith(home + "/"):
        rest = posix[len(home) + 1:]
        first = rest.split("/", 1)[0]
        if first in _HOME_SUBPATH_BLOCKLIST:
            raise ValueError(
                f"local_path is inside a blocked credential tree: ~/{first}"
            )
    if must_not_be_repo and (resolved / ".git").is_dir():
        raise ValueError(f"local_path is itself a git repository: {resolved}")
    return resolved
```

- [ ] **Step 4: Run test, confirm it passes**

```bash
cd backend && python -m pytest tests/test_repos.py -v -k validate_local_path
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/repo_manager.py backend/tests/test_repos.py
git commit -m "feat(repo-manager): add must_not_be_repo flag to validate_local_path"
```

---

### Task 3: Create setup router and `/setup/status`

**Files:**
- Create: `backend/app/api/routes/setup.py`
- Modify: `backend/app/main.py:13` (router import) and `backend/app/main.py:268-281` (registration)
- Test: `backend/tests/test_setup_route.py` (existing tests now pass)

- [ ] **Step 1: Create the router file**

Create `backend/app/api/routes/setup.py`:

```python
"""Setup wizard router.

All endpoints under ``/api/v1/setup/*`` are gated by ``require_uninitialized``
except ``GET /api/v1/setup/status`` (which is the public probe used by the
wizard's route guard). Once the admin password is set, every wizard endpoint
returns 403, and the wizard frontend redirects new visitors to ``/login``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.config import Config

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

ADMIN_PASSWORD_KEY = "admin_password_hash"


class StatusResponse(BaseModel):
    initialized: bool


@router.get("/status", response_model=StatusResponse)
async def setup_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Config).where(Config.key == ADMIN_PASSWORD_KEY)
    )
    return StatusResponse(initialized=result.scalar_one_or_none() is not None)
```

- [ ] **Step 2: Register the router**

Edit `backend/app/main.py`:

Change line 13 from:
```python
from app.api.routes import analytics, auth, chat, code, config, graph, memories, pipeline as pipeline_routes, pipeline_failures, reembed, repos, tags, vectors
```
to:
```python
from app.api.routes import analytics, auth, chat, code, config, graph, memories, pipeline as pipeline_routes, pipeline_failures, reembed, repos, setup, tags, vectors
```

After the `app.include_router(reembed.router)` line (around line 280), add:
```python
app.include_router(setup.router)
```

- [ ] **Step 3: Run the status test**

```bash
cd backend && python -m pytest tests/test_setup_route.py::test_require_uninitialized_allows_when_no_password -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/setup.py backend/app/main.py
git commit -m "feat(setup): add /api/v1/setup router with status endpoint"
```

---

### Task 4: Add `POST /setup/probe-models`

**Files:**
- Modify: `backend/app/api/routes/setup.py`
- Test: `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_setup_route.py`:

```python
from unittest.mock import AsyncMock, patch


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
```

- [ ] **Step 2: Run, confirm failures**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k probe
```

Expected: FAIL — endpoint not implemented.

- [ ] **Step 3: Implement the endpoint**

Append to `backend/app/api/routes/setup.py`:

```python
import httpx
from typing import Literal

from fastapi import HTTPException

from app.api.auth import require_uninitialized


def _ollama_native_root(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    if base.endswith("/api"):
        return base[:-4]
    return base


class ProbeModelsRequest(BaseModel):
    api_kind: Literal["openai", "anthropic", "ollama", "google", "deepseek", "zai"]
    base_url: str
    api_key: str | None = None


class ProbeModelsResponse(BaseModel):
    models: list[str]
    fetched_via: str
    error: str | None = None


@router.post(
    "/probe-models",
    response_model=ProbeModelsResponse,
    dependencies=[Depends(require_uninitialized)],
)
async def probe_models(body: ProbeModelsRequest) -> ProbeModelsResponse:
    """Live model probe used by the wizard.

    No DB writes — uses the supplied connection details directly so the
    user can iterate on the API key without persisting anything until
    the final ``POST /api/v1/setup`` call.
    """
    headers = {"Accept": "application/json"}
    if body.api_kind == "ollama":
        url = f"{_ollama_native_root(body.base_url)}/api/tags"
        kind_label = "ollama_native:/api/tags"
    else:
        if body.api_kind != "ollama" and not body.api_key:
            return ProbeModelsResponse(
                models=[],
                fetched_via="openai_compat:/v1/models",
                error=f"API key required for api_kind={body.api_kind!r}",
            )
        if body.api_kind == "anthropic":
            headers["x-api-key"] = body.api_key or ""
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {body.api_key}"
        url = f"{body.base_url.rstrip('/')}/models"
        kind_label = "openai_compat:/v1/models"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client_:
            resp = await client_.get(url, headers=headers)
        if not resp.is_success:
            return ProbeModelsResponse(
                models=[], fetched_via=kind_label,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
    except httpx.HTTPError as exc:
        return ProbeModelsResponse(
            models=[], fetched_via=kind_label, error=f"network error: {exc}",
        )

    models: list[str] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            for entry in data["data"]:
                mid = entry.get("id") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
        elif isinstance(data.get("models"), list):
            for entry in data["models"]:
                mid = entry.get("name") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
    return ProbeModelsResponse(models=sorted(set(models)), fetched_via=kind_label)
```

- [ ] **Step 4: Run, confirm pass**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k probe
```

Expected: PASS for all four `probe` tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/setup.py backend/tests/test_setup_route.py
git commit -m "feat(setup): add probe-models endpoint for wizard model picker"
```

---

### Task 5: Add `GET /setup/fs/roots` and `GET /setup/fs/list`

**Files:**
- Modify: `backend/app/api/routes/setup.py`
- Test: `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_setup_route.py`:

```python
import os


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

    # Without detect_repos: navigation is allowed.
    nav = await client.get("/api/v1/setup/fs/list", params={"path": str(repo)})
    assert nav.status_code == 200
    assert nav.json()["is_git"] is True

    # With detect_repos: confirm-time guard refuses.
    confirm = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(repo), "detect_repos": "true"},
    )
    assert confirm.status_code == 422


@pytest.mark.asyncio
async def test_fs_list_rejects_blocklisted_paths(client, tmp_path, monkeypatch):
    # Mock home to point at tmp_path so we can test the credential-tree block.
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".ssh").mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

    response = await client.get(
        "/api/v1/setup/fs/list",
        params={"path": str(fake_home / ".ssh")},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run, confirm failures**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k fs
```

Expected: FAIL — endpoints not implemented.

- [ ] **Step 3: Implement the endpoints**

Append to `backend/app/api/routes/setup.py`:

```python
import os
import sys
from pathlib import Path

from app.services.repo_manager import validate_local_path


class FsRoot(BaseModel):
    path: str
    label: str


class FsRootsResponse(BaseModel):
    roots: list[FsRoot]


class FsListEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    is_git: bool
    has_repos: bool
    repo_count: int


class FsListResponse(BaseModel):
    path: str
    parent: str | None
    entries: list[FsListEntry]
    is_git: bool
    blocked_reason: str | None = None


def _enumerate_roots() -> list[FsRoot]:
    roots: list[FsRoot] = []
    if sys.platform == "win32":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append(FsRoot(path=drive, label=f"{letter}:"))
        if not roots:
            roots.append(FsRoot(path="C:\\", label="C:"))
    else:
        roots.append(FsRoot(path="/", label="/"))
        home = str(Path.home())
        roots.append(FsRoot(path=home, label="~"))
    return roots


def _list_directory(path: Path, *, detect_repos: bool) -> list[FsListEntry]:
    entries: list[FsListEntry] = []
    try:
        children = sorted(path.iterdir(), key=lambda p: p.name.lower())
    except (PermissionError, OSError):
        return entries
    for child in children:
        try:
            is_dir = child.is_dir()
        except OSError:
            continue
        if not is_dir:
            continue
        is_git = False
        has_repos = False
        repo_count = 0
        if detect_repos:
            try:
                is_git = (child / ".git").is_dir()
            except OSError:
                pass
            if not is_git:
                try:
                    for grandchild in child.iterdir():
                        try:
                            if grandchild.is_dir() and (grandchild / ".git").is_dir():
                                repo_count += 1
                        except OSError:
                            continue
                except (PermissionError, OSError):
                    pass
                has_repos = repo_count > 0
        entries.append(FsListEntry(
            name=child.name,
            path=str(child),
            is_dir=True,
            is_git=is_git,
            has_repos=has_repos,
            repo_count=repo_count,
        ))
    return entries


@router.get(
    "/fs/roots",
    response_model=FsRootsResponse,
    dependencies=[Depends(require_uninitialized)],
)
async def fs_roots() -> FsRootsResponse:
    return FsRootsResponse(roots=_enumerate_roots())


@router.get(
    "/fs/list",
    response_model=FsListResponse,
    dependencies=[Depends(require_uninitialized)],
)
async def fs_list(path: str, detect_repos: bool = False) -> FsListResponse:
    try:
        resolved = validate_local_path(path, must_not_be_repo=detect_repos)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    parent = str(resolved.parent) if resolved.parent != resolved else None
    entries = _list_directory(resolved, detect_repos=detect_repos)
    is_git = (resolved / ".git").is_dir()
    return FsListResponse(
        path=str(resolved),
        parent=parent,
        entries=entries,
        is_git=is_git,
    )
```

- [ ] **Step 4: Run, confirm pass**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k fs
```

Expected: PASS for all five `fs` tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/setup.py backend/tests/test_setup_route.py
git commit -m "feat(setup): add fs/roots and fs/list endpoints with .git detection"
```

---

### Task 6: Add `POST /api/v1/setup` finalize endpoint

**Files:**
- Modify: `backend/app/api/routes/setup.py`
- Test: `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_setup_route.py`:

```python
from app.models.audit import AuditLog
from app.models.code import Repository
from app.models.llm_config import LLMProvider, LLMProfile, LLMPurposeConfigRow


@pytest.mark.asyncio
async def test_setup_finalize_password_only(client, session):
    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["password"]["ok"] is True
    assert body["llm"]["ok"] is True  # skipped counts as ok
    assert body["repos"]["ok"] is True

    # Cookie set
    set_cookie = response.headers.get("set-cookie", "")
    assert "darkmem_session=" in set_cookie

    # Password row exists
    config = (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none()
    assert config is not None

    # Audit logs
    audits = (await session.execute(select(AuditLog))).scalars().all()
    actions = {a.action for a in audits}
    assert "auth_setup" in actions and "setup_complete" in actions


@pytest.mark.asyncio
async def test_setup_finalize_with_llm(client, session, tmp_path):
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

    providers = (await session.execute(select(LLMProvider))).scalars().all()
    assert len(providers) == 1 and providers[0].name == "OpenAI"
    assert providers[0].api_key == "sk-test"

    profiles = (await session.execute(select(LLMProfile))).scalars().all()
    assert len(profiles) == 4
    profile_names = sorted(p.name for p in profiles)
    assert profile_names == [
        "default-classification",
        "default-embedding",
        "default-extraction",
        "default-reasoning",
    ]

    purposes = (await session.execute(select(LLMPurposeConfigRow))).scalars().all()
    assert len(purposes) == 4


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


@pytest.mark.asyncio
async def test_setup_finalize_per_repo_failures_isolated(client, session, tmp_path):
    base = tmp_path / "workspace"
    base.mkdir()
    valid_repo = base / "valid"
    valid_repo.mkdir()
    (valid_repo / ".git").mkdir()
    # missing path: not created on disk

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
```

- [ ] **Step 2: Run, confirm failures**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k finalize
```

Expected: FAIL — endpoint not implemented.

- [ ] **Step 3: Implement the endpoint**

Append to `backend/app/api/routes/setup.py`:

```python
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.auth import (
    create_access_token,
    hash_password,
    set_auth_cookie,
)
from app.models.audit import AuditLog
from app.models.code import Repository
from app.models.llm_config import LLMProvider, LLMProfile, LLMPurposeConfigRow


PURPOSE_LITERAL = Literal[
    "embedding", "extraction", "classification",
    "reasoning", "summarization", "reranker",
]


class SetupLLMPurpose(BaseModel):
    model: str
    reasoning: bool = False
    dimensions: int | None = None


class SetupLLM(BaseModel):
    provider_name: str
    api_kind: str
    base_url: str
    api_key: str | None = None
    supports_embedding: bool = True
    purposes: dict[PURPOSE_LITERAL, SetupLLMPurpose]


class SetupRepo(BaseModel):
    name: str
    sub_path: str


class SetupRepos(BaseModel):
    base_path: str
    repos: list[SetupRepo] = []


class SetupRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    llm: SetupLLM | None = None
    repos: SetupRepos | None = None


class SetupSectionStatus(BaseModel):
    ok: bool
    message: str | None = None


class SetupResponse(BaseModel):
    password: SetupSectionStatus
    llm: SetupSectionStatus
    repos: SetupSectionStatus
    repos_added: list[str]
    repos_failed: list[dict]


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "",
    response_model=SetupResponse,
    dependencies=[Depends(require_uninitialized)],
)
async def setup_finalize(
    body: SetupRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Finalize the wizard.

    Password is the only required block. LLM and repo blocks each run
    inside their own savepoint so partial failures are reported but never
    roll back the password commit. The auth cookie is issued unconditionally
    on a successful password write.
    """
    from app.services.config import get_llm_config as fetch_llm_config
    from app.services.llm import LLMOrchestrator
    from app.services.repo_manager import validate_local_path

    repos_added: list[str] = []
    repos_failed: list[dict] = []
    llm_status = SetupSectionStatus(ok=True)
    repos_status = SetupSectionStatus(ok=True)

    async with request.app.state.llm_config_lock:
        # 1. Password block — required.
        session.add(Config(
            key=ADMIN_PASSWORD_KEY,
            value={"hash": hash_password(body.password)},
        ))
        session.add(AuditLog(
            action="auth_setup",
            details={"ip": _client_ip(request)},
        ))
        await session.flush()

        # 2. LLM block — optional, savepoint-isolated.
        if body.llm is not None:
            try:
                async with session.begin_nested():
                    provider = LLMProvider(
                        name=body.llm.provider_name,
                        provider=body.llm.api_kind,
                        base_url=body.llm.base_url,
                        api_key=body.llm.api_key,
                        api_kind=body.llm.api_kind,
                        supports_embedding=body.llm.supports_embedding,
                    )
                    if body.llm.api_key:
                        provider.api_key_rotated_at = datetime.now(timezone.utc)
                    session.add(provider)
                    await session.flush()

                    for purpose_key, spec in body.llm.purposes.items():
                        is_embedding = (purpose_key == "embedding")
                        profile = LLMProfile(
                            name=f"default-{purpose_key}",
                            provider_id=provider.id,
                            model=spec.model,
                            params={},
                            is_embedding=is_embedding,
                            reasoning=False if is_embedding else spec.reasoning,
                        )
                        session.add(profile)
                        await session.flush()

                        purpose_row = LLMPurposeConfigRow(
                            purpose=purpose_key,
                            provider_id=provider.id,
                            profile_id=profile.id,
                            model=spec.model,
                            dimensions=spec.dimensions if is_embedding else None,
                            reasoning=False if is_embedding else spec.reasoning,
                            api_kind=body.llm.api_kind,
                            provider=body.llm.api_kind,
                            base_url=body.llm.base_url,
                            api_key=body.llm.api_key,
                            params={},
                        )
                        session.add(purpose_row)
                    await session.flush()
            except Exception as exc:
                llm_status = SetupSectionStatus(ok=False, message=str(exc))

        # 3. Repos block — optional, per-row savepoint-isolated.
        if body.repos is not None:
            try:
                async with session.begin_nested():
                    base_resolved = validate_local_path(
                        body.repos.base_path, must_not_be_repo=True,
                    )
                    existing = (await session.execute(
                        select(Config).where(Config.key == "repos_default_local_path")
                    )).scalar_one_or_none()
                    if existing:
                        existing.value = {"path": str(base_resolved)}
                    else:
                        session.add(Config(
                            key="repos_default_local_path",
                            value={"path": str(base_resolved)},
                        ))
                    await session.flush()
            except Exception as exc:
                repos_status = SetupSectionStatus(ok=False, message=str(exc))
            else:
                for entry in body.repos.repos:
                    try:
                        async with session.begin_nested():
                            full_path = validate_local_path(
                                str(Path(body.repos.base_path) / entry.sub_path)
                            )
                            session.add(Repository(
                                name=entry.name,
                                provider="local",
                                local_path=str(full_path),
                                default_branch="main",
                                status="ready",
                                is_active=True,
                            ))
                            await session.flush()
                        repos_added.append(entry.name)
                    except Exception as exc:
                        repos_failed.append({"name": entry.name, "error": str(exc)})

        await session.commit()

        # 4. Rebuild the live orchestrator if the LLM block landed.
        if body.llm is not None and llm_status.ok:
            from app.api.routes.config import _replace_orchestrator
            new_config = await fetch_llm_config(session)
            new_llm = LLMOrchestrator(new_config)
            _replace_orchestrator(request, new_llm)

        # 5. Audit log + cookie
        session.add(AuditLog(
            action="setup_complete",
            details={
                "ip": _client_ip(request),
                "llm": llm_status.ok,
                "llm_skipped": body.llm is None,
                "repos": repos_status.ok,
                "repos_skipped": body.repos is None,
                "repos_added": repos_added,
                "repos_failed_count": len(repos_failed),
            },
        ))
        await session.commit()

    payload = SetupResponse(
        password=SetupSectionStatus(ok=True),
        llm=llm_status,
        repos=repos_status,
        repos_added=repos_added,
        repos_failed=repos_failed,
    )
    response = JSONResponse(content=payload.model_dump())
    token = create_access_token({"sub": "admin"})
    return set_auth_cookie(response, token)
```

Make sure the Pydantic import line at the top of `setup.py` includes `Field`. Edit the existing `from pydantic import BaseModel` line (added in Task 3) to:

```python
from pydantic import BaseModel, Field
```

- [ ] **Step 4: Run, confirm pass**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v
```

Expected: PASS for every test in the file.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/setup.py backend/tests/test_setup_route.py
git commit -m "feat(setup): add POST /setup finalize endpoint with savepoint isolation"
```

---

### Task 7: Add authenticated `system/fs/*` endpoints

**Files:**
- Create: `backend/app/api/routes/system.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_setup_route.py`:

```python
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
```

- [ ] **Step 2: Run, confirm failures**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k system_fs
```

Expected: FAIL — `/system/fs/*` endpoints don't exist.

- [ ] **Step 3: Create the system router**

Create `backend/app/api/routes/system.py`:

```python
"""Authenticated system utility endpoints.

Mirrors the wizard-only ``/api/v1/setup/fs/*`` shapes for use after the
install has been initialised — the wizard endpoints 403 once the password
is set, so the Settings page (and any future operator-tools UI) needs an
auth-gated mirror.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_auth
from app.api.routes.setup import (
    FsListResponse,
    FsRootsResponse,
    _enumerate_roots,
    _list_directory,
)
from app.services.repo_manager import validate_local_path

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/fs/roots", response_model=FsRootsResponse)
async def system_fs_roots(_user=Depends(require_auth)) -> FsRootsResponse:
    return FsRootsResponse(roots=_enumerate_roots())


@router.get("/fs/list", response_model=FsListResponse)
async def system_fs_list(
    path: str,
    detect_repos: bool = False,
    _user=Depends(require_auth),
) -> FsListResponse:
    try:
        resolved = validate_local_path(path, must_not_be_repo=detect_repos)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    parent = str(resolved.parent) if resolved.parent != resolved else None
    entries = _list_directory(resolved, detect_repos=detect_repos)
    is_git = (resolved / ".git").is_dir()
    return FsListResponse(
        path=str(resolved),
        parent=parent,
        entries=entries,
        is_git=is_git,
    )
```

- [ ] **Step 4: Register the router**

Edit `backend/app/main.py`. Update line 13 to include `system`:

```python
from app.api.routes import analytics, auth, chat, code, config, graph, memories, pipeline as pipeline_routes, pipeline_failures, reembed, repos, setup, system, tags, vectors
```

After `app.include_router(setup.router)`, add:

```python
app.include_router(system.router)
```

- [ ] **Step 5: Run, confirm pass**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k system_fs
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/system.py backend/app/main.py backend/tests/test_setup_route.py
git commit -m "feat(setup): add authenticated /system/fs/* mirror endpoints"
```

---

### Task 8: Add `repos-path` config endpoints

**Files:**
- Modify: `backend/app/api/routes/config.py`
- Test: `backend/tests/test_setup_route.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_setup_route.py`:

```python
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
```

- [ ] **Step 2: Run, confirm failures**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k repos_path
```

Expected: FAIL — endpoints not implemented.

- [ ] **Step 3: Implement the endpoints**

Append to `backend/app/api/routes/config.py`:

```python
class ReposPathResponse(BaseModel):
    path: str | None


class ReposPathUpdate(BaseModel):
    path: str


@router.get("/repos-path", response_model=ReposPathResponse)
async def get_repos_path(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return ReposPathResponse(path=None)
    return ReposPathResponse(path=row.value.get("path"))


@router.put("/repos-path", response_model=ReposPathResponse)
async def update_repos_path(
    body: ReposPathUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.repo_manager import validate_local_path

    try:
        resolved = validate_local_path(body.path, must_not_be_repo=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key="repos_default_local_path", value={"path": str(resolved)}))
    else:
        row.value = {"path": str(resolved)}
    await session.flush()
    return ReposPathResponse(path=str(resolved))
```

- [ ] **Step 4: Run, confirm pass**

```bash
cd backend && python -m pytest tests/test_setup_route.py -v -k repos_path
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/config.py backend/tests/test_setup_route.py
git commit -m "feat(config): add repos-path GET/PUT for default code repo path"
```

---

### Task 9: Remove old `auth_setup` and `auth_status`, migrate fixtures

**Files:**
- Modify: `backend/app/api/routes/auth.py:25-78` (remove `auth_setup`, `auth_status`, related schemas)
- Modify: `backend/tests/conftest.py` (no functional change needed — fixture writes Config directly)
- Modify: `backend/tests/test_backfill_v2.py` (no setup call; safe)
- Modify: `backend/scripts/seed_test_memories.py`
- Modify: `docs/e2e/scripts/lib/client.py`
- Modify: `docs/e2e/scripts/01_auth_flow.py`

- [ ] **Step 1: Audit callers of removed routes**

```bash
cd "D:/Repositories/_local_projects/darkmem" && grep -rn "/api/v1/auth/status\|/api/v1/auth/setup" --include="*.py" --include="*.ts" --include="*.tsx"
```

Confirm callers match the file inventory in this task.

- [ ] **Step 2: Remove `auth_setup`, `auth_status`, and unused schemas from `auth.py`**

Edit `backend/app/api/routes/auth.py`:

1. Delete the `StatusResponse` class (lines 43-44) and the `SetupRequest` class (lines 33-35).
2. Delete the `auth_status` route handler (lines 51-55) and the `auth_setup` handler (lines 58-78).
3. Keep the `ADMIN_PASSWORD_KEY = "admin_password_hash"` constant on line 26 — it is still referenced by `auth_login` and `auth_change_password`.
4. Keep `PasswordRequest` and `ChangePasswordRequest` (still used).
5. The remaining handlers (`auth_login`, `auth_logout`, `auth_change_password`, `auth_refresh`, `auth_me`) and their imports stay unchanged.

- [ ] **Step 3: Migrate the e2e client**

Edit `docs/e2e/scripts/lib/client.py`:

Replace the `auth_status` and `setup` methods with:

```python
    async def auth_status(self) -> dict:
        r = await self._client.get(f"{self.base_url}/api/v1/setup/status")
        r.raise_for_status()
        return r.json()

    async def setup(self) -> None:
        r = await self._client.post(
            f"{self.base_url}/api/v1/setup",
            json={"password": self.password},
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Setup failed ({r.status_code}): {r.text}")
        self._cookie = r.cookies.get("darkmem_session")
        if not self._cookie:
            raise RuntimeError("Setup did not return a session cookie")
        if self.verbose:
            print(f"  [setup] ok, cookie set")
```

- [ ] **Step 4: Migrate the auth flow script**

Edit `docs/e2e/scripts/01_auth_flow.py`. Replace every URL `/api/v1/auth/status` with `/api/v1/setup/status`, every `/api/v1/auth/setup` with `/api/v1/setup`. Also adjust the "second setup returns 400" assertion to `403`:

```python
        # Setup again should 403 (already initialized)
        r = await raw.post(f"{base}/api/v1/setup", json={"password": args.password})
        if r.status_code == 403:
            report.ok("second setup returns 403")
        else:
            report.fail("second setup", f"status {r.status_code}")
```

- [ ] **Step 5: Migrate `seed_test_memories.py`**

```bash
cd "D:/Repositories/_local_projects/darkmem" && grep -n "auth/setup\|auth/status" backend/scripts/seed_test_memories.py
```

For each line printed, replace `/api/v1/auth/setup` with `/api/v1/setup` and `/api/v1/auth/status` with `/api/v1/setup/status`.

- [ ] **Step 6: Run the full backend test suite**

```bash
cd backend && python -m pytest -v
```

Expected: PASS for every test (including the new `test_setup_route.py` and the existing `test_repositories.py`, `test_repos.py`, etc.). If any failure references `/api/v1/auth/setup` or `/api/v1/auth/status`, fix the caller and rerun.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/auth.py docs/e2e/scripts/lib/client.py docs/e2e/scripts/01_auth_flow.py backend/scripts/seed_test_memories.py
git commit -m "refactor(auth): remove auth/setup and auth/status; migrate callers"
```

---

## Phase 2 — Frontend Foundation

### Task 10: Setup wizard Zustand store

**Files:**
- Create: `frontend/src/features/setup/setupWizardStore.ts`

- [ ] **Step 1: Create the store**

Create `frontend/src/features/setup/setupWizardStore.ts`:

```ts
import { create } from "zustand"

export type Purpose =
  | "embedding"
  | "extraction"
  | "classification"
  | "reasoning"
  | "summarization"
  | "reranker"

export const PURPOSES: Purpose[] = [
  "embedding",
  "extraction",
  "classification",
  "reasoning",
  "summarization",
  "reranker",
]

export const REQUIRED_PURPOSES_NON_EMBEDDING: Purpose[] = [
  "extraction",
  "classification",
  "reasoning",
]

export type DetectedRepo = {
  name: string
  subPath: string
  selected: boolean
}

export type PurposeDraft = {
  model: string
  reasoning: boolean
  dimensions?: number
}

type SetupWizardState = {
  step: 1 | 2 | 3 | 4
  password: { value: string; confirm: string }
  llm: {
    skipped: boolean
    provider_name: string
    api_kind: string
    base_url: string
    api_key: string
    supports_embedding: boolean
    models: string[]
    perPurpose: Record<Purpose, PurposeDraft>
  }
  repos: {
    skipped: boolean
    basePath: string
    detected: DetectedRepo[]
  }
  setStep: (step: 1 | 2 | 3 | 4) => void
  setPassword: (value: string, confirm: string) => void
  setLlmField: <K extends keyof SetupWizardState["llm"]>(
    key: K,
    value: SetupWizardState["llm"][K],
  ) => void
  setLlmPurpose: (purpose: Purpose, draft: Partial<PurposeDraft>) => void
  setLlmSkipped: (skipped: boolean) => void
  setReposBasePath: (path: string) => void
  setReposDetected: (detected: DetectedRepo[]) => void
  toggleRepoSelected: (subPath: string) => void
  renameDetectedRepo: (subPath: string, name: string) => void
  setReposSkipped: (skipped: boolean) => void
  reset: () => void
}

const emptyPurposeDraft: PurposeDraft = { model: "", reasoning: false }

const initial = (): Omit<
  SetupWizardState,
  | "setStep"
  | "setPassword"
  | "setLlmField"
  | "setLlmPurpose"
  | "setLlmSkipped"
  | "setReposBasePath"
  | "setReposDetected"
  | "toggleRepoSelected"
  | "renameDetectedRepo"
  | "setReposSkipped"
  | "reset"
> => ({
  step: 1,
  password: { value: "", confirm: "" },
  llm: {
    skipped: false,
    provider_name: "",
    api_kind: "openai",
    base_url: "https://api.openai.com/v1",
    api_key: "",
    supports_embedding: true,
    models: [],
    perPurpose: {
      embedding: { ...emptyPurposeDraft },
      extraction: { ...emptyPurposeDraft },
      classification: { ...emptyPurposeDraft },
      reasoning: { ...emptyPurposeDraft },
      summarization: { ...emptyPurposeDraft },
      reranker: { ...emptyPurposeDraft },
    },
  },
  repos: { skipped: false, basePath: "", detected: [] },
})

export const useSetupWizardStore = create<SetupWizardState>((set) => ({
  ...initial(),
  setStep: (step) => set({ step }),
  setPassword: (value, confirm) => set({ password: { value, confirm } }),
  setLlmField: (key, value) =>
    set((s) => ({ llm: { ...s.llm, [key]: value } })),
  setLlmPurpose: (purpose, draft) =>
    set((s) => ({
      llm: {
        ...s.llm,
        perPurpose: {
          ...s.llm.perPurpose,
          [purpose]: { ...s.llm.perPurpose[purpose], ...draft },
        },
      },
    })),
  setLlmSkipped: (skipped) => set((s) => ({ llm: { ...s.llm, skipped } })),
  setReposBasePath: (basePath) =>
    set((s) => ({ repos: { ...s.repos, basePath } })),
  setReposDetected: (detected) =>
    set((s) => ({ repos: { ...s.repos, detected } })),
  toggleRepoSelected: (subPath) =>
    set((s) => ({
      repos: {
        ...s.repos,
        detected: s.repos.detected.map((r) =>
          r.subPath === subPath ? { ...r, selected: !r.selected } : r,
        ),
      },
    })),
  renameDetectedRepo: (subPath, name) =>
    set((s) => ({
      repos: {
        ...s.repos,
        detected: s.repos.detected.map((r) =>
          r.subPath === subPath ? { ...r, name } : r,
        ),
      },
    })),
  setReposSkipped: (skipped) =>
    set((s) => ({ repos: { ...s.repos, skipped } })),
  reset: () => set(initial()),
}))
```

- [ ] **Step 2: Type-check the file**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: no errors mentioning `setupWizardStore.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/setup/setupWizardStore.ts
git commit -m "feat(setup-ui): add wizard Zustand store"
```

---

### Task 11: API hooks for the setup wizard

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/api/use-setup-api.ts`
- Modify: `frontend/src/hooks/api/index.ts`
- Modify: `frontend/src/hooks/api/use-config-api.ts`

- [ ] **Step 1: Repoint `checkSetupStatus` and remove old `setup`**

Edit `frontend/src/lib/api.ts`:

Replace the `checkSetupStatus` function body's URL from `/auth/status` to `/setup/status`. Delete the entire `setup(password: string)` function (lines 70-84).

```ts
export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/setup/status`, {
    credentials: "include",
  })
  return response.json()
}
```

- [ ] **Step 2: Add the setup-api hook file**

Create `frontend/src/hooks/api/use-setup-api.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useAuthStore } from "@/features/auth"

export type ProbeModelsRequest = {
  api_kind: "openai" | "anthropic" | "ollama" | "google" | "deepseek" | "zai"
  base_url: string
  api_key?: string | null
}

export type ProbeModelsResponse = {
  models: string[]
  fetched_via: string
  error: string | null
}

export type FsRoot = { path: string; label: string }
export type FsRootsResponse = { roots: FsRoot[] }

export type FsListEntry = {
  name: string
  path: string
  is_dir: boolean
  is_git: boolean
  has_repos: boolean
  repo_count: number
}

export type FsListResponse = {
  path: string
  parent: string | null
  entries: FsListEntry[]
  is_git: boolean
  blocked_reason: string | null
}

export type SetupRepoSelection = { name: string; sub_path: string }

export type SetupLLMPurpose = {
  model: string
  reasoning: boolean
  dimensions?: number | null
}

export type SetupRequest = {
  password: string
  llm?: {
    provider_name: string
    api_kind: string
    base_url: string
    api_key: string | null
    supports_embedding: boolean
    purposes: Partial<Record<
      "embedding" | "extraction" | "classification" | "reasoning" | "summarization" | "reranker",
      SetupLLMPurpose
    >>
  } | null
  repos?: {
    base_path: string
    repos: SetupRepoSelection[]
  } | null
}

export type SetupSectionStatus = { ok: boolean; message: string | null }

export type SetupResponse = {
  password: SetupSectionStatus
  llm: SetupSectionStatus
  repos: SetupSectionStatus
  repos_added: string[]
  repos_failed: { name: string; error: string }[]
}

const API_BASE = "/api/v1"

async function rawFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function useProbeModels() {
  return useMutation<ProbeModelsResponse, Error, ProbeModelsRequest>({
    mutationFn: (body) =>
      rawFetch<ProbeModelsResponse>("/setup/probe-models", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  })
}

export function useFsRoots(apiBase: "/setup" | "/system") {
  return useQuery<FsRootsResponse>({
    queryKey: ["fs", apiBase, "roots"],
    queryFn: () =>
      apiBase === "/setup"
        ? rawFetch<FsRootsResponse>("/setup/fs/roots")
        : apiFetch<FsRootsResponse>("/system/fs/roots"),
  })
}

export async function fsList(
  apiBase: "/setup" | "/system",
  path: string,
  detectRepos = false,
): Promise<FsListResponse> {
  const qs = new URLSearchParams({ path, detect_repos: String(detectRepos) })
  if (apiBase === "/setup") {
    return rawFetch<FsListResponse>(`/setup/fs/list?${qs.toString()}`)
  }
  return apiFetch<FsListResponse>(`/system/fs/list?${qs.toString()}`)
}

export function useFinalizeSetup() {
  return useMutation<SetupResponse, Error, SetupRequest>({
    mutationFn: async (body) => {
      const result = await rawFetch<SetupResponse>("/setup", {
        method: "POST",
        body: JSON.stringify(body),
      })
      useAuthStore.getState().setAuthenticated(true)
      return result
    },
  })
}

export function useReposPath() {
  return useQuery<{ path: string | null }>({
    queryKey: ["reposPath"],
    queryFn: () => apiFetch<{ path: string | null }>("/config/repos-path"),
  })
}

export function useUpdateReposPath() {
  const qc = useQueryClient()
  return useMutation<{ path: string | null }, Error, { path: string }>({
    mutationFn: (body) =>
      apiFetch<{ path: string | null }>("/config/repos-path", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reposPath"] }),
  })
}
```

- [ ] **Step 3: Re-export the new hooks**

Edit `frontend/src/hooks/api/index.ts`:

Append:

```ts
export * from "./use-setup-api"
```

- [ ] **Step 4: Adjust the import in use-setup-api.ts**

Edit `frontend/src/hooks/api/use-setup-api.ts`. Replace `import { apiFetch, useAuthStore } from "@/lib/api"` with the two correct sources:

```ts
import { apiFetch } from "@/lib/api"
import { useAuthStore } from "@/features/auth"
```

- [ ] **Step 5: Type-check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: no errors in the new files. Existing callers still work because we only repointed an internal URL and added new exports.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/hooks/api/use-setup-api.ts frontend/src/hooks/api/index.ts
git commit -m "feat(setup-ui): add setup wizard API hooks"
```

---

### Task 12: ServerPathBrowser component

**Files:**
- Create: `frontend/src/components/setup/ServerPathBrowser.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/setup/ServerPathBrowser.tsx`:

```tsx
import { useEffect, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Badge } from "darkraise-ui/components/badge"
import { Folder, FolderGit2, ChevronRight } from "lucide-react"
import { fsList, useFsRoots, type FsListEntry } from "@/hooks/api/use-setup-api"

type Props = {
  apiBase: "/setup" | "/system"
  value: string
  onChange: (path: string) => void
  onConfirm: (path: string) => void | Promise<void>
  disabled?: boolean
}

export function ServerPathBrowser({ apiBase, value, onChange, onConfirm, disabled }: Props) {
  const { data: rootsData } = useFsRoots(apiBase)
  const [entries, setEntries] = useState<FsListEntry[]>([])
  const [parent, setParent] = useState<string | null>(null)
  const [isGit, setIsGit] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [manual, setManual] = useState(value)

  useEffect(() => {
    setManual(value)
  }, [value])

  useEffect(() => {
    if (!value) return
    let cancelled = false
    fsList(apiBase, value, false)
      .then((res) => {
        if (cancelled) return
        setEntries(res.entries)
        setParent(res.parent)
        setIsGit(res.is_git)
        setError(null)
      })
      .catch((e) => {
        if (cancelled) return
        setError((e as Error).message)
        setEntries([])
        setParent(null)
        setIsGit(false)
      })
    return () => {
      cancelled = true
    }
  }, [apiBase, value])

  const navigate = (path: string) => onChange(path)

  const handleManualGo = () => {
    if (manual.trim()) onChange(manual.trim())
  }

  const handleConfirm = async () => {
    setError(null)
    try {
      await fsList(apiBase, value, true)
      await onConfirm(value)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Server folder browser</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {(rootsData?.roots ?? []).map((r) => (
            <Button
              key={r.path}
              size="sm"
              variant={value === r.path ? "default" : "outline"}
              disabled={disabled}
              onClick={() => navigate(r.path)}
            >
              {r.label}
            </Button>
          ))}
        </div>

        <div className="flex gap-2">
          <Input
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            placeholder="/absolute/path/to/folder"
            disabled={disabled}
          />
          <Button variant="outline" onClick={handleManualGo} disabled={disabled}>
            Go
          </Button>
        </div>

        {parent && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate(parent)}
            disabled={disabled}
          >
            ..
          </Button>
        )}

        <div className="border rounded-md max-h-72 overflow-y-auto divide-y">
          {entries.map((entry) => (
            <button
              key={entry.path}
              type="button"
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-accent text-left"
              onClick={() => navigate(entry.path)}
              disabled={disabled}
            >
              {entry.is_git ? <FolderGit2 className="h-4 w-4" /> : <Folder className="h-4 w-4" />}
              <span className="flex-1 truncate">{entry.name}</span>
              {entry.is_git && <Badge variant="secondary">git</Badge>}
              {entry.has_repos && <Badge>{`repos:${entry.repo_count}`}</Badge>}
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          ))}
          {entries.length === 0 && !error && (
            <div className="px-3 py-6 text-sm text-muted-foreground text-center">
              No subfolders.
            </div>
          )}
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="flex justify-end">
          <Button onClick={handleConfirm} disabled={disabled || !value || isGit}>
            Use this folder
          </Button>
        </div>
        {isGit && (
          <p className="text-xs text-muted-foreground">
            This folder is itself a git repository — pick its parent to register the repos
            inside.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: no errors in `ServerPathBrowser.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/setup/ServerPathBrowser.tsx
git commit -m "feat(setup-ui): add ServerPathBrowser component"
```

---

### Task 13: StepPassword component

**Files:**
- Create: `frontend/src/components/setup/StepPassword.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/setup/StepPassword.tsx`:

```tsx
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { useSetupWizardStore } from "@/features/setup/setupWizardStore"

export function StepPassword() {
  const { password, setPassword } = useSetupWizardStore((s) => ({
    password: s.password,
    setPassword: s.setPassword,
  }))

  const error =
    password.value.length > 0 && password.value.length < 8
      ? "Password must be at least 8 characters"
      : password.confirm.length > 0 && password.value !== password.confirm
        ? "Passwords do not match"
        : null

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label htmlFor="password">Admin password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          value={password.value}
          onChange={(e) => setPassword(e.target.value, password.confirm)}
          placeholder="At least 8 characters"
          autoFocus
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input
          id="confirm"
          type="password"
          autoComplete="new-password"
          value={password.confirm}
          onChange={(e) => setPassword(password.value, e.target.value)}
          placeholder="Repeat password"
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

export function isStepPasswordValid(state: { value: string; confirm: string }): boolean {
  return state.value.length >= 8 && state.value === state.confirm
}
```

- [ ] **Step 2: Type-check + commit**

```bash
cd frontend && pnpm tsc --noEmit
git add frontend/src/components/setup/StepPassword.tsx
git commit -m "feat(setup-ui): add StepPassword component"
```

---

### Task 14: StepLLM component

**Files:**
- Create: `frontend/src/components/setup/StepLLM.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/setup/StepLLM.tsx`:

```tsx
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { API_KIND_OPTIONS, type LlmApiKind } from "@/components/pipeline/api-kinds"
import {
  PURPOSES,
  REQUIRED_PURPOSES_NON_EMBEDDING,
  type Purpose,
  useSetupWizardStore,
} from "@/features/setup/setupWizardStore"
import { useProbeModels } from "@/hooks/api/use-setup-api"

const BASE_URL_DEFAULTS: Record<LlmApiKind, string> = {
  openai: "https://api.openai.com/v1",
  ollama: "http://localhost:11434/v1",
  anthropic: "https://api.anthropic.com/v1",
  google: "https://generativelanguage.googleapis.com/v1beta/openai",
  deepseek: "https://api.deepseek.com/v1",
  zai: "https://api.z.ai/api/paas/v4",
}

const PURPOSE_HINT: Record<Purpose, string> = {
  embedding: "Vector model used for memory and code search",
  extraction: "Structured-data extraction from memories",
  classification: "Memory classification and tagging",
  reasoning: "Chat answers, summaries, plan reasoning",
  summarization: "Optional — long-form summarisation calls",
  reranker: "Optional — reorders search hits",
}

export function StepLLM() {
  const llm = useSetupWizardStore((s) => s.llm)
  const setLlmField = useSetupWizardStore((s) => s.setLlmField)
  const setLlmPurpose = useSetupWizardStore((s) => s.setLlmPurpose)
  const probe = useProbeModels()
  const [probeError, setProbeError] = useState<string | null>(null)

  const handleApiKindChange = (api_kind: LlmApiKind) => {
    setLlmField("api_kind", api_kind)
    if (!llm.base_url || Object.values(BASE_URL_DEFAULTS).includes(llm.base_url)) {
      setLlmField("base_url", BASE_URL_DEFAULTS[api_kind])
    }
  }

  const handleFetchModels = async () => {
    setProbeError(null)
    try {
      const result = await probe.mutateAsync({
        api_kind: llm.api_kind as LlmApiKind,
        base_url: llm.base_url,
        api_key: llm.api_key || null,
      })
      if (result.error) {
        setProbeError(result.error)
        setLlmField("models", [])
      } else {
        setLlmField("models", result.models)
      }
    } catch (e) {
      setProbeError((e as Error).message)
    }
  }

  const visiblePurposes = PURPOSES.filter(
    (p) => p !== "embedding" || llm.supports_embedding,
  )

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Provider</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Display name</Label>
              <Input
                value={llm.provider_name}
                onChange={(e) => setLlmField("provider_name", e.target.value)}
                placeholder="e.g. OpenAI"
              />
            </div>
            <div className="space-y-1">
              <Label>API kind</Label>
              <Select
                value={llm.api_kind}
                onValueChange={(v) => handleApiKindChange(v as LlmApiKind)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {API_KIND_OPTIONS.map((k) => (
                    <SelectItem key={k.value} value={k.value}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <Label>Base URL</Label>
            <Input
              value={llm.base_url}
              onChange={(e) => setLlmField("base_url", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>API key</Label>
            <Input
              type="password"
              value={llm.api_key}
              onChange={(e) => setLlmField("api_key", e.target.value)}
              placeholder={llm.api_kind === "ollama" ? "(not required for Ollama)" : "sk-..."}
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={llm.supports_embedding}
              onCheckedChange={(v) => setLlmField("supports_embedding", v)}
            />
            <span className="text-sm">Provider supports embeddings</span>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleFetchModels} disabled={probe.isPending}>
              {probe.isPending ? "Fetching..." : "Fetch available models"}
            </Button>
            {llm.models.length > 0 && (
              <span className="text-sm text-muted-foreground">
                {llm.models.length} model{llm.models.length === 1 ? "" : "s"} loaded
              </span>
            )}
          </div>
          {probeError && (
            <p role="alert" className="text-sm text-destructive">
              {probeError}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Per-purpose models</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {visiblePurposes.map((purpose) => {
            const draft = llm.perPurpose[purpose]
            const required =
              purpose === "embedding"
                ? llm.supports_embedding
                : REQUIRED_PURPOSES_NON_EMBEDDING.includes(purpose)
            return (
              <div
                key={purpose}
                className="grid grid-cols-[140px,1fr,auto] gap-3 items-center"
              >
                <div>
                  <div className="text-sm font-medium capitalize">
                    {purpose}
                    {required && <span className="text-destructive ml-1">*</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">{PURPOSE_HINT[purpose]}</div>
                </div>
                <div className="flex flex-col gap-1">
                  <Input
                    list={`models-${purpose}`}
                    value={draft.model}
                    onChange={(e) => setLlmPurpose(purpose, { model: e.target.value })}
                    placeholder="model id"
                  />
                  <datalist id={`models-${purpose}`}>
                    {llm.models.map((m) => (
                      <option key={m} value={m} />
                    ))}
                  </datalist>
                </div>
                {purpose !== "embedding" && purpose !== "reranker" ? (
                  <label className="flex items-center gap-2 text-xs">
                    <Switch
                      checked={draft.reasoning}
                      onCheckedChange={(v) => setLlmPurpose(purpose, { reasoning: v })}
                    />
                    reasoning
                  </label>
                ) : (
                  <span />
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

export function isStepLLMValid(llm: ReturnType<typeof useSetupWizardStore.getState>["llm"]): boolean {
  if (llm.skipped) return true
  if (!llm.provider_name.trim()) return false
  if (!llm.base_url.trim()) return false
  if (llm.supports_embedding && !llm.perPurpose.embedding.model.trim()) return false
  for (const p of REQUIRED_PURPOSES_NON_EMBEDDING) {
    if (!llm.perPurpose[p].model.trim()) return false
  }
  return true
}
```

- [ ] **Step 2: Type-check + commit**

```bash
cd frontend && pnpm tsc --noEmit
git add frontend/src/components/setup/StepLLM.tsx
git commit -m "feat(setup-ui): add StepLLM with model probe"
```

---

### Task 15: StepRepoPath component

**Files:**
- Create: `frontend/src/components/setup/StepRepoPath.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/setup/StepRepoPath.tsx`:

```tsx
import { useEffect } from "react"
import { useSetupWizardStore, type DetectedRepo } from "@/features/setup/setupWizardStore"
import { fsList } from "@/hooks/api/use-setup-api"
import { ServerPathBrowser } from "./ServerPathBrowser"

export function StepRepoPath() {
  const repos = useSetupWizardStore((s) => s.repos)
  const setReposBasePath = useSetupWizardStore((s) => s.setReposBasePath)
  const setReposDetected = useSetupWizardStore((s) => s.setReposDetected)

  // Re-derive the basePath display from the store
  useEffect(() => {
    if (!repos.basePath) setReposDetected([])
  }, [repos.basePath, setReposDetected])

  const handleConfirm = async (path: string) => {
    setReposBasePath(path)
    const result = await fsList("/setup", path, true)
    const detected: DetectedRepo[] = result.entries
      .filter((e) => e.is_git)
      .map((e) => ({
        name: e.name,
        subPath: e.name,
        selected: true,
      }))
    setReposDetected(detected)
  }

  return (
    <div className="space-y-4">
      <ServerPathBrowser
        apiBase="/setup"
        value={repos.basePath}
        onChange={setReposBasePath}
        onConfirm={handleConfirm}
      />
      {repos.basePath && (
        <div className="text-sm text-muted-foreground">
          Selected base path: <span className="font-mono">{repos.basePath}</span>
          {repos.detected.length > 0 ? (
            <> — found <strong>{repos.detected.length}</strong> repository(ies). Review them on the next step.</>
          ) : (
            <> — no immediate-child repositories detected.</>
          )}
        </div>
      )}
    </div>
  )
}

export function isStepRepoPathValid(repos: { basePath: string; skipped: boolean }): boolean {
  if (repos.skipped) return true
  return repos.basePath.length > 0
}
```

- [ ] **Step 2: Type-check + commit**

```bash
cd frontend && pnpm tsc --noEmit
git add frontend/src/components/setup/StepRepoPath.tsx
git commit -m "feat(setup-ui): add StepRepoPath using ServerPathBrowser"
```

---

### Task 16: StepFinish component

**Files:**
- Create: `frontend/src/components/setup/StepFinish.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/setup/StepFinish.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { useSetupWizardStore, PURPOSES } from "@/features/setup/setupWizardStore"

export function StepFinish() {
  const password = useSetupWizardStore((s) => s.password)
  const llm = useSetupWizardStore((s) => s.llm)
  const repos = useSetupWizardStore((s) => s.repos)
  const toggle = useSetupWizardStore((s) => s.toggleRepoSelected)
  const rename = useSetupWizardStore((s) => s.renameDetectedRepo)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Admin password</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {password.value ? "Set" : "Not set"}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Default LLM provider</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-1">
          {llm.skipped || !llm.provider_name ? (
            <span className="text-muted-foreground">Skipped — system defaults will be used.</span>
          ) : (
            <>
              <div>
                <strong>{llm.provider_name}</strong> ({llm.api_kind})
              </div>
              <ul className="ml-4 list-disc">
                {PURPOSES.filter(
                  (p) => (p !== "embedding" || llm.supports_embedding) && llm.perPurpose[p].model,
                ).map((p) => (
                  <li key={p}>
                    <span className="capitalize">{p}</span>: <span className="font-mono">{llm.perPurpose[p].model}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Default code repo path</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          {repos.skipped || !repos.basePath ? (
            <span className="text-muted-foreground">Skipped — configure later under Settings.</span>
          ) : (
            <>
              <div>
                Base path: <span className="font-mono">{repos.basePath}</span>
              </div>
              {repos.detected.length === 0 ? (
                <div className="text-muted-foreground">No repositories detected.</div>
              ) : (
                <div className="space-y-1">
                  {repos.detected.map((r) => (
                    <div key={r.subPath} className="flex items-center gap-2">
                      <Checkbox
                        checked={r.selected}
                        onCheckedChange={() => toggle(r.subPath)}
                      />
                      <Input
                        className="h-8 flex-1"
                        value={r.name}
                        onChange={(e) => rename(r.subPath, e.target.value)}
                      />
                      <span className="text-xs text-muted-foreground font-mono">{r.subPath}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Type-check + commit**

```bash
cd frontend && pnpm tsc --noEmit
git add frontend/src/components/setup/StepFinish.tsx
git commit -m "feat(setup-ui): add StepFinish review summary"
```

---

### Task 17: SetupWizard shell + route migration

**Files:**
- Create: `frontend/src/components/setup/SetupWizard.tsx`
- Modify: `frontend/src/routes/_guest/setup.tsx` (full rewrite)

- [ ] **Step 1: Create the wizard shell**

Create `frontend/src/components/setup/SetupWizard.tsx`:

```tsx
import { useNavigate } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent } from "darkraise-ui/components/card"
import { toast } from "sonner"
import { useSetupWizardStore, PURPOSES } from "@/features/setup/setupWizardStore"
import { useFinalizeSetup, type SetupRequest } from "@/hooks/api/use-setup-api"
import { StepPassword, isStepPasswordValid } from "./StepPassword"
import { StepLLM, isStepLLMValid } from "./StepLLM"
import { StepRepoPath, isStepRepoPathValid } from "./StepRepoPath"
import { StepFinish } from "./StepFinish"

const STEP_TITLES: Record<1 | 2 | 3 | 4, string> = {
  1: "Admin password",
  2: "Default LLM provider",
  3: "Default code repo path",
  4: "Finish setup",
}

export function SetupWizard() {
  const navigate = useNavigate()
  const step = useSetupWizardStore((s) => s.step)
  const setStep = useSetupWizardStore((s) => s.setStep)
  const setLlmSkipped = useSetupWizardStore((s) => s.setLlmSkipped)
  const setReposSkipped = useSetupWizardStore((s) => s.setReposSkipped)
  const password = useSetupWizardStore((s) => s.password)
  const llm = useSetupWizardStore((s) => s.llm)
  const repos = useSetupWizardStore((s) => s.repos)
  const reset = useSetupWizardStore((s) => s.reset)
  const finalize = useFinalizeSetup()

  const stepValid =
    step === 1
      ? isStepPasswordValid(password)
      : step === 2
        ? isStepLLMValid(llm)
        : step === 3
          ? isStepRepoPathValid(repos)
          : true

  const goNext = () => {
    if (step === 1 && !isStepPasswordValid(password)) return
    if (step === 2) setLlmSkipped(false)
    if (step === 3) setReposSkipped(false)
    if (step < 4) setStep((step + 1) as 1 | 2 | 3 | 4)
  }
  const goBack = () => {
    if (step > 1) setStep((step - 1) as 1 | 2 | 3 | 4)
  }
  const skip = () => {
    if (step === 2) {
      setLlmSkipped(true)
      setStep(3)
    } else if (step === 3) {
      setReposSkipped(true)
      setStep(4)
    }
  }

  const buildRequest = (): SetupRequest => {
    const body: SetupRequest = { password: password.value }
    if (!llm.skipped && llm.provider_name) {
      const purposes: NonNullable<SetupRequest["llm"]>["purposes"] = {}
      for (const p of PURPOSES) {
        if (p === "embedding" && !llm.supports_embedding) continue
        const draft = llm.perPurpose[p]
        if (!draft.model.trim()) continue
        purposes[p] = {
          model: draft.model.trim(),
          reasoning: draft.reasoning,
          dimensions: draft.dimensions ?? null,
        }
      }
      body.llm = {
        provider_name: llm.provider_name.trim(),
        api_kind: llm.api_kind,
        base_url: llm.base_url.trim(),
        api_key: llm.api_key || null,
        supports_embedding: llm.supports_embedding,
        purposes,
      }
    }
    if (!repos.skipped && repos.basePath) {
      body.repos = {
        base_path: repos.basePath,
        repos: repos.detected
          .filter((r) => r.selected)
          .map((r) => ({ name: r.name.trim(), sub_path: r.subPath })),
      }
    }
    return body
  }

  const handleFinish = async () => {
    try {
      const result = await finalize.mutateAsync(buildRequest())
      if (!result.llm.ok && result.llm.message) {
        toast.warning(`LLM setup partial: ${result.llm.message}`)
      }
      for (const f of result.repos_failed) {
        toast.warning(`Repo "${f.name}" not added: ${f.error}`)
      }
      reset()
      navigate({ to: "/" })
    } catch (e) {
      toast.error(`Setup failed: ${(e as Error).message}`)
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-4">
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold font-mono">darkmem</h1>
        <p className="text-sm text-muted-foreground">{STEP_TITLES[step]}</p>
      </div>
      <ol className="flex justify-center gap-2 text-xs">
        {[1, 2, 3, 4].map((s) => (
          <li
            key={s}
            className={`px-3 py-1 rounded-md border ${
              s === step
                ? "border-primary text-primary"
                : s < step
                  ? "border-muted text-muted-foreground line-through"
                  : "border-muted text-muted-foreground"
            }`}
          >
            {s}. {STEP_TITLES[s as 1 | 2 | 3 | 4]}
          </li>
        ))}
      </ol>

      <Card>
        <CardContent className="pt-6">
          {step === 1 && <StepPassword />}
          {step === 2 && <StepLLM />}
          {step === 3 && <StepRepoPath />}
          {step === 4 && <StepFinish />}
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button variant="ghost" onClick={goBack} disabled={step === 1 || finalize.isPending}>
          Back
        </Button>
        <div className="flex gap-2">
          {(step === 2 || step === 3) && (
            <Button variant="outline" onClick={skip}>
              Skip
            </Button>
          )}
          {step < 4 ? (
            <Button onClick={goNext} disabled={!stepValid}>
              Next
            </Button>
          ) : (
            <Button onClick={handleFinish} disabled={finalize.isPending}>
              {finalize.isPending ? "Finishing..." : "Finish"}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Replace the route file**

Overwrite `frontend/src/routes/_guest/setup.tsx`:

```tsx
import { createFileRoute, redirect } from "@tanstack/react-router"
import { checkSetupStatus } from "@/lib/api"
import { SetupWizard } from "@/components/setup/SetupWizard"

export const Route = createFileRoute("/_guest/setup")({
  beforeLoad: async () => {
    const { initialized } = await checkSetupStatus()
    if (initialized) {
      throw redirect({ to: "/login" })
    }
  },
  component: SetupWizard,
})
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/setup/SetupWizard.tsx frontend/src/routes/_guest/setup.tsx
git commit -m "feat(setup-ui): wire SetupWizard into /setup route"
```

---

### Task 18: Settings page "Default code repo path" card

**Files:**
- Modify: `frontend/src/routes/_authenticated/settings.tsx`

- [ ] **Step 1: Add the card component**

Inside `frontend/src/routes/_authenticated/settings.tsx`, add a new component near the other Card components (before `function SettingsPage`). First import the hooks and the browser:

```tsx
import { useReposPath, useUpdateReposPath } from "@/hooks/api/use-setup-api"
import { ServerPathBrowser } from "@/components/setup/ServerPathBrowser"
```

Then define the component:

```tsx
function ReposPathCard() {
  const { data, isLoading } = useReposPath()
  const update = useUpdateReposPath()
  const [draft, setDraft] = useState<string>("")

  useEffect(() => {
    if (data?.path) setDraft(data.path)
  }, [data?.path])

  const handleSave = async (path: string) => {
    try {
      await update.mutateAsync({ path })
      setDraft(path)
      toast.success("Default code repo path saved")
    } catch (e) {
      toast.error(`Save failed: ${(e as Error).message}`)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Default code repo path</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-32 bg-muted rounded animate-pulse" />
        ) : (
          <ServerPathBrowser
            apiBase="/system"
            value={draft}
            onChange={setDraft}
            onConfirm={handleSave}
          />
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Mount the card in the settings layout**

Settings has six tabs: `flags`, `classification`, `workers`, `assistant`, `llm-providers`, `llm-profiles`. Mount `<ReposPathCard />` inside `<TabsContent value="flags" className="mt-4">` (the most general bucket — feature flags + repo path = top-level system configuration). Add it after the existing flags content but before closing `</TabsContent>`.

- [ ] **Step 3: Type-check**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/_authenticated/settings.tsx
git commit -m "feat(settings): add Default code repo path card"
```

---

## Phase 3 — Verification

### Task 19: Run the full backend test suite

- [ ] **Step 1: Run pytest**

```bash
cd backend && python -m pytest -v
```

Expected: PASS for every test. Pay attention to:
- `test_setup_route.py` — every wizard endpoint
- `test_repos.py` — `validate_local_path` round-trip
- Any test that previously hit `/api/v1/auth/setup` or `/api/v1/auth/status` should now use the new paths.

If any test fails, investigate the root cause before proceeding. Don't move on with red tests.

- [ ] **Step 2: Run the e2e auth script (smoke check)**

Bring up the backend (locally with the dev DB) and run:

```bash
python docs/e2e/scripts/01_auth_flow.py --base-url http://localhost:8000 --password e2e-admin-pw
```

Expected: every assertion `[PASS]`. If any line says `[FAIL]`, fix the cause.

---

### Task 20: Manual Playwright sweep

- [ ] **Step 1: Start the backend with a fresh DB**

Ensure `darkmem` DB is reset (drop + alembic upgrade). Start `uvicorn app.main:app --reload --port 8000`.

- [ ] **Step 2: Start the frontend**

```bash
cd frontend && pnpm dev
```

- [ ] **Step 3: Drive the wizard end-to-end (full path)**

In a browser at the frontend URL:
1. Confirm a redirect to `/setup` (because `initialized=false`).
2. Step 1: enter password "test-admin-pw" twice. Click Next.
3. Step 2: pick "OpenAI" as api_kind, paste a real test key, click "Fetch available models", pick a model for embedding, extraction, classification, reasoning. Click Next.
4. Step 3: navigate to a folder containing existing git repos. Click "Use this folder". Confirm the count appears.
5. Step 4: review summary, leave all repos checked, click Finish.
6. Confirm redirect to `/`, the user is logged in, and toast warnings (if any) match `repos_failed` in the response.

- [ ] **Step 4: Reset DB and run skip-LLM path**

Reset DB. Repeat steps 1 → 4 with Skip pressed on step 2. Confirm Finish completes; visit Settings → LLM Providers and confirm no rows.

- [ ] **Step 5: Reset DB and run skip-repos path**

Reset DB. Repeat with Skip on step 3. Confirm Finish completes; visit Settings → Default code repo path card and confirm the field is empty. Set a path through the Settings card and confirm it persists.

- [ ] **Step 6: Confirm post-init guard**

While logged out (clear cookies), navigate to `/setup`. Confirm redirect to `/login`. Hit `POST /api/v1/setup` with curl directly — expect 403.

- [ ] **Step 7: Commit any tweaks discovered during the sweep**

If small UI bugs surface during the sweep, fix them and commit each as a separate small commit referencing the wizard ("fix(setup-ui): ..."). Re-run the sweep after each fix until every checkbox above passes.

---

## File Inventory Recap

**Created:**
- `backend/app/api/routes/setup.py`
- `backend/app/api/routes/system.py`
- `backend/tests/test_setup_route.py`
- `frontend/src/features/setup/setupWizardStore.ts`
- `frontend/src/hooks/api/use-setup-api.ts`
- `frontend/src/components/setup/ServerPathBrowser.tsx`
- `frontend/src/components/setup/StepPassword.tsx`
- `frontend/src/components/setup/StepLLM.tsx`
- `frontend/src/components/setup/StepRepoPath.tsx`
- `frontend/src/components/setup/StepFinish.tsx`
- `frontend/src/components/setup/SetupWizard.tsx`

**Modified:**
- `backend/app/api/auth.py` — `require_uninitialized` dependency.
- `backend/app/api/routes/auth.py` — removed `auth_setup`, `auth_status`.
- `backend/app/api/routes/config.py` — `repos-path` GET/PUT.
- `backend/app/services/repo_manager.py` — `must_not_be_repo` flag.
- `backend/app/main.py` — register `setup` and `system` routers.
- `backend/tests/test_repos.py` — new validate_local_path tests.
- `frontend/src/lib/api.ts` — repoint `checkSetupStatus`, remove `setup`, export `useAuthStore`.
- `frontend/src/hooks/api/index.ts` — re-export setup hooks.
- `frontend/src/routes/_guest/setup.tsx` — render `SetupWizard`.
- `frontend/src/routes/_authenticated/settings.tsx` — add `ReposPathCard`.
- `docs/e2e/scripts/lib/client.py` — point at new endpoints.
- `docs/e2e/scripts/01_auth_flow.py` — point at new endpoints, expect 403.
- `backend/scripts/seed_test_memories.py` — point at new endpoints.
