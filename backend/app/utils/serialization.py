from datetime import datetime
from uuid import UUID

from app.schemas.memory import MemoryResponse

# MemoryResponse fields whose value does not come from an identically named
# attribute on the Memory row.
_ORM_ATTRS = {
    "metadata": "metadata_",
}

_COMPUTED = {
    "tags": lambda memory: [tag.name for tag in memory.tags],
    "technologies": lambda memory: list(memory.technologies or []),
    # Neither is carried by the memory row: crossrefs are a second query and
    # the retrieval trace only exists under `with_trace`. A REST read leaves
    # both null as well, so emitting null keeps the two doors' rows the same
    # shape without making an ordinary read pay for either.
    "related_memories": lambda memory: None,
    "trace": lambda memory: None,
    # `MemoryService.get_memory` attaches `.predecessors` (never absent
    # there); every other caller's Memory row never sets it, so `hasattr`
    # tells "not computed for this read" (-> null) apart from "computed,
    # zero rows" (-> `[]`) — a plain `getattr(..., None)` cannot make that
    # distinction because `[]` and the missing-attribute default would look
    # identical. Reaches the MCP `memory_get` tool automatically, since it
    # calls the same `MemoryService.get_memory` REST's single-get route does.
    "predecessors": lambda memory: (
        [
            {
                "id": _jsonable(p.id),
                "content": p.content,
                "created_at": _jsonable(p.created_at),
                "status": p.status,
            }
            for p in memory.predecessors
        ]
        if hasattr(memory, "predecessors")
        else None
    ),
}


def _jsonable(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def memory_to_dict(memory) -> dict:
    """Convert a Memory ORM instance to a plain dict for API/MCP responses.

    The field list is read off ``MemoryResponse`` rather than restated here.
    A second hand-written list is what once let the MCP row drift seven fields
    behind the REST row, hiding ``status`` and ``superseded_by`` from every MCP
    reader — an agent could not tell a superseded memory from a live one.
    """
    row = {}
    for name in MemoryResponse.model_fields:
        computed = _COMPUTED.get(name)
        if computed is not None:
            row[name] = computed(memory)
        else:
            row[name] = _jsonable(getattr(memory, _ORM_ATTRS.get(name, name)))
    return row
