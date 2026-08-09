"""T2.17 — strip-before-rewrite idempotence and endpoint self-healing.

Doc 08 §5.5. Two Done-whens, both already mechanically true in the tree
before this file existed: T2.16 built the derivation strip as
`clear_pass_block` then `delete_edge` only on `exclusive`, and doc 08 §5.5 /
doc 04 §8.2 put composite `(memory_id, project)` FKs with `ON DELETE CASCADE`
on both `memory_relations` endpoints. This file's job is to prove both
properties non-vacuously rather than to build new mechanism — a negative that
passes because the property was never reachable proves nothing, which is the
exact shape T2.16's own review caught twice (I1, I2).

Every property below carries either a companion assertion or an in-tree
mutation that must turn it red, so the property is demonstrated to be *held*,
not merely *unreachable*.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories import memory_relations as edges
from app.services import dream_journal as journal
from app.services import memory_dream as dream

from tests.test_memory_relation_derivation import (
    FP,
    build_overlap_pair,
    committing,
    derivation_events,
    derive,
    pass_edges,
    project,
    read_seeds,
    seed_memory,
    seed_partition,
)


@pytest.fixture(autouse=True)
async def _partition(committing):
    """`derive`'s default fingerprint is `FP`, so the proximity arm probes
    its partition table on every call even when a test only cares about the
    overlap arm. T2.16's own suite gets this for free because an earlier
    test in that file creates the table first and the session-scoped
    database fixture keeps it for the rest of the run; this file is a
    separate module and must not depend on that ordering accident."""
    async with committing() as session:
        await seed_partition(session, FP)
        await session.commit()


# ── Done-when 1: re-derivation is idempotent ──────────────────────────────


class TestRederivationIsIdempotent:
    async def test_two_runs_over_an_unchanged_corpus_are_byte_identical(
        self, committing, project
    ):
        """The strip's write-then-strip cycle must be a true no-op on replay:
        same edges, same blocks, and the append-only journal gains nothing
        for a pair that never moved."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])

        await derive(committing, seeds)
        after_first = await pass_edges(committing, project)

        second_run = await derive(committing, seeds)
        after_second = await pass_edges(committing, project)

        def comparable(rows):
            out = []
            for row in rows:
                block = dict(edges.pass_block_of(row, journal.DERIVATION_PASS))
                # `derived_at` moves by construction on every run; nothing
                # else may.
                block.pop("derived_at")
                out.append(
                    (row["source"], row["target"], row["rel_type"], block)
                )
            return out

        assert comparable(after_first) == comparable(after_second)
        assert second_run.derived == 0
        assert second_run.unchanged == 1
        assert second_run.stripped == 0
        assert len(await derivation_events(committing, project)) == 1

    async def test_a_changed_corpus_produces_a_different_set(
        self, committing, project
    ):
        """Non-vacuity for the test above: byte-identical replay is not the
        trivial equality of two empty runs, nor of a pass that ignores its
        inputs. A real corpus change must move the edge set."""
        first, second, lonely = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second, lonely])
        await derive(committing, seeds)
        before = {
            (row["source"], row["target"])
            for row in await pass_edges(committing, project)
        }

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE entities SET memory_ids = memory_ids "
                    "  || CAST(:extra AS uuid[]) WHERE name LIKE :like"
                ),
                {"extra": [str(lonely)], "like": f"t216-shared-%-{project}"},
            )
            await session.commit()
        await derive(committing, seeds)
        after = {
            (row["source"], row["target"])
            for row in await pass_edges(committing, project)
        }

        assert after != before
        assert len(after) > len(before)

    async def test_without_the_unchanged_skip_replay_would_not_be_idempotent(
        self, committing, project, monkeypatch
    ):
        """Mutation drill, committed rather than run-and-discarded. The two
        properties above hold only because `write_derived_edge` skips a
        block that has not moved (`_derived_is_unchanged`). Disabling that
        skip must make an otherwise-identical second run write and journal
        again — proving the earlier assertions were not vacuously true of a
        pass that happens to no-op on every second call for some unrelated
        reason (e.g. candidate generation finding nothing on any run)."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])
        await derive(committing, seeds)
        assert len(await derivation_events(committing, project)) == 1

        monkeypatch.setattr(
            dream, "_derived_is_unchanged", lambda existing, block: False
        )
        second_run = await derive(committing, seeds)

        assert second_run.derived == 1
        assert second_run.unchanged == 0
        assert len(await derivation_events(committing, project)) == 2


# ── Done-when 2: a deleted endpoint leaves no dangling edge ──────────────


async def seed_edge(
    factory, *, project: str, source, target, rel_type: str = "RELATES_TO"
) -> None:
    """A `memory_relations` row written directly through the repository,
    bypassing the derivation pass entirely — this file's second clause is a
    test against the schema, not a re-run of the strip, so the edge under
    test must not owe its removal to anything the pass itself would do."""
    async with factory() as session:
        await edges.upsert_edge(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
            project=project,
            pass_key=journal.DERIVATION_PASS,
            block={
                "kind": "derived",
                "signal": "entity_overlap",
                "signals": {"entity_overlap": 1.0},
                "score": 1.0,
                "derived_at": "2026-08-05T00:00:00+00:00",
            },
        )
        await session.commit()


async def edge_row(factory, *, source, target, rel_type: str = "RELATES_TO"):
    async with factory() as session:
        return await edges.get_edge(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
        )


async def memory_exists(factory, memory_id) -> bool:
    async with factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM memories WHERE id = CAST(:id AS uuid)"),
            {"id": str(memory_id)},
        )
        return result.first() is not None


class TestEndpointSelfHealing:
    """Endpoint self-healing is structural, not code: composite
    `(memory_id, project)` FKs with `ON DELETE CASCADE` on both endpoints
    make a dangling edge and a cross-project edge equally unrepresentable.
    These tests exercise the schema directly rather than adding an
    application-level sweep."""

    async def test_deleting_the_target_endpoint_removes_the_edge(
        self, committing, project
    ):
        async with committing() as session:
            source = await seed_memory(session, project=project, content="alpha")
            target = await seed_memory(session, project=project, content="beta")
            await session.commit()
        await seed_edge(committing, project=project, source=source, target=target)

        # The edge genuinely exists first — otherwise its disappearance
        # after the delete would prove nothing.
        assert await edge_row(committing, source=source, target=target) is not None

        async with committing() as session:
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(target)},
            )
            await session.commit()

        assert await edge_row(committing, source=source, target=target) is None

    async def test_deleting_the_source_endpoint_also_removes_the_edge(
        self, committing, project
    ):
        """The two endpoint FKs are independent constraints
        (`fk_memory_relations_source` / `_target`); only exercising one
        direction would leave the other unproven."""
        async with committing() as session:
            source = await seed_memory(session, project=project, content="alpha")
            target = await seed_memory(session, project=project, content="beta")
            await session.commit()
        await seed_edge(committing, project=project, source=source, target=target)

        assert await edge_row(committing, source=source, target=target) is not None

        async with committing() as session:
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(source)},
            )
            await session.commit()

        assert await edge_row(committing, source=source, target=target) is None

    async def test_without_the_cascade_the_delete_is_refused_outright(
        self, committing, project
    ):
        """Non-vacuity for the two tests above: the `ON DELETE CASCADE`
        clause is what removes the edge, not some incidental cleanup that
        would leave the same end state regardless. Swap the target FK to
        `NO ACTION` inside a transaction this test never commits, and the
        identical delete must be refused by Postgres outright rather than
        quietly leaving a dangling row or succeeding some other way. The
        ALTER, and the delete attempt it guards, live in one session whose
        transaction rolls back automatically on the raised error — so the
        schema is restored to `CASCADE` the moment this test ends."""
        async with committing() as session:
            source = await seed_memory(session, project=project, content="alpha")
            target = await seed_memory(session, project=project, content="beta")
            await session.commit()
        await seed_edge(committing, project=project, source=source, target=target)

        with pytest.raises(IntegrityError) as excinfo:
            async with committing() as session:
                await session.execute(
                    text(
                        "ALTER TABLE memory_relations "
                        "DROP CONSTRAINT fk_memory_relations_target"
                    )
                )
                await session.execute(
                    text(
                        "ALTER TABLE memory_relations "
                        "ADD CONSTRAINT fk_memory_relations_target "
                        "FOREIGN KEY (target_memory_id, project) "
                        "REFERENCES memories (id, project) ON DELETE NO ACTION"
                    )
                )
                await session.execute(
                    text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                    {"id": str(target)},
                )
                await session.commit()

        assert "fk_memory_relations_target" in str(excinfo.value)

        # The failed transaction rolled back in full: the constraint is back
        # to CASCADE, and both the memory row and the edge survive untouched.
        assert await edge_row(committing, source=source, target=target) is not None
        assert await memory_exists(committing, target) is True

        # And with the real schema restored, the same delete now succeeds
        # and heals the edge exactly as the tests above proved.
        async with committing() as session:
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(target)},
            )
            await session.commit()
        assert await edge_row(committing, source=source, target=target) is None
