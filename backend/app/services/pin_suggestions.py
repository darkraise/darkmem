"""Pin suggestions — diffing communities across runs (doc 09 §3.4) — T2.20.

**What this module is not.** It never calls
`memory_community_detection.detect_for_project` (detection is T2.18's, Tier
C, invariant 15) and it never schedules anything (T2.53's). It is a pure
read/derive surface, exactly like `topic_browsing.py` and
`memory_community_reports.py`'s `report_status`: given the durable rows a run
already produced, compute what changed and what a human should be asked
about.

**Reusing T2.19's churn-survival mechanism, not minting a second one.**
`memory_communities` is delete-and-rewritten per project on every detection
run (doc 06 §7), so "diff run N against run N+1" cannot mean "read two
persisted snapshots" — there is only ever one live copy. `snapshot_reports`
solved exactly this for report text by reading the *current* (soon to be
overwritten) rows immediately before the rewrite. `snapshot_topics` below is
the same pattern applied to community shape: read `label -> (member_count,
dominant subject)` before `detect_for_project` deletes the row, then diff
that snapshot against `list_with_members`'s result after the rewrite. No new
durable "prior run" table is needed or added.

**The substantive design question: what happens when a label splits, merges,
or disappears between runs.** A community's `label` is a deterministic join
of its top dominant entities (`memory_community_labels.py`); it is *not* a
persistent identity a community carries across runs, so label churn under
split/merge is expected, not a bug to route around. This module resolves it
by keeping two identities that behave differently:

- **The label diff** (`diff_topics`) classifies at the label level, purely by
  string match against the pre-rewrite snapshot: a label absent from the
  snapshot is `new`, a label present with a member count grown by at least
  `growth_threshold` is `grown`, present and not grown is `stable`, and a
  snapshot label absent from the new set is `decayed`. This is honest about
  what a label *is* — nothing tracks "this new label used to be that old
  one," because nothing about a joined dominant-entity string can prove that
  claim.
- **The suggestion gate** (`compute_pin_suggestions`) operates one level
  down, on the community's single most-dominant entity's soft key
  `(name_lower, entity_type)` — not the label, and not the community id.
  This is what makes split and merge safe rather than merely tolerated:
  - **Split.** A community "postgres, backups" (label) splits into
    "postgres, replication" and "backups, retention" next run. The label
    diff reports the parent `decayed` and both children `new`. But if
    `postgres` was already pinned or dismissed under the parent label, the
    child community whose dominant entity is still `postgres` is suppressed
    by the *subject* gate regardless of its new label — the human is not
    asked about the same entity twice just because its label text moved.
  - **Merge.** Two communities collapse into one next run; symmetric to
    split — both parents `decay`, the merged label is `new`, and the
    merged community's dominant entity (whichever ranks highest post-merge)
    carries forward whatever pin/dismiss decision it already had.
  - **Disappear.** A label present in the snapshot has no successor at all
    (its members were superseded, expired, or moved projects out from
    under it). It is reported `decayed` and nothing is suggested for it —
    there is deliberately no persisted "this suggestion is still pending"
    row for a vanished community to leave behind. Suggestions are
    recomputed fresh from current communities plus the durable
    accept/dismiss decisions on every call (see below); a decayed
    community simply stops being a candidate on this diff and every one
    after it, the same as if it had never existed.

**What is durable, and what is deliberately not.** Only the human's decision
persists: `accept_pin_suggestion` / `dismiss_pin_suggestion` write to
`app.repositories.pinned_subjects`, which owns two lists —
`pinned_subjects` / `dismissed_subjects` — inside the `projects.properties`
jsonb (doc 09 §3.4, doc 04 §7; no schema change, an existing column gets a
narrowly-scoped new writer). The *suggestion itself* is never stored as its
own row — recomputing it from current `memory_communities` plus the
persisted decision sets is cheap, and storing a "pending suggestion" table
would need its own churn-survival story on top of the one this diff already
solves. This is why `compute_pin_suggestions` writes nothing and
`journal_pin_suggestions` is a separate, explicit call (see below): the
former is a safe, idempotent read a browsing UI can call on every page load,
the latter is a one-time-per-run journal entry a scheduler should call
exactly once after a detection pass, not on every read.

**Subject key is provisional pending T3.02.** Doc 04 §8.8 / doc 09 §4
describe `knowledge_articles.subject_key` abstractly as a
`(name_lower, entity_type)` soft key but never fix a concrete string
encoding, and nothing in the codebase writes to that column yet
(`article_synthesis` is still a `PlaceholderJobRunner`, T3.02's). This module
picks `f"{name_lower}::{entity_type}"` (`subject_soft_key` below) as that
encoding for its own two purposes — the pinned/dismissed lists, and the
"already a live article subject" gate read against `knowledge_articles`.
Since no writer of that column exists yet, the gate read is inert today
(always no-match) but forward-compatible if T3.02 adopts the same encoding;
if it picks a different one, this function's encoding must move to match —
flagged here rather than left implicit.

**Fact-count and article-subject gates are read-only, not ladder logic.**
Doc 09 §3.4 requires a suggestion's dominant entity to already anchor a
floor of non-disputed corroborated/confirmed facts, and to not already be a
live article subject. Both are plain `SELECT`s against existing
`knowledge_triples` / `knowledge_articles` columns — nothing here writes
`verification_status`, computes salience, or touches the verification
ladder. `verified_fact_count` matches on `subject_name` only (entities are
lowercased on write, invariant 7, and `knowledge_triples` carries no
`entity_type` column of its own — a soft ref, doc 08 §3), a documented
approximation rather than a false precision.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_communities import CommunityRow, list_with_members
from app.repositories.pinned_subjects import (
    DISMISSED_KEY,
    PINNED_KEY,
    append_subject,
    get_subject_lists,
)
from app.services.events import record_event

DEFAULT_GROWTH_THRESHOLD = 2
DEFAULT_FACT_FLOOR = 1

STATUS_NEW = "new"
STATUS_GROWN = "grown"
STATUS_STABLE = "stable"
STATUS_DECAYED = "decayed"

EVENT_TYPE_CONSOLIDATED = "consolidated"
EVENT_TYPE_DECISION = "pin_decision"
OBJECT_TYPE = "topic"

VERDICT_ACCEPTED = "accepted"
VERDICT_DISMISSED = "dismissed"
PIN_VERDICTS = frozenset({VERDICT_ACCEPTED, VERDICT_DISMISSED})

_VERIFIED_STATUSES = ("corroborated", "confirmed")

_FACT_COUNT = text(
    "SELECT COUNT(*) FROM knowledge_triples "
    "WHERE project = CAST(:project AS text) "
    "AND subject_name = CAST(:name_lower AS text) "
    "AND verification_status = ANY(CAST(:statuses AS text[])) "
    "AND expired_at IS NULL"
)

_LIVE_ARTICLE_SUBJECT = text(
    "SELECT 1 FROM knowledge_articles "
    "WHERE project = CAST(:project AS text) "
    "AND subject_key = CAST(:subject_key AS text) "
    "AND status <> 'superseded' LIMIT 1"
)


def subject_soft_key(name_lower: str, entity_type: str) -> str:
    """See the module docstring's "Subject key is provisional" note."""
    return f"{name_lower}::{entity_type}"


def _dominant_entity(row: CommunityRow) -> tuple[str, str] | None:
    dominant = row.properties.get("dominant_entities") or []
    if not dominant:
        return None
    top = dominant[0]
    name = top.get("name")
    entity_type = top.get("type")
    if not name or not entity_type:
        return None
    return (name, entity_type)


@dataclass(frozen=True)
class TopicSnapshot:
    label: str
    member_count: int
    dominant_name: str | None
    dominant_entity_type: str | None


async def snapshot_topics(
    session: AsyncSession, project: str
) -> dict[str, TopicSnapshot]:
    """Capture `label -> (member_count, dominant subject)` for every current
    community, called before `detect_for_project`'s delete-and-rewrite —
    the same seam `memory_community_reports.snapshot_reports` uses."""
    rows = await list_with_members(session, project)
    out: dict[str, TopicSnapshot] = {}
    for row in rows:
        if not row.label:
            continue
        dominant = _dominant_entity(row)
        out[row.label] = TopicSnapshot(
            label=row.label,
            member_count=len(row.memory_ids),
            dominant_name=dominant[0] if dominant else None,
            dominant_entity_type=dominant[1] if dominant else None,
        )
    return out


@dataclass(frozen=True)
class TopicDiffEntry:
    label: str
    status: str
    dominant_name: str | None
    dominant_entity_type: str | None
    member_count: int
    prior_member_count: int | None


def diff_topics(
    prior: dict[str, TopicSnapshot],
    current: Sequence[CommunityRow],
    *,
    growth_threshold: int = DEFAULT_GROWTH_THRESHOLD,
) -> list[TopicDiffEntry]:
    """Classify every label in `current` (post-rewrite) against `prior`
    (pre-rewrite) as new / grown / stable, plus every `prior` label with no
    successor in `current` as decayed. See the module docstring for how
    split/merge/disappear are handled at the subject-gate level, not here."""
    entries: list[TopicDiffEntry] = []
    seen_labels: set[str] = set()

    for row in current:
        if not row.label:
            continue
        seen_labels.add(row.label)
        member_count = len(row.memory_ids)
        dominant = _dominant_entity(row)
        prior_snapshot = prior.get(row.label)

        if prior_snapshot is None:
            status = STATUS_NEW
            prior_count = None
        else:
            prior_count = prior_snapshot.member_count
            status = (
                STATUS_GROWN
                if member_count - prior_count >= growth_threshold
                else STATUS_STABLE
            )

        entries.append(
            TopicDiffEntry(
                label=row.label,
                status=status,
                dominant_name=dominant[0] if dominant else None,
                dominant_entity_type=dominant[1] if dominant else None,
                member_count=member_count,
                prior_member_count=prior_count,
            )
        )

    for label, snapshot in prior.items():
        if label in seen_labels:
            continue
        entries.append(
            TopicDiffEntry(
                label=label,
                status=STATUS_DECAYED,
                dominant_name=snapshot.dominant_name,
                dominant_entity_type=snapshot.dominant_entity_type,
                member_count=0,
                prior_member_count=snapshot.member_count,
            )
        )

    return entries


async def _verified_fact_count(
    session: AsyncSession, project: str, name_lower: str
) -> int:
    result = await session.execute(
        _FACT_COUNT,
        {
            "project": project,
            "name_lower": name_lower,
            "statuses": list(_VERIFIED_STATUSES),
        },
    )
    return int(result.scalar_one())


async def _is_live_article_subject(
    session: AsyncSession, project: str, subject_key: str
) -> bool:
    result = await session.execute(
        _LIVE_ARTICLE_SUBJECT, {"project": project, "subject_key": subject_key}
    )
    return result.first() is not None


@dataclass(frozen=True)
class PinSuggestion:
    subject_key: str
    dominant_name: str
    dominant_entity_type: str
    label: str
    why: str
    member_count: int
    verified_fact_count: int


async def compute_pin_suggestions(
    session: AsyncSession,
    project: str,
    diff_entries: Sequence[TopicDiffEntry],
    *,
    fact_floor: int = DEFAULT_FACT_FLOOR,
) -> list[PinSuggestion]:
    """Nominations only (doc 09 §3.4) — never auto-creates a pinned subject.

    Read-only: no event is journalled here (see `journal_pin_suggestions`),
    so this is safe to call on every browsing read without spamming the
    journal with a row per page view.
    """
    pinned, dismissed = await get_subject_lists(session, project)

    suggestions: list[PinSuggestion] = []
    for entry in diff_entries:
        if entry.status not in (STATUS_NEW, STATUS_GROWN):
            continue
        if not entry.dominant_name or not entry.dominant_entity_type:
            continue

        subject_key = subject_soft_key(entry.dominant_name, entry.dominant_entity_type)
        if subject_key in pinned or subject_key in dismissed:
            continue
        if await _is_live_article_subject(session, project, subject_key):
            continue

        fact_count = await _verified_fact_count(session, project, entry.dominant_name)
        if fact_count < fact_floor:
            continue

        suggestions.append(
            PinSuggestion(
                subject_key=subject_key,
                dominant_name=entry.dominant_name,
                dominant_entity_type=entry.dominant_entity_type,
                label=entry.label,
                why=entry.status,
                member_count=entry.member_count,
                verified_fact_count=fact_count,
            )
        )

    return suggestions


async def journal_pin_suggestions(
    session: AsyncSession, project: str, suggestions: Sequence[PinSuggestion]
) -> None:
    """One `events` row per newly-computed suggestion. A scheduler (T2.53's
    future `topic_detection` body) calls this once per detection run, after
    `compute_pin_suggestions` — never a browsing read, or every page view
    would journal a duplicate row for the same still-pending nomination."""
    for suggestion in suggestions:
        await record_event(
            session,
            event_type=EVENT_TYPE_CONSOLIDATED,
            object_type=OBJECT_TYPE,
            object_id=None,
            project=project,
            payload={
                "action": "pin_suggested",
                "label": suggestion.label,
                "subject_key": suggestion.subject_key,
                "why": suggestion.why,
                "member_count": suggestion.member_count,
                "verified_fact_count": suggestion.verified_fact_count,
            },
        )


async def accept_pin_suggestion(
    session: AsyncSession, project: str, subject_key: str, *, label: str | None = None
) -> None:
    """A human accepts a suggestion: `subject_key` becomes a pinned subject,
    eligible for synthesis (doc 09 §4, T3.02's to consume)."""
    await append_subject(session, project, PINNED_KEY, subject_key)
    await record_event(
        session,
        event_type=EVENT_TYPE_DECISION,
        object_type=OBJECT_TYPE,
        object_id=None,
        project=project,
        payload={"subject_key": subject_key, "label": label, "verdict": VERDICT_ACCEPTED},
    )


async def dismiss_pin_suggestion(
    session: AsyncSession, project: str, subject_key: str, *, label: str | None = None
) -> None:
    """A human dismisses a suggestion: `subject_key` is recorded so the diff
    suppresses it on every later run (doc 09 §3.4) — permanently, until
    something explicitly un-dismisses it, which nothing in this task does."""
    await append_subject(session, project, DISMISSED_KEY, subject_key)
    await record_event(
        session,
        event_type=EVENT_TYPE_DECISION,
        object_type=OBJECT_TYPE,
        object_id=None,
        project=project,
        payload={"subject_key": subject_key, "label": label, "verdict": VERDICT_DISMISSED},
    )
