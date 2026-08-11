"""The articles read surface (doc 12 §4, doc 13 §5.2, T3.06).

Provides:
  - GET /api/v1/knowledge/articles       — a page of live articles, each badged
  - GET /api/v1/knowledge/articles/{id}  — one article, its citations, its lineage

Read-only. Ratification of an article (`POST /knowledge/articles/{id}/ratify`)
is doc 12 §6's single-door write and is not this module's; the reason it lives
apart is the trust model, not the routing.

Doc 12's route table names the detail door and not the list. The list is added
on the precedent its own sibling already set — `GET /knowledge/facts` is
likewise absent from that table and shipped, because doc 13's browsing surfaces
need a page and a semantic search is not one. Recorded here rather than
silently: the table is enumerative, so a door it does not name is a doc gap to
close, not permission to invent a shape.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.articles import ArticleDetailResponse, ArticleListResponse
from app.services import articles_read

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/articles", response_model=ArticleListResponse)
async def list_articles(
    project: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    items, total = await articles_read.list_articles(
        session, project=project, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/articles/{article_id}", response_model=ArticleDetailResponse)
async def get_article(
    article_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    item = await articles_read.get_article(session, article_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return item
