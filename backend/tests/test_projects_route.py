"""`kind` on the derived scope catalogue.

The catalogue is a union over memories, documents, workstreams and pages, so a
personal space holding nothing would be invisible to its own picker -- which
is what made `projects.kind` inert.
"""
from uuid import uuid4

import pytest

from app.repositories.documents import upsert_by_uri
from app.services.project_registry import seed_personal_project


@pytest.mark.asyncio
async def test_an_empty_personal_project_still_appears_with_its_kind(
    client, auth_headers, session
):
    await seed_personal_project(session)
    await session.commit()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    rows = {p["name"]: p for p in resp.json()}
    assert "notes" in rows
    assert rows["notes"]["kind"] == "personal"
    assert rows["notes"]["document_count"] == 0


@pytest.mark.asyncio
async def test_a_personal_project_holding_documents_appears_exactly_once(
    client, auth_headers, session
):
    """The personal arm and the documents arm both name it; `UNION` dedupes."""
    await seed_personal_project(session)
    await upsert_by_uri(
        session, document_id=uuid4(), project="notes",
        uri=f"/{uuid4().hex}.md", title=None, source_type="md",
        content_hash="y" * 64, properties=None, content=None,
    )
    await session.commit()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    body = resp.json()
    matching = [p for p in body if p["name"] == "notes"]
    assert len(matching) == 1
    assert matching[0]["kind"] == "personal"
    assert matching[0]["document_count"] == 1


@pytest.mark.asyncio
async def test_an_ordinary_project_defaults_to_kind_project(
    client, auth_headers, session
):
    project = f"proj-{uuid4().hex[:8]}"
    await upsert_by_uri(
        session, document_id=uuid4(), project=project,
        uri=f"/{uuid4().hex}.md", title=None, source_type="md",
        content_hash="z" * 64, properties=None, content=None,
    )
    await session.commit()

    body = (await client.get("/api/v1/projects", headers=auth_headers)).json()
    row = next(p for p in body if p["name"] == project)
    assert row["kind"] == "project"
