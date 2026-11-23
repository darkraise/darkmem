"""Doc 07 §5's cold start and the two output shapes (T2.56).

Split from T2.43 — grouping is T2.55's, cold start and the sectioned/fused
shapes are this task's.

**Cold start is a vault carrying memories but no facts, not a vault carrying
nothing.** ``test_knowledge_search.py`` already pins the genuinely empty case
(``test_an_empty_vault_answers_two_hundred_with_an_envelope``): zero memories
and zero facts is an honest ``rows: []``, and that stays true here — this
file does not touch it. Doc 07 §5's cold start is the day-one state a fresh
install actually sits in: capture has run, fact-lift has not, so
``knowledge_triples`` holds nothing for the project yet. A verified-only
default would read that as "nothing to show" for months; the composition must
not, because ``compose()`` never filters by verification status
(``layer_composition.py``'s own docstring: "An all-``candidate`` input
composes to a full, labelled result, which is the floor T2.56's cold start
inherits"). What was missing before this task is proof of that floor, the
plain "unverified" word on the label doc 07 §5 asks for, and the two output
shapes doc 07 §5 also fixes.

**Three answers, not two (invariant 14).** A cold-start result (candidates,
labelled, served), a genuine no-match (a populated vault with nothing
relevant to *this* query, served as an honest empty), and a failed read
(every channel down, ``CompositionUnavailable``) must each be reachable and
distinguishable. All three are exercised below specifically so a change that
collapses any two of them turns a test red rather than passing quietly.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.api.mcp import server as mcp_server
from app.main import app
from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.schemas.knowledge import knowledge_search_response
from app.services import facts_channel, hybrid_search
from app.services import layer_composition as lc
from app.services.embedder_registry import child_table
from app.services.fact_provenance import memory_source_ref

pytestmark = pytest.mark.asyncio

PROJECT = "t2-56-cold-start"
AT = datetime(2026, 8, 4, 9, 0, 0, tzinfo=timezone.utc)


class _FakeLLM:
    def __init__(self, vector, fingerprint):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


def _raises():
    async def _boom(self, *args, **kwargs):
        raise RuntimeError("channel down")
    return _boom


async def _register_partition(session, fingerprint: str, dims: int = 4) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'fake-embedder', :dims, 'llm') ON CONFLICT DO NOTHING"
        ),
        {"fp": fingerprint, "dims": dims},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _add_memory(session, fingerprint: str, vector: list[float], *, content: str, project: str) -> str:
    memory_id = uuid4()
    session.add(Memory(id=memory_id, content=content, source="test", project=project))
    await session.flush()
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {
            "mid": memory_id, "fp": fingerprint, "vec": str(vector),
            "payload": json.dumps({"content": content, "source": "test", "tags": []}),
        },
    )
    return str(memory_id)


# ── Done-when 1: a query against a vault with no facts yet is not zero rows ──


async def test_a_vault_with_memories_but_no_facts_returns_labelled_candidates(session):
    """The mutation that breaks this: anything that reads "the facts channel
    came back empty" as "there is nothing to show" — a verification-status
    filter added to ``compose()``, or a short-circuit in
    ``LayerCompositionService.search`` that drops the memory candidates
    whenever no fact candidate exists. Both turn this red; neither exists in
    the shipped code, which is what this test is pinning.
    """
    fingerprint = "t2-56-cold|4"
    vector = [1.0, 0.0, 0.0, 0.0]
    await _register_partition(session, fingerprint)
    await _add_memory(
        session, fingerprint, vector,
        content="pgbouncer connection pooling runs on the homelab",
        project=PROJECT,
    )
    await session.commit()

    # No fact-lift has run: knowledge_triples holds nothing for this project.
    service = lc.LayerCompositionService(_FakeLLM(vector, fingerprint), session)
    result = await service.search("pgbouncer connection pooling", project=PROJECT)

    assert result.rows, "cold start must serve labelled candidates, not zero rows"
    assert [row.id_kind for row in result.rows] == ["memory"]
    assert result.rows[0].labels["unverified"] is True
    assert result.rows[0].labels["badge"] is None, "L0 carries no badge (doc 12 §4)"
    assert result.envelope.partial is False
    assert result.envelope.channels["fact.keyword"].ran is True
    assert result.envelope.channels["fact.keyword"].failed is False


async def test_a_freshly_lifted_candidate_fact_is_labelled_unverified_too(session, cleared_promotion_record):
    """Doc 07 §5: "cold-start serves candidate rows labelled as candidates".
    A fact one origin has just lifted — before any corroboration — is served
    exactly as plainly as a bare memory is, and stops being once corroborated.
    """
    fingerprint = "t2-56-candidate|4"
    vector = [1.0, 0.0, 0.0, 0.0]
    await _register_partition(session, fingerprint)

    repo = KnowledgeTripleRepository(session)
    fact = await repo.insert_open(
        triple_key=f"t256-{uuid4()}",
        subject_name="pgbouncer",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer connection pooling runs on the homelab",
        reference_time=AT,
        project=PROJECT,
    )
    await session.commit()

    service = lc.LayerCompositionService(_FakeLLM(vector, fingerprint), session)
    result = await service.search("pgbouncer connection pooling", project=PROJECT)

    assert [row.id_kind for row in result.rows] == ["fact"]
    fact_row = result.rows[0]
    assert fact_row.verification_status == "candidate"
    assert fact_row.labels["unverified"] is True
    assert fact_row.labels["badge"]["origin_count"] == 0

    await repo.set_verification_status(fact["id"], "corroborated")
    await session.commit()

    corroborated = await service.search("pgbouncer connection pooling", project=PROJECT)
    assert corroborated.rows[0].labels["unverified"] is False


# ── the other two of the three answers, so cold start is proven by contrast ──


async def test_a_genuine_no_match_is_still_an_honest_empty_answer(session, monkeypatch):
    """A populated vault with nothing relevant to *this* query is not cold
    start, and serving candidates it never retrieved would be the opposite
    dishonesty from the one this task fixes."""
    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[])

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    result = await lc.LayerCompositionService(_FakeLLM([0.0], "fp"), session).search(
        "q", project=PROJECT,
    )

    assert result.rows == []
    assert result.envelope.partial is False


async def test_a_failed_read_is_never_served_as_a_cold_start_candidate_list(session, monkeypatch):
    """Both channels down must raise, not degrade into "candidates" nobody
    actually retrieved — that would be doc 12 §3's unavailability wearing a
    cold-start label."""
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _raises())
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _raises())

    with pytest.raises(lc.CompositionUnavailable):
        await lc.LayerCompositionService(_FakeLLM([0.0], "fp"), session).search(
            "q", project=PROJECT,
        )


# ── Done-when 2: both output shapes, on both doors ───────────────────


SHAPE_PROJECT = "t2-56-shape"
SHAPE_FINGERPRINT = "t2-56-shape|4"
SHAPE_DIMS = 4
SHAPE_QUERY = "pgbouncer connection pooling"
SHAPE_VECTOR = [1.0, 0.0, 0.0, 0.0]
ROUTE = "/api/v1/knowledge/search"


class _FakeShapeLLM:
    async def embed(self, query: str):
        return SHAPE_VECTOR, SHAPE_FINGERPRINT


class _Pipeline:
    def __init__(self):
        self.llm = _FakeShapeLLM()


@pytest.fixture(autouse=True)
def mcp_door(session, monkeypatch):
    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", _Pipeline())


@pytest.fixture(autouse=True)
def rest_door(monkeypatch):
    monkeypatch.setattr(app.state, "llm", _FakeShapeLLM(), raising=False)


async def _seed_shape_corpus(session) -> tuple[str, str]:
    await _register_partition(session, SHAPE_FINGERPRINT, SHAPE_DIMS)
    memory_id = await _add_memory(
        session, SHAPE_FINGERPRINT, SHAPE_VECTOR,
        content="pgbouncer connection pooling runs on the homelab",
        project=SHAPE_PROJECT,
    )
    repo = KnowledgeTripleRepository(session)
    fact = await repo.insert_open(
        triple_key=f"t256-shape-{uuid4()}",
        subject_name="pgbouncer",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer connection pooling runs on the homelab",
        reference_time=AT,
        project=SHAPE_PROJECT,
    )
    await session.commit()
    return memory_id, str(fact["id"])


async def _rest_body(client, auth_headers, **overrides) -> dict:
    body = {"query": SHAPE_QUERY, "project": SHAPE_PROJECT}
    body.update(overrides)
    response = await client.post(ROUTE, json=body, headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_fuse_defaults_to_the_sectioned_shape(client, auth_headers, session):
    """Doc 07 §5: "the default output is sectioned-by-layer with a fused
    fallback for token-budgeted consumers" — and again, "the default response
    returns the results sectioned by layer". Doc 07 §8's envelope table and
    doc 13 §5.4 both name the same default. A caller that never names
    ``fuse`` must get that shape, so a future flip back to flat is caught
    here rather than discovered silently at integration."""
    await _seed_shape_corpus(session)

    body = await _rest_body(client, auth_headers)

    assert body["rows"] is None
    assert body["sections"]["memory"] or body["sections"]["facts"], (
        "the fixture must retrieve something"
    )
    assert body["envelope"]["fused"] is False


async def test_fuse_false_returns_the_sectioned_shape(client, auth_headers, session):
    await _seed_shape_corpus(session)

    body = await _rest_body(client, auth_headers, fuse=False)

    assert body["rows"] is None
    assert body["envelope"]["fused"] is False
    sections = body["sections"]
    assert sections["memory"], "the fixture seeded a memory row"
    assert sections["facts"], "the fixture seeded a fact row"
    assert sections["articles"] == []
    assert {row["id_kind"] for row in sections["memory"]} == {"memory"}
    assert {row["id_kind"] for row in sections["facts"]} == {"fact"}


async def test_the_two_shapes_carry_the_same_rows_merely_partitioned(client, auth_headers, session):
    """Doc 07 §5: "both shapes apply the identical composition rules; only
    the presentation differs" — proven as a set-equality over what each shape
    actually served, not assumed from the two shapes sharing one code path.
    """
    await _seed_shape_corpus(session)

    fused = await _rest_body(client, auth_headers, fuse=True)
    sectioned = await _rest_body(client, auth_headers, fuse=False)

    fused_ids = {(row["id_kind"], row["id"]) for row in fused["rows"]}
    sectioned_ids = {
        (row["id_kind"], row["id"])
        for bucket in sectioned["sections"].values()
        for row in bucket
    }
    assert fused_ids, "the fixture must retrieve something or this is vacuous"
    assert fused_ids == sectioned_ids


async def test_a_sections_internal_order_is_the_composed_order_restricted_to_it(
    session, monkeypatch
):
    """Doc 07 §5: "each internally ranked"; the ``KnowledgeSearchSections``
    docstring: "Partitioning never reorders". Neither was enforced anywhere:
    the set-equality test above cannot see a reversal (it compares sets, not
    sequences), and every fixture in this module seeds at most one row per
    populated bucket, so even an order-sensitive assertion over them would
    hold vacuously. This fixture stubs the memory channel with three rows
    whose composed order (fixed by ``channel_rank``, i.e. the order the
    channel served them in) is neither ascending nor descending in id order
    — 3, 1, 2 — so a bucket-local reorder is caught on its own terms rather
    than by accidentally matching a sort-by-id artifact.

    The facts channel is stubbed the same way (R1, T2.56 fix round 2): two
    rows whose composed order runs opposite id order. Before this, the
    fixture populated only the memory bucket, so a facts-specific reorder —
    the section doc 13's panel renders first — passed every test in this
    file silently.
    """
    memory_ids = [str(UUID(int=n)) for n in (3, 1, 2)]
    fact_ids = [str(UUID(int=n)) for n in (20, 10)]

    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[
            {
                "memory_id": mid,
                "payload": {"content": f"memory {mid}"},
                "project": PROJECT,
                "status": "active",
                "rrf_score": 0.5 - 0.1 * index,
            }
            for index, mid in enumerate(memory_ids)
        ])

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[
            {
                "fact_id": fid,
                "id": fid,
                "fact": f"fact {fid}",
                "subject_name": "pgbouncer",
                "rel_type": "DEPLOYED_ON",
                "object_name": "homelab",
                "project": PROJECT,
                "verification_status": "candidate",
                "review_state": None,
                "rrf_score": 0.5,
            }
            for fid in fact_ids
        ])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    result = await lc.LayerCompositionService(_FakeShapeLLM(), session).search(
        "q", project=PROJECT, limit=20,
    )

    fused = knowledge_search_response(result, fuse=True).model_dump()
    composed_memory_order = [row["id"] for row in fused["rows"] if row["id_kind"] == "memory"]
    composed_fact_order = [row["id"] for row in fused["rows"] if row["id_kind"] == "fact"]
    assert composed_memory_order == memory_ids, (
        "the fixture's composed order must be exactly what channel_rank set, "
        "or this test proves nothing"
    )
    assert composed_fact_order == fact_ids, (
        "the fixture's composed fact order must be exactly what channel_rank "
        "set, or the facts half of this test proves nothing"
    )

    sectioned = knowledge_search_response(result, fuse=False).model_dump()
    assert [row["id"] for row in sectioned["sections"]["memory"]] == composed_memory_order
    assert [row["id"] for row in sectioned["sections"]["facts"]] == composed_fact_order


async def test_a_grouped_rows_nesting_survives_sectioning(session, monkeypatch):
    """F7: the ``KnowledgeSearchSections`` docstring claims "a row nested
    under a fact stays nested wherever its enclosing fact's section lands",
    and nothing fed the shipped ``_sectioned`` a grouped row before this —
    T2.55's own order test proved the same claim only against a local
    simulation helper, never the real serialiser. The memory here is fully
    consumed as evidence for the one fact, so it must not also be listed
    standalone in the memory section (the same grouping ``compose()``
    already gives the fused shape); sectioning must carry that consumption
    through rather than re-surface it as a bucket assignment.
    """
    memory_id = str(uuid4())
    repo = KnowledgeTripleRepository(session)
    fact = await repo.insert_open(
        triple_key=f"t256-nest-{uuid4()}",
        subject_name="pgbouncer",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer connection pooling runs on the homelab",
        reference_time=AT,
        project=PROJECT,
    )
    fact_id = str(fact["id"])
    await FactSourceRepository(session).add_source(
        fact_id=fact_id, source_kind="memory",
        source_ref=memory_source_ref(memory_id), origin_key="origin-nest",
    )
    await session.flush()

    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=[{
            "memory_id": memory_id,
            "payload": {"content": "pgbouncer connection pooling runs on the homelab"},
            "project": PROJECT,
            "status": "active",
            "rrf_score": 0.5,
        }])

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[{
            "fact_id": fact_id,
            "id": fact_id,
            "fact": "pgbouncer connection pooling runs on the homelab",
            "subject_name": "pgbouncer",
            "rel_type": "DEPLOYED_ON",
            "object_name": "homelab",
            "project": PROJECT,
            "verification_status": "candidate",
            "review_state": None,
            "rrf_score": 0.5,
        }])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    result = await lc.LayerCompositionService(_FakeShapeLLM(), session).search(
        "q", project=PROJECT, limit=20,
    )
    sectioned = knowledge_search_response(result, fuse=False).model_dump()

    assert sectioned["sections"]["memory"] == []
    facts_bucket = sectioned["sections"]["facts"]
    assert len(facts_bucket) == 1
    assert facts_bucket[0]["id"] == fact_id
    assert [nested["id"] for nested in facts_bucket[0]["supported_by"]] == [memory_id]


async def test_both_doors_offer_fuse_with_the_same_default(session):
    """Invariant 17: a shape offered on one door and not its twin is a
    capability asymmetry wearing a parameter's clothes — including the
    default itself, not just the parameter's presence."""
    await _seed_shape_corpus(session)

    default = json.loads(await mcp_server.knowledge_search(query=SHAPE_QUERY, project=SHAPE_PROJECT))
    fused = json.loads(
        await mcp_server.knowledge_search(query=SHAPE_QUERY, project=SHAPE_PROJECT, fuse=True)
    )

    assert default["rows"] is None
    assert default["sections"]["memory"] or default["sections"]["facts"]
    assert fused["rows"]
    assert fused["sections"] is None


# ── Done-when 3: the label states plainly it is unverified, on the wire ──


async def test_the_wire_label_states_plainly_the_row_is_unverified(client, auth_headers, session):
    await _seed_shape_corpus(session)

    body = await _rest_body(client, auth_headers, fuse=True)

    memory_row = next(row for row in body["rows"] if row["id_kind"] == "memory")
    fact_row = next(row for row in body["rows"] if row["id_kind"] == "fact")
    assert memory_row["labels"]["unverified"] is True
    assert fact_row["labels"]["unverified"] is True, "freshly lifted, still 'candidate'"


async def test_a_different_project_is_a_genuine_empty_not_a_cold_start(client, auth_headers, session):
    """The contrast, at the wire: this project holds nothing at all, so the
    honest answer is an empty result in whichever shape was asked for — not
    the other project's candidates and not a fabricated placeholder."""
    await _seed_shape_corpus(session)

    sectioned = await _rest_body(client, auth_headers, project="t2-56-nothing-here")
    assert sectioned["rows"] is None
    assert sectioned["sections"] == {"memory": [], "facts": [], "articles": []}

    fused = await _rest_body(client, auth_headers, project="t2-56-nothing-here", fuse=True)
    assert fused["rows"] == []
    assert fused["envelope"]["partial"] is False
    assert sectioned["envelope"]["partial"] is False
