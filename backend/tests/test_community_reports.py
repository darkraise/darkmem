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
    assert snapshot == {"alpha": "the original report"}

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
REPORTS_PATH = "app/services/memory_community_reports.py"


def _docstring_constants(tree: ast.AST) -> set[int]:
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _report_module_offenders(paths, backend_root) -> list[str]:
    """Every route from a file under `app/` to the report-generation module.

    Parsed, not grepped, for the same reason T2.18's detector scan is parsed:
    a line-based scan misses a wrapped `from app.services import (\n
    memory_community_reports,\n)` and a dotted path split across adjacent
    string literals.
    """
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(backend_root))
        if rel == REPORTS_PATH:
            continue
        source = path.read_text()
        if REPORTS_BASENAME not in source:
            continue
        tree = ast.parse(source, filename=rel)
        docstrings = _docstring_constants(tree)
        for node in ast.walk(tree):
            reached = ""
            if isinstance(node, ast.Import):
                reached = " ".join(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                reached = " ".join(
                    f"{node.module or ''}.{alias.name}" for alias in node.names
                )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                reached = node.value
            if REPORTS_BASENAME in reached:
                offenders.append(f"{rel}:{node.lineno}: {reached.strip()}")
    return offenders


def test_no_app_code_reaches_report_generation():
    """Report generation is Tier C: nothing on a capture or retrieval path
    may reach it. This is the structural proof for 'never blocks a read' —
    a call counter cannot show a negative, an AST reachability scan can."""
    paths = [
        p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)
    ]
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scan would pass "
        "vacuously; check BACKEND / the glob path"
    )
    assert not _report_module_offenders(paths, BACKEND)


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
