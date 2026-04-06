import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.models.code import CodeFile, CodeSymbol, Repository
from app.schemas.code import (
    CodeFileResponse,
    CodeSearchRequest,
    CodeSearchResult,
    CodeSymbolResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/code", tags=["code"])


@router.post("/search", response_model=list[CodeSearchResult])
async def search_code(
    body: CodeSearchRequest,
    _user=Depends(require_auth),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    results_map: dict[str, dict] = {}

    llm = getattr(request.app.state, "llm", None) if request else None
    qdrant = getattr(request.app.state, "vector_repo", None) if request else None

    if llm and qdrant:
        try:
            vector = await llm.embed(body.query)
            conditions = []
            if body.repo_id:
                conditions.append(FieldCondition(key="repo_id", match=MatchValue(value=str(body.repo_id))))
            if body.language:
                conditions.append(FieldCondition(key="language", match=MatchValue(value=body.language)))
            qdrant_filter = Filter(must=conditions) if conditions else None

            vector_results = await qdrant.client.query_points(
                collection_name="code_chunks",
                query=vector,
                limit=body.limit * 2,
                query_filter=qdrant_filter,
            )
            for rank, p in enumerate(vector_results.points):
                key = f"{p.payload.get('file_path', '')}:{p.payload.get('line_start', 0)}"
                if key not in results_map:
                    results_map[key] = {
                        "chunk_content": p.payload.get("chunk_content", ""),
                        "file_path": p.payload.get("file_path", ""),
                        "repo_id": p.payload.get("repo_id", ""),
                        "language": p.payload.get("language"),
                        "symbol_name": p.payload.get("symbol_name"),
                        "line_start": p.payload.get("line_start", 0),
                        "line_end": p.payload.get("line_end", 0),
                        "rrf_score": 0,
                    }
                results_map[key]["rrf_score"] += 1.0 / (60 + rank)
        except Exception as e:
            logger.warning("Vector search failed: %s", e)

    try:
        escaped = body.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        text_query = (
            select(CodeSymbol, CodeFile.file_path, CodeFile.repo_id)
            .join(CodeFile)
            .where(
                (CodeSymbol.name.ilike(f"%{escaped}%"))
                | (CodeSymbol.source_code.ilike(f"%{escaped}%"))
            )
        )
        if body.repo_id:
            text_query = text_query.where(CodeFile.repo_id == body.repo_id)
        text_query = text_query.limit(body.limit * 2)

        text_results = (await session.execute(text_query)).all()
        for rank, (sym, file_path, repo_id) in enumerate(text_results):
            key = f"{file_path}:{sym.line_start}"
            if key not in results_map:
                results_map[key] = {
                    "chunk_content": sym.source_code[:500] if sym.source_code else "",
                    "file_path": file_path,
                    "repo_id": str(repo_id),
                    "language": None,
                    "symbol_name": sym.name,
                    "line_start": sym.line_start,
                    "line_end": sym.line_end,
                    "rrf_score": 0,
                }
            results_map[key]["rrf_score"] += 1.0 / (60 + rank)
    except Exception as e:
        logger.warning("Text search failed: %s", e)

    sorted_results = sorted(results_map.values(), key=lambda x: x["rrf_score"], reverse=True)[:body.limit]

    return [
        CodeSearchResult(
            chunk_content=r["chunk_content"],
            file_path=r["file_path"],
            repo_id=UUID(r["repo_id"]) if r["repo_id"] else UUID("00000000-0000-0000-0000-000000000000"),
            language=r["language"],
            symbol_name=r["symbol_name"],
            line_start=r["line_start"],
            line_end=r["line_end"],
            score=r["rrf_score"],
        )
        for r in sorted_results
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


@router.get("/symbols/lookup")
async def lookup_symbol(
    name: str = Query(...),
    file_path: str = Query(...),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    sym = (await session.execute(
        select(CodeSymbol).join(CodeFile).where(
            CodeSymbol.name == name,
            CodeFile.file_path == file_path,
        )
    )).scalars().first()
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
    _user=Depends(require_auth),
):
    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    repo_id_str = str(repo_id)
    nodes = []
    edges = []

    async with graph_repo.driver.session() as neo:
        file_result = await neo.run(
            "MATCH (f:CodeFile {repo_id: $repo_id}) RETURN f.file_path AS id, f.file_path AS label, 'file' AS kind",
            repo_id=repo_id_str,
        )
        async for record in file_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        sym_result = await neo.run(
            """
            MATCH (s:CodeSymbol {repo_id: $repo_id})
            RETURN s.name + '::' + s.file_path AS id, s.name AS label, s.kind AS kind, s.file_path AS file_path
            """,
            repo_id=repo_id_str,
        )
        async for record in sym_result:
            nodes.append({
                "id": record["id"], "label": record["label"],
                "kind": record["kind"], "file_path": record["file_path"],
            })

        mod_result = await neo.run(
            """
            MATCH (:CodeFile {repo_id: $repo_id})-[:IMPORTS]->(m:Module)
            RETURN DISTINCT 'mod::' + m.name AS id, m.name AS label, 'module' AS kind
            """,
            repo_id=repo_id_str,
        )
        async for record in mod_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        defines_result = await neo.run(
            """
            MATCH (f:CodeFile {repo_id: $repo_id})-[:DEFINES]->(s:CodeSymbol {repo_id: $repo_id})
            RETURN f.file_path AS source, s.name + '::' + s.file_path AS target, 'defines' AS type
            """,
            repo_id=repo_id_str,
        )
        async for record in defines_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        contains_result = await neo.run(
            """
            MATCH (p:CodeSymbol {repo_id: $repo_id})-[:CONTAINS]->(c:CodeSymbol {repo_id: $repo_id})
            RETURN p.name + '::' + p.file_path AS source, c.name + '::' + c.file_path AS target, 'contains' AS type
            """,
            repo_id=repo_id_str,
        )
        async for record in contains_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        imports_result = await neo.run(
            """
            MATCH (f:CodeFile {repo_id: $repo_id})-[:IMPORTS]->(m:Module)
            RETURN f.file_path AS source, 'mod::' + m.name AS target, 'imports' AS type
            """,
            repo_id=repo_id_str,
        )
        async for record in imports_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        calls_result = await neo.run(
            """
            MATCH (s1:CodeSymbol {repo_id: $repo_id})-[r:CALLS]->(s2:CodeSymbol {repo_id: $repo_id})
            RETURN s1.name + '::' + s1.file_path AS source, s2.name + '::' + s2.file_path AS target, 'calls' AS type
            """,
            repo_id=repo_id_str,
        )
        async for record in calls_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # Property nodes
        prop_result = await neo.run(
            "MATCH (p:Property {repo_id: $repo_id}) RETURN 'prop::' + p.owner + '.' + p.name + '::' + p.file_path AS id, p.name AS label, 'property' AS kind, p.file_path AS file_path",
            repo_id=repo_id_str,
        )
        async for record in prop_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"], "file_path": record.get("file_path")})

        # Route nodes
        route_result = await neo.run(
            "MATCH (r:Route {repo_id: $repo_id}) RETURN 'route::' + r.method + '::' + r.path AS id, COALESCE(r.method, '') + ' ' + r.path AS label, 'route' AS kind",
            repo_id=repo_id_str,
        )
        async for record in route_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        # Tool nodes
        tool_result = await neo.run(
            "MATCH (t:Tool {repo_id: $repo_id}) RETURN 'tool::' + t.name AS id, t.name AS label, 'tool' AS kind",
            repo_id=repo_id_str,
        )
        async for record in tool_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        # EXTENDS edges
        extends_result = await neo.run(
            "MATCH (c:CodeSymbol {repo_id: $repo_id})-[:EXTENDS]->(p:CodeSymbol {repo_id: $repo_id}) RETURN c.name + '::' + c.file_path AS source, p.name + '::' + p.file_path AS target, 'extends' AS type",
            repo_id=repo_id_str,
        )
        async for record in extends_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # IMPLEMENTS edges
        impl_result = await neo.run(
            "MATCH (c:CodeSymbol {repo_id: $repo_id})-[:IMPLEMENTS]->(p:CodeSymbol {repo_id: $repo_id}) RETURN c.name + '::' + c.file_path AS source, p.name + '::' + p.file_path AS target, 'implements' AS type",
            repo_id=repo_id_str,
        )
        async for record in impl_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # HAS_METHOD edges
        hm_result = await neo.run(
            "MATCH (c:CodeSymbol {repo_id: $repo_id})-[:HAS_METHOD]->(m:CodeSymbol {repo_id: $repo_id}) RETURN c.name + '::' + c.file_path AS source, m.name + '::' + m.file_path AS target, 'has_method' AS type",
            repo_id=repo_id_str,
        )
        async for record in hm_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # HAS_PROPERTY edges
        hp_result = await neo.run(
            "MATCH (c:CodeSymbol {repo_id: $repo_id})-[:HAS_PROPERTY]->(p:Property {repo_id: $repo_id}) RETURN c.name + '::' + c.file_path AS source, 'prop::' + p.owner + '.' + p.name + '::' + p.file_path AS target, 'has_property' AS type",
            repo_id=repo_id_str,
        )
        async for record in hp_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # HANDLES_ROUTE edges
        hr_result = await neo.run(
            "MATCH (f:CodeFile {repo_id: $repo_id})-[:HANDLES_ROUTE]->(r:Route {repo_id: $repo_id}) RETURN f.file_path AS source, 'route::' + COALESCE(r.method, '') + '::' + r.path AS target, 'handles_route' AS type",
            repo_id=repo_id_str,
        )
        async for record in hr_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # HANDLES_TOOL edges
        ht_result = await neo.run(
            "MATCH (f:CodeFile {repo_id: $repo_id})-[:HANDLES_TOOL]->(t:Tool {repo_id: $repo_id}) RETURN f.file_path AS source, 'tool::' + t.name AS target, 'handles_tool' AS type",
            repo_id=repo_id_str,
        )
        async for record in ht_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # METHOD_OVERRIDES edges
        mo_result = await neo.run(
            "MATCH (c:CodeSymbol {repo_id: $repo_id})-[:METHOD_OVERRIDES]->(m:CodeSymbol {repo_id: $repo_id}) RETURN c.name + '::' + c.file_path AS source, m.name + '::' + m.file_path AS target, 'method_overrides' AS type",
            repo_id=repo_id_str,
        )
        async for record in mo_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # METHOD_IMPLEMENTS edges
        mi_result = await neo.run(
            "MATCH (m1:CodeSymbol {repo_id: $repo_id})-[:METHOD_IMPLEMENTS]->(m2:CodeSymbol {repo_id: $repo_id}) RETURN m1.name + '::' + m1.file_path AS source, m2.name + '::' + m2.file_path AS target, 'method_implements' AS type",
            repo_id=repo_id_str,
        )
        async for record in mi_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # ACCESSES edges
        acc_result = await neo.run(
            "MATCH (s:CodeSymbol {repo_id: $repo_id})-[:ACCESSES]->(p:Property {repo_id: $repo_id}) RETURN s.name + '::' + s.file_path AS source, 'prop::' + p.owner + '.' + p.name + '::' + p.file_path AS target, 'accesses' AS type",
            repo_id=repo_id_str,
        )
        async for record in acc_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # Community nodes
        comm_result = await neo.run(
            "MATCH (c:Community {repo_id: $repo_id}) RETURN 'comm::' + toString(c.community_id) AS id, c.label AS label, 'community' AS kind",
            repo_id=repo_id_str,
        )
        async for record in comm_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        # Process nodes
        proc_result = await neo.run(
            "MATCH (p:Process {repo_id: $repo_id}) RETURN 'proc::' + p.name AS id, p.name AS label, 'process' AS kind",
            repo_id=repo_id_str,
        )
        async for record in proc_result:
            nodes.append({"id": record["id"], "label": record["label"], "kind": record["kind"]})

        # MEMBER_OF edges
        mof_result = await neo.run(
            "MATCH (s:CodeSymbol {repo_id: $repo_id})-[:MEMBER_OF]->(c:Community {repo_id: $repo_id}) RETURN s.name + '::' + s.file_path AS source, 'comm::' + toString(c.community_id) AS target, 'member_of' AS type",
            repo_id=repo_id_str,
        )
        async for record in mof_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # STEP_IN_PROCESS edges
        sip_result = await neo.run(
            "MATCH (s:CodeSymbol {repo_id: $repo_id})-[:STEP_IN_PROCESS]->(p:Process {repo_id: $repo_id}) RETURN s.name + '::' + s.file_path AS source, 'proc::' + p.name AS target, 'step_in_process' AS type",
            repo_id=repo_id_str,
        )
        async for record in sip_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

        # ENTRY_POINT_OF edges
        epo_result = await neo.run(
            """
            MATCH (r)-[:ENTRY_POINT_OF]->(p:Process {repo_id: $repo_id})
            WHERE r.repo_id = $repo_id AND (r:Route OR r:Tool)
            RETURN
                CASE WHEN r:Route THEN 'route::' + COALESCE(r.method, '') + '::' + r.path
                     ELSE 'tool::' + r.name END AS source,
                'proc::' + p.name AS target,
                'entry_point_of' AS type
            """,
            repo_id=repo_id_str,
        )
        async for record in epo_result:
            edges.append({"source": record["source"], "target": record["target"], "type": record["type"]})

    return {"nodes": nodes, "edges": edges}


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


class BlastRadiusRequest(BaseModel):
    symbol_id: str
    max_depth: int = 10


@router.post("/blast-radius")
async def blast_radius(
    body: BlastRadiusRequest,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Support both UUID and composite "name::file_path" format
    sym = None
    file = None
    if "::" in body.symbol_id:
        parts = body.symbol_id.split("::", 1)
        name, file_path = parts[0], parts[1]
        sym = (await session.execute(
            select(CodeSymbol).join(CodeFile).where(
                CodeSymbol.name == name,
                CodeFile.file_path == file_path,
            )
        )).scalars().first()
        if sym:
            file = (await session.execute(
                select(CodeFile).where(CodeFile.id == sym.file_id)
            )).scalar_one_or_none()
    else:
        try:
            from uuid import UUID as UUIDType
            uid = UUIDType(body.symbol_id)
            sym = (await session.execute(
                select(CodeSymbol).where(CodeSymbol.id == uid)
            )).scalar_one_or_none()
            if sym:
                file = (await session.execute(
                    select(CodeFile).where(CodeFile.id == sym.file_id)
                )).scalar_one_or_none()
        except ValueError:
            pass

    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")

    graph_repo = getattr(request.app.state, "graph_repo", None)
    if not graph_repo:
        raise HTTPException(status_code=503, detail="Graph service not available")

    async with graph_repo.driver.session() as neo:
        result = await neo.run(
            """
            MATCH (start:CodeSymbol {name: $name, repo_id: $repo_id})
            MATCH path = (caller)-[:CALLS|EXTENDS|IMPLEMENTS|ACCESSES|METHOD_OVERRIDES*1..10]->(start)
            WHERE caller <> start AND caller.repo_id = $repo_id
            RETURN DISTINCT caller.name AS name, caller.kind AS kind, caller.file_path AS file_path, length(path) AS distance
            ORDER BY distance
            """,
            name=sym.name,
            repo_id=str(file.repo_id) if file else "",
        )
        records = [r async for r in result]

    by_depth: dict[str, list] = {"1": [], "2": [], "3+": []}
    affected = []
    for r in records:
        entry = {"name": r["name"], "kind": r["kind"], "file_path": r["file_path"], "distance": r["distance"]}
        affected.append(entry)
        d = r["distance"]
        if d == 1:
            by_depth["1"].append(entry)
        elif d == 2:
            by_depth["2"].append(entry)
        else:
            by_depth["3+"].append(entry)

    direct_callers = len(by_depth["1"])
    risk = "LOW"
    if direct_callers > 10:
        risk = "CRITICAL"
    elif direct_callers > 5:
        risk = "HIGH"
    elif direct_callers > 2:
        risk = "MEDIUM"

    return {
        "symbol": {"id": str(sym.id), "name": sym.name, "file_path": file.file_path if file else ""},
        "affected": affected,
        "by_depth": by_depth,
        "risk": risk,
        "total": len(affected),
    }
