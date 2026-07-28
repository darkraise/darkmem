"""Coverage of the one-time cutover transform (T1.51).

The transform is the only code in the repository that moves irrecoverable user
data, so these tests are written to fail if a guard is removed rather than to
demonstrate that a happy path works. Two of them pin the **order** of the two
verification legs, which is the property the whole design rests on: a
driver-level defect corrupts staging and target identically, so a check that
only compares those two agrees with itself and passes.

The fixture databases are derived from ``TEST_DATABASE_URL`` — never the real
``darkmem`` database, and never the shared unnumbered ones.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cutover import db as cutover_db  # noqa: E402
from cutover import preflight, spec, stage, transform, verify  # noqa: E402
from cutover.__main__ import CutoverResult, run_cutover, write_snapshot  # noqa: E402
from cutover.__main__ import _amain as cli_amain  # noqa: E402
from cutover.__main__ import main as cli_main  # noqa: E402
from cutover.db import CutoverError  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DSN = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
)


def _base_identity():
    return cutover_db.dsn_identity(TEST_DSN)


BASE = _base_identity()
SOURCE_DB = f"{BASE.database}_cutsrc"
TARGET_DB = f"{BASE.database}_cuttgt"


def _dsn_for(database: str) -> str:
    scheme, _, rest = cutover_db.normalise_dsn(TEST_DSN).partition("://")
    authority = rest.split("/", 1)[0]
    return f"postgresql://{authority}/{database}"


SOURCE_DSN = _dsn_for(SOURCE_DB)
TARGET_DSN = _dsn_for(TARGET_DB)
ADMIN_DSN = _dsn_for("postgres")


# The brownfield schema at revision 0006, reproduced from the six migrations
# deleted by the baseline squash. The five carried tables and the three the
# pre-flight reads carry their real shape; the remaining eighteen are stubs,
# because the only assertion that touches them is a name-presence check.
LEGACY_DDL = """
CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded');

CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);

CREATE TABLE tags (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50)
);

CREATE TABLE memories (
    id                  UUID NOT NULL PRIMARY KEY,
    content             TEXT NOT NULL,
    source              VARCHAR(100) NOT NULL,
    source_agent        VARCHAR(255),
    memory_type         VARCHAR(50),
    importance          DOUBLE PRECISION NOT NULL,
    metadata            JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ,
    is_archived         BOOLEAN NOT NULL DEFAULT false,
    llm_classified_type VARCHAR(50),
    llm_summary         TEXT,
    llm_emotions        JSONB,
    llm_flags           JSONB,
    project             TEXT NOT NULL DEFAULT 'default',
    status              memory_status NOT NULL DEFAULT 'active',
    superseded_by       UUID,
    technologies        TEXT[] NOT NULL DEFAULT '{}',
    confidence          REAL NOT NULL DEFAULT 0.75,
    search_vector       TSVECTOR,
    CONSTRAINT chk_superseded_has_pointer
        CHECK (status != 'superseded' OR superseded_by IS NOT NULL),
    CONSTRAINT fk_memories_superseded_by
        FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL
);

CREATE TABLE memory_tags (
    memory_id UUID    NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tag_id    INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, tag_id)
);

CREATE TABLE conversations (
    id          UUID NOT NULL PRIMARY KEY,
    title       TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id              UUID NOT NULL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR NOT NULL,
    content         TEXT NOT NULL,
    context         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE repositories (
    id                  UUID NOT NULL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    url                 VARCHAR(1024),
    local_path          VARCHAR(1024),
    provider            VARCHAR(50) NOT NULL,
    default_branch      VARCHAR(100) NOT NULL,
    auth_token_ref      VARCHAR(255),
    last_indexed_commit VARCHAR(64),
    last_indexed_at     TIMESTAMPTZ,
    auto_sync           BOOLEAN NOT NULL DEFAULT false,
    status              VARCHAR(20) NOT NULL DEFAULT 'idle',
    status_message      VARCHAR(500),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE api_keys (id UUID NOT NULL PRIMARY KEY, name VARCHAR(255) NOT NULL);
CREATE TABLE knowledge_triples (id UUID NOT NULL PRIMARY KEY, subject TEXT);
CREATE TABLE config (key VARCHAR(255) NOT NULL PRIMARY KEY, value JSONB NOT NULL);
"""

STUB_TABLES = (
    "audit_log",
    "code_edges",
    "code_files",
    "code_graph_nodes",
    "code_symbols",
    "embedders",
    "enrichment_queue",
    "entities",
    "entity_relations",
    "llm_profiles",
    "llm_providers",
    "llm_purpose_configs",
    "memory_crossrefs",
    "ml_profiles",
    "pipeline_failures",
    "token_blocklist",
)

TARGET_WIPE_TABLES = (
    "memory_tags",
    "messages",
    "memories",
    "conversations",
    "tags",
    "projects",
    "entities",
    "entity_relations",
    "memory_crossrefs",
    "memory_access_stats",
    "memory_relations",
    "memory_community_members",
    "memory_communities",
)


async def _admin_execute(statement: str) -> None:
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await conn.execute(statement)
    finally:
        await conn.close()


async def _drop_database(name: str) -> None:
    await _admin_execute(
        f'SELECT pg_terminate_backend(pid) FROM pg_stat_activity '
        f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
    )
    await _admin_execute(f'DROP DATABASE IF EXISTS "{name}"')


def _alembic_upgrade(dsn: str) -> None:
    env = {**os.environ, "DATABASE_URL": dsn.replace("postgresql://", "postgresql+asyncpg://")}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed for {dsn}:\n{result.stdout}\n{result.stderr}"
        )


@pytest_asyncio.fixture(scope="session")
async def cutover_databases():
    await _drop_database(SOURCE_DB)
    await _drop_database(TARGET_DB)
    await _admin_execute(f'CREATE DATABASE "{SOURCE_DB}"')
    await _admin_execute(f'CREATE DATABASE "{TARGET_DB}"')

    conn = await asyncpg.connect(SOURCE_DSN)
    try:
        await conn.execute(LEGACY_DDL)
        for table in STUB_TABLES:
            await conn.execute(f'CREATE TABLE "{table}" (id BIGSERIAL PRIMARY KEY)')
    finally:
        await conn.close()

    _alembic_upgrade(TARGET_DSN)
    yield
    await _drop_database(SOURCE_DB)
    await _drop_database(TARGET_DB)


@pytest_asyncio.fixture
async def source(cutover_databases):
    conn = await asyncpg.connect(SOURCE_DSN)
    try:
        await conn.execute(
            "TRUNCATE memory_tags, messages, memories, conversations, tags, "
            "repositories, api_keys, knowledge_triples, config "
            "RESTART IDENTITY CASCADE"
        )
        await conn.execute("DELETE FROM alembic_version")
        await conn.execute(
            "INSERT INTO alembic_version (version_num) VALUES ($1)", spec.SOURCE_REVISION
        )
    finally:
        await conn.close()
    conn = await cutover_db.connect_source(SOURCE_DSN)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def target(cutover_databases):
    conn = await asyncpg.connect(TARGET_DSN)
    try:
        await conn.execute(
            "TRUNCATE " + ", ".join(TARGET_WIPE_TABLES) + " RESTART IDENTITY CASCADE"
        )
        for table in spec.CARRIED:
            await conn.execute(f'DROP TABLE IF EXISTS "{table.staging_name}"')
    finally:
        await conn.close()
    conn = await cutover_db.connect_target(TARGET_DSN)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def source_writer(source):
    """A second, writable handle on the source — the fixture connection is
    read-only at the database, which is the point of it."""
    conn = await asyncpg.connect(SOURCE_DSN)
    yield conn
    await conn.close()


# ----------------------------------------------------------------------------
# Fixture data
# ----------------------------------------------------------------------------

OLD_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
NEW_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
BARE_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
CONV_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
MSG_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")


async def seed_source(writer: asyncpg.Connection) -> None:
    """A corpus shaped to exercise every §4.1 row at once.

    The forward-pointing supersession is the load-bearing part: OLD_ID is
    inserted first and points at NEW_ID, which is inserted after it. A
    row-at-a-time or batched load fails on exactly that pair.
    """
    await writer.execute(
        "INSERT INTO tags (id, name, category) VALUES (7, 'postgres', 'tech'), "
        "(8, 'Rust', NULL)"
    )
    await writer.execute("SELECT setval('tags_id_seq', 8, true)")

    await writer.execute(
        """
        INSERT INTO memories (
            id, content, source, source_agent, memory_type, importance, metadata,
            created_at, updated_at, expires_at, is_archived, llm_classified_type,
            llm_summary, llm_emotions, llm_flags, project, status, superseded_by,
            technologies, confidence
        ) VALUES
        ($1, 'we used sqlite', 'mcp', 'claude-code', 'decision', 0.9,
         '{"seq": 1, "prec": 1.000000000000000000000000001}'::jsonb,
         '2020-06-01T00:00:00Z', '2020-06-02T00:00:00Z', NULL, false, 'decision',
         'old summary', '{"joy": 0.1}'::jsonb, '["stale"]'::jsonb, 'homelab',
         'superseded', $2, '{sqlite}', 0.55),
        ($2, 'we replaced sqlite with postgres', 'api', NULL, NULL, 0.5,
         '{"seq": 2}'::jsonb,
         '2021-01-01T00:00:00Z', '2021-01-01T00:00:00Z',
         '2099-01-01T00:00:00Z', false, NULL, NULL,
         '{"relief": 0.9}'::jsonb, NULL, 'homelab', 'active', NULL, '{postgres}', 0.75),
        ($3, 'unrelated note', 'mcp', 'codex', 'fact', 0.2, '{}'::jsonb,
         '2022-03-03T00:00:00Z', '2022-03-04T00:00:00Z', NULL, true, 'fact',
         NULL, NULL, NULL, 'default', 'active', NULL, '{}', 0.75)
        """,
        OLD_ID,
        NEW_ID,
        BARE_ID,
    )
    await writer.execute(
        "INSERT INTO memory_tags (memory_id, tag_id) VALUES ($1, 7), ($2, 8)",
        OLD_ID,
        NEW_ID,
    )
    await writer.execute(
        "INSERT INTO conversations (id, title, is_archived, created_at, updated_at) "
        "VALUES ($1, 'a chat', false, '2023-01-01T00:00:00Z', '2023-01-02T00:00:00Z')",
        CONV_ID,
    )
    await writer.execute(
        "INSERT INTO messages (id, conversation_id, role, content, context, created_at) "
        "VALUES ($1, $2, 'user', 'hello', '{\"k\": 1}'::jsonb, '2023-01-01T00:00:00Z')",
        MSG_ID,
        CONV_ID,
    )
    await writer.execute(
        "INSERT INTO repositories (id, name, url, local_path, provider, "
        "default_branch, auth_token_ref, auto_sync) VALUES "
        "($1, 'darkmem', 'https://example.invalid/darkmem', '/srv/darkmem', "
        "'github', 'main', 'repo_token:darkmem', true)",
        uuid.uuid4(),
    )


# ----------------------------------------------------------------------------
# Step 1 — the source guards and the banned constructs
# ----------------------------------------------------------------------------

PACKAGE_SOURCES = sorted((SCRIPTS_DIR / "cutover").glob("*.py"))


def test_package_registers_no_asyncpg_type_codec():
    """Constraint 9. Under asyncpg's default codecs a jsonb value round-trips as
    an opaque str; install a json codec and a numeric past a double's precision
    comes back rounded."""
    for path in PACKAGE_SOURCES:
        text = path.read_text(encoding="utf-8")
        assert "set_type_codec" not in text, path
        assert "json.loads(" not in text, path


def test_package_contains_no_varchar_width_cast():
    """Constraint 4. An over-length value raises string_data_right_truncation on
    a plain insert — loud. An explicit ::varchar(n) cast silently truncates."""
    for path in PACKAGE_SOURCES:
        text = path.read_text(encoding="utf-8").lower()
        assert "::varchar(" not in text, path
        assert "as varchar(" not in text, path


def test_package_never_coalesces_origin_key():
    """Constraint 5. COUNT(DISTINCT x) skips NULLs, so a carried memory
    contributes zero distinct origins. Any COALESCE here mints one."""
    for path in PACKAGE_SOURCES:
        text = path.read_text(encoding="utf-8").lower().replace("\n", " ")
        assert "coalesce(origin_key" not in text, path


def test_memories_load_is_one_statement():
    sql = transform.load_sql(spec.MEMORIES)
    assert sql.count("INSERT INTO") == 1
    assert ";" not in sql
    assert "cutover_stage_memories" in sql
    assert '"search_vector"' not in sql


def test_load_names_every_column_on_both_sides():
    sql = transform.load_sql(spec.MEMORIES)
    assert "SELECT *" not in sql
    for column in spec.MEMORIES.columns:
        assert f'"{column.target}"' in sql
    assert '"origin_key"' in sql
    assert '"technologies"' in sql


async def test_source_connection_is_read_only(source):
    with pytest.raises(asyncpg.PostgresError):
        await source.execute("INSERT INTO tags (name) VALUES ('nope')")


def test_same_database_dsn_is_refused():
    with pytest.raises(CutoverError, match="same database"):
        cutover_db.assert_distinct_databases(SOURCE_DSN, SOURCE_DSN)


def test_production_source_name_is_refused():
    with pytest.raises(CutoverError, match="darkmem"):
        cutover_db.assert_source_not_production(_dsn_for("darkmem"))


def test_distinct_databases_pass_the_dsn_guard():
    cutover_db.assert_distinct_databases(SOURCE_DSN, TARGET_DSN)


async def test_same_live_database_is_refused(cutover_databases):
    """Two DSNs can spell one database differently, which the string comparison
    cannot see."""
    first = await asyncpg.connect(SOURCE_DSN)
    second = await asyncpg.connect(SOURCE_DSN.replace("localhost", "127.0.0.1"))
    try:
        with pytest.raises(CutoverError, match="same live database"):
            await cutover_db.assert_distinct_live_databases(first, second)
    finally:
        await first.close()
        await second.close()


# ----------------------------------------------------------------------------
# Step 2 — the pre-flight, one injected defect at a time
# ----------------------------------------------------------------------------


def _check(report: preflight.PreflightReport, name: str) -> preflight.Check:
    for check in report.checks:
        if check.name == name:
            return check
    raise AssertionError(f"no check named {name}: {[c.name for c in report.checks]}")


async def test_preflight_passes_on_a_clean_pair(source, target, source_writer):
    await seed_source(source_writer)
    report = await preflight.run_preflight(source, target)
    assert report.passed, report.failures
    assert _check(report, "source_carried_row_counts").detail["counts"] == {
        "tags": 2,
        "memories": 3,
        "memory_tags": 2,
        "conversations": 1,
        "messages": 1,
    }


async def test_preflight_rejects_a_pre_0006_source(source, target, source_writer):
    await source_writer.execute("UPDATE alembic_version SET version_num = '0005'")
    report = await preflight.run_preflight(source, target)
    assert not _check(report, "source_revision_is_0006").passed


async def test_preflight_rejects_a_foreign_extra_table(source, target, source_writer):
    await source_writer.execute("CREATE TABLE memories__backup (id UUID)")
    try:
        report = await preflight.run_preflight(source, target)
        check = _check(report, "source_table_set")
        assert not check.passed
        assert check.detail["foreign"] == ["memories__backup"]
    finally:
        await source_writer.execute("DROP TABLE memories__backup")


async def test_preflight_accepts_per_fingerprint_child_tables(
    source, target, source_writer
):
    """A.1 was extracted from a database with zero registered fingerprints, so
    set equality would false-abort on every genuine source."""
    await source_writer.execute("CREATE TABLE memory_embeddings__abc123 (id UUID)")
    await source_writer.execute("CREATE TABLE entity_embedding_cache__abc123 (id UUID)")
    try:
        report = await preflight.run_preflight(source, target)
        check = _check(report, "source_table_set")
        assert check.passed, check.detail
        assert set(check.detail["child_tables"]) == {
            "memory_embeddings__abc123",
            "entity_embedding_cache__abc123",
        }
    finally:
        await source_writer.execute("DROP TABLE memory_embeddings__abc123")
        await source_writer.execute("DROP TABLE entity_embedding_cache__abc123")


async def test_preflight_rejects_a_missing_a1_table(source, target, source_writer):
    await source_writer.execute("ALTER TABLE token_blocklist RENAME TO token_blocklist_x")
    try:
        report = await preflight.run_preflight(source, target)
        check = _check(report, "source_table_set")
        assert not check.passed
        assert check.detail["missing"] == ["token_blocklist"]
    finally:
        await source_writer.execute(
            "ALTER TABLE token_blocklist_x RENAME TO token_blocklist"
        )


async def test_preflight_rejects_a_non_empty_target(source, target, source_writer):
    await seed_source(source_writer)
    await target.execute("INSERT INTO tags (name) VALUES ('already here')")
    report = await preflight.run_preflight(source, target)
    check = _check(report, "target_carried_tables_empty")
    assert not check.passed
    assert check.detail["non_empty"] == {"tags": 1}


async def test_preflight_reports_target_baseline_revision(source, target):
    report = await preflight.run_preflight(source, target)
    check = _check(report, "target_revision_is_baseline")
    assert check.passed, check.detail
    assert check.detail["expected"] == preflight.baseline_revision()


async def test_preflight_catches_a_superseded_row_without_a_pointer(
    source, target, source_writer
):
    await seed_source(source_writer)
    # The source CHECK forbids this shape, so it has to be dropped to inject
    # it — a dump is not the schema, which is why the assertion exists.
    await source_writer.execute(
        "ALTER TABLE memories DROP CONSTRAINT chk_superseded_has_pointer"
    )
    try:
        await source_writer.execute(
            "UPDATE memories SET superseded_by = NULL WHERE id = $1", OLD_ID
        )
        report = await preflight.run_preflight(source, target)
        check = _check(report, "source_superseded_rows_have_pointer")
        assert not check.passed
        assert check.detail["offending_ids"] == [str(OLD_ID)]
    finally:
        await source_writer.execute("TRUNCATE memories CASCADE")
        await source_writer.execute(
            "ALTER TABLE memories ADD CONSTRAINT chk_superseded_has_pointer "
            "CHECK (status != 'superseded' OR superseded_by IS NOT NULL)"
        )


async def test_preflight_catches_a_dangling_pointer(source, target, source_writer):
    await seed_source(source_writer)
    await source_writer.execute(
        "ALTER TABLE memories DROP CONSTRAINT fk_memories_superseded_by"
    )
    try:
        ghost = uuid.uuid4()
        await source_writer.execute(
            "UPDATE memories SET superseded_by = $1 WHERE id = $2", ghost, OLD_ID
        )
        report = await preflight.run_preflight(source, target)
        check = _check(report, "source_superseded_by_resolves")
        assert not check.passed
        assert check.detail["offending"] == [
            {"id": str(OLD_ID), "superseded_by": str(ghost)}
        ]
    finally:
        await source_writer.execute("TRUNCATE memories CASCADE")
        await source_writer.execute(
            "ALTER TABLE memories ADD CONSTRAINT fk_memories_superseded_by "
            "FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL"
        )


async def test_preflight_catches_a_lineage_cycle(source, target, source_writer):
    await seed_source(source_writer)
    await source_writer.execute(
        "UPDATE memories SET status = 'superseded', superseded_by = $1 WHERE id = $2",
        OLD_ID,
        NEW_ID,
    )
    report = await preflight.run_preflight(source, target)
    check = _check(report, "source_superseded_by_acyclic")
    assert not check.passed
    assert set(check.detail["offending_ids"]) == {str(OLD_ID), str(NEW_ID)}


@pytest.mark.parametrize("table", ("api_keys", "knowledge_triples"))
async def test_preflight_requires_empty_unwired_tables(
    source, target, source_writer, table
):
    assert table in spec.SOURCE_MUST_BE_EMPTY
    if table == "api_keys":
        await source_writer.execute(
            "INSERT INTO api_keys (id, name) VALUES ($1, 'x')", uuid.uuid4()
        )
    else:
        await source_writer.execute(
            "INSERT INTO knowledge_triples (id, subject) VALUES ($1, 'x')", uuid.uuid4()
        )
    report = await preflight.run_preflight(source, target)
    check = _check(report, f"source_{table}_is_empty")
    assert not check.passed
    assert check.detail["count"] == 1


async def test_preflight_reports_memory_type_histogram_and_stops_on_a_stale_value(
    source, target, source_writer
):
    """MEMORY_TYPES changed under this column and the target has no CHECK.
    Rewriting a user-visible classification is the harm the task exists to
    prevent, so the run stops and the operator decides."""
    await seed_source(source_writer)
    await source_writer.execute(
        "UPDATE memories SET memory_type = 'insight' WHERE id = $1", BARE_ID
    )
    report = await preflight.run_preflight(source, target)
    check = _check(report, "source_memory_type_in_vocabulary")
    assert not check.passed
    assert check.detail["out_of_vocabulary"] == {"insight": 1}
    assert check.detail["histogram"]["NULL"] == 1


async def test_preflight_catches_orphan_child_rows(source, target, source_writer):
    await seed_source(source_writer)
    await source_writer.execute(
        "ALTER TABLE memory_tags DROP CONSTRAINT memory_tags_tag_id_fkey"
    )
    try:
        await source_writer.execute("UPDATE memory_tags SET tag_id = 999")
        report = await preflight.run_preflight(source, target)
        assert not _check(report, "source_memory_tags_resolve").passed
    finally:
        await source_writer.execute("UPDATE memory_tags SET tag_id = 7")
        await source_writer.execute(
            "ALTER TABLE memory_tags ADD CONSTRAINT memory_tags_tag_id_fkey "
            "FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE"
        )


async def test_repository_inventory_carries_no_secret(source, target, source_writer):
    await seed_source(source_writer)
    report = await preflight.run_preflight(source, target)
    check = _check(report, "source_repository_inventory")
    (row,) = check.detail["repositories"]
    assert row["name"] == "darkmem"
    assert row["has_auth_token"] is True
    assert row["auto_sync"] is True
    assert "auth_token_ref" not in row
    assert "repo_token:darkmem" not in repr(report.to_dict())


# ----------------------------------------------------------------------------
# Step 4 — the transform, the load and the two verification legs
# ----------------------------------------------------------------------------


async def _run(source, target, **kwargs) -> CutoverResult:
    return await run_cutover(source, target, **kwargs)


async def test_carried_set_lands_column_by_column(source, target, source_writer):
    await seed_source(source_writer)
    result = await _run(source, target)

    assert result.staged == {
        "tags": 2,
        "memories": 3,
        "memory_tags": 2,
        "conversations": 1,
        "messages": 1,
    }

    old = await target.fetchrow("SELECT * FROM memories WHERE id = $1", OLD_ID)
    assert old["content"] == "we used sqlite"
    assert old["source"] == "mcp"
    assert old["source_agent"] == "claude-code"
    assert old["memory_type"] == "decision"
    assert old["importance"] == pytest.approx(0.9)
    assert old["project"] == "homelab"
    assert old["is_archived"] is False
    # The four llm_* renames.
    assert old["classified_type"] == "decision"
    assert old["summary"] == "old summary"
    assert old["emotions"] == '{"joy": 0.1}'
    assert old["flags"] == '["stale"]'
    # Lineage verbatim, including the forward reference.
    assert old["status"] == "superseded"
    assert old["superseded_by"] == NEW_ID
    # Transform-supplied.
    assert old["origin_key"] is None
    assert old["technologies"] == []
    assert old["search_vector"] is not None

    new = await target.fetchrow("SELECT * FROM memories WHERE id = $1", NEW_ID)
    assert new["memory_type"] is None
    assert new["expires_at"] is not None
    assert new["classified_type"] is None
    assert new["emotions"] == '{"relief": 0.9}'

    assert await target.fetchval("SELECT count(*) FROM memory_tags") == 2
    assert await target.fetchval("SELECT count(*) FROM messages") == 1
    assert (
        await target.fetchval("SELECT category FROM tags WHERE id = 8")
    ) is None


async def test_created_and_updated_at_carry_verbatim(source, target, source_writer):
    """The 90-day supersession window and the (created_at, id) tie-break both
    read created_at, and touch_updated_at is BEFORE UPDATE only."""
    await seed_source(source_writer)
    before = await source.fetch("SELECT id, created_at, updated_at FROM memories ORDER BY id")
    await _run(source, target)
    after = await target.fetch("SELECT id, created_at, updated_at FROM memories ORDER BY id")
    assert [dict(r) for r in before] == [dict(r) for r in after]


async def test_jsonb_metadata_survives_byte_for_byte(source, target, source_writer):
    await seed_source(source_writer)
    before = await source.fetchval(
        "SELECT metadata::text FROM memories WHERE id = $1", OLD_ID
    )
    await _run(source, target)
    after = await target.fetchval(
        "SELECT metadata::text FROM memories WHERE id = $1", OLD_ID
    )
    assert before == after
    assert "1.000000000000000000000000001" in after


async def test_projects_is_seeded_from_the_carried_rows(source, target, source_writer):
    await seed_source(source_writer)
    await _run(source, target)
    names = [r["name"] for r in await target.fetch("SELECT name FROM projects ORDER BY 1")]
    assert names == ["default", "homelab"]


async def test_tag_sequence_is_advanced_past_the_carried_ids(
    source, target, source_writer
):
    """Without the setval the first tag created after the cutover collides on
    the primary key — after verification is already green."""
    await seed_source(source_writer)
    await _run(source, target)
    new_id = await target.fetchval(
        "INSERT INTO tags (name) VALUES ('fresh') RETURNING id"
    )
    assert new_id > 8


async def test_verification_report_carries_measured_values(
    source, target, source_writer
):
    await seed_source(source_writer)
    result = await _run(source, target)
    assert result.source_vs_staging["problems"] == []
    assert result.staging_vs_target["problems"] == []
    assert result.positive_assertions["measured"]["total"] == 3
    assert result.positive_assertions["measured"]["origin_key_not_null"] == 0
    assert result.post_seed["measured"]["max_tag_id"] == 8
    memories = result.source_vs_staging["source"]["memories"]
    assert memories["status_breakdown"] == {"active": 2, "superseded": 1}
    assert memories["lineage_pairs"] is not None


async def test_snapshot_captures_the_eleven_columns(
    source, target, source_writer, tmp_path
):
    await seed_source(source_writer)
    await _run(source, target)
    path = tmp_path / "snapshot.jsonl"
    written = await write_snapshot(target, path)
    assert written == 3
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 3
    row = json.loads(lines[0])
    assert set(row) == set(spec.SNAPSHOT_COLUMNS)


async def test_a_second_run_against_a_loaded_target_refuses(
    source, target, source_writer
):
    await seed_source(source_writer)
    await _run(source, target)
    with pytest.raises(CutoverError, match="target_carried_tables_empty"):
        await _run(source, target)
    assert await target.fetchval("SELECT count(*) FROM memories") == 3


# ----------------------------------------------------------------------------
# Ruling 1 — the ORDER of the two legs, proven directly
# ----------------------------------------------------------------------------


async def test_source_to_staging_parity_runs_before_any_carried_write(
    source, target, source_writer, monkeypatch
):
    """Leg one must gate the first carried-table write. A defect on the
    source-to-staging hop lands identically in staging and in the target, so
    every later check agrees with itself and passes."""
    loads: list[str] = []
    real_load = transform.load_table

    async def spy(conn, table):
        loads.append(table.name)
        await real_load(conn, table)

    monkeypatch.setattr(transform, "load_table", spy)

    real_compare = verify.compare_aggregates
    calls = {"n": 0}

    def failing_first(left, right, a, b):
        calls["n"] += 1
        if calls["n"] == 1:
            return ["injected source/staging mismatch"]
        return real_compare(left, right, a, b)

    monkeypatch.setattr(verify, "compare_aggregates", failing_first)

    await seed_source(source_writer)
    with pytest.raises(CutoverError, match="source-to-staging parity failed"):
        await _run(source, target)

    assert loads == []
    for table in spec.CARRIED:
        assert await target.fetchval(f'SELECT count(*) FROM "{table.name}"') == 0


async def test_staging_to_target_parity_runs_before_the_setval(
    source, target, source_writer, monkeypatch
):
    """Leg two must run inside the load transaction and ahead of the setval.
    setval is non-transactional and is not rolled back, so an unchanged
    sequence is the proof that the abort happened first."""
    before = await target.fetchrow("SELECT last_value, is_called FROM tags_id_seq")

    real_compare = verify.compare_aggregates
    calls = {"n": 0}

    def failing_second(left, right, a, b):
        calls["n"] += 1
        if calls["n"] == 2:
            return ["injected staging/target mismatch"]
        return real_compare(left, right, a, b)

    monkeypatch.setattr(verify, "compare_aggregates", failing_second)

    await seed_source(source_writer)
    with pytest.raises(CutoverError, match="staging-to-target verification failed"):
        await _run(source, target)

    after = await target.fetchrow("SELECT last_value, is_called FROM tags_id_seq")
    assert dict(after) == dict(before)
    for table in spec.CARRIED:
        assert await target.fetchval(f'SELECT count(*) FROM "{table.name}"') == 0
    assert await target.fetchval("SELECT count(*) FROM projects") == 0


async def test_a_value_level_corruption_aborts_the_load(
    source, target, source_writer, monkeypatch
):
    """A column-to-column misassignment is invisible to a count: both columns
    are text, both non-empty, and the row count is identical either way."""
    real_load_sql = transform.load_sql

    def corrupting(table):
        sql = real_load_sql(table)
        if table.name == "memories":
            return sql.replace('s."llm_summary"', 's."content"')
        return sql

    monkeypatch.setattr(transform, "load_sql", corrupting)

    await seed_source(source_writer)
    with pytest.raises(CutoverError, match="staging-to-target verification failed"):
        await _run(source, target)

    for table in spec.CARRIED:
        assert await target.fetchval(f'SELECT count(*) FROM "{table.name}"') == 0


async def test_a_null_position_swap_is_caught_by_the_sentinel(
    source, target, source_writer, monkeypatch
):
    """Measured: two tables differing only in which row holds the NULL produce
    the same unguarded checksum, the same NULL count and the same distinct
    count. Three covers fail at once; the COALESCE sentinel is what sees it."""
    real_load_sql = transform.load_sql

    def swapping(table):
        sql = real_load_sql(table)
        if table.name == "memories":
            return sql.replace(
                's."llm_classified_type"',
                "CASE WHEN s.llm_classified_type IS NULL THEN 'decision' "
                "WHEN s.id = $$" + str(OLD_ID) + "$$::uuid THEN NULL "
                "ELSE s.llm_classified_type END",
            )
        return sql

    monkeypatch.setattr(transform, "load_sql", swapping)

    await seed_source(source_writer)
    with pytest.raises(CutoverError, match="staging-to-target verification failed"):
        await _run(source, target)


async def test_the_coalesce_sentinel_is_what_makes_the_checksum_positional(target):
    """Break the guard on purpose: without the sentinel, a NULL-position swap
    defeats the checksum, the NULL count and the distinct count at the same
    time, and an all-NULL column checksums to SQL NULL — which compares equal
    to the other side's NULL client-side."""
    await target.execute(
        "CREATE TEMP TABLE swap_a (id INT, v TEXT); "
        "CREATE TEMP TABLE swap_b (id INT, v TEXT); "
        "INSERT INTO swap_a VALUES (1, 'x'), (2, NULL), (3, 'y'); "
        "INSERT INTO swap_b VALUES (1, NULL), (2, 'x'), (3, 'y')"
    )
    unguarded = "SELECT md5(string_agg(v::text, '|' ORDER BY id)) FROM {}"
    guarded = (
        "SELECT md5(string_agg(COALESCE(v::text, '"
        + spec.NULL_SENTINEL
        + "'), '|' ORDER BY id)) FROM {}"
    )
    stats = (
        "SELECT count(*) FILTER (WHERE v IS NULL) AS nulls, "
        "count(DISTINCT v) AS dist, count(*) AS n FROM {}"
    )

    assert await target.fetchval(unguarded.format("swap_a")) == await target.fetchval(
        unguarded.format("swap_b")
    )
    assert dict(await target.fetchrow(stats.format("swap_a"))) == dict(
        await target.fetchrow(stats.format("swap_b"))
    )
    assert await target.fetchval(guarded.format("swap_a")) != await target.fetchval(
        guarded.format("swap_b")
    )

    await target.execute("CREATE TEMP TABLE all_null (id INT, v TEXT)")
    await target.execute("INSERT INTO all_null VALUES (1, NULL), (2, NULL)")
    assert await target.fetchval(unguarded.format("all_null")) is None
    assert await target.fetchval(guarded.format("all_null")) is not None


async def test_dropping_the_pointer_hits_the_check_constraint(
    source, target, source_writer, monkeypatch
):
    """Layer 2. Even with the pre-flight wrong, a transform that dropped the
    pointer cannot commit — the loudness is structural."""
    real_load_sql = transform.load_sql

    def coercing(table):
        sql = real_load_sql(table)
        if table.name == "memories":
            return sql.replace('s."superseded_by"', "CAST(NULL AS uuid)")
        return sql

    monkeypatch.setattr(transform, "load_sql", coercing)

    await seed_source(source_writer)
    with pytest.raises(asyncpg.CheckViolationError, match="chk_superseded_has_pointer"):
        await _run(source, target)
    assert await target.fetchval("SELECT count(*) FROM memories") == 0


class _Rollback(Exception):
    pass


async def test_a_row_at_a_time_load_breaks_on_the_forward_reference(
    source, target, source_writer
):
    """The measurement behind the single-statement rule, pinned as a test so a
    later 'optimisation' into batching fails here rather than in production, on
    the one pair whose pointer happens to cross a batch boundary."""
    await seed_source(source_writer)
    row_wise = (
        "INSERT INTO memories (id, content, source, importance, metadata, "
        "created_at, updated_at, is_archived, project, status, superseded_by, "
        "technologies, confidence) "
        "SELECT id, content, source, importance, metadata, created_at, "
        "updated_at, is_archived, project, CAST(status AS memory_status), "
        "superseded_by, '{}'::text[], confidence "
        'FROM "cutover_stage_memories" WHERE id = $1'
    )
    try:
        async with target.transaction():
            await stage.stage_all(source, target)
            rows = await target.fetch(
                'SELECT id FROM "cutover_stage_memories" ORDER BY id'
            )
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                for row in rows:
                    await target.execute(row_wise, row["id"])
            raise _Rollback()
    except _Rollback:
        pass

    # And the same rows load as one statement.
    await _run(source, target)
    assert await target.fetchval("SELECT count(*) FROM memories") == 3


# ----------------------------------------------------------------------------
# Ruling 4 — --reset, the one path where the tool can destroy real data
# ----------------------------------------------------------------------------


async def test_reset_reloads_a_target_that_holds_only_the_dump(
    source, target, source_writer
):
    await seed_source(source_writer)
    await _run(source, target)
    result = await _run(source, target, reset=True)
    assert result.reset["guard"]["total"] == 0
    assert result.reset["deleted"]["memories"] == 3
    assert await target.fetchval("SELECT count(*) FROM memories") == 3


# Spelled out here rather than read from spec, so narrowing the refusal list
# fails these behavioural tests instead of quietly deleting them.
CASCADING_INTO_MEMORIES = (
    "entities",
    "entity_relations",
    "memory_crossrefs",
    "memory_access_stats",
    "memory_relations",
    "memory_community_members",
)


@pytest.mark.parametrize("table", CASCADING_INTO_MEMORIES)
async def test_reset_refuses_when_a_derivation_exists(
    source, target, source_writer, table
):
    """Six base tables carry an ON DELETE CASCADE FK into memories(id), so
    deleting a memory silently deletes their rows too. The first draft of this
    guard listed two of them."""
    await seed_source(source_writer)
    await _run(source, target)
    await _seed_derivation(target, table)
    with pytest.raises(CutoverError, match="reset_derivations_absent"):
        await _run(source, target, reset=True)
    assert await target.fetchval("SELECT count(*) FROM memories") == 3


async def test_reset_refuses_when_an_embedding_partition_holds_rows(
    source, target, source_writer
):
    """Refusal trigger seven: the partition's cascade comes from the table
    template rather than the baseline, so it is invisible to a reading of
    0001_baseline.py alone."""
    await seed_source(source_writer)
    await _run(source, target)
    await target.execute(
        'CREATE TABLE "memory_embeddings__t1" (memory_id UUID PRIMARY KEY '
        "REFERENCES memories(id) ON DELETE CASCADE)"
    )
    try:
        await target.execute(
            'INSERT INTO "memory_embeddings__t1" (memory_id) VALUES ($1)', OLD_ID
        )
        with pytest.raises(CutoverError, match="memory_embeddings__t1"):
            await _run(source, target, reset=True)
        assert await target.fetchval("SELECT count(*) FROM memories") == 3
    finally:
        await target.execute('DROP TABLE "memory_embeddings__t1"')


async def test_reset_refuses_rows_the_dump_never_contained(
    source, target, source_writer
):
    """The window the first guard missed: between the transform completing and
    the backfill producing its first entity, every derivation table is empty,
    so a proxy for 'the backfill has run' never fires while users capture."""
    await seed_source(source_writer)
    await _run(source, target)
    captured = uuid.uuid4()
    await target.execute(
        "INSERT INTO memories (id, content, source, importance, metadata, project) "
        "VALUES ($1, 'captured after the cutover', 'mcp', 0.5, '{}'::jsonb, 'homelab')",
        captured,
    )
    with pytest.raises(CutoverError, match="--reset refused"):
        await _run(source, target, reset=True)
    assert await target.fetchval(
        "SELECT count(*) FROM memories WHERE id = $1", captured
    ) == 1


async def test_reset_refuses_rows_edited_since_the_dump(source, target, source_writer):
    """A post-cutover edit keeps its id, so the id-set difference cannot see it;
    the reload destroys it just the same."""
    await seed_source(source_writer)
    await _run(source, target)
    await target.execute(
        "UPDATE memories SET content = 'edited after the cutover' WHERE id = $1",
        BARE_ID,
    )
    with pytest.raises(CutoverError, match="rows edited since the dump"):
        await _run(source, target, reset=True)
    assert (
        await target.fetchval("SELECT content FROM memories WHERE id = $1", BARE_ID)
        == "edited after the cutover"
    )


async def test_reset_override_must_carry_the_exact_reported_count(
    source, target, source_writer
):
    """The count is part of the override so it cannot be pasted from a previous
    run into a situation with a different one."""
    await seed_source(source_writer)
    await _run(source, target)
    await target.execute(
        "INSERT INTO memories (id, content, source, importance, metadata, project) "
        "VALUES ($1, 'captured after the cutover', 'mcp', 0.5, '{}'::jsonb, 'homelab')",
        uuid.uuid4(),
    )
    with pytest.raises(CutoverError, match="--reset refused"):
        await _run(source, target, reset=True, acknowledged_row_loss=99)
    result = await _run(source, target, reset=True, acknowledged_row_loss=1)
    assert result.reset["guard"]["total"] == 1
    assert await target.fetchval("SELECT count(*) FROM memories") == 3


async def test_reset_leaves_projects_and_reports_the_stale_row(
    source, target, source_writer
):
    await seed_source(source_writer)
    await _run(source, target)
    await target.execute("INSERT INTO projects (name) VALUES ('retired')")
    result = await _run(source, target, reset=True)
    assert result.post_seed["measured"]["projects_without_memories"] == ["retired"]
    assert await target.fetchval(
        "SELECT count(*) FROM projects WHERE name = 'retired'"
    ) == 1


async def _seed_derivation(target: asyncpg.Connection, table: str) -> None:
    if table == "entities":
        await target.execute(
            "INSERT INTO entities (name, entity_type, memory_ids) "
            "VALUES ('sqlite', 'tool', ARRAY[$1]::uuid[])",
            OLD_ID,
        )
    elif table == "entity_relations":
        source_entity = await target.fetchval(
            "INSERT INTO entities (name, entity_type) VALUES ('a', 'tool') RETURNING id"
        )
        target_entity = await target.fetchval(
            "INSERT INTO entities (name, entity_type) VALUES ('b', 'tool') RETURNING id"
        )
        await target.execute(
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, "
            "rel_type, memory_ids) VALUES ($1, $2, 'REPLACES', ARRAY[$3]::uuid[])",
            source_entity,
            target_entity,
            OLD_ID,
        )
    elif table == "memory_crossrefs":
        await target.execute(
            "INSERT INTO memory_crossrefs (memory_id, related_memory_id, score) "
            "VALUES ($1, $2, 0.9)",
            OLD_ID,
            NEW_ID,
        )
    elif table == "memory_access_stats":
        await target.execute(
            "INSERT INTO memory_access_stats (memory_id) VALUES ($1)", OLD_ID
        )
    elif table == "memory_relations":
        await target.execute(
            "INSERT INTO memory_relations (id, source_memory_id, target_memory_id, "
            "project, rel_type) VALUES ($1, $2, $3, 'homelab', 'RELATED_TO')",
            uuid.uuid4(),
            OLD_ID,
            NEW_ID,
        )
    elif table == "memory_community_members":
        community = uuid.uuid4()
        await target.execute(
            "INSERT INTO memory_communities (id, project, label) "
            "VALUES ($1, 'homelab', 'c')",
            community,
        )
        await target.execute(
            "INSERT INTO memory_community_members (community_id, memory_id) "
            "VALUES ($1, $2)",
            community,
            OLD_ID,
        )
    else:  # pragma: no cover - the parametrisation is closed
        raise AssertionError(f"no derivation seed for {table}")


# ----------------------------------------------------------------------------
# The command line
# ----------------------------------------------------------------------------


def test_cli_refuses_a_production_source_before_connecting(tmp_path):
    """The refusal is pure string work on the DSN, so the real database is
    never opened — not even to read."""
    code = cli_main(
        [
            "--source-dsn",
            _dsn_for("darkmem"),
            "--target-dsn",
            TARGET_DSN,
            "--report-dir",
            str(tmp_path),
        ]
    )
    assert code == 1
    assert list(tmp_path.iterdir()) == []


async def test_cli_runs_preflight_then_the_full_transform(
    source, target, source_writer, tmp_path
):
    await seed_source(source_writer)
    argv = [
        "--source-dsn",
        SOURCE_DSN,
        "--target-dsn",
        TARGET_DSN,
        "--report-dir",
        str(tmp_path),
    ]
    assert await cli_amain([*argv, "--preflight-only"]) == 0
    assert len(list(tmp_path.glob("cutover-preflight-*.json"))) == 1

    assert await cli_amain(argv) == 0
    (verification,) = list(tmp_path.glob("cutover-verification-*.json"))
    (snapshot,) = list(tmp_path.glob("cutover-snapshot-*.jsonl"))
    payload = json.loads(verification.read_text(encoding="utf-8"))
    assert payload["source_vs_staging"]["problems"] == []
    assert payload["staging_vs_target"]["problems"] == []
    assert len(snapshot.read_text(encoding="utf-8").strip().splitlines()) == 3
    assert await target.fetchval("SELECT count(*) FROM memories") == 3
    assert await target.fetchval(
        "SELECT count(*) FROM pg_class WHERE relname LIKE 'cutover_stage_%'"
    ) == 0


# ----------------------------------------------------------------------------
# The bucket enumeration — nothing carried by accident, nothing resurrected
# ----------------------------------------------------------------------------


def test_every_source_table_has_exactly_one_disposition():
    carried = {t.name for t in spec.CARRIED}
    rebuilt = set(spec.REBUILT_TABLES)
    dropped = set(spec.DROPPED_TABLES)
    assert len(carried) == 5
    assert len(rebuilt) == 10
    assert len(dropped) == 11
    assert carried & rebuilt == set()
    assert carried & dropped == set()
    assert rebuilt & dropped == set()
    assert carried | rebuilt | dropped == set(spec.SOURCE_TABLES_A1)


def test_config_carries_nothing():
    assert "config" in spec.DROPPED_TABLES
    assert "config" not in {t.name for t in spec.CARRIED}


def test_reset_refusal_list_covers_seven_triggers():
    assert set(spec.RESET_REFUSAL_TABLES) == set(CASCADING_INTO_MEMORIES)
    assert len(spec.RESET_REFUSAL_TABLES) == 6
    assert spec.RESET_REFUSAL_TABLE_PREFIX == "memory_embeddings__"


def test_snapshot_covers_eleven_columns():
    assert len(spec.SNAPSHOT_COLUMNS) == 11
