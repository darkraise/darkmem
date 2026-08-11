"""The articles read surface (doc 12 §4/§5, doc 13 §5.2) — T3.06.

Provides the rows behind two REST doors and MCP's ``article_get``:

  - GET /api/v1/knowledge/articles       — a page of live articles, each badged
  - GET /api/v1/knowledge/articles/{id}  — one article, its citations, its lineage

Read-only, and structurally so. Everything here is a `SELECT`: an article's
prose, its coverage and its rung are written by the synthesis job and its
entailment pass, and staleness is *derived* rather than stored. A write on this
surface would put a second writer on an axis whose single writer is what makes
its journal countable — the same reasoning `facts_read` states for the fact
side.

**Three properties this door owes doc 13 §5.2, none of them cosmetic.**

*The rung passes the gate.* `status` is emitted through `row_labels`, doc 12's
one producer of the claim surface, with `id_kind="article"` and the gate read
from the judge's own door. `knowledge_articles`' CHECK admits `corroborated`,
so an article promoted by any writer would otherwise reach a reader here
without passing G-D at all. `label_suppressed` rides alongside so a suppressed
rung and a genuinely-candidate one do not read alike.

*Coverage is served in both detail levels.* This module does not know about
detail levels — the frontend does — but it is why `confidence` is on the list
row and not only on the detail: a surface can only show in Simple what the list
already carries. Doc 13 calls the number an honesty signal rather than technical
detail, which is the distinction T1.48 drew when it made the raw `fact_set_hash`
advanced-only and left the stale label in both.

*Stale is a label, never a filter.* A stale article is returned like any other,
flagged. The hash comparison runs through `ArticlesChannel.live_fact_set_hashes`
rather than a copy: two spellings of "the fact set" would make every article
read stale forever, or none of them ever.

**Superseded articles are excluded by default and reachable by id.** The list
serves the live article per subject (doc 04 §8.8's partial-unique), but a
lineage that 404s is not lineage, so the detail door reads any article — the
prior one included — and carries both directions of the pointer.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.articles_channel import ArticlesChannel
from app.services.fact_badge import row_labels
from app.services.pin_suggestions import decode_subject_soft_key

logger = logging.getLogger(__name__)

ARTICLE_ID_KIND = "article"

# Enough prose to recognise an article by, never the whole body: the list is a
# browsing surface, and a page of full articles is a page of unbounded text.
#
# 200 to match the review queue's own article boundary, which is what makes the
# isolation probe's over-length article fixture load-bearing here too: its tail
# marker begins past 260 characters, so a boundary beyond that would let an
# untruncated `content` reach the wire while the probe still reported clean.
EXCERPT_CHARS = 200

_LIST_SQL = """
    SELECT a.id,
           a.subject_key,
           a.project,
           a.title,
           a.status,
           a.confidence,
           a.review_state,
           a.fact_set_hash,
           a.applies_when,
           a.learned_in,
           a.superseded_by,
           a.resynthesis_held_at,
           a.resynthesis_held_coverage,
           a.synthesized_at,
           a.created_at,
           left(a.content, {excerpt}) AS excerpt
    FROM knowledge_articles a
    WHERE a.status <> 'superseded'
      {project}
    ORDER BY a.synthesized_at DESC NULLS LAST, a.id
    LIMIT :limit OFFSET :offset
"""

_COUNT_SQL = """
    SELECT COUNT(*) FROM knowledge_articles a
    WHERE a.status <> 'superseded'
      {project}
"""

_DETAIL_SQL = text(
    """
    SELECT a.id,
           a.subject_key,
           a.project,
           a.title,
           a.content,
           a.status,
           a.confidence,
           a.review_state,
           a.fact_set_hash,
           a.applies_when,
           a.learned_in,
           a.superseded_by,
           a.resynthesis_held_at,
           a.resynthesis_held_coverage,
           a.synthesized_at,
           a.created_at
    FROM knowledge_articles a
    WHERE a.id = CAST(:id AS uuid)
    """
)

# The prior article in the lineage — the row pointing *at* this one. Doc 09
# §4.4 keeps lineage "retained and reachable", and reachable means from either
# end: a reader landing on the current article can walk back, and one landing
# on a superseded article can walk forward.
_SUPERSEDES_SQL = text(
    """
    SELECT id FROM knowledge_articles
    WHERE superseded_by = CAST(:id AS uuid)
    ORDER BY synthesized_at DESC NULLS LAST, id
    LIMIT 1
    """
)

# Each citation with the fact text it grounds, so the detail page can render a
# claim's support without a second round trip per citation. The join is safe to
# make an INNER one: `fact_id` is a hard FK and facts are invalidate-not-delete,
# which is the whole premise doc 09 §4.3 takes it on.
_CITATIONS_SQL = text(
    """
    SELECT c.id,
           c.fact_id,
           lower(c.claim_span) AS span_lo,
           upper(c.claim_span) AS span_hi,
           t.fact,
           t.subject_name,
           t.rel_type,
           t.object_name,
           t.invalid_at,
           t.expired_at
    FROM article_citations c
    JOIN knowledge_triples t ON t.id = c.fact_id
    WHERE c.article_id = CAST(:id AS uuid)
    ORDER BY lower(c.claim_span), c.id
    """
)


async def _gate(session: AsyncSession):
    """The article claim gate, from the judge's own door.

    Resolved once per response rather than per row — one record read answers
    for every row on the page. A failure to resolve it is not a licence to
    serve: the caller gets the same fail-closed default an unwired caller gets.
    """
    from app.services.config import get_llm_config
    from app.services.verification_judge import article_claim_gate

    try:
        llm_config = await get_llm_config(session)
        return await article_claim_gate(session, llm_config)
    except Exception:  # noqa: BLE001 - an unresolvable gate serves nothing
        logger.warning("articles_read: article gate unresolved; serving closed")
        from app.services.claim_gates import groundedness_gate

        return groundedness_gate()


def subject_name_of(subject_key: str) -> str:
    """The subject half of a soft key, tolerating a key that has no type half.

    ``decode_subject_soft_key`` raises on a key without ``::``, which is right
    for a caller that minted the key itself. It is wrong for a *read* over
    whatever the table holds: one row written by an older path — or by hand —
    would take down the whole page with a 500, and a browsing surface that
    cannot render its list is strictly worse than one that renders a row
    conservatively.

    Conservatively means stale: the fallback name will not match any grouped
    hash, so the article reads as "its knowledge moved" rather than as current.
    Labelling an article stale when it may not be costs a re-synthesis;
    labelling it current when it is not is the claim this layer exists to
    avoid making.
    """
    try:
        name, _entity_type = decode_subject_soft_key(subject_key)
    except ValueError:
        return subject_key.lower()
    return name


async def _stale_flags(
    session: AsyncSession, rows: list[Any]
) -> dict[str, bool]:
    """Which of these articles' subjects have moved since synthesis.

    Grouped by project because the hash query is project-scoped: a subject name
    means different facts in two projects, and pooling them would compare an
    article against another project's knowledge.
    """
    by_project: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for row in rows:
        names[str(row["id"])] = subject_name_of(row["subject_key"])
        by_project.setdefault(row["project"], []).append(names[str(row["id"])])

    live: dict[tuple[str, str], str] = {}
    for project, project_names in by_project.items():
        hashes = await ArticlesChannel.live_fact_set_hashes(
            session, project=project, names=project_names
        )
        for name, digest in hashes.items():
            live[(project, name)] = digest

    return {
        str(row["id"]): live.get((row["project"], names[str(row["id"])]))
        != row["fact_set_hash"]
        for row in rows
    }


def _item(row: Any, *, gate, stale: bool) -> dict[str, Any]:
    labels = row_labels(
        id_kind=ARTICLE_ID_KIND,
        verification_status=row["status"],
        gate=gate,
    )
    return {
        "id": str(row["id"]),
        "subject_key": row["subject_key"],
        "project": row["project"],
        "title": row["title"],
        "status": labels["verification_status"],
        "label_suppressed": labels["label_suppressed"],
        "unverified": labels["unverified"],
        # Doc 13 §5.2: the value *is* the fraction of sentences a verified fact
        # entails, so every surface labels it claim-support coverage rather
        # than a vague score. Named `coverage` on the wire for that reason —
        # `confidence` is the column, not the claim.
        "coverage": row["confidence"],
        "review_state": row["review_state"],
        "fact_set_hash": row["fact_set_hash"],
        "stale": stale,
        "superseded_by": (
            str(row["superseded_by"]) if row["superseded_by"] is not None else None
        ),
        # Doc 09 §4.4's held marker. Served beside the stale label so a reader
        # can tell "refresh pending" from "refresh attempted and held", which
        # the bare stale label cannot express.
        "resynthesis_held_at": row["resynthesis_held_at"],
        "resynthesis_held_coverage": row["resynthesis_held_coverage"],
        "applies_when": row["applies_when"],
        "learned_in": list(row["learned_in"] or []),
        "synthesized_at": row["synthesized_at"],
        "created_at": row["created_at"],
    }


async def list_articles(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """A page of live articles, badged and stale-flagged.

    Nothing here filters on the verification rung. An article withheld from the
    corroborated view is withheld by `review_state`, which is a curation state
    a human set or the entailment pass wrote — not by its badge. Filtering on
    the rung would also invert the claim gate, which is why `facts_read` takes
    its status filter through `raw_statuses_for_served` and why this door
    offers no status filter at all rather than a wrong one.
    """
    clause = " AND a.project = CAST(:project AS text)" if project is not None else ""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if project is not None:
        params["project"] = project

    rows = (
        await session.execute(
            text(_LIST_SQL.format(excerpt=EXCERPT_CHARS, project=clause)), params
        )
    ).mappings().all()

    gate = await _gate(session)
    stale = await _stale_flags(session, rows)
    items = [
        {**_item(row, gate=gate, stale=stale[str(row["id"])]), "excerpt": row["excerpt"]}
        for row in rows
    ]

    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (
        await session.execute(text(_COUNT_SQL.format(project=clause)), count_params)
    ).scalar_one()
    return items, int(total)


async def get_article(
    session: AsyncSession, article_id: UUID | str
) -> dict | None:
    """One article: prose, citations, lineage, and the same labels the list has.

    Reads a superseded article too. Doc 09 §4.4 retains lineage so a reader can
    see what an article used to say, and a 404 on the prior row would make the
    pointer decorative.
    """
    row = (
        await session.execute(_DETAIL_SQL, {"id": str(article_id)})
    ).mappings().first()
    if row is None:
        return None

    gate = await _gate(session)
    stale = await _stale_flags(session, [row])
    item = {**_item(row, gate=gate, stale=stale[str(row["id"])])}
    item["content"] = row["content"]
    item["supersedes"] = (
        (lambda r: str(r[0]) if r is not None else None)(
            (
                await session.execute(_SUPERSEDES_SQL, {"id": str(article_id)})
            ).first()
        )
    )

    citations = (
        await session.execute(_CITATIONS_SQL, {"id": str(article_id)})
    ).mappings().all()
    item["citations"] = [
        {
            "id": str(c["id"]),
            "fact_id": str(c["fact_id"]),
            # int4range is half-open and Postgres normalises it, so the pair is
            # reported as stored rather than re-derived from the prose — a span
            # the UI recomputed could disagree with the row the FK protects.
            "claim_span": [c["span_lo"], c["span_hi"]],
            "fact": c["fact"],
            "subject_name": c["subject_name"],
            "rel_type": c["rel_type"],
            "object_name": c["object_name"],
            # A citation whose fact is no longer believed still renders — the
            # citation is why the sentence was written, and hiding it would
            # leave an uncited claim on the page. It is flagged instead, and it
            # is also why the article above reads stale.
            "believed": c["invalid_at"] is None and c["expired_at"] is None,
        }
        for c in citations
    ]
    return item


__all__ = ["ARTICLE_ID_KIND", "get_article", "list_articles"]
