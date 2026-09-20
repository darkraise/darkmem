from __future__ import annotations

from app.main import (
    MAX_REQUEST_BODY_BYTES,
    bounds_own_body,
    is_attachment_upload_path,
    is_page_import_path,
)


def test_the_import_path_bounds_its_own_body():
    assert is_page_import_path("/api/v1/pages/import/notion") is True
    assert bounds_own_body("/api/v1/pages/import/notion") is True


def test_the_attachment_upload_path_still_bounds_its_own_body():
    path = "/api/v1/pages/11111111-1111-1111-1111-111111111111/attachments"
    assert is_attachment_upload_path(path) is True
    assert bounds_own_body(path) is True


def test_the_two_predicates_stay_distinct():
    upload = "/api/v1/pages/11111111-1111-1111-1111-111111111111/attachments"
    assert is_page_import_path(upload) is False
    assert is_attachment_upload_path("/api/v1/pages/import/notion") is False


def test_an_ordinary_page_route_is_still_capped():
    assert bounds_own_body("/api/v1/pages") is False
    assert bounds_own_body("/api/v1/pages/11111111-1111-1111-1111-111111111111") is False
    assert bounds_own_body("/api/v1/memories") is False


def test_a_lookalike_import_path_is_not_exempt():
    assert is_page_import_path("/api/v1/pages/import/notion/extra") is False
    assert is_page_import_path("/api/v1/pages/import") is False
    assert is_page_import_path("/api/v1/documents/import/notion") is False


async def test_an_oversized_body_on_an_ordinary_route_is_refused(client):
    response = await client.post(
        "/api/v1/memories",
        content=b"x" * 16,
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
    )
    assert response.status_code == 413


async def test_an_oversized_declared_body_reaches_the_import_route(client):
    # Past the edge cap, so the refusal must come from the route's own auth or
    # validation rather than from `payload_too_large`.
    response = await client.post(
        "/api/v1/pages/import/notion?project=notes",
        content=b"PK\x05\x06" + b"\x00" * 18,
        headers={"content-length": str(MAX_REQUEST_BODY_BYTES + 1)},
    )
    assert response.status_code != 413
