"""The belief axis of a Layer-2 fact.

A fact runs on two orthogonal axes (doc 08 §3): the **belief** axis
(``valid_at`` / ``invalid_at`` / ``expired_at``) and the **verification** axis
(``verification_status``). They are independent — a fact can be expired yet
confirmed — so the belief-axis methods below never write ``verification_status``,
and ``set_verification_status`` never touches the three timestamps. No method in
this module writes both axes. Conflating them is the modelling error the
fact-layer rebuild exists to fix.

Invalidation is a re-save on the retained row, never a delete: the retained
rows are the only thing that can answer "what did we believe as of date X".

These are primitives, not decisions. The two deterministic fact-write temporal
passes — stale-on-arrival and disjoint-window — belong to ``fact_lift``
(doc 08 §3.2), which chooses between them. The ordering contract this module
guarantees is that ``close_window()`` on the older row followed by
``insert_open()`` for the newer one satisfies the partial-unique
``ux_knowledge_triples_open``: a window-closed row leaves that index's scope
while staying live.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.events import record_event
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# "Live" is exactly this, spelled once. A window-closed row (invalid_at set) is
# still live history; only belief withdrawal removes a row from the live set.
LIVE_PREDICATE = "expired_at IS NULL"

# The database CHECK's four values. 'confirmed' is excluded from
# _MACHINE_WRITABLE_VERIFICATION_STATUSES on purpose: only a human ratifies a
# fact, via the path T2.05 owns, which does not exist yet.
_MACHINE_WRITABLE_VERIFICATION_STATUSES = frozenset({"candidate", "corroborated", "disputed"})

# The review queue's membership literal. ``ix_knowledge_triples_review`` is
# partial on exactly this value and doc 08 §6 defines the queue as
# ``WHERE review_state='open'``, so on disk this column is a boolean with a
# string spelling. Spelled once here, beside the column, and imported by the
# derivation rather than re-typed.
REVIEW_STATE_OPEN = "open"


class _UnsetReviewState:
    """Sentinel: this caller has no opinion about ``review_state``.

    Distinct from ``None``, which means *clear the flag*. Without the
    distinction every caller that writes a bare status would silently drop the
    fact off the review queue.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET_REVIEW_STATE"


UNSET_REVIEW_STATE = _UnsetReviewState()

_COLUMNS = """
    id, subject_id, object_id, subject_name, object_name, rel_type,
    valid_at, invalid_at, expired_at, reference_time, fact, project,
    triple_key, verification_status, confidence, applies_when,
    learned_in, review_state, source_file, created_at
"""


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def _row_to_dict(row: Any) -> dict:
    out = dict(row)
    for key in ("id", "subject_id", "object_id"):
        value = out.get(key)
        out[key] = str(value) if value is not None else None
    learned_in = out.get("learned_in")
    out["learned_in"] = list(learned_in) if learned_in is not None else None
    return out


class KnowledgeTripleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_open(
        self,
        *,
        triple_key: str,
        subject_name: str,
        object_name: str,
        rel_type: str,
        fact: str,
        reference_time: datetime,
        project: str = "default",
        valid_at: datetime | None = None,
        subject_id: UUID | str | None = None,
        object_id: UUID | str | None = None,
        confidence: float | None = None,
        applies_when: dict | None = None,
        learned_in: list[str] | None = None,
        review_state: str | None = None,
        source_file: str | None = None,
    ) -> dict:
        """Insert an open-ended belief: ``invalid_at`` and ``expired_at`` NULL.

        ``triple_key`` is supplied by the caller — the identity function is
        ``app.services.triple_key.compute_triple_key`` and its first producer
        is fact lifting, not this layer.

        This does not look for an existing open row on the same key and close
        it. The disjoint-window case is legitimate (two employment stints at
        one company are two believed facts, both live), so the choice between
        closing the older window and leaving both live is fact lifting's.
        """
        params = {
            "id": str(new_id()),
            "subject_id": str(subject_id) if subject_id is not None else None,
            "object_id": str(object_id) if object_id is not None else None,
            "subject_name": subject_name,
            "object_name": object_name,
            "rel_type": rel_type,
            "valid_at": valid_at,
            "reference_time": reference_time,
            "fact": fact,
            "project": project,
            "triple_key": triple_key,
            "confidence": confidence,
            "applies_when": json.dumps(applies_when) if applies_when is not None else None,
            "learned_in": learned_in,
            "review_state": review_state,
            "source_file": source_file,
        }
        # verification_status is absent from the column list on purpose: the
        # database default seeds it as 'candidate' and this module never writes
        # the verification axis.
        result = await self.session.execute(
            text(f"""
                INSERT INTO knowledge_triples (
                    id, subject_id, object_id, subject_name, object_name,
                    rel_type, valid_at, reference_time, fact, project,
                    triple_key, confidence, applies_when, learned_in,
                    review_state, source_file
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:subject_id AS uuid),
                    CAST(:object_id AS uuid),
                    CAST(:subject_name AS text),
                    CAST(:object_name AS text),
                    CAST(:rel_type AS text),
                    CAST(:valid_at AS timestamptz),
                    CAST(:reference_time AS timestamptz),
                    CAST(:fact AS text),
                    CAST(:project AS text),
                    CAST(:triple_key AS text),
                    CAST(:confidence AS real),
                    CAST(:applies_when AS jsonb),
                    CAST(:learned_in AS text[]),
                    CAST(:review_state AS text),
                    CAST(:source_file AS text)
                )
                RETURNING {_COLUMNS}
            """),
            params,
        )
        return _row_to_dict(result.mappings().one())

    async def close_window(self, triple_id: UUID | str, invalid_at: datetime) -> dict | None:
        """Close a belief's validity window. The row stays live.

        Writes ``invalid_at`` only — ``expired_at`` is untouched, so the row
        remains in the live set as retained history while leaving the scope of
        ``ux_knowledge_triples_open``.

        Journals ``invalidated`` with the before/after ``invalid_at`` —
        but only when the write actually changes the value. The prior value
        is read with ``FOR UPDATE`` in this same transaction, not a separate
        round trip, so a concurrent close on the same row cannot make the
        journalled "before" a lie, and cannot make a no-op look like a
        transition either. This is a window closing, not an expiry — the row
        stays live (``expired_at`` untouched) — so it is journalled as its
        own event type rather than reusing ``expired``.

        The write itself is unconditional (re-closing to the same
        ``invalid_at`` still executes the UPDATE); only the journal call is
        suppressed when before equals after, because ``events`` is
        append-only and a phantom "transition" row can never be deleted —
        "a row means a transition" must be true by construction, not by
        every future reader remembering to filter it out.
        """
        prior = await self.session.execute(
            text(
                "SELECT invalid_at, project FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(triple_id)},
        )
        prior_row = prior.mappings().first()
        if prior_row is None:
            logger.debug("close_window: no knowledge_triples row for id %s", triple_id)
            return None

        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET invalid_at = CAST(:invalid_at AS timestamptz)
                WHERE id = CAST(:id AS uuid)
                RETURNING {_COLUMNS}
            """),
            {"id": str(triple_id), "invalid_at": invalid_at},
        )
        row = result.mappings().first()
        row_dict = _row_to_dict(row)
        if prior_row["invalid_at"] != row["invalid_at"]:
            await record_event(
                self.session,
                event_type="invalidated",
                object_type="fact",
                object_id=triple_id if isinstance(triple_id, UUID) else UUID(str(triple_id)),
                project=prior_row["project"],
                payload={
                    "before": {"invalid_at": _iso(prior_row["invalid_at"])},
                    "after": {"invalid_at": _iso(row["invalid_at"])},
                },
            )
        return row_dict

    async def expire(self, triple_id: UUID | str) -> dict | None:
        """Withdraw belief. A re-save on the retained row, never a delete.

        COALESCE keeps the withdrawal time from drifting on a repeated call:
        a fact was disbelieved once, and a second expire must not rewrite when.

        Journals ``expired`` with the before/after ``expired_at`` — but only
        when the write actually changes the value. Because of the COALESCE
        above, a repeat call on an already-expired row writes back the same
        value it read, so it is a no-op by this method's own contract and
        must not journal (append-only ``events`` can never un-write a
        phantom row, so "a row means a transition" has to be true by
        construction). The prior value is read with ``FOR UPDATE`` in this
        same transaction, not a separate round trip, so a concurrent expire
        on the same row cannot make the journalled "before" a lie or make a
        no-op look like a transition.
        """
        prior = await self.session.execute(
            text(
                "SELECT expired_at, project FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(triple_id)},
        )
        prior_row = prior.mappings().first()
        if prior_row is None:
            logger.debug("expire: no knowledge_triples row for id %s", triple_id)
            return None

        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET expired_at = COALESCE(expired_at, now())
                WHERE id = CAST(:id AS uuid)
                RETURNING {_COLUMNS}
            """),
            {"id": str(triple_id)},
        )
        row = result.mappings().first()
        row_dict = _row_to_dict(row)
        if prior_row["expired_at"] != row["expired_at"]:
            await record_event(
                self.session,
                event_type="expired",
                object_type="fact",
                object_id=triple_id if isinstance(triple_id, UUID) else UUID(str(triple_id)),
                project=prior_row["project"],
                payload={
                    "before": {"expired_at": _iso(prior_row["expired_at"])},
                    "after": {"expired_at": _iso(row["expired_at"])},
                },
            )
        return row_dict

    async def get_live(
        self,
        *,
        project: str,
        triple_key: str | None = None,
        subject_name: str | None = None,
        rel_type: str | None = None,
        object_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Rows in ``project`` belief has not been withdrawn from.

        Disjoint validity windows legitimately leave several live rows on one
        subject/predicate/object, so this may return more than one row per key.

        ``project`` is required, not an optional filter: the scope is rendered
        here rather than at the front door, so no caller can serve facts across
        projects by forgetting to pass it.
        """
        conditions = [LIVE_PREDICATE, "project = CAST(:project AS text)"]
        params: dict = {"limit": limit, "project": project}
        for column, value in (
            ("triple_key", triple_key),
            ("subject_name", subject_name),
            ("rel_type", rel_type),
            ("object_name", object_name),
        ):
            if value is not None:
                conditions.append(f"{column} = CAST(:{column} AS text)")
                params[column] = value

        result = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM knowledge_triples
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at, id
                LIMIT CAST(:limit AS integer)
            """),
            params,
        )
        return [_row_to_dict(row) for row in result.mappings().all()]

    async def set_verification_status(
        self,
        triple_id: UUID | str,
        status: str | None,
        *,
        confidence: float | None = None,
        outcome: str | None = None,
        origin_count: int | None = None,
        required_n: int | None = None,
        gate_fired: str | None = None,
        source_kinds: tuple[str, ...] | list[str] | None = None,
        contradiction_blocked: bool = False,
        review_state: str | None | _UnsetReviewState = UNSET_REVIEW_STATE,
    ) -> None:
        """Write the verification axis only. Belief columns are untouched.

        ``status=None`` means **write confidence only** — no status change, and
        therefore no journal row on that account alone, because no transition
        occurred. That is what lets the ladder refresh the support estimate on
        a fact it must not move: a ``confirmed`` fact cannot be passed its own
        status back, because the refusal below fires before any read.
        ``candidate`` and ``corroborated`` holds may take either route, since
        passing an unchanged status is already a journal no-op.

        ``confidence`` rides the same UPDATE as the status so the two can never
        drift. Both are verification-axis columns, so writing them together
        does not breach this module's no-both-axes contract, which is about the
        belief and verification *axes*, not two columns of one axis.

        ``review_state`` rides that same UPDATE, and the co-location is the
        point rather than a convenience. Doc 08 §4.3's flowchart makes "set
        ``disputed``, ``review_state`` open" **one node**, so splitting it into
        two statements — even two inside this transaction and this lock — makes
        ``disputed``-but-unqueued a state a later refactor can reach, and an
        unqueued dispute is one the human never sees. The value passed here is
        *derived*, never chosen: ``verification_ladder.derive_review_state``
        holds the ruling that decides it and is the only intended producer.
        A caller that passes nothing leaves the column untouched;
        ``None`` means *clear*; ``UNSET_REVIEW_STATE`` is what keeps those two
        apart, because collapsing them would make every bare-status caller
        silently drain the review queue.

        **Opening is unconditional; clearing carries the burden of proof.**
        Writing ``'open'`` can only *add* a row to the review queue, so it hides
        nothing and is applied whatever the column held — including over a value
        this module does not recognise, because clause 1's "not a reachable
        state" outranks preserving a value nobody can name. Writing NULL
        *removes* a row from the queue, so it is applied only over a value this
        derivation could itself have produced (NULL or ``'open'``); anything
        else is left in place with a warning rather than stomped. The asymmetry
        is the veto's, in the other direction: the error direction is fixed, and
        a stale queue entry costs the human one glance while a wrongly cleared
        one costs them the fact.

        **One residue, stated rather than papered over.** Because the parameter
        is optional, a caller may still write ``disputed`` with the flag left
        UNSET and leave the queue closed. Nothing in the tree does — the ladder
        passes the derivation on every call, which is what makes
        ``disputed``-but-unqueued unreachable today — but that is caller
        discipline plus this paragraph, not structure. Making it structural
        would mean refusing ``disputed`` with an UNSET flag, which reaches a
        T2.06-era test and is recorded for triage rather than done here.

        Refuses ``confirmed``: the machine's ceiling is ``corroborated``, and
        only a human reaches ``confirmed``, via the ratification path T2.05
        owns. Raising here — before a producer exists — is the point of this
        method, not a gap to be filled in later. A refused call performs no
        read and no write, so it journals nothing: no transition occurred.

        Journals ``verified`` with the before/after ``verification_status``
        whenever the write actually changes the value; setting a row to the
        status it already holds is a no-op and must not journal on that
        account (append-only ``events`` can never un-write a phantom row, so
        "a row means a transition" has to be true by construction). The prior
        value is read with ``FOR UPDATE`` in this same transaction, not a
        separate round trip, so a concurrent write to the same row cannot make
        the journalled "before" a lie or make a no-op look like a transition.

        ``outcome``/``origin_count``/``required_n``/``gate_fired``/
        ``source_kinds``/``contradiction_blocked`` are T2.06's decision
        evidence (the applier's decision record, see the promotion-decision
        module beside this one), threaded through as plain values rather than
        that dataclass itself, to avoid a repository -> service import cycle.
        They are optional so every direct/legacy caller that only ever wrote a
        bare status keeps its original two-key payload verbatim. When
        ``outcome`` is given the full evidence block rides the payload too —
        this is the row G-C's promotion-rate and false-promotion-audit SQL
        reads, so the payload must carry everything those queries need
        without a join back to ``knowledge_triples``.

        ``contradiction_blocked=True`` journals even when ``status`` is
        ``None`` (unchanged): a fact the veto is *still* holding in
        ``disputed`` across a recompute cycle is not a status transition, but
        it is exactly the ongoing-veto evidence doc 08 §4.2's audit needs, and
        it is the one hold this method journals on purpose. Every other hold
        (a human-ratified ``confirmed`` refresh, an unblocked candidate below
        its bar, or a corroborated fact still meeting its bar) stays a pure
        no-op. That is *not* principally a volume argument -- the recompute
        that calls this drains ``sources_changed`` past a watermark (doc 08
        §4.3), so it touches only facts with real source activity, not every
        live fact on every cycle -- but even bounded to real activity, a
        plain hold carries no information any G-C metric reads: an unblocked
        candidate below its bar was never "eligible" (excluded from the
        promotion-rate denominator by construction, not by omission), and a
        corroborated fact still holding says nothing new about it. The one
        hold that *does* carry information is the contradiction-blocked one,
        because the periodic contradiction scan (T2.11) re-adjudicates every
        standing dispute independently of ``sources_changed``, and each such
        pass is the only durable record that the veto is still active --
        which is the evidence this method exists to preserve. (One volume
        consequence worth naming for that job's owner: every scan pass over
        a standing dispute journals one row, so a long-lived dispute
        accumulates one blocked-hold event per pass, not per source change.)

        Guarding on ``status is None and confidence is None`` above happens
        *before* this journal branch, so a call carrying
        ``contradiction_blocked=True`` but neither ``status`` nor
        ``confidence`` would return early and journal nothing, contradicting
        the "journals on purpose" claim above. Unreachable today -- the
        promotion decision's applier always supplies a computed confidence
        alongside the evidence -- but a future caller passing bare evidence
        with both left ``None`` would silently lose the blocked-hold row;
        that caller does not exist, so this is a documented caveat, not a
        code change.

        **``review_state`` movement is deliberately NOT a third journal
        trigger** (T2.62). The branch below still fires on ``changed or
        contradiction_blocked`` and the ``verified`` population is byte-for-byte
        the one G-C's promotion-rate SQL was written against. Two reasons, and
        the second is the load-bearing one: a queue flag is not a verification
        transition, so counting it would put rows carrying no status change into
        a metric whose whole premise is "one row means one transition"; and the
        flag is a *pure function* of the decision this payload already records
        (see ``derive_review_state``), so a separate journal of it would be
        redundant state, and redundant state drifts. The payload is unchanged
        for the same reason. Every movement this path can produce today already
        coincides with a row the existing trigger writes — an open rides either
        a ``dispute`` transition or a ``contradiction_blocked`` hold, a clear
        rides a ``recover`` transition — with one exception that has no
        producer: a ``confirmed`` fact's clear, which cannot occur until T2.05
        lands a ratification path, and which that path journals itself.

        The promotion decision's applier is this module's sole caller into
        the verification axis, which is what makes the event count here
        countable rather than a duplicate of a second writer's.
        """
        if status is not None and status not in _MACHINE_WRITABLE_VERIFICATION_STATUSES:
            if status == "confirmed":
                raise ValueError(
                    "set_verification_status cannot write 'confirmed': only a "
                    "human may ratify a fact, via the path T2.05 owns"
                )
            raise ValueError(
                f"invalid verification_status {status!r}; must be one of "
                f"{sorted(_MACHINE_WRITABLE_VERIFICATION_STATUSES)}"
            )
        if not isinstance(review_state, _UnsetReviewState) and review_state not in (
            None,
            REVIEW_STATE_OPEN,
        ):
            raise ValueError(
                f"invalid review_state {review_state!r}; the review queue's "
                f"predicate and its partial index are both the literal "
                f"{REVIEW_STATE_OPEN!r}, so a label stored here is a row that "
                "has silently left the queue"
            )
        if (
            status is None
            and confidence is None
            and isinstance(review_state, _UnsetReviewState)
        ):
            return

        prior = await self.session.execute(
            text(
                "SELECT verification_status, review_state, project "
                "FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(triple_id)},
        )
        prior_row = prior.mappings().first()
        if prior_row is None:
            logger.debug(
                "set_verification_status: no knowledge_triples row for id %s", triple_id
            )
            return

        assignments = []
        params: dict[str, Any] = {"id": str(triple_id)}
        if status is not None:
            assignments.append("verification_status = CAST(:status AS text)")
            params["status"] = status
        if confidence is not None:
            assignments.append("confidence = CAST(:confidence AS real)")
            params["confidence"] = confidence
        if not isinstance(review_state, _UnsetReviewState):
            if review_state == REVIEW_STATE_OPEN:
                assignments.append("review_state = CAST(:review_state AS text)")
                params["review_state"] = review_state
            elif prior_row["review_state"] in (None, REVIEW_STATE_OPEN):
                assignments.append("review_state = NULL")
            else:
                logger.warning(
                    "set_verification_status: leaving review_state %r on fact %s "
                    "in place; the derivation clears only NULL or %r, and a value "
                    "it could not have written belongs to an owner it cannot name",
                    prior_row["review_state"],
                    triple_id,
                    REVIEW_STATE_OPEN,
                )
        if assignments:
            await self.session.execute(
                text(
                    f"UPDATE knowledge_triples SET {', '.join(assignments)} "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                params,
            )
        changed = status is not None and prior_row["verification_status"] != status
        if changed or contradiction_blocked:
            payload: dict[str, Any] = {
                "before": {"verification_status": prior_row["verification_status"]},
                "after": {
                    "verification_status": (
                        status if status is not None else prior_row["verification_status"]
                    )
                },
            }
            if outcome is not None:
                payload["outcome"] = outcome
                payload["origin_count"] = origin_count
                payload["required_n"] = required_n
                payload["gate_fired"] = gate_fired
                payload["source_kinds"] = (
                    list(source_kinds) if source_kinds is not None else []
                )
                payload["contradiction_blocked"] = contradiction_blocked
                payload["confidence"] = confidence
            await record_event(
                self.session,
                event_type="verified",
                object_type="fact",
                object_id=triple_id if isinstance(triple_id, UUID) else UUID(str(triple_id)),
                project=prior_row["project"],
                payload=payload,
            )

    async def as_of(
        self,
        t: datetime,
        *,
        project: str,
        triple_key: str | None = None,
        subject_name: str | None = None,
        rel_type: str | None = None,
        object_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Rows in ``project`` believed at time ``t``.

        The window is half-open — ``valid_at <= t < invalid_at`` — so the
        adjacent windows the disjoint-window pass produces never both match a
        single instant. NULL ``valid_at`` reads as unbounded-past and NULL
        ``invalid_at`` as open-ended.

        ``expired_at`` is deliberately not a filter here: this is the historical
        question, and a fact whose belief has since been withdrawn was still
        believed at ``t``. Filtering it would collapse the retained history that
        makes the question answerable.

        ``project`` is required, not an optional filter — same reason as
        ``get_live``: the scope belongs in the repository, not at the front door.
        """
        conditions = [
            "(valid_at IS NULL OR valid_at <= CAST(:t AS timestamptz))",
            "(invalid_at IS NULL OR invalid_at > CAST(:t AS timestamptz))",
            "project = CAST(:project AS text)",
        ]
        params: dict = {"t": t, "limit": limit, "project": project}
        for column, value in (
            ("triple_key", triple_key),
            ("subject_name", subject_name),
            ("rel_type", rel_type),
            ("object_name", object_name),
        ):
            if value is not None:
                conditions.append(f"{column} = CAST(:{column} AS text)")
                params[column] = value

        result = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM knowledge_triples
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at, id
                LIMIT CAST(:limit AS integer)
            """),
            params,
        )
        return [_row_to_dict(row) for row in result.mappings().all()]
