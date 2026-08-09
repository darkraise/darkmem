"""T3.15 — the browser capture lands on the ordinary door (doc 15 §4).

The extension's own suite proves its client-side halves. This file proves the
two claims that are only checkable on the server:

- **"Uses the ordinary REST/MCP door into `memory_buffer` — no new pipeline."**
  Asserted by driving the real door with the real payload shape and reading
  the buffer, and by a scan proving no route or service was added for this
  client. A second capture path is the failure: it would need keeping in step
  with buffering, source resolution and the ack contract forever.
- **The capture is attributable.** A browser capture carries a per-install
  `origin_key`, and what that key becomes on the server decides what
  `COUNT(DISTINCT origin_key)` means for every fact lifted from it.
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

PROJECT = "t3-15-browser"
EXTENSION_SOURCE = "browser-extension"


def _payload(**overrides) -> dict:
    """Exactly what `extension/src/capture.js` builds, field for field.

    Hand-mirrored rather than imported — the extension is a separate package
    with no Python — so it carries the risk of drifting from the real client.
    That drift is what the field-name assertions below exist to catch: they
    fail if the server stops accepting a field this payload sends.
    """
    body = {
        "content": "postgres uses MVCC",
        "source": EXTENSION_SOURCE,
        "origin_key": f"ext:{uuid4()}",
        "project": PROJECT,
        "metadata": {
            "page_url": "https://claude.ai/chat/1",
            "page_title": "A chat",
            "capture_surface": "claude",
            "turn_roles": ["user", "assistant"],
        },
    }
    body.update(overrides)
    return body


class TestTheOrdinaryDoor:
    async def test_a_browser_capture_is_accepted_and_buffered(self, client, auth_headers):
        """202 and a buffer row: the same contract every capture door honours.

        Not 201 — every capture buffers, and a client treating only 201 as
        success would report every ordinary capture as a failure.
        """
        response = await client.post(
            "/api/v1/memories", json=_payload(), headers=auth_headers
        )

        assert response.status_code == 202, response.text
        assert response.json()["id"]

    async def test_the_capture_lands_in_memory_buffer_not_somewhere_new(
        self, client, auth_headers, session
    ):
        body = _payload()
        await client.post("/api/v1/memories", json=body, headers=auth_headers)

        queued = (await session.execute(
            text("SELECT COUNT(*) FROM memory_buffer WHERE project = CAST(:p AS text)"),
            {"p": PROJECT},
        )).scalar_one()
        assert queued >= 1

    async def test_the_extension_metadata_survives_the_door(
        self, client, auth_headers, session
    ):
        """The adapter's attribution is only worth adding if it arrives. A
        door that dropped unknown metadata keys would make the surface label
        unrecoverable without saying so."""
        body = _payload()
        await client.post("/api/v1/memories", json=body, headers=auth_headers)

        row = (await session.execute(
            text("SELECT metadata FROM memory_buffer WHERE project = CAST(:p AS text) "
                 "ORDER BY created_at DESC LIMIT 1"),
            {"p": PROJECT},
        )).scalar_one()

        client_metadata = row["metadata"]
        assert client_metadata["capture_surface"] == "claude"
        assert client_metadata["turn_roles"] == ["user", "assistant"]
        assert client_metadata["page_url"] == body["metadata"]["page_url"]

    async def test_the_source_is_resolved_to_the_client_not_the_transport(
        self, client, auth_headers, session
    ):
        """`source` is what the audit and the origin key both key on. A
        browser capture must not read as a generic `api` write, or every
        clipping in the vault loses the fact that a human clipped it."""
        body = _payload()
        await client.post("/api/v1/memories", json=body, headers=auth_headers)

        # `source` is a column on `memory_buffer`; `origin_key` rides in the
        # metadata blob. Read both from where they actually live rather than
        # assuming one shape -- an earlier draft looked for `source` inside
        # the blob and failed on correct code.
        row = (await session.execute(
            text("SELECT source, metadata FROM memory_buffer "
                 "WHERE project = CAST(:p AS text) ORDER BY created_at DESC LIMIT 1"),
            {"p": PROJECT},
        )).mappings().one()

        assert row["source"] == EXTENSION_SOURCE
        row = row["metadata"]

        # And the declared install id was **resolved**, not stored verbatim:
        # `resolve_origin_key` prefixes the resolved source and strips colons,
        # so what counts toward COUNT(DISTINCT origin_key) is this install
        # under this client -- not a raw string a page could have chosen.
        assert row["origin_key"].startswith(f"{EXTENSION_SOURCE}:")
        assert ":" not in row["origin_key"][len(EXTENSION_SOURCE) + 1 :]

    async def test_an_empty_selection_is_refused_by_the_door_too(
        self, client, auth_headers
    ):
        """The client refuses it first, but the door is what makes the refusal
        a property of the system rather than of one client."""
        response = await client.post(
            "/api/v1/memories", json=_payload(content=""), headers=auth_headers
        )
        assert response.status_code == 422


class TestNoNewPipeline:
    async def test_no_route_or_service_was_added_for_this_client(self):
        """The done-when's "no new pipeline", asserted rather than reviewed.

        A browser-specific capture route or service is the shape this forbids;
        the extension must be indistinguishable from any other client of the
        ordinary door. The scan is over names, so it catches the honest
        version of the mistake — someone adding `browser_capture.py` — rather
        than every conceivable one.
        """
        app_dir = Path(__file__).resolve().parents[1] / "app"
        offenders = [
            str(path)
            for path in app_dir.rglob("*.py")
            if any(token in path.name for token in ("browser", "extension", "scrape"))
        ]
        assert not offenders, (
            "the browser extension captures through the ordinary door; a "
            f"client-specific module is a second capture path: {offenders}"
        )

    async def test_no_capture_route_names_the_extension(self):
        """The other half: an existing module could branch on the client."""
        offenders: list[str] = []
        api = Path(__file__).resolve().parents[1] / "app/api"
        scanned = sorted(api.rglob("*.py"))
        assert len(scanned) > 10, "the scan reached no files"
        for path in scanned:
            source = path.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value in {EXTENSION_SOURCE, "browser_extension"}:
                        offenders.append(f"{path}:{node.lineno}")
        assert not offenders, (
            "a door branching on the extension's source label is a "
            f"client-specific capture path: {offenders}"
        )
