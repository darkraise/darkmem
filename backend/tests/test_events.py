"""T2.103 — enforce EVENT_TYPES as a closed vocabulary at every emit site.

``record_event`` never raises on an out-of-vocabulary ``event_type``; it
only logs a warning (deliberately — a journal write must never fail the
operation it records, doc 04 §8.1). That means a typo'd or stale literal
at any call site is otherwise invisible until someone reads a warning log
in production. The auth family drifted exactly this way for five values
(`auth_login_success`, `auth_login_failed`, `auth_logout`,
`auth_password_change`, `auth_setup`) before T2.103, and nothing failed a
build over it. This module is the scan that makes it fail one.

**Two call shapes exist in `backend/app`.**

1. Direct: `record_event(..., event_type=<literal-or-resolvable>)`. The
   literal may be a string constant, a bare name/attribute resolving to a
   module- or class-level `NAME = "literal"` assignment, or a
   `<dict>.get(key, default)` read off a dict literal — the same shapes
   `test_event_taxonomy_map.py` already resolves for its own, differently
   scoped guard.
2. Indirect, through a **wrapper**: a function defined under `backend/app`
   whose own body calls `record_event` (or another already-resolved
   wrapper) passing one of *its own parameters* as `event_type`.
   `app/api/routes/auth.py`'s `_record_audit(action, details)` is the one
   instance today — `_record_audit("auth_login_failed", ...)` carries no
   keyword named `event_type` at all, so a scan that only matches that
   keyword literally (shape 1 above) never even looks at this call site,
   and would silently report the whole auth family as compliant while it
   sat entirely outside `EVENT_TYPES`. That is precisely the miss this
   module exists to close.

The wrapper resolution below is generic — it is not special-cased to the
name `_record_audit`. Any function whose body forwards one of its
parameters into `record_event(event_type=<that parameter>)` is discovered
and registered; every call site of that function elsewhere in the tree
then has the corresponding argument (by keyword, or positionally at the
parameter's declared index) resolved the same way a direct `event_type=`
argument would be. This is one fixed-point pass over a single "wraps a
wrapper" hop, which is enough for every shape in the codebase today; a
second layer of indirection would need the pass re-run once the outer
wrapper is registered, which `_resolve_emitted_types` already does by
iterating to a fixed point rather than a single pass (see its docstring).

**What this cannot see.** An event type assembled at runtime — an
f-string, string concatenation, a value read from config or the database —
resolves to nothing usable and is simply absent from `emitted`; it can
never be checked against `EVENT_TYPES` by a static scan. None exist in the
codebase today. A wrapper whose forwarded parameter is passed under a
*different* keyword name at every one of its own call sites (never
positionally, never under its declared name) would also be missed; no
such shape exists today either.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services.events import EVENT_TYPES

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "backend" / "app"

_EVENT_TYPE_SET = frozenset(EVENT_TYPES)


def _iter_py_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _parsed_modules() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in _iter_py_files()
    ]


def _collect_name_constants(modules: list[tuple[Path, ast.Module]]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for _, tree in modules:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                names.setdefault(target.id, set()).add(node.value.value)
    return names


def _collect_dict_constants(modules: list[tuple[Path, ast.Module]]) -> dict[str, set[str]]:
    dicts: dict[str, set[str]] = {}
    for _, tree in modules:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Dict):
                values = {
                    v.value
                    for v in node.value.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                }
                if values:
                    dicts.setdefault(target.id, set()).update(values)
    return dicts


def _resolve(expr: ast.expr, name_consts: dict, dict_consts: dict) -> set[str]:
    """Best-effort literal resolution. Returns the empty set when the
    expression cannot be resolved — never raises, never guesses."""
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return {expr.value}
    if isinstance(expr, ast.Name):
        return name_consts.get(expr.id, set())
    if isinstance(expr, ast.Attribute):
        return name_consts.get(expr.attr, set())
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "get"
    ):
        base = expr.func.value
        dict_name = (
            base.attr if isinstance(base, ast.Attribute)
            else base.id if isinstance(base, ast.Name)
            else None
        )
        if dict_name and dict_name in dict_consts:
            return dict_consts[dict_name]
    return set()


def _call_event_type_kwarg(call: ast.Call) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == "event_type":
            return kw.value
    return None


def _find_calls(tree: ast.AST, name: str) -> list[ast.Call]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        callee = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else None
        )
        if callee == name:
            found.append(node)
    return found


def _iter_function_defs(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _param_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[list[str], set[str]]:
    """(positional-eligible params in call order, all param names). A
    keyword-only parameter (after a bare ``*`` in the signature, the shape
    `_journal`'s ``event_type`` uses) can never be bound positionally, so it
    is excluded from the ordered list but still counts as "one of the
    function's own parameters" for wrapper discovery."""
    positional = [a.arg for a in func.args.args]
    all_names = set(positional) | {a.arg for a in func.args.kwonlyargs}
    return positional, all_names


def _arg_for_param(
    call: ast.Call, positional: list[str], param: str
) -> ast.expr | None:
    """The expression bound to `param` at `call`, whether passed by keyword
    or positionally at `param`'s declared index — only for a parameter that
    is positional-eligible in the callee's signature; a keyword-only
    parameter is matched by keyword alone."""
    for kw in call.keywords:
        if kw.arg == param:
            return kw.value
    if param in positional:
        idx = positional.index(param)
        if idx < len(call.args):
            return call.args[idx]
    return None


def _resolve_emitted_types(
    modules: list[tuple[Path, ast.Module]],
) -> tuple[set[str], set[tuple[str, str]]]:
    """Every literal event_type reachable through any `record_event`
    (direct) or wrapper (indirect) call site, plus the (file, callee) of
    every site that could not be resolved to one.

    Wrapper discovery is a fixed point: a function forwarding a parameter
    into an already-known emitter (`record_event`, or a previously
    discovered wrapper) is itself registered as an emitter, and the pass
    repeats until no new wrapper is found. One hop already covers every
    shape in the codebase; the loop costs nothing extra and means a
    second layer of indirection would be caught too, not silently missed.
    """
    name_consts = _collect_name_constants(modules)
    dict_consts = _collect_dict_constants(modules)

    # wrapper name -> forwarded parameter name
    wrappers: dict[str, str] = {}
    emitter_names = {"record_event"}

    changed = True
    while changed:
        changed = False
        for _, tree in modules:
            for func in _iter_function_defs(tree):
                if func.name in wrappers:
                    continue
                _, all_param_names = _param_names(func)
                for call in ast.walk(func):
                    if not isinstance(call, ast.Call):
                        continue
                    func_expr = call.func
                    callee = (
                        func_expr.attr if isinstance(func_expr, ast.Attribute)
                        else func_expr.id if isinstance(func_expr, ast.Name)
                        else None
                    )
                    if callee not in emitter_names:
                        continue
                    forwarded = _call_event_type_kwarg(call)
                    if isinstance(forwarded, ast.Name) and forwarded.id in all_param_names:
                        wrappers[func.name] = forwarded.id
                        emitter_names.add(func.name)
                        changed = True
                        break

    positional_params: dict[str, list[str]] = {}
    for _, tree in modules:
        for func in _iter_function_defs(tree):
            if func.name in wrappers and func.name not in positional_params:
                positional_params[func.name], _ = _param_names(func)

    emitted: set[str] = set()
    unresolved: set[tuple[str, str]] = set()

    for path, tree in modules:
        rel = str(path.relative_to(REPO_ROOT / "backend"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_expr = node.func
            callee = (
                func_expr.attr if isinstance(func_expr, ast.Attribute)
                else func_expr.id if isinstance(func_expr, ast.Name)
                else None
            )
            if callee == "record_event":
                expr = _call_event_type_kwarg(node)
                if expr is None:
                    continue
                values = _resolve(expr, name_consts, dict_consts)
                emitted |= values
                if not values:
                    unresolved.add((rel, callee))
            elif callee in wrappers:
                param = wrappers[callee]
                expr = _arg_for_param(node, positional_params.get(callee, []), param)
                if expr is None:
                    continue
                values = _resolve(expr, name_consts, dict_consts)
                emitted |= values
                if not values:
                    unresolved.add((rel, callee))

    return emitted, unresolved


# Call sites where the *inner* `record_event(..., event_type=<bare Name>)`
# call, taken on its own, cannot be resolved to a literal — the name is a
# parameter of the enclosing wrapper, not a module constant. Both entries
# below are wrappers this scan already traces (see `wrappers` in
# `_resolve_emitted_types`): the literal is found instead at each
# wrapper's own call sites, which is exactly what
# `test_auth_family_resolves_through_the_record_audit_wrapper` pins for
# `_record_audit`. Reviewed by hand; a new entry appearing here without a
# matching line added to this set is exactly the silent-miss shape this
# module exists to close — the test fails until the new site is triaged
# and either taught to the resolver or added here with a reason.
_EXPECTED_UNRESOLVED: set[tuple[str, str]] = {
    # `_record_audit(action, details)` forwards `action` as `event_type`;
    # the literals ("auth_login_failed", "auth_lockout", ...) live at
    # `_record_audit`'s own call sites in auth.py, resolved via the
    # wrapper trace instead.
    ("app/api/routes/auth.py", "record_event"),
    # `_journal(..., *, event_type, ...)` forwards its own keyword-only
    # `event_type` straight through; the literals ("superseded",
    # "deprecated") live at `_journal`'s two call sites, resolved via the
    # wrapper trace instead.
    ("app/services/supersede.py", "record_event"),
    # `_journal_each(..., *, event_type, ...)` forwards its keyword-only
    # `event_type`; the literals ("page_deleted", "page_restored",
    # "page_purged") live at its three call sites, resolved via the wrapper
    # trace instead.
    ("app/services/page_door.py", "record_event"),
}


def test_no_new_unresolvable_emit_site():
    modules = _parsed_modules()
    _, unresolved = _resolve_emitted_types(modules)
    assert unresolved == _EXPECTED_UNRESOLVED, (
        f"unexpected unresolved event_type emit site(s): "
        f"{unresolved - _EXPECTED_UNRESOLVED}. Either teach the resolver "
        f"to follow it, or add it to _EXPECTED_UNRESOLVED with a reason."
    )


def test_every_emitted_event_type_is_in_the_closed_vocabulary():
    """The deliverable. No `record_event` call anywhere in `backend/app` —
    directly, or through a one-hop wrapper like `_record_audit` — may name
    a value outside `EVENT_TYPES`. `record_event` itself only warns on
    this; this test is what turns the warning into a build failure."""
    modules = _parsed_modules()
    emitted, _ = _resolve_emitted_types(modules)

    outside_vocabulary = emitted - _EVENT_TYPE_SET
    assert not outside_vocabulary, (
        f"record_event call site(s) emit value(s) outside EVENT_TYPES: "
        f"{sorted(outside_vocabulary)}. Land the value in EVENT_TYPES "
        f"before its emitter ships (taxonomy-first, doc 04 §8.1)."
    )


def test_auth_family_resolves_through_the_record_audit_wrapper():
    """Pins the exact regression T2.103 fixes: a scan that only matches the
    literal-keyword shape at `record_event` itself sees nothing at
    `_record_audit`'s call sites and would report the auth family
    compliant by omission. This asserts the wrapper trace actually finds
    them, so a future refactor that breaks the trace (renaming
    `_record_audit`'s parameter, say) fails here specifically rather than
    only via a coincidentally-still-passing vocabulary check."""
    modules = _parsed_modules()
    emitted, _ = _resolve_emitted_types(modules)

    for value in ("auth_login_failed", "auth_lockout"):
        assert value in emitted, (
            f"{value!r} is emitted only through _record_audit's wrapper "
            f"shape and the scan failed to trace it"
        )


def test_document_updated_is_in_the_vocabulary():
    """Widening is taxonomy-first: the value lands before its emitter ships,
    or the first emission logs an unknown-type warning and misfiles the row."""
    assert "document_updated" in EVENT_TYPES


def test_documents_deleted_is_in_the_vocabulary():
    """Taxonomy-first: the value lands before its emitter, so the subtree
    delete cannot ship as the one document mutation with no journal row."""
    from app.services.events import EVENT_TYPES

    assert "documents_deleted" in EVENT_TYPES


def test_the_page_vocabulary_is_admitted_before_its_emitters():
    """Taxonomy-first: an emitter shipping ahead of its vocabulary logs a
    warning and writes an unclassified row, which is the failure this
    ordering exists to prevent."""
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    assert "page" in OBJECT_TYPES
    for event in (
        "page_created",
        "page_updated",
        "page_moved",
        "page_deleted",
        "page_restored",
        "page_purged",
    ):
        assert event in EVENT_TYPES, f"{event} is not admitted"
