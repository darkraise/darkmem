"""The Notion import door over REST."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.config import settings
from tests.fixtures.notion.builder import FLAT_EXPORT, HTML_EXPORT, build_fixture

V1 = "/api/v1"
ZIP = {"Content-Type": "application/zip"}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path / "attachments"))
    return tmp_path


@pytest.fixture
async def project(session):
    # kind='project', not 'personal': `ux_projects_one_personal` is a partial
    # unique index, so a personal row leaked by any other module would collide.
    # The route checks the name only.
    await session.execute(
        text("INSERT INTO projects (name) VALUES ('notes') "
             "ON CONFLICT (name) DO NOTHING")
    )
    return "notes"


def _zip(entries, tmp_path, name="export.zip") -> bytes:
    return build_fixture(entries, tmp_path / name).read_bytes()


async def _post(client, auth_headers, tmp_path, entries=FLAT_EXPORT, project="notes"):
    return await client.post(
        f"{V1}/pages/import/notion?project={project}",
        content=_zip(entries, tmp_path),
        headers={**auth_headers, **ZIP},
    )


async def test_an_import_answers_201_with_the_report(
    client, auth_headers, root, project, tmp_path
):
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
        "root_page_id", "pages_created", "databases", "attachments_stored",
        "attachment_bytes", "warnings", "warnings_omitted",
    }
    assert body["pages_created"] == 6
    assert all(set(w) == {"path", "kind", "detail"} for w in body["warnings"])


async def test_an_unknown_project_is_refused(client, auth_headers, root, tmp_path):
    response = await _post(client, auth_headers, tmp_path, project="no-such-project")
    assert response.status_code == 422
    assert "no-such-project" in response.json()["detail"]


async def test_an_html_export_is_refused_with_advice(
    client, auth_headers, root, project, tmp_path
):
    response = await _post(client, auth_headers, tmp_path, entries=HTML_EXPORT)
    assert response.status_code == 422
    assert "Markdown & CSV" in response.json()["detail"]


async def test_a_body_over_the_ceiling_answers_413(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_bytes", 64)
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 413


async def test_a_concurrent_import_answers_409(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    from app.services import page_import

    class Held:
        def locked(self) -> bool:
            return True

    monkeypatch.setattr(page_import, "_import_lock", Held())
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 409


async def test_insufficient_space_answers_507(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 507


async def test_the_route_needs_auth(client, root, project, tmp_path):
    response = await client.post(
        f"{V1}/pages/import/notion?project=notes",
        content=_zip(FLAT_EXPORT, tmp_path),
        headers=ZIP,
    )
    assert response.status_code == 401


async def test_the_route_is_refused_on_a_read_only_instance(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "read_only", True)
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 403


async def test_the_route_does_not_shadow_a_page_read(client, auth_headers):
    response = await client.get(f"{V1}/pages/import", headers=auth_headers)
    assert response.status_code in (404, 422)


async def test_the_deadline_answers_422_naming_the_bound(
    client, auth_headers, root, project, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_seconds", 0)
    response = await _post(client, auth_headers, tmp_path)
    assert response.status_code == 422
    assert "notion_import_max_seconds" in response.json()["detail"]
