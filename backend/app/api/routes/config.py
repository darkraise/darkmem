import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.config import FEATURE_FLAGS_DEFAULTS
from app.database import get_session
from app.models.config import Config
from app.models.llm_config import LLMProvider, LLMProfile, LLMPurposeConfigRow
from app.schemas.config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMConfigUpdateResponse,
    LLMProfileSchema,
    LLMProfilesResponse,
    LLMProfilesUpdate,
    LLMProviderModelsResponse,
    LLMProviderProfileSchema,
    LLMProviderTestRequest,
    LLMProviderTestResponse,
    LLMProvidersResponse,
    LLMProvidersUpdate,
)
from app.services.config import (
    PURPOSES,
    cfg_to_schema,
    get_llm_profiles as fetch_llm_profiles,
    get_llm_providers as fetch_llm_providers,
)
from app.services.config import get_llm_config as fetch_llm_config
from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict

router = APIRouter(prefix="/api/v1/config", tags=["config"])

logger = logging.getLogger(__name__)


def _swap_pipeline_llm(pipeline, new_llm) -> None:
    """Replace every LLM reference the pipeline holds.

    The ``ExtractionService`` / ``ClassificationService`` instances pin
    their own copy via ``self.llm = llm`` at construction time, so a bare
    ``pipeline.llm = new_llm`` would leave the call sites firing against
    the stale orchestrator (e.g. still OpenAI after the user pointed
    extraction at Ollama).
    """
    pipeline.llm = new_llm
    extraction_svc = getattr(pipeline, "extraction", None)
    if extraction_svc is not None:
        extraction_svc.llm = new_llm
    classification_svc = getattr(pipeline, "classification", None)
    if classification_svc is not None:
        classification_svc.llm = new_llm


async def _close_orchestrator_safely(old_llm) -> None:
    """Close the previous orchestrator's httpx client without raising.

    Runs as a background task so any concurrent request that still holds
    a reference to ``old_llm`` finishes before its connection pool is
    torn down. Swallows close-time exceptions to a warning — the new
    orchestrator is already live so a failed close is just a leaked
    socket, not a user-visible error.
    """
    try:
        await old_llm.close()
    except Exception:
        logger.warning("Failed to close replaced LLM orchestrator", exc_info=True)


def _replace_orchestrator(request: Request, new_llm) -> None:
    """Atomically install ``new_llm`` as the active orchestrator.

    Updates ``app.state.llm``, swaps every reference inside the
    pipeline, and schedules the previous orchestrator's client to be
    closed as a background task so its keep-alive connections don't
    leak. Without this teardown, every Save on the LLM Providers page
    leaked an ``httpx.AsyncClient``; under load that produced sporadic
    Bad Gateway responses on the *first* save (stale pool) followed by
    a clean second save (fresh pool warmed up).
    """
    old_llm = getattr(request.app.state, "llm", None)
    request.app.state.llm = new_llm
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is not None:
        _swap_pipeline_llm(pipeline, new_llm)
    if old_llm is not None and old_llm is not new_llm:
        asyncio.create_task(_close_orchestrator_safely(old_llm))


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    config = await fetch_llm_config(session)
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in config.items()})


@router.post("/llm", response_model=LLMConfigUpdateResponse)
async def update_llm_config(
    body: LLMConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.llm import LLMOrchestrator

    # Serialise concurrent config swaps so two admins saving at once can't
    # leave ``app.state.llm`` and ``app.state.pipeline`` wired to different
    # orchestrators.
    async with request.app.state.llm_config_lock:
        update_data = body.model_dump(exclude_unset=True)

        # Look up provider/profile name → id once for the whole request.
        prov_rows = (await session.execute(select(LLMProvider))).scalars().all()
        provider_id_by_name = {row.name: row.id for row in prov_rows}
        prof_rows = (await session.execute(select(LLMProfile))).scalars().all()
        profile_id_by_name = {row.name: row.id for row in prof_rows}

        for purpose in PURPOSES:
            if purpose not in update_data or update_data[purpose] is None:
                continue
            incoming = {k: v for k, v in update_data[purpose].items() if v is not None}
            # Sentinel: "***" means "don't rotate the stored API key".
            if incoming.get("api_key") == "***":
                incoming.pop("api_key")

            row = (await session.execute(
                select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == purpose)
            )).scalar_one_or_none()
            if row is None:
                row = LLMPurposeConfigRow(purpose=purpose, model="")
                session.add(row)

            # Map name-based fields onto the FK columns. Empty string means
            # "clear the link" (matches the API contract used by the UI).
            if "provider_ref" in incoming:
                ref = incoming.pop("provider_ref") or None
                if ref and ref not in provider_id_by_name:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown provider {ref!r}",
                    )
                row.provider_id = provider_id_by_name.get(ref) if ref else None
            if "profile_ref" in incoming:
                ref = incoming.pop("profile_ref") or None
                if ref and ref not in profile_id_by_name:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown profile {ref!r}",
                    )
                row.profile_id = profile_id_by_name.get(ref) if ref else None

            for field in (
                "model", "dimensions", "reasoning", "api_kind",
                "provider", "base_url", "api_key", "params",
            ):
                if field in incoming:
                    setattr(row, field, incoming[field])
            row.updated_at = datetime.now(timezone.utc)

        await session.flush()

        # Re-resolve through ``fetch_llm_config`` so profile-referenced
        # purposes get their connection fields overlaid before the
        # orchestrator goes live. ``new_value`` itself stays unresolved on
        # disk by design — the overlay is applied at read time.
        updated_config = await fetch_llm_config(session)
        new_llm = LLMOrchestrator(updated_config)
        _replace_orchestrator(request, new_llm)

        # Resolve the dimensions of the new embedder before updating the
        # fingerprint. Prefer the explicit user value; otherwise probe the
        # model; otherwise leave it unset and let the next embed call
        # populate the registry on demand.
        new_embedding_dims: int | None = updated_config["embedding"].dimensions
        if new_embedding_dims is None:
            try:
                probe, _ = await new_llm.embed("dimension probe")
                new_embedding_dims = len(probe)
            except Exception as exc:
                logger.warning("Could not probe new embedder dimensions: %s", exc)

        pipeline = getattr(request.app.state, "pipeline", None)

        obsolete_after_change = None
        if pipeline is not None and new_embedding_dims:
            from app.services.reembed import ReembedService
            reembed_svc = ReembedService(session)
            new_fp = f"{updated_config['embedding'].model}|{new_embedding_dims}"
            obsolete_after_change = await reembed_svc.count_missing(new_fp)

    purpose_payload = {p: cfg_to_schema(c) for p, c in updated_config.items()}
    return LLMConfigUpdateResponse(
        **purpose_payload,
        obsolete_after_change=obsolete_after_change,
    )


# ── LLM Providers (table-backed) ─────────────────────────────────────


def _provider_to_schema(row: LLMProvider) -> LLMProviderProfileSchema:
    """Mask the api_key as ``"***"`` when set so the UI can show
    "configured" without exposing the secret."""
    return LLMProviderProfileSchema(
        provider=row.provider,
        base_url=row.base_url,
        api_key="***" if row.api_key else None,
        api_kind=row.api_kind,
        supports_embedding=row.supports_embedding,
    )


def _validate_name(name: str, *, kind: str) -> None:
    cleaned = name.strip()
    if not cleaned or cleaned != name:
        raise HTTPException(
            status_code=422,
            detail=f"{kind} name must be non-empty and untrimmed-equal: {name!r}",
        )
    if "/" in name or len(name) > 64:
        raise HTTPException(
            status_code=422,
            detail=f"{kind} name {name!r} must omit '/' and stay under 64 chars",
        )


@router.get("/llm-providers", response_model=LLMProvidersResponse)
async def get_llm_providers_route(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(select(LLMProvider))).scalars().all()
    return LLMProvidersResponse(
        profiles={row.name: _provider_to_schema(row) for row in rows},
    )


@router.put("/llm-providers", response_model=LLMProvidersResponse)
async def update_llm_providers_route(
    body: LLMProvidersUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Replace / upsert the provider table from the posted set.

    Honours the ``"***"`` masking sentinel on ``api_key``: posting it
    back keeps the stored secret. Empty string clears it. Any other
    value rotates it (and stamps ``api_key_rotated_at``).

    Any provider currently in the table that's NOT in the request body
    is left alone — this matches the JSONB-era behaviour where PUT
    didn't delete absent rows. Use the DELETE endpoint to remove a
    specific provider.
    """
    from app.services.llm import LLMOrchestrator  # noqa: PLC0415

    for name in body.profiles:
        _validate_name(name, kind="provider")

    async with request.app.state.llm_config_lock:
        existing_rows = (await session.execute(select(LLMProvider))).scalars().all()
        existing_by_name = {r.name: r for r in existing_rows}

        for name, incoming in body.profiles.items():
            data = incoming.model_dump()
            row = existing_by_name.get(name)
            if row is None:
                row = LLMProvider(name=name)
                session.add(row)
            row.provider = data["provider"]
            row.base_url = data["base_url"]
            row.api_kind = data["api_kind"]
            row.supports_embedding = data["supports_embedding"]
            new_key = data.get("api_key")
            if new_key == "***":
                pass  # keep existing
            elif new_key != row.api_key:
                row.api_key = new_key or None
                row.api_key_rotated_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
        await session.flush()

        # Rebuild the live orchestrator so any purpose referencing these
        # providers starts using the new connection details on the next
        # call. ``_replace_orchestrator`` schedules the previous client
        # to close as a background task to avoid leaking httpx pools.
        new_config = await fetch_llm_config(session)
        new_llm = LLMOrchestrator(new_config)
        _replace_orchestrator(request, new_llm)

    rows = (await session.execute(select(LLMProvider))).scalars().all()
    return LLMProvidersResponse(
        profiles={row.name: _provider_to_schema(row) for row in rows},
    )


@router.delete("/llm-providers/{name}", response_model=LLMProvidersResponse)
async def delete_llm_provider_route(
    name: str,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Remove a provider. The FK from ``llm_profiles.provider_id``
    refuses the delete (RESTRICT) when any profile still points at it,
    surfacing as a 409. Purposes link with ``ON DELETE SET NULL`` so
    they survive the deletion (provider_ref becomes None).
    """
    from app.services.llm import LLMOrchestrator  # noqa: PLC0415

    async with request.app.state.llm_config_lock:
        row = (await session.execute(
            select(LLMProvider).where(LLMProvider.name == name)
        )).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail=f"provider {name!r} not found")

        # Pre-flight: block delete when any profile or purpose still
        # references this provider. The FK on llm_profiles.provider_id
        # is RESTRICT so it would also fail in the DB, but we want the
        # combined error message naming both kinds of dependents in one
        # 409 response so the user knows everything they need to fix.
        referencing_profiles = (await session.execute(
            select(LLMProfile.name).where(LLMProfile.provider_id == row.id)
        )).scalars().all()
        referencing_purposes = (await session.execute(
            select(LLMPurposeConfigRow.purpose).where(
                LLMPurposeConfigRow.provider_id == row.id
            )
        )).scalars().all()
        if referencing_profiles or referencing_purposes:
            parts = []
            if referencing_purposes:
                parts.append(f"purposes: {', '.join(sorted(referencing_purposes))}")
            if referencing_profiles:
                parts.append(f"profiles: {', '.join(sorted(referencing_profiles))}")
            raise HTTPException(
                status_code=409,
                detail=(
                    f"provider {name!r} is still referenced by "
                    f"{'; '.join(parts)}. Update those first."
                ),
            )

        await session.delete(row)
        await session.flush()

        new_config = await fetch_llm_config(session)
        new_llm = LLMOrchestrator(new_config)
        _replace_orchestrator(request, new_llm)

    rows = (await session.execute(select(LLMProvider))).scalars().all()
    return LLMProvidersResponse(
        profiles={r.name: _provider_to_schema(r) for r in rows},
    )


# Sensible default models per api_kind for the connectivity probe — chosen
# for cheapness and broad availability on each vendor's free / cheapest tier.
# The user can override via the request body.
_DEFAULT_TEST_MODELS: dict[str, dict[str, str]] = {
    "openai":    {"chat": "gpt-4o-mini",       "embedding": "text-embedding-3-small"},
    "ollama":    {"chat": "qwen2.5:3b",        "embedding": "nomic-embed-text"},
    "anthropic": {"chat": "claude-haiku-4-5",  "embedding": ""},
    "google":    {"chat": "gemini-2.0-flash",  "embedding": "text-embedding-004"},
    "deepseek":  {"chat": "deepseek-chat",     "embedding": ""},
    "zai":       {"chat": "glm-4.5-flash",     "embedding": "embedding-2"},
}


def _ollama_native_root(base_url: str) -> str:
    """Strip ``/v1`` or ``/api`` so we can append the native Ollama path."""
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base[:-3]
    if base.endswith("/api"):
        return base[:-4]
    return base


@router.post("/llm-providers/{name}/test", response_model=LLMProviderTestResponse)
async def test_llm_provider_route(
    name: str,
    body: LLMProviderTestRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Run a tiny chat or embedding call against the profile's base URL.

    The probe builds the request URL the same way the live LLM client
    would (native Ollama path for ``api_kind="ollama"``, OpenAI-compat
    path for everything else), so a 200 here means the saved
    ``base_url`` + ``api_key`` + ``api_kind`` combination is reachable
    and authenticated. The probe never touches the live orchestrator.
    """
    import time  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    profiles = await fetch_llm_providers(session)
    if name not in profiles:
        raise HTTPException(status_code=404, detail=f"profile {name!r} not found")
    profile = profiles[name]

    if body.mode == "embedding" and not profile.supports_embedding:
        raise HTTPException(
            status_code=409,
            detail=(
                f"profile {name!r} is marked supports_embedding=false; "
                "the vendor does not expose an embeddings endpoint."
            ),
        )

    # Cloud providers always need a bearer token. Save the round trip
    # and give the operator a pointer to fix it.
    if profile.api_kind != "ollama" and not profile.api_key:
        raise HTTPException(
            status_code=409,
            detail=(
                f"API key not set for Provider {name!r}. Open "
                "Settings → LLM Providers, click into the row, "
                "paste your API key, and Save."
            ),
        )

    model = body.model or _DEFAULT_TEST_MODELS.get(profile.api_kind, {}).get(body.mode, "")
    if not model:
        raise HTTPException(
            status_code=422,
            detail=(
                f"no default {body.mode} model is known for api_kind={profile.api_kind!r}; "
                "supply a `model` in the request body."
            ),
        )

    headers = {"Content-Type": "application/json"}
    if profile.api_key:
        headers["Authorization"] = f"Bearer {profile.api_key}"

    if profile.api_kind == "ollama":
        root = _ollama_native_root(profile.base_url)
        if body.mode == "embedding":
            url = f"{root}/api/embed"
            payload = {"model": model, "input": "ping"}
        else:
            url = f"{root}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "stream": False,
                "think": False,
                "options": {"num_predict": 4},
            }
    else:
        base = profile.base_url.rstrip("/")
        if body.mode == "embedding":
            url = f"{base}/embeddings"
            payload = {"model": model, "input": "ping"}
        else:
            url = f"{base}/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 4,
            }

    t0 = time.monotonic()
    status_code: int | None = None
    ok = False
    message = ""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
        status_code = resp.status_code
        ok = resp.is_success
        if ok:
            message = "OK"
        else:
            # Trim response body so we don't echo a 50 KB HTML error page
            # back at the UI.
            message = resp.text[:300] if resp.text else f"HTTP {status_code}"
    except httpx.HTTPError as exc:
        message = f"network error: {exc}"
    except Exception as exc:  # pragma: no cover — belt & suspenders
        message = f"unexpected error: {exc}"
    latency_ms = int((time.monotonic() - t0) * 1000)

    return LLMProviderTestResponse(
        ok=ok,
        status_code=status_code,
        latency_ms=latency_ms,
        url=url,
        message=message,
    )


# ── LLM Provider models-fetch ────────────────────────────────────────


@router.get("/llm-providers/{name}/models", response_model=LLMProviderModelsResponse)
async def list_llm_provider_models_route(
    name: str,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Fetch the list of models the configured Provider exposes.

    Used by the UI to populate a model dropdown after the user picks a
    Provider when creating a Profile or running a test. Routes to
    ``GET {base_url}/models`` for the OpenAI-compat surface (works with
    OpenAI itself, vLLM, LM Studio, Ollama's compat layer) and
    ``GET {root}/api/tags`` for native Ollama. Vendor-specific kinds
    (Anthropic, Google, DeepSeek, z.ai) currently dispatch through the
    OpenAI-compat path; the model list is whatever each vendor's
    compat shim exposes.
    """
    import time  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    profiles = await fetch_llm_providers(session)
    if name not in profiles:
        raise HTTPException(status_code=404, detail=f"profile {name!r} not found")
    profile = profiles[name]

    headers = {"Accept": "application/json"}

    if profile.api_kind == "ollama":
        root = profile.base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        elif root.endswith("/api"):
            root = root[:-4]
        url = f"{root}/api/tags"
        kind_label = "ollama_native:/api/tags"
    else:
        # Every cloud Provider's /v1/models endpoint requires auth, but
        # the auth scheme varies. Short-circuit with a UX-friendly error
        # rather than passing through the vendor's generic auth message.
        if not profile.api_key:
            return LLMProviderModelsResponse(
                models=[],
                fetched_via="openai_compat:/v1/models",
                error=(
                    f"API key not set for Provider {name!r}. Open "
                    "Settings → LLM Providers, click into the row, "
                    "paste your API key, and Save."
                ),
            )
        # Anthropic uses x-api-key + anthropic-version, not bearer.
        # Everyone else (OpenAI, DeepSeek, z.ai, Google's OpenAI-compat
        # endpoint at /v1beta/openai) accepts bearer.
        if profile.api_kind == "anthropic":
            headers["x-api-key"] = profile.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {profile.api_key}"
        url = f"{profile.base_url.rstrip('/')}/models"
        kind_label = "openai_compat:/v1/models"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
        if not resp.is_success:
            return LLMProviderModelsResponse(
                models=[], fetched_via=kind_label,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
    except httpx.HTTPError as exc:
        return LLMProviderModelsResponse(
            models=[], fetched_via=kind_label, error=f"network error: {exc}",
        )

    # Normalise across the two response shapes.
    # OpenAI-compat: ``{"data": [{"id": "model-id", ...}, ...]}``
    # Ollama native: ``{"models": [{"name": "model-id", ...}, ...]}``
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
    models = sorted(set(models))

    return LLMProviderModelsResponse(models=models, fetched_via=kind_label)


# ── LLM Profile profiles ─────────────────────────────────────────────


async def _profile_to_schema(row: LLMProfile, provider_name: str) -> LLMProfileSchema:
    return LLMProfileSchema(
        provider_ref=provider_name,
        model=row.model,
        params=row.params or {},
        is_embedding=row.is_embedding,
        reasoning=row.reasoning,
    )


async def _list_profiles_with_provider(session: AsyncSession) -> dict[str, LLMProfileSchema]:
    stmt = (
        select(LLMProfile, LLMProvider.name.label("provider_name"))
        .join(LLMProvider, LLMProfile.provider_id == LLMProvider.id)
    )
    rows = (await session.execute(stmt)).all()
    return {
        row.name: LLMProfileSchema(
            provider_ref=prov_name,
            model=row.model,
            params=row.params or {},
            is_embedding=row.is_embedding,
            reasoning=row.reasoning,
        )
        for row, prov_name in rows
    }


@router.get("/llm-profiles", response_model=LLMProfilesResponse)
async def get_llm_profiles_route(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return LLMProfilesResponse(profiles=await _list_profiles_with_provider(session))


@router.put("/llm-profiles", response_model=LLMProfilesResponse)
async def update_llm_profiles_route(
    body: LLMProfilesUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Upsert the posted profiles into the ``llm_profiles`` table.

    Validates that every ``provider_ref`` resolves to a real provider
    (FK enforcement makes this a hard requirement at the SQL layer too,
    we surface it as a clean 422 here). Profiles that exist in the DB
    but are NOT in the request body are left alone — same semantics as
    the providers PUT.
    """
    providers = (await session.execute(select(LLMProvider))).scalars().all()
    provider_by_name = {p.name: p for p in providers}

    for prof_name, prof in body.profiles.items():
        _validate_name(prof_name, kind="profile")
        if prof.provider_ref not in provider_by_name:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"profile {prof_name!r} references Provider {prof.provider_ref!r} "
                    "which does not exist; create the Provider first"
                ),
            )
        if prof.is_embedding and not provider_by_name[prof.provider_ref].supports_embedding:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"profile {prof_name!r} is_embedding=True but provider "
                    f"{prof.provider_ref!r} has supports_embedding=False"
                ),
            )

    existing_rows = (await session.execute(select(LLMProfile))).scalars().all()
    existing_by_name = {r.name: r for r in existing_rows}

    for prof_name, prof in body.profiles.items():
        provider_id = provider_by_name[prof.provider_ref].id
        row = existing_by_name.get(prof_name)
        if row is None:
            row = LLMProfile(name=prof_name, provider_id=provider_id, model=prof.model)
            session.add(row)
        row.provider_id = provider_id
        row.model = prof.model
        row.params = prof.params or {}
        row.is_embedding = prof.is_embedding
        row.reasoning = prof.reasoning if not prof.is_embedding else False
        row.updated_at = datetime.now(timezone.utc)
    await session.flush()

    return LLMProfilesResponse(profiles=await _list_profiles_with_provider(session))


@router.delete("/llm-profiles/{name}", response_model=LLMProfilesResponse)
async def delete_llm_profile_route(
    name: str,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(LLMProfile).where(LLMProfile.name == name)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"profile {name!r} not found")
    await session.delete(row)
    await session.flush()
    return LLMProfilesResponse(profiles=await _list_profiles_with_provider(session))


class FeatureFlagsResponse(BaseModel):
    llm_enrichment_enabled: bool
    hybrid_search_enabled: bool
    reranker_enabled: bool
    pipeline_concurrency: int
    classification_areas: list[str]
    classification_mode: str
    embedding_batch_size: int
    embedding_concurrency: int
    entity_cache_ttl_minutes: int
    relation_rescue: bool = True
    confidence_rank_gamma: float = 0.0


class FeatureFlagsUpdate(BaseModel):
    llm_enrichment_enabled: bool | None = None
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = Field(default=None, ge=1, le=20)
    classification_areas: list[str] | None = None
    classification_mode: Literal["simple", "expanded"] | None = None
    embedding_batch_size: int | None = Field(default=None, ge=1, le=200)
    embedding_concurrency: int | None = Field(default=None, ge=1, le=10)
    entity_cache_ttl_minutes: int | None = Field(default=None, ge=1, le=1440)
    relation_rescue: bool | None = None
    confidence_rank_gamma: float | None = Field(default=None, ge=0, le=5)


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    flags = await get_feature_flags_dict(session)
    return FeatureFlagsResponse(**flags)


@router.put("/feature-flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    body: FeatureFlagsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    current = await get_feature_flags_dict(session)
    updates = body.model_dump(exclude_unset=True)

    if "classification_areas" in updates:
        from app.services.classification_areas import AREAS
        invalid = [a for a in updates["classification_areas"] if a not in AREAS]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Unknown classification areas: {invalid}")
        # `general` is the always-on fallback — enforce it server-side so
        # classification can never be left without at least the base area.
        if "general" not in updates["classification_areas"]:
            updates["classification_areas"] = ["general", *updates["classification_areas"]]

    current.update(updates)

    # Drop any keys that aren't part of the current schema so deprecated flags
    # don't linger in the DB row forever.
    stored = {k: current[k] for k in FEATURE_FLAGS_DEFAULTS if k in current}

    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if config:
        config.value = stored
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=stored))
    await session.flush()

    return FeatureFlagsResponse(**stored)


@router.get("/classification-areas")
async def list_classification_areas(
    _user=Depends(require_auth),
):
    from app.services.classification_areas import AREAS
    return [
        {
            "key": area.key,
            "display_name": area.display_name,
            "types": list(area.llm_types.keys()),
            "type_descriptions": area.llm_types,
        }
        for area in AREAS.values()
    ]


class EnrichmentConfigUpdate(BaseModel):
    enabled: bool = False
    batch_size: int = Field(default=5, ge=1, le=100)
    interval_seconds: int = Field(default=10, ge=1, le=3600)


@router.get("/enrichment")
async def get_enrichment_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    if not config:
        return {"enabled": False, "batch_size": 5, "interval_seconds": 10}
    return config.value


@router.put("/enrichment")
async def update_enrichment_config(
    body: EnrichmentConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == "enrichment_config"))
    config = result.scalar_one_or_none()
    new_value = body.model_dump()
    if config:
        config.value = new_value
    else:
        session.add(Config(key="enrichment_config", value=new_value))
    await session.flush()

    worker = getattr(request.app.state, "enrichment_worker", None)
    if worker:
        worker.batch_size = body.batch_size
        worker.interval = body.interval_seconds

        if body.enabled and not worker._running:
            old_task = getattr(request.app.state, "enrichment_task", None)
            if old_task and not old_task.done():
                worker.stop()
                old_task.cancel()
                # Wait for the cancelled loop to actually exit before we start
                # a new one so we never have two run_loops racing on the same
                # worker state.
                try:
                    await old_task
                except (asyncio.CancelledError, Exception):
                    pass
            worker._running = False

            task = asyncio.create_task(worker.run_loop())
            request.app.state.enrichment_task = task
        elif not body.enabled and worker._running:
            worker.stop()

    return new_value


# ── System prompts (UI-editable) ─────────────────────────────────────


class SystemPromptsResponse(BaseModel):
    defaults: dict[str, str]
    overrides: dict[str, str]
    effective: dict[str, str]


class SystemPromptsUpdate(BaseModel):
    """Partial update. Keys map to the prompt body.

    - A non-empty string installs / replaces the override for that purpose.
    - An empty string clears the override (falls back to the in-code default).
    - Omitted keys are left unchanged.
    """

    overrides: dict[str, str] = Field(default_factory=dict)


@router.get("/system-prompts", response_model=SystemPromptsResponse)
async def get_system_prompts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    await _prompt_mod.refresh_from_db(session)
    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


@router.put("/system-prompts", response_model=SystemPromptsResponse)
async def update_system_prompts(
    body: SystemPromptsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    row = (
        await session.execute(select(Config).where(Config.key == _prompt_mod.SYSTEM_PROMPTS_KEY))
    ).scalar_one_or_none()
    stored: dict[str, str] = {}
    if row and isinstance(row.value, dict):
        for k, v in row.value.items():
            if isinstance(k, str) and isinstance(v, str):
                stored[k] = v

    for key, value in body.overrides.items():
        if not isinstance(key, str) or key not in _prompt_mod.PROMPTS:
            raise HTTPException(status_code=422, detail=f"Unknown prompt purpose: {key!r}")
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"Prompt for {key!r} must be a string")
        if value == "":
            stored.pop(key, None)
        else:
            # Guard against silently storing 500KB blobs that would blow up
            # the system prompt budget on small-context models.
            if len(value) > 20_000:
                raise HTTPException(
                    status_code=422,
                    detail=f"Prompt for {key!r} exceeds 20,000 characters",
                )
            stored[key] = value

    if row:
        row.value = stored
    else:
        session.add(Config(key=_prompt_mod.SYSTEM_PROMPTS_KEY, value=stored))
    await session.flush()

    await _prompt_mod.refresh_from_db(session)

    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


@router.post("/enrichment/trigger")
async def trigger_enrichment(
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.enrichment_worker import EnrichmentWorker

    llm = getattr(request.app.state, "llm", None)
    if not llm:
        raise HTTPException(status_code=503, detail="LLM not available")

    # Honour the user's persisted batch_size so "Run Now" matches the Save
    # semantics. Fall back to the schema default when the row is missing.
    row = (
        await session.execute(select(Config).where(Config.key == "enrichment_config"))
    ).scalar_one_or_none()
    stored = row.value if row and isinstance(row.value, dict) else {}
    try:
        size = int(stored.get("batch_size", EnrichmentConfigUpdate().batch_size))
    except (TypeError, ValueError):
        size = EnrichmentConfigUpdate().batch_size
    size = max(1, min(100, size))

    worker = EnrichmentWorker(llm)
    count = await worker.process_batch(batch_size=size)

    return {"processed": count, "batch_size": size}
