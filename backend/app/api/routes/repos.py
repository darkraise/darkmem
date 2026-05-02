import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_code_pipeline, get_repo_manager
from app.database import get_session
from app.models.code import CodeFile, CodeSymbol, Repository
from app.schemas.code import RepoCreate, RepoResponse, RepoUpdate
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager

logger = logging.getLogger(__name__)

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
    try:
        repo = await manager.create(body)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Repository '{body.name}' already exists")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    request: FastAPIRequest,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    # Snapshot the current values BEFORE the update so we can detect
    # whether the change actually flipped any polling-relevant field.
    # Both ``sync_interval_minutes`` and ``is_active`` directly affect
    # the periodic_repo_sync loop's "is this repo due now?" decision —
    # changes to either should wake the worker so the new cadence
    # takes effect immediately instead of after the next 5-minute tick.
    existing = await manager.get(repo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Repository not found")
    prev_interval = existing.sync_interval_minutes
    prev_active = existing.is_active

    repo = await manager.update(repo_id, body)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    polling_relevant_changed = (
        repo.sync_interval_minutes != prev_interval
        or repo.is_active != prev_active
    )
    if polling_relevant_changed:
        wakeup = getattr(request.app.state, "repo_sync_wakeup", None)
        if wakeup is not None:
            wakeup.set()

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
    pipeline: CodePipeline = Depends(get_code_pipeline),
    manager: RepoManager = Depends(get_repo_manager),
):
    from app.database import async_session_factory

    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if repo.status in ("indexing", "cloning"):
        return {"status": "already_running", "repo_id": str(repo_id)}

    repo.status = "indexing"
    repo.status_message = "Queued for indexing..."
    await manager.session.flush()
    await manager.session.commit()

    _collection_name = pipeline.vector_repo.collection_name if pipeline.vector_repo else "code_chunks"
    _llm = pipeline.llm

    async def _run_index():
        try:
            async with async_session_factory() as session:
                from app.repositories.vector import PostgresVectorRepository
                fresh_vector_repo = PostgresVectorRepository(session, _collection_name)
                idx = CodePipeline(
                    session=session,
                    llm=_llm,
                    vector_repo=fresh_vector_repo,
                    repo_manager=RepoManager(session),
                )
                await idx.run(repo_id, full=full)
        except Exception as e:
            logger.error(f"Background reindex failed for {repo_id}: {e}")
            from app.api.websocket import event_manager
            await event_manager.broadcast("repo.indexing_failed", {"repo_id": str(repo_id), "error": str(e)[:200]})
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

    from app.services.task_registry import TaskRegistry
    task = asyncio.create_task(_run_index())
    TaskRegistry.register(repo_id, "reindex", task, "Indexing repository...")
    return {"status": "indexing", "repo_id": str(repo_id)}


@router.get("/{repo_id}/tasks")
async def get_repo_tasks(
    repo_id: UUID,
    _user=Depends(require_auth),
):
    from app.services.task_registry import TaskRegistry
    return TaskRegistry.get_repo_tasks(repo_id)


@router.delete("/{repo_id}/tasks/{task_id}")
async def cancel_repo_task(
    repo_id: UUID,
    task_id: str,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    from app.services.task_registry import TaskRegistry
    cancelled = TaskRegistry.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or already completed")

    repo = await manager.get(repo_id)
    if repo and repo.status in ("cloning", "indexing"):
        repo.status = "cancelled"
        repo.status_message = f"Task {task_id} cancelled by user"
        await manager.session.flush()

    return {"status": "cancelled", "task_id": task_id}


