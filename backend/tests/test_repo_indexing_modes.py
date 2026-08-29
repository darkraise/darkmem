"""Per-repo indexing modes (spec 2026-08-29).

Every recurring indexing behaviour is a switch the operator sets. The bug
these replace: `code_reconcile` selected every indexed repo and never read
`auto_sync`, so there was no setting that stopped darkmem reindexing a
working tree another agent was editing.
"""
import subprocess
from pathlib import Path

import pytest

from app.models.code import Repository
from app.services import job_runners


async def test_a_new_repository_opts_into_nothing(session):
    """Opt-in means opt-in: adding a row arms no recurring work."""
    repo = Repository(name="fresh", local_path=None, url=None)
    session.add(repo)
    await session.flush()

    assert repo.fetch_enabled is False
    assert repo.index_on_commit_enabled is False
    assert repo.index_uncommitted is False
    assert repo.fetch_interval_seconds == 300
    assert repo.commit_poll_seconds == 60


def test_auto_sync_is_gone():
    """Kept as a synonym it would recreate the confusion it caused: a name
    suggesting it governs all automatic behaviour while governing one loop
    of two."""
    assert not hasattr(Repository, "auto_sync")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def _commit(work: Path, text: str, message: str):
    (work / "f.py").write_text(text)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", message)


def _make_repo_dir(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "def alpha():\n    return 1\n", "one")
    return tmp_path


@pytest.fixture
def indexed_repo(session, tmp_path):
    """A repo row whose graph is current with its HEAD, all switches off."""
    work = _make_repo_dir(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()
    repo = Repository(
        name="watched", local_path=str(work), provider="local",
        last_indexed_commit=head, status="ready",
    )
    session.add(repo)
    return repo


class _Runs:
    """Records what the loop decided to do, without running a pipeline."""

    def __init__(self):
        self.indexed: list[tuple] = []
        self.fetched: list = []


@pytest.fixture
def spy(monkeypatch):
    runs = _Runs()

    async def fake_run(self, repo_id, **kwargs):
        runs.indexed.append((repo_id, kwargs.get("forced_files")))
        return {"status": "indexed"}

    async def fake_pull(self, repo):
        runs.fetched.append(repo.id)
        return None

    from app.services.code_pipeline import CodePipeline
    from app.services.repo_manager import RepoManager

    monkeypatch.setattr(CodePipeline, "run", fake_run)
    monkeypatch.setattr(RepoManager, "pull_repo", fake_pull)
    job_runners._due_reset()
    return runs


async def test_all_switches_off_does_nothing(session, session_factory, indexed_repo, spy):
    """The bug this feature exists for: a repo darkmem must not touch."""
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []
    assert spy.fetched == []


async def test_index_on_commit_indexes_a_new_commit(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert [r[0] for r in spy.indexed] == [indexed_repo.id]
    assert spy.indexed[0][1] is None


async def test_index_on_commit_is_quiet_when_head_has_not_moved(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []


async def test_fetch_on_and_index_off_leaves_the_graph_behind(
    session, session_factory, indexed_repo, spy,
):
    """A legal combination -- track the remote, index on my say-so -- that the
    loop must not second-guess."""
    indexed_repo.fetch_enabled = True
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.fetched == [indexed_repo.id]
    assert spy.indexed == []


async def test_index_uncommitted_off_ignores_a_dirty_tree(
    session, session_factory, indexed_repo, spy,
):
    """Another agent's half-saved file is not an assertion darkmem makes."""
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    (Path(indexed_repo.local_path) / "f.py").write_text("def dirty():\n    return 3\n")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.indexed == []


async def test_index_uncommitted_on_indexes_a_dirty_tree(
    session, session_factory, indexed_repo, spy,
):
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.index_uncommitted = True
    await session.commit()
    (Path(indexed_repo.local_path) / "f.py").write_text("def dirty():\n    return 3\n")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert len(spy.indexed) == 1
    assert spy.indexed[0][1] is not None


async def test_a_fetch_never_rewinds_a_local_checkout(session, session_factory, tmp_path):
    """Spec 3.2. `pull_repo` advances a local_path repo with `merge --ff-only`
    and never `reset --hard`, so darkmem cannot discard a commit another agent
    has not pushed. Unchanged behaviour, pinned here because this loop is now
    what calls it on a schedule."""
    work = _make_repo_dir(tmp_path)
    _commit(work, "def unpushed():\n    return 9\n", "local only")
    before = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()

    repo = Repository(
        name="local-only", local_path=str(work), provider="local",
        url=None, fetch_enabled=True, status="ready",
    )
    session.add(repo)
    await session.commit()

    # No remote at all: the fetch fails, and the tree must survive it.
    await job_runners.make_repo_sync_runner(None, session_factory)()

    after = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert after == before
    assert (work / "f.py").read_text() == "def unpushed():\n    return 9\n"


async def test_an_interval_is_honoured(session, session_factory, indexed_repo, spy):
    """Two ticks inside one interval must examine the repo once."""
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.commit_poll_seconds = 3600
    await session.commit()
    runner = job_runners.make_repo_sync_runner(None, session_factory)

    await runner()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")
    await runner()

    assert spy.indexed == []


async def test_the_index_lane_never_fetches(session, session_factory, indexed_repo, monkeypatch):
    """`CodePipeline.run` pulls unconditionally, so an index tick used to fetch
    even with fetch_enabled off -- ff-advancing the operator's branch, and on a
    managed clone `reset --hard`-ing away the drift forced_files names."""
    pulls: list = []

    async def fake_pull(self, repo):
        pulls.append(repo.id)
        return None

    from app.services.repo_manager import RepoManager

    monkeypatch.setattr(RepoManager, "pull_repo", fake_pull)
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert pulls == []


async def test_a_fetch_failure_leaves_the_index_switch_alone(
    session, session_factory, indexed_repo, monkeypatch,
):
    """A network fault must not turn off a switch the operator chose -- and
    noticing local commits needs no network at all."""
    async def boom(self, repo):
        raise RuntimeError("network down")

    from app.services.repo_manager import RepoManager

    monkeypatch.setattr(RepoManager, "pull_repo", boom)
    indexed_repo.fetch_enabled = True
    indexed_repo.index_on_commit_enabled = True
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()
    await session.refresh(indexed_repo)

    assert indexed_repo.index_on_commit_enabled is True
    assert indexed_repo.fetch_enabled is True
