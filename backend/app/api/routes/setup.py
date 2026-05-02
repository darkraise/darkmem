"""Setup wizard router.

All endpoints under ``/api/v1/setup/*`` are gated by ``require_uninitialized``
except ``GET /api/v1/setup/status`` (which is the public probe used by the
wizard's route guard). Once the admin password is set, every wizard endpoint
returns 403, and the wizard frontend redirects new visitors to ``/login``.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    create_access_token,
    hash_password,
    require_uninitialized,
    set_auth_cookie,
)
from app.database import get_session
from app.models.audit import AuditLog
from app.models.code import Repository
from app.models.config import Config
from app.models.llm_config import LLMProfile, LLMProvider, LLMPurposeConfigRow
from app.services.repo_manager import validate_local_path

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

ADMIN_PASSWORD_KEY = "admin_password_hash"
REPOS_PATH_KEY = "repos_default_local_path"

PURPOSE_LITERAL = Literal[
    "embedding", "extraction", "classification",
    "reasoning", "summarization", "reranker",
]


# ── Status ────────────────────────────────────────────────────────────


class StatusResponse(BaseModel):
    initialized: bool


@router.get("/status", response_model=StatusResponse)
async def setup_status(session: AsyncSession = Depends(get_session)) -> StatusResponse:
    result = await session.execute(
        select(Config).where(Config.key == ADMIN_PASSWORD_KEY)
    )
    return StatusResponse(initialized=result.scalar_one_or_none() is not None)


# ── Probe-models ──────────────────────────────────────────────────────


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
        if not body.api_key:
            return ProbeModelsResponse(
                models=[],
                fetched_via="openai_compat:/v1/models",
                error=f"API key required for api_kind={body.api_kind!r}",
            )
        if body.api_kind == "anthropic":
            headers["x-api-key"] = body.api_key
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


# ── Filesystem browse ────────────────────────────────────────────────


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


# ── Finalize ──────────────────────────────────────────────────────────


class SetupLLMPurpose(BaseModel):
    model: str
    reasoning: bool = False
    dimensions: int | None = None


class SetupLLM(BaseModel):
    provider_name: str = Field(min_length=1, max_length=64)
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

    repos_added: list[str] = []
    repos_failed: list[dict] = []
    llm_status = SetupSectionStatus(ok=True)
    repos_status = SetupSectionStatus(ok=True)

    async with request.app.state.llm_config_lock:
        # 1. Password block — required. Commit immediately so subsequent
        # rollbacks (for failed LLM / repo blocks) don't undo it.
        session.add(Config(
            key=ADMIN_PASSWORD_KEY,
            value={"hash": hash_password(body.password)},
        ))
        session.add(AuditLog(
            action="auth_setup",
            details={"ip": _client_ip(request)},
        ))
        await session.commit()

        # 2. LLM block — optional. All-or-nothing: any exception rolls
        # back the partial LLM writes only.
        if body.llm is not None:
            try:
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

                    # Upsert: migrations seed a default row per purpose so we
                    # update it in place rather than insert a conflicting one.
                    existing_purpose = (await session.execute(
                        select(LLMPurposeConfigRow).where(
                            LLMPurposeConfigRow.purpose == purpose_key
                        )
                    )).scalar_one_or_none()
                    if existing_purpose is None:
                        session.add(LLMPurposeConfigRow(
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
                        ))
                    else:
                        existing_purpose.provider_id = provider.id
                        existing_purpose.profile_id = profile.id
                        existing_purpose.model = spec.model
                        existing_purpose.dimensions = spec.dimensions if is_embedding else None
                        existing_purpose.reasoning = False if is_embedding else spec.reasoning
                        existing_purpose.api_kind = body.llm.api_kind
                        existing_purpose.provider = body.llm.api_kind
                        existing_purpose.base_url = body.llm.base_url
                        existing_purpose.api_key = body.llm.api_key
                        existing_purpose.params = {}
                        existing_purpose.updated_at = datetime.now(timezone.utc)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                llm_status = SetupSectionStatus(ok=False, message=str(exc))

        # 3. Repos block — optional, per-row isolated.
        if body.repos is not None:
            try:
                base_resolved = validate_local_path(
                    body.repos.base_path, must_not_be_repo=True,
                )
                existing = (await session.execute(
                    select(Config).where(Config.key == REPOS_PATH_KEY)
                )).scalar_one_or_none()
                if existing:
                    existing.value = {"path": str(base_resolved)}
                else:
                    session.add(Config(
                        key=REPOS_PATH_KEY,
                        value={"path": str(base_resolved)},
                    ))
                await session.commit()
            except Exception as exc:
                await session.rollback()
                repos_status = SetupSectionStatus(ok=False, message=str(exc))
            else:
                from app.services.repo_manager import add_git_safe_directory
                for entry in body.repos.repos:
                    try:
                        full_path = validate_local_path(
                            str(Path(body.repos.base_path) / entry.sub_path)
                        )
                        # Whitelist the working tree before the first
                        # periodic fetch tries to operate on it. Without
                        # this, wizard-imported repos owned by a different
                        # uid than the backend process trip git's
                        # "dubious ownership" guard on every sync.
                        await add_git_safe_directory(full_path)
                        # Wizard-imported repos default to auto_sync=False so
                        # the first periodic tick doesn't immediately try to
                        # fetch every detected folder. The user reviews them
                        # on the Repositories page and flips Auto-sync on per
                        # repo from the Edit dialog once they're sure each
                        # one should be auto-pulled. Manual reindex still
                        # works regardless of auto_sync, so any repo can be
                        # walked into the index without enabling auto-sync.
                        session.add(Repository(
                            name=entry.name,
                            provider="local",
                            local_path=str(full_path),
                            default_branch="main",
                            status="ready",
                            auto_sync=False,
                        ))
                        await session.commit()
                        repos_added.append(entry.name)
                    except Exception as exc:
                        await session.rollback()
                        repos_failed.append({"name": entry.name, "error": str(exc)})

        # 4. Rebuild the live orchestrator if the LLM block landed.
        if body.llm is not None and llm_status.ok:
            from app.api.routes.config import _replace_orchestrator
            new_config = await fetch_llm_config(session)
            new_llm = LLMOrchestrator(new_config)
            _replace_orchestrator(request, new_llm)

        # 5. Audit log
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
