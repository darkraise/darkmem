"""The hygiene queue — a housekeeping surface distinct from truth review
(doc 08 §6, T2.23).

**Why a second surface rather than folding this into the review queue.**
Doc 08 §6 draws the line on what a queue *adjudicates*: the review queue
(T2.22) is over ``knowledge_triples``/``knowledge_articles`` and answers "is
this belief still true" — disputed facts, under-sourced facts, ungrounded
articles. This module is over ``memories``/``memory_relations`` and answers
"does this L0 capture need housekeeping" — a duplicate a human should
triage, a low-confidence capture, a row about to expire, a memory already
retired into someone else's lineage. Conflating the two is how truth work
gets buried under chores (the epic's own words); keeping them on disjoint
tables is what makes "the two queues share no rows" true **by construction**
rather than by data coincidence — see ``build_duplicates_query`` /
``build_low_confidence_query`` / ``build_expiring_soon_query`` /
``build_superseded_query`` below: none of the four ever names
``knowledge_triples``, ``knowledge_articles`` or ``fact_sources`` in its SQL
text, so a subject's fact-side disposition (disputed, ungrounded) can never
promote or suppress its memory-side hygiene eligibility, or the reverse.
``tests/test_hygiene_queue.py`` proves this with a fixture where the *same*
memory is both low-confidence (hygiene-eligible) and the sole
``fact_sources`` origin of a disputed fact (review-eligible), and asserts
each surface returns only its own table's id.

**Membership, like T2.22's, is a status/predicate read over existing
columns, never a queue table** (doc 08 §6 rejects a table explicitly — it
grows unboundedly and makes the human the throughput bottleneck). Unlike the
review queue's single ``review_state`` column, hygiene's four reasons live on
four different columns/tables with no single state flag, so there is no one
partial index this module can share the way T2.22 shares
``ix_knowledge_triples_review``. Three of the four literal predicates below
(``hygiene_state = 'open'``, ``status = 'active'`` for the endpoint guard,
``expires_at`` approaching) have **no dedicated backing index in the
baseline** — adding one is a schema change, and this task's lane does not own
``migrations/`` (the epic serialises schema edits through one owner). The
fourth, ``status = 'superseded'``, *is* backed today by the existing
``ix_memories_status`` (non-partial, but a plain B-tree on the column serves
an equality filter), and ``tests/test_hygiene_queue.py`` proves that one
against a real EXPLAIN the same way T2.22 proves ``review_state``. The other
three are left as an honest, reported gap — a follow-up in the schema-owning
lane can add partial indexes over the same literal predicates without
changing this module's queries.

**Ordering states each arm's real primary key, not a blanket "recency"
claim (Fable review follow-up).** Doc 08 §6 asks both queues to be
"consequence-ranked and never FIFO." T2.24 built that for the review queue
over facts; none of this module's four arms do — ``duplicates`` and
``superseded`` sort by ``created_at DESC`` (newest first), ``low_confidence``
by ``confidence ASC`` (lowest first, ties by newest), ``expiring_soon`` by
``expires_at ASC`` (soonest first) — see ``build_*_query`` below for the
literal ``ORDER BY`` clauses. None of the four is consequence-ranked, and
the reason is not laziness — it is that T2.24's machinery is fact-shaped and
does not drop in over memory rows unchanged. Its **retrieval-frequency** arm
actually transfers cleanly: it
bridges ``memory_access_stats`` (keyed directly by ``memory_id``) through
``fact_sources`` only because a *fact* has no direct access counter of its
own — a memory row needs no bridge at all, since ``memory_access_stats`` is
already keyed on exactly the id this module lists. Its **subject-salience**
arm does not transfer: the SQL joins on a fact's own ``subject_name`` column
against ``entity_relations``, and memories carry no such column — a memory's
analogous salience (aggregate graph degree over the entities *it* asserts,
via ``entity_relations.memory_ids``) is a different derivation this module
would have to design and prove, not a column rename. The duplicates arm also
has a candidate signal T2.24 never needed — the near-duplicate cosine score
already sitting in the block — which argues for a hygiene-specific ranking
design rather than a verbatim port of T2.24's. Building any of this properly
(config rows, an EXPLAIN-proved statement, a tested failure mode per input,
the same rigor T2.24 gave the review queue) is real, separate scope; it is
reported here rather than bolted on as an unproven ordering. Recommended
follow-up: a T2.24-shaped task for the hygiene queue, scoped to memories.

**The within-cycle race T2.12's re-review found is closed here, generally.**
A duplicate pair can outrank a subsume pair in one dreaming cycle, leaving a
``near_duplicate`` edge written against a memory retired later in the very
same tick. Rather than special-case "same cycle", every duplicate-candidate
read here joins both endpoints and requires **both to still be `active`**
(``build_duplicates_query``). That is a strictly more general fix: it clears
the pair whether the retiring supersession happened in the same dreaming
cycle, a later one, or through this very surface's own "supersede" bulk
action — a stale duplicate is stale regardless of when the correction landed,
and the queue self-corrects on every read rather than needing a repair pass.

**Bulk actions, and which ones are undoable.** Doc 08 §6 names four:
set/extend a TTL, prune, supersede, confirm a dedup. Doc 08 §7's undo
primitive (T2.13, ``dream_undo.undo``) inverts exactly three action kinds —
subsume, associate, refine — and this module may not add a fourth (the
primitive's atomicity guarantees are proved by an AST scan over
``dream_undo.py`` that would have to be re-argued, not just re-run, for a new
inverse; that is out of this lane). Three of the four named actions map onto
an existing invertible kind without stretching its contract:

- **supersede** *is* ``ACTION_SUBSUME`` — this module calls the same
  ``supersede()`` Tier-C primitive ``memory_dream`` calls, then journals the
  identical ``consolidated``/``subsume`` shape ``dream_journal`` defines, so
  the existing ``dream_undo``/``dream_digest`` machinery inverts it with no
  new code.
- **prune** reuses ``ACTION_SUBSUME`` too, over the sibling primitive
  ``deprecate()`` (retire with no successor). Doc 01 F6 forbids a hard
  delete here regardless — "deletes are off by default; every change routes
  through supersession or invalidation" — so prune was never going to be a
  ``DELETE``. ``dream_undo``'s subsume inverse restores whatever
  ``(status, superseded_by)`` pair the journal names; it does not care
  whether the primitive that produced the pair was ``supersede()`` or
  ``deprecate()``, so reusing it for a no-successor retirement is a faithful
  application of the same inverse, not a stretch of it.
- **confirm a dedup** *is* ``ACTION_ASSOCIATE`` — it rewrites the *same*
  ``near_duplicate`` pass-block ``memory_dream``'s associate arm owns,
  through the same ``upsert_edge`` pass-keyed write, changing only
  ``hygiene_state``. Journalled with the identical associate shape, it is
  independently undoable, and — this is the amendment log's own prediction
  (2026-08-02, T2.13/T2.08) — it also makes the **original** associate action
  refuse a later undo via ``state_changed``, because ``dream_undo``'s CAS
  compares the whole pass-block and a human's triage write is not the
  journalled "after". That is the intended interlock, not a bug: an undo
  that "restored" the pre-triage block out from under a human decision would
  be the worse failure.

**Set/extend a TTL has no invertible expression and is not shipped here.**
``refine`` is the only invertible kind that could plausibly cover a memory
column, and its allowlist (``memory_dream._REFINABLE_COLUMNS``) is
deliberately narrow — ``summary`` only, guarded by three independent layers
specifically to keep anything **but** derived enrichment unreachable through
it. Widening that allowlist to admit ``expires_at`` is an edit to
``memory_dream.py``'s own safety guard, which this lane was told to touch
only as a reported decision, and it is not one: extending a guard that
exists to keep one column reachable, to admit an unrelated column, is a
different guard, not this task's to redesign. Per the brief's R4, the gap is
reported as a Tier-2 amendment (see the task's report) rather than shipped as
an action that claims undoability it does not have.

**Every bulk action journals per item, never once for the batch** (R2). Each
item's own ``consolidated`` event *is* the per-item record; there is no
additional batch-summary row a count-based metric could double-count. A
no-op (nothing changed) or a refusal (stale, not found, already in the
target state) journals nothing — ``events`` is append-only, so a phantom
transition can never be pruned once written, the same discipline
``memory_dream._journal`` documents.

**One cycle id per request.** Every item in one bulk-action call shares a
freshly minted ``cycle_id``, exactly as one dreaming tick does, so the
existing dream digest (``/api/v1/dream-digest/cycles/{id}``) renders and
undoes a hygiene bulk action the same way it renders an automated cycle —
this is the intended unification: doc 08 §7's journal substrate is one
stream for both origins, distinguished only by an informational ``origin``
key on the payload (``dream_undo``/``dream_digest`` never read it, so it
changes no existing behaviour).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_relations import pass_block_of, upsert_edge
from app.services import dream_journal as journal
from app.services.events import record_event
from app.services.supersede import deprecate, supersede
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# Operator-tunable via query params rather than a `config` row: this task's
# scope is the queue and its actions, not a new job/config surface, and a
# request-scoped override is enough for a human triaging interactively.
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_EXPIRING_SOON_DAYS = 7

# T2.12's own vocabulary (`dream_journal.HYGIENE_STATE_OPEN`) declares exactly
# one value. `confirm a dedup` (doc 08 §6) is the only triage verb the doc
# names, so this is the only transition this module makes — a `dismissed`
# verdict is not declared anywhere the vocabulary lives and was dropped
# rather than shipped as a silent, undeclared widening. Add it back, taxonomy-
# first, in the module that owns the vocabulary, the day a real second state
# is designed.
HYGIENE_STATE_CONFIRMED = "confirmed"

# Informational only — an extra key on the shared journal payload naming
# which surface produced the row. Neither `dream_undo` nor `dream_digest`
# reads it; it exists for an operator reading the raw event.
ORIGIN_HYGIENE = "hygiene_queue"


# ── read side: four membership arms, none touching the review-queue tables ──


def build_duplicates_query(project: str | None) -> tuple[str, str]:
    """(items_sql, count_sql) for candidate-duplicate pairs.

    ``hygiene_state = 'open'`` is a literal in the SQL text, unparameterised,
    mirroring T2.22's discipline for the same planner reason (a future
    partial index on this exact expression would match by construction).
    Both endpoints must be `active` — see the module docstring on the
    within-cycle race this closes generally.
    """
    where = [
        "(mr.properties -> 'dream' -> 'near_duplicate' ->> 'hygiene_state') = 'open'",
        "src.status = 'active'",
        "tgt.status = 'active'",
    ]
    if project is not None:
        where.append("mr.project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    items_sql = (
        "SELECT CAST(mr.id AS text) AS id, "
        "       CAST(mr.source_memory_id AS text) AS source_memory_id, "
        "       CAST(mr.target_memory_id AS text) AS target_memory_id, "
        "       mr.rel_type, mr.project, mr.properties, mr.created_at "
        "FROM memory_relations mr "
        "JOIN memories src ON src.id = mr.source_memory_id "
        "JOIN memories tgt ON tgt.id = mr.target_memory_id "
        f"WHERE {where_sql} "
        "ORDER BY mr.created_at DESC, mr.id DESC LIMIT :limit OFFSET :offset"
    )
    count_sql = (
        "SELECT COUNT(*) FROM memory_relations mr "
        "JOIN memories src ON src.id = mr.source_memory_id "
        "JOIN memories tgt ON tgt.id = mr.target_memory_id "
        f"WHERE {where_sql}"
    )
    return items_sql, count_sql


def build_low_confidence_query(project: str | None) -> tuple[str, str]:
    """``status = 'active'`` is literal (the arm's own fixed scope, like
    T2.22's ``review_state = 'open'``); ``confidence`` threshold is a bind
    parameter because it is operator-tunable per call.
    """
    where = ["status = 'active'", "is_archived = false", "confidence < CAST(:threshold AS real)"]
    if project is not None:
        where.append("project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    items_sql = (
        "SELECT CAST(id AS text) AS id, content, project, confidence, "
        "       status::text AS status, expires_at, created_at "
        "FROM memories "
        f"WHERE {where_sql} "
        "ORDER BY confidence ASC, created_at DESC, id DESC LIMIT :limit OFFSET :offset"
    )
    count_sql = f"SELECT COUNT(*) FROM memories WHERE {where_sql}"
    return items_sql, count_sql


def build_expiring_soon_query(project: str | None) -> tuple[str, str]:
    where = [
        "status = 'active'",
        "is_archived = false",
        "expires_at IS NOT NULL",
        "expires_at <= now() + make_interval(days => CAST(:within_days AS int))",
    ]
    if project is not None:
        where.append("project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    items_sql = (
        "SELECT CAST(id AS text) AS id, content, project, confidence, "
        "       status::text AS status, expires_at, created_at "
        "FROM memories "
        f"WHERE {where_sql} "
        "ORDER BY expires_at ASC, id ASC LIMIT :limit OFFSET :offset"
    )
    count_sql = f"SELECT COUNT(*) FROM memories WHERE {where_sql}"
    return items_sql, count_sql


def build_superseded_query(project: str | None) -> tuple[str, str]:
    """``status = 'superseded'`` is literal and backed today by
    ``ix_memories_status`` — the one arm this module proves against a real
    EXPLAIN (``tests/test_hygiene_queue.py``), the same discipline T2.22 used
    for ``review_state``.
    """
    where = ["status = 'superseded'"]
    if project is not None:
        where.append("project = CAST(:project AS text)")
    where_sql = " AND ".join(where)
    items_sql = (
        "SELECT CAST(id AS text) AS id, content, project, confidence, "
        "       status::text AS status, CAST(superseded_by AS text) AS superseded_by, "
        "       created_at "
        "FROM memories "
        f"WHERE {where_sql} "
        "ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :offset"
    )
    count_sql = f"SELECT COUNT(*) FROM memories WHERE {where_sql}"
    return items_sql, count_sql


def _duplicate_item(row: dict) -> dict:
    block = pass_block_of(row, journal.NEAR_DUPLICATE_PASS)
    return {
        "id": row["id"],
        "source_memory_id": row["source_memory_id"],
        "target_memory_id": row["target_memory_id"],
        "rel_type": row["rel_type"],
        "project": row["project"],
        "score": (block or {}).get("score"),
        "verdict": (block or {}).get("verdict"),
        "hygiene_state": (block or {}).get("hygiene_state"),
        "detected_at": (block or {}).get("detected_at"),
        "created_at": row["created_at"],
    }


async def list_duplicates(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    items_sql, count_sql = build_duplicates_query(project)
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if project is not None:
        params["project"] = project
    rows = (await session.execute(text(items_sql), params)).mappings().all()
    items = [_duplicate_item(dict(row)) for row in rows]
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


def _memory_item(row: dict, *, reason: str) -> dict:
    return {
        "id": row["id"],
        "project": row["project"],
        "content_preview": (row["content"] or "")[:200],
        "confidence": row.get("confidence"),
        "expires_at": row.get("expires_at"),
        "status": row["status"],
        "superseded_by": row.get("superseded_by"),
        "reason": reason,
        "created_at": row["created_at"],
    }


async def list_low_confidence(
    session: AsyncSession,
    *,
    project: str | None = None,
    threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    items_sql, count_sql = build_low_confidence_query(project)
    params: dict[str, Any] = {"limit": limit, "offset": offset, "threshold": threshold}
    if project is not None:
        params["project"] = project
    rows = (await session.execute(text(items_sql), params)).mappings().all()
    items = [_memory_item(dict(row), reason="low_confidence") for row in rows]
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


async def list_expiring_soon(
    session: AsyncSession,
    *,
    project: str | None = None,
    within_days: int = DEFAULT_EXPIRING_SOON_DAYS,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    items_sql, count_sql = build_expiring_soon_query(project)
    params: dict[str, Any] = {"limit": limit, "offset": offset, "within_days": within_days}
    if project is not None:
        params["project"] = project
    rows = (await session.execute(text(items_sql), params)).mappings().all()
    items = [_memory_item(dict(row), reason="expiring_soon") for row in rows]
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


async def list_superseded(
    session: AsyncSession,
    *,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    items_sql, count_sql = build_superseded_query(project)
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if project is not None:
        params["project"] = project
    rows = (await session.execute(text(items_sql), params)).mappings().all()
    items = [_memory_item(dict(row), reason="superseded_lineage") for row in rows]
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()
    return items, int(total)


async def counts(
    session: AsyncSession,
    *,
    project: str | None = None,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> dict[str, int]:
    """Cheap totals for all four arms — the ``pipeline_failures``/T2.22
    ``/counts`` companion pattern."""
    _, dup_count_sql = build_duplicates_query(project)
    _, low_count_sql = build_low_confidence_query(project)
    _, exp_count_sql = build_expiring_soon_query(project)
    _, sup_count_sql = build_superseded_query(project)

    base_params: dict[str, Any] = {}
    if project is not None:
        base_params["project"] = project

    dup_total = (await session.execute(text(dup_count_sql), base_params)).scalar_one()
    low_total = (
        await session.execute(
            text(low_count_sql), {**base_params, "threshold": low_confidence_threshold}
        )
    ).scalar_one()
    exp_total = (
        await session.execute(
            text(exp_count_sql), {**base_params, "within_days": expiring_soon_days}
        )
    ).scalar_one()
    sup_total = (await session.execute(text(sup_count_sql), base_params)).scalar_one()

    return {
        "duplicates": int(dup_total),
        "low_confidence": int(low_total),
        "expiring_soon": int(exp_total),
        "superseded": int(sup_total),
    }


# ── bulk actions ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HygieneActionResult:
    """One item's outcome — never a batch summary (R2)."""

    item_id: str
    applied: bool
    event_id: int | None
    reason: str | None


_READ_MEMORY_STATE = text(
    "SELECT status::text AS status, CAST(superseded_by AS text) AS superseded_by, "
    "       project "
    "FROM memories WHERE id = CAST(:memory_id AS uuid)"
)

_EDGE_BY_ID = text(
    "SELECT CAST(id AS text) AS id, "
    "       CAST(source_memory_id AS text) AS source_memory_id, "
    "       CAST(target_memory_id AS text) AS target_memory_id, "
    "       rel_type, project, properties "
    "FROM memory_relations WHERE id = CAST(:id AS uuid)"
)

# Read-your-own-write within the same session/transaction: `record_event`
# reports nothing back, and it is the one writer (CLAUDE.md), so this reads
# the row it just committed to its own SAVEPOINT rather than inserting a
# second time through a different path.
#
# **Scoped by `cycle_id` and a `created_at` floor, not by `object_id` alone.**
# `record_event` degrades loudly and never raises (CLAUDE.md): if its own
# insert fails, this module's caller sees nothing wrong and moves on believing
# the action journalled. An `object_id`-only readback would then return the
# id of whatever *prior* `consolidated` event that memory carries — a
# supersession from an earlier cycle, say — reporting it as this action's
# `event_id`. That is silent false attribution on the wire (a caller trusts a
# stale id as its own) and a silently unjournalled, un-undoable action. The
# `cycle_id` this batch just minted cannot collide with any event from a
# different batch or an automated tick, so scoping on it is what makes "no
# row" mean "the write did not land" rather than "an old row happened to
# match". The floor is the same discipline `dream_undo`'s by-id lookups use
# (CLAUDE.md: "every undo lookup carries a created_at bound and prunes to one
# or two [partitions]") — a correctness backstop is not a reason to scan every
# monthly child.
_LAST_EVENT = text(
    "SELECT id FROM events "
    "WHERE event_type = CAST(:event_type AS text) "
    "  AND object_type = CAST(:object_type AS text) "
    "  AND object_id = CAST(:object_id AS uuid) "
    "  AND payload ->> 'cycle_id' = CAST(:cycle_id AS text) "
    "  AND created_at >= CAST(:floor AS timestamptz) "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)

_SERVER_NOW = text("SELECT now() AS now")


async def _server_now(session: AsyncSession) -> datetime:
    """The batch's floor, read from the server rather than the app clock —
    the same reason every other timestamp bound in this codebase that guards
    correctness (not just display) is server-side."""
    row = (await session.execute(_SERVER_NOW)).mappings().one()
    return row["now"]


async def _memory_state(session: AsyncSession, memory_id: str) -> dict | None:
    row = (
        await session.execute(_READ_MEMORY_STATE, {"memory_id": memory_id})
    ).mappings().first()
    return dict(row) if row else None


async def _read_edge_by_id(session: AsyncSession, relation_id: str) -> dict | None:
    row = (await session.execute(_EDGE_BY_ID, {"id": relation_id})).mappings().first()
    return dict(row) if row else None


async def _last_event_id(
    session: AsyncSession, *, object_id: str, cycle_id: str, floor: datetime
) -> int | None:
    row = (
        await session.execute(
            _LAST_EVENT,
            {
                "event_type": journal.EVENT_TYPE,
                "object_type": journal.OBJECT_TYPE,
                "object_id": object_id,
                "cycle_id": cycle_id,
                "floor": floor,
            },
        )
    ).mappings().first()
    return int(row["id"]) if row else None


async def _journal_subsume(
    session: AsyncSession,
    *,
    memory_id: str,
    project: str | None,
    before: dict,
    after: dict,
    pair: dict,
    cycle_id: str,
    batch_floor: datetime,
    actor: str,
    hygiene_reason: str,
) -> int | None:
    """The same ``consolidated``/``subsume`` shape ``memory_dream.apply_subsume``
    writes, so ``dream_undo``/``dream_digest`` need no new code to see it.
    """
    await record_event(
        session,
        event_type=journal.EVENT_TYPE,
        object_type=journal.OBJECT_TYPE,
        object_id=UUID(memory_id),
        project=project,
        actor=actor,
        payload={
            "action": journal.ACTION_SUBSUME,
            "before": before,
            "after": after,
            "pair": pair,
            "detector": journal.DETECTOR,
            "verdict": None,
            "score": None,
            "cycle_id": cycle_id,
            "origin": ORIGIN_HYGIENE,
            "hygiene_reason": hygiene_reason,
        },
    )
    return await _last_event_id(
        session, object_id=memory_id, cycle_id=cycle_id, floor=batch_floor
    )


async def bulk_supersede(
    session: AsyncSession,
    items: list[dict],
    *,
    actor: str,
    cycle_id: str | None = None,
) -> tuple[str, list[HygieneActionResult]]:
    """Human-directed supersession — the primitive memory_dream calls, plus
    the shared journal shape that makes it undoable through T2.13."""
    batch_cycle_id = cycle_id or str(new_id())
    batch_floor = await _server_now(session)
    results: list[HygieneActionResult] = []
    for item in items:
        memory_id = str(item["memory_id"])
        successor_id = str(item["superseded_by"])
        async with session.begin_nested():
            before_state = await _memory_state(session, memory_id)
            if before_state is None:
                results.append(
                    HygieneActionResult(
                        item_id=memory_id, applied=False, event_id=None,
                        reason="not_found",
                    )
                )
                continue
            result = await supersede(
                session,
                memory_id=memory_id,
                superseded_by=successor_id,
                reason=f"{ORIGIN_HYGIENE}:supersede",
            )
            if not result.applied:
                results.append(
                    HygieneActionResult(
                        item_id=memory_id, applied=False, event_id=None,
                        reason=result.reason,
                    )
                )
                continue
            event_id = await _journal_subsume(
                session,
                memory_id=memory_id,
                project=before_state["project"],
                before={
                    "status": before_state["status"],
                    "superseded_by": before_state["superseded_by"],
                },
                after={"status": result.status, "superseded_by": result.superseded_by},
                pair={"older": memory_id, "newer": successor_id},
                cycle_id=batch_cycle_id,
                batch_floor=batch_floor,
                actor=actor,
                hygiene_reason="supersede",
            )
        results.append(
            HygieneActionResult(
                item_id=memory_id, applied=True, event_id=event_id, reason=None
            )
        )
    return batch_cycle_id, results


async def bulk_prune(
    session: AsyncSession,
    memory_ids: list[str],
    *,
    actor: str,
    cycle_id: str | None = None,
) -> tuple[str, list[HygieneActionResult]]:
    """Retire a memory with no live successor (``deprecate()``), reusing the
    subsume inverse — see the module docstring for why that is a faithful
    reuse and not a stretch of its contract. Never a hard delete (doc 01 F6).
    """
    batch_cycle_id = cycle_id or str(new_id())
    batch_floor = await _server_now(session)
    results: list[HygieneActionResult] = []
    for raw_id in memory_ids:
        memory_id = str(raw_id)
        async with session.begin_nested():
            before_state = await _memory_state(session, memory_id)
            if before_state is None:
                results.append(
                    HygieneActionResult(
                        item_id=memory_id, applied=False, event_id=None,
                        reason="not_found",
                    )
                )
                continue
            result = await deprecate(
                session, memory_id=memory_id, reason=f"{ORIGIN_HYGIENE}:prune"
            )
            if not result.applied:
                results.append(
                    HygieneActionResult(
                        item_id=memory_id, applied=False, event_id=None,
                        reason=result.reason,
                    )
                )
                continue
            event_id = await _journal_subsume(
                session,
                memory_id=memory_id,
                project=before_state["project"],
                before={
                    "status": before_state["status"],
                    "superseded_by": before_state["superseded_by"],
                },
                after={"status": result.status, "superseded_by": result.superseded_by},
                pair={"older": memory_id, "newer": None},
                cycle_id=batch_cycle_id,
                batch_floor=batch_floor,
                actor=actor,
                hygiene_reason="prune",
            )
        results.append(
            HygieneActionResult(
                item_id=memory_id, applied=True, event_id=event_id, reason=None
            )
        )
    return batch_cycle_id, results


async def bulk_confirm_dedup(
    session: AsyncSession,
    relation_ids: list[str],
    *,
    actor: str,
    cycle_id: str | None = None,
) -> tuple[str, list[HygieneActionResult]]:
    """Triage a duplicate candidate — rewrites the same ``near_duplicate``
    pass-block ``memory_dream``'s associate arm owns, changing only
    ``hygiene_state`` to ``HYGIENE_STATE_CONFIRMED``, journalled as the same
    associate shape so it is independently undoable and so the *original*
    associate action's own undo correctly refuses via ``state_changed`` (the
    amendment log's own prediction for this exact write).
    """
    batch_cycle_id = cycle_id or str(new_id())
    batch_floor = await _server_now(session)
    results: list[HygieneActionResult] = []
    for raw_id in relation_ids:
        relation_id = str(raw_id)
        async with session.begin_nested():
            edge = await _read_edge_by_id(session, relation_id)
            if edge is None:
                results.append(
                    HygieneActionResult(
                        item_id=relation_id, applied=False, event_id=None,
                        reason="not_found",
                    )
                )
                continue
            existing_block = pass_block_of(edge, journal.NEAR_DUPLICATE_PASS)
            if existing_block is None:
                results.append(
                    HygieneActionResult(
                        item_id=relation_id, applied=False, event_id=None,
                        reason="not_a_duplicate_candidate",
                    )
                )
                continue
            src_state = await _memory_state(session, edge["source_memory_id"])
            tgt_state = await _memory_state(session, edge["target_memory_id"])
            if (
                src_state is None or tgt_state is None
                or src_state["status"] != "active" or tgt_state["status"] != "active"
            ):
                results.append(
                    HygieneActionResult(
                        item_id=relation_id, applied=False, event_id=None,
                        reason="stale",
                    )
                )
                continue
            if existing_block.get("hygiene_state") == HYGIENE_STATE_CONFIRMED:
                results.append(
                    HygieneActionResult(
                        item_id=relation_id, applied=False, event_id=None,
                        reason="unchanged",
                    )
                )
                continue

            new_block = {**existing_block, "hygiene_state": HYGIENE_STATE_CONFIRMED}
            write = await upsert_edge(
                session,
                source_memory_id=edge["source_memory_id"],
                target_memory_id=edge["target_memory_id"],
                rel_type=edge["rel_type"],
                project=edge["project"],
                pass_key=journal.NEAR_DUPLICATE_PASS,
                block=new_block,
            )
            object_id = edge["source_memory_id"]
            await record_event(
                session,
                event_type=journal.EVENT_TYPE,
                object_type=journal.OBJECT_TYPE,
                object_id=UUID(object_id),
                project=edge["project"],
                actor=actor,
                payload={
                    "action": journal.ACTION_ASSOCIATE,
                    "before": {"edge": existing_block},
                    "after": {
                        "edge": {
                            "source": edge["source_memory_id"],
                            "target": edge["target_memory_id"],
                            "rel_type": edge["rel_type"],
                            "properties": {journal.NEAR_DUPLICATE_PASS: new_block},
                        }
                    },
                    "created": write.created,
                    "pair": {
                        "older": edge["target_memory_id"],
                        "newer": edge["source_memory_id"],
                    },
                    "detector": journal.DETECTOR,
                    "verdict": existing_block.get("verdict"),
                    "score": existing_block.get("score"),
                    "cycle_id": batch_cycle_id,
                    "origin": ORIGIN_HYGIENE,
                    "hygiene_reason": "confirm_dedup",
                },
            )
            event_id = await _last_event_id(
                session, object_id=object_id, cycle_id=batch_cycle_id, floor=batch_floor
            )
        results.append(
            HygieneActionResult(
                item_id=relation_id, applied=True, event_id=event_id, reason=None
            )
        )
    return batch_cycle_id, results
