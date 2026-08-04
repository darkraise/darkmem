"""The vault's wire shapes, declared once for both doors (doc 12 §3–§4).

Invariant 17 is *two front doors, one service layer*, and the drift it fears
does not start in the service — it starts in the serialiser. ``code_search``
and ``code_blast_radius`` shared a service and still answered differently,
because each door reshaped the result itself. So the composition's rows become
a wire payload in exactly one place: :func:`knowledge_search_response`. MCP's
``knowledge_search`` and doc 12 §2's ``POST /api/v1/knowledge/search`` (T2.80)
both spend that one function.

The **degraded** payload is serialised once here too, by
:func:`knowledge_search_unavailable`. An outage is the shape a reader is least
able to check and the one a door is most tempted to compose for itself: the
channel record comes off the raise rather than being rebuilt from what the door
believes it asked, so neither door can describe an outage the composition did
not record.

**No part of the claim sentence is spelled here.** ``fact_badge`` is its sole
producer, ``layer_composition`` maps that producer's ``row_labels`` over the
composed rows, and this module carries the resulting object through whole.
:class:`FactBadge` is the same model the REST fact-detail route serialises,
imported rather than restated, so the badge a caller reads is byte-identical
whichever door answered.

**The row's text comes from the composition's own closed dispatch.**
``rerank_document_text`` knows where each layer keeps its text and raises on a
layer it was never taught; resolving it here with a second fall-through chain
is how a fact ends up served under an empty ``text`` while every count still
looks right.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from app.schemas.facts import FactBadge
from app.schemas.retrieval_trace import ChannelStatus, RetrievalEnvelope

if TYPE_CHECKING:  # pragma: no cover
    from app.services.layer_composition import (
        ComposedResult,
        ComposedRow,
        CompositionUnavailable,
    )


# The answer budget both doors accept, declared once. Two doors that each
# wrote their own cap would read their arms to different fusion depths for one
# request (``rank_fusion.fusion_fetch_depth``), and RRF is not
# truncation-consistent across depths: the shorter list would stop being the
# longer one's prefix and start being a second ranking.
KNOWLEDGE_SEARCH_MAX_LIMIT = 500
KNOWLEDGE_SEARCH_DEFAULT_LIMIT = 20


class ComposedRowLabels(BaseModel):
    """Doc 12 §4's per-row labels, read off the composition, never derived.

    The L0 and L2/L3 halves are both declared and both optional because one
    model serves every layer: a memory carries ``status`` and a null badge, a
    fact carries ``verification_status``, ``review_state`` and a real one.
    ``fact_badge.row_labels`` is what makes the wrong combination
    unconstructible upstream; declaring both halves here would only re-decide
    it in a second place.
    """

    project: str | None = None
    status: str | None = None
    verification_status: str | None = None
    review_state: str | None = None
    lifecycle: str | None = None
    badge: FactBadge | None = None


class ComposedRowContext(BaseModel):
    match: str
    boost: float


class ComposedRowResponse(BaseModel):
    """One composed row on the wire.

    ``supported_by`` is recursive because doc 07 §5 requires a grouped memory
    to arrive whole, its own scores included; flattening it into a count would
    hand an agent a fact whose evidence it cannot read.
    """

    id: str
    id_kind: str
    layer: str
    text: str
    channel_rank: int
    band: int
    tier: int
    score: float
    rank_fusion_factor: float
    labels: ComposedRowLabels
    context: ComposedRowContext
    dispute: dict[str, Any] | None = None
    grouping: dict[str, Any] | None = None
    supported_by: list["ComposedRowResponse"] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    """The composed read's three axes, and deliberately only those.

    ``LayerCompositionService.search`` takes four more — ``statuses``,
    ``declared_context``, ``weights`` and a wide ``project=None`` — and none of
    them is offered here, because the MCP twin offers none of them either. A
    door that accepted a scope the other cannot express would be a capability
    asymmetry wearing a parameter's clothes: the same query would be answerable
    on one door and not the other, which is the thing invariant 17 forbids.
    """

    query: str = Field(min_length=1)
    project: str = "default"
    limit: int = Field(
        default=KNOWLEDGE_SEARCH_DEFAULT_LIMIT,
        ge=1,
        le=KNOWLEDGE_SEARCH_MAX_LIMIT,
    )


class KnowledgeSearchUnavailable(BaseModel):
    """Doc 12 §3's recoverable unavailability, in one shape for both doors.

    ``rows`` is present and empty rather than absent. An empty list *alone* is
    the shape invariant 14 forbids — indistinguishable from a vault that holds
    nothing — so it is the ``status`` beside it that carries the meaning; a
    consumer that reads rows first must still find the key it expects.

    ``channels`` is the record the composition had already built when it gave
    up, carried through rather than recomposed. A door that rebuilt it from
    what it believes it asked would assert an outage on a channel no request
    ever reached.
    """

    status: Literal["unavailable"] = "unavailable"
    reason: str
    channels: dict[str, ChannelStatus] = Field(default_factory=dict)
    rows: list[ComposedRowResponse] = Field(default_factory=list)


class KnowledgeSearchResponse(BaseModel):
    """The composed four-layer read, rows plus the envelope that qualifies them.

    The envelope is not decoration: it carries which channels ran, which
    failed, and doc 07 §8's unconditional ``by_context_conflict`` tally, so a
    degraded answer can never be read as a complete one (invariant 14).
    """

    rows: list[ComposedRowResponse]
    envelope: RetrievalEnvelope


def composed_row_response(row: "ComposedRow") -> ComposedRowResponse:
    from app.services.layer_composition import rerank_document_text

    return ComposedRowResponse(
        id=row.id,
        id_kind=row.id_kind,
        layer=row.layer,
        text=rerank_document_text(row),
        channel_rank=row.channel_rank,
        band=row.band,
        tier=row.tier,
        score=row.weighted_score,
        rank_fusion_factor=row.rank_fusion_factor,
        labels=ComposedRowLabels(**dict(row.labels)),
        context=ComposedRowContext(
            match=row.context.match.value, boost=row.context.boost
        ),
        dispute=None if row.dispute is None else dict(row.dispute),
        grouping=None if row.grouping is None else dict(row.grouping),
        supported_by=[composed_row_response(nested) for nested in row.supported_by],
    )


def knowledge_search_response(result: "ComposedResult") -> KnowledgeSearchResponse:
    return KnowledgeSearchResponse(
        rows=[composed_row_response(row) for row in result.rows],
        envelope=result.envelope,
    )


def knowledge_search_unavailable(
    exc: "CompositionUnavailable",
) -> KnowledgeSearchUnavailable:
    return KnowledgeSearchUnavailable(reason=str(exc), channels=exc.channels)
