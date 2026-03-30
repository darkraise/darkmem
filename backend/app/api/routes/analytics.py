import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import require_auth
from app.database import get_session
from app.models.memory import Memory, Tag
from app.schemas.config import StatsResponse
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
    tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
    sources_result = await session.execute(select(Memory.source).distinct())
    sources = [r[0] for r in sources_result.all()]

    entity_count = None
    rel_count = None
    graph_repo = getattr(request.app.state, "graph_repo", None) if request else None
    if graph_repo:
        try:
            stats = await graph_repo.get_stats()
            entity_count = stats["entity_count"]
            rel_count = stats["relationship_count"]
        except Exception:
            pass

    return StatsResponse(
        memories=memory_count, tags=tag_count,
        entities=entity_count, relationships=rel_count, sources=sources,
    )


@router.post("/reprocess")
async def reprocess_all_memories(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    pipeline: ProcessingPipeline | None = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        return {"error": "Pipeline not available", "processed": 0}

    stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712
    result = await session.execute(stmt)
    memories = result.scalars().all()

    processed = 0
    errors = 0
    for memory in memories:
        try:
            await pipeline.process_memory(
                memory_id=memory.id,
                content=memory.content,
                source=memory.source,
                tags=[t.name for t in memory.tags],
                memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            )
            processed += 1
            logger.info(f"Reprocessed {memory.id}")
        except Exception as e:
            errors += 1
            logger.error(f"Reprocess failed for {memory.id}: {e}")

    return {"processed": processed, "errors": errors, "total": len(memories)}
