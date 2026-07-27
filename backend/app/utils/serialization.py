def memory_to_dict(memory) -> dict:
    """Convert a Memory ORM instance to a plain dict for API/MCP responses."""
    return {
        "id": str(memory.id),
        "content": memory.content,
        "source": memory.source,
        "source_agent": memory.source_agent,
        "memory_type": memory.memory_type,
        "importance": memory.importance,
        "metadata": memory.metadata_,
        "tags": [t.name for t in memory.tags],
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
        "is_archived": memory.is_archived,
        "llm_classified_type": memory.classified_type,
        "llm_summary": memory.summary,
        "llm_emotions": memory.emotions,
        "llm_flags": memory.flags,
    }
