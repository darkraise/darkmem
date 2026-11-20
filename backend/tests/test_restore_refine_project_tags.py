"""The lost project-tag script, against real committed rows."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories.relational import PostgresMemoryRepository
from app.services import dream_journal as journal
from app.services import events as events_module
from app.utils.ids import new_id
from scripts import restore_refine_project_tags as script


@pytest.fixture
async def committing(setup_database):
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            for statement in (
                "DELETE FROM memories WHERE project LIKE 'rtag-%'",
                "DELETE FROM tags WHERE name LIKE 'rtag-%' "
                "OR name LIKE 'project/rtag-%'",
            ):
                await cleanup.execute(text(statement))
            await cleanup.commit()
        await engine.dispose()


async def _refined(factory, project, *, before_tags, current_tags):
    memory_id = new_id()
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO memories (id, content, source, project) "
                "VALUES (CAST(:id AS uuid), 'the sweeper runs hourly', 'api', :project)"
            ),
            {"id": str(memory_id), "project": project},
        )
        await PostgresMemoryRepository(session).set_tags(memory_id, current_tags)
        await events_module.record_event(
            session,
            event_type=journal.EVENT_TYPE,
            object_type=journal.OBJECT_TYPE,
            object_id=memory_id,
            project=project,
            payload={
                "action": journal.ACTION_REFINE,
                "before": {"summary": None, "tags": before_tags},
                "after": {"summary": "s", "tags": current_tags},
                "fields": ["summary", "tags"],
                "detector": journal.DETECTOR,
                "cycle_id": str(new_id()),
            },
        )
        await session.commit()
    return str(memory_id)


async def _tags(factory, memory_id) -> list[str]:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT t.name FROM memory_tags mt JOIN tags t ON t.id = mt.tag_id "
                "WHERE mt.memory_id = CAST(:id AS uuid) ORDER BY t.name"
            ),
            {"id": memory_id},
        )
        return list(result.scalars().all())


@pytest.fixture
async def lost(committing):
    project = f"rtag-{new_id().hex[:12]}"
    alpha = f"project/{project}"
    first = await _refined(
        committing, project, before_tags=[alpha, "rtag-x"], current_tags=["rtag-x"]
    )
    second = await _refined(
        committing, project, before_tags=[alpha], current_tags=["rtag-y"]
    )
    kept = await _refined(
        committing, project, before_tags=[alpha], current_tags=[alpha, "rtag-z"]
    )
    return committing, alpha, first, second, kept


async def test_dry_run_lists_lost_project_tags(lost, capsys):
    factory, alpha, first, second, kept = lost

    code = await script.run(settings.test_database_url, apply=False)

    assert code == 0
    lines = capsys.readouterr().out.splitlines()
    assert sorted(lines[:-1]) == sorted([f"{first}\t{alpha}", f"{second}\t{alpha}"])
    assert lines[-1] == "memories: 2"
    assert await _tags(factory, first) == ["rtag-x"]
    assert await _tags(factory, second) == ["rtag-y"]


async def test_apply_restores_only_the_lost_project_tags(lost, capsys):
    factory, alpha, first, second, kept = lost

    assert await script.run(settings.test_database_url, apply=True) == 0
    capsys.readouterr()

    assert await _tags(factory, first) == sorted([alpha, "rtag-x"])
    assert await _tags(factory, second) == sorted([alpha, "rtag-y"])
    assert await _tags(factory, kept) == sorted([alpha, "rtag-z"])

    assert await script.run(settings.test_database_url, apply=True) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "memories: 0"


def test_script_refuses_production_without_the_flag(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/darkmem")

    def no_connection(*args, **kwargs):
        raise AssertionError("the script connected before refusing")

    monkeypatch.setattr(script, "create_async_engine", no_connection)

    assert script.main(["--apply"]) == 2
    assert "--i-am-the-owner" in capsys.readouterr().err
