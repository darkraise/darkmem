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

**T3.14 widened the binding twice, and this file with it.** The route-level
guard passed while both emitted clients posted an ``applies_when`` key that no
request schema in the contract has: every door ignored it, so a declared
context reached nothing and nothing said so. Route existence cannot see that,
which is why ``_require_contract`` checks the request-body fields and the
``X-Darkmem-Context`` header too.

A review then defeated the widened version twice more. The **field tuple** was
checked while the *emitted body* was not, so an extra key added to a template
generated cleanly; the body literals are now rendered from that same tuple
(``_body``), and the test below drills it. And the header was checked for
**spelling** while nothing asked whether any bound door *read* it — it did not,
on either. That refusal is here; the proof that the new binding is actually
consumed is ``test_sdk_contract_conformance.py``, which drives the real app,
because no schema check can answer it.

Every refusal below has its own mutation.

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
        generates the SDK to prevent.

        Matched on the route arm's own message rather than on "refusing to
        generate". A mutation drill found the looser assertion green with the
        route check deleted: a path the contract lacks has no request schema
        either, so the *field* arm refuses instead and a reader would be told
        the route guard held when it was gone.
        """
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "capture",
            {
                "method": "post",
                "path": "/api/v1/route-that-does-not-exist",
                "fields": ("content",),
                "carries_context": False,
            },
        )

        with pytest.raises(
            SystemExit, match=r"capture → POST /api/v1/route-that-does-not-exist"
        ):
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
                "carries_context": False,
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

    async def test_generation_refuses_a_context_verb_on_a_door_without_the_field(
        self, monkeypatch
    ):
        """The refusal a review had to find by driving the app. `carries_context`
        means the SDK puts `X-Darkmem-Context` on that request; a door with no
        rank-1 `context` argument is not in doc 12 §5's chain at all, and the
        header dies there in silence.

        `POST /api/v1/memories` is the real case: it is the capture door, it
        exists, its fields all check out, and it resolves no context on either
        rank."""
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "search",
            {
                "method": "post",
                "path": "/api/v1/memories",
                "fields": ("content",),
                "carries_context": True,
            },
        )

        with pytest.raises(SystemExit, match="not in doc 12 §5's declared-context chain"):
            sdk_generate._require_contract(_schema_copy())

    async def test_generation_refuses_when_no_verb_carries_the_header(
        self, monkeypatch
    ):
        """The other half, and the one that makes the first un-evadable: the
        header binds a mechanism rather than a door, so turning every verb's
        `carries_context` off satisfies the per-verb check by having no verbs
        to check. That is precisely the state the SDK shipped in."""
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "search",
            {**sdk_generate.VERBS["search"], "carries_context": False},
        )

        with pytest.raises(SystemExit, match="would reach no door at all"):
            sdk_generate._require_contract(_schema_copy())

    async def test_the_surface_is_three_verbs(self):
        """Doc 15 §6 is explicit that darkmem is not building a client
        platform: `capture`, `search`, `declareContext` and nothing else. A
        fourth verb is a design decision, not a generator change."""
        assert set(sdk_generate.VERBS) == {"capture", "search", "declareContext"}

    async def test_search_binds_the_door_that_serves_the_context_chain(self):
        """Doc 01 F3 is the memory retrieval flow returning "ranked results
        with a 'why retrieved' trace", and doc 15 §6's own mermaid names the
        memories twin. An earlier round bound the composed read on the strength
        of doc 15 §6's `fused?` argument; that door serves neither rank of doc
        12 §5's context chain, which is how `declareContext` came to reach
        nothing. `fused` is the cost, recorded rather than faked."""
        verb = sdk_generate.VERBS["search"]
        assert verb["path"] == "/api/v1/memories/search/paginated"
        assert verb["carries_context"] is True
        assert sdk_generate.CONTEXT_FIELD in verb["fields"]
        assert "with_trace" in verb["fields"]
        assert not any(
            "fuse" in v.get("fields", ()) for v in sdk_generate.VERBS.values()
        )

    async def test_capture_carries_no_context(self):
        """`MemoryCreate` has no `context` field and the route reads no header,
        so doc 15 §6's `capture(content, project?, context?, source?)` names an
        argument the contract does not serve. Doc 15 §6 defers the wire shape
        to doc 12, so the contract wins and the argument is absent."""
        verb = sdk_generate.VERBS["capture"]
        assert verb["carries_context"] is False
        assert sdk_generate.CONTEXT_FIELD not in verb["fields"]

        properties = sdk_generate._request_properties(_schema_copy(), verb)
        assert sdk_generate.CONTEXT_FIELD not in properties


class TestTheEmittedBodyIsTheDeclaredFields:
    """The drill that got past the field guard: the tuple was checked, the
    literal the template posted was not. Both clients' bodies are now rendered
    from the tuple, so the two cannot say different things."""

    async def test_the_python_body_keys_are_exactly_the_declared_fields(self):
        """Parsed out of the **emitted client**, not out of `_body`'s return
        value. Comparing the renderer against itself would pass while a key
        sat in the template beside the rendered block, which is the same
        never-checked gap in a new place."""
        import ast

        tree = ast.parse(sdk_generate.render_python("digest"))
        posted = {
            node.name: [
                key.value
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and getattr(call.func, "attr", None) == "_post"
                for argument in call.args
                if isinstance(argument, ast.Dict)
                for key in argument.keys
            ]
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name != "_post"
        }
        assert posted == {
            "capture": list(sdk_generate.VERBS["capture"]["fields"]),
            "search": list(sdk_generate.VERBS["search"]["fields"]),
        }

    async def test_the_typescript_body_keys_are_exactly_the_declared_fields(self):
        """The same property on the other client, read out of the emitted
        source for the same reason."""
        import re

        emitted = sdk_generate.render_typescript("digest")
        for verb_name in ("capture", "search"):
            block = re.search(
                r'#post<\w+>\(\s*"[^"]+",\s*\{(.*?)\n      \},',
                emitted.split(f"async {verb_name}(", 1)[-1],
                re.DOTALL,
            )
            assert block, f"no post body found for {verb_name}"
            keys = re.findall(r"^\s*([\w$]+):", block.group(1), re.MULTILINE)
            assert keys == list(sdk_generate.VERBS[verb_name]["fields"])

    async def test_a_field_with_no_expression_refuses_rather_than_emitting(
        self, monkeypatch
    ):
        """The remaining way to declare a field and not send it. Refusing here
        keeps `fields` honest in both directions: every declared field is
        checked against the contract *and* reaches the wire."""
        monkeypatch.setitem(
            sdk_generate.VERBS,
            "capture",
            {**sdk_generate.VERBS["capture"], "fields": ("content", "importance")},
        )

        with pytest.raises(SystemExit, match="no expression to emit"):
            sdk_generate._body("capture", sdk_generate.PY_EXPRESSIONS, "", True)


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

        schema["components"]["schemas"]["MemorySearchRequest"]["properties"][
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
