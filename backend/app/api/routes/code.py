import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.services.llm import lease_llm
from app.database import SessionDep
from app.schemas.code import (
    BlastRadiusRequest,
    CodeFileResponse,
    CodeSearchRequest,
    CodeSearchResult,
    CodeSymbolResponse,
)
from app.schemas.envelope import ErrorDetail, ErrorEnvelope
from app.services.code_query import CodeQueryService, SymbolAmbiguous, symbol_candidate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code", tags=["code"])


def _symbol_ambiguous(exc: SymbolAmbiguous):
    from fastapi.responses import JSONResponse

    body = ErrorEnvelope(
        error=ErrorDetail(code="symbol_ambiguous", message=str(exc)),
        detail=str(exc),
    ).model_dump()
    body["error"]["candidates"] = exc.candidates
    return JSONResponse(status_code=409, content=body)


def _get_service(request: Request, session: AsyncSession) -> CodeQueryService:
    llm = getattr(request.app.state, "llm", None) if request else None
    return CodeQueryService(session, llm=llm)


@router.post("/search", response_model=list[CodeSearchResult])
async def search_code(
    body: CodeSearchRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        answer = await svc.search_code(body.query, body.limit, body.repo_id, body.language)
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
            for r in answer.results
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
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        result = await svc.list_symbols(repo_id, file_path, kind, q, offset, limit)
        result["items"] = [CodeSymbolResponse(**item) for item in result["items"]]
        result["limit"] = limit
        result["offset"] = offset
        return result


@router.get("/symbols/lookup")
async def lookup_symbol(
    name: str = Query(...),
    file_path: str = Query(...),
    owner: str | None = Query(None),
    repo_id: UUID | None = Query(None),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        rows = await svc.lookup_symbol(repo_id, name, file_path, owner)
        if not rows:
            raise HTTPException(status_code=404, detail="Symbol not found")
        if len(rows) > 1:
            return _symbol_ambiguous(SymbolAmbiguous(
                name, [symbol_candidate(row) for row in rows],
            ))
        return CodeSymbolResponse(**rows[0])


@router.get("/symbols/{symbol_id}", response_model=CodeSymbolResponse)
async def get_symbol(
    symbol_id: UUID,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
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
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        results = await svc.list_files(repo_id, path_prefix, language)
        return [CodeFileResponse(**f) for f in results]


@router.get("/graph/{repo_id}")
async def code_graph(
    repo_id: UUID,
    level: Literal["symbol", "file", "auto"] | None = Query(
        None,
        description=(
            "Level of detail. Omitted with no scope: the whole symbol graph, "
            "unchanged. 'file' folds symbols into their files; 'auto' folds "
            "only when the scope holds more files plus symbols than the "
            "response's auto_limit."
        ),
    ),
    scope: str | None = Query(
        None, max_length=1024,
        description="A file or folder path; only it and what lies under it is drawn.",
    ),
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        return await svc.get_code_graph(repo_id, level=level, scope=scope)


@router.get("/wiki/{repo_id}", response_model=dict | None)
async def get_wiki(
    repo_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Read-only: returns the cached wiki, or null if none has been generated.
    Generating the wiki is an explicit, state-changing action — reindex the repo
    with generate_wiki=true (POST /repos/{repo_id}/reindex). A GET must never
    trigger generation."""
    from app.services.wiki_generator import WikiGenerator
    return await WikiGenerator(session, None).read(repo_id)


@router.post("/blast-radius")
async def blast_radius(
    body: BlastRadiusRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = SessionDep,
):
    svc = _get_service(request, session)
    with lease_llm(svc.llm):
        try:
            result = await svc.calculate_blast_radius(
                body.symbol_id, body.max_depth, repo_id=body.repo_id,
            )
        except SymbolAmbiguous as exc:
            return _symbol_ambiguous(exc)
        if not result:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return result
