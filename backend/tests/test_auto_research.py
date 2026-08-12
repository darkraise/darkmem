"""T3.07 — the research loop's three done-when clauses, plus the seam T3.08 needs.

The clauses are each asserted structurally where a behavioural test alone
would rot:

* **No new ingestion path.** ``test_the_loop_reaches_ingest_only_through_the_
  memory_service`` pins the module's entire ``app.*`` import set to a
  whitelist, so reaching ``memory_buffer``/``pipeline``/a repository directly
  fails the build rather than passing review. The behavioural half —
  ``test_a_run_lands_in_the_ordinary_capture_buffer`` — proves the rows really
  went through the buffered door, and ``test_a_whole_run_is_one_capture_call``
  proves they went through it *once*, which is what makes a run atomic.
* **Tier-C, bounded by a config budget.** ``test_no_app_code_reaches_the_
  research_loop`` is invariant 15's direction (nothing on capture or retrieval
  may reach this module), on the same AST scanner the dream-job family uses.
  The budget tests cover the `config` row, its defaults, its clamp against the
  capture door's own batch cap, and both refusals.
* **A failed run leaves no partial state.** Covered on both sides of the one
  write: a gatherer that raises, and a failure *inside* the capture call after
  rows are enqueued and before the commit.

The origin tests are the ones that matter two months from now. This loop
manufactures origins rather than observing them, so the corpus has to be able
to slice them out; ``is_researched_origin`` is that slice and it is asserted
against a real human-shaped key, not only against itself.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp.client_identity import resolve_origin_key
from app.models.config import Config
from app.models.memory import MemoryBuffer
from app.schemas.memory import CaptureAck
from app.services import auto_research
from app.services.auto_research import (
    AUTO_RESEARCH_CONFIG_KEY,
    AUTO_RESEARCH_DEFAULTS,
    MAX_FINDINGS_CEILING,
    RESEARCH_SOURCE,
    ResearchBudget,
    ResearchBudgetExceeded,
    ResearchDisabled,
    ResearchFinding,
    is_researched_origin,
    load_budget,
    research_origin_key,
    run_research,
)
from app.services.memory import CaptureResult, MemoryService
from tests._reachability_scan import ReachabilityRules, app_sources, find_forbidden_reach

BACKEND = Path(__file__).resolve().parent.parent
LOOP_MODULE = "app/services/auto_research.py"

# Everything the loop is allowed to reach. `app.services.memory` is the whole
# point: capture is reached through the service the four doors share, and
# nothing else under `app.services` or `app.repositories` is touched.
ALLOWED_APP_IMPORTS = {
    "app.api.mcp.client_identity",
    "app.models.config",
    "app.schemas.memory",
    "app.services.events",
    "app.services.memory",
    "app.utils.ids",
}


class _Gatherer:
    """A stand-in for the capability that lives outside darkmem's box."""

    def __init__(self, findings, *, fail: Exception | None = None):
        self.findings = findings
        self.fail = fail
        self.limits: list[int] = []

    async def gather(self, subject: str, *, limit: int):
        self.limits.append(limit)
        if self.fail is not None:
            raise self.fail
        return self.findings


class _CountingService:
    """Records how many capture calls one run makes."""

    def __init__(self):
        self.calls: list[list] = []

    async def batch_create_memories(self, entries, api_key_id, **kwargs):
        self.calls.append(list(entries))
        from app.utils.ids import new_id

        return [CaptureResult(ack=CaptureAck(id=new_id())) for _ in entries]


ENABLED = ResearchBudget(enabled=True, max_findings_per_run=20, max_content_chars=8000)


def _finding(text: str, source_id: str | None = None) -> ResearchFinding:
    return ResearchFinding(content=text, source_id=source_id)


async def _buffer_count(session) -> int:
    return (await session.execute(
        select(func.count()).select_from(MemoryBuffer)
    )).scalar_one()


async def _buffer_rows(session) -> list[MemoryBuffer]:
    return list((await session.execute(select(MemoryBuffer))).scalars().all())


# --------------------------------------------------------------------------
# Clause 1 — no new ingestion path
# --------------------------------------------------------------------------


def _app_imports(source: str) -> set[str]:
    """Every `app.*` dotted path the module imports, in any absolute style."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("app."))
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in the loop defeats this whitelist"
            module = node.module or ""
            if not module.startswith("app"):
                continue
            if module == "app.services" or module == "app.repositories":
                found.update(f"{module}.{a.name}" for a in node.names)
            else:
                found.add(module)
    return found


def test_the_loop_reaches_ingest_only_through_the_memory_service():
    """A whitelist, not a blacklist: the loop may reach exactly these modules.

    A blacklist of today's ingest internals would go quiet the moment someone
    added a new one. Pinning the whole set means any widening — a direct
    `memory_buffer.enqueue`, a `ProcessingPipeline`, a repository write, raw
    SQL against `memories` through a new import — fails here first.

    **Its bound, stated rather than left to be discovered:** this catches every
    ordinary import shape, including function-level ones, but not obfuscation —
    a bare `import app` reached by attribute chain (the name carries no `app.`
    prefix) or an `importlib.import_module` by string literal both slip past.
    The sibling reachability scanner documents its own bound the same way; a
    scan that claims completeness it does not have is worse than one that
    names its edge.
    """
    imports = _app_imports((BACKEND / LOOP_MODULE).read_text())
    assert imports <= ALLOWED_APP_IMPORTS, (
        f"the research loop reaches outside its whitelist: "
        f"{sorted(imports - ALLOWED_APP_IMPORTS)} — a second ingestion path is "
        f"exactly what T3.07 may not add"
    )
    assert "app.services.memory" in imports, (
        "the loop no longer files through MemoryService at all"
    )


@pytest.mark.asyncio
async def test_a_whole_run_is_one_capture_call(session):
    """Atomicity comes from the shape of the run, not from a try block.

    Five findings must be one `batch_create_memories` call, because that call
    is one transaction and one commit. N calls would mean N commits and a real
    window in which a failure leaves some findings durable and others not.
    """
    service = _CountingService()
    gatherer = _Gatherer([_finding(f"finding {i}", f"https://example.test/{i}") for i in range(5)])
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        gatherer=gatherer, service=service, budget=ENABLED,
    )
    assert len(service.calls) == 1
    assert len(service.calls[0]) == 5
    assert result.filed == 5


@pytest.mark.asyncio
async def test_a_run_lands_in_the_ordinary_capture_buffer(session):
    """The rows arrive as buffered captures — the 202 path every door uses."""
    gatherer = _Gatherer([
        _finding("pgvector stores fixed-dimension vectors.", "https://example.test/a"),
        _finding("HNSW is pgvector's graph index.", "https://example.test/b"),
    ])
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        gatherer=gatherer, budget=ENABLED,
    )

    rows = await _buffer_rows(session)
    assert len(rows) == 2
    assert {row.status for row in rows} == {"pending"}
    assert {row.project for row in rows} == {"research-lane"}
    # The ack's id is the pre-minted memory id riding the buffer row, never the
    # buffer row's own tracking handle (doc 05 section 2.2).
    assert {str(mid) for mid in result.memory_ids} == {
        row.metadata_["memory_id"] for row in rows
    }
    assert not {row.id for row in rows} & set(result.memory_ids)
    for row in rows:
        # The caller's own metadata nests under `metadata` rather than merging
        # into the buffer's bookkeeping keys (doc 05 section 3.1), and replays
        # verbatim onto `memories.metadata_` at flush.
        research = row.metadata_["metadata"]["research"]
        assert research["run_id"] == str(result.run_id)
        assert research["subject"] == "pgvector"
        assert research["source_id"].startswith("https://example.test/")


@pytest.mark.asyncio
async def test_the_gatherer_is_bounded_by_the_budget(session):
    service = _CountingService()
    gatherer = _Gatherer([_finding("one")])
    await run_research(
        session, subject="s", project="p", gatherer=gatherer, service=service,
        budget=ResearchBudget(enabled=True, max_findings_per_run=7, max_content_chars=100),
    )
    assert gatherer.limits == [7]


# --------------------------------------------------------------------------
# Clause 2 — Tier-C, bounded by a config budget
# --------------------------------------------------------------------------


def test_no_app_code_reaches_the_research_loop():
    """Invariant 15's direction: nothing on capture or retrieval may reach a
    Tier-C consumer to accelerate a gate.

    Vacuous today by construction — no module imports the loop — and that is
    the point of running it: the day someone wires a research run into the
    pipeline or a search route to fill the corpus faster, this goes red. The
    scan is the dream-job family's own, so an import spelled across lines, an
    attribute reach through the package, or the dotted path inside a string
    literal are all covered.

    Note it is blanket over `app/` with no exemption in use, so a **sanctioned**
    driver — a jobs registration, a research route, an MCP tool — trips it too,
    and must visibly invoke the `exempt_node_ids` machinery the dream-job scan
    already uses. That is the intended default: reaching this loop should be an
    argued act, never an incidental import.
    """
    paths = app_sources(BACKEND)
    offenders = find_forbidden_reach(
        paths, BACKEND,
        ReachabilityRules(
            forbidden_modules=frozenset({"app.services.auto_research"}),
            forbidden_attrs=frozenset({"auto_research"}),
            forbidden_literals=frozenset({"auto_research"}),
        ),
        skip_files=frozenset({LOOP_MODULE}),
    )
    assert not offenders, (
        "app code reaches the Tier-C research loop: " + "; ".join(offenders)
    )


@pytest.mark.asyncio
async def test_the_budget_defaults_fail_closed(session):
    """An install that has never configured research runs no research.

    Building the loop is not running it: pointing it at a live instance is a
    separate decision, so the absence of a config row must mean off, never
    "off but with defaults that would run".
    """
    await session.execute(delete(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY))
    budget = await load_budget(session)
    assert budget.enabled is False
    assert budget.max_findings_per_run == AUTO_RESEARCH_DEFAULTS["max_findings_per_run"]
    assert budget.max_content_chars == AUTO_RESEARCH_DEFAULTS["max_content_chars"]


@pytest.mark.asyncio
async def test_a_disabled_install_refuses_the_run_before_gathering(session):
    gatherer = _Gatherer([_finding("evidence")])
    with pytest.raises(ResearchDisabled):
        await run_research(session, subject="s", project="p", gatherer=gatherer)
    assert gatherer.limits == [], "a disabled install still called the gatherer"
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_the_budget_is_read_from_the_config_row(session):
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={
        "enabled": True, "max_findings_per_run": 4, "max_content_chars": 250,
    }))
    await session.flush()
    budget = await load_budget(session)
    assert budget == ResearchBudget(
        enabled=True, max_findings_per_run=4, max_content_chars=250,
    )


@pytest.mark.asyncio
async def test_a_budget_over_the_capture_batch_cap_is_clamped(session):
    """The budget may not authorise a batch the front door would reject."""
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={
        "enabled": True, "max_findings_per_run": MAX_FINDINGS_CEILING + 500,
    }))
    await session.flush()
    budget = await load_budget(session)
    assert budget.max_findings_per_run == MAX_FINDINGS_CEILING


@pytest.mark.asyncio
async def test_a_malformed_budget_row_degrades_to_the_defaults(session):
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={
        "enabled": True, "max_findings_per_run": "lots", "max_content_chars": -3,
    }))
    await session.flush()
    budget = await load_budget(session)
    assert budget.max_findings_per_run == AUTO_RESEARCH_DEFAULTS["max_findings_per_run"]
    assert budget.max_content_chars == AUTO_RESEARCH_DEFAULTS["max_content_chars"]


@pytest.mark.asyncio
async def test_a_malformed_enabled_fails_closed_rather_than_truthy(session):
    """The string "false" is the most natural malformed shape an operator
    writes, and it is truthy — so `bool()` on the master switch would fail
    *open*, which is the one direction "building it is not running it" cannot
    survive. The int fields already degrade strictly; this one has to as well."""
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={"enabled": "false"}))
    await session.flush()

    budget = await load_budget(session)
    assert budget.enabled is False
    assert budget.enabled == AUTO_RESEARCH_DEFAULTS["enabled"]


@pytest.mark.asyncio
async def test_a_truthy_non_boolean_enabled_does_not_arm_the_loop(session):
    """Not only the "false" case: any non-boolean falls back to the default,
    so no operator typo can arm a loop the owner has not armed."""
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={"enabled": "yes"}))
    await session.flush()

    assert (await load_budget(session)).enabled is False


@pytest.mark.asyncio
async def test_more_findings_than_the_budget_allows_refuses_the_whole_run(session):
    gatherer = _Gatherer([_finding(f"f{i}") for i in range(4)])
    with pytest.raises(ResearchBudgetExceeded):
        await run_research(
            session, subject="s", project="p", gatherer=gatherer,
            budget=ResearchBudget(enabled=True, max_findings_per_run=3, max_content_chars=100),
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_an_over_long_finding_refuses_the_whole_run(session):
    """Refused, not truncated. A truncated filing would record a run whose
    origin story is untrue in a way nothing downstream could detect."""
    gatherer = _Gatherer([_finding("ok"), _finding("x" * 200)])
    with pytest.raises(ResearchBudgetExceeded):
        await run_research(
            session, subject="s", project="p", gatherer=gatherer,
            budget=ResearchBudget(enabled=True, max_findings_per_run=10, max_content_chars=50),
        )
    assert await _buffer_count(session) == 0


# --------------------------------------------------------------------------
# Clause 3 — a failed run leaves no partial state
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_gatherer_failure_writes_nothing(session):
    gatherer = _Gatherer([], fail=RuntimeError("fetch timed out"))
    with pytest.raises(RuntimeError):
        await run_research(
            session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_a_failure_inside_the_capture_call_rolls_the_whole_run_back(
    session, monkeypatch,
):
    """The sharp case: rows are already enqueued when the failure lands.

    `_capture_batch` enqueues every row, journals, hands off repo hints and
    only then commits. Failing at the hand-off means three rows exist in the
    session and none is committed — so a loop that swallowed the error, or
    merely re-raised without rolling back, would leave the caller's
    transaction holding a half-written research run.
    """
    async def boom(self, rows, entries):
        raise RuntimeError("hint hand-off failed")

    monkeypatch.setattr(MemoryService, "_handoff_repo_hints", boom)
    gatherer = _Gatherer([_finding(f"finding {i}") for i in range(3)])
    with pytest.raises(RuntimeError):
        await run_research(
            session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_a_failed_journal_commit_does_not_report_a_filed_run_as_failed(
    session, monkeypatch,
):
    """The run is two transactions, not one: the capture call commits the
    filing, then the journal commits separately. A raise in that second window
    would report a durable run as failed, and a driver retrying on it would
    file the whole run twice. It degrades to the same unjournalled outcome the
    non-fatal `record_event` branch already tolerates.

    The durability half is deliberately not asserted here: conftest wraps each
    test in an outer transaction, so the filing's "commit" is a savepoint and
    the degradation's rollback discards rows that a real commit would have made
    permanent. What the harness *can* observe is the reported outcome, which is
    the half a retrying driver reads."""
    committed: list[int] = []
    real_commit = AsyncSession.commit

    async def commit(self):
        committed.append(1)
        if len(committed) > 1:            # the filing's own commit is the first
            raise RuntimeError("journal commit failed")
        await real_commit(self)

    gatherer = _Gatherer([_finding("f0"), _finding("f1")])
    monkeypatch.setattr(AsyncSession, "commit", commit)
    result = await run_research(
        session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
    )
    monkeypatch.undo()

    assert result.filed == 2, "the filing happened and must be reported as filed"
    assert result.journalled is False, "and the lost journal must be visible"
    assert len(committed) == 2, "the journal commit was reached and did raise"


@pytest.mark.asyncio
async def test_one_unfileable_finding_refuses_the_whole_run(session):
    """The capture door's own validation runs before any write.

    Entries are built and validated through `MemoryBatchCreate` before the
    service is called at all, so a finding the door would reject takes the
    run down while it is still free to take nothing with it.
    """
    gatherer = _Gatherer([_finding("real evidence"), _finding("")])
    with pytest.raises(ValidationError):
        await run_research(
            session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_a_run_that_gathers_nothing_writes_nothing(session):
    result = await run_research(
        session, subject="s", project="p", gatherer=_Gatherer([]), budget=ENABLED,
    )
    assert (result.gathered, result.filed) == (0, 0)
    assert result.journalled is False
    assert await _buffer_count(session) == 0


# --------------------------------------------------------------------------
# The origin discipline, and the seam T3.08 fills
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_researched_capture_carries_the_reserved_source(session):
    gatherer = _Gatherer([_finding("a", "https://example.test/a")])
    await run_research(
        session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    assert {row.source for row in rows} == {RESEARCH_SOURCE}
    assert all(is_researched_origin(row.metadata_["origin_key"]) for row in rows)


@pytest.mark.asyncio
async def test_two_independent_sources_are_one_origin_today(session):
    """The honest undercount, and the reason this task cannot promote a fact.

    Two genuinely different sources still resolve to a single `origin_key`,
    because establishing per-source identity is T3.08's task and doc 09
    section 6's rule for unestablished identity is merge-to-one. Minting two
    here would be manufactured corroboration.
    """
    gatherer = _Gatherer([
        _finding("claim", "https://example.test/a"),
        _finding("same claim", "https://other.test/b"),
    ])
    await run_research(
        session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    assert len({row.metadata_["origin_key"] for row in rows}) == 1


@pytest.mark.asyncio
async def test_the_merged_origin_never_fires_a_corroboration_gate(session):
    """It lands in the capture layer's anonymous bucket on purpose.

    `fact_sources` folds every `unknown:`-prefixed key into one reserved
    bucket that contributes to the count and to nothing else, so a research
    run cannot reach the N = 2 diversity bar alongside one real witness.
    """
    gatherer = _Gatherer([_finding("claim", "https://example.test/a")])
    await run_research(
        session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    assert rows[0].metadata_["origin_key"].startswith("unknown:")


def test_a_researched_origin_never_looks_like_a_human_capture():
    """The disclosure has to hold against real keys, not only against itself."""
    researched = research_origin_key(_finding("a", "https://example.test/a"), project="p")
    assert is_researched_origin(researched)

    for human in (
        resolve_origin_key(None, None, source="api", project="p"),
        resolve_origin_key(None, None, source="mcp", project="p"),
        resolve_origin_key("boot-uuid", None, source="claude-code", project="p"),
        resolve_origin_key("boot-uuid", None, source="codex", project="p"),
    ):
        assert not is_researched_origin(human), human
    assert not is_researched_origin(None)
    assert not is_researched_origin("")


def test_the_declared_form_t3_08_will_mint_is_already_recognised():
    """T3.08 replaces the merged key with a declared one; the slice predicate
    must not need editing when it does, or the disclosure has a gap exactly
    where the origins start counting."""
    assert is_researched_origin(f"{RESEARCH_SOURCE}:https-example-test-a")


@pytest.mark.asyncio
async def test_the_origin_seam_is_per_finding(session, monkeypatch):
    """Proof the seam is real: nothing but `research_origin_id` decides
    whether two findings share an origin.

    Standing in for T3.08 — one function returning a per-source identity —
    turns two findings into two distinct declared origins, both still
    recognised as researched. That is the whole change T3.08 has to make,
    which is what "leave the seam" means.
    """
    monkeypatch.setattr(
        auto_research, "research_origin_id", lambda finding: finding.source_id,
    )
    gatherer = _Gatherer([
        _finding("claim", "https://example.test/a"),
        _finding("same claim", "https://other.test/b"),
    ])
    await run_research(
        session, subject="s", project="p", gatherer=gatherer, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    keys = {row.metadata_["origin_key"] for row in rows}
    assert len(keys) == 2
    assert all(is_researched_origin(key) for key in keys)
    assert all(key.startswith(f"{RESEARCH_SOURCE}:") for key in keys)


# --------------------------------------------------------------------------
# Run journaling
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_completed_run_journals_one_row_carrying_no_content(session):
    gatherer = _Gatherer([_finding("a secret paragraph of evidence", "https://example.test/a")])
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        gatherer=gatherer, budget=ENABLED,
    )
    assert result.journalled is True

    journal = (await session.execute(text(
        "SELECT event_type, object_type, project, source, payload FROM events "
        "WHERE event_type = 'research_run'"
    ))).mappings().all()
    assert len(journal) == 1
    row = journal[0]
    assert (row["object_type"], row["project"], row["source"]) == (
        "system", "research-lane", RESEARCH_SOURCE,
    )
    payload = row["payload"]
    assert payload["run_id"] == str(result.run_id)
    assert payload["filed"] == 1
    assert payload["origins_manufactured"] is True
    assert "secret paragraph" not in str(payload)


def test_research_run_is_in_the_closed_event_vocabulary():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert "research_run" in EVENT_TYPES
    assert "system" in OBJECT_TYPES
