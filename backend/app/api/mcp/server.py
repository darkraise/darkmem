import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from sqlalchemy import select, text

from app.api.mcp.auth import ApiKeyTokenVerifier, current_api_key_id, current_key_name
from app.api.mcp.client_identity import (
    FALLBACK_SOURCE,
    declared_origin,
    resolve_client_source,
    resolve_entry_identity,
    resolve_origin_key,
    resolve_source_agent,
)
from app.api.mcp.scopes import ToolScopeMiddleware
from app.config import settings
from app.database import async_session_factory
from app.schemas.envelope import ENVELOPE_SCHEMA_VERSION
from app.schemas.memory import MemoryBatchCreate, MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.schemas.research import MAX_FINDINGS_CEILING, ResearchFindingInput
from app.services.document_door import SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT
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


# `issuer_url` is a required field on `AuthSettings` and darkmem issues no
# OAuth tokens: the credential is a static API key the operator mints. Nothing
# serves this URL - `create_auth_routes` needs an `auth_server_provider` and
# `create_protected_resource_routes` needs a `resource_server_url`, and this
# door has neither - but the SDK refuses a `token_verifier` with no
# `AuthSettings` at all, so the block exists to turn bearer verification on.
# `required_scopes` stays empty on purpose: the transport requires a *verified*
# key for every request, and which scope that key must hold is per tool, which
# a route-wide list cannot express. `ToolScopeMiddleware` decides that.
_MCP_AUTH = AuthSettings(
    issuer_url="http://localhost",
    resource_server_url=None,
    required_scopes=[],
)

mcp = MCPServer(
    "darkmem",
    instructions="",
    auth=_MCP_AUTH,
    token_verifier=ApiKeyTokenVerifier(),
    middleware=[ToolScopeMiddleware()],
)

# v2 moved json_response/stateless_http/streamable_http_path/transport_security
# off the MCPServer constructor and onto streamable_http_app()'s own kwargs
# (https://py.sdk.modelcontextprotocol.io/v2/migration/). Centralised here so
# every streamable_http_app() call site (app boot, test fixtures) serves the
# same transport posture instead of re-declaring the literals.
def mcp_streamable_http_kwargs() -> dict:
    return {
        "streamable_http_path": "/",
        "json_response": True,
        "stateless_http": True,
        "transport_security": build_transport_security(settings.mcp_allowed_hosts),
    }

_pipeline = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


def refresh_mcp_instructions() -> None:
    """Push the current ``agent_instructions`` prompt onto the live MCP server.

    ``MCPServer.instructions`` is a read-only property backed by the v2
    lowlevel ``Server``, so ``_lowlevel_server.instructions`` is the single
    writable path. The SDK reads it per request when building the initialize
    response, so calling this after a prompt edit makes the new text take
    effect without a restart.
    """
    from app.services import prompt as _prompt

    instructions = _prompt.get("agent_instructions")
    if instructions:
        mcp._lowlevel_server.instructions = instructions


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
    description="Store a new memory in the knowledge system. Use this to save facts, decisions, preferences, debugging insights, infrastructure details, or any information worth remembering across sessions. One memory holds ONE fact, in 1-3 sentences: several facts belong in several entries via memory_batch_add, and a long write-up belongs in document_put. The origin tool is auto-detected and recorded in 'source'. Buffered by default (Tier-A accept, doc 05 §2): returns immediately with the memory's final id while extraction/classification runs asynchronously. Pass wait_process=true to drive that processing inline instead, bounded by buffer_wait_timeout_seconds — the fully processed memory is returned when it settles in time, otherwise the same buffered ack."
)
async def memory_add(
    content: Annotated[str, Field(
        description="The one fact to store, in 1-3 sentences (aim under ~500 characters). State the fact and why it holds; omit how you found it and any session narrative. Several facts means several entries via memory_batch_add, never one long memory - a memory is one embedding and supersession retires it whole, so a multi-topic row retrieves poorly and can never be superseded."
    )],
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
        content: The one fact to store, in 1-3 sentences. State the fact and why it holds; omit session narrative. Several facts means several entries (memory_batch_add), not one long memory.
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
        result = await service.create_memory(
            data, api_key_id=current_api_key_id(), wait_process=wait_process,
            # The authenticated key's name, not the client tool: `resolved_source`
            # (the tool that made the call) still rides `data.source`, stored on
            # the memory row and echoed in this event's own payload, so nothing
            # is lost by preferring the credential's identity here — it just
            # matches what `events.actor` already means on REST's keyed capture
            # door (`app/api/routes/memories.py`'s `user.actor`).
            actor=current_key_name() or resolved_source,
        )
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
    description=(
        "Retrieve one memory by its UUID, with its content, tags, type, "
        "project and enrichment fields. Use it when a search result or an "
        "earlier call gave you an id and you need the full row."
    )
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
    description=(
        "Revise a stored memory in place: its content, tags, or memory type. "
        "Editing content re-runs extraction, so the entity and relationship "
        "graph for that memory is rebuilt. Use it to correct a memory rather "
        "than adding a second one that contradicts the first. Replace the "
        "fact; never append to it — a new fact is a new memory, not a "
        "section bolted onto this one."
    )
)
async def memory_update(
    memory_id: str,
    content: str | None = None,
    tags: list[str] | None = None,
    memory_type: str | None = None,
    ctx: Context | None = None,
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
        # Prefer the authenticated key's name (parity with `events.actor` on
        # REST's keyed doors); fall back to the client-tool guess only when
        # the call carries no token, which cannot happen once every tool
        # requires a bearer key but keeps this honest if that ever changes.
        actor = current_key_name() or resolve_client_source(None, ctx)
        memory = await service.update_memory(
            mid, data, api_key_id=current_api_key_id(), actor=actor,
        )
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps(_memory_to_dict(memory))


@mcp.tool(
    description=(
        "Permanently delete a memory, its vectors, and the graph contributions "
        "it alone asserts; entities other memories still assert survive. This "
        "is not a content purge - the append-only events journal keeps its "
        "own record by design."
    )
)
async def memory_delete(memory_id: str, ctx: Context | None = None) -> str:
    """
    Args:
        memory_id: The UUID of the memory to delete.
    """
    mid = _validate_uuid(memory_id)
    async with _memory_service_context() as service:
        actor = current_key_name() or resolve_client_source(None, ctx)
        result = await service.delete_memory(mid, api_key_id=current_api_key_id(), actor=actor)
        if not result:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps({"deleted": True, "memory_id": memory_id})


@mcp.tool(
    description="Create multiple memories in a single operation - the right shape whenever a session produced several facts, which are several entries rather than one long memory. Each entry follows the same format as memory_add, one fact each; entries without 'source' get the auto-detected origin tool. Buffered by default (one 202-style accept per entry, doc 05 §2); pass wait_process=true to drive the whole batch's flush inline as a single pipeline pass, bounded by buffer_wait_timeout_seconds."
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
            validated.entries, api_key_id=current_api_key_id(), wait_process=wait_process,
            # Per-entry `source` (client tool) still rides each entry's own
            # `data.source` and this event's own payload; see memory_add.
            actor=current_key_name()
            or resolve_client_source(None, ctx, fallback=FALLBACK_SOURCE),
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
# Session checkpoints (T3.16) — the second door onto app.services.checkpoints
#
# Both verbs go through the same service the REST route calls. Invariant 17
# asks for two-door parity, and the only version of parity that survives a
# later change is the one where there is a single behaviour to change.
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "Save a session checkpoint: a compact summary and structured next "
        "steps for this agent run, keyed on origin_key. Operational notes, "
        "not vault knowledge — a checkpoint carries no verification badge."
    )
)
async def checkpoint_save(
    summary: str,
    origin_key: str | None = None,
    next_steps: list[str] | None = None,
    project: str = "default",
    ctx: Context | None = None,
) -> str:
    from app.schemas.checkpoint import CheckpointCreate
    from app.services import checkpoints as checkpoint_service

    # Validated through the same schema the REST door uses, so a payload one
    # door refuses is not a payload the other accepts — the bound is a
    # property of a checkpoint, not of a transport.
    body = CheckpointCreate(
        origin_key=origin_key,
        summary=summary,
        next_steps=list(next_steps or []),
        project=project,
    )
    # Resolved exactly as the REST twin resolves it, through doc 05 §2.1 --
    # and that means resolving `source` from this transport too, not passing
    # the door's fallback as a constant. A constant here is a second key space:
    # a client declaring `X-Darkmem-Client: codex` saved `codex:<id>` over REST
    # and `checkpoint:<id>` over MCP, so `checkpoint_latest` on one door
    # silently missed the other door's checkpoint.
    source = resolve_client_source(
        None, ctx, fallback=checkpoint_service.DOOR_SOURCE
    )
    origin = checkpoint_service.resolve_checkpoint_origin(
        body.origin_key or declared_origin(ctx),
        source=source,
        project=body.project,
    )
    async with async_session_factory() as session:
        try:
            row = await checkpoint_service.save_checkpoint(
                session,
                origin_key=origin,
                summary=body.summary,
                next_steps=body.bounded_steps(),
                project=body.project,
                actor=source,
            )
            payload = checkpoint_service.serialize(row)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps(payload)


@mcp.tool(
    description=(
        "Get the latest session checkpoint for an origin_key, or null when "
        "that run saved none."
    )
)
async def checkpoint_latest(
    origin_key: str | None = None,
    project: str = "default",
    ctx: Context | None = None,
) -> str:
    from app.services import checkpoints as checkpoint_service

    # Same ladder as the save above, for the same reason: a read resolving a
    # different source from the write can never find what the write stored.
    source = resolve_client_source(
        None, ctx, fallback=checkpoint_service.DOOR_SOURCE
    )
    resolved = checkpoint_service.resolve_checkpoint_origin(
        origin_key or declared_origin(ctx), source=source, project=project
    )
    async with async_session_factory() as session:
        row = await checkpoint_service.latest_checkpoint(
            session, origin_key=resolved, project=project
        )
        # `null` rather than an empty object, matching REST's 404: "saved
        # nothing" and "saved an empty note" are different answers and the
        # resume path branches on which one it got.
        return json.dumps(
            checkpoint_service.serialize(row) if row is not None else None
        )


# ---------------------------------------------------------------------------
# Document tools -- the MCP half of the document door (doc 16, spec 2026-08-23)
#
# Each one is a call into `app.services.document_door`, the same functions
# `api/routes/documents.py` serves, for the reason the checkpoint banner above
# states: two transports over one module, never two implementations. Session
# handling follows each service function's own stated commit posture --
# `put_document` commits internally, `delete_document` relies on this caller,
# and the read verbs commit nothing.
#
# The three verbs keyed on a document take `document_id` OR `(project, uri)`,
# and resolve it through `resolve_document_target` rather than through
# `_validate_uuid`: naming nothing, naming an unfiled uri and naming a
# vanished id are one answer to a caller, and this door's REST twin renders
# the same refusal as a 404 from the same producer. It raises rather than
# degrading, which is `_degraded`'s own rule -- a caller naming no document
# made a caller's mistake, and the server is not down.
# ---------------------------------------------------------------------------


@mcp.tool(
    description=(
        "File a markdown or plain-text document into darkmem, keyed on its "
        "repo-relative path. Re-filing the same path updates it in place. "
        "Returns the document id and how many blocks were filed and embedded."
    )
)
async def document_put(
    project: str,
    uri: str,
    content: str,
    title: str | None = None,
    source_type: str | None = None,
    expected_hash: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Args:
        project: Scope, the same key memory_add writes under.
        uri: Repo-relative path, e.g. "docs/plans/2026-08-23-thing.md".
        content: The file's text. The server never reads your filesystem.
        title: Optional; falls back to the document's first heading.
        source_type: Optional; inferred from the uri suffix.
        expected_hash: Optional compare-and-set -- file only if the document
            still holds this content_hash (the value a previous put or
            document_get echoed). Omit for last-writer-wins. A mismatch
            answers a `hash_conflict` envelope naming both hashes, never an
            error: the caller made no mistake, it lost a race.
    """
    from app.services.document_ingest import DocumentHashConflict
    from app.services.document_door import DocumentIsBlockFirst, put_document

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))

    # The same ladder every other capture tool resolves through, and for the
    # same reason: a constant here would be a second key space for the client
    # that declares itself.
    source = resolve_client_source(None, ctx)
    async with async_session_factory() as session:
        try:
            result = await put_document(
                session, _pipeline.llm,
                project=project, uri=uri, content=content,
                title=title, source_type=source_type, source=source,
                expected_hash=expected_hash,
            )
        except DocumentIsBlockFirst as exc:
            # A structured refusal, not a tool error (review M-4): its REST
            # twin is a 409, and an agent should be able to machine-read this
            # and switch to the block verbs rather than parse a traceback.
            await session.rollback()
            return json.dumps({
                "status": "direction_conflict",
                "document_uri": uri,
                "project": project,
                "reason": str(exc),
            })
        except DocumentHashConflict as exc:
            # A structured refusal rather than a tool error: the caller can
            # machine-read this, re-read the document and retry. Its REST twin
            # is a 409 carrying the same two hashes.
            await session.rollback()
            return json.dumps({
                "status": "hash_conflict",
                "document_uri": uri,
                "project": project,
                "expected_hash": exc.expected_hash,
                "current_hash": exc.current_hash,
            })
        except Exception:
            await session.rollback()
            raise
    return json.dumps(vars(result))


@mcp.tool(
    description=(
        "Search documents by meaning and get back the matching sections, not "
        "whole files. Each hit carries its document title, path and heading "
        "path. Use this before reading a spec or plan from disk."
    )
)
async def document_search(
    query: str,
    project: str,
    limit: int = SEARCH_DEFAULT_LIMIT,
    document_id: str | None = None,
) -> str:
    """
    Args:
        query: What you are looking for, in your own words.
        project: Scope. Required and never defaulted, matching the block
            channel, which refuses an omittable retrieval scope.
        limit: How many sections to return.
        document_id: Optional; confines the search to one document.
    """
    from app.services.document_door import search_sections

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", results=[]))

    limit = _clamp_limit(
        limit, default=SEARCH_DEFAULT_LIMIT, maximum=SEARCH_MAX_LIMIT,
    )
    async with async_session_factory() as session:
        hits = await search_sections(
            session, _pipeline.llm, query=query, project=project,
            limit=limit, document_id=document_id,
        )
    return json.dumps([vars(h) for h in hits])


@mcp.tool(
    description=(
        "List a document's headings with their levels and block ids. No body "
        "text. Name the document by document_id, or by the project and uri "
        "it was filed under."
    )
)
async def document_outline(
    document_id: str | None = None,
    project: str | None = None,
    uri: str | None = None,
) -> str:
    """
    Args:
        document_id: The document's id, if you have one.
        project: Scope, when naming the document by uri.
        uri: The repo-relative path it was filed under.
    """
    from app.services.document_door import document_outline as _outline
    from app.services.document_door import resolve_document_target

    async with async_session_factory() as session:
        target = await resolve_document_target(
            session, document_id=document_id, project=project, uri=uri,
        )
        nodes = await _outline(session, document_id=target)
    return json.dumps([vars(n) for n in nodes])


@mcp.tool(
    description=(
        "Fetch a document's blocks, or only the block ids named. Name the "
        "document by document_id, or by the project and uri it was filed "
        "under."
    )
)
async def document_get(
    document_id: str | None = None,
    block_ids: list[str] | None = None,
    project: str | None = None,
    uri: str | None = None,
    include_content: bool = False,
    include_hash: bool = False,
) -> str:
    """
    Args:
        document_id: The document's id, if you have one.
        block_ids: Optional; only these blocks, the drill-down after an
            outline. An empty list names zero blocks and returns zero.
        project: Scope, when naming the document by uri.
        uri: The repo-relative path it was filed under.
        include_content: Also return the document's verbatim filed source
            under `content`. The result becomes `{content, blocks}` instead
            of the bare block array -- one of the two flags that box this
            tool's reply, `include_hash` being the other, since a bare array
            has nowhere to carry a field. Off by default: the source can be a
            megabyte.
        include_hash: Also return the document's current `content_hash` under
            `content_hash`, to precondition a later block verb on. Boxes the
            reply the same way `include_content` does -- a bare array has
            nowhere to carry a field.
    """
    from app.services.document_door import (
        document_blocks,
        document_content,
        document_hash,
        resolve_document_target,
    )

    # Parsed here rather than handed to `CAST(:ids AS uuid[])`: the REST twin
    # declares `list[UUID]` and answers 422 for a malformed one, and this door
    # has to reach the same refusal by hand because a tool argument carries no
    # validation of its own. An unparsed id reaches asyncpg as a DataError with
    # a SQL traceback, which is the least readable thing this door can hand a
    # caller that is a machine. `None` stays `None`; `[]` names zero blocks.
    if block_ids is not None:
        block_ids = [str(_validate_uuid(str(block_id))) for block_id in block_ids]

    async with async_session_factory() as session:
        target = await resolve_document_target(
            session, document_id=document_id, project=project, uri=uri,
        )
        rows = await document_blocks(
            session, document_id=target, block_ids=block_ids,
        )
        # Inside the session block: the content read is a second statement on
        # the same connection, and the same service function the route calls.
        raw = (
            await document_content(session, document_id=target)
            if include_content
            else None
        )
        current_hash = (
            await document_hash(session, document_id=target)
            if include_hash
            else None
        )
    blocks = [vars(r) for r in rows]
    if include_content or include_hash:
        boxed: dict = {}
        if include_content:
            boxed["content"] = raw
        if include_hash:
            boxed["content_hash"] = current_hash
        boxed["blocks"] = blocks
        return json.dumps(boxed)
    return json.dumps(blocks)


@mcp.tool(
    description=(
        "Delete a document, its blocks and its vectors. Use when its file is "
        "gone. Name the document by document_id, or by the project and uri "
        "it was filed under."
    )
)
async def document_delete(
    document_id: str | None = None,
    project: str | None = None,
    uri: str | None = None,
) -> str:
    """
    Args:
        document_id: The document's id, if you have one.
        project: Scope, when naming the document by uri.
        uri: The repo-relative path it was filed under.
    """
    from app.services.document_door import (
        DocumentTargetUnresolved, delete_document, resolve_document_target,
    )

    async with async_session_factory() as session:
        # Resolved outside the rollback guard: naming no document writes
        # nothing, so there is nothing for a rollback to undo and the raise
        # leaves the session as it found it.
        target = await resolve_document_target(
            session, document_id=document_id, project=project, uri=uri,
        )
        try:
            # Never a raw DELETE: the shared service is where a delete's
            # shape is decided, so both doors remove the same rows rather
            # than one door growing its own. It relies on this caller to
            # commit.
            if not await delete_document(session, document_id=target):
                raise DocumentTargetUnresolved("document not found")
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return json.dumps({"document_id": target, "deleted": True})


@mcp.tool(
    description=(
        "Edit a document's metadata, or rename a whole subtree. Name a "
        "document_id to retitle, move, pin or re-tag one document; name a "
        "project plus uri_prefix and new_uri_prefix to rewrite that prefix "
        "across every document under it. Never both."
    )
)
async def document_update(
    document_id: str | None = None,
    title: str | None = None,
    uri: str | None = None,
    pinned: bool | None = None,
    tags: list[str] | None = None,
    project: str | None = None,
    uri_prefix: str | None = None,
    new_uri_prefix: str | None = None,
) -> str:
    """
    Args:
        document_id: The single-document mode's address, from document_get.
        title: Optional new title.
        uri: Optional new path. Onto an occupied path this refuses.
        pinned: Optional; true pins, false unpins.
        tags: Optional; replaces the document's tag set rather than merging.
        project: Scope, for the subtree mode.
        uri_prefix: The prefix to rewrite, for the subtree mode.
        new_uri_prefix: What to rewrite it to.

    An omitted field writes no assignment at all, so a rename cannot silently
    unpin a document or strip its tags. `project` is not a single-document
    field: moving a document between spaces is not a rename.
    """
    from app.schemas.memory import validate_tag_lengths
    from app.services.document_door import (
        DocumentTargetUnresolved, DocumentUriConflict, rename_documents,
        update_document_metadata,
    )

    subtree = uri_prefix is not None or new_uri_prefix is not None
    if (document_id is None) == (not subtree):
        return json.dumps({
            "status": "invalid_mode",
            "reason": (
                "name a document_id, or a project with uri_prefix and "
                "new_uri_prefix -- never both and never neither"
            ),
        })
    if subtree and not (project and uri_prefix and new_uri_prefix):
        return json.dumps({
            "status": "invalid_mode",
            "reason": "the subtree mode needs project, uri_prefix and new_uri_prefix",
        })

    # A field belonging to the mode that was not selected is refused rather
    # than dropped. Silently ignoring it would answer `ok` for a call that
    # moved none of what the caller asked to move, and the REST twin forbids
    # extras outright -- a dropped key is a 422 there.
    stray = sorted(
        name for name, value in (
            (("project", project), ("uri_prefix", uri_prefix),
             ("new_uri_prefix", new_uri_prefix))
            if not subtree else
            (("title", title), ("uri", uri), ("pinned", pinned), ("tags", tags))
        )
        if value is not None
    )
    if stray:
        return json.dumps({
            "status": "invalid_mode",
            "reason": (
                f"{', '.join(stray)} belongs to the other mode; this call "
                "would have ignored it"
            ),
        })

    if document_id is not None:
        try:
            UUID(str(document_id))
        except ValueError:
            # Its REST twin refuses the same shape as a 422 on the path
            # parameter, before any handler runs.
            return json.dumps({
                "status": "unresolved",
                "reason": f"document_id is not a uuid: {document_id!r}",
            })

    # The `tags` table's own columns are the only guard below this door:
    # `get_or_create` validates nothing, so a name or a derived category
    # longer than its column reaches the driver as a DataError with no
    # savepoint under it -- a poisoned transaction rather than a refusal.
    # One shared validator with the capture and REST doors so they cannot
    # drift apart.
    validate_tag_lengths(tags)

    async with async_session_factory() as session:
        try:
            if subtree:
                renamed = await rename_documents(
                    session, project=project, uri_prefix=uri_prefix,
                    new_uri_prefix=new_uri_prefix,
                )
            else:
                await update_document_metadata(
                    session, document_id=document_id, title=title, uri=uri,
                    pinned=pinned, tags=tags,
                )
            await session.commit()
        except DocumentUriConflict as exc:
            # Structured refusals rather than tool errors, the shape the
            # block verbs already answer: the path is taken, or the document
            # is gone. Their REST twins are a 409 and a 404.
            await session.rollback()
            return json.dumps({"status": "uri_conflict", "reason": str(exc)})
        except DocumentTargetUnresolved as exc:
            await session.rollback()
            return json.dumps({"status": "unresolved", "reason": str(exc)})
        except Exception:
            await session.rollback()
            raise

    if subtree:
        return json.dumps({
            "status": "ok", "project": project, "renamed": renamed,
        })
    return json.dumps({"status": "ok", "document_id": document_id})


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
    description=(
        "Request an immediate reindex of named files in a repository, "
        "optionally verifying an expected commit sha first. Address the "
        "repository by its working-directory path or its name."
    )
)
async def code_reindex(
    repo_path: str | None = None,
    repo_name: str | None = None,
    files: list[str] | None = None,
    commit: str | None = None,
) -> str:
    """The first MCP write door into the code subsystem (spec §6.1).

    Args:
        repo_path: Working directory of the repository (matched against local_path).
        repo_name: Repository name, if the path is not known.
        files: Repository-relative paths the caller changed.
        commit: Expected HEAD sha; the call is refused if darkmem is elsewhere.

    ``prepare_reindex`` journals only its own refusals (spec §1's shared entry
    point); every path here that it does not already cover -- an unresolved or
    ambiguous repository reference, no embedder configured, claim loss, or a
    scheduling failure -- journals its own outcome exactly once, mirroring
    ``reindex_repo_files``'s REST shape. The argument check below is the one
    branch that journals nothing, deliberately: it names no repository, so the
    row would carry neither an id nor a caller reference and would record
    nothing an operator could act on.
    """
    from pathlib import Path

    from app.models.code import Repository
    from app.services.reindex_request import (
        ReindexRefused, journal_reindex_outcome, prepare_reindex,
    )
    from app.services.repo_manager import RepoManager

    if not repo_path and not repo_name:
        raise ValueError("one of repo_path or repo_name is required")

    # The raw caller-supplied count, not `accepted.union_files` -- the same
    # choice `reindex_repo_files` makes, so a caller comparing audit rows
    # across doors sees one counting convention.
    file_count = len(files or [])
    actor = current_key_name()
    api_key_id = current_api_key_id()

    async def _journal(repo_id: UUID | None, outcome: str) -> None:
        async with _code_service_context() as journal_session:
            await journal_reindex_outcome(
                journal_session, repo_id, outcome=outcome, file_count=file_count,
                commit=commit, actor=actor, api_key_id=api_key_id,
                source="reindex_mcp",
                # A resolution failure has no UUID to stamp, so without the
                # caller's own reference the row would name no repository at
                # all and record nothing an operator could act on. Carried on
                # every row, not only the id-less ones, so one door's audit
                # reads the same however the reference resolved.
                repo_path=repo_path, repo_name=repo_name,
            )

    async with _code_service_context() as session:
        if repo_path:
            resolved = str(Path(repo_path).expanduser().resolve())
            rows = (await session.execute(
                select(Repository).where(Repository.local_path == resolved)
            )).scalars().all()
        else:
            rows = (await session.execute(
                select(Repository).where(Repository.name == repo_name)
            )).scalars().all()

    if not rows:
        await _journal(None, "not_found")
        raise ValueError(f"Repository not found: {repo_path or repo_name}")
    if len(rows) > 1:
        # `name` and `local_path` carry no uniqueness, so this is reachable;
        # a scalar_one_or_none here would raise MultipleResultsFound at the
        # caller instead of naming the candidates.
        await _journal(None, "ambiguous_repo")
        raise ValueError(
            "Repository reference is ambiguous; pass one of these ids: "
            + ", ".join(str(r.id) for r in rows)
        )
    repo = rows[0]

    if _pipeline is None:
        # Guarded here, before any claim is taken: `_spawn_repo_index`
        # immediately dereferences `pipeline.vector_repo`, and `code_search`
        # in this same file returns a typed result rather than letting that
        # become an unhandled AttributeError on an instance with no embedder
        # configured.
        await _journal(repo.id, "embedder_not_configured")
        return json.dumps({"status": "refused", "reason": "embedder_not_configured"})

    async with _code_service_context() as session:
        try:
            accepted = await prepare_reindex(
                session, repo, files=files, commit=commit,
                actor=actor, api_key_id=api_key_id, source="reindex_mcp",
            )
        except ReindexRefused as refused:
            # `refused.detail` can itself carry a `status` key (the busy
            # precheck's `status=repo.status`) -- spread it first so this
            # tool's own "refused" marker always wins the collision rather
            # than being silently overwritten by the repo's git-side status.
            return json.dumps({
                **refused.detail,
                "status": "refused",
                "reason": refused.reason,
            })

    async with async_session_factory() as claim_session:
        claimed = await RepoManager(claim_session).claim_for_indexing(
            repo.id, message="Queued for indexing...",
        )
    if not claimed:
        await _journal(repo.id, "repo_busy")
        return json.dumps({"status": "refused", "reason": "repo_busy"})

    from app.api.routes.repos import _spawn_repo_index

    try:
        _spawn_repo_index(
            repo.id, _pipeline, async_session_factory,
            kind="reindex-files",
            union_files=accepted.union_files,
        )
    except Exception as exc:
        # The claim above already committed "indexing"; leaving the repo
        # wedged there with no task is worse than the REST door's own
        # recovery, which this mirrors.
        logger.error("Failed to schedule MCP reindex for %s: %s", repo.id, exc)
        async with _code_service_context() as error_session:
            error_repo = await error_session.get(Repository, repo.id)
            if error_repo is not None:
                error_repo.status = "error"
                error_repo.status_message = "Failed to start indexing"
        await _journal(repo.id, "spawn_failed")
        return json.dumps({"status": "refused", "reason": "spawn_failed"})

    await _journal(repo.id, "indexing")
    return json.dumps({
        "status": "indexing",
        "repo_id": str(repo.id),
        "commit": accepted.head,
        "accepted": len(accepted.union_files),
    })


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
    description=(
        "List every code symbol defined in one file - functions, classes, "
        "methods - in line order, with signatures. Use it to understand a "
        "file's structure before reading it, or to find the exact symbol name "
        "to pass to code_symbol or code_context."
    )
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


@mcp.tool(
    description=(
        "List the code communities Leiden clustering found in a repository - "
        "groups of symbols that call each other more than they call outward. "
        "Use it to learn a codebase's natural subsystem boundaries when you "
        "do not yet know what to search for."
    )
)
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


@mcp.tool(
    description=(
        "List the execution flows traced from a repository's entry points - "
        "each route or tool followed through the calls it makes. Use it to "
        "see how a request actually travels through the system rather than "
        "reconstructing the path one caller at a time."
    )
)
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
    description="Read one synthesised article from the knowledge vault by its UUID: the grounded prose, its verification status, the claim-support coverage (the fraction of its sentences a verified fact entails), the citations grounding each claim, whether it is stale, and both directions of its supersession lineage. Use this after knowledge_search surfaces an article id and you need the claims behind the prose. A stale article is still served: the label says its supporting facts changed since it was written, never that it is wrong."
)
async def article_get(article_id: str) -> str:
    """
    Args:
        article_id: The UUID of the article to retrieve.
    """
    from app.schemas.articles import ArticleDetailResponse
    from app.services import articles_read

    aid = _validate_uuid(article_id)
    async with _code_service_context() as session:
        item = await articles_read.get_article(session, aid)
        if item is None:
            raise ValueError(f"Article not found: {article_id}")
        return ArticleDetailResponse.model_validate(item).model_dump_json()


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


# ── The research door (doc 09 §6, T3.27) ──────────────────────────────────
#
# Why the F7 loop's one door is an MCP tool, and not a route, a job or a
# script.
#
# Doc 09 §6's flow is demand-driven — `Human->>Agent: research subject S into
# project P` — so the door has to carry a per-request subject. That rules out
# a job on its own: a cron expression carries no subject, and
# `job_registry.FieldDescriptor.default` is typed `int`, so a job's
# `config_schema` cannot carry one either.
#
# What picks MCP over REST is the gatherer. `ResearchGatherer` has no in-tree
# implementation by design, because a model without web access would invent
# its sources — so the door cannot *call* a gatherer, the caller has to *be*
# one. On MCP the caller is the web-capable agent that did the searching a
# moment ago: it hands over its own findings and their per-source locators,
# and the tool description delivers the origin-identity contract to the exact
# actor that can violate it. REST's callers are the SPA and the generated
# three-verb SDK, neither of which can gather, so the honest REST shape of
# "research subject S into project P" is a route that gathers server-side —
# the in-tree gatherer this design refuses — and the other REST shape, a body
# carrying findings someone else gathered, is a second capture door wearing a
# research label.
#
# The door adds no capability `/mcp` did not already have. Every row it files
# is *more* disclosed than one filed through `memory_add`, not less: the
# source is the reserved research kind and the origin_key is one
# `is_researched_origin` recognises, and neither is a parameter here, so a
# caller cannot file through this door while looking like ordinary capture.
# Building the door is not arming the loop either — it stays refused until
# the owner enables the config row.


class _SuppliedFindings:
    """The gatherer for a caller that has already gathered.

    Deliberately not a slice to ``limit``. A door that trimmed an over-budget
    call would file part of a research run and report it as filed, which is
    the truncated filing the loop refuses outright; handing every supplied
    finding back is what lets the budget refuse the whole run instead.
    """

    def __init__(self, findings: list):
        self._findings = findings

    async def gather(self, subject: str, *, limit: int) -> list:
        return self._findings


@mcp.tool(
    description="File research evidence YOU have already gathered into this project as one research run. This tool does not search or fetch anything: evidence gathering is your capability, not darkmem's, so do the searching with your own tools and hand the findings here. Give every finding the canonical locator of the source it actually came from in 'source_id' — corroboration counts distinct sources, so two findings from one page must carry the same source_id and two independent pages must carry different ones, and a finding whose source you cannot identify must leave it null so it merges into one anonymous origin rather than counting twice. Never split one page into several source_ids or paraphrase one page into two findings with different ones: that manufactures corroboration for a claim only one source made. Every row filed here is marked research-originated and cannot be filed as ordinary capture. Disabled by default — an install whose research config row is not enabled refuses the run and files nothing."
)
async def research_run(
    subject: str,
    project: str,
    # Bounded at the schema boundary, not only at runtime: an unauthenticated
    # door should refuse an oversized list before validating and materialising
    # it three times. The bound is the capture door's own ceiling, read off
    # `MemoryBatchCreate` rather than re-typed, so it cannot drift from the cap
    # the run is measured against. The configured budget is a further, lower
    # refusal — this only stops work no budget could ever authorise.
    findings: Annotated[
        list[ResearchFindingInput], Field(max_length=MAX_FINDINGS_CEILING),
    ],
) -> str:
    """
    Args:
        subject: What the evidence was gathered about. Recorded on every filed row and on the run's journal entry; it is not a search query and nothing is fetched for it.
        project: The project to file into. Required and never defaulted, so manufactured origins land where the caller asked for them rather than in "default" by omission.
        findings: The evidence you gathered, one entry per finding. Each is {"content": the finding's text, "source_id": the canonical URL or document id of the source it came from (null when you cannot establish it), "metadata": optional extra fields}. There is no 'source' or 'origin_key' field: this door stamps both, and sending either is an error rather than a silently ignored key.
    """
    from app.services.auto_research import (
        ResearchDisabled,
        ResearchFinding,
        run_research,
    )

    subject = (subject or "").strip()
    project = (project or "").strip()
    if not subject:
        raise ValueError("subject is required")
    if not project:
        raise ValueError("project is required")

    parsed = [ResearchFindingInput.model_validate(finding) for finding in findings]
    if not parsed:
        # An empty run would return a filed-shaped result with filed=0, which
        # reads to an agent as "stored" — the same reason the batch cap
        # refuses an empty batch rather than accepting it as a no-op.
        raise ValueError("findings must not be empty")

    gatherer = _SuppliedFindings([
        ResearchFinding(
            content=finding.content,
            source_id=finding.source_id,
            metadata=dict(finding.metadata),
        )
        for finding in parsed
    ])
    async with _memory_service_context() as service:
        try:
            result = await run_research(
                service.session,
                subject=subject,
                project=project,
                gatherer=gatherer,
                service=service,
            )
        except ResearchDisabled as exc:
            # An install that has not armed the loop is unavailability the
            # owner can recover, not a caller mistake: doc 12 §3's envelope
            # says so without teaching the agent it called wrong. A budget
            # refusal is the caller's mistake and still raises.
            return json.dumps(
                _degraded(str(exc), subject=subject, project=project, filed=0)
            )
        return json.dumps({
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "status": "filed",
            "run_id": str(result.run_id),
            "subject": result.subject,
            "project": result.project,
            "filed": result.filed,
            "memory_ids": [str(memory_id) for memory_id in result.memory_ids],
            "origins_manufactured": True,
            "journalled": result.journalled,
        })


# ── Block verbs (increment 8, spec §8) ───────────────────────────────
#
# The thin twins of the four REST routes, over the same `block_verbs`
# service. No `ctx`/`source` resolution: the verbs journal `blocks_edited`
# themselves, and the editor's identity question is the session's rather than
# a capture header's.
#
# Four refusals answer a structured envelope rather than a tool error, and in
# none of them did the caller make an avoidable mistake: it lost a race
# (`hash_conflict`), or it asked to edit a document the block model cannot
# represent (`not_convertible`), to move a block inside its own subtree
# (`cycle_refused`), or to address a block that is not where it said it was
# (`unresolved`). An agent can machine-read an envelope and choose; it cannot
# machine-read a traceback. Their REST twins are a 409, a 422, a 422 and a 404
# carrying the same reasons.


def _block_refusal(exc: Exception, **fields) -> str | None:
    from app.services.block_verbs import BlockCycleError, BlockTargetUnresolved
    from app.services.document_door import DocumentNotConvertible
    from app.services.document_ingest import DocumentHashConflict

    if isinstance(exc, DocumentHashConflict):
        # The caller lost a race rather than making a mistake, so it gets a
        # machine-readable outcome it can re-read and retry from. REST answers
        # the same refusal as a 409.
        return json.dumps({
            "status": "hash_conflict",
            "expected_hash": exc.expected_hash,
            "current_hash": exc.current_hash,
            **fields,
        })
    if isinstance(exc, DocumentNotConvertible):
        return json.dumps({"status": "not_convertible", "reason": str(exc), **fields})
    if isinstance(exc, BlockCycleError):
        return json.dumps({"status": "cycle_refused", "reason": str(exc), **fields})
    if isinstance(exc, BlockTargetUnresolved):
        return json.dumps({"status": "unresolved", "reason": str(exc), **fields})
    return None


@mcp.tool(
    description=(
        "Edit one block's text in a block-first document. The document "
        "converts on the first block verb, after which document_put refuses "
        "it. Send the block's markdown source as `text`."
    )
)
async def block_update(
    block_id: str,
    text: str,
    type: str | None = None,
    properties: dict | None = None,
    expected_hash: str | None = None,
) -> str:
    """
    Args:
        block_id: The block's id, from document_get.
        text: The block's new text, marker-stripped as document_get returns it.
        type: Optional; normalised through the closed block vocabulary.
        properties: Optional; merged over the block's existing properties.
        expected_hash: Optional; the document's `content_hash` as you last saw
            it, from document_get with include_hash. A mismatch refuses.
    """
    from app.services.block_verbs import update_block

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))
    async with async_session_factory() as session:
        try:
            result = await update_block(
                session, _pipeline.llm, block_id=block_id, text=text,
                type=type, properties=properties, expected_hash=expected_hash,
            )
        except Exception as exc:
            await session.rollback()
            refusal = _block_refusal(exc, block_id=block_id)
            if refusal is not None:
                return refusal
            raise
    return json.dumps(vars(result))


@mcp.tool(
    description=(
        "Insert a block into a document. First child of `parent_id` by "
        "default, or directly after `after_block_id` among that parent's "
        "children."
    )
)
async def block_insert(
    document_id: str,
    type: str,
    text: str,
    parent_id: str | None = None,
    after_block_id: str | None = None,
    properties: dict | None = None,
    expected_hash: str | None = None,
) -> str:
    """
    Args:
        document_id: The document to insert into.
        type: A block type; normalised through the closed vocabulary.
        text: The block's text.
        parent_id: Optional; omit for a root-level block.
        after_block_id: Optional; omit to insert as the first child.
        properties: Optional; a heading's level, a list item's marker.
        expected_hash: Optional; the document's `content_hash` as you last saw
            it, from document_get with include_hash. A mismatch refuses.
    """
    from app.services.block_verbs import insert_block

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))
    async with async_session_factory() as session:
        try:
            result = await insert_block(
                session, _pipeline.llm, document_id=document_id, type=type,
                text=text, parent_id=parent_id, after_block_id=after_block_id,
                properties=properties, expected_hash=expected_hash,
            )
        except Exception as exc:
            await session.rollback()
            refusal = _block_refusal(exc, document_id=document_id)
            if refusal is not None:
                return refusal
            raise
    return json.dumps(vars(result))


@mcp.tool(
    description=(
        "Move a block within its document, reparenting and repositioning it. "
        "Moving a block inside its own subtree is refused."
    )
)
async def block_move(
    block_id: str,
    new_parent_id: str | None = None,
    after_block_id: str | None = None,
    expected_hash: str | None = None,
) -> str:
    """
    Args:
        block_id: The block to move.
        new_parent_id: Optional; omit to move it to the root level.
        after_block_id: Optional; omit to make it the first child.
        expected_hash: Optional; the document's `content_hash` as you last saw
            it, from document_get with include_hash. A mismatch refuses.
    """
    from app.services.block_verbs import move_block

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))
    async with async_session_factory() as session:
        try:
            result = await move_block(
                session, _pipeline.llm, block_id=block_id,
                new_parent_id=new_parent_id, after_block_id=after_block_id,
                expected_hash=expected_hash,
            )
        except Exception as exc:
            await session.rollback()
            refusal = _block_refusal(exc, block_id=block_id)
            if refusal is not None:
                return refusal
            raise
    return json.dumps(vars(result))


@mcp.tool(
    description=(
        "Delete a block and everything nested under it. The block channel "
        "mints no fact, so nothing is withdrawn or expired elsewhere."
    )
)
async def block_delete(block_id: str, expected_hash: str | None = None) -> str:
    """
    Args:
        block_id: The block to delete. Its whole subtree goes with it.
        expected_hash: Optional; the document's `content_hash` as you last saw
            it, from document_get with include_hash. A mismatch refuses.
    """
    from app.services.block_verbs import delete_block

    if not _pipeline or not _pipeline.llm:
        return json.dumps(_degraded("embedder not configured", document_id=None))
    async with async_session_factory() as session:
        try:
            result = await delete_block(
                session, _pipeline.llm, block_id=block_id,
                expected_hash=expected_hash,
            )
        except Exception as exc:
            await session.rollback()
            refusal = _block_refusal(exc, block_id=block_id)
            if refusal is not None:
                return refusal
            raise
    return json.dumps(vars(result))
