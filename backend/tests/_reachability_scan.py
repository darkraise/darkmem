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

**Four independent routes are covered, matched structurally rather than by
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
- **Literal route** (`forbidden_literals` and `forbidden_modules`): two
  different match disciplines over `ast.Constant`, deliberately not one,
  because one discipline cannot serve both vocabularies without either
  missing real reaches or flagging innocent prose:
  - `forbidden_literals` (bare names — a job key, a module's own basename)
    match by **exact equality only**. A bare word is common English and
    common log-message vocabulary (`memory_community_detection.py`'s own
    help text says "topic_detection", `verification_recompute.py` logs a
    "verification_recompute" prefix) — a substring check over bare names
    would flag that prose, and get "loosened away" the first time it did.
  - `forbidden_modules` (dotted `app.services.<x>` paths) match by
    **substring at an identifier boundary** — the match cannot be
    immediately preceded or followed by an alphanumeric-or-underscore
    character. This is what a bare-name exact match structurally cannot
    catch: `exec("import app.services.fact_lift")`, a `bytes` literal
    fed through `.decode()`, a loader-spec string
    (`"app.services.fact_lift:run_lift"`), or the same dotted path sitting
    in an otherwise-ordinary sentence. A dotted path is specific enough
    that a boundary-scoped substring does not collide with real code —
    verified against this repository's own tree — the way a bare-name
    substring does.
  - Both disciplines run over **both `str` and `bytes` constants**, because
    `b"app.services.fact_lift".decode()` is exactly as executable as the
    `str` form and a scan that only looked at `str` would have a
    documented, exploitable hole through the one path it explicitly claims
    to close.
  - An adjacent-literal split (`"app.services." "fact_lift"`) is folded
    into one constant by the parser before this walk ever runs, on both
    `str` and `bytes`.
  - A docstring is exempted by structural role, never by matching its
    text (see `docstring_node_ids`), so prose explaining the guard cannot
    be "loosened away" by tripping the guard itself. Because the literal
    route no longer requires exact equality to the whole forbidden path,
    the docstring exemption is genuinely load-bearing here (a "see also:
    app.services.fact_lift" docstring is exactly the shape that would
    trip the boundary-substring check without it) — narrower-but-still-
    real coverage than under the exact-match-only design this replaced.
- **Loader-call route**: `import_module(...)`/`__import__(...)` called
  with a **relative** literal name (`".fact_lift"`) and a literal
  `package=` (or, for `import_module`, a second positional argument),
  resolved to the absolute dotted path the same way
  `importlib._bootstrap._resolve_name` does and matched against
  `forbidden_modules` the same way an absolute import statement is.
  `import_module(".memory_community_reports", package="app.services")`
  is fully static and literal-spelled on both arguments — nothing about
  it is computed — so it belongs on this list rather than in the bound
  below, even though no scan (T2.18's original AST rebuild, T2.67's
  first pass, or the family/detector scans before either) ever
  recognised it before a re-review named it explicitly.

**The bound, stated once here rather than only in a report.** Two shapes
remain structurally invisible to a static AST walk, and no rework of this
matching discipline closes them:
  - A **computed** string assembled from more than one runtime expression
    — `"a" + "b"` where the two sides are not adjacent literals, an
    f-string with any non-constant interpolated part, or a name/attribute
    path built through concatenation, formatting, or `getattr` with a
    *computed* (non-literal) attribute name.
  - A reach that never spells the module's own **full** dotted path at
    all: `from app.services import *` followed by a bare
    `fact_lift.run(...)` (star-import plus bare-`Name` use — the module
    route only recognises explicit `Import`/`ImportFrom` nodes and the
    literal route only recognises the dotted path, and neither fires on
    a bare name that resolves through `*`), or a prefix-free literal
    that names the module without the leading `app.services.` at all
    (`"services.fact_lift.run_lift"`, a bare basename mentioned in
    ordinary prose, `operator.attrgetter(...)` fed either shape) — the
    boundary-substring check is scoped to the full forbidden dotted path
    specifically to avoid the false-positive collisions a shorter,
    prefix-free needle would cause against ordinary prose (see
    `forbidden_literals` above), and that scoping is what leaves this
    shape uncovered. Turning a prefix-free literal or a bare mention
    into an executable reach needs runtime string surgery the reader
    cannot see statically (reconstructing `app.services.` from context,
    or resolving the name against `sys.path` some other way) — a
    genuinely different shape from the loader-call route above, which
    needs no such reconstruction because both of its arguments already
    spell the full path between them.
This scanner catches every route above that is spelled as a literal
reachable by exact-match, boundary-substring, or the loader-call's
relative+package resolution; it does not claim, and cannot be made by any
static rework, to catch a route that is computed at runtime or that never
spells a forbidden dotted path in full. That is a property of static
analysis and of the boundary-substring design choice, not an oversight in
this implementation.

**Read this as a tripwire, not a sandbox.** As a tripwire — something that
reliably fails the build the moment a forbidden path is spelled out in
full, however it is spelled — this scanner is trustworthy: every route
above is mutation-proven (delete the route, watch its own negative control
fail) and re-verified against the real `app/` tree with zero false
positives. As a sandbox — something that prevents *any* possible reach,
including one an adversarial author deliberately obfuscates — it is not,
and does not claim to be: an evader who computes the string at runtime, or
who never writes the full dotted path anywhere in the source, walks
through untouched. That is the correct, honestly-stated posture for a
static-analysis guard, not a shortfall to apologise for.
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


def _is_identifier_char(unit) -> bool:
    ch = chr(unit) if isinstance(unit, int) else unit
    return ch.isalnum() or ch == "_"


def _contains_at_boundary(haystack, needle) -> bool:
    """`needle` occurs in `haystack` with no identifier character touching
    either end of the match.

    Works over both `str` and `bytes` (indexing a `bytes` object yields
    `int`, hence `_is_identifier_char`'s dual handling) with the same
    logic, so the same call site serves the `str` and the `bytes` literal
    route without a second implementation to keep in sync.
    """
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            return False
        before_ok = idx == 0 or not _is_identifier_char(haystack[idx - 1])
        end = idx + len(needle)
        after_ok = end == len(haystack) or not _is_identifier_char(haystack[end])
        if before_ok and after_ok:
            return True
        start = idx + 1


def _matches_forbidden_module(level: int, dotted: str, forbidden: str) -> bool:
    if level == 0:
        return dotted == forbidden or dotted.startswith(forbidden + ".")
    dotted_parts = [p for p in dotted.split(".") if p]
    forbidden_parts = forbidden.split(".")
    k = min(len(dotted_parts), len(forbidden_parts))
    if k == 0:
        return False
    return dotted_parts[-k:] == forbidden_parts[-k:]


_LOADER_CALL_NAMES = {"import_module", "__import__"}


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _resolve_relative_loader_call(node: ast.Call) -> str | None:
    """The absolute dotted path an `import_module`/`__import__` call
    resolves to, when both its relative first argument and its `package`
    are literal strings.

    Mirrors `importlib._bootstrap._resolve_name`'s own algorithm
    (`package.rsplit(".", level - 1)[0]` plus the trailing name) closely
    enough for a fully literal-spelled call — this is not a general
    call-argument evaluator, only the one named, fully-static, executable
    shape a re-review identified: `import_module(".fact_lift",
    package="app.services")`. Returns `None` for anything not shaped
    exactly like this: a non-literal argument, a name with no leading dot
    (an absolute literal name is already caught by the ordinary literal
    route), or no resolvable `package`.
    """
    if _call_func_name(node) not in _LOADER_CALL_NAMES:
        return None
    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    name = node.args[0].value
    if not isinstance(name, str) or not name.startswith("."):
        return None
    package: str | None = None
    for keyword in node.keywords:
        if (
            keyword.arg == "package"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            package = keyword.value.value
    if package is None and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
        candidate = node.args[1].value
        if isinstance(candidate, str):
            package = candidate
    if not package:
        return None
    level = len(name) - len(name.lstrip("."))
    rest = name[level:]
    bits = package.rsplit(".", level - 1) if level > 1 else [package]
    base = bits[0]
    return f"{base}.{rest}" if rest else base


@dataclass(frozen=True)
class ReachabilityRules:
    """A caller's own forbidden vocabulary for `find_forbidden_reach`.

    `forbidden_modules` are full dotted `app.*` paths — used by *two*
    routes: the import route (an exact match, or a submodule prefix match,
    against a parsed import statement) and, since T2.67's Critical fix, the
    literal route's boundary-substring check (any `str`/`bytes` constant
    that contains one of these dotted paths with no identifier character
    touching either edge of the match — `exec("import app.services.
    fact_lift")`, a `bytes` literal decoded before use, a loader-spec
    string, or the same path sitting in a comment-shaped constant).
    `forbidden_attrs` are bare names (attribute route) — normally each
    forbidden module's own final segment, so `from app import services;
    services.fact_lift.run()` is caught without naming the module in any
    import. `forbidden_literals` are bare names too (a job key, a module's
    own basename) — matched by the literal route's *other* check, **exact
    equality only**, over both `str` and `bytes`. The two literal-route
    checks are deliberately different disciplines: a bare name is common
    prose and log-message vocabulary (this repository's own
    `verification_recompute.py` logs a "verification_recompute" prefix,
    `memory_community_detection.py`'s help text says "topic_detection"), so
    a substring check over `forbidden_literals` would flag real,
    load-bearing strings; a *dotted* path is specific enough that a
    boundary-scoped substring does not collide with anything in this
    repository's tree (verified, not assumed — see
    `tests/test_dream_jobs.py`'s and `tests/test_communities.py`'s exec /
    bytes / loader-spec / prose test cases). Put a literal in
    `forbidden_modules` only if it is a full `app.*` dotted path; put it in
    `forbidden_literals` only if it is a bare name you want matched
    exactly. Neither field is a general-purpose "flag this string anywhere"
    list.

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
    if isinstance(node, ast.Call):
        resolved = _resolve_relative_loader_call(node)
        if resolved is not None:
            for forbidden in rules.forbidden_modules:
                if _matches_forbidden_module(0, resolved, forbidden):
                    return f"loader-call route: {resolved}"
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        if id(node) in docstrings:
            return None
        value = node.value
        is_bytes = isinstance(value, bytes)
        for literal in rules.forbidden_literals:
            needle = literal.encode("utf-8") if is_bytes else literal
            if value == needle:
                return f"literal route (exact{' bytes' if is_bytes else ''}): {value!r}"
        for module in rules.forbidden_modules:
            needle = module.encode("utf-8") if is_bytes else module
            if _contains_at_boundary(value, needle):
                return (
                    f"literal route (boundary substring"
                    f"{' bytes' if is_bytes else ''}): {value!r} contains {module!r}"
                )
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
    """Every `app.services` module a source file imports, in any *absolute*
    import style — `from app.services.x import y`, `from app.services
    import x`, `import app.services.x` — parsed rather than split on lines,
    so a formatter's parenthesised, multi-line
    `from app.services import (\n    x,\n)` is one `ImportFrom` node
    regardless of how many lines it spans.

    A **relative** import (`from .x import y`, `from . import x`) is not
    recognised here. This is the derivation used to build the *forbidden*
    module set out of `dream_jobs.py`'s own imports, not the general
    reachability scan applied to arbitrary files under `app/` — that
    general scan (`_matches_forbidden_module` above) does handle relative
    imports when checking whether some *other* file reaches a forbidden
    module. The umbrella module relative-importing one of its own job
    bodies would be an unusual, self-referential shape this function would
    miss; it is not expected to occur, and is called out here rather than
    silently assumed away.
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
