"""T2.13 — the dream digest and its per-action / per-batch undo.

Doc 08 §7, doc 13 §6.3. Three Done-whens, and every one of them is a claim a
green suite can make vacuously:

- *"Undo restores exact prior state"* passes trivially if the assertions only
  check that no exception was raised. Every inverse here is asserted field by
  field, against the exclusion table in the plan's D2, and each exclusion is
  itself a first-class assertion rather than an unmentioned gap.
- *"Batch undo is atomic"* is a claim about what the code can *express*, so the
  behavioural tests are backed by an AST scan over ``dream_undo.py`` for the
  five shapes that could produce or report a partial outcome.
- *"Undo itself journals"* passes with the journal readback deleted if the test
  asserts the row is present. It is asserted the other way round instead: with
  ``record_event`` stubbed to a no-op, the *restore* must be absent.
"""
from __future__ import annotations

import json
import logging
import pathlib

import pytest

from app.services import dream_journal as journal
from app.services import events as events_module
from app.services import memory_dream as dream
from tests.test_dream_jobs import dream_job_implementation_modules

BACKEND = pathlib.Path(__file__).resolve().parent.parent


# ── Step 1: the vocabulary ───────────────────────────────────────────────


class TestVocabulary:
    def test_undone_is_in_the_closed_vocabulary(self):
        """T-VOC1."""
        assert "undone" in events_module.EVENT_TYPES

    async def test_journalling_undone_warns_about_nothing(self, session, caplog):
        """T-VOC2 — the non-vacuous half.

        T-VOC1 alone is a tautology over a list literal: it would keep passing
        if `record_event` never consulted the list. This one asserts the
        emitter's own view, through the frozenset it actually checks.
        """
        with caplog.at_level(logging.WARNING, logger=events_module.__name__):
            await events_module.record_event(
                session,
                event_type="undone",
                object_type="memory",
                payload={"probe": True},
            )
        assert not [
            record for record in caplog.records
            if "closed vocabulary" in record.getMessage()
        ]

    async def test_an_unknown_type_still_warns(self, session, caplog):
        """T-VOC2's negative control: the check the previous test relies on is
        live, so its silence means the value was admitted rather than that the
        warning was removed."""
        with caplog.at_level(logging.WARNING, logger=events_module.__name__):
            await events_module.record_event(
                session,
                event_type="undone_but_not_really",
                object_type="memory",
                payload={"probe": True},
            )
        assert [
            record for record in caplog.records
            if "closed vocabulary" in record.getMessage()
        ]


# ── Step 2: the shared vocabulary module ─────────────────────────────────

# Everything the producer used to assign and now imports. The move is a pure
# re-export, so each name must still resolve off the producer's module and be
# the *same object* — a duplicated literal would satisfy an equality check.
MOVED_NAMES = (
    "EVENT_TYPE",
    "OBJECT_TYPE",
    "DETECTOR",
    "ACTION_SUBSUME",
    "ACTION_ASSOCIATE",
    "ACTION_REFINE",
    "NEAR_DUPLICATE_PASS",
    "HYGIENE_STATE_OPEN",
    "REFINE_MARKER_PATH",
    "refine_marker_of",
    "content_sha",
)


class TestSharedVocabulary:
    @pytest.mark.parametrize("name", MOVED_NAMES)
    def test_the_producer_re_exports_the_moved_name(self, name):
        """T-VOC3. Written to hold under either of D1's two layouts: it
        compares objects across the two modules rather than asserting where
        the assignment lives."""
        assert hasattr(dream, name), (
            f"{name} no longer resolves off the producer's module, so the "
            "move stopped being a pure re-export and T2.12's suite is only "
            "passing because nothing reads it"
        )
        assert getattr(dream, name) is getattr(journal, name)

    def test_the_shared_module_is_outside_the_forbidden_set(self):
        """T-VOC5, asserted from this lane rather than trusted.

        The whole module layout rests on invariant 15's forbidden set being
        derived ONE HOP from the umbrella's imports. A rebuild that computed
        the transitive closure would pull this module in the moment the
        producer imports it, and the undo service importing it would then fail
        the build. Pinned here so that regression fails by name instead of
        surfacing as an unexplained import error somewhere else.
        """
        assert "dream_journal" not in dream_job_implementation_modules()
