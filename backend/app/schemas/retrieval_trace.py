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
    # How many rows the arm returned before fusion, read to its fetch depth:
    # zero is exact (the arm matched nothing in scope), a count at the depth
    # is a floor. Memory search sets it so a reader can tell "no memory holds
    # these words" from "the keyword hits ranked below this page", which
    # per-row scores alone cannot: the semantic arm has no score floor. A door
    # that does not count leaves it unset and off the wire, so it never reads
    # as zero and every other door's channel shape stays as it was.
    hits: int | None = Field(default=None, exclude_if=lambda value: value is None)


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
    # Doc 07 §5's channel-topology flag (T2.56): which of the two output
    # shapes was served — sectioned-by-layer (``False``) or one fused list
    # (``True``). Only ``knowledge_search_response`` stamps a meaningful
    # value; every other envelope construction leaves the default. ``None``,
    # not ``False`` — a door with no shape choice at all (memory search,
    # chat) did not serve "sectioned", so a bare ``False`` would misdescribe
    # what it served. ``None`` reads honestly as "no shape choice was on
    # offer here" instead.
    fused: bool | None = None

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
