"""T2.60 — the supersession-signal promotion blocker (spec §2.1 condition 4).

Doc 08 §4.1 dropped the supersession half of promotion condition 4 by drift;
the Tier-3 ruling of 2026-07-29 restored it. This suite pins the four Done-when
clauses and, separately, every word of the predicate that was a decision:

* **D1** the predicate is deterministic — no LLM, no model call, no clock, no
  configuration knob that could soften it.
* **D2** a fact that meets its N-origin bar but carries a superseded live
  source does **not** promote — with the no-signal control beside it, because a
  hold test without its control proves only that the fact failed to promote,
  not that this blocker is what held it.
* **D3** the signal writes no ``disputed`` and causes no demotion. Both are
  negatives, so both are asserted on a fact where the opposite *could* have
  happened: an already-``corroborated`` fact carrying the signal.
* **D4** the blocked hold is journaled with its own flag, and lands in the
  promotion-rate denominator T2.51's runner derives.

The predicate decisions each get a rule test that fails if that rule is
deleted: the applied-status reading (and therefore the inherited speculative
gate), the newer-superseder comparison, the memory-kind filter, and the
any-source rather than all-sources quantifier.
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import supersession_hold as hold_module
from app.services.fact_provenance import memory_source_ref
from app.services.supersession import detect_supersessions
from app.services.supersession_hold import (
    adjudicate_supersession_hold,
    detect_supersession_hold,
)
from app.services.verification_ladder import LadderConfig, decide, recompute_fact
from app.repositories.fact_sources import OriginObservation, OriginProfile

T0 = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "supersession-blocker"


# ─────────────────────────────── fixtures ───────────────────────────────


def _code_only(source: str) -> str:
    """``source`` with every docstring and comment stripped.

    The structural scans below look for a token appearing in *executable code*.
    Run against raw text they also read prose, so a docstring that merely
    explains why the module reads no clock would fail the no-clock test — the
    guard would be reporting on its own documentation. ``ast.unparse`` drops
    comments for free; the docstring nodes have to be removed by hand.
    """
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


async def _memory(
    session, *, content: str, technologies=(), created_at=None, id=None
) -> Memory:
    row = Memory(
        id=id or uuid.uuid4(),
        content=content,
        source="test",
        source_agent=None,
        memory_type=None,
        importance=0.5,
        metadata_={},
        project=PROJECT,
        status="active",
        technologies=list(technologies),
        created_at=created_at or T0,
    )
    session.add(row)
    await session.flush()
    return row


async def _fact(session, *, key: str, status: str | None = None) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=key,
        subject_name="darkmem",
        object_name=key,
        rel_type="USES",
        fact=f"darkmem uses {key}",
        reference_time=T0,
        project=PROJECT,
    )
    if status is not None:
        # Raw SQL rather than the repository writer: seeding through
        # `set_verification_status` would itself journal a transition and
        # pollute the event counts D4 asserts on the ladder's own decisions.
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = "
                "CAST(:s AS text) WHERE id = CAST(:id AS uuid)"
            ),
            {"s": status, "id": row["id"]},
        )
    return row["id"]


async def _source(session, fact_id, *, memory: Memory | None = None, origin: str,
                  kind: str = "memory", ref: str | None = None) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref if ref is not None else memory_source_ref(memory.id),
        origin_key=origin,
    )


async def _supersede(session, *, old: Memory, new: Memory) -> None:
    """Flip ``old`` to superseded by ``new`` directly, bypassing the detector.

    Used only where the case under test is one the write-time detector cannot
    produce (an older superseder). The headline tests drive the real detector
    instead, so the suite proves the coupling rather than assuming it.
    """
    await session.execute(
        text(
            "UPDATE memories SET status='superseded', superseded_by=CAST(:new AS uuid) "
            "WHERE id = CAST(:old AS uuid)"
        ),
        {"new": str(new.id), "old": str(old.id)},
    )


async def _status(session, fact_id) -> str:
    return (
        await session.execute(
            text(
                "SELECT verification_status FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(fact_id)},
        )
    ).scalar_one()


async def _events(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type='verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [row[0] for row in result.all()]


async def _at_bar_fact(session, *, key: str, status: str | None = None):
    """A fact meeting N=2, sourced by one memory and one repository.

    The *diversity* gate, not the time gate, and the choice is forced rather
    than stylistic: ``OriginProfile``'s time gap is measured over
    ``fact_sources.created_at`` — when the provenance row was recorded — not
    over the memory's own ``created_at``. Two memories seeded microseconds
    apart in one test therefore never clear a seven-day gap however their
    memory rows are dated, so a two-memory fixture silently sits below N=3 and
    every "blocked" assertion would pass for the wrong reason.

    The memory-kind origin is the one the blocker can reach; the ``code``
    origin only carries the bar.
    """
    m_old = await _memory(session, content="we run on qdrant", technologies=["qdrant"])
    fact_id = await _fact(session, key=key, status=status)
    await _source(session, fact_id, memory=m_old, origin="sess-a")
    await _source(session, fact_id, origin="repo-b", kind="code", ref=f"repo:{key}")
    await session.commit()
    return fact_id, m_old


async def _replacement(session, *, replaces: str, text_: str, created_at) -> Memory:
    """A memory carrying a real REPLACES relation, run through the detector."""
    new = await _memory(session, content=text_, created_at=created_at)
    await session.flush()
    flipped = await detect_supersessions(
        session,
        new_memory_id=new.id,
        new_memory_text=text_,
        new_memory_created_at=created_at,
        project=PROJECT,
        new_relations=[{"type": "REPLACES", "target": replaces}],
        now=created_at,
    )
    await session.commit()
    return new, flipped


# ───────────────── D1 — deterministic: no model, no knob, no clock ─────────────────


class TestTheBlockerIsDeterministic:
    def test_the_module_makes_no_model_call(self):
        """Structural, the way the veto's tests assert it.

        A promotion path that reached an LLM would put a model call on the
        deterministic half of condition 4 — the half that exists precisely
        because the expensive half is 6-hourly and judge-gated.
        """
        source = _code_only(Path(inspect.getfile(hold_module)).read_text())
        forbidden = (
            "llm_orchestrator",
            "LLMOrchestrator",
            "chat_completion",
            "embed",
            "openai",
            "adjudicate_contradiction",
        )
        hits = [token for token in forbidden if token in source]
        assert not hits, f"the supersession blocker reached a model: {hits}"

    def test_the_module_reads_no_configuration(self):
        source = _code_only(Path(inspect.getfile(hold_module)).read_text())
        for token in ("Config", "get_feature_flags", "config_schema", "LADDER_CONFIG"):
            assert token not in source, (
                f"the blocker reached configuration ({token}). Like the veto it is "
                "not a weight and not a threshold; a knob here would be a way to "
                "turn a truth guard down without a measurement."
            )

    def test_the_module_reads_no_clock(self):
        """Every comparison is between two stored timestamps, never against now.

        A wall-clock read would make a replay of identical rows answer
        differently as the calendar moves — the property `decide` is built
        around and which this input must not break from outside.
        """
        source = _code_only(Path(inspect.getfile(hold_module)).read_text())
        for token in ("now(", "utcnow", "today(", "time.time", "monotonic"):
            assert token not in source, f"{token} on the deterministic path"

    def test_the_detector_signature_carries_no_tunable(self):
        for func in (detect_supersession_hold, adjudicate_supersession_hold):
            assert list(inspect.signature(func).parameters) == ["session", "fact_id"]

    def test_decide_stays_pure_with_the_new_input(self):
        """The blocker is adjudicated in the applier, never inside `decide`."""
        source = _code_only(inspect.getsource(decide))
        # Whole words only: `supersession_blocked` contains "session" as a
        # substring, so a bare `in` check flags the very parameter this task
        # adds and the guard would fail on correct code.
        for token in ("session", "await", "execute", "supersession_hold"):
            assert not re.search(rf"\b{token}\b", source), (
                f"`decide` reached {token!r}; the purity boundary is deliberate "
                "(T2.03) and the blocker belongs on the applier's side of it, "
                "exactly like the contradiction verdict"
            )


# ───────────────── D2 — an at-bar fact with a superseded source holds ─────────────────


class TestTheBlockWithholdsPromotion:
    async def test_an_at_bar_fact_with_a_superseded_source_holds_at_candidate(
        self, session
    ):
        """The ruling's constructed scenario, end to end through the real detector."""
        fact_id, m_old = await _at_bar_fact(session, key="blocked-1")
        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we replaced qdrant with pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert m_old.id in flipped, "fixture failed to produce the signal"

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.origin_count >= decision.required_n, (
            "the fact must MEET its bar, else this proves nothing about the "
            "blocker — an under-sourced fact holds for an unrelated reason"
        )
        assert decision.outcome == "hold"
        assert decision.target_status == "candidate"
        assert decision.supersession_blocked is True
        assert await _status(session, fact_id) == "candidate"

    async def test_the_same_fact_without_the_signal_promotes(self, session):
        """The control. Without it the test above cannot distinguish a working
        blocker from a fact that was never going to promote."""
        fact_id, _ = await _at_bar_fact(session, key="control-1")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "promote"
        assert decision.supersession_blocked is False
        assert await _status(session, fact_id) == "corroborated"

    async def test_one_superseded_source_among_live_ones_is_enough(self, session):
        """The any-source quantifier, not all-sources.

        Refined to all-sources this goes green while the ruling's own v1
        predicate ("at least one") is gone.
        """
        fact_id, m_old = await _at_bar_fact(session, key="any-1")
        # A second memory source the replacement does not touch: its
        # `technologies` do not overlap the REPLACES target, so the detector's
        # third guard spares it and the fact ends with one superseded source
        # and one live one.
        m_live = await _memory(
            session, content="we also run redis", technologies=["redis"]
        )
        await _source(session, fact_id, memory=m_live, origin="sess-c")
        await session.commit()

        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we replaced qdrant with pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert m_old.id in flipped and m_live.id not in flipped, (
            "the fixture must produce a MIXED source set, else this cannot "
            "tell the any-quantifier from an all-quantifier"
        )

        decision = await recompute_fact(session, fact_id)
        await session.commit()
        assert decision.supersession_blocked is True
        assert decision.outcome == "hold"


# ───────────────── D3 — hold only: no `disputed`, no demotion ─────────────────


class TestTheSignalHoldsAndNothingElse:
    async def test_an_already_corroborated_fact_is_not_demoted(self, session):
        """Clause 3's real test: the signal over a fact that HAS the badge.

        Asserting "unchanged" on a candidate proves nothing, because nothing
        would have changed it. This fact could be demoted, and must not be.
        """
        fact_id, m_old = await _at_bar_fact(
            session, key="nodemote-1", status="corroborated"
        )
        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we replaced qdrant with pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert m_old.id in flipped

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "hold"
        assert decision.target_status == "corroborated"
        assert await _status(session, fact_id) == "corroborated"
        # The flag means "withheld a promotion". Nothing was withheld here, and
        # setting it would inflate G-C's blocked count with facts that already
        # hold the badge.
        assert decision.supersession_blocked is False

    async def test_the_signal_never_writes_disputed(self, session):
        """Across both shapes the blocker can reach, no `disputed` is written."""
        for key, seed in (("nodisp-1", None), ("nodisp-2", "corroborated")):
            fact_id, m_old = await _at_bar_fact(session, key=key, status=seed)
            _, flipped = await _replacement(
                session,
                replaces="qdrant",
                text_="we replaced qdrant with pgvector",
                created_at=T0 + timedelta(days=10),
            )
            assert m_old.id in flipped

            decision = await recompute_fact(session, fact_id)
            await session.commit()

            assert decision.target_status != "disputed"
            assert await _status(session, fact_id) != "disputed"
            for payload in await _events(session, fact_id):
                assert payload["after"]["verification_status"] != "disputed"

    def test_no_blocked_grid_position_reaches_disputed_or_demotes(self):
        """Exhaustive over the decision surface, not just the seeded rows.

        `disputed` must be unreachable from this input at every status and
        origin count, and a `corroborated` fact must never be moved down by it.
        """
        for status in ("candidate", "corroborated", "confirmed"):
            for k in (0, 1, 2, 5):
                prof = OriginProfile(
                    fact_id="f",
                    origins=tuple(
                        OriginObservation(
                            origin_key=f"o{i}",
                            source_kinds=("memory",),
                            first_seen=T0,
                            last_seen=T0,
                            row_count=1,
                        )
                        for i in range(k)
                    ),
                )
                blocked = decide(
                    "f", status, prof, LadderConfig(), supersession_blocked=True
                )
                unblocked = decide(
                    "f", status, prof, LadderConfig(), supersession_blocked=False
                )
                assert blocked.target_status != "disputed"
                if status == "corroborated":
                    assert blocked.target_status == unblocked.target_status, (
                        "the blocker moved a corroborated fact; it may only "
                        "withhold a promotion, never demote"
                    )
                if unblocked.outcome == "demote":
                    assert blocked.outcome == "demote", (
                        "the blocker changed a demotion into something else"
                    )


# ───────────────── D4 — the blocked hold journals, and G-C can count it ─────────────────


class TestTheBlockedHoldIsJournaled:
    async def test_a_blocked_hold_journals_with_the_flag(self, session):
        fact_id, m_old = await _at_bar_fact(session, key="journal-1")
        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we replaced qdrant with pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert m_old.id in flipped

        await recompute_fact(session, fact_id)
        await session.commit()

        events = await _events(session, fact_id)
        assert len(events) == 1, (
            "a blocked hold changes no status, so without its own journal "
            "branch it leaves no trace at all — the omission the T2.06 ruling "
            "forbids"
        )
        payload = events[0]
        assert payload["supersession_blocked"] is True
        assert payload["outcome"] == "hold"
        assert payload["before"]["verification_status"] == "candidate"
        assert payload["after"]["verification_status"] == "candidate"
        assert payload["origin_count"] >= payload["required_n"]

    async def test_an_ordinary_hold_still_does_not_journal(self, session):
        """T2.06's rule is narrowed by exactly one shape, not repealed."""
        m = await _memory(session, content="lonely", technologies=["qdrant"])
        fact_id = await _fact(session, key="ordinary-1")
        await _source(session, fact_id, memory=m, origin="sess-only")
        await session.commit()

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "hold"
        assert decision.supersession_blocked is False
        assert await _events(session, fact_id) == []

    async def test_every_verified_payload_carries_the_flag(self, session):
        """The key rides every evidence block, exactly like `contradiction_blocked`.

        This is the coupling to T2.51: a new payload key is precisely what its
        `KNOWN_PAYLOAD_KEYS` guard refuses, so the runner must be widened in
        step. Pinned here so the key's presence is a stated contract rather
        than an accident of one branch.
        """
        fact_id, _ = await _at_bar_fact(session, key="everypayload-1")
        await recompute_fact(session, fact_id)
        await session.commit()

        payload = (await _events(session, fact_id))[0]
        assert payload["outcome"] == "promote"
        assert payload["supersession_blocked"] is False

    async def test_a_blocked_hold_lands_in_the_promotion_rate_denominator(self, session):
        """The denominator ruling, executable.

        T2.51 derives "eligible" as a journaled transition out of `candidate`
        whose bar was met, as `outcome IN ('promote','dispute')`. A
        supersession-blocked hold is exactly that shape with a third outcome,
        and the ruling (argued in `supersession_hold`'s docstring) is that it
        **counts**: excluding it would let a widening block shrink the
        denominator instead of the numerator, leaving the measured rate flat
        while fewer facts promoted — a distortion with no trace.

        The restated filter is asserted here against real journaled rows so
        the ruling is checked rather than merely written down.
        """
        promoted_id, _ = await _at_bar_fact(session, key="denom-promote")
        await recompute_fact(session, promoted_id)
        await session.commit()

        blocked_id, m_old = await _at_bar_fact(session, key="denom-blocked")
        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we replaced qdrant with pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert m_old.id in flipped
        await recompute_fact(session, blocked_id)
        await session.commit()

        row = (
            await session.execute(
                text("""
                SELECT
                    COUNT(*) FILTER (WHERE payload->>'outcome' = 'promote') AS promoted,
                    COUNT(*) FILTER (
                        WHERE (payload->>'supersession_blocked')::boolean
                    ) AS blocked,
                    COUNT(*) AS eligible
                FROM events
                WHERE event_type = 'verified'
                  AND object_type = 'fact'
                  AND payload->'before'->>'verification_status' = 'candidate'
                  AND (
                      payload->>'outcome' IN ('promote', 'dispute')
                      OR (
                          payload->>'outcome' = 'hold'
                          AND (payload->>'supersession_blocked')::boolean
                      )
                  )
                  AND (payload->>'origin_count')::int
                      >= (payload->>'required_n')::int
                """)
            )
        ).mappings().one()

        assert row["promoted"] == 1
        assert row["blocked"] == 1
        assert row["eligible"] == 2, (
            "the blocked hold must size the denominator; at 1 the block has "
            "silently left the measurement and a widening block would read as "
            "a stable promotion rate"
        )


# ───────────────── the predicate's own rules, one test each ─────────────────


class TestThePredicateRules:
    async def test_a_speculative_replacement_does_not_block(self, session):
        """The whole argument for keying off the status column.

        "We might switch" supersedes nothing, because `detect_supersessions`'
        sixth guard filters it. Reading the raw REPLACES-family edge would
        inherit none of the six and this fact would be held on a replacement
        nobody made.
        """
        fact_id, m_old = await _at_bar_fact(session, key="speculative-1")
        _, flipped = await _replacement(
            session,
            replaces="qdrant",
            text_="we might switch from qdrant to pgvector",
            created_at=T0 + timedelta(days=10),
        )
        assert flipped == [], "the speculative gate should have declined to flip"

        decision = await recompute_fact(session, fact_id)
        await session.commit()
        assert decision.supersession_blocked is False
        assert decision.outcome == "promote"

    async def test_an_older_superseder_is_not_a_newer_signal(self, session):
        """The `newer` comparison, anchored to the source memory.

        Unreachable through the write-time detector (its fifth guard already
        orders the pair), so it is seeded directly — `memories.status` has a
        second future writer in doc 08 §3.4's status bridge, whose guards say
        nothing about timestamps.
        """
        fact_id, m_old = await _at_bar_fact(session, key="older-1")
        stale = await _memory(
            session, content="ancient", created_at=T0 - timedelta(days=30)
        )
        await _supersede(session, old=m_old, new=stale)
        await session.commit()

        assert await adjudicate_supersession_hold(session, fact_id) is False
        decision = await recompute_fact(session, fact_id)
        await session.commit()
        assert decision.outcome == "promote"

    async def test_a_newer_superseder_blocks(self, session):
        """The positive half of the same comparison, so the guard is not vacuous."""
        fact_id, m_old = await _at_bar_fact(session, key="newer-1")
        fresh = await _memory(
            session, content="successor", created_at=T0 + timedelta(days=30)
        )
        await _supersede(session, old=m_old, new=fresh)
        await session.commit()

        assert await adjudicate_supersession_hold(session, fact_id) is True

    async def _tie_break_fact(self, session, *, key: str, source_id, superseder_id):
        """A fact whose one memory source is superseded at an *equal* timestamp.

        Both memories share one ``created_at``, which is the shape a within-batch
        supersession produces: same-batch rows take one server-side timestamp, so
        the strict ``>`` never fires and only the id tie-break can.
        """
        m_old = await _memory(
            session, content="replaced", created_at=T0, id=source_id
        )
        sup = await _memory(
            session, content="successor", created_at=T0, id=superseder_id
        )
        fact_id = await _fact(session, key=key)
        await _source(session, fact_id, memory=m_old, origin="sess-a")
        await _source(session, fact_id, origin="repo-b", kind="code", ref=f"repo:{key}")
        await _supersede(session, old=m_old, new=sup)
        await session.commit()
        return fact_id

    async def test_an_equal_timestamp_superseder_blocks_on_the_id_tie_break(
        self, session
    ):
        """The ``(created_at, id)`` tie-break arm, which strict ``>`` cannot reach.

        Deleting the arm leaves every other test in this file green while
        within-batch supersessions stop blocking — and failing to block is the
        unsafe direction, so the omission would be silent in the worst way.
        """
        lower, higher = sorted([uuid.uuid4(), uuid.uuid4()])
        fact_id = await self._tie_break_fact(
            session, key="tiebreak-1", source_id=lower, superseder_id=higher
        )
        assert await adjudicate_supersession_hold(session, fact_id) is True

    async def test_an_equal_timestamp_superseder_below_the_tie_break_does_not_block(
        self, session
    ):
        """The arm is directional, not "equal timestamps always block".

        A superseder whose id sorts *below* its candidate is a pair the
        write-time detector cannot produce — its fifth guard is the same
        comparison — so declining to read it as a supersession signal keeps the
        two definitions identical rather than inventing a third.
        """
        lower, higher = sorted([uuid.uuid4(), uuid.uuid4()])
        fact_id = await self._tie_break_fact(
            session, key="tiebreak-2", source_id=higher, superseder_id=lower
        )
        assert await adjudicate_supersession_hold(session, fact_id) is False

    async def test_a_deprecated_source_does_not_block(self, session):
        """Only `superseded` is the signal; `deprecated` is retirement without
        a successor and carries no replacement claim."""
        fact_id, m_old = await _at_bar_fact(session, key="deprecated-1")
        await session.execute(
            text(
                "UPDATE memories SET status='deprecated' WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(m_old.id)},
        )
        await session.commit()

        assert await adjudicate_supersession_hold(session, fact_id) is False

    async def test_a_non_memory_source_kind_is_not_consulted(self, session):
        """The kind filter.

        `source_ref` carries no type discriminator, so without the filter a
        `human` or `code` ref that happened to spell a superseded memory id
        would block. Seeded as the pathological case directly.
        """
        m_old = await _memory(session, content="replaced", technologies=["qdrant"])
        fresh = await _memory(
            session, content="successor", created_at=T0 + timedelta(days=30)
        )
        fact_id = await _fact(session, key="kind-1")
        # Same ref spelling, wrong kind: the only thing keeping this out is the
        # source_kind predicate.
        await _source(
            session, fact_id, origin="human-1", kind="human", ref=memory_source_ref(m_old.id)
        )
        await _source(
            session, fact_id, origin="repo-1", kind="code", ref=memory_source_ref(m_old.id)
        )
        await _supersede(session, old=m_old, new=fresh)
        await session.commit()

        assert await adjudicate_supersession_hold(session, fact_id) is False

    async def test_the_finding_names_both_memories(self, session):
        """A hold nobody can trace to a source and its replacement is a hold
        nobody can review."""
        fact_id, m_old = await _at_bar_fact(session, key="finding-1")
        fresh = await _memory(
            session, content="successor", created_at=T0 + timedelta(days=30)
        )
        await _supersede(session, old=m_old, new=fresh)
        await session.commit()

        finding = await detect_supersession_hold(session, fact_id)
        assert finding is not None
        assert finding.memory_ref == memory_source_ref(m_old.id)
        assert finding.superseder_ref == memory_source_ref(fresh.id)

    async def test_a_fact_with_no_sources_is_not_blocked(self, session):
        fact_id = await _fact(session, key="empty-1")
        await session.commit()
        assert await adjudicate_supersession_hold(session, fact_id) is False


# ───────────────── the recovery door, the blocker's second branch ─────────────────


class TestRecoveryOutOfDisputedIsAlsoBlocked:
    async def test_a_blocked_fact_recovers_to_candidate_not_corroborated(self, session):
        """Leaving `disputed` at or above the bar is a promotion.

        Letting it through would make the block depend on whether the fact
        happened to be disputed first — the same fact, two answers.
        """
        fact_id, m_old = await _at_bar_fact(
            session, key="recover-1", status="disputed"
        )
        fresh = await _memory(
            session, content="successor", created_at=T0 + timedelta(days=30)
        )
        await _supersede(session, old=m_old, new=fresh)
        await session.commit()

        decision = await recompute_fact(session, fact_id, open_contradiction=False)
        await session.commit()

        assert decision.outcome == "recover"
        assert decision.target_status == "candidate"
        assert decision.supersession_blocked is True
        assert await _status(session, fact_id) == "candidate"

    async def test_the_same_recovery_without_the_signal_reaches_corroborated(
        self, session
    ):
        fact_id, _ = await _at_bar_fact(
            session, key="recover-2", status="disputed"
        )
        decision = await recompute_fact(session, fact_id, open_contradiction=False)
        await session.commit()

        assert decision.outcome == "recover"
        assert decision.target_status == "corroborated"


# ───────────────── the veto still outranks the blocker ─────────────────


class TestTheVetoStillOutranksTheBlocker:
    def test_a_contradicted_and_blocked_fact_is_disputed(self):
        """The veto is absolute (doc 08 §4.2) and is checked first.

        A fact that is both contradicted and superseded is `disputed`: the
        blocker must not downgrade a dispute into a quiet hold, which would
        take a fact off the review queue.
        """
        prof = OriginProfile(
            fact_id="f",
            origins=tuple(
                OriginObservation(
                    origin_key=f"o{i}",
                    source_kinds=("memory",),
                    first_seen=T0,
                    last_seen=T0,
                    row_count=1,
                )
                for i in range(3)
            ),
        )
        decision = decide(
            "f",
            "candidate",
            prof,
            LadderConfig(),
            open_contradiction=True,
            supersession_blocked=True,
        )
        assert decision.target_status == "disputed"
        assert decision.outcome == "dispute"
        assert decision.contradiction_blocked is True
        # The flag must NOT ride the dispute. It means "withheld a promotion",
        # and G-C's blocked FILTER carries no outcome constraint, so a flag set
        # here would count every contradiction-disputed fact as a supersession
        # block and inflate the number T2.40 tunes against.
        assert decision.supersession_blocked is False

    def test_a_confirmed_fact_is_immune_to_the_blocker(self):
        """Doc 08 §4.4: the machine never moves a human-ratified fact."""
        prof = OriginProfile(
            fact_id="f",
            origins=(
                OriginObservation(
                    origin_key="o",
                    source_kinds=("human",),
                    first_seen=T0,
                    last_seen=T0,
                    row_count=1,
                ),
            ),
        )
        decision = decide(
            "f", "confirmed", prof, LadderConfig(), supersession_blocked=True
        )
        assert decision.target_status == "confirmed"
        assert decision.supersession_blocked is False


# ───────── Invariant 15 — the blocker is Tier-C only ─────────

BACKEND = Path(__file__).resolve().parent.parent

# The ladder is the blocker's only legitimate consumer: it is an input to the
# verification decision and nothing else. Mirrors `_ALLOWED_VETO_FILES` in
# `test_contradiction_veto.py`, because each Tier-C input needs its own scan --
# the ladder's own scan matches ladder imports and `recompute_fact`, so a
# capture path importing this module directly is invisible to it.
_ALLOWED_BLOCKER_FILES: set[str] = {"app/services/verification_ladder.py"}


def _forbidden_blocker_references(paths: list[Path], root: Path = BACKEND) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(root))
        if rel == "app/services/supersession_hold.py" or rel in _ALLOWED_BLOCKER_FILES:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if (
                "app.services.supersession_hold" in line
                or "from app.services import supersession_hold" in line
                or "detect_supersession_hold" in line
                or "adjudicate_supersession_hold" in line
            ):
                offenders.append(f"{rel}:{lineno}: {stripped}")
    return offenders


def test_no_app_code_outside_the_ladder_reaches_the_blocker():
    paths = [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scan below would pass "
        "vacuously; check BACKEND / the glob path"
    )
    offenders = _forbidden_blocker_references(paths)
    assert not offenders, (
        "app code outside the verification ladder reached the supersession "
        "blocker:\n" + "\n".join(offenders) + "\nThe blocker is Tier-C "
        "(invariant 15): promotion is reconciled off the hot path, and the "
        "tempting failure is a capture path consulting it so a fact settles "
        "immediately."
    )


def test_the_blocker_guard_rejects_a_forbidden_reference(tmp_path):
    """In-suite negative control — proven every run, not once by hand."""
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True)
    violation = fake / "eager_block.py"
    violation.write_text(
        "from app.services.supersession_hold import adjudicate_supersession_hold\n"
        "async def on_write(session, fact_id):\n"
        "    await adjudicate_supersession_hold(session, fact_id)\n"
    )
    offenders = _forbidden_blocker_references([violation], root=tmp_path)
    assert offenders, (
        "the real guard failed to flag a synthesised violation; the tree-wide "
        "scan above would be reporting success while blind"
    )
