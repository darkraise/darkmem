"""Every deliberately wide read hands back rows that name their own scope.

The pushdown work (T1.29a-e) settled *which* rows a channel may return. This
module pins the other half: a channel that is legitimately wide — ``reason``
and chat default to every project, the re-embed queue is deployment-wide by
design — must label what it returns, or a consumer cannot tell a foreign or
superseded row from a local live one. Narrowing these channels is the wrong
fix and is pinned against elsewhere; the label is what buys them the width.

The labels are stamped where the rows are **produced**, not at each consumer:
``PostgresVectorRepository.search`` and both ``HybridSearchService`` arms join
``memories`` unconditionally, exactly as ``get_all_vectors`` does, so a row
reaching a caller nobody enumerated still arrives self-describing. Each test
below fails if that join or its two columns are removed at the producer, which
is the point — four call-site fixes would leave the fifth caller unlabelled.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.schemas.memory import MemoryResponse
from app.services.chat import ChatService
from app.services.content_surfaces import surface
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.services.memory import MemoryService
from app.services.reembed import ReembedService
from app.utils.scope_labels import SCOPE_LABEL_FIELDS, scope_labels

pytestmark = pytest.mark.asyncio

FINGERPRINT = "scope-labels|4"
DIMS = 4
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]
OBSERVER = "alpha"
FOREIGN = "beta"
KEYWORD_TERM = "pgbouncer"


class _FakeLLM:
    """Embeds deterministically and records what the reasoning model was asked."""

    def __init__(self):
        self.prompts: list[list[dict]] = []

    async def embed(self, query: str):
        return QUERY_VECTOR, FINGERPRINT

    async def chat_completion(self, purpose, messages=None, **kwargs):
        self.prompts.append(list(messages or []))
        return "synthesised answer"

    async def chat_completion_stream(self, purpose, messages=None, **kwargs):
        self.prompts.append(list(messages or []))
        yield "synthesised answer"


class _RealSemanticPipeline:
    """``semantic_search`` delegated to the production repository.

    A canned row list would prove nothing here: the labels under test are put
    on the row by the SQL, so the probe has to reach Postgres.
    """

    def __init__(self, session):
        self.session = session
        self.llm = _FakeLLM()

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        return await PostgresVectorRepository(self.session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT, limit=limit, filters=filters,
        )


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "scope-labels", "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, *, embed: bool = True, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content=f"{KEYWORD_TERM} is the connection pooler",
        source="test",
        importance=0.5,
        metadata_={},
        project=OBSERVER,
        status="active",
        memory_type="decision",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()

    if embed:
        child = child_table("memory_embeddings", FINGERPRINT)
        await session.execute(
            text(
                f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
                "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
            ),
            {
                "mid": base["id"], "fp": FINGERPRINT, "vec": str(QUERY_VECTOR),
                "payload": f'{{"content": "{base["content"]}"}}',
            },
        )
    await session.flush()
    return memory


async def _wide_corpus(session) -> dict[str, Memory]:
    """A local live row plus the two kinds of row a wide read must label."""
    await _seed_partition(session)
    live = await _add_memory(session, content=f"{KEYWORD_TERM} local live pooler note")
    return {
        "live": live,
        "foreign": await _add_memory(
            session, project=FOREIGN,
            content=f"{KEYWORD_TERM} foreign-project pooler note",
        ),
        "retired": await _add_memory(
            session, status="superseded", superseded_by=live.id,
            content=f"{KEYWORD_TERM} superseded pooler note",
        ),
    }


def _labels_of(rows, key="memory_id") -> dict[str, tuple]:
    return {str(r[key]): tuple(r[name] for name in SCOPE_LABEL_FIELDS) for r in rows}


# ── the vocabulary ───────────────────────────────────────────────────


async def test_the_wide_row_labels_are_the_id_addressed_row_field_names():
    """A wide row must be readable with the same keys as a direct read, or a
    consumer has to learn two names for one fact."""
    assert set(SCOPE_LABEL_FIELDS) <= set(MemoryResponse.model_fields)


async def test_a_producer_missing_a_label_raises_instead_of_emitting_none():
    """``None`` would read downstream as a row with genuinely no project."""
    with pytest.raises(KeyError):
        scope_labels({"project": OBSERVER})


# ── the production points ────────────────────────────────────────────


async def test_vector_search_labels_every_row_even_when_unscoped(session):
    """``filters=None`` is the crossref probe's shape and the one a future
    caller reaches for; it must still hand back labelled rows."""
    rows = await _wide_corpus(session)

    results = await PostgresVectorRepository(session).search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=20, filters=None,
    )

    labels = _labels_of(results)
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")
    assert labels[str(rows["retired"].id)] == (OBSERVER, "superseded")
    assert labels[str(rows["live"].id)] == (OBSERVER, "active")


async def test_vector_search_labels_survive_a_scoped_call(session):
    rows = await _wide_corpus(session)

    results = await PostgresVectorRepository(session).search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=20,
        filters=MemoryFilter(project=OBSERVER, statuses=("active",)),
    )

    assert _labels_of(results) == {str(rows["live"].id): (OBSERVER, "active")}


async def test_vector_search_labels_never_go_stale_against_the_row(session):
    """The labels come off ``memories`` rather than the write-time payload
    snapshot, so a supersession after the upsert is reflected immediately."""
    rows = await _wide_corpus(session)
    await session.execute(
        text("UPDATE memories SET status = 'superseded', superseded_by = CAST(:s AS uuid) "
             "WHERE id = CAST(:id AS uuid)"),
        {"s": str(rows["live"].id), "id": str(rows["foreign"].id)},
    )
    await session.flush()

    results = await PostgresVectorRepository(session).search(
        QUERY_VECTOR, fingerprint=FINGERPRINT, limit=20, filters=None,
    )

    assert _labels_of(results)[str(rows["foreign"].id)] == (FOREIGN, "superseded")


async def test_hybrid_semantic_arm_labels_every_row_even_when_unscoped(session):
    rows = await _wide_corpus(session)
    svc = HybridSearchService(_FakeLLM(), session)

    results = await svc._semantic_search(QUERY_VECTOR, FINGERPRINT, 20, None)

    labels = _labels_of(results)
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")
    assert labels[str(rows["retired"].id)] == (OBSERVER, "superseded")


async def test_hybrid_keyword_arm_labels_every_row_even_when_unscoped(session):
    rows = await _wide_corpus(session)
    svc = HybridSearchService(_FakeLLM(), session)

    results = await svc._keyword_search(KEYWORD_TERM, 20, None)

    labels = _labels_of(results)
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")
    assert labels[str(rows["retired"].id)] == (OBSERVER, "superseded")


async def test_a_keyword_only_row_keeps_its_labels_through_fusion(session):
    """RRF copies the first-seen side's row, so a row only the keyword arm
    found carries the keyword arm's labels or none at all."""
    await _seed_partition(session)
    keyword_only = await _add_memory(
        session, embed=False, project=FOREIGN,
        content=f"{KEYWORD_TERM} foreign row with no vector",
    )

    svc = HybridSearchService(_FakeLLM(), session)
    fused = await svc.search(KEYWORD_TERM, limit=20)

    assert _labels_of(fused)[str(keyword_only.id)] == (FOREIGN, "active")


# ── surface: memory_reason, both doors ───────────────────────────────


async def test_reason_labels_every_cited_source(session):
    """The project default is every project (ratified), so a cited row has to
    say which project it came from."""
    rows = await _wide_corpus(session)

    result = await MemoryService(session, pipeline=_RealSemanticPipeline(session)).reason(
        "which pooler are we using", limit=20,
    )

    labels = _labels_of(result["sources"])
    assert labels[str(rows["live"].id)] == (OBSERVER, "active")
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")


async def test_reason_labels_the_type_hint_pass_too(session):
    """The type/tag passes run before the semantic early-return and build
    their own citations, so they are a second place a label can be dropped."""
    rows = await _wide_corpus(session)

    class _NoSemantic(_RealSemanticPipeline):
        async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
            return []

    result = await MemoryService(session, pipeline=_NoSemantic(session)).reason(
        "summarize recent decisions", limit=20,
    )

    assert result["sources"], "the type pass must still contribute rows"
    labels = _labels_of(result["sources"])
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")


async def test_mcp_reason_labels_its_sources_like_the_rest_door(
    mcp_http_client, session, monkeypatch,
):
    """Invariant 17: both doors of one surface behave identically. The MCP
    tool serialises the service's citation dict, so it inherits the labels
    rather than hand-building a second row shape."""
    import json

    import app.api.mcp.server as mcp_module

    rows = await _wide_corpus(session)
    monkeypatch.setattr(mcp_module, "_pipeline", _RealSemanticPipeline(session))

    response = await mcp_http_client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "memory_reason",
            "arguments": {"question": "which pooler are we using", "limit": 20},
        },
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert not body["result"].get("isError"), body
    payload = json.loads(body["result"]["content"][0]["text"])

    labels = _labels_of(payload["sources"])
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")
    assert labels[str(rows["live"].id)] == (OBSERVER, "active")


# ── surface: chat retrieval and its persisted citations ──────────────


async def test_chat_sources_event_labels_every_retrieved_row(session):
    rows = await _wide_corpus(session)
    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))

    retrieval = await svc._retrieve("which pooler", None)

    by_content = {m["content"]: m for m in retrieval["memories"]}
    assert by_content[rows["foreign"].content]["project"] == FOREIGN
    assert by_content[rows["foreign"].content]["status"] == "active"
    assert by_content[rows["live"].content]["project"] == OBSERVER


async def test_chat_persists_a_label_on_every_citation(session):
    """The stored snippet is re-served on every conversation read, so an
    unlabelled citation keeps leaking long after the answer was produced."""
    rows = await _wide_corpus(session)
    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))

    message_id = None
    async for event in svc.send_message(None, "which pooler", None):
        if event["type"] == "done":
            message_id = uuid.UUID(event["message_id"])

    from app.models.chat import Message
    stored = await session.get(Message, message_id)
    cited = {c["id"]: c for c in stored.context["memories"]}
    assert cited[str(rows["foreign"].id)]["project"] == FOREIGN
    assert cited[str(rows["foreign"].id)]["status"] == "active"


# ── surface: the re-embed backfill queue ─────────────────────────────


async def test_reembed_queue_labels_the_rows_it_stays_wide_to_show(session):
    """Deployment-wide on purpose: a row this queue hid would never get a
    vector under the active embedder. The labels are the trade for that."""
    rows = await _wide_corpus(session)
    await session.execute(
        text(f"DELETE FROM {child_table('memory_embeddings', FINGERPRINT)}")
    )
    await session.flush()

    items, total, partition_missing = await ReembedService(session).list_obsolete_memories(
        FINGERPRINT, limit=100,
    )

    assert partition_missing is False
    assert total == len(rows)
    labels = _labels_of(items)
    assert labels[str(rows["foreign"].id)] == (FOREIGN, "active")
    assert labels[str(rows["retired"].id)] == (OBSERVER, "superseded")


# ── the registry says what the responses now do ──────────────────────


@pytest.mark.parametrize("key", [
    "memory_reason", "chat_retrieval", "chat_history_citations",
    "reembed_backfill_queue",
])
async def test_the_registry_declares_the_labels_these_surfaces_emit(key):
    """The registry's value is that it can be wrong in a way a build catches,
    so its claim and the response shape are pinned to move together."""
    assert set(SCOPE_LABEL_FIELDS) <= set(surface(key).labels)
