"""Page attachments over REST."""
from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings

V1 = "/api/v1"
PAGE = "22222222-2222-2222-2222-222222222222"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
async def page(session):
    await session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        f"VALUES ('{PAGE}', 'p', 0, 'h')"
    ))
    return PAGE


async def _upload(client, auth_headers, page_id, body, **headers):
    return await client.post(
        f"{V1}/pages/{page_id}/attachments", content=body,
        headers={**auth_headers, **headers},
    )


async def test_upload_then_get(client, auth_headers, root, page):
    created = await _upload(
        client, auth_headers, page, PNG,
        **{"X-Filename": "shot%201.png", "Content-Type": "text/html"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["content_type"] == "image/png"
    assert body["filename"] == "shot 1.png"
    assert body["size_bytes"] == len(PNG)
    assert body["url"] == f"/api/v1/pages/attachments/{body['id']}"

    got = await client.get(body["url"], headers=auth_headers)
    assert got.status_code == 200
    assert got.content == PNG
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.headers["content-security-policy"] == "sandbox"
    assert got.headers["content-disposition"].startswith("inline;")
    assert got.headers["etag"] == f'"{hashlib.sha256(PNG).hexdigest()}"'


async def test_html_is_served_as_a_download(client, auth_headers, root, page):
    created = await _upload(
        client, auth_headers, page, b"<html><script>alert(1)</script>",
        **{"X-Filename": "x.html", "Content-Type": "text/html"},
    )
    got = await client.get(created.json()["url"], headers=auth_headers)
    assert got.headers["content-type"] == "application/octet-stream"
    assert got.headers["content-disposition"].startswith("attachment;")


async def test_missing_filename_defaults(client, auth_headers, root, page):
    created = await _upload(client, auth_headers, page, b"abc")
    assert created.json()["filename"] == "file"


async def test_declared_length_over_the_cap_is_413(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "attachment_max_bytes", 10)
    response = await _upload(client, auth_headers, page, b"x" * 11)
    assert response.status_code == 413
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_streamed_body_over_the_cap_is_413(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "attachment_max_bytes", 10)

    async def body():
        yield b"x" * 6
        yield b"x" * 6

    response = await client.post(
        f"{V1}/pages/{page}/attachments", content=body(), headers=auth_headers,
    )
    assert response.status_code == 413
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_upload_to_an_unknown_page_is_404(client, auth_headers, root):
    response = await _upload(client, auth_headers, str(uuid4()), b"abc")
    assert response.status_code == 404


async def test_upload_to_an_unknown_page_reads_no_body(client, auth_headers, root, monkeypatch):
    from app.api.routes import page_attachments

    staged = []

    async def stage_upload(*args, **kwargs):
        staged.append(args)
        raise AssertionError("the body was read for a page that does not exist")

    monkeypatch.setattr(page_attachments, "stage_upload", stage_upload)
    response = await _upload(client, auth_headers, str(uuid4()), b"abc")

    assert response.status_code == 404
    assert staged == []


async def test_upload_to_a_trashed_page_is_404(client, auth_headers, root, page, session):
    await session.execute(text(f"UPDATE pages SET deleted_at = now() WHERE id = '{PAGE}'"))
    response = await _upload(client, auth_headers, page, b"abc")
    assert response.status_code == 404


async def test_upload_is_refused_on_a_read_only_instance(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "read_only", True)
    response = await _upload(client, auth_headers, page, b"abc")
    assert response.status_code == 403
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_get_missing_is_404(client, auth_headers, root):
    response = await client.get(f"{V1}/pages/attachments/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


async def test_get_with_row_but_no_file_is_404(client, auth_headers, root, page):
    created = await _upload(client, auth_headers, page, b"abc")
    for path in root.rglob("*"):
        if path.is_file():
            path.unlink()
    response = await client.get(created.json()["url"], headers=auth_headers)
    assert response.status_code == 404


async def test_an_unauthenticated_upload_is_401_even_read_only(
    client, root, page, monkeypatch,
):
    """Auth first: the posture of an instance is not an anonymous caller's
    to learn."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.post(f"{V1}/pages/{page}/attachments", content=b"a")
    assert response.status_code == 401


async def test_both_routes_need_auth(client, root, page):
    assert (await client.post(f"{V1}/pages/{page}/attachments", content=b"a")).status_code == 401
    assert (await client.get(f"{V1}/pages/attachments/{uuid4()}")).status_code == 401


async def test_an_upload_whose_part_was_collected_answers_408(
    client, auth_headers, root, page, monkeypatch,
):
    from app.api.routes import page_attachments as route

    real = route.stage_upload

    async def stage_then_collect(*args, **kwargs):
        staged = await real(*args, **kwargs)
        staged.part.unlink()
        return staged

    monkeypatch.setattr(route, "stage_upload", stage_then_collect)
    response = await _upload(client, auth_headers, page, PNG)

    assert response.status_code == 408, response.text
    assert response.json()["error"]["code"] == "request_timeout"
    assert [p for p in root.rglob("*") if p.is_file()] == []
