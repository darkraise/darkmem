import json
import logging
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.database import async_session_factory
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

mcp = FastMCP("darkmem", json_response=True, stateless_http=True, streamable_http_path="/")

_pipeline = None

def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


async def _get_service():
    session = async_session_factory()
    return MemoryService(session, pipeline=_pipeline), session


def _memory_to_dict(memory) -> dict:
    return {
        "id": str(memory.id),
        "content": memory.content,
        "source": memory.source,
        "source_agent": memory.source_agent,
        "memory_type": memory.memory_type,
        "importance": memory.importance,
        "tags": [t.name for t in memory.tags],
        "created_at": memory.created_at.isoformat(),
    }


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
    service, session = await _get_service()
    try:
        data = MemoryCreate(content=content, tags=tags, source=source, source_agent=source_agent, memory_type=memory_type)
        memory = await service.create_memory(data, api_key_id=None)
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        await session.rollback()
        raise RuntimeError(f"Failed to create memory: {e}") from e
    finally:
        await session.close()


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
    service, session = await _get_service()
    try:
        params = MemorySearchRequest(query=query, tags_any=tags_any, tags_all=tags_all, memory_type=memory_type, source=source, limit=limit)
        memories = await service.search_memories(params)
        return json.dumps([_memory_to_dict(m) for m in memories])
    except Exception as e:
        raise RuntimeError(f"Search failed: {e}") from e
    finally:
        await session.close()


@mcp.tool(
    description="Retrieve a specific memory by its UUID."
)
async def memory_get(memory_id: str) -> str:
    """
    Args:
        memory_id: The UUID of the memory to retrieve.
    """
    mid = _validate_uuid(memory_id)
    service, session = await _get_service()
    try:
        memory = await service.get_memory(mid)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        return json.dumps(_memory_to_dict(memory))
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to get memory: {e}") from e
    finally:
        await session.close()


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
    service, session = await _get_service()
    try:
        data = MemoryUpdate(content=content, tags=tags, memory_type=memory_type)
        memory = await service.update_memory(mid, data, api_key_id=None)
        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except ValueError:
        raise
    except Exception as e:
        await session.rollback()
        raise RuntimeError(f"Failed to update memory: {e}") from e
    finally:
        await session.close()


@mcp.tool(
    description="Permanently delete a memory and its associated vectors and graph entities."
)
async def memory_delete(memory_id: str) -> str:
    """
    Args:
        memory_id: The UUID of the memory to delete.
    """
    mid = _validate_uuid(memory_id)
    service, session = await _get_service()
    try:
        result = await service.delete_memory(mid, api_key_id=None)
        if not result:
            raise ValueError(f"Memory not found: {memory_id}")
        await session.commit()
        return json.dumps({"deleted": True, "memory_id": memory_id})
    except ValueError:
        raise
    except Exception as e:
        await session.rollback()
        raise RuntimeError(f"Failed to delete memory: {e}") from e
    finally:
        await session.close()


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
    service, session = await _get_service()
    try:
        results = []
        for entry in entries:
            data = MemoryCreate(**entry)
            memory = await service.create_memory(data, api_key_id=None)
            results.append(_memory_to_dict(memory))
        await session.commit()
        return json.dumps(results)
    except Exception as e:
        await session.rollback()
        raise RuntimeError(f"Batch add failed: {e}") from e
    finally:
        await session.close()


@mcp.tool(
    description="Ask a question and get an answer based on stored memories (RAG). Searches semantically for relevant memories, then uses an LLM to synthesize an answer with source citations."
)
async def memory_reason(question: str, limit: int = 10) -> str:
    """
    Args:
        question: The question to answer using stored knowledge.
        limit: Maximum number of source memories to consider (default: 10).
    """
    service, session = await _get_service()
    try:
        result = await service.reason(question, limit=limit)
        return json.dumps(result)
    except Exception as e:
        raise RuntimeError(f"Reasoning failed: {e}") from e
    finally:
        await session.close()


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
    service, session = await _get_service()
    try:
        results = await service.find_duplicates(mid, threshold)
        return json.dumps(results, default=str)
    except Exception as e:
        raise RuntimeError(f"Duplicate search failed: {e}") from e
    finally:
        await session.close()


@mcp.tool(
    description="Get statistics about the memory system: total memories, tags, active sources."
)
async def memory_stats() -> str:
    from sqlalchemy import func, select
    from app.models.memory import Memory, Tag

    session = async_session_factory()
    try:
        memory_count = (await session.execute(select(func.count()).select_from(Memory))).scalar()
        tag_count = (await session.execute(select(func.count()).select_from(Tag))).scalar()
        sources_result = await session.execute(select(Memory.source).distinct())
        sources = [r[0] for r in sources_result.all()]
        return json.dumps({"memories": memory_count, "tags": tag_count, "sources": sources})
    except Exception as e:
        raise RuntimeError(f"Failed to get stats: {e}") from e
    finally:
        await session.close()


@mcp.tool(
    description="List all tags with the number of memories in each. Useful for understanding how knowledge is categorized."
)
async def memory_tags() -> str:
    from app.repositories.relational import PostgresTagRepository

    session = async_session_factory()
    try:
        repo = PostgresTagRepository(session)
        tags_with_counts = await repo.get_with_counts()
        return json.dumps([{"name": t.name, "category": t.category, "count": c} for t, c in tags_with_counts])
    except Exception as e:
        raise RuntimeError(f"Failed to list tags: {e}") from e
    finally:
        await session.close()
