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

from pydantic import BaseModel, Field, model_validator

from app.schemas.facts import FactBadge
from app.services.claim_gates import ungated_mapping
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

    ``unverified`` (T2.56) is doc 07 §5's cold-start label — plain and
    boolean rather than a second English sentence, because the honest-claim
    prose is ``badge.claim``'s alone. It is produced by the same function
    that produces every other key here, ``fact_badge.row_labels``, so a
    caller cannot receive one without the other.

    ``label_suppressed`` (T2.95) is the reason a promoted rung was withheld
    for want of its evidence record, and it is declared here because pydantic
    drops what a model does not name. The producer emitted it from the day the
    gate landed and every wire schema silently swallowed it, which made a
    suppressed row and a genuinely-``candidate`` row byte-identical on every
    door — a missing measurement reading as a property of the corpus, which is
    the exact failure the gate exists to prevent.
    """

    project: str | None = None
    status: str | None = None
    verification_status: str | None = None
    review_state: str | None = None
    lifecycle: str | None = None
    badge: FactBadge | None = None
    unverified: bool = True
    label_suppressed: str | None = None


class ComposedRowResponse(BaseModel):
    """One composed row on the wire.

    ``supported_by`` is recursive because doc 07 §5 requires a grouped memory
    to arrive whole, its own scores included; flattening it into a count would
    hand an agent a fact whose evidence it cannot read.

    ``tier`` is the served rung's tier, not the row's ranking tier (T2.95).
    The two differ only while a rung is suppressed, and there the ranking one
    is the withheld label in numeric form: serving ``tier: 3`` beside
    ``labels.verification_status: "candidate"`` hands a reader the promoted
    rung back, trivially inverted through ``TIER_BY_VERIFICATION_STATUS``. The
    row still *ranks* on its true tier — derivation may use the status the
    wire may not reveal — so this field is the only place the two part.
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
    dispute: dict[str, Any] | None = None
    grouping: dict[str, Any] | None = None
    supported_by: list["ComposedRowResponse"] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    """The composed read's three axes, and deliberately only those.

    ``LayerCompositionService.search`` takes three more — ``statuses``,
    ``weights`` and a wide ``project=None`` — and none of
    them is offered here, because the MCP twin offers none of them either. A
    door that accepted a scope the other cannot express would be a capability
    asymmetry wearing a parameter's clothes: the same query would be answerable
    on one door and not the other, which is the thing invariant 17 forbids.

    ``fuse`` (T2.56) is doc 07 §5's channel-topology choice, not a ranking one:
    both shapes compose the identical order, only the presentation differs, so
    it never reaches ``LayerCompositionService.search`` and cannot move a row.
    It defaults ``False`` — the sectioned-by-layer shape doc 07 §5 states as
    the default output ("the default output is sectioned-by-layer with a
    fused fallback for token-budgeted consumers", §5's channel-topology
    paragraph, doc 07 §8's envelope table, doc 13 §5.4) — so a caller that
    never names ``fuse`` gets the document the corpus records as settled. The
    flat shape is reached with ``fuse=true``. Present on both doors or on
    neither (invariant 17): the MCP twin's ``fuse`` argument carries the same
    default for the same reason.
    """

    query: str = Field(min_length=1)
    project: str = "default"
    limit: int = Field(
        default=KNOWLEDGE_SEARCH_DEFAULT_LIMIT,
        ge=1,
        le=KNOWLEDGE_SEARCH_MAX_LIMIT,
    )
    fuse: bool = False


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


class KnowledgeSearchSections(BaseModel):
    """Doc 07 §5's sectioned shape — the served rows partitioned by layer.

    Keyed by the words doc 13 §5.4's panel renders as section headers
    (Memory / Facts / Articles). Partitioning never reorders: each bucket
    keeps the composition's own top-level order, the identical sequence
    ``rows`` would carry in the fused shape, merely split by ``id_kind``
    instead of interleaved. A row nested under a fact (``supported_by``)
    stays nested wherever its enclosing fact's section lands — grouping and
    sectioning are orthogonal passes, and this one never touches the other.
    """

    memory: list[ComposedRowResponse] = Field(default_factory=list)
    facts: list[ComposedRowResponse] = Field(default_factory=list)
    articles: list[ComposedRowResponse] = Field(default_factory=list)


# doc 07 §5's fixed vocabulary, id_kind to the section it fills. Closed and
# dispatched rather than a fall-through: an id_kind this table does not know
# would otherwise vanish from the sectioned shape silently while the fused
# shape kept carrying it, which is exactly the shape-dependent row loss
# doc 07 §5 says the two presentations must never allow.
_SECTION_BY_ID_KIND: dict[str, str] = {"memory": "memory", "fact": "facts", "article": "articles"}


def _sectioned(rows: list[ComposedRowResponse]) -> KnowledgeSearchSections:
    buckets: dict[str, list[ComposedRowResponse]] = {"memory": [], "facts": [], "articles": []}
    for row in rows:
        try:
            key = _SECTION_BY_ID_KIND[row.id_kind]
        except KeyError:
            raise ValueError(
                f"no section is known for id_kind {row.id_kind!r}; doc 07 §5's "
                f"sectioned shape is closed to {sorted(_SECTION_BY_ID_KIND)}"
            ) from None
        buckets[key].append(row)
    return KnowledgeSearchSections(**buckets)


class KnowledgeSearchResponse(BaseModel):
    """The composed four-layer read, in whichever of doc 07 §5's two shapes
    the caller selected, plus the envelope that qualifies it.

    ``rows`` and ``sections`` are the tri-state pair the shape choice makes:
    exactly one is populated and the other is ``None``, never both and never
    neither — a caller that reads the wrong one for the requested shape finds
    ``None`` rather than a plausible-looking empty list. ``envelope.fused``
    names which shape was served, so a reader need not infer it from which
    key came back non-null. The XOR is enforced below rather than left to
    :func:`knowledge_search_response`'s one constructor alone: the OpenAPI
    document still shows two independently nullable fields, so an SDK
    generator reading it — doc 15's, eventually — has no way to derive the
    exclusivity from the schema itself without this.

    The envelope is not decoration otherwise: it carries which channels ran,
    which failed, and the unconditional ``by_result_limit`` tally, so a
    degraded answer can never be read as a complete one (invariant 14).
    """

    rows: list[ComposedRowResponse] | None = None
    sections: KnowledgeSearchSections | None = None
    envelope: RetrievalEnvelope

    @model_validator(mode="after")
    def _exactly_one_shape(self) -> "KnowledgeSearchResponse":
        if (self.rows is None) == (self.sections is None):
            raise ValueError(
                "exactly one of rows/sections must be set (the fuse choice "
                "the caller made), never both and never neither"
            )
        return self


def composed_row_response(row: "ComposedRow") -> ComposedRowResponse:
    from app.services.layer_composition import rerank_document_text, tier_for

    return ComposedRowResponse(
        id=row.id,
        id_kind=row.id_kind,
        layer=row.layer,
        text=rerank_document_text(row),
        channel_rank=row.channel_rank,
        band=row.band,
        # Derived from the label this row is served with, never from
        # ``row.tier`` — that one is the ranking's, computed off the raw rung,
        # and putting it on the wire beside a suppressed label publishes the
        # withheld rung as a number.
        tier=tier_for(row.labels.get("verification_status")),
        score=row.weighted_score,
        rank_fusion_factor=row.rank_fusion_factor,
        labels=ComposedRowLabels(**dict(row.labels)),
        dispute=None if row.dispute is None else dict(ungated_mapping(row.dispute)),
        grouping=None if row.grouping is None else dict(ungated_mapping(row.grouping)),
        supported_by=[composed_row_response(nested) for nested in row.supported_by],
    )


def knowledge_search_response(
    result: "ComposedResult", *, fuse: bool = True
) -> KnowledgeSearchResponse:
    """The composed result, shaped per doc 07 §5 (T2.56).

    Both shapes are built from the identical row list and the identical
    envelope — ``fuse`` selects presentation, never ranking, so it is stamped
    onto the envelope's own ``fused`` field rather than threaded back into
    the composition. ``model_copy`` rather than a second ``RetrievalEnvelope``
    construction: the envelope already carries every other field the service
    computed, and rebuilding it here is how a second copy of that assembly
    drifts from the first.
    """
    rows = [composed_row_response(row) for row in result.rows]
    envelope = result.envelope.model_copy(update={"fused": fuse})
    if fuse:
        return KnowledgeSearchResponse(rows=rows, sections=None, envelope=envelope)
    return KnowledgeSearchResponse(rows=None, sections=_sectioned(rows), envelope=envelope)


def knowledge_search_unavailable(
    exc: "CompositionUnavailable",
) -> KnowledgeSearchUnavailable:
    return KnowledgeSearchUnavailable(reason=str(exc), channels=exc.channels)
