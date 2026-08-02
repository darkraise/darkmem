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

import pytest

from app.services import events as events_module


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
