"""``llm_fingerprint()``'s ``|0`` sentinel must never carry a bulk read (T2.68).

``LLMOrchestrator.llm_fingerprint()`` returns ``f"{model}|0"`` when the
embedding purpose's ``dimensions`` is unset — a legal, documented
configuration. Reading a partition keyed on that sentinel either raises
``UndefinedTable`` (nothing was ever registered under it) or, if some other
fingerprint happens to fold to the same slug, silently returns rows nothing
wrote — both worse than a named refusal. These tests pin
``PostgresVectorRepository.resolve_read_fingerprint`` and the
``/api/v1/vectors/projection`` route that must use it instead of the bare
``llm_fingerprint()`` read.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.api.routes.vectors import get_vector_projection
from app.models.memory import Memory
from app.repositories.vector import EmbedderFingerprintUnresolved, PostgresVectorRepository
from app.services.embedder_registry import child_table
from fastapi import HTTPException

pytestmark = pytest.mark.asyncio

MODEL_ID = "vectors-route-model"
REAL_FINGERPRINT = f"{MODEL_ID}|4"
SENTINEL_FINGERPRINT = f"{MODEL_ID}|0"
DIMS = 4
VECTOR = [1.0, 0.0, 0.0, 0.0]


class _SentinelLLM:
    """The shape both read paths receive under an unset ``dimensions`` config."""

    def llm_fingerprint(self) -> str:
        return SENTINEL_FINGERPRINT


class _FakeAppState:
    def __init__(self, llm):
        self.llm = llm


class _FakeApp:
    def __init__(self, llm):
        self.state = _FakeAppState(llm)


class _FakeRequest:
    def __init__(self, llm):
        self.app = _FakeApp(llm)


async def _register_real_fingerprint(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": REAL_FINGERPRINT, "mid": MODEL_ID, "dims": DIMS},
    )
    child = child_table("memory_embeddings", REAL_FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory_with_vector(session) -> uuid.UUID:
    memory_id = uuid.uuid4()
    session.add(Memory(
        id=memory_id, content="real vector under the real fingerprint", source="test",
        importance=0.5, metadata_={}, project="default", status="active",
        memory_type="decision", is_archived=False,
    ))
    await session.flush()
    child = child_table("memory_embeddings", REAL_FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {"mid": memory_id, "fp": REAL_FINGERPRINT, "vec": str(VECTOR), "payload": '{"content": "x"}'},
    )
    await session.flush()
    return memory_id


# ── the repository-level resolver ───────────────────────────────────────


async def test_resolve_read_fingerprint_passes_through_a_real_fingerprint(session):
    class _RealLLM:
        def llm_fingerprint(self) -> str:
            return REAL_FINGERPRINT

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_RealLLM())
    assert resolved == REAL_FINGERPRINT


async def test_resolve_read_fingerprint_finds_the_real_partition_behind_the_sentinel(session):
    """Dimensions cleared after a real embed already registered the model:
    the sentinel must resolve to the fingerprint that actually has data,
    never proceed keyed on ``|0``."""
    await _register_real_fingerprint(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_SentinelLLM())

    assert resolved == REAL_FINGERPRINT
    assert resolved != SENTINEL_FINGERPRINT


async def test_resolve_read_fingerprint_raises_when_nothing_is_registered(session):
    """Fresh config, dimensions unset, no embed has ever run for this model:
    there is no partition to read, so this must refuse loudly rather than
    hand back the sentinel for a caller to read empty forever."""
    with pytest.raises(EmbedderFingerprintUnresolved):
        await PostgresVectorRepository(session).resolve_read_fingerprint(_SentinelLLM())


# ── reproduced on unmodified code: what a bare sentinel read actually does ──


async def test_unmodified_bare_sentinel_read_raises_undefined_table(session):
    """Documents the defect this task closes: a naive ``get_all_vectors`` call
    keyed directly on the sentinel does not return an empty, well-formed
    result — it blows up on a relation Postgres has never heard of, which is
    the raw material the fixed read paths must never expose to a caller."""
    repo = PostgresVectorRepository(session)
    with pytest.raises(Exception) as exc_info:
        await repo.get_all_vectors(fingerprint=SENTINEL_FINGERPRINT, limit=10)
    assert "does not exist" in str(exc_info.value) or "UndefinedTable" in str(exc_info.value)


# ── the route ─────────────────────────────────────────────────────────────


async def test_projection_route_refuses_loudly_under_an_unresolved_sentinel(session):
    with pytest.raises(HTTPException) as exc_info:
        await get_vector_projection(
            limit=500, project=None, status=["active"], _user=None,
            request=_FakeRequest(_SentinelLLM()), session=session,
        )
    assert exc_info.value.status_code == 503
    assert MODEL_ID in exc_info.value.detail


async def test_projection_route_serves_real_points_when_the_sentinel_resolves(session):
    await _register_real_fingerprint(session)
    memory_id = await _add_memory_with_vector(session)

    result = await get_vector_projection(
        limit=500, project=None, status=["active"], _user=None,
        request=_FakeRequest(_SentinelLLM()), session=session,
    )

    assert [str(p["memory_id"]) for p in result["points"]] == [str(memory_id)]
