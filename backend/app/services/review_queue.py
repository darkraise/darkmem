"""The review queue read surface (doc 08 §6, T2.22).

Two truth-adjudication surfaces — disputed/under-sourced facts and
low-confidence/ungrounded articles — sharing one membership predicate:
``review_state = 'open'``. Doc 08 §6 chose a ``status + partial index`` over a
queue *table* precisely because a queue table grows unboundedly and makes the
human the throughput bottleneck; the partial indexes
(``ix_knowledge_triples_review``, ``ix_knowledge_articles_review``, both in
the baseline since T0.12b) are what make that cheap. Every query in this
module keeps the literal ``review_state = 'open'`` predicate un-parameterised
in the SQL text so it matches those indexes' own predicate by construction.
A bound ``'open'`` value can still use the index too, on a fresh custom plan
per execution — the real hazard is a *cached* generic plan under prepared-
statement reuse, which the planner may build without the constant in view
and then reuse across different bound values. The literal sidesteps that
question entirely. Widening the predicate itself (``IS NOT NULL``, an ``IN``
list) is the one change that provably loses the index regardless of binding,
since the partial index's own predicate no longer implies the query's.

**This module has no writer.** ``review_state`` is opened and cleared inside
the verification ladder's applier, under the same row-locking window that
journals the transition (T2.62) — the sole journaller — so a surface-layer
writer here would open a window in which a fact is ``disputed`` but unqueued.
Every function below is a plain ``SELECT``.

**Never a gate on the read path (doc 08 §6, invariant 14).** This module does
not touch ordinary fact retrieval at all — it only lists queue membership.
The property that a queued fact stays retrievable, unfiltered and unreordered,
is proved in ``tests/test_review_queue.py`` against
``KnowledgeTripleRepository.get_live`` (today's only fact-level read path;
there is no agent-facing retrieval surface over ``knowledge_triples`` yet — no
hybrid-search fusion arm, no REST GET beyond this module's own queue list).

**The "reason" a fact is queued is derived from the fact's own columns, never
from the ``review_state`` value itself** — the brief for T2.62 (running
concurrently) is still settling how one ``review_state`` column serves three
independent openers (dispute, T2.46's under-sourced hysteresis, doc 09's
ungrounded articles) plus a human clear, so this module does not guess at a
vocabulary T2.62 may define. Today the only column that reliably distinguishes
a reason is ``verification_status`` / ``status``: ``'disputed'`` renders as
the ``disputed`` reason, and every other open row renders as ``unspecified``
(honest: an ``unspecified`` row's opener is one of T2.46's hysteresis or doc
09's ungrounded-article check, neither of which has landed a distinguishing
column yet).

**"Both sides" — a real, reported gap.** T2.06's enriched ``verified`` events
journal decision evidence (``outcome``, ``origin_count``, ``required_n``,
``gate_fired``, ``source_kinds``, ``contradiction_blocked``, before/after) that
this module surfaces as best-effort ``evidence`` alongside a disputed fact, so
a human can see the support count the veto overrode. But that payload does not
carry the contradiction's *counterpart* fact id or witness origin (the finding
that produces those is computed on the fly by the deterministic same-endpoint
scan in the contradiction-veto module and never persisted), and this module
does not call into that scan to re-derive it: the verification ladder is that
scan's *sole* legitimate caller, enforced by a tree-wide reference scan in the
veto's own test suite that fails the build on a second entry point. So "what
are the competing claims" is answerable today only as "this fact's own claim,
disputed, with N origins of these kinds" — not "disputed by fact X asserting
Y". Rendering the actual counterpart claim needs either a persisted pointer on
the fact row (a schema change, out of this task's scope) or a future surface
that owns querying the scan. Flagged as a coordination item, not solved here.

**The ordering seam, filled (T2.24).** Doc 08 §6: the queue is "ranked by
consequence — retrieval frequency and subject salience — not arrival order".
``ReviewQueueOrder`` now carries the ``CONSEQUENCE`` member T2.22 left room
for and ``_DEFAULT_ORDER`` names it; ``ARRIVAL_DESC`` survives as an explicit
opt-in so the two orders can be compared rather than assumed to differ. The
ranking itself — how each consequence input is derived, what each one's
failure mode is, and why a stale dispute's decay is a rank tier rather than a
status — lives in ``app/services/review_ranking.py``.

Two properties of that fill are this module's to keep. **The ranking changes
the ``ORDER BY`` and the projection, never the membership predicate**: the
consequence statement applies the caller's ``review_state = 'open'`` predicate
verbatim inside its leading CTE, so the partial index property above still
holds and the EXPLAIN proof still runs the exact executed statement. And
**consequence ranking degrades to arrival order rather than to arbitrary
order**: a queue whose facts have no access history and no graph presence
scores every row 0, and the tiebreak is ``created_at DESC, id DESC`` — the
same key ``ARRIVAL_DESC`` sorts on — so a fresh vault's queue is stable and
the ordering only starts to move once there is a signal to move it.

**Articles keep ``ARRIVAL_DESC``, and it is pinned rather than defaulted.**
Neither consequence input exists for an article: there is no ``fact_sources``
bridge to ``memory_access_stats`` and ``subject_key`` is a text key, not an
entity pointer. A ranking derived from nothing would be arrival order wearing
a score, so this arm names its order explicitly instead of inheriting a
default it cannot honour. Ranking articles needs an input doc 09's synthesis
job would have to produce, and ``article_synthesis`` is still a placeholder.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.review_ranking import (
    DEFAULT_RANKING_CONFIG,
    RankingConfig,
    build_ranked_facts_sql,
    consequence_explanation,
    get_ranking_config,
)

logger = logging.getLogger(__name__)


class ReviewQueueOrder(str, enum.Enum):
    """Ordering strategies for the review queue's list endpoints.

    ``CONSEQUENCE`` is doc 08 §6's policy and the default. ``ARRIVAL_DESC``
    was T2.22's disclosed placeholder and is kept as an explicit opt-in: it is
    what a caller pins to compare the two orders, and a test that seeds a
    queue where they *agree* proves nothing about either.
    """

    ARRIVAL_DESC = "arrival_desc"
    CONSEQUENCE = "consequence"


# The consequence key's tail is ARRIVAL_DESC's whole key, and that is the
# point rather than a coincidence: ties (a queue with no telemetry yet) fall
# through to a total, deterministic order instead of to whatever the plan
# happened to emit, and pagination stays stable across pages.
_ORDER_SQL: dict[ReviewQueueOrder, str] = {
    ReviewQueueOrder.ARRIVAL_DESC: "created_at DESC, id DESC",
    ReviewQueueOrder.CONSEQUENCE: (
        "active_tier DESC, consequence_score DESC, o.created_at DESC, o.id DESC"
    ),
}

_DEFAULT_ORDER = ReviewQueueOrder.CONSEQUENCE

_FACT_COLUMN_NAMES = (
    "id",
    "subject_name",
    "object_name",
    "rel_type",
    "fact",
    "project",
    "valid_at",
    "invalid_at",
    "expired_at",
    "verification_status",
    "confidence",
    "review_state",
    "created_at",
)

_FACT_COLUMNS = ", ".join(_FACT_COLUMN_NAMES)

_ARTICLE_COLUMNS = (
    "id, subject_key, project, title, status, confidence, "
    "fact_set_hash, review_state, synthesized_at, created_at, "
    "LEFT(content, 200) AS content_preview"
)


def _fact_reason(verification_status: str | None) -> str:
    """Derived from the fact's own column, never from ``review_state``."""
    if verification_status == "disputed":
        return "disputed"
    return "unspecified"


def _article_reason(status: str | None) -> str:
    """Derived from the article's own column, never from ``review_state``."""
    if status == "disputed":
        return "disputed"
    return "unspecified"


def build_facts_query(
    project: str | None,
    *,
    order: ReviewQueueOrder | None = None,
    ranking: RankingConfig | None = None,
) -> tuple[str, str]:
    """Return (items_sql, count_sql) for the open-facts membership query.

    Exported so the EXPLAIN test in ``tests/test_review_queue.py`` runs the
    *exact* statement production code executes, not a hand-copied
    approximation of it — the same discipline
    ``tests/test_technologies_denorm.py`` and
    ``tests/test_memory_lineage_index.py`` use for their own index-usage
    proofs. ``review_state = 'open'`` is a literal in the SQL text, never a
    bind parameter — see the module docstring.

    Both ``order`` and ``ranking`` default to the shipped policy, so the
    statement is reachable without threading configuration through the
    EXPLAIN proofs; the bound parameter set is ``limit``/``offset`` (plus
    ``project``) either way, because every ranking knob is interpolated as a
    literal for the same planner reason the membership predicate is.
    """
    order = order or _DEFAULT_ORDER
    where = ["review_state = 'open'"]
    if project is not None:
        where.append("project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    order_sql = _ORDER_SQL[order]

    if order is ReviewQueueOrder.CONSEQUENCE:
        items_sql = build_ranked_facts_sql(
            column_names=_FACT_COLUMN_NAMES,
            where_sql=where_sql,
            order_sql=order_sql,
            config=ranking or DEFAULT_RANKING_CONFIG,
        )
    else:
        items_sql = (
            f"SELECT {_FACT_COLUMNS} FROM knowledge_triples "
            f"WHERE {where_sql} ORDER BY {order_sql} LIMIT :limit OFFSET :offset"
        )
    count_sql = f"SELECT COUNT(*) FROM knowledge_triples WHERE {where_sql}"
    return items_sql, count_sql


def build_articles_query(project: str | None) -> tuple[str, str]:
    """Return (items_sql, count_sql) for the open-articles membership query.

    Same discipline as ``build_facts_query``: exported for the EXPLAIN test,
    literal ``review_state = 'open'`` predicate.

    Pinned to ``ARRIVAL_DESC`` rather than reading ``_DEFAULT_ORDER``: neither
    consequence input exists for an article (see the module docstring), so
    inheriting the facts arm's default would be a claim this arm cannot back.
    """
    where = ["review_state = 'open'"]
    if project is not None:
        where.append("project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    order_sql = _ORDER_SQL[ReviewQueueOrder.ARRIVAL_DESC]
    items_sql = (
        f"SELECT {_ARTICLE_COLUMNS} FROM knowledge_articles "
        f"WHERE {where_sql} ORDER BY {order_sql} LIMIT :limit OFFSET :offset"
    )
    count_sql = f"SELECT COUNT(*) FROM knowledge_articles WHERE {where_sql}"
    return items_sql, count_sql


async def _latest_verified_evidence(
    session: AsyncSession, fact_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Best-effort decision evidence from the most recent ``verified`` event
    per fact. Empty for a fact with no verification history yet (e.g. a
    freshly seeded row, or any row before T2.62's writer lands) — that is a
    legitimate ``None``, not a fetch failure.

    One batched query (``DISTINCT ON``) rather than one round trip per row,
    same reasoning as ``PipelineFailureService.list_unresolved``'s single
    join: the queue list is a bounded page, not a per-item fan-out.
    """
    if not fact_ids:
        return {}
    result = await session.execute(
        text(
            """
            SELECT DISTINCT ON (object_id) object_id, payload, created_at
            FROM events
            WHERE object_type = 'fact'
              AND event_type = 'verified'
              AND object_id = ANY(CAST(:ids AS uuid[]))
            ORDER BY object_id, created_at DESC, id DESC
            """
        ),
        {"ids": fact_ids},
    )
    out: dict[str, dict[str, Any]] = {}
    for row in result.mappings().all():
        out[str(row["object_id"])] = {
            "payload": row["payload"],
            "recorded_at": row["created_at"],
        }
    return out


async def list_open_facts(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
    order: ReviewQueueOrder | None = None,
) -> tuple[list[dict], int]:
    """Facts whose ``review_state = 'open'`` — disputed and (once T2.46 lands)
    under-sourced facts. Membership is exactly the partial index's predicate;
    see ``build_facts_query``.

    Consequence-ranked by default (doc 08 §6). Each item carries a
    ``consequence`` block naming every input that moved its score, so the
    ranking is answerable per item rather than an opaque float; the block is
    absent only when a caller pins ``ARRIVAL_DESC``, which computes none of
    those inputs.
    """
    order = order or _DEFAULT_ORDER
    ranked = order is ReviewQueueOrder.CONSEQUENCE
    # One primary-key read per call, not per item, and its value is
    # interpolated into the single ranking statement below.
    ranking = await get_ranking_config(session) if ranked else DEFAULT_RANKING_CONFIG

    items_sql, count_sql = build_facts_query(project, order=order, ranking=ranking)
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if project is not None:
        params["project"] = project

    result = await session.execute(text(items_sql), params)
    rows = [dict(row) for row in result.mappings().all()]

    fact_ids = [str(row["id"]) for row in rows]
    evidence_by_id = await _latest_verified_evidence(session, fact_ids)

    items = []
    for row in rows:
        fid = str(row["id"])
        items.append(
            {
                "id": fid,
                "subject_name": row["subject_name"],
                "object_name": row["object_name"],
                "rel_type": row["rel_type"],
                "fact": row["fact"],
                "project": row["project"],
                "valid_at": row["valid_at"],
                "invalid_at": row["invalid_at"],
                "expired_at": row["expired_at"],
                "verification_status": row["verification_status"],
                "confidence": row["confidence"],
                "review_state": row["review_state"],
                "reason": _fact_reason(row["verification_status"]),
                "evidence": evidence_by_id.get(fid),
                "consequence": consequence_explanation(row, ranking) if ranked else None,
                "created_at": row["created_at"],
            }
        )

    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


async def list_open_articles(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Articles whose ``review_state = 'open'`` — low-confidence/ungrounded
    articles (doc 09). ``article_synthesis`` is a ``PlaceholderJobRunner``
    until T3.02 (behind G-D), so nothing writes ``knowledge_articles`` in
    production yet: this arm is exercised in tests only against seeded rows,
    never against a real producer. Do not read a passing test here as proof
    against live data — there is none yet.
    """
    items_sql, count_sql = build_articles_query(project)
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if project is not None:
        params["project"] = project

    result = await session.execute(text(items_sql), params)
    rows = [dict(row) for row in result.mappings().all()]

    items = []
    for row in rows:
        items.append(
            {
                "id": str(row["id"]),
                "subject_key": row["subject_key"],
                "project": row["project"],
                "title": row["title"],
                "status": row["status"],
                "confidence": row["confidence"],
                "fact_set_hash": row["fact_set_hash"],
                "review_state": row["review_state"],
                "reason": _article_reason(row["status"]),
                "content_preview": row["content_preview"],
                "synthesized_at": row["synthesized_at"],
                "created_at": row["created_at"],
            }
        )

    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


async def counts(session: AsyncSession) -> dict[str, int]:
    """Cheap totals for the two queue arms — the ``pipeline_failures``
    ``/counts`` companion pattern (doc 08 §6 names that module as the model).
    """
    facts_total = (
        await session.execute(
            text("SELECT COUNT(*) FROM knowledge_triples WHERE review_state = 'open'")
        )
    ).scalar_one()
    articles_total = (
        await session.execute(
            text("SELECT COUNT(*) FROM knowledge_articles WHERE review_state = 'open'")
        )
    ).scalar_one()
    return {"facts": int(facts_total), "articles": int(articles_total)}
