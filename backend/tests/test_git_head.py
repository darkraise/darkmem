"""Resolving HEAD without a subprocess in the common case.

The first draft of the spec proposed an mtime gate on `.git/HEAD`. That is
wrong and the test below is the reason: a commit on a branch never touches
that file — it holds `ref: refs/heads/<branch>` and only the branch's loose
ref moves — so the gate would miss every ordinary commit while looking like
it worked.
"""
import subprocess

import pytest

from app.services.git_head import resolve_head_sha


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def _repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f.txt").write_text("one")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "one")
    return tmp_path


def _rev_parse(cwd) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout.strip()


async def test_resolves_a_loose_ref(tmp_path):
    work = _repo(tmp_path)

    assert await resolve_head_sha(work) == _rev_parse(work)


async def test_sees_a_new_commit(tmp_path):
    """The whole point: a commit must change the answer."""
    work = _repo(tmp_path)
    first = await resolve_head_sha(work)

    (work / "f.txt").write_text("two")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "two")

    second = await resolve_head_sha(work)
    assert second != first
    assert second == _rev_parse(work)


async def test_resolves_a_packed_ref(tmp_path):
    """`git gc` moves the loose ref into packed-refs and deletes the file.
    The read path must fall back rather than report None, which would read
    as 'not a repository' and stall indexing forever."""
    work = _repo(tmp_path)
    expected = _rev_parse(work)
    _git(work, "pack-refs", "--all")
    assert not (work / ".git" / "refs" / "heads" / "main").exists()

    assert await resolve_head_sha(work) == expected


async def test_resolves_a_detached_head(tmp_path):
    work = _repo(tmp_path)
    sha = _rev_parse(work)
    _git(work, "checkout", "-q", "--detach", sha)

    assert await resolve_head_sha(work) == sha


async def test_a_directory_that_is_not_a_repository_is_none(tmp_path):
    assert await resolve_head_sha(tmp_path) is None
