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

**Not a second writer of ``verified``.** The ladder's applier remains the sole
journaller of verification transitions (T2.06/T2.62) — this module never calls
it, and the Tier-C source scan in ``tests/test_verification_ladder.py`` is what
holds that. Nothing here writes ``verification_status`` or ``review_state``;
the payload merely *records* what the fact held when the human acted, which is
what lets the audit read a verdict without joining back to
``knowledge_triples``.

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

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import record_event

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
        "verification_status": verification_status,
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
        verification_status=row["verification_status"],
        review_state=row["review_state"],
        project=row["project"],
        actor=actor,
        note=note,
    )
    return {
        "project": row["project"],
        "verification_status": row["verification_status"],
        "review_state": row["review_state"],
    }
