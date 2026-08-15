"""TH1.17 — the executable half of "import the bars, never restate them".

Mirrors ``tests/test_chat_retrieval_parity.py``'s two ``RRF_K`` legs exactly:
a scan for the **binding**, never the literal — a scan for ``0.95`` proves
nothing (the number is a coincidence away from being right and a rename
away from being wrong), while a scan for the write is the event that
creates a second source of truth.

Lives under ``backend/tests/`` — the repo floor, collected by a plain
``pytest -q`` — rather than under ``scripts/benchlib/tests/``, because
TH1.09's future role-wiring lands under ``app/`` and the floor is what a
reviewer runs by default; a scan that only ran under the harness suite
would leave that landing unprotected on the path most people take. Scope is
``backend/app`` and ``backend/scripts/benchlib``: TH1.09 wires the role
under the former, this task's own runner lives under the latter, and a
restatement risk exists in either.

``FAITHFULNESS_BARS`` is read at collection time, so a fourth bar joining
the module is scanned for automatically — nobody has to remember to widen
this file when the goalposts do.

**Known limit, inherited from the ``RRF_K`` scans this mirrors, not closed
here.** Both legs key on the word "faithfulness" (or on one of the three
committed bar-key strings for the dict-key leg); a neutrally-named
restatement such as ``PRECISION_BAR = 0.95`` in some other module matches
neither leg and passes the scan undetected. The dict-key leg is strictly
*stronger* than its ``RRF_K`` counterpart (it also catches a copy-pasted
dict literal under any variable name, so long as the *keys* are the bar
strings), but a bare neutrally-named numeric constant that happens to equal
a bar's value is a restatement no AST scan here can distinguish from an
unrelated number. Do not widen this scan to chase that; it is the same
inherent limit doc 07's parity discussion already accepts for ``RRF_K``.
"""
from __future__ import annotations

import ast
import pathlib
import re

from app.services import faithfulness_bars as fb

APP_ROOT = pathlib.Path(__file__).resolve().parents[1] / "app"
BACKEND_ROOT = APP_ROOT.parent
BENCHLIB_ROOT = BACKEND_ROOT / "scripts" / "benchlib"
CANONICAL = APP_ROOT / "services" / "faithfulness_bars.py"

BAR_KEYS = tuple(fb.FAITHFULNESS_BARS)
DEFAULT_NAMES = ("FAITHFULNESS_BAR_DEFAULTS", "FAITHFULNESS_BARS")

# "faithfulness" anywhere, any case, is distinctive enough on its own (unlike
# RRF, no separate lower-case/number-only leg is needed): nothing in this
# tree spells that word by coincidence. A name is still only flagged when
# it is bound to a numeric literal OR spelled in the upper-case constant
# convention -- an ordinary variable computed from a call
# (``faithfulness_coverage = compute()``) is a use, not a restatement.
FAITHFULNESS_NAME = re.compile(r"faithfulness", re.IGNORECASE)
CONSTANT_NAME = re.compile(r"FAITHFULNESS")


def _scanned_sources() -> list[pathlib.Path]:
    sources = []
    for root in (APP_ROOT, BENCHLIB_ROOT):
        for path in sorted(root.rglob("*.py")):
            if path == CANONICAL:
                continue
            if "tests" in path.relative_to(BACKEND_ROOT).parts:
                continue
            sources.append(path)
    return sources


def _bound_names(target: ast.expr):
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _bound_names(element)
    elif isinstance(target, ast.Starred):
        yield from _bound_names(target.value)


def _numeric_declarations(tree: ast.AST):
    """Every binding that could be a second faithfulness-bar constant:
    assignment, annotated assignment, augmented assignment, and the walrus
    all bind and are all walked, exactly as the RRF_K scan does."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            if node.value is None:
                continue
            targets, value = [node.target], node.value
        elif isinstance(node, (ast.AugAssign, ast.NamedExpr)):
            targets, value = [node.target], node.value
        else:
            continue
        numeric = (
            isinstance(value, ast.Constant)
            and isinstance(value.value, (int, float))
            and not isinstance(value.value, bool)
        )
        for name in (n for t in targets for n in _bound_names(t)):
            if CONSTANT_NAME.search(name) or (FAITHFULNESS_NAME.search(name) and numeric):
                yield name, node.lineno


def _dict_key_declarations(tree: ast.AST):
    """A dict literal restating one of the three committed bar *keys* with
    a numeric value -- catches copy-pasting ``FAITHFULNESS_BARS`` or
    ``FAITHFULNESS_BAR_DEFAULTS`` into a local mirror under a different
    variable name, which the name-binding leg above cannot see because
    nothing there is named ``faithfulness`` anything."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value in BAR_KEYS
                and isinstance(value, ast.Constant)
                and isinstance(value.value, (int, float))
                and not isinstance(value.value, bool)
            ):
                yield key.value, node.lineno


def test_no_second_faithfulness_bar_constant_is_declared_outside_its_module():
    offenders = []
    for path in _scanned_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders += [
            f"{path.relative_to(BACKEND_ROOT)}:{line} declares {name}"
            for name, line in _numeric_declarations(tree)
        ]
        offenders += [
            f"{path.relative_to(BACKEND_ROOT)}:{line} restates bar key {key!r} "
            f"with a literal value"
            for key, line in _dict_key_declarations(tree)
        ]
    assert offenders == [], (
        "a faithfulness bar is restated outside faithfulness_bars.py: "
        + "; ".join(offenders)
    )


def test_every_module_using_the_faithfulness_bar_defaults_imports_them():
    """The other half: a module may not obtain the defaults from a copy
    someone else re-exported."""
    offenders = []
    for path in _scanned_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        used = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id in DEFAULT_NAMES
        }
        if not used:
            continue
        imported = {
            alias.asname or alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").endswith("faithfulness_bars")
            for alias in node.names
        }
        missing = sorted(used - imported)
        if missing:
            offenders.append(f"{path.relative_to(BACKEND_ROOT)} uses {missing} without importing them")
    assert offenders == [], "; ".join(offenders)
