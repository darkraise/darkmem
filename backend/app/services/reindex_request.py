"""The one entry point both file-scoped reindex doors call (spec §1).

Order is the design: precheck, then canonicalise, then verify HEAD, then claim.
Canonicalisation walks the working tree, which for a repository still cloning
may not exist and which a concurrent claimed run may be mid-rmtree on -- so the
status and existence checks come first, or the door fails inside an ``rglob``
instead of returning the honest ``repo_busy``.

The HEAD check is read-only on purpose. ``pull_repo`` runs ``reset --hard`` on a
clone and can re-clone the directory outright; firing it from this unclaimed
path would reset the tree under a concurrent run's parser. The spawned run does
its own pull under the claim, exactly as it does today. The guarantee this door
can honestly make is therefore "HEAD equalled your sha when the request was
accepted", and nothing stronger.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import Repository
from app.services.events import record_event
from app.services.reindex_files import MAX_UNION_FILES, canonicalise_paths
from app.services.repo_manager import RepoManager

logger = logging.getLogger(__name__)

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

BUSY_STATUSES = ("indexing", "cloning")


class ReindexRefused(Exception):
    """A refusal with the shape both doors render."""

    def __init__(self, status_code: int, reason: str, **detail):
        super().__init__(reason)
        self.status_code = status_code
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ReindexAccepted:
    union_files: list[str]
    commit: str | None
    head: str


async def _journal(
    session: AsyncSession,
    repo_id: UUID | None,
    *,
    outcome: str,
    file_count: int,
    commit: str | None,
    actor: str | None,
    api_key_id: UUID | None,
    source: str,
) -> None:
    """One row per request, written last because it carries the outcome.

    The webhook journals before its lookup and can, because its payload is only
    ``{"keyed": ...}``. An outcome does not exist until the door has decided, so
    a pre-lookup row here could not carry one. Writing last records every
    computed refusal and loses only the unhandled-exception path.
    """
    await record_event(
        session,
        event_type="repo_reindex_requested",
        object_type="repository",
        object_id=repo_id,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        payload={"outcome": outcome, "file_count": file_count, "commit": commit},
    )


async def prepare_reindex(
    session: AsyncSession,
    repo: Repository,
    *,
    files: list[str] | None,
    commit: str | None,
    actor: str | None,
    api_key_id: UUID | None,
    source: str,
) -> ReindexAccepted:
    """Validate and verify, or raise ``ReindexRefused``. Journals either way."""
    files = files or []
    count = len(files)

    async def refuse(status_code: int, reason: str, **detail):
        await _journal(
            session, repo.id, outcome=reason, file_count=count,
            commit=commit, actor=actor, api_key_id=api_key_id, source=source,
        )
        await session.commit()
        raise ReindexRefused(status_code, reason, **detail)

    if count > MAX_UNION_FILES:
        await refuse(400, "too_many_files", limit=MAX_UNION_FILES, given=count)

    if commit is not None and not _SHA_RE.match(commit):
        await refuse(400, "malformed_commit")

    if repo.status in BUSY_STATUSES:
        await refuse(409, "repo_busy", status=repo.status)

    manager = RepoManager(session)
    try:
        work_dir = manager.repo_working_dir(repo)
    except ValueError as exc:
        await refuse(409, "repo_unavailable", error=str(exc))
    if not (work_dir / ".git").exists():
        await refuse(409, "repo_unavailable", error="working directory is not a git repository")

    try:
        canonical, invalid = canonicalise_paths(work_dir, files)
    except OSError as exc:
        await refuse(409, "tree_unreadable", error=str(exc))
    if invalid:
        await refuse(400, "invalid_files", paths=sorted(invalid)[:20])

    try:
        head = (await RepoManager._run_git(
            work_dir, ["git", "rev-parse", "HEAD"],
        )).strip()
    except Exception as exc:
        await refuse(409, "head_unreadable", error=str(exc)[:200])

    if commit is not None and head != commit:
        await refuse(409, "head_mismatch", expected=commit, actual=head)

    await _journal(
        session, repo.id, outcome="indexing", file_count=count,
        commit=commit, actor=actor, api_key_id=api_key_id, source=source,
    )
    await session.commit()
    return ReindexAccepted(union_files=canonical, commit=commit, head=head)
