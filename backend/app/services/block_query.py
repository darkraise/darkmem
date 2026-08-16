"""The block channel — document RAG, semantic-only, never fused (TH1.06).

Doc 16 §4 resolves the fuse-or-separate question in favour of **separate**:
block retrieval is its own channel and its own tool, the document-side twin of
code search, and document content reaches the four-layer memory/vault
composition only as *lifted facts* (§5), never as raw block rows. Three reasons
are recorded there and all three bind this module:

1. **The firewall.** Fusing blocks would make the core read path depend on the
   unshipped EH1 horizon, which is the one thing a horizon lane may never
   cause. `tests/test_block_retrieval.py` asserts the separation structurally
   rather than trusting this paragraph — no fusion module imports this one, and
   `block` is not a channel or an id-kind the composition knows.
2. **The product boundary.** This answers "what does my document corpus say",
   which is not "what has darkmem verified".
3. **The eval gate.** A separate tool can ship and be gated (G-F) without
   touching the core ranking path.

**Semantic-only is the v1 shape, stated rather than implied.** Doc 16 §4 makes
a keyword arm over block text a later refinement. There is one arm here, so
there is no fusion inside the channel either — no RRF, no rank arms, no
reranker — and a caller reading `score` is reading a cosine similarity, not a
fused rank.

**One arm means a failure raises.** Doc 07's channel shape lets a *one-sided*
failure degrade honestly because the other side still answers; with a single
side there is no honest degradation left, and returning `[]` would be
indistinguishable from "your corpus has no match" (invariant 14). So nothing
here catches — the caller sees the failure.

The trace addendum (`block` id-kind, `document` layer) is **TH1.07's**, not
this module's: until it lands, this channel emits no trace at all rather than
stamping a kind the shared enum does not yet carry (invariant 23).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import search_blocks

__all__ = ["BlockHit", "BlockQueryService"]


@dataclass(frozen=True)
class BlockHit:
    """One ranked block, resolved to its document and span.

    `char_span` is a half-open `[start, end)` pair or `None` — the parsers
    store a range and a block may carry none. It is a plain tuple because the
    point of serving it is that a caller can slice the source back out.
    """

    block_id: str
    document_id: str
    project: str
    uri: str | None
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    score: float


class BlockQueryService:
    def __init__(self, session: AsyncSession, llm) -> None:
        self.session = session
        self.llm = llm

    async def search(
        self,
        query: str,
        *,
        project: str,
        limit: int = 20,
        document_id: str | None = None,
    ) -> list[BlockHit]:
        """Rank this project's blocks against `query`.

        The query is embedded once and the probe runs against **the fingerprint
        that embedding produced**, never a separately resolved one: those two
        can differ across an embedder rotation, and comparing a vector from one
        embedder against a partition written by another has no defined cosine
        distance (invariant 3).

        `project` has no default. A retrieval scope that can be omitted gets
        omitted, and this channel reads a corpus whose whole organising unit is
        the project.
        """
        vector, fingerprint = await self.llm.embed(query)
        rows = await search_blocks(
            self.session,
            vector=vector,
            fingerprint=fingerprint,
            project=project,
            limit=limit,
            document_id=document_id,
        )
        return [_hit(row) for row in rows]


def _hit(row: dict) -> BlockHit:
    start, end = row.get("span_start"), row.get("span_end")
    return BlockHit(
        # Normalised at the boundary: the probe casts ids to text in SQL so a
        # consumer never has to know whether it holds a UUID or a str, which is
        # the drift that silently drops matches elsewhere (invariant 9).
        block_id=str(row["block_id"]),
        document_id=str(row["document_id"]),
        project=row["project"],
        uri=row.get("uri"),
        type=row.get("type"),
        text=row.get("text") or "",
        order_index=row.get("order_index"),
        char_span=(int(start), int(end)) if start is not None and end is not None else None,
        score=float(row["score"]),
    )
