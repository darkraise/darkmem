"""Setup wizard router.

All endpoints under ``/api/v1/setup/*`` are gated by ``require_uninitialized``
except ``GET /api/v1/setup/status`` (which is the public probe used by the
wizard's route guard). Once the admin password is set, every wizard endpoint
returns 403, and the wizard frontend redirects new visitors to ``/login``.
"""
from __future__ import annotations

import logging
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
from app.models.code import Repository
from app.models.config import Config
from app.services.events import record_event
from app.models.llm_config import LLMPurposeConfigRow
from app.services.llm_quirks import models_probe, quirks_for
from app.services.model_probe import parse_model_list
from app.services.repo_manager import validate_local_path

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])
logger = logging.getLogger(__name__)

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
    target = models_probe(body.api_kind, body.base_url, body.api_key)
    url, kind_label = target.url, target.label
    if quirks_for(body.api_kind).requires_api_key and not body.api_key:
        return ProbeModelsResponse(
            models=[],
            fetched_via=kind_label,
            error=f"API key required for api_kind={body.api_kind!r}",
        )
    headers = {"Accept": "application/json", **target.headers}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client_:
            resp = await client_.get(url, headers=headers)
        if not resp.is_success:
            return ProbeModelsResponse(
                models=[], fetched_via=kind_label,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        return ProbeModelsResponse(
            models=[], fetched_via=kind_label, error=f"network error: {exc}",
        )

    models = parse_model_list(data)
    return ProbeModelsResponse(models=models, fetched_via=kind_label)


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


# Intentional exposure: before an admin password exists these two
# filesystem-browse endpoints are reachable by any client on the network (gated
# only by require_uninitialized), so a network peer can enumerate host drives
# during the pre-setup window. This is the accepted trust-on-first-use model for
# a local/LAN install — the wizard needs to browse for a repo folder before
# credentials are set, and the first caller to finish /setup closes the window.
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
        await record_event(
            session,
            event_type="auth_setup",
            object_type="system",
            payload={"ip": _client_ip(request)},
        )
        await session.commit()

        # 2. LLM block — optional. Writes DEFAULT_PURPOSE_CONFIGS as inline
        # `llm_purpose_configs` rows (there are no provider/profile tables
        # left to seed — doc 04 §7) so the user finishes setup with every
        # purpose resolvable, including the two Tier-C purposes (synthesis,
        # verification) T1.05 seeded inert. The user's per-purpose model
        # selections then overlay the matching rows; DEFAULT_PROVIDERS and
        # DEFAULT_PROFILES stay pure-Python lookups used only to fill in a
        # default base_url and a matching params preset for the user's
        # chosen vendor+model, never written to the database themselves.
        #
        # Upsert, not insert: `purpose` is the primary key, and re-running
        # the wizard against an instance whose purpose rows already exist
        # (T1.01 made the wizard re-run the supported upgrade path, doc 20
        # §10) must overlay the same rows rather than fail on a duplicate
        # key. See doc 11 §9.4 / T1.56.
        if body.llm is not None:
            try:
                from app.models.llm_provider import LLMProviderRow
                from app.services.llm_seed import (
                    DEFAULT_PROFILES,
                    DEFAULT_PROVIDER_ROWS,
                    DEFAULT_PURPOSE_CONFIGS,
                    default_provider_row_name_for_purpose,
                    provider_seed_by_kind,
                )

                existing_providers = {
                    r.name: r
                    for r in (await session.execute(select(LLMProviderRow))).scalars().all()
                }
                for ps in DEFAULT_PROVIDER_ROWS:
                    prow = existing_providers.get(ps.name)
                    if prow is None:
                        prow = LLMProviderRow(name=ps.name)
                        session.add(prow)
                        existing_providers[ps.name] = prow
                    prow.api_kind = ps.api_kind
                    prow.base_url = ps.base_url
                    prow.api_key = ps.api_key
                await session.flush()

                existing_rows = (
                    await session.execute(select(LLMPurposeConfigRow))
                ).scalars().all()
                purpose_rows: dict[str, LLMPurposeConfigRow] = {
                    r.purpose: r for r in existing_rows
                }
                for pc in DEFAULT_PURPOSE_CONFIGS:
                    row = purpose_rows.get(pc.purpose)
                    if row is None:
                        row = LLMPurposeConfigRow(purpose=pc.purpose)
                        session.add(row)
                        purpose_rows[pc.purpose] = row
                    row.model = pc.model
                    row.dimensions = pc.dimensions
                    row.reasoning = pc.reasoning
                    row.provider_name = default_provider_row_name_for_purpose(pc.purpose)
                    row.params = dict(pc.params)
                await session.flush()

                user_provider_seed = provider_seed_by_kind(body.llm.api_kind)
                user_base_url = body.llm.base_url or (
                    user_provider_seed.base_url if user_provider_seed else ""
                )

                user_provider_name = f"user-{body.llm.api_kind}"
                uprow = existing_providers.get(user_provider_name)
                if uprow is None:
                    uprow = LLMProviderRow(name=user_provider_name)
                    session.add(uprow)
                    existing_providers[user_provider_name] = uprow
                uprow.api_kind = body.llm.api_kind
                uprow.base_url = user_base_url
                uprow.api_key = body.llm.api_key
                await session.flush()

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

                    pcfg = purpose_rows.get(purpose_key)
                    if pcfg is None:
                        # Should not happen for the six canonical
                        # purposes; create the row defensively.
                        pcfg = LLMPurposeConfigRow(purpose=purpose_key, model="")
                        session.add(pcfg)
                    pcfg.model = spec.model
                    pcfg.dimensions = spec.dimensions if is_embedding else None
                    pcfg.reasoning = False if is_embedding else spec.reasoning
                    pcfg.provider_name = user_provider_name
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
        await record_event(
            session,
            event_type="setup_complete",
            object_type="system",
            payload={
                "ip": _client_ip(request),
                "llm": llm_status.ok,
                "llm_skipped": body.llm is None,
                "repos": repos_status.ok,
                "repos_skipped": body.repos is None,
                "repos_added": repos_added,
                "repos_failed_count": len(repos_failed),
            },
        )
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
