from fastapi import APIRouter, Depends, HTTPException, Query, Request

import numpy as np

from app.api.auth import require_auth
from app.repositories.vector import QdrantVectorRepository

router = APIRouter(prefix="/api/v1/vectors", tags=["vectors"])


def _get_vector_repo(request: Request) -> QdrantVectorRepository:
    repo = getattr(request.app.state, "vector_repo", None)
    if not repo:
        raise HTTPException(status_code=503, detail="Vector service not available")
    return repo


def _pca_2d(vectors: list[list[float]]) -> list[list[float]]:
    mat = np.array(vectors, dtype=np.float32)
    mat -= mat.mean(axis=0)
    cov = np.cov(mat, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1][:2]
    projection = mat @ eigenvectors[:, idx]
    # Normalize to [-1, 1]
    pmax = np.abs(projection).max(axis=0, keepdims=True)
    pmax[pmax == 0] = 1
    projection = projection / pmax
    return projection.tolist()


@router.get("/graph")
async def get_memory_graph(
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(200),
    _user=Depends(require_auth),
    request: Request = None,
):
    repo = _get_vector_repo(request)
    graph = await repo.get_similarity_graph(threshold=threshold, limit=limit)
    nodes = []
    for n in graph["nodes"]:
        payload = n.get("payload", {})
        nodes.append({
            "id": n["memory_id"],
            "content": (payload.get("content", "") or "")[:120],
            "source": payload.get("source", ""),
            "tags": payload.get("tags", []),
            "memory_type": payload.get("memory_type"),
        })
    return {"nodes": nodes, "edges": graph["edges"]}


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
    coords = _pca_2d(vectors)

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
