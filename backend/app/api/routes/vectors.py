from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.auth import require_auth
from app.repositories.vector import QdrantVectorRepository
from app.utils.math import pca_2d

router = APIRouter(prefix="/api/v1/vectors", tags=["vectors"])


def _get_vector_repo(request: Request) -> QdrantVectorRepository:
    repo = getattr(request.app.state, "vector_repo", None)
    if not repo:
        raise HTTPException(status_code=503, detail="Vector service not available")
    return repo


@router.get("/projection")
async def get_vector_projection(
    limit: int = Query(500),
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_vector_repo(request)
    points = await repo.get_all_vectors(limit=limit)

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
