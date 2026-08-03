"""The vault's MCP tools — ``fact_get`` and ``knowledge_search`` (T2.72).

Doc 12 §2 assigns ``fact_get`` a REST twin at ``GET /knowledge/facts/{id}``
and §3 puts the agent-facing vault reads on these two tools. Neither existed,
so the detail route sat filed REST-only on a trust-posture argument that does
not decide door count — every two-door read in this repo already pairs an
unauthenticated tool with an authenticated route.

What this module pins, and why each one is here rather than left to review:

* **One service, two doors (invariant 17).** ``code_search`` and
  ``code_blast_radius`` shared a capability, held parallel implementations,
  and had already drifted by the time anyone looked. So the tools are asserted
  to *reach* the shared service, not merely to answer plausibly — a tool that
  grew its own query would still return rows.
* **The badge is read, never rendered.** ``fact_badge`` is the claim's sole
  producer. The assertion below compares the served badge against that
  producer's own output for the same fact, so a tool that formatted its own
  sentence fails here as well as under T2.71's scan.
* **A caller error raises; unavailability is typed.** Doc 12 §3 draws that
  line explicitly: a bad UUID or a missing id is the caller's mistake, and
  returning it as ``{"status": "unavailable"}`` teaches an agent to read its
  own bug as an outage. A composition with every channel down is the other
  case, and an empty ``rows`` list without that status would be the one shape
  invariant 14 forbids — indistinguishable from a genuine no-match.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

import app.services.facts_channel as facts_channel
import app.services.hybrid_search as hybrid_search
import app.services.layer_composition as layer_composition
from app.api.mcp import server as mcp_server
from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository

pytestmark = pytest.mark.asyncio

PROJECT = "t272-vault"
AT = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def mcp_session(session, monkeypatch):
    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", None)
    return session


async def _seed_fact(session, *, project: str = PROJECT, origins=("origin-a",)) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"t272-{uuid.uuid4()}",
        subject_name="darkmem",
        object_name="postgres",
        rel_type="USES",
        fact="darkmem USES postgres",
        reference_time=AT,
        project=project,
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
    for origin in origins:
        await sources.add_source(
            fact_id=row["id"],
            source_kind="memory",
            source_ref=str(uuid.uuid4()),
            origin_key=origin,
        )
    await session.flush()
    return str(row["id"])


async def _seed_memory(session, content: str, *, project: str = PROJECT) -> str:
    memory_id = uuid.uuid4()
    session.add(
        Memory(id=memory_id, content=content, source="test", project=project)
    )
    await session.flush()
    return str(memory_id)


def _memory_row(memory_id: str, *, content: str, project: str = PROJECT) -> dict:
    return {
        "memory_id": memory_id,
        "payload": {"content": content},
        "project": project,
        "status": "active",
        "rrf_score": 0.4,
    }


def _fact_row(fact_id: str, *, project: str = PROJECT) -> dict:
    return {
        "fact_id": fact_id,
        "id": fact_id,
        "fact": "darkmem USES postgres",
        "subject_name": "darkmem",
        "rel_type": "USES",
        "object_name": "postgres",
        "project": project,
        "verification_status": "corroborated",
        "review_state": None,
        "rrf_score": 0.5,
    }


def _stub_channels(monkeypatch, *, memories=(), facts=()):
    async def _memory(self, *args, **kwargs):
        return hybrid_search.ChannelTrace(results=list(memories))

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=list(facts))

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)


def _boom(*_args, **_kwargs):
    async def _raise(self, *a, **kw):
        raise RuntimeError("channel down")

    return _raise


# ─────────────────────────────── fact_get ───────────────────────────────


async def test_fact_get_answers_through_the_shared_service(session, monkeypatch):
    """The tool must reach ``facts_read.get_fact``, the function the REST
    route spends. A hand-rolled query would answer plausibly and drift."""
    from app.services import facts_read

    fact_id = await _seed_fact(session)

    calls = []
    original = facts_read.get_fact

    async def spy(*args, **kwargs):
        calls.append(str(args[1] if len(args) > 1 else kwargs["fact_id"]))
        return await original(*args, **kwargs)

    monkeypatch.setattr(facts_read, "get_fact", spy)

    body = json.loads(await mcp_server.fact_get(fact_id=fact_id))
    assert calls == [fact_id]
    assert body["id"] == fact_id
    assert body["id_kind"] == "fact"
    assert body["badge"]["claim"]
    assert body["sources"], "the detail read owes the provenance groups"


async def test_fact_get_raises_on_an_id_that_is_not_there(session):
    """Doc 12 §3: a missing id is a caller error and raises. Returning the
    typed unavailable envelope here would teach an agent to read its own bad
    id as the server being down."""
    with pytest.raises(ValueError, match="Fact not found"):
        await mcp_server.fact_get(fact_id=str(uuid.uuid4()))


async def test_fact_get_raises_on_a_malformed_id(session):
    with pytest.raises(ValueError, match="Invalid UUID"):
        await mcp_server.fact_get(fact_id="not-a-uuid")


async def test_fact_get_serves_a_belief_withdrawn_fact(session):
    """A window-closed fact is retained history, not a withdrawn read: the
    id-addressed door serves it and the belief window says which it is. A
    door that 404'd here would make the vault's own bookkeeping unreadable
    at exactly the row a reader is checking."""
    fact_id = await _seed_fact(session)
    await KnowledgeTripleRepository(session).close_window(fact_id, AT)
    await session.flush()

    body = json.loads(await mcp_server.fact_get(fact_id=fact_id))
    assert body["belief_window"]["invalid_at"] is not None


# ──────────────────────────── knowledge_search ────────────────────────────


async def test_knowledge_search_composes_both_layers(session, monkeypatch):
    """A fact and its supporting memory arrive as one group, not two rows.

    The nesting is what makes the answer budget spend on distinct claims
    rather than on a fact and the memory restating it, so the count is the
    assertion rather than mere presence.
    """
    fact_id = await _seed_fact(session)
    memory_id = await _seed_memory(session, "postgres is the store")
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref=memory_id,
        origin_key="origin-b",
    )
    await session.flush()

    _stub_channels(
        monkeypatch,
        memories=[_memory_row(memory_id, content="postgres is the store")],
        facts=[_fact_row(fact_id)],
    )

    body = json.loads(await mcp_server.knowledge_search(query="postgres", project=PROJECT))

    assert [row["id_kind"] for row in body["rows"]] == ["fact"]
    row = body["rows"][0]
    assert row["id"] == fact_id
    assert row["layer"] == "L2"
    assert row["text"] == "darkmem USES postgres"
    assert row["labels"]["project"] == PROJECT
    assert row["labels"]["verification_status"] == "corroborated"
    assert row["grouping"] is not None
    assert [nested["id"] for nested in row["supported_by"]] == [memory_id]

    nested = row["supported_by"][0]
    assert nested["labels"]["status"] == "active"
    assert nested["labels"]["badge"] is None, (
        "an L0 row carries no badge: nothing adjudicated it"
    )
    assert nested["text"] == "postgres is the store"


async def test_the_badge_is_the_producers_and_is_not_rendered_by_the_tool(
    session, monkeypatch
):
    """The served badge must equal ``fact_badge``'s own output for that fact.

    This is the assertion a second producer fails. Comparing the whole object
    rather than the claim alone means a tool that kept the producer's claim
    and recomputed the origin count beside it fails too.
    """
    from app.services.fact_badge import badges_for_facts

    fact_id = await _seed_fact(session, origins=("origin-a", "origin-b"))
    _stub_channels(monkeypatch, facts=[_fact_row(fact_id)])

    body = json.loads(await mcp_server.knowledge_search(query="postgres", project=PROJECT))
    served = body["rows"][0]["labels"]["badge"]

    row = {**_fact_row(fact_id), "id": fact_id}
    expected = (await badges_for_facts(session, [row]))[fact_id].as_dict()
    assert served == json.loads(json.dumps(expected, default=str))
    assert served["origin_count"] == 2


async def test_knowledge_search_spends_the_shared_composition(session, monkeypatch):
    """Invariant 17's real content: the tool must reach
    ``LayerCompositionService.search``. A tool that fanned out to the two
    channels itself would answer rows and skip the ordering, the tiering, the
    grouping and the envelope."""
    _stub_channels(monkeypatch, facts=[_fact_row(await _seed_fact(session))])

    calls = []
    original = layer_composition.LayerCompositionService.search

    async def spy(self, query, **kwargs):
        calls.append((query, kwargs.get("project"), kwargs.get("limit")))
        return await original(self, query, **kwargs)

    monkeypatch.setattr(layer_composition.LayerCompositionService, "search", spy)

    await mcp_server.knowledge_search(query="postgres", project=PROJECT, limit=7)
    assert calls == [("postgres", PROJECT, 7)]


async def test_knowledge_search_clamps_an_unbounded_limit(session, monkeypatch):
    _stub_channels(monkeypatch, facts=[_fact_row(await _seed_fact(session))])

    calls = []
    original = layer_composition.LayerCompositionService.search

    async def spy(self, query, **kwargs):
        calls.append(kwargs.get("limit"))
        return await original(self, query, **kwargs)

    monkeypatch.setattr(layer_composition.LayerCompositionService, "search", spy)

    await mcp_server.knowledge_search(query="postgres", project=PROJECT, limit=10_000)
    assert calls == [mcp_server._MAX_LIMIT]


async def test_the_envelope_reports_a_one_sided_outage(session, monkeypatch):
    """A surviving layer is served and the envelope says the other one fell
    over. Dropping the envelope on the tool door would leave an agent unable
    to tell a half-answer from a whole one (invariant 14)."""
    _stub_channels(monkeypatch, facts=[_fact_row(await _seed_fact(session))])
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _boom())

    body = json.loads(await mcp_server.knowledge_search(query="postgres", project=PROJECT))

    assert body["envelope"]["partial"] is True
    assert body["envelope"]["channels"]["memory.semantic"]["failed"] is True
    assert body["envelope"]["channels"]["article.semantic"]["ran"] is False
    assert body["envelope"]["excluded"]["by_context_conflict"] == 0
    assert len(body["rows"]) == 1


async def test_every_channel_down_is_a_typed_unavailable_not_an_empty_list(
    session, monkeypatch
):
    """Doc 12 §3's degradation envelope. An empty ``rows`` list on its own is
    indistinguishable from a vault that simply holds nothing, which is the
    one shape invariant 14 forbids serving."""
    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _boom())
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _boom())

    body = json.loads(await mcp_server.knowledge_search(query="postgres", project=PROJECT))

    assert body["status"] == "unavailable"
    assert body["reason"]
    assert body["rows"] == []
    assert "envelope" not in body


async def test_knowledge_search_scopes_every_channel_to_the_named_project(
    session, monkeypatch
):
    """``project`` is a required keyword on the composition and is pushed
    down by both channels; the tool must forward the caller's value rather
    than defaulting past it."""
    seen: dict[str, object] = {}

    async def _memory(self, query, *, limit=20, filters=None, **kwargs):
        seen["memory"] = getattr(filters, "project", None)
        return hybrid_search.ChannelTrace(results=[])

    async def _facts(self, query, *, project, limit=20, **kwargs):
        seen["fact"] = project
        return facts_channel.FactChannelTrace(results=[])

    monkeypatch.setattr(hybrid_search.HybridSearchService, "search_with_trace", _memory)
    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    await mcp_server.knowledge_search(query="postgres", project="t272-elsewhere")
    assert seen == {"memory": "t272-elsewhere", "fact": "t272-elsewhere"}
