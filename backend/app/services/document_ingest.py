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

**The replace is atomic in the writer, not in each caller** (TH1.18). The strip
runs before a parse that can fail, so an unguarded filing leaves the document
row carrying the *new* ``content_hash`` while the old blocks are already
deleted and the replacement never landed — and the hash is the worse half,
because the next re-file of that same content short-circuits on a gate that now
agrees with a tree nobody wrote. So ``file_document`` opens a SAVEPOINT around
its whole body, the same atomic-replace shape Phase 5 gives savepoint B: a
failure anywhere in resolve, strip, parse or write rolls back to the mark, the
prior tree and the prior hash both survive, and the session stays usable for
the caller. TH1.04 gave that to the one module it owned, which left the
foot-gun live for every other direct caller; the guard belongs here, where a
caller cannot forget it. The declared cost is that the short-circuit path pays
a ``SAVEPOINT`` and a ``RELEASE`` it does not need — two statements that write
nothing and parse nothing, and are the price of the gate living inside the
guarded region rather than in front of it. Duplicating the gate outside it to
skip them would put two answers to "did the content change" in the tree.

``_file_document_without_savepoint`` is that body, unguarded and reachable, so
TH1.04's standing drill can run the identical failure through it and show the
damage the SAVEPOINT prevents — a guard whose absence is never
exercised is decorative. It is private, absent from ``__all__``, and
``tests/test_block_pipeline.py`` fails the build if anything outside
``file_document`` itself names it, anywhere under ``app/``, ``scripts/`` or
``migrations/``.

What this module deliberately does **not** do: parse anything (TH1.03 owns the
parser stack), embed anything (TH1.05 owns ``block_embeddings__<slug>``), or
run the five-phase memory pipeline over document content (doc 16 §3 — a filed
document is candidate signal, and reaches the graph only through the on-demand
lift in §5). It does not commit; the caller owns the transaction boundary.
"""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import documents as documents_repo
from app.services.block_embeddings import carry_document_vectors, document_vectors_by_text
from app.services.document_revisions import REVISION_KEEP_DAYS, REVISION_KEEP_NEWEST
from app.services.events import record_event
from app.taxonomy import normalize_block_type
from app.utils.ids import new_id

__all__ = [
    "BlockDraft",
    "CREATED",
    "DOCUMENT_FILED_EVENT",
    "DocumentHashConflict",
    "DocumentTooLarge",
    "DocumentUriConflict",
    "DocumentIngest",
    "OVERSIZED_BLOCK_CHARS",
    "REVISIONS_PRUNED_EVENT",
    "UNCHANGED",
    "UPDATED",
    "compute_content_hash",
    "file_document",
    "prune_revisions",
]

DOCUMENT_FILED_EVENT = "document_filed"
REVISIONS_PRUNED_EVENT = "document_revisions_pruned"
OBJECT_TYPE = "document"

class DocumentTooLarge(ValueError):
    """Refused at the door. The message names which bound was hit."""


class DocumentHashConflict(Exception):
    """``expected_hash`` did not match the document's current ``content_hash``.

    Three raise sites, one guarantee. ``file_document`` raises it after the
    SAVEPOINT has rolled the filing back, like every other filing failure; a
    block verb raises it under the document's row lock, before any savepoint
    has opened; ``document_door.update_document_metadata`` raises it after its
    guarded UPDATE matched no row (the SAVEPOINT has already closed on zero
    rows written), or, for a tags-only call, under the row lock before any
    tag is touched. Nothing was written on any path.

    ``current_hash`` is the hash that actually holds, so under a race it names
    the winner: re-read after the compare-and-set matched zero rows on the
    filing and metadata paths, read under the lock on the block path and the
    tags-only metadata path. It is None when the column itself is NULL.

    A missing document is reported differently per path, deliberately. Only
    the filing path reports it through this exception, with ``current_hash``
    None (and ``document_id`` None when nothing resolved at all), because an
    unfiled uri is a valid put target, so a hash naming it is a failed
    precondition rather than a bad address. The block verbs raise
    ``BlockTargetUnresolved`` and the metadata writer raises
    ``DocumentTargetUnresolved`` instead, never this exception.
    """

    def __init__(self, *, document_id, expected_hash: str, current_hash: str | None):
        self.document_id = document_id
        self.expected_hash = expected_hash
        self.current_hash = current_hash
        super().__init__(
            f"expected_hash {expected_hash} does not match the document's "
            f"current content_hash {current_hash}"
        )


class DocumentUriConflict(ValueError):
    """A rename would land on a ``(project, uri)`` another document holds.

    It sits beside the other conflict classes this module defines; its only
    raise site is ``document_door``, which imports it from here.
    """

    def __init__(self, uri: str | None):
        self.uri = uri
        super().__init__(
            f"another document in this project already holds the uri {uri!r}"
        )


# A stated conservative floor in CHARACTERS, not tokens: the tighter live
# embedder (nomic-embed-text) holds ~2048 tokens, and ~4 chars/token puts the
# start of truncation risk at 8,000 chars. Deliberately not a per-embedder
# probe -- that would put a model call on the parse path for a warning -- and
# deliberately char-basis: do not "correct" this to 2048, the bases differ.
OVERSIZED_BLOCK_CHARS = 8_000

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
    # None = not measured: the UNCHANGED short-circuit returns before any
    # parse. Measured (possibly 0) on CREATED/UPDATED. A reader must not
    # flatten None to 0 -- 0 is a clean bill this filing never issued.
    oversized_blocks: int | None = None
    largest_block_chars: int | None = None


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
    api_key_id: UUID | None = None,
    source: str | None = None,
    expected_hash: str | None = None,
    force_reparse: bool = False,
    carry_fingerprint: str | None = None,
    max_blocks: int | None = None,
) -> DocumentIngest:
    """File `content` as a document and replace its blocks, atomically.
    Does not commit.

    Raises whatever went wrong — an unparseable source, a malformed tree, a
    database error — after the SAVEPOINT has already rolled the whole filing
    back, so a caller that catches sees the document exactly as it was, keeps
    its prior `content_hash`, and gets a session it can keep using.

    With `carry_fingerprint`, each new block whose text an old block had keeps
    that text's vector under that fingerprint across the strip.
    """
    async with session.begin_nested():
        return await _file_document_without_savepoint(
            session,
            project=project,
            content=content,
            parse=parse,
            uri=uri,
            document_id=document_id,
            title=title,
            source_type=source_type,
            properties=properties,
            actor=actor,
            api_key_id=api_key_id,
            source=source,
            expected_hash=expected_hash,
            force_reparse=force_reparse,
            carry_fingerprint=carry_fingerprint,
            max_blocks=max_blocks,
        )


async def _file_document_without_savepoint(
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
    api_key_id: UUID | None = None,
    source: str | None = None,
    expected_hash: str | None = None,
    force_reparse: bool = False,
    carry_fingerprint: str | None = None,
    max_blocks: int | None = None,
) -> DocumentIngest:
    """`file_document`'s body with the atomic replace taken away.

    Reachable only from `file_document` and from the standing drill that
    exists to show what the SAVEPOINT buys; see the module docstring.

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
    # Text sources round-trip verbatim; a bytes source has no text form, so it
    # stores NULL rather than a lossy decode.
    stored_content = content if isinstance(content, str) else None

    if uri is not None:
        existing = await documents_repo.resolve_by_uri(session, project=project, uri=uri)
    elif document_id is not None:
        existing = await documents_repo.resolve_by_id(session, document_id)
    else:
        existing = None

    if expected_hash is not None:
        if existing is None:
            raise DocumentHashConflict(
                document_id=None, expected_hash=expected_hash, current_hash=None,
            )
        if existing.content_hash != expected_hash:
            # Fast-fail on the resolve's snapshot. This read-then-refuse only
            # ever REFUSES -- the authority that closes the race is the SQL
            # predicate below, which re-checks under the row lock. A spurious
            # refusal here (the row moved to `expected` after this read) is a
            # safe 409 the caller retries; the naive version of this feature
            # was a read-then-WRITE, which is the bug (review M1).
            raise DocumentHashConflict(
                document_id=existing.id,
                expected_hash=expected_hash,
                current_hash=existing.content_hash,
            )

    # Note the ordering decision: a byte-identical re-push carrying a STALE
    # expected_hash is a conflict, not UNCHANGED. The precondition "the
    # document is as I last saw it" failed, and refusing is the consistent
    # contract even where the write would have been a no-op. A matching
    # expected_hash still short-circuits here exactly as before.
    # `force_reparse` is the corpus-rewrite escape and nothing else: after a
    # parser change the filed blocks are stale while the bytes are identical,
    # so the change gate -- correct for every ordinary filing -- is exactly
    # what stops the fix reaching them. No door sets it; only the maintenance
    # script does. `expected_hash` is still honoured above, so forcing does
    # not also defeat a caller's compare-and-set.
    if (
        existing is not None
        and existing.content_hash == content_hash
        and not force_reparse
    ):
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
            content=stored_content,
            properties=properties,
        )
        # A different id back means another filer won the uri between the
        # resolve above and this write; that row is the document, and this
        # call updated it.
        outcome = CREATED if resolved_id == minted else UPDATED
    else:
        resolved_id = existing.id
        outcome = UPDATED
        matched = await documents_repo.update_document(
            session,
            document_id=resolved_id,
            title=title,
            source_type=source_type,
            content_hash=content_hash,
            content=stored_content,
            properties=properties,
            expected_hash=expected_hash,
        )
        if matched == 0 and expected_hash is not None:
            # The predicate re-evaluated under the row lock and disagreed:
            # another lane committed between our resolve and this write. Re-read
            # so the refusal names the hash that actually won.
            current = await documents_repo.resolve_by_id(session, resolved_id)
            raise DocumentHashConflict(
                document_id=resolved_id,
                expected_hash=expected_hash,
                current_hash=None if current is None else current.content_hash,
            )

    previous_vectors = (
        await document_vectors_by_text(session, resolved_id, carry_fingerprint)
        if carry_fingerprint is not None else {}
    )
    stripped = await documents_repo.strip_blocks(session, resolved_id)
    # Off the event loop: a megabyte of markdown parses for long enough to
    # stall every other request on the single worker. Counted before the
    # insert, so an oversized source writes no block row before the refusal.
    drafts = await asyncio.to_thread(parse)
    if max_blocks is not None and len(drafts) > max_blocks:
        raise DocumentTooLarge(
            f"document parses to {len(drafts)} blocks; the bound is {max_blocks} blocks"
        )
    rows = _resolve_tree(drafts)
    await documents_repo.insert_blocks(session, resolved_id, rows)
    if previous_vectors:
        await carry_document_vectors(session, resolved_id, carry_fingerprint, previous_vectors)

    # A post-image: the content this filing wrote, written only when the
    # filing changed the row's hash. A forced reparse of identical bytes
    # changed nothing a reader can see, and a bytes source has no text to keep.
    # A filing that resolved no row may still have updated one: losing a
    # first-filing race folds it onto the winner's row, whose prior hash it
    # never read. By here it holds that row's lock, so the winner's revision
    # has committed and is the prior hash; the upsert refuses a block-first
    # row, so no block edit sits between that revision and the row.
    if existing is not None:
        changed = existing.content_hash != content_hash
    else:
        changed = await documents_repo.latest_revision_hash(session, resolved_id) != content_hash
    if stored_content is not None and changed:
        await prune_revisions(
            session, resolved_id,
            project=project, actor=actor, api_key_id=api_key_id, source=source,
        )
        await documents_repo.insert_revision(
            session,
            revision_id=new_id(),
            document_id=resolved_id,
            content=stored_content,
            content_hash=content_hash,
            actor=actor,
            api_key_id=api_key_id,
        )

    # Counted, never refused: 27 corpus files exceed the budget and refusing
    # would block the import. An oversized block embeds truncated while the
    # filing reports success, so the count is the loud report invariant 14
    # asks for in place of a silent degradation.
    oversized = sum(1 for row in rows if len(row.text) > OVERSIZED_BLOCK_CHARS)
    largest = max((len(row.text) for row in rows), default=0)

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
        api_key_id=api_key_id,
        source=source,
        payload={
            "outcome": outcome,
            "content_hash": content_hash,
            "source_type": source_type,
            "blocks_written": len(rows),
            "blocks_stripped": stripped,
            "oversized_blocks": oversized,
            "largest_block_chars": largest,
        },
    )

    return DocumentIngest(
        resolved_id, outcome, content_hash,
        blocks_written=len(rows), blocks_stripped=stripped,
        oversized_blocks=oversized, largest_block_chars=largest,
    )


async def prune_revisions(
    session: AsyncSession,
    document_id: UUID,
    *,
    project: str,
    actor: str | None,
    api_key_id: UUID | None,
    source: str | None,
) -> None:
    # A filing runs this before its own revision is written, so the window
    # keeps the newest earlier revisions and the new one rides on top of them;
    # a block verb on a document runs it in its write savepoint. The count is
    # journalled first and the rows go only if that row landed: an unrecorded
    # erase of content is worse than keeping it one more write. A failed
    # delete raises into the caller's savepoint and refuses the write.
    ids = await documents_repo.prunable_revision_ids(
        session, document_id,
        keep_newest=REVISION_KEEP_NEWEST, keep_days=REVISION_KEEP_DAYS,
    )
    if not ids:
        return
    landed = await record_event(
        session,
        event_type=REVISIONS_PRUNED_EVENT,
        object_type=OBJECT_TYPE,
        object_id=document_id,
        project=project,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        payload={"pruned": len(ids)},
    )
    if landed:
        await documents_repo.delete_revisions(session, ids)


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
