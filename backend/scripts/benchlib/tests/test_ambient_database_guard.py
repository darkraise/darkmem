"""Every script that can destroy rows must say which database it may destroy.

`purge_eval.py` resurrects every superseded memory in whatever `DATABASE_URL`
resolves to, and on this host that default is production. The guard already
exists (`db_target.assert_destructive_target_allowed`); what was missing is
anything that notices a destructive script which does not call it.

**What the scan below actually covers, and what it does not.** It matches
only destructive SQL that appears as a string literal (``DELETE FROM``,
``DROP SCHEMA``, ``DROP TABLE``, ``TRUNCATE``, ``UPDATE ``) somewhere in a
module's own AST -- a text search over parsed source, not a data-flow or
call-graph analysis. It does **not** see:

- SQLAlchemy ORM constructs (``sqlalchemy.delete(Memory)``,
  ``session.delete(obj)``, ``update(Memory).values(...)``) -- no verb
  string appears in the caller's own source;
- SQL assembled so the verb itself is not a literal
  (``text(f"{verb} FROM memories")``);
- SQL that lives in a helper module while the *caller* is the one that
  resolves the ambient URL -- the helper gets flagged (and may be exempt
  on its own terms below), but the caller that points it at production
  does not;
- SQL loaded from a ``.sql`` file or other data file at runtime;
- anything destructive that is not SQL at all -- exactly `run.py`'s MCP
  `memory_delete` call, which this scan does not match;
- anything outside ``SCRIPTS`` (``backend/scripts``) at all -- the walk
  below is rooted there, so a destructive harness landing in
  ``backend/app/`` or the repo-root ``scripts/`` is invisible to the
  population scan regardless of how its SQL is written.

`_names_the_guard` has the mirror-image limitation: it proves
`assert_destructive_target_allowed` is *named* somewhere in the module, not
that a call to it actually runs, runs before the destructive statement, or
is passed the URL that will be connected to. A module that calls the guard
against a hardcoded bench URL, or calls it after the session already
opened, satisfies this check. It is not nothing, though -- a bare
``from benchlib.db_target import assert_destructive_target_allowed`` does
*not* satisfy it on its own, since an import binds an ``ast.alias``, which
is neither an ``ast.Name`` nor an ``ast.Attribute``; the module has to
actually reference the name, not just import it.

So: this test enumerates the population its scan can see, so a destructive
SQL *literal* added to a new harness cannot land ungated silently. It is not
a proof that every destructive script in this tree is safe.
"""
from __future__ import annotations

import ast
import pathlib

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
    # The e2e stack builds and tears down its own disposable database by
    # name, and deliberately never darkmem_test -- guarding it with
    # assert_destructive_target_allowed would refuse its own
    # darkmem_test_1/darkmem_test_N target, since LANE_TEST_PREFIX forbids
    # that prefix too, and break the e2e suite.
    "e2e/e2e_db.py": "creates and drops the database it names, never an ambient one",
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
    # Both are pure libraries: every destructive statement runs against a
    # `session_factory` parameter their caller supplies, never a factory
    # either module opens itself. retrieval_gold.py touches neither
    # app.database nor DATABASE_URL. promotion_corpus.py does import
    # benchlib.bench_db (which overrides os.environ["DATABASE_URL"] to the
    # bench database as an import-time side effect, the same mechanism
    # isolation_probe.py relies on) -- but it never uses that override to
    # open a session of its own. Their only caller in this tree
    # (run_gc_evidence.py, via arm_ablation.py / run_retrieval_eval.py)
    # passes a bench-scoped factory obtained after a guarded reset.
    "benchlib/promotion_corpus.py": "library; writes only through a caller-supplied session_factory; imports bench_db for the DATABASE_URL override but opens no session itself",
    "benchlib/retrieval_gold.py": "library; writes only through a caller-supplied session_factory, always bench-scoped in this tree",
    # arm_ablation.py and run_retrieval_eval.py each default their entry
    # point's session_factory parameter to bench_db.session_factory.
    # run_smoke.py has no such parameter -- it references
    # bench_db.session_factory directly wherever it needs a session. All
    # three call bench_db.reset_bench_db() -- which calls the guard -- before
    # any destructive statement runs.
    "benchlib/arm_ablation.py": "defaults to bench_db.session_factory; calls bench_db.reset_bench_db() before writing",
    "benchlib/run_retrieval_eval.py": "defaults to bench_db.session_factory; calls bench_db.reset_bench_db() before writing",
    "benchlib/run_smoke.py": "hardcodes bench_db.session_factory (no parameter); calls bench_db.reset_bench_db() before writing",
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

# Entry points this task added a guard call to. Two of them -- run.py and
# debug_clean.py -- carry no destructive SQL literal (run.py's destructive
# action is an MCP call, not SQL; debug_clean.py writes nothing today), so
# test_every_destructive_script_declares_its_target never examines them and
# a regression there would otherwise leave every test in this file green.
GUARDED_ENTRY_POINTS = (
    "eval_round3/purge_eval.py",
    "eval_round3/run.py",
    "eval_round3/debug_clean.py",
    "backfill_metadata_v2.py",
)

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


def test_the_exempt_list_names_only_modules_the_scan_still_matches():
    """An exemption for a module the scan no longer flags is dead weight at
    best -- it suppresses nothing -- and at worst hides a module that was
    rewritten so its stated reason no longer holds. Membership in the scan's
    own found set subsumes the older "does the file still exist" check: a
    deleted file cannot appear in it either."""
    found = {rel for rel, _ in _destructive_modules()}
    stale = sorted(rel for rel in EXEMPT if rel not in found)
    assert stale == [], f"EXEMPT names modules the scan no longer matches: {stale}"


def test_the_scan_finds_the_scripts_it_is_meant_to_cover():
    """A scan that matches nothing passes for the wrong reason, and the
    guard call this task added to each of GUARDED_ENTRY_POINTS must not
    regress even on a file the scan above cannot see at all."""
    found = {rel for rel, _ in _destructive_modules()}
    for rel in ("benchlib/bench_db.py", "eval_round3/purge_eval.py"):
        assert rel in found, (
            "the destructive-SQL scan no longer sees a known-destructive "
            f"module ({rel}), so it is no longer finding what it was "
            f"written to find; it saw {sorted(found)}"
        )

    ungated = []
    for rel in GUARDED_ENTRY_POINTS:
        tree = ast.parse((SCRIPTS / rel).read_text(encoding="utf-8"))
        if not _names_the_guard(tree):
            ungated.append(rel)
    assert ungated == [], (
        f"these known entry points no longer call the guard: {ungated}. "
        "eval_round3/run.py and eval_round3/debug_clean.py in particular "
        "carry no destructive SQL literal, so "
        "test_every_destructive_script_declares_its_target cannot catch "
        "their regression on its own -- this anchor is what does."
    )
