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
from the ``review_state`` value itself.** T2.62 settled how one
``review_state`` column serves several independent openers plus a human clear —
it derives the flag from the decision instead of letting each opener assign it
— so this module reads four columns and names three of the four reasons.
``verification_status = 'disputed'`` renders as ``disputed``;
``demotion_pending_since IS NOT NULL`` renders as ``under-sourced``, the
column T2.46 landed and the reason this docstring previously had to report as
``unspecified``; ``contradiction_suspected_at IS NOT NULL`` renders as
``contradiction-suspected``, with ``contradiction_counterpart_id`` serving the
counterpart beside it.

``unspecified`` covers the fourth — doc 09's ungrounded articles, which live in
a different table entirely — for the same reason as before: no distinguishing
column exists here.

**The contradiction-suspected reason was that gap, and T2.112 closed it
(corrected 2026-08-09).** This paragraph used to say the flag "is persisted
nowhere", that a flagged fact "arrives here wearing ``unspecified``", and that
choosing between a journal read and a fact-row column was "a design call this
module does not own" — all three were true of T2.109's shape and none survives
T2.112. The column won, and for an invariant rather than a preference: reading
the finding from the queue would mean importing the adjudication module onto a
read surface, and invariant 15's tree-wide scan fails the build on that — as it
does on this paragraph naming the module, which is why it does not. The ladder
writes both columns in the **same** UPDATE as ``verification_status``, so they
are a cache the authority refreshes every recompute and not a frozen verdict.
The same scan keeps the finding's own channel to the three modules that declare,
write and read it — which is exactly why the reason arrives here as columns.

**"Both sides" — closed by T2.64 (2026-08-02).** T2.06's enriched ``verified``
events journal decision evidence (``outcome``, ``origin_count``, ``required_n``,
``gate_fired``, ``source_kinds``, ``contradiction_blocked``, before/after) that
this module surfaces as best-effort ``evidence`` alongside a disputed fact, so
a human can see the support count the veto overrode. **T2.64 added a
``contradiction`` block to that same payload**, carrying the counterpart's
structured triple (``counterpart_id``, subject, ``rel_type``, object) plus the
``rule`` and ``witness_origin`` — so ``_latest_verified_evidence`` already
delivers "disputed by fact X asserting Y" with **no query change here**.

Two properties of that block a reader must not re-derive. It names the
counterpart the verdict turned on, not every counterpart in the database:
adjudication short-circuits at the first detector that finds anything, since
one contradiction is already absolute, and the block says so in-band via
``enumeration: "first_finding"``. And it is **absent** on a recovery, on a
caller-overridden verdict, and on any dispute predating that commit — absent
means "no scan produced one here", never "no counterpart exists".

This paragraph previously said the gap needed a persisted pointer on the fact
row (a schema change) or a future surface owning the scan. **Both were wrong**,
and the correction matters more than the staleness: the ladder remains the
scan's *sole* legitimate caller, enforced by a tree-wide reference scan that
fails the build on a second entry point, so a surface that "owns querying the
scan" is forbidden by construction. The closure was one jsonb field written
where the finding was already in scope, and no schema change at all.

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

from app.services.claim_gates import (
    FACT_ID_KIND,
    gated_journal_payload,
    ungated_mapping,
)
from app.services.fact_badge import row_labels
from app.services.review_ranking import (
    DEFAULT_RANKING_CONFIG,
    RankingConfig,
    build_ranked_facts_sql,
    consequence_explanation,
    get_ranking_config,
)
from app.services.verified_evidence import latest_verified_evidence

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
    "demotion_pending_since",
    # Doc 08 §6's third opener (T2.112). Read as columns, not by asking the
    # veto: an `app.services.contradiction_veto` import on a read surface is
    # what invariant 15's source scan fails the build on. The ladder
    # re-derives the finding every recompute and lands it here, so this surface
    # reads a marker the authority refreshes rather than re-adjudicating.
    "contradiction_suspected_at",
    "contradiction_counterpart_id",
    "created_at",
)

_FACT_COLUMNS = ", ".join(_FACT_COLUMN_NAMES)

_ARTICLE_COLUMNS = (
    "id, subject_key, project, title, status, confidence, "
    "fact_set_hash, review_state, synthesized_at, created_at, "
    "LEFT(content, 200) AS content_preview"
)


def _served_labels(verification_status: str | None) -> dict[str, Any]:
    """The rung this door may serve, and why it differs from the column.

    ``row_labels`` is asked for the whole triplet and two keys are taken: the
    queue item declares no badge (the claim sentence belongs to the fact
    surfaces) and no lifecycle. Taking them from the producer rather than
    calling the gate directly is what keeps this door one of its consumers
    instead of a second implementation of it.
    """
    labels = row_labels(
        id_kind=FACT_ID_KIND, verification_status=verification_status
    )
    return {
        "verification_status": labels["verification_status"],
        "label_suppressed": labels["label_suppressed"],
    }


def _fact_reason(
    verification_status: str | None,
    demotion_pending_since: Any = None,
    contradiction_suspected_at: Any = None,
) -> str:
    """Derived from the fact's own columns, never from ``review_state``.

    T2.46 supplied the distinguishing column the module docstring said did not
    exist yet, so an under-sourced fact now names its own reason instead of
    falling through to ``unspecified``. ``unspecified`` survives for doc 09's
    ungrounded articles, which are a different table and still have no
    distinguishing column of their own, and for T2.109's contradiction-suspected
    fact, which has no column at all — the module docstring says what closing
    that would cost.

    ``disputed`` wins a tie on the graver condition, and the tie is
    unreachable today: the veto is adjudicated before every count, so a
    contradicted fact never leaves ``decide`` on a ``demote`` and its marker
    is cleared on that same cycle. Ordered anyway, because a reason that
    depended on which condition the reader checked first is the ambiguity
    ``derive_review_state`` was written to remove.
    """
    if verification_status == "disputed":
        return "disputed"
    if demotion_pending_since is not None:
        return "under-sourced"
    if contradiction_suspected_at is not None:
        return "contradiction-suspected"
    return "unspecified"


async def _counterpart_triples(session: AsyncSession, ids: list) -> dict[str, dict]:
    """The suspected counterparts' own triples, one query for the page.

    Expired counterparts are deliberately included. Facts are
    invalidate-not-delete, and a flag raised against a fact that has since been
    retired is exactly the case a reviewer most needs to see rendered — the
    alternative is a flag whose other side silently reads as missing.
    """
    wanted = {str(i) for i in ids if i is not None}
    if not wanted:
        return {}
    result = await session.execute(
        text(
            "SELECT id, subject_name, rel_type, object_name, expired_at "
            "FROM knowledge_triples WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": list(wanted)},
    )
    # Projected field by field rather than copied wholesale: a bare mapping
    # copy is the shape `claim_gates` fails the build on, because a widened
    # projection could start carrying a `verification_status` past the one
    # producer allowed to build a served label. This block serves no rung.
    return {
        str(r["id"]): {
            "subject_name": r["subject_name"],
            "rel_type": r["rel_type"],
            "object_name": r["object_name"],
            "expired_at": r["expired_at"],
        }
        for r in result.mappings().all()
    }


def _suspicion_block(row: dict, counterparts: dict[str, dict]) -> dict | None:
    if row["contradiction_suspected_at"] is None:
        return None
    counterpart_id = row["contradiction_counterpart_id"]
    triple = counterparts.get(str(counterpart_id)) if counterpart_id else None
    return {
        "counterpart_id": str(counterpart_id) if counterpart_id else None,
        "counterpart_subject": triple["subject_name"] if triple else None,
        "counterpart_rel_type": triple["rel_type"] if triple else None,
        "counterpart_object": triple["object_name"] if triple else None,
        "counterpart_expired_at": triple["expired_at"] if triple else None,
        "suspected_at": row["contradiction_suspected_at"],
    }


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
    """Delegates to the one reader of this journal shape.

    The composition (T2.43) reads the same latest ``verified`` event per fact,
    and a second copy of the query is how the same shape acquires two
    behaviours. Kept as a private name here so this module's own call sites and
    tests are unchanged by where the statement lives.
    """
    return await latest_verified_evidence(session, fact_ids)


async def list_open_facts(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
    order: ReviewQueueOrder | None = None,
) -> tuple[list[dict], int]:
    """Facts whose ``review_state = 'open'`` — disputed and under-sourced
    facts. Membership is exactly the partial index's predicate; see
    ``build_facts_query``.

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
    rows = [dict(ungated_mapping(row)) for row in result.mappings().all()]

    fact_ids = [str(row["id"]) for row in rows]
    # Journal rows embedded in a claim surface: the triager reads this block
    # beside a label the gate may have suppressed, so it goes through the gate
    # too. One call for the page, so the whole page answers to one gate state.
    evidence_by_id = gated_journal_payload(
        await _latest_verified_evidence(session, fact_ids), id_kind=FACT_ID_KIND
    )

    # One query for the page, like the evidence block above: the counterpart
    # id is on the row already, but an id alone sends every reader back to
    # `knowledge_triples` for the sentence they are being asked to judge.
    counterpart_triples = await _counterpart_triples(
        session, [row["contradiction_counterpart_id"] for row in rows]
    )

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
                # Through doc 12's one producer, like every other labelled
                # door. A triager is a reader: serving the raw column here
                # showed a `corroborated` rung whose promotion audit does not
                # exist, on rows that are queued precisely because their
                # support is in question.
                **_served_labels(row["verification_status"]),
                "confidence": row["confidence"],
                "review_state": row["review_state"],
                "demotion_pending_since": row["demotion_pending_since"],
                # Derived from the raw rung, which is what a reason is for: it
                # answers why the row is queued, and `disputed` is ungated.
                "reason": _fact_reason(
                    row["verification_status"],
                    row["demotion_pending_since"],
                    row["contradiction_suspected_at"],
                ),
                # Doc 08 §6's "labelled with both sides", for the one opener
                # that had neither a side nor a label. Absent rather than empty
                # when unflagged, so "no suspicion" and "a suspicion naming
                # nothing" stay distinguishable.
                "suspected_contradiction": _suspicion_block(
                    row, counterpart_triples
                ),
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
    rows = [dict(ungated_mapping(row)) for row in result.mappings().all()]

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


async def counts(session: AsyncSession, *, project: str | None = None) -> dict[str, int]:
    """Cheap totals for the two queue arms — the ``pipeline_failures``
    ``/counts`` companion pattern (doc 08 §6 names that module as the model).

    Reuses ``build_facts_query`` / ``build_articles_query`` for the count SQL
    instead of hand-writing a second copy of the ``WHERE`` clause (T2.88):
    the counts arm and the two list arms shared the ``review_state = 'open'``
    predicate as *text* before, and a hand-duplicated predicate is exactly
    the shape that drifts silently when only one copy gets edited. Sharing
    the builder makes that drift a compile-time impossibility rather than a
    thing a test merely happens to catch.
    """
    _, facts_count_sql = build_facts_query(project)
    _, articles_count_sql = build_articles_query(project)

    params: dict[str, Any] = {}
    if project is not None:
        params["project"] = project

    facts_total = (await session.execute(text(facts_count_sql), params)).scalar_one()
    articles_total = (
        await session.execute(text(articles_count_sql), params)
    ).scalar_one()
    return {"facts": int(facts_total), "articles": int(articles_total)}
