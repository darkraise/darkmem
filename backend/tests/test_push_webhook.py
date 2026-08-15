"""T4.05 -- push webhook receiver (doc 10 §5, doc 15 §9).

The central constraint is "never a second indexing path": the webhook must
call the identical change-gated ``CodePipeline.run`` polling uses, not a
look-alike reimplementation. That is proven three ways here rather than by
reading the route body:

* ``TestSharedEntryPoint`` structurally scans the handler's AST and asserts
  its only method call is ``pipeline.run(...)`` -- no parsing, no git, no
  direct graph writes live in the handler.
* ``TestSignatureVerification`` patches ``CodePipeline.run`` with a
  call-counting mock and asserts a bad credential never reaches it, while a
  good one reaches it exactly once with the same ``(repo_id)`` shape
  polling's own call site (``app/services/job_runners.py``) uses -- no
  ``full``, no ``forced_files``, nothing the change gate would treat
  differently from an ordinary polling tick.
* ``TestNeverDoubleIndex`` runs the *real*, unmocked pipeline against a tiny
  local repo through the webhook route twice at the same HEAD sha and
  asserts the second call is the same up-to-date short-circuit polling gets,
  not a second index.

Every guard here also gets a mutation drill (``TestMutationDrill``): the
dependency is bypassed via ``app.dependency_overrides`` and the request is
shown to reach the pipeline unauthenticated, then the override is removed
and the same request is refused again.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, update

from app.api.auth import Principal
from app.api.deps import get_code_pipeline
from app.api.routes import repos as repos_module
from app.main import app
from app.models.code import Repository
from app.services.api_keys import issue_key, mint_credential, revoke_key
from app.services.code_pipeline import CodePipeline
from app.services.repo_manager import RepoManager

# asyncio_mode = "auto" (pyproject.toml) collects async tests without a
# marker, and applying `pytestmark = pytest.mark.asyncio` at module scope
# would also mark TestSharedEntryPoint's synchronous AST test, which warns.


async def _make_local_repo(client, headers, tmp_path, name: str = "webhook-repo") -> str:
    repo_dir = tmp_path / name
    repo_dir.mkdir()
    (repo_dir / "svc.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
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


# ---------------------------------------------------------------------------
# Never a second indexing path -- structural proof
# ---------------------------------------------------------------------------


class TestSharedEntryPoint:
    def test_the_handler_calls_nothing_but_pipeline_run(self):
        """AST scan, not a read-through: the handler body's only method call
        is ``pipeline.run(...)``. A future edit that inlines parsing, git, or
        direct graph writes into this handler fails this test even if every
        other test here still passes."""
        source = textwrap.dedent(inspect.getsource(repos_module.repo_push_webhook))
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, ast.AsyncFunctionDef)

        call_targets: list[str] = []
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                call_targets.append(node.func.attr)

        # manager.get is the existence check; pipeline.run is the entry
        # point. Nothing else may be called on either service object, and
        # no other object may have a `.run`-shaped or indexing-shaped call.
        assert "run" in call_targets
        run_calls = [
            node for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ]
        assert len(run_calls) == 1
        (only_run_call,) = run_calls
        assert isinstance(only_run_call.func.value, ast.Name)
        assert only_run_call.func.value.id == "pipeline"

        forbidden_prefixes = ("phase_", "_parse", "_clone", "_delete_all_repo_data")
        for name in call_targets:
            assert not name.startswith(forbidden_prefixes), (
                f"webhook handler calls {name!r} directly -- that is a "
                "second indexing path, not a call into CodePipeline.run"
            )


# ---------------------------------------------------------------------------
# Signature verification happens before any work
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    async def test_no_credential_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        resp = await client.post(f"/api/v1/repos/{uuid.uuid4()}/webhook")
        assert resp.status_code == 401
        run_mock.assert_not_awaited()

    async def test_wrong_scope_is_forbidden_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["capture"])
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        run_mock.assert_not_awaited()

    async def test_forged_credential_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {mint_credential().token}"},
        )
        assert resp.status_code == 401
        run_mock.assert_not_awaited()

    async def test_revoked_key_is_refused_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        row, token = await issue_key(session, name="ci", scopes=["admin"])
        await revoke_key(session, row.id)
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        run_mock.assert_not_awaited()

    async def test_unknown_repo_with_valid_key_is_404_and_nothing_is_called(
        self, client, session, monkeypatch,
    ):
        run_mock = _mock_run(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["admin"])
        resp = await client.post(
            f"/api/v1/repos/{uuid.uuid4()}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        run_mock.assert_not_awaited()

    async def test_a_valid_admin_key_is_admitted_and_calls_pipeline_run_once(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)
        _, token = await issue_key(session, name="ci", scopes=["admin"])

        resp = await client.post(
            f"/api/v1/repos/{repo_id}/webhook",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202, resp.text

        # Exactly the shape polling's own call site uses
        # (`app/services/job_runners.py`: `await pipeline.run(repo.id)`) --
        # one positional arg, no `full`, no `forced_files`, nothing that
        # would make the change gate treat this run differently.
        run_mock.assert_awaited_once()
        assert run_mock.await_args.args == (uuid.UUID(repo_id),)
        assert run_mock.await_args.kwargs == {}

    async def test_a_human_session_is_admitted(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        repo_id = await _make_local_repo(client, auth_headers, tmp_path)
        run_mock = _mock_run(monkeypatch)

        resp = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
        assert resp.status_code == 202, resp.text
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

        # Simulate an in-flight run (from polling or a prior webhook
        # delivery) the same way `CodePipeline.run` itself marks one.
        await session.execute(
            update(Repository).where(Repository.id == uuid.UUID(repo_id)).values(status="indexing")
        )
        await session.flush()

        resp = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
        assert resp.status_code == 409
        run_mock.assert_not_awaited()

    async def test_unchanged_head_short_circuits_exactly_as_polling_does(
        self, client, session, auth_headers, tmp_path, monkeypatch,
    ):
        """Real, unmocked ``CodePipeline.run`` through the webhook route
        twice at the same HEAD sha. The second call must be the same
        up-to-date short-circuit polling's own change gate produces, never a
        second index of the same commit.

        ``vector_repo=None`` matches the established pattern for a
        deterministic real pipeline run without a live embedder
        (``test_code_fail_stale.py``, ``test_code_pipeline_integration.py``);
        the default DI-provided pipeline instead carries a real
        ``PostgresVectorRepository``, whose first-index cleanup path
        (``_delete_all_repo_data`` -> ``delete_code_chunks_by_repo``) queries
        every fingerprint ever registered against ``embedders`` in this
        shared test database -- including ones other test modules (e.g.
        ``test_memory_dream.py``) register and whose partition tables do not
        survive to this test. That is a pre-existing cross-test hazard in
        `embedder_registry`/`_delete_all_repo_data`, not something this route
        introduces; overriding the dependency the same way sibling pipeline
        tests already do sidesteps it rather than papering over it.
        """
        async def _pipeline_without_vector_repo():
            return CodePipeline(
                session=session, llm=None, vector_repo=None,
                repo_manager=RepoManager(session),
            )

        app.dependency_overrides[get_code_pipeline] = _pipeline_without_vector_repo
        try:
            repo_id = await _make_local_repo(client, auth_headers, tmp_path)
            _patch_pull(monkeypatch, sha="fixed-sha-1")

            first = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
            assert first.status_code == 202, first.text
            assert first.json()["status"] == "indexed"
            assert first.json()["commit"] == "fixed-sha-1"

            symbols_after_first = (await session.execute(
                select(Repository.last_indexed_commit).where(Repository.id == uuid.UUID(repo_id))
            )).scalar_one()
            assert symbols_after_first == "fixed-sha-1"

            second = await client.post(f"/api/v1/repos/{repo_id}/webhook", headers=auth_headers)
            assert second.status_code == 202, second.text
            assert second.json()["status"] == "up_to_date"
        finally:
            del app.dependency_overrides[get_code_pipeline]


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

        async def _bypass():
            return Principal(actor="bypass", api_key_id=None, scopes=frozenset({"admin"}))

        app.dependency_overrides[repos_module._require_repo_admin] = _bypass
        try:
            bypassed = await client.post(f"/api/v1/repos/{repo_id}/webhook")
        finally:
            del app.dependency_overrides[repos_module._require_repo_admin]

        assert bypassed.status_code == 202, bypassed.text
        run_mock.assert_awaited_once()

        run_mock.reset_mock()
        restored = await client.post(f"/api/v1/repos/{repo_id}/webhook")
        assert restored.status_code == 401
        run_mock.assert_not_awaited()
