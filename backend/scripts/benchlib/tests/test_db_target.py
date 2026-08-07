"""The one rule for which database a harness URL actually reaches.

This exists because the rule had five separate readings, four of which were
wrong in the same way: they parsed the URL *path*. A ``?database=`` query
param overrides the path for the asyncpg dialect, measured live —
``postgresql+asyncpg://…/darkmem?database=darkmem_test`` reports
``current_database() = darkmem_test`` while every path-derived reading says
``darkmem``. So a guard could approve a URL precisely because it was reading
the name that would not be connected to, with no symptom either way.

Three of the five doors had no name guard at all: ``reset_bench_db`` runs
``DROP SCHEMA public CASCADE`` against whatever ``BENCH_DATABASE_URL`` names,
and the smoke, retrieval-eval and contradiction-miss-rate runners all reach
it. ``BenchDatabase`` checked only that the name was a safe SQL identifier,
which every real database name is.
"""
import pytest

from benchlib import db_target


REAL = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
BENCH = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench"


class TestResolvedDatabaseName:
    def test_reads_the_path_when_there_is_no_override(self):
        assert db_target.resolved_database_name(REAL) == "darkmem"

    def test_a_query_param_overrides_the_path(self):
        # The whole finding, in one assertion: the path says darkmem, the
        # connection lands on darkmem_test, and this must report the latter.
        assert (
            db_target.resolved_database_name(f"{REAL}?database=darkmem_test")
            == "darkmem_test"
        )

    def test_percent_decodes_like_asyncpgs_own_dsn_parser(self):
        assert (
            db_target.resolved_database_name(f"{BENCH}?database=darkmem%5Ftest")
            == "darkmem_test"
        )

    def test_an_empty_override_falls_back_to_the_path(self):
        assert db_target.resolved_database_name(f"{BENCH}?database=") == "darkmem_bench"


class TestDestructiveGuard:
    @pytest.mark.parametrize(
        "url",
        [
            REAL,
            f"{BENCH}?database=darkmem",
            "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
            f"{BENCH}?database=darkmem_test",
            "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_cf",
            f"{BENCH}?database=darkmem_test_cf",
            f"{BENCH}?database=darkmem%5Ftest",
        ],
    )
    def test_refuses_every_route_to_a_database_we_do_not_own(self, url):
        with pytest.raises(RuntimeError, match="refuses to run a destructive reset"):
            db_target.assert_destructive_target_allowed(url, actor="test")

    @pytest.mark.parametrize("url", [BENCH, f"{BENCH}_cf", f"{REAL}?database=darkmem_bench_cf"])
    def test_allows_a_bench_database_however_it_is_addressed(self, url):
        db_target.assert_destructive_target_allowed(url, actor="test")  # must not raise

    def test_names_the_actor_so_the_refusal_says_which_door_refused(self):
        with pytest.raises(RuntimeError, match="reset_bench_db"):
            db_target.assert_destructive_target_allowed(REAL, actor="reset_bench_db")


class TestEveryDoorReadsTheSameRule:
    """A door that reimplements the parse is how this became five readings."""

    def test_bench_db_re_exports_rather_than_reimplements(self):
        from benchlib import bench_db

        assert bench_db.resolved_database_name is db_target.resolved_database_name
        assert (
            bench_db.assert_destructive_target_allowed
            is db_target.assert_destructive_target_allowed
        )

    def test_the_harvest_door_resolves_the_override(self):
        from benchlib import harvest_l2_facts

        assert (
            harvest_l2_facts.bench_db_name(f"{BENCH}?database=darkmem_test")
            == "darkmem_test"
        )

    def test_the_promotion_metrics_door_refuses_the_override(self):
        from benchlib import run_promotion_metrics as rpm

        with pytest.raises(RuntimeError, match="darkmem_test"):
            rpm._assert_not_forbidden(f"{REAL}?database=darkmem_test")

    def test_bench_database_refuses_a_destructive_target_at_construction(self):
        from benchlib import bench_db

        with pytest.raises(RuntimeError, match="refuses to run a destructive reset"):
            bench_db.BenchDatabase(f"{BENCH}?database=darkmem_test")
