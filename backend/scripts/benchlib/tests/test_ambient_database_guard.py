"""Every script that can destroy rows must say which database it may destroy.

`purge_eval.py` resurrects every superseded memory in whatever `DATABASE_URL`
resolves to, and on this host that default is production. The guard already
exists (`db_target.assert_destructive_target_allowed`); what was missing is
anything that notices a destructive script which does not call it.

This test enumerates the population rather than asserting one call site, so the
next harness that opens the ambient session and issues a DELETE cannot land
silently — which is the failure mode the whole review found repeatedly.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[2]

# Modules that issue destructive SQL but are exempt, each with the reason.
#
# This dict was widened past the original three entries after a first run of
# the scan below against the real tree: the DESTRUCTIVE tuple's "UPDATE " and
# "TRUNCATE" match ordinary English prose ("update the config", "truncated
# preview") as readily as SQL, and several benchlib modules issue real
# destructive SQL that only ever reaches the bench database, not an ambient
# one. Every entry here was individually verified by reading the module, not
# assumed from its name.
EXEMPT = {
    # bench_db owns the guard's other side: it calls assert_destructive_target_allowed
    # itself before DROP SCHEMA, and re-checking it here would assert the guard twice.
    "benchlib/bench_db.py": "calls the guard directly before DROP SCHEMA",
    # The e2e stack builds and tears down its own disposable database by name.
    "e2e/e2e_db.py": "creates and drops the database it names, never an ambient one",
    "e2e/stack.py": "drives e2e_db, holds no SQL of its own",
    # db_target.py is the guard itself: the matched "DROP SCHEMA" is its own
    # docstring quoting bench_db.reset_bench_db's behaviour, not SQL this
    # module issues.
    "benchlib/db_target.py": "the guard module; matched text is a docstring describing bench_db, not SQL it issues",
    # These four match only because "truncate"/"truncated"/"update" appear as
    # ordinary English words in docstrings and comments; none contains SQL.
    "benchlib/entailment_gold.py": "matched text is prose ('truncated or padded'), not SQL",
    "benchlib/full_context.py": "matched text is prose ('context-truncated', 'truncate'), not SQL",
    "benchlib/replacement_premise_draw.py": "matched text is prose ('truncated'), not SQL",
    "benchlib/resample_sheet.py": "matched text is prose ('update _RULEBOOK_HEADINGS'), not SQL",
    # seed_test_memories.py's matches live entirely inside sample memory
    # content strings used as fixture data (fake debugging tips); the script
    # itself only adds rows through the pipeline, never raw destructive SQL.
    "seed_test_memories.py": "matched text is inside seed fixture content strings, not SQL the script issues",
    # isolation_probe.py has one real `DELETE FROM memories` statement, but it
    # imports benchlib.bench_db before any app.database import (overriding the
    # ambient DATABASE_URL to the bench database as an import-time side
    # effect), and its sole entry point, run_probe(), calls
    # bench_db.reset_bench_db() -- which itself calls the guard -- before that
    # statement can run.
    "benchlib/isolation_probe.py": "bench_db import overrides DATABASE_URL first; run_probe() resets via bench_db before writing",
    # promotion_corpus.py and retrieval_gold.py are pure libraries: every
    # destructive statement runs against a `session_factory` parameter their
    # caller supplies. Neither imports app.database or resolves DATABASE_URL
    # itself. Their only caller in this tree (run_gc_evidence.py, via
    # arm_ablation.py / run_retrieval_eval.py) passes a bench-scoped factory
    # obtained after a guarded reset.
    "benchlib/promotion_corpus.py": "library; writes only through a caller-supplied session_factory, always bench-scoped in this tree",
    "benchlib/retrieval_gold.py": "library; writes only through a caller-supplied session_factory, always bench-scoped in this tree",
    # arm_ablation.py, run_retrieval_eval.py and run_smoke.py each default
    # their entry point's session_factory to bench_db.session_factory and
    # call bench_db.reset_bench_db() -- which calls the guard -- before any
    # destructive statement runs.
    "benchlib/arm_ablation.py": "defaults to bench_db.session_factory; calls bench_db.reset_bench_db() before writing",
    "benchlib/run_retrieval_eval.py": "defaults to bench_db.session_factory; calls bench_db.reset_bench_db() before writing",
    "benchlib/run_smoke.py": "defaults to bench_db.session_factory; calls bench_db.reset_bench_db() before writing",
    # run_promotion_metrics.py is the one sanctioned exception that targets
    # the real `darkmem` database on purpose, as a read-only gate probe: its
    # engine is opened with `default_transaction_read_only=on` at the
    # Postgres connection level, so a write fails in the database, not in
    # review. The matched "DROP SCHEMA" is prose in its own docstring/comments
    # describing why it must not touch darkmem_test.
    "benchlib/run_promotion_metrics.py": "read-only by connection GUC (default_transaction_read_only=on); matched text is prose",
    # The whole cutover/ package (the LLM-providers-transition dump loader)
    # requires explicit --source-dsn/--target-dsn CLI arguments; no file in
    # the package reads DATABASE_URL or imports app.database, so there is no
    # ambient default to guard. It carries its own bespoke guard chain
    # (assert_source_not_production, assert_distinct_databases,
    # assert_distinct_live_databases, and a read-only source connection)
    # purpose-built for its two-DSN transform shape, which
    # assert_destructive_target_allowed (a single ambient URL) does not fit.
    "cutover/backfill.py": "requires --target-dsn explicitly; no ambient DATABASE_URL fallback in this package",
    "cutover/stage.py": "requires --target-dsn explicitly; no ambient DATABASE_URL fallback in this package",
    "cutover/transform.py": "requires --target-dsn explicitly; no ambient DATABASE_URL fallback in this package",
}

DESTRUCTIVE = ("DELETE FROM", "DROP SCHEMA", "DROP TABLE", "TRUNCATE", "UPDATE ")


def _sql_literals(tree: ast.AST) -> list[str]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


def _names_the_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "assert_destructive_target_allowed":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "assert_destructive_target_allowed":
            return True
    return False


def _destructive_modules() -> list[tuple[str, pathlib.Path]]:
    found = []
    for path in sorted(SCRIPTS.rglob("*.py")):
        if "__pycache__" in path.parts or "/tests/" in path.as_posix():
            continue
        rel = path.relative_to(SCRIPTS).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        sql = " ".join(_sql_literals(tree)).upper()
        if any(verb in sql for verb in DESTRUCTIVE):
            found.append((rel, path))
    return found


def test_every_destructive_script_declares_its_target():
    offenders = []
    for rel, path in _destructive_modules():
        if rel in EXEMPT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _names_the_guard(tree):
            offenders.append(rel)
    assert offenders == [], (
        "these scripts issue destructive SQL against whatever DATABASE_URL "
        f"resolves to, with no target guard: {offenders}. Call "
        "benchlib.db_target.assert_destructive_target_allowed(url, actor=...) "
        "before opening the session, or add the module to EXEMPT with a reason."
    )


def test_the_exempt_list_names_only_modules_that_still_exist():
    """An exemption for a deleted file is an exemption nobody is reading."""
    missing = [rel for rel in EXEMPT if not (SCRIPTS / rel).exists()]
    assert missing == [], f"EXEMPT names modules that no longer exist: {missing}"


def test_the_scan_finds_the_scripts_it_is_meant_to_cover():
    """A scan that matches nothing passes for the wrong reason."""
    found = {rel for rel, _ in _destructive_modules()}
    assert "benchlib/bench_db.py" in found, (
        "the destructive-SQL scan no longer sees bench_db, so it is no longer "
        f"finding what it was written to find; it saw {sorted(found)}"
    )
