"""T3.12 — inject records in the journal (doc 13 §6.5).

The done-when is two claims: each inject writes an event carrying the item ids
and the budget used, and the records surface in the timeline and calendar.

The second is the one worth testing hard. "Surfaces in the timeline" is easy to
assert against a hand-built row and easy to get wrong against the real readers,
which filter by project, bucket by a UTC day expression, and — for the timeline
— key on ``object_id``. This suite drives the shipped readers.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.services import inject_journal as ij
from app.services.events import EVENT_TYPES, OBJECT_TYPES, calendar_counts, list_events

pytestmark = pytest.mark.asyncio

PROJECT = "t3-12-inject"


async def _push(session, **kw):
    defaults = dict(
        tool="claude-code", context_file="CLAUDE.md", project=PROJECT,
        memory_ids=[uuid4()], fact_ids=[uuid4(), uuid4()],
        budget_tokens=4000, tokens_used=1200,
    )
    defaults.update(kw)
    await ij.record_inject(session, **defaults)
    await session.flush()
    return defaults


async def _payloads(session, event_type: str) -> list[dict]:
    rows = await session.execute(
        text("SELECT payload FROM events WHERE event_type = CAST(:t AS text) "
             "AND project = CAST(:p AS text) ORDER BY created_at, id"),
        {"t": event_type, "p": PROJECT},
    )
    return [row[0] for row in rows.all()]


# ─────────────── clause 1: the ids and the budget ───────────────


class TestWhatThePushRecords:
    async def test_the_item_ids_are_recorded_per_layer(self, session):
        """Kept as three lists, not merged: a reader asking whether a *fact*
        was injected cannot recover the layer from a flat list without
        querying every table for every id."""
        sent = await _push(session)

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]
        assert payload["memory_ids"] == [str(sent["memory_ids"][0])]
        assert payload["fact_ids"] == [str(i) for i in sent["fact_ids"]]
        assert payload["article_ids"] == []

    async def test_the_budget_and_the_spend_are_both_recorded(self, session):
        """One without the other is not diagnostic: a push that used 40 of
        4000 tokens and one that hit its ceiling look identical from the id
        list, and they mean different things about what was left out."""
        await _push(session, budget_tokens=4000, tokens_used=3999)

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]
        assert (payload["budget_tokens"], payload["tokens_used"]) == (4000, 3999)

    async def test_the_target_is_named_so_the_record_says_where(self, session):
        await _push(session, tool="cursor", context_file=".cursor/rules/darkmem.mdc")

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]
        assert payload["tool"] == "cursor"
        assert payload["context_file"] == ".cursor/rules/darkmem.mdc"

    async def test_served_order_is_preserved_not_sorted(self, session):
        """The fill is truth-first (doc 15 §3.4), so the sequence records the
        priority the budget actually spent. Sorting would erase it."""
        ordered = [uuid4() for _ in range(5)]
        await _push(session, memory_ids=ordered, fact_ids=[])

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]
        assert payload["memory_ids"] == [str(i) for i in ordered]

    async def test_no_injected_content_is_copied_into_the_payload(self, session):
        """Write-time minimization, and it binds hardest here: this fires on
        every session start of every client, into a table that outlives the
        deletion of what it describes."""
        await _push(session)

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]

        # An allowlist, not a substring hunt. The first version searched the
        # serialised blob for "fact" and failed on the `fact_ids` key it was
        # meant to permit -- and a substring check would in any case pass for
        # a payload that carried prose under an unlisted key. Pinning the key
        # set means a new field has to be added here deliberately.
        assert set(payload) == {
            "tool", "context_file", "memory_ids", "fact_ids", "article_ids",
            "budget_tokens", "tokens_used",
        }
        # And nothing under those keys is free text: the id lists hold ids.
        for key in ("memory_ids", "fact_ids", "article_ids"):
            for value in payload[key]:
                UUID(value)

    async def test_injected_ids_follow_doc_15_s_truth_first_fill_order(self, session):
        """Task review, Important. The helper iterated memories first while its
        docstring claimed "served order" — inverting the very ordering it
        promised. Doc 15 §3.4 fills facts, then articles, then memory
        summaries."""
        facts = [uuid4(), uuid4()]
        articles = [uuid4()]
        memories = [uuid4()]
        await _push(session, memory_ids=memories, fact_ids=facts, article_ids=articles)

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]

        assert ij.injected_ids(payload) == [
            *[str(i) for i in facts], *[str(i) for i in articles],
            *[str(i) for i in memories],
        ]

    async def test_the_writer_reports_whether_the_row_landed(self, session):
        """The journal is this module's deliverable, so a push whose record
        silently failed is the silent context swap invariant 14 forbids. The
        writer does not raise — T2.113's strict contract belongs to the ladder
        — but it must tell its caller, which is the only way T3.10 can."""
        landed = await ij.record_inject(
            session, tool="claude-code", context_file="CLAUDE.md", project=PROJECT
        )
        assert landed is True

        child = (await session.execute(
            text("SELECT 'events_' || to_char(date_trunc('month', now()), 'YYYYMM')")
        )).scalar_one()
        await session.execute(text(f"DROP TABLE {child}"))

        lost = await ij.record_inject(
            session, tool="claude-code", context_file="CLAUDE.md", project=PROJECT
        )
        assert lost is False

    async def test_an_empty_push_still_journals(self, session):
        """"Nothing was injected" is an answer the human needs — it is the
        difference between a quiet system and a broken one."""
        await _push(session, memory_ids=[], fact_ids=[], article_ids=[])

        payload = (await _payloads(session, ij.INJECT_EVENT))[0]
        assert ij.injected_ids(payload) == []


class TestTheCurb:
    async def test_a_curb_is_its_own_event_not_an_empty_push(self, session):
        """A reader counting injections would otherwise count a curb as a push
        of nothing, and the question a curb is asked about is *when the human
        turned it off*."""
        await ij.record_inject_curbed(
            session, tool="claude-code", context_file="CLAUDE.md",
            project=PROJECT, reason="too noisy",
        )
        await session.flush()

        assert len(await _payloads(session, ij.INJECT_CURBED_EVENT)) == 1
        assert await _payloads(session, ij.INJECT_EVENT) == []

    async def test_both_types_are_in_the_closed_vocabulary(self):
        assert ij.INJECT_EVENT in EVENT_TYPES
        assert ij.INJECT_CURBED_EVENT in EVENT_TYPES
        assert ij.OBJECT_TYPE in OBJECT_TYPES


# ─────────────── clause 2: the records surface ───────────────


class TestTheRecordsSurface:
    async def test_an_inject_appears_in_the_events_list_reader(self, session):
        await _push(session)

        rows, total = await list_events(
            session, project=PROJECT, event_type=ij.INJECT_EVENT, limit=10, offset=0
        )
        assert total == 1 and rows[0]["event_type"] == ij.INJECT_EVENT

    async def test_an_inject_is_counted_by_the_calendar_reader(self, session):
        """Driven through the shipped reader rather than asserted against a
        hand-built bucket: the calendar's day expression must match
        `ix_events_day`'s immutable UTC expression verbatim, so a test that
        recomputed the bucket itself would pass while the real one missed."""
        await _push(session)

        now = datetime.now(timezone.utc)
        buckets = await calendar_counts(
            session, project=PROJECT,
            since=now - timedelta(days=1), until=now + timedelta(days=1),
        )
        assert sum(b["count"] for b in buckets) >= 1

    async def test_the_project_filter_reaches_it(self, session):
        """An inject records this installation's own behaviour, but it is
        still project-scoped: a reader looking at one project must not be
        shown another's pushes."""
        await _push(session)
        await ij.record_inject(
            session, tool="cline", context_file=".clinerules/darkmem.md",
            project="somewhere-else",
        )
        await session.flush()

        _, total = await list_events(
            session, project=PROJECT, event_type=ij.INJECT_EVENT, limit=10, offset=0
        )
        assert total == 1

    async def test_the_frontend_map_accounts_for_both_now_that_they_emit(self):
        """The map's own rule: a value with a live emitter owes either a tab or
        a recorded exclusion, and this task is the emitter. Its docstring said
        deciding was "a design call this task does not own" — T3.12 owns it.
        """
        taxonomy = (
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "frontend/src/features/activity/event-taxonomy.ts"
        ).read_text()
        for value in (ij.INJECT_EVENT, ij.INJECT_CURBED_EVENT):
            assert f'"{value}"' in taxonomy, value
