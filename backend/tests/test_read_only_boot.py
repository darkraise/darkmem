"""The backup worker's boot posture (increment 7, spec §9.5 as redesigned).

**The flag is not the enforcement.** The `darkmem_viewer` Postgres role is,
and `tests/test_read_only_role.py` is where that is proven. What this module
covers is the boot pass, where the role alone is genuinely insufficient:

- Five of the seven boot writers already degrade under a caught exception, so
  the role would make them inert without help. Depending on a caught exception
  for correctness is the "silently fails to hold" shape B1 condemns, so they
  are skipped rather than allowed to fail.
- **`set_config("code_enrichment", ...)` is not one of those.** It has no
  `try` around it, so under the role it does not degrade -- it takes the
  worker down at boot. That one is the reason this file has an AST test.
- **`start_all()` is not a write at all**, which is exactly why the role
  cannot reach it. An armed scheduler makes LLM calls, git fetches and egress
  attempts *client-side* of the database, spending money before anything is
  refused. `backup_ship` would ship snapshots of snapshots.

The AST test is what keeps a future boot writer from landing unguarded: it
reads `app/main.py`'s own source rather than observing one boot, so a writer
added behind a condition this suite never exercises still fails the build.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.config import settings

MAIN = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _guarded_by_read_only(tree: ast.AST, predicate) -> bool:
    """True when every call matching `predicate` sits under an `if` whose test
    mentions `read_only`."""
    found = []

    class Walker(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0

        def visit_If(self, node: ast.If) -> None:
            names = {
                n.attr if isinstance(n, ast.Attribute) else n.id
                for n in ast.walk(node.test)
                if isinstance(n, (ast.Attribute, ast.Name))
            }
            guarded = "read_only" in names
            if guarded:
                self.depth += 1
            for child in ast.iter_child_nodes(node):
                if child is not node.test:
                    self.visit(child)
            if guarded:
                self.depth -= 1

        def visit_Call(self, node: ast.Call) -> None:
            if predicate(node):
                found.append(self.depth > 0)
            self.generic_visit(node)

    Walker().visit(tree)
    assert found, "the call this test is about is no longer in app/main.py"
    return all(found)


def _is_start_all(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == "start_all"


def _is_enrichment_set_config(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_config"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "code_enrichment"
    )


@pytest.fixture(scope="module")
def main_tree() -> ast.AST:
    return ast.parse(MAIN.read_text(encoding="utf-8"))


def test_start_all_is_never_reached_under_the_flag(main_tree):
    """The scheduler is disarmed by a source-level guard, not by hoping every
    job's first write fails. A job's LLM calls, git fetches and egress happen
    client-side of the database, so the role never sees them -- and
    `backup_ship` would ship snapshots of snapshots off a machine whose whole
    purpose is holding them."""
    assert _guarded_by_read_only(main_tree, _is_start_all), (
        "await job_registry.start_all() must sit under an `if not "
        "settings.read_only` guard -- the viewer role cannot stop a job "
        "spending money before its first write"
    )


def test_the_unguarded_enrichment_config_write_is_gated(main_tree):
    """The one boot write with no `try` around it. Under the viewer role it
    does not degrade -- it raises out of `lifespan` and the worker never
    boots at all."""
    assert _guarded_by_read_only(main_tree, _is_enrichment_set_config), (
        "set_config('code_enrichment', ...) must sit under an `if not "
        "settings.read_only` guard: it is unguarded by any try/except, so "
        "under the SELECT-only role it takes the whole app down at boot"
    )


def test_the_reconciliation_writers_are_gated(main_tree):
    """The four already-degrading boot writers (A2-A5). Skipped rather than
    left to a caught exception: a restored snapshot already carries its
    partitions, so there is nothing to reconcile, and depending on an
    exception being swallowed for correctness is the shape B1 condemns."""
    for attr in ("reconcile", "reconcile_event_partitions", "backfill_projects"):
        assert _guarded_by_read_only(
            main_tree,
            lambda node, a=attr: (
                (isinstance(node.func, ast.Attribute) and node.func.attr == a)
                or (isinstance(node.func, ast.Name) and node.func.id == a)
            ),
        ), f"{attr}() must be skipped under settings.read_only"


async def test_the_trigger_route_refuses_under_the_flag(
    client, auth_headers, monkeypatch,
):
    """C5. A disarmed scheduler does not disarm the manual door: `trigger`
    runs the job on demand, and an LLM or egress job spends before it fails."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.post(
        "/api/v1/jobs/buffer_flush/trigger", headers=auth_headers
    )
    assert response.status_code == 403
    assert "read-only" in response.text.lower()


async def test_the_trigger_route_is_unchanged_by_default(client, auth_headers):
    """The regression pin: prod behaviour must be byte-identical to what it was
    before the flag existed. A 404 here means the route reached its own
    unknown-job check, which is proof it was not refused up front."""
    response = await client.post(
        "/api/v1/jobs/definitely_not_a_job/trigger", headers=auth_headers
    )
    assert response.status_code == 404
