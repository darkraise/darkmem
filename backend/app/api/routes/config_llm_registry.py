from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.routes.config import _replace_orchestrator
from app.database import get_session
from app.models.llm_config import LLMProvider, LLMProfile, LLMPurposeConfigRow, MLProfile
from app.schemas.config import (
    LLMProfileSchema,
    LLMProfilesResponse,
    LLMProfilesUpdate,
    LLMProviderModelsResponse,
    LLMProviderProfileSchema,
    LLMProviderTestRequest,
    LLMProviderTestResponse,
    LLMProvidersResponse,
    LLMProvidersUpdate,
    MLProfileSchema,
    MLProfilesResponse,
    MLProfilesUpdate,
)
from app.services.config import (
    get_llm_providers as fetch_llm_providers,
)
from app.services.config import get_llm_config as fetch_llm_config

router = APIRouter(prefix="/api/v1/config", tags=["config"])


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
    if name != name.strip():
        raise HTTPException(
            status_code=422,
            detail=f"{kind} name must not have leading or trailing whitespace: {name!r}",
        )
    if not name:
        raise HTTPException(
            status_code=422,
            detail=f"{kind} name must be non-empty",
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
        # Anthropic uses x-api-key + anthropic-version, not bearer.
        # Everyone else (OpenAI, DeepSeek, z.ai, Google's OpenAI-compat
        # endpoint) accepts bearer.
        if profile.api_kind == "anthropic":
            headers["x-api-key"] = profile.api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
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
        purpose=row.purpose,
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
            purpose=row.purpose,
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
        if prof.purpose is not None:
            row.purpose = prof.purpose or None
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


# ── ML profiles ─────────────────────────────────────────────────────


def _ml_profile_to_schema(row: MLProfile) -> MLProfileSchema:
    return MLProfileSchema(model_repo=row.model_repo, ttl_seconds=row.ttl_seconds)


@router.get("/ml-profiles", response_model=MLProfilesResponse)
async def get_ml_profiles_route(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(select(MLProfile))).scalars().all()
    return MLProfilesResponse(
        profiles={r.name: _ml_profile_to_schema(r) for r in rows},
    )


@router.put("/ml-profiles", response_model=MLProfilesResponse)
async def update_ml_profiles_route(
    body: MLProfilesUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Upsert the posted ML profiles. Profiles in the table that are
    NOT in the request body are left alone — same semantics as the
    LLM profiles endpoint. Use DELETE /ml-profiles/{name} to remove."""
    for name in body.profiles:
        _validate_name(name, kind="ml-profile")
        ttl = body.profiles[name].ttl_seconds
        if ttl < 0:
            raise HTTPException(
                status_code=422,
                detail=f"ml-profile {name!r}: ttl_seconds must be >= 0 (0 means no eviction)",
            )

    existing_rows = (await session.execute(select(MLProfile))).scalars().all()
    existing_by_name = {r.name: r for r in existing_rows}
    for name, prof in body.profiles.items():
        row = existing_by_name.get(name)
        if row is None:
            row = MLProfile(
                name=name,
                model_repo=prof.model_repo,
                ttl_seconds=prof.ttl_seconds,
            )
            session.add(row)
        else:
            row.model_repo = prof.model_repo
            row.ttl_seconds = prof.ttl_seconds
            row.updated_at = datetime.now(timezone.utc)
    await session.flush()

    rows = (await session.execute(select(MLProfile))).scalars().all()
    return MLProfilesResponse(
        profiles={r.name: _ml_profile_to_schema(r) for r in rows},
    )


@router.delete("/ml-profiles/{name}", response_model=MLProfilesResponse)
async def delete_ml_profile_route(
    name: str,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(MLProfile).where(MLProfile.name == name)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"ml-profile {name!r} not found")
    await session.delete(row)
    await session.flush()
    rows = (await session.execute(select(MLProfile))).scalars().all()
    return MLProfilesResponse(
        profiles={r.name: _ml_profile_to_schema(r) for r in rows},
    )
