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
    noticing local commits needs no network at all.

    Asserts via a spy on `mark_periodic_sync_failure` (the one and only writer
    of `index_on_commit_enabled = False` on this path) rather than a post-loop
    DB re-read. Finding 3's fix (`repo_session.rollback()` inside the fetch
    lane's own except) means this scenario now rolls back a `session_factory`
    session mid-loop, and `session_factory` binds every session to the *same*
    connection the outer `session` fixture holds -- confirmed by direct
    reproduction: even a bare `get() -> rollback() -> get()` sequence on that
    shared connection makes the second `get()`, on the very same session,
    return None. A `session.refresh(indexed_repo)` afterward is therefore not
    a reliable oracle in this suite once the loop performs a deliberate
    mid-flight rollback; asserting on the call that would have disabled the
    switch is both immune to that artifact and a more direct statement of
    the guarantee this test exists to pin."""
    from app.services.repo_manager import RepoManager

    async def boom(self, repo):
        raise RuntimeError("network down")

    disable_calls: list = []
    orig_mark_failure = RepoManager.mark_periodic_sync_failure

    async def tracking_mark_failure(self, repo_id, error):
        disable_calls.append(repo_id)
        return await orig_mark_failure(self, repo_id, error)

    monkeypatch.setattr(RepoManager, "pull_repo", boom)
    monkeypatch.setattr(RepoManager, "mark_periodic_sync_failure", tracking_mark_failure)
    indexed_repo.fetch_enabled = True
    indexed_repo.index_on_commit_enabled = True
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert disable_calls == []


async def test_a_fetch_error_rolls_back_and_rereads_before_the_index_lane(
    session, session_factory, indexed_repo, spy, monkeypatch,
):
    """Unit-level proof for Finding 3: the fetch lane's `except` must both roll
    back `repo_session` and re-read `repo` through it before anything later
    touches an attribute on it -- a bare rollback expires every loaded
    attribute and turns the next access into MissingGreenlet.

    This does NOT drive a genuine DB-layer fault (e.g. get_credential's
    session.get() erroring) end to end. `session_factory` binds every session
    it opens to the *same* underlying connection as the outer `session`
    fixture (conftest.py's `session_factory`, by design, so writes from any
    session are visible to the test and rolled back with it). Confirmed by
    trying the literal DB-fault test first: `RepoManager.pull_repo` issuing a
    real failing statement (`SELECT 1/0`) on that shared connection recovers
    fine *inside* the loop -- the fetch except's own `repo_session.rollback()`
    (a ROLLBACK TO SAVEPOINT under `join_transaction_mode="conditional_savepoint"`)
    lets the loop finish and even index -- but then poisons the *outer*
    `session` fixture's own transaction bookkeeping: a later
    `await session.refresh(indexed_repo)` on the outer session raises
    `InvalidRequestError: Could not refresh instance`, with SQLAlchemy warning
    "transaction already deassociated from connection". Every `AsyncSession`
    bound to one shared `AsyncConnection` mutates that connection's Core-level
    transaction state when one of them rolls back, which the *other* sessions'
    Python-side transaction wrappers do not learn about -- a test-fixture
    artifact of sharing one physical connection, not a defect in production,
    where each session in `make_repo_sync_runner` opens on the real engine and
    is genuinely independent. So this test proves the *code path* fires
    (rollback then re-read, in that order, exactly once each) rather than
    proving recovery from a real DB fault under production's session
    topology."""
    from sqlalchemy.ext.asyncio import AsyncSession as SAAsyncSession

    from app.services.repo_manager import RepoManager

    rollback_calls: list = []
    orig_rollback = SAAsyncSession.rollback

    async def tracking_rollback(self):
        rollback_calls.append(self)
        return await orig_rollback(self)

    get_calls: list = []
    orig_get = RepoManager.get

    async def tracking_get(self, repo_id):
        get_calls.append(repo_id)
        return await orig_get(self, repo_id)

    async def boom(self, repo):
        raise RuntimeError("db fault inside pull_repo")

    monkeypatch.setattr(SAAsyncSession, "rollback", tracking_rollback)
    monkeypatch.setattr(RepoManager, "get", tracking_get)
    monkeypatch.setattr(RepoManager, "pull_repo", boom)

    indexed_repo.fetch_enabled = True
    indexed_repo.index_on_commit_enabled = True
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert len(rollback_calls) == 1
    assert get_calls.count(indexed_repo.id) == 2, (
        "repo must be read once at loop start and re-read once after the "
        "fetch lane's rollback, before the index lane touches it"
    )
    # HEAD never moved and index_uncommitted is off: the index lane, once it
    # safely resumes on the re-read repo, correctly finds nothing to do.
    assert spy.indexed == []


async def test_create_defaults_every_switch_off(client, auth_headers):
    r = await client.post(
        "/api/v1/repos",
        json={"name": "api-default", "local_path": None},
        headers=auth_headers,
    )

    assert r.status_code == 201
    body = r.json()
    assert body["fetch_enabled"] is False
    assert body["index_on_commit_enabled"] is False
    assert body["index_uncommitted"] is False
    assert body["fetch_interval_seconds"] == 300
    assert body["commit_poll_seconds"] == 60


async def test_a_below_floor_interval_is_refused_at_the_door(client, auth_headers):
    """A two-second interval would spin the loop, so it is a 422 rather than a
    value the scheduler has to defend against."""
    r = await client.post(
        "/api/v1/repos",
        json={"name": "too-fast", "index_on_commit_enabled": True, "commit_poll_seconds": 2},
        headers=auth_headers,
    )

    assert r.status_code == 422


async def test_update_round_trips_the_switches(client, auth_headers):
    created = (await client.post(
        "/api/v1/repos", json={"name": "api-update"}, headers=auth_headers,
    )).json()

    r = await client.put(
        f"/api/v1/repos/{created['id']}",
        json={"index_on_commit_enabled": True, "commit_poll_seconds": 30},
        headers=auth_headers,
    )

    assert r.status_code == 200
    assert r.json()["index_on_commit_enabled"] is True
    assert r.json()["commit_poll_seconds"] == 30

async def test_adding_a_repository_indexes_it_once(client, monkeypatch, auth_headers):
    """With every recurring switch off, nothing else would ever index a new
    repo -- adding one would do nothing at all. Opt-in governs recurring work;
    asking darkmem to track a repo is the opt-in for indexing it once."""
    spawned: list = []

    from app.api.routes import repos as repos_route

    def fake_spawn(repo_id, pipeline, session_factory, **kwargs):
        spawned.append((repo_id, kwargs.get("kind")))

        class _T:
            pass

        return _T()

    monkeypatch.setattr(repos_route, "_spawn_repo_index", fake_spawn)

    r = await client.post(
        "/api/v1/repos",
        json={"name": "index-once", "local_path": None},
        headers=auth_headers,
    )

    assert r.status_code == 201
    assert len(spawned) == 1
    assert spawned[0][1] == "initial"
