"""T2.21 — the `memory_overview` map-reduce: cost, the single reduce, two doors.

**The three Done-when clauses are measured here, not read off the code.**

* *Cost is bounded by community count, not memory count.* A design that only
  looks bounded is worth nothing, so the bound is exercised against two
  corpora built to differ on exactly one axis: same topics, same reports,
  eight times the memories. The number of model calls and the reduce's input
  budget must not move, no memory's content may appear in the prompt at all,
  and — the non-vacuity half — adding *communities* must move the input,
  otherwise a bound that ignored everything would pass just as well.
* *The reduce is one call.* Counted on a stub, including the over-budget case
  where the temptation is a second pass. The excess is dropped and declared
  (`reports_omitted`, `omitted_labels`), never folded in silently.
* *Both front doors expose it.* Both are asserted to route through
  `get_overview` itself, not merely to answer similar JSON.

The structural guard is separate and deliberately not a call count: doc 09
§3.3 says the reports are precomputed and a missing one renders as pending.
"Never generates a report on read" is a negative, and a counter cannot show a
negative — the AST reachability scan below can.
"""
from __future__ import annotations

import ast
import json
import pathlib

from sqlalchemy import text

from app.repositories import memory_communities as repo
from app.services import memory_overview as overview
from app.utils.ids import new_id

from tests._reachability_scan import ReachabilityRules, find_forbidden_reach

BACKEND = pathlib.Path(__file__).resolve().parent.parent

PROJECT = "t221-overview"
OTHER_PROJECT = "t221-overview-other"

_INSERT_MEMORY = text(
    "INSERT INTO memories (id, content, source, project, status) "
    "VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')"
)


class CountingLLM:
    """Records every completion so "exactly one call" is a count, not a claim."""

    def __init__(self, answer: str = "a project overview"):
        self.answer = answer
        self.calls: list[dict] = []

    async def chat_completion(self, purpose, messages, **kwargs):
        self.calls.append({"purpose": purpose, "messages": messages})
        return self.answer

    @property
    def prompts(self) -> list[str]:
        return [m["content"] for call in self.calls for m in call["messages"]]


class ExplodingLLM:
    """Any completion at all is a failure — for the paths that must spend none."""

    async def chat_completion(self, purpose, messages, **kwargs):
        raise AssertionError(f"an unexpected {purpose} completion was dispatched")


async def seed_memories(session, project: str, count: int, prefix: str) -> list:
    ids = []
    for i in range(count):
        memory_id = new_id()
        await session.execute(
            _INSERT_MEMORY,
            {
                "id": str(memory_id),
                "content": f"{prefix} memory {i} about postgres tuning",
                "project": project,
            },
        )
        ids.append(memory_id)
    return ids


async def seed_communities(
    session,
    project: str,
    *,
    communities: int,
    members_each: int,
    with_reports: bool = True,
    report_text=None,
) -> None:
    """Build a project whose topic count and corpus size vary independently.

    That independence is the whole point of the fixture: the cost claim is
    about communities, so the test needs a corpus it can grow without growing
    the topic set.
    """
    drafts = []
    for c in range(communities):
        label = f"topic {c}"
        member_ids = await seed_memories(
            session, project, members_each, f"{project}-{c}"
        )
        drafts.append(
            repo.CommunityDraft(
                label=label,
                memory_ids=tuple(member_ids),
                properties={"size": members_each, "dominant_entities": []},
            )
        )
    written = await repo.replace_project_communities(session, project, drafts)
    if not with_reports:
        return
    for community_id, draft in zip(written, drafts):
        body = (
            report_text(draft.label)
            if callable(report_text)
            else f"a precomputed report about {draft.label}"
        )
        await repo.set_report(session, community_id, report_string=body)
    await session.flush()


# ---------------------------------------------------------------------------
# Done-when 1: cost is bounded by community count, not memory count
# ---------------------------------------------------------------------------


async def test_growing_the_corpus_moves_neither_the_calls_nor_the_budget(session):
    """The measured form of "bounded by community count".

    Two projects, four topics each, identical reports — one holds 12
    memories, the other 96. If the cost were a function of the corpus, the
    prompt would grow with it and a big enough corpus would need a second
    call; both must be flat.
    """

    await seed_communities(session, PROJECT, communities=4, members_each=3)
    await seed_communities(session, OTHER_PROJECT, communities=4, members_each=24)

    small_llm = CountingLLM()
    big_llm = CountingLLM()
    small = await overview.get_overview(session, small_llm, PROJECT)
    big = await overview.get_overview(session, big_llm, OTHER_PROJECT)

    assert small.reports_used == big.reports_used == 4
    assert len(small_llm.calls) == len(big_llm.calls) == 1

    # Eight times the memories, and the prompt may only grow by the extra
    # digits in each topic's member count.
    assert big.reduce_input_chars - small.reduce_input_chars <= 4 * big.reports_used
    assert small.reduce_input_chars <= overview.reduce_input_bound(4)
    assert big.reduce_input_chars <= overview.reduce_input_bound(4)


async def test_no_memory_content_reaches_the_reduce_prompt(session):
    """The mechanism behind the bound: the map's unit is the report, so a
    memory's text has no route into the prompt however many memories a topic
    holds."""

    await seed_communities(session, PROJECT, communities=2, members_each=5)
    llm = CountingLLM()
    await overview.get_overview(session, llm, PROJECT)

    prompt = "\n".join(llm.prompts)
    assert f"{PROJECT}-0 memory 0 about postgres tuning" not in prompt
    assert "memory 0 about postgres" not in prompt
    assert "a precomputed report about topic 0" in prompt


async def test_the_bound_tracks_communities_so_it_is_not_vacuous(session):
    """A bound that ignored its input would pass every assertion above. More
    topics must cost more, or "bounded by community count" says nothing."""

    await seed_communities(session, PROJECT, communities=2, members_each=2)
    await seed_communities(session, OTHER_PROJECT, communities=8, members_each=2)

    few = await overview.get_overview(session, CountingLLM(), PROJECT)
    many = await overview.get_overview(session, CountingLLM(), OTHER_PROJECT)

    assert many.reduce_input_chars > few.reduce_input_chars
    assert overview.reduce_input_bound(8) > overview.reduce_input_bound(2)


# ---------------------------------------------------------------------------
# Done-when 2: the reduce is exactly one call
# ---------------------------------------------------------------------------


async def test_the_reduce_is_one_call_and_the_repeat_is_none(session):

    await seed_communities(session, PROJECT, communities=6, members_each=2)

    llm = CountingLLM()
    first = await overview.get_overview(session, llm, PROJECT)
    assert len(llm.calls) == 1
    assert llm.calls[0]["purpose"] == overview.REDUCE_PURPOSE
    assert first.cached is False and first.model_calls == 1

    second = await overview.get_overview(session, llm, PROJECT)
    assert len(llm.calls) == 1, "the cached overview re-ran the reduce"
    assert second.cached is True and second.model_calls == 0
    assert second.text == first.text
    assert second.community_set_hash == first.community_set_hash


async def test_an_over_budget_report_set_is_dropped_and_declared(session):
    """Invariant 14. The bound is enforced by selection, and the selection is
    stated on the output — never by a second silent call."""

    await seed_communities(session, PROJECT, communities=5, members_each=2)

    llm = CountingLLM()
    result = await overview.get_overview(session, llm, PROJECT, max_reports=2)

    assert len(llm.calls) == 1
    assert result.reports_ready == 5
    assert result.reports_used == 2
    assert result.reports_omitted == 3
    assert len(result.omitted_labels) == 3
    assert set(result.omitted_labels) <= {f"topic {i}" for i in range(5)}
    assert result.reduce_input_chars <= overview.reduce_input_bound(2)
    assert sum(1 for t in result.topics if t.used_in_reduce) == 2


async def test_the_largest_topics_are_the_ones_kept(session):

    small_ids = await seed_memories(session, PROJECT, 1, "small")
    big_ids = await seed_memories(session, PROJECT, 4, "big")
    written = await repo.replace_project_communities(
        session,
        PROJECT,
        [
            repo.CommunityDraft("tiny topic", tuple(small_ids), {"size": 1}),
            repo.CommunityDraft("large topic", tuple(big_ids), {"size": 4}),
        ],
    )
    for community_id, label in zip(written, ("tiny topic", "large topic")):
        await repo.set_report(session, community_id, report_string=f"report {label}")
    await session.flush()

    result = await overview.get_overview(session, CountingLLM(), PROJECT, max_reports=1)
    assert result.omitted_labels == ("tiny topic",)
    assert [t.label for t in result.topics if t.used_in_reduce] == ["large topic"]


async def test_an_over_long_report_is_truncated_and_says_so(session):

    await seed_communities(
        session,
        PROJECT,
        communities=1,
        members_each=2,
        report_text=lambda label: "x" * (overview.MAX_REPORT_CHARS + 500),
    )

    result = await overview.get_overview(session, CountingLLM(), PROJECT)
    assert result.reports_truncated == 1
    assert result.reduce_input_chars <= overview.reduce_input_bound(1)


async def test_an_empty_project_spends_nothing(session):

    result = await overview.get_overview(session, ExplodingLLM(), PROJECT)
    assert result.text is None
    assert result.model_calls == 0
    assert result.communities_total == 0
    assert result.reports_ready == 0


async def test_a_topic_set_with_no_reports_yet_spends_nothing(session):
    """R5's read half: a topic whose report has not been generated renders as
    pending. Nothing here asks for one — `ExplodingLLM` fails the test if a
    completion is dispatched at all."""

    await seed_communities(
        session, PROJECT, communities=2, members_each=4, with_reports=False
    )

    result = await overview.get_overview(session, ExplodingLLM(), PROJECT)
    assert result.text is None
    assert result.communities_total == 2
    assert result.reports_ready == 0
    assert {t.report_status for t in result.topics} == {"pending"}
    assert all(t.report is None for t in result.topics)


async def test_a_pending_topic_is_counted_beside_the_ready_ones(session):

    await seed_communities(session, PROJECT, communities=2, members_each=3)
    pending_ids = await seed_memories(session, PROJECT, 3, "pending")
    existing = await repo.list_with_members(session, PROJECT)
    drafts = [
        repo.CommunityDraft(row.label, row.memory_ids, row.properties)
        for row in existing
    ] + [repo.CommunityDraft("unreported topic", tuple(pending_ids), {"size": 3})]
    written = await repo.replace_project_communities(session, PROJECT, drafts)
    for community_id, row in zip(written, existing):
        await repo.set_report(session, community_id, report_string=row.report_string)
    await session.flush()

    llm = CountingLLM()
    result = await overview.get_overview(session, llm, PROJECT)

    assert result.communities_total == 3
    assert result.reports_used == 2
    assert len(llm.calls) == 1
    assert "unreported topic" not in "\n".join(llm.prompts)
    pending = [t for t in result.topics if t.label == "unreported topic"]
    assert pending and pending[0].report_status == "pending"
    assert pending[0].report is None


# ---------------------------------------------------------------------------
# The cache is keyed on the community set, not on time
# ---------------------------------------------------------------------------


async def test_a_changed_report_invalidates_the_cache(session):

    await seed_communities(session, PROJECT, communities=2, members_each=2)
    llm = CountingLLM()
    first = await overview.get_overview(session, llm, PROJECT)

    rows = await repo.list_with_members(session, PROJECT)
    await repo.set_report(session, rows[0].id, report_string="a rewritten report")
    await session.flush()

    llm.answer = "a second overview"
    second = await overview.get_overview(session, llm, PROJECT)
    assert len(llm.calls) == 2
    assert second.cached is False
    assert second.community_set_hash != first.community_set_hash
    assert second.text == "a second overview"


async def test_the_hash_ignores_the_ids_that_churn_every_run(session):
    """Community ids are rewritten on every detection run (doc 04 §8.4). If
    the hash covered them, the nightly rewrite would burn a reduce call even
    when it produced an identical topic set."""

    await seed_communities(session, PROJECT, communities=3, members_each=2)
    before = await repo.list_with_members(session, PROJECT)

    llm = CountingLLM()
    first = await overview.get_overview(session, llm, PROJECT)

    drafts = [
        repo.CommunityDraft(row.label, row.memory_ids, row.properties)
        for row in before
    ]
    written = await repo.replace_project_communities(session, PROJECT, drafts)
    for community_id, row in zip(written, before):
        await repo.set_report(session, community_id, report_string=row.report_string)
    await session.flush()

    after = await repo.list_with_members(session, PROJECT)
    assert {r.id for r in after}.isdisjoint({r.id for r in before})

    second = await overview.get_overview(session, llm, PROJECT)
    assert second.community_set_hash == first.community_set_hash
    assert second.cached is True
    assert len(llm.calls) == 1


async def test_the_cache_row_is_the_documented_config_key(session):

    await seed_communities(session, PROJECT, communities=1, members_each=2)
    await overview.get_overview(session, CountingLLM(), PROJECT)

    value = (
        await session.execute(
            text("SELECT value FROM config WHERE key = :k"),
            {"k": f"overview:{PROJECT}"},
        )
    ).scalar_one()
    assert set(value) >= {"community_set_hash", "text"}


# ---------------------------------------------------------------------------
# Scope: the overview has no wide mode
# ---------------------------------------------------------------------------


async def test_another_projects_topics_never_reach_the_overview(session):

    await seed_communities(session, PROJECT, communities=2, members_each=2)
    await seed_communities(
        session,
        OTHER_PROJECT,
        communities=2,
        members_each=2,
        report_text=lambda label: f"FOREIGN report about {label}",
    )

    llm = CountingLLM()
    result = await overview.get_overview(session, llm, PROJECT)

    assert result.communities_total == 2
    assert all(t.project == PROJECT for t in result.topics)
    assert "FOREIGN" not in "\n".join(llm.prompts)
    assert all("FOREIGN" not in (t.report or "") for t in result.topics)


# ---------------------------------------------------------------------------
# The output is organizational, and says so
# ---------------------------------------------------------------------------


async def test_the_overview_carries_no_verification_badge(session):

    await seed_communities(session, PROJECT, communities=1, members_each=2)
    payload = (await overview.get_overview(session, CountingLLM(), PROJECT)).to_dict()

    assert payload["kind"] == overview.OVERVIEW_KIND == "organizational"
    rendered = json.dumps(payload)
    for forbidden in ("badge", "verification_status", "human_ratified", "confidence"):
        assert forbidden not in rendered


# ---------------------------------------------------------------------------
# Done-when 3: both front doors expose it, through one service
# ---------------------------------------------------------------------------


async def test_the_rest_door_answers_through_the_shared_service(
    session, client, auth_headers, monkeypatch
):

    await seed_communities(session, PROJECT, communities=2, members_each=2)

    from app.main import app

    monkeypatch.setattr(app.state, "llm", CountingLLM(), raising=False)

    calls = []
    original = overview.get_overview

    async def spy(*args, **kwargs):
        calls.append(args[2] if len(args) > 2 else kwargs.get("project"))
        return await original(*args, **kwargs)

    monkeypatch.setattr("app.api.routes.overview.get_overview", spy)

    response = await client.get(
        f"/api/v1/knowledge/overview?project={PROJECT}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert calls == [PROJECT]
    assert body["project"] == PROJECT
    assert body["kind"] == "organizational"
    assert len(body["topics"]) == 2
    assert all(t["project"] == PROJECT for t in body["topics"])


async def test_the_mcp_door_answers_through_the_shared_service(
    session, monkeypatch
):

    await seed_communities(session, PROJECT, communities=2, members_each=2)

    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def fake_factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", fake_factory)

    class _Pipeline:
        llm = CountingLLM()

    monkeypatch.setattr(mcp_server, "_pipeline", _Pipeline())

    calls = []
    original = overview.get_overview

    async def spy(*args, **kwargs):
        calls.append(args[2] if len(args) > 2 else kwargs.get("project"))
        return await original(*args, **kwargs)

    monkeypatch.setattr(overview, "get_overview", spy)

    body = json.loads(await mcp_server.memory_overview(project=PROJECT))
    assert calls == [PROJECT]
    assert body["project"] == PROJECT
    assert body["kind"] == "organizational"
    assert len(body["topics"]) == 2


async def test_both_doors_agree_on_the_same_project(
    session, client, auth_headers, monkeypatch
):
    """Invariant 17 is about the answer, not the wiring: the two doors must
    publish the same topics, the same declared drops and the same cache
    identity, or one of them is describing a corpus the other is not."""

    await seed_communities(session, PROJECT, communities=3, members_each=2)

    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server
    from app.main import app

    llm = CountingLLM()
    monkeypatch.setattr(app.state, "llm", llm, raising=False)

    @asynccontextmanager
    async def fake_factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", fake_factory)

    class _Pipeline:
        pass

    _Pipeline.llm = llm
    monkeypatch.setattr(mcp_server, "_pipeline", _Pipeline())

    rest = (
        await client.get(
            f"/api/v1/knowledge/overview?project={PROJECT}", headers=auth_headers
        )
    ).json()
    tool = json.loads(await mcp_server.memory_overview(project=PROJECT))

    assert len(llm.calls) == 1, "the second door re-ran the reduce"
    assert rest["community_set_hash"] == tool["community_set_hash"]
    assert rest["text"] == tool["text"]
    assert rest["reports_used"] == tool["reports_used"]
    assert rest["reports_omitted"] == tool["reports_omitted"]
    assert [t["label"] for t in rest["topics"]] == [t["label"] for t in tool["topics"]]


async def test_the_rest_door_degrades_rather_than_500s_without_a_model(
    session, client, auth_headers, monkeypatch
):

    await seed_communities(session, PROJECT, communities=1, members_each=2)

    from app.main import app

    monkeypatch.setattr(app.state, "llm", None, raising=False)
    response = await client.get(
        f"/api/v1/knowledge/overview?project={PROJECT}", headers=auth_headers
    )
    assert response.status_code == 503


async def test_the_mcp_door_returns_the_typed_degradation_without_a_model(
    session, monkeypatch
):

    await seed_communities(session, PROJECT, communities=1, members_each=2)

    from contextlib import asynccontextmanager

    from app.api.mcp import server as mcp_server

    @asynccontextmanager
    async def fake_factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", fake_factory)
    monkeypatch.setattr(mcp_server, "_pipeline", None)

    body = json.loads(await mcp_server.memory_overview(project=PROJECT))
    assert body["status"] == "unavailable"


# ---------------------------------------------------------------------------
# R5, structurally: nothing on this surface can generate a report
# ---------------------------------------------------------------------------

OVERVIEW_SURFACE_FILES = (
    "app/services/memory_overview.py",
    "app/api/routes/overview.py",
    "app/api/mcp/server.py",
)

# The whole-tree version of this scan lives in `test_community_reports.py` and
# already covers these files. It is repeated here narrowed to this surface for
# one reason: when it fails there, the message is "some file under app/ reaches
# report generation", and the surface that made a read door reach it is exactly
# the one whose own suite should say so.
_GENERATION_SYMBOLS = frozenset({"generate_report", "generate_reports"})


_REPORTS_MODULE = "app.services.memory_community_reports"
_REPORTS_BASENAME = "memory_community_reports"

_GENERATION_RULES = ReachabilityRules(
    forbidden_modules=frozenset({_REPORTS_MODULE}),
    forbidden_attrs=frozenset({_REPORTS_BASENAME}),
    forbidden_literals=frozenset({_REPORTS_BASENAME}),
)


def _exempt_status_only_imports(rel, tree):
    """A from-import naming no generation symbol is the sanctioned route.

    All-or-nothing per statement, matching the whole-tree scan's own
    exemption: one generation name alongside the projection symbols exempts
    nothing.
    """
    exempted = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == _REPORTS_MODULE
            and node.level == 0
            and node.names
            and all(a.name not in _GENERATION_SYMBOLS for a in node.names)
        ):
            exempted.add(id(node))
    return exempted


def _generation_offenders(paths, root) -> list[str]:
    return find_forbidden_reach(
        paths, root, _GENERATION_RULES,
        exempt_node_ids=_exempt_status_only_imports,
    )


def test_the_overview_surface_cannot_reach_report_generation():
    paths = [BACKEND / rel for rel in OVERVIEW_SURFACE_FILES]
    assert all(p.exists() for p in paths), paths
    assert not _generation_offenders(paths, BACKEND)


def test_that_scan_would_catch_a_generation_call(tmp_path):
    """A guard nobody tried to break is a guard nobody has tested."""
    offender = tmp_path / "app" / "services" / "memory_overview.py"
    offender.parent.mkdir(parents=True, exist_ok=True)
    offender.write_text(
        "from app.services.memory_community_reports import generate_reports\n",
        encoding="utf-8",
    )
    assert _generation_offenders([offender], tmp_path)


def test_that_scan_still_admits_the_status_projection(tmp_path):
    """The exemption has to be real, or the guard above would be satisfied by
    a rule nothing can legally pass."""
    allowed = tmp_path / "app" / "services" / "memory_overview.py"
    allowed.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text(
        "from app.services.memory_community_reports import report_status\n",
        encoding="utf-8",
    )
    assert not _generation_offenders([allowed], tmp_path)


# ---------------------------------------------------------------------------
# The registered surface and its probe driver ship together
# ---------------------------------------------------------------------------


def test_the_surface_is_registered_on_both_doors():
    from app.services.content_surfaces import surface

    entry = surface("memory_overview")
    assert set(entry.front_doors) == {
        "GET /api/v1/knowledge/overview",
        "mcp:memory_overview",
    }
    assert entry.labels == ("project",)


def test_the_registered_surface_has_an_isolation_probe_driver():
    """A `ContentSurface` without a driver takes the whole cross-project leak
    probe offline, and `testpaths` hides that from the backend floor. This
    assertion is inside the floor on purpose."""
    probe_path = BACKEND / "scripts" / "benchlib" / "isolation_probe.py"
    source = probe_path.read_text(encoding="utf-8")
    assert '"memory_overview": _drive_memory_overview,' in source
    assert "async def _drive_memory_overview(" in source
