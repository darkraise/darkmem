import uuid
from dataclasses import dataclass
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
from app.database import SessionDep, get_session
from app.services.api_key_scopes import API_KEY_SCOPES, FORBIDDEN_SCOPES
from app.services.api_keys import authenticate, looks_like_credential, mark_key_used

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
COOKIE_NAME = "darkmem_session"
# Config row holding the Unix timestamp of the last admin password change.
# Tokens issued strictly before this instant are rejected so a password
# change revokes every outstanding session. Kept in sync with
# ``app.api.routes.auth.PASSWORD_CHANGED_AT_KEY``.
PASSWORD_CHANGED_AT_KEY = "admin_password_changed_at"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    jti: str


def hash_password(password: str) -> str:
    validate_password_bytes(password)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        validate_password_bytes(password)
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def validate_password_bytes(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return password


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
        secure=settings.session_cookie_secure,
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


async def _password_changed_after(iat: int, session: AsyncSession) -> bool:
    """True if the admin password changed after a token was issued.

    Lets ``require_auth`` reject every session created before the most recent
    password change without enumerating individual ``jti`` values.
    """
    from app.models.config import Config

    result = await session.execute(
        select(Config).where(Config.key == PASSWORD_CHANGED_AT_KEY)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    changed_at = row.value.get("ts") if isinstance(row.value, dict) else None
    if not isinstance(changed_at, int):
        return False
    return iat < changed_at


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
    session: AsyncSession = SessionDep,
) -> TokenPayload:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await validate_session_token(token, session)


async def require_auth_for_stream(
    request: Request,
    session: AsyncSession = Depends(get_session, scope="request"),
) -> TokenPayload:
    """`require_auth` on a streaming route's request-scoped session, so the
    route holds one session rather than a second one closed before it streams."""
    return await require_auth(request, session)


async def validate_session_token(token: str, session: AsyncSession) -> TokenPayload:
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

    if await _password_changed_after(token_data.iat, session):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    return token_data


@dataclass(frozen=True)
class Principal:
    """Who is making a request, once one of the two credentials has resolved.

    ``api_key_id`` is ``None`` for a human session and is what T4.02 stamps on
    ``events``. ``scopes`` is present on both so a caller reads one shape, but
    it never carries ``ratify``: confirmed power is not expressible as a scope,
    it is the absence of a key, and ``require_auth`` alone is what guards it.
    """

    actor: str
    api_key_id: uuid.UUID | None
    scopes: frozenset[str]

    @property
    def is_human(self) -> bool:
        return self.api_key_id is None


def require_scope(scope: str):
    """Build a dependency admitting a human session, or a key holding ``scope``.

    **This is opt-in, and that is the fail-closed half of the activation.**
    ``require_auth`` is unchanged and still decodes a login JWT and nothing
    else, so every route that declares it stays unreachable by any key. A key
    reaches exactly the routes that name a scope here — today that is the
    push-webhook receiver alone (``POST /repos/{repo_id}/webhook``, T4.05),
    sanctioned by doc 18 §5 as one of the activation's own two triggers, not
    an anticipation of this route by T4.03. Assigning scopes to the rest of
    the existing surface is still T4.03's, and doing it by widening
    ``require_auth`` instead would have made every route keyed at once,
    silently.

    The scope literal is validated at decoration time, so a typo is a startup
    failure rather than a route that quietly admits nobody. ``ratify`` fails
    here twice over — it is forbidden, and it is not in the closed set.
    """
    if scope in FORBIDDEN_SCOPES or scope not in API_KEY_SCOPES:
        raise ValueError(
            f"{scope!r} is not an API-key scope; the closed set is "
            f"{', '.join(API_KEY_SCOPES)}"
        )

    async def _require_scope(
        request: Request,
        session: AsyncSession = SessionDep,
    ) -> Principal:
        # Cookie first, matching `_extract_token`: a browser session wins over
        # anything in the Authorization header, exactly as it does today.
        if not request.cookies.get(COOKIE_NAME):
            presented = request.headers.get("authorization", "")
            if presented.startswith("Bearer "):
                bearer = presented[7:].strip()
                if looks_like_credential(bearer):
                    principal = await authenticate(session, bearer)
                    if principal is None:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid API key",
                        )
                    if scope not in principal.scopes:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Key lacks the '{scope}' scope",
                        )
                    # After the scope check, not inside `authenticate`: a
                    # call that authenticates and then fails the scope gate
                    # did not use the key for anything.
                    await mark_key_used(principal.api_key_id)
                    return Principal(
                        actor=principal.name,
                        api_key_id=principal.api_key_id,
                        scopes=principal.scopes,
                    )

        token_data = await require_auth(request, session)
        return Principal(
            actor=token_data.sub,
            api_key_id=None,
            scopes=frozenset(API_KEY_SCOPES),
        )

    return _require_scope


async def require_uninitialized(
    session: AsyncSession = SessionDep,
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
