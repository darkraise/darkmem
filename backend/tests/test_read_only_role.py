"""The viewer role is the enforcement, proven rather than asserted.

`scripts/worker/viewer-grants.sql` is what actually makes the backup worker
read-only. Everything the `DARKMEM_READ_ONLY` flag does is ergonomics on top
of it, so this module is the one that has to hold: it applies the real grants
file to the real test database, opens a second engine as that role, and
checks both directions -- the reads the viewer must keep and the writes it
must be refused, asserted on **SQLSTATE 42501** rather than on a message.

The D-group scan below is the other half. The worker's read paths only work
if no read takes a row lock, because `SELECT ... FOR UPDATE` needs privilege
beyond `SELECT`. That claim is pinned as an equality against a recorded
writer set rather than a subset: an allowlist a future author widens to go
green proves nothing, which is the failure this test exists to prevent.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

REPO_ROOT = Path(__file__).resolve().parents[2]
GRANTS = REPO_ROOT / "scripts" / "worker" / "viewer-grants.sql"
APP = REPO_ROOT / "backend" / "app"

VIEWER = "darkmem_viewer_test"
VIEWER_PASSWORD = "viewer-test-password"


# ---------------------------------------------------------------------------
# The role, against the real database
# ---------------------------------------------------------------------------


def _viewer_url() -> str:
    """The test URL with the credentials swapped for the scratch role's."""
    url = settings.test_database_url
    head, tail = url.split("://", 1)
    _, host_and_db = tail.split("@", 1)
    return f"{head}://{VIEWER}:{VIEWER_PASSWORD}@{host_and_db}"


async def _apply_grants(conn, dbname: str) -> None:
    """Run the real grants file, resolving psql's own syntax.

    The statements are executed from the committed file rather than restated
    here: a test that restated them would go green against grants nobody
    applies, which is the one way this proof could be worthless.

    `\\gexec` means "run every string this query returned", so that is exactly
    what happens below -- the `format()` call is evaluated by Postgres and its
    result executed, rather than the literal being pulled out of the source by
    a regex that would rot the first time the file is reformatted. psql's
    `:'var'` interpolation (a quoted literal) is substituted first, since
    asyncpg has no notion of it.
    """
    body = GRANTS.read_text(encoding="utf-8")
    body = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    )
    body = (
        body.replace(":'viewer_password'", f"'{VIEWER_PASSWORD}'")
        .replace(":'dbname'", f"'{dbname}'")
        .replace("darkmem_viewer", VIEWER)
    )

    for chunk in re.split(r"\\gexec|;", body):
        statement = chunk.strip()
        if not statement:
            continue
        if statement.upper().startswith("SELECT"):
            for produced in (await conn.execute(text(statement))).scalars():
                if produced:
                    await conn.execute(text(produced))
        else:
            await conn.execute(text(statement))


PROBE_FINGERPRINT = "viewer-role-probe|4"


@pytest_asyncio.fixture
async def viewer_engine(setup_database):
    """A scratch role holding exactly what the grants file grants.

    Depends on `setup_database`, never on `session`: that fixture holds an
    open transaction on these tables, and `GRANT` takes an exclusive lock on
    every object it touches, so the grants would block on it forever.

    An embedding partition is created *before* the grants run, mirroring
    production order -- the restore replays the whole snapshot, then
    `restore-cycle.sh` applies the grants. `GRANT SELECT ON ALL TABLES` only
    covers what exists at grant time, so getting this order wrong is the way a
    worker ends up able to read everything except the vectors retrieval needs.

    Roles are cluster-global, so the teardown is unconditional -- a leaked
    `darkmem_viewer_test` would silently change what the next run measures.
    """
    from app.services.embedder_registry import child_table

    privileged = create_async_engine(
        settings.test_database_url, isolation_level="AUTOCOMMIT"
    )
    dbname = settings.test_database_url.rsplit("/", 1)[-1]
    child = child_table("memory_embeddings", PROBE_FINGERPRINT)

    async with privileged.connect() as conn:
        await conn.execute(
            text(
                "INSERT INTO embedders (fingerprint, model_id, dims, source) "
                "VALUES (:fp, :mid, 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
            ),
            {"fp": PROBE_FINGERPRINT, "mid": "viewer-role-probe"},
        )
        await conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {child} ("
                " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
                " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
                " embedding vector(4) NOT NULL,"
                " PRIMARY KEY (memory_id, fingerprint))"
            )
        )
        exists = (
            await conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": VIEWER}
            )
        ).scalar()
        if exists:
            await conn.execute(text(f"DROP OWNED BY {VIEWER}"))
            await conn.execute(text(f"DROP ROLE {VIEWER}"))
        await _apply_grants(conn, dbname)

    engine = create_async_engine(_viewer_url())
    try:
        yield engine
    finally:
        await engine.dispose()
        async with privileged.connect() as conn:
            await conn.execute(text(f"DROP OWNED BY {VIEWER}"))
            await conn.execute(text(f"DROP ROLE IF EXISTS {VIEWER}"))
            # The probe partition is committed, so it outlives the test. Left
            # behind, every later reader that walks `embedders` looks for
            # sibling partitions this probe never created.
            await conn.execute(text(f"DROP TABLE IF EXISTS {child}"))
            await conn.execute(
                text("DELETE FROM embedders WHERE fingerprint = :fp"),
                {"fp": PROBE_FINGERPRINT},
            )
        await privileged.dispose()


def _sqlstate(exc: Exception) -> str | None:
    return getattr(getattr(exc, "orig", None), "sqlstate", None)


READABLE = (
    "memories",
    "knowledge_triples",
    "events",
    "documents",
    "blocks",
    "config",
    "entities",
)


@pytest.mark.parametrize("table", READABLE)
async def test_the_viewer_can_read_every_surface_the_worker_serves(
    viewer_engine, table,
):
    async with viewer_engine.connect() as conn:
        await conn.execute(text(f"SELECT * FROM {table} LIMIT 1"))


async def test_the_viewer_can_read_an_embedding_partition(viewer_engine):
    """The case most likely to be missed. `GRANT SELECT ON ALL TABLES` covers
    what exists at grant time, and a worker that can read every table except
    the per-fingerprint vector partitions can log in, browse, and return
    nothing for every search."""
    from app.services.embedder_registry import child_table

    child = child_table("memory_embeddings", PROBE_FINGERPRINT)
    async with viewer_engine.connect() as conn:
        await conn.execute(text(f"SELECT * FROM {child} LIMIT 1"))


WRITES = (
    ("INSERT INTO memories (content, source, memory_type) "
     "VALUES ('x', 'test', 'fact')"),
    "UPDATE config SET value = '{}'::jsonb WHERE key = 'nothing_here'",
    "DELETE FROM events WHERE id = -1",
    "SELECT * FROM memory_buffer LIMIT 1 FOR UPDATE",
    "CREATE TABLE viewer_should_not_manage_this (id int)",
)


@pytest.mark.parametrize("statement", WRITES)
async def test_every_write_is_refused_with_sqlstate_42501(viewer_engine, statement):
    """Asserted on the code, not the message: the 403 handler keys on 42501,
    so a refusal that carried any other SQLSTATE would surface to the operator
    as a 500 instead of a clean read-only answer.

    `SELECT ... FOR UPDATE` is in this list on purpose -- a row lock needs
    privilege beyond SELECT, which is why the D-group scan below has to hold
    for the worker's read paths to work at all."""
    async with viewer_engine.connect() as conn:
        with pytest.raises(ProgrammingError) as exc:
            await conn.execute(text(statement))
        assert _sqlstate(exc.value) == "42501", (
            f"expected an insufficient-privilege refusal, got "
            f"{_sqlstate(exc.value)}"
        )


# ---------------------------------------------------------------------------
# The D-group scan: which modules take a row lock
# ---------------------------------------------------------------------------

#: Every module that takes a row lock, and every one of them is a writer path.
#: This is an equality, not an allowlist: a new entrant fails the test and takes
#: a recorded classification, which is the whole point. Widening it to go green
#: proves nothing.
#:
#: **This set is measured, and every hand-written inventory of it so far has
#: been wrong.** The plan's first list named `api/routes/config.py` and
#: `job_registry.py`; review M-6 corrected that (`_lock_config_row` takes a
#: transaction advisory lock and its own comment says `FOR UPDATE` "would not
#: do", and `job_registry` issues no lock at all) and gave a twelve-module
#: replacement -- which this scan then found wrong in both directions on
#: 2026-09-02. `services/wait_process.py` and `services/memory_buffer.py` were
#: named and only *discuss* the lock in a docstring; the real lock is in
#: `buffer_flush.flush_claimed`, which both of them point at. And increment
#: 8's `services/block_verbs.py` and `services/document_door.py` were missing,
#: having landed after the amendment was written.
#:
#: Which is the argument for the scan: three successive prose inventories of
#: one grep's output disagreed with the grep. Read the set off the failure,
#: never off a document.
ROW_LOCK_WRITERS = {
    "repositories/knowledge_triples.py",
    "services/block_verbs.py",
    "services/block_embeddings.py",
    "services/buffer_flush.py",
    "services/buffer_monitor.py",
    "services/document_door.py",
    # Holds the dream actions' locked memory read; memory_dream and
    # dream_undo, both writers, are the only modules that execute it.
    "services/dream_journal.py",
    "services/dream_undo.py",
    "services/entity_merge.py",
    "services/fact_lift.py",
    "services/fact_provenance.py",
    "services/human_adjudication.py",
    "services/page_door.py",
    "services/pipeline.py",
    "services/supersede.py",
    "services/verification_ladder.py",
    "services/verification_recompute.py",
    "services/worklog.py",
}

#: Modules that serve the worker's reads and must take no lock at all. Asserted
#: separately from the equality above so the claim is stated positively where a
#: reader will look for it.
#:
#: `document_door` is deliberately absent: it serves reads *and* writes, and
#: increment 8's conversion race is closed by a `FOR UPDATE` on the document
#: row. That lock fails under the viewer role with 42501 and reaches the 403
#: handler, which is exactly what a write should do. Its read verbs
#: (`document_blocks`, `document_outline`, `search_sections`) take no lock, and
#: that is what the D-group claim actually rests on -- asserting the whole
#: module is lock-free would be asserting something false about a writer.
PURE_READ_MODULES = (
    "services/hybrid_search.py",
    "services/facts_channel.py",
    "services/block_query.py",
    "services/events.py",
    "services/code_query.py",
)


def _takes_a_row_lock(path: Path) -> bool:
    """True when the module *executes* a row lock, ignoring prose about one.

    A bare string statement is a docstring; a string handed to `text()` is
    code. `api/routes/config.py:430` and `models/memory.py:91` are the former
    and must not count as either kind of hit.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "with_for_update":
            return True
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "FOR UPDATE" in node.value
            and id(node) not in docstrings
        ):
            return True
    return False


def test_every_row_lock_in_the_tree_is_on_a_writer_path():
    live = {
        str(path.relative_to(APP))
        for path in APP.rglob("*.py")
        if _takes_a_row_lock(path)
    }
    assert live == ROW_LOCK_WRITERS, (
        "the row-lock inventory moved. A row lock needs privilege beyond "
        "SELECT, so it fails under the viewer role: a new entrant must be "
        "classified as a writer path (add it here) or removed from the read "
        f"path. missing={ROW_LOCK_WRITERS - live}, unexpected={live - ROW_LOCK_WRITERS}"
    )


@pytest.mark.parametrize("module", PURE_READ_MODULES)
def test_the_worker_read_path_takes_no_row_lock(module):
    assert not _takes_a_row_lock(APP / module), (
        f"{module} serves the read-only worker's reads and now takes a row "
        f"lock, which the viewer role refuses with 42501"
    )


def test_the_grants_file_holds_no_write_verb():
    """The floor stays a floor. A GRANT on a sequence or a function, or any
    write verb, is an addition to the attack surface and takes a recorded
    reason -- not a quiet edit."""
    body = GRANTS.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for forbidden in ("INSERT", "UPDATE ", "DELETE", "TRUNCATE", "ALL PRIVILEGES",
                      "ON SEQUENCES", "ON FUNCTIONS", "GRANT USAGE ON SEQUENCE"):
        assert forbidden not in code, (
            f"viewer-grants.sql grants {forbidden!r} -- the role is SELECT-only"
        )
    assert "GRANT SELECT ON ALL TABLES IN SCHEMA PUBLIC" in code
