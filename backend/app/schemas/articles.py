"""Wire shapes for the articles read surface (doc 12 §4/§5, T3.06)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArticleCitation(BaseModel):
    """One claim's grounding — doc 09 §4.3's hard FK, on the wire.

    ``claim_span`` is the stored `int4range` as ``[lo, hi)``, reported rather
    than re-derived: a span the renderer recomputed from the prose could
    disagree with the row the FK protects, and the citation would then point
    at text it does not ground.
    """

    id: str
    fact_id: str
    claim_span: list[int | None]
    fact: str
    subject_name: str
    rel_type: str
    object_name: str
    # False when the cited fact's belief window has closed. The citation still
    # renders — it is why the sentence exists — and it is also why the article
    # above it reads stale.
    believed: bool


class ArticleRow(BaseModel):
    """The list row. Carries ``coverage`` because doc 13 §5.2 makes the number
    an honesty signal shown in **both** detail levels, and a surface can only
    show in Simple what the list already carries."""

    id: str
    subject_key: str
    project: str
    title: str | None
    # The status a reader may see, through `row_labels` — never the column.
    status: str | None
    label_suppressed: str | None
    unverified: bool
    coverage: float | None
    review_state: str | None
    fact_set_hash: str | None
    stale: bool
    # A re-synthesis of this subject was attempted and held below the coverage
    # bar. The article is **not** withheld for it — it keeps its status, badge
    # and place in retrieval — so this is an attention signal beside the stale
    # label, never a suppression.
    resynthesis_held_at: datetime | None = None
    resynthesis_held_coverage: float | None = None
    superseded_by: str | None
    applies_when: dict[str, Any] | None
    learned_in: list[str]
    synthesized_at: datetime | None
    created_at: datetime | None
    excerpt: str | None = None


class ArticleListResponse(BaseModel):
    items: list[ArticleRow]
    total: int
    limit: int
    offset: int


class ArticleDetailResponse(ArticleRow):
    """The single-row detail `article_get` returns: the grounded prose, the
    citations behind each claim, and both directions of the lineage pointer."""

    content: str
    citations: list[ArticleCitation]
    supersedes: str | None
