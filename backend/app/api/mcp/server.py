import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.database import async_session_factory
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

mcp = FastMCP("darkmem", json_response=True, stateless_http=True, streamable_http_path="/", instructions="")

_pipeline = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


@asynccontextmanager
async def _memory_service_context():
    session = async_session_factory()
    try:
        yield MemoryService(session, pipeline=_pipeline)
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            await session.close()
        except Exception:
            pass


from app.utils.serialization import memory_to_dict as _memory_to_dict


def _validate_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid UUID format: {value}")


@mcp.tool(
    description="Store a new memory in the knowledge system. Use this to save facts, decisions, preferences, debugging insights, infrastructure details, or any information worth remembering across sessions."
)
async def memory_add(
    content: str,
    tags: list[str] = [],
    source: str = "mcp",
    source_agent: str | None = None,
    memory_type: str | None = None,
) -> str:
    """
    Args:
        content: The memory content to store. Be specific and include context.
        tags: Categorization tags using slash notation (e.g., "project/darkmem", "debug/root-cause", "infra/services").
        source: Origin identifier (default: "mcp").
        source_agent: Optional agent/session identifier.
        memory_type: Classification: fact, decision, preference, debug, architecture, workflow, or session.
    """
    async with _memory_service_context() as service:
        data = MemoryCreate(content=content, tags=tags, source=source, source_agent=source_agent, memory_type=memory_type)
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
) -> str:
    """
    Args:
        query: Natural language search query. Uses semantic search if available, falls back to text matching.
        tags_any: Return memories matching ANY of these tags.
        tags_all: Return memories matching ALL of these tags.
        memory_type: Filter by type: fact, decision, preference, debug, architecture, workflow, session.
        source: Filter by origin (e.g., "claude-code", "mcp", "api").
        limit: Maximum number of results (default: 20).
    """
    async with _memory_service_context() as service:
        params = MemorySearchRequest(query=query, tags_any=tags_any, tags_all=tags_all, memory_type=memory_type, source=source, limit=limit)
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
    description="Create multiple memories in a single operation. Each entry follows the same format as memory_add."
)
async def memory_batch_add(entries: list[dict]) -> str:
    """
    Args:
        entries: List of memory objects, each with 'content' (required), and optional 'tags', 'source', 'source_agent', 'memory_type'.
    """
    if not entries:
        raise ValueError("entries list cannot be empty")
    async with _memory_service_context() as service:
        results = []
        for entry in entries:
            data = MemoryCreate(**entry)
            memory = await service.create_memory(data, api_key_id=None)
            results.append(_memory_to_dict(memory))
        return json.dumps(results)


@mcp.tool(
    description="Ask a question and get an answer based on stored memories (RAG). Searches semantically for relevant memories, then uses an LLM to synthesize an answer with source citations."
)
async def memory_reason(question: str, limit: int = 10) -> str:
    """
    Args:
        question: The question to answer using stored knowledge.
        limit: Maximum number of source memories to consider (default: 10).
    """
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
    from sqlalchemy import func, select

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
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            await session.close()
        except Exception:
            pass


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
    if not _pipeline or not _pipeline.llm or not _pipeline.vector_repo:
        return json.dumps({"error": "Pipeline not initialized"})

    from qdrant_client.models import FieldCondition, Filter, MatchValue
    from sqlalchemy import select

    from app.models.code import Repository

    query_vector = await _pipeline.llm.embed(query)

    conditions = []
    if repo_name:
        async with _code_service_context() as session:
            repo = (await session.execute(
                select(Repository).where(Repository.name == repo_name)
            )).scalar_one_or_none()
            if not repo:
                return json.dumps({"error": f"Repository not found: {repo_name}"})
            conditions.append(FieldCondition(key="repo_id", match=MatchValue(value=str(repo.id))))
    if language:
        conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))

    query_filter = Filter(must=conditions) if conditions else None

    results = await _pipeline.vector_repo.client.query_points(
        collection_name="code_chunks",
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    )

    return json.dumps([
        {
            "file_path": p.payload.get("file_path", ""),
            "symbol_name": p.payload.get("symbol_name"),
            "chunk_content": p.payload.get("chunk_content", ""),
            "language": p.payload.get("language"),
            "line_start": p.payload.get("line_start", 0),
            "line_end": p.payload.get("line_end", 0),
            "score": p.score,
        }
        for p in results.points
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
    from sqlalchemy import select

    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        query = select(CodeSymbol).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == name)
        rows = (await session.execute(query)).scalars().all()

        if not rows:
            return json.dumps({"error": f"Symbol not found: {name}"})

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
    from sqlalchemy import select

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
    if not _pipeline or not _pipeline.graph_repo:
        return json.dumps({"error": "Graph service not initialized"})

    from sqlalchemy import select

    from app.models.code import CodeFile, CodeSymbol, Repository

    async with _code_service_context() as session:
        query = select(CodeSymbol).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == symbol_name)
        sym = (await session.execute(query)).scalars().first()

        if not sym:
            return json.dumps({"error": f"Symbol not found: {symbol_name}"})

        file = sym.file
        repo_id = str(file.repo_id) if file else ""

    depth = int(max_depth)
    async with _pipeline.graph_repo.driver.session() as neo:
        result = await neo.run(
            f"""
            MATCH (start:CodeSymbol {{name: $name, repo_id: $repo_id}})
            MATCH (caller:CodeSymbol)-[:CALLS*1..{depth}]->(start)
            WHERE caller <> start AND caller.repo_id = $repo_id
            RETURN DISTINCT caller.name AS name, caller.kind AS kind, caller.file_path AS file_path
            """,
            name=sym.name,
            repo_id=repo_id,
        )
        records = [r async for r in result]

    affected = [
        {"name": r["name"], "kind": r["kind"], "file_path": r["file_path"]}
        for r in records
    ]

    return json.dumps({
        "symbol": {
            "id": str(sym.id),
            "name": sym.name,
            "file_path": file.file_path if file else "",
        },
        "affected": affected,
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
    if not _pipeline or not _pipeline.graph_repo:
        return json.dumps({"error": "Graph service not initialized"})

    from sqlalchemy import select

    from app.models.code import Repository

    async with _code_service_context() as session:
        repo = (await session.execute(
            select(Repository).where(Repository.name == repo_name)
        )).scalar_one_or_none()
        if not repo:
            return json.dumps({"error": f"Repository not found: {repo_name}"})
        repo_id = str(repo.id)

    async with _pipeline.graph_repo.driver.session() as neo:
        if file_path:
            result = await neo.run(
                """
                MATCH (f:CodeFile {repo_id: $repo_id, file_path: $file_path})-[r:IMPORTS]->(m:Module)
                RETURN f.file_path AS file, m.name AS module, r.names AS names
                """,
                repo_id=repo_id,
                file_path=file_path,
            )
        else:
            result = await neo.run(
                """
                MATCH (f:CodeFile {repo_id: $repo_id})-[r:IMPORTS]->(m:Module)
                RETURN f.file_path AS file, m.name AS module, r.names AS names
                """,
                repo_id=repo_id,
            )
        records = [r async for r in result]

    return json.dumps([
        {"file": r["file"], "module": r["module"], "names": r["names"]}
        for r in records
    ])
