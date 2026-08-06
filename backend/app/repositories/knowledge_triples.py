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
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.claim_gates import ungated_status
from app.services.events import record_event
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# "Live" is exactly this, spelled once. A window-closed row (invalid_at set) is
# still live history; only belief withdrawal removes a row from the live set.
LIVE_PREDICATE = "expired_at IS NULL"

# Currently-open belief, spelled once beside the predicate it is most often
# confused with. The two are NOT interchangeable and the difference is a
# correctness one, not a performance one: `LIVE_PREDICATE` admits window-closed
# rows, which are retained history (doc 08 §3.1), while this admits only beliefs
# nothing has superseded. `ux_knowledge_triples_open` is partial on exactly this,
# and so are the three retrieval indexes doc 07 §2's fact channel reads, so a
# query that widens it silently leaves every one of their scopes.
OPEN_BELIEF_PREDICATE = "expired_at IS NULL AND invalid_at IS NULL"

# The database CHECK's four values. 'confirmed' is excluded from
# _MACHINE_WRITABLE_VERIFICATION_STATUSES on purpose: only a human ratifies a
# fact, and `ratify` below is the one method that writes it.
_MACHINE_WRITABLE_VERIFICATION_STATUSES = frozenset({"candidate", "corroborated", "disputed"})

CONFIRMED = "confirmed"

# The rung `open_born_corroborated` opens at — the ladder's one exception
# (doc 08 §4.1). Spelled beside the machine-writable set rather than inside
# the method so the two values that may reach this column from this module
# are read together.
BORN_CORROBORATED = "corroborated"

# The `fact_sources.source_kind` a ratification writes, spelled here because
# `ratify`'s UPDATE predicate is what makes doc 08 §4.4 structural. Mirrors
# app.repositories.fact_sources.SOURCE_KINDS' member of the same name;
# tests/test_ratification.py pins the two together.
HUMAN_SOURCE_KIND = "human"

# The `verified` payload's outcome for a ratification. It is deliberately not
# one of the ladder's machine outcomes: a human's imprimatur is not a promotion
# decision, carries no origin count and no gate, and must never land in the
# G-C promotion rate. `scripts/benchlib/promotion_metrics.KNOWN_OUTCOMES`
# carries the same literal so the metrics runner can bucket the row rather
# than raising on it.
RATIFY_OUTCOME = "ratify"

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


@dataclass(frozen=True)
class DemotionPending:
    """Doc 08 §4.3's hysteresis bookkeeping, as one value.

    ``since`` is the marker: ``IS NOT NULL`` is the ``under-sourced`` label
    and the review-queue predicate at once. ``cycles`` counts how many
    consecutive recompute cycles have already observed the pending demotion,
    because the grace window is fixed in cycles and a timestamp cannot count
    them.

    The two travel as one value so "marker set with a zero count" and "count
    set with no marker" are not shapes a caller can write by passing one
    argument and forgetting the other. Which value to write is the ladder's
    decision (``verification_ladder.apply_demotion_hysteresis``); this type
    only refuses the incoherent pairs.
    """

    since: datetime | None
    cycles: int

    def __post_init__(self) -> None:
        if self.cycles < 0:
            raise ValueError(f"demotion_pending_cycles must be >= 0, got {self.cycles}")
        if self.since is None and self.cycles != 0:
            raise ValueError(
                "a cleared demotion marker carries no cycle count: "
                f"since=None with cycles={self.cycles} would leave the next "
                "pending demotion counting from a window that already closed"
            )
        if self.since is not None and self.cycles < 1:
            raise ValueError(
                "an open demotion marker has been observed at least once: "
                "since is set, so the cycle that set it already counts"
            )


class _UnsetDemotionPending:
    """Sentinel: this caller has no opinion about the hysteresis columns.

    The ``UNSET_REVIEW_STATE`` distinction, for the same reason — a bare
    status write must not silently clear a fact's pending demotion, and
    ``None`` is not available as "no opinion" because a cleared marker is a
    real value this column takes.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET_DEMOTION_PENDING"


UNSET_DEMOTION_PENDING = _UnsetDemotionPending()

_COLUMNS = """
    id, subject_id, object_id, subject_name, object_name, rel_type,
    valid_at, invalid_at, expired_at, reference_time, fact, project,
    triple_key, verification_status, confidence, applies_when,
    learned_in, review_state, source_file, demotion_pending_since,
    demotion_pending_cycles, created_at, stated_expiry
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


class HumanSourceRequired(RuntimeError):
    """``ratify`` was called on a fact no ``human``-kind source row asserts.

    Raised rather than returned because the caller's next act is to journal a
    ratification: a falsy return would be read as "no such fact" and the
    verdict would be written over a fact that never moved.
    """


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
        stated_expiry: datetime | None = None,
    ) -> dict:
        """Insert an open-ended belief: ``invalid_at`` and ``expired_at`` NULL.

        ``stated_expiry`` is recorded, never spent here (T2.85). The window
        stays open until the recompute arm sees the date pass; writing it into
        ``invalid_at`` at insert time would drop the fact out of the
        open-belief predicate on the day it was written rather than the day it
        expires.

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
            "stated_expiry": stated_expiry,
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
                    review_state, source_file, stated_expiry
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
                    CAST(:source_file AS text),
                    CAST(:stated_expiry AS timestamptz)
                )
                RETURNING {_COLUMNS}
            """),
            params,
        )
        return _row_to_dict(result.mappings().one())

    async def open_born_corroborated(self, **fields) -> dict:
        """Open a fact directly at the ladder's second rung — the ONE exception.

        Doc 08 §4.1 and doc 10 §6: a fact derived from a repository's parsed
        imports is born ``corroborated`` because the parse *is* the
        verification. Every other route to that rung counts distinct origins
        and runs through the Tier-C recompute.

        **A separate method rather than a parameter on ``insert_open``**, and
        that is the whole of its design. A ``born_corroborated=True`` keyword
        would be one token away from every ordinary lift, and the guard on it
        would be a convention; a method nobody calls by accident is a property.
        Its sole caller is ``fact_lift.mint_born_corroborated``, which refuses
        any source kind but the deterministic one before reaching here.

        **The birth is not journalled, and that is not an omission.** A
        ``verified`` row means a *transition* — the append-only journal's whole
        premise — and a fact opened at a rung moved off nothing. A row with no
        prior status would also be a status change carrying no promotion
        decision, which ``benchlib.promotion_metrics`` refuses by name because
        such a row is invisible to every eligibility filter its SQL uses. What
        records this birth is the ``fact_sources`` row that justifies it, and
        the badge honestly reads ``verification not yet recomputed`` until the
        ladder first visits the fact.

        The rung is re-read from what actually landed rather than assumed,
        for the reason ``fact_lift._mint_fact`` re-reads its own: a fact
        sitting at the wrong rung is this layer's failure mode, and it is
        silent.
        """
        row = await self.insert_open(**fields)
        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET verification_status = CAST(:status AS text)
                WHERE id = CAST(:id AS uuid)
                RETURNING {_COLUMNS}
            """),
            {"id": row["id"], "status": BORN_CORROBORATED},
        )
        promoted = _row_to_dict(result.mappings().one())
        if promoted["verification_status"] != BORN_CORROBORATED:
            raise RuntimeError(
                f"fact {promoted['id']} was to be born {BORN_CORROBORATED!r} "
                f"and landed {promoted['verification_status']!r}"
            )
        return promoted

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

    async def get(self, triple_id: UUID | str) -> dict | None:
        """One fact by id, whatever its belief window or verification rung.

        Unfiltered on purpose. A window-closed or belief-withdrawn fact is
        retained history and is exactly what "what did we believe as of X"
        asks for; a detail read that 404'd on one would make the retention
        unreachable from the surface that exists to show it.
        """
        result = await self.session.execute(
            text(f"SELECT {_COLUMNS} FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
            {"id": str(triple_id)},
        )
        row = result.mappings().first()
        return _row_to_dict(row) if row is not None else None

    async def list_live(
        self,
        *,
        project: str | None,
        subject_name: str | None = None,
        rel_type: str | None = None,
        object_name: str | None = None,
        verification_statuses: Collection[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """A page of live facts, and the total that matched — a browsing read.

        **It does not rank and it does not gate.** The order is arrival
        (``created_at DESC, id DESC``), a queued, disputed or candidate fact is
        listed like any other, and ``verification_statuses`` is a filter the
        caller opts into rather than a default that hides rungs. Doc 08 §6's
        rule that the review queue is never a gate on the read path is a rule
        about *this* kind of surface too.

        The status filter takes a *set* because the caller filters on what a
        reader is served, and a served rung can stand for more than one stored
        one while a claim gate is closed. Resolving that set is the serving
        layer's job (``facts_read``); this method matches the column against
        whatever it is given, and an empty set matches nothing rather than
        everything.

        ``project`` is required as a keyword but may be ``None``, unlike
        ``get_live`` and ``as_of`` where it is mandatory. Those two answer a
        retrieval question and must not serve across projects by omission;
        this one is the authenticated human's browsing view over their own
        box, where an all-projects list is a legitimate thing to ask for — the
        same posture ``review_queue`` takes over the same table. Making the
        parameter keyword-only and undefaulted is what keeps that a decision
        at every call site rather than a default nobody noticed.
        """
        conditions = [LIVE_PREDICATE]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        for column, value in (
            ("project", project),
            ("subject_name", subject_name),
            ("rel_type", rel_type),
            ("object_name", object_name),
        ):
            if value is not None:
                conditions.append(f"{column} = CAST(:{column} AS text)")
                params[column] = value
        if verification_statuses is not None:
            # Membership spelled as a subquery rather than the house
            # `= ANY(CAST(...))`: the verification axis is guarded by a scan
            # that reads a bare `verification_status =` binding as a write to
            # the column, and it is right to, since the shipped writer builds
            # its SET list as exactly such a fragment. A filter must not look
            # like the one thing only two functions are allowed to do.
            conditions.append(
                "verification_status IN "
                "(SELECT unnest(CAST(:verification_statuses AS text[])))"
            )
            params["verification_statuses"] = sorted(verification_statuses)
        where_sql = " AND ".join(conditions)

        result = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM knowledge_triples
                WHERE {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT CAST(:limit AS integer) OFFSET CAST(:offset AS integer)
            """),
            params,
        )
        rows = [_row_to_dict(row) for row in result.mappings().all()]

        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = await self.session.execute(
            text(f"SELECT COUNT(*) FROM knowledge_triples WHERE {where_sql}"),
            count_params,
        )
        return rows, int(total.scalar_one())

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
        supersession_blocked: bool = False,
        contradiction: dict[str, Any] | None = None,
        review_state: str | None | _UnsetReviewState = UNSET_REVIEW_STATE,
        demotion_pending: DemotionPending | _UnsetDemotionPending = UNSET_DEMOTION_PENDING,
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

        ``demotion_pending`` rides that same UPDATE and for the identical
        reason (doc 08 §4.3, T2.46). The marker is the ``under-sourced``
        label on a still-``corroborated`` row, so a statement that moved the
        status without the marker — or the marker without the status — makes
        two contradictory states reachable by a later refactor: a fact
        demoted to ``candidate`` while still wearing the caution overlay that
        promised it had not been demoted yet, and a fact whose demotion was
        suppressed with nothing on the row recording that a demotion is
        owed. Both are silent. One statement under one lock is what makes
        them unrepresentable rather than merely unwritten.

        **This column pair is never a journal trigger**, exactly as
        ``review_state`` is not (see the T2.62 paragraph below). Entering,
        holding and cancelling an under-sourced state are not verification
        transitions — the rung does not move — so counting them would put
        rows carrying no status change into a ``verified`` stream whose
        premise is "one row means one transition", and
        ``benchlib.promotion_metrics`` refuses an unexplained ``hold`` for
        precisely that reason. The eventual demotion journals normally, on
        its own status change, with the payload shape unchanged. The marker
        *is* the durable record of the interim state: it carries the instant
        the pending demotion opened, on the row, on every read path.

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
        ``source_kinds``/``contradiction_blocked``/``supersession_blocked``
        are the promotion decision's
        evidence (the applier's decision record, see the promotion-decision
        module beside this one), threaded through as plain values rather than
        that dataclass itself, to avoid a repository -> service import cycle.
        They are optional so every direct/legacy caller that only ever wrote a
        bare status keeps its original two-key payload verbatim. When
        ``outcome`` is given the full evidence block rides the payload too —
        this is the row G-C's promotion-rate and false-promotion-audit SQL
        reads, so the payload must carry everything those queries need
        without a join back to ``knowledge_triples``.

        ``contradiction`` is the veto's counterpart block (T2.64) — already
        reduced to plain values by ``verification_ladder`` for the same reason
        the evidence above is, so this module never imports the finding's type.
        It is **a field on rows that already existed, never a row of its own**:
        it is folded into the payload the branch below was already going to
        write, and it appears in no condition that decides whether that branch
        runs. A ``contradiction`` supplied on a call that journals nothing is
        therefore silently dropped, which is the correct outcome — a payload
        with no event is not a thing — and unreachable in any case, since the
        ladder produces the block only from a verdict that forces the branch.

        ``contradiction_blocked=True`` journals even when ``status`` is
        ``None`` (unchanged): a fact the veto is *still* holding in
        ``disputed`` across a recompute cycle is not a status transition, but
        it is exactly the ongoing-veto evidence doc 08 §4.2's audit needs.

        ``supersession_blocked=True`` journals on the same terms and is the
        **second** such hold (T2.60). Its status is unchanged by construction —
        the blocker withholds a promotion rather than moving the fact — so
        without this branch the one decision that G-C's promotion rate most
        needs to see would be the one decision that leaves no trace. It is the
        meets-bar-but-holds shape the paragraph below argues cannot exist;
        that argument was true only until this blocker landed, and the
        denominator consequence is argued in ``supersession_hold``'s module
        docstring. Every *other* hold
        (a human-ratified ``confirmed`` refresh, an unblocked candidate below
        its bar, or a corroborated fact still meeting its bar) stays a pure
        no-op. That is *not* principally a volume argument -- the recompute
        that calls this drains ``sources_changed`` past a watermark (doc 08
        §4.3), so it touches only facts with real source activity, not every
        live fact on every cycle -- but even bounded to real activity, a
        plain hold carries no information any G-C metric reads: an unblocked
        candidate below its bar was never "eligible" (excluded from the
        promotion-rate denominator by construction, not by omission), and a
        corroborated fact still holding says nothing new about it. The holds
        that *do* carry information are the two flagged above. The
        contradiction-blocked one carries it because
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
            and isinstance(demotion_pending, _UnsetDemotionPending)
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
        if not isinstance(demotion_pending, _UnsetDemotionPending):
            assignments.append(
                "demotion_pending_since = CAST(:demotion_pending_since AS timestamptz)"
            )
            params["demotion_pending_since"] = demotion_pending.since
            assignments.append(
                "demotion_pending_cycles = CAST(:demotion_pending_cycles AS integer)"
            )
            params["demotion_pending_cycles"] = demotion_pending.cycles
        if assignments:
            await self.session.execute(
                text(
                    f"UPDATE knowledge_triples SET {', '.join(assignments)} "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                params,
            )
        changed = status is not None and prior_row["verification_status"] != status
        if changed or contradiction_blocked or supersession_blocked:
            # Journal, not label: the two rungs a transition moved between are
            # the history of the ladder, and a gated copy would record a
            # movement that did not happen. `ungated_status` says so at the
            # site — see `claim_gates` for what the declaration commits to.
            payload: dict[str, Any] = {
                "before": {
                    "verification_status": ungated_status(
                        prior_row["verification_status"]
                    )
                },
                "after": {
                    "verification_status": ungated_status(
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
                payload["supersession_blocked"] = supersession_blocked
                payload["confidence"] = confidence
            if contradiction is not None:
                payload["contradiction"] = dict(contradiction)
            await record_event(
                self.session,
                event_type="verified",
                object_type="fact",
                object_id=triple_id if isinstance(triple_id, UUID) else UUID(str(triple_id)),
                project=prior_row["project"],
                payload=payload,
            )

    async def ratify(self, triple_id: UUID | str) -> dict | None:
        """Write ``confirmed``. The only method in the tree that can (doc 08 §4.4).

        ``set_verification_status`` refuses the value outright, so this is not
        one writer among several — it is the whole surface, and the human
        source row is its precondition rather than its caller's promise.

        **The precondition rides the UPDATE's own WHERE clause.** A Python
        ``if`` before the write would be a check a later refactor can reorder,
        skip, or satisfy against a row a concurrent transaction is about to
        delete; the ``EXISTS`` below is evaluated by Postgres against the same
        snapshot that performs the write, under the row lock this method
        already holds. That is what makes "no code path sets ``confirmed``
        without a ``human`` source row" a property of the statement rather than
        of caller discipline. A fact that exists but has no such row updates
        zero rows and raises — the refusal is loud, because a silent no-op here
        reads to the caller exactly like a ratification that worked.

        **The ratification's who/when live where they belong.** The ``human``
        row in ``fact_sources`` carries the ratifier and what they were shown
        (doc 08 §4.4's "who / when / what-was-shown"), and the ``events`` row
        carries ``actor`` and ``created_at`` as its own columns. Neither is
        duplicated into this payload: a second copy of an identity is a second
        thing to keep true.

        **Ratifying resolves the queue item and cancels any pending demotion.**
        Doc 08 §6 has the human's verbs clear ``review_state``, and §4.4 makes
        a ratified fact immune to demotion — so leaving
        ``demotion_pending_since`` set would keep the ``under-sourced`` caution
        overlay (doc 13 §5.3) rendering over a fact a human has just vouched
        for, which is the badge lying in the one direction this epic's
        under-claiming rule does not cover. Both columns ride the same
        statement as the status for the reason ``set_verification_status``
        gives: a split makes the half-applied states reachable.

        **Idempotent, and silent on the repeat.** Re-ratifying an already
        ``confirmed`` fact rewrites the same value and journals nothing, on the
        rule this module applies everywhere — ``events`` is append-only, so "a
        row means a transition" has to hold by construction, and a second
        ratification is not a second transition. The caller's own
        ``human_verdict`` row still records that a human acted again.

        Returns the fact row, or ``None`` when no such fact exists. Does not
        commit.
        """
        prior = await self.session.execute(
            text(
                "SELECT verification_status, project FROM knowledge_triples "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(triple_id)},
        )
        prior_row = prior.mappings().first()
        if prior_row is None:
            logger.debug("ratify: no knowledge_triples row for id %s", triple_id)
            return None

        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET verification_status = CAST(:confirmed AS text),
                    review_state = NULL,
                    demotion_pending_since = NULL,
                    demotion_pending_cycles = 0
                WHERE id = CAST(:id AS uuid)
                  AND EXISTS (
                        SELECT 1 FROM fact_sources
                        WHERE fact_id = CAST(:id AS uuid)
                          AND source_kind = CAST(:human AS text)
                  )
                RETURNING {_COLUMNS}
            """),
            {
                "id": str(triple_id),
                "confirmed": CONFIRMED,
                "human": HUMAN_SOURCE_KIND,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise HumanSourceRequired(
                f"refusing to confirm fact {triple_id}: no {HUMAN_SOURCE_KIND!r}-kind "
                f"fact_sources row asserts it, and doc 08 §4.4 makes the "
                f"ratification itself that row — a confirmed fact whose human "
                f"source is missing is one the source-emptying sweep can silently "
                f"discard"
            )

        if prior_row["verification_status"] != CONFIRMED:
            await record_event(
                self.session,
                event_type="verified",
                object_type="fact",
                object_id=triple_id if isinstance(triple_id, UUID) else UUID(str(triple_id)),
                project=prior_row["project"],
                payload={
                    "before": {
                        "verification_status": ungated_status(
                            prior_row["verification_status"]
                        )
                    },
                    "after": {"verification_status": ungated_status(CONFIRMED)},
                    "outcome": RATIFY_OUTCOME,
                },
            )
        return _row_to_dict(row)

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
