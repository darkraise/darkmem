import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, text

from app.database import async_session_factory
from app.schemas.memory import MemoryBatchCreate, MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService
from app.utils.graph_keys import compose_key, decompose_key

logger = logging.getLogger(__name__)

mcp = FastMCP("darkmem", json_response=True, stateless_http=True, streamable_http_path="/", instructions="")

_pipeline = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


@asynccontextmanager
async def _memory_service_context():
    async with async_session_factory() as session:
        try:
            yield MemoryService(session, pipeline=_pipeline)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from app.utils.serialization import memory_to_dict as _memory_to_dict


def _validate_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid UUID format: {value}")


# Mirror the HTTP search bound (MemorySearchRequest: limit ge=1, le=500) so an
# MCP caller cannot request an unbounded result set.
_MAX_LIMIT = 500


def _clamp_limit(limit: int, default: int) -> int:
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, _MAX_LIMIT))


@mcp.tool(
    description="Store a new memory in the knowledge system. Use this to save facts, decisions, preferences, debugging insights, infrastructure details, or any information worth remembering across sessions."
)
async def memory_add(
    content: str,
    tags: list[str] | None = None,
    source: str = "mcp",
    source_agent: str | None = None,
    memory_type: str | None = None,
    project: str | None = None,
) -> str:
    """
    Args:
        content: The memory content to store. Be specific and include context.
        tags: Categorization tags using slash notation (e.g., "project/darkmem", "debug/root-cause", "infra/services").
        source: Origin identifier (default: "mcp").
        source_agent: Optional agent/session identifier.
        memory_type: One of fact, decision, preference, problem, architecture, reference, milestone. Aliases (e.g. "debug"→"problem") are normalized; unknown values fall back to "fact".
        project: Supersession scope (default "default"). Set this so REPLACES-based supersession can fire within the intended project; tags do NOT feed this.
    """
    async with _memory_service_context() as service:
        data = MemoryCreate(
            content=content, tags=tags or [], source=source,
            source_agent=source_agent, memory_type=memory_type, project=project,
        )
        memory = await service.create_memory(data, api_key_id=None)
        return json.dumps(_memory_to_dict(memory))


@mcp.tool(
    description="Search stored memories by semantic query, tags, type, or source. Returns matching memories ranked by relevance. Use this to retrieve context before making decisions or to find previously stored knowledge."
)
async def memory_search(
    query: str | None = None,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    memory_type: str | None = None,
    source: str | None = None,
    limit: int = 20,
    offset: int = 0,
    semantic_weight: float = 0.7,
) -> str:
    """
    Args:
        query: Natural language search query. Uses semantic search if available, falls back to text matching.
        tags_any: Return memories matching ANY of these tags.
        tags_all: Return memories matching ALL of these tags.
        memory_type: Filter by type: fact, decision, preference, problem, architecture, reference, milestone.
        source: Filter by origin (e.g., "claude-code", "mcp", "api").
        limit: Maximum number of results (default: 20).
        offset: Pagination offset (default: 0).
        semantic_weight: Balance between semantic (1.0) and keyword (0.0) search (default: 0.7).
    """
    limit = _clamp_limit(limit, default=20)
    offset = max(0, int(offset))
    semantic_weight = min(1.0, max(0.0, float(semantic_weight)))
    async with _memory_service_context() as service:
        params = MemorySearchRequest(
            query=query, tags_any=tags_any, tags_all=tags_all,
            memory_type=memory_type, source=source,
            limit=limit, offset=offset, semantic_weight=semantic_weight,
        )
        memories = await service.search_memories(params)
        return json.dumps([_memory_to_dict(m) for m in memories])


@mcp.tool(
    description="Retrieve a specific memory by its UUID."
)
async def memory_get(memory_id: str) -> str:
    """
    Args:
        memory_id: The UUID of the memory to retrieve.
    """
    mid = _validate_uuid(memory_id)
    async with _memory_service_context() as service:
        memory = await service.get_memory(mid)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps(_memory_to_dict(memory))


@mcp.tool(
    description="Update an existing memory's content, tags, or type."
)
async def memory_update(
    memory_id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    memory_type: str | None = None,
) -> str:
    """
    Args:
        memory_id: The UUID of the memory to update.
        content: New content (replaces existing). Omit to keep current content.
        tags: New tags (replaces existing). Omit to keep current tags.
        memory_type: New type classification. Omit to keep current type.
    """
    mid = _validate_uuid(memory_id)
    async with _memory_service_context() as service:
        data = MemoryUpdate(content=content, tags=tags, memory_type=memory_type)
        memory = await service.update_memory(mid, data, api_key_id=None)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps(_memory_to_dict(memory))


@mcp.tool(
    description="Permanently delete a memory and its associated vectors and graph entities."
)
async def memory_delete(memory_id: str) -> str:
    """
    Args:
        memory_id: The UUID of the memory to delete.
    """
    mid = _validate_uuid(memory_id)
    async with _memory_service_context() as service:
        result = await service.delete_memory(mid, api_key_id=None)
        if not result:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps({"deleted": True, "memory_id": memory_id})


@mcp.tool(
    description="Create multiple memories in a single operation with parallel pipeline processing. Each entry follows the same format as memory_add. Concurrency is controlled by the pipeline_concurrency setting."
)
async def memory_batch_add(entries: list[dict]) -> str:
    """
    Args:
        entries: List of memory objects (1-100), each with 'content' (required), and optional 'tags', 'source', 'source_agent', 'memory_type', 'project' (supersession scope).
    """
    # Mirror the HTTP /memories/batch cap (MemoryBatchCreate: 1-100 entries)
    # so the MCP path cannot enqueue an unbounded batch.
    validated = MemoryBatchCreate(entries=entries)

    # Delegate to the service so creation threads every field (notably
    # ``project``, the supersession scope) and runs the phased batch pipeline
    # once. Re-implementing creation here previously dropped ``project``,
    # landing every batch-added memory in 'default'.
    async with _memory_service_context() as service:
        memories = await service.batch_create_memories(validated.entries, api_key_id=None)
        return json.dumps([_memory_to_dict(m) for m in memories])


@mcp.tool(
    description="Ask a question and get an answer based on stored memories (RAG). Searches semantically for relevant memories, then uses an LLM to synthesize an answer with source citations."
)
async def memory_reason(question: str, limit: int = 10) -> str:
    """
    Args:
        question: The question to answer using stored knowledge.
        limit: Maximum number of source memories to consider (default: 10).
    """
    limit = _clamp_limit(limit, default=10)
    async with _memory_service_context() as service:
        result = await service.reason(question, limit=limit)
        return json.dumps(result)


@mcp.tool(
    description="Find memories that are semantically similar to a given memory. Useful for detecting duplicates or finding related knowledge."
)
async def memory_find_duplicates(memory_id: str, threshold: float = 0.9) -> str:
    """
    Args:
        memory_id: The UUID of the memory to find duplicates for.
        threshold: Minimum similarity score (0.0-1.0, default: 0.9). Lower values return more results.
    """
    mid = _validate_uuid(memory_id)
    async with _memory_service_context() as service:
        results = await service.find_duplicates(mid, threshold)
        return json.dumps(results, default=str)


@mcp.tool(
    description="Get statistics about the memory system: total memories, tags, active sources."
)
async def memory_stats() -> str:
    from sqlalchemy import func

    from app.models.memory import Memory, Tag

    async with _memory_service_context() as service:
        session = service.session
        memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
        tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
        sources_result = await session.execute(select(Memory.source).distinct())
        sources = [r[0] for r in sources_result.all()]
        return json.dumps({"memories": memory_count, "tags": tag_count, "sources": sources})


@mcp.tool(
    description="List all tags with the number of memories in each. Useful for understanding how knowledge is categorized."
)
async def memory_tags() -> str:
    from app.repositories.relational import PostgresTagRepository

    async with _memory_service_context() as service:
        repo = PostgresTagRepository(service.session)
        tags_with_counts = await repo.get_with_counts()
        return json.dumps([{"name": t.name, "category": t.category, "count": c} for t, c in tags_with_counts])


# ---------------------------------------------------------------------------
# Code knowledge tools
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _code_service_context():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@mcp.tool(
    description="List all indexed code repositories with name, URL, file count, and symbol count."
)
async def list_repos() -> str:
    """
    Args: (none)
    """
    from app.services.repo_manager import RepoManager

    async with _code_service_context() as session:
        rows = await RepoManager(session).list_all()
        return json.dumps([
            {
                "id": str(r["repo"].id),
                "name": r["repo"].name,
                "url": r["repo"].url,
                "file_count": r["file_count"],
                "symbol_count": r["symbol_count"],
            }
            for r in rows
        ])


@mcp.tool(
    description="Semantic search over indexed code chunks. Returns matching file paths, symbol names, content snippets, and relevance scores."
)
async def code_search(
    query: str,
    repo_name: str | None = None,
    language: str | None = None,
    limit: int = 10,
) -> str:
    """
    Args:
        query: Natural language or code query to search for.
        repo_name: Optional repository name to restrict search to.
        language: Optional language filter (e.g., "python", "typescript").
        limit: Maximum number of results (default: 10).
    """
    if not _pipeline or not _pipeline.llm:
        raise ValueError("Pipeline not initialized")

    from app.models.code import Repository
    from app.repositories.vector import PostgresVectorRepository

    query_vector, query_fingerprint = await _pipeline.llm.embed(query)

    repo_id: UUID | None = None
    if repo_name:
        async with _code_service_context() as session:
            repo = (await session.execute(
                select(Repository).where(Repository.name == repo_name)
            )).scalar_one_or_none()
            if not repo:
                raise ValueError(f"Repository not found: {repo_name}")
            repo_id = repo.id

    async with _code_service_context() as session:
        vector_repo = PostgresVectorRepository(session)
        results = await vector_repo.search_code_chunks(
            query_vector,
            fingerprint=query_fingerprint,
            limit=limit,
            repo_id=repo_id,
            language=language,
        )

    return json.dumps([
        {
            "file_path": r["file_path"],
            "symbol_name": r["symbol_name"],
            "chunk_content": r["chunk_content"],
            "language": r["language"],
            "line_start": r["line_start"],
            "line_end": r["line_end"],
            "score": r["score"],
        }
        for r in results
    ])


@mcp.tool(
    description="Look up a code symbol by name. Returns its source code, summary, signature, file path, and metadata."
)
async def code_symbol(
    name: str,
    repo_name: str | None = None,
) -> str:
    """
    Args:
        name: The symbol name to look up (function, class, method, etc.).
        repo_name: Optional repository name to narrow the search.
    """
    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        query = select(CodeSymbol).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == name)
        rows = (await session.execute(query)).scalars().all()

        if not rows:
            raise ValueError(f"Symbol not found: {name}")

        return json.dumps([
            {
                "id": str(s.id),
                "name": s.name,
                "kind": s.kind,
                "file_path": s.file.file_path if s.file else "",
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "docstring": s.docstring,
                "source_code": s.source_code,
                "summary": s.summary,
                "visibility": s.visibility,
            }
            for s in rows
        ])


@mcp.tool(
    description="List all code symbols defined in a specific file, ordered by line number."
)
async def code_file_symbols(
    repo_name: str,
    file_path: str,
) -> str:
    """
    Args:
        repo_name: The repository name.
        file_path: The file path within the repository.
    """
    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        query = (
            select(CodeSymbol)
            .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
            .join(Repository, CodeFile.repo_id == Repository.id)
            .where(Repository.name == repo_name, CodeFile.file_path == file_path)
            .order_by(CodeSymbol.line_start)
        )
        rows = (await session.execute(query)).scalars().all()

        return json.dumps([
            {
                "id": str(s.id),
                "name": s.name,
                "kind": s.kind,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "summary": s.summary,
                "visibility": s.visibility,
            }
            for s in rows
        ])


@mcp.tool(
    description="Compute the blast radius of a symbol: find all symbols that transitively call it. Useful for impact analysis before refactoring."
)
async def code_blast_radius(
    symbol_name: str,
    repo_name: str | None = None,
    max_depth: int = 10,
) -> str:
    """
    Args:
        symbol_name: The name of the symbol to analyze.
        repo_name: Optional repository name to restrict the search.
        max_depth: Maximum call-chain depth to traverse (default: 10).
    """
    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        query = select(CodeSymbol, CodeFile).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == symbol_name)
        row = (await session.execute(query)).first()

        if not row:
            raise ValueError(f"Symbol not found: {symbol_name}")

        sym, file = row
        repo_id_str = str(file.repo_id)
        owner = None
        if sym.parent_symbol_id:
            owner = (await session.execute(
                select(CodeSymbol.name).where(CodeSymbol.id == sym.parent_symbol_id)
            )).scalar_one_or_none()
        symbol_key = compose_key("symbol", sym.name, file.file_path, owner=owner)
        depth = max(1, min(int(max_depth), 50))

        rows = (await session.execute(
            text("""
                WITH RECURSIVE callers AS (
                    SELECT source_key AS name, source_kind AS kind, 1 AS distance
                    FROM code_edges
                    WHERE repo_id = :repo_id
                      AND target_key = :symbol_key
                      AND edge_type IN ('calls', 'extends', 'implements', 'accesses', 'method_overrides')
                    UNION
                    SELECT e.source_key, e.source_kind, c.distance + 1
                    FROM callers c
                    JOIN code_edges e
                        ON e.target_key = c.name
                        AND e.repo_id = :repo_id
                        AND e.edge_type IN ('calls', 'extends', 'implements', 'accesses', 'method_overrides')
                    WHERE c.distance < :max_depth
                )
                SELECT DISTINCT name, kind, MIN(distance) AS distance
                FROM callers
                GROUP BY name, kind
                ORDER BY distance
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key, "max_depth": depth},
        )).mappings().all()

    by_depth: dict[str, list] = {"1": [], "2": [], "3+": []}
    affected = []
    for r in rows:
        name_val = r["name"]
        dist = r["distance"]
        file_path_val = None
        if "::" in (name_val or ""):
            name_val, file_path_val = decompose_key("symbol", name_val)
        entry = {"name": name_val, "kind": r["kind"], "file_path": file_path_val, "distance": dist}
        affected.append(entry)
        if dist == 1:
            by_depth["1"].append(entry)
        elif dist == 2:
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

    return json.dumps({
        "symbol": {
            "id": str(sym.id),
            "name": sym.name,
            "file_path": file.file_path,
        },
        "affected": affected,
        "by_depth": by_depth,
        "risk": risk,
        "total": len(affected),
    })


@mcp.tool(
    description="Query import dependencies for code files in a repository from the knowledge graph. Returns IMPORTS edges between files and modules."
)
async def code_dependencies(
    repo_name: str,
    file_path: str | None = None,
) -> str:
    """
    Args:
        repo_name: The repository name.
        file_path: Optional file path to get dependencies for a single file.
    """
    from app.models.code import Repository

    async with _code_service_context() as session:
        repo = (await session.execute(
            select(Repository).where(Repository.name == repo_name)
        )).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository not found: {repo_name}")

        params: dict = {"repo_id": str(repo.id)}
        extra_filter = ""
        if file_path:
            extra_filter = " AND source_key = :file_path"
            params["file_path"] = file_path

        rows = (await session.execute(
            text(f"""
                SELECT source_key AS file, target_key AS module
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'imports'
                  {extra_filter}
            """),
            params,
        )).mappings().all()

    return json.dumps([{"file": r["file"], "module": r["module"]} for r in rows])


@mcp.tool(description="Get 360-degree context for a code symbol: callers, callees, heritage, accesses, processes, community.")
async def code_context(
    symbol_name: str,
    repo_name: str | None = None,
) -> str:
    """
    Args:
        symbol_name: Name of the function, class, or method.
        repo_name: Optional repository name filter.
    """
    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        stmt = select(CodeSymbol, CodeFile.file_path).join(CodeFile).where(CodeSymbol.name == symbol_name)
        if repo_name:
            stmt = stmt.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        row = (await session.execute(stmt.limit(1))).first()
        if not row:
            raise ValueError(f"Symbol '{symbol_name}' not found")

        sym, file_path = row
        file = (await session.execute(select(CodeFile).where(CodeFile.id == sym.file_id))).scalar_one_or_none()
        repo_id_str = str(file.repo_id) if file else ""
        owner = None
        if sym.parent_symbol_id:
            owner = (await session.execute(
                select(CodeSymbol.name).where(CodeSymbol.id == sym.parent_symbol_id)
            )).scalar_one_or_none()
        symbol_key = compose_key("symbol", sym.name, file_path, owner=owner)

        context: dict = {
            "symbol": {
                "name": sym.name,
                "kind": sym.kind,
                "file_path": file_path,
                "signature": sym.signature,
                "summary": sym.summary,
            },
            "callers": [],
            "callees": [],
            "heritage": {"extends": [], "extended_by": [], "implements": []},
            "accesses": [],
            "processes": [],
            "community": None,
        }

        # Callers: symbols with an edge targeting this symbol_key via calls
        callers_rows = (await session.execute(
            text("""
                SELECT source_key
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND target_key = :symbol_key
                  AND edge_type = 'calls'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        for r in callers_rows:
            name_val = r["source_key"]
            fp_val = None
            if "::" in (name_val or ""):
                name_val, fp_val = decompose_key("symbol", name_val)
            context["callers"].append({"name": name_val, "file_path": fp_val})

        # Callees: symbols this symbol calls
        callees_rows = (await session.execute(
            text("""
                SELECT target_key
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND source_key = :symbol_key
                  AND edge_type = 'calls'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        for r in callees_rows:
            name_val = r["target_key"]
            fp_val = None
            if "::" in (name_val or ""):
                name_val, fp_val = decompose_key("symbol", name_val)
            context["callees"].append({"name": name_val, "file_path": fp_val})

        # Heritage: extends
        extends_rows = (await session.execute(
            text("""
                SELECT target_key FROM code_edges
                WHERE repo_id = :repo_id AND source_key = :symbol_key AND edge_type = 'extends'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        context["heritage"]["extends"] = [r["target_key"].split("::")[0] for r in extends_rows]

        extended_by_rows = (await session.execute(
            text("""
                SELECT source_key FROM code_edges
                WHERE repo_id = :repo_id AND target_key = :symbol_key AND edge_type = 'extends'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        context["heritage"]["extended_by"] = [r["source_key"].split("::")[0] for r in extended_by_rows]

        implements_rows = (await session.execute(
            text("""
                SELECT target_key FROM code_edges
                WHERE repo_id = :repo_id AND source_key = :symbol_key AND edge_type = 'implements'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        context["heritage"]["implements"] = [r["target_key"].split("::")[0] for r in implements_rows]

        # Community membership
        community_row = (await session.execute(
            text("""
                SELECT n.key, n.label
                FROM code_edges e
                JOIN code_graph_nodes n ON n.key = e.target_key AND n.repo_id = e.repo_id
                WHERE e.repo_id = :repo_id
                  AND e.source_key = :symbol_key
                  AND e.edge_type = 'member_of'
                  AND n.kind = 'community'
                LIMIT 1
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().first()
        if community_row:
            context["community"] = {"label": community_row["label"], "key": community_row["key"]}

        # Processes
        process_rows = (await session.execute(
            text("""
                SELECT n.label
                FROM code_edges e
                JOIN code_graph_nodes n ON n.key = e.target_key AND n.repo_id = e.repo_id
                WHERE e.repo_id = :repo_id
                  AND e.source_key = :symbol_key
                  AND e.edge_type = 'step_in_process'
                  AND n.kind = 'process'
            """),
            {"repo_id": repo_id_str, "symbol_key": symbol_key},
        )).mappings().all()
        context["processes"] = [r["label"] for r in process_rows]

    return json.dumps(context)


@mcp.tool(description="Analyze uncommitted git changes and identify affected code symbols and processes.")
async def code_changes(
    repo_name: str,
) -> str:
    """
    Args:
        repo_name: Repository name to analyze.
    """
    async with _code_service_context() as session:
        from app.models.code import CodeFile, CodeSymbol, Repository
        from app.services.repo_manager import RepoManager

        repo = (await session.execute(select(Repository).where(Repository.name == repo_name))).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")

        manager = RepoManager(session)
        work_dir = manager.repo_working_dir(repo)

        if not work_dir.exists():
            raise ValueError("Repository working directory not found")

        try:
            diff_output = await RepoManager._run_git(work_dir, ["git", "diff", "--name-status", "HEAD"])
        except Exception:
            diff_output = ""

        try:
            staged_output = await RepoManager._run_git(work_dir, ["git", "diff", "--name-status", "--cached"])
        except Exception:
            staged_output = ""

        changed_files = set()
        for line in (diff_output + "\n" + staged_output).strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                changed_files.add(parts[-1])

        if not changed_files:
            return json.dumps({"changed_files": [], "affected_symbols": [], "message": "No uncommitted changes"})

        affected = []
        for fp in changed_files:
            syms = (await session.execute(
                select(CodeSymbol).join(CodeFile).where(
                    CodeFile.repo_id == repo.id,
                    CodeFile.file_path == fp,
                )
            )).scalars().all()
            for s in syms:
                affected.append({"name": s.name, "kind": s.kind, "file_path": fp, "line_start": s.line_start})

        return json.dumps({
            "changed_files": list(changed_files),
            "affected_symbols": affected,
            "total_symbols": len(affected),
        })


@mcp.tool(description="List code communities detected via Leiden clustering for a repository.")
async def code_communities(repo_name: str) -> str:
    from app.models.code import Repository

    async with _code_service_context() as session:
        repo = (await session.execute(select(Repository).where(Repository.name == repo_name))).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")

        rows = (await session.execute(
            text("""
                SELECT key, label, properties
                FROM code_graph_nodes
                WHERE repo_id = :repo_id AND kind = 'community'
                ORDER BY label
            """),
            {"repo_id": str(repo.id)},
        )).mappings().all()

    communities = [
        {
            "key": r["key"],
            "label": r["label"],
            "size": (r["properties"] or {}).get("size") if r["properties"] else None,
        }
        for r in rows
    ]
    return json.dumps(communities)


@mcp.tool(description="List execution flow processes traced from route and tool entry points.")
async def code_processes(repo_name: str) -> str:
    from app.models.code import Repository

    async with _code_service_context() as session:
        repo = (await session.execute(select(Repository).where(Repository.name == repo_name))).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")

        process_rows = (await session.execute(
            text("""
                SELECT n.key, n.label, n.properties
                FROM code_graph_nodes n
                WHERE n.repo_id = :repo_id AND n.kind = 'process'
                ORDER BY n.label
            """),
            {"repo_id": str(repo.id)},
        )).mappings().all()

        processes = []
        for p in process_rows:
            meta = p["properties"] or {}
            step_rows = (await session.execute(
                text("""
                    SELECT source_key
                    FROM code_edges
                    WHERE repo_id = :repo_id
                      AND target_key = :proc_key
                      AND edge_type = 'step_in_process'
                """),
                {"repo_id": str(repo.id), "proc_key": p["key"]},
            )).mappings().all()
            steps = [r["source_key"].split("::")[0] for r in step_rows]
            processes.append({
                "name": p["label"] or p["key"],
                "kind": meta.get("entry_kind"),
                "entry_file": meta.get("entry_file"),
                "steps": steps,
            })

    return json.dumps(processes)


@mcp.tool(description="Find all references to a symbol for cross-file rename. Returns locations and confidence.")
async def code_rename(
    symbol_name: str,
    repo_name: str,
) -> str:
    """
    Args:
        symbol_name: Name of the symbol to rename.
        repo_name: Repository name.
    """
    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        repo = (await session.execute(select(Repository).where(Repository.name == repo_name))).scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository '{repo_name}' not found")

        definitions = (await session.execute(
            select(CodeSymbol, CodeFile.file_path).join(CodeFile).where(
                CodeFile.repo_id == repo.id,
                CodeSymbol.name == symbol_name,
            )
        )).all()

        if not definitions:
            raise ValueError(f"Symbol '{symbol_name}' not found")

        references = []
        for sym, fp in definitions:
            references.append({
                "file_path": fp,
                "line": sym.line_start,
                "kind": "definition",
                "symbol_kind": sym.kind,
                "confidence": 1.0,
            })

        repo_id_str = str(repo.id)

        # Call references
        call_rows = (await session.execute(
            text("""
                SELECT source_key, properties
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'calls'
                  AND (target_key = :sym_name OR target_key LIKE :sym_prefix)
            """),
            {
                "repo_id": repo_id_str,
                "sym_name": symbol_name,
                "sym_prefix": f"{symbol_name}::%",
            },
        )).mappings().all()
        for r in call_rows:
            src = r["source_key"]
            caller_name, caller_fp = decompose_key("symbol", src) if "::" in src else (src, None)
            props = r["properties"] or {}
            references.append({
                "file_path": caller_fp,
                "line": props.get("line"),
                "kind": "call",
                "caller": caller_name,
                "confidence": props.get("confidence", 0.5),
            })

        # Heritage references (extends/implements)
        heritage_rows = (await session.execute(
            text("""
                SELECT source_key, edge_type
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type IN ('extends', 'implements')
                  AND (target_key = :sym_name OR target_key LIKE :sym_prefix)
            """),
            {
                "repo_id": repo_id_str,
                "sym_name": symbol_name,
                "sym_prefix": f"{symbol_name}::%",
            },
        )).mappings().all()
        for r in heritage_rows:
            src = r["source_key"]
            child_name, child_fp = decompose_key("symbol", src) if "::" in src else (src, None)
            references.append({
                "file_path": child_fp,
                "line": None,
                "kind": "heritage",
                "symbol": child_name,
                "confidence": 0.95,
            })

        # Import references
        import_rows = (await session.execute(
            text("""
                SELECT source_key
                FROM code_edges
                WHERE repo_id = :repo_id
                  AND edge_type = 'imports'
                  AND target_key = :sym_name
            """),
            {"repo_id": repo_id_str, "sym_name": symbol_name},
        )).mappings().all()
        for r in import_rows:
            references.append({
                "file_path": r["source_key"],
                "line": 0,
                "kind": "import",
                "confidence": 0.8,
            })

    references.sort(key=lambda x: (-x.get("confidence", 0), x.get("file_path") or "", x.get("line") or 0))

    return json.dumps({
        "symbol": symbol_name,
        "total_references": len(references),
        "references": references,
    })
