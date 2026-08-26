"""F1 Capture (docs/planning/e2e-test-plan.md's coverage table): a capture
through REST *and* through MCP lands in the buffer, flushes, and appears in
search with its `origin_key` intact.

Four ordered tests, not one function behind a module-level skip (T1.64 plan
§2.4 — the original single-skip design meant the whole file could silently
prove nothing on the only machine that runs the gate). The first three are
**unconditional** — none needs a reachable embedder:

1. ``test_capture_lands_in_buffer`` — REST accept.
2. ``test_buffer_flush_lands_row_or_records_failure`` — REST flush; asserts
   either the row lands `active` or `pipeline_failures` names the
   `content_embedding` failure, and asserts `origin_key` against the row
   directly (neither door's response schema carries the column — plan §2.5).
3. ``test_mcp_capture_lands_in_buffer_and_flushes`` — the same, through the
   MCP door, over a real MCP session against the booted stack's `/mcp`
   endpoint (plan §2.5 closes the REST-only gap Important finding I2 named).

Only the fourth may skip, and only with the real, recorded reason:

4. ``test_capture_appears_in_search`` — search for whichever capture's flush
   actually landed `active`; skips with the verbatim `pipeline_failures`
   error only when neither REST nor MCP produced an active row this run.

State rides a module-level dict rather than a fixture, since fixtures reset
per test and these four need to share the ids and outcomes ordinary pytest
execution order produces (top-to-bottom within a file, no reordering
plugin is installed in this suite).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from mcp import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402
from mcp.shared._httpx_utils import create_mcp_http_client  # noqa: E402

PROJECT = "e2e-f1"
BUFFER_FLUSH_TRIGGER_RETRIES = 20
BUFFER_FLUSH_TRIGGER_DELAY_S = 0.5

# Shared across this module's four tests, in execution order.
_state: dict = {}


async def _trigger_buffer_flush(client: httpx.AsyncClient) -> None:
    """Trigger buffer_flush, tolerating a 409 busy (Minor M2: the registry's
    own scheduled loop can hold the lock on the first manual attempt) by
    polling/retrying rather than failing on it."""
    for _ in range(BUFFER_FLUSH_TRIGGER_RETRIES):
        resp = await client.post("/api/v1/jobs/buffer_flush/trigger")
        if resp.status_code == 409:
            await asyncio.sleep(BUFFER_FLUSH_TRIGGER_DELAY_S)
            continue
        assert resp.status_code == 200, (
            f"buffer_flush trigger failed: {resp.status_code} {resp.text}"
        )
        return
    raise TimeoutError(
        f"buffer_flush trigger stayed busy (409) across "
        f"{BUFFER_FLUSH_TRIGGER_RETRIES} retries"
    )


async def _assert_row_lands_or_records_failure(
    db_session, memory_id: str, expected_origin_key: str,
) -> tuple[bool, str | None]:
    """Read the `memories` row directly and assert `origin_key`.

    ``materialize()`` (buffer_flush.py) inserts the row with status defaulting
    to 'active' (the column's server default) BEFORE the pipeline ever runs,
    and nothing in ``process_batch`` ever demotes it on a Phase-1 embed
    failure — measured live this run: a memory whose embed failed still reads
    status='active'. So status is never the signal for "did this land
    searchable" here; the presence of a ``content_embedding``
    ``pipeline_failures`` row is. Returns (embed_succeeded, failure_reason).
    """
    row = (await db_session.execute(
        text("SELECT status, origin_key FROM memories WHERE id = CAST(:id AS uuid)"),
        {"id": memory_id},
    )).first()
    assert row is not None, (
        f"memory {memory_id} has no row after buffer_flush — "
        "materialize() must run before the pipeline, regardless of outcome"
    )
    status, origin_key = row
    assert status == "active", (
        f"memory {memory_id} has status={status!r} — materialize() always "
        "writes 'active' regardless of pipeline outcome, so anything else "
        "means the write itself never happened"
    )
    assert origin_key == expected_origin_key, (
        f"origin_key mismatch for {memory_id}: {origin_key!r} != "
        f"{expected_origin_key!r}"
    )

    failure = (await db_session.execute(
        text(
            "SELECT error_message FROM pipeline_failures "
            "WHERE entity_type = 'memory' AND entity_id = CAST(:id AS uuid) "
            "AND pipeline_name = 'memory_ingest' AND failed_step = "
            "'content_embedding' AND resolved_at IS NULL"
        ),
        {"id": memory_id},
    )).first()
    if failure is None:
        return True, None
    return False, failure[0]


async def test_capture_lands_in_buffer(api_client):
    resp = await api_client.post(
        "/api/v1/memories",
        json={"content": "T1.64 F1 REST capture probe", "project": PROJECT},
    )
    assert resp.status_code == 202, f"expected 202, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["id"], "CaptureAck.id must be the pre-minted memory id"
    _state["rest_memory_id"] = body["id"]


async def test_buffer_flush_lands_row_or_records_failure(api_client, db_session):
    memory_id = _state["rest_memory_id"]
    await _trigger_buffer_flush(api_client)

    landed_active, failure_reason = await _assert_row_lands_or_records_failure(
        db_session, memory_id, expected_origin_key=f"unknown:api:{PROJECT}",
    )
    _state["rest_landed_active"] = landed_active
    _state["rest_failure_reason"] = failure_reason


async def test_mcp_capture_lands_in_buffer_and_flushes(
    api_client, db_session, e2e_base_url,
):
    # /mcp requires a bearer key on every request. The probe mints one over the
    # admin session it already holds rather than reading an env var, because
    # the disposable stack this runs against boots with no keys at all.
    minted = await api_client.post(
        "/api/v1/api-keys", json={"name": "e2e-mcp-probe", "scopes": ["capture"]},
    )
    assert minted.status_code == 201, f"could not mint an MCP key: {minted.text}"
    credential = minted.json()["token"]

    http_client = create_mcp_http_client(
        headers={"Authorization": f"Bearer {credential}"}
    )
    async with http_client, streamable_http_client(
        f"{e2e_base_url}/mcp", http_client=http_client
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "memory_add",
                {
                    "content": "T1.64 F1 MCP capture probe",
                    "project": PROJECT,
                },
            )
            assert not result.is_error, f"memory_add tool call failed: {result}"
            ack = json.loads(result.content[0].text)
            assert ack["status"] == "accepted"
            assert ack["id"], "MCP memory_add ack must carry the pre-minted memory id"
            memory_id = ack["id"]

    await _trigger_buffer_flush(api_client)

    landed_active, failure_reason = await _assert_row_lands_or_records_failure(
        db_session, memory_id, expected_origin_key=f"unknown:mcp:{PROJECT}",
    )
    _state["mcp_memory_id"] = memory_id
    _state["mcp_landed_active"] = landed_active
    _state["mcp_failure_reason"] = failure_reason


async def test_capture_appears_in_search(api_client):
    active_leg = None
    if _state.get("rest_landed_active"):
        active_leg = ("rest_memory_id", "T1.64 F1 REST capture probe")
    elif _state.get("mcp_landed_active"):
        active_leg = ("mcp_memory_id", "T1.64 F1 MCP capture probe")

    if active_leg is None:
        reason = _state.get("rest_failure_reason") or _state.get("mcp_failure_reason")
        pytest.skip(
            f"content embedding failed this run: {reason} "
            f"(pipeline_failures, memory {_state.get('rest_memory_id')}) — "
            "search cannot be proven without a reachable embedder"
        )

    memory_key, needle = active_leg
    memory_id = _state[memory_key]

    resp = await api_client.post(
        "/api/v1/memories/search",
        json={"query": needle, "project": PROJECT, "limit": 20},
    )
    assert resp.status_code == 200, f"search failed: {resp.status_code} {resp.text}"
    ids = {row["id"] for row in resp.json()}
    assert memory_id in ids, (
        f"memory {memory_id} did not appear in search results for its own content"
    )
