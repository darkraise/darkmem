from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.schemas.memory import MemoryStatus
from app.utils.math import pca_2d

router = APIRouter(prefix="/api/v1/vectors", tags=["vectors"])


def _point(p: dict, x: float, y: float) -> dict:
    payload = p["payload"]
    return {
        "memory_id": p["memory_id"],
        "x": x,
        "y": y,
        "content": (payload.get("content", "") or "")[:100],
        "source": payload.get("source", ""),
        "tags": payload.get("tags", []),
        "memory_type": payload.get("memory_type"),
        "project": p.get("project"),
        "status": p.get("status"),
    }


@router.get("/projection")
async def get_vector_projection(
    limit: int = Query(500, ge=1, le=5000),
    project: str | None = Query(None),
    status: list[MemoryStatus] = Query(default=["active"]),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    llm = getattr(request.app.state, "llm", None) if request else None
    if llm is None:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    # Project the active embedder's vectors. Inactive fingerprints live in
    # other partitions; mixing spaces would yield meaningless coordinates.
    fingerprint = llm.llm_fingerprint()
    repo = PostgresVectorRepository(session)
    points = await repo.get_all_vectors(
        fingerprint=fingerprint,
        limit=limit,
        filters=MemoryFilter(project=project, statuses=tuple(status)),
    )

    if len(points) < 2:
        return {"points": [_point(p, 0.0, 0.0) for p in points]}

    vectors = [p["vector"] for p in points]
    coords = pca_2d(vectors)

    return {
        "points": [
            _point(p, round(coords[i][0], 4), round(coords[i][1], 4))
            for i, p in enumerate(points)
        ]
    }
