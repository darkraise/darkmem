import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from sqlalchemy import select, text

from app.api.mcp.client_identity import (
    FALLBACK_SOURCE,
    resolve_client_source,
    resolve_entry_identity,
    resolve_origin_key,
    resolve_source_agent,
)
from app.config import settings
from app.database import async_session_factory
from app.schemas.envelope import ENVELOPE_SCHEMA_VERSION
from app.schemas.memory import MemoryBatchCreate, MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService
from app.utils.graph_keys import compose_key, decompose_key

logger = logging.getLogger(__name__)

# DNS-rebinding protection. The SDK default only allows a localhost Host header,
# which 421-rejects LAN agents reaching the server by its IP. Rather than disable
# the check wholesale, allowlist the configured host(s): a real agent sends an
# allowed Host and passes, while a rebinding payload (Host: attacker-domain) is
# refused. Browser Origins are allowlisted to the same hosts (agents send none).
_LOCALHOST_HOSTS = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]


def build_transport_security(allowed_hosts_csv: str) -> TransportSecuritySettings:
    extra = [h.strip() for h in allowed_hosts_csv.split(",") if h.strip()]
    if "*" in extra:
        # Explicit opt-out: no Host validation. Use only on a fully trusted,
        # isolated network.
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = _LOCALHOST_HOSTS + extra
    origins = [f"http://{h}" for h in hosts] + [f"https://{h}" for h in hosts]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


mcp = FastMCP(
    "darkmem",
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
    instructions="",
    transport_security=build_transport_security(settings.mcp_allowed_hosts),
)

_pipeline = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


def refresh_mcp_instructions() -> None:
    """Push the current ``agent_instructions`` prompt onto the live MCP server.

    FastMCP exposes ``instructions`` only as a read-only property, so the
    low-level server attribute is the single writable path. The SDK reads it
    per request when building the initialize response, so calling this after a
    prompt edit makes the new text take effect without a restart.
    """
    from app.services import prompt as _prompt

    instructions = _prompt.get("agent_instructions")
    if instructions:
        mcp._mcp_server.instructions = instructions


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


def _ack_to_dict(ack) -> dict:
    """The buffered accept, serialised from ``CaptureAck`` rather than by hand.

    Hand-building it here is how the two doors' ack shapes drifted before:
    a field added to the schema reached REST and stopped at the MCP door.
    """
    return json.loads(ack.model_dump_json())


def _degraded(reason: str, **extra) -> dict:
    """Doc 12 §3's recoverable-unavailability shape.

    A caller error still **raises** — a bad UUID or a missing id is the
    caller's mistake, not a degradation, and returning one as a typed result
    would teach an agent to treat its own error as the server being down.
    """
    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "status": "unavailable",
        "reason": reason,
        **extra,
    }


def _clamp_limit(limit: int, default: int, maximum: int = _MAX_LIMIT) -> int:
    """The tool-side bound. ``maximum`` lets a surface whose REST twin declares
    its own cap clamp to that one constant instead of to a second copy of it.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, maximum))


@mcp.tool(
    description="Store a new memory in the knowledge system. Use this to save facts, decisions, preferences, debugging insights, infrastructure details, or any information worth remembering across sessions. The origin tool is auto-detected and recorded in 'source'. Buffered by default (Tier-A accept, doc 05 §2): returns immediately with the memory's final id while extraction/classification runs asynchronously. Pass wait_process=true to drive that processing inline instead, bounded by buffer_wait_timeout_seconds — the fully processed memory is returned when it settles in time, otherwise the same buffered ack."
)
async def memory_add(
    content: str,
    tags: list[str] | None = None,
    source: Annotated[str | None, Field(
        description="Origin tool. Auto-detected for known clients; pass a value only to override."
    )] = None,
    source_agent: str | None = None,
    memory_type: str | None = None,
    project: str | None = None,
    wait_process: bool = False,
    ctx: Context | None = None,
) -> str:
    """
    Args:
        content: The memory content to store. Be specific and include context.
        tags: Categorization tags using slash notation (e.g., "project/darkmem", "debug/root-cause", "infra/services").
        source: Origin tool. Auto-detected per request (X-Darkmem-Client header, then User-Agent); pass a value only to override. Falls back to "mcp".
        source_agent: Optional agent/session identifier; defaults to the caller's raw User-Agent.
        memory_type: One of fact, decision, preference, problem, architecture, reference, milestone, episodic, procedural. Aliases (e.g. "debug"→"problem") are normalized; unknown values fall back to "fact".
        project: Supersession scope (default "default"). Set this so REPLACES-based supersession can fire within the intended project; tags do NOT feed this.
        wait_process: If true, drive this capture's flush inline (bounded by buffer_wait_timeout_seconds) instead of only buffering it. Use when you need the memory queryable immediately; the default leaves extraction to run asynchronously.
    """
    async with _memory_service_context() as service:
        resolved_source = resolve_client_source(source, ctx)
        resolved_project = project or "default"
        data = MemoryCreate(
            content=content, tags=tags or [],
            source=resolved_source,
            source_agent=resolve_source_agent(source_agent, ctx),
            origin_key=resolve_origin_key(
                None, ctx, source=resolved_source, project=resolved_project,
            ),
            memory_type=memory_type, project=resolved_project,
        )
        result = await service.create_memory(data, api_key_id=None, wait_process=wait_process)
        if result.memory is not None:
            return json.dumps(_memory_to_dict(result.memory))
        return json.dumps(_ack_to_dict(result.ack))


@mcp.tool(
    description="Search stored memories by semantic query, tags, type, or source. Returns matching memories ranked by relevance. Use this to retrieve context before making decisions or to find previously stored knowledge."
)
async def memory_search(
    query: str | None = None,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    memory_type: str | None = None,
    source: Annotated[str | None, Field(
        description='Filter by origin tool, e.g. "claude-code", "codex", "dashboard", "api", "mcp". "mcp"/"api" also cover all writes from before attribution landed (2026-06).'
    )] = None,
    project: Annotated[str | None, Field(
        description="Restrict results to one project. Omit to search every project."
    )] = None,
    limit: int = 20,
    offset: int = 0,
    semantic_weight: float = 0.7,
) -> str:
    """
    Args:
        query: Natural language search query. Uses semantic search if available, falls back to text matching.
        tags_any: Return memories matching ANY of these tags.
        tags_all: Return memories matching ALL of these tags.
        memory_type: Filter by type: fact, decision, preference, problem, architecture, reference, milestone, episodic, procedural.
        source: Filter by origin tool (e.g., "claude-code", "codex", "dashboard", "api", "mcp"). "mcp"/"api" also cover all writes from before attribution landed (2026-06).
        project: Restrict results to one project (the same isolation key memory_add writes). Omit to search every project.
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
            memory_type=memory_type, source=source, project=project,
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
    # Only set fields the caller actually provided. Passing every arg (each
    # defaulting to None) would mark them "set" on the model, defeating the
    # service's exclude_unset guard and clobbering the omitted columns — nulling
    # the NOT NULL content (which also aborts before tags apply). ``tags=[]``
    # still clears tags, since only ``None`` means "omitted".
    fields: dict = {}
    if content is not None:
        fields["content"] = content
    if tags is not None:
        fields["tags"] = tags
    if memory_type is not None:
        fields["memory_type"] = memory_type
    async with _memory_service_context() as service:
        data = MemoryUpdate(**fields)
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
    description="Create multiple memories in a single operation. Each entry follows the same format as memory_add; entries without 'source' get the auto-detected origin tool. Buffered by default (one 202-style accept per entry, doc 05 §2); pass wait_process=true to drive the whole batch's flush inline as a single pipeline pass, bounded by buffer_wait_timeout_seconds."
)
async def memory_batch_add(
    entries: list[dict], wait_process: bool = False, ctx: Context | None = None,
) -> str:
    """
    Args:
        entries: List of memory objects (1-100), each with 'content' (required), and optional 'tags', 'source' (auto-detected when omitted), 'source_agent' (defaults to the caller's User-Agent), 'memory_type', 'project' (supersession scope).
        wait_process: If true, drive the whole batch's flush inline instead of only buffering it. Use when you need every memory queryable immediately.
    """
    # Resolve on the raw dicts, through the same helper the REST batch door
    # uses, so the two can never drift.
    resolved = [
        resolve_entry_identity(entry, ctx=ctx, fallback=FALLBACK_SOURCE)
        for entry in entries
    ]

    # Mirror the HTTP /memories/batch cap (MemoryBatchCreate: 1-100 entries)
    # so the MCP path cannot enqueue an unbounded batch.
    validated = MemoryBatchCreate(entries=resolved)

    # Delegate to the service so creation threads every field (notably
    # ``project``, the supersession scope) and runs the phased batch pipeline
    # once. Re-implementing creation here previously dropped ``project``,
    # landing every batch-added memory in 'default'.
    async with _memory_service_context() as service:
        results = await service.batch_create_memories(
            validated.entries, api_key_id=None, wait_process=wait_process,
        )
        return json.dumps([
            _memory_to_dict(r.memory) if r.memory is not None
            else _ack_to_dict(r.ack)
            for r in results
        ])


@mcp.tool(
    description="Ask a question and get an answer based on stored memories (RAG). Searches semantically for relevant memories, then uses an LLM to synthesize an answer with source citations."
)
async def memory_reason(
    question: str, limit: int = 10, project: str | None = None,
) -> str:
    """
    Args:
        question: The question to answer using stored knowledge.
        limit: Maximum number of source memories to consider (default: 10).
        project: Optional project to restrict the reasoning context to.
    """
    limit = _clamp_limit(limit, default=10)
    async with _memory_service_context() as service:
        result = await service.reason(question, limit=limit, project=project)
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
    description="Get a project-wide organizational overview of what the memory store contains, organized by topic. This is a map-reduce over precomputed topic reports, not a ranked search: use memory_search when you want the memories most relevant to a query, and this when you want to know what is in here at all. Carries no verification badge — it describes what is stored, it does not assert it is true. The per-topic reports are precomputed off the hot path, so the answer costs at most one model call and is cached until the topic set changes."
)
async def memory_overview(project: str = "default") -> str:
    """
    Args:
        project: The project to summarize (default "default"). The overview is always scoped to one project.
    """
    from app.services.memory_overview import OverviewUnavailable, get_overview

    async with _code_service_context() as session:
        llm = _pipeline.llm if _pipeline is not None else None
        try:
            result = await get_overview(session, llm, project)
        except OverviewUnavailable as exc:
            return json.dumps(_degraded(str(exc), project=project))
        return json.dumps(result.to_dict())


@mcp.tool(
    description="Get statistics about the memory system: total memories, tags, active sources, plus entity and relationship counts from the knowledge graph."
)
async def memory_stats() -> str:
    from app.repositories.graph import PostgresGraphRepository
    from app.services.analytics import AnalyticsService

    async with _code_service_context() as session:
        service = AnalyticsService(session, graph_repo=PostgresGraphRepository(session))
        stats = await service.get_stats()
        return json.dumps(stats)


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
    limit = _clamp_limit(limit, default=10)
    if not _pipeline or not _pipeline.llm:
        # Return a typed, machine-readable result rather than raising a tool
        # error so the MCP client can degrade gracefully (e.g. fall back to a
        # text search) instead of treating an unconfigured embedder as a crash.
        return json.dumps(_degraded("embedder not configured", results=[]))

    from app.models.code import Repository
    from app.services.code_query import CodeQueryService

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
        results = await CodeQueryService(session, llm=_pipeline.llm).search_code(
            query, limit, repo_id, language,
        )

    return json.dumps([
        {
            "file_path": r["file_path"],
            "symbol_name": r["symbol_name"],
            "chunk_content": r["chunk_content"],
            "language": r["language"],
            "repo_id": r["repo_id"],
            "line_start": r["line_start"],
            "line_end": r["line_end"],
            # The REST twin serialises the same fused value under the same key
            # (CodeSearchResult.score = rrf_score); emitting the raw semantic
            # distance here is what let the two doors rank the same query
            # differently.
            "score": r["rrf_score"],
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
    from app.services.code_query import CodeQueryService

    async with _code_service_context() as session:
        # Only the name-to-id resolution lives here; the traversal itself is the
        # REST twin's. Keeping a second copy of the recursive CTE is how this
        # tool silently lost the owner-qualified `key` the graph nodes are
        # addressed by while the REST door kept emitting it.
        query = select(CodeSymbol.id).join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        if repo_name:
            query = query.join(Repository, CodeFile.repo_id == Repository.id).where(Repository.name == repo_name)
        query = query.where(CodeSymbol.name == symbol_name)
        symbol_id = (await session.execute(query)).scalars().first()
        if symbol_id is None:
            raise ValueError(f"Symbol not found: {symbol_name}")

        result = await CodeQueryService(session).calculate_blast_radius(
            str(symbol_id), max_depth,
        )

    if result is None:
        raise ValueError(f"Symbol not found: {symbol_name}")
    return json.dumps(result)


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


# ---------------------------------------------------------------------------
# Vault tools — the agent's side of L2/L3 (doc 12 §3)
# ---------------------------------------------------------------------------
#
# Both tools spend the service the REST door spends and reshape nothing:
# ``fact_get`` serialises through ``FactDetailResponse``, the very model
# ``GET /api/v1/knowledge/facts/{fact_id}`` declares as its response, so the
# two doors cannot answer different shapes for one fact. Neither tool spells
# any part of the verification claim — ``fact_badge`` is its sole producer and
# the badge rides through whole.


@mcp.tool(
    description="Read one fact from the knowledge vault by its UUID: the subject/relation/object triple, its verification status and honest claim badge, the provenance groups behind that badge's distinct-origin count, the applies_when context labels, the bi-temporal belief window and the review state. Use this after knowledge_search or memory_search surfaces a fact id and you need the evidence behind it. The badge's claim is shown verbatim or not at all — never paraphrase it."
)
async def fact_get(fact_id: str) -> str:
    """
    Args:
        fact_id: The UUID of the fact to retrieve.
    """
    from app.schemas.facts import FactDetailResponse
    from app.services import facts_read

    fid = _validate_uuid(fact_id)
    async with _code_service_context() as session:
        item = await facts_read.get_fact(session, fid)
        if item is None:
            raise ValueError(f"Fact not found: {fact_id}")
        return FactDetailResponse.model_validate(item).model_dump_json()


@mcp.tool(
    description="Search the knowledge vault across epistemic layers at once: stored memories (L0) and lifted facts (L2), merged into one ranked list where every fact carries its verification badge and the memories that source it are nested under it. Use this instead of memory_search when you want what is believed rather than what was said, and read the envelope: it names which channels ran, which failed, and how many rows were excluded by a context conflict, so a degraded answer is never mistaken for an empty vault."
)
async def knowledge_search(
    query: str,
    project: str = "default",
    limit: int = 20,
    fuse: bool = False,
) -> str:
    """
    Args:
        query: Natural language query. Both layers are searched with it.
        project: The project to search (default "default"). Every channel scopes to it.
        limit: Maximum number of composed rows to return (default: 20). A fact and the memories nested under it count as one.
        fuse: Output shape (default false). False returns "sections" split by layer (memory / facts / articles), each internally ranked — doc 07 §5's stated default. True returns one ranked "rows" list instead. Both carry every row's layer and verification labels; only the presentation differs.
    """
    from app.schemas.knowledge import (
        KNOWLEDGE_SEARCH_DEFAULT_LIMIT,
        KNOWLEDGE_SEARCH_MAX_LIMIT,
        knowledge_search_response,
        knowledge_search_unavailable,
    )
    from app.services.layer_composition import (
        CompositionUnavailable,
        LayerCompositionService,
    )

    limit = _clamp_limit(
        limit,
        default=KNOWLEDGE_SEARCH_DEFAULT_LIMIT,
        maximum=KNOWLEDGE_SEARCH_MAX_LIMIT,
    )
    async with _code_service_context() as session:
        llm = _pipeline.llm if _pipeline is not None else None
        service = LayerCompositionService(llm, session)
        try:
            result = await service.search(query, project=project, limit=limit)
        except CompositionUnavailable as exc:
            # Every channel down is recoverable unavailability, not a caller
            # error: doc 12 §3 says say so in a typed envelope rather than
            # returning rows a client cannot tell from a genuine no-match.
            #
            # The typed class and not its ``RuntimeError`` base (T2.80). The
            # composition raises the base for its own defects — the grouping
            # fixpoint that stopped decreasing, a reranker that returned a
            # window of the wrong length — and catching those here served a
            # bug over a healthy vault as an outage, which is the
            # failed-versus-empty conflation this envelope exists to prevent,
            # pointed at the operator instead of at the code.
            return json.dumps({
                **_degraded(str(exc), project=project),
                **knowledge_search_unavailable(exc).model_dump(mode="json"),
            })
        return knowledge_search_response(result, fuse=fuse).model_dump_json()
