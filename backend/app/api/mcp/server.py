import json
import logging
import os
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from app.api.auth import hash_api_key
from app.database import async_session_factory
from app.repositories.relational import PostgresApiKeyRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

mcp = FastMCP("darkmem", json_response=True, stateless_http=True, streamable_http_path="/")

# Module-level reference set during app lifespan
_pipeline = None

_mcp_api_key: str | None = os.environ.get("MCP_API_KEY")


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


async def _get_mcp_api_key_id() -> UUID | None:
    """Get the API key ID for MCP operations, validating MCP_API_KEY if configured."""
    if not _mcp_api_key:
        return None
    session = async_session_factory()
    try:
        key_hash = hash_api_key(_mcp_api_key)
        repo = PostgresApiKeyRepository(session)
        api_key = await repo.get_by_key_hash(key_hash)
        return api_key.id if api_key else None
    finally:
        await session.close()


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


@mcp.tool(description="Create a new memory")
async def memory_add(content: str, tags: list[str] = [], source: str = "mcp", source_agent: str | None = None, memory_type: str | None = None) -> str:
    api_key_id = await _get_mcp_api_key_id()
    service, session = await _get_service()
    try:
        data = MemoryCreate(content=content, tags=tags, source=source, source_agent=source_agent, memory_type=memory_type)
        memory = await service.create_memory(data, api_key_id=api_key_id)
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Search memories by query, tags, or filters")
async def memory_search(query: str | None = None, tags_any: list[str] | None = None, tags_all: list[str] | None = None, memory_type: str | None = None, source: str | None = None, limit: int = 20) -> str:
    service, session = await _get_service()
    try:
        params = MemorySearchRequest(query=query, tags_any=tags_any, tags_all=tags_all, memory_type=memory_type, source=source, limit=limit)
        memories = await service.search_memories(params)
        return json.dumps([_memory_to_dict(m) for m in memories])
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Get a memory by ID")
async def memory_get(memory_id: str) -> str:
    service, session = await _get_service()
    try:
        memory = await service.get_memory(UUID(memory_id))
        if not memory:
            return json.dumps({"error": "Memory not found"})
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Update a memory")
async def memory_update(memory_id: str, content: str | None = None, tags: list[str] | None = None, memory_type: str | None = None) -> str:
    api_key_id = await _get_mcp_api_key_id()
    service, session = await _get_service()
    try:
        data = MemoryUpdate(content=content, tags=tags, memory_type=memory_type)
        memory = await service.update_memory(UUID(memory_id), data, api_key_id=api_key_id)
        if not memory:
            return json.dumps({"error": "Memory not found"})
        await session.commit()
        return json.dumps(_memory_to_dict(memory))
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Delete a memory")
async def memory_delete(memory_id: str) -> str:
    api_key_id = await _get_mcp_api_key_id()
    service, session = await _get_service()
    try:
        result = await service.delete_memory(UUID(memory_id), api_key_id=api_key_id)
        await session.commit()
        return json.dumps({"deleted": result})
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Create multiple memories at once")
async def memory_batch_add(entries: list[dict]) -> str:
    api_key_id = await _get_mcp_api_key_id()
    service, session = await _get_service()
    try:
        results = []
        for entry in entries:
            data = MemoryCreate(**entry)
            memory = await service.create_memory(data, api_key_id=api_key_id)
            results.append(_memory_to_dict(memory))
        await session.commit()
        return json.dumps(results)
    except Exception as e:
        await session.rollback()
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Ask a question about stored knowledge (RAG)")
async def memory_reason(question: str, limit: int = 10) -> str:
    service, session = await _get_service()
    try:
        result = await service.reason(question, limit=limit)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Find near-duplicate memories")
async def memory_find_duplicates(memory_id: str, threshold: float = 0.9) -> str:
    service, session = await _get_service()
    try:
        results = await service.find_duplicates(UUID(memory_id), threshold)
        return json.dumps(results, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="Get memory system statistics")
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
        return json.dumps({"error": str(e)})
    finally:
        await session.close()


@mcp.tool(description="List all tags with memory counts")
async def memory_tags() -> str:
    from app.repositories.relational import PostgresTagRepository

    session = async_session_factory()
    try:
        repo = PostgresTagRepository(session)
        tags_with_counts = await repo.get_with_counts()
        return json.dumps([{"name": t.name, "category": t.category, "count": c} for t, c in tags_with_counts])
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await session.close()
