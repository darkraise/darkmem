"""T3.25 / T3.14 — the SDK generator (doc 15 §6).

T3.25's done-when is "the generator is named and runs from a documented
command; both packages build; regeneration is idempotent". Two of those three
are checked by the task's own Verify (``cd sdks && make generate && git diff
--exit-code``), which is where they belong — this file pins the properties that
command cannot see.

**Doc 15 §6's reason for generating at all**: it "guarantees the SDK never
drifts from the two front doors … it enforces invariant 17 (the SDK cannot
expose a behaviour the contract does not)". A generator that emitted a method
for a route the contract had dropped would satisfy every idempotence check and
break that guarantee, so the binding between verb and contract surface is what
is tested here.

**T3.14 widened the binding from routes to fields, and this file with it.**
The route-level guard passed while both emitted clients posted an
``applies_when`` key that no request schema in the contract has: every door
ignored it, so a declared context reached nothing and nothing said so. Route
existence cannot see that, which is why ``_require_contract`` now checks the
request-body fields and the ``X-Darkmem-Context`` header too, and why each of
the three refusals below has its own mutation.

The SDK-side behaviour tests are not here — they live with the packages
(``sdks/python/tests/`` and ``sdks/ts/src/client.test.ts``, T3.14's Verify),
because they exercise the emitted client rather than the generator.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import pytest

SDKS = Path(__file__).resolve().parents[2] / "sdks"
sys.path.insert(0, str(SDKS))

import generate as sdk_generate  # noqa: E402

pytestmark = pytest.mark.asyncio


def _schema_copy() -> dict:
    """A private copy of the contract.

    `app.openapi()` **caches** and returns the same object every call, so a
    test that mutates it corrupts the schema for every later test in the
    session — which is exactly what an earlier version of the two hash tests
    below did, and how they made the emitted-file comparisons fail against
    correct code. Deep-copied here so a probe stays a probe.
    """
    from app.main import app

    return deepcopy(app.openapi())


class TestTheContractBinding:
    async def test_every_verb_names_a_surface_the_contract_serves(self):
        """The invariant-17 guarantee, checked against the live schema rather
        than a committed copy — a checked-in contract can age into agreeing
        with an SDK that no longer matches the app."""
        sdk_generate._require_contract(_schema_copy())

    async def test_every_bound_route_exists_with_every_field_it_sends(self):
        """The same property spelled out, so a failure names which half broke
        rather than only that the refusal fired."""
        schema = _schema_copy()
        for name, verb in sdk_generate.VERBS.items():
            if "header" in verb:
                continue
            operations = schema["paths"].get(verb["path"], {})
            assert verb["method"] in operations, f"{name} → {verb['path']}"
            properties = sdk_generate._request_properties(schema, verb)
            for field in verb["fields"]:
                assert field in properties, f"{name} → {verb['path']}.{field}"

    async def test_generation_refuses_when_a_route_is_missing(self, monkeypatch):
        """The refusal is the enforcement. Without it the generator would
        happily emit a method that calls a 404, which is the drift doc 15 §6
        generates the SDK to prevent."""
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "capture",
            {
                "method": "post",
                "path": "/api/v1/route-that-does-not-exist",
                "fields": ("content",),
            },
        )

        with pytest.raises(SystemExit, match="refusing to generate"):
            sdk_generate._require_contract(_schema_copy())

    async def test_generation_refuses_when_a_field_is_missing(self, monkeypatch):
        """T3.14's guard, and its regression test: ``applies_when`` is the
        exact key both clients used to post. The route exists, the method
        exists, and the SDK still spoke a language the door does not."""
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "capture",
            {
                "method": "post",
                "path": "/api/v1/memories",
                "fields": ("content", "applies_when"),
            },
        )

        with pytest.raises(SystemExit, match="has no field 'applies_when'"):
            sdk_generate._require_contract(_schema_copy())

    async def test_generation_refuses_when_the_context_header_drifts(
        self, monkeypatch
    ):
        """Doc 12 §5 settles per-session context as a header because a
        stateful declare tool "would be a lie on a stateless_http=True
        server". There is therefore no route to bind, and an unchecked
        literal would let a rename silently point the SDK at a header nothing
        reads — the same failure as a missing route, given the same refusal."""
        monkeypatch.setitem(
            sdk_generate.VERBS, "declareContext", {"header": "X-Darkmem-Ctx"}
        )

        with pytest.raises(SystemExit, match="X-Darkmem-Ctx"):
            sdk_generate._require_contract(_schema_copy())

    async def test_the_pinned_header_is_the_one_the_app_resolves(self):
        from app.api.context_resolution import DECLARED_CONTEXT_HEADER

        assert (
            sdk_generate.CONTEXT_HEADER.lower() == DECLARED_CONTEXT_HEADER.lower()
        )

    async def test_the_surface_is_three_verbs(self):
        """Doc 15 §6 is explicit that darkmem is not building a client
        platform: `capture`, `search`, `declareContext` and nothing else. A
        fourth verb is a design decision, not a generator change."""
        assert set(sdk_generate.VERBS) == {"capture", "search", "declareContext"}

    async def test_search_binds_the_composed_read(self):
        """Doc 15 §6 defines the verb as "the F3 read" returning "the labelled
        results with their trace" and gives it a `fused?` argument. Only
        `/api/v1/knowledge/search` serves any of that — the plain memories
        search answers a bare list with no envelope, no layer or verification
        labels and no `fuse` axis, so binding there would have satisfied the
        route guard while delivering none of the verb's stated behaviour."""
        assert sdk_generate.VERBS["search"]["path"] == "/api/v1/knowledge/search"
        assert "fuse" in sdk_generate.VERBS["search"]["fields"]


class TestDeterminism:
    async def test_the_contract_hash_covers_only_the_bound_surface(self):
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

    async def test_the_hash_moves_when_a_bound_field_changes(self):
        """A field's *type* can change without its name moving, and the SDK
        keeps posting it — so the digest covers the field schemas, not merely
        their presence."""
        schema = _schema_copy()
        before = sdk_generate._hash(schema)

        schema["components"]["schemas"]["KnowledgeSearchRequest"]["properties"][
            "limit"
        ]["type"] = "string"

        assert sdk_generate._hash(schema) != before

    async def test_the_hash_moves_when_the_header_is_renamed(self, monkeypatch):
        schema = _schema_copy()
        before = sdk_generate._hash(schema)

        monkeypatch.setitem(
            sdk_generate.VERBS, "declareContext", {"header": "X-Darkmem-Ctx"}
        )

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
        digest = sdk_generate._hash(_schema_copy())
        committed = (SDKS / "ts/src/client.ts").read_text()

        assert committed == sdk_generate.render_typescript(digest)

    async def test_the_committed_python_is_what_the_generator_emits(self):
        digest = sdk_generate._hash(_schema_copy())
        committed = (SDKS / "python/darkmem_sdk/client.py").read_text()

        assert committed == sdk_generate.render_python(digest)

    async def test_the_generated_files_say_they_are_generated(self):
        """A generated file a human edits by hand loses the edit on the next
        run, silently. Saying so at the top is the cheapest guard there is."""
        for relative in ("ts/src/client.ts", "python/darkmem_sdk/client.py"):
            text = (SDKS / relative).read_text()
            assert "Generated by sdks/generate.py" in text
            assert "make generate" in text
