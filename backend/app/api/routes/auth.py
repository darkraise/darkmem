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
from app.config import settings
from app.database import get_session
from app.models.audit import AuditLog
from app.models.config import Config
from app.models.token_blocklist import TokenBlocklist

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ADMIN_PASSWORD_KEY = "admin_password_hash"


class PasswordRequest(BaseModel):
    password: str = Field(max_length=128)


class SetupRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    setup_secret: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class StatusResponse(BaseModel):
    initialized: bool


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/status", response_model=StatusResponse)
async def auth_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()
    return StatusResponse(initialized=config is not None)


@router.post("/setup")
async def auth_setup(
    body: SetupRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if settings.setup_secret and body.setup_secret != settings.setup_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid setup secret")

    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password already set")

    hashed = hash_password(body.password)
    session.add(Config(key=ADMIN_PASSWORD_KEY, value={"hash": hashed}))
    session.add(AuditLog(action="auth_setup", details={"ip": _client_ip(request)}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


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
        session.add(AuditLog(action="auth_login_failed", details={"ip": _client_ip(request)}))
        await session.flush()
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
    session.add(AuditLog(action="auth_password_change", details={"ip": _client_ip(request)}))
    await session.flush()

    return JSONResponse(content={"ok": True})


@router.post("/refresh")
async def auth_refresh(payload: TokenPayload = Depends(require_auth)):
    token = create_access_token({"sub": payload.sub})
    response = JSONResponse(content={"ok": True})
    return set_auth_cookie(response, token)


@router.get("/me")
async def auth_me(payload: TokenPayload = Depends(require_auth)):
    return {"authenticated": True, "sub": payload.sub}
