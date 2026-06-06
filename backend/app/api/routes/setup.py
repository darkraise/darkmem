"""Setup wizard router.

All endpoints under ``/api/v1/setup/*`` are gated by ``require_uninitialized``
except ``GET /api/v1/setup/status`` (which is the public probe used by the
wizard's route guard). Once the admin password is set, every wizard endpoint
returns 403, and the wizard frontend redirects new visitors to ``/login``.
"""
from __future__ import annotations

import hmac
import logging
import os
import sys
import uuid
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
from app.config import settings
from app.database import get_session
from app.models.audit import AuditLog
from app.models.code import Repository
from app.models.config import Config
from app.models.llm_config import LLMProfile, LLMProvider, LLMPurposeConfigRow
from app.services.repo_manager import validate_local_path

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])
logger = logging.getLogger(__name__)

ADMIN_PASSWORD_KEY = "admin_password_hash"
REPOS_PATH_KEY = "repos_default_local_path"

PURPOSE_LITERAL = Literal[
    "embedding", "extraction", "classification",
    "reasoning", "summarization", "reranker",
]


def _check_setup_secret(presented: str | None) -> None:
    """Compare a presented secret against ``SETUP_SECRET``.

    When a secret is configured, require a matching one (constant-time compare).
    When none is configured the endpoint stays open for the no-credentials local
    install path — except in production, where the startup validator guarantees a
    secret, so an unset value here is a misconfiguration.
    """
    expected = settings.setup_secret
    if not expected:
        if _is_production():
            raise HTTPException(
                status_code=503,
                detail="SETUP_SECRET is not configured on the server",
            )
        return
    if not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing setup secret")


def require_setup_secret(request: Request) -> None:
    """Dependency gating header-only pre-setup endpoints (fs browse, model probe).

    These have no request body to carry the secret, so they accept it via the
    ``X-Setup-Secret`` header. Like the finalize gate, this is a no-op outside
    production when no secret is configured.
    """
    _check_setup_secret(request.headers.get("X-Setup-Secret"))


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
    dependencies=[Depends(require_uninitialized), Depends(require_setup_secret)],
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


# Intentional exposure: on a no-secret, non-production install these two
# filesystem-browse endpoints are reachable before an admin password exists, so
# any client on the network can enumerate host drives. This is the documented
# local-install convenience path (the wizard needs to browse for a repo folder
# before credentials are set). require_setup_secret blocks it once a
# SETUP_SECRET is configured, and the startup validator forces a secret in
# production — so the open window only exists for the explicit local trust
# model. See docs/api-rest-conventions.md and config._check_setup_secret.
@router.get(
    "/fs/roots",
    response_model=FsRootsResponse,
    dependencies=[Depends(require_uninitialized), Depends(require_setup_secret)],
)
async def fs_roots() -> FsRootsResponse:
    return FsRootsResponse(roots=_enumerate_roots())


@router.get(
    "/fs/list",
    response_model=FsListResponse,
    dependencies=[Depends(require_uninitialized), Depends(require_setup_secret)],
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
    api_kind: str
    base_url: str | None = None
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
    setup_secret: str | None = None
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


def _is_production() -> bool:
    # NOTE: this predicate is broader than config.py's startup validators
    # (_check_jwt_secret / _check_setup_secret), which gate solely on
    # ``settings.environment == "production"``. The extra ``/.dockerenv`` probe
    # here can classify a containerized non-prod install as production and
    # demand a SETUP_SECRET the startup validator never required — a self-
    # lockout. Keep the two definitions in sync; prefer config.py's as the
    # source of truth if they are ever unified.
    return settings.environment == "production" or os.path.exists("/.dockerenv")


def _enforce_setup_secret(request: Request, body: SetupRequest) -> None:
    """Gate the finalize endpoint behind ``SETUP_SECRET`` in production.

    ``config._check_setup_secret`` guarantees ``settings.setup_secret`` is a
    non-empty string at startup in production, but nothing actually compared
    the caller's input against it — the prod guard was a no-op. Require the
    caller to present the matching secret (``X-Setup-Secret`` header or the
    request body) before any admin-bootstrap write happens.

    Outside production the secret is optional: if one is configured we still
    enforce it, otherwise the endpoint stays open (gated only by
    ``require_uninitialized``) for the no-credentials local install path.
    """
    _check_setup_secret(request.headers.get("X-Setup-Secret") or body.setup_secret)


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

    _enforce_setup_secret(request, body)

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

        # 2. LLM block — optional. Inserts the full default seed
        # (DEFAULT_PROVIDERS + DEFAULT_PROFILES + DEFAULT_PURPOSE_CONFIGS)
        # so the user finishes setup with a fully populated menu of
        # vendors and preset profiles. The user's api_key is applied
        # to the matching api_kind row; their per-purpose model
        # selections override the default purpose-config rows. This
        # replaces the pre-refactor "single provider, six profiles"
        # path AND removes the dependency on migration-seeded rows
        # that the pre-refactor handler upserted into.
        if body.llm is not None:
            try:
                from app.services.llm_seed import (
                    DEFAULT_PROVIDERS,
                    DEFAULT_PROFILES,
                    DEFAULT_PURPOSE_CONFIGS,
                    provider_seed_by_kind,
                )

                # Insert every seeded provider. The matching api_kind
                # row gets the user-supplied api_key and (optionally)
                # an overridden base_url and supports_embedding flag.
                provider_id_by_name: dict[str, uuid.UUID] = {}
                for ps in DEFAULT_PROVIDERS:
                    is_user_choice = (ps.api_kind == body.llm.api_kind)
                    provider = LLMProvider(
                        name=ps.name,
                        provider=ps.provider,
                        base_url=(body.llm.base_url or ps.base_url) if is_user_choice else ps.base_url,
                        api_key=body.llm.api_key if is_user_choice else None,
                        api_kind=ps.api_kind,
                        supports_embedding=(
                            body.llm.supports_embedding if is_user_choice else ps.supports_embedding
                        ),
                    )
                    if is_user_choice and body.llm.api_key:
                        provider.api_key_rotated_at = datetime.now(timezone.utc)
                    session.add(provider)
                    await session.flush()
                    provider_id_by_name[ps.name] = provider.id

                # Insert every seeded profile.
                profile_id_by_name: dict[str, uuid.UUID] = {}
                for prof in DEFAULT_PROFILES:
                    profile = LLMProfile(
                        name=prof.name,
                        provider_id=provider_id_by_name[prof.provider_name],
                        model=prof.model,
                        params=dict(prof.params),
                        is_embedding=prof.is_embedding,
                        reasoning=prof.reasoning,
                    )
                    session.add(profile)
                    await session.flush()
                    profile_id_by_name[prof.name] = profile.id

                # Insert default purpose configs (Ollama defaults so a
                # no-credentials install still runs end-to-end).
                purpose_rows: dict[str, LLMPurposeConfigRow] = {}
                for pc in DEFAULT_PURPOSE_CONFIGS:
                    row = LLMPurposeConfigRow(
                        purpose=pc.purpose,
                        provider_id=provider_id_by_name.get(pc.provider_name),
                        profile_id=None,
                        model=pc.model,
                        dimensions=pc.dimensions,
                        reasoning=pc.reasoning,
                        api_kind=pc.api_kind,
                        provider=pc.provider,
                        base_url=pc.base_url,
                        api_key=None,
                        params=dict(pc.params),
                    )
                    session.add(row)
                    purpose_rows[pc.purpose] = row
                await session.flush()

                # Apply user choices on top: for each purpose the user
                # picked a model for, overlay api_kind / base_url /
                # api_key / model onto the seeded purpose-config row,
                # and create a ``default-<purpose>`` profile pointing
                # at the user's vendor for the dropdown to surface.
                user_provider_seed = provider_seed_by_kind(body.llm.api_kind)
                user_provider_id = (
                    provider_id_by_name.get(user_provider_seed.name)
                    if user_provider_seed else None
                )
                user_base_url = body.llm.base_url or (
                    user_provider_seed.base_url if user_provider_seed else ""
                )
                from app.services.llm_seed import DEFAULT_PROFILES

                for purpose_key, spec in body.llm.purposes.items():
                    is_embedding = (purpose_key == "embedding")

                    # Inherit the vendor's reasoning-control params for this
                    # purpose (reasoning_effort / thinking / max_tokens) from the
                    # seed instead of blanking to {}, which the orchestrator
                    # depends on to disable hidden CoT (e.g. google/gpt-5).
                    seed_candidates = [
                        p for p in DEFAULT_PROFILES
                        if p.name.startswith(f"{body.llm.api_kind}-")
                        and p.name.endswith(purpose_key)
                    ]
                    seed_match = next(
                        (c for c in seed_candidates if c.model == spec.model),
                        seed_candidates[0] if seed_candidates else None,
                    )
                    seed_params = dict(seed_match.params) if seed_match else {}

                    user_profile = LLMProfile(
                        name=f"default-{purpose_key}",
                        provider_id=user_provider_id,
                        model=spec.model,
                        params=seed_params,
                        is_embedding=is_embedding,
                        reasoning=False if is_embedding else spec.reasoning,
                    )
                    session.add(user_profile)
                    await session.flush()

                    pcfg = purpose_rows.get(purpose_key)
                    if pcfg is None:
                        # Should not happen for the six canonical
                        # purposes; create the row defensively.
                        pcfg = LLMPurposeConfigRow(purpose=purpose_key, model="")
                        session.add(pcfg)
                    pcfg.provider_id = user_provider_id
                    pcfg.profile_id = user_profile.id
                    pcfg.model = spec.model
                    pcfg.dimensions = spec.dimensions if is_embedding else None
                    pcfg.reasoning = False if is_embedding else spec.reasoning
                    pcfg.api_kind = body.llm.api_kind
                    pcfg.provider = body.llm.api_kind
                    pcfg.base_url = user_base_url
                    pcfg.api_key = body.llm.api_key
                    pcfg.params = seed_params
                    pcfg.updated_at = datetime.now(timezone.utc)

                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Setup LLM finalize failed")
                # Don't leak the raw exception (could carry a DB DSN, host
                # path, or vendor error body) to an unauthenticated caller;
                # the detail is in the server log.
                llm_status = SetupSectionStatus(
                    ok=False,
                    message="LLM configuration failed; see server logs for details.",
                )

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
            except Exception:
                await session.rollback()
                logger.exception("Setup repos base-path finalize failed")
                repos_status = SetupSectionStatus(
                    ok=False,
                    message="Repository base path could not be configured; "
                    "see server logs for details.",
                )
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
                    except ValueError as exc:
                        # validate_local_path raises user-actionable validation
                        # messages (bad/dubious path); surfacing those helps the
                        # operator fix the input.
                        await session.rollback()
                        repos_failed.append({"name": entry.name, "error": str(exc)})
                    except Exception:
                        await session.rollback()
                        logger.exception("Setup repo %r finalize failed", entry.name)
                        repos_failed.append({
                            "name": entry.name,
                            "error": "could not be added; see server logs for details.",
                        })

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
