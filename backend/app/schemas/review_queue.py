from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConsequenceFrequency(BaseModel):
    """The retrieval-frequency arm's inputs, not just its output."""

    source_memories: int
    peak_access_count: int
    last_accessed: datetime | None
    decayed_access: float
    half_life_days: int
    weight: float
    component: float


class ConsequenceSalience(BaseModel):
    neighbour_count: int
    weight: float
    component: float


class ConsequenceStaleness(BaseModel):
    """The decay, rendered as what it is: a priority tier and a label.

    Nothing here mirrors ``verification_status`` or ``review_state`` — a
    decayed dispute is still ``disputed`` on the fact row and still ``open``
    on the queue, and those two fields on the item carry that unchanged.
    """

    stale: bool
    label: str
    dispute_opened_at: datetime | None
    dispute_age_days: float | None
    threshold_days: int


class ConsequenceExplanation(BaseModel):
    """Why this item ranks where it does (doc 08 §6, T2.24).

    Structural, not decorative: the score is the sum of the two arms'
    ``component`` values, so a reader can reproduce the total from the parts
    and see which arm produced it.
    """

    score: float
    tier: int
    retrieval_frequency: ConsequenceFrequency
    subject_salience: ConsequenceSalience
    staleness: ConsequenceStaleness


class ReviewQueueFactItem(BaseModel):
    id: str
    subject_name: str
    object_name: str
    rel_type: str
    fact: str
    project: str
    valid_at: datetime | None
    invalid_at: datetime | None
    expired_at: datetime | None
    verification_status: str
    confidence: float | None
    review_state: str | None
    reason: str
    evidence: dict[str, Any] | None
    # None only when a caller pins ARRIVAL_DESC, which computes no ranking.
    consequence: ConsequenceExplanation | None = None
    created_at: datetime


class ReviewQueueFactListResponse(BaseModel):
    items: list[ReviewQueueFactItem]
    total: int
    limit: int
    offset: int


class ReviewQueueArticleItem(BaseModel):
    id: str
    subject_key: str
    project: str
    title: str | None
    status: str
    confidence: float | None
    fact_set_hash: str | None
    review_state: str | None
    reason: str
    content_preview: str | None
    synthesized_at: datetime | None
    created_at: datetime


class ReviewQueueArticleListResponse(BaseModel):
    items: list[ReviewQueueArticleItem]
    total: int
    limit: int
    offset: int


class ReviewQueueCountsResponse(BaseModel):
    facts: int
    articles: int
