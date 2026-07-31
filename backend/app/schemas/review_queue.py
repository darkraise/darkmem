from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
