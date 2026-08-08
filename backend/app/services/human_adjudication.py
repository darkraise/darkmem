"""Human adjudication verdicts on a fact, journalled (doc 08 §6, doc 17 §5.1).

Doc 17 §5.1 defines the false-promotion audit as "the count of corroborated
facts later disputed **or human-rejected**". The disputed half is a self-join
over ``verified`` events (T2.06). The human-rejected half had no source at
all: T2.62 settled ``review_state`` as pure queue membership — ``'open'`` is
the only writable value and human resolution clears it to NULL — so no column
anywhere ever means "a human rejected this", and the audit read zero forever
and silently.

**A human verdict is an event, not a state.** That is the whole design. The
verdict is a thing that happened at a moment, to a fact, by a person; the
review queue is a derived view of the fact's *current* conditions. Recording
the verdict in the journal keeps both honest: the audit can count rejections
that happened even after the fact row itself stopped being live, and
``review_state`` keeps the single derived writer T2.62 gave it.

**One event type, a closed verdict set in the payload.** ``human_verdict``
carries ``verdict`` from ``HUMAN_VERDICTS``, mirroring the ``verified`` event's
own ``outcome`` field exactly — the established shape for "one transition kind,
several named outcomes". A type per verb would grow the closed
``EVENT_TYPES`` vocabulary by four for one concept, make "any human verdict on
this fact" a four-way OR, and need another vocabulary change the first time doc
08 §6 names a fifth verb. Filtering in SQL costs the audit the same
``payload->>`` predicate its disputed half already uses. The verdict set gets a
*stronger* guard than ``EVENT_TYPES`` gives, not a weaker one:
``record_human_verdict`` **raises** on an unknown verdict, so the row never
exists, where ``record_event``'s own vocabulary check only warns and inserts
the row regardless.

**Not a second writer of the ladder.** This module never calls the ladder, and
the Tier-C source scan in ``tests/test_verification_ladder.py`` is what holds
that. The ``human_verdict`` payload merely *records* what the fact held when
the human acted, which is what lets the audit read a verdict without joining
back to ``knowledge_triples``.

**Which verbs move the fact, and which do not** (widened by T2.05; before it,
this module moved no verification column at all). ``reject_fact`` still moves
nothing on the verification axis — it withdraws belief, which is the *belief*
axis. ``ratify_fact`` does move it, to ``confirmed``, and that is the one
transition the machine cannot make: doc 08 §4.4 puts the human's floor above
the machine's ceiling, so a module of human verbs is exactly where its writer
belongs. It reaches the column through
``KnowledgeTripleRepository.ratify``, which journals its own ``verified`` row
the way ``set_verification_status`` journals the ladder's — so the journaller
is still the repository, and "one ``verified`` row means one transition" is
unchanged. What *is* no longer true is that the ladder's applier is the only
decision behind those rows; the promotion metrics tell the two apart on the
payload's ``outcome`` (``ratify`` is not a machine outcome and never enters the
G-C promotion rate).

**Rejection's condition-side expression is belief withdrawal, and it has to
be.** T2.62 ruled that a human's bare clear of ``review_state`` correctly
reopens on the next recompute, because doc 08 §6's human verbs each change a
*condition* the derivation already honours. Rejection is not in §6's list, so
its condition had to be identified rather than assumed: a human saying a fact
is wrong is exactly belief withdrawal, which is ``expire``'s existing meaning
(doc 08 §3 — a re-save on the retained row, never a delete, so the history
survives). So ``reject_fact`` withdraws belief through that primitive and
journals the verdict beside it. It writes no verification column and no queue
column, so T2.62's derivation and its refusal guard are untouched.

**A rejectable fact is not necessarily a queued one, and that is deliberate.**
The audit counts *corroborated* facts a human later rejected, and a corroborated
fact has no opener firing on it, so it is not on the queue at all. Requiring
``review_state = 'open'`` here would make doc 17 §5.1's audit structurally
unable to count its own principal case. The door therefore accepts any fact id.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import (
    HUMAN_SOURCE_KIND,
    KnowledgeTripleRepository,
)
from app.services.claim_gates import journalled_status, unserved_status
from app.services.events import CONTRADICTION_DISMISSED, record_event

logger = logging.getLogger(__name__)

HUMAN_VERDICT_EVENT_TYPE = "human_verdict"

# Doc 08 §6's three human verbs — "the human ratifies (`confirmed`, §4.4),
# re-grounds, or edits" — plus the rejection doc 17 §5.1's audit counts and
# §6 leaves implied. Closed: an unknown verdict raises rather than landing an
# uncountable row in an append-only table.
VERDICT_RATIFIED = "ratified"
VERDICT_REGROUNDED = "regrounded"
VERDICT_EDITED = "edited"
VERDICT_REJECTED = "rejected"

HUMAN_VERDICTS: frozenset[str] = frozenset(
    {VERDICT_RATIFIED, VERDICT_REGROUNDED, VERDICT_EDITED, VERDICT_REJECTED}
)

# Journal payloads outlive the rows they describe (CLAUDE.md, events journal),
# so the free-text half of a verdict is bounded here rather than at whichever
# door happens to call in.
NOTE_MAX_LENGTH = 500

# Doc 08 §4.4's "what-was-shown": the claim sentence the ratifier had in front
# of them. Bounded here for the same reason the note is — it lands in a
# `fact_sources.detail` blob that outlives the surface that rendered it — and
# larger than the note because a badge claim carries the origin kinds and the
# as-of date inline.
SHOWN_MAX_LENGTH = 1000


class FactNotFound(LookupError):
    """No ``knowledge_triples`` row with that id."""


_LOAD_FOR_VERDICT = text(
    "SELECT project, verification_status, review_state "
    "FROM knowledge_triples WHERE id = CAST(:id AS uuid) FOR UPDATE"
)


async def record_human_verdict(
    session: AsyncSession,
    *,
    fact_id: UUID | str,
    verdict: str,
    verification_status: str | None,
    review_state: str | None,
    project: str | None,
    actor: str | None,
    note: str | None = None,
) -> None:
    """Journal one human adjudication verdict. Does not commit.

    The single writer of ``human_verdict``. Every door and every future verb
    (T2.05's ratification included) goes through here so the payload shape
    cannot fork.

    The payload carries what doc 17 §5.1's audit needs and nothing it does
    not: which fact (the event's own ``object_id``), which verdict, and the
    ``verification_status`` the fact held when the human acted — so the audit
    never joins back to ``knowledge_triples``, whose current status is by then
    a different question from the one the audit is asking. ``review_state``
    rides along as the queue membership at verdict time; it is recorded, never
    written.
    """
    if verdict not in HUMAN_VERDICTS:
        raise ValueError(
            f"unknown human verdict {verdict!r}; the closed set is "
            f"{sorted(HUMAN_VERDICTS)}. A verdict outside it is a row doc 17 "
            f"§5.1's audit cannot bucket, in a table that cannot un-write it"
        )
    payload: dict = {
        "verdict": verdict,
        # Journal, not label: the audit asks which rung the fact held when the
        # human acted, and a gated copy would answer a different question.
        "verification_status": journalled_status(verification_status),
        "review_state": review_state,
    }
    if note:
        payload["note"] = note[:NOTE_MAX_LENGTH]
    await record_event(
        session,
        event_type=HUMAN_VERDICT_EVENT_TYPE,
        object_type="fact",
        object_id=fact_id if isinstance(fact_id, UUID) else UUID(str(fact_id)),
        project=project,
        actor=actor,
        payload=payload,
    )


async def reject_fact(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    actor: str | None,
    note: str | None = None,
) -> dict:
    """A human rejects a fact: withdraw belief, then journal the verdict.

    Does not commit — the caller's transaction owns both writes, so a fact can
    never be disbelieved without the verdict that explains why, nor the reverse.

    The status is read under the same ``FOR UPDATE`` that ``expire`` re-takes,
    and read *before* the withdrawal, because the payload must record what the
    fact held when the human formed the verdict rather than what this call
    left behind.
    """
    row = (await session.execute(_LOAD_FOR_VERDICT, {"id": str(fact_id)})).mappings().first()
    if row is None:
        raise FactNotFound(str(fact_id))

    await KnowledgeTripleRepository(session).expire(fact_id)
    await record_human_verdict(
        session,
        fact_id=fact_id,
        verdict=VERDICT_REJECTED,
        verification_status=journalled_status(row["verification_status"]),
        review_state=row["review_state"],
        project=row["project"],
        actor=actor,
        note=note,
    )
    # The pre-rejection row, for a caller's own bookkeeping. The REST door
    # discards it and answers 204 by design, so nothing here reaches a reader
    # at all — unlike the copy of the same value two lines up, which the
    # journal keeps and `/events` serves.
    return {
        "project": row["project"],
        "verification_status": unserved_status(row["verification_status"]),
        "review_state": row["review_state"],
    }


async def ratify_fact(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    actor: str,
    shown: str | None = None,
    note: str | None = None,
) -> dict:
    """A human ratifies a fact: write the human source, then confirm it.

    Doc 08 §4.4's decision is that the ratification **is** a ``human``-kind
    ``fact_sources`` row, not merely accompanied by one. Writing the row first
    and confirming second is that decision expressed as an ordering: the
    repository's ``ratify`` refuses to write ``confirmed`` unless the row is
    already visible to its own statement, so the two cannot be performed in the
    wrong order and cannot be separated by a caller who only wants one.

    Recording it as a source is what makes a confirmed fact survive
    re-extraction. When a later lift withdraws every *memory* source, the
    human's row remains, so the source-emptying sweep never silently discards
    a fact a person vouched for.

    Does not commit — the caller's transaction owns the source row, the status
    and the verdict together, so a fact can never be confirmed without the
    provenance that entitles it to be, nor the reverse.

    The actor is required. "The ratifier is recorded" is not satisfiable by an
    anonymous ratification, and a ``human`` row with no identity would fold
    into the unknown-origin bucket, making the one dominant origin in the
    design indistinguishable from an unattributable one.
    """
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError(
            "ratification requires an actor: doc 08 §4.4 records who ratified, "
            "and an unattributed human source counts as the merged "
            "unknown-origin bucket rather than as the dominant origin it is"
        )
    ratifier = actor.strip()

    row = (await session.execute(_LOAD_FOR_VERDICT, {"id": str(fact_id)})).mappings().first()
    if row is None:
        raise FactNotFound(str(fact_id))

    # One ref per (fact, human), so a second ratification by the same person is
    # the same row rather than a second origin: `add_source` is idempotent on
    # this key and first assertion wins, which keeps the original ratifier and
    # the original `created_at` — the "when" — from being rewritten by a later
    # click. `origin_key` matches for the same reason it exists: two *different*
    # humans are genuinely two origins, and with one principal today that
    # collapses to the single dominant origin doc 08 §4.1 describes.
    identity = f"{HUMAN_SOURCE_KIND}:{ratifier}"
    detail: dict = {"ratified_by": ratifier}
    if shown:
        detail["shown"] = shown[:SHOWN_MAX_LENGTH]
    if note:
        detail["note"] = note[:NOTE_MAX_LENGTH]

    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=HUMAN_SOURCE_KIND,
        source_ref=identity,
        origin_key=identity,
        detail=detail,
    )

    fact = await KnowledgeTripleRepository(session).ratify(fact_id)
    if fact is None:  # pragma: no cover - the FOR UPDATE above already loaded it
        raise FactNotFound(str(fact_id))

    await record_human_verdict(
        session,
        fact_id=fact_id,
        verdict=VERDICT_RATIFIED,
        verification_status=journalled_status(row["verification_status"]),
        review_state=row["review_state"],
        project=row["project"],
        actor=ratifier,
        note=note,
    )
    return fact


async def dismiss_contradiction_suspicion(
    session: AsyncSession,
    fact_id: UUID | str,
    *,
    actor: str | None,
    note: str | None = None,
) -> bool:
    """A human says the model scan's flag on this fact was wrong (T2.112).

    Returns whether a live flag was dismissed. Does not commit, for
    ``reject_fact``'s reason: the caller's transaction owns both writes.

    **Not a ``human_verdict``, and it must not become one.** The four verbs in
    ``HUMAN_VERDICTS`` adjudicate the fact; this adjudicates the *finding*, and
    leaves the fact's rung, badge and retrieval position exactly as they were.
    If it journalled as ``rejected`` it would land in doc 17 §5.1's
    human-rejection arm and manufacture a false promotion out of a cleared
    flag — the audit would count the scan's own false positive as the ladder's
    error. It gets its own event type for that reason, and because a dismissal
    is the only live-data evidence of an LLM-scan false positive this system
    can produce.

    **It clears one opener, and only by clearing one condition.**
    ``derive_review_state`` stays total and the clear stays the absence of
    *every* opener, so a fact also disputed or under-sourced stays queued on
    those. The marker is cleared here so the reviewer sees the flag go at once;
    the durable reason it stays gone is the journalled dismissal, which
    ``detect_scanned_contradiction`` honours on every later recompute. Clearing
    the column alone would be undone by the next cycle — the failure T2.62
    named for a bare ``review_state`` clear, in a different column.

    **Reads the marker rather than re-adjudicating.** The suspicion columns are
    the ladder's own re-derived output, so this door needs no contradiction
    machinery of its own — which is also what keeps invariant 15's source scan
    green: adjudication stays reachable from the ladder alone, and no
    human-facing surface imports the veto module.
    """
    row = (
        await session.execute(
            text(
                "SELECT id, project, contradiction_suspected_at, "
                "contradiction_counterpart_id FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(fact_id)},
        )
    ).mappings().first()
    if row is None:
        raise FactNotFound(str(fact_id))
    if row["contradiction_suspected_at"] is None:
        return False

    await record_event(
        session,
        event_type=CONTRADICTION_DISMISSED,
        object_type="fact",
        object_id=row["id"],
        project=row["project"],
        actor=actor,
        payload={
            # The flag as it was shown, so the record answers "what did the
            # human actually dismiss" without re-deriving it against rows that
            # may since have moved.
            "counterpart_id": str(row["contradiction_counterpart_id"])
            if row["contradiction_counterpart_id"] else None,
            "suspected_at": row["contradiction_suspected_at"],
            "note": note,
        },
    )
    await KnowledgeTripleRepository(session).set_verification_status(
        fact_id, None, suspicion=None
    )
    return True
