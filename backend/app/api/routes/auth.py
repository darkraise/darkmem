from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import create_access_token, hash_password, verify_password
from app.database import get_session
from app.models.config import Config

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ADMIN_PASSWORD_KEY = "admin_password_hash"


class PasswordRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str


class StatusResponse(BaseModel):
    initialized: bool


@router.get("/status", response_model=StatusResponse)
async def auth_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()
    return StatusResponse(initialized=config is not None)


@router.post("/setup", response_model=TokenResponse)
async def auth_setup(body: PasswordRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password already set")

    if len(body.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    hashed = hash_password(body.password)
    session.add(Config(key=ADMIN_PASSWORD_KEY, value={"hash": hashed}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    return TokenResponse(token=token)


@router.post("/login", response_model=TokenResponse)
async def auth_login(body: PasswordRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Config).where(Config.key == ADMIN_PASSWORD_KEY))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin password not set")

    if not verify_password(body.password, config.value["hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    token = create_access_token({"sub": "admin"})
    return TokenResponse(token=token)
