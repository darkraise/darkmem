"""T3.14 — what the SDK *cannot* express, asserted rather than reviewed.

Doc 15 §6 is explicit about the omission: ratification, review and vault
administration "are **not** in the SDK: those are human-authenticated REST/UI
actions". The task's done-when says the absence is asserted "by a test that
greps the generated surface, not by review".

**This file has been through a review that defeated it three ways, and the
lesson is written into its shape.** The first version filtered class members on
``callable``, matched TypeScript members with a regex requiring ``(`` after the
name, and checked the prototype. All three drills passed every suite while the
emitted client ratified a fact:

- a TypeScript **class field** (``send = async (...) => {...}``) — invisible to
  a regex expecting ``(``, and an *instance* property, so absent from the
  prototype;
- a Python **classmethod** — ``callable(classmethod(f))`` is ``False``, so the
  whitelist's own filter hid it;
- a **module-level function** in either language — on no class at all.

So the checks are now whitelists over three surfaces rather than one, and none
of them filters by kind: the class's whole public attribute set, the module's
whole public name set, and the emitted TypeScript's whole member and export
set. A fourth verb has to survive all of them, and the run-time probes in
``ts/src/client.test.ts`` (prototype **and** instance) cover the TypeScript
constructs a source scan reads poorly.

Reach still missing, stated rather than implied: Python's ``_post`` is a naming
convention that a determined caller can reach, and these scans read the emitted
files rather than executing the Python client, so a construct that changes the
surface only at run time (a metaclass, a ``__getattr__``) would pass. Both are
noted as things a future defect could use, not as things that hold today.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import darkmem_sdk
import darkmem_sdk.client as client_module
from darkmem_sdk.client import CAPTURE_PATH, SEARCH_PATH, Darkmem

SDKS = Path(__file__).resolve().parents[2]
PYTHON_CLIENT = SDKS / "python/darkmem_sdk/client.py"
TYPESCRIPT_CLIENT = SDKS / "ts/src/client.ts"

THE_THREE_VERBS_PY = {"capture", "search", "declare_context"}
THE_THREE_VERBS_TS = {"capture", "search", "declareContext"}
BOUND_PATHS = {CAPTURE_PATH, SEARCH_PATH}

# Everything the Python client module is allowed to expose at module level:
# its three constants, the client, and the imports it needs. A new public name
# of any kind — a helper function, a second class — fails this.
PY_MODULE_PUBLIC = {
    "Any",
    "CAPTURE_PATH",
    "CONTEXT_HEADER",
    "Darkmem",
    "SEARCH_PATH",
    "annotations",
    "httpx",
    "json",
}

# Value exports of the TypeScript client. Types are erased at run time and are
# listed separately so a new *value* export cannot hide among them.
TS_VALUE_EXPORTS = {"Darkmem"}
TS_TYPE_EXPORTS = {
    "CaptureAck",
    "DarkmemOptions",
    "DeclaredContext",
    "MemoryRow",
    "RetrievalEnvelope",
    "SearchResult",
}


def _typescript_class_members(source: str) -> set[str]:
    """Every member name declared at class-body indentation.

    Deliberately not restricted to methods: a class **field** holding an arrow
    function is a method in every sense that matters to a caller, and the
    earlier `name(` shape missed exactly that. Two-space indentation is the
    generator's own formatting, which is what makes this parseable without a
    TypeScript parser.
    """
    body = source.split("export class Darkmem {", 1)[-1]
    return set(
        re.findall(
            r"^  (?:readonly\s+)?(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?"
            r"([A-Za-z_$#][\w$]*)\s*[(<:=;]",
            body,
            re.MULTILINE,
        )
    )


def _typescript_exports(source: str) -> tuple[set[str], set[str]]:
    """(value exports, type exports) declared by the emitted client."""
    values = set(
        re.findall(r"^export (?:class|const|function|let|var)\s+([A-Za-z_$][\w$]*)",
                   source, re.MULTILINE)
    )
    types = set(
        re.findall(r"^export (?:interface|type)\s+([A-Za-z_$][\w$]*)",
                   source, re.MULTILINE)
    )
    return values, types


def _python_code_names(source: str) -> set[str]:
    """Every identifier and non-docstring string constant in the Python client.

    Docstrings are excluded deliberately: the class docstring *explains* the
    omission and names the ratify door's posture, so a prose scan would fail on
    the sentence documenting the property being asserted.
    """
    tree = ast.parse(source)
    docstrings = {
        ast.get_docstring(node, clean=False)
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value not in docstrings:
                names.add(node.value)
    return names


def _typescript_without_comments(source: str) -> str:
    without_block = re.sub(r"/\*[\s\S]*?\*/", "", source)
    return re.sub(r"//.*$", "", without_block, flags=re.MULTILINE)


class TestThePublicSurfaceIsTheThreeVerbs:
    def test_the_python_class_exposes_exactly_three_public_attributes(self):
        """No `callable` filter. `callable(classmethod(f))` is False, which is
        how a classmethod fourth verb sat on this class through a whole green
        suite; a property or a staticmethod would have done the same."""
        public = {
            name for name in dir(Darkmem) if not name.startswith("_")
        } - set(dir(object))
        assert public == THE_THREE_VERBS_PY

    def test_the_python_module_exposes_no_other_public_name(self):
        """A module-level `async def send(client, path, body)` is on no class
        and reaches any door. Neither the class whitelist nor `vars(package)`
        can see it — this is the surface that can."""
        public = {name for name in vars(client_module) if not name.startswith("_")}
        assert public == PY_MODULE_PUBLIC

    def test_the_package_exports_only_the_client(self):
        assert darkmem_sdk.__all__ == ["Darkmem"]
        exported = {name for name in vars(darkmem_sdk) if not name.startswith("_")}
        assert exported == {"Darkmem", "client"}

    def test_the_typescript_class_exposes_exactly_three_members(self):
        members = _typescript_class_members(TYPESCRIPT_CLIENT.read_text())
        public = {name for name in members if not name.startswith("#")}
        assert public == THE_THREE_VERBS_TS | {"constructor"}

    def test_the_typescript_module_exports_only_the_client(self):
        values, types = _typescript_exports(TYPESCRIPT_CLIENT.read_text())
        assert values == TS_VALUE_EXPORTS
        assert types == TS_TYPE_EXPORTS

    def test_the_typescript_transport_is_hard_private(self):
        """`private` is erased at compile time and leaves the method on the
        prototype; `#` does not. A `private post()` would satisfy the type
        checker and still let any caller reach an arbitrary path at run time.

        Scanned over the comment-stripped source: a doc comment that happens to
        use the word "private" is not a defect, and failing the build on one
        teaches the next reader to delete the check."""
        source = TYPESCRIPT_CLIENT.read_text()
        assert "#post" in _typescript_class_members(source)
        assert "private" not in _typescript_without_comments(source)


class TestNoOtherDoorIsReachable:
    @pytest.mark.parametrize("client", [PYTHON_CLIENT, TYPESCRIPT_CLIENT])
    def test_the_only_route_literals_are_the_bound_paths(self, client: Path):
        """Ratification lives at `POST /api/v1/knowledge/facts/{id}/ratify`.
        No third path literal means no third door, whatever it is named."""
        literals = set(re.findall(r'"(/api/[^"]*)"', client.read_text()))
        assert literals == BOUND_PATHS

    @pytest.mark.parametrize("client", [PYTHON_CLIENT, TYPESCRIPT_CLIENT])
    def test_no_path_is_assembled_from_pieces(self, client: Path):
        """The whitelist above only holds while paths are whole literals. A
        client that concatenated `/api/v1/knowledge/` with a suffix would pass
        it while reaching anywhere; the bound paths are the only `/api/`
        fragments in either file, so there is nothing to build from.

        Not redundant with the test above, and measured rather than assumed: a
        drill that added a `ratify` method to both clients failed the quoted
        literal check on the Python one and **passed** it on the TypeScript
        one, because the interpolated path was in backticks. This is what
        caught it.
        """
        fragments = set(re.findall(r"/api/[\w/{}.-]*", client.read_text()))
        assert fragments == BOUND_PATHS


class TestTheWordItself:
    """The done-when's literal reading — kept as a last line, not the first."""

    def test_ratify_is_not_a_name_in_the_python_client(self):
        names = _python_code_names(PYTHON_CLIENT.read_text())
        assert not [name for name in names if "ratif" in name.lower()]

    def test_ratify_appears_nowhere_in_the_typescript_client(self):
        code = _typescript_without_comments(TYPESCRIPT_CLIENT.read_text())
        assert "ratif" not in code.lower()
