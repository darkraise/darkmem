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
