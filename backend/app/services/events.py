"""The append-only events writer, the journaling convention (T1.07), and the
read API over the durable substrate (T1.08).

Doc 04 §8.1 makes ``events`` the sole audit substrate from day one.
``record_event`` is the one helper every subsystem journals through —
capture, extraction/pipeline outcomes, supersession, auth, and setup all
route the same shape through here (doc 05 §2.3) — so payload conventions
stay uniform and the append-only/partition mechanics live in exactly one
place.

``EVENT_TYPES`` / ``OBJECT_TYPES`` are the closed vocabularies doc 04 §8.1
names, kept here rather than in ``app.taxonomy`` deliberately: that module's
four vocabularies (doc 06 §3) normalise *LLM-emitted* strings, so an unknown
value must be rewritten to a safe fallback (``concept``, ``RELATED_TO``, ...)
or a hallucinated type would land on disk. ``event_type``/``object_type`` are
never LLM output — every call site is a literal string written by this
codebase — so there is nothing to rewrite; an unrecognised value is a
programming error, not untrusted input, and the correct response is a loud
warning (so it surfaces in review/CI logs) rather than a silent substitution
that would quietly misfile the row. That asymmetry is why these vocabularies
live beside their one writer instead of joining taxonomy.py's LLM-facing set
— the same reasoning that already keeps ``TECH_TYPES`` in ``app.services.relations``
beside the graph code that reads it rather than in taxonomy.py.

``list_events``/``calendar_counts``/``object_timeline`` back the doc 12 §7
read API. Each builds its WHERE clause (and the calendar's GROUP BY) so the
project/object/date predicates ride the query Postgres actually executes,
never a post-fetch Python filter — that is what lets the two doc 04 §8.1
indexes carry the read: ``ix_events_object`` for the timeline,
``ix_events_day`` for the calendar. The calendar bucket expression,
``(created_at AT TIME ZONE 'UTC')::date``, must match the index expression
verbatim — a bare ``created_at::date`` is only STABLE (it resolves against
the session ``TimeZone`` GUC), so it neither matches the IMMUTABLE index
expression nor means the same UTC day to every viewer.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Named rather than spelled twice, because two modules that may not import each
# other both depend on it meaning the same thing: the Tier-C contradiction scan
# writes it and the veto reads it back. The vocabulary is the neutral ground
# they share.
CONTRADICTION_SCANNED = "contradiction_scanned"

# A human's dismissal of the model scan's flag (T2.112). **Deliberately its own
# type rather than a `human_verdict` carrying a fifth verdict value**, which is
# the shape `human_adjudication` argues for and is right for its own case.
# `HUMAN_VERDICTS` is doc 08 §6's four verbs and all four adjudicate *the fact*
# — its truth, its grounding, its rung. A dismissal adjudicates the **finding**;
# the fact is left exactly as it was. Adding `dismissed` there would make it a
# legal verdict to record against any fact, which means nothing, and that set is
# closed and raise-guarded precisely so unmeaning verdicts cannot exist.
#
# It also creates a signal rather than destroying one: a dismissal is a measured
# false positive of the LLM contradiction scan on live data — the evidence a
# later re-qualification of that arm would want, and the only such evidence this
# system produces outside a gold set.
CONTRADICTION_DISMISSED = "contradiction_dismissed"

# Doc 10 §6's re-verify outcome. Named rather than spelled twice for the reason
# above: the re-verifier writes it and a human reading a downgraded badge is
# what reads it back, and the two only meet through this vocabulary. It is
# deliberately its own type rather than a second `sources_changed`: that one
# says a fact's evidence moved and is the recompute's queue, while this one says
# *why* a particular citation stopped resolving — the address, the sha it broke
# at — which is the record invariant 14 requires a silent-looking demotion to
# leave behind.
CITATION_STALE = "citation_stale"

# Doc 09 §4.4's "labelled stale" transition (T3.05), and the debounce's clock.
# Named here because two things read it back: the tick that decides whether a
# stale article's fact set has settled long enough to re-synthesise, and a human
# asking why an article carries the label.
#
# It is the debounce anchor because **nothing else records when a subject's
# verified set last moved**: `knowledge_triples` has no `updated_at`, and a
# promotion — the burst §4.4 names — writes no timestamp on the fact row at all.
# The row's `created_at` is therefore the only honest "the set changed at" this
# schema holds, and it is one the doc already required to be written.
ARTICLE_STALE = "article_stale"

# Doc 09 §4.4 as amended 2026-08-12: a re-synthesis measured below the coverage
# bar. The row is honestly *about* the standing article — "an attempted
# replacement for this article was held" — and carries measurements only, never
# the held prose, which is discarded.
#
# Its own type rather than a `verified` row, because the standing article's
# prose was **not** what was measured: a `verified` row here would poison any
# later article-side metric SQL over that stream, which is the same reasoning
# that keeps `contradiction_dismissed` out of `HUMAN_VERDICTS`.
RESYNTHESIS_HELD = "resynthesis_held"

# Doc 18 §5's key lifecycle, landed with their emitters (T4.01) on the rule
# T3.16 settled for `resumed`: a vocabulary value with no writer is
# indistinguishable from one whose writer was deleted.
#
# `object_type='system'`, matching `setup_complete` and `auth_lockout` under doc
# 18 §10 — a credential is box-level, not one of the ten domain objects, and
# widening `OBJECT_TYPES` for it would put a non-domain member in a set every
# timeline read enumerates. `object_id` still names the key, so the two rows
# reconstruct one credential's life through the ordinary object index.
#
# `api_key_id` on these two rows is deliberately null. That column means "the
# key that made this call"; a mint and a revocation are made by a human session
# over the single door, so stamping it would attribute a key's creation to
# itself and put a row in doc 17's keyed-call population that no key made.
API_KEY_CREATED = "api_key_created"
API_KEY_REVOKED = "api_key_revoked"

# Increment 6's off-host ship (spec §9.3-§9.4). `object_type='system'`: a
# snapshot is the whole box, not one of the ten domain objects. Named
# constants rather than bare literals in the list below, so the emitter can
# import them -- `tests/test_events.py`'s scan resolves a Name it can find as
# a module-level string constant, and that is what keeps the emit site
# traceable instead of unresolved.
#
# A snapshot landed on a destination and its read-back checksum matched.
BACKUP_SHIPPED = "backup_shipped"
# Uploaded is not restorable: the read-back disagreed or could not be taken at
# all. Its own value rather than a flag on the row above, so the failure is
# countable without parsing a payload.
BACKUP_VERIFY_FAILED = "backup_verify_failed"

# Doc 04 §8.1's list is explicitly non-exhaustive ("..."); this is the subset
# named there plus the values T1.07's call sites (capture, extraction,
# supersession, pipeline outcomes) actually emit. Widening it is
# taxonomy-first, same discipline as app.taxonomy: land the value here before
# any emitter ships it.
EVENT_TYPES: list[str] = [
    "created",
    # The three memory-door actions `PostgresAuditRepository.log` forwards
    # unmapped. Its `_ACTION_EVENT_TYPE` remaps only "create" and "pipeline";
    # every other action reaches `record_event` as its own imperative spelling,
    # so these three sit beside the past-participle values rather than matching
    # them. The vocabulary is corrected to the emitted literal, never the other
    # way around -- the same call `setup_complete` below records, and here it
    # is load-bearing twice over: `tests/test_mcp_auth.py` asserts the literal
    # "delete" in the journal, and the audit endpoint's action filter excludes
    # these exact strings.
    #
    # They warned on every memory update, delete and merge from the day the
    # vocabulary closed. Neither AST guard could see them: both resolve
    # `_ACTION_EVENT_TYPE.get(action, action)` to the dict's *mapped* values
    # and are blind to the pass-through default, which is why the scan reports
    # no unresolved site here either.
    "update",
    "delete",
    "merge",
    "superseded",
    "deprecated",
    "expired",
    "invalidated",
    "extracted",
    "consolidated",
    "merged",
    "verified",
    "sources_changed",
    CITATION_STALE,
    ARTICLE_STALE,
    RESYNTHESIS_HELD,
    CONTRADICTION_SCANNED,
    CONTRADICTION_DISMISSED,
    "document_filed",
    # The metadata verb's journal row; carries no document text.
    "document_updated",
    # Increment 8's block verbs (spec §8.2). One row per verb call; the
    # payload names the verb, the block id and the resulting content_hash,
    # and carries NO block text -- write-time minimization, stated here at
    # the vocabulary because the writer lives in block_verbs.py.
    "blocks_edited",
    # The subtree delete's journal row, one per deleted document (increment 2).
    # `delete_document` journals nothing and that is right for one note; a
    # bulk delete is unrecoverable and, over MCP, the event's `api_key_id` is
    # the only record of who ran it. Carries ids and the prefix, no content.
    "documents_deleted",
    # The page tree's lifecycle. `page_updated` is a title or property edit;
    # a block edit journals `blocks_edited` like a document's does. Deletion
    # is a `deleted_at` stamp, so `page_deleted` and `page_purged` are
    # different events: the first is reversible by `page_restored` and the
    # second is not.
    "page_created",
    "page_updated",
    "page_moved",
    "page_deleted",
    "page_restored",
    "page_purged",
    # One row per import, on its root page. Non-strict: the import is
    # re-runnable, so a lost row costs an audit line, not a denominator.
    "pages_imported",
    # The block-embedding backstop job's run summary (T-doc-door.6). Landed
    # ahead of its emitter, taxonomy-first, same as every other value here.
    "block_embeddings_refreshed",
    "repo_registered",
    "repo_synced",
    "repo_indexed",
    # The keyed act, distinct from the indexing it triggers: the webhook is
    # the only route a credential reaches, and the index that follows is the
    # system's own work (it may short-circuit on an unchanged HEAD, or never
    # start at all on a 409). Attributing the *index* to the key would leave
    # exactly the deliveries an operator most wants to see — probes, conflicts
    # — unrecorded (E4 epic review, C1).
    "repo_webhook_received",
    # The file-scoped reindex doors (REST + MCP), journalled once at the end of
    # the door with the outcome the door computed. Distinct from `repo_indexed`,
    # which is the run's own work, and from `repo_webhook_received`, which names
    # a different door. Landed ahead of its emitter, taxonomy-first.
    "repo_reindex_requested",
    # A /mcp request that arrived through the proxy while the exposed
    # switch is on, and was refused (T4.17). Journalled at most once a
    # minute: the refusal is unbounded, the record of it must not be.
    "mcp_proxied_refused",
    "inject",
    "inject_curbed",
    # "setup_completed" carried a spelling drift against the literal
    # `setup.py` actually journals ("setup_complete", no trailing "d") —
    # found by T2.102, fixed by T2.103. The vocabulary is corrected to
    # match the emitted value rather than the other way around: changing
    # the emitted literal would be a behaviour change to what the audit
    # trail records, and existing rows already carry the "setup_complete"
    # spelling.
    "setup_complete",
    "auth_setup",
    "auth_login_success",
    "auth_login_failed",
    "auth_logout",
    "auth_password_change",
    "auth_lockout",
    "repo_hint_rejected",
    "buffer_requeued",
    "buffer_discarded",
    "maintenance_run",
    "human_verdict",
    "pin_decision",
    "undone",
    "checkpoint_saved",
    # T3.17, landed 2026-08-11 with its emitter. T3.16 reserved this slot and
    # deliberately left it empty, on the reasoning that an unemitted value here
    # is indistinguishable from one whose writer was deleted — so the value
    # lands *with* the writer, not ahead of it.
    "resumed",
    # The work-log lane (spec 2026-09-23 §1). Lifecycle only: no entry body
    # or properties value reaches a payload, because the entries table is
    # the history and this journal is unpurgeable by ruling (T2.59).
    "workstream_opened",
    "workstream_closed",
    "workstream_reopened",
    "workstream_purged",
    # T3.07's research run, landed with its emitter on the same reasoning.
    # `object_type='system'`: a run is not any one memory, and the memories it
    # filed are named in the payload.
    "research_run",
    API_KEY_CREATED,
    API_KEY_REVOKED,
    BACKUP_SHIPPED,
    BACKUP_VERIFY_FAILED,
]

OBJECT_TYPES: list[str] = [
    "memory",
    "entity",
    "relation",
    "fact",
    "article",
    "topic",
    "document",
    "page",
    "repository",
    "checkpoint",
    "workstream",
    "system",
]

_EVENT_TYPE_SET = frozenset(EVENT_TYPES)
_OBJECT_TYPE_SET = frozenset(OBJECT_TYPES)

_INSERT = text(
    "INSERT INTO events "
    "(event_type, object_type, object_id, project, actor, api_key_id, source, payload) "
    "VALUES (:event_type, :object_type, CAST(:object_id AS uuid), :project, "
    ":actor, CAST(:api_key_id AS uuid), :source, CAST(:payload AS jsonb))"
)


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    object_type: str,
    object_id: uuid.UUID | None = None,
    project: str | None = None,
    actor: str | None = None,
    api_key_id: uuid.UUID | None = None,
    source: str | None = None,
    payload: dict | None = None,
) -> bool:
    """Append one row to the durable events journal. Returns whether it landed.

    Never raises. Journaling is a side-channel to the operation it records —
    a capture, an extraction pass, a supersession flip — so a broken
    partition, a bad payload, or any other journal-side failure must degrade
    loudly (logged here) without failing the caller. The insert runs inside
    its own SAVEPOINT so a real DB-level failure (a constraint violation, a
    missing partition) rolls back only the journal write, leaving the
    caller's own transaction exactly as usable as if this call had never
    happened.

    **The return value exists because that contract is right for most callers
    and wrong for a few** (T2.113). A capture must survive a journal failure;
    a *verification transition* must not, because doc 17 §5.1's metrics are SQL
    over this table alone, so a status change whose row never landed is not a
    lost log line — it is a transition that silently leaves the denominator,
    and under-power announces itself where this does not. Raising here instead
    would impose the strict contract on every caller and take down capture with
    the journal; returning the signal lets each caller answer for itself, and
    the callers that ignore it behave exactly as before.

    ``False`` means the row is not there: the SAVEPOINT rolled it back, so a
    caller that treats this as fatal is refusing an operation that genuinely
    has no audit record, not one that might.
    """
    if event_type not in _EVENT_TYPE_SET:
        logger.warning(
            "events: event_type %r is outside the doc 04 §8.1 closed vocabulary",
            event_type,
        )
    if object_type not in _OBJECT_TYPE_SET:
        logger.warning(
            "events: object_type %r is outside the doc 04 §8.1 closed vocabulary",
            object_type,
        )

    try:
        # asyncpg cannot infer the uuid and jsonb parameter types here, so
        # each is cast explicitly (invariant 10).
        async with session.begin_nested():
            await session.execute(
                _INSERT,
                {
                    "event_type": event_type,
                    "object_type": object_type,
                    "object_id": str(object_id) if object_id else None,
                    "project": project,
                    "actor": actor,
                    "api_key_id": str(api_key_id) if api_key_id else None,
                    "source": source,
                    "payload": json.dumps(payload or {}, default=str),
                },
            )
    except Exception:
        logger.error(
            "events: failed to journal event_type=%r object_type=%r object_id=%s",
            event_type, object_type, object_id,
            exc_info=True,
        )
        return False
    return True


async def record_maintenance_run(
    session_factory,
    *,
    operation: str,
    outcome: str,
    detail: dict | None = None,
) -> None:
    """Journal one Settings -> Maintenance / Jobs -> cleanup operation run.

    The one writer for the ``maintenance_run`` event type, shared by
    ``job_runners.py``'s cleanup runners and ``reembed.py``'s background
    tasks, so the two call sites can never drift into their own vocabulary
    or payload shape (T1.63 ruling 2). Runs through a fresh, independently
    committed session — mirroring ``auth.py``'s ``_record_audit`` — because
    a background task's own session may already be closed, rolled back, or
    mid-exception by the time the outcome is known.
    """
    try:
        async with session_factory() as session:
            await record_event(
                session,
                event_type="maintenance_run",
                object_type="system",
                payload={"operation": operation, "outcome": outcome, "detail": detail or {}},
            )
            await session.commit()
    except Exception:
        # record_event itself never raises; a failure here is the fresh
        # session/commit machinery around it (a DB blip). Journaling is a
        # side-channel to the operation it records (same rule as
        # record_event's own docstring) — it must never take the operation
        # down with it.
        logger.error(
            "events: failed to journal maintenance_run operation=%r outcome=%r",
            operation, outcome, exc_info=True,
        )


# Months kept ahead of the current one. A RANGE-partitioned parent rejects every
# insert that lands outside a child, so running out of partitions does not
# degrade the journal — it stops it, and takes the write that was being journaled
# with it.
_MONTHS_AHEAD = 1

_ENSURE_PARTITIONS = text(
    "SELECT events_ensure_partition("
    "    (date_trunc('month', now() AT TIME ZONE 'UTC')"
    "     + (make_interval(months => g))::interval)::date) AS child "
    "FROM generate_series(0, :months_ahead) AS g"
)


async def reconcile_event_partitions(session: AsyncSession) -> list[str]:
    """Ensure the current and next monthly `events` children exist, and return
    their names.

    Idempotent, and deliberately not boot-only: a process that boots in January
    and is still running in March would have exhausted the two partitions the
    baseline created, so the same reconcile also runs as an arm on
    ``pipeline_failure_cleanup``. The per-child TRUNCATE guard is attached by
    ``events_ensure_partition`` itself — the parent's truncate trigger does not
    cascade to children, so a partition created without it would be truncatable.
    """
    rows = await session.execute(_ENSURE_PARTITIONS, {"months_ahead": _MONTHS_AHEAD})
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Read API (T1.08, doc 12 §7) — three shapes over the durable substrate.
# `events` is never written through the API (§8.1: forbid-triggers, no
# POST/PUT/DELETE here), so every route this module backs is a GET.
# ---------------------------------------------------------------------------

_EVENT_COLUMNS = (
    "id, created_at, event_type, object_type, object_id, "
    "project, actor, api_key_id, source, payload"
)


async def list_events(
    session: AsyncSession,
    *,
    object_type: str | None = None,
    object_id: uuid.UUID | None = None,
    project: str | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Filtered, paginated event list — newest first.

    Every predicate lands in the SQL WHERE clause (never a post-fetch Python
    filter), so `project` isolation and the other filters ride the same
    query the partition-pruning and `ix_events_object` planner sees.
    """
    where_parts: list[str] = []
    params: dict = {"limit": limit, "offset": offset}
    if object_type:
        where_parts.append("object_type = :object_type")
        params["object_type"] = object_type
    if object_id is not None:
        where_parts.append("object_id = CAST(:object_id AS uuid)")
        params["object_id"] = str(object_id)
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    if event_type:
        where_parts.append("event_type = :event_type")
        params["event_type"] = event_type
    if since is not None:
        where_parts.append("created_at >= :since")
        params["since"] = since
    if until is not None:
        where_parts.append("created_at <= :until")
        params["until"] = until
    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

    items_sql = (
        f"SELECT {_EVENT_COLUMNS} FROM events "
        f"WHERE {where_sql} "
        "ORDER BY created_at DESC, id DESC "
        "LIMIT :limit OFFSET :offset"
    )
    result = await session.execute(text(items_sql), params)
    items = [dict(row) for row in result.mappings().all()]

    count_sql = f"SELECT COUNT(*) FROM events WHERE {where_sql}"
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()

    return items, int(total)


async def calendar_counts(
    session: AsyncSession,
    *,
    project: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    event_type: str | None = None,
    object_type: str | None = None,
) -> list[dict]:
    """Per-UTC-day event counts for the contribution heatmap.

    ``event_type`` narrows the same buckets to one kind, which is how a
    caller asks "which days hold an inject" (T3.20) without fetching the days'
    rows and counting them itself — a client-side count would silently
    under-report the moment the page bound truncated. ``object_type`` narrows
    further, since one event type can span kinds — ``created`` is journalled
    for memories and for synthesised articles alike.

    The GROUP BY expression is `(created_at AT TIME ZONE 'UTC')::date`,
    byte-for-byte the `ix_events_day` index expression — a bare
    `created_at::date` would still group correctly today but would silently
    change which day a row belongs to under a non-UTC session `TimeZone` GUC,
    since that cast is only STABLE (doc 04 §8.1).
    """
    where_parts: list[str] = []
    params: dict = {}
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    if since is not None:
        where_parts.append("created_at >= :since")
        params["since"] = since
    if until is not None:
        where_parts.append("created_at <= :until")
        params["until"] = until
    if event_type:
        where_parts.append("event_type = :event_type")
        params["event_type"] = event_type
    if object_type:
        where_parts.append("object_type = :object_type")
        params["object_type"] = object_type
    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"

    sql = (
        "SELECT (created_at AT TIME ZONE 'UTC')::date AS day, COUNT(*) AS count "
        "FROM events "
        f"WHERE {where_sql} "
        "GROUP BY (created_at AT TIME ZONE 'UTC')::date "
        "ORDER BY day"
    )
    result = await session.execute(text(sql), params)
    return [{"day": row["day"], "count": int(row["count"])} for row in result.mappings().all()]


async def object_timeline(
    session: AsyncSession,
    *,
    object_type: str,
    object_id: uuid.UUID,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
    newest_first: bool = False,
) -> tuple[list[dict], int]:
    """One object's history, `limit`+`offset` bounded.

    `object_type = ... AND object_id = ...` are the two leading columns of
    `ix_events_object`; both orderings below sort by the index's own
    `created_at` column (ascending or the same index scanned backward), so
    the planner needs no extra sort either way.

    Default is oldest-to-newest, the shape `GET /events/timeline` pages
    forward through with `offset` — flipping that default would change what
    every existing offset means for that door. `newest_first=True` orders
    `created_at DESC, id DESC` instead, for a caller that wants the most
    recent slice of a capped, unpaginated history (the fact detail ladder,
    T2.86 fix round) without disturbing the ascending contract above — the
    returned slice is in descending order and it is the caller's job to
    reverse it if a chronological display is wanted.

    Accepted limitation (doc 04 §8.1): bigint-keyed code-graph objects carry
    their key in `payload`, not `object_id`, so their timelines are not
    reachable through this index-backed shape.
    """
    where_parts = ["object_type = :object_type", "object_id = CAST(:object_id AS uuid)"]
    params: dict = {
        "object_type": object_type,
        "object_id": str(object_id),
        "limit": limit,
        "offset": offset,
    }
    if project:
        where_parts.append("project = :project")
        params["project"] = project
    where_sql = " AND ".join(where_parts)

    order_dir = "DESC" if newest_first else "ASC"
    items_sql = (
        f"SELECT {_EVENT_COLUMNS} FROM events "
        f"WHERE {where_sql} "
        f"ORDER BY created_at {order_dir}, id {order_dir} "
        "LIMIT :limit OFFSET :offset"
    )
    result = await session.execute(text(items_sql), params)
    items = [dict(row) for row in result.mappings().all()]

    count_sql = f"SELECT COUNT(*) FROM events WHERE {where_sql}"
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await session.execute(text(count_sql), count_params)).scalar_one()

    return items, int(total)
