"""Filing a document — the first writer to `documents` / `blocks` (TH1.02).

Doc 16 §3's pipeline variant, up to the point where blocks exist. Two things
are settled here and nothing else is: **which row a filed source is**, and
**whether any work runs at all**.

**Identity.** ``(project, uri)`` when the source has a locator, the row's own
id when it does not. The partial ``UNIQUE (project, uri) WHERE uri IS NOT NULL``
is what makes both true at once — many uri-less notes coexist because NULLs do
not collide under the predicate, while a re-filed path resolves to the row it
resolved to last time. The constraint lives in the database, so a caller that
races the resolving SELECT folds onto the existing row instead of minting a
second one.

**The change gate.** ``content_hash`` decides whether the pipeline runs, the
way an unchanged HEAD sha short-circuits a code reindex. An unchanged hash
does *nothing*: no parse, no strip, no block write, no journal row, not even a
bumped ``updated_at``. That is why ``parse`` is a callable rather than a
materialised block list — the gate sits in front of the parse in doc 16 §3's
flowchart, and a caller that had to parse before calling would have paid the
expensive half of the pipeline before the gate could refuse it.

**The gate's cost, stated rather than discovered.** It keys on content alone,
so re-filing identical content under a new ``title`` (or a new
``source_type``, or new ``properties``) short-circuits and the metadata does
not move. Metadata-only edits are a document *update* surface, not a filing;
folding them in here would mean the gate no longer answers "did the content
change", and the whole short-circuit would turn on a field a caller can wiggle.

**Blocks are replaced, never merged** (doc 16 §3, invariant 8 generalised):
the document's prior blocks are stripped before the new set is written, in the
caller's transaction, so a failed write leaves the prior tree rather than a
half-replaced one. Block ids are minted fresh each time, which is what makes
"this re-ingest did no block work" observable from outside rather than merely
asserted — an unchanged re-file leaves the *same* ids behind.

What this module deliberately does **not** do: parse anything (TH1.03 owns the
parser stack), embed anything (TH1.05 owns ``block_embeddings__<slug>``), or
run the five-phase memory pipeline over document content (doc 16 §3 — a filed
document is candidate signal, and reaches the graph only through the on-demand
lift in §5). It does not commit; the caller owns the transaction boundary.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import documents as documents_repo
from app.services.events import record_event
from app.taxonomy import normalize_block_type
from app.utils.ids import new_id

__all__ = [
    "BlockDraft",
    "CREATED",
    "DOCUMENT_FILED_EVENT",
    "DocumentFileFailure",
    "DocumentFileJob",
    "DocumentIngest",
    "UNCHANGED",
    "UPDATED",
    "compute_content_hash",
    "file_document",
    "file_documents_isolated",
]

DOCUMENT_FILED_EVENT = "document_filed"
OBJECT_TYPE = "document"

CREATED = "created"
UPDATED = "updated"
UNCHANGED = "unchanged"


@dataclass(frozen=True)
class BlockDraft:
    """One block as a parser hands it over, before ids exist.

    ``parent`` is an index into the same draft sequence and must point
    *backwards*: a parser emits a tree in reading order, and the restriction is
    what makes a cycle unrepresentable — the table has no constraint that would
    catch one, and a cyclic tree is a renderer that never terminates.
    """

    text: str
    type: str = "paragraph"
    parent: int | None = None
    order_index: int | None = None
    properties: dict | None = None
    char_span: tuple[int, int] | None = None


@dataclass(frozen=True)
class DocumentIngest:
    document_id: UUID
    outcome: str
    content_hash: str
    blocks_written: int = 0
    blocks_stripped: int = 0


def compute_content_hash(content: str | bytes) -> str:
    """The change gate's key. Text is hashed as UTF-8 so a source read as
    ``str`` and the same source read as ``bytes`` gate identically."""
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw).hexdigest()


async def file_document(
    session: AsyncSession,
    *,
    project: str,
    content: str | bytes,
    parse: Callable[[], Sequence[BlockDraft]],
    uri: str | None = None,
    document_id: UUID | None = None,
    title: str | None = None,
    source_type: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    source: str | None = None,
) -> DocumentIngest:
    """File `content` as a document and replace its blocks. Does not commit.

    `document_id` addresses an existing uri-less document — a note being
    re-filed. Passing it alongside a `uri` is refused rather than resolved by
    precedence: the two name different identities, and silently preferring one
    would re-ingest a row the caller did not mean.
    """
    if uri is not None and document_id is not None:
        raise ValueError(
            "a document is identified by (project, uri) or by id, never both: "
            "pass `uri` for a located source, `document_id` to re-file a note"
        )

    content_hash = compute_content_hash(content)

    if uri is not None:
        existing = await documents_repo.resolve_by_uri(session, project=project, uri=uri)
    elif document_id is not None:
        existing = await documents_repo.resolve_by_id(session, document_id)
    else:
        existing = None

    if existing is not None and existing.content_hash == content_hash:
        return DocumentIngest(existing.id, UNCHANGED, content_hash)

    if existing is None:
        minted = document_id or new_id()
        resolved_id = await documents_repo.upsert_by_uri(
            session,
            document_id=minted,
            project=project,
            uri=uri,
            title=title,
            source_type=source_type,
            content_hash=content_hash,
            properties=properties,
        )
        # A different id back means another filer won the uri between the
        # resolve above and this write; that row is the document, and this
        # call updated it.
        outcome = CREATED if resolved_id == minted else UPDATED
    else:
        resolved_id = existing.id
        outcome = UPDATED
        await documents_repo.update_document(
            session,
            document_id=resolved_id,
            title=title,
            source_type=source_type,
            content_hash=content_hash,
            properties=properties,
        )

    stripped = await documents_repo.strip_blocks(session, resolved_id)
    rows = _resolve_tree(parse())
    await documents_repo.insert_blocks(session, resolved_id, rows)

    # Best-effort, unlike a verification transition: no metric is SQL over
    # these rows, so a filing that did not journal is a lost log line rather
    # than a corrupted denominator. The payload carries no block text — a
    # journal row outlives the document it describes.
    await record_event(
        session,
        event_type=DOCUMENT_FILED_EVENT,
        object_type=OBJECT_TYPE,
        object_id=resolved_id,
        project=project,
        actor=actor,
        source=source,
        payload={
            "outcome": outcome,
            "content_hash": content_hash,
            "source_type": source_type,
            "blocks_written": len(rows),
            "blocks_stripped": stripped,
        },
    )

    return DocumentIngest(
        resolved_id, outcome, content_hash,
        blocks_written=len(rows), blocks_stripped=stripped,
    )


@dataclass(frozen=True)
class DocumentFileJob:
    """One document to file, addressed the same way `file_document` is.

    `label` is the caller's own identifier for reporting a failure — a
    filename, a uri, whatever the batch was keyed on — never used to resolve
    identity; that is still `uri` or `document_id`.
    """

    project: str
    content: str | bytes
    parse: Callable[[], Sequence[BlockDraft]]
    uri: str | None = None
    document_id: UUID | None = None
    title: str | None = None
    source_type: str | None = None
    properties: dict | None = None
    actor: str | None = None
    source: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class DocumentFileFailure:
    label: str | None
    error: str


async def file_documents_isolated(
    session: AsyncSession, jobs: Sequence[DocumentFileJob],
) -> list[DocumentIngest | DocumentFileFailure]:
    """File every job, isolating one job's failure from the rest of the batch.

    A parse failure (TH1.03's parsers all raise `DocumentParseError` on
    unparseable content) is the expected case, but nothing here is narrowed to
    that type — any exception `file_document` lets through isolates the same
    way, including a bad-parent `ValueError` or a genuine database error.

    **Why a SAVEPOINT and not a bare try/except.** `file_document` does not
    commit (the caller owns the transaction boundary), so a parse failure
    lands *after* the strip and *before* the new blocks are written — the
    exact midpoint doc 16 §3's flowchart draws as one atomic step. Without a
    SAVEPOINT, catching the exception and moving on would leave that
    document's prior blocks deleted with nothing written to replace them,
    staged in the caller's still-open transaction, to be committed along with
    every other job's success. `session.begin_nested()` scopes each job to
    its own SAVEPOINT: on exception it rolls back to the mark automatically
    (SQLAlchemy's async context-manager contract) before this function's own
    `except` ever runs, so the failed job's partial writes never reach the
    outer transaction and every other job's is untouched.
    """
    results: list[DocumentIngest | DocumentFileFailure] = []
    for job in jobs:
        try:
            async with session.begin_nested():
                result = await file_document(
                    session,
                    project=job.project,
                    content=job.content,
                    parse=job.parse,
                    uri=job.uri,
                    document_id=job.document_id,
                    title=job.title,
                    source_type=job.source_type,
                    properties=job.properties,
                    actor=job.actor,
                    source=job.source,
                )
        except Exception as exc:
            results.append(DocumentFileFailure(label=job.label, error=str(exc)))
        else:
            results.append(result)
    return results


def _resolve_tree(drafts: Sequence[BlockDraft]) -> list[documents_repo.BlockRow]:
    """Mint ids, resolve `parent` indexes to those ids, normalise the type."""
    ids = [new_id() for _ in drafts]
    rows: list[documents_repo.BlockRow] = []
    for position, draft in enumerate(drafts):
        parent_id = None
        if draft.parent is not None:
            if not 0 <= draft.parent < position:
                raise ValueError(
                    f"block {position} names parent {draft.parent}: a parent must be "
                    "an earlier draft in the same sequence"
                )
            parent_id = ids[draft.parent]
        rows.append(
            documents_repo.BlockRow(
                id=ids[position],
                parent_id=parent_id,
                order_index=position if draft.order_index is None else draft.order_index,
                type=normalize_block_type(draft.type),
                text=draft.text,
                properties=draft.properties,
                char_span=draft.char_span,
            )
        )
    return rows
