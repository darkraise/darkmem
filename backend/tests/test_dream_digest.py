"""T2.89 — the digest read side reports what an undo restored.

`UndoBatchResponse.undone[]` (the undo door's own response) has always carried
per-action `restored` / `not_restored` — see `tests/test_dream_undo.py`'s
`TestUndoJournal`. Before this task the *read* side, `DreamActionView` /
`DreamAction`, dropped both lists on the floor: a re-read after the one-shot
undo toast disappeared could say an action was undone and by whom, never what
came back. `dream_undo._journal_undo` already writes both lists into the
`undone` event's own payload (`payload["restored"]`, `payload["not_restored"]`),
so this is read-side reconstruction from the existing journal — no new column,
no new query, and no widening of the events-retention question CLAUDE.md's
"Events journal" section already flags as open.

`read_cycle_actions`'s `_UNDONE_FOR_ACTIONS` query is unchanged: it was already
selecting `payload`; this only reads two more keys out of it. It stays bounded
the same way it already was — `created_at >= :since` on a RANGE-partitioned
table prunes to the surrounding monthly children, the same pruning
`tests/test_dream_undo.py::TestDigest::test_a_row_outside_the_window_is_absent`
exercises. No `WHERE id = :id` by-id scan is introduced.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.repositories import memory_relations as edges
from app.services import dream_digest as digest
from app.services import dream_journal as journal
from app.services import dream_undo as undo
from app.services import memory_dream as dream
from app.utils.ids import new_id
from tests.test_dream_undo import (
    NOW,
    committing,
    memory_row_of,
    produce_refine,
    produce_subsume,
    project,
    seed_memory,
    undo_ids,
)

__all__ = ["committing", "project"]  # re-exported fixtures, used by pytest


class TestRestoredRoundTrip:
    async def test_restored_and_not_restored_survive_the_round_trip(
        self, committing, project
    ):
        """The invariant-bearing case. A subsume's inverse restores exactly
        `status` / `superseded_by` and deliberately excludes three other
        fields (`_invert_subsume`) — genuinely disjoint, non-empty lists, so a
        read side that could only echo "restored everything" or "restored
        nothing" cannot pass this by accident.
        """
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        batch = await undo_ids(committing, event_id, actor="curator")

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        assert len(actions) == 1
        action = actions[0]

        assert action.undone is True
        assert set(action.restored) == {"status", "superseded_by"}
        assert set(action.not_restored) == {
            "updated_at", "events", "metadata.dream.undone_subsume",
        }
        # The two lists are disjoint, so a read side that collapsed them into
        # one bucket (or swapped them) is also caught here.
        assert set(action.restored).isdisjoint(action.not_restored)

        # Parity with the undo door's own one-shot response — the read side
        # is not allowed to invent a different account of the same undo.
        undone_response = batch.undone[0]
        assert set(action.restored) == set(undone_response.restored)
        assert set(action.not_restored) == set(undone_response.not_restored)

    async def test_a_not_yet_undone_action_reports_empty_lists(
        self, committing, project
    ):
        """The companion case: `restored` / `not_restored` are not a stale
        leftover from some other read — they are empty until an `undone`
        event actually exists for this action, and `undone` is what
        disambiguates that from "restored nothing"."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        assert len(actions) == 1
        assert actions[0].undone is False
        assert actions[0].restored == ()
        assert actions[0].not_restored == ()

    async def test_two_actions_in_one_cycle_keep_their_own_lists(
        self, committing, project
    ):
        """A subsume and a refine undone in the same batch must not bleed
        their per-action lists into each other on the read side."""
        cycle = str(new_id())
        _, _, subsume_id = await produce_subsume(committing, project, cycle_id=cycle)
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle, tags=("t213-alpha",)
        )

        await undo_ids(committing, subsume_id, refine_id, actor="curator")

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        by_action = {view.action: view for view in actions}

        assert set(by_action["subsume"].restored) == {"status", "superseded_by"}
        assert set(by_action["refine"].restored) == {"summary", "tags"}
        assert by_action["subsume"].restored != by_action["refine"].restored


async def _derived_edge(factory, project, *, cycle_id, label):
    async with factory() as session:
        older = await seed_memory(
            session, project=project, content=f"{label} a", created_at=NOW
        )
        newer = await seed_memory(
            session, project=project, content=f"{label} b",
            created_at=NOW + timedelta(hours=1),
        )
        await session.commit()
    signal = dream.SIGNAL_EMBEDDING_PROXIMITY
    edge = dream.DerivedEdge(
        source=memory_row_of(
            newer, project=project, content=f"{label} b",
            created_at=NOW + timedelta(hours=1),
        ),
        target=memory_row_of(older, project=project, content=f"{label} a"),
        signal=signal,
        scores={signal: 0.95},
    )
    async with factory() as session:
        assert await dream.write_derived_edge(
            session, edge, cycle_id=cycle_id, outcome=dream.DerivationOutcome()
        )
        await session.commit()
    return str(newer), str(older), edge.rel_type


async def test_derivation_associate_is_undoable_exactly_when_undo_succeeds(
    committing, project
):
    """The flag must read the derivation pass's block, not the near-duplicate
    one: a sibling block on the same row leaves the action undoable, and a
    rewrite of this pass's own block makes it not."""
    cycle = str(new_id())
    shared = await _derived_edge(committing, project, cycle_id=cycle, label="shared")
    rewritten = await _derived_edge(committing, project, cycle_id=cycle, label="moved")
    async with committing() as session:
        await edges.upsert_edge(
            session, source_memory_id=shared[0], target_memory_id=shared[1],
            rel_type=shared[2], project=project,
            pass_key=journal.NEAR_DUPLICATE_PASS,
            block={"kind": "duplicate_candidate", "score": 0.99},
        )
        signal = dream.SIGNAL_EMBEDDING_PROXIMITY
        await edges.upsert_edge(
            session, source_memory_id=rewritten[0], target_memory_id=rewritten[1],
            rel_type=rewritten[2], project=project,
            pass_key=journal.DERIVATION_PASS,
            block=dream.derived_block(
                signal=signal, scores={signal: 0.91}, derived_at="later"
            ),
        )
        await session.commit()

    async with committing() as session:
        views = await digest.annotate_undoability(
            session, await digest.read_cycle_actions(session, cycle)
        )
    by_source = {view.object_id: view for view in views}

    assert by_source[shared[0]].undoable is True
    assert by_source[rewritten[0]].undoable is False
    await undo_ids(committing, by_source[shared[0]].event_id)
    with pytest.raises(undo.UndoRefused):
        await undo_ids(committing, by_source[rewritten[0]].event_id)
