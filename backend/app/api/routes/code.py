import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.schemas.code import (
    BlastRadiusRequest,
    CodeFileResponse,
    CodeSearchRequest,
    CodeSearchResult,
    CodeSymbolResponse,
)
from app.services.code_query import CodeQueryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code", tags=["code"])


def _get_service(request: Request, session: AsyncSession) -> CodeQueryService:
    llm = getattr(request.app.state, "llm", None) if request else None
    return CodeQueryService(session, llm=llm)


@router.post("/search", response_model=list[CodeSearchResult])
async def search_code(
    body: CodeSearchRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    results = await svc.search_code(body.query, body.limit, body.repo_id, body.language)
    return [
        CodeSearchResult(
            chunk_content=r["chunk_content"],
            file_path=r["file_path"],
            repo_id=UUID(r["repo_id"]) if r["repo_id"] else None,
            language=r["language"],
            symbol_name=r["symbol_name"],
            line_start=r["line_start"],
            line_end=r["line_end"],
            score=r["rrf_score"],
        )
        for r in results
    ]


@router.get("/symbols")
async def list_symbols(
    repo_id: UUID | None = None,
    file_path: str | None = None,
    kind: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    result = await svc.list_symbols(repo_id, file_path, kind, q, offset, limit)
    result["items"] = [CodeSymbolResponse(**item) for item in result["items"]]
    return result


@router.get("/symbols/lookup")
async def lookup_symbol(
    name: str = Query(...),
    file_path: str = Query(...),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    result = await svc.lookup_symbol(name, file_path)
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return CodeSymbolResponse(**result)


@router.get("/symbols/{symbol_id}", response_model=CodeSymbolResponse)
async def get_symbol(
    symbol_id: UUID,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    result = await svc.get_symbol(symbol_id)
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return CodeSymbolResponse(**result)


@router.get("/files/{repo_id}", response_model=list[CodeFileResponse])
async def list_files(
    repo_id: UUID,
    path_prefix: str | None = None,
    language: str | None = None,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    results = await svc.list_files(repo_id, path_prefix, language)
    return [CodeFileResponse(**f) for f in results]


@router.get("/graph/{repo_id}")
async def code_graph(
    repo_id: UUID,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    return await svc.get_code_graph(repo_id)


@router.get("/wiki/{repo_id}")
async def get_wiki(
    repo_id: UUID,
    force: bool = False,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    from app.services.wiki_generator import WikiGenerator
    llm = getattr(request.app.state, "llm", None) if request else None
    generator = WikiGenerator(session, llm)
    return await generator.generate(repo_id, force=force)


@router.post("/blast-radius")
async def blast_radius(
    body: BlastRadiusRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    svc = _get_service(request, session)
    result = await svc.calculate_blast_radius(body.symbol_id, body.max_depth)
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return result
