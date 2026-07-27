"""The adjudication of every operational surface that returns memory content.

T1.29a-d closed the retrieval channels. What kept escaping was the other set:
surfaces that return memory-derived data as a side effect of an operational job
— a backfill queue, a triage list, a dashboard, an append-only journal. Three
sweeps enumerated retrieval channels and stopped, so this module pins both the
distinction and the decision made for each surface.

Two of them are decided here in the opposite direction from the rest, and that
is the point: the pipeline-failure triage list and the re-embed backfill queue
are **deliberately deployment-wide**, because a triage screen that hid another
project's failures and a backfill queue that hid another project's unembedded
rows would each be a worse tool, not a safer one. Those decisions are pinned
from both sides — a test fails if they are narrowed, and a test fails if the
labels that make them honest are dropped.

The remaining edge is the guard at the top: every route the app registers and
every MCP tool it exposes must be classified. A new front door that returns
memory content and nobody decided fails the build rather than waiting for a
fourth sweep to find it.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from app.main import app
from app.models.memory import Memory
from app.services.content_surfaces import (
    CONTENT_SURFACES,
    MCP_TOOLS_WITHOUT_MEMORY_CONTENT,
    ROUTES_WITHOUT_MEMORY_CONTENT,
    Scoping,
    SurfaceKind,
    declared_front_doors,
    escalated_surfaces,
    memory_content_surfaces,
    operator_wide_surfaces,
    retrieval_channels,
    surface,
)
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.memory_buffer import enqueue
from app.services.pipeline_failures import PipelineFailureService
from app.services.reembed import ReembedService

pytestmark = pytest.mark.asyncio

FINGERPRINT = "surface-embedder|4"
DIMS = 4


def _rest_routes() -> set[str]:
    paths = app.openapi()["paths"]
    return {
        f"{method.upper()} {path}"
        for path, operations in paths.items()
        for method in operations
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }


async def _mcp_tools() -> set[str]:
    from app.api.mcp.server import mcp

    return {f"mcp:{tool.name}" for tool in await mcp.list_tools()}


async def _add_memory(session, **fields) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="the connection pool sizing note",
        source="test",
        memory_type="fact",
        importance=0.5,
        metadata_={},
        project="alpha",
        status="active",
        is_archived=False,
    )
    base.update(fields)
    memory = Memory(**base)
    session.add(memory)
    await session.flush()
    return memory


async def _create_partition(session, fingerprint: str = FINGERPRINT) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint, "mid": fingerprint.split("|")[0], "dims": DIMS},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))
    await session.flush()


# ── the guard: nothing may be undecided ──────────────────────────────


async def test_every_rest_route_is_classified():
    """A front door nobody decided is the defect this whole series exists to
    prevent, so the route table itself is the fixture: adding a route without
    classifying it fails here rather than three sweeps later."""
    declared = {door for door in declared_front_doors() if not door.startswith("mcp:")}
    classified = declared | ROUTES_WITHOUT_MEMORY_CONTENT
    live = _rest_routes()

    assert live - classified == set(), "route registered but not classified"
    assert classified - live == set(), "classified route no longer registered"


async def test_every_mcp_tool_is_classified():
    declared = {door for door in declared_front_doors() if door.startswith("mcp:")}
    classified = declared | MCP_TOOLS_WITHOUT_MEMORY_CONTENT
    live = await _mcp_tools()

    assert live - classified == set(), "MCP tool registered but not classified"
    assert classified - live == set(), "classified MCP tool no longer registered"


async def test_no_front_door_is_claimed_twice():
    seen: set[str] = set()
    for s in CONTENT_SURFACES:
        for door in s.front_doors:
            assert door not in seen, f"{door} claimed by two surfaces"
            seen.add(door)
    assert not seen & ROUTES_WITHOUT_MEMORY_CONTENT
    assert not seen & MCP_TOOLS_WITHOUT_MEMORY_CONTENT


async def test_every_surface_carries_a_decision_and_a_reason():
    for s in CONTENT_SURFACES:
        assert s.front_doors, s.key
        assert s.crosses, s.key
        assert s.decided_by, s.key
        assert len(s.reason) > 40, f"{s.key} has no stated reason"


async def test_full_content_surfaces_are_labelled():
    """Whole memory content presented to a reader must name the project and
    status it came from. The honesty bar counts *unlabelled* cross-project and
    superseded rows, so labelling is what a surface that is deliberately wide
    trades for staying wide."""
    for s in CONTENT_SURFACES:
        if "content" in s.crosses and s.scoping is not Scoping.ID_ADDRESSED:
            assert "project" in s.labels and "status" in s.labels, s.key


async def test_the_two_kinds_are_both_populated():
    """The distinction is the deliverable: a probe built from retrieval
    channels alone returns a clean zero over the operational half."""
    assert len(retrieval_channels()) >= 5
    assert len(memory_content_surfaces()) >= 5
    assert {s.kind for s in CONTENT_SURFACES} == set(SurfaceKind)
    assert operator_wide_surfaces()
    assert escalated_surfaces()


# ── surface 1: the re-embed backfill queue ───────────────────────────


async def test_absent_partition_counts_every_row_without_previewing_it(session):
    """The anti-join used to degrade to a literal TRUE, at which point the
    endpoint paged a content preview of the entire table under a filter that
    discriminated nothing. The count is still exact; the enumeration is not."""
    for _ in range(3):
        await _add_memory(session)

    items, total, partition_missing = await ReembedService(session).list_obsolete_memories(
        "ghostmodel|512", limit=100,
    )

    assert total == 3
    assert partition_missing is True
    assert items == []


async def test_absent_partition_withholds_the_entity_listing_too(session):
    await session.execute(text(
        "INSERT INTO entities (id, name, entity_type, memory_ids) "
        "VALUES (gen_random_uuid(), 'postgres', 'tool', ARRAY[]::uuid[])"
    ))
    await session.flush()

    items, total, partition_missing = await ReembedService(session).list_obsolete_entities(
        "ghostmodel|512", limit=100,
    )

    assert total == 1
    assert partition_missing is True
    assert items == []


async def test_present_partition_still_previews_the_rows_that_need_work(session):
    """The fix must not cost the endpoint its job: with the partition present
    the anti-join discriminates, so the listing names the rows behind it."""
    await _create_partition(session)
    embedded = await _add_memory(session)
    missing = await _add_memory(session)
    await session.execute(
        text(
            f"INSERT INTO {child_table('memory_embeddings', FINGERPRINT)} "
            "(memory_id, fingerprint, embedding) "
            "VALUES (:mid, :fp, CAST(:vec AS vector))"
        ),
        {"mid": embedded.id, "fp": FINGERPRINT, "vec": str([1.0, 0.0, 0.0, 0.0])},
    )
    await session.flush()

    items, total, partition_missing = await ReembedService(session).list_obsolete_memories(
        FINGERPRINT, limit=100,
    )

    assert partition_missing is False
    assert total == 1
    assert [i["memory_id"] for i in items] == [str(missing.id)]
    assert items[0]["content_preview"]


async def test_backfill_queue_stays_deployment_wide(session):
    """Decided operator-wide, and pinned so a later sweep cannot narrow it by
    reflex: re-embedding is a partition backfill, so a row the queue hides is a
    row that never gets a vector under the active embedder."""
    await _create_partition(session)
    live = await _add_memory(session)
    await _add_memory(session, project="beta")
    await _add_memory(session, is_archived=True)
    await _add_memory(session, status="superseded", superseded_by=live.id)

    _, total, _ = await ReembedService(session).list_obsolete_memories(FINGERPRINT, limit=100)

    assert total == 4
    assert surface("reembed_backfill_queue").scoping is Scoping.OPERATOR_WIDE


# ── surface 2: the pipeline-failure triage list ──────────────────────


async def _record_failure(session, memory_id) -> None:
    await PipelineFailureService(session).record(
        entity_type="memory",
        entity_id=memory_id,
        pipeline_name="memory_processing",
        failed_step="extract",
        error_message="boom",
    )


async def test_failure_triage_previews_every_project_and_labels_the_scope(session):
    """Operator-wide on purpose. A failure the operator cannot see is a failure
    nobody retries, so the join stays unscoped — and every row names the project
    and lifecycle state its memory is in, which is what keeps that honest."""
    live = await _add_memory(session)
    foreign = await _add_memory(session, project="beta")
    retired = await _add_memory(session, status="superseded", superseded_by=live.id)
    for memory in (live, foreign, retired):
        await _record_failure(session, memory.id)

    items, total = await PipelineFailureService(session).list_unresolved()

    assert total == 3
    by_id = {i["entity_id"]: i for i in items}
    assert by_id[str(foreign.id)]["entity_project"] == "beta"
    assert by_id[str(retired.id)]["entity_status"] == "superseded"
    assert all(i["entity_preview"] for i in items)


async def test_failure_triage_survives_a_deleted_memory(session):
    """The LEFT JOIN is what lets a failure outlive its memory; a plain join
    would drop the row and strand the failure as unresolvable."""
    memory = await _add_memory(session)
    await _record_failure(session, memory.id)
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"), {"id": str(memory.id)}
    )
    await session.flush()

    items, total = await PipelineFailureService(session).list_unresolved()

    assert total == 1
    assert items[0]["entity_preview"] is None
    assert items[0]["entity_project"] is None


# ── surface 3: the analytics recents list ────────────────────────────


async def test_analytics_recents_label_project_and_status(client, auth_headers, session):
    """Deployment-wide like every other number on the dashboard, and labelled
    rather than narrowed: supersession is itself recent activity."""
    live = await _add_memory(session)
    await _add_memory(session, project="beta")
    await _add_memory(session, status="superseded", superseded_by=live.id)

    response = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert response.status_code == 200
    recents = response.json()["recent_memories"]

    assert {r["project"] for r in recents} == {"alpha", "beta"}
    assert "superseded" in {r["status"] for r in recents}
    assert all(r["project"] and r["status"] for r in recents)


async def test_analytics_recents_still_exclude_archived(client, auth_headers, session):
    await _add_memory(session)
    archived = await _add_memory(session, is_archived=True)

    response = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    ids = {r["id"] for r in response.json()["recent_memories"]}

    assert str(archived.id) not in ids


# ── surface 4: the capture-buffer triage queue ───────────────────────


async def test_buffer_defaults_to_every_project_and_names_each(client, auth_headers, session):
    """Scopeable, defaulting wide — the same shape the ratified `reason` default
    carries. Buffer rows are pre-flush captures with no status or is_archived
    yet, so project is the only scope there is, and every row states it."""
    await enqueue(session, content="alpha capture", project="alpha", source="api")
    await enqueue(session, content="beta capture", project="beta", source="api")
    await session.flush()

    response = await client.get("/api/v1/memory-buffer", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 2
    assert {r["project"] for r in body["items"]} == {"alpha", "beta"}


async def test_buffer_project_parameter_narrows_the_query(client, auth_headers, session):
    await enqueue(session, content="alpha capture", project="alpha", source="api")
    await enqueue(session, content="beta capture", project="beta", source="api")
    await session.flush()

    response = await client.get("/api/v1/memory-buffer?project=beta", headers=auth_headers)
    body = response.json()

    assert body["total"] == 1
    assert body["items"][0]["project"] == "beta"


# ── surface 5: the journal, escalated rather than decided ────────────


async def test_the_journal_preview_outlives_the_memory_it_came_from(session):
    """Escalated, not resolved. `events` is append-only by design (T1.06's three
    forbid-triggers), so a discarded capture's 500-char preview stays in the
    journal after the memory is gone: deleting a memory does not delete its
    content from the record. This test states the behaviour so the human's
    retention decision has something to flip, and fails loudly if a redaction
    scheme is introduced without one."""
    memory = await _add_memory(session)
    await record_event(
        session,
        event_type="buffer_discarded",
        object_type="memory",
        object_id=memory.id,
        project="alpha",
        source="api",
        payload={"content_preview": "the discarded capture"},
    )
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"), {"id": str(memory.id)}
    )
    await session.flush()

    payload = (await session.execute(
        text("SELECT payload FROM events WHERE event_type = 'buffer_discarded'")
    )).scalar_one()
    payload = json.loads(payload) if isinstance(payload, str) else payload

    assert payload["content_preview"] == "the discarded capture"
    assert surface("event_journal").scoping is Scoping.ESCALATED


async def test_chat_history_carries_the_same_retention_property(session):
    """The second store with this property, found while adjudicating the first.
    Retrieval was scoped when the answer was produced, but each assistant
    message persists a 150-char snippet of every cited memory and nothing prunes
    it when the memory is deleted."""
    assert surface("chat_history_citations").scoping is Scoping.ESCALATED

    memory = await _add_memory(session)
    conversation_id = (await session.execute(
        text("INSERT INTO conversations (id, title) VALUES (gen_random_uuid(), 't') RETURNING id")
    )).scalar_one()
    await session.execute(
        text(
            "INSERT INTO messages (id, conversation_id, role, content, context) "
            "VALUES (gen_random_uuid(), CAST(:cid AS uuid), 'assistant', 'answer', "
            "CAST(:ctx AS jsonb))"
        ),
        {
            "cid": str(conversation_id),
            "ctx": json.dumps({"memories": [{"id": str(memory.id), "content": "cited text"}]}),
        },
    )
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"), {"id": str(memory.id)}
    )
    await session.flush()

    context = (await session.execute(text("SELECT context FROM messages"))).scalar_one()
    context = json.loads(context) if isinstance(context, str) else context

    assert context["memories"][0]["content"] == "cited text"
