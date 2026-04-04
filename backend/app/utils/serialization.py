def memory_to_dict(memory) -> dict:
    """Convert a Memory ORM instance to a plain dict for API/MCP responses."""
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
