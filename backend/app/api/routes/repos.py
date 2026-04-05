import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_code_indexer, get_repo_manager
from app.database import get_session
from app.models.code import CodeFile, CodeSymbol, Repository
from app.schemas.code import RepoCreate, RepoResponse, RepoUpdate
from app.services.code_indexer import CodeIndexer
from app.services.repo_manager import RepoManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/repos", tags=["repos"])

_active_reindex_tasks: set[asyncio.Task] = set()


def cancel_active_reindex_tasks():
    for task in _active_reindex_tasks:
        task.cancel()
    _active_reindex_tasks.clear()


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
        status=repo.status,
        status_message=repo.status_message,
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


@router.get("/stats")
async def repo_stats(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    total_repos = (await session.execute(select(func.count()).select_from(Repository))).scalar() or 0
    total_files = (await session.execute(select(func.count()).select_from(CodeFile))).scalar() or 0
    total_symbols = (await session.execute(select(func.count()).select_from(CodeSymbol))).scalar() or 0
    pending = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "pending")
    )).scalar() or 0
    completed = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "completed")
    )).scalar() or 0
    return {
        "total_repos": total_repos,
        "total_files": total_files,
        "total_symbols": total_symbols,
        "enrichment_pending": pending,
        "enrichment_completed": completed,
    }


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


@router.post("/{repo_id}/reindex")
async def reindex_repo(
    repo_id: UUID,
    full: bool = False,
    _user=Depends(require_auth),
    indexer: CodeIndexer = Depends(get_code_indexer),
    manager: RepoManager = Depends(get_repo_manager),
):
    from app.database import async_session_factory

    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.status = "indexing"
    repo.status_message = "Queued for indexing..."
    await manager.session.flush()
    await manager.session.commit()

    async def _run_index():
        try:
            async with async_session_factory() as session:
                from app.api.deps import get_code_indexer as _make_indexer
                idx = CodeIndexer(
                    session,
                    indexer.llm,
                    indexer.vector_repo,
                    indexer.graph_repo,
                )
                await idx.index_repo(repo_id, full=full)
        except Exception as e:
            logger.error(f"Background reindex failed for {repo_id}: {e}")
            try:
                async with async_session_factory() as session:
                    from app.models.code import Repository
                    from sqlalchemy import select
                    r = (await session.execute(
                        select(Repository).where(Repository.id == repo_id)
                    )).scalar_one_or_none()
                    if r:
                        r.status = "error"
                        r.status_message = str(e)[:500]
                        await session.commit()
            except Exception as inner_e:
                logger.error("Failed to set error status for repo %s: %s", repo_id, inner_e)

    task = asyncio.create_task(_run_index())
    _active_reindex_tasks.add(task)
    task.add_done_callback(_active_reindex_tasks.discard)
    return {"status": "indexing", "repo_id": str(repo_id)}


@router.post("/webhook")
async def webhook(
    request: FastAPIRequest,
    indexer: CodeIndexer = Depends(get_code_indexer),
    manager: RepoManager = Depends(get_repo_manager),
):
    body = await request.json()
    repo_url = None
    if "repository" in body:
        repo_url = (
            body["repository"].get("clone_url")
            or body["repository"].get("html_url")
            or body["repository"].get("url")
        )
    if not repo_url:
        return {"status": "ignored", "reason": "no repository URL found"}
    repos_list = await manager.list_all()
    matched = None
    for item in repos_list:
        r = item["repo"]
        if r.url and repo_url.rstrip(".git").rstrip("/") in r.url.rstrip(".git").rstrip("/"):
            matched = r
            break
    if not matched:
        return {"status": "ignored", "reason": "no matching repository"}
    result = await indexer.index_repo(matched.id)
    return {"status": "indexed", "repo": matched.name, "result": result}
