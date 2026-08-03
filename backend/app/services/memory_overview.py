"""The `memory_overview` global map-reduce (doc 09 §3.3, doc 12 §3) — T2.21.

**The shape, and why it is not a search.** Doc 09 §3.3 fixes `memory_overview`
as a project-scoped map-reduce over doc 06's durable `memory_communities`
rows: the *map* is each community's precomputed `report_string`, the *reduce*
is **one** bounded `summarization` call that stitches those per-community
reports into a single project overview. It is deliberately a separate tool
rather than a mode of `memory_search`, because "what does this project's
memory contain" is a different question from "what is most relevant to this
query", and conflating the global map-reduce with per-memory RRF is the exact
error doc 04 §8.4 forbids.

**Cost is bounded by community count, not memory count — and that is
measured, not asserted.** The map step spends nothing: the reports already
exist, written off the hot path by T2.19's generator at detection time, so
this module never fans out an LLM call per community and never generates a
missing report on read (doc 09 §3.3; a `pending` community is *counted* on
the response, never quietly filled in). The only model call is the single
reduce, and its input is built from at most `MAX_REPORTS_IN_REDUCE` reports,
each truncated to `MAX_REPORT_CHARS` with a `MAX_LABEL_CHARS` label — so
`reduce_input_bound(reports_used)` is a closed function of the *number of
communities*, and no memory's content ever reaches the prompt. Adding ten
thousand memories to an existing topic set changes neither the call count nor
the prompt budget. `tests/test_memory_overview.py` grows memories without
growing communities and asserts exactly that, because a claim about cost that
nobody measured is a design intention wearing a measurement's clothes.

**One call, and a stated bound — never a second silent call.** When the ready
reports exceed the budget, the excess is *dropped and declared*
(`reports_omitted`, `omitted_labels`) rather than folded in by a second
round-trip. A hierarchical reduce would make the cost O(communities) in model
calls again, and an undeclared drop would make the overview quietly partial —
invariant 14: if you drop reports to fit, say how many.

**Cached against the community-set hash (doc 04 §7, doc 09 §3.3).** The cache
is one `config` row `overview:<project>` holding `{community_set_hash, text,
...}` — not a new table. The hash covers every community's label, member
count and report text, so the cached overview is invalidated by exactly the
event that changes what the overview says: doc 06's delete-and-rewrite
detection run. Between runs the community set is immutable (nothing but the
detector writes those rows), so a repeated overview request is a `config`-row
read and zero model calls.

**No verification badge, ever.** The reduce is a summary of summaries — a
*report*, not a grounded article — so it reuses `summarization` rather than
the truth-critical `synthesis` purpose (doc 11 §6), and its output is an
*organizational* view of what memory contains, explicitly labelled
`OVERVIEW_KIND` and carrying no badge field for a consumer to mistake for a
verified claim (doc 12 §3's tool table: "no badge").

**Reaching T2.19's module.** Only `report_status` and its status constants are
imported from `memory_community_reports` — the symbol-precise exemption
`tests/test_community_reports.py` grants for exactly this shape. Importing
`generate_report`/`generate_reports` here would put LLM report generation on a
read door, which is what invariant 15 and that scan forbid; the three-state
projection is a pure function of stored columns and is the documented way for
a reader to avoid re-deriving `report_string IS NULL` itself.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.memory_communities import CommunityRow, list_with_members
from app.services.memory_community_reports import (
    REPORT_STATUS_READY,
    report_status,
)

logger = logging.getLogger(__name__)

OVERVIEW_CONFIG_PREFIX = "overview:"
REDUCE_PURPOSE = "summarization"

# The overview is an organizational view of what memory contains, never a
# verified claim. Doc 12 §3's tool table gives it no badge column; this label
# is what a consumer reads instead of looking for one.
OVERVIEW_KIND = "organizational"

# The three numbers that make the bound a function of community count alone.
# Every one of them is enforced by construction in `_build_messages`, so
# `reduce_input_bound` is an upper bound rather than an aspiration.
MAX_REPORTS_IN_REDUCE = 40
MAX_REPORT_CHARS = 600
MAX_LABEL_CHARS = 120

# "- <label> (<n> memories)\n" plus the blank line between topics, with room
# for a member count of any plausible magnitude.
PER_TOPIC_OVERHEAD_CHARS = 48

SYSTEM_PROMPT = (
    "You write a short organizational overview of one project's personal "
    "knowledge base. You are given a list of its topics, each with a "
    "member count and a precomputed summary of that topic. Stitch them into "
    "a single overview of 4-8 sentences that says what this project's "
    "memory covers and how the topics relate. Use only the summaries given; "
    "never invent topics, facts or numbers. This is an organizational "
    "description of what is stored, not a verified claim about the world."
)

_HEADER_CHARS = 256


def reduce_input_bound(reports_used: int) -> int:
    """The largest prompt `_build_messages` can produce for `reports_used`
    topics. A closed function of the community count: nothing in it varies
    with how many memories those communities hold."""
    return (
        len(SYSTEM_PROMPT)
        + _HEADER_CHARS
        + reports_used * (MAX_LABEL_CHARS + MAX_REPORT_CHARS + PER_TOPIC_OVERHEAD_CHARS)
    )


class OverviewUnavailable(RuntimeError):
    """The reduce is needed and no model is configured to run it.

    Distinct from an empty project: there, the honest answer is that no topic
    carries a report yet, and it costs nothing to say so.
    """


@dataclass(frozen=True)
class TopicSection:
    """One community as the overview presents it — the map's unit.

    Carries `project` so the row is self-describing on the wire even though
    the door is project-scoped (`content_surfaces.py`'s labelling rule).
    """

    project: str
    label: str
    member_count: int
    report_status: str
    report: str | None
    used_in_reduce: bool


@dataclass(frozen=True)
class OverviewResult:
    project: str
    kind: str
    text: str | None
    community_set_hash: str
    generated_at: str
    cached: bool
    model_calls: int
    communities_total: int
    reports_ready: int
    reports_used: int
    reports_omitted: int
    omitted_labels: tuple[str, ...]
    reports_truncated: int
    reduce_input_chars: int
    reduce_input_bound: int
    topics: tuple[TopicSection, ...]

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "kind": self.kind,
            "text": self.text,
            "community_set_hash": self.community_set_hash,
            "generated_at": self.generated_at,
            "cached": self.cached,
            "model_calls": self.model_calls,
            "communities_total": self.communities_total,
            "reports_ready": self.reports_ready,
            "reports_used": self.reports_used,
            "reports_omitted": self.reports_omitted,
            "omitted_labels": list(self.omitted_labels),
            "reports_truncated": self.reports_truncated,
            "reduce_input_chars": self.reduce_input_chars,
            "reduce_input_bound": self.reduce_input_bound,
            "topics": [
                {
                    "project": t.project,
                    "label": t.label,
                    "member_count": t.member_count,
                    "report_status": t.report_status,
                    "report": t.report,
                    "used_in_reduce": t.used_in_reduce,
                }
                for t in self.topics
            ],
        }


def config_key(project: str) -> str:
    return f"{OVERVIEW_CONFIG_PREFIX}{project}"


def community_set_hash(rows: list[CommunityRow]) -> str:
    """Identity of the *community set*, which is what the overview describes.

    Deliberately not the community ids: those churn on every detection run
    (doc 04 §8.4) and would invalidate the cache on every rewrite even when
    the topics came back identical. Label, member count and report text are
    what the reduce actually reads, so a hash over them changes exactly when
    the overview's answer would.
    """
    digest = hashlib.sha256()
    for label, size, report in sorted(
        (row.label or "", len(row.memory_ids), row.report_string or "")
        for row in rows
    ):
        digest.update(label.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\x00")
        digest.update(hashlib.sha256(report.encode("utf-8")).digest())
        digest.update(b"\x00")
    return digest.hexdigest()


def _select_reports(
    rows: list[CommunityRow], max_reports: int
) -> tuple[list[CommunityRow], list[CommunityRow]]:
    """The ready reports the reduce reads, and the ones dropped to fit.

    Largest topics first so a truncated overview describes the project's bulk
    rather than an arbitrary slice, with the label as a deterministic
    tie-break: two runs over the same community set must select the same
    reports or the cache hash would promise a stability the selection does
    not have.
    """
    ready = [row for row in rows if report_status(row) == REPORT_STATUS_READY]
    ready.sort(key=lambda row: (-len(row.memory_ids), row.label or ""))
    return ready[:max_reports], ready[max_reports:]


def _build_messages(
    project: str, used: list[CommunityRow]
) -> tuple[list[dict], int]:
    """The single reduce prompt, with every unbounded field clipped.

    The label and report clips are what make `reduce_input_bound` true; the
    absence of any memory content is what makes the bound a function of
    community count rather than corpus size.
    """
    truncated = 0
    lines = []
    for row in used:
        report = row.report_string or ""
        if len(report) > MAX_REPORT_CHARS:
            report = report[:MAX_REPORT_CHARS]
            truncated += 1
        label = (row.label or "")[:MAX_LABEL_CHARS]
        lines.append(f"- {label} ({len(row.memory_ids)} memories)\n  {report}")
    user_prompt = (
        f"Project: {project[:MAX_LABEL_CHARS]}\n"
        f"Topics ({len(used)}):\n" + "\n".join(lines)
    )
    return (
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        truncated,
    )


def _messages_chars(messages: list[dict]) -> int:
    return sum(len(m["content"]) for m in messages)


async def _read_cache(session: AsyncSession, project: str) -> dict | None:
    row = (
        await session.execute(
            select(Config).where(Config.key == config_key(project))
        )
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return None
    return row.value


async def _write_cache(session: AsyncSession, project: str, value: dict) -> None:
    row = (
        await session.execute(
            select(Config).where(Config.key == config_key(project))
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key=config_key(project), value=value))
    else:
        row.value = value
    await session.flush()


def _topics(rows: list[CommunityRow], used_ids: set) -> tuple[TopicSection, ...]:
    sections = []
    for row in rows:
        status = report_status(row)
        sections.append(
            TopicSection(
                project=row.project,
                label=row.label or "",
                member_count=len(row.memory_ids),
                report_status=status,
                report=row.report_string if status == REPORT_STATUS_READY else None,
                used_in_reduce=row.id in used_ids,
            )
        )
    sections.sort(key=lambda t: (-t.member_count, t.label))
    return tuple(sections)


async def get_overview(
    session: AsyncSession,
    llm,
    project: str,
    *,
    max_reports: int = MAX_REPORTS_IN_REDUCE,
) -> OverviewResult:
    """The whole tool, both doors' single implementation (invariant 17).

    Reads the project's communities once, serves the cached reduce when the
    community set is unchanged, and otherwise spends exactly one
    `summarization` call. Never writes a `report_string` and never asks for
    one to be generated: a community without a report is reported as such.
    """
    rows = await list_with_members(session, project)
    set_hash = community_set_hash(rows)
    used, omitted = _select_reports(rows, max_reports)
    used_ids = {row.id for row in used}
    messages, truncated = _build_messages(project, used)
    input_chars = _messages_chars(messages) if used else 0
    bound = reduce_input_bound(len(used))
    topics = _topics(rows, used_ids)

    common = {
        "project": project,
        "kind": OVERVIEW_KIND,
        "community_set_hash": set_hash,
        "communities_total": len(rows),
        "reports_ready": len(used) + len(omitted),
        "reports_used": len(used),
        "reports_omitted": len(omitted),
        "omitted_labels": tuple(row.label or "" for row in omitted),
        "reports_truncated": truncated,
        "reduce_input_chars": input_chars,
        "reduce_input_bound": bound,
        "topics": topics,
    }

    if not used:
        return OverviewResult(
            text=None,
            generated_at=_now(),
            cached=False,
            model_calls=0,
            **common,
        )

    cached = await _read_cache(session, project)
    if cached is not None and cached.get("community_set_hash") == set_hash:
        return OverviewResult(
            text=cached.get("text"),
            generated_at=cached.get("generated_at") or _now(),
            cached=True,
            model_calls=0,
            **common,
        )

    if llm is None:
        raise OverviewUnavailable(
            "the overview reduce needs the summarization purpose and no LLM "
            "is configured"
        )

    text = await llm.chat_completion(REDUCE_PURPOSE, messages=messages)
    generated_at = _now()
    await _write_cache(
        session,
        project,
        {
            "community_set_hash": set_hash,
            "text": text,
            "generated_at": generated_at,
            "reports_used": len(used),
            "reports_omitted": len(omitted),
            "omitted_labels": list(common["omitted_labels"]),
            "reports_truncated": truncated,
            "reduce_input_chars": input_chars,
        },
    )
    return OverviewResult(
        text=text,
        generated_at=generated_at,
        cached=False,
        model_calls=1,
        **common,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
