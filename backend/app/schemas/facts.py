from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.event_log import EventLogEntry
from app.services.human_adjudication import NOTE_MAX_LENGTH, SHOWN_MAX_LENGTH


class FactBadge(BaseModel):
    """Doc 12 §4's badge object, on the wire exactly as that doc fixes it.

    ``claim`` is the contract: every consumer shows it verbatim or not at all,
    and no screen recomputes or softens it. ``stale`` is an article-only
    overlay and is always ``False`` here; it rides the object so the one badge
    shape serves L2 and L3 rather than forking into two.
    """

    verification_status: str | None
    origin_count: int
    origin_kinds: list[str]
    as_of: datetime | None
    contradiction: bool
    human_ratified: bool
    stale: bool
    claim: str


class AppliesWhenLabel(BaseModel):
    axis: str
    value: str


class BeliefWindow(BaseModel):
    """The belief axis, separate from the verification axis it is independent
    of (doc 08 §3). A closed window is retained history, not a withdrawn
    claim, and a withdrawn claim is ``expired_at``."""

    valid_at: datetime | None
    invalid_at: datetime | None
    expired_at: datetime | None


class FactSourceRow(BaseModel):
    id: str
    source_kind: str
    source_ref: str
    detail: dict[str, Any] | None
    created_at: datetime


class FactSourceGroup(BaseModel):
    """One origin's provenance rows — the badge's ``origin_count`` audited.

    ``origin_key`` is ``None`` for the merged unknown-identity bucket, which
    is one origin however many anonymous rows fell into it; ``unknown_origin``
    says so in-band so a renderer does not read the null as missing data.

    ``stale`` (doc 10 §6, T2.48/T2.86) is true when every row of this origin
    has stopped resolving — a code citation the re-verifier could no longer
    match against its repository's current HEAD. The group is still served in
    full: a broken citation is retained evidence, not deleted evidence, and
    dropping it here would make a downgraded badge look like a fact whose
    provenance silently vanished. This field was undeclared until T2.86 found
    it: ``facts_read._source_group`` has computed it since T2.48, but pydantic
    silently drops any key a response model does not declare, so it never
    reached the wire — the same shape invariant 14 exists to catch.
    """

    origin_key: str | None
    unknown_origin: bool
    stale: bool
    source_kinds: list[str]
    first_seen: datetime
    last_seen: datetime
    sources: list[FactSourceRow]


class FactListItem(BaseModel):
    id: str
    id_kind: str
    subject_name: str
    object_name: str
    rel_type: str
    fact: str
    project: str
    verification_status: str | None
    lifecycle: str | None
    badge: FactBadge | None
    # Doc 07 §5's cold-start label (T2.56), from the same ``row_labels`` the
    # composed read's wire carries it through — this is the facts list's own
    # door onto the tier, not a second adjudication of it.
    unverified: bool
    # Why a promoted rung was withheld, or ``None`` when nothing was (T2.95).
    # Undeclared, pydantic dropped it and a suppressed row read exactly like a
    # genuine ``candidate`` — the silent downgrade the gate exists to prevent.
    # This is the third field this model has lost that way; ``unverified`` was
    # the second.
    label_suppressed: str | None = None
    confidence: float | None
    review_state: str | None
    demotion_pending_since: datetime | None = None
    belief_window: BeliefWindow
    applies_when: dict[str, Any] | None
    applies_when_labels: list[AppliesWhenLabel]
    created_at: datetime


class FactListResponse(BaseModel):
    items: list[FactListItem]
    total: int
    limit: int
    offset: int


class FactDisputeTriple(BaseModel):
    """One claim, in the shape both sides of a dispute are rendered in
    (``layer_composition._triple``) — neither side privileged by structure."""

    subject: str | None
    rel_type: str | None
    object: str | None
    id: str | None


class FactDispute(BaseModel):
    """``layer_composition.dispute_label``'s output, on the wire verbatim.

    Present only when the fact's ``verification_status`` is currently
    ``disputed``; a fact with a past, now-resolved dispute carries none —
    the reader has no field to reconstruct that history honestly and does
    not pretend to. ``counterpart`` is ``None`` when the veto's finding was
    never journalled against this fact (a recovery, a caller-overridden
    verdict, or a dispute predating T2.64); ``counterpart_absent`` names
    that case in-band rather than leaving it indistinguishable from "no
    dispute". The two-sided claim **sentence** itself is ``badge.claim``,
    not this block — this carries the structured triple a screen can lay
    out, never a second English rendering of it.
    """

    review_state: str | None
    claim: FactDisputeTriple
    counterpart: FactDisputeTriple | None
    counterpart_absent: str | None = None
    rule: str | None = None
    witness_origin: str | None = None
    enumeration: str | None = None


class FactDetailResponse(FactListItem):
    sources: list[FactSourceGroup]
    triple_key: str
    learned_in: list[str] | None
    source_file: str | None
    reference_time: datetime | None
    # The newest ``LADDER_LIMIT`` ``object_type='fact'`` journal rows for this
    # id, oldest-to-newest, via the same ``ix_events_object``-backed reader
    # ``GET /events/timeline`` uses — never a second query shape over the same
    # index (doc 04 §8.1). ``ladder_total`` is the full journalled count, so a
    # ladder truncated by the cap is never presented as complete.
    ladder: list[EventLogEntry]
    ladder_total: int
    dispute: FactDispute | None


class FactRatifyRequest(BaseModel):
    """Doc 08 §4.4's "what-was-shown", plus the reviewer's optional note.

    ``shown`` is the claim sentence the ratifier had in front of them when they
    vouched. It is recorded rather than derived because the point of keeping it
    is to know what the human actually saw — a server-side recomputation would
    reconstruct today's claim, not the one they read, and the two differ the
    moment provenance changes.

    Who ratified and when are not fields here: the actor comes from the
    authenticated session and the timestamp from the row's own ``created_at``,
    so neither is a value a caller can assert about itself.
    """

    shown: str | None = Field(default=None, max_length=SHOWN_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=NOTE_MAX_LENGTH)
