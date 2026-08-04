from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TopicItem(BaseModel):
    """`topic_browsing.TopicView` on the wire (doc 09 §3.1, T2.39a).

    `report_status` and `report` never collapse into one signal: a topic
    whose report has not been generated carries `report_status="pending"`
    (or `skipped`/`failed`) and `report=None`; a topic whose generated
    report is genuinely empty text would still carry `report_status="ready"`
    with `report=""` — `None` means "nothing to inject", not "inject
    nothing". `report` is the unit `get_injectable_report` hands to a
    caller, not a second, looser rendering of `report_status`.
    """

    project: str
    label: str
    dominant_entities: list[dict[str, Any]]
    impact_rating: float | None
    member_count: int
    report_status: str
    report: str | None


class TopicListResponse(BaseModel):
    items: list[TopicItem]


class TopicDetailResponse(TopicItem):
    pass


class TopicDiffItem(BaseModel):
    """One `pin_suggestions.TopicDiffEntry` — the diff `diff_topics` computes,
    not merely the current set. `status` is `new` / `grown` / `stable` /
    `decayed`; a browsing read has no pre-rewrite snapshot to diff against
    (only the detection job holds one mid-run), so every entry a live read
    returns is `new` — the seam `pin_suggestions.py`'s own docstring names
    for a UI-driven caller. `grown`/`stable`/`decayed` are real when this
    door is fed a snapshot in the future; nothing here invents one.
    """

    project: str
    label: str
    status: str
    dominant_name: str | None
    dominant_entity_type: str | None
    member_count: int
    prior_member_count: int | None


class PinSuggestionItem(BaseModel):
    """One `pin_suggestions.PinSuggestion` — gated nominations, keyed on the
    dominant entity's soft key (`subject_key`), never a community id."""

    project: str
    subject_key: str
    dominant_name: str
    dominant_entity_type: str
    label: str
    why: str
    member_count: int
    verified_fact_count: int


class PinSuggestionsResponse(BaseModel):
    diff: list[TopicDiffItem]
    suggestions: list[PinSuggestionItem]
    pinned_subject_keys: list[str]
    dismissed_subject_keys: list[str]


class PinDecisionRequest(BaseModel):
    """Accept/dismiss request body.

    `subject_key` is `pin_suggestions.subject_soft_key(name_lower,
    entity_type)` — the dominant entity's identity, stable across a
    community's rewrite. There is no `community_id` field here and there
    must never be one: a community's id changes on every detection rewrite
    (`memory_communities` is delete-and-rewrite per project, doc 06 §7), so
    keying accept/dismiss on it would silently reintroduce the churn T2.20's
    subject-level gate exists to suppress.
    """

    project: str = "default"
    subject_key: str
    label: str | None = None
