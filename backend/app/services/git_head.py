"""Resolve a working directory's HEAD to a sha.

Read git's own files rather than shelling out, so the poll that runs every
few seconds per repository costs two small reads instead of a subprocess.

Do NOT replace this with an mtime check on `.git/HEAD`. A commit on a branch
does not touch that file -- it holds `ref: refs/heads/<branch>` and only the
branch's loose ref moves -- so an mtime gate there misses every ordinary
commit while appearing to work.
"""
from __future__ import annotations

import re
from pathlib import Path

_SHA = re.compile(r"^[0-9a-f]{40}$")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None


async def resolve_head_sha(work_dir: Path) -> str | None:
    git_dir = work_dir / ".git"

    # Linked worktrees created by `git worktree add` have `.git` as a FILE
    # containing `gitdir: /path/to/main/.git/worktrees/<name>`, not a directory.
    # Skip the file-reading fast path and go straight to the subprocess, which
    # git resolves natively without requiring us to parse the pointer.
    if not git_dir.is_dir():
        from app.services.repo_manager import RepoManager

        try:
            out = await RepoManager._run_git(work_dir, ["git", "rev-parse", "HEAD"])
        except Exception:
            return None
        out = out.strip()
        return out if _SHA.match(out) else None

    head = _read(git_dir / "HEAD")
    if head is None:
        return None

    if _SHA.match(head):
        return head

    if not head.startswith("ref: "):
        return None

    ref = head[len("ref: "):].strip()
    loose = _read(git_dir / ref)
    if loose is not None and _SHA.match(loose):
        return loose

    # Packed: `git gc` deletes the loose ref. Falling back to the subprocess
    # here rather than returning None matters -- None reads as "not a
    # repository" to the caller, which would stall indexing on a repo that is
    # merely well packed.
    from app.services.repo_manager import RepoManager

    try:
        out = await RepoManager._run_git(work_dir, ["git", "rev-parse", "HEAD"])
    except Exception:
        return None
    out = out.strip()
    return out if _SHA.match(out) else None
