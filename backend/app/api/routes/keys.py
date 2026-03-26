from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import generate_api_key, require_scope
from app.api.deps import get_api_key_repository
from app.repositories.relational import PostgresApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    raw_key, key_hash = generate_api_key()
    new_key = await repo.create(
        name=body.name,
        key_hash=key_hash,
        scopes=body.scopes,
        profile=body.profile,
        expires_at=body.expires_at,
    )
    return ApiKeyCreatedResponse(
        id=new_key.id,
        name=new_key.name,
        scopes=new_key.scopes,
        profile=new_key.profile,
        created_at=new_key.created_at,
        last_used_at=new_key.last_used_at,
        expires_at=new_key.expires_at,
        raw_key=raw_key,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    keys = await repo.list_all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    if not await repo.delete(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
