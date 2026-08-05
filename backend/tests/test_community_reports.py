"""T2.19 — community `report_string` generation: status, churn survival, and
the never-on-a-read-path guard.

**What T2.18 already did.** `label = dominant entities` is written by
`memory_community_detection.detect_for_project` via
`memory_community_labels.label_communities` before any community row is ever
inserted (`tests/test_communities.py` already covers determinism, the
display-name rendering, and collision disambiguation up to and including the
four-entity-widened-label provenance fix, `3e21aa1`). Nothing here duplicates
that: every fixture below seeds communities with an already-decided label,
the same way `detect_for_project` would leave them, and only exercises the
`report_string` half of doc 06 §7's Report box.

**The organising principle**, mirrored from `test_communities.py`: no test
here pins which memories a real Leiden run would cluster together, because
that suite already owns that property. Everything below is either a pure
function of stored columns (`report_status`) or an integration test seeded
directly through `repo.replace_project_communities`, exactly like T2.18's own
fixtures.
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories import memory_communities as repo
from app.services import memory_community_reports as reports
from app.utils.ids import new_id

from tests._reachability_scan import ReachabilityRules, app_sources, find_forbidden_reach

PROJECT = "t219-reports"
OTHER_PROJECT = "t219-reports-other"

BACKEND = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_INSERT_MEMORY = text(
    "INSERT INTO memories (id, content, source, project, status) "
    "VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')"
)


async def seed_memory(session, project: str = PROJECT, content: str = "seeded memory"):
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {"id": str(memory_id), "content": content, "project": project},
    )
    return memory_id


class StubLLM:
    """Minimal orchestrator stand-in: records every call and replays canned
    responses in order, mirroring `test_verification_judge.py`'s `StubLLM`."""

    def __init__(self, responses=None, *, fail_on: set[str] | None = None):
        self.responses = list(responses or [])
        self.fail_on = fail_on or set()
        self.calls: list[dict] = []

    async def chat_completion(self, purpose, messages, **kwargs):
        self.calls.append({"purpose": purpose, "messages": messages, **kwargs})
        label = None
        for message in messages:
            if message["role"] == "user" and "Topic label:" in message["content"]:
                label = message["content"].split("Topic label:")[1].splitlines()[0].strip()
        if label in self.fail_on:
            raise RuntimeError(f"stub failure for {label}")
        if self.responses:
            return self.responses.pop(0)
        return f"a report about {label}"


@pytest_asyncio.fixture
async def committing(setup_database):
    """A real session factory with real commits — `generate_reports` and
    `restore_reports` open their own session per community/label, which the
    rollback-per-test `session` fixture cannot express."""
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM memory_communities WHERE project LIKE 't219-%'")
            )
            await cleanup.execute(
                text("DELETE FROM memories WHERE project LIKE 't219-%'")
            )
            await cleanup.commit()
        await engine.dispose()


def _row(label="alpha", report_string=None, properties=None, memory_ids=()):
    return repo.CommunityRow(
        id=new_id(),
        project=PROJECT,
        label=label,
        report_string=report_string,
        properties=properties or {},
        created_at=None,
        memory_ids=tuple(memory_ids),
    )


# ---------------------------------------------------------------------------
# report_status — pure function, the three-state (four-value) contract
# ---------------------------------------------------------------------------


def test_status_is_ready_when_report_string_is_set():
    row = _row(report_string="a report", properties={"size": 5})
    assert reports.report_status(row) == reports.REPORT_STATUS_READY


def test_status_is_pending_when_eligible_and_unattempted():
    row = _row(properties={"size": 5})
    assert reports.report_status(row) == reports.REPORT_STATUS_PENDING


def test_status_is_skipped_below_the_minimum_size():
    row = _row(properties={"size": 2})
    assert reports.report_status(row, min_report_size=3) == reports.REPORT_STATUS_SKIPPED


def test_status_is_failed_when_an_attempt_recorded_an_error():
    row = _row(properties={"size": 5, "report_error": "boom"})
    assert reports.report_status(row) == reports.REPORT_STATUS_FAILED


def test_status_falls_back_to_member_count_when_size_is_absent():
    row = _row(properties={}, memory_ids=(new_id(), new_id()))
    assert reports.report_status(row, min_report_size=3) == reports.REPORT_STATUS_SKIPPED


def test_ready_wins_over_a_stale_error_marker():
    """A community that failed once and later succeeded (carried forward or
    regenerated) must read as ready, not failed — `report_string` is checked
    first."""
    row = _row(report_string="now it worked", properties={"size": 5, "report_error": "old"})
    assert reports.report_status(row) == reports.REPORT_STATUS_READY


# ---------------------------------------------------------------------------
# generate_reports — the LLM call, off the hot path, per community
# ---------------------------------------------------------------------------


async def test_generate_reports_fills_in_pending_communities(committing):
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        c = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        (community_id,) = await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b, c), properties={"size": 3})],
        )
        await session.commit()

    llm = StubLLM()
    outcome = await reports.generate_reports(factory, llm, PROJECT)

    assert outcome.attempted == 1
    assert outcome.generated == 1
    assert outcome.failed == 0
    assert llm.calls[0]["purpose"] == "summarization"

    async with factory() as session:
        row = (await repo.list_with_members(session, PROJECT))[0]
    assert row.report_string == "a report about alpha"
    assert reports.report_status(row) == reports.REPORT_STATUS_READY


async def test_generate_reports_skips_undersized_communities(committing):
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="tiny", memory_ids=(a, b), properties={"size": 2})],
        )
        await session.commit()

    llm = StubLLM()
    outcome = await reports.generate_reports(factory, llm, PROJECT)

    assert outcome.attempted == 0
    assert llm.calls == []
    async with factory() as session:
        row = (await repo.list_with_members(session, PROJECT))[0]
    assert reports.report_status(row) == reports.REPORT_STATUS_SKIPPED


async def test_generate_reports_records_a_failure_without_raising(committing):
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        c = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b, c), properties={"size": 3})],
        )
        await session.commit()

    llm = StubLLM(fail_on={"alpha"})
    outcome = await reports.generate_reports(factory, llm, PROJECT)

    assert outcome.attempted == 1
    assert outcome.generated == 0
    assert outcome.failed == 1
    assert outcome.labels_failed == ["alpha"]

    async with factory() as session:
        row = (await repo.list_with_members(session, PROJECT))[0]
    assert row.report_string is None
    assert reports.report_status(row) == reports.REPORT_STATUS_FAILED
    assert "stub failure" in row.properties["report_error"]


async def test_a_failed_community_is_retried_next_run_not_stuck(committing):
    """Doc 06 §7's delete-and-rewrite resets `properties` wholesale, so a
    `failed` mark from one run must not survive into the next as a permanent
    state — it must read `pending` again once size is re-supplied fresh."""
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        c = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b, c), properties={"size": 3})],
        )
        await session.commit()

    await reports.generate_reports(factory, StubLLM(fail_on={"alpha"}), PROJECT)

    # The next detection run rewrites the project's communities from scratch
    # (T2.18's `replace_project_communities`), which is what actually clears
    # the stale `report_error` — simulated here exactly as `detect_for_project`
    # would drive it.
    async with factory() as session:
        await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b, c), properties={"size": 3})],
        )
        await session.commit()

    outcome = await reports.generate_reports(factory, StubLLM(), PROJECT)
    assert outcome.attempted == 1
    assert outcome.generated == 1


async def test_report_generation_journals_one_row_per_attempt(committing):
    # `events` is append-only (no UPDATE/DELETE, CLAUDE.md), so a project
    # shared with the other `committing` tests above would accumulate their
    # journal rows too. A dedicated project keeps this assertion exact.
    project = f"{PROJECT}-journal"
    factory = committing
    async with factory() as session:
        a = await seed_memory(session, project)
        b = await seed_memory(session, project)
        c = await seed_memory(session, project)
        await session.commit()
    async with factory() as session:
        await repo.replace_project_communities(
            session, project,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b, c), properties={"size": 3})],
        )
        await session.commit()

    await reports.generate_reports(factory, StubLLM(), project)

    async with factory() as session:
        rows = (await session.execute(
            text(
                "SELECT object_id, payload FROM events "
                "WHERE event_type = 'consolidated' AND object_type = 'topic' "
                "AND project = CAST(:p AS text)"
            ),
            {"p": project},
        )).all()
    assert len(rows) == 1
    object_id, payload = rows[0]
    assert object_id is None
    assert payload == {"label": "alpha", "status": "ready"}


# ---------------------------------------------------------------------------
# Surviving the churn — snapshot / restore, keyed on label via get_by_label
# ---------------------------------------------------------------------------


async def test_a_ready_report_carries_forward_across_a_rewrite_by_label(committing):
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        (first,) = await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b), properties={"size": 2})],
        )
        await repo.set_report(session, first, report_string="the original report")
        await session.commit()

    async with factory() as session:
        snapshot = await reports.snapshot_reports(session, PROJECT)
    assert snapshot == {"alpha": reports.CarriedReport(report_string="the original report")}

    # Simulate the nightly rewrite: the label survives, the id does not.
    async with factory() as session:
        (second,) = await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a,), properties={"size": 1})],
        )
        await session.commit()
    assert second != first

    async with factory() as session:
        outcome = await reports.restore_reports(session, PROJECT, snapshot)
        await session.commit()
    assert outcome.carried_forward == 1

    async with factory() as session:
        row = await repo.get_by_label(session, PROJECT, "alpha")
    assert row.id == second
    assert row.report_string == "the original report"
    assert reports.report_status(row) == reports.REPORT_STATUS_READY


async def test_a_dropped_label_does_not_carry_a_report_onto_the_wrong_topic(committing):
    """The other half of the churn contract: if the label does not survive
    the rewrite, nothing carries forward onto whatever now exists — a stale
    report must never attach to an unrelated new topic."""
    factory = committing
    async with factory() as session:
        a = await seed_memory(session)
        b = await seed_memory(session)
        await session.commit()
    async with factory() as session:
        (first,) = await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="alpha", memory_ids=(a, b), properties={"size": 2})],
        )
        await repo.set_report(session, first, report_string="the original report")
        await session.commit()

    async with factory() as session:
        snapshot = await reports.snapshot_reports(session, PROJECT)

    async with factory() as session:
        await repo.replace_project_communities(
            session, PROJECT,
            [repo.CommunityDraft(label="beta", memory_ids=(a, b), properties={"size": 2})],
        )
        await session.commit()

    async with factory() as session:
        outcome = await reports.restore_reports(session, PROJECT, snapshot)
        await session.commit()
    assert outcome.carried_forward == 0

    async with factory() as session:
        row = await repo.get_by_label(session, PROJECT, "beta")
    assert row.report_string is None
    assert reports.report_status(row) == reports.REPORT_STATUS_SKIPPED


# ---------------------------------------------------------------------------
# T2.92 — an empty completion is a failure, and the retry loop is bounded
# ---------------------------------------------------------------------------


async def _seed_one_community(factory, project, label="alpha", properties=None):
    async with factory() as session:
        ids = tuple([await seed_memory(session, project) for _ in range(3)])
        await session.commit()
    await _rewrite(factory, project, ids, label=label, properties=properties)
    return ids


async def _rewrite(factory, project, ids, *, label="alpha", properties=None):
    """One detection run's delete-and-rewrite, driven exactly as
    `detect_for_project` would leave it."""
    async with factory() as session:
        await repo.replace_project_communities(
            session, project,
            [repo.CommunityDraft(
                label=label, memory_ids=ids, properties=properties or {"size": 3},
            )],
        )
        await session.commit()


async def _churn(factory, project, ids, *, label="alpha"):
    """The full seam T2.53's runner is handed: snapshot, rewrite, restore."""
    async with factory() as session:
        snapshot = await reports.snapshot_reports(session, project)
    await _rewrite(factory, project, ids, label=label)
    async with factory() as session:
        await reports.restore_reports(session, project, snapshot)
        await session.commit()


async def _only_row(factory, project):
    async with factory() as session:
        return (await repo.list_with_members(session, project))[0]


async def test_generate_report_refuses_an_empty_completion(session):
    """The guard is on the write path: an empty completion never becomes a
    return value, so `set_report` can never be handed one."""
    a = await seed_memory(session)
    row = _row(properties={"size": 3}, memory_ids=(a,))
    with pytest.raises(reports.EmptyReportError):
        await reports.generate_report(session, StubLLM(responses=["   \n\t "]), row)


@pytest.mark.parametrize("empty", ["", "   \n\t "])
async def test_an_empty_completion_lands_as_failed_never_as_pending(committing, empty):
    """The defect this task exists for: stored raw, `""` reads as *falsy*,
    which `report_status` cannot tell apart from "never generated" — so the
    topic reads `pending` forever and every later pass pays for the call
    again. It must read `failed`, with the reason on the row."""
    factory = committing
    project = f"{PROJECT}-empty-{len(empty)}"
    await _seed_one_community(factory, project)

    llm = StubLLM(responses=[empty])
    outcome = await reports.generate_reports(factory, llm, project)

    assert outcome.attempted == 1
    assert outcome.generated == 0
    assert outcome.failed == 1

    row = await _only_row(factory, project)
    assert row.report_string is None
    assert reports.report_status(row) != reports.REPORT_STATUS_PENDING
    assert reports.report_status(row) == reports.REPORT_STATUS_FAILED
    assert "empty completion" in row.properties["report_error"]
    assert reports.report_attempts(row) == 1


async def test_one_failure_still_retries_after_the_rewrite(committing):
    """The cap must not turn the first transient vendor error into a
    permanent state — below the cap the carried count restores without the
    error, so the community reads `pending` and gets its retry."""
    factory = committing
    project = f"{PROJECT}-retry"
    ids = await _seed_one_community(factory, project)

    await reports.generate_reports(factory, StubLLM(fail_on={"alpha"}), project)
    await _churn(factory, project, ids)

    carried = await _only_row(factory, project)
    assert reports.report_attempts(carried) == 1
    assert reports.report_status(carried) == reports.REPORT_STATUS_PENDING

    llm = StubLLM()
    outcome = await reports.generate_reports(factory, llm, project)
    assert outcome.generated == 1
    assert len(llm.calls) == 1

    row = await _only_row(factory, project)
    assert reports.report_status(row) == reports.REPORT_STATUS_READY


async def test_the_retry_loop_is_bounded_across_detection_rewrites(committing):
    """The re-billing loop, closed. Without the carried count the rewrite
    resets `properties` wholesale every run, so the cap is unreachable and a
    permanently-empty topic costs one model call per cycle forever."""
    factory = committing
    project = f"{PROJECT}-bounded"
    ids = await _seed_one_community(factory, project)

    calls_per_cycle = []
    for _ in range(reports.DEFAULT_MAX_REPORT_ATTEMPTS):
        llm = StubLLM(responses=[""])
        await reports.generate_reports(factory, llm, project)
        calls_per_cycle.append(len(llm.calls))
        await _churn(factory, project, ids)

    assert calls_per_cycle == [1] * reports.DEFAULT_MAX_REPORT_ATTEMPTS

    exhausted = await _only_row(factory, project)
    assert reports.report_status(exhausted) == reports.REPORT_STATUS_FAILED

    llm = StubLLM(responses=[""])
    outcome = await reports.generate_reports(factory, llm, project)
    assert llm.calls == []
    assert outcome.attempted == 0


async def test_an_exhausted_community_is_never_called_again(committing):
    """The cap is enforced in the generator too, not only by the error the
    restore carries — a count at the cap stops the call even if the row
    reached that state some other way."""
    factory = committing
    project = f"{PROJECT}-exhausted"
    await _seed_one_community(
        factory, project,
        properties={"size": 3, "report_attempts": reports.DEFAULT_MAX_REPORT_ATTEMPTS},
    )

    llm = StubLLM()
    outcome = await reports.generate_reports(factory, llm, project)

    assert llm.calls == []
    assert outcome.attempted == 0
    assert outcome.exhausted == 1

    row = await _only_row(factory, project)
    assert reports.report_status(row) == reports.REPORT_STATUS_FAILED


# ---------------------------------------------------------------------------
# set_report's properties_patch — merges, and clears report_error on success
# ---------------------------------------------------------------------------


async def test_set_report_merges_properties_without_clobbering_t218s_keys(session):
    a = await seed_memory(session)
    (community_id,) = await repo.replace_project_communities(
        session, PROJECT,
        [repo.CommunityDraft(
            label="alpha", memory_ids=(a,),
            properties={"size": 1, "dominant_entities": [{"name": "postgres"}]},
        )],
    )
    await session.flush()

    await repo.set_report(
        session, community_id, properties_patch={"report_error": "boom"}
    )
    await session.flush()
    row = await repo.get_by_label(session, PROJECT, "alpha")
    assert row.properties["report_error"] == "boom"
    assert row.properties["dominant_entities"] == [{"name": "postgres"}]
    assert row.properties["size"] == 1

    await repo.set_report(session, community_id, report_string="all good now")
    await session.flush()
    row = await repo.get_by_label(session, PROJECT, "alpha")
    assert row.report_string == "all good now"
    assert "report_error" not in row.properties
    assert row.properties["dominant_entities"] == [{"name": "postgres"}]


# ---------------------------------------------------------------------------
# Never on a read path — the AST scan (invariant 15), mirroring T2.18's T13
# ---------------------------------------------------------------------------

REPORTS_BASENAME = "memory_community_reports"
REPORTS_MODULE = f"app.services.{REPORTS_BASENAME}"
REPORTS_PATH = "app/services/memory_community_reports.py"
REPORTS_MODULE = f"app.services.{REPORTS_BASENAME}"

# T2.20 amendment (2026-08-02): this module's own docstring names T2.20's
# browsing surface as the intended consumer of `report_status` — "T2.20
# inherits `report_status` as the read-time projection its browsing surface
# renders from, rather than re-deriving the three-state classification
# against `report_string IS NULL` directly." A blanket module-name ban
# cannot honour that without also forbidding the only correct way to satisfy
# it, so the scan is precise at the symbol level for exactly these five pure,
# side-effect-free names (a plain function of stored columns plus its four
# string constants; no session, no LLM, no I/O). Every other route to this
# module — a whole-module import, an attribute-style `from app.services
# import memory_community_reports`, any of the LLM-calling functions
# (`generate_report`, `generate_reports`), or a mixed import naming even one
# unsafe symbol alongside a safe one — is still caught, proven below.
SAFE_REPORT_PROJECTION_SYMBOLS = frozenset(
    {
        "report_status",
        "REPORT_STATUS_READY",
        "REPORT_STATUS_PENDING",
        "REPORT_STATUS_FAILED",
        "REPORT_STATUS_SKIPPED",
    }
)

# T2.67 folds this scan onto the shared `_reachability_scan` walker (raised
# in that task's re-review as a third instance of the same decorative-guard
# shape: this scan's own `if REPORTS_BASENAME not in source: continue`
# prefilter ran on raw source *text* before the AST walk below ever got a
# chance to run, so `import_module('app.services.memory_community' '_
# reports')` — two adjacent string literals the parser folds into one
# constant, exactly the case this scan's own docstring claimed to cover —
# never even reached the parser: the unsplit basename never appears in the
# raw text, so the prefilter skipped the file outright. Dropping the
# prefilter and reusing the shared walker closes that the same way T2.67's
# Critical fix closed the family/detector scans' literal-route gap.
#
# **This is not a pure superset of the scan it replaces — say what changed,
# not only what was gained.** The old scan matched `REPORTS_BASENAME` by
# *substring* over every non-docstring `str` constant, with no distinction
# between a bare mention and a dotted path. The shared walker's
# `forbidden_literals` is exact-match-only (T2.67's Critical fix made that
# deliberate, to stop a bare name colliding with ordinary prose elsewhere in
# the tree); `forbidden_modules` covers the dotted `app.services.<x>` form
# by boundary-substring, not the bare basename alone. Three shapes that the
# old substring check caught therefore do not survive unchanged:
#   1. `import_module(".memory_community_reports", package="app.services")`
#      — an executable relative-import-plus-package reach. Restored by the
#      loader-call route (`_resolve_relative_loader_call`), which all three
#      scans now share, so this one is not actually lost.
#   2. A prefix-free literal — `"services.memory_community_reports"`,
#      naming the module without `app.services.` — genuinely lost, and
#      folded into the documented computed/partial-spelling bound in
#      `_reachability_scan`'s module docstring rather than chased: turning
#      it into an executable reach needs the missing prefix reconstructed
#      from context, which is runtime string surgery, not a literal spelling.
#   3. A bare mention of the basename inside otherwise-ordinary prose (a
#      non-docstring constant, e.g. "do not call memory_community_reports
#      directly") — also genuinely lost, same disclosed bound, and the
#      same tradeoff the family/detector scans' bare-name exact-match
#      discipline already accepts for the reasons given there.
_REPORTS_RULES = ReachabilityRules(
    forbidden_modules=frozenset({REPORTS_MODULE}),
    forbidden_attrs=frozenset({REPORTS_BASENAME}),
    forbidden_literals=frozenset({REPORTS_BASENAME}),
)




def _safe_projection_import_node_ids(rel: str, tree: ast.Module) -> set[int]:
    """The one legitimate route into this module: a from-import naming only
    pure, side-effect-free projection symbols.

    All-or-nothing per statement — a single unsafe name alongside safe ones
    exempts nothing, so `from ... import report_status, generate_reports`
    is still an offence. Whole-module imports and attribute-style reaches
    are never exempted here, because the exemption is granted to a specific
    `ImportFrom` node, not to the module name appearing in a file.
    """
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == REPORTS_MODULE
            and node.level == 0
            and node.names
            and all(a.name in SAFE_REPORT_PROJECTION_SYMBOLS for a in node.names)
        ):
            exempt.add(id(node))
    return exempt

def _report_module_offenders(paths, backend_root) -> list[str]:
    """Every route from a file under `app/` to the report-generation module.

    Merge resolution (T2.20 + T2.67): T2.67 folds this scan onto the shared
    walker; T2.20 made it precise at the symbol level. Both are load-bearing
    and neither branch had the other, so the symbol precision is carried onto
    the walker as a node exemption rather than as a special case inside the
    scan — the same mechanism `main.py`'s wiring uses, matched by node
    identity within this file's own parse, never by rendered text.
    """
    return find_forbidden_reach(
        paths,
        backend_root,
        _REPORTS_RULES,
        skip_files=frozenset({REPORTS_PATH}),
        exempt_node_ids=_safe_projection_import_node_ids,
    )


def test_no_app_code_reaches_report_generation():
    """Report generation is Tier C: nothing on a capture or retrieval path
    may reach it. This is the structural proof for 'never blocks a read' —
    a call counter cannot show a negative, an AST reachability scan can."""
    assert not _report_module_offenders(app_sources(BACKEND), BACKEND)


def _write(tmp_path, body: str):
    offender = tmp_path / "app" / "services" / "memory.py"
    offender.parent.mkdir(parents=True, exist_ok=True)
    offender.write_text(body)
    return offender


def test_the_scan_catches_a_plain_import_from_a_capture_module(tmp_path):
    offender = _write(
        tmp_path,
        "from app.services.memory_community_reports import generate_reports\n",
    )
    offenders = _report_module_offenders([offender], tmp_path)
    assert len(offenders) == 1
    assert offenders[0].startswith("app/services/memory.py:1:")


def test_the_scan_catches_a_wrapped_import(tmp_path):
    offender = _write(
        tmp_path,
        "from app.services import (\n    memory_community_reports,\n)\n",
    )
    assert _report_module_offenders([offender], tmp_path)


def test_the_scan_catches_an_adjacent_string_literal_split(tmp_path):
    """The decorative-guard defect T2.67's re-review found: the prefilter
    this scan carried before folding onto the shared walker checked whether
    `REPORTS_BASENAME` appeared in the raw *source text*, before any
    parsing happened. Splitting the basename across two adjacent string
    literals — which Python's parser folds into one constant at parse time,
    long before this scan would ever see it — made the unsplit basename
    never appear in the raw text, so the prefilter skipped the file outright
    and the AST walk underneath it, which really could have caught this,
    never ran at all."""
    offender = _write(
        tmp_path,
        "from importlib import import_module\n"
        "import_module('app.services.memory_community' '_reports')\n",
    )
    assert _report_module_offenders([offender], tmp_path)


def test_the_scan_catches_a_relative_loader_call_with_package(tmp_path):
    """The Important finding a re-review raised: the old (pre-fold-in)
    substring-based scan caught `import_module(".memory_community_reports",
    package="app.services")`, and folding onto the shared walker's
    exact-match `forbidden_literals` silently dropped it — the one
    genuinely executable shape among the three the fold-in traded away.
    Restored in the shared walker (`_resolve_relative_loader_call`), so all
    three scans, including this one, catch it again."""
    offender = _write(
        tmp_path,
        "from importlib import import_module\n"
        'import_module(".memory_community_reports", package="app.services")\n',
    )
    offenders = _report_module_offenders([offender], tmp_path)
    assert offenders
    assert any("loader-call" in o for o in offenders), offenders


def test_the_scan_does_not_fail_on_prose(tmp_path):
    innocent = tmp_path / "app" / "repositories" / "memory_communities.py"
    innocent.parent.mkdir(parents=True)
    innocent.write_text(
        '"""No file under `app/` may import '
        'app.services.memory_community_reports."""\n'
    )
    assert _report_module_offenders([innocent], tmp_path) == []


def test_the_scan_does_not_fail_on_the_detector_module_name(tmp_path):
    """`memory_community_detection` is not `memory_community_reports`; a
    sloppier substring would forbid T2.18's own module."""
    innocent = _write(
        tmp_path,
        "from app.services import memory_community_detection\n",
    )
    assert _report_module_offenders([innocent], tmp_path) == []


def test_the_scan_allows_the_pure_report_status_projection(tmp_path):
    """T2.20's amendment: `report_status` and its four constants are a pure
    read-time projection of stored columns, named by this module's own
    docstring as T2.20's browsing surface's intended import — not the
    LLM-calling capability invariant 15 exists to contain."""
    innocent = _write(
        tmp_path,
        "from app.services.memory_community_reports import (\n"
        "    REPORT_STATUS_READY,\n"
        "    report_status,\n"
        ")\n",
    )
    assert _report_module_offenders([innocent], tmp_path) == []


def test_the_scan_still_catches_generate_reports_by_precise_name(tmp_path):
    offender = _write(
        tmp_path,
        "from app.services.memory_community_reports import generate_report\n",
    )
    assert _report_module_offenders([offender], tmp_path)


def test_the_scan_still_catches_a_mixed_import_with_one_unsafe_name(tmp_path):
    """One unsafe symbol in the same import statement voids the exemption —
    the allowlist is all-or-nothing per statement, not per-name filtering."""
    offender = _write(
        tmp_path,
        "from app.services.memory_community_reports import (\n"
        "    report_status,\n"
        "    generate_reports,\n"
        ")\n",
    )
    assert _report_module_offenders([offender], tmp_path)


def test_the_scan_still_catches_the_whole_module_import(tmp_path):
    """`import app.services.memory_community_reports` reaches everything in
    the module through attribute access, so it is never exempt regardless of
    which attributes are actually used."""
    offender = _write(
        tmp_path,
        "import app.services.memory_community_reports\n",
    )
    assert _report_module_offenders([offender], tmp_path)
