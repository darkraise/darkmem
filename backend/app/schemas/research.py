"""The research door's wire shape (doc 09 §6, T3.27).

One model, and what it deliberately does **not** carry. A researched
capture's ``source`` and ``origin_key`` are stamped by the loop, never by its
caller — that pair is the machine-enforced disclosure a later measurement
slices manufactured origins out on. So this model forbids extra fields rather
than ignoring them: an agent that sends ``source`` or ``origin_key`` gets a
validation error instead of a silently dropped key it would believe took
effect.

``content`` carries no length bound here on purpose. ``MemoryCreate`` owns the
minimum and the ``auto_research`` config row owns the maximum, and a second
copy of either at the door is a bound that drifts from the one that actually
governs the write.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResearchFindingInput(BaseModel):
    """One piece of evidence the calling agent gathered outside the box."""

    model_config = ConfigDict(extra="forbid")

    content: str
    source_id: str | None = Field(
        default=None,
        description=(
            "The canonical locator of the source this finding came from — a URL "
            "or a document id. Two findings from one source must carry the same "
            "value and two independent sources must carry different ones, "
            "because corroboration counts distinct sources. Null when identity "
            "cannot be established, which merges into one anonymous origin that "
            "counts once."
        ),
    )
    metadata: dict = Field(default_factory=dict)
