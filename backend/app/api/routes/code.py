from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.models.code import CodeFile, CodeSymbol
from app.schemas.code import (
    CodeFileResponse,
    CodeSearchRequest,
    CodeSearchResult,
    CodeSymbolResponse,
)

router = APIRouter(prefix="/api/v1/code", tags=["code"])


@router.post("/search", response_model=list[CodeSearchResult])
async def search_code(
    body: CodeSearchRequest,
    request: Request,
    _user=Depends(require_auth),
):
    llm = getattr(request.app.state, "llm", None)
    vector_repo = getattr(request.app.state, "vector_repo", None)
    if not llm or not vector_repo:
        raise HTTPException(status_code=503, detail="Search service not available")

    query_vector = await llm.embed(body.query)

    conditions = []
    if body.repo_id:
        conditions.append(FieldCondition(key="repo_id", match=MatchValue(value=str(body.repo_id))))
    if body.language:
        conditions.append(FieldCondition(key="language", match=MatchValue(value=body.language)))

    query_filter = Filter(must=conditions) if conditions else None

    results = await vector_repo.client.query_points(
        collection_name="code_chunks",
        query=query_vector,
        query_filter=query_filter,
        limit=body.limit,
    )

    return [
        CodeSearchResult(
            chunk_content=p.payload.get("chunk_content", ""),
            file_path=p.payload.get("file_path", ""),
            repo_id=p.payload.get("repo_id", ""),
            language=p.payload.get("language"),
            symbol_name=p.payload.get("symbol_name"),
            line_start=p.payload.get("line_start", 0),
            line_end=p.payload.get("line_end", 0),
            score=p.score,
        )
        for p in results.points
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
    session: AsyncSession = Depends(get_session),
):
    query = select(CodeSymbol).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
    count_query = select(func.count(CodeSymbol.id)).join(CodeFile, CodeSymbol.file_id == CodeFile.id)

    if repo_id:
        query = query.where(CodeFile.repo_id == repo_id)
        count_query = count_query.where(CodeFile.repo_id == repo_id)
    if file_path:
        query = query.where(CodeFile.file_path == file_path)
        count_query = count_query.where(CodeFile.file_path == file_path)
    if kind:
        query = query.where(CodeSymbol.kind == kind)
        count_query = count_query.where(CodeSymbol.kind == kind)
    if q:
        query = query.where(CodeSymbol.name.ilike(f"%{q}%"))
        count_query = count_query.where(CodeSymbol.name.ilike(f"%{q}%"))

    total = (await session.execute(count_query)).scalar() or 0
    rows = (await session.execute(query.offset(offset).limit(limit))).scalars().all()

    items = []
    for sym in rows:
        items.append(CodeSymbolResponse(
            id=sym.id,
            name=sym.name,
            kind=sym.kind,
            file_path=sym.file.file_path if sym.file else "",
            line_start=sym.line_start,
            line_end=sym.line_end,
            signature=sym.signature,
            docstring=sym.docstring,
            visibility=sym.visibility,
            source_code=sym.source_code,
            summary=sym.summary,
            enrichment_status=sym.enrichment_status,
        ))

    return {"items": items, "total": total}


@router.get("/symbols/{symbol_id}", response_model=CodeSymbolResponse)
async def get_symbol(
    symbol_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    sym = (await session.execute(
        select(CodeSymbol).where(CodeSymbol.id == symbol_id)
    )).scalar_one_or_none()
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")

    file = (await session.execute(
        select(CodeFile).where(CodeFile.id == sym.file_id)
    )).scalar_one_or_none()

    return CodeSymbolResponse(
        id=sym.id,
        name=sym.name,
        kind=sym.kind,
        file_path=file.file_path if file else "",
        line_start=sym.line_start,
        line_end=sym.line_end,
        signature=sym.signature,
        docstring=sym.docstring,
        visibility=sym.visibility,
        source_code=sym.source_code,
        summary=sym.summary,
        enrichment_status=sym.enrichment_status,
    )


@router.get("/files/{repo_id}", response_model=list[CodeFileResponse])
async def list_files(
    repo_id: UUID,
    path_prefix: str | None = None,
    language: str | None = None,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    query = select(CodeFile).where(CodeFile.repo_id == repo_id)
    if path_prefix:
        query = query.where(CodeFile.file_path.startswith(path_prefix))
    if language:
        query = query.where(CodeFile.language == language)

    rows = (await session.execute(query)).scalars().all()
    return [
        CodeFileResponse(
            id=f.id,
            file_path=f.file_path,
            language=f.language,
            last_commit_sha=f.last_commit_sha,
            indexed_at=f.indexed_at,
        )
        for f in rows
    ]


@router.get("/graph/{repo_id}")
async def code_graph(
    repo_id: UUID,
    request: Request,
    view: str = Query("files", pattern="^(files|symbols)$"),
    _user=Depends(require_auth),
):
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    async with graph_repo.driver.session() as neo:
        if view == "files":
            result = await neo.run(
                """
                MATCH (f:CodeFile {repo_id: $repo_id})
                OPTIONAL MATCH (f)-[:IMPORTS]->(m:Module)<-[:IMPORTS]-(f2:CodeFile {repo_id: $repo_id})
                WHERE f <> f2
                RETURN collect(DISTINCT {id: f.file_path, label: f.file_path, type: 'file'}) AS nodes,
                       collect(DISTINCT {source: f.file_path, target: f2.file_path, label: m.name}) AS edges
                """,
                repo_id=str(repo_id),
            )
        else:
            result = await neo.run(
                """
                MATCH (s:CodeSymbol {repo_id: $repo_id})
                OPTIONAL MATCH (s)-[r:CALLS|CONTAINS]->(t:CodeSymbol {repo_id: $repo_id})
                RETURN collect(DISTINCT {id: s.name + '::' + s.file_path, label: s.name, kind: s.kind, file_path: s.file_path}) AS nodes,
                       collect(DISTINCT {source: s.name + '::' + s.file_path, target: t.name + '::' + t.file_path, label: type(r)}) AS edges
                """,
                repo_id=str(repo_id),
            )
        record = await result.single()

    nodes = record["nodes"] if record else []
    edges = [e for e in (record["edges"] if record else []) if e.get("target") is not None]
    return {"nodes": nodes, "edges": edges}


class BlastRadiusRequest(BaseModel):
    symbol_id: UUID
    max_depth: int = 10


@router.post("/blast-radius")
async def blast_radius(
    body: BlastRadiusRequest,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    sym = (await session.execute(
        select(CodeSymbol).where(CodeSymbol.id == body.symbol_id)
    )).scalar_one_or_none()
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")

    file = (await session.execute(
        select(CodeFile).where(CodeFile.id == sym.file_id)
    )).scalar_one_or_none()

    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    async with graph_repo.driver.session() as neo:
        result = await neo.run(
            """
            MATCH (start:CodeSymbol {name: $name, repo_id: $repo_id})
            MATCH (caller:CodeSymbol)-[:CALLS*1..]->(start)
            WHERE caller <> start AND caller.repo_id = $repo_id
            RETURN DISTINCT caller.name AS name, caller.kind AS kind, caller.file_path AS file_path
            """,
            name=sym.name,
            repo_id=str(file.repo_id) if file else "",
        )
        records = [r async for r in result]

    affected = [
        {"name": r["name"], "kind": r["kind"], "file_path": r["file_path"]}
        for r in records
    ]

    return {
        "symbol": {
            "id": str(sym.id),
            "name": sym.name,
            "file_path": file.file_path if file else "",
            "repo_id": str(file.repo_id) if file else "",
        },
        "affected": affected,
        "total": len(affected),
    }
