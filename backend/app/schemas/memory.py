import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.memory import (
    TAG_CATEGORY_MAX_LENGTH,
    TAG_NAME_MAX_LENGTH,
    tag_category,
)
from app.schemas.envelope import ENVELOPE_SCHEMA_VERSION
from app.schemas.retrieval_trace import MemoryResultTrace, RetrievalEnvelope


MemoryStatus = Literal["active", "deprecated", "superseded"]


def validate_tag_lengths(tags: list[str] | None) -> list[str] | None:
    """Reject a tag the `tags` table cannot hold, at the door.

    Capture is a 202 accept: the write it acknowledges happens later, in the
    buffer flush, where a tag longer than its column raises against data the
    caller can no longer be told about. Rejecting it here keeps the ack honest —
    a capture that cannot possibly be materialised is a 4xx, never an accept
    followed by a silent landing in the poison queue (Fable review of T1.13,
    finding I-1).
    """
    if not tags:
        return tags
    for tag in tags:
        if len(tag) > TAG_NAME_MAX_LENGTH:
            raise ValueError(
                f"tag is {len(tag)} characters, over the "
                f"{TAG_NAME_MAX_LENGTH}-character limit: {tag[:40]!r}..."
            )
        category = tag_category(tag)
        if category is not None and len(category) > TAG_CATEGORY_MAX_LENGTH:
            raise ValueError(
                f"tag category {category[:40]!r}... is {len(category)} characters, "
                f"over the {TAG_CATEGORY_MAX_LENGTH}-character limit"
            )
    return tags


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    # No default, deliberately. A default here stamps a value during
    # validation, after which a caller who omitted `source` and one who sent
    # the door's own fallback literal are indistinguishable — and the sentinel
    # rule that stops an agent masking detection by copying the old default
    # has nothing left to read. Each front door resolves the chain and applies
    # its own fallback ("api" for REST, "mcp" for MCP) before constructing
    # this model; `tests/test_envelope.py` fails if the default returns.
    source: str | None = None
    source_agent: str | None = None
    # Declared capture-session identity. Resolved at the front door before
    # this schema is built; see resolve_origin_key (doc 05 §2.1).
    origin_key: str | None = None
    memory_type: str | None = None
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)
    expires_at: datetime | None = None
    project: str | None = None

    _check_tags = field_validator("tags")(validate_tag_lengths)


class CaptureAck(BaseModel):
    """Tier-A accept response (doc 05 §2.2).

    ``id`` is the pre-minted **memory** id — the caller's durable reference,
    resolvable once the buffer flush (T1.13) runs. It is deliberately not the
    internal `memory_buffer` row's own id, which is a tracking handle the
    caller never sees (`memory_buffer.buffered_memory_id`).
    """

    schema_version: int = ENVELOPE_SCHEMA_VERSION
    id: uuid.UUID
    status: Literal["accepted"] = "accepted"


# The `MemoryUpdate` fields whose column is NOT NULL, so an explicit `null`
# names a state the row cannot hold. `tests/test_empty_content_update.py`
# derives this set from the ORM mapper and fails if a field drifts out of it.
NOT_NULL_UPDATE_FIELDS = ("content", "importance", "metadata", "is_archived", "project", "status")


class MemoryUpdate(BaseModel):
    # The same floor ``MemoryCreate`` carries, because the corpus has two
    # content doors and only one of them had it. An update to ``""`` wrote an
    # empty row, the re-embed refreshed ``payload.content`` to ``""``
    # verbatim, and any later search that reranked that row raised out of the
    # request — ``RerankerService`` refuses to score a document against an
    # empty string rather than scoring one silently (T2.69).
    #
    # ``None`` is a different fact from absent, and — measured, against an
    # earlier version of this comment that claimed otherwise — it is **not**
    # "the field is not being updated". Only omitting the field is that:
    # ``exclude_unset`` keys off ``model_fields_set``, which sending the key
    # populates, so an explicit ``null`` survives the service's dump and lands
    # on the column. Where the column is nullable (``memory_type``,
    # ``expires_at``) that is a real instruction and stays legal — it clears
    # the field. Where it is NOT NULL it used to reach the flush and raise
    # ``NotNullViolationError`` out of the request, which the HTTP boundary
    # serves as a 500; `_refuse_explicit_null` makes it a 422 instead.
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    memory_type: str | None = None
    importance: float | None = None
    metadata: dict | None = None
    expires_at: datetime | None = None
    is_archived: bool | None = None
    project: str | None = None
    status: MemoryStatus | None = None

    _check_tags = field_validator("tags")(validate_tag_lengths)

    @model_validator(mode="before")
    @classmethod
    def _refuse_explicit_null(cls, data):
        # Refused rather than dropped, because dropping it would have to guess
        # what the caller meant on a model where `null` is meaningful for two
        # other fields. No caller sends one: MCP's `memory_update` builds its
        # dict from the fields the caller actually set, and the SPA has no
        # caller of this route at all.
        if not isinstance(data, dict):
            return data
        nulled = [name for name in NOT_NULL_UPDATE_FIELDS if name in data and data[name] is None]
        if nulled:
            raise ValueError(
                f"{', '.join(nulled)}: null is not an update instruction for a "
                "column that cannot be null — omit the field to leave it unchanged"
            )
        return data



class MemoryLineageEntry(BaseModel):
    """One predecessor in a memory's reverse supersession lineage.

    Carries enough for the UI to render a navigable link with an excerpt
    without a second round trip per row (id + content), plus created_at/
    status so the row can be labelled honestly without re-fetching.
    """

    id: uuid.UUID
    content: str
    created_at: datetime
    status: MemoryStatus


class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    source: str
    source_agent: str | None
    memory_type: str | None
    importance: float
    metadata: dict
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    is_archived: bool
    classified_type: str | None = None
    summary: str | None = None
    emotions: list[str] | None = None
    flags: list[str] | None = None
    related_memories: list[dict] | None = None
    project: str = "default"
    status: MemoryStatus = "active"
    superseded_by: uuid.UUID | None = None
    # The reverse of `superseded_by` — memories this one directly replaced.
    # Bounded at MEMORY_PREDECESSORS_LIMIT (app/repositories/relational.py),
    # newest first. Populated (as `[]` when there are none, never `None`)
    # only by the single-get doors (GET /memories/{id}, MCP `memory_get`) —
    # every other reader of MemoryResponse (search, create, update, batch)
    # leaves this `None`, meaning "not computed for this read," which the UI
    # must render as a distinct, honest "unknown" state rather than as "no
    # predecessors."
    predecessors: list[MemoryLineageEntry] | None = None
    technologies: list[str] = Field(default_factory=list)
    confidence: float = 0.75
    # Populated only when the request set `with_trace=True` — the "why
    # retrieved" explanation for this row (doc 07 §8, T1.33). Absent
    # (`None`) is the zero-cost default for every other read of a memory.
    trace: MemoryResultTrace | None = None


class PaginatedMemoryResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    limit: int
    offset: int
    # Populated only alongside `with_trace=True`; `None` otherwise (T1.33).
    envelope: RetrievalEnvelope | None = None


class MemorySearchRequest(BaseModel):
    query: str | None = None
    tags_any: list[str] | None = None
    tags_all: list[str] | None = None
    memory_type: str | None = None
    source: str | None = None
    limit: int = Field(default=20, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    project: str | None = None
    status: list[MemoryStatus] = Field(default_factory=lambda: ["active"])
    technologies_any: list[str] | None = None
    source_any: list[str] | None = None
    memory_type_any: list[str] | None = None
    # The request flag (T1.33): attaches the retrieval trace envelope and a
    # per-row trace to the paginated search response. Structurally
    # zero-cost when unset — the trace-assembly path is never entered.
    with_trace: bool = False
    # Tier 1 of doc 12 §5's declared-context chain: the per-call argument,
    # which outranks the X-Darkmem-Context header and the project default.
    # `project` is not an axis and is stripped before the declaration is
    # built — the isolation boundary is not the context hint (T1.65).
    context: dict | None = None


class MemoryBatchCreate(BaseModel):
    entries: list[MemoryCreate] = Field(min_length=1, max_length=100)


class MemoryBulkDelete(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class MemoryBulkDeleteResponse(BaseModel):
    deleted: int
    not_found: list[uuid.UUID] = Field(default_factory=list)
    errored: list[uuid.UUID] = Field(default_factory=list)


class MemoryMergeRequest(BaseModel):
    target_id: uuid.UUID
