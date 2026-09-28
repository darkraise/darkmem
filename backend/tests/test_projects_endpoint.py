"""The scope catalogue.

These tests scope every assertion to the projects they seed. Since the
endpoint was widened to union documents, workstreams and pages (2026-08-31,
review M2), a global assertion here would also be asserting the state of every
other test module that commits a workstream or a document -- suites that commit
rows outlive their own test, and asserting "the corpus is empty" would be
asserting something about that module rather than about this endpoint.
"""
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.documents import upsert_by_uri


async def _seed_page(
    session, project: str, *, deleted: bool = False
) -> None:
    deleted_at_sql = "now()" if deleted else "NULL"
    await session.execute(
        text(
            "INSERT INTO pages (id, project, order_index, content_hash, "
            f"deleted_at) VALUES (gen_random_uuid(), :project, 0, 'h', "
            f"{deleted_at_sql})"
        ),
        {"project": project},
    )


async def _seed_document(session, project: str, uri: str) -> None:
    await upsert_by_uri(
        session, document_id=uuid4(), project=project, uri=uri,
        title=None, source_type="md", content_hash="x" * 64, properties=None,
        # Passed explicitly rather than omitted: the project index counts
        # documents and never reads their source, so a seeded row with no
        # content is the honest fixture.
        content=None,
    )


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
    seeded = [p for p in body if p["name"] in {"alpha", "beta", "gamma"}]
    # Relative order among the seeded three: busiest first is the contract,
    # and it holds regardless of what else the database happens to carry.
    assert [(p["name"], p["memory_count"]) for p in seeded] == [
        ("beta", 3),
        ("alpha", 2),
        ("gamma", 1),
    ]


@pytest.mark.asyncio
async def test_a_project_nothing_carries_is_absent(client, auth_headers):
    """Derived, never a registry: a name no row carries does not appear.

    Formerly `test_empty_corpus_lists_no_projects`, which asserted the whole
    response was empty. That asserted the state of the shared test database
    rather than of this endpoint, and stopped holding the moment the union
    could see another module's committed rows.
    """
    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert "a-project-nothing-carries" not in names


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
    # Exact equality on the seeded row, so an accidental extra FIELD still
    # fails; scoped to that row, so another module's committed rows
    # do not.
    mixed = next(p for p in resp.json() if p["name"] == "mixed")
    assert mixed == {
        "name": "mixed",
        "kind": "project",
        "memory_count": 2,
        "document_count": 0,
        "page_count": 0,
        "workstream_count": 0,
        "open_workstream_count": 0,
        "last_worklog_at": None,
        "last_event_day": None,
    }


@pytest.mark.asyncio
async def test_a_document_only_project_is_visible(client, auth_headers, session):
    """Review M2: the corpus import creates exactly this shape -- documents,
    zero memories -- and the index must show it."""
    await _seed_document(session, "docs-only", "docs/readme.md")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "docs-only" in body
    assert body["docs-only"]["memory_count"] == 0
    assert body["docs-only"]["document_count"] == 1


@pytest.mark.asyncio
async def test_a_worklog_only_project_is_visible(client, auth_headers, session):
    """The Activity route's open-workstream list finds its projects here."""
    from app.services import worklog

    first = await worklog.append(
        session, project="worklog-only", key="plan-a", run_key="r",
        entries=[{"kind": "note", "body": "a"}],
    )
    await worklog.append(
        session, project="worklog-only", key="plan-b", run_key="r",
        entries=[{"kind": "note", "body": "b"}],
    )
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "worklog-only" in body
    row = body["worklog-only"]
    assert row["workstream_count"] == 2
    assert row["open_workstream_count"] == 1
    assert row["last_worklog_at"] is not None
    assert row["memory_count"] == 0


@pytest.mark.asyncio
async def test_a_project_holding_only_pages_is_listed(client, auth_headers, session):
    """The catalogue is a union, and a project absent from it cannot be
    selected in any UI that reads it."""
    await _seed_page(session, "pages-only")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = {p["name"]: p for p in resp.json()}
    assert "pages-only" in body
    assert body["pages-only"]["page_count"] == 1


@pytest.mark.asyncio
async def test_trashed_pages_do_not_count(client, auth_headers, session):
    await _seed_page(session, "pages-trashed", deleted=True)
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    names = {p["name"] for p in resp.json()}
    # A project whose only pages are in the trash reads as empty, which is
    # what it is -- so it is absent from the derived catalogue entirely.
    assert "pages-trashed" not in names


@pytest.mark.asyncio
async def test_one_project_in_two_corpora_is_one_row(client, auth_headers, session):
    await _seed(session, ("m", "both"))
    await _seed_document(session, "both", "docs/a.md")
    await session.flush()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    rows = [p for p in resp.json() if p["name"] == "both"]
    assert len(rows) == 1
    assert rows[0]["memory_count"] == 1
    assert rows[0]["document_count"] == 1
