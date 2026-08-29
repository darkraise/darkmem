"""T4.05 -- push webhook receiver (doc 10 §5, doc 15 §9).

Fix round 1 (2026-08-16): the review found the shipped handler awaited
``CodePipeline.run`` synchronously inline and returned 202 with the
*terminal* result already in the body -- the tell that the intended shape
was async-accepted, bent away from it to dodge a harness limitation. The fix
factors ``reindex_repo``'s own shape (guard, commit ``status='indexing'`` in
the route before any work, spawn a tracked background task on a fresh
session, return 202 with no terminal result) into one shared helper,
``repos_module._spawn_repo_index``, that both routes call.

The central constraint is still "never a second indexing path": the webhook
must dispatch into the identical change-gated ``CodePipeline.run`` polling
uses, not a look-alike reimplementation. That is proven several ways here
rather than by reading the route body:

* ``TestSharedEntryPoint`` structurally scans the handler's AST and asserts
  its only calls are the existence/status-commit bookkeeping and a single
  dispatch into ``_spawn_repo_index`` -- the same helper ``reindex_repo``
  calls. The scan inspects both ``ast.Attribute`` **and bare ``ast.Name``**
  calls; ``TestMutationDrillCatchesBareNameCalls`` proves by construction
  that an attribute-only scan is blind to a smuggled bare-name call.
* ``TestPollingCallShapeStaysAsserted`` pins polling's own call shape
  (``app/services/job_runners.py``: ``await pipeline.run(repo_id,
  forced_files=forced, pull=False)`` since T3 split polling into a fetch
  lane and an index lane) directly against that source, rather than only in
  a comment here. The webhook's own call site is still the bare
  ``pipeline.run(repo_id)`` shape below -- the two are no longer identical,
  and that divergence is deliberate: the webhook has no fetch lane of its
  own to hand `pull` off to.
* ``TestSignatureVerification`` patches ``CodePipeline.run`` with a
  call-counting mock, captures the background task ``_spawn_repo_index``
  schedules, awaits it, and asserts a bad credential never reaches
  ``CodePipeline.run`` while a good one reaches it exactly once with
  polling's own ``(repo_id)`` call shape -- no kwargs, since the webhook
  never passes ``full``/``enrich_symbols``/``generate_wiki``.
* ``TestNeverDoubleIndex`` runs the *real*, unmocked pipeline through the
  webhook route twice at the same HEAD sha and asserts the second call is
  the same up-to-date short-circuit polling gets, not a second index. This
  drives a genuinely committed background task: the request-scoped
  ``get_session`` override the rest of this suite relies on wraps every
  write in a rolled-back outer transaction, which a detached task's own
  fresh session cannot see, so this test swaps it out for the app's real
  ``get_session`` -- true per-request commits, exactly what production runs
  -- and cleans its own committed rows up afterward.

Every guard here also gets a mutation drill (``TestMutationDrill``): the
auth dependency is bypassed via ``app.dependency_overrides`` and the request
is shown to reach the pipeline unauthenticated, then the override is
removed and the same request is refused again.
"""
from __future__ import annotations

import asyncio
import ast
import inspect
import subprocess
import textwrap
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.database as database_module
from app.api.auth import Principal
from app.api.deps import get_code_pipeline
from app.api.routes import repos as repos_module
from app.database import get_session
from app.main import app
from app.models.code import Repository
from app.services import job_runners as job_runners_module
from app.services.api_keys import issue_key, mint_credential, revoke_key
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager

# asyncio_mode = "auto" (pyproject.toml) collects async tests without a
# marker, and applying `pytestmark = pytest.mark.asyncio` at module scope
# would also mark TestSharedEntryPoint's synchronous AST tests, which warns.


async def _make_local_repo(
    client, headers, tmp_path, name: str = "webhook-repo",
    *, suppress_initial_index: bool = True,
) -> str:
    """Create a local-path repo through the real route.

    Fix round 1 (Task 5, per-repo indexing modes): ``create_repo`` now
    claims and spawns an "initial" background index for every non-URL repo.
    Every test in this module except
    ``test_unchanged_head_short_circuits_exactly_as_polling_does`` wants the
    plain pre-existing behaviour -- a freshly created, idle (``status ==
    "ready"``) repo it can drive its own webhook calls against -- and does
    not care about that initial index at all. ``suppress_initial_index``
    (the default) makes ``claim_for_indexing`` refuse just for this one
    call, via a scoped ``pytest.MonkeyPatch.context()`` rather than the
    caller's own ``monkeypatch`` fixture, so the patch cannot leak past this
    function or collide with a mock the caller sets up before or after it.
    With no claim taken, ``create_repo`` never spawns, so nothing is left
    running against a background session that -- for every test using the
    ordinary ``client`` fixture -- cannot even see the just-created row (its
    creating transaction is never truly committed), which is exactly what
    produced the "Repository ... not found" / "relation ... does not
    exist" noise this default closes.

    Pass ``suppress_initial_index=False`` for a test that means to exercise
    the real initial index end to end; the caller is then responsible for
    draining the background task itself before relying on the repo's
    status.
    """
    repo_dir = tmp_path / name
    repo_dir.mkdir()
    (repo_dir / "svc.py").write_text("def hello():\n    return 1\n", encoding="utf-8")

    async def _refuse_claim(self, repo_id, *, message):
        return False

    if suppress_initial_index:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(RepoManager, "claim_for_indexing", _refuse_claim)
            resp = await client.post(
                "/api/v1/repos",
                json={"name": name, "local_path": str(repo_dir), "provider": "local"},
                headers=headers,
            )
    else:
        resp = await client.post(
            "/api/v1/repos",
            json={"name": name, "local_path": str(repo_dir), "provider": "local"},
            headers=headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _patch_pull(monkeypatch, sha: str) -> None:
    """Stand in for a real ``git fetch``/``git pull`` at a fixed HEAD sha."""
    async def _pull(self, repo):
        return sha
    monkeypatch.setattr(RepoManager, "pull_repo", _pull)


def _mock_run(monkeypatch, **result) -> AsyncMock:
    mock = AsyncMock(return_value={"status": "indexed", "commit": "deadbeef", **result})
    monkeypatch.setattr(CodePipeline, "run", mock)
    return mock


def _capture_background_tasks(monkeypatch) -> list[asyncio.Task]:
    """Background dispatch happens via ``asyncio.create_task`` inside
    ``_spawn_repo_index``; a test needs a handle on the created task to await
    it before asserting on its effects -- the route itself returns as soon
    as the task is scheduled, not when it finishes.

    Patching ``asyncio.create_task`` itself would patch it process-wide --
    `repos_module.asyncio` is the very same module object every other
    library sees, and SQLAlchemy's own connection-pool bookkeeping spawns
    tasks of its own during a request. Patching
    ``TaskRegistry.register`` instead captures exactly the one task
    ``_spawn_repo_index`` hands it, nothing incidental.
    """
    captured: list[asyncio.Task] = []
    real_register = repos_module.TaskRegistry.register

    def _capturing_register(repo_id, kind, task, message=""):
        captured.append(task)
        return real_register(repo_id, kind, task, message)

    monkeypatch.setattr(repos_module.TaskRegistry, "register", _capturing_register)
    return captured


def _collect_call_targets(func_ast: ast.AST) -> tuple[list[str], list[str]]:
    """Every call's target name, split by whether it was reached via
    attribute access (``obj.method(...)``) or a bare name (``func(...)``).
    An attribute-only scan is blind to the second shape -- exactly how a
    smuggled second indexing path can hide (see the mutation drill below).

    Walks only the function's own body, not its decorator list or its
    argument defaults -- ``@router.post(...)`` and each parameter's
    ``Depends(...)`` are call expressions too, but they are routing/DI
    wiring, not business logic the handler's body chose to call."""
    attr_calls: list[str] = []
    name_calls: list[str] = []
    body = getattr(func_ast, "body", None)
    statements = body if body is not None else [func_ast]
    for stmt in statements:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr_calls.append(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    name_calls.append(node.func.id)
    return attr_calls, name_calls


# The webhook handler's only sanctioned bare-name calls: raising one of the
# closed set of HTTPExceptions, dispatching into the one shared background
# path, and `str(repo_id)` in the response body.
# `record_event` and `session_factory` joined this set with E4.F1, and the
# extension is deliberate rather than accommodating: the guard's subject is a
# *second indexing path*, and a journal write is not one. It reads nothing
# about the repository, spawns nothing, and touches no pipeline — it records
# that a credential presented itself, which is the observability doc 18 §5
# requires and the C1 finding said was absent. The forbidden-prefix check
# below is untouched and still fails on any parse/clone/phase call.
ALLOWED_NAME_CALLS = {
    "HTTPException", "_spawn_repo_index", "str", "record_event", "session_factory",
}


# ---------------------------------------------------------------------------
# Never a second indexing path -- structural proof
# ---------------------------------------------------------------------------


class TestSharedEntryPoint:
    def test_the_handler_dispatches_only_through_the_shared_spawner(self):
        """AST scan, not a read-through: the handler body's only calls are
        the existence check, the in-route status='indexing' commit, and one
        dispatch into ``_spawn_repo_index`` -- the identical helper
        ``reindex_repo`` calls. A future edit that inlines parsing, git, or
        direct graph writes into this handler fails this test even if every
        other test here still passes."""
        source = textwrap.dedent(inspect.getsource(repos_module.repo_push_webhook))
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, ast.AsyncFunctionDef)

        attr_calls, name_calls = _collect_call_targets(func)

        # manager.get is the existence check; claim_for_indexing takes the
        # in-route status='indexing' write atomically (T4.16 — it replaced the
        # flush/commit pair that used to do it non-atomically, and is a status
        # write, not an indexing path); manager.session.commit lands the
        # schedule-failure recovery, alongside logger.error which
        # `reindex_repo` also carries. Nothing else may be called on any
        # service object.
        assert set(attr_calls) <= {
            "get", "claim_for_indexing", "flush", "commit", "error",
        }

        assert name_calls.count("_spawn_repo_index") == 1
        for name in name_calls:
            assert name in ALLOWED_NAME_CALLS, (
                f"webhook handler calls {name!r} directly -- that is a "
                "second indexing path, not a dispatch through the shared "
                "spawner"
            )

        forbidden_prefixes = ("phase_", "_parse", "_clone", "_delete_all_repo_data")
        for name in (*attr_calls, *name_calls):
            assert not name.startswith(forbidden_prefixes), (
                f"webhook handler calls {name!r} directly -- that is a "
                "second indexing path, not a call into the shared spawner"
            )

    def test_status_indexing_is_committed_before_the_background_spawn(self):
        """Important 2: committing ``status='indexing'`` in the route body
        before the background dispatch is what narrows the concurrent-
        delivery window from the pipeline's own ``git pull`` down to the
        route body. Pin the order, not just the presence of both calls --
        a regression that spawned first and committed after would still
        pass every other assertion here."""
        source = textwrap.dedent(inspect.getsource(repos_module.repo_push_webhook))
        tree = ast.parse(source)
        func = tree.body[0]

        commit_lines = [
            node.lineno for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
        ]
        spawn_lines = [
            node.lineno for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_spawn_repo_index"
        ]
        assert commit_lines and spawn_lines
        # The earliest commit is the in-route status='indexing' write; a
        # second, later commit exists too (the schedule-failure recovery
        # path, which runs *after* the spawn attempt and must not be
        # confused with it).
        assert min(commit_lines) < min(spawn_lines), (
            "status='indexing' must be committed before _spawn_repo_index "
            "is dispatched, not after"
        )

    def test_reindex_and_webhook_dispatch_through_the_identical_helper(self):
        """'One shared background-run helper' is not naming symmetry --
        both routes must reference the exact same function object."""
        reindex_source = textwrap.dedent(inspect.getsource(repos_module.reindex_repo))
        webhook_source = textwrap.dedent(inspect.getsource(repos_module.repo_push_webhook))
        assert "_spawn_repo_index(" in reindex_source
        assert "_spawn_repo_index(" in webhook_source
        # There is exactly one function by that name in the module, so both
        # routes referencing it by name can only be calling the same one.
        matches = [
            node for node in ast.walk(ast.parse(inspect.getsource(repos_module)))
            if isinstance(node, ast.FunctionDef) and node.name == "_spawn_repo_index"
        ]
        assert len(matches) == 1

    def test_the_shared_spawner_s_background_run_calls_only_pipeline_run(self):
        """The dispatched closure's own only pipeline-shaped call is
        ``idx.run(...)`` -- everything else in it is registry/broadcast
        bookkeeping or error-path status recovery."""
        source = textwrap.dedent(inspect.getsource(repos_module._spawn_repo_index))
        tree = ast.parse(source)
        outer = tree.body[0]
        inner = next(
            node for node in ast.walk(outer)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run_index"
        )
        run_calls = [
            node for node in ast.walk(inner)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ]
        assert len(run_calls) == 1
        (only_run_call,) = run_calls
        assert isinstance(only_run_call.func.value, ast.Name)
        assert only_run_call.func.value.id == "idx"

        forbidden_prefixes = ("phase_", "_parse", "_clone", "_delete_all_repo_data")
        attr_calls, _ = _collect_call_targets(inner)
        for name in attr_calls:
            assert not name.startswith(forbidden_prefixes)


class TestMutationDrillCatchesBareNameCalls:
    """m2: the reviewer verified a smuggled ``do_second_indexing_path(repo)``
    -- a bare ``ast.Name`` call -- passes an attribute-only scan. This drill
    reproduces that finding and then shows the widened scan catches it."""

    MUTATED_SOURCE = textwrap.dedent('''
        async def repo_push_webhook(repo_id, _principal=None, pipeline=None,
                                      manager=None, session_factory=None):
            repo = await manager.get(repo_id)
            if not repo:
                raise HTTPException(status_code=404)
            do_second_indexing_path(repo)
            _spawn_repo_index(repo_id, pipeline, session_factory, kind="webhook")
            return {"status": "indexing"}
    ''')

    def test_a_smuggled_bare_name_call_is_invisible_to_an_attribute_only_scan(self):
        tree = ast.parse(self.MUTATED_SOURCE)
        func = tree.body[0]
        attr_calls, _ = _collect_call_targets(func)
        assert "do_second_indexing_path" not in attr_calls

    def test_the_widened_scan_catches_the_same_smuggled_call(self):
        tree = ast.parse(self.MUTATED_SOURCE)
        func = tree.body[0]
        _, name_calls = _collect_call_targets(func)
        assert "do_second_indexing_path" in name_calls

        with pytest.raises(AssertionError):
            for name in name_calls:
                assert name in ALLOWED_NAME_CALLS, (
                    f"webhook handler calls {name!r} directly"
                )


# ---------------------------------------------------------------------------
# Polling's own call shape -- asserted, not only cited in a comment (m3)
# ---------------------------------------------------------------------------


class TestPollingCallShapeStaysAsserted:
    def test_job_runners_calls_pipeline_run_with_the_index_lane_shape(self):
        """Per-repo indexing modes (T3) split polling into a fetch lane and an
        index lane, so polling's call site is no longer the bare
        `pipeline.run(repo.id)` the webhook still uses -- it now passes
        `forced_files` (uncommitted-drift support) and `pull=False`.
        `pull=False` is load-bearing: the fetch lane above already owns
        fetching this tick, so an unconditional pull inside the pipeline
        would `reset --hard` away the very drift `forced_files` names. If
        this call site drifts, this test must go red with it."""
        source = textwrap.dedent(inspect.getsource(job_runners_module.make_repo_sync_runner))
        tree = ast.parse(source)

        run_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pipeline"
        ]
        assert len(run_calls) == 1
        (call,) = run_calls
        assert len(call.args) == 1
        assert isinstance(call.args[0], ast.Name) and call.args[0].id == "repo_id"
        keyword_names = {kw.arg for kw in call.keywords}
        assert keyword_names == {"forced_files", "pull"}
        pull_kw = next(kw for kw in call.keywords if kw.arg == "pull")
        assert isinstance(pull_kw.value, ast.Constant) and pull_kw.value.value is False


def _init_committed_repo_dir(path) -> None:
    """A real, minimal git repo with one commit -- the polling loop's index
    lane resolves HEAD off the working tree's own `.git` files
    (`app/services/git_head.py`) before it will ever call `pipeline.run`, so
    a fixture standing in for a real repository needs a real one, not a bare
    path string."""
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", *args], cwd=path, check=True, capture_output=True, timeout=30,
    )
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (path / "f.py").write_text("def a():\n    return 1\n")
    run("add", "-A")
    run("commit", "-q", "-m", "one")


@pytest.fixture
async def committed_repo(tmp_path):
    """A repository row visible to sessions other than the fixture's.

    The claim is a cross-caller guard, so testing it needs callers that can
    actually see each other's writes — and a repo created through the API in
    the rollback-isolated fixture transaction is visible to nobody else, which
    makes every claim against it match zero rows and return False for the wrong
    reason. Inserted and cleaned up on its own committed session.
    """
    from sqlalchemy import text as sql_text
    from tests.conftest import test_engine

    created: list[str] = []

    async def _make(
        name: str, *, index_on_commit_enabled: bool = False, status: str = "ready",
    ) -> str:
        repo_id = str(uuid.uuid4())
        repo_dir = tmp_path / name
        repo_dir.mkdir()
        _init_committed_repo_dir(repo_dir)
        async with AsyncSession(test_engine) as own:
            await own.execute(
                sql_text(
                    "INSERT INTO repositories (id, name, provider, default_branch, "
                    "status, index_on_commit_enabled, local_path) VALUES "
                    "(CAST(:id AS uuid), :name, 'local', 'main', :status, "
                    ":index_on_commit_enabled, :path)"
                ),
                {
                    "id": repo_id, "name": name, "status": status,
                    "index_on_commit_enabled": index_on_commit_enabled,
                    "path": str(repo_dir),
                },
            )
            await own.commit()
        created.append(repo_id)
        return repo_id

    yield _make

    async with AsyncSession(test_engine) as cleanup:
        for repo_id in created:
            await cleanup.execute(
                sql_text("DELETE FROM repositories WHERE id = CAST(:id AS uuid)"),
                {"id": repo_id},
            )
        await cleanup.commit()


class TestTheIndexClaimIsAtomic:
    """T4.16 — "the two never double-index", finally proven against polling.

    The epic review's I2: `repo_sync` never read `repo.status` and
    `CodePipeline.run` had no compare-and-set, so a poll tick landing inside a
    webhook run indexed the same repository twice, concurrently. Both routes
    also claimed by reading the status and then assigning it, which two
    simultaneous deliveries can both pass.
    """

    async def test_only_one_of_two_simultaneous_claims_wins(self, committed_repo):
        """The claim is one UPDATE with the predicate inside it, so the second
        caller's statement matches no row. A read-then-write lets both through
        and this is the test that says so."""
        from app.services.repo_manager import RepoManager
        from tests.conftest import test_engine

        repo_id = await committed_repo("claim-race")

        async with AsyncSession(test_engine) as first, AsyncSession(test_engine) as second:
            first_won = await RepoManager(first).claim_for_indexing(
                uuid.UUID(repo_id), message="first"
            )
            second_won = await RepoManager(second).claim_for_indexing(
                uuid.UUID(repo_id), message="second"
            )

        assert first_won is True
        assert second_won is False, "two callers both took the indexing claim"

    async def test_polling_skips_a_repo_a_webhook_is_already_indexing(
        self, committed_repo, monkeypatch,
    ):
        """The double-index the review named: a repository whose indexing claim
        is already held must not be indexed again by the polling tick."""
        from app.services import job_runners as job_runners_module
        from app.services.code_pipeline import CodePipeline
        from tests.conftest import test_engine

        await committed_repo("polled-repo", index_on_commit_enabled=True, status="indexing")

        polled: list = []

        async def _tracking_run(self, *args, **kwargs):
            polled.append(args)
            return {"status": "up_to_date"}

        monkeypatch.setattr(CodePipeline, "run", _tracking_run)
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        class _App:
            class state:
                llm = None

        await job_runners_module.make_repo_sync_runner(_App, factory)()

        assert polled == [], (
            "polling indexed a repository whose indexing claim was already held "
            "— this is the concurrent double-index"
        )

    async def test_polling_does_index_a_repo_nobody_has_claimed(
        self, committed_repo, monkeypatch,
    ):
        """Without this the test above passes against a polling loop that
        stopped indexing anything at all."""
        from app.services import job_runners as job_runners_module
        from app.services.code_pipeline import CodePipeline
        from tests.conftest import test_engine

        await committed_repo("free-polled-repo", index_on_commit_enabled=True, status="ready")

        polled: list = []

        async def _tracking_run(self, *args, **kwargs):
            polled.append(args)
            return {"status": "up_to_date"}

        monkeypatch.setattr(CodePipeline, "run", _tracking_run)
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        class _App:
            class state:
                llm = None

        await job_runners_module.make_repo_sync_runner(_App, factory)()

        assert len(polled) == 1, "polling must still index a repository nobody holds"

    async def test_a_free_repo_is_still_claimable(self, committed_repo):
        """The counterpart: the guard must not refuse everything. Without this
        the test above passes against a claim that always returns False."""
        from app.services.repo_manager import RepoManager
        from tests.conftest import test_engine

        repo_id = await committed_repo("claimable-repo")

        async with AsyncSession(test_engine) as own:
            assert await RepoManager(own).claim_for_indexing(
                uuid.UUID(repo_id), message="free"
            ) is True

    async def test_the_up_to_date_short_circuit_releases_the_claim(self, committed_repo):
        """A run that finds nothing to do must hand the claim back, committed.

        The claim is taken and committed in the route body, then the work runs
        in `_spawn_repo_index`'s own session, which is closed without a commit
        of its own. A short-circuit that only flushes `status='ready'` is
        therefore rolled back with that session, and the row stays `indexing` —
        after which every reindex, every webhook delivery and every polling
        tick fails the claim forever.
        """
        from app.services.repo_manager import RepoManager
        from tests.conftest import test_engine

        sha = "sha-already-indexed"
        repo_id = await committed_repo("claim-release-repo")

        async with AsyncSession(test_engine) as setup:
            await setup.execute(
                update(Repository)
                .where(Repository.id == uuid.UUID(repo_id))
                .values(last_indexed_commit=sha)
            )
            await setup.commit()

        async with AsyncSession(test_engine) as claim_session:
            assert await RepoManager(claim_session).claim_for_indexing(
                uuid.UUID(repo_id), message="Queued for indexing..."
            ) is True

        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as run_session:
            manager = RepoManager(run_session)

            async def _pull(_repo, _sha=sha):
                return _sha

            manager.pull_repo = _pull
            result = await CodePipeline(
                session=run_session, llm=None, vector_repo=None, repo_manager=manager,
            ).run(uuid.UUID(repo_id))

        assert result["status"] == "up_to_date"

        async with AsyncSession(test_engine) as check:
            status, status_message = (await check.execute(
                select(Repository.status, Repository.status_message)
                .where(Repository.id == uuid.UUID(repo_id))
            )).one()

        assert status == "ready", (
            "the up-to-date short-circuit kept the committed indexing claim; "
            "every later reindex, webhook and polling tick now fails it"
        )
        assert status_message is None

        async with AsyncSession(test_engine) as later:
            assert await RepoManager(later).claim_for_indexing(
                uuid.UUID(repo_id), message="next run"
            ) is True


# ---------------------------------------------------------------------------
# Signature verification happens before any work
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    async def test_no_credential_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        resp = await client.post(f"/api/v1/repos/{uuid.uuid4()}/webhook")
        assert resp.status_code == 401
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_wrong_scope_is_forbidden_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["capture"])
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_forged_credential_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {mint_credential().token}"},
        )
        assert resp.status_code == 401
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_revoked_key_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        row, token = await issue_key(session, name="ci", scopes=["admin"])
        await revoke_key(session, row.id)
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_unknown_repo_with_valid_key_is_404_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["admin"])
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_a_valid_admin_key_is_admitted_and_calls_pipeline_run_once(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["admin"])

        resp = await client.post(
            f"/api/v1/repos/{repo_id}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202, resp.text
        assert resp.json() == {"status": "indexing", "repo_id": repo_id}

        assert len(tasks) == 1
        await asyncio.gather(*tasks)

        # The webhook's own call shape -- one positional arg, no `full`,
        # no `forced_files`, nothing that would make the change gate treat
        # this run differently. Polling's own call site has since grown
        # `forced_files`/`pull=False` (pinned in
        # `TestPollingCallShapeStaysAsserted` above); the two call shapes
        # are no longer identical, only both dispatching into the same
        # change-gated `CodePipeline.run`.
        run_mock.assert_awaited_once()
        assert run_mock.await_args.args == (uuid.UUID(repo_id),)
        assert run_mock.await_args.kwargs == {}

    async def test_a_human_session_is_admitted(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)

        resp = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
        assert resp.status_code == 202, resp.text
        assert resp.json() == {"status": "indexing", "repo_id": repo_id}

        assert len(tasks) == 1
        await asyncio.gather(*tasks)
        run_mock.assert_awaited_once()


# ---------------------------------------------------------------------------
# Never double-index
# ---------------------------------------------------------------------------


class TestNeverDoubleIndex:
    async def test_a_run_already_in_flight_is_a_conflict_not_a_second_call(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)

        # Simulate an in-flight run (from polling or a prior webhook
        # delivery) the same way `CodePipeline.run` itself marks one.
        await session.execute(
            update(Repository).where(Repository.id == uuid.UUID(repo_id)).values(status="indexing")
        )
        await session.flush()

        resp = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
        assert resp.status_code == 409
        assert tasks == []
        run_mock.assert_not_awaited()

    async def test_unchanged_head_short_circuits_exactly_as_polling_does(
        self, client, auth_headers, tmp_path, monkeypatch,
    ):
        """Real, unmocked ``CodePipeline.run`` through the webhook route
        twice at the same HEAD sha. The second call must be the same
        up-to-date short-circuit polling's own change gate produces, never a
        second index of the same commit.

        The route now backgrounds its work (fix round 1), so this test must
        exercise a genuinely committed background task: the request-scoped
        `session` fixture the rest of this suite relies on wraps every
        write in a rolled-back outer transaction, invisible to a detached
        task's own fresh connection. This test swaps `get_session` for the
        app's real one -- true per-request commits, exactly what production
        runs -- for its own duration, and cleans its committed rows up
        itself in a `finally`. `get_session_factory` needs no override: its
        default already resolves to `app.database.async_session_factory`,
        the very sessionmaker `get_session` itself opens from, so the
        background task's session and the request's session share one real
        engine without any extra wiring.

        `vector_repo=None`/`llm=None` matches the established pattern for a
        deterministic real pipeline run without a live embedder
        (`test_code_fail_stale.py`, `test_code_pipeline_integration.py`);
        the default DI-provided pipeline instead carries a real
        `PostgresVectorRepository`, whose first-index cleanup path
        (`_delete_all_repo_data` -> `delete_code_chunks_by_repo`) queries
        every fingerprint ever registered against `embedders` in this
        shared test database -- including ones other test modules (e.g.
        `test_memory_dream.py`) register with real commits of their own and
        whose partition tables do not survive to this test. That is a
        pre-existing cross-test hazard in
        `embedder_registry`/`_delete_all_repo_data`, not something this
        route introduces; overriding the dependency the same way sibling
        pipeline tests already do sidesteps it rather than papering over
        it.

        ``_make_local_repo`` is called here with
        ``suppress_initial_index=False``: this test is the one place in the
        module that wants ``create_repo``'s own claim-and-spawn (fix round
        1, Finding 1) to run for real, so its background task is drained
        and left to settle *before* the first webhook post -- otherwise
        that post would race a repo still claimed "indexing" by its own
        creation and correctly get refused with 409, which is a true
        positive for the claim guard, not a defect in this test's subject.
        The repo directory this helper writes has no ``.git`` at all, so
        that initial run fails fast (`git rev-parse HEAD` outside a
        repository) and leaves the repo `status="error"` -- settled, not
        "indexing", which is all the first webhook post needs from it. Its
        `CodePipeline.run` raises before returning, so `_spy_run` never
        appends it to `results`; the two `results` entries asserted below
        are only the two webhook-driven runs.
        """
        results: list[dict] = []
        original_run = CodePipeline.run

        async def _spy_run(self, *args, **kwargs):
            result = await original_run(self, *args, **kwargs)
            results.append(result)
            return result

        monkeypatch.setattr(CodePipeline, "run", _spy_run)

        async def _pipeline_without_vector_repo(session: AsyncSession = Depends(get_session)):
            return CodePipeline(
                session=session, llm=None, vector_repo=None,
                repo_manager=RepoManager(session),
            )

        original_session_override = app.dependency_overrides.get(get_session)
        del app.dependency_overrides[get_session]
        app.dependency_overrides[get_code_pipeline] = _pipeline_without_vector_repo
        tasks = _capture_background_tasks(monkeypatch)
        repo_id: str | None = None
        try:
            repo_id = await _make_local_repo(
                client, auth_headers, tmp_path, suppress_initial_index=False,
            )
            # Drain the initial index `create_repo` itself spawned and let
            # it settle before anything else touches this repo's status.
            assert len(tasks) == 1
            await asyncio.gather(*tasks)
            tasks.clear()

            _patch_pull(monkeypatch, sha="fixed-sha-1")

            first = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
            assert first.status_code == 202, first.text
            assert first.json() == {"status": "indexing", "repo_id": repo_id}

            assert len(tasks) == 1
            await asyncio.gather(*tasks)
            tasks.clear()

            assert results[-1]["status"] == "indexed"
            assert results[-1]["commit"] == "fixed-sha-1"

            async with database_module.async_session_factory() as check:
                last_commit = (await check.execute(
                    select(Repository.last_indexed_commit).where(Repository.id == uuid.UUID(repo_id))
                )).scalar_one()
            assert last_commit == "fixed-sha-1"

            second = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
            assert second.status_code == 202, second.text
            assert second.json() == {"status": "indexing", "repo_id": repo_id}

            assert len(tasks) == 1
            await asyncio.gather(*tasks)

            assert results[-1]["status"] == "up_to_date"
            assert len(results) == 2
        finally:
            del app.dependency_overrides[get_code_pipeline]
            if original_session_override is not None:
                app.dependency_overrides[get_session] = original_session_override
            if repo_id is not None:
                async with database_module.async_session_factory() as cleanup:
                    await cleanup.execute(delete(Repository).where(Repository.id == uuid.UUID(repo_id)))
                    await cleanup.commit()


# ---------------------------------------------------------------------------
# Mutation drill: prove the guard is load-bearing, not decorative
# ---------------------------------------------------------------------------


class TestMutationDrill:
    async def test_bypassing_the_guard_admits_an_unauthenticated_request(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        """Break the guard, watch the pipeline reach an unauthenticated
        caller; restore it, watch that same caller get refused again. A
        guard that cannot be shown to fail this way is decorative."""
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)
        tasks = _capture_background_tasks(monkeypatch)

        async def _bypass():
            return Principal(actor="bypass", api_key_id=None, scopes=frozenset({"admin"}))

        app.dependency_overrides[repos_module._require_repo_admin] = _bypass
        try:
            bypassed = await client.post(f"/api/v1/repos/{repo_id}/webhook")
        finally:
            del app.dependency_overrides[repos_module._require_repo_admin]

        assert bypassed.status_code == 202, bypassed.text
        assert len(tasks) == 1
        await asyncio.gather(*tasks)
        run_mock.assert_awaited_once()

        run_mock.reset_mock()
        tasks.clear()
        restored = await client.post(f"/api/v1/repos/{repo_id}/webhook")
        assert restored.status_code == 401
        assert tasks == []
        run_mock.assert_not_awaited()
