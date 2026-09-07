"""The projects registry's seed of the one `kind='personal'` space."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_the_personal_project_is_seeded_idempotently(session):
    from app.services.project_registry import seed_personal_project

    await seed_personal_project(session)
    await seed_personal_project(session)
    rows = (await session.execute(text(
        "SELECT name, kind FROM projects WHERE kind = 'personal'"
    ))).all()
    assert [(r.name, r.kind) for r in rows] == [("notes", "personal")]


@pytest.mark.asyncio
async def test_the_seed_repairs_a_row_a_capture_created_first(session):
    """`project_registry.register` runs on every capture and inserts with
    `ON CONFLICT DO NOTHING`, so a memory captured into `notes` before the
    first boot mints the row with kind defaulting to 'project'. A
    DO-NOTHING seed would leave it wrong forever."""
    from app.services.project_registry import register, seed_personal_project

    await register(session, "notes")
    assert await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'notes'")
    ) == "project"

    await seed_personal_project(session)
    assert await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'notes'")
    ) == "personal"
