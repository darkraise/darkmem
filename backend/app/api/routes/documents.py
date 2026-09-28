"""The documents read surface (TH1.16, doc 16 §6, doc 13).

Provides:
  - GET    /api/v1/documents
  - GET    /api/v1/documents/{document_id}/summary
  - GET    /api/v1/documents/{document_id}/connections
  - GET    /api/v1/documents/{document_id}/outline
  - GET    /api/v1/documents/{document_id}
  - POST   /api/v1/documents/qa
  - POST   /api/v1/documents
  - PATCH  /api/v1/documents/{document_id}
  - POST   /api/v1/documents/rename
  - POST   /api/v1/documents/delete
  - DELETE /api/v1/documents/{document_id}
  - POST   /api/v1/documents/search
  - GET    /api/v1/documents/by-uri/outline
  - GET    /api/v1/documents/by-uri
  - DELETE /api/v1/documents/by-uri
  - GET    /api/v1/documents/manifest
  - GET    /api/v1/documents/{document_id}/revisions
  - GET    /api/v1/documents/{document_id}/revisions/{revision_id}

**A caller that filed by path has a path, not an id.** The three verbs keyed
on a document — outline, blocks, delete — each answer at two paths: the
`{document_id}` form and a `by-uri` form taking `?project=` and `?uri=`.
Outline and delete serve both from one handler; the blocks read's `by-uri`
form has its own handler only because it admits a read key, and it delegates
to the `{document_id}` one. Either way one body answers both forms, so they
cannot answer differently, and `document_door.resolve_document_target` is the
single producer of every refusal, shared with the MCP twins.

**Each `by-uri` route must be registered before its `{document_id}` sibling**,
which is why it is the lower decorator of the two: decorators apply
bottom-up, `/{document_id}` matches the literal segment `by-uri` too, and
whichever registers first wins the match. Reversing the pair does not fail —
it answers 422 `invalid uuid` for every by-uri call, which is why
`test_by_uri_is_not_shadowed_by_the_id_route` pins it.

**This is the EH1 horizon's one door and it adds no semantics.** Every read is
a call into a service that already exists and already carries the honesty rule
it enforces: `read_summary` (unbadged by construction), `connections_for_document`
(cosine over block vectors, no model call), and the grounded Q&A flow behind its
faithfulness gate. The door's own job is to serve those answers without softening them.

**The Q&A response is the gate's verdict, not the answer plus a hint.** It
carries `grounded`, `outcome`, the counts the decision was made on, and the
sentences — and when the outcome is `withheld` it carries **no sentences at
all**. A withheld answer whose text was still on the wire would be served as
ungrounded prose by any client that forgot to read a flag, which is exactly
invariant 14's failure. The label is the payload in that case.

**No lift door.** `POST /{document_id}/lift` existed and was removed with
proposition lifting itself, on the ruling's own grounds (spec §1, §1.1):
granularity and volume, not synthesis. The extraction unit was one block, and
most blocks are too small to hold a standalone assertion -- a priced sample
minted 2.17 propositions per block, one memory per 67 characters of source,
101 of them from headings restated as claims -- which extrapolated to roughly
104,000 machine-extracted memories against the 50 the corpus was hand-captured
with. Relatedness is now a cosine join over vectors both sides already carry,
which mints no row at all. ("Unbadged synthesis" is the spec's phrase for
generated prose, which is what this door still must not serve; it is not what
the lift did wrong.)
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import Principal, require_auth, require_scope
from app.api.deps import refuse_when_read_only, get_llm
from app.database import get_session
from app.services.block_pipeline import UnsupportedSource
from app.services.document_connections import connections_for_document
from app.services.document_related import related_memories_for_document
from app.services.document_door import (
    SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT, DocumentTargetUnresolved,
    DocumentIsBlockFirst,
    DocumentNotConvertible,
    DocumentNothingToChange,
    DocumentTooLarge, DocumentUriConflict, delete_document, delete_documents,
    document_blocks,
    document_content,
    document_hash,
    document_outline,
    put_document, rename_documents, resolve_document_target, search_sections,
    update_document_metadata,
)
from app.services.block_verbs import (
    BlockCycleError,
    BlockTargetUnresolved,
    delete_block,
    insert_block,
    move_block,
    update_block,
)
from app.services.document_ingest import DocumentHashConflict
from app.services import document_revisions
from app.services.document_parsers import DocumentParseError
from app.repositories.documents import resolve_by_id
from app.services.document_summary import (
    EmptySummaryError, read_summary, summarise_document,
)
from app.schemas.memory import validate_tag_lengths
from app.services.faithfulness_gate import FaithfulnessGate, Outcome
from app.services.grounded_qa import GroundedQaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# The routes a dr-superpowers mirror syncs through (spec 2026-09-23 §2) are the
# only document doors a `dmk_` key reaches: filing, the single-document
# metadata PATCH, the by-uri read, the manifest and the two revision reads.
# Every other document route stays login-only; widening one is a decision
# about what a leaked key can read or erase, made per route.
_require_capture = require_scope("capture")
_require_read = require_scope("read")


async def _resolve_target(
    session: AsyncSession,
    *,
    document_id: UUID | None,
    project: str | None,
    uri: str | None,
) -> str:
    """404 for every way of naming no document, in the service's own words.

    `project` and `uri` are optional on the `by-uri` routes rather than
    required so that naming nothing lands here as a 404 like the other
    refusals, instead of splitting one answer across a 422 and a 404
    depending on which half the caller left out.
    """
    try:
        return await resolve_document_target(
            session, document_id=document_id, project=project, uri=uri,
        )
    except DocumentTargetUnresolved as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


class DocumentListItem(BaseModel):
    id: str
    title: str | None
    uri: str | None
    source_type: str | None
    project: str
    block_count: int
    # Served here and NOT on the keyed reads: those are TWO_DOOR and MCP
    # `document_get` has no metadata slot, so a REST-only field there would
    # be a wire divergence. This route is `documents.reads`, REST-only
    # already, so the field costs no parity.
    pinned_at: datetime | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    # The horizon label rides the payload, not only the page chrome: a client
    # that renders this data anywhere else must still be able to say what it
    # is looking at (invariant 23).
    horizon: bool = True


class DocumentSummaryResponse(BaseModel):
    document_id: str
    text: str
    generated_at: str
    block_count: int
    # Stated, not implied. A summary is a report over one document and never a
    # verified claim, so the wire says so rather than leaving a renderer to
    # infer it from the absence of a badge field (doc 16 §6).
    badged: bool = False


class RelatedMemoryItem(BaseModel):
    memory_id: str
    content: str
    memory_type: str | None = None
    status: str
    source: str | None = None
    # `content_surfaces` declares this surface labels `project` and `status`;
    # the label defence is worth nothing unless the label is on the wire.
    project: str
    # The passage is the evidence and the score is an ordering key -- never a
    # calibrated relevance measure. The distribution is continuous, so a client
    # rendering this as a percentage or a badge asserts a precision nobody
    # measured.
    score: float
    block_id: str
    block_text: str
    span_start: int | None = None
    span_end: int | None = None


class RelatedMemoriesResponse(BaseModel):
    items: list[RelatedMemoryItem]
    # False means the comparison could not be made -- no live fingerprint holds
    # vectors for both this document and the project's memories -- which is a
    # different answer from an empty list. It does NOT distinguish "the project
    # holds no memory": `comparable_memories` does, and it is counted
    # independently of the fingerprint for exactly that reason, so a client
    # must test `comparable_memories == 0` before it tests `embedded`.
    embedded: bool
    comparable_memories: int


class DocumentConnectionItem(BaseModel):
    document_id: str
    title: str | None = None
    score: float
    block_id: str
    block_text: str
    other_block_id: str
    other_block_text: str


class DocumentConnectionsResponse(BaseModel):
    items: list[DocumentConnectionItem]
    # `RelatedMemoriesResponse`'s twin, and read the same way: test
    # `comparable_documents == 0` before `embedded`.
    embedded: bool
    comparable_documents: int


class QaRequest(BaseModel):
    question: str = Field(min_length=1)
    project: str = Field(min_length=1)
    document_id: str | None = None
    max_blocks: int = Field(default=12, ge=1, le=50)
    # A caller may refuse the partial: some surfaces would rather show nothing
    # than an answer they have to caveat.
    allow_labelled: bool = True


class QaCitation(BaseModel):
    block_id: str
    document_id: str
    span_start: int
    span_end: int


class QaSentence(BaseModel):
    text: str
    citation: QaCitation | None = None


class QaResponse(BaseModel):
    question: str
    outcome: str
    grounded: bool
    label: str | None
    entailed: int
    total: int
    judged: bool
    reason: str | None
    sentences: list[QaSentence] = Field(default_factory=list)
    horizon: bool = True


class DocumentPutRequest(BaseModel):
    project: str = Field(min_length=1, max_length=200)
    uri: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    title: str | None = None
    source_type: str | None = None
    # Optional compare-and-set: file only if the document still holds this
    # content_hash. Omit for last-writer-wins, which is what every existing
    # caller gets. 409 when it does not match (spec §5.3, review M1).
    expected_hash: str | None = None


class DocumentPatchRequest(BaseModel):
    # `project` is deliberately absent: moving a document between spaces is
    # not a rename, and forbidding extras makes an attempt a 422 rather than a
    # silently dropped key.
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    uri: str | None = Field(default=None, min_length=1, max_length=500)
    pinned: bool | None = None
    tags: list[str] | None = None
    expected_hash: str | None = None

    # The `tags` table's own columns are the only guard below this door:
    # `get_or_create` validates nothing, so a name or a derived category
    # longer than its column raises a driver DataError with no savepoint
    # under it -- a 500 and a poisoned transaction rather than a refusal.
    # The capture door's validator covers both axes; one shared function so
    # the two cannot drift apart.
    _bound_tags = field_validator("tags")(validate_tag_lengths)


class DocumentPatchResponse(BaseModel):
    document_id: str


class DocumentRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=200)
    uri_prefix: str = Field(min_length=1, max_length=500)
    new_uri_prefix: str = Field(min_length=1, max_length=500)


class DocumentRenameResponse(BaseModel):
    renamed: int


class DocumentSubtreeDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=200)
    uri_prefix: str = Field(min_length=1, max_length=500)


class DocumentSubtreeDeleteResponse(BaseModel):
    deleted: int


class DocumentPutResponse(BaseModel):
    document_id: str
    # created | updated | unchanged. `unchanged` still reports an embedded
    # count: it is the repair path for a filing whose embed failed.
    outcome: str
    blocks_filed: int
    blocks_embedded: int
    # False only when `outcome == "unchanged"`: `file_document`'s
    # content-hash gate short-circuits before any row write runs, so a
    # re-filed identical document's explicit `title` (or any other field) is
    # never applied, and nothing else on the wire says so (Task 1 review, M6).
    title_applied: bool
    # Counts of blocks whose text exceeds the embedder's budget, and the
    # largest block's size. None when `outcome == "unchanged"` -- nothing was
    # parsed, so nothing was measured; 0 is a clean bill, None is no bill.
    oversized_blocks: int | None = None
    largest_block_chars: int | None = None
    # What the document now holds -- precondition the next edit on it.
    content_hash: str | None = None
    horizon: bool = True


class BlockInsertRequest(BaseModel):
    type: str = Field(min_length=1)
    text: str
    parent_id: str | None = None
    after_block_id: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None


class BlockUpdateRequest(BaseModel):
    text: str
    type: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None


class BlockMoveRequest(BaseModel):
    new_parent_id: str | None = None
    after_block_id: str | None = None
    expected_hash: str | None = None


class BlockWriteResponse(BaseModel):
    document_id: str
    block_id: str | None
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int
    horizon: bool = True


class DocumentSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    project: str = Field(min_length=1)
    limit: int = Field(
        default=SEARCH_DEFAULT_LIMIT, ge=1, le=SEARCH_MAX_LIMIT,
    )
    document_id: str | None = None


class SectionHitModel(BaseModel):
    block_id: str
    document_id: str
    project: str
    uri: str | None
    title: str | None
    heading_path: list[str]
    path_truncated: bool
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    score: float
    # The block channel's own addendum labels (`block_query.py`), carried
    # through unchanged: this route is the first surface where an
    # `id_kind="block"` row reaches a caller outside that channel, and
    # `block_query.py`'s docstring is explicit that a row travelling alone
    # into a surface like this one must still say what kind of thing it is.
    id_kind: str
    layer: str


class DocumentSearchResponse(BaseModel):
    items: list[SectionHitModel]
    horizon: bool = True


class OutlineNodeModel(BaseModel):
    block_id: str
    level: int
    text: str
    order_index: int | None


class DocumentOutlineResponse(BaseModel):
    document_id: str
    items: list[OutlineNodeModel]
    horizon: bool = True


class BlockRowModel(BaseModel):
    block_id: str
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    # The enclosing block, or None at the top level. A nested list item's
    # parent is the enclosing *item*, so a renderer rebuilds the tree from
    # this alone rather than inferring depth.
    parent_id: str | None = None
    # A heading's level, a table's header and alignments. NOT a list marker:
    # the parser writes no properties for a list block at all.
    properties: dict | None = None
    # The block's own markdown source. `text` is marker-stripped, so they
    # differ: a heading's text is "Foo" where its source is "## Foo".
    source: str | None = None


class DocumentBlocksResponse(BaseModel):
    document_id: str
    blocks: list[BlockRowModel]
    # The verbatim filed source, which blocks.char_span indexes into. Present
    # only when the request opted in with include_content -- absent by default
    # so no existing reader pays for a potentially megabyte field (spec §5.2).
    content: str | None = None
    # Served unconditionally: one short string, and without it a caller cannot
    # precondition its first edit at all (spec section 5).
    content_hash: str | None = None
    horizon: bool = True


_LIST_SQL = text(
    """
    SELECT CAST(d.id AS text) AS id, d.title, d.uri, d.source_type, d.project,
           d.pinned_at, count(b.id) AS block_count
    FROM documents d
    LEFT JOIN blocks b ON b.document_id = d.id
    -- CAST because asyncpg cannot infer a bare parameter's type in an
    -- IS NULL comparison (the cross-cutting invariant on raw-SQL params).
    WHERE (CAST(:project AS text) IS NULL OR d.project = CAST(:project AS text))
    GROUP BY d.id, d.title, d.uri, d.source_type, d.project, d.pinned_at
    ORDER BY d.created_at DESC
    LIMIT :limit OFFSET :offset
    """
)


class DocumentManifestItem(BaseModel):
    id: str
    uri: str
    content_hash: str | None
    updated_at: datetime


class DocumentManifestResponse(BaseModel):
    items: list[DocumentManifestItem]
    next_after: str | None


# The whole-segment prefix predicate the subtree rename and delete use, so
# `superpowers` never matches `superpowersx/`. An empty prefix lists the whole
# project. Keyset on uri, which is unique within a project.
_MANIFEST_SQL = text(
    """
    SELECT CAST(id AS text) AS id, uri, content_hash, updated_at
    FROM documents
    WHERE project = CAST(:project AS text)
      AND uri IS NOT NULL
      AND (CAST(:prefix AS text) = ''
           OR uri = CAST(:prefix AS text)
           OR left(uri, length(CAST(:prefix AS text)) + 1) = CAST(:prefix AS text) || '/')
      AND (CAST(:after AS text) IS NULL OR uri > CAST(:after AS text))
    ORDER BY uri
    LIMIT :limit
    """
)


@router.get("/manifest", response_model=DocumentManifestResponse)
async def document_manifest(
    project: str = Query(min_length=1),
    uri_prefix: str = Query(""),
    after: str | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentManifestResponse:
    """`{id, uri, content_hash, updated_at}` for a project's documents under a prefix, no content.

    What a mirror pull diffs against its recorded hashes, so it fetches only
    the documents that changed. A trailing slash on the prefix is dropped:
    `superpowers/` and `superpowers` name the same subtree.
    """
    rows = (await session.execute(
        _MANIFEST_SQL,
        {"project": project, "prefix": uri_prefix.rstrip("/"), "after": after, "limit": limit},
    )).mappings().all()
    items = [DocumentManifestItem(**dict(row)) for row in rows]
    return DocumentManifestResponse(
        items=items,
        next_after=items[-1].uri if len(items) == limit else None,
    )


class DocumentRevisionItem(BaseModel):
    id: str
    content_hash: str
    actor: str | None
    api_key_id: str | None
    created_at: datetime


class DocumentRevisionListResponse(BaseModel):
    document_id: str
    items: list[DocumentRevisionItem]
    next_before: str | None


class DocumentRevisionResponse(DocumentRevisionItem):
    document_id: str
    content: str


@router.get("/{document_id}/revisions", response_model=DocumentRevisionListResponse)
async def list_document_revisions_route(
    document_id: UUID,
    before: UUID | None = Query(None),
    limit: int = Query(
        document_revisions.DEFAULT_LIMIT, ge=1, le=document_revisions.MAX_LIMIT
    ),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentRevisionListResponse:
    """A document's revisions newest first, without content; page back with
    `next_before`. 404 when the document does not exist, 422 when `before`
    names no revision of it."""
    target = await _resolve_target(session, document_id=document_id, project=None, uri=None)
    try:
        page = await document_revisions.list_revisions(
            session, document_id=target, before=before, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return DocumentRevisionListResponse(**page)


@router.get(
    "/{document_id}/revisions/{revision_id}", response_model=DocumentRevisionResponse
)
async def get_document_revision_route(
    document_id: UUID,
    revision_id: UUID,
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentRevisionResponse:
    """One revision with the content it filed. 404 when the document does not
    exist or the revision is not one of its own."""
    target = await _resolve_target(session, document_id=document_id, project=None, uri=None)
    found = await document_revisions.get_revision(
        session, document_id=target, revision_id=revision_id,
    )
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no revision {revision_id} in document {target}"
        )
    return DocumentRevisionResponse(**found)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    rows = (await session.execute(
        _LIST_SQL, {"project": project, "limit": limit, "offset": offset}
    )).mappings().all()
    return DocumentListResponse(
        items=[DocumentListItem(**dict(row)) for row in rows]
    )


@router.post(
    "/{document_id}/summary",
    response_model=DocumentSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_summary(
    document_id: UUID,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> DocumentSummaryResponse:
    """Generate this document's summary and store it. 201, because it creates
    the summary the GET twin reads.

    `summarise_document` shipped with no caller at all, so the GET route read
    a property nothing in the tree could write and every summary panel was
    empty by construction. This is that missing door.

    Spends an LLM call on the `summarization` purpose, which is why it carries
    `refuse_when_read_only` -- an external call is not a database write, so
    the viewer role's SQLSTATE 42501 handler would never catch it.

    422 rather than an empty 200 when the document has no blocks to summarise:
    `summarise_document` deliberately answers None there instead of storing
    "", so that "no summary yet" and "its summary is empty prose" stay
    different answers on the GET.
    """
    if await resolve_by_id(session, document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no document {document_id}",
        )
    try:
        summary = await summarise_document(session, llm, document_id=document_id)
    except EmptySummaryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc),
        ) from exc
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="this document has no blocks to summarise",
        )
    await session.commit()
    return DocumentSummaryResponse(
        document_id=summary.document_id,
        text=summary.text,
        generated_at=summary.generated_at,
        block_count=summary.block_count,
    )


@router.get("/{document_id}/summary", response_model=DocumentSummaryResponse)
async def get_document_summary(
    document_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummaryResponse:
    """404 when no summary has been generated.

    Deliberately not an empty 200: "this document has no summary yet" and
    "its summary is empty prose" are different answers, and generating one is
    an explicit act nobody has performed (doc 16 §6, TH1.14).
    """
    summary = await read_summary(session, document_id=document_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary has been generated for this document",
        )
    return DocumentSummaryResponse(
        document_id=summary.document_id,
        text=summary.text,
        generated_at=summary.generated_at,
        block_count=summary.block_count,
    )


@router.get("/{document_id}/connections", response_model=DocumentConnectionsResponse)
async def get_document_connections(
    document_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentConnectionsResponse:
    """Documents nearest this one, with the passage pair that matched.

    No model call and no new table: both sides are already embedded, so this is
    a join. `embedded=false` says the comparison could not be made rather than
    that nothing relates.
    """
    connections = await connections_for_document(
        session, document_id=document_id, limit=limit,
    )
    return DocumentConnectionsResponse(
        embedded=connections.embedded,
        comparable_documents=connections.comparable_documents,
        items=[
            DocumentConnectionItem(
                document_id=c.document_id,
                title=c.title,
                score=c.score,
                block_id=c.block_id,
                block_text=c.block_text,
                other_block_id=c.other_block_id,
                other_block_text=c.other_block_text,
            )
            for c in connections.items
        ],
    )


@router.get(
    "/{document_id}/related-memories", response_model=RelatedMemoriesResponse
)
async def get_related_memories(
    document_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> RelatedMemoriesResponse:
    """Memories nearest this document, with the passage that matched.

    No model call and no new table: both sides are already embedded, so this is
    a join. `embedded=false` says the comparison could not be made rather than
    that nothing relates.
    """
    related = await related_memories_for_document(
        session, document_id=document_id, limit=limit,
    )
    return RelatedMemoriesResponse(
        embedded=related.embedded,
        comparable_memories=related.comparable_memories,
        items=[
            RelatedMemoryItem(
                memory_id=m.memory_id,
                content=m.content,
                memory_type=m.memory_type,
                status=m.status,
                source=m.source,
                project=m.project,
                score=m.score,
                block_id=m.block_id,
                block_text=m.block_text,
                span_start=m.span_start,
                span_end=m.span_end,
            )
            for m in related.items
        ],
    )


@router.post("/qa", response_model=QaResponse)
async def grounded_qa(
    body: QaRequest,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> QaResponse:
    """Retrieve, generate, gate — in that order, and the gate decides.

    The check runs before this returns, never after: a caller cannot obtain
    the sentences and the verdict separately, so there is no window in which
    ungated prose exists on the wire (TH1.09).
    """
    answer = await GroundedQaService(session, llm).answer(
        body.question,
        project=body.project,
        max_blocks=body.max_blocks,
        document_id=body.document_id,
    )

    gated = await FaithfulnessGate(session, llm=llm).check(
        answer, allow_labelled=body.allow_labelled,
    )

    sentences: list[QaSentence] = []
    if gated.outcome is not Outcome.WITHHELD:
        for sentence in gated.answer.sentences:
            citation = None
            if sentence.citation is not None:
                start, end = sentence.citation.char_span
                citation = QaCitation(
                    block_id=sentence.citation.block_id,
                    document_id=sentence.citation.document_id,
                    span_start=start,
                    span_end=end,
                )
            sentences.append(QaSentence(text=sentence.text, citation=citation))

    return QaResponse(
        question=body.question,
        outcome=gated.outcome.value,
        grounded=gated.grounded,
        label=gated.label,
        entailed=gated.entailed,
        total=gated.total,
        judged=gated.judged,
        reason=gated.reason,
        sentences=sentences,
    )


@router.post("", response_model=DocumentPutResponse, status_code=status.HTTP_201_CREATED)
async def put_document_route(
    body: DocumentPutRequest,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> DocumentPutResponse:
    """File one document, then embed its blocks.

    201 on every outcome including `unchanged`: the document exists at a
    known id either way, and a caller distinguishing the cases reads
    `outcome`.
    """
    try:
        result = await put_document(
            session, llm,
            project=body.project, uri=body.uri, content=body.content,
            title=body.title, source_type=body.source_type, source="api",
            actor=principal.actor,
            api_key_id=principal.api_key_id,
            expected_hash=body.expected_hash,
        )
    except DocumentTooLarge as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except UnsupportedSource as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except DocumentIsBlockFirst as exc:
        # 409, the conventions' conflict shape and the same status the
        # content-hash CAS uses: the caller made no mistake, the document is
        # simply owned by the block verbs now.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except DocumentHashConflict as exc:
        # 409, not 422: the caller made no mistake -- it lost a race, or the
        # document moved since it last read it. The detail names both hashes
        # so the caller can re-read and retry without a second round trip.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        ) from exc

    return DocumentPutResponse(
        document_id=result.document_id,
        outcome=result.outcome,
        blocks_filed=result.blocks_filed,
        blocks_embedded=result.blocks_embedded,
        title_applied=result.title_applied,
        oversized_blocks=result.oversized_blocks,
        largest_block_chars=result.largest_block_chars,
        content_hash=result.content_hash,
    )


@router.post("/rename", response_model=DocumentRenameResponse)
async def rename_documents_route(
    body: DocumentRenameRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentRenameResponse:
    """Rewrite a uri prefix across a subtree.

    A POST rather than a PATCH because the request names no single document:
    the body carries the whole address of the work, which is the conventions'
    complex-request shape.
    """
    try:
        renamed = await rename_documents(
            session,
            project=body.project,
            uri_prefix=body.uri_prefix,
            new_uri_prefix=body.new_uri_prefix,
        )
    except DocumentUriConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except DocumentNothingToChange as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc
    await session.commit()
    return DocumentRenameResponse(renamed=renamed)


@router.post("/delete", response_model=DocumentSubtreeDeleteResponse)
async def delete_subtree_route(
    body: DocumentSubtreeDeleteRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentSubtreeDeleteResponse:
    """Delete every document under a uri prefix.

    POST rather than DELETE, and 200 rather than 204: `DELETE`-with-body is
    poorly supported by clients and proxies, and the reply is a count. The
    conventions name `POST /memories/delete` as the bulk-delete precedent.
    """
    try:
        deleted = await delete_documents(
            session, project=body.project, uri_prefix=body.uri_prefix,
        )
    except DocumentNothingToChange as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc
    await session.commit()
    return DocumentSubtreeDeleteResponse(deleted=deleted)


@router.patch("/{document_id}", response_model=DocumentPatchResponse)
async def patch_document_route(
    document_id: UUID,
    body: DocumentPatchRequest,
    principal: Principal = Depends(_require_capture),
    session: AsyncSession = Depends(get_session),
) -> DocumentPatchResponse:
    """Write only the metadata fields the caller named.

    A capture-scoped key reaches this route as it reaches filing, so a
    client can retire a document by moving it under `expected_hash`: a move
    keeps the document's revisions, where a delete would cascade them away.
    The subtree rename stays login-only.
    """
    try:
        await update_document_metadata(
            session,
            document_id=document_id,
            title=body.title,
            uri=body.uri,
            pinned=body.pinned,
            tags=body.tags,
            expected_hash=body.expected_hash,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
        )
    except DocumentTargetUnresolved as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except DocumentUriConflict as exc:
        # 409, the same shape the content-hash CAS and the block-first
        # refusal use: the caller made no mistake, the path is taken.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except DocumentHashConflict as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        ) from exc
    except DocumentNothingToChange as exc:
        # 422 rather than 200: the body is well formed and names nothing to
        # do, which is the same class as a body pydantic would reject.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc
    await session.commit()
    return DocumentPatchResponse(document_id=str(document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/by-uri", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_route(
    document_id: UUID | None = None,
    project: str | None = Query(None),
    uri: str | None = Query(None),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove a document, its block subtree and its vectors.

    `blocks.document_id` cascades and `block_embeddings__<slug>` cascades
    from there, so one delete takes all three in every partition. There is
    no provenance to close behind it: nothing mints a `fact_sources` row
    from a block, so a document's blocks corroborate no fact and deleting
    one cannot leave a fact standing on evidence that no longer exists. It
    journals nothing either — there is no delete event type.
    Wire-shape production belongs in the shared
    service, not here, so an MCP delete twin calls the same function rather
    than re-implementing this — the same reason `title_applied` has one
    producer rather than one per transport.

    Answers at `/{document_id}` and at `/by-uri?project=&uri=`; see the
    module docstring for why the pair is ordered the way it is.
    """
    target = await _resolve_target(
        session, document_id=document_id, project=project, uri=uri,
    )
    existed = await delete_document(session, document_id=target)
    if not existed:
        # Unreachable through `_resolve_target`, which has already confirmed
        # the row -- kept because the service reports it and a concurrent
        # delete between the two statements is the one way it can still be
        # False.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "document not found")
    await session.commit()


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents_route(
    body: DocumentSearchRequest,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> DocumentSearchResponse:
    """Rank this project's blocks and resolve each hit's heading path.

    An empty list means no match, never a failure -- the block channel has
    one arm (`block_query.py`'s own rule), so a failure raises rather than
    degrading to `[]`. Read-only: writes nothing and commits nothing, same
    as `search_sections` itself.

    404 when `document_id` names no document, through the same resolver the
    keyed verbs use: an empty page for a document that is gone is the one
    answer a caller cannot tell from a genuine no-match.
    """
    try:
        hits = await search_sections(
            session, llm, query=body.query, project=body.project,
            limit=body.limit, document_id=body.document_id,
        )
    except DocumentTargetUnresolved as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return DocumentSearchResponse(
        items=[SectionHitModel(**vars(h)) for h in hits]
    )


@router.get("/{document_id}/outline", response_model=DocumentOutlineResponse)
@router.get("/by-uri/outline", response_model=DocumentOutlineResponse)
async def document_outline_route(
    document_id: UUID | None = None,
    project: str | None = Query(None),
    uri: str | None = Query(None),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentOutlineResponse:
    """The heading tree, no body text -- the map before an agent decides
    what to pull with `GET /{document_id}` below. Read-only, same as
    `search_documents_route`: writes and commits nothing.

    404 when the document does not exist, distinguishing "deleted or never
    filed" from "filed but has no headings" -- the same distinction
    `get_document_summary` draws between "no summary yet" and an empty one,
    and the same condition `delete_document_route` already 404s on for this
    exact id. Answers at `/{document_id}/outline` and at
    `/by-uri/outline?project=&uri=`; see the module docstring for the
    ordering the pair depends on.
    """
    target = await _resolve_target(
        session, document_id=document_id, project=project, uri=uri,
    )

    nodes = await document_outline(session, document_id=target)
    return DocumentOutlineResponse(
        document_id=target,
        items=[OutlineNodeModel(**vars(n)) for n in nodes],
    )


@router.get("/by-uri", response_model=DocumentBlocksResponse)
async def document_blocks_by_uri_route(
    block_ids: list[UUID] | None = Query(default=None),
    project: str | None = Query(None),
    uri: str | None = Query(None),
    include_content: bool = Query(False),
    _principal: Principal = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> DocumentBlocksResponse:
    """The keyed twin of `GET /{document_id}`: same read, reachable by a read key.

    Registered before `/{document_id}` so the literal path wins the match.
    """
    return await _document_blocks_response(
        session, document_id=None, block_ids=block_ids, project=project, uri=uri,
        include_content=include_content,
    )


@router.get("/{document_id}", response_model=DocumentBlocksResponse)
async def document_blocks_route(
    document_id: UUID | None = None,
    block_ids: list[UUID] | None = Query(default=None),
    project: str | None = Query(None),
    uri: str | None = Query(None),
    include_content: bool = Query(False),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DocumentBlocksResponse:
    """The whole document's blocks in order, or only the ones named in
    `block_ids` -- the drill-down after an outline. Read-only, same as
    `search_documents_route`: writes and commits nothing.

    `block_ids` is `list[UUID]`, not `list[str]`: a malformed value fails
    FastAPI's own validation (422) instead of reaching
    `CAST(:ids AS uuid[])` and surfacing as an unhandled 500, the same
    validation `document_id: UUID` on this signature already earns.

    404 when the document does not exist -- see `document_outline_route`.
    Answers at `/{document_id}`; `/by-uri?project=&uri=` has its own keyed
    handler, `document_blocks_by_uri_route`; both answer through
    `_document_blocks_response`.
    """
    return await _document_blocks_response(
        session, document_id=document_id, block_ids=block_ids, project=project,
        uri=uri, include_content=include_content,
    )


async def _document_blocks_response(
    session: AsyncSession,
    *,
    document_id: UUID | None,
    block_ids: list[UUID] | None,
    project: str | None,
    uri: str | None,
    include_content: bool,
) -> DocumentBlocksResponse:
    target = await _resolve_target(
        session, document_id=document_id, project=project, uri=uri,
    )

    rows = await document_blocks(
        session, document_id=target,
        block_ids=[str(b) for b in block_ids] if block_ids is not None else None,
    )
    content = (
        await document_content(session, document_id=target)
        if include_content
        else None
    )
    return DocumentBlocksResponse(
        document_id=target,
        blocks=[BlockRowModel(**vars(r)) for r in rows],
        content=content,
        content_hash=await document_hash(session, document_id=target),
    )


# ── Block verbs (increment 8, spec §8) ───────────────────────────────
#
# Four routes over `block_verbs`, which both doors share. A keyed handler
# confirms the block belongs to the path's document first: a block in another
# document does not exist *at this path*, so a mismatch is the same 404 as a
# missing block rather than a 403 that would confirm the id exists elsewhere.


def _block_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BlockTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, BlockCycleError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    if isinstance(exc, (DocumentTooLarge, DocumentNotConvertible)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    if isinstance(exc, DocumentHashConflict):
        # 409, not 422: the caller made no mistake -- it lost a race, or the
        # document moved since it last read it. The detail names both hashes
        # so it can re-read and retry without a second round trip.
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"document's current content_hash {exc.current_hash}",
        )
    raise exc


async def _assert_block_is_in(session, document_id: UUID, block_id: UUID) -> None:
    owner = (await session.execute(
        text("SELECT CAST(document_id AS text) FROM blocks WHERE id = CAST(:id AS uuid)"),
        {"id": str(block_id)},
    )).scalar_one_or_none()
    if owner is None or owner != str(document_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no block {block_id} in document {document_id}",
        )


@router.post(
    "/{document_id}/blocks",
    response_model=BlockWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_block_route(
    document_id: UUID,
    body: BlockInsertRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> BlockWriteResponse:
    """Insert a block. First child of `parent_id` by default, or after
    `after_block_id` among that parent's children."""
    try:
        result = await insert_block(
            session, llm, document_id=str(document_id), type=body.type,
            text=body.text, parent_id=body.parent_id,
            after_block_id=body.after_block_id, properties=body.properties,
            expected_hash=body.expected_hash,
        )
    except Exception as exc:
        raise _block_write_error(exc) from exc
    return BlockWriteResponse(**vars(result))


@router.patch("/{document_id}/blocks/{block_id}", response_model=BlockWriteResponse)
async def update_block_route(
    document_id: UUID,
    block_id: UUID,
    body: BlockUpdateRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> BlockWriteResponse:
    await _assert_block_is_in(session, document_id, block_id)
    try:
        result = await update_block(
            session, llm, block_id=str(block_id), text=body.text,
            type=body.type, properties=body.properties,
            expected_hash=body.expected_hash,
        )
    except Exception as exc:
        raise _block_write_error(exc) from exc
    return BlockWriteResponse(**vars(result))


@router.post("/{document_id}/blocks/{block_id}/move", response_model=BlockWriteResponse)
async def move_block_route(
    document_id: UUID,
    block_id: UUID,
    body: BlockMoveRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> BlockWriteResponse:
    """Verb-shaped POST rather than a PATCH: a move is not a partial update
    of the block's own fields, it is a repositioning within the tree."""
    await _assert_block_is_in(session, document_id, block_id)
    try:
        result = await move_block(
            session, llm, block_id=str(block_id),
            new_parent_id=body.new_parent_id, after_block_id=body.after_block_id,
            expected_hash=body.expected_hash,
        )
    except Exception as exc:
        raise _block_write_error(exc) from exc
    return BlockWriteResponse(**vars(result))


@router.delete(
    "/{document_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_block_route(
    document_id: UUID,
    block_id: UUID,
    expected_hash: str | None = Query(
        None, description="Refuse unless the document's content_hash matches."
    ),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> None:
    """204 with no body, per the REST conventions. The subtree goes with it.

    `expected_hash` rides the query string here, not a body field: DELETE
    carries no body in this API's conventions, so a body field would be
    silently ignored rather than refused."""
    await _assert_block_is_in(session, document_id, block_id)
    try:
        await delete_block(session, llm, block_id=str(block_id), expected_hash=expected_hash)
    except Exception as exc:
        raise _block_write_error(exc) from exc
