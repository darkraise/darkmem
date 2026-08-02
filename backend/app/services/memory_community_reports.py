"""Tier-C community `report_string` generation (doc 06 §7, doc 11 §6/§9) — T2.19.

**Scope, narrowed from the task text.** T2.18 already writes the deterministic
label (`memory_community_labels.py`) from dominant entities — doc 06 §7 puts
`label = dominant entities` inside the *Insert* box and requires each
detection run to journal referencing its communities by label, which is
impossible unless detection labels. So the task's first Done-when clause
("labels derive deterministically") is satisfied upstream; nothing here
recomputes a label, and T2.18's fix for the four-entity widened label's
provenance payload (`3e21aa1`, `LABEL_WIDENED_ENTITY_COUNT` sliced into
`dominant_entities` too) is untouched and still holds — this module only
reads `properties["dominant_entities"]`, never regenerates it. This module
owns exactly the `report_string` half of §7's Report box: one LLM call per
community, off the hot path.

**Which purpose, and on whose authority.** Doc 11 §6's purpose→consumer
matrix and §9's open-question ruling are explicit: community/topic reports
"reuse `summarization`" because the task shape and token budget match a
short code summary, not a long Layer-3 article (`synthesis`, still inert
behind T3.02) or an NLI verdict (`verification`). `summarization` is one of
the six *live* purposes (`app/services/config.py`'s `PURPOSES`,
`llm_seed.py`'s `DEFAULT_PURPOSE_CONFIGS`), already dispatched by
`wiki_generator.py` and `enrichment_worker.py` — this is reusing a live
purpose, not activating an inert one.

**Three-state rendering, not two.** A community's report state is a pure
function of stored columns (`report_status` below), because `report_string
IS NULL` alone cannot distinguish "not generated yet" from "generation
failed" from "will never be generated":

- **ready** — `report_string` is set.
- **skipped** — too small to be worth an LLM call
  (`properties["size"] < min_report_size`); this community will never get a
  report and `generate_reports` never attempts one. Distinct from *pending*
  so a browsing surface (T2.20) does not show a perpetual spinner for a
  topic that will never resolve one.
- **failed** — an attempt ran and raised; the error lands in
  `properties["report_error"]`. Retried next cycle rather than stuck
  forever: `detect_for_project`'s delete-and-rewrite replaces `properties`
  wholesale (T2.18's), so a failed community's next run is a fresh attempt,
  not a resurrected failure.
- **pending** — everything else: eligible, not yet attempted.

**Surviving the id churn.** `detect_for_project` deletes and rewrites a
project's communities every run (doc 06 §7: "ids churn on every run"), so a
`report_string` written against the old row id is gone the moment the next
run commits. `get_by_label` is what T2.18 left for carrying a report
forward: call `snapshot_reports` *before* the rewrite to capture
`label -> report_string` for every currently-ready community, run
detection, then `restore_reports` *after* the rewrite to re-attach a
carried report to whichever new row now holds that label, via `get_by_label`
— the documented seam (T2.18's plan §7.1), not a bulk re-derivation. A
community whose label did not survive the rewrite starts `pending` (or
`skipped`) again, same as a brand-new topic. Only *ready* reports carry
forward: a `failed` mark never does, so a transient vendor error is retried
on the very next run instead of sticking forever.

**Never on a read path (invariant 15).** Nothing here is imported from
`app/api/*`, `app/services/pipeline.py`, `app/services/memory.py`, or any
other capture/retrieval module. `tests/test_community_reports.py` proves
this the same way T2.18 proved it for the detector: an AST walk over every
file under `app/`, not a grep, because a line-based scan misses a
parenthesised multi-line import (the hole `tests/test_dream_jobs.py`'s
family scan still has — T2.67's to fix, not relied on here).
`generate_reports` and `restore_reports` both take a `session_factory` and
open their own sessions per community, exactly like `_make_lift_runner` /
`_make_recompute_runner` in `dream_jobs.py`: there is no code path from a
request handler into this module, only from a future Tier-C job body.

**The seam T2.53 inherits.** `topic_detection`'s eventual real runner is
expected to sequence, per project: `snapshot_reports` (read, pre-rewrite)
-> `memory_community_detection.detect_for_project` (T2.18's,
delete-and-rewrite) -> `restore_reports` (carry forward matching labels) ->
`generate_reports` (LLM calls for whatever is still `pending`). This module
never calls `detect_for_project` itself and registers no job and no cron;
T2.53 owns the schedule, and the sequence above is the contract it is
handed. T2.20 inherits `report_status` as the read-time projection its
browsing surface renders from, rather than re-deriving the three-state
classification against `report_string IS NULL` directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_communities import (
    CommunityRow,
    get_by_label,
    list_with_members,
    set_report,
)
from app.services.events import record_event

logger = logging.getLogger(__name__)

REPORT_STATUS_READY = "ready"
REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_FAILED = "failed"
REPORT_STATUS_SKIPPED = "skipped"

# Below this many members, an LLM-written report mostly restates the one or
# two notes involved; the community is still a valid topic for browsing, it
# just never gets a generated report.
DEFAULT_MIN_REPORT_SIZE = 3
DEFAULT_MAX_MEMORIES_IN_PROMPT = 8
DEFAULT_CONTENT_CHARS = 240

REPORT_PURPOSE = "summarization"
EVENT_TYPE = "consolidated"
OBJECT_TYPE = "topic"

SYSTEM_PROMPT = (
    "You write a short, factual summary of one topic cluster from a "
    "personal knowledge base. You are given the topic's label, its "
    "dominant entities, and a sample of its member notes. In 2-4 "
    "sentences, describe what this topic covers. Use only what the notes "
    "show; never invent facts, dates, or relationships not present in them."
)

_MEMORY_CONTENT = text(
    "SELECT id, content FROM memories "
    "WHERE id = ANY(CAST(:ids AS uuid[])) "
    "ORDER BY id"
)


def report_status(
    row: CommunityRow, *, min_report_size: int = DEFAULT_MIN_REPORT_SIZE
) -> str:
    """The three-state (four-value) classification `generate_reports` and
    T2.20's browsing surface both read from — never re-derive this against
    `report_string IS NULL` at a call site, or the pending/skipped/failed
    distinction will drift out of sync across consumers."""
    if row.report_string:
        return REPORT_STATUS_READY
    if row.properties.get("report_error"):
        return REPORT_STATUS_FAILED
    size = row.properties.get("size")
    if size is None:
        size = len(row.memory_ids)
    if size < min_report_size:
        return REPORT_STATUS_SKIPPED
    return REPORT_STATUS_PENDING


async def snapshot_reports(session: AsyncSession, project: str) -> dict[str, str]:
    """Capture every currently-ready report's `label -> report_string`,
    called before `detect_for_project` deletes the rows carrying them."""
    rows = await list_with_members(session, project)
    return {row.label: row.report_string for row in rows if row.report_string and row.label}


@dataclass
class RestoreOutcome:
    carried_forward: int = 0


async def restore_reports(
    session: AsyncSession, project: str, snapshot: dict[str, str]
) -> RestoreOutcome:
    """Re-attach a carried-forward report to whichever new row now holds a
    snapshotted label, via `get_by_label` — T2.18's documented seam for
    surviving the nightly id churn. A label that no longer exists (the topic
    merged, split, or dissolved) or whose new row already has a report
    (should not happen immediately after a rewrite, but is checked rather
    than assumed) is simply skipped."""
    carried = 0
    for label, report_string in snapshot.items():
        row = await get_by_label(session, project, label)
        if row is None or row.report_string is not None:
            continue
        await set_report(session, row.id, report_string=report_string)
        carried += 1
    return RestoreOutcome(carried_forward=carried)


async def _sample_content(
    session: AsyncSession, memory_ids: tuple[UUID, ...], limit: int
) -> list[str]:
    ids = list(memory_ids[:limit])
    if not ids:
        return []
    result = await session.execute(_MEMORY_CONTENT, {"ids": [str(i) for i in ids]})
    return [row[1] for row in result]


def _build_messages(row: CommunityRow, contents: list[str], content_chars: int) -> list[dict]:
    dominant = row.properties.get("dominant_entities") or []
    entity_names = ", ".join(
        e.get("display_name") or e.get("name", "") for e in dominant
    ) or row.label
    excerpts = "\n".join(f"- {c[:content_chars]}" for c in contents) or "(no excerpts available)"
    user_prompt = (
        f"Topic label: {row.label}\n"
        f"Dominant entities: {entity_names}\n"
        f"Member notes ({len(contents)} of {len(row.memory_ids)} total):\n"
        f"{excerpts}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


async def generate_report(
    session: AsyncSession,
    llm,
    row: CommunityRow,
    *,
    max_memories: int = DEFAULT_MAX_MEMORIES_IN_PROMPT,
    content_chars: int = DEFAULT_CONTENT_CHARS,
) -> str:
    """One `summarization`-purpose call producing a community's report text.
    Raises on any orchestrator failure; the caller decides how to record it —
    this function never swallows an error into a placeholder string."""
    contents = await _sample_content(session, row.memory_ids, max_memories)
    messages = _build_messages(row, contents, content_chars)
    return await llm.chat_completion(REPORT_PURPOSE, messages=messages)


@dataclass
class GenerateOutcome:
    attempted: int = 0
    generated: int = 0
    failed: int = 0
    labels_failed: list[str] = field(default_factory=list)


async def generate_reports(
    session_factory,
    llm,
    project: str,
    *,
    min_report_size: int = DEFAULT_MIN_REPORT_SIZE,
    max_memories: int = DEFAULT_MAX_MEMORIES_IN_PROMPT,
) -> GenerateOutcome:
    """Fill in `report_string` for every `pending` community in `project`.

    Structurally off the hot path: this function opens its own short-lived
    session per community rather than holding one across the whole batch or
    across any LLM call, and it is never imported by a capture or retrieval
    module (`tests/test_community_reports.py`'s AST scan). One community's
    LLM failure cannot roll back another's success, because each gets its
    own session and its own commit.
    """
    async with session_factory() as session:
        rows = await list_with_members(session, project)

    outcome = GenerateOutcome()
    for row in rows:
        if report_status(row, min_report_size=min_report_size) != REPORT_STATUS_PENDING:
            continue
        outcome.attempted += 1
        async with session_factory() as session:
            try:
                report_text = await generate_report(
                    session, llm, row, max_memories=max_memories
                )
            except Exception as exc:
                logger.warning(
                    "Community report failed for %r label %r: %s",
                    project, row.label, exc,
                )
                await set_report(
                    session, row.id,
                    properties_patch={"report_error": str(exc)[:500]},
                )
                await record_event(
                    session, event_type=EVENT_TYPE, object_type=OBJECT_TYPE,
                    object_id=None, project=project,
                    payload={"label": row.label, "status": REPORT_STATUS_FAILED},
                )
                await session.commit()
                outcome.failed += 1
                outcome.labels_failed.append(row.label)
                continue

            await set_report(session, row.id, report_string=report_text)
            await record_event(
                session, event_type=EVENT_TYPE, object_type=OBJECT_TYPE,
                object_id=None, project=project,
                payload={"label": row.label, "status": REPORT_STATUS_READY},
            )
            await session.commit()
            outcome.generated += 1

    return outcome
