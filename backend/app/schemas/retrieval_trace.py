"""The retrieval trace wire contract (doc 07 §8, T1.33).

Transient by design — no table backs this. Assembled on the request path and
returned alongside results only when the caller sets ``with_trace`` on
``MemorySearchRequest``; every field here is the honest record of what the
ranking actually did, never a plausible-looking reconstruction of it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from app.schemas.envelope import ResponseEnvelope


class ChannelStatus(BaseModel):
    ran: bool
    failed: bool = False


class RetrievalEnvelope(ResponseEnvelope):
    """Request-level facts: which channels ran, what weights were in effect,
    and every count of a row this request excluded — surfaced even when zero
    rows survive, because that is exactly the case a silent drop hides
    (invariant 14).

    The retrieval specialisation of the one ``ResponseEnvelope``, from which
    it inherits ``schema_version``, ``excluded``, ``page`` and ``context``.
    """

    query: str
    channels: dict[str, ChannelStatus] = Field(default_factory=dict)
    reranked: bool = False
    weights: dict[str, float] = Field(default_factory=dict)

    @computed_field
    @property
    def partial(self) -> bool:
        return any(channel.failed for channel in self.channels.values())


class MemoryResultTrace(BaseModel):
    """Per-row explanation. ``scores.rrf_score`` is the sole ordering signal;
    ``scores.semantic`` / ``scores.keyword`` are each channel's own raw score
    and must never be read as "the score" (doc 07 §3's trap)."""

    scores: dict[str, float | None] = Field(default_factory=dict)
    rank_fusion_factor: float = 1.0
    rank_fusion_breakdown: dict[str, float] = Field(default_factory=dict)
