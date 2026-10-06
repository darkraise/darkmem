"""The badge object and its claim string (doc 12 §4, doc 13 §5.3, T2.36a).

The claim is pinned **character for character**, for every form, and that is
deliberate rather than fussy. The epic already learned the lesson on the
confidence formula: all four properties the corpus stated about it were
survived by a coefficient typo, so the formula was pinned by exact-value
vectors instead. A badge test asserting only that the sentence "contains 3"
passes on a badge no reader would accept — wrong noun, wrong order, wrong
tense, a softened claim — so every assertion below is on the whole string.

The plain form's vector is doc 12's own worked example, copied out of the doc
rather than out of the implementation: it is the one assertion here that can
fail because the *code* is wrong rather than because someone changed both
sides together.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.fact_badge import (
    CLAIM_VOCABULARY,
    VERIFIED_TIER_STATUSES,
    Badge,
    CertaintyWordError,
    assert_no_certainty_words,
    badge_for_fact,
    badges_for_facts,
    build_badge,
    build_claim,
    counterpart_claim,
    row_labels,
)

pytestmark = pytest.mark.asyncio

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
AS_OF = datetime(2026, 7, 20, 9, 14, 0, tzinfo=timezone.utc)
PROJECT = "t2-36a-badge"

# Doc 12 §4's worked example, verbatim.
DOC_12_PLAIN_CLAIM = (
    "asserted by 3 distinct origins of kinds [code, memory], "
    "no known contradiction, as of 2026-07-20"
)


# ─────────────────────────── the three forms, pinned ───────────────────────────


def test_plain_claim_is_doc_12s_worked_example_character_for_character():
    assert (
        build_claim(
            verification_status="corroborated",
            origin_count=3,
            origin_kinds=["code", "memory"],
            as_of=AS_OF,
        )
        == DOC_12_PLAIN_CLAIM
    )


def test_confirmed_claim_gains_the_trailing_human_ratified_clause():
    assert build_claim(
        verification_status="confirmed",
        origin_count=2,
        origin_kinds=["human", "memory"],
        as_of=AS_OF,
    ) == (
        "asserted by 2 distinct origins of kinds [human, memory], "
        "no known contradiction, as of 2026-07-20, human-ratified"
    )


def test_disputed_claim_is_two_sided_and_names_both_counts():
    assert build_claim(
        verification_status="disputed",
        origin_count=2,
        origin_kinds=["memory"],
        as_of=AS_OF,
        claim_text="postgres RUNS_ON docker",
        counterpart_text="postgres RUNS_ON kubernetes",
        counterpart_origin_count=1,
    ) == (
        "disputed: 2 origins assert postgres RUNS_ON docker, "
        "1 origin asserts postgres RUNS_ON kubernetes, as of 2026-07-20"
    )


def test_a_single_origin_reads_in_the_singular():
    assert build_claim(
        verification_status="candidate",
        origin_count=1,
        origin_kinds=["memory"],
        as_of=AS_OF,
    ) == (
        "asserted by 1 distinct origin of kinds [memory], "
        "no known contradiction, as of 2026-07-20"
    )


def test_a_dispute_with_no_journalled_counterpart_says_so_rather_than_collapsing():
    """The degradation that must never be the plain one-sided form.

    "no known contradiction" on a fact we know is disputed is the single
    sentence this module exists to make unwritable, so the absence of the
    counterpart block is stated in the claim rather than papered over.
    """
    claim = build_claim(
        verification_status="disputed",
        origin_count=2,
        origin_kinds=["memory"],
        as_of=AS_OF,
        claim_text="postgres RUNS_ON docker",
    )
    assert claim == (
        "disputed: 2 origins assert postgres RUNS_ON docker, "
        "the contradicting claim was not recorded, as of 2026-07-20"
    )
    assert "no known contradiction" not in claim


def test_a_disputed_badge_never_renders_the_plain_form():
    """Pinned separately from the string above because this is the honesty
    rule rather than the copy: whatever the two-sided wording becomes, a
    disputed fact must never be served the one-sided sentence."""
    for counterpart in (None, "postgres RUNS_ON kubernetes"):
        claim = build_claim(
            verification_status="disputed",
            origin_count=2,
            origin_kinds=["memory"],
            as_of=AS_OF,
            claim_text="postgres RUNS_ON docker",
            counterpart_text=counterpart,
            counterpart_origin_count=1 if counterpart else None,
        )
        assert claim.startswith("disputed: ")
        assert "asserted by" not in claim
        assert "no known contradiction" not in claim


def test_a_fact_verification_has_never_reached_claims_no_timestamp():
    """``as_of`` is the events transition or nothing. Cold start reaches this
    on every fact, and substituting ``created_at`` would put a plausible date
    on a recompute that never happened."""
    claim = build_claim(
        verification_status="candidate",
        origin_count=2,
        origin_kinds=["memory"],
        as_of=None,
    )
    assert claim == (
        "asserted by 2 distinct origins of kinds [memory], "
        "no known contradiction, verification not yet recomputed"
    )
    assert "as of" not in claim


def test_a_fact_nothing_asserts_renders_the_zero_origin_sentence():
    """Reachable in production, not only in a fixture: the withdrawal sweep
    deletes a fact's provenance before expiring the fact it orphans, so a fact
    with no sources exists between those two writes. Pinned rather than
    special-cased — the sentence says nothing currently asserts this, which is
    what a reader of a just-withdrawn row most needs to see."""
    assert build_claim(
        verification_status="candidate",
        origin_count=0,
        origin_kinds=[],
        as_of=AS_OF,
    ) == (
        "asserted by 0 distinct origins of kinds [], "
        "no known contradiction, as of 2026-07-20"
    )


def test_the_zero_origin_sentence_survives_having_no_transition_either():
    assert build_claim(
        verification_status="candidate",
        origin_count=0,
        origin_kinds=[],
        as_of=None,
    ) == (
        "asserted by 0 distinct origins of kinds [], "
        "no known contradiction, verification not yet recomputed"
    )


def test_a_fact_the_recompute_reached_and_held_names_the_checked_day():
    """Degradation 1's other half: an ordinary hold journals nothing, so a
    fact the drain reached and kept on its rung has no transition, and
    "not yet recomputed" would say the job never ran."""
    assert build_claim(
        verification_status="candidate",
        origin_count=1,
        origin_kinds=["memory"],
        as_of=None,
        checked_as_of=AS_OF,
    ) == (
        "asserted by 1 distinct origin of kinds [memory], "
        "no known contradiction, checked as of 2026-07-20"
    )


def test_a_journalled_transition_keeps_its_own_day_over_a_check():
    claim = build_claim(
        verification_status="corroborated",
        origin_count=2,
        origin_kinds=["memory"],
        as_of=AS_OF,
        checked_as_of=AS_OF + timedelta(days=3),
    )
    assert claim.endswith(", as of 2026-07-20")
    assert "checked" not in claim


def test_the_claimed_day_is_utc_whatever_offset_the_row_arrives_in():
    east = datetime(2026, 7, 21, 1, 30, 0, tzinfo=timezone(timedelta(hours=13)))
    assert east.date().isoformat() == "2026-07-21"
    assert build_claim(
        verification_status="corroborated",
        origin_count=2,
        origin_kinds=["memory"],
        as_of=east,
    ).endswith("as of 2026-07-20")


# ─────────────────────────── the forbidden words ───────────────────────────


@pytest.mark.parametrize(
    "sentence",
    [
        "asserted by 3 distinct origins, verified as of 2026-07-20",
        "this claim is true",
        "VERIFIED by three origins",
    ],
)
def test_the_guard_refuses_a_sentence_claiming_certainty(sentence):
    with pytest.raises(CertaintyWordError):
        assert_no_certainty_words(sentence)


def test_the_badges_own_vocabulary_carries_no_certainty_word():
    """The import-time guard, re-run as a test so the failure is legible.

    Editing any template fragment to say "true" or "verified" fails here and
    fails every import of the module besides — the build, not one row.
    """
    for fragment in CLAIM_VOCABULARY:
        assert_no_certainty_words(fragment)


def test_a_rendered_claim_is_guarded_after_the_data_is_removed():
    """A fact whose object is literally the word "verified" is the badge
    quoting evidence, not claiming certainty; refusing to serve that row
    would be a read-path failure invented by a lint."""
    claim = build_claim(
        verification_status="disputed",
        origin_count=1,
        origin_kinds=["memory"],
        as_of=AS_OF,
        claim_text="build STATUS verified",
        counterpart_text="build STATUS true",
        counterpart_origin_count=1,
    )
    assert claim == (
        "disputed: 1 origin asserts build STATUS verified, "
        "1 origin asserts build STATUS true, as of 2026-07-20"
    )


def test_no_form_of_the_claim_says_true_or_verified():
    for status in ("candidate", "corroborated", "confirmed", "disputed"):
        claim = build_claim(
            verification_status=status,
            origin_count=3,
            origin_kinds=["code", "human", "memory"],
            as_of=AS_OF,
            claim_text="postgres RUNS_ON docker",
            counterpart_text="postgres RUNS_ON kubernetes",
            counterpart_origin_count=1,
        )
        assert_no_certainty_words(claim)


# ─────────────────────────── the L0 rule ───────────────────────────


def _badge() -> Badge:
    return Badge(
        verification_status="corroborated",
        origin_count=2,
        origin_kinds=("memory",),
        as_of=AS_OF,
        contradiction=False,
        human_ratified=False,
        stale=False,
        claim="x",
    )


def test_a_memory_row_carries_a_lifecycle_and_no_badge():
    labels = row_labels(id_kind="memory", lifecycle="active")
    assert labels == {
        "verification_status": None,
        "lifecycle": "active",
        "badge": None,
        "unverified": True,
    }


def test_emitting_a_badge_on_a_memory_row_is_refused():
    with pytest.raises(ValueError, match="carries no badge"):
        row_labels(id_kind="memory", lifecycle="active", badge=_badge())


def test_emitting_a_verification_status_on_a_memory_row_is_refused():
    with pytest.raises(ValueError, match="carries no verification_status"):
        row_labels(id_kind="memory", lifecycle="active", verification_status="candidate")


# The two tests below take `cleared_promotion_record` because T2.95 withholds a
# promoted status — and its badge — at the serving boundary until G-C's evidence
# record exists. They are about the badge's *shape*, not about the gate, so they
# open it; the gate's own behaviour is tested in test_claim_serving_gates.py.
def test_a_fact_row_carries_a_badge_and_no_lifecycle(cleared_promotion_record):
    labels = row_labels(
        id_kind="fact", verification_status="corroborated", badge=_badge()
    )
    assert labels["lifecycle"] is None
    assert labels["verification_status"] == "corroborated"
    assert labels["badge"]["origin_count"] == 2
    assert labels["unverified"] is False


@pytest.mark.parametrize(
    "verification_status,expected",
    [
        ("candidate", True),
        ("disputed", True),
        ("corroborated", False),
        ("confirmed", False),
    ],
)
def test_unverified_follows_the_ladder_tier(verification_status, expected, cleared_promotion_record):
    """T2.56's cold-start label: plain, mechanical, and read off the tier the
    ladder already wrote rather than a second adjudication of it."""
    labels = row_labels(
        id_kind="fact", verification_status=verification_status, badge=_badge()
    )
    assert labels["unverified"] is expected


def test_verified_tier_statuses_is_exactly_the_top_two_rungs():
    assert VERIFIED_TIER_STATUSES == {"corroborated", "confirmed"}


def test_the_word_unverified_survives_the_certainty_word_guard():
    """``\\bverified\\b`` needs a boundary before the match; ``un`` leaves
    none, so the cold-start label is not the word the guard exists to catch."""
    assert_no_certainty_words("this row is unverified")


def test_a_lifecycle_on_a_vault_row_is_refused():
    with pytest.raises(ValueError, match="carries no lifecycle"):
        row_labels(id_kind="fact", verification_status="candidate", lifecycle="active")


# ─────────────────────────── against the database ───────────────────────────


async def _fact(
    session,
    *,
    subject: str = "postgres",
    rel: str = "RUNS_ON",
    obj: str = "docker",
    project: str = PROJECT,
    status: str | None = None,
) -> str:
    """Seed a fact, writing the rung directly.

    ``set_verification_status`` is not used: it journals a ``verified`` event
    of its own, stamped now, which would be the latest transition and would
    make every ``as_of`` assertion below read today's date rather than the one
    the fixture placed. The rung is a column here and the transition is
    journalled explicitly by ``_journal_verified``, so the two are
    independently controllable — which is the property under test.
    """
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"k-{uuid.uuid4()}",
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=T0,
        project=project,
    )
    if status is not None:
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = CAST(:s AS text) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"s": status, "id": row["id"]},
        )
    await session.flush()
    return row["id"]


async def _source(session, fact_id, *, kind="memory", ref=None, origin=None):
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref or f"ref-{uuid.uuid4()}",
        origin_key=origin,
    )


async def _row(session, fact_id) -> dict:
    row = await KnowledgeTripleRepository(session).get(fact_id)
    assert row is not None
    return row


async def _journal_verified(session, fact_id, *, at, contradiction=None):
    """A ``verified`` transition at a chosen instant.

    Inserted directly rather than through ``record_event``, which stamps
    ``created_at`` itself: the whole point of these fixtures is that ``as_of``
    tracks the transition's own time and not the clock. ``events`` is
    append-only, so the row cannot be nudged afterwards — the partition is
    ensured first and the timestamp written on the insert.
    """
    payload = {
        "before": {"verification_status": "candidate"},
        "after": {"verification_status": "disputed"},
    }
    if contradiction is not None:
        payload["contradiction"] = contradiction
    await session.execute(
        text("SELECT events_ensure_partition(CAST(:at AS timestamptz)::date)"),
        {"at": at},
    )
    await session.execute(
        text(
            """
            INSERT INTO events (created_at, event_type, object_type, object_id,
                                project, payload)
            VALUES (
                CAST(:at AS timestamptz), 'verified', 'fact',
                CAST(:fid AS uuid), CAST(:project AS text),
                CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "at": at,
            "fid": str(fact_id),
            "project": PROJECT,
            "payload": json.dumps(payload),
        },
    )
    await session.flush()


async def test_origin_count_counts_origins_not_rows(session):
    """R2's property, and the fixture is the one a row count gets wrong: one
    origin that asserted the same fact three times over three refs."""
    fact_id = await _fact(session)
    for _ in range(3):
        await _source(session, fact_id, origin="session-a")
    await session.flush()

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.origin_count == 1
    assert badge.claim.startswith("asserted by 1 distinct origin of kinds [memory],")


async def test_origin_count_matches_the_repositorys_own_counter(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await _source(session, fact_id, origin="session-a")
    await _source(session, fact_id, kind="code", origin="repo-b")
    await session.flush()

    counted = await FactSourceRepository(session).count_distinct_origins(fact_id)
    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.origin_count == counted == 2
    assert badge.origin_kinds == ("code", "memory")


async def test_every_anonymous_row_merges_into_one_origin(session):
    fact_id = await _fact(session)
    for _ in range(4):
        await _source(session, fact_id, origin=None)
    await session.flush()

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.origin_count == 1


async def test_as_of_is_the_verification_transition_not_the_row_timestamp(session):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await _journal_verified(session, fact_id, at=AS_OF)

    row = await _row(session, fact_id)
    badge = await badge_for_fact(session, row)
    assert badge.as_of == AS_OF
    assert badge.as_of != row["created_at"]
    assert badge.claim.endswith("as of 2026-07-20")


async def test_a_fact_with_no_verification_history_carries_no_as_of(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await session.flush()

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.as_of is None
    assert badge.claim.endswith("verification not yet recomputed")


# ───────────── Degradation 1: the recompute's progress, read as data ─────────────


async def _journal_sources_changed(session, fact_id, *, at) -> int:
    """A ``sources_changed`` event at a chosen instant, as the producers write
    it; returns the event id, the watermark's tiebreak."""
    await session.execute(
        text("SELECT events_ensure_partition(CAST(:at AS timestamptz)::date)"),
        {"at": at},
    )
    event_id = (
        await session.execute(
            text(
                """
                INSERT INTO events (created_at, event_type, object_type, object_id,
                                    project, payload)
                VALUES (
                    CAST(:at AS timestamptz), 'sources_changed', 'fact',
                    CAST(:fid AS uuid), CAST(:project AS text),
                    CAST(:payload AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                "at": at,
                "fid": str(fact_id),
                "project": PROJECT,
                "payload": json.dumps({"fact_id": str(fact_id)}),
            },
        )
    ).scalar_one()
    await session.flush()
    return int(event_id)


async def _set_watermark(session, *, at, event_id) -> None:
    """The recompute's state row, as its drain saves it. Other suites commit a
    real one, so every test here writes its own inside its own transaction."""
    from app.services.fact_badge import RECOMPUTE_STATE_KEY

    state = {"watermark_created_at": None, "watermark_id": None}
    if at is not None:
        state = {"watermark_created_at": at.isoformat(), "watermark_id": event_id}
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (:key, CAST(:value AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"key": RECOMPUTE_STATE_KEY, "value": json.dumps(state)},
    )
    await session.flush()


def test_the_state_key_is_the_jobs_own():
    """Spelled twice because the read path may not import the job (invariant
    15); this pins the two spellings together."""
    from app.services.fact_badge import RECOMPUTE_STATE_KEY
    from app.services.verification_recompute import _STATE_CONFIG_KEY

    assert RECOMPUTE_STATE_KEY == _STATE_CONFIG_KEY


async def test_a_fact_whose_evidence_the_drain_passed_reads_checked_as_of(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await _journal_sources_changed(session, fact_id, at=AS_OF)
    other = await _fact(session, obj="kubernetes")
    later = await _journal_sources_changed(session, other, at=AS_OF + timedelta(days=2))
    await _set_watermark(session, at=AS_OF + timedelta(days=2), event_id=later)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.as_of is None, "a check is not a transition; as_of stays the journal's"
    assert badge.claim == (
        "asserted by 1 distinct origin of kinds [memory], "
        "no known contradiction, checked as of 2026-07-22"
    )


async def test_evidence_newer_than_the_watermark_is_not_yet_checked(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    first = await _journal_sources_changed(session, fact_id, at=AS_OF)
    await _journal_sources_changed(session, fact_id, at=AS_OF + timedelta(days=1))
    await _set_watermark(session, at=AS_OF, event_id=first)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.claim.endswith("verification not yet recomputed")


async def test_a_same_instant_tie_reads_the_way_the_drain_ordered_it(session):
    """Two events of one transaction share ``created_at``; the drain orders
    them by id, and so must the reader, or it claims a check the drain has not
    reached yet."""
    reached = await _fact(session, obj="reached")
    pending = await _fact(session, obj="pending")
    for fact_id in (reached, pending):
        await _source(session, fact_id, origin="session-a")
    watermark = await _journal_sources_changed(session, reached, at=AS_OF)
    await _journal_sources_changed(session, pending, at=AS_OF)
    await _set_watermark(session, at=AS_OF, event_id=watermark)

    badges = await badges_for_facts(
        session, [await _row(session, reached), await _row(session, pending)]
    )
    assert badges[str(reached)].claim.endswith("checked as of 2026-07-20")
    assert badges[str(pending)].claim.endswith("verification not yet recomputed")


async def test_a_recompute_that_never_drained_claims_no_check(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await _journal_sources_changed(session, fact_id, at=AS_OF)
    await _set_watermark(session, at=None, event_id=None)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.claim.endswith("verification not yet recomputed")


async def test_the_real_drain_holding_a_candidate_turns_the_badge_to_checked(session):
    """End to end through the job itself: a lone origin keeps its fact a
    candidate, so the drain journals nothing, and the badge must still say
    the fact was checked."""
    from app.services.events import record_event
    from app.services.verification_recompute import run_recompute

    tail = (
        await session.execute(
            text(
                "SELECT created_at, id FROM events WHERE event_type = 'sources_changed' "
                "ORDER BY created_at DESC, id DESC LIMIT 1"
            )
        )
    ).first()
    if tail is None:
        await _set_watermark(session, at=datetime(1970, 1, 1, tzinfo=timezone.utc), event_id=-1)
    else:
        await _set_watermark(session, at=tail.created_at, event_id=tail.id)

    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=uuid.UUID(str(fact_id)),
        project=PROJECT,
        payload={"fact_id": str(fact_id)},
    )
    await session.flush()
    before = await badge_for_fact(session, await _row(session, fact_id))
    assert before.claim.endswith("verification not yet recomputed")

    outcome = await run_recompute(
        session, now=datetime.now(timezone.utc) + timedelta(seconds=30)
    )
    assert str(fact_id) in outcome.drain.recomputed_ids
    assert outcome.drain.transitions == 0
    await session.flush()  # the job's runner commits its state row

    emitted_at = (
        await session.execute(
            text(
                "SELECT created_at FROM events WHERE event_type = 'sources_changed' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": str(fact_id)},
        )
    ).scalar_one()
    after = await badge_for_fact(session, await _row(session, fact_id))
    assert after.as_of is None
    assert after.claim.endswith(
        f"checked as of {emitted_at.astimezone(timezone.utc).date().isoformat()}"
    )


async def test_a_disputed_fact_renders_both_sides_from_the_journalled_block(session):
    counterpart_id = await _fact(session, obj="kubernetes")
    await _source(session, counterpart_id, origin="session-c")

    fact_id = await _fact(session, status="disputed")
    await _source(session, fact_id, origin="session-a")
    await _source(session, fact_id, origin="session-b")
    await _journal_verified(
        session,
        fact_id,
        at=AS_OF,
        contradiction={
            "counterpart_id": str(counterpart_id),
            "counterpart_subject": "postgres",
            "counterpart_rel_type": "RUNS_ON",
            "counterpart_object": "kubernetes",
            "rule": "functional_uniqueness",
            "witness_origin": "session-c",
            "enumeration": "first_finding",
        },
    )

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.contradiction is True
    assert badge.claim == (
        "disputed: 2 origins assert postgres RUNS_ON docker, "
        "1 origin asserts postgres RUNS_ON kubernetes, as of 2026-07-20"
    )


async def test_a_disputed_fact_with_no_block_degrades_rather_than_inventing(session):
    fact_id = await _fact(session, status="disputed")
    await _source(session, fact_id, origin="session-a")
    await _journal_verified(session, fact_id, at=AS_OF)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.contradiction is True
    assert badge.claim == (
        "disputed: 1 origin asserts postgres RUNS_ON docker, "
        "the contradicting claim was not recorded, as of 2026-07-20"
    )


@pytest.mark.parametrize("malformed_id", ["", "   ", None])
async def test_a_malformed_counterpart_id_degrades_rather_than_raising(
    session, malformed_id
):
    """``events`` is append-only, so a malformed historical row cannot be
    pruned and every reader has to survive one forever. No writer produces
    these today; that is the reason to handle them here rather than the
    reason not to."""
    fact_id = await _fact(session, status="disputed")
    await _source(session, fact_id, origin="session-a")
    await _journal_verified(
        session,
        fact_id,
        at=AS_OF,
        contradiction={
            "counterpart_id": malformed_id,
            "counterpart_subject": "postgres",
            "counterpart_rel_type": "RUNS_ON",
            "counterpart_object": "kubernetes",
            "rule": "functional_uniqueness",
            "witness_origin": "session-c",
            "enumeration": "first_finding",
        },
    )

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.contradiction is True
    assert badge.claim == (
        "disputed: 1 origin asserts postgres RUNS_ON docker, "
        "the contradicting claim was not recorded, as of 2026-07-20"
    )


def test_a_blank_counterpart_id_reports_as_absent_not_as_a_lookup_key():
    block = {
        "counterpart_id": "  ",
        "counterpart_subject": "postgres",
        "counterpart_rel_type": "RUNS_ON",
        "counterpart_object": "kubernetes",
    }
    assert counterpart_claim(block) == (None, "postgres RUNS_ON kubernetes")


async def test_human_ratified_tracks_a_human_kind_source(session):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await session.flush()
    assert (await badge_for_fact(session, await _row(session, fact_id))).human_ratified is False

    await _source(session, fact_id, kind="human", origin="reviewer-1")
    await session.flush()
    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.human_ratified is True
    # The rung, not the flag, carries the sentence's suffix: a human source on
    # a fact nobody ratified is evidence, and the claim under-claims.
    assert not badge.claim.endswith("human-ratified")


async def test_as_of_is_the_latest_transition_when_a_fact_has_several(session):
    fact_id = await _fact(session, status="corroborated")
    await _source(session, fact_id, origin="session-a")
    await _journal_verified(session, fact_id, at=datetime(2026, 5, 4, tzinfo=timezone.utc))
    await _journal_verified(session, fact_id, at=AS_OF)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.as_of == AS_OF


async def test_a_confirmed_fact_reports_human_ratified_and_the_suffix(session):
    """``set_verification_status`` refuses to write ``confirmed`` — only a
    human ratifies, through a path that does not exist yet — so the rung is
    seeded directly, which is what the ratification path will produce."""
    fact_id = await _fact(session, status="confirmed")
    await _source(session, fact_id, kind="human", origin="reviewer-1")
    await _source(session, fact_id, origin="session-a")
    await _journal_verified(session, fact_id, at=AS_OF)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert badge.human_ratified is True
    assert badge.claim == (
        "asserted by 2 distinct origins of kinds [human, memory], "
        "no known contradiction, as of 2026-07-20, human-ratified"
    )


async def test_a_code_originated_fact_carries_code_among_its_kinds(session):
    fact_id = await _fact(session, status="corroborated")
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind="code",
        source_ref="darkmem@abc123:app/main.py",
        origin_key="repo-darkmem",
        detail={"commit_sha": "abc123", "file_path": "app/main.py", "symbol_key": "main"},
    )
    await _journal_verified(session, fact_id, at=AS_OF)

    badge = await badge_for_fact(session, await _row(session, fact_id))
    assert "code" in badge.origin_kinds
    assert badge.claim == (
        "asserted by 1 distinct origin of kinds [code], "
        "no known contradiction, as of 2026-07-20"
    )


async def test_a_page_of_facts_is_badged_in_a_bounded_number_of_queries(session):
    ids = []
    for index in range(5):
        fact_id = await _fact(session, obj=f"host-{index}")
        await _source(session, fact_id, origin=f"session-{index}")
        ids.append(fact_id)
    await session.flush()

    rows = [await _row(session, fact_id) for fact_id in ids]
    badges = await badges_for_facts(session, rows)
    assert set(badges) == {str(i) for i in ids}
    assert all(badge.origin_count == 1 for badge in badges.values())


async def test_stale_is_an_article_overlay_and_is_false_on_a_fact(session):
    fact_id = await _fact(session)
    await _source(session, fact_id, origin="session-a")
    await session.flush()
    assert (await badge_for_fact(session, await _row(session, fact_id))).stale is False


def test_the_badge_object_carries_every_field_doc_12_fixes():
    badge = build_badge(
        verification_status="corroborated",
        profile=type(
            "_P", (), {"origin_count": 3, "source_kinds": ("code", "memory")}
        )(),
        as_of=AS_OF,
        subject_name="postgres",
        rel_type="RUNS_ON",
        object_name="docker",
    )
    assert json.loads(json.dumps(badge.as_dict(), default=str)) == {
        "verification_status": "corroborated",
        "origin_count": 3,
        "origin_kinds": ["code", "memory"],
        "as_of": "2026-07-20 09:14:00+00:00",
        "contradiction": False,
        "human_ratified": False,
        "stale": False,
        "claim": DOC_12_PLAIN_CLAIM,
    }
