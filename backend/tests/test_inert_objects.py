"""Every dormant object lands reviewed, frozen, and with NO writer (T0.13).

Doc 19 §3 and invariant 23: what lands inert lands *reviewed and frozen* with
nothing writing to it, so the risky logic is tested while it is riskless and
its writer ships later against an unchanged contract. The point of this module
is that "nothing writes to it" is **asserted**, not inspected — a future writer
that lands early fails here rather than being noticed in review.

Each object's first-writer task id lives in
``docs/planning/baseline-schema-inventory.md`` §7.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.embedder_registry import _AUX_INDEXES, _TABLE_TEMPLATES

BACKEND = Path(__file__).resolve().parent.parent

# The inert objects, with the task that will first write to each.
#
# `documents` and `blocks` are no longer here: TH1.02, their declared first
# writer (schema inventory §7), landed `app/services/document_ingest.py` and
# `app/repositories/documents.py`. Filing a document resolves its identity on
# the partial `UNIQUE (project, uri)` and gates the pipeline on `content_hash`;
# `tests/test_documents.py` exercises both tables against real rows, which is
# strictly stronger than asserting they stay empty.
#
# The set is now EMPTY, so every test below that loops over it quantifies over
# nothing. As with INERT_COLUMNS, each of those skips with a reason rather than
# passing silently: a green tick on a vacuous loop reads exactly like a green
# tick on a real one. The scaffold is kept for the next table that lands inert.
INERT_TABLES: dict[str, str] = {}
# repositories.index_debt is no longer here: T1.39, its declared first writer
# (schema inventory §7), landed the re-trace drain that writes it.
# entities.repo_ids and entity_relations.repo_ids are no longer here: T2.27,
# their declared first writer (schema inventory §7), landed
# `app/services/code_deriver.py` and the `assert_from_repo` /
# `strip_repo_assertions` primitives. Both arrays now have a real writer, and
# the amended sweeps' `NOT EXISTS (live repo)` predicates are exercised
# against non-empty arrays by `tests/test_code_deriver.py` — of the test
# database; the deriver has no scheduled caller until T2.96, so in production
# the arrays are still empty.
#
# The set is now EMPTY, and every test below that loops over it therefore
# quantifies over nothing. That is intended — this is the scaffold the next
# inert column plugs into, not a live assertion — so each of those tests
# skips with a reason rather than passing silently, because a green tick on a
# vacuous loop reads exactly like a green tick on a real one.
INERT_COLUMNS: dict[tuple[str, str], str] = {}
# triple_embeddings is no longer here: T2.33, its declared first writer (schema
# inventory §7), landed on T2.52's measured 41.7% shortlist miss rate, so the
# conditional branch that would have kept the template inert forever is closed.
# relation_embeddings is no longer here: T2.49, its declared first writer
# (schema inventory §7), landed `app/services/relation_embeddings.py` and the
# Tier-C refresh job that keeps the partition current.
# block_embeddings is no longer here: TH1.05, its declared first writer
# (schema inventory §7), landed `app/services/block_embeddings.py`.
INERT_TEMPLATES = {
    "article_embeddings": "T3.23",
}


# ── the objects exist ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inert_tables_exist(session):
    if not INERT_TABLES:
        pytest.skip("no inert table remains — see INERT_TABLES")
    for table in INERT_TABLES:
        found = (await session.execute(
            text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}
        )).scalar()
        assert found is not None, f"{table} is missing from the baseline"


@pytest.mark.asyncio
async def test_inert_columns_exist(session):
    if not INERT_COLUMNS:
        pytest.skip("no inert column remains — see INERT_COLUMNS")
    for (table, column) in INERT_COLUMNS:
        found = (await session.execute(
            text("SELECT 1 FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name=:t AND column_name=:c"),
            {"t": table, "c": column},
        )).scalar()
        assert found == 1, f"{table}.{column} is missing from the baseline"


def test_inert_templates_are_registered():
    for parent in INERT_TEMPLATES:
        assert parent in _TABLE_TEMPLATES, f"{parent} template is missing"
        assert parent in _AUX_INDEXES, f"{parent} aux indexes are missing"


# ── the objects are empty ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inert_tables_are_empty(session):
    if not INERT_TABLES:
        pytest.skip("no inert table remains — see INERT_TABLES")
    for table in INERT_TABLES:
        count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
        assert count == 0, f"{table} is not empty — something wrote to an inert table"


# The emptiness assertion over `repo_ids` retired with T2.27: the deriver is
# its writer, so a populated array is now the expected state and asserting
# otherwise would forbid the feature. What replaced it is stronger — the
# sweeps are asserted against non-empty arrays in `tests/test_code_deriver.py`
# rather than merely asserted to be vacuous here.


# ── no code path writes to them ──────────────────────────────────────────

def _app_sources() -> list[Path]:
    return [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def test_no_app_code_writes_the_inert_columns():
    """A write is an assignment or an INSERT/UPDATE naming the column.

    Reads are fine — the amended orphan sweeps read ``repo_ids`` in their
    ``NOT EXISTS`` predicates, which is exactly the frozen-but-inert shape
    doc 19 §3 asks for.
    """
    if not INERT_COLUMNS:
        pytest.skip("no inert column remains — see INERT_COLUMNS")
    columns = tuple(sorted({column for _table, column in INERT_COLUMNS}))
    offenders: list[str] = []
    for path in _app_sources():
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for column in columns:
                writes = (
                    f".{column} =" in line
                    or f"{column}=" in line.replace("==", "")
                    or f"SET {column}" in line
                )
                if writes:
                    offenders.append(f"{path.relative_to(BACKEND)}:{lineno}: {stripped}")
    assert not offenders, (
        "an inert column gained a writer:\n" + "\n".join(offenders)
        + "\nIf this is the intended first writer, remove the object from this "
          "module and update the schema inventory §7."
    )


def test_no_app_code_writes_the_inert_tables():
    if not INERT_TABLES:
        pytest.skip("no inert table remains — see INERT_TABLES")
    offenders: list[str] = []
    for path in _app_sources():
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            upper = stripped.upper()
            for table in INERT_TABLES:
                if (f"INSERT INTO {table.upper()}" in upper
                        or f"UPDATE {table.upper()}" in upper
                        or f"DELETE FROM {table.upper()}" in upper):
                    offenders.append(f"{path.relative_to(BACKEND)}:{lineno}: {stripped}")
    assert not offenders, (
        "an inert table gained a writer:\n" + "\n".join(offenders)
    )


def test_no_app_code_writes_the_inert_partitions():
    """The templates are registered but nothing may embed into them.

    ``child_table(parent, fingerprint)`` is the only sanctioned namer, so a
    writer shows up as that call with one of the still-inert parents.
    """
    offenders: list[str] = []
    for path in _app_sources():
        src = path.read_text()
        for parent in INERT_TEMPLATES:
            for marker in (f'child_table("{parent}"', f"child_table('{parent}'"):
                if marker in src:
                    offenders.append(f"{path.relative_to(BACKEND)}: {marker}")
    assert not offenders, (
        "an inert partition family gained a writer:\n" + "\n".join(offenders)
    )


# ── the amendment is behaviour-preserving ────────────────────────────────

def test_amended_sweeps_carry_the_live_repo_predicate():
    """The predicate is present in every statement that can delete a graph row.

    Doc 04 §4.2 gave each of the four original sweep statements one
    ``NOT EXISTS (live repo)`` clause; T2.27's ``strip_repo_assertions`` adds
    the two code-side ones, which need it for the same reason and for a second
    one besides — a repo stripping its own assertion must not delete a row a
    *different* live repo still asserts. Six statements, one clause each. The
    predicate is no longer vacuous: see ``tests/test_code_deriver.py``.
    """
    src = (BACKEND / "app" / "repositories" / "graph.py").read_text()
    assert src.count("FROM repositories rp") == 6, (
        "expected one live-repo predicate in each of the six delete statements"
    )


@pytest.mark.asyncio
async def test_live_repo_predicate_spares_a_repo_asserted_row(session):
    """The amendment is *correct*, not merely vacuous.

    Doc 19 §3's rationale for landing this inert is that the deletion-logic
    change gets reviewed and tested **while it is riskless**. That is only true
    if the predicate is exercised in its non-vacuous form, so this test writes
    ``repo_ids`` directly and proves the sweep spares a row a live repo still
    asserts. T2.27 landed the deriver that writes them for real; this stays as
    the writer-independent proof of the sweep itself.
    """
    from uuid import uuid4

    from app.repositories.graph import PostgresGraphRepository

    repo_id = uuid4()
    await session.execute(
        text("INSERT INTO repositories (id, name, status) "
             "VALUES (CAST(:id AS uuid), 'probe', 'ready')"),
        {"id": str(repo_id)},
    )
    # An entity no memory asserts, but a live repo does.
    ent_id = uuid4()
    await session.execute(
        text("INSERT INTO entities (id, name, entity_type, memory_ids, repo_ids) "
             "VALUES (CAST(:id AS uuid), 'repo-asserted', 'concept', "
             "'{}'::uuid[], ARRAY[CAST(:rid AS uuid)])"),
        {"id": str(ent_id), "rid": str(repo_id)},
    )
    # A second entity nothing asserts at all — the control.
    ghost_id = uuid4()
    await session.execute(
        text("INSERT INTO entities (id, name, entity_type, memory_ids, repo_ids) "
             "VALUES (CAST(:id AS uuid), 'ghost', 'concept', '{}'::uuid[], '{}'::uuid[])"),
        {"id": str(ghost_id)},
    )
    await session.flush()

    result = await PostgresGraphRepository(session).prune_orphan_entities()

    survived = (await session.execute(
        text("SELECT count(*) FROM entities WHERE id = CAST(:id AS uuid)"),
        {"id": str(ent_id)},
    )).scalar()
    reaped = (await session.execute(
        text("SELECT count(*) FROM entities WHERE id = CAST(:id AS uuid)"),
        {"id": str(ghost_id)},
    )).scalar()

    assert survived == 1, "a row a live repo asserts must survive the sweep"
    assert reaped == 0, "a row nothing asserts must still be reaped"
    assert result["entities_pruned"] >= 1


# ── The two Tier-C LLM purposes seeded inert (T1.05, doc 11 §6) ──────


def test_inert_purposes_are_seeded_and_resolvable():
    """Doc 11 §6: the rows, their seeds, and the PURPOSES sweep land BEFORE any
    consumer dispatches. A consumer reaching an unseeded purpose is the same
    class of bug as a feature emitting an untabled entity type — so `inert` here
    means *nothing dispatches*, not *not configured*."""
    from app.services.config import PURPOSES
    from app.services.llm_seed import DEFAULT_PURPOSE_CONFIGS

    seeded = {p.purpose for p in DEFAULT_PURPOSE_CONFIGS}
    for purpose in ("synthesis", "verification"):
        assert purpose in seeded, f"{purpose} is not seeded"
        assert purpose in PURPOSES, f"{purpose} missing from the PURPOSES sweep"


@pytest.mark.asyncio
async def test_inert_purposes_resolve_without_a_row(session):
    """A fresh install has no `llm_purpose_configs` rows until the wizard
    finalizes. Resolution must still return both purposes rather than raising —
    adding a purpose to PURPOSES without a Settings default is a KeyError at the
    first call, and the first call would be a Tier-C consumer in E2/E3."""
    from app.services.config import get_llm_config

    config = await get_llm_config(session)
    for purpose in ("synthesis", "verification"):
        assert purpose in config
        assert config[purpose].model


def test_no_app_code_dispatches_the_inert_purposes():
    """**There are no inert purposes left**, and this guard is the record of
    how each one left.

    `verification` left on 2026-07-31 with T2.26, its declared first writer:
    the judge dispatches on it, and the single-door discipline moved to the
    stricter scan in `tests/test_verification_judge.py`. `synthesis` left on
    2026-08-11 with T3.02, exactly as this test's own instructions said it
    should — `app/services/article_synthesis.py` is the article writer, the
    last of doc 11's eight purposes to gain a consumer.

    The loop below now quantifies over an empty tuple and so asserts nothing.
    It is kept, and kept empty rather than deleted, because a ninth purpose
    seeded inert would need exactly this guard and re-deriving it then is
    harder than leaving it — the same reasoning the dream-job family's
    unshipped-members test carries. `test_every_seeded_purpose_has_a_consumer`
    below is what has teeth today."""
    allowed = {
        "app/config.py",              # the Settings defaults
        "app/services/config.py",     # PURPOSES + the defaults map
        "app/services/llm_seed.py",   # the seed rows
    }
    offenders: list[str] = []
    for path in _app_sources():
        rel = str(path.relative_to(BACKEND))
        if rel in allowed:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for purpose in ():
                if f'"{purpose}"' in line or f"'{purpose}'" in line:
                    offenders.append(f"{rel}:{lineno}: {stripped}")
    assert not offenders, (
        "an inert LLM purpose gained a dispatcher:\n" + "\n".join(offenders)
        + "\nIf this is the intended first writer (T3.02), remove the "
          "purpose from this test and update the planning record, as T2.26 "
          "did for verification."
    )


# ── The Tier-C dream-job family inert members (T2.08, T2.14) ─────────


def test_article_synthesis_job_is_inert():
    """**No longer inert, and this is where that is recorded.**

    T2.14 registered the job with a `PlaceholderJobRunner` and this test held
    it there until its owning task landed. T3.02 landed it on 2026-08-11, so
    the assertion is inverted rather than deleted: the job must now carry a
    real runner, and a regression to a placeholder — which is what a bad merge
    of this file would look like — fails here.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services.dream_jobs import (
        ARTICLE_SYNTHESIS_JOB_KEY,
        PlaceholderJobRunner,
        register_dream_jobs,
    )
    from app.services.job_registry import JobRegistry

    from .conftest import test_engine

    registry = JobRegistry(async_sessionmaker(test_engine, expire_on_commit=False))
    register_dream_jobs(registry)
    job = registry.get(ARTICLE_SYNTHESIS_JOB_KEY)
    assert job is not None, f"{ARTICLE_SYNTHESIS_JOB_KEY} not registered"
    assert not isinstance(job.runner, PlaceholderJobRunner), (
        "article_synthesis carries T3.02's real runner; a placeholder here is "
        "a regression, not a pending task"
    )


def test_every_seeded_purpose_has_a_consumer():
    """The inverse of the guard above, and the one with teeth now.

    Doc 11 seeds eight purposes. Each was resolvable from day one and each was
    to gain a dispatcher when its owning task landed; `synthesis` was the last
    outstanding one and T3.02 is its consumer. If a ninth is seeded inert, this
    fails and points at the now-empty loop above as the guard to re-arm.
    """
    from app.services.config import PURPOSES

    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _app_sources()
        if str(path.relative_to(BACKEND)) not in {
            "app/config.py", "app/services/config.py", "app/services/llm_seed.py",
        }
    )
    missing = [
        purpose for purpose in PURPOSES
        if f'"{purpose}"' not in sources and f"'{purpose}'" not in sources
    ]

    assert missing == [], (
        "these seeded purposes have no consumer anywhere in app/: "
        f"{missing}. A purpose landing inert is lawful — re-arm the loop in "
        "`test_no_app_code_dispatches_the_inert_purposes` with its name."
    )
