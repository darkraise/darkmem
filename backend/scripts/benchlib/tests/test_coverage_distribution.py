"""T3.24 — the coverage-distribution runner's behaviour.

The pure-function half runs without a database. The two tests that prove
the *production read* claims — that the connection is read-only and that
the live predicate is the index's — opt into the bench database, because a
mocked connection would prove the branch and not the property.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from benchlib import coverage_distribution as cd
from benchlib import run_coverage_distribution as rcd

READ_AT = datetime(2026, 8, 12, tzinfo=timezone.utc)


def _rows(*coverages, ids=None):
    ids = ids or [f"a-{i}" for i in range(len(coverages))]
    return [
        {"id": i, "project": "default", "subject_key": f"s::{i}", "coverage": c}
        for i, c in zip(ids, coverages)
    ]


def _summarise(*coverages, **kwargs):
    return cd.summarise(
        _rows(*coverages), snapshot="t", database_identity="darkmem_bench",
        read_at=READ_AT, **kwargs,
    )


# ── the distribution itself ──────────────────────────────────────────────


def test_percentiles_are_observations_never_interpolations():
    """Nearest-rank, so every reported percentile is a coverage some article
    actually has. An interpolated p90 over a handful of articles is a number
    between two real ones, and G-E asks how many *articles* clear the bar."""
    values = [0.10, 0.50, 0.90, 1.00]
    for p in (0, 10, 25, 50, 75, 90, 100):
        assert cd.percentile(values, p) in values
    assert cd.percentile(values, 0) == 0.10
    assert cd.percentile(values, 100) == 1.00
    assert cd.percentile([0.42], 50) == 0.42


def test_a_mean_would_hide_what_the_distribution_shows():
    """The reason G-E is specified as a distribution. These two corpora have
    the same mean coverage and opposite verdicts: one has every article at
    the bar, the other has half its corpus ungrounded."""
    uniform = _summarise(*[0.95] * 10)
    split = _summarise(*([1.00] * 5 + [0.90] * 5))

    assert uniform.corpus_share == 1.0
    assert split.corpus_share == 0.5
    assert uniform.percentiles[0] == 0.95
    assert split.percentiles[0] == 0.90


def test_a_coverage_exactly_at_the_threshold_counts_as_at_or_above():
    """'At or above', not 'above'. 0.95 is a passing article -- the runtime
    routes on the same comparison, and a probe stricter than the bar it
    measures would report a corpus worse than the one that shipped."""
    report = _summarise(0.95, 0.9499, 0.9501)
    assert report.at_or_above_threshold == 2


# ── unmeasured is not zero (T3.03's ruling, inherited) ───────────────────


def test_unmeasured_articles_are_excluded_never_counted_as_zero():
    """**The module's spine.** A refusing judge, an outage and an invalid
    verdict all produce NULL, and none is evidence an article is
    ungrounded. Folding them in as zeros would manufacture a low coverage
    number out of a judge that never ran."""
    report = _summarise(1.0, 1.0, None, None, None)

    assert report.live_articles == 5
    assert report.measured_articles == 2
    assert report.unmeasured_articles == 3
    # The share is over the measured population, not the live one: 2/2, not 2/5.
    assert report.corpus_share == 1.0
    assert report.percentiles[0] == 1.0
    assert any("never counted as zero" in note for note in report.notes)


def test_an_all_unmeasured_corpus_is_not_evaluable_rather_than_zero():
    """Today's standing state on every install: G-D is open, the judge
    refuses unconditionally, so no article carries a number. That must read
    as 'not evaluable', which is what T2.40 recorded for G-C rather than
    inventing a verdict."""
    report = _summarise(None, None, None)

    assert report.measured_articles == 0
    assert report.corpus_share is None
    assert report.under_powered is True
    assert report.percentiles == {}
    assert any("not evaluable" in note for note in report.notes)
    assert "0.0" not in cd.render_report(report).split("## Distribution")[1][:80]


def test_a_thin_measured_population_is_under_powered_not_a_percentage():
    assert _summarise(*[1.0] * (cd.UNDER_POWERED_THRESHOLD - 1)).under_powered is True
    assert _summarise(*[1.0] * cd.UNDER_POWERED_THRESHOLD).under_powered is False
    # The share is still computed and reported -- under-powered qualifies a
    # number, it does not withhold it.
    assert _summarise(1.0, 1.0).corpus_share == 1.0


# ── the named snapshot (done-when 3) ─────────────────────────────────────


def test_the_population_hash_covers_unmeasured_articles_too():
    """A run whose measured set is identical but which saw ten more
    unmeasured articles read a different corpus, and the share it reports
    means something different. The hash has to say so."""
    two = cd.summarise(_rows(1.0, None, ids=["a", "b"]), snapshot="t",
                       database_identity="d", read_at=READ_AT)
    three = cd.summarise(_rows(1.0, None, None, ids=["a", "b", "c"]), snapshot="t",
                         database_identity="d", read_at=READ_AT)

    assert two.corpus_share == three.corpus_share == 1.0
    assert two.population_sha256 != three.population_sha256


def test_the_population_hash_is_order_independent_but_content_sensitive():
    a = cd.summarise(_rows(0.9, 1.0, ids=["x", "y"]), snapshot="t",
                     database_identity="d", read_at=READ_AT)
    reordered = cd.summarise(list(reversed(_rows(0.9, 1.0, ids=["x", "y"]))),
                             snapshot="t", database_identity="d", read_at=READ_AT)
    moved = cd.summarise(_rows(0.9, 0.99, ids=["x", "y"]), snapshot="t",
                         database_identity="d", read_at=READ_AT)

    assert a.population_sha256 == reordered.population_sha256
    assert a.population_sha256 != moved.population_sha256


def test_no_schema_is_reported_distinctly_from_an_empty_corpus():
    """Both are zero measured articles; only one means 'never deployed'."""
    missing = cd.no_schema_report(
        snapshot="t", database_identity="d", read_at=READ_AT)
    empty = cd.summarise([], snapshot="t", database_identity="d", read_at=READ_AT)

    assert missing.schema_present is False
    assert empty.schema_present is True
    assert missing.measured_articles == empty.measured_articles == 0
    assert "never been migrated" in " ".join(missing.notes)


# ── plumbing, not judgment (runbook §2) ──────────────────────────────────


def test_the_report_states_the_bars_but_renders_no_verdict():
    text = cd.render_report(_summarise(*[1.0] * 10))
    assert "0.95" in text and "0.9" in text          # both bars reported
    assert "No verdict is rendered here" in text
    for word in ("CLEARED", "NOT CLEARED", "PASS", "FAIL"):
        assert word not in text


def test_the_ledger_row_carries_the_population_hash_and_the_bars():
    row = cd.to_ledger_row(_summarise(1.0, 0.5, None))
    assert row["kind"] == "coverage_distribution"
    assert row["population_sha256"]
    assert row["threshold"] == 0.95
    assert row["corpus_share_bar"] == 0.90
    assert row["unmeasured_articles"] == 1


# ── the production read (doc 20 §4's sanctioned exception) ───────────────


class TestTargetGuard:
    @pytest.mark.parametrize("name", ["darkmem_test", "darkmem_test_7"])
    def test_refuses_pytest_owned_databases(self, name):
        with pytest.raises(RuntimeError, match="three-databases rule"):
            rcd._assert_not_forbidden(
                f"postgresql+asyncpg://u:p@localhost:5433/{name}")

    def test_refuses_a_forbidden_name_hidden_in_a_query_param(self):
        """`?database=` overrides the path for asyncpg, so a path-only
        reading approves a URL that lands somewhere else."""
        with pytest.raises(RuntimeError, match="three-databases rule"):
            rcd._assert_not_forbidden(
                "postgresql+asyncpg://u:p@localhost:5433/darkmem"
                "?database=darkmem_test")

    def test_allows_the_real_and_bench_databases(self):
        for name in ("darkmem", "darkmem_bench"):
            rcd._assert_not_forbidden(
                f"postgresql+asyncpg://u:p@localhost:5433/{name}")


pytestmark_db = pytest.mark.usefixtures("_bench_db")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_bench_db")
async def test_the_connection_actually_refuses_a_write():
    """Done-when 2: proves the mechanism, **not** this runner's binding to it.

    `default_transaction_read_only=on` makes Postgres refuse an accidental
    write in the database rather than in review, and that is what is proved
    here. What is *not* proved is that `run_coverage_distribution.run`
    actually sends the setting: the engine below is built from a copy
    written in this test, so stripping the `connect_args` from `run` leaves
    this green.

    The docstring said "this test fails if someone drops the connect_args"
    until 2026-08-16, which is false and was found by TH1.17's re-review
    while probing the test that copied this one. The binding-proving shape
    is in `test_run_faithfulness_gate.py::test_fetch_bar_rows_actually_refuses_a_write`:
    capture the kwargs off `create_async_engine` and probe with exactly
    those. Applying it here needs a way to drive `run` cheaply, so it is
    recorded rather than done.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from benchlib import bench_db

    engine = create_async_engine(
        bench_db.BENCH_DATABASE_URL,
        connect_args={"server_settings": {"default_transaction_read_only": "on"}},
    )
    try:
        async with async_sessionmaker(engine)() as session:
            # Reads are fine.
            await session.execute(text("SELECT count(*) FROM knowledge_articles"))
            with pytest.raises(DBAPIError) as caught:
                await session.execute(
                    text("INSERT INTO knowledge_articles "
                         "(id, subject_key, project, content) "
                         "VALUES (gen_random_uuid(), 'x::concept', 'p', 'c')")
                )
    finally:
        await engine.dispose()
    assert "read-only" in str(caught.value).lower()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_bench_db")
async def test_superseded_articles_are_not_part_of_the_live_corpus():
    """The live predicate is `ux_knowledge_articles_live`'s own, not a
    restatement. A superseded article is a previous version a re-synthesis
    retired; counting it would measure history."""
    from sqlalchemy import text

    from benchlib import bench_db

    async with bench_db.session_factory() as session:
        await session.execute(text("DELETE FROM knowledge_articles"))
        for subject, status, coverage in (
            ("live-a", "candidate", 1.0),
            ("live-b", "candidate", 0.5),
            ("old-a", "superseded", 0.0),
        ):
            await session.execute(
                text("INSERT INTO knowledge_articles "
                     "(id, subject_key, project, content, status, confidence) "
                     "VALUES (:id, :k, 'p', 'c', :s, :c)"),
                {"id": str(uuid.uuid4()), "k": f"{subject}::concept",
                 "s": status, "c": coverage},
            )
        await session.commit()

        report = await cd.compute_coverage_distribution(
            session, snapshot="t", database_identity="darkmem_bench",
            read_at=READ_AT,
        )

        assert report.live_articles == 2
        assert report.measured_articles == 2
        # The superseded 0.0 would have halved the share and dragged p0 to
        # the floor had the predicate been wrong.
        assert report.percentiles[0] == 0.5
        assert report.corpus_share == 0.5

        await session.execute(text("DELETE FROM knowledge_articles"))
        await session.commit()
