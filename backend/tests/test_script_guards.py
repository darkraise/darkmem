"""scripts/build-push.sh, run for real in a scratch repository with `docker`
replaced by a stub that records its arguments."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_PUSH = REPO_ROOT / "scripts" / "build-push.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()


def _tags(repo: Path) -> list[str]:
    log = repo.parent / f"{repo.name}-docker.log"
    stub_dir = repo.parent / f"{repo.name}-bin"
    stub_dir.mkdir()
    stub = stub_dir / "docker"
    stub.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" >> "{log}"\n')
    stub.chmod(0o755)
    result = subprocess.run(
        ["bash", "scripts/build-push.sh"],
        cwd=repo, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PATH": f"{stub_dir}:{os.environ['PATH']}", "DARKMEM_PUSH": "0"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    args = log.read_text().splitlines()
    assert args[0] == "build" and "push" not in args
    return [args[i + 1] for i, a in enumerate(args) if a == "-t"]


def _repo(tmp_path: Path, name: str) -> tuple[Path, str]:
    repo = tmp_path / name
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "build-push.sh").write_text(BUILD_PUSH.read_text())
    (repo / "README").write_text("base\n")
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "chore: base")
    return repo, _git(repo, "rev-parse", "--short", "HEAD")


def test_dirty_tree_is_not_tagged_with_the_head_sha(tmp_path):
    clean, sha = _repo(tmp_path, "clean")
    (clean / "untracked.txt").write_text("not part of the build's commit\n")
    assert f"darkraise/darkmem:{sha}" in _tags(clean)

    dirty, sha = _repo(tmp_path, "dirty")
    (dirty / "README").write_text("changed\n")
    tags = _tags(dirty)
    assert f"darkraise/darkmem:{sha}-dirty" in tags
    assert f"darkraise/darkmem:{sha}" not in tags
