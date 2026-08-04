"""The composed read on both doors, ranking one corpus one way (T2.80).

``POST /api/v1/knowledge/search`` is doc 12 §2's twin for MCP's
``knowledge_search``. T2.72 shipped the tool and filed the surface
MCP-single-door; the filing was honest and it was wrong, because
``memory.search`` and ``code.search`` are both two-door and a cross-layer
*ranked* answer is a capability by this repo's own precedent.

What this module pins, and the mutation that breaks each one:

* **One serialiser, and it is spent rather than imitated.** Both doors are
  spied on: each must call ``knowledge_search_response`` exactly once. A door
  that rebuilt the payload from ``ComposedRow`` itself would still answer a
  plausible document, which is precisely how ``code_search`` and
  ``code_blast_radius`` drifted while sharing a service.

* **Parity on the order, not the shape.** T2.72's finding 2: the reranker is a
  door-side constructor argument, so the moment one door passes one the two
  rank differently while every row-shape test stays green. The assertions here
  compare the id sequences the doors produce over one corpus, including the
  order of the memories nested under a fact, and the deep case runs over a
  corpus longer than ``FUSION_FETCH_DEPTH`` so that a door reading its arms to
  a different depth reorders rather than merely truncating. A 5-row corpus
  proves nothing: RRF is truncation-consistent on a corpus that fits inside
  every window.

* **Three outcomes, not two.** An empty vault, a total channel outage and a
  defect *inside* the composition are three different answers. Both doors used
  to catch bare ``RuntimeError``, and the composition raises that base for its
  own bugs — the grouping fixpoint that stopped decreasing
  (``layer_composition._group_within_limit``), a reranker that returned a
  window of the wrong length (``derive_rerank_scores``) — so a bug over a
  healthy vault was served as "the vault is down". That is the
  failed-versus-empty conflation T2.66 spent a task eliminating, pointed at
  the operator rather than at the code.

**Where the doors are not equal, deliberately.** The route is authenticated and
the tool is not (invariant 20's trust posture), so an operator can point the
two at different row sets; the parity asserted here is parity *within* an equal
row set, taken over one session. And the parity holds while every rank arm sits
at weight 0 — the doors weight ``confidence_rank_gamma`` on different bases
(``tests/test_chat_retrieval_parity.py`` measures that), so activating an arm
obliges re-measuring this file rather than trusting it.
"""

from __future__ import annotations

import ast
import json
import math
import pathlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

import app.api.routes.knowledge_search as knowledge_route
import app.services.facts_channel as facts_channel
import app.services.hybrid_search as hybrid_search
from app.api.mcp import server as mcp_server
from app.main import app
from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.schemas import knowledge as knowledge_schemas
from app.schemas.knowledge import KNOWLEDGE_SEARCH_MAX_LIMIT
from app.services.embedder_registry import child_table
from app.services.layer_composition import (
    CompositionUnavailable,
    LayerCompositionService,
    outage_channels,
)
from app.services.rank_fusion import FUSION_FETCH_DEPTH

ROUTE = "/api/v1/knowledge/search"
PROJECT = "t280-vault"
QUERY = "pgbouncer connection pooling"
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]
FINGERPRINT = "t280-parity|4"
DIMS = 4
AT = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)


class _FakeLLM:
    async def embed(self, query: str):
        return QUERY_VECTOR, FINGERPRINT


class _Pipeline:
    def __init__(self):
        self.llm = _FakeLLM()


@pytest.fixture(autouse=True)
def mcp_door(session, monkeypatch):
    """The tool's session and orchestrator, pointed at the test's own.

    Both doors must read one session or the "same corpus" the parity claim
    rests on is two corpora that happen to agree.
    """
    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", _Pipeline())


@pytest.fixture(autouse=True)
def rest_door(monkeypatch):
    monkeypatch.setattr(app.state, "llm", _FakeLLM(), raising=False)


# ── the corpus ───────────────────────────────────────────────────────


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "t280-parity", "dims": DIMS},
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


async def _add_memories(session, rows: list[tuple[str, list[float]]]) -> list[str]:
    """Insert in one round trip per table; a 341-row fixture inserted row at a
    time spends more of the suite's budget than the property is worth."""
    ids = [uuid.uuid4() for _ in rows]
    session.add_all([
        Memory(
            id=memory_id, content=content, source="test", importance=0.5,
            metadata_={}, project=PROJECT, status="active", memory_type="fact",
            is_archived=False,
        )
        for memory_id, (content, _) in zip(ids, rows)
    ])
    await session.flush()

    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        [
            {
                "mid": memory_id, "fp": FINGERPRINT, "vec": str(vector),
                "payload": json.dumps({"content": content, "source": "test", "tags": []}),
            }
            for memory_id, (content, vector) in zip(ids, rows)
        ],
    )
    await session.flush()
    return [str(memory_id) for memory_id in ids]


async def _corpus(session) -> dict[str, str]:
    """Rows whose semantic order, keyword order and fused order all disagree.

    ``keyword_only`` is orthogonal to the query vector and lexically closest;
    ``semantic_only`` is the nearest vector and carries no query term. Fusion
    has to move both, so an ordering assertion over this corpus cannot pass
    against a semantic-only ranking.
    """
    await _seed_partition(session)
    keys = ("semantic_only", "both", "middle", "keyword_only")
    ids = await _add_memories(session, [
        ("the box runs a database proxy on the LAN", [1.0, 0.0, 0.0, 0.0]),
        ("pgbouncer connection pooling is configured in transaction mode",
         [0.92, 0.39, 0.0, 0.0]),
        ("connection pooling notes for the homelab", [0.7, 0.71, 0.0, 0.0]),
        ("pgbouncer connection pooling was chosen over pgcat", [0.0, 0.0, 1.0, 0.0]),
    ])
    return dict(zip(keys, ids))


FILLERS = 340


async def _deep_corpus(session) -> str:
    """A corpus longer than the shared fusion depth, with one row whose rank
    is a function of how deep the arms were read.

    Every filler is semantically closer to the query than the target and
    carries no query term, so the keyword arm never sees one. The target is the
    least similar row and the only lexical match: read to a depth that reaches
    it, it fuses a deep semantic contribution onto a rank-one keyword one and
    lands mid-list; read to a shallower depth it is keyword-only and lands
    lower. Two doors reading to different depths therefore produce different
    *orders*, which is the failure a length-tolerant shape test cannot see.
    """
    await _seed_partition(session)
    rows = [
        (f"the box runs a database proxy on the LAN, note {i}",
         [math.cos(0.004 * (i + 1)), math.sin(0.004 * (i + 1)), 0.0, 0.0])
        for i in range(FILLERS)
    ]
    rows.append(
        ("pgbouncer connection pooling was chosen over pgcat",
         [math.cos(1.4), math.sin(1.4), 0.0, 0.0])
    )
    return (await _add_memories(session, rows))[-1]


async def _seed_fact(session, *, sourced_by: str | None = None) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=f"t280-{uuid.uuid4()}",
        subject_name="pgbouncer",
        object_name="homelab",
        rel_type="DEPLOYED_ON",
        fact="pgbouncer connection pooling runs on the homelab",
        reference_time=AT,
        project=PROJECT,
        valid_at=AT,
    )
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'corroborated' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": row["id"]},
    )
    sources = FactSourceRepository(session)
    for origin, ref in (("origin-a", str(uuid.uuid4())), ("origin-b", sourced_by)):
        if ref is None:
            continue
        await sources.add_source(
            fact_id=row["id"], source_kind="memory", source_ref=ref,
            origin_key=origin,
        )
    await session.flush()
    return str(row["id"])


# ── the two doors ────────────────────────────────────────────────────


async def _rest(client, auth_headers, *, limit: int = 20, project: str = PROJECT, fuse: bool = True):
    return await client.post(
        ROUTE,
        json={"query": QUERY, "project": project, "limit": limit, "fuse": fuse},
        headers=auth_headers,
    )


async def _rest_body(client, auth_headers, **kwargs) -> dict:
    response = await _rest(client, auth_headers, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


async def _mcp_body(*, limit: int = 20, project: str = PROJECT, fuse: bool = True) -> dict:
    return json.loads(
        await mcp_server.knowledge_search(query=QUERY, project=project, limit=limit, fuse=fuse)
    )


def _order(document: dict) -> list[str]:
    """The served order, nesting included.

    A fact's supporting memories are part of the answer's order, not decoration
    under it: a door that ranked the nested list differently would serve the
    same top-level sequence with a different first citation under each fact.
    """
    served: list[str] = []
    for row in document["rows"]:
        served.append(f"{row['id_kind']}:{row['id']}")
        served += [f"  {n['id_kind']}:{n['id']}" for n in row["supported_by"]]
    return served


# ── Done-when 1: the route exists and both doors spend one serialiser ─


async def test_the_route_answers_the_composed_read(client, auth_headers, session):
    await _corpus(session)
    fact_id = await _seed_fact(session)

    body = await _rest_body(client, auth_headers)

    assert body["rows"], "the fixture must retrieve something"
    assert {row["id_kind"] for row in body["rows"]} == {"memory", "fact"}
    fact_row = next(row for row in body["rows"] if row["id_kind"] == "fact")
    assert fact_row["id"] == fact_id
    assert fact_row["layer"] == "L2"
    assert fact_row["labels"]["badge"]["claim"]
    assert body["envelope"]["query"] == QUERY
    assert body["envelope"]["channels"]["memory.keyword"] == {"ran": True, "failed": False}
    assert body["envelope"]["excluded"]["by_context_conflict"] == 0


async def test_both_doors_serve_the_same_document(client, auth_headers, session):
    """The whole document, not a field list. A key-presence check passes a door
    that dropped a value and a field list passes a door that grew a key nobody
    enumerated; both doors serialise through one function, so this holds
    structurally rather than by agreement."""
    rows = await _corpus(session)
    await _seed_fact(session, sourced_by=rows["both"])

    rest = await _rest_body(client, auth_headers)
    tool = await _mcp_body()

    assert tool == rest


async def test_each_door_spends_the_shared_serialiser_exactly_once(
    client, auth_headers, session, monkeypatch
):
    """Invariant 17 at the payload layer. A door that reshaped the composition
    result itself would answer a document that still parses — the shape test
    above would only catch it once the two shapes had already diverged, which
    is one release too late."""
    await _corpus(session)
    original = knowledge_schemas.knowledge_search_response
    calls: list[str] = []

    def _rest_spy(result, **kwargs):
        calls.append("rest")
        return original(result, **kwargs)

    def _mcp_spy(result, **kwargs):
        calls.append("mcp")
        return original(result, **kwargs)

    monkeypatch.setattr(knowledge_route, "knowledge_search_response", _rest_spy)
    monkeypatch.setattr(knowledge_schemas, "knowledge_search_response", _mcp_spy)

    await _rest_body(client, auth_headers)
    await _mcp_body()

    assert calls == ["rest", "mcp"]


async def test_the_two_doors_share_one_answer_budget_cap(session, monkeypatch):
    """Two doors that each wrote their own cap would read their arms to
    different fusion depths for one request, and RRF is not
    truncation-consistent across depths."""
    await _corpus(session)
    seen: list[int] = []
    original = LayerCompositionService.search

    async def _spy(self, query, **kwargs):
        seen.append(kwargs["limit"])
        return await original(self, query, **kwargs)

    monkeypatch.setattr(LayerCompositionService, "search", _spy)

    await _mcp_body(limit=KNOWLEDGE_SEARCH_MAX_LIMIT * 10)
    assert seen == [KNOWLEDGE_SEARCH_MAX_LIMIT]


async def test_the_route_bounds_its_budget_at_the_shared_cap(
    client, auth_headers, session
):
    """The one stated wire asymmetry on the budget: REST validates where the
    tool clamps. Both edges are asserted, because only the pair pins the same
    bound — a route that refused past the cap and *also* refused at it would
    leave a request the tool answers unanswerable here, which is a capability
    asymmetry rather than a wire one.
    """
    await _corpus(session)

    assert (
        await _rest(client, auth_headers, limit=KNOWLEDGE_SEARCH_MAX_LIMIT + 1)
    ).status_code == 422
    assert (
        await _rest(client, auth_headers, limit=KNOWLEDGE_SEARCH_MAX_LIMIT)
    ).status_code == 200


async def test_an_unauthenticated_request_is_refused(client, session):
    """The trust posture, recorded rather than asserted away: the route is
    authenticated and its twin is not, the same pairing every two-door read on
    this table carries. It is why the parity above is taken over one session —
    an operator can aim the two doors at different row sets, and order parity
    means anything only within an equal one."""
    await _corpus(session)
    response = await client.post(ROUTE, json={"query": QUERY, "project": PROJECT})
    assert response.status_code in (401, 403)


# ── Done-when 3: the two doors rank the same, on the order ───────────


async def test_the_two_doors_rank_one_corpus_identically(
    client, auth_headers, session
):
    rows = await _corpus(session)
    await _seed_fact(session, sourced_by=rows["both"])

    rest = _order(await _rest_body(client, auth_headers))
    tool = _order(await _mcp_body())

    assert rest, "the fixture must retrieve something or the parity is vacuous"
    assert any(entry.startswith("  ") for entry in rest), (
        "the fixture must nest a memory under a fact, or the nested order is "
        "compared over an empty list"
    )
    assert rest == tool


async def test_the_parity_fixture_can_tell_two_orderings_apart(
    client, auth_headers, session
):
    """The fixture's own competence check. If the composed order coincided with
    the semantic-only order on this corpus, the assertion above would pass
    against a door that had lost its keyword arm entirely and would be worth
    nothing."""
    rows = await _corpus(session)

    semantic_only = [
        f"memory:{row['memory_id']}"
        for row in await PostgresVectorRepository(session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT, limit=20,
            filters=MemoryFilter(project=PROJECT),
        )
    ]
    served = _order(await _rest_body(client, auth_headers))

    assert served != semantic_only
    # The keyword-only row is the one a semantic-only ranking puts last.
    assert semantic_only[-1] == f"memory:{rows['keyword_only']}"
    assert served.index(f"memory:{rows['keyword_only']}") < len(served) - 1


async def test_the_doors_rank_alike_past_the_shared_fusion_depth(
    client, auth_headers, session
):
    """The corpus size at which a depth difference stops truncating and starts
    reordering.

    T2.58 fixed ``FUSION_FETCH_DEPTH`` precisely so one door's list is another's
    prefix. The fixture straddles it — the lexical match sits below every filler
    semantically, past the constant — so a door reading its arms to a shallower
    depth serves that row in a different position rather than merely serving
    fewer rows. Both assertions matter: the straddle is asserted, not assumed,
    because a fixture that fitted inside the window would compare two
    identically-truncated lists forever.
    """
    target = await _deep_corpus(session)
    # Past the corpus, so the arms are read deeper than the corpus is long and
    # the target's rank is the one the fusion actually produced rather than an
    # artefact of where the request's own budget cut.
    limit = FILLERS + 20

    semantic = [
        str(row["memory_id"])
        for row in await PostgresVectorRepository(session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT, limit=limit,
            filters=MemoryFilter(project=PROJECT),
        )
    ]
    assert len(semantic) > FUSION_FETCH_DEPTH, (
        "the corpus fits inside the shared fusion depth, so this test compares "
        "two lists that could not have differed"
    )
    assert semantic[-1] == target, "the target must be the least similar row"
    assert semantic.index(target) >= FUSION_FETCH_DEPTH, (
        "the target is reachable at the default depth, so its rank does not "
        "depend on how deep the arms were read"
    )

    rest = _order(await _rest_body(client, auth_headers, limit=limit))
    tool = _order(await _mcp_body(limit=limit))

    # The clause first, so a genuine divergence is reported as one; the
    # fixture guard second, because two doors that truncated identically would
    # agree here and still be comparing a list the budget cut.
    assert rest == tool
    assert len(rest) == FILLERS + 1, (
        "every seeded row must reach the answer, or the comparison is over a "
        "list the request's own budget cut before the depth could matter"
    )
    # Read to this depth the target fuses a deep semantic contribution onto a
    # rank-one keyword one and lands mid-list; a shallower read leaves it
    # keyword-only and further down. Pinning the position is what makes a
    # depth divergence a failure rather than a coincidence.
    assert 0 < rest.index(f"memory:{target}") < len(rest) - 1


async def test_neither_door_constructs_the_composition_with_a_reranker(session):
    """T2.72's finding 2, as a build failure rather than a review note.

    ``LayerCompositionService`` takes its reranker as a **constructor
    argument**, so reranking is a property of whoever built the service rather
    than of the composition. A door that passed one would rank differently from
    its twin while every row-shape parity test stayed green, and
    ``envelope.reranked`` would report the difference on one door only.

    The scan is deliberately total rather than door-scoped: activating the
    reranker is a both-doors decision that must be taken inside the service and
    re-measured (the arm-activation discipline ``rank_fusion.RANK_ARMS``
    carries), so a caller reintroducing the asymmetry fails here whichever
    module it lives in.

    **What it does not catch:** a reranker passed positionally (the parameter is
    keyword-only, so this is a TypeError rather than a silent divergence), one
    assigned after construction (``service.reranker = …``, an ``Attribute``
    target), and anything outside ``backend/app``.
    """
    app_root = pathlib.Path(knowledge_route.__file__).resolve().parents[2]
    offenders = []
    for path in sorted(app_root.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "LayerCompositionService":
                continue
            if any(keyword.arg == "reranker" for keyword in node.keywords):
                offenders.append(f"{path.relative_to(app_root.parent)}:{node.lineno}")
    assert offenders == [], (
        "a caller constructs the composition with a reranker of its own, so "
        f"its ranking is no longer its twin's: {offenders}"
    )


async def test_the_doors_construct_and_call_the_composition_identically(
    client, auth_headers, session, monkeypatch
):
    """The behavioural half of the same property. The scan above sees a literal
    keyword; this sees whatever each door actually passed, including a reranker
    resolved at runtime and any scope axis one door defaults differently."""
    await _corpus(session)
    seen: list[dict] = []
    original_init = LayerCompositionService.__init__
    original_search = LayerCompositionService.search

    def _init(self, llm, session_, *, reranker=None):
        seen.append({"reranker": reranker})
        original_init(self, llm, session_, reranker=reranker)

    async def _search(self, query, **kwargs):
        seen[-1].update({"query": query, **kwargs})
        return await original_search(self, query, **kwargs)

    monkeypatch.setattr(LayerCompositionService, "__init__", _init)
    monkeypatch.setattr(LayerCompositionService, "search", _search)

    await _rest_body(client, auth_headers)
    await _mcp_body()

    assert len(seen) == 2
    assert seen[0]["reranker"] is None
    assert seen[0] == seen[1]


async def test_the_served_ids_are_normalised_strings_that_resolve(
    client, auth_headers, session
):
    """Invariant 9. The hybrid arms emit ``str`` and the vector repository emits
    ``UUID``; a consumer that fails to normalise at the boundary drops the match
    with no error at all."""
    rows = await _corpus(session)

    body = await _rest_body(client, auth_headers)
    served = {row["id"] for row in body["rows"] if row["id_kind"] == "memory"}

    assert all(isinstance(row["id"], str) for row in body["rows"])
    assert served == set(rows.values())


# ── Done-when 2: empty, unavailable and broken are three answers ─────


async def test_an_empty_vault_answers_two_hundred_with_an_envelope(
    client, auth_headers, session
):
    await _seed_partition(session)

    response = await _rest(client, auth_headers)
    tool = await _mcp_body()

    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["envelope"]["partial"] is False
    assert "status" not in body, (
        "an empty vault must not carry the unavailability marker; the two are "
        "the exact pair invariant 14 requires a reader to tell apart"
    )
    assert tool == body


async def test_every_channel_down_is_unavailable_at_both_doors(
    client, auth_headers, session, monkeypatch
):
    """The other side of the same pair. An empty ``rows`` list on its own is
    indistinguishable from a vault that holds nothing, so the outage says so —
    and says it out of the record the composition built rather than out of what
    the door believes it asked."""
    await _corpus(session)
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _boom())
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _boom())

    response = await _rest(client, auth_headers)
    tool = await _mcp_body()

    assert response.status_code == 503
    body = response.json()
    # The app's own error envelope, and the word in it is the word the tool
    # uses: ``_HTTP_ERROR_CODES[503]`` is "unavailable" and so is the tool's
    # ``status``. tests/test_envelope.py pins that agreement across the doors.
    assert body["error"]["code"] == "unavailable"
    unavailable = body["error"]["details"][0]
    assert unavailable["status"] == "unavailable"
    assert unavailable["reason"] == body["error"]["message"]
    assert unavailable["rows"] == []
    assert unavailable["channels"] == {
        name: status.model_dump()
        for name, status in outage_channels(fact_asked=True).items()
    }
    assert tool["status"] == "unavailable"
    assert tool["rows"] == []
    assert tool["channels"] == unavailable["channels"]
    assert "envelope" not in tool


async def test_a_composition_defect_is_not_served_as_unavailable(
    client, auth_headers, session, monkeypatch
):
    """T2.72's finding 1, over a healthy vault.

    ``derive_rerank_scores`` and the grouping fixpoint both raise plain
    ``RuntimeError`` for a defect in this module's own code. While the doors
    caught that base, such a bug arrived as ``{"status": "unavailable"}`` on a
    vault whose every channel had answered — sending an operator to the
    database and the channel list for a fault that is in neither.
    """
    await _corpus(session)

    async def _defect(self, query, rows):
        raise RuntimeError("the reranker returned 3 rows for a window of 5")

    monkeypatch.setattr(LayerCompositionService, "derive_rerank_scores", _defect)

    with pytest.raises(RuntimeError) as rest_raised:
        await _rest(client, auth_headers)
    with pytest.raises(RuntimeError) as tool_raised:
        await _mcp_body()

    for raised in (rest_raised, tool_raised):
        assert not isinstance(raised.value, CompositionUnavailable)
        assert "window" in str(raised.value)


async def test_a_one_sided_outage_reaches_the_route_as_partial(
    client, auth_headers, session, monkeypatch
):
    """Invariant 14 through this door: a degraded answer must be readable as
    degraded, or a short list reads as a small corpus."""
    await _seed_fact(session)
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _boom())

    body = await _rest_body(client, auth_headers)

    assert body["envelope"]["partial"] is True
    assert body["envelope"]["channels"]["memory.semantic"]["failed"] is True
    assert body["rows"], "a one-sided outage degrades, it does not empty"


async def test_the_route_scopes_every_channel_to_the_named_project(
    client, auth_headers, session, monkeypatch
):
    """``project`` is required by the composition and pushed down by both
    channels; the route must forward the caller's value rather than defaulting
    past it."""
    seen: dict[str, object] = {}

    async def _memory(self, query, *, limit=20, filters=None, **kwargs):
        seen["memory"] = getattr(filters, "project", None)
        return hybrid_search.ChannelTrace(results=[])

    async def _facts(self, query, *, project, limit=20, **kwargs):
        seen["fact"] = project
        return facts_channel.FactChannelTrace(results=[])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    await _rest_body(client, auth_headers, project="t280-elsewhere")

    assert seen == {"memory": "t280-elsewhere", "fact": "t280-elsewhere"}


def _boom():
    async def _raise(self, *args, **kwargs):
        raise RuntimeError("channel down")

    return _raise
