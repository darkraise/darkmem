"""Chat and the search surface rank one corpus one way (T2.58).

Doc 07 §9 and invariant 17: every read consumer spends one ranking path, so a
behaviour cannot exist on one front door and not the other. Chat used to spend
a second one — ``vector_repo.search``, semantic-only — and the divergence it
caused was invisible, because both doors returned plausible rows in a plausible
order and nothing compared them.

The four properties here, each with the mutation that breaks it:

* **Parity is asserted on the order, not on the call.** A test that only
  checked which function chat calls would pass with the fusion mis-parameterised
  on one side (a different ``semantic_weight``, a different scope, a lost
  keyword arm); the assertions below compare the id sequences two doors produce
  over one seeded corpus and one fixed query.
* **The fusion is real.** A row the semantic arm ranks last and the keyword arm
  ranks first must move, so the fixture is built so semantic-only order and
  fused order *disagree* — otherwise a regression to the old path would still
  pass.
* **``rrf_score`` is the ordering signal.** Fused rows keep a per-modality
  ``score`` key that means something different per row, so the fixture also
  makes ``score``-descending order disagree with the served order.
* **Chat's own scope survives the move.** Its rows land in a prompt verbatim,
  so a superseded, deprecated, archived or foreign row must never reach one —
  the composition's default is every lifecycle state, and chat passes its own.

Plus the constant scan Done-when 3 asks for, which is a *declaration* check
rather than a literal check; its exact reach and its blind spots are stated on
the test itself.

**What none of this can see.** The two doors agree exactly while the rank arms
sit at their default zero, which is the shipped state and the state every gate
measures. They are not proven to agree under an activated arm: the memory search
surface multiplies the arm factor onto ``rrf_score`` and re-sorts, while the
composition multiplies it onto a rank-derived magnitude and re-sorts within the
channel, so the two can order the same rows differently at a non-zero weight.
That is a property of converging on the composition rather than something this
task introduced — it is equally true of ``knowledge_search`` today — and it is
recorded here so an arm activation re-measures both doors instead of one.
"""

from __future__ import annotations

import ast
import math
import pathlib
import re
import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.schemas.memory import MemorySearchRequest
from app.services.chat import CHAT_RETRIEVAL_LIMIT, CHAT_STATUSES, ChatService
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.services.memory import MemoryService

FINGERPRINT = "chat-parity|4"
DIMS = 4
QUERY = "pgbouncer connection pooling"
QUERY_VECTOR = [1.0, 0.0, 0.0, 0.0]
PROJECT = "chat-parity"
FOREIGN = "chat-parity-foreign"


class _FakeLLM:
    """Only ``embed`` and the streaming completion are reached below."""

    async def embed(self, query: str):
        return QUERY_VECTOR, FINGERPRINT

    async def chat_completion(self, purpose, messages=None, **kwargs):
        return "answer"

    async def chat_completion_stream(self, purpose, messages=None, **kwargs):
        yield "answer"


class _SearchSurfacePipeline:
    """What ``MemoryService``'s traced path reaches: an ``llm`` and nothing else.

    The traced path builds its own ``HybridSearchService`` off this ``llm``, so
    the search surface under test is the production one rather than a stand-in
    for it.
    """

    def __init__(self):
        self.llm = _FakeLLM()


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "chat-parity", "dims": DIMS},
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


async def _add_memory(session, *, vector: list[float], **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="pgbouncer connection pooling notes",
        source="test",
        importance=0.5,
        metadata_={},
        project=PROJECT,
        status="active",
        memory_type="fact",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()

    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), CAST(:payload AS jsonb))"
        ),
        {
            "mid": base["id"], "fp": FINGERPRINT, "vec": str(vector),
            "payload": '{"content": "seeded", "source": "test", "tags": []}',
        },
    )
    await session.flush()
    return memory


async def _corpus(session) -> dict[str, Memory]:
    """Six rows whose semantic order and keyword order deliberately disagree.

    ``keyword_only`` is orthogonal to the query vector and lexically closest to
    the query; ``semantic_only`` is the nearest vector and shares no query term.
    A semantic-only ranking puts the second first and the first last (or drops
    it), so any assertion below that passes on the fused order fails on the
    pre-T2.58 one.
    """
    await _seed_partition(session)
    rows = {
        "semantic_only": await _add_memory(
            session, vector=[1.0, 0.0, 0.0, 0.0],
            content="the box runs a database proxy on the LAN",
        ),
        "both": await _add_memory(
            session, vector=[0.92, 0.39, 0.0, 0.0],
            content="pgbouncer connection pooling is configured in transaction mode",
        ),
        "middle": await _add_memory(
            session, vector=[0.7, 0.71, 0.0, 0.0],
            content="connection pooling notes for the homelab",
        ),
        "keyword_only": await _add_memory(
            session, vector=[0.0, 0.0, 1.0, 0.0],
            content="pgbouncer connection pooling was chosen over pgcat",
        ),
        "retired": await _add_memory(
            session, vector=[0.99, 0.14, 0.0, 0.0], status="deprecated",
            content="pgbouncer connection pooling ran in session mode",
        ),
        "foreign": await _add_memory(
            session, vector=[0.98, 0.19, 0.0, 0.0], project=FOREIGN,
            content="pgbouncer connection pooling on someone else's box",
        ),
    }
    return rows


FILLERS = 35


async def _deep_corpus(session) -> Memory:
    """A corpus deeper than a chat turn's arm window used to reach.

    ``FILLERS`` rows carry descending similarity to the query vector and not
    one query term, so the keyword arm never sees them. The returned target
    sits below every one of them semantically and matches the query lexically,
    which makes its rank a function of **how deep the arms were read**: inside
    the window it fuses a mid-list semantic contribution onto a rank-one
    keyword contribution and comes first, outside it, it is keyword-only and
    falls below every filler. The doors used to read to different depths, so
    on this corpus the search surface answered with a row chat never served.
    """
    await _seed_partition(session)
    for i in range(FILLERS):
        angle = 0.02 * (i + 1)
        await _add_memory(
            session,
            vector=[math.cos(angle), math.sin(angle), 0.0, 0.0],
            content=f"the box runs a database proxy on the LAN, note {i}",
        )
    return await _add_memory(
        session,
        vector=[math.cos(1.2), math.sin(1.2), 0.0, 0.0],
        content="pgbouncer connection pooling was chosen over pgcat",
    )


_SCOPED = {"project": PROJECT}


async def _chat_ids(session, context: dict | None = _SCOPED) -> list[str]:
    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, context)
    return [row["id"] for row in retrieval["memories"]]


async def _search_surface_ids(session, *, limit: int = CHAT_RETRIEVAL_LIMIT) -> list[str]:
    """The Memories door's own ranking, through its own service and route path."""
    service = MemoryService(session, pipeline=_SearchSurfacePipeline())
    page = await service.search_memories_paginated(
        MemorySearchRequest(
            query=QUERY, project=PROJECT, status=list(CHAT_STATUSES),
            limit=limit, offset=0, with_trace=True,
        )
    )
    return [str(item.memory.id) for item in page["items"]]


# ── Done-when 4: the two doors rank one corpus one way ───────────────


async def test_a_chat_turn_and_the_search_surface_rank_the_same_corpus_alike(session):
    """The clause, on the order rather than on the call.

    Both lists are taken over the same seeded corpus, the same query and the
    same scope. The search surface over-fetches further than chat does, so the
    guarantee is that chat's list is the search surface's list restricted to
    the rows chat served — equal head, equal order, no row reordered between
    the doors.
    """
    await _corpus(session)

    chat = await _chat_ids(session)
    surface = await _search_surface_ids(session)

    assert chat, "the fixture must retrieve something or the parity is vacuous"
    assert chat == [row_id for row_id in surface if row_id in set(chat)]
    assert chat == surface[:len(chat)]


async def test_the_doors_rank_alike_on_a_corpus_deeper_than_a_turn_fetches(session):
    """Parity at one fixed depth, on the corpus size that used to break it.

    Same service and same weights is not enough: RRF is not
    truncation-consistent across depths, and the doors read to different ones.
    Chat asked its arms for ``limit x 3`` = 30 rows while the search surface
    asked for ``(limit + offset + 50) x 3``, so on 36 rows the surface's **top
    answer** was a row chat never served at all — at fully default flags, with
    both doors on the same fusion. A shape comparison cannot see that; only an
    ordering over a corpus deeper than the shallower window can.
    """
    target = await _deep_corpus(session)
    scope = MemoryFilter(project=PROJECT, statuses=CHAT_STATUSES, include_archived=False)

    semantic = [
        str(row["memory_id"])
        for row in await PostgresVectorRepository(session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT, limit=FILLERS + 1, filters=scope,
        )
    ]
    # The fixture has to straddle the window the shallow door used to read —
    # 36 rows against the retired ``limit x 3`` = 30 — or it exercises nothing.
    assert len(semantic) > 30
    assert semantic[-1] == str(target.id), "the target must be the least similar row"

    chat = await _chat_ids(session)
    surface = await _search_surface_ids(session, limit=CHAT_RETRIEVAL_LIMIT * 2)

    assert chat[0] == str(target.id), (
        "the keyword-strong row is the search surface's top answer; a turn "
        "that fuses a shallower window never sees it"
    )
    assert surface[0] == str(target.id)
    # The doors truncate at different lengths on purpose: fusing at one depth
    # is what makes the shorter list the longer one's prefix rather than a
    # second ranking.
    assert len(surface) > len(chat)
    assert chat == surface[:len(chat)]


async def test_chat_ranks_by_the_fused_order_and_not_by_the_semantic_one(session):
    """The fixture has to be able to tell the two apart, and this proves it can.

    If semantic-only order ever coincided with fused order on this corpus, the
    parity assertion above would pass against the pre-T2.58 implementation and
    would be worth nothing. So the disagreement is asserted, not assumed.
    """
    rows = await _corpus(session)
    scope = MemoryFilter(project=PROJECT, statuses=CHAT_STATUSES, include_archived=False)

    semantic_only = [
        str(row["memory_id"])
        for row in await PostgresVectorRepository(session).search(
            QUERY_VECTOR, fingerprint=FINGERPRINT,
            limit=CHAT_RETRIEVAL_LIMIT, filters=scope,
        )
    ]
    fused = [
        row["memory_id"]
        for row in (
            await HybridSearchService(_FakeLLM(), session).search_with_trace(
                QUERY, limit=CHAT_RETRIEVAL_LIMIT, filters=scope,
            )
        ).results
    ]

    assert semantic_only != fused
    # The keyword-only row is the one the old path could not rank: its vector
    # is orthogonal to the query's.
    assert semantic_only[-1] == str(rows["keyword_only"].id)
    assert fused.index(str(rows["keyword_only"].id)) < len(fused) - 1

    assert await _chat_ids(session) == fused


async def test_chat_orders_by_rrf_score_and_not_by_the_surviving_score_key(session):
    """Constraint 2: the per-modality ``score`` on a fused row is the
    first-seen side's raw number, so it means something different per row.
    Ordering by it is a live mistake, not a hypothetical one — chat's previous
    implementation read exactly that key."""
    await _corpus(session)
    scope = MemoryFilter(project=PROJECT, statuses=CHAT_STATUSES, include_archived=False)

    fused = (
        await HybridSearchService(_FakeLLM(), session).search_with_trace(
            QUERY, limit=CHAT_RETRIEVAL_LIMIT, filters=scope,
        )
    ).results
    by_raw_score = [
        row["memory_id"]
        for row in sorted(fused, key=lambda r: r["score"], reverse=True)
    ]
    by_rrf = [row["memory_id"] for row in fused]

    assert by_raw_score != by_rrf, "the fixture cannot tell the two orderings apart"
    assert await _chat_ids(session) == by_rrf


# ── the scope chat cannot lose in the move ───────────────────────────


async def test_a_chat_turn_answers_only_out_of_active_rows(session):
    """The composition serves every lifecycle state by default, labelled, which
    is right for a vault reader and wrong for a prompt: chat's rows are quoted
    to a user, so a retired row reaching one is a stale answer with no reader
    to notice the label."""
    rows = await _corpus(session)

    served = set(await _chat_ids(session))

    assert str(rows["both"].id) in served
    assert str(rows["retired"].id) not in served


async def test_a_wide_chat_turn_still_excludes_dead_and_archived_rows(session):
    """Chat's project default is every project by ratified decision, so the
    lifecycle scope is the only thing standing between a retired row and the
    prompt on this path."""
    rows = await _corpus(session)

    served = set(await _chat_ids(session, context=None))

    assert str(rows["foreign"].id) in served
    assert str(rows["retired"].id) not in served


async def test_the_ids_a_turn_serves_are_normalised_strings_that_resolve(session):
    """Invariant 9. The hybrid arms emit ``str`` and the vector repository
    emits ``UUID``; chat crossed that boundary in this task, and a consumer
    that fails to normalise drops the match with no error at all."""
    rows = await _corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, {"project": PROJECT})

    live = {str(rows[key].id) for key in ("semantic_only", "both", "middle", "keyword_only")}
    assert all(isinstance(row["id"], str) for row in retrieval["memories"])
    assert {row["id"] for row in retrieval["memories"]} == live


# ── Done-when 2's input: the envelope a panel can render ─────────────


async def test_a_turn_carries_the_envelope_and_its_exclusion_counts(session):
    await _corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, {"project": PROJECT})
    envelope = retrieval["envelope"]

    assert envelope["query"] == QUERY
    assert envelope["channels"]["memory.semantic"] == {"ran": True, "failed": False}
    assert envelope["channels"]["memory.keyword"] == {"ran": True, "failed": False}
    assert envelope["partial"] is False
    # Both tallies are present at zero: a suppressed count reads as "no check
    # ran", which is the case a reader most needs to tell apart.
    assert envelope["excluded"]["by_context_conflict"] == 0
    assert envelope["excluded"]["by_result_limit"] == 0
    assert envelope["excluded"]["not_found"] == 0


async def test_every_served_row_carries_the_arm_scores_that_ranked_it(session):
    """The per-row half of doc 07 §8. The arms are the only place these numbers
    exist, so a composed row alone can say *that* a row ranked and never *why*;
    a panel handed only the row would have to invent the breakdown or omit it.

    The keyword-only row is the case that matters: it has a keyword score and
    is the one row the pre-convergence path could not have scored at all.
    """
    rows = await _corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, {"project": PROJECT})
    by_id = {row["id"]: row for row in retrieval["memories"]}

    keyword_only = by_id[str(rows["keyword_only"].id)]
    assert keyword_only["scores"]["keyword"] > 0
    assert keyword_only["scores"]["rrf_score"] > 0
    # Orthogonal to the query vector, so the semantic arm still ranked it —
    # what it must not do is claim a score the arm never produced.
    assert set(keyword_only["scores"]) <= {"semantic", "keyword", "rrf_score"}

    semantic_only = by_id[str(rows["semantic_only"].id)]
    assert semantic_only["scores"]["semantic"] > 0
    assert "keyword" not in semantic_only["scores"]


async def test_a_wide_turn_says_the_fact_channel_was_not_asked(session):
    """The facts channel is born with its project pushed into both arms' SQL,
    so a wide request has no arm to ask. ``ran=False`` says that; ``failed``
    would report an outage that did not happen, and omitting the keys would
    make "not asked" indistinguishable from "asked and empty"."""
    await _corpus(session)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, None)
    channels = retrieval["envelope"]["channels"]

    assert retrieval["facts"] == []
    assert channels["fact.keyword"] == {"ran": False, "failed": False}
    assert channels["fact.name"] == {"ran": False, "failed": False}
    assert retrieval["envelope"]["partial"] is False


async def test_a_row_that_vanishes_between_ranking_and_reading_is_counted(session):
    """The composition ordered it, so its absence from the answer is this
    request's own exclusion to declare. Uncounted, a row deleted mid-request
    would leave a context one row shorter than the ranking that built it, with
    nothing anywhere saying so."""
    await _corpus(session)
    ghost = str(uuid.uuid4())

    async def _with_ghost(self, query, **kwargs):
        from app.services import hybrid_search

        real = await original(self, query, **kwargs)
        return hybrid_search.ChannelTrace(
            results=[*real.results, {
                "memory_id": ghost, "score": 0.1, "rrf_score": 0.001,
                "payload": {"content": "gone"}, "project": PROJECT, "status": "active",
            }],
            channel_scores=real.channel_scores,
        )

    original = HybridSearchService.search_with_trace
    HybridSearchService.search_with_trace = _with_ghost
    try:
        svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
        retrieval = await svc._retrieve(QUERY, {"project": PROJECT})
    finally:
        HybridSearchService.search_with_trace = original

    assert ghost not in {row["id"] for row in retrieval["memories"]}
    assert retrieval["envelope"]["excluded"]["not_found"] == 1


async def test_a_fact_reaches_the_prompt_with_its_claim_verbatim(session, monkeypatch):
    """A layer that is retrieved and then dropped from the prompt is worse than
    one never asked for: the panel would show it as context this turn used
    while the model never saw it. The claim rides through as the producer built
    it — a paraphrase inside a prompt is a second, softer claim."""
    await _corpus(session)
    fact_id = str(uuid.uuid4())

    from app.services import facts_channel

    async def _facts(self, *args, **kwargs):
        return facts_channel.FactChannelTrace(results=[{
            "fact_id": fact_id, "id": fact_id,
            "fact": "pgbouncer is the pooler in use",
            "subject_name": "pgbouncer", "rel_type": "DEPLOYED_ON",
            "object_name": "homelab", "project": PROJECT,
            "verification_status": "corroborated", "review_state": None,
            "rrf_score": 0.1,
        }])

    monkeypatch.setattr(facts_channel.FactsChannel, "search_with_trace", _facts)

    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
    retrieval = await svc._retrieve(QUERY, {"project": PROJECT})
    served = retrieval["facts"]
    assert [row["id"] for row in served] == [fact_id]
    claim = served[0]["badge"]["claim"]
    assert claim

    conversation = await svc.create_conversation()
    messages = await svc._build_prompt(conversation.id, QUERY, retrieval)
    system = messages[0]["content"]
    assert "<verified_facts>" in system
    assert "pgbouncer is the pooler in use" in system
    assert claim in system


async def test_a_one_sided_channel_outage_reaches_the_turn_as_partial(session):
    """Invariant 14 through chat's own door: a degraded turn must be readable
    as degraded, or a short context reads as a small corpus."""
    await _corpus(session)

    async def _boom(self, *args, **kwargs):
        raise RuntimeError("keyword arm down")

    original = HybridSearchService._keyword_search
    HybridSearchService._keyword_search = _boom
    try:
        svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))
        retrieval = await svc._retrieve(QUERY, {"project": PROJECT})
    finally:
        HybridSearchService._keyword_search = original

    assert retrieval["envelope"]["channels"]["memory.keyword"]["failed"] is True
    assert retrieval["envelope"]["partial"] is True
    assert retrieval["memories"], "a one-sided outage degrades, it does not empty"


async def test_the_persisted_turn_keeps_the_envelope_it_answered_under(session):
    """The stored snapshot is what the panel renders for every past turn, so an
    envelope that lives only on the live stream leaves history unexplainable."""
    await _corpus(session)
    svc = ChatService(session, _FakeLLM(), PostgresGraphRepository(session))

    message_id = None
    async for event in svc.send_message(None, QUERY, {"project": PROJECT}):
        if event["type"] == "sources":
            assert event["envelope"]["query"] == QUERY
        if event["type"] == "done":
            message_id = uuid.UUID(event["message_id"])

    from app.models.chat import Message
    stored = await session.get(Message, message_id)
    assert stored.context["envelope"]["channels"]["memory.keyword"]["ran"] is True
    assert stored.context["memories"], "the citations must survive with the envelope"


# ── Done-when 3: one RRF constant, enforced ──────────────────────────

APP_ROOT = pathlib.Path(__file__).resolve().parents[1] / "app"
CANONICAL = APP_ROOT / "services" / "rank_fusion.py"

# Names that could carry an RRF constant, in either of the two spellings one
# can arrive in: the constant convention (``RRF_K``, upper case, any value at
# all), and a lower-case name bound to a bare number, which is what a constant
# smuggled in as an ordinary variable looks like. A lower-case name bound to
# anything else — ``cross_layer_rrf`` the function, ``rrf_score`` off a row —
# is a computation over the one constant rather than a second copy of it, and
# flagging those would make the scan noise a reader learns to skip.
RRF_NAME = re.compile(r"(^|_)rrf(_|$)", re.IGNORECASE)
RRF_CONSTANT_NAME = re.compile(r"(^|_)RRF(_|$)")


def _python_sources() -> list[pathlib.Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _bound_names(target: ast.expr):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _bound_names(element)
    elif isinstance(target, ast.Starred):
        yield from _bound_names(target.value)


def _declarations(tree: ast.AST):
    """Every name this module *binds* that could be a second RRF constant.

    A binding, never a literal: a scan for ``60`` proves nothing (the number is
    a coincidence away from being right and a rename away from being wrong),
    while a scan for the write is exactly the event that creates a second
    source of truth. Assignment, annotated assignment, augmented assignment and
    the walrus all bind, and all four are walked. An annotation with no value
    (``cross_layer_rrf: float`` on a dataclass) binds nothing at runtime and is
    not one.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            if node.value is None:
                continue
            targets, value = [node.target], node.value
        elif isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            targets, value = [node.target], node.value
        else:
            continue
        numeric = isinstance(value, ast.Constant) and isinstance(value.value, (int, float))
        for name in (n for t in targets for n in _bound_names(t)):
            if RRF_CONSTANT_NAME.search(name) or (RRF_NAME.search(name) and numeric):
                yield name, node.lineno


def test_no_second_rrf_constant_is_declared_outside_rank_fusion():
    """``code_query.py`` held one for long enough that CLAUDE.md recorded the
    drift and named no owner for it. This is the owner.

    **What this catches:** any module under ``app/`` binding an upper-case
    ``RRF``-named name at any value, or a lower-case ``rrf`` name bound to a
    bare number — module level, class body or function body, plain, annotated,
    augmented or walrus.

    **What it does not:** a constant named without the letters ``rrf``
    (``K = 60``, ``FUSION_K``), a bare inlined ``1.0 / (60 + rank)`` that binds
    nothing at all, a value smuggled through a mutable container
    (``TUNING["rrf_k"] = 55``, a ``Subscript`` target rather than a ``Name``),
    and anything outside ``backend/app``. The second leg below narrows the
    first blind spot from the other side; the arithmetic one is deliberately
    left to review, because a scan able to recognise it would flag every
    unrelated reciprocal in the tree.
    """
    offenders = []
    for path in _python_sources():
        if path == CANONICAL:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders += [
            f"{path.relative_to(APP_ROOT.parent)}:{line} declares {name}"
            for name, line in _declarations(tree)
        ]
    assert offenders == [], (
        "a second RRF constant is declared outside rank_fusion.py: "
        + "; ".join(offenders)
    )


def test_every_module_that_ranks_by_rrf_k_imports_it_from_rank_fusion():
    """The other half: a module may not obtain the constant from a copy.

    Without this, deleting a declaration and importing it from whichever module
    happened to re-export it would satisfy the first leg while leaving two
    places able to change what ``RRF_K`` means.
    """
    offenders = []
    for path in _python_sources():
        if path == CANONICAL:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        used = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and RRF_CONSTANT_NAME.search(node.id)
        }
        if not used:
            continue
        imported = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").endswith("rank_fusion")
            for alias in node.names
        }
        missing = sorted(used - imported)
        if missing:
            offenders.append(f"{path.relative_to(APP_ROOT.parent)} uses {missing}")
    assert offenders == [], (
        "these modules read an RRF constant they did not import from "
        "rank_fusion.py: " + "; ".join(offenders)
    )


def test_chat_holds_no_second_ranking_path():
    """The convergence as a structural property rather than a behavioural one.

    Chat's defect was not a wrong ordering — it was owning the machinery to
    produce one. A regression would most plausibly arrive as a "fallback" for
    the case where the composition returns nothing, so the import itself is
    what is pinned.
    """
    tree = ast.parse((APP_ROOT / "services" / "chat.py").read_text(encoding="utf-8"))
    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {"PostgresVectorRepository", "HybridSearchService", "rrf_fuse", "RankedList"}
    assert imported & forbidden == set(), (
        "chat imported a ranking primitive of its own: "
        f"{sorted(imported & forbidden)}"
    )
    assert "vector_repo" not in (APP_ROOT / "services" / "chat.py").read_text(encoding="utf-8")
