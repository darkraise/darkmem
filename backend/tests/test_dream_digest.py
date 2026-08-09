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

from app.services import dream_digest as digest
from app.utils.ids import new_id
from tests.test_dream_undo import committing, produce_refine, produce_subsume, project, undo_ids

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
        memory, refine_id = await produce_refine(committing, project, cycle_id=cycle)

        await undo_ids(committing, subsume_id, refine_id, actor="curator")

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        by_action = {view.action: view for view in actions}

        assert set(by_action["subsume"].restored) == {"status", "superseded_by"}
        assert set(by_action["refine"].restored) == {"summary", "tags"}
        assert by_action["subsume"].restored != by_action["refine"].restored
