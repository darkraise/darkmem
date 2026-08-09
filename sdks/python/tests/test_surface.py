"""T3.14 — what the SDK *cannot* express, asserted rather than reviewed.

Doc 15 §6 is explicit about the omission and about why it matters: ratification,
review and vault administration "are **not** in the SDK: those are
human-authenticated REST/UI actions … and putting them in a LAN client SDK
would hand ``confirmed``-power to an unauthenticated caller". The task's own
done-when says the absence is asserted "by a test that greps the generated
surface, not by review".

**A grep alone is worth exactly its reach, and this file's primary assertion is
therefore a whitelist rather than a blocklist.** Searching for the word
"ratify" is defeated by a renamed method, a computed path, a base-URL join, or
any verb nobody thought to forbid. So the load-bearing checks are positive: the
public callable surface *is* the three verbs, and the only route literals in
either client *are* the two bound paths. A fourth verb fails the first even if
it is called something none of us imagined; a call to any other endpoint fails
the second even if it never spells the word.

What that pair still cannot see: a caller that reaches the transport through
the module's imports rather than the class. The TypeScript side closes that at
run time — the transport is a ``#private`` method, so it does not exist on the
prototype (asserted in ``ts/src/client.test.ts``) — while the Python side rests
on the ``_post`` convention, which a determined caller can defeat. Stated here
because a scan that overstates its reach is worse than no scan.

Both files are generated, so these are assertions about the *generator*: the
way to break one is to change ``sdks/generate.py``, which is the point.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import darkmem_sdk
from darkmem_sdk.client import CAPTURE_PATH, SEARCH_PATH, Darkmem

SDKS = Path(__file__).resolve().parents[2]
PYTHON_CLIENT = SDKS / "python/darkmem_sdk/client.py"
TYPESCRIPT_CLIENT = SDKS / "ts/src/client.ts"

THE_THREE_VERBS_PY = {"capture", "search", "declare_context"}
THE_THREE_VERBS_TS = {"capture", "search", "declareContext"}
BOUND_PATHS = {CAPTURE_PATH, SEARCH_PATH}


def _typescript_class_members(source: str) -> set[str]:
    """Member names declared at class-body indentation in the emitted client.

    Two-space indentation is the generator's own formatting, which is what
    makes this parseable without a TypeScript parser — and what makes it this
    repo's file rather than a general one.
    """
    return set(
        re.findall(
            r"^  (?:readonly\s+)?(?:async\s+)?([A-Za-z_$#][\w$]*)\s*(?:<[^>]*>)?\(",
            source,
            re.MULTILINE,
        )
    )


def _python_code_names(source: str) -> set[str]:
    """Every identifier and non-docstring string constant in the Python client.

    Docstrings are excluded deliberately: the class docstring *explains* the
    omission and names ``confirmed``-power, so a prose scan would fail on the
    sentence that documents the very property being asserted.
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
    def test_the_python_client_exposes_exactly_three_callables(self):
        callables = {
            name
            for name, value in vars(Darkmem).items()
            if not name.startswith("_") and callable(value)
        }
        assert callables == THE_THREE_VERBS_PY

    def test_the_package_exports_only_the_client(self):
        assert darkmem_sdk.__all__ == ["Darkmem"]
        exported = {name for name in vars(darkmem_sdk) if not name.startswith("_")}
        assert exported == {"Darkmem", "client"}

    def test_the_typescript_client_exposes_exactly_three_methods(self):
        members = _typescript_class_members(TYPESCRIPT_CLIENT.read_text())
        public = {name for name in members if not name.startswith("#")}
        assert public == THE_THREE_VERBS_TS | {"constructor"}

    def test_the_typescript_transport_is_hard_private(self):
        """`private` is erased at compile time and leaves the method on the
        prototype; `#` does not. A `private post()` would satisfy the type
        checker and still let any caller reach an arbitrary path at run time,
        which is exactly the escape hatch this file exists to close."""
        members = _typescript_class_members(TYPESCRIPT_CLIENT.read_text())
        assert "#post" in members
        assert "private" not in TYPESCRIPT_CLIENT.read_text()


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
        fragments in either file, so there is nothing to build from."""
        fragments = set(re.findall(r"/api/[\w/{}.-]*", client.read_text()))
        assert fragments == BOUND_PATHS


class TestTheWordItself:
    """The done-when's literal reading — kept as a second line, not the first."""

    def test_ratify_is_not_a_name_in_the_python_client(self):
        names = _python_code_names(PYTHON_CLIENT.read_text())
        assert not [name for name in names if "ratif" in name.lower()]

    def test_ratify_appears_nowhere_in_the_typescript_client(self):
        code = _typescript_without_comments(TYPESCRIPT_CLIENT.read_text())
        assert "ratif" not in code.lower()
