from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
COOKIE_NAME = "darkmem_session"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    jti: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode["exp"] = expire
    to_encode["iat"] = now
    to_encode["jti"] = uuid4().hex
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def set_auth_cookie(response: JSONResponse, token: str) -> JSONResponse:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=settings.environment == "production",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    return response


def clear_auth_cookie(response: JSONResponse) -> JSONResponse:
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return response


async def is_token_revoked(jti: str, session: AsyncSession) -> bool:
    from app.models.token_blocklist import TokenBlocklist

    result = await session.execute(select(TokenBlocklist).where(TokenBlocklist.jti == jti))
    return result.scalar_one_or_none() is not None


def _extract_token(request: Request) -> str | None:
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


async def require_auth(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPayload:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        token_data = TokenPayload(**payload)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    if await is_token_revoked(token_data.jti, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    return token_data


async def require_uninitialized(
    session: AsyncSession = Depends(get_session),
) -> None:
    """Gate wizard-only endpoints to a fresh-install state.

    Raises 403 once the admin password row exists in ``config``. The
    setup wizard is the only legitimate caller; once setup completes,
    these endpoints stay locked even though they are unauthenticated.
    """
    from app.models.config import Config

    result = await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        )
