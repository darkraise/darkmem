"""Serve the built single-page app from the API process.

The app is the network edge in the shipped posture, so the SPA is a mount
rather than a route: a ``Mount`` is not an ``APIRoute``, so it stays out of
the OpenAPI schema and out of the two live-router enumerations
(``test_rest_conformance``, ``test_door_parity``) that classify every REST
capability. An ``@app.get("/{full_path:path}")`` catch-all would demand a
row in both, asserting that the SPA is a REST capability with a two-door
disposition.
"""
from __future__ import annotations

import logging
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocketClose

logger = logging.getLogger(__name__)

INDEX_FILE = "index.html"

# First path segments the mount must never answer for. The mount is
# registered last and matches everything, so without this an unknown
# /api/v1/... path would come back as index.html with 200 where the REST
# contract says a 404 error envelope.
RESERVED_PREFIXES = frozenset({"api", "health", "ws", "mcp"})

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
INDEX_CACHE_CONTROL = "no-cache"


class SPAFiles(StaticFiles):
    """``StaticFiles`` with deep-link fallback, reserved prefixes and caching.

    ``StaticFiles(html=True)`` does not give the deep-link guarantee: on a
    miss it looks for ``404.html`` and otherwise raises 404, and the built
    bundle carries no ``404.html``, so a hard refresh on /settings would 404.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # The mount matches every unrouted path, including websocket scopes,
        # which StaticFiles asserts against. Mirror the router's own
        # not-found close instead of raising AssertionError out of the app.
        if scope["type"] != "http":
            await WebSocketClose()(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or _first_segment(path) in RESERVED_PREFIXES:
                raise
            response = await super().get_response(INDEX_FILE, scope)
            _apply_cache_control(response, INDEX_FILE)
            return response
        _apply_cache_control(response, path)
        return response


def _first_segment(path: str) -> str:
    return path.split("/", 1)[0]


def _apply_cache_control(response: Response, path: str) -> None:
    # nginx's rules, moved rather than retuned: a cached index.html that
    # references hashed chunks a newer image no longer carries is the classic
    # post-deploy white screen.
    if path == INDEX_FILE:
        response.headers["cache-control"] = INDEX_CACHE_CONTROL
    elif _first_segment(path) == "assets":
        response.headers["cache-control"] = IMMUTABLE_CACHE_CONTROL


def mount_spa(app, directory: Path | str) -> bool:
    """Mount the built SPA at ``/``; return whether it was mounted.

    An absent directory is tolerated because backend tests and host-side dev
    runs have no build. It is logged at WARNING rather than INFO: an image
    whose SPA copy failed boots perfectly, passes its healthcheck and serves
    every API route, so a silent line here is the only symptom until a human
    opens the UI.
    """
    directory = Path(directory)
    if not directory.is_dir():
        logger.warning(
            "SPA directory %s not found — the API will not serve the UI", directory
        )
        return False
    app.mount("/", SPAFiles(directory=directory, html=False), name="spa")
    logger.info("Serving the SPA from %s", directory)
    return True
