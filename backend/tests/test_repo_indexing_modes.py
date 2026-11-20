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

    async def fake_pull(self, repo, **_kwargs):
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


async def test_a_failed_fetch_never_rewinds_a_local_checkout(session, session_factory, tmp_path):
    """Spec 3.2, the half this loop reaches. The repo has no remote, so the
    fetch fails and `merge --ff-only` is never reached: what is pinned here is
    that a fetch which cannot run leaves the operator's tree alone rather than
    falling through to the re-clone. The merge itself is pinned in
    `test_repos.py` (`test_pull_repo_never_rewinds_a_local_checkout` and its
    fast-forward sibling), which build a real upstream to reach it."""
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

    async def fake_pull(self, repo, **_kwargs):
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

    async def boom(self, repo, **_kwargs):
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

    async def boom(self, repo, **_kwargs):
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
        spawned.append((repo_id, kwargs))

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
    assert spawned[0][1]["kind"] == "initial"


async def test_create_repo_passes_pull_false_to_spawn(client, monkeypatch, auth_headers):
    """Fix round 1, Finding 3, half one: `create_repo`'s own call into
    `_spawn_repo_index` must carry `pull=False` for the initial index --
    checked against a fake `_spawn_repo_index` so this half is independent
    of whatever `_spawn_repo_index` itself does with the flag (that half is
    `test_initial_index_never_pulls` below, against the real function)."""
    spawned: list = []

    from app.api.routes import repos as repos_route

    def fake_spawn(repo_id, pipeline, session_factory, **kwargs):
        spawned.append(kwargs)

        class _T:
            pass

        return _T()

    monkeypatch.setattr(repos_route, "_spawn_repo_index", fake_spawn)

    r = await client.post(
        "/api/v1/repos",
        json={"name": "index-once-no-pull", "local_path": None},
        headers=auth_headers,
    )

    assert r.status_code == 201
    assert len(spawned) == 1
    assert spawned[0]["kind"] == "initial"
    assert spawned[0]["pull"] is False


async def test_initial_index_never_pulls(client, monkeypatch, auth_headers, tmp_path):
    """Fix round 1, Finding 3, half two: the real, unmocked
    `_spawn_repo_index` must actually thread `pull=False` down into
    `CodePipeline.run` -- not just receive it as a kwarg (`fake_spawn` in
    the sibling test above would pass even if `_spawn_repo_index` silently
    dropped the flag on the floor). `CodePipeline.run` itself is mocked so
    this proves the call shape reaching it, not a real pipeline execution;
    `_make_local_repo`-style local_path avoids the URL clone path
    entirely, keeping this test to the local-repo initial-index arm."""
    import asyncio
    from unittest.mock import AsyncMock

    from app.api.routes import repos as repos_route
    from app.services.code_pipeline import CodePipeline
    from app.services.task_registry import TaskRegistry

    run_mock = AsyncMock(return_value={"status": "indexed", "commit": "deadbeef"})
    monkeypatch.setattr(CodePipeline, "run", run_mock)

    captured_tasks: list = []
    real_register = TaskRegistry.register

    def capturing_register(repo_id, kind, task, message=""):
        captured_tasks.append(task)
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(TaskRegistry, "register", capturing_register)

    repo_dir = tmp_path / "initial-index-no-pull"
    repo_dir.mkdir()

    r = await client.post(
        "/api/v1/repos",
        json={"name": "initial-index-no-pull", "local_path": str(repo_dir), "provider": "local"},
        headers=auth_headers,
    )

    assert r.status_code == 201
    assert len(captured_tasks) == 1
    await asyncio.gather(*captured_tasks)

    run_mock.assert_awaited_once()
    assert run_mock.await_args.kwargs == {"pull": False}


async def test_create_repo_never_spawns_without_a_successful_claim(
    client, monkeypatch, auth_headers,
):
    """Fix round 1, Finding 1a: `create_repo` is the only one of six
    `_spawn_repo_index` call sites that used to spawn with no claim taken
    first -- a real race window against the pipeline's own `status =
    "indexing"` write. Simulating a refused claim (as if another caller had
    already claimed the repo between its creation and this point) and
    asserting nothing is spawned pins the ordering: claim, then spawn, never
    the reverse."""
    from app.api.routes import repos as repos_route
    from app.services.repo_manager import RepoManager

    spawned: list = []

    def fake_spawn(repo_id, pipeline, session_factory, **kwargs):
        spawned.append(kwargs)

        class _T:
            pass

        return _T()

    monkeypatch.setattr(repos_route, "_spawn_repo_index", fake_spawn)

    async def refuse_claim(self, repo_id, *, message):
        return False

    monkeypatch.setattr(RepoManager, "claim_for_indexing", refuse_claim)

    r = await client.post(
        "/api/v1/repos",
        json={"name": "claim-gates-spawn", "local_path": None},
        headers=auth_headers,
    )

    assert r.status_code == 201
    assert spawned == []


async def test_create_repo_does_not_spawn_index_for_a_url_repo_at_create_time(
    client, monkeypatch, auth_headers,
):
    """Fix round 1, Finding 2 (the un-covered half): a URL repo is still
    cloning and has no tree to read yet. `create_repo` must not claim or
    spawn an index before the clone lands -- only `on_ready`, invoked from
    `_clone_in_background` after a successful clone, may do that. The clone
    is gated on an event this test controls, so "no spawn yet" is a real
    assertion rather than a race against a background task that just
    hasn't run."""
    import asyncio

    from app.api.routes import repos as repos_route
    from app.services.repo_manager import RepoManager
    from app.services.task_registry import TaskRegistry

    spawned: list = []

    def fake_spawn(repo_id, pipeline, session_factory, **kwargs):
        spawned.append(kwargs)

        class _T:
            pass

        return _T()

    monkeypatch.setattr(repos_route, "_spawn_repo_index", fake_spawn)

    gate = asyncio.Event()

    async def blocked_clone(self, repo):
        await gate.wait()

    monkeypatch.setattr(RepoManager, "_clone_repo", blocked_clone)

    captured_tasks: list = []
    real_register = TaskRegistry.register

    def capturing_register(repo_id, kind, task, message=""):
        captured_tasks.append(task)
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(TaskRegistry, "register", capturing_register)

    r = await client.post(
        "/api/v1/repos",
        json={"name": "url-repo-no-immediate-spawn", "url": "https://github.com/example/example.git"},
        headers=auth_headers,
    )

    assert r.status_code == 201
    assert spawned == []

    # Let the still-blocked clone task settle rather than leaving it
    # pending past this test.
    gate.set()
    await asyncio.gather(*captured_tasks)


async def test_url_repo_is_indexed_once_when_its_clone_completes(monkeypatch):
    """Fix round 1, Finding 2: before this fix, `_clone_in_background` set
    the repo `status="ready"` and stopped -- with every recurring switch
    defaulting off, a URL repo was never indexed at all. `on_ready` closes
    that: `RepoManager.create`'s only caller, `create_repo`, passes a
    callback that claims and spawns the initial index once the clone
    actually lands.

    Uses the real `async_session_factory` throughout, not the per-test
    `session` fixture: `_clone_in_background` always opens its own session
    on that factory, so a row only visible on the isolated per-test
    connection would be invisible to it, exactly as it would be in
    production if the two used different engines."""
    import asyncio

    from sqlalchemy import delete

    import app.database as database_module
    from app.schemas.code import RepoCreate
    from app.services.repo_manager import RepoManager
    from app.services.task_registry import TaskRegistry

    async def instant_clone(self, repo):
        return None

    monkeypatch.setattr(RepoManager, "_clone_repo", instant_clone)

    on_ready_calls: list = []

    def on_ready(repo_id):
        on_ready_calls.append(repo_id)

    captured_tasks: list = []
    real_register = TaskRegistry.register

    def capturing_register(repo_id, kind, task, message=""):
        captured_tasks.append((kind, task))
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(TaskRegistry, "register", capturing_register)

    repo_id = None
    try:
        async with database_module.async_session_factory() as session:
            manager = RepoManager(session)
            repo = await manager.create(
                RepoCreate(
                    name="clone-index-once",
                    url="https://github.com/example/example.git",
                ),
                on_ready=on_ready,
            )
            repo_id = repo.id

        clone_tasks = [t for kind, t in captured_tasks if kind == "clone"]
        assert len(clone_tasks) == 1
        await asyncio.gather(*clone_tasks)

        assert on_ready_calls == [repo_id]
    finally:
        if repo_id is not None:
            async with database_module.async_session_factory() as cleanup:
                await cleanup.execute(delete(Repository).where(Repository.id == repo_id))
                await cleanup.commit()


async def test_url_repo_route_claims_and_spawns_initial_after_clone(
    client, auth_headers, monkeypatch,
):
    """Fix round 2, Item 1: round 1's two Finding-2 tests each pin one side
    of the wiring and neither pins the wiring itself.
    `test_url_repo_is_indexed_once_when_its_clone_completes` drives
    `RepoManager.create`/`_clone_in_background` directly with a stub
    `on_ready` of the test's own, so it never touches `create_repo`'s real
    `_index_after_clone` closure at all --
    `test_create_repo_does_not_spawn_index_for_a_url_repo_at_create_time`
    only asserts the *absence* of an early spawn. Neither would notice
    `on_ready=_index_after_clone` being deleted from `create_repo`, which
    silently reintroduces Finding 2 verbatim (a URL repo cloned, marked
    ready, never indexed) -- confirmed by a re-review that deleted exactly
    that line and watched every test in this module and
    `test_push_webhook.py` stay green.

    This drives the real route end to end: a real clone (mocked
    instantaneous), the route's own `on_ready` callback claiming and
    spawning through `_spawn_repo_index`, and `CodePipeline.run` actually
    receiving `pull=False` -- so it also covers the post-clone arm of
    Finding 3, which the round-1 mutation drill only exercised on the
    local-repo arm.

    Uses the app's real `get_session` for the duration, the same pattern
    `test_unchanged_head_short_circuits_exactly_as_polling_does` uses:
    `_clone_in_background` and the claim-and-spawn child task both open
    their own sessions on the real `async_session_factory`, so the created
    row must be genuinely committed for either to see it.
    """
    import asyncio
    import uuid
    from unittest.mock import AsyncMock

    import app.database as database_module
    from app.database import get_session
    from app.main import app
    from app.services.code_pipeline import CodePipeline
    from app.services.repo_manager import RepoManager
    from app.services.task_registry import TaskRegistry
    from sqlalchemy import delete, select

    run_mock = AsyncMock(return_value={"status": "indexed", "commit": "cafe"})
    monkeypatch.setattr(CodePipeline, "run", run_mock)

    async def instant_clone(self, repo):
        return None

    monkeypatch.setattr(RepoManager, "_clone_repo", instant_clone)

    captured: list = []
    real_register = TaskRegistry.register

    def capturing_register(repo_id, kind, task, message=""):
        captured.append((kind, task))
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(TaskRegistry, "register", capturing_register)

    original_session_override = app.dependency_overrides.get(get_session)
    del app.dependency_overrides[get_session]
    repo_id = None
    try:
        r = await client.post(
            "/api/v1/repos",
            json={"name": "e2e-url-initial", "url": "https://github.com/example/e2e.git"},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        repo_id = uuid.UUID(r.json()["id"])

        clone_tasks = [t for k, t in captured if k == "clone"]
        assert len(clone_tasks) == 1
        await asyncio.gather(*clone_tasks)

        # The claim-and-spawn child task is registered (Item 2) but still
        # fire-and-forget from this test's perspective -- give the loop a
        # bounded window to run it and the index task it spawns.
        for _ in range(300):
            index_tasks = [t for k, t in captured if k == "initial"]
            if index_tasks and all(t.done() for t in index_tasks):
                break
            await asyncio.sleep(0.01)
        index_tasks = [t for k, t in captured if k == "initial"]
        assert len(index_tasks) == 1, (
            f"route's post-clone closure never spawned an initial index; "
            f"captured={[(k, t.done()) for k, t in captured]}"
        )
        await asyncio.gather(*index_tasks)

        run_mock.assert_awaited_once()
        assert run_mock.await_args.kwargs == {"pull": False}

        async with database_module.async_session_factory() as check:
            status = (await check.execute(
                select(Repository.status).where(Repository.id == repo_id)
            )).scalar_one()
        # The claim wrote "indexing" before the spawn; the mocked run never
        # releases it, which is fine -- the claim having been taken first is
        # exactly what is asserted here.
        assert status == "indexing"
    finally:
        if original_session_override is not None:
            app.dependency_overrides[get_session] = original_session_override
        if repo_id is not None:
            async with database_module.async_session_factory() as cleanup:
                await cleanup.execute(delete(Repository).where(Repository.id == repo_id))
                await cleanup.commit()


async def test_the_fetch_lane_skips_a_repo_a_run_already_owns(
    session, session_factory, indexed_repo, spy,
):
    """A clone, a webhook run or a manual reindex owns the working tree
    `pull_repo` would `reset --hard`. The index lane takes
    `claim_for_indexing`; the fetch lane takes nothing, so it has to read the
    same statuses that claim refuses on -- and on a failing fetch `pull_repo`
    rmtree's the very directory an in-flight clone is writing into."""
    indexed_repo.fetch_enabled = True
    indexed_repo.status = "cloning"
    await session.commit()

    await job_runners.make_repo_sync_runner(None, session_factory)()

    assert spy.fetched == []


async def test_a_busy_tick_does_not_burn_the_fetch_interval(
    session, session_factory, indexed_repo, spy,
):
    """The interval bounds how often a fetch happens, not how often one is
    refused: a repo skipped while busy must fetch on the first tick after it
    goes idle, not one whole interval later."""
    indexed_repo.fetch_enabled = True
    indexed_repo.fetch_interval_seconds = 3600
    indexed_repo.status = "indexing"
    await session.commit()
    runner = job_runners.make_repo_sync_runner(None, session_factory)

    await runner()
    assert spy.fetched == []

    indexed_repo.status = "ready"
    await session.commit()
    await runner()

    assert spy.fetched == [indexed_repo.id]


async def test_re_arming_a_lane_makes_the_next_tick_act(
    session, session_factory, indexed_repo, spy, client, auth_headers,
):
    """Spec section 6: switching a repository on acts immediately. The loop's
    per-repo due-times are derived from the switches, so a PUT that changes one
    leaves them stale -- and a stale due-time refuses every tick until the OLD
    interval lapses, including the wakeup-triggered tick the arming PUT fires."""
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.commit_poll_seconds = 3600
    await session.commit()
    runner = job_runners.make_repo_sync_runner(None, session_factory)

    await runner()
    assert spy.indexed == []

    off = await client.put(
        f"/api/v1/repos/{indexed_repo.id}",
        json={"index_on_commit_enabled": False}, headers=auth_headers,
    )
    assert off.status_code == 200
    on = await client.put(
        f"/api/v1/repos/{indexed_repo.id}",
        json={"index_on_commit_enabled": True}, headers=auth_headers,
    )
    assert on.status_code == 200

    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")
    await runner()

    assert [r[0] for r in spy.indexed] == [indexed_repo.id]


async def test_shortening_an_interval_takes_effect_at_once(
    session, session_factory, indexed_repo, spy, client, auth_headers,
):
    """Same root cause as re-arming: the old interval must not outlive the PUT
    that replaced it."""
    indexed_repo.index_on_commit_enabled = True
    indexed_repo.commit_poll_seconds = 3600
    await session.commit()
    runner = job_runners.make_repo_sync_runner(None, session_factory)

    await runner()
    assert spy.indexed == []

    r = await client.put(
        f"/api/v1/repos/{indexed_repo.id}",
        json={"commit_poll_seconds": 15}, headers=auth_headers,
    )
    assert r.status_code == 200

    _commit(Path(indexed_repo.local_path), "def beta():\n    return 2\n", "two")
    await runner()

    assert [r[0] for r in spy.indexed] == [indexed_repo.id]


async def test_deleting_a_repo_evicts_its_due_times(
    session, session_factory, indexed_repo, spy, client, auth_headers,
):
    """`_DUE` is keyed by repo id and nothing else ever removes an entry, so a
    deleted repo's due-times survive until the process restarts."""
    indexed_repo.index_on_commit_enabled = True
    await session.commit()
    await job_runners.make_repo_sync_runner(None, session_factory)()
    assert indexed_repo.id in job_runners._DUE

    r = await client.delete(
        f"/api/v1/repos/{indexed_repo.id}", headers=auth_headers,
    )
    assert r.status_code == 204

    assert indexed_repo.id not in job_runners._DUE


async def test_a_restart_releases_the_claims_a_dead_process_left(session):
    """A claim outlives the process that took it: a redeploy or a cancelled
    task ends the run without reaching its own status reset, and every reindex
    door then refuses the repo. A fresh process runs nothing, so every claim
    it finds is stale."""
    from app.services.repo_manager import RepoManager

    indexed = Repository(
        name="was-indexing", local_path="/tmp/was-indexing", status="indexing",
        last_indexed_commit="a" * 40,
    )
    cloning = Repository(name="was-cloning", url="https://forge.invalid/r.git", status="cloning")
    idle = Repository(name="was-idle", local_path="/tmp/was-idle", status="ready")
    session.add_all([indexed, cloning, idle])
    await session.flush()

    released = await RepoManager.release_interrupted_runs(session)

    assert released == 2
    for repo in (indexed, cloning, idle):
        await session.refresh(repo)
    assert (indexed.status, cloning.status, idle.status) == ("stale", "error", "ready")
    assert await RepoManager(session).claim_for_indexing(indexed.id, message="again") is True
