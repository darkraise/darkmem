"""T3.25 — the SDK generator (doc 15 §6).

The done-when is "the generator is named and runs from a documented command;
both packages build; regeneration is idempotent". Two of those three are
checked by the task's own Verify (``cd sdks && make generate && git diff
--exit-code``), which is where they belong — this file pins the property that
command cannot see.

**Doc 15 §6's reason for generating at all**: it "guarantees the SDK never
drifts from the two front doors … it enforces invariant 17 (the SDK cannot
expose a behaviour the contract does not)". A generator that emitted a method
for a route the contract had dropped would satisfy every idempotence check and
break that guarantee, so the binding between verb and route is what is tested
here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SDKS = Path(__file__).resolve().parents[2] / "sdks"
sys.path.insert(0, str(SDKS))

import generate as sdk_generate  # noqa: E402

pytestmark = pytest.mark.asyncio


class TestTheContractBinding:
    async def test_every_verb_names_a_route_the_contract_serves(self):
        """The invariant-17 guarantee, checked against the live schema rather
        than a committed copy — a checked-in contract can age into agreeing
        with an SDK that no longer matches the app."""
        from app.main import app

        schema = app.openapi()
        for name, verb in sdk_generate.VERBS.items():
            operations = schema["paths"].get(verb["path"], {})
            assert verb["method"] in operations, f"{name} → {verb['path']}"

    async def test_generation_refuses_when_a_route_is_missing(self, monkeypatch):
        """The refusal is the enforcement. Without it the generator would
        happily emit a method that calls a 404, which is the drift doc 15 §6
        generates the SDK to prevent."""
        monkeypatch.setitem(
            sdk_generate.VERBS, "capture",
            {"method": "post", "path": "/api/v1/route-that-does-not-exist"},
        )
        from app.main import app

        with pytest.raises(SystemExit, match="refusing to generate"):
            sdk_generate._require_routes(app.openapi())

    async def test_the_surface_is_three_verbs(self):
        """Doc 15 §6 is explicit that darkmem is not building a client
        platform: `capture`, `search`, `declareContext` and nothing else. A
        fourth verb is a design decision, not a generator change."""
        assert set(sdk_generate.VERBS) == {"capture", "search", "declareContext"}


def _schema_copy() -> dict:
    """A private copy of the contract.

    `app.openapi()` **caches** and returns the same object every call, so a
    test that mutates it corrupts the schema for every later test in the
    session — which is exactly what an earlier version of the two hash tests
    below did, and how they made the emitted-file comparisons fail against
    correct code. Deep-copied here so a probe stays a probe.
    """
    from copy import deepcopy

    from app.main import app

    return deepcopy(app.openapi())


class TestDeterminism:
    async def test_the_contract_hash_covers_only_the_bound_routes(self):
        """Hashing the whole document would report a change every time an
        unrelated route moved, which trains a reader to ignore the signal."""
        schema = _schema_copy()
        before = sdk_generate._hash(schema)

        schema["paths"]["/api/v1/unrelated-route"] = {"get": {"summary": "noise"}}

        assert sdk_generate._hash(schema) == before

    async def test_the_hash_moves_when_a_bound_route_changes(self):
        """The other half: a signal that never fires is not a signal."""
        schema = _schema_copy()
        before = sdk_generate._hash(schema)

        schema["paths"]["/api/v1/memories"]["post"]["summary"] = "changed"

        assert sdk_generate._hash(schema) != before

    async def test_rendering_is_a_pure_function_of_the_digest(self):
        """No clock, no environment, no ordering by dict insertion — the
        task's own Verify is `git diff --exit-code`, which a generator with
        any of those would fail on a second run."""
        first = sdk_generate.render_typescript("abc123")
        second = sdk_generate.render_typescript("abc123")
        assert first == second

        python_first = sdk_generate.render_python("abc123")
        assert python_first == sdk_generate.render_python("abc123")
        assert "abc123" in first and "abc123" in python_first


class TestTheEmittedFilesMatchTheGenerator:
    async def test_the_committed_typescript_is_what_the_generator_emits(self):
        """The committed output is regenerable, which is what makes
        `git diff --exit-code` meaningful rather than a check on whether
        anyone ran the command."""
        from app.main import app

        digest = sdk_generate._hash(app.openapi())
        committed = (SDKS / "ts/src/client.ts").read_text()

        assert committed == sdk_generate.render_typescript(digest)

    async def test_the_committed_python_is_what_the_generator_emits(self):
        from app.main import app

        digest = sdk_generate._hash(app.openapi())
        committed = (SDKS / "python/darkmem_sdk/client.py").read_text()

        assert committed == sdk_generate.render_python(digest)

    async def test_the_generated_files_say_they_are_generated(self):
        """A generated file a human edits by hand loses the edit on the next
        run, silently. Saying so at the top is the cheapest guard there is."""
        for relative in ("ts/src/client.ts", "python/darkmem_sdk/client.py"):
            text = (SDKS / relative).read_text()
            assert "Generated by sdks/generate.py" in text
            assert "make generate" in text
