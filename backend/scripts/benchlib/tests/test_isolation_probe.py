"""Integration coverage of the isolation probe itself (T1.35).

These tests pin the measuring instrument, never the measurement: the gate
number belongs in the gate ledger, and a fix that drives it to zero must not
break this suite. What is pinned instead:

- every surface in the content-surfaces registry is driven (both directions),
- the probe is deterministic across runs,
- a single removed predicate turns into named V1 rows — the probe's
  sensitivity, proven by injecting the leak rather than trusting the design.
"""
import pytest
import pytest_asyncio
from sqlalchemy import text

from benchlib import isolation_probe
from benchlib.isolation_probe import DRIVERS, run_probe
from benchlib.isolation_rules import Verdict

pytestmark = pytest.mark.asyncio


def _registry_keys() -> list[str]:
    from app.services.content_surfaces import CONTENT_SURFACES

    return [s.key for s in CONTENT_SURFACES]


@pytest_asyncio.fixture(scope="module")
async def baseline_report():
    return await run_probe()


async def test_driver_table_matches_the_registry():
    assert set(DRIVERS) == set(_registry_keys())


async def test_every_registry_surface_is_driven(baseline_report):
    assert baseline_report.surfaces_driven == _registry_keys() + ["content_free_routes"]


async def test_every_memory_content_surface_produced_sightings(baseline_report):
    """A driver that silently observed nothing is a hole in a zero-count."""
    observed = {c.sighting.surface for c in baseline_report.classified}
    assert set(_registry_keys()) <= observed


async def test_probe_makes_zero_model_calls(baseline_report):
    stub = isolation_probe.StubOrchestrator()
    assert not hasattr(stub, "_client"), "stub grew an HTTP client"


async def test_probe_is_deterministic(baseline_report):
    second = await run_probe()
    assert second.render() == baseline_report.render()


async def test_no_unaccounted_sentinel_in_the_baseline(baseline_report):
    """Every sentinel the drivers saw was matched to an enumerated row: the
    raw-body net is armed but silent on the unmutated tree. If this fails, a
    response field crossed that no driver models — extend the driver, never
    the exemptions."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.forced_v1_reason == "sentinel outside every enumerated row"
    ]
    assert forced == []


async def test_no_article_content_crosses_past_its_declared_preview(baseline_report):
    """`review_queue_articles` declares it crosses `content_preview`, not
    `content`, and every article fixture runs past the LEFT(content, 200)
    boundary — so a tail marker on the wire means the surface widened beyond
    what `content_surfaces` declares.

    The raw-body net above cannot catch this: the sentinel deliberately sits
    inside the first 200 characters, because the preview is a declared
    crossing and must cross, so `scan_sentinels` sees the same thing whether
    the content was truncated or not. Without this assertion the over-length
    fixture is decorative — it seeds the boundary and nothing reads it."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.forced_v1_reason
        == "article content crossed past its declared preview"
    ]
    assert forced == []


async def test_no_memory_content_crosses_past_its_declared_preview(baseline_report):
    """The same assertion one surface up, over memories instead of articles.

    ``hygiene_queue_memories`` declares it crosses ``content_preview``, and
    every fixture its three arms return runs past the ``[:200]`` boundary with
    a distinct tail. The raw-body net cannot see this — the sentinel leads the
    content, so it crosses identically whether or not the preview truncated —
    which is precisely why the marker exists."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert forced == []


async def test_every_hygiene_row_served_can_be_seen_past_the_boundary(baseline_report):
    """The preview check is only as wide as the fixtures it can see.

    ``_preview_boundary`` can only fail on a fixture whose content runs past
    200 characters, so a future fixture that lands in one of the three arms
    while shorter than the boundary would be served with no truncation
    coverage at all — silently, and with the surface still reporting zero.
    Derived from the rows the arms actually returned rather than from the
    fixture table's own comment, so it fails when the two drift."""
    from benchlib.isolation_probe import _all_content_fixtures

    fixtures = _all_content_fixtures()
    served = {
        c.sighting.row for c in baseline_report.classified
        if c.sighting.surface == "hygiene_queue_memories"
    }
    assert served, "the hygiene memory arms returned nothing"
    for key in sorted(served):
        fixture = fixtures[key]
        assert fixture.long and len(fixture.content) > 200, (
            f"{key} is served by a surface declaring content_preview but does "
            "not run past the 200-character boundary, so a widened preview "
            "would cross undetected"
        )


async def test_the_duplicates_arm_observed_every_seeded_pair(baseline_report):
    """Both cases of the duplicates arm reached it, and both pairs crossed.

    The arm's happy path emits no violation by design — the ids are I1 — so
    without this a case that returned nothing at all (an empty page, a changed
    membership predicate, a 200 with no items) would look exactly like a clean
    one."""
    sightings = [
        c.sighting for c in baseline_report.classified
        if c.sighting.surface == "hygiene_queue_duplicates"
    ]
    assert {"a_active", "a_twin", "b_active", "b_succ"} <= {s.row for s in sightings}
    filtered = [s for s in sightings if "project filter" in s.case]
    assert filtered, "the filtered case of the duplicates arm observed nothing"


async def test_a_dropped_project_predicate_on_a_hygiene_arm_fails_the_probe(
    baseline_report, monkeypatch,
):
    """A caller-applied project filter that stops riding the SQL is a V1.

    The hygiene arms are operator-wide by ratification, so their teeth are not
    in the default read — they are in the filtered one: a caller who names a
    project and is served another project's rows has been lied to, however
    well those rows are labelled."""
    from app.services import hygiene_queue

    original = hygiene_queue.build_superseded_query
    monkeypatch.setattr(
        hygiene_queue, "build_superseded_query", lambda project: original(None),
    )
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.verdict is Verdict.V1
        and c.sighting.surface == "hygiene_queue_memories"
        and any("outside requested" in reason for reason in c.reasons)
    ]
    assert breaches, "no named project-breach row despite the removed predicate"


async def test_a_forged_project_label_on_the_duplicates_arm_fails_the_probe(
    baseline_report, monkeypatch,
):
    """The scope check must not ask the surface under test to declare its scope.

    Drop the filter *and* stamp every row's label from the request parameter —
    one serializer bug, and the shape a check comparing the row's own
    ``project`` to the request cannot see: every pair looks in-scope while
    foreign-project memory ids cross. The comparison is against the projects
    ``DUPLICATE_PAIRS`` seeded, so it survives a lying label."""
    from app.services import hygiene_queue

    original = hygiene_queue.list_duplicates

    async def leaky(session, *, project=None, limit=50, offset=0):
        items, total = await original(session, project=None, limit=limit, offset=offset)
        if project is not None:
            items = [{**item, "project": project} for item in items]
        return items, total

    monkeypatch.setattr(hygiene_queue, "list_duplicates", leaky)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.sighting.surface == "hygiene_queue_duplicates"
        and c.sighting.forced_v1_reason == "pair outside the requested project"
    ]
    assert breaches, "a forged label hid a foreign pair from the scope check"


async def test_an_unlabelled_fact_fails_the_probe(baseline_report, monkeypatch):
    """Both fact surfaces are wide on the project axis — one by ratification,
    one because the caller named the row — so the label is the whole defence.
    Blank it and the foreign-project fact must land as a named V2."""
    from app.services import facts_read

    original = facts_read._base_item

    def unlabelled(row, badge):
        item = original(row, badge)
        item["project"] = ""
        return item

    monkeypatch.setattr(facts_read, "_base_item", unlabelled)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    escapes = [
        c for c in mutated.violations()
        if c.verdict is Verdict.V2
        and c.sighting.surface in {"knowledge_facts_browsing", "knowledge_fact_detail"}
    ]
    assert escapes, "no unlabelled cross-project fact despite the blanked label"


async def test_a_removed_status_predicate_fails_the_probe(baseline_report, monkeypatch):
    """The gate's teeth: strip the status clause out of MemoryFilter's SQL
    rendering (the exact shape of a real regression) and the probe must
    produce new, named V1 rows. Verified by mutation here so 'a single
    leaked row fails the probe loudly' is a measured property, not a claim."""
    from app.repositories.vector import MemoryFilter

    def leaky_where_sql(self, alias: str) -> str:
        clauses = []
        if not self.include_archived:
            clauses.append(f"{alias}.is_archived = FALSE")
        if self.project is not None:
            clauses.append(f"{alias}.project = CAST(:flt_project AS text)")
        return " AND ".join(clauses) if clauses else "TRUE"

    monkeypatch.setattr(MemoryFilter, "where_sql", leaky_where_sql)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    status_breaches = [
        c for c in mutated.violations()
        if c.verdict is Verdict.V1
        and any("status" in reason and "outside requested" in reason for reason in c.reasons)
    ]
    assert status_breaches, "no named status-breach row despite the removed predicate"


async def test_a_registry_surface_without_a_driver_aborts_the_run(monkeypatch):
    """The completeness inheritance: a surface added to the registry without
    a probe driver must stop the gate number from being produced at all,
    never narrow it silently (Ruling 1's failure shape)."""
    from app.services.content_surfaces import CONTENT_SURFACES, ContentSurface, Scoping, SurfaceKind

    phantom = ContentSurface(
        key="phantom_surface", kind=SurfaceKind.MEMORY_CONTENT_SURFACE,
        front_doors=("GET /api/v1/phantom",), crosses=("content",),
        scoping=Scoping.SCOPED, labels=("project", "status"),
        decided_by="test", reason="a surface the probe has no driver for" + " " * 10,
    )
    monkeypatch.setattr(
        isolation_probe, "_registry_surfaces", lambda: CONTENT_SURFACES + (phantom,),
    )
    with pytest.raises(RuntimeError, match="phantom_surface"):
        await run_probe()


# ── T2.74: three surfaces that declared content_preview but nothing checked it ──
#
# reembed_backfill_queue, pipeline_failure_triage and capture_buffer_triage
# each truncate at their own length (120, 80 and 500 characters
# respectively — see reembed.py, pipeline_failures.py and buffer_monitor.py),
# and none of their drivers called `_preview_boundary` before this task. Each
# surface below gets the same three-part proof `hygiene_queue_memories`
# already had: the check is clean under correct code, the fixtures it relies
# on demonstrably exceed *this* surface's own boundary (not assumed from
# another surface, per Ruling 2), and widening the surface's own query fails
# the probe. Reusing one fixture set and one boundary blindly is exactly what
# false-positived on capture_buffer_triage during review (Ruling 1): its
# 500-char boundary sits past every existing ~275-char long fixture, so it
# needed its own, longer ones (`BUFFER_LONG_FIXTURES`).


async def test_a_fixture_under_its_surfaces_boundary_fails_the_build():
    """The fourth Done-when box: the guarantee must not rest on a fixture
    comment, because a comment can drift out of step with the fixture table
    silently. `_preview_boundary` asserts every fixture it is handed is
    actually longer than the boundary it is meant to prove crosses, so a
    future fixture edit that shrinks one under its surface's boundary fails
    loudly here instead of reporting a clean zero that means nothing."""
    from benchlib.isolation_probe import OBSERVER, MemoryFixture, _preview_boundary

    short = MemoryFixture("too_short_for_its_boundary", OBSERVER, long=True, pad_to=10)
    with pytest.raises(AssertionError, match="too_short_for_its_boundary"):
        _preview_boundary(
            "any_surface", "GET /any", "case", short.content, [short], 200,
        )


async def test_no_reembed_content_crosses_past_its_declared_preview(baseline_report):
    """reembed_backfill_queue truncates at LEFT(m.content, 120)
    (reembed.py's `list_obsolete_memories`). Scoped to this surface because
    `forced_v1_reason` is the same string every `_preview_boundary` caller
    uses — the surface filter is what tells the three apart."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.surface == "reembed_backfill_queue"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert forced == []


async def test_a_reembed_row_served_can_be_seen_past_its_declared_boundary(baseline_report):
    """reembed_backfill_queue serves whichever fixtures lack an active-partition
    embedding (`a_oldfp`, `a_super_nofp`, `b_nofp`) — unlike the three hygiene
    arms, not every one of those is a `long` fixture, so the check here is
    that at least one served row demonstrably runs past the surface's own
    120-char boundary, not that every served row does."""
    from benchlib.isolation_probe import REEMBED_PREVIEW_CHARS, _all_content_fixtures

    fixtures = _all_content_fixtures()
    served = {
        c.sighting.row for c in baseline_report.classified
        if c.sighting.surface == "reembed_backfill_queue"
    }
    assert served, "the reembed backfill queue returned nothing"
    long_served = {key for key in served if fixtures.get(key) and fixtures[key].long}
    assert long_served, (
        "no long fixture reached reembed_backfill_queue -- the preview "
        "boundary check has nothing to prove against"
    )
    for key in sorted(long_served):
        fixture = fixtures[key]
        assert len(fixture.content) > REEMBED_PREVIEW_CHARS, (
            f"{key} is served by a surface declaring content_preview but does "
            f"not run past the {REEMBED_PREVIEW_CHARS}-character boundary, so "
            "a widened preview would cross undetected"
        )


async def test_widening_the_reembed_preview_slice_fails_the_probe(
    baseline_report, monkeypatch,
):
    """Widen reembed_backfill_queue's own query past its declared 120-char
    boundary and the probe must report the crossing rather than staying
    clean -- the drill R2 asks for, over this surface's own code."""
    from app.services import reembed
    from app.services.embedder_registry import child_table
    from app.utils.scope_labels import SCOPE_LABEL_COLUMNS, scope_labels
    from sqlalchemy import text as sa_text

    async def widened(self, fingerprint, limit=100, offset=0):
        mem_table = child_table("memory_embeddings", fingerprint)
        mem_anti = await self._anti_join(
            mem_table,
            f"NOT EXISTS (SELECT 1 FROM {mem_table} me WHERE me.memory_id = m.id)",
        )
        total = int((await self.session.execute(
            sa_text(f"SELECT COUNT(*) FROM memories m{reembed._where(mem_anti)}"),
        )).scalar_one())
        if mem_anti is None:
            return [], total, True
        rows = (await self.session.execute(
            sa_text(f"""
                SELECT m.id AS memory_id, LEFT(m.content, 5000) AS content_preview,
                       {SCOPE_LABEL_COLUMNS}
                FROM memories m
                WHERE {mem_anti}
                ORDER BY m.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        )).mappings().all()
        items = [
            {
                "memory_id": str(r["memory_id"]),
                "content_preview": r["content_preview"],
                **scope_labels(r),
            }
            for r in rows
        ]
        return items, total, False

    monkeypatch.setattr(reembed.ReembedService, "list_obsolete_memories", widened)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.sighting.surface == "reembed_backfill_queue"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert breaches, "no boundary violation despite the widened preview slice"


async def test_no_pipeline_failure_content_crosses_past_its_declared_preview(
    baseline_report,
):
    """pipeline_failure_triage truncates at LEFT(m.content, 80)
    (pipeline_failures.py's `list_unresolved`, wire field `entity_preview`).
    `_preview_boundary` scans the raw response body for the tail marker
    regardless of field name, so the substring check still applies."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.surface == "pipeline_failure_triage"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert forced == []


async def test_every_pipeline_failure_row_served_can_be_seen_past_its_declared_boundary(
    baseline_report,
):
    """Unlike reembed_backfill_queue, every row pipeline_failure_triage
    serves (`a_active`, `a_super`, `b_active`) is a `long` fixture -- the
    three keys the probe deliberately records failures against -- so this
    mirrors hygiene_queue_memories' own 'every served row' shape, just
    against this surface's 80-char boundary instead of assuming 200."""
    from benchlib.isolation_probe import (
        PIPELINE_FAILURE_PREVIEW_CHARS,
        _all_content_fixtures,
    )

    fixtures = _all_content_fixtures()
    served = {
        c.sighting.row for c in baseline_report.classified
        if c.sighting.surface == "pipeline_failure_triage"
    }
    assert served, "the pipeline failure triage queue returned nothing"
    for key in sorted(served):
        fixture = fixtures[key]
        assert fixture.long and len(fixture.content) > PIPELINE_FAILURE_PREVIEW_CHARS, (
            f"{key} is served by a surface declaring content_preview but does "
            f"not run past the {PIPELINE_FAILURE_PREVIEW_CHARS}-character "
            "boundary, so a widened preview would cross undetected"
        )


async def test_widening_the_pipeline_failure_preview_slice_fails_the_probe(
    baseline_report, monkeypatch,
):
    """Widen pipeline_failure_triage's own query past its declared 80-char
    boundary and the probe must report the crossing."""
    from app.services import pipeline_failures
    from sqlalchemy import text as sa_text

    async def widened(self, entity_type=None, pipeline_name=None, limit=100, offset=0):
        where_parts = ["pf.resolved_at IS NULL"]
        params: dict = {"limit": limit, "offset": offset}
        if entity_type:
            where_parts.append("pf.entity_type = :entity_type")
            params["entity_type"] = entity_type
        if pipeline_name:
            where_parts.append("pf.pipeline_name = :pipeline_name")
            params["pipeline_name"] = pipeline_name
        where_sql = " AND ".join(where_parts)

        items_sql = f"""
            SELECT
                pf.id, pf.entity_type, pf.entity_id, pf.pipeline_name,
                pf.failed_step, pf.error_message, pf.attempts,
                pf.first_failed_at, pf.last_attempt_at, pf.resolved_at,
                pf.metadata,
                CASE
                    WHEN pf.entity_type = 'memory' THEN LEFT(m.content, 5000)
                    WHEN pf.entity_type = 'code_repo' THEN r.name
                    ELSE NULL
                END AS entity_preview,
                m.project AS entity_project,
                m.status AS entity_status
            FROM pipeline_failures pf
            LEFT JOIN memories m ON pf.entity_type = 'memory' AND m.id = pf.entity_id
            LEFT JOIN repositories r ON pf.entity_type = 'code_repo' AND r.id = pf.entity_id
            WHERE {where_sql}
            ORDER BY pf.last_attempt_at DESC
            LIMIT :limit OFFSET :offset
        """
        result = await self.session.execute(sa_text(items_sql), params)
        items = []
        for row in result.mappings().all():
            items.append({
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "entity_id": str(row["entity_id"]),
                "pipeline_name": row["pipeline_name"],
                "failed_step": row["failed_step"],
                "error_message": row["error_message"],
                "attempts": row["attempts"],
                "first_failed_at": row["first_failed_at"],
                "last_attempt_at": row["last_attempt_at"],
                "resolved_at": row["resolved_at"],
                "metadata": row["metadata"] or {},
                "entity_preview": row["entity_preview"],
                "entity_project": row["entity_project"],
                "entity_status": row["entity_status"],
            })
        count_sql = f"SELECT COUNT(*) FROM pipeline_failures pf WHERE {where_sql}"
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = (await self.session.execute(sa_text(count_sql), count_params)).scalar_one()
        return items, int(total)

    monkeypatch.setattr(pipeline_failures.PipelineFailureService, "list_unresolved", widened)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.sighting.surface == "pipeline_failure_triage"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert breaches, "no boundary violation despite the widened preview slice"


async def test_no_buffer_content_crosses_past_its_declared_preview(baseline_report):
    """capture_buffer_triage truncates at LEFT(content, 500)
    (buffer_monitor.py's `CONTENT_PREVIEW_CHARS`)."""
    forced = [
        c for c in baseline_report.classified
        if c.sighting.surface == "capture_buffer_triage"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert forced == []


async def test_the_long_buffer_fixtures_are_served_past_their_declared_boundary(
    baseline_report,
):
    """The false-positive Ruling 1 measured directly: buf_alpha/buf_beta's
    plain "... buffered capture" bodies are far short of 500 characters, so
    capture_buffer_triage needed its own longer fixtures
    (`BUFFER_LONG_FIXTURES`) rather than reusing hygiene_queue_memories' or
    reembed_backfill_queue's ~275-char ones. Checked against the actually
    served rows rather than assumed, same as the other two surfaces above."""
    from benchlib.isolation_probe import (
        BUFFER_LONG_FIXTURES,
        CAPTURE_BUFFER_PREVIEW_CHARS,
    )

    by_key = {fx.key: fx for fx in BUFFER_LONG_FIXTURES}
    served = {
        c.sighting.row for c in baseline_report.classified
        if c.sighting.surface == "capture_buffer_triage"
    }
    long_served = served & set(by_key)
    assert long_served, "neither long buffer fixture reached capture_buffer_triage"
    for key in sorted(long_served):
        fixture = by_key[key]
        assert len(fixture.content) > CAPTURE_BUFFER_PREVIEW_CHARS, (
            f"{key} is served by a surface declaring content_preview but does "
            f"not run past the {CAPTURE_BUFFER_PREVIEW_CHARS}-character "
            "boundary, so a widened preview would cross undetected"
        )


async def test_widening_the_capture_buffer_preview_slice_fails_the_probe(
    baseline_report, monkeypatch,
):
    """Widen capture_buffer_triage's own CONTENT_PREVIEW_CHARS past its
    declared 500-char boundary and the probe must report the crossing.
    `_ROW_COLUMNS` is a module-level string built once at import from the
    constant, so the constant alone can't be monkeypatched after the fact --
    the built SQL fragment has to be replaced directly."""
    from app.services import buffer_monitor

    widened_columns = buffer_monitor._ROW_COLUMNS.replace(
        f"LEFT(content, {buffer_monitor.CONTENT_PREVIEW_CHARS})",
        "LEFT(content, 5000)",
    )
    assert widened_columns != buffer_monitor._ROW_COLUMNS, (
        "the replacement did not match _ROW_COLUMNS -- CONTENT_PREVIEW_CHARS "
        "or its literal rendering changed shape"
    )
    monkeypatch.setattr(buffer_monitor, "_ROW_COLUMNS", widened_columns)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.sighting.surface == "capture_buffer_triage"
        and c.sighting.forced_v1_reason
        == "memory content crossed past its declared preview"
    ]
    assert breaches, "no boundary violation despite the widened preview slice"


async def test_a_dropped_project_predicate_on_related_memories_fails_the_probe(
    baseline_report, monkeypatch,
):
    """The related-memories read is scoped in SQL, and this is what proves it.

    The seeded OBSERVER document's block and the FOREIGN `b_active` carry the
    same vector under the same fingerprint, so their cosine is exactly 1.0 and
    only the project predicate keeps that row out of the page. That makes a
    predicate-free variant the exact mutation worth pinning.

    The predicate now lives inside `_related_sql`, a builder rather than a
    module-level constant, so the mutation targets the builder. And the fixture
    seeds real vectors on both sides deliberately: with nothing embedded the
    mutated surface would return nothing either, and the test would pass while
    proving that a leak is undetectable. Verified by running it against the
    mutated module before it was kept.
    """
    from app.services import document_related

    original = document_related._related_sql

    def predicate_free(memories_table: str, blocks_table: str) -> str:
        # CAST, because a bare bind in this position has no inferable type and
        # asyncpg refuses it (the cross-cutting invariant).
        return original(memories_table, blocks_table).replace(
            "WHERE m.project = :project", "WHERE CAST(:project AS text) IS NOT NULL"
        )

    monkeypatch.setattr(document_related, "_related_sql", predicate_free)
    mutated = await run_probe()

    assert mutated.count() > baseline_report.count()
    breaches = [
        c for c in mutated.violations()
        if c.verdict is Verdict.V1
        and c.sighting.surface == "document_related_memories"
        and any("outside requested" in reason for reason in c.reasons)
    ]
    assert breaches, "no named project-breach row despite the removed predicate"
