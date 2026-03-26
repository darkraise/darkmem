import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.api_key import ApiKey
from app.repositories.relational import PostgresApiKeyRepository

security = HTTPBearer()


def generate_api_key(prefix: str | None = None) -> tuple[str, str]:
    prefix = prefix or settings.api_key_prefix
    raw = prefix + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: AsyncSession = Depends(get_session),
) -> ApiKey:
    key_hash = hash_api_key(credentials.credentials)
    repo = PostgresApiKeyRepository(session)
    api_key = await repo.get_by_key_hash(key_hash)

    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    await repo.update_last_used(api_key.id)
    return api_key


def require_scope(scope: str):
    async def _checker(api_key: ApiKey = Depends(get_current_api_key)) -> ApiKey:
        if scope not in api_key.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Scope '{scope}' required")
        return api_key

    return _checker
