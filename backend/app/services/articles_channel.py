"""The L3 articles retrieval channel (T3.23, doc 07 §2, doc 04 §5.3).

Doc 07 §2 makes the articles channel **semantic only** over
``article_embeddings__<slug>``. That is not a stage of a keyword arm that
someone forgot to write: an article is generated prose whose words are the
model's, so a keyword arm would rank on phrasing this system chose rather than
on knowledge it verified. The facts channel keeps a keyword arm because a
fact's text is a claim; an article's is a rendering.

**Scope pushdown from the first commit.** ``project`` is a ``WHERE`` on the
join, not a filter over fetched rows. A channel that fetched globally and
dropped out-of-scope rows afterwards returns fewer than ``limit`` results
whenever the top-K crosses a project boundary, and does it silently — the
isolation failure looks like a thin result set.

**A stale article is returned labelled, never withheld.** Doc 09 §4.4 makes
staleness a property of the fact set, and doc 13 makes it a label: a stale
article is still the best write-up of that subject and hiding it leaves the
reader with nothing while a fresher-looking absence implies the subject is
unknown. The label is derived by comparing the article's stored
``fact_set_hash`` against the subject's live verified set — verified *and still
believed*, per §4.4 as amended 2026-08-11 — computed for the returned page only.

**Composed, never fused here.** The channel returns candidates; doc 07 §5's
composition (T2.43) is what merges layers, and this module holds no ranking of
its own beyond the semantic distance it was asked for.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.retrieval_trace import ChannelStatus
from app.services.article_eligibility import (
    SUPPORTING_BELIEF_PREDICATE,
    VERIFIED_STATUSES,
)
from app.services.embedder_registry import child_table
from app.services.pin_suggestions import decode_subject_soft_key

__all__ = [
    "ARTICLE_EMBEDDINGS_PARENT",
    "ID_KIND",
    "LAYER",
    "SEMANTIC_ARM",
    "ArticleChannelTrace",
    "ArticlesChannel",
    "article_fact_set_hash",
]

LAYER = "L3"
ID_KIND = "article"
SEMANTIC_ARM = "semantic"

ARTICLE_EMBEDDINGS_PARENT = "article_embeddings"

# Superseded articles are not results. `ux_knowledge_articles_live` already
# keeps one live row per subject, so admitting superseded ones would return the
# same subject twice — once as it reads now and once as it used to.
_LIVE_PREDICATE = "a.status <> 'superseded'"


@dataclass
class ArticleChannelTrace:
    """The channel's rows plus its one arm's status (doc 07 §8)."""

    results: list[dict]
    arm_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    semantic_failed: bool = False
    # No partition for this fingerprint: the install has never synthesised an
    # article, so there was nothing to ask. Distinct from `semantic_failed`,
    # and the distinction is what keeps a fresh install off `partial` — see
    # `channel_status`.
    semantic_ran: bool = True
    modalities: tuple[str, ...] = (SEMANTIC_ARM,)

    def channel_status(self) -> dict[str, ChannelStatus]:
        """One arm, present and honest.

        Only ``semantic`` — this channel has no keyword modality by design, so
        there is no key to stamp ``ran=False`` for. Composition namespaces
        these under ``article.`` for the reason the facts channel's docstring
        gives: the envelope's dict is flat and a bare ``semantic`` key would
        overwrite the memory hybrid's own.

        **An absent partition reports ``ran=False``, never ``failed``.** The
        composition's own note says marking a deferred writer failed "would put
        it into partial, which is a different lie" — and it would be a
        permanent one here: every install that has not yet synthesised an
        article would serve every search flagged partially degraded, forever,
        for a layer it has no content in. Failure is reserved for a partition
        that exists and would not answer.
        """
        return {
            SEMANTIC_ARM: ChannelStatus(
                ran=self.semantic_ran, failed=self.semantic_failed
            )
        }


def article_fact_set_hash(fact_ids: list[str]) -> str:
    """The same digest ``article_synthesis`` stores, so the two can be compared.

    Imported by value rather than by reference to avoid a service-to-service
    import cycle; pinned equal by test, because two spellings of "the fact set"
    would make every article read stale forever or none of them ever.
    """
    return hashlib.sha256("|".join(sorted(fact_ids)).encode("utf-8")).hexdigest()


_SEARCH_SQL = """
    SELECT a.id AS article_id,
           a.subject_key,
           a.project,
           a.title,
           a.content,
           a.status AS verification_status,
           a.confidence,
           a.applies_when,
           a.learned_in,
           a.fact_set_hash,
           a.synthesized_at,
           1 - (e.embedding <=> CAST(:vec AS vector)) AS score
    FROM {table} e
    JOIN knowledge_articles a ON a.id = e.article_id
    WHERE {live}
      AND a.project = CAST(:project AS text)
    ORDER BY e.embedding <=> CAST(:vec AS vector)
    LIMIT :limit
"""

# One statement for the whole page's staleness, not one per row: the page is
# small but the query is not free, and N round trips to label N rows is the
# shape that turns a cheap label into a per-result cost.
_LIVE_HASHES_SQL = text(
    f"""
    SELECT lower(t.subject_name) AS name_lower,
           array_agg(CAST(t.id AS text) ORDER BY CAST(t.id AS text)) AS fact_ids
    FROM knowledge_triples t
    WHERE t.project = CAST(:project AS text)
      AND lower(t.subject_name) = ANY(CAST(:names AS text[]))
      AND t.verification_status = ANY(CAST(:statuses AS text[]))
      AND {SUPPORTING_BELIEF_PREDICATE}
    GROUP BY lower(t.subject_name)
    """
)


class ArticlesChannel:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query_vector: list[float],
        *,
        fingerprint: str,
        project: str,
        limit: int = 10,
    ) -> list[dict]:
        return (
            await self.search_with_trace(
                query_vector, fingerprint=fingerprint, project=project, limit=limit
            )
        ).results

    async def search_with_trace(
        self,
        query_vector: list[float],
        *,
        fingerprint: str,
        project: str,
        limit: int = 10,
    ) -> ArticleChannelTrace:
        """The channel's rows, each labelled ``stale`` or not.

        ``fingerprint`` is required rather than resolved here: the caller
        embedded the query and knows which embedder produced the vector, and a
        channel that picked its own partition could compare a vector from one
        embedder against rows from another — a cross-fingerprint comparison has
        no defined cosine distance.
        """
        table = child_table(ARTICLE_EMBEDDINGS_PARENT, fingerprint)
        if not await self._partition_exists(table):
            # Nothing to ask, rather than asked and broken.
            return ArticleChannelTrace(results=[], semantic_ran=False)
        sql = _SEARCH_SQL.format(table=table, live=_LIVE_PREDICATE)
        # **Inside a savepoint, and that is not defensive style.** The partition
        # may not exist on an install that has never synthesised, and in
        # Postgres a failed statement poisons the whole transaction — every
        # later query in the request raises `InFailedSQLTransactionError`. A
        # bare `try` here would turn a missing L3 partition into a failure of
        # the memory and fact channels that had already succeeded.
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    text(sql),
                    {
                        "vec": str(query_vector),
                        "project": project,
                        "limit": limit,
                    },
                )
                rows = [dict(row) for row in result.mappings().all()]
                # **Normalised at the boundary**, which is where CLAUDE.md's
                # id-type-drift invariant says to do it. The driver hands back
                # `article_id` as a UUID while `arm_scores` below is keyed by
                # its string form; leaving both would make a consumer joining
                # rows to scores miss every row, silently.
                for row in rows:
                    row["article_id"] = str(row["article_id"])
        except Exception:
            # The partition exists and would not answer — a real outage, and
            # reported as one: an empty result and a broken channel must never
            # read alike (invariant 14).
            return ArticleChannelTrace(results=[], semantic_failed=True)

        stale_by_subject = await self._stale_subjects(rows, project=project)
        for row in rows:
            row["stale"] = bool(stale_by_subject.get(row["subject_key"], False))

        return ArticleChannelTrace(
            results=rows,
            arm_scores={
                str(row["article_id"]): {SEMANTIC_ARM: float(row["score"])}
                for row in rows
            },
        )

    async def _partition_exists(self, table: str) -> bool:
        """Whether this fingerprint's child table has been created.

        `to_regclass` answers without raising, which is the point: probing by
        running the query and catching the error would poison the transaction
        on the most ordinary state this channel has — an install that has never
        synthesised an article.
        """
        return (
            await self.session.execute(
                text("SELECT to_regclass(CAST(:name AS text)) IS NOT NULL"),
                {"name": table},
            )
        ).scalar_one()

    async def _stale_subjects(
        self, rows: list[dict], *, project: str
    ) -> dict[str, bool]:
        """Which of this page's subjects have moved since their article.

        Compares the stored ``fact_set_hash`` against the subject's live
        verified set. An article whose subject now has *no* verified facts is
        stale rather than absent-from-the-map: the knowledge it was built on is
        gone, which is the strongest form of the thing staleness names.

        The basis is ``SUPPORTING_BELIEF_PREDICATE``, shared with the write side
        so the two can never disagree — a read basis narrower than the write
        basis makes every article read stale from the moment it is written.
        """
        if not rows:
            return {}

        names = {}
        for row in rows:
            name, _type = decode_subject_soft_key(row["subject_key"])
            names[row["subject_key"]] = name

        live = {
            r["name_lower"]: article_fact_set_hash(list(r["fact_ids"]))
            for r in (
                await self.session.execute(
                    _LIVE_HASHES_SQL,
                    {
                        "project": project,
                        "names": sorted(set(names.values())),
                        "statuses": list(VERIFIED_STATUSES),
                    },
                )
            ).mappings().all()
        }

        out: dict[str, bool] = {}
        for row in rows:
            current = live.get(names[row["subject_key"]])
            out[row["subject_key"]] = current != row["fact_set_hash"]
        return out
