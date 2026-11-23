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

Those three were closed and a second review found **two more**, which is the
finding that matters: closing named instances is not closing the class.

- a TypeScript ``static`` member — on the *constructor*, so neither the
  prototype probe nor the instance probe sees it, and the source regex was
  anchored to exactly two leading spaces, which the generator itself writes;
- a Python ``def __call__`` — every whitelist filtered names on a leading
  underscore, so **no dunder could ever appear in one**, and an instance that
  is callable is a verb by any measure;

and a third round found two more, which is the finding rather than a footnote:

- a **symbol-keyed** TypeScript member (``[Symbol.for("send")]()``) —
  ``Object.getOwnPropertyNames`` enumerates no symbol in *any* of the three
  homes, so all three run-time probes were blind to one construct at once, and
  a computed key starts ``[`` where the source regex wants an identifier. The
  probes read ``Reflect.ownKeys`` now;
- a Python **instance** attribute (``self.send = lambda ...`` in ``__init__``)
  — ``vars(Darkmem)`` is the *class* dict and never moves. The TypeScript side
  had an instance probe from the previous round; this side had none.

So no check here filters by kind *or* by name shape any more. Each is an exact
whitelist of a whole surface: ``vars(Darkmem)`` including every dunder, the
module's names owned by that module, and the emitted TypeScript's members and
exports. The run-time probes in ``ts/src/client.test.ts`` cover all three
JavaScript homes a member can have — prototype, instance, constructor —
because a source scan reads none of them reliably.

Reach still missing, stated rather than implied: these scans read the emitted
files and the imported module, so a construct that changes the surface only
when something else happens (a ``__getattr__``, a metaclass, a monkeypatch at
import time) would pass. ``_post`` remains reachable by a caller who wants it.
Both are things a future defect could use, not things that hold today.
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

THE_TWO_VERBS_PY = {"capture", "search"}

# `vars(Darkmem)` in full, dunders included. Not "public names" — a whitelist
# that filters on a leading underscore can never see a `__call__`, and an
# instance you can call is a verb. The interpreter-supplied entries are listed
# rather than subtracted so a new one is a visible, deliberate edit.
PY_CLASS_MEMBERS = {
    "__dict__",
    "__doc__",
    "__firstlineno__",
    "__init__",
    "__module__",
    "__static_attributes__",
    "__weakref__",
    "_post",
    "capture",
    "search",
}
THE_TWO_VERBS_TS = {"capture", "search"}
BOUND_PATHS = {CAPTURE_PATH, SEARCH_PATH}

# Everything the Python client module is allowed to expose at module level:
# its two constants, the client, and the imports it needs. A new public name
# of any kind — a helper function, a second class — fails this.
PY_MODULE_PUBLIC = {
    "CAPTURE_PATH",
    "Darkmem",
    "SEARCH_PATH",
    "annotations",
    "httpx",
}

# Value exports of the TypeScript client. Types are erased at run time and are
# listed separately so a new *value* export cannot hide among them.
TS_VALUE_EXPORTS = {"Darkmem"}
TS_TYPE_EXPORTS = {
    "CaptureAck",
    "DarkmemOptions",
    "MemoryRow",
    "RetrievalEnvelope",
    "SearchResult",
}


def _typescript_class_members(source: str) -> set[str]:
    """Every member name declared directly in the class body.

    Deliberately not restricted to methods: a class **field** holding an arrow
    function is a method in every sense that matters to a caller, and the first
    version's `name(` shape missed exactly that. Nor to one indentation — the
    second version anchored on exactly two leading spaces, and the file's
    formatting is written by the very generator this defends against, so a
    `static` member at four spaces was invisible. Depth is tracked by counting
    braces instead, with comments and string literals removed first so a brace
    inside either cannot move it.

    A text scan is the secondary check regardless. `ts/src/client.test.ts`'s
    three run-time probes are the primary one: they read what the engine sees —
    prototype, instance and constructor — rather than what the text looks like.
    """
    body = _typescript_without_comments(source).split("export class Darkmem {", 1)[-1]
    body, _ = _mask_strings(body)

    members: set[str] = set()
    depth = 1
    # Parentheses too: a multi-line method signature keeps brace depth at 1
    # while its parameters sit inside `(`, and `query: string,` on its own line
    # is not a member declaration.
    parens = 0
    for line in body.splitlines():
        if depth == 1 and parens == 0:
            match = re.match(
                r"\s*(?:readonly\s+)?(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?"
                r"([A-Za-z_$#][\w$]*)\s*[(<:=;]",
                line,
            )
            if match:
                members.add(match.group(1))
        depth += line.count("{") - line.count("}")
        parens += line.count("(") - line.count(")")
        if depth <= 0:
            break
    return members


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


# Escapes handled: `"\"{"` is one literal holding a brace, and reading it as
# two would move the depth walk below. The placeholder uses NUL, which cannot
# occur in the source, because a literal `"__STR1__"` in the file collided with
# the substitution and corrupted the restore.
_STRING_LITERAL = re.compile(
    r'"(?:[^"\\\n]|\\.)*"' r"|'(?:[^'\\\n]|\\.)*'" r"|`(?:[^`\\]|\\.)*`"
)
_PLACEHOLDER = "\x00STR{}\x00"


def _mask_strings(source: str) -> tuple[str, list[str]]:
    """Replace every string literal with a placeholder, keeping the originals.

    Order matters and cost a round here: stripping `//` comments first eats the
    rest of any line holding a URL, because `http://` is two slashes. That
    truncated `(options.baseUrl ?? "http:` mid-expression, left an unbalanced
    parenthesis, and made the member scan below stop reading after the
    constructor — reporting a one-member class as if that were the truth.
    """
    kept: list[str] = []

    def take(match: re.Match) -> str:
        kept.append(match.group(0))
        return _PLACEHOLDER.format(len(kept) - 1)

    return _STRING_LITERAL.sub(take, source), kept


def _typescript_without_comments(source: str) -> str:
    """Comments removed, string literals intact.

    The literals are kept because a path or a verb name hiding in one is
    exactly what the scans below look for; only the comments are noise.
    """
    masked, kept = _mask_strings(source)
    without_block = re.sub(r"/\*[\s\S]*?\*/", "", masked)
    stripped = re.sub(r"//.*$", "", without_block, flags=re.MULTILINE)
    for index, literal in enumerate(kept):
        stripped = stripped.replace(_PLACEHOLDER.format(index), literal)
    return stripped


# Everything a constructed client is allowed to carry. `vars(Darkmem)` is the
# class dict and cannot see an attribute assigned in `__init__`, which is where
# a fourth verb sat through a green suite.
PY_INSTANCE_ATTRIBUTES = {"base_url", "token", "project"}


class TestThePublicSurfaceIsTheTwoVerbs:
    def test_a_constructed_client_carries_only_its_configuration(self):
        """The Python instance probe, matching the one the TypeScript suite has
        had since the class-field escape. `self.send = lambda ...` in
        `__init__` leaves every class-level whitelist byte-identical.

        **This probe is not total and must not be read as if it were.** An
        instance's attribute set is a function of the constructor's arguments,
        and both constructions below sit at the default `base_url`, so a
        member attached only under some *other* construction is invisible here
        — which is escape 8, found 2026-08-10 on the fourth reopening of this
        finding. The total check is a source walk over assignment targets,
        `backend/tests/test_sdk_generator.py::TestNoMemberCanBeAttachedConditionally`;
        it never constructs anything, so no branch can hide from it. This
        stays because it is the cheap one that fails first.
        """
        assert set(vars(Darkmem())) == PY_INSTANCE_ATTRIBUTES
        assert set(vars(Darkmem(token="t", project="p"))) == (
            PY_INSTANCE_ATTRIBUTES
        )

    def test_the_python_class_carries_no_member_it_was_not_given(self):
        """Every member, dunder included, against an exact whitelist.

        Two filters failed here in turn. `callable(classmethod(f))` is False,
        so a classmethod fourth verb sat on this class through a green suite;
        then `startswith("_")` meant a `def __call__` could not appear in the
        set at all, and `Darkmem(token=...)(path, body)` reached the ratify
        door. Neither kind nor name shape decides membership now.
        """
        assert set(vars(Darkmem)) == PY_CLASS_MEMBERS
        # The two verbs are in there, so the whitelist cannot be satisfied by
        # a client that lost them.
        assert THE_TWO_VERBS_PY <= PY_CLASS_MEMBERS

    def test_the_python_module_exposes_no_other_public_name(self):
        """A module-level `async def send(client, path, body)` is on no class
        and reaches any door. Neither the class whitelist nor `vars(package)`
        can see it — this is the surface that can."""
        public = {name for name in vars(client_module) if not name.startswith("_")}
        assert public == PY_MODULE_PUBLIC

    def test_the_python_module_defines_only_the_client(self):
        """The name-shape-free half of the same check: anything *defined here*
        rather than imported, whatever it is called. An underscore-prefixed
        module-level helper is as reachable as a public one."""
        owned = {
            name
            for name, value in vars(client_module).items()
            if getattr(value, "__module__", None) == client_module.__name__
        }
        assert owned == {"Darkmem"}

    def test_the_package_exports_only_the_client(self):
        assert darkmem_sdk.__all__ == ["Darkmem"]
        exported = {name for name in vars(darkmem_sdk) if not name.startswith("_")}
        assert exported == {"Darkmem", "client"}

    def test_the_typescript_class_exposes_exactly_two_verbs(self):
        members = _typescript_class_members(TYPESCRIPT_CLIENT.read_text())
        public = {name for name in members if not name.startswith("#")}
        assert public == THE_TWO_VERBS_TS | {"constructor"}

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


class TestTheCommentStripperItself:
    """`_typescript_without_comments` is what every source scan below reads,
    so a regression in it silently weakens all of them at once — and it has
    regressed once already: stripping `//` comments before masking string
    literals ate the rest of any line holding a URL, truncated
    `(options.baseUrl ?? "http:` mid-expression, and made the member scan stop
    reading after the constructor while reporting a one-member class as the
    truth.

    The hardening was shipped with no test of its own (rescope NEW-6): it was
    covered only transitively, by scans that happen to pass on today's client.
    A future regression of either regex would keep those green on a file that
    no longer parses the way they assume, so the helper is pinned directly on
    the three shapes that broke it or would.
    """

    def test_a_url_in_a_literal_survives_comment_stripping(self):
        """The exact regression. `http://` is two slashes inside a string."""
        source = 'const a = (o.baseUrl ?? "http://localhost:8000"); // trailing'

        stripped = _typescript_without_comments(source)

        assert '"http://localhost:8000"' in stripped
        assert "trailing" not in stripped

    def test_an_escaped_quote_does_not_end_the_literal(self):
        """`"\\"{"` is one literal holding a brace. Reading it as two moves the
        brace-depth walk the member scan depends on."""
        source = 'const a = "she said \\"{\\" loudly"; // gone\nconst b = 1;'

        stripped = _typescript_without_comments(source)

        assert 'she said \\"{\\" loudly' in stripped
        assert "gone" not in stripped
        assert "const b = 1;" in stripped

    def test_a_literal_shaped_like_the_placeholder_round_trips(self):
        """The placeholder is NUL-delimited precisely because a literal
        `"__STR0__"` in the source collided with the substitution and corrupted
        the restore. If someone 'tidies' NUL back to underscores, this fails."""
        source = 'const a = "__STR0__"; const b = "real"; /* c */'

        stripped = _typescript_without_comments(source)

        assert '"__STR0__"' in stripped
        assert '"real"' in stripped
        assert "c */" not in stripped

    def test_a_block_comment_between_literals_goes_without_taking_them(self):
        source = 'const a = "keep"; /* drop\nme */ const b = "keep2";'

        stripped = _typescript_without_comments(source)

        assert '"keep"' in stripped and '"keep2"' in stripped
        assert "drop" not in stripped
