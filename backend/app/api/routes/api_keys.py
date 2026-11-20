"""Key management — the single door to a credential (doc 18 §5, T4.01).

Provides:
  - POST   /api/v1/api-keys        issue, returning the plaintext once
  - GET    /api/v1/api-keys        list, never returning a secret
  - DELETE /api/v1/api-keys/{id}   revoke in place

**Authenticated by the session, never by a key scope**, for the reason
`ratification.py` gives about its own route: doc 18 §5 calls a credential mint
confirmed-grade power. Every handler here declares ``require_auth``, so a key
can never mint, list or revoke a key — including a key holding ``admin``. That
is why ``admin`` is not the scope of this surface: it is the scope of config,
jobs and repos, and this surface is behind the human door instead.

Revocation is ``DELETE`` returning 204 per the REST conventions, but it sets
``revoked_at`` rather than removing the row: `events.api_key_id` has no foreign
key, so a deleted row would orphan the history of every call the key made.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.models.api_key import ApiKey
from app.schemas.api_keys import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from app.services.api_key_scopes import ScopeRejected
from app.services.api_keys import issue_key, revoke_key

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreated)
async def create_api_key(
    body: ApiKeyCreate,
    user=Depends(require_auth),
    session: AsyncSession = SessionDep,
) -> ApiKeyCreated:
    try:
        row, token = await issue_key(
            session,
            name=body.name,
            scopes=body.scopes,
            expires_at=body.expires_at,
            actor=user.sub,
        )
    except ScopeRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    await session.commit()
    return ApiKeyCreated(
        id=row.id,
        name=row.name,
        key_id=row.key_id,
        scopes=list(row.scopes),
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        token=token,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
) -> list[ApiKeyResponse]:
    rows = (
        await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    ).scalars().all()
    return [
        ApiKeyResponse(
            id=row.id,
            name=row.name,
            key_id=row.key_id,
            scopes=list(row.scopes) if isinstance(row.scopes, list) else [],
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
        )
        for row in rows
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    user=Depends(require_auth),
    session: AsyncSession = SessionDep,
) -> None:
    if not await revoke_key(session, key_id, actor=user.sub):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key not found"
        )
    await session.commit()
