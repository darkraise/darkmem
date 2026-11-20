"""T3.07 — the research loop's three done-when clauses, the seam T3.08 needs,
and (T3.27) the one door that reaches it.

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
* **A failed run leaves no partial state.** Covered at the one write: a
  failure *inside* the capture call after rows are enqueued and before the
  commit.

The origin tests are the ones that matter two months from now. This loop
manufactures origins rather than observing them, so the corpus has to be able
to slice them out; ``is_researched_origin`` is that slice and it is asserted
against a real human-shaped key, not only against itself.
"""
from __future__ import annotations

import ast
import inspect
import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.mcp.server as mcp_server
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
from app.schemas.research import ResearchFindingInput
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
    # T3.28 split the `auto_research` config row into its own module so a
    # config surface could reach it without importing this one. The loop still
    # reads its budget, so the whitelist gains the split half rather than the
    # loop keeping a second copy of the reader.
    "app.services.research_config",
    "app.utils.ids",
}


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


def test_the_door_and_the_loop_derive_one_ceiling():
    """Two derivations, one source. Both read `MemoryBatchCreate`'s own bound —
    the door needs it at module scope (importing the loop there is the
    invariant-15 crossing the scan flags outside the tool body) and the loop
    needs it to refuse. They cannot drift in value, and this pins that so a
    future edit to either cannot make them disagree silently."""
    from app.schemas.research import MAX_FINDINGS_CEILING as DOOR_CEILING

    assert DOOR_CEILING == MAX_FINDINGS_CEILING == 100


@pytest.mark.asyncio
async def test_a_list_past_the_ceiling_is_refused_at_the_wire():
    """The schema bound, not only the runtime budget. An unauthenticated door
    should refuse an oversized list before validating and materialising it,
    and no configured budget can authorise more than the capture cap anyway."""
    from pydantic import BaseModel, Field
    from typing import Annotated

    from app.schemas.research import ResearchFindingInput

    class _Door(BaseModel):
        findings: Annotated[
            list[ResearchFindingInput], Field(max_length=MAX_FINDINGS_CEILING),
        ]

    over = [{"content": f"f{i}"} for i in range(MAX_FINDINGS_CEILING + 1)]
    with pytest.raises(ValidationError):
        _Door(findings=over)

    at_the_bound = [{"content": f"f{i}"} for i in range(MAX_FINDINGS_CEILING)]
    assert len(_Door(findings=at_the_bound).findings) == MAX_FINDINGS_CEILING


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
    findings = [_finding(f"finding {i}", f"https://example.test/{i}") for i in range(5)]
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        findings=findings, service=service, budget=ENABLED,
    )
    assert len(service.calls) == 1
    assert len(service.calls[0]) == 5
    assert result.filed == 5


@pytest.mark.asyncio
async def test_a_run_lands_in_the_ordinary_capture_buffer(session):
    """The rows arrive as buffered captures — the 202 path every door uses."""
    findings = [
        _finding("pgvector stores fixed-dimension vectors.", "https://example.test/a"),
        _finding("HNSW is pgvector's graph index.", "https://example.test/b"),
    ]
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        findings=findings, budget=ENABLED,
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


# --------------------------------------------------------------------------
# Clause 2 — Tier-C, bounded by a config budget
# --------------------------------------------------------------------------


_LOOP_RULES = ReachabilityRules(
    forbidden_modules=frozenset({"app.services.auto_research"}),
    forbidden_attrs=frozenset({"auto_research"}),
    forbidden_literals=frozenset({"auto_research"}),
)

RESEARCH_DOOR = "app/api/mcp/server.py"
RESEARCH_TOOL = "research_run"


def _research_door_exempt_node_ids(rel: str, tree: ast.Module) -> set[int]:
    """T3.27's one sanctioned crossing, found by structural role, not by text.

    The scan below stays blanket over `app/`, which means the door T3.27
    landed trips it exactly as an unsanctioned reach would — deliberately, so
    that reaching this loop is an argued act. This is the argument, expressed
    the way `tests/test_dream_jobs.py` expresses the dream-job family's one
    boot registration: the exemption is scoped to nodes *inside the research
    tool's own body*, so the same import copied to module level, or into
    `memory_add`, or into any other tool in the same file, is still an
    offender. A text-matching allowlist could not tell those apart — the two
    statements render identically.

    The `Call` arm suppresses nothing: `run_research(...)` matches no route
    this scanner checks (the loader-call route only fires on
    `import_module`/`__import__` with a relative literal name). It is
    collected because `test_the_door_is_the_sanctioned_crossing` reuses this
    same walk as its presence witness, and a second copy of the walk would
    drift from this one.
    """
    if rel != RESEARCH_DOOR:
        return set()
    tool = next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == RESEARCH_TOOL
        ),
        None,
    )
    if tool is None:
        return set()
    exempt: set[int] = set()
    for node in ast.walk(tool):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module == "app.services.auto_research"
        ):
            exempt.add(id(node))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_research"
        ):
            exempt.add(id(node))
    return exempt


CONFIG_MODULE = "app/services/research_config.py"


def _config_key_exempt_node_ids(rel: str, tree: ast.Module) -> set[int]:
    """The config row's own key constant, and nothing else (T3.28).

    `auto_research` is in `forbidden_literals` as the loop module's basename,
    and it is *also* the `config` row key — so the module that owns that key
    trips the literal route by holding its own name. The exemption is scoped to
    the single assignment `AUTO_RESEARCH_CONFIG_KEY = "auto_research"`, not to
    the file: an import of the loop, an attribute reach through the package, or
    the same literal anywhere else in this module is still an offender.

    Splitting the config out of the loop is what made this necessary and is
    also why it is safe: a config surface must be able to read and write the
    row without importing the Tier-C module, and the alternative — exempting
    the *route* — would have widened a guard that is doing its job.
    """
    if rel != CONFIG_MODULE:
        return set()
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if "AUTO_RESEARCH_CONFIG_KEY" in names:
            exempt.update(id(child) for child in ast.walk(node))
    return exempt


def _loop_reach_offenders(paths: list[Path], root: Path) -> list[str]:
    def exempt(rel: str, tree: ast.Module) -> set[int]:
        return _research_door_exempt_node_ids(rel, tree) | _config_key_exempt_node_ids(rel, tree)

    return find_forbidden_reach(
        paths, root, _LOOP_RULES,
        skip_files=frozenset({LOOP_MODULE}),
        exempt_node_ids=exempt,
    )


def test_the_config_key_exemption_is_one_assignment_not_the_file():
    """The drill: the identical literal elsewhere in the config module is still
    an offender, so the exemption cannot become a whole-file pass."""
    tree = ast.parse(
        'AUTO_RESEARCH_CONFIG_KEY = "auto_research"\n'
        'SNEAKY = "auto_research"\n'
    )
    exempt = _config_key_exempt_node_ids(CONFIG_MODULE, tree)
    literals = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and n.value == "auto_research"
    ]
    assert len(literals) == 2
    assert sum(1 for n in literals if id(n) in exempt) == 1


def test_no_app_code_reaches_the_research_loop():
    """Invariant 15's direction: nothing on capture or retrieval may reach a
    Tier-C consumer to accelerate a gate.

    It was vacuous until T3.27 — no module imported the loop at all — and it
    is not any more: the MCP research door reaches it, and the scan records
    that crossing through `exempt_node_ids` rather than being widened, given a
    whole-file pass, or deleted. Everything else still goes red on contact:
    the day someone wires a research run into the pipeline or a search route
    to fill the corpus faster, this fails. The scan is the dream-job family's
    own, so an import spelled across lines, an attribute reach through the
    package, or the dotted path inside a string literal are all covered.

    That the exemption is genuinely narrow — and not a whole-file pass in
    disguise — is proven by `test_a_reach_outside_the_research_tool_is_still_
    flagged`, which puts the identical import in the same file outside the
    tool and watches this scan flag it.
    """
    paths = app_sources(BACKEND)
    offenders = _loop_reach_offenders(paths, BACKEND)
    assert not offenders, (
        "app code reaches the Tier-C research loop: " + "; ".join(offenders)
    )


def test_the_door_is_the_sanctioned_crossing():
    """Exempting a crossing is not the same as having one.

    Every door test below drives `research_run` directly, so none of them
    would notice if the tool stopped importing the loop and started calling
    something else — the exemption would go quiet and the scan would pass on
    a door that no longer reaches anything. This asserts the two nodes the
    exemption resolves actually exist, by the same structural predicate the
    exemption itself uses rather than by reading the file's text.
    """
    tree = ast.parse((BACKEND / RESEARCH_DOOR).read_text(), filename=RESEARCH_DOOR)
    exempt = _research_door_exempt_node_ids(RESEARCH_DOOR, tree)
    kinds = {type(node).__name__ for node in ast.walk(tree) if id(node) in exempt}
    assert kinds == {"ImportFrom", "Call"}, (
        f"{RESEARCH_DOOR} no longer crosses to the research loop inside "
        f"{RESEARCH_TOOL}(): found {kinds!r}"
    )


def test_a_reach_outside_the_research_tool_is_still_flagged(tmp_path):
    """The node-addressable exemption's own negative control.

    A second, textually identical copy of the door's one sanctioned import,
    placed at module level and inside a capture tool in the same file, has the
    same *text* as the exempted node and not the same *structural role*. A
    whole-file `skip_files` pass — or a text-matching allowlist — would let
    both through; this must not.
    """
    offending = tmp_path / "app" / "api" / "mcp" / "server.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "from app.services.auto_research import run_research\n"
        "\n"
        "\n"
        "async def memory_add(content):\n"
        "    from app.services.auto_research import run_research\n"
        "    return run_research\n"
        "\n"
        "\n"
        "async def research_run(subject, project, findings):\n"
        "    from app.services.auto_research import run_research\n"
        "    return await run_research(None, subject=subject, project=project)\n",
        encoding="utf-8",
    )
    offenders = _loop_reach_offenders([offending], tmp_path)
    lines = {int(offender.split(":")[1]) for offender in offenders}
    assert lines == {1, 5}, (
        f"expected the module-level copy and the one inside memory_add to be "
        f"flagged and only the tool's own to be exempt, got {offenders}"
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
async def test_a_disabled_install_refuses_the_run_before_filing(session):
    with pytest.raises(ResearchDisabled):
        await run_research(
            session, subject="s", project="p", findings=[_finding("evidence")],
        )
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
    findings = [_finding(f"f{i}") for i in range(4)]
    with pytest.raises(ResearchBudgetExceeded):
        await run_research(
            session, subject="s", project="p", findings=findings,
            budget=ResearchBudget(enabled=True, max_findings_per_run=3, max_content_chars=100),
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_an_over_long_finding_refuses_the_whole_run(session):
    """Refused, not truncated. A truncated filing would record a run whose
    origin story is untrue in a way nothing downstream could detect."""
    findings = [_finding("ok"), _finding("x" * 200)]
    with pytest.raises(ResearchBudgetExceeded):
        await run_research(
            session, subject="s", project="p", findings=findings,
            budget=ResearchBudget(enabled=True, max_findings_per_run=10, max_content_chars=50),
        )
    assert await _buffer_count(session) == 0


# --------------------------------------------------------------------------
# Clause 3 — a failed run leaves no partial state
# --------------------------------------------------------------------------


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
    findings = [_finding(f"finding {i}") for i in range(3)]
    with pytest.raises(RuntimeError):
        await run_research(
            session, subject="s", project="p", findings=findings, budget=ENABLED,
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

    findings = [_finding("f0"), _finding("f1")]
    monkeypatch.setattr(AsyncSession, "commit", commit)
    result = await run_research(
        session, subject="s", project="p", findings=findings, budget=ENABLED,
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
    findings = [_finding("real evidence"), _finding("")]
    with pytest.raises(ValidationError):
        await run_research(
            session, subject="s", project="p", findings=findings, budget=ENABLED,
        )
    assert await _buffer_count(session) == 0


@pytest.mark.asyncio
async def test_a_run_that_gathers_nothing_writes_nothing(session):
    result = await run_research(
        session, subject="s", project="p", findings=[], budget=ENABLED,
    )
    assert (result.gathered, result.filed) == (0, 0)
    assert result.journalled is False
    assert await _buffer_count(session) == 0


# --------------------------------------------------------------------------
# The origin discipline, and the seam T3.08 fills
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_researched_capture_carries_the_reserved_source(session):
    findings = [_finding("a", "https://example.test/a")]
    await run_research(
        session, subject="s", project="p", findings=findings, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    assert {row.source for row in rows} == {RESEARCH_SOURCE}
    assert all(is_researched_origin(row.metadata_["origin_key"]) for row in rows)


@pytest.mark.asyncio
async def test_findings_without_source_identity_are_one_origin(session):
    """The honest undercount doc 09 section 6 requires.

    T3.08 filled the seam, so two *identified* sources are now two origins —
    ``tests/test_research_origins.py`` owns that half. This is the half that did
    not change: findings whose identity the gatherer could not establish still
    resolve to a single `origin_key`, because minting one apiece would be
    manufactured corroboration.
    """
    findings = [
        _finding("claim", None),
        _finding("same claim", None),
    ]
    await run_research(
        session, subject="s", project="p", findings=findings, budget=ENABLED,
    )
    rows = await _buffer_rows(session)
    assert len({row.metadata_["origin_key"] for row in rows}) == 1


@pytest.mark.asyncio
async def test_the_merged_origin_never_fires_a_corroboration_gate(session):
    """It lands in the capture layer's anonymous bucket on purpose.

    `fact_sources` folds every `unknown:`-prefixed key into one reserved
    bucket that contributes to the count and to nothing else, so a research
    finding of unestablished identity cannot reach the N = 2 diversity bar
    alongside one real witness.
    """
    findings = [_finding("claim", None)]
    await run_research(
        session, subject="s", project="p", findings=findings, budget=ENABLED,
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


def test_the_declared_form_t3_08_mints_is_recognised_too():
    """T3.08 replaced the merged key with a declared one, and the slice
    predicate did not have to be edited for it — a widening made at that moment
    would have left a gap exactly where the origins start counting."""
    assert is_researched_origin(f"{RESEARCH_SOURCE}:example.test/a")
    assert is_researched_origin(
        research_origin_key(_finding("a", "https://example.test/a"), project="p")
    )


@pytest.mark.asyncio
async def test_the_origin_seam_is_per_finding(session, monkeypatch):
    """Proof the seam is real: nothing but `research_origin_id` decides
    whether two findings share an origin.

    It stood in for T3.08 before that task landed and is kept after it for the
    same reason, pointed the other way: substituting an identity function still
    changes the origins, so the *call site* remains per-finding and no second
    place has quietly acquired a say in what an origin is.
    """
    monkeypatch.setattr(
        auto_research, "research_origin_id", lambda finding: finding.source_id,
    )
    findings = [
        _finding("claim", "https://example.test/a"),
        _finding("same claim", "https://other.test/b"),
    ]
    await run_research(
        session, subject="s", project="p", findings=findings, budget=ENABLED,
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
    findings = [_finding("a secret paragraph of evidence", "https://example.test/a")]
    result = await run_research(
        session, subject="pgvector", project="research-lane",
        findings=findings, budget=ENABLED,
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


# --------------------------------------------------------------------------
# T3.27 — the door
#
# The loop was reachable from tests alone: no job, no route, no MCP tool, no
# script, and an in-process `AsyncSession` in its signature, so the one actor
# that could honestly drive it — a web-capable agent outside the box — could
# not call it even in principle. The door is `research_run` on `/mcp`; the
# argument for that shape over a route or a job is recorded above the tool in
# `app/api/mcp/server.py`. What is asserted here is the part a reviewer cannot
# take on trust: that the door files through the loop and not past it, that
# `enabled` still governs it, and that nothing a caller sends can shed the
# manufactured-origin disclosure.
# --------------------------------------------------------------------------


@pytest.fixture
def door(session, monkeypatch):
    """The MCP tools' module-level session factory, pointed at the test session."""
    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    monkeypatch.setattr(mcp_server, "_pipeline", None)
    return session


async def _arm(session, **overrides) -> None:
    await session.execute(delete(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY))
    session.add(Config(key=AUTO_RESEARCH_CONFIG_KEY, value={
        "enabled": True, **overrides,
    }))
    await session.flush()


async def test_the_door_is_registered_as_an_mcp_tool():
    """A tool nothing registers is the gap T3.27 exists to close, one layer up."""
    registered = {tool.name for tool in await mcp_server.mcp.list_tools()}
    assert RESEARCH_TOOL in registered


@pytest.mark.asyncio
async def test_the_door_files_a_run_through_the_ordinary_capture_buffer(door):
    """End to end through the door: the same buffered 202 path every capture
    door funnels into, with the run's identity reported back to the caller."""
    await _arm(door)

    body = json.loads(await mcp_server.research_run(
        subject="pgvector",
        project="research-lane",
        findings=[
            {"content": "pgvector stores fixed-dimension vectors.",
             "source_id": "https://example.test/a"},
            {"content": "HNSW is pgvector's graph index.",
             "source_id": "https://example.test/b"},
        ],
    ))

    assert body["status"] == "filed"
    assert body["filed"] == 2
    assert body["origins_manufactured"] is True
    assert body["project"] == "research-lane"

    rows = await _buffer_rows(door)
    assert len(rows) == 2
    assert {row.project for row in rows} == {"research-lane"}
    assert {str(row.metadata_["memory_id"]) for row in rows} == set(body["memory_ids"])
    # Two identified sources, two origins — the door does not collapse what
    # T3.08 separated.
    assert len({row.metadata_["origin_key"] for row in rows}) == 2


@pytest.mark.asyncio
async def test_the_door_refuses_while_the_loop_is_disabled(door):
    """Building a door is not arming the loop.

    The default is off and the refusal is the loop's own, reached before
    anything is written — so an install that has never made the owner's
    decision cannot be made to file by calling the tool.
    """
    await door.execute(delete(Config).where(Config.key == AUTO_RESEARCH_CONFIG_KEY))

    body = json.loads(await mcp_server.research_run(
        subject="pgvector", project="p",
        findings=[{"content": "evidence", "source_id": "https://example.test/a"}],
    ))

    assert body["status"] == "unavailable"
    assert body.get("filed") == 0
    assert "memory_ids" not in body
    assert await _buffer_count(door) == 0


@pytest.mark.asyncio
async def test_the_door_cannot_file_a_row_that_looks_like_ordinary_capture(door):
    """The disclosure has to survive a caller trying to shed it.

    `metadata` is the one free-form field the door forwards, and it is spread
    *under* the loop's own keys — so a caller who names `source` or
    `origin_key` in it changes nothing about the row that lands. Both markers
    are the machine-enforced slice a later measurement uses to separate
    manufactured origins from observed ones; a row that shed either would be
    pooled with real capture and nothing downstream could tell.
    """
    await _arm(door)

    await mcp_server.research_run(
        subject="pgvector", project="research-lane",
        findings=[{
            "content": "a finding that would rather look human",
            "source_id": "https://example.test/a",
            "metadata": {
                "source": "claude-code",
                "origin_key": "claude-code:boot-uuid",
                "research": {"subject": "something else"},
            },
        }],
    )

    rows = await _buffer_rows(door)
    assert len(rows) == 1
    row = rows[0]
    assert row.source == RESEARCH_SOURCE
    assert is_researched_origin(row.metadata_["origin_key"])
    assert row.metadata_["metadata"]["research"]["subject"] == "pgvector"


def test_the_door_offers_no_way_to_declare_an_identity():
    """The structural half of the same claim, which the behavioural test above
    cannot make: not that a declared identity is overridden, but that there is
    nowhere to declare one.

    No `source`, no `origin_key`, and — the one a reviewer would miss — no
    `ctx`, so the `X-Darkmem-Client` and `X-Darkmem-Origin` headers that steer
    every other MCP capture's identity have no route into a research run at
    all. `extra="forbid"` on the finding model makes a caller that tries
    anyway fail loudly instead of watching a key be dropped.
    """
    parameters = set(inspect.signature(mcp_server.research_run).parameters)
    assert parameters == {"subject", "project", "findings"}

    fields = set(ResearchFindingInput.model_fields)
    assert fields == {"content", "source_id", "metadata"}
    assert ResearchFindingInput.model_config.get("extra") == "forbid"
    with pytest.raises(ValidationError):
        ResearchFindingInput.model_validate({"content": "x", "source": "claude-code"})


@pytest.mark.asyncio
async def test_a_source_id_shaped_like_another_doors_key_stays_researched(door):
    """A declared id cannot forge its way out of the research prefix.

    `resolve_origin_key` composes `<source>:<declared>` and the loop's own
    bounding strips `:` from the declared half, so the most obvious attempt —
    handing the door another door's whole key as a locator — still lands under
    `research:` and stays inside the slice.
    """
    await _arm(door)

    await mcp_server.research_run(
        subject="s", project="p",
        findings=[{"content": "evidence", "source_id": "mcp:boot-uuid"}],
    )

    rows = await _buffer_rows(door)
    key = rows[0].metadata_["origin_key"]
    assert key.startswith(f"{RESEARCH_SOURCE}:")
    assert is_researched_origin(key)


@pytest.mark.asyncio
async def test_the_door_refuses_an_over_budget_run_rather_than_trimming(door):
    """The budget bounds what the door may file, and the refusal is whole-run.

    A door that sliced the supplied findings down to the budget would file a
    partial run and report it filed — a corpus whose origin story is untrue in
    a way nothing downstream could detect. The door hands every supplied
    finding to the loop precisely so the budget can refuse them all.
    """
    await _arm(door, max_findings_per_run=2)

    with pytest.raises(ResearchBudgetExceeded):
        await mcp_server.research_run(
            subject="s", project="p",
            findings=[
                {"content": f"finding {i}", "source_id": f"https://example.test/{i}"}
                for i in range(3)
            ],
        )
    assert await _buffer_count(door) == 0


@pytest.mark.asyncio
async def test_the_door_refuses_a_run_with_nothing_in_it(door):
    """An empty run would come back filed-shaped with `filed: 0`, which reads
    to an agent as "stored" — the same reason the batch cap refuses an empty
    batch instead of accepting it as a successful no-op."""
    await _arm(door)

    with pytest.raises(ValueError):
        await mcp_server.research_run(subject="s", project="p", findings=[])
    assert await _buffer_count(door) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("subject,project", [("", "p"), ("   ", "p"), ("s", ""), ("s", " ")])
async def test_the_door_requires_a_subject_and_a_project(door, subject, project):
    """Neither is defaulted. A blank project would land manufactured origins in
    whatever the write path treats as the fallback scope, which is the one
    project a reader is least likely to be auditing for them."""
    await _arm(door)

    with pytest.raises(ValueError):
        await mcp_server.research_run(
            subject=subject, project=project,
            findings=[{"content": "evidence", "source_id": "https://example.test/a"}],
        )
    assert await _buffer_count(door) == 0
