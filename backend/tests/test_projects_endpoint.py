import pytest

from app.models.memory import Memory


async def _seed(session, *rows: tuple[str, str]) -> None:
    for content, project in rows:
        session.add(Memory(content=content, source="test", project=project))
    await session.flush()


@pytest.mark.asyncio
async def test_list_projects_requires_auth(client):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_lists_distinct_projects_busiest_first(
    client, auth_headers, session
):
    await _seed(
        session,
        ("a", "alpha"),
        ("b", "beta"),
        ("c", "beta"),
        ("d", "beta"),
        ("e", "alpha"),
        ("f", "gamma"),
    )

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200

    body = resp.json()
    assert [(p["name"], p["memory_count"]) for p in body] == [
        ("beta", 3),
        ("alpha", 2),
        ("gamma", 1),
    ]


@pytest.mark.asyncio
async def test_empty_corpus_lists_no_projects(client, auth_headers):
    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# The switcher this feeds is a *scope* picker: a project holding nothing but
# retired rows is still a scope worth switching into, and omitting it would
# leave those rows unreachable from the UI.
@pytest.mark.asyncio
async def test_counts_every_status_not_only_active(
    client, auth_headers, session
):
    await _seed(session, ("live", "mixed"), ("retired", "mixed"))
    row = (
        await session.execute(
            Memory.__table__.select().where(Memory.project == "mixed")
        )
    ).first()
    await session.execute(
        Memory.__table__.update()
        .where(Memory.id == row.id)
        .values(status="deprecated")
    )
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.json() == [{"name": "mixed", "memory_count": 2}]
