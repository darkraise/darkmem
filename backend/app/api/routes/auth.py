from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import (
    TokenPayload,
    clear_auth_cookie,
    create_access_token,
    hash_password,
    require_auth,
    set_auth_cookie,
    verify_password,
)
from app.database import async_session_factory, get_session
from app.models.audit import AuditLog
from app.models.config import Config
from app.models.token_blocklist import TokenBlocklist

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ADMIN_PASSWORD_KEY = "admin_password_hash"
PASSWORD_CHANGED_AT_KEY = "admin_password_changed_at"


async def _record_audit(action: str, details: dict) -> None:
    """Persist an audit row in its own committed session.

    The request-scoped session from ``get_session`` rolls back whenever the
    handler raises (e.g. a failed login raising 401), which silently discards
    audit rows merely flushed into it. Writing through a fresh session commits
    the audit trail independently of the request outcome.
    """
    async with async_session_factory() as audit_session:
        audit_session.add(AuditLog(action=action, details=details))
        await audit_session.commit()


class PasswordRequest(BaseModel):
    password: str = Field(max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def auth_login(
    body: PasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not verify_password(body.password, config.value["hash"]):
        await _record_audit("auth_login_failed", {"ip": _client_ip(request)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    session.add(AuditLog(action="auth_login_success", details={"ip": _client_ip(request)}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.post("/logout")
async def auth_logout(
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
    session.add(TokenBlocklist(jti=payload.jti, expires_at=expires_at))
    session.add(AuditLog(action="auth_logout", details={"sub": payload.sub}))
    await session.commit()

    response = JSONResponse(content={"ok": True}, status_code=status.HTTP_200_OK)
    return clear_auth_cookie(response)


@router.post("/change-password")
async def auth_change_password(
    body: ChangePasswordRequest,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not verify_password(body.current_password, config.value["hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    config.value = {"hash": hash_password(body.new_password)}

    # Stamp the change time so every token issued before now is rejected by
    # require_auth. Without this, outstanding sessions survive a password
    # change and keep full admin access until they expire on their own.
    changed_at = int(datetime.now(timezone.utc).timestamp())
    stamp = (await session.execute(
        select(Config).where(Config.key == PASSWORD_CHANGED_AT_KEY)
    )).scalar_one_or_none()
    if stamp:
        stamp.value = {"ts": changed_at}
    else:
        session.add(Config(key=PASSWORD_CHANGED_AT_KEY, value={"ts": changed_at}))

    session.add(AuditLog(action="auth_password_change", details={"ip": _client_ip(request)}))

    response = JSONResponse(content={"ok": True})
    # The caller's own current token predates changed_at and would be rejected
    # on the next request; reissue so they stay logged in after rotating.
    token = create_access_token({"sub": payload.sub})
    return set_auth_cookie(response, token)


@router.post("/refresh")
async def auth_refresh(payload: TokenPayload = Depends(require_auth)):
    token = create_access_token({"sub": payload.sub})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.get("/me")
async def auth_me(payload: TokenPayload = Depends(require_auth)):
    return {"authenticated": True, "sub": payload.sub}
