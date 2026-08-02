"""Shared AST reachability scanner for invariant-15's hot-path guards.

`tests/test_dream_jobs.py`'s dream-job family scan and
`tests/test_communities.py`'s detector scan ask the same question of every
file under `app/`: does this file reach a forbidden module, a forbidden
attribute access, or a forbidden literal — outside its own small set of
allowlisted exemptions? Before T2.67 each guard answered that with its own
line-based or ad-hoc walk; the family scan's was line-based and a
parenthesised multi-line import (the form an autoformatter produces) defeated
it outright, because no single line named both the package and the module.
T2.18's detector scan had already solved that with a real AST walk, and
T2.45's supersession-pointer scan solved a structurally different but
overlapping problem the same way — this module lifts the shared shape of
both into one scanner, parameterised on each caller's own forbidden
vocabulary, so a future forbidden-reach guard reuses it instead of growing a
third copy, and a fix to one blind spot benefits every caller in one place.

**Three independent routes are covered, matched structurally rather than by
line text:**

- **Module route** (`forbidden_modules`): any import statement — `import
  a.b.c`, `from a.b import c`, `from a.b.c import d`, a relative import, or
  the same import wrapped across several lines by a formatter — whose
  resolved dotted path is one of these, or a submodule of one of these.
  Wrapping an import across lines does not change its AST shape, so the
  parenthesised-multi-line bypass has no purchase here.
- **Attribute route** (`forbidden_attrs`): an `ast.Attribute` access whose
  `.attr` is one of these, catching reach through a parent-package import
  that never names the forbidden module in an import statement at all —
  `from app import services` followed by `services.fact_lift.run(...)`. The
  module route alone is structurally blind to this: `import app.services`
  reaches nothing on its own, and the reach only exists at the attribute
  access that follows it.
- **Literal route** (`forbidden_literals`): an exact string constant
  matching one of these, anywhere in the file — an `ast.Constant` walk, not
  a substring search, so an adjacent-literal split
  (`"app.services." "fact_lift"`) is folded into one constant by the parser
  before this walk ever sees it, and a string that merely *contains* a
  forbidden spelling (`"memory_dream_state"` containing `"memory_dream"`) is
  not a false positive the way a substring check would make it. A docstring
  is exempted by structural role, never by matching its text (see
  `docstring_node_ids`), so prose explaining the guard cannot be "loosened
  away" by tripping the guard itself.

**The bound, stated once here rather than only in a report.** A *computed*
string — `"a" + "b"`, an f-string with any non-constant part, a name or
attribute path assembled at runtime (`"fact_" + "lift"`,
`getattr(mod, dynamic_name)`) — is invisible to a static AST walk. This
scanner catches every route above that is spelled as a literal, and does not
claim, and cannot be made by any static rework, to catch a route that is
computed at runtime. That is a property of static analysis, not a gap in
this implementation.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ExemptNodeIds = Callable[[str, ast.Module], "set[int]"]

_DOCSTRING_HOLDERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def docstring_node_ids(tree: ast.AST) -> set[int]:
    """Identity of every docstring constant in `tree`.

    A module's, class's or function's leading string-literal statement may
    name a forbidden module in prose without tripping the scan. The
    exemption is by structural role — "the first statement of a body that
    can hold a docstring, and is one" — never by matching the string's text,
    so a non-docstring constant that happens to share the same words is not
    accidentally let through, and the docstring's exact wording can change
    freely without touching this set.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_HOLDERS):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.add(id(first.value))
    return found


def _import_dotted_targets(node: ast.AST) -> list[tuple[int, str]]:
    """(level, dotted-path) pairs an import statement names, one per alias.

    `level` is 0 for an absolute import. For a relative import the caller
    has only the trailing components actually written in the statement —
    resolving the true absolute path would need the importing file's own
    package, which this scan does not track — so a relative import is
    matched on however many trailing components it names (see
    `_matches_forbidden_module`), the same final-path-segment discipline
    T2.45 established for exactly this reason.

    An `ImportFrom` yields *two* candidates per alias, because a single
    combined `base.alias` string is ambiguous about whether `alias` is a
    submodule (`from ..services import dream_jobs`) or a symbol defined
    inside `base` (`from .dream_jobs import register_dream_jobs`) — and a
    relative import cannot distinguish the two without resolving the
    package, which this scan does not do. Matching only the combined form
    misses the second shape entirely: `base` alone ("dream_jobs") carries
    the real module path, and appending the symbol name pushes the
    trailing-segment comparison one slot out of alignment. Yielding `base`
    alone as well closes that gap without needing to tell the two shapes
    apart.
    """
    targets: list[tuple[int, str]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append((0, alias.name))
    elif isinstance(node, ast.ImportFrom):
        base = node.module or ""
        for alias in node.names:
            full = f"{base}.{alias.name}" if base else alias.name
            targets.append((node.level, full))
            if node.level > 0 and base:
                targets.append((node.level, base))
    return targets


def _matches_forbidden_module(level: int, dotted: str, forbidden: str) -> bool:
    if level == 0:
        return dotted == forbidden or dotted.startswith(forbidden + ".")
    dotted_parts = [p for p in dotted.split(".") if p]
    forbidden_parts = forbidden.split(".")
    k = min(len(dotted_parts), len(forbidden_parts))
    if k == 0:
        return False
    return dotted_parts[-k:] == forbidden_parts[-k:]


@dataclass(frozen=True)
class ReachabilityRules:
    """A caller's own forbidden vocabulary for `find_forbidden_reach`.

    `forbidden_modules` are full dotted `app.*` paths (import route).
    `forbidden_attrs` are bare names (attribute route) — normally each
    forbidden module's own final segment, so `from app import services;
    services.fact_lift.run()` is caught without naming the module in any
    import. `forbidden_literals` are exact strings (literal route) — every
    forbidden module's dotted path *and* final segment, plus any other
    literal (a registry key, for instance) reaching the same target by a
    different spelling than its module path.

    **This scanner matches whatever `forbidden_modules` it is handed; how
    deep that set reaches is entirely the caller's derivation, and depth is
    a contract, not a free implementation choice.**
    `tests/test_dream_jobs.py`'s `dream_job_implementation_modules()` is the
    concrete instance: it reads only the umbrella module's own direct
    imports (one hop), deliberately never a transitive walk of what those
    modules import in turn. T2.12 and T2.13 both depend on that shallowness
    to expose a shared helper module to code outside the family (a
    repository, or a neutral module two job bodies both import) without
    that helper itself becoming forbidden. A caller that widens its own
    derivation to transitive closure silently forbids everything its
    forbidden modules import, which is a scope change to what "reaches a
    family job" means — decide that deliberately in the caller, and say so
    there, rather than assuming this generic scanner enforces a depth on
    your behalf.
    """

    forbidden_modules: frozenset[str] = frozenset()
    forbidden_attrs: frozenset[str] = frozenset()
    forbidden_literals: frozenset[str] = frozenset()


def _offense_detail(
    node: ast.AST, rules: ReachabilityRules, docstrings: set[int]
) -> str | None:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for level, dotted in _import_dotted_targets(node):
            for forbidden in rules.forbidden_modules:
                if _matches_forbidden_module(level, dotted, forbidden):
                    return f"import route: {dotted}"
        return None
    if isinstance(node, ast.Attribute):
        if node.attr in rules.forbidden_attrs:
            return f"attribute route: .{node.attr}"
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if id(node) in docstrings:
            return None
        if node.value in rules.forbidden_literals:
            return f"literal route: {node.value!r}"
        return None
    return None


def find_forbidden_reach(
    paths: list[Path],
    root: Path,
    rules: ReachabilityRules,
    *,
    skip_files: frozenset[str] = frozenset(),
    exempt_node_ids: ExemptNodeIds | None = None,
) -> list[str]:
    """Every AST-visible route from a file under `root` to `rules`'s targets.

    `skip_files` (relative to `root`) are whole files exempted outright —
    the umbrella/detector module itself, which necessarily names its own
    vocabulary. `exempt_node_ids(rel, tree)` lets a caller carve out
    specific, structurally identified nodes within one otherwise-scanned
    file (e.g. "the one registration call inside `lifespan`"), matched by
    node identity within that file's own parse — never by comparing
    rendered text, so a second, textually-identical occurrence elsewhere in
    the same file is not silently exempted alongside the real one.
    """
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(root))
        if rel in skip_files:
            continue
        tree = ast.parse(path.read_text(), filename=rel)
        docstrings = docstring_node_ids(tree)
        exempt = exempt_node_ids(rel, tree) if exempt_node_ids else set()
        for node in ast.walk(tree):
            if id(node) in exempt:
                continue
            detail = _offense_detail(node, rules, docstrings)
            if detail:
                offenders.append(f"{rel}:{node.lineno}: {detail}")
    return offenders


def app_sources(backend: Path) -> list[Path]:
    paths = [p for p in (backend / "app").rglob("*.py") if "__pycache__" not in str(p)]
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scan below would "
        "pass vacuously; check the backend root / the glob path"
    )
    return paths


def service_modules_imported_by(source: str) -> set[str]:
    """Every `app.services` module a source file imports, in any import
    style — parsed rather than split on lines, so a formatter's
    parenthesised, multi-line `from app.services import (\n    x,\n)` is one
    `ImportFrom` node regardless of how many lines it spans.
    """
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "app.services":
                modules.update(alias.name for alias in node.names)
            elif node.module.startswith("app.services."):
                modules.add(node.module[len("app.services."):].split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    modules.add(alias.name[len("app.services."):].split(".")[0])
    return {module for module in modules if module}
