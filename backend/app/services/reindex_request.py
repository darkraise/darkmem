"""The one entry point both file-scoped reindex doors call (spec §1).

Order is the design: precheck, then canonicalise, then verify HEAD, then claim.
The precheck runs before canonicalisation because ``repo_working_dir``
re-validates the path on every access and raises for one that no longer
exists or sits inside a blocked tree, and a busy repository (``indexing`` or
``cloning``) deserves the honest ``repo_busy`` rather than whatever exception
that re-validation would otherwise raise first.

The HEAD check is read-only on purpose. ``pull_repo`` runs ``reset --hard`` on a
clone and can re-clone the directory outright; firing it from this unclaimed
path would reset the tree under a concurrent run's parser. The spawned run does
its own pull under the claim, exactly as it does today. The guarantee this door
can honestly make is therefore "HEAD equalled your sha when the request was
accepted", and nothing stronger.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NoReturn
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import Repository
from app.services.events import record_event
from app.services.reindex_files import MAX_UNION_FILES, canonicalise_paths
from app.services.repo_manager import RepoManager

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


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


async def journal_reindex_outcome(
    session: AsyncSession,
    repo_id: UUID | None,
    *,
    outcome: str,
    file_count: int,
    commit: str | None,
    actor: str | None,
    api_key_id: UUID | None,
    source: str,
    **extra,
) -> None:
    """Journal one ``repo_reindex_requested`` row carrying the caller's outcome.

    ``extra`` is folded into the payload so a door whose repository reference
    never resolved can still say what the caller named. ``record_event``'s
    ``object_id`` is nullable, and an id-less row that also names no repository
    records nothing an operator could act on -- which is the probe-recording
    purpose this journalling borrowed from the webhook.

    ``prepare_reindex`` calls this for every refusal it computes, before it
    raises -- the outcome exists the moment a refusal is decided. It does NOT
    call this on success: the claim that actually starts indexing happens
    downstream, in the door, after ``prepare_reindex`` returns, and that claim
    can still lose (``409 repo_busy``) to a concurrent run. Journalling
    ``"indexing"`` from here would leave a lying row on the losing path. The
    door calls this helper itself, once, with whichever outcome the claim
    produced.
    """
    await record_event(
        session,
        event_type="repo_reindex_requested",
        object_type="repository",
        object_id=repo_id,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        payload={
            **extra,
            "outcome": outcome, "file_count": file_count, "commit": commit,
        },
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
    """Validate and verify, or raise ``ReindexRefused``, journalling every
    refusal. Acceptance is not journalled here -- the caller journals its own
    outcome via ``journal_reindex_outcome`` once the downstream claim settles
    whether indexing actually starts.
    """
    files = files or []
    count = len(files)

    async def refuse(status_code: int, reason: str, **detail) -> NoReturn:
        await journal_reindex_outcome(
            session, repo.id, outcome=reason, file_count=count,
            commit=commit, actor=actor, api_key_id=api_key_id, source=source,
        )
        await session.commit()
        raise ReindexRefused(status_code, reason, **detail)

    if count > MAX_UNION_FILES:
        await refuse(400, "too_many_files", limit=MAX_UNION_FILES, given=count)

    if commit is not None and not _SHA_RE.match(commit):
        await refuse(400, "malformed_commit")

    if repo.status in RepoManager.BUSY_STATUSES:
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
        # The regex admits 7-40 hex characters, so a correct abbreviated sha
        # reaches here despite naming HEAD itself. Comparing the git-resolved
        # value is what tells "you named HEAD in short form" apart from the
        # head_mismatch this would otherwise report, whose client guidance
        # ("darkmem is at a different commit it does hold") would then be wrong.
        try:
            await RepoManager._run_git(
                work_dir, ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            )
            resolved = (await RepoManager._run_git(
                work_dir, ["git", "rev-parse", f"{commit}^{{commit}}"],
            )).strip()
        except Exception:
            await refuse(409, "unknown_commit", expected=commit, actual=head)
        if resolved != head:
            await refuse(409, "head_mismatch", expected=commit, actual=head)

    return ReindexAccepted(union_files=canonical, commit=commit, head=head)
