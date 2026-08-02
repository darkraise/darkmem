"""T2.12 — `memory_dream`: subsume, associate, refine; never merges, never deletes.

Doc 08 §5.4. Three Done-whens, two of them negatives, and a negative is where a
decorative guard hides: asserting a row still exists after a cycle that was
never going to remove it proves nothing. Every negative here is proven twice —
a differential arm (the same fixture builder, one flipped bit, asserting the
opposite outcome) and, where the claim is about code shape rather than
behaviour, a source scan carrying its own in-suite negative control.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories import memory_relations as edges
from app.utils.ids import new_id

PROJECT = "t212-dream"
OTHER_PROJECT = "t212-dream-other"

NOW = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)


_INSERT_MEMORY = text(
    """
    INSERT INTO memories (
        id, content, source, project, status, is_archived, created_at,
        summary, metadata
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), false,
        :created_at, :summary,
        CAST(:metadata AS jsonb)
    )
    """
)


async def seed_memory(
    session,
    *,
    project: str = PROJECT,
    content: str = "a memory",
    status: str = "active",
    created_at: datetime | None = None,
    summary: str | None = None,
    metadata: dict | None = None,
    memory_id: UUID | None = None,
) -> UUID:
    identifier = memory_id or new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(identifier),
            "content": content,
            "project": project,
            "status": status,
            "created_at": created_at or NOW,
            "summary": summary,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return identifier


async def read_edge(session, source, target, rel_type="RELATES_TO") -> dict | None:
    return await edges.get_edge(
        session,
        source_memory_id=source,
        target_memory_id=target,
        rel_type=rel_type,
    )


# ── Step 1: the memory_relations writer ──────────────────────────────────


class TestEdgeWriter:
    async def test_upsert_creates_then_updates_and_reports_created(self, session):
        older = await seed_memory(session, content="older")
        newer = await seed_memory(session, content="newer")
        await session.flush()

        first = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="ELABORATES",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.9},
        )
        assert first.created is True
        assert first.before is None

        second = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="ELABORATES",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.95},
        )
        assert second.created is False
        assert second.before is not None
        assert edges.pass_block_of(second.before, "near_duplicate") == {"score": 0.9}

        row = await read_edge(session, newer, older, "ELABORATES")
        assert edges.pass_block_of(row, "near_duplicate") == {"score": 0.95}

    async def test_a_supersedes_write_is_refused(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()

        with pytest.raises(edges.ProjectedRelationTypeError):
            await edges.upsert_edge(
                session,
                source_memory_id=newer,
                target_memory_id=older,
                rel_type="SUPERSEDES",
                project=PROJECT,
                pass_key="near_duplicate",
                block={},
            )

    async def test_an_unknown_type_falls_back_within_the_closed_set(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()

        await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="INVENTED_BY_A_MODEL",
            project=PROJECT,
            pass_key="near_duplicate",
            block={},
        )
        stored = await session.execute(
            text(
                "SELECT rel_type FROM memory_relations "
                "WHERE source_memory_id = CAST(:s AS uuid)"
            ),
            {"s": str(newer)},
        )
        assert stored.scalar_one() == "RELATES_TO"

    async def test_a_cross_project_pair_is_rejected_by_the_composite_fk(self, session):
        """The guard is the schema's, not this module's — a cross-project edge is
        unrepresentable rather than merely forbidden."""
        here = await seed_memory(session, project=PROJECT)
        elsewhere = await seed_memory(session, project=OTHER_PROJECT)
        await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await edges.upsert_edge(
                    session,
                    source_memory_id=here,
                    target_memory_id=elsewhere,
                    rel_type="RELATES_TO",
                    project=PROJECT,
                    pass_key="near_duplicate",
                    block={},
                )

    async def test_deleting_an_endpoint_removes_the_edge(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()
        await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="RELATES_TO",
            project=PROJECT,
            pass_key="near_duplicate",
            block={},
        )
        assert await read_edge(session, newer, older) is not None

        await session.execute(
            text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(older)},
        )
        assert await read_edge(session, newer, older) is None

    @pytest.mark.parametrize(
        "existing",
        [None, {}, {"note": "x"}, {"dream": {"proximity": {"w": 1}}}],
        ids=["null", "empty", "foreign-key", "sibling-pass"],
    )
    async def test_the_block_lands_whatever_shape_the_row_already_had(
        self, session, existing
    ):
        """The nested `jsonb_set`'s reason for existing.

        A single `jsonb_set` on the two-element path returns its target
        unchanged — no error — for the first three shapes, so the block would
        never be written and `created=false` would still be reported.
        """
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await session.flush()
        await session.execute(
            text(
                "INSERT INTO memory_relations "
                "(id, source_memory_id, target_memory_id, rel_type, project, "
                " properties) "
                "VALUES (CAST(:id AS uuid), CAST(:s AS uuid), CAST(:t AS uuid), "
                "'RELATES_TO', CAST(:p AS text), CAST(:props AS jsonb))"
            ),
            {
                "id": str(new_id()),
                "s": str(newer),
                "t": str(older),
                "p": PROJECT,
                "props": None if existing is None else json.dumps(existing),
            },
        )

        write = await edges.upsert_edge(
            session,
            source_memory_id=newer,
            target_memory_id=older,
            rel_type="RELATES_TO",
            project=PROJECT,
            pass_key="near_duplicate",
            block={"score": 0.91},
        )
        assert write.created is False

        row = await read_edge(session, newer, older)
        assert edges.pass_block_of(row, "near_duplicate") == {"score": 0.91}
        if existing:
            for key, value in existing.items():
                if key == "dream":
                    assert row["properties"]["dream"]["proximity"] == value["proximity"]
                else:
                    assert row["properties"][key] == value
