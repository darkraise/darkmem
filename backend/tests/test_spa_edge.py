"""The SPA mount that makes the app the network edge.

The mount matches every path no router claimed, so the properties worth
guarding are the ones that go wrong silently: a deep link must serve the
index rather than 404, a reserved prefix must stay an honest 404 envelope
rather than a 200 of index.html, and the SPA must never enter the OpenAPI
schema or the live-router enumerations.

Every case runs against a tmp_path fixture holding a fake bundle, never a
real ``npm run build`` and never the production directory constant.
"""
from __future__ import annotations

import pytest
from starlette.routing import Mount

from app.api.spa import SPAFiles, mount_spa
from app.main import app

INDEX_BODY = "<!doctype html><html><body><div id=\"root\"></div></body></html>"
ASSET_BODY = "console.log('spa');\n"


@pytest.fixture
def spa_dir(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX_BODY)
    (tmp_path / "assets" / "app.js").write_text(ASSET_BODY)
    return tmp_path


@pytest.fixture
def mounted(spa_dir):
    assert mount_spa(app, spa_dir) is True
    try:
        yield spa_dir
    finally:
        app.router.routes[:] = [
            route for route in app.router.routes
            if not (isinstance(route, Mount) and route.name == "spa")
        ]


async def test_root_serves_the_index_with_no_cache(client, mounted):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text == INDEX_BODY
    assert "no-cache" in response.headers["cache-control"]


@pytest.mark.parametrize(
    "path",
    ["/settings", "/memories/6f1c2b0e-6b4a-4a1d-9d4a-0f5d5b2a1c33", "/graph/deep/link"],
)
async def test_deep_links_serve_the_index(client, mounted, path):
    response = await client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX_BODY
    assert "no-cache" in response.headers["cache-control"]


async def test_hashed_assets_are_immutable(client, mounted):
    response = await client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == ASSET_BODY
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


@pytest.mark.parametrize(
    "path",
    ["/api/v1/definitely-not-a-route", "/api/v1/auth/typo", "/health/nonsense", "/ws/nonsense"],
)
async def test_reserved_prefixes_stay_honest_404_envelopes(client, mounted, path):
    response = await client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "not_found"
    assert INDEX_BODY not in response.text


@pytest.mark.parametrize("path", ["api/x", "health/x", "ws/x", "mcp/x"])
async def test_every_reserved_prefix_reraises_the_404(spa_dir, path):
    """The /mcp arm has its own Mount in the real app, so the SPA never sees
    it there; assert the branch directly rather than leaving it untested."""
    from starlette.exceptions import HTTPException

    files = SPAFiles(directory=spa_dir, html=False)
    scope = {"type": "http", "method": "GET", "path": "/" + path, "headers": []}
    with pytest.raises(HTTPException) as excinfo:
        await files.get_response(path, scope)
    assert excinfo.value.status_code == 404


async def test_non_http_scope_closes_instead_of_asserting(spa_dir):
    """StaticFiles asserts scope["type"] == "http"; the mount matches every
    unrouted websocket path too, so an unknown /ws/... connect would raise
    AssertionError out of the ASGI app instead of closing cleanly."""
    files = SPAFiles(directory=spa_dir, html=False)
    scope = {"type": "websocket", "path": "/ws/nonsense", "headers": []}
    sent = []

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        sent.append(message)

    await files(scope, receive, send)
    assert [m["type"] for m in sent] == ["websocket.close"]


async def test_registered_routes_are_not_shadowed(client, mounted):
    health = await client.get("/health")
    assert health.status_code in (200, 503)
    assert "services" in health.json()

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "unauthorized"


async def test_absent_directory_skips_the_mount(tmp_path):
    missing = tmp_path / "never-built"
    before = len(app.router.routes)
    assert mount_spa(app, missing) is False
    assert len(app.router.routes) == before


async def test_absent_directory_still_serves_the_api(client, tmp_path):
    """The branch every other backend test runs in: no build, app still up."""
    assert mount_spa(app, tmp_path / "never-built") is False
    response = await client.get("/health")
    assert response.status_code in (200, 503)


async def test_spa_is_a_mount_and_never_an_api_route(mounted):
    from fastapi.routing import APIRoute

    spa_routes = [
        route for route in app.router.routes
        if isinstance(route, Mount) and route.name == "spa"
    ]
    assert len(spa_routes) == 1
    assert isinstance(spa_routes[0].app, SPAFiles)

    for route in app.router.routes:
        if isinstance(route, APIRoute):
            assert ":path}" not in route.path, route.path

    paths = app.openapi()["paths"]
    assert not [p for p in paths if ":path}" in p]
    assert "/{path}" not in paths
    assert "/{full_path}" not in paths


async def test_the_mount_is_registered_last(mounted):
    assert isinstance(app.router.routes[-1], Mount)
    assert app.router.routes[-1].name == "spa"
