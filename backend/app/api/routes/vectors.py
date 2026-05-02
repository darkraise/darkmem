from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.repositories.vector import PostgresVectorRepository
from app.utils.math import pca_2d

router = APIRouter(prefix="/api/v1/vectors", tags=["vectors"])


@router.get("/projection")
async def get_vector_projection(
    limit: int = Query(500, ge=1, le=5000),
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
    points = await repo.get_all_vectors(fingerprint=fingerprint, limit=limit)

    if len(points) < 2:
        return {"points": [
            {
                "memory_id": p["memory_id"],
                "x": 0.0,
                "y": 0.0,
                "content": (p["payload"].get("content", "") or "")[:100],
                "source": p["payload"].get("source", ""),
                "tags": p["payload"].get("tags", []),
                "memory_type": p["payload"].get("memory_type"),
            }
            for p in points
        ]}

    vectors = [p["vector"] for p in points]
    coords = pca_2d(vectors)

    result = []
    for i, p in enumerate(points):
        result.append({
            "memory_id": p["memory_id"],
            "x": round(coords[i][0], 4),
            "y": round(coords[i][1], 4),
            "content": (p["payload"].get("content", "") or "")[:100],
            "source": p["payload"].get("source", ""),
            "tags": p["payload"].get("tags", []),
            "memory_type": p["payload"].get("memory_type"),
        })

    return {"points": result}
