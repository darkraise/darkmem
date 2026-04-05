from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import require_auth
from app.api.deps import get_repo_manager
from app.models.code import Repository
from app.schemas.code import RepoCreate, RepoResponse, RepoUpdate
from app.services.repo_manager import RepoManager

router = APIRouter(prefix="/api/v1/repos", tags=["repos"])


def _to_response(repo: Repository, file_count: int = 0, symbol_count: int = 0) -> RepoResponse:
    return RepoResponse(
        id=repo.id,
        name=repo.name,
        url=repo.url,
        local_path=repo.local_path,
        provider=repo.provider,
        default_branch=repo.default_branch,
        last_indexed_commit=repo.last_indexed_commit,
        last_indexed_at=repo.last_indexed_at,
        sync_interval_minutes=repo.sync_interval_minutes,
        is_active=repo.is_active,
        file_count=file_count,
        symbol_count=symbol_count,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
    )


@router.post("", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def create_repo(
    body: RepoCreate,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    repo = await manager.create(body)
    return _to_response(repo)


@router.get("", response_model=list[RepoResponse])
async def list_repos(
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    entries = await manager.list_all()
    return [_to_response(e["repo"], e["file_count"], e["symbol_count"]) for e in entries]


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(
    repo_id: UUID,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return _to_response(repo)


@router.put("/{repo_id}", response_model=RepoResponse)
async def update_repo(
    repo_id: UUID,
    body: RepoUpdate,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    repo = await manager.update(repo_id, body)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return _to_response(repo)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repo(
    repo_id: UUID,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    if not await manager.delete(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found")
