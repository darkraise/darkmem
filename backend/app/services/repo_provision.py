"""The repository-hint auto-provision handoff (doc 05 §2.4).

Capture owns *validate and enqueue* and nothing beyond it. When a captured
memory carries a repository hint the project does not yet track, Tier A
checks the hint against doc 18 §6's allowlist gate, upserts the shared
`repositories` row plus its `project_repositories` association, and stops.
The clone, the pull and the first index all run in Tier C — the
`repo_sync` job drains repositories with `fetch_enabled` or
`index_on_commit_enabled` armed at the standard cadence (doc 10 §5), which
is what makes the auto-provisioned row a queue entry rather than work.
**Capture never clones**: nothing in this module issues a
network request, resolves a name, or invokes git.

A rejected hint is refused visibly and never fatally (doc 18 §6 rule 4).
The memory is the caller's content and is worth keeping independently of a
provisioning convenience that happened to look hostile, so the refusal
journals a `repo_hint_rejected` event and the capture completes normally.
The same posture covers an unexpected failure anywhere in here: the handoff
runs inside its own savepoint and swallows its own errors, because a
secondary concern must degrade loudly without taking the primary action
down with it.

The remote written to `repositories.url` is the gate's **reconstructed**
URL, never the caller's raw string — the value that eventually reaches a
git argv is one this codebase rebuilt from validated parts.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import Repository
from app.services.events import record_event
from app.services.repo_allowlist import HintVerdict, evaluate_hint, load_allowlist

logger = logging.getLogger(__name__)

# The one metadata key a repository hint rides (doc 04 §8.7: the hint uses the
# existing `memories.metadata_` jsonb, no new column).
REPO_HINT_KEY = "repo_hint"

ADDED_FROM_MEMORY_HINT = "memory_hint"

# Tier C has not picked the row up yet. `repo_sync` filters on
# `fetch_enabled` / `index_on_commit_enabled`, not on status, so this is a
# label for the operator rather than a predicate.
PROVISION_QUEUED_STATUS = "queued"

_UPSERT_ASSOCIATION = text(
    "INSERT INTO project_repositories (project, repo_id, added_from) "
    "VALUES (:project, CAST(:repo_id AS uuid), :added_from) "
    "ON CONFLICT (project, repo_id) DO NOTHING"
)

_SELECT_ASSOCIATION = text(
    "SELECT opt_out FROM project_repositories "
    "WHERE project = :project AND repo_id = CAST(:repo_id AS uuid)"
)


def extract_hint(metadata: object) -> str | None:
    """The caller-supplied repository hint, if this capture carries one."""
    if not isinstance(metadata, dict):
        return None
    hint = metadata.get(REPO_HINT_KEY)
    return hint if isinstance(hint, str) and hint.strip() else None


def _repo_name(verdict: HintVerdict) -> str:
    tail = verdict.path.rsplit("/", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[: -len(".git")]
    return (tail or verdict.host)[:255]


async def _resolve_repository(session: AsyncSession, verdict: HintVerdict) -> Repository:
    """The shared `Repository` for this remote — one row per remote, so two
    projects naming the same repo own the same code graph rather than private
    copies (doc 04 §8.7)."""
    existing = (
        await session.execute(select(Repository).where(Repository.url == verdict.remote))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    repo = Repository(
        id=uuid.uuid4(),
        name=_repo_name(verdict),
        url=verdict.remote,
        provider="git",
        default_branch="main",
        # Auto-provisioned from a capture hint with no operator review, so
        # both lanes are armed: the repo is fetched and indexed at the
        # standard cadence with no further action needed.
        fetch_enabled=True,
        index_on_commit_enabled=True,
        status=PROVISION_QUEUED_STATUS,
        status_message="Queued for auto-provision indexing",
    )
    session.add(repo)
    await session.flush()
    return repo


async def _provision(
    session: AsyncSession,
    *,
    verdict: HintVerdict,
    memory_id: uuid.UUID,
    project: str,
    source: str | None,
) -> None:
    repo = await _resolve_repository(session, verdict)
    params = {"project": project, "repo_id": str(repo.id)}
    opt_out = (await session.execute(_SELECT_ASSOCIATION, params)).scalar_one_or_none()
    if opt_out:
        logger.info(
            "repo hint %s skipped: project %s has opted out of auto-provision",
            verdict.remote, project,
        )
        return

    await session.execute(
        _UPSERT_ASSOCIATION, {**params, "added_from": ADDED_FROM_MEMORY_HINT}
    )
    await record_event(
        session,
        event_type="repo_registered",
        object_type="repository",
        object_id=repo.id,
        project=project,
        source=source,
        payload={
            "remote": verdict.remote,
            "added_from": ADDED_FROM_MEMORY_HINT,
            "memory_id": str(memory_id),
            "queued_for": "tier_c",
        },
    )


async def handoff_capture_hint(
    session: AsyncSession,
    *,
    metadata: object,
    memory_id: uuid.UUID,
    project: str,
    source: str | None = None,
    patterns: object = None,
) -> HintVerdict | None:
    """Validate this capture's repository hint and queue Tier C past it.

    Returns the gate's verdict — the decision, not the provisioning outcome —
    or `None` when the capture carried no hint. Never raises: the caller is a
    capture, and a capture must not fail over a provisioning convenience.
    """
    raw = extract_hint(metadata)
    if raw is None:
        return None

    try:
        if patterns is None:
            patterns = await load_allowlist(session)
        verdict = evaluate_hint(raw, patterns)
    except Exception:
        logger.error("repo hint gate failed for memory %s", memory_id, exc_info=True)
        return None

    try:
        async with session.begin_nested():
            if verdict.allowed:
                await _provision(
                    session, verdict=verdict, memory_id=memory_id,
                    project=project, source=source,
                )
            else:
                logger.warning(
                    "repo hint refused (%s) for memory %s", verdict.reason, memory_id,
                )
                await record_event(
                    session,
                    event_type="repo_hint_rejected",
                    object_type="repository",
                    project=project,
                    source=source,
                    payload={
                        "hint": raw[:512],
                        "reason": verdict.reason,
                        "verdict": "matched_nothing",
                        "memory_id": str(memory_id),
                    },
                )
    except Exception:
        logger.error(
            "repo hint handoff failed for memory %s; capture continues",
            memory_id, exc_info=True,
        )
    return verdict
