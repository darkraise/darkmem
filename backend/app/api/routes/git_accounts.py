"""Git forge account CRUD.

One row per credential, selected by name from every repo that uses it, so a
token rotation is one edit rather than one per repo. Tokens are write-only over
the wire: a response carries ``token_hint`` and nothing more.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.git_account import (
    GitAccountCreate,
    GitAccountListResponse,
    GitAccountOut,
    GitAccountUpdate,
    GitAccountVerifyRequest,
    GitAccountVerifyResponse,
)
from app.services.git_accounts import (
    GitAccountError,
    GitAccountInUse,
    GitAccountService,
    verify_token,
)

router = APIRouter(prefix="/api/v1/git-accounts", tags=["git-accounts"])


def _raise(exc: GitAccountError) -> None:
    # GitAccountInUse carries a repo list, and the app's error envelope keeps
    # `details` only from a dedicated handler — an HTTPException whose detail is
    # a dict is flattened to "Request failed". main.py registers that handler.
    if isinstance(exc, GitAccountInUse):
        raise exc
    raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("", response_model=GitAccountListResponse)
async def list_git_accounts(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_auth),
) -> GitAccountListResponse:
    return GitAccountListResponse(accounts=await GitAccountService(session).list())


@router.post("/verify", response_model=GitAccountVerifyResponse)
async def verify_git_token(
    data: GitAccountVerifyRequest,
    _: dict = Depends(require_auth),
) -> GitAccountVerifyResponse:
    """Check a token without storing it, so the dialog can confirm before saving."""
    try:
        host, username, scopes = await verify_token(data.token, data.provider, data.host)
    except GitAccountError as exc:
        _raise(exc)
    return GitAccountVerifyResponse(
        username=username, scopes=scopes, host=host, provider=data.provider,
    )


@router.post("", response_model=GitAccountOut, status_code=status.HTTP_201_CREATED)
async def create_git_account(
    data: GitAccountCreate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_auth),
) -> GitAccountOut:
    service = GitAccountService(session)
    try:
        account = await service.create(data)
    except GitAccountError as exc:
        _raise(exc)
    return service.to_out(account)


@router.put("/{account_id}", response_model=GitAccountOut)
async def update_git_account(
    account_id: uuid.UUID,
    data: GitAccountUpdate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_auth),
) -> GitAccountOut:
    service = GitAccountService(session)
    try:
        account = await service.update(account_id, data)
    except GitAccountError as exc:
        _raise(exc)
    if account is None:
        raise HTTPException(status_code=404, detail="Git account not found")
    repos = await service.repos_using(account.id)
    return service.to_out(account, len(repos))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_git_account(
    account_id: uuid.UUID,
    reassign_to: uuid.UUID | None = Query(
        default=None,
        description="Move repos using this account onto this one instead of refusing.",
    ),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_auth),
) -> None:
    try:
        deleted = await GitAccountService(session).delete(account_id, reassign_to)
    except GitAccountError as exc:
        _raise(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Git account not found")
