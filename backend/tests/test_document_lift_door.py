"""The lift door exists because a human asked, and stays unreachable to a job.

`routes/documents.py` recorded, before this route existed:

    **No lift door.** `lift_document` is on-demand by design and a route is
    the easiest way for something to call it on a schedule; nothing in EH1
    needs one **before a human asks**.

The spec's §6.1 is the human asking. The note's *reason* is kept rather than
discarded, because the hazard it names is **scheduled** calling, not human
calling: a lift on a cron would re-extract propositions from every filed
document on every tick, which is both an unbounded spend and a corpus that
rewrites itself while nobody is looking.

So the guard is not "there is no route" any more. It is "no job can reach
one", pinned structurally rather than by reading today's job list.
"""
from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
JOB_MODULES = (
    APP / "services" / "job_runners.py",
    APP / "services" / "dream_jobs.py",
    APP / "main.py",
)


def _calls(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == name:
            return True
    return False


def _references(tree: ast.AST, name: str) -> bool:
    """A bare reference, not a call.

    A `JobRegistry` runner takes no arguments, so the shape a scheduled lift
    would actually take is `runner=lift_document` or a partial over it -- a
    Name load, which a call-only scan does not see. That is the hole this
    catches.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == name:
            return True
    return False


def test_no_job_module_can_reach_the_lift():
    offenders = []
    for path in JOB_MODULES:
        assert path.exists(), f"{path} moved; this scan is now vacuous"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _calls(tree, "lift_document") or _references(tree, "lift_document"):
            offenders.append(str(path.relative_to(BACKEND)))
    assert not offenders, (
        f"a job module can reach the lift: {offenders} — the lift is on-demand "
        "by design (spec §6.1). A scheduled lift re-extracts every filed "
        "document on every tick."
    )


def test_the_scan_would_catch_a_registered_runner():
    """The shape the hazard would actually take, so the scan is not vacuous."""
    import textwrap

    registered = ast.parse(textwrap.dedent("""
        from app.services.proposition_lift import lift_document
        JOB = Job(key="document_lift", runner=lift_document)
    """))
    called = ast.parse(textwrap.dedent("""
        from app.services import proposition_lift
        async def tick(session, llm, svc, ids):
            for i in ids:
                await proposition_lift.lift_document(session, llm, svc, document_id=i)
    """))
    # A bare `runner=` reference is not a call, which is why the scan checks
    # both shapes rather than only the obvious one.
    assert not _calls(registered, "lift_document")
    assert _references(registered, "lift_document")
    assert _calls(called, "lift_document")


def test_the_route_declares_no_config_schema():
    """A job is configurable; this door is not, and that asymmetry is the
    point. A `config_schema` on the lift would be the first half of turning it
    into a scheduled job."""
    source = (APP / "api" / "routes" / "documents.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "lift_document_route":
            args = [a.arg for a in node.args.args + node.args.kwonlyargs]
            assert "config_schema" not in args
            assert "cron" not in args
            break
    else:  # pragma: no cover - the route was renamed or removed
        raise AssertionError("lift_document_route not found; update this scan")
