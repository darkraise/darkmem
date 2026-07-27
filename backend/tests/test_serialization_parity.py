"""The MCP memory row is derived from MemoryResponse, and must stay derived.

``memory_to_dict`` and ``MemoryResponse`` are the two doors' views of one
memory row. They drifted seven fields apart once — ``status`` and
``superseded_by`` among them — so an MCP agent could not tell a superseded
memory from a live one, and could not see which project a memory came from.
These tests fail on the divergence itself, not on today's field list.
"""
from __future__ import annotations

import json
import uuid

import pytest

from app.models.memory import Memory
from app.schemas.memory import MemoryResponse
from app.utils import serialization
from app.utils.serialization import memory_to_dict


# The MCP wire keys that predate the reconciliation. Additive only: a rename or
# a removal here breaks shipped MCP clients. The ``llm_*`` keys in particular
# are a deliberate split from the ``classified_type``/``summary``/``emotions``/
# ``flags`` columns, retired by T1.42b and by nothing else.
_FROZEN_WIRE_KEYS = frozenset({
    "id", "content", "source", "source_agent", "memory_type", "importance",
    "metadata", "tags", "created_at", "updated_at", "expires_at",
    "is_archived", "llm_classified_type", "llm_summary", "llm_emotions",
    "llm_flags",
})


def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="placeholder",
        source="test",
        importance=0.5,
        metadata_={},
    )
    base.update(overrides)
    return Memory(**base)


def test_every_memory_response_field_is_resolvable():
    """The drift guard: no DB, no fixtures, just the two declarations.

    Adding a field to MemoryResponse without teaching the serializer where it
    comes from fails here, naming the field.
    """
    unresolved = [
        name
        for name in MemoryResponse.model_fields
        if name not in serialization._COMPUTED
        and not hasattr(Memory, serialization._ORM_ATTRS.get(name, name))
    ]
    assert not unresolved, (
        "MemoryResponse carries fields the MCP serializer cannot resolve: "
        f"{unresolved}. Give each one an entry in app/utils/serialization.py "
        "(_ORM_ATTRS for a renamed column, _COMPUTED otherwise). A field on "
        "the REST row and absent from the MCP row is exactly the drift that "
        "once hid supersession from every MCP reader."
    )


async def test_memory_to_dict_emits_every_memory_response_field(session):
    successor = _mem(content="parity successor")
    session.add(successor)
    await session.flush()

    memory = _mem(
        content="parity probe",
        source_agent="probe-agent",
        memory_type="fact",
        project="lane-f",
        status="superseded",
        superseded_by=successor.id,
        technologies=["postgres", "pgvector"],
        confidence=0.42,
    )
    session.add(memory)
    await session.flush()
    await session.refresh(memory)

    row = memory_to_dict(memory)

    assert set(row) == set(MemoryResponse.model_fields)
    # The MCP tools hand this straight to json.dumps.
    json.dumps(row)

    assert row["id"] == str(memory.id)
    assert row["project"] == "lane-f"
    assert row["status"] == "superseded"
    assert row["superseded_by"] == str(successor.id)
    assert row["technologies"] == ["postgres", "pgvector"]
    assert row["confidence"] == pytest.approx(0.42, rel=1e-6)
    assert row["related_memories"] is None
    assert row["trace"] is None


async def test_frozen_wire_keys_survive(session):
    memory = _mem(content="frozen key probe", memory_type="decision")
    session.add(memory)
    await session.flush()
    await session.refresh(memory)

    row = memory_to_dict(memory)

    missing = _FROZEN_WIRE_KEYS - set(row)
    assert not missing, f"MCP wire keys removed or renamed: {sorted(missing)}"
    assert row["memory_type"] == "decision"
    assert row["created_at"] == memory.created_at.isoformat()


async def test_trace_is_null_without_trace_work(session, monkeypatch):
    """`trace` is present for shape parity with the REST row, and costs nothing.

    T1.33 made the retrieval trace a with_trace-only path; an ordinary read of
    a memory must not assemble one. The row carries the key as null, the same
    as a REST read that did not ask for a trace.
    """
    import app.schemas.retrieval_trace as retrieval_trace

    def _explode(*args, **kwargs):
        raise AssertionError("an ordinary memory read must not build a trace")

    monkeypatch.setattr(retrieval_trace.MemoryResultTrace, "__init__", _explode)

    memory = _mem(content="trace probe")
    session.add(memory)
    await session.flush()
    await session.refresh(memory)

    assert memory_to_dict(memory)["trace"] is None
