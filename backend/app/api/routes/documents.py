"""The documents read surface (TH1.16, doc 16 §6, doc 13).

Provides:
  - GET    /api/v1/documents
  - GET    /api/v1/documents/{document_id}/summary
  - GET    /api/v1/documents/{document_id}/connections
  - GET    /api/v1/documents/{document_id}/outline
  - GET    /api/v1/documents/{document_id}
  - POST   /api/v1/documents/qa
  - POST   /api/v1/documents
  - DELETE /api/v1/documents/{document_id}
  - POST   /api/v1/documents/search
  - GET    /api/v1/documents/by-uri/outline
  - GET    /api/v1/documents/by-uri
  - DELETE /api/v1/documents/by-uri

**A caller that filed by path has a path, not an id.** The three verbs keyed
on a document — outline, blocks, delete — each answer at two paths served by
one handler: the `{document_id}` form and a `by-uri` form taking `?project=`
and `?uri=`. One handler rather than two so the two addressing forms cannot
answer differently, and `document_door.resolve_document_target` is the single
producer of every refusal, shared with the MCP twins.

**Each `by-uri` route must be registered before its `{document_id}` sibling**,
which is why it is the lower decorator of the two: decorators apply
bottom-up, `/{document_id}` matches the literal segment `by-uri` too, and
whichever registers first wins the match. Reversing the pair does not fail —
it answers 422 `invalid uuid` for every by-uri call, which is why
`test_by_uri_is_not_shadowed_by_the_id_route` pins it.

**This is the EH1 horizon's one door and it adds no semantics.** Every read is
a call into a service that already exists and already carries the honesty rule
it enforces: `read_summary` (unbadged by construction), `connections_for_document`
(emergent, no model call), and the grounded Q&A flow behind its faithfulness
gate. The door's own job is to serve those answers without softening them.

**The Q&A response is the gate's verdict, not the answer plus a hint.** It
carries `grounded`, `outcome`, the counts the decision was made on, and the
sentences — and when the outcome is `withheld` it carries **no sentences at
all**. A withheld answer whose text was still on the wire would be served as
ungrounded prose by any client that forgot to read a flag, which is exactly
invariant 14's failure. The label is the payload in that case.

**No lift door.** `lift_document` is on-demand by design and a route is the
easiest way for something to call it on a schedule; nothing in EH1 needs one
before a human asks, so the trigger stays out of the HTTP surface (TH1.11).
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_llm
from app.database import get_session
from app.services.block_pipeline import UnsupportedSource
from app.services.document_connections import connections_for_document
from app.services.document_door import (
    SEARCH_DEFAULT_LIMIT, SEARCH_MAX_LIMIT, DocumentTargetUnresolved,
    DocumentTooLarge, delete_document, document_blocks, document_outline,
    put_document, resolve_document_target, search_sections,
)
from app.services.document_parsers import DocumentParseError
from app.services.document_summary import read_summary
from app.services.faithfulness_gate import FaithfulnessGate, Outcome
from app.services.grounded_qa import GroundedQaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


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


class DocumentConnectionItem(BaseModel):
    document_id: str
    title: str | None
    shared_entities: list[str]


class DocumentConnectionsResponse(BaseModel):
    items: list[DocumentConnectionItem]
    horizon: bool = True


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


class DocumentBlocksResponse(BaseModel):
    document_id: str
    blocks: list[BlockRowModel]
    horizon: bool = True


_LIST_SQL = text(
    """
    SELECT CAST(d.id AS text) AS id, d.title, d.uri, d.source_type, d.project,
           count(b.id) AS block_count
    FROM documents d
    LEFT JOIN blocks b ON b.document_id = d.id
    -- CAST because asyncpg cannot infer a bare parameter's type in an
    -- IS NULL comparison (the cross-cutting invariant on raw-SQL params).
    WHERE (CAST(:project AS text) IS NULL OR d.project = CAST(:project AS text))
    GROUP BY d.id, d.title, d.uri, d.source_type, d.project
    ORDER BY d.created_at DESC
    LIMIT :limit OFFSET :offset
    """
)


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
    connections = await connections_for_document(
        session, document_id=document_id, limit=limit,
    )
    return DocumentConnectionsResponse(
        items=[
            DocumentConnectionItem(
                document_id=c.document_id,
                title=c.title,
                shared_entities=list(c.shared_entities),
            )
            for c in connections
        ]
    )


@router.post("/qa", response_model=QaResponse)
async def grounded_qa(
    body: QaRequest,
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
    _user=Depends(require_auth),
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
        )
    except DocumentTooLarge as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except UnsupportedSource as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return DocumentPutResponse(
        document_id=result.document_id,
        outcome=result.outcome,
        blocks_filed=result.blocks_filed,
        blocks_embedded=result.blocks_embedded,
        title_applied=result.title_applied,
    )


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
    from there, so one delete takes all three in every partition. Neither
    cascade reaches `fact_sources`: `source_ref` carries no foreign key, so
    a fact a deleted document's blocks corroborated would otherwise keep
    its origin count and its verification rung on evidence that no longer
    exists, and never get recomputed until the slow reconciliation arm's
    rotation happened to reach it. `delete_document` closes that window —
    withdrawing the block sources, expiring any fact left with none, and
    enqueueing every affected fact for the ordinary verification recompute
    — before the row goes. Wire-shape production belongs in the shared
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
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> DocumentSearchResponse:
    """Rank this project's blocks and resolve each hit's heading path.

    An empty list means no match, never a failure -- the block channel has
    one arm (`block_query.py`'s own rule), so a failure raises rather than
    degrading to `[]`. Read-only: writes nothing and commits nothing, same
    as `search_sections` itself.
    """
    hits = await search_sections(
        session, llm, query=body.query, project=body.project,
        limit=body.limit, document_id=body.document_id,
    )
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


@router.get("/{document_id}", response_model=DocumentBlocksResponse)
@router.get("/by-uri", response_model=DocumentBlocksResponse)
async def document_blocks_route(
    document_id: UUID | None = None,
    block_ids: list[UUID] | None = Query(default=None),
    project: str | None = Query(None),
    uri: str | None = Query(None),
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
    Answers at `/{document_id}` and at `/by-uri?project=&uri=`.
    """
    target = await _resolve_target(
        session, document_id=document_id, project=project, uri=uri,
    )

    rows = await document_blocks(
        session, document_id=target,
        block_ids=[str(b) for b in block_ids] if block_ids is not None else None,
    )
    return DocumentBlocksResponse(
        document_id=target,
        blocks=[BlockRowModel(**vars(r)) for r in rows],
    )
