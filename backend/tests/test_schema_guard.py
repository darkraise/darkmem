"""The boot check that refuses to serve against a drifted schema.

Measured cause, 2026-08-17: until 2026-09-28 a schema change regenerated
``0001_baseline.py`` in place, so the revision id never moved and
``alembic upgrade head`` is a no-op on a database built from an older copy — the
deploy reports a clean migration while the code runs against a schema it lacks.
Production drifted five columns that way and ``article_synthesis`` died on every
scheduled run for days. The baseline is now permanent; the two tests below keep
it that way.
"""
from __future__ import annotations

import hashlib

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app import schema_guard


def test_the_baseline_it_hashes_actually_exists():
    """A guard that hashes a missing file would raise at boot rather than check
    anything, and the path differs between the repo and the image (`/app`), so
    it is asserted rather than assumed."""
    assert schema_guard.BASELINE.exists(), schema_guard.BASELINE
    assert schema_guard.BASELINE.name == "0001_baseline.py"


def test_the_baseline_is_never_regenerated():
    """Every deployed database is stamped with this digest. Editing the file in
    place — even its docstring — moves it and makes every deployed app refuse to
    boot. A schema change is a new revision chained after ``0001``."""
    assert schema_guard.baseline_sha() == schema_guard.FROZEN_BASELINE_SHA


def test_the_revision_chain_is_linear_from_the_baseline():
    """Two lanes that each add a revision off the same parent leave two heads,
    and ``alembic upgrade head`` then refuses to run at boot. Rebase the later
    revision's ``down_revision`` onto the other."""
    versions = schema_guard.BASELINE.parent
    config = Config()
    config.set_main_option("script_location", str(versions.parent))
    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1, script.get_heads()
    assert script.get_bases() == ["0001"]


def test_baseline_sha_is_the_files_own_digest():
    assert schema_guard.baseline_sha() == hashlib.sha256(
        schema_guard.BASELINE.read_bytes()
    ).hexdigest()


async def test_a_fresh_database_is_stamped_and_admitted(session):
    """First boot: nothing stored. It adopts the schema that is actually there,
    which is the only honest thing it can do — it cannot know retroactively
    whether that schema was current."""
    await session.execute(
        text("DELETE FROM config WHERE key = :k"), {"k": schema_guard.CONFIG_KEY}
    )
    await session.commit()

    code = await schema_guard.evaluate(await session.connection())
    assert code == 0

    stored = (
        await session.execute(
            text("SELECT value->>'sha' FROM config WHERE key = :k"),
            {"k": schema_guard.CONFIG_KEY},
        )
    ).scalar()
    assert stored == schema_guard.baseline_sha()


async def test_an_unchanged_baseline_is_admitted(session):
    await schema_guard.evaluate(await session.connection())          # stamp
    assert await schema_guard.evaluate(await session.connection()) == 0   # and again


async def test_a_regenerated_baseline_is_REFUSED(session):
    """The whole point. A mismatch must fail closed, because serving on is
    quiet and was measured to cost days of a dead job while refusing is loud."""
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (:k, jsonb_build_object('sha', CAST(:v AS text))) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": schema_guard.CONFIG_KEY, "v": "a" * 64},
    )
    await session.commit()

    assert await schema_guard.evaluate(await session.connection()) == 1


async def test_there_is_no_override_flag(session, monkeypatch):
    """An env var that skipped this would be reached for at exactly the moment
    it is protecting someone. If one is ever added, this test says so."""
    monkeypatch.setenv("DARKMEM_ALLOW_SCHEMA_DRIFT", "1")
    monkeypatch.setenv("DARKMEM_SKIP_SCHEMA_CHECK", "1")
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (:k, jsonb_build_object('sha', CAST(:v AS text))) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": schema_guard.CONFIG_KEY, "v": "b" * 64},
    )
    await session.commit()

    assert await schema_guard.evaluate(await session.connection()) == 1


