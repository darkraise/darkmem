"""Provider CRUD and model-probe endpoints.

One row per vendor connection (`llm_providers`), referenced by name from every
purpose that uses it (doc 04 §7 reversed by the 2026-08-20 owner ruling). This
router lets an operator manage a vendor once instead of once per purpose.

Connection writes (POST/PUT/DELETE) all take ``app.state.llm_config_lock`` —
the same lock ``POST /config/llm`` holds — so a purpose write validating a
provider reference and a concurrent provider delete can never race into a
foreign-key violation. PUT additionally installs a fresh orchestrator through
``apply_llm_config_change`` (shared with the purpose route) because a provider
edit changes connection details exactly as a purpose edit does; POST and
DELETE skip that step since a brand-new or now-deleted provider serves no
purpose yet.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.config import LLMApiKind
from app.database import get_session
from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.schemas.config import LLMProviderModelsResponse
from app.services import llm_quirks
from app.services.config import VERIFICATION_PURPOSE
from app.services.llm_provider_guard import (
    assert_identity_fields_unchanged,
    verification_provider,
)
from app.services.model_probe import parse_model_list

from .config import apply_llm_config_change

router = APIRouter(prefix="/api/v1/config/llm-providers", tags=["config"])

MASKED_KEY = "***"


class ProviderOut(BaseModel):
    name: str
    api_kind: LLMApiKind
    base_url: str
    api_key: str | None = None
    used_by: list[str] = Field(default_factory=list)
    serves_verification: bool = False


class ProviderListResponse(BaseModel):
    providers: list[ProviderOut] = Field(default_factory=list)


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    api_kind: LLMApiKind
    base_url: str
    api_key: str | None = None


class ProviderUpdate(BaseModel):
    """Full-replace body, with one deliberate exception on ``api_key``,
    because the server never round-trips the real secret for a form to
    resend:

    - omitted (field absent from the body) — key unchanged.
    - ``"***"`` (the mask ``GET``/``POST`` echo back) — key unchanged.
    - explicit ``null`` — key cleared, matching the purpose route's
      explicit-null-clears convention.
    - any other string — key rotated to that value.
    """

    api_kind: LLMApiKind
    base_url: str
    api_key: str | None = None


class ProviderPutResponse(ProviderOut):
    no_embedding_purposes: list[str] = Field(default_factory=list)


class ProviderProbeDraft(BaseModel):
    api_kind: LLMApiKind
    base_url: str
    api_key: str | None = None


async def _used_by(session: AsyncSession, name: str) -> list[str]:
    rows = (await session.execute(
        select(LLMPurposeConfigRow.purpose)
        .where(LLMPurposeConfigRow.provider_name == name)
    )).scalars().all()
    return list(rows)


def _provider_out(row: LLMProviderRow, used_by: list[str]) -> ProviderOut:
    return ProviderOut(
        name=row.name,
        api_kind=row.api_kind,
        base_url=row.base_url,
        api_key=MASKED_KEY if row.api_key else None,
        used_by=used_by,
        serves_verification=VERIFICATION_PURPOSE in used_by,
    )


async def _probe(api_kind: str, base_url: str, api_key: str | None) -> LLMProviderModelsResponse:
    target = llm_quirks.models_probe(api_kind, base_url, api_key)
    if llm_quirks.quirks_for(api_kind).requires_api_key and not api_key:
        return LLMProviderModelsResponse(
            models=[], fetched_via=target.label,
            error=f"API key required for api_kind={api_kind!r}",
        )
    headers = {"Accept": "application/json", **target.headers}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(target.url, headers=headers)
        if not resp.is_success:
            return LLMProviderModelsResponse(
                models=[], fetched_via=target.label,
                error=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
        data = resp.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        # ``ValueError`` also catches ``resp.json()`` raising
        # ``json.JSONDecodeError`` when a vendor or reverse proxy answers 200
        # with a non-JSON body (HTML, plain text): that is vendor behaviour,
        # not a darkmem failure, so it gets the same 200-with-error shape as
        # every other probe failure rather than escaping as a 500.
        return LLMProviderModelsResponse(
            models=[], fetched_via=target.label, error=f"probe failed: {exc}",
        )
    return LLMProviderModelsResponse(models=parse_model_list(data), fetched_via=target.label)


@router.get("", response_model=ProviderListResponse)
async def list_providers(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(select(LLMProviderRow))).scalars().all()
    by_provider: dict[str, list[str]] = {}
    for purpose, provider_name in await session.execute(
        select(LLMPurposeConfigRow.purpose, LLMPurposeConfigRow.provider_name)
    ):
        by_provider.setdefault(provider_name, []).append(purpose)
    return ProviderListResponse(
        providers=[_provider_out(row, by_provider.get(row.name, [])) for row in rows]
    )


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: ProviderCreate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    async with request.app.state.llm_config_lock:
        existing = (await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == body.name)
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=409, detail=f"provider {body.name!r} already exists",
            )
        row = LLMProviderRow(
            name=body.name, api_kind=body.api_kind,
            base_url=body.base_url, api_key=body.api_key,
        )
        session.add(row)
        await session.flush()
        await session.commit()
    return _provider_out(row, [])


@router.put("/{name}", response_model=ProviderPutResponse)
async def update_provider(
    name: str,
    body: ProviderUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    async with request.app.state.llm_config_lock:
        row = (await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == name)
        )).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail=f"provider {name!r} not found")

        update_data = body.model_dump(exclude_unset=True)
        assert_identity_fields_unchanged(
            name, row, update_data, await verification_provider(session),
        )

        row.api_kind = body.api_kind
        row.base_url = body.base_url
        if "api_key" in update_data and update_data["api_key"] != MASKED_KEY:
            row.api_key = update_data["api_key"]
        row.updated_at = datetime.now(timezone.utc)
        await session.flush()

        used_by = await _used_by(session, name)
        no_embedding_purposes = (
            [p for p in used_by if p == "embedding"]
            if not llm_quirks.quirks_for(row.api_kind).supports_embedding
            else []
        )

        await apply_llm_config_change(request, session)
        await session.commit()

    return ProviderPutResponse(
        name=row.name,
        api_kind=row.api_kind,
        base_url=row.base_url,
        api_key=MASKED_KEY if row.api_key else None,
        used_by=used_by,
        serves_verification=VERIFICATION_PURPOSE in used_by,
        no_embedding_purposes=no_embedding_purposes,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    name: str,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    async with request.app.state.llm_config_lock:
        row = (await session.execute(
            select(LLMProviderRow).where(LLMProviderRow.name == name)
        )).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail=f"provider {name!r} not found")

        used_by = await _used_by(session, name)
        if used_by:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"provider {name!r} is still used by: "
                    f"{', '.join(sorted(used_by))}"
                ),
            )
        await session.delete(row)
        await session.flush()
        await session.commit()


@router.post("/probe-models", response_model=LLMProviderModelsResponse, dependencies=[Depends(refuse_when_read_only)])
async def probe_draft_provider(
    body: ProviderProbeDraft,
    _user=Depends(require_auth),
):
    """Probe connection details that have not been saved as a provider yet."""
    return await _probe(body.api_kind, body.base_url, body.api_key)


@router.post("/{name}/probe-models", response_model=LLMProviderModelsResponse, dependencies=[Depends(refuse_when_read_only)])
async def probe_saved_provider(
    name: str,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(LLMProviderRow).where(LLMProviderRow.name == name)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"provider {name!r} not found")
    return await _probe(row.api_kind, row.base_url, row.api_key)
