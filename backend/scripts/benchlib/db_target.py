"""Which database a URL actually reaches, and whether we may destroy it.

Deliberately free of import-time side effects. ``bench_db`` cannot host this:
importing it rewrites ``os.environ["DATABASE_URL"]`` to the bench database,
which is exactly why ``run_promotion_metrics`` refuses to import it — and that
runner needs this resolution too. A guard that half the callers cannot import
is a guard half the callers will reimplement, which is how this rule came to
have five separate readings in the first place.
"""
from __future__ import annotations

from urllib.parse import unquote

from sqlalchemy.engine import make_url

# Every database a harness may never destroy, and the prefix pytest owns per lane.
FORBIDDEN_TARGETS = frozenset({"darkmem", "darkmem_test"})
LANE_TEST_PREFIX = "darkmem_test_"


def resolved_database_name(url: str) -> str:
    """The database a connection to ``url`` actually lands on.

    **Not** the path component, and not ``make_url(url).database`` either. A
    ``?database=`` query param overrides the path for the asyncpg dialect,
    which passes it through as a connect kwarg — measured live:
    ``postgresql+asyncpg://…/darkmem?database=darkmem_test`` reports
    ``current_database() = darkmem_test`` while every path-derived reading
    says ``darkmem``. A guard parsing the path alone therefore approves a URL
    that reaches a forbidden database, silently and with no symptom.

    ``unquote`` on top, because asyncpg's own DSN parser percent-decodes a
    name (``darkmem%5Ftest`` connects to ``darkmem_test``), so this reading
    must never be looser than whichever code path ends up connecting.
    """
    parsed = make_url(url)
    override = parsed.query.get("database")
    if isinstance(override, tuple):  # SQLAlchemy renders a repeated key as one
        override = override[-1] if override else None
    return unquote(str(override) if override else (parsed.database or ""))


def assert_destructive_target_allowed(
    url: str, *, actor: str, env_var: str = "BENCH_DATABASE_URL"
) -> None:
    """Refuse to aim a schema-destroying operation at a database that is not ours.

    ``bench_db.reset_bench_db`` runs ``DROP SCHEMA public CASCADE`` against
    whatever ``BENCH_DATABASE_URL`` names and had no name guard at all — only
    a SQL-identifier safety check, which every real database name passes. The
    three runners reaching it (smoke, retrieval eval, contradiction miss-rate)
    inherited that gap.

    ``env_var`` names the environment variable the caller actually resolved
    ``url`` from, so the refusal points the operator back at the variable
    they can fix. It defaults to ``BENCH_DATABASE_URL`` for ``bench_db``'s
    original callers; a caller that resolves ``DATABASE_URL`` (or any other
    variable) instead must pass its own name here, or the remedy misdirects
    them to a variable unrelated to their situation.
    """
    db = resolved_database_name(url)
    if db in FORBIDDEN_TARGETS or db.startswith(LANE_TEST_PREFIX):
        raise RuntimeError(
            f"{actor} refuses to run a destructive reset against {db!r}. "
            f"darkmem is the real database and darkmem_test/darkmem_test_N "
            f"belong to pytest, which drops and recreates them concurrently; "
            f"see CLAUDE.md's three-databases rule. Point {env_var} at a "
            f"database this operation may safely destroy instead."
        )
