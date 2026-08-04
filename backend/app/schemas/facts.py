from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

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
    """

    origin_key: str | None
    unknown_origin: bool
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


class FactDetailResponse(FactListItem):
    sources: list[FactSourceGroup]
    triple_key: str
    learned_in: list[str] | None
    source_file: str | None
    reference_time: datetime | None


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
