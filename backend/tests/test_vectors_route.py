"""An unconfirmed ``llm_fingerprint()`` must never carry a bulk read (T2.68, T2.83).

``LLMOrchestrator.llm_fingerprint()`` is built from static config, never from
an actual embed, so it can name a partition no real embed ever wrote to. Two
shapes of that: ``dimensions`` unset (the ``model|0`` sentinel, T2.68) and
``dimensions`` set to the WRONG positive value (768 configured while the model
emits 1024, T2.83) — boot-time registration refuses to create a table for the
first (``dims <= 0`` fails validation) but happily creates an empty,
syntactically valid one for the second, since a positive number passes the
only check registration runs. Reading either keyed fingerprint directly either
raises ``UndefinedTable`` (nothing was ever registered under it) or, worse,
silently returns zero rows forever with no error at all — both worse than a
named refusal. These tests pin ``PostgresVectorRepository.resolve_read_fingerprint``
and the ``/api/v1/vectors/projection`` route that must use it instead of the
bare ``llm_fingerprint()`` read, for both shapes of the same class.
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
# A wrong non-zero dims: distinct from both the sentinel and the real one, so
# it collides with neither. Boot-time registration accepts it (dims > 0)
# and creates its child table, but no real embed will ever populate it.
WRONG_FINGERPRINT = f"{MODEL_ID}|8"
DIMS = 4
WRONG_DIMS = 8
VECTOR = [1.0, 0.0, 0.0, 0.0]


class _SentinelLLM:
    """The shape both read paths receive under an unset ``dimensions`` config."""

    def llm_fingerprint(self) -> str:
        return SENTINEL_FINGERPRINT


class _WrongDimsLLM:
    """The shape both read paths receive under a wrong non-zero ``dimensions``
    config (768 configured, 1024 real — T2.83)."""

    def llm_fingerprint(self) -> str:
        return WRONG_FINGERPRINT


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


async def _register_wrong_fingerprint_empty(session) -> None:
    """What boot-time registration does under a wrong non-zero ``dimensions``:
    create the ``embedders`` row and the child table, but populate nothing —
    only a real embed call, which ``_check_dims`` refuses under this exact
    mismatch, could ever write a row here."""
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": WRONG_FINGERPRINT, "mid": MODEL_ID, "dims": WRONG_DIMS},
    )
    child = child_table("memory_embeddings", WRONG_FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({WRONG_DIMS}) NOT NULL,"
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


async def test_resolve_read_fingerprint_passes_through_a_registered_real_fingerprint(session):
    """The fast, common path: a correctly configured, actively used model
    resolves to itself with no rewriting."""
    class _RealLLM:
        def llm_fingerprint(self) -> str:
            return REAL_FINGERPRINT

    await _register_real_fingerprint(session)
    await _add_memory_with_vector(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_RealLLM())
    assert resolved == REAL_FINGERPRINT


async def test_resolve_read_fingerprint_finds_the_real_partition_behind_the_sentinel(session):
    """Dimensions cleared after a real embed already registered the model:
    the sentinel must resolve to the fingerprint that actually has data,
    never proceed keyed on ``|0``."""
    await _register_real_fingerprint(session)
    await _add_memory_with_vector(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_SentinelLLM())

    assert resolved == REAL_FINGERPRINT
    assert resolved != SENTINEL_FINGERPRINT


async def test_resolve_read_fingerprint_raises_when_nothing_is_registered(session):
    """Fresh config, dimensions unset, no embed has ever run for this model:
    there is no partition to read, so this must refuse loudly rather than
    hand back the sentinel for a caller to read empty forever."""
    with pytest.raises(EmbedderFingerprintUnresolved):
        await PostgresVectorRepository(session).resolve_read_fingerprint(_SentinelLLM())


# ── T2.83: a wrong non-zero dims reproduces the same class ─────────────────


async def test_resolve_read_fingerprint_finds_the_real_partition_behind_a_wrong_nonzero_dims(session):
    """768 configured, 1024 real (here: WRONG_DIMS configured, DIMS real).

    Boot already created the empty ``model|8`` partition (dims > 0 passes its
    only check) and real embeds already populated ``model|4`` before the
    config drifted. A read keyed on the configured fingerprint must not settle
    for the empty partition that happens to carry its exact name — it must
    find the one with real data, the same way it does for the sentinel."""
    await _register_real_fingerprint(session)
    await _add_memory_with_vector(session)
    await _register_wrong_fingerprint_empty(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_WrongDimsLLM())

    assert resolved == REAL_FINGERPRINT
    assert resolved != WRONG_FINGERPRINT


async def test_resolve_read_fingerprint_passes_through_an_unconfirmable_wrong_dims_partition(session):
    """The documented, unclosable gap: nothing has EVER been embedded for
    this model under any dims, so the only registered partition is the
    (possibly wrong) configured one, empty. That state is bit-for-bit
    identical to a brand-new, correctly configured deployment with nothing
    ingested yet — no read-only signal distinguishes them, since only an
    actual embed call (which this resolver deliberately never makes) could
    reveal the true dimension. Refusing here would 503 every legitimate
    fresh install, so this passes the configured fingerprint through and
    reads an honestly empty partition, exactly as it would for a correct
    config in the same state — see 'Known gaps' in the T2.83 report."""
    await _register_wrong_fingerprint_empty(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(_WrongDimsLLM())

    assert resolved == WRONG_FINGERPRINT


# ── the memory-only probe stays the shared default (T-doc-door.6 review) ───
#
# ``_partition_has_data``/``resolve_read_fingerprint`` hardcode the "does
# this candidate hold real data" probe to ``memory_embeddings``. A round-1
# fix gave this a ``parent_table`` parameter so a caller like
# ``block_embeddings.resolve_read_fingerprint`` could point the probe at its
# own family instead — closing the direction where a block-only install
# never converges, but reopening the WORSE direction on an embedder
# rotation: a data probe of *any* family prefers whichever fingerprint
# already has rows, which is exactly the stale, pre-rotation one, not the
# active-but-still-empty one retrieval actually reads. Round 2 reverted the
# parameter entirely — a backstop sweep cannot resolve its fingerprint from
# any data probe and instead resolves it from a real embed call,
# ``block_embeddings.resolve_active_fingerprint`` (see
# `tests/test_block_embedding_refresh.py::test_refresh_targets_the_rotated_fingerprint_not_the_stale_full_one`
# for the sweep's rotation case pinned end to end). Round 3 found the
# identical bias in ``document_door.put_document``'s ``unchanged`` gap-fill
# repair and moved it onto ``resolve_active_fingerprint`` too (see
# `tests/test_document_door.py::test_unchanged_repair_targets_the_rotated_fingerprint_not_the_stale_full_one`),
# so that caller no longer touches this resolver either. This resolver, and
# the test below, are back to exactly their pre-T-doc-door.6 shape: the
# memory-only probe is still what every other family's own callers
# (relation, entity-anchoring, entity-merge, triple embeddings) get,
# unchanged — the block family itself has no caller left for it, and it
# stays exported for a future one of that shape (see
# ``block_embeddings.resolve_read_fingerprint``'s own docstring).

BLOCK_MODEL_ID = "vectors-route-block-model"
# Two live fingerprints sharing one model_id, exactly the residual shape
# `block_embedding_refresh`'s own docstring now describes: one holds real
# block data and no memory data, the other holds real memory data and no
# block data.
BLOCK_ONLY_FINGERPRINT = f"{BLOCK_MODEL_ID}|4"
MEMORY_ONLY_FINGERPRINT = f"{BLOCK_MODEL_ID}|8"
BLOCK_ONLY_DIMS = 4
MEMORY_ONLY_DIMS = 8


async def _register_fingerprint_with_child(session, fingerprint, dims, parent_table):
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint, "mid": BLOCK_MODEL_ID, "dims": dims},
    )
    child = child_table(parent_table, fingerprint)
    if parent_table == "memory_embeddings":
        await session.execute(text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            f" embedding vector({dims}) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            " PRIMARY KEY (memory_id, fingerprint))"
        ))
    else:
        await session.execute(text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " block_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            f" embedding vector({dims}) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            " PRIMARY KEY (block_id, fingerprint))"
        ))


async def _add_block_with_vector(session) -> uuid.UUID:
    document_id = uuid.uuid4()
    block_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO documents (id, project) VALUES (:id, 'p')"),
        {"id": document_id},
    )
    await session.execute(
        text(
            "INSERT INTO blocks (id, document_id, order_index, type, text) "
            "VALUES (:id, :doc_id, 0, 'paragraph', 'body')"
        ),
        {"id": block_id, "doc_id": document_id},
    )
    child = child_table("block_embeddings", BLOCK_ONLY_FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (block_id, fingerprint, embedding, payload) "
            "VALUES (:bid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {
            "bid": block_id, "fp": BLOCK_ONLY_FINGERPRINT,
            "vec": str([1.0, 0.0, 0.0, 0.0]), "payload": "{}",
        },
    )
    return block_id


async def _add_memory_with_vector_under(session, fingerprint, dims) -> uuid.UUID:
    memory_id = uuid.uuid4()
    session.add(Memory(
        id=memory_id, content="real vector, wrong family for the block probe",
        source="test", importance=0.5, metadata_={}, project="default",
        status="active", memory_type="decision", is_archived=False,
    ))
    await session.flush()
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {"mid": memory_id, "fp": fingerprint, "vec": str([1.0] * dims), "payload": '{"content": "x"}'},
    )
    return memory_id


class _SharedModelLLM:
    """Reports the block-only fingerprint — the real, current embedder."""

    def llm_fingerprint(self) -> str:
        return BLOCK_ONLY_FINGERPRINT


async def _seed_diverged_family_traffic(session) -> None:
    """Two live fingerprints, one model_id: block data under the configured
    (current) one, memory data under the older sibling, none of the reverse.
    """
    await _register_fingerprint_with_child(
        session, MEMORY_ONLY_FINGERPRINT, MEMORY_ONLY_DIMS, "memory_embeddings",
    )
    await _register_fingerprint_with_child(
        session, MEMORY_ONLY_FINGERPRINT, MEMORY_ONLY_DIMS, "block_embeddings",
    )
    await _register_fingerprint_with_child(
        session, BLOCK_ONLY_FINGERPRINT, BLOCK_ONLY_DIMS, "memory_embeddings",
    )
    await _register_fingerprint_with_child(
        session, BLOCK_ONLY_FINGERPRINT, BLOCK_ONLY_DIMS, "block_embeddings",
    )
    await _add_memory_with_vector_under(session, MEMORY_ONLY_FINGERPRINT, MEMORY_ONLY_DIMS)
    await _add_block_with_vector(session)
    await session.flush()


async def test_resolve_read_fingerprint_still_only_asks_memory(session):
    """The shared resolver reads only the memory partition, even when a
    sibling fingerprint for the same model_id holds real BLOCK data and no
    memory data — that block data is invisible to this method by design; a
    caller whose family needs to see it must resolve some other way (a real
    embed call, not a data probe of any family — see
    `block_embeddings.resolve_active_fingerprint`)."""
    await _seed_diverged_family_traffic(session)

    resolved = await PostgresVectorRepository(session).resolve_read_fingerprint(
        _SharedModelLLM(),
    )

    assert resolved == MEMORY_ONLY_FINGERPRINT
    assert resolved != BLOCK_ONLY_FINGERPRINT


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


async def test_projection_route_serves_real_points_behind_a_wrong_nonzero_dims_config(session):
    """T2.83: 768 configured, 1024 real. Boot already created the empty
    ``model|8`` partition; the route must not read it and hand back an
    empty, well-formed 200 — it must find the real data instead."""
    await _register_real_fingerprint(session)
    memory_id = await _add_memory_with_vector(session)
    await _register_wrong_fingerprint_empty(session)

    result = await get_vector_projection(
        limit=500, project=None, status=["active"], _user=None,
        request=_FakeRequest(_WrongDimsLLM()), session=session,
    )

    assert [str(p["memory_id"]) for p in result["points"]] == [str(memory_id)]
