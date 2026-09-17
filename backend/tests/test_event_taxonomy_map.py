"""T2.102 — the guard that makes the frontend event-taxonomy map's next
silent miss impossible.

Three straight rounds (T2.11, T2.48) each found exactly one ``EVENT_TYPES``
value with a live emitter that
``frontend/src/features/activity/event-taxonomy.ts`` had never learned
about, and fixed only that one. The map is maintained reactively — a value
lands in the closed vocabulary, its emitter ships, and nothing failed when
the map did not learn about it. This module is what fails.

**What counts as "live".** A value in ``EVENT_TYPES`` with no emitter yet —
landed taxonomy-first, ahead of its feature — must not fail the build; that
would punish exactly the discipline the corpus requires (``inject`` and
``inject_curbed`` are in this state today: the vocabulary carries them,
nothing calls ``record_event`` with them). "Live" is defined operationally:
some call anywhere under ``backend/app`` passes a literal string equal to
that value through a keyword argument literally named ``event_type``.

**``auth_lockout`` is a known blind spot in that operational definition,
not evidence it lacks an emitter.** T2.103 (2026-08-07) wired it up in
``app/api/routes/auth.py``, but the literal travels through
``_record_audit``'s positional ``action`` parameter, never through a
keyword literally named ``event_type`` at any resolvable call site — the
same shape that keeps ``auth_login_failed`` out of ``emitted`` below. See
``backend/tests/test_events.py`` for the scan that *does* trace that
shape (it exists to enforce the closed vocabulary, not frontend coverage,
so it lives in its own module). This test still treats ``auth_lockout``
as not-live and does not require the frontend map to classify it for that
reason; T2.103 classified it in ``EVENT_TYPES_WITHOUT_TAB`` anyway, ahead
of what this guard would have required.

**Why match any ``event_type=`` keyword, not just calls to
``record_event`` itself.** The obvious version — walk calls to
``record_event`` and resolve its ``event_type`` argument — misses
``supersede.py``'s ``_journal`` helper: ``_journal(event_type="deprecated")``
passes the literal at the *wrapper's* call site, then forwards it to
``record_event`` through a bare parameter the AST cannot resolve without
tracing the call graph. Matching the keyword name instead of the callee
finds the literal at whichever call site actually carries it, including
that one, with no call-graph tracing at all. The trade is
``app/api/routes/events.py``'s ``list_events(event_type=...)`` — an
unrelated read-side filter parameter that happens to share the name — which
this scan also visits and correctly fails to resolve to a literal (it is a
query argument, not a constant). It lands in ``_EXPECTED_UNRESOLVED`` below
alongside the two genuine indirections, so a *new* unresolved site — the
shape that would hide a real miss — still fails the build instead of being
silently absorbed.

**What this still cannot see.** A value assembled at runtime (an f-string,
a function call, string concatenation) resolves to nothing and is treated
as unresolved, so it must be triaged by hand at that name or added to the
allowlist with a reason — it is never silently dropped from the coverage
check. A same-named module-level constant assigned two different literals
in two unrelated files would union both into the candidate set for that
name; that can only ever add a spurious "live" candidate, never hide a real
one, so it fails safe.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from app.services.events import EVENT_TYPES

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "backend" / "app"
TAXONOMY_TS = REPO_ROOT / "frontend/src/features/activity/event-taxonomy.ts"

# Call sites where `event_type=` cannot be resolved to a literal by this
# scan's one-hop name/attribute/dict lookup, reviewed by hand (see module
# docstring). A new entry appearing here without a matching line added to
# this tuple is exactly the silent-miss shape T2.102 closes — the test
# fails until the new site is triaged and either taught to the resolver or
# added here with its own reason.
_EXPECTED_UNRESOLVED = {
    # `_record_audit`'s callers pass literals ("auth_login_failed",
    # "auth_lockout") through its positional `action` parameter, which
    # `record_event(..., event_type=action)` inside it then forwards as a
    # bare Name this one-hop resolver cannot follow back to a constant.
    # Both literals are EVENT_TYPES members as of T2.103 (2026-08-07),
    # which closed the earlier gap between auth's event types and the
    # closed vocabulary; `tests/test_events.py` is the scan that traces
    # this exact wrapper shape to enforce that membership. This test's
    # own "live" definition still can't see through it (see module
    # docstring), which only affects whether the frontend map guard
    # *requires* a classification here — it does not affect correctness.
    ("app/api/routes/auth.py", "record_event"),
    # `list_events`'s `event_type` is a read-side query filter parameter,
    # not a value being emitted — same keyword name, unrelated concept.
    ("app/api/routes/events.py", "list_events"),
    # `calendar_counts` gained the same read-side filter with T3.20, so the
    # calendar can say which days hold an inject. Identical reasoning to its
    # sibling above: a query argument, never an emitted value.
    ("app/api/routes/events.py", "calendar_counts"),
    # `_journal`'s own inner `record_event` call forwards its caller's
    # `event_type` parameter unresolved; the literals ("superseded",
    # "deprecated") are captured at `_journal`'s two call sites instead.
    ("app/services/supersede.py", "record_event"),
    # `_journal_each(..., *, event_type, ...)` forwards its keyword-only
    # `event_type`; the literals ("page_deleted", "page_restored",
    # "page_purged") live at its three call sites, resolved via the wrapper
    # trace instead.
    ("app/services/page_door.py", "record_event"),
}


def _iter_py_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _collect_name_constants() -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for path in _iter_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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


def _collect_dict_constants() -> dict[str, set[str]]:
    dicts: dict[str, set[str]] = {}
    for path in _iter_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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


def _resolve(expr: ast.expr, name_consts: dict, dict_consts: dict) -> tuple[set[str], bool]:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return {expr.value}, True
    if isinstance(expr, ast.Name):
        return name_consts.get(expr.id, set()), expr.id in name_consts
    if isinstance(expr, ast.Attribute):
        return name_consts.get(expr.attr, set()), expr.attr in name_consts
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
            return dict_consts[dict_name], True
    return set(), False


def _scan_event_type_kwargs() -> tuple[set[str], set[tuple[str, str]]]:
    """Every literal reachable through a keyword argument named
    ``event_type``, plus the (file, callee) of every site that could not be
    resolved to one."""
    name_consts = _collect_name_constants()
    dict_consts = _collect_dict_constants()
    emitted: set[str] = set()
    unresolved: set[tuple[str, str]] = set()
    for path in _iter_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = str(path.relative_to(REPO_ROOT / "backend"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kw = next((k for k in node.keywords if k.arg == "event_type"), None)
            if kw is None:
                continue
            func = node.func
            callee = (
                func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name)
                else "?"
            )
            values, ok = _resolve(kw.value, name_consts, dict_consts)
            emitted |= values
            if not ok:
                unresolved.add((rel, callee))
    return emitted, unresolved


def _parse_frontend_map() -> tuple[set[str], set[str]]:
    ts = TAXONOMY_TS.read_text(encoding="utf-8")

    category_block = ts.split(
        "const EVENT_TYPE_CATEGORY: Record<string, FeedCategory> = {", 1
    )[1].split("}", 1)[0]
    tabbed = set(re.findall(r'^\s*([A-Za-z0-9_]+):\s*"[a-z]+"', category_block, re.M))

    untabbed_block = ts.split(
        "const EVENT_TYPES_WITHOUT_TAB = new Set<string>([", 1
    )[1].split("])", 1)[0]
    untabbed = set(re.findall(r'"([a-zA-Z0-9_]+)"', untabbed_block))

    return tabbed, untabbed


def test_no_new_unresolvable_event_type_call_site():
    """A new indirection shape (a helper that forwards `event_type` through
    something this scan's one-hop resolver cannot follow) must be triaged by
    a human, not silently swallowed into a false sense of coverage."""
    _, unresolved = _scan_event_type_kwargs()
    assert unresolved == _EXPECTED_UNRESOLVED, (
        f"unexpected unresolved event_type call site(s): "
        f"{unresolved - _EXPECTED_UNRESOLVED}. Either teach "
        f"_resolve()/the wrapper trace to follow it, or add it to "
        f"_EXPECTED_UNRESOLVED with a reason."
    )


def test_frontend_event_taxonomy_covers_every_live_emitted_event_type():
    """The guard. Every EVENT_TYPES value with a live `record_event`-family
    emitter must be classified in the frontend map — either given a tab, or
    named explicitly in EVENT_TYPES_WITHOUT_TAB. A value present in neither
    surfaces only under "all" with no record of why, which is the exact bug
    three straight rounds each found and re-fixed one instance of."""
    emitted, _ = _scan_event_type_kwargs()
    live = emitted & set(EVENT_TYPES)

    tabbed, untabbed = _parse_frontend_map()

    missing = live - tabbed - untabbed
    assert not missing, (
        f"EVENT_TYPES value(s) with a live emitter have no tab and no "
        f"recorded exclusion in event-taxonomy.ts: {sorted(missing)}"
    )

    overlap = tabbed & untabbed
    assert not overlap, (
        f"value(s) claimed by both a tab and EVENT_TYPES_WITHOUT_TAB: "
        f"{sorted(overlap)}"
    )
