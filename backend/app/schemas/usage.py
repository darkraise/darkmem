"""Response models for the usage read API.

Every aggregate carries its own confidence alongside its number. A total that
silently dropped the calls whose tokens were never reported would read as
complete when it is a floor, and the four states a call can be in -- priced,
measured-free, unpriced, unmeasured -- are not collapsible into one currency
figure without inventing the difference.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UsageBreakdownRow(BaseModel):
    """One `GROUP BY` bucket, on whichever axis the parent named."""

    key: str
    cost_micros: int
    calls: int
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    unmeasured_calls: int
    unpriced_calls: int


class UsageOverviewResponse(BaseModel):
    window_start: datetime | None
    window_end: datetime

    total_cost_micros: int
    total_calls: int
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    reasoning_tokens: int

    unmeasured_calls: int
    unpriced_calls: int
    #: Named, not merely counted: "3 calls not priced" is actionable only when
    #: the operator can see which model to add a price row for.
    unpriced_models: list[str]

    #: Under the default config the classification purpose is folded into the
    #: extraction call, so its total reads near zero. Unflagged, an operator
    #: "optimising the free-looking purpose" draws exactly the wrong conclusion.
    merged_classification_present: bool

    cache_hit_ratio: float | None
    failed_calls: int
    failed_cost_micros: int

    by_purpose: list[UsageBreakdownRow]
    by_model: list[UsageBreakdownRow]
    by_subject_type: list[UsageBreakdownRow]


class UsageSeriesBucket(BaseModel):
    bucket_start: datetime
    cost_micros: int
    calls: int
    prompt_tokens: int
    completion_tokens: int
    unmeasured_calls: int


class UsageSeriesResponse(BaseModel):
    bucket: str
    buckets: list[UsageSeriesBucket]


class UsageCallRow(BaseModel):
    id: str
    occurred_at: datetime
    purpose: str
    model: str
    provider: str | None
    api_kind: str
    subject_type: str
    subject_id: str | None
    project: str | None
    prompt_tokens: int | None
    cached_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    tokens_measured: bool
    cost_micros: int | None
    ok: bool
    error_kind: str | None
    duration_ms: int
    merged_classification: bool


class UsageSubjectResponse(BaseModel):
    subject_type: str
    subject_id: str
    total_cost_micros: int
    total_calls: int
    #: True when this subject's work rode a batched embed. The embed's cost
    #: belongs to the batch and has no defined per-memory share, so it is named
    #: here rather than divided.
    batched_embedding: bool
    calls: list[UsageCallRow]


class UsageTopRow(BaseModel):
    subject_type: str
    subject_id: str | None
    project: str | None
    cost_micros: int
    calls: int
    duration_ms: int
    unmeasured_calls: int


class UsageTopResponse(BaseModel):
    by: str
    items: list[UsageTopRow]


class ModelPriceRow(BaseModel):
    model: str
    input_micros_per_mtok: int
    cached_micros_per_mtok: int
    output_micros_per_mtok: int
    #: Whether the config row moved this model off its shipped rates. A form
    #: that cannot show this makes a corrected price indistinguishable from a
    #: default that happens to match.
    overridden: bool


class ModelPricesResponse(BaseModel):
    models: list[ModelPriceRow]


class ModelPricesUpdate(BaseModel):
    #: Full replace of the override layer, per the config-singleton convention.
    #: Partial per-model rates are still merged over the shipped defaults.
    prices: dict[str, dict[str, float]]
