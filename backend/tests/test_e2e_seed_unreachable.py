"""T2.90's clause 1: the knowledge-e2e fact-seeding path must be unreachable
from a normal deployment, and this must be a test, not a claim.

``backend/scripts/e2e/seed_facts.py`` writes real Layer-1 rows and calls the
real ``fact_lift.run_lift`` over them (see that module's docstring) — it is
not a hand-crafted ``knowledge_triples`` insert, but it is still a way to make
a fact appear that did not go through a live capture, and the Facts surface
is GET-only specifically so nothing but ``fact_lift`` can do that. Two
independent, cheap guards make the seeding path unreachable in a deployed
darkmem:

1. The production image never contains ``backend/scripts`` at all — the
   Dockerfile's runtime stage only ``COPY``s ``backend/app``, migrations and
   the built SPA. This is checked directly against the Dockerfile's own
   text.
2. Even if it were copied, nothing under ``backend/app`` — the package that
   *is* shipped — imports it. Checked with the same AST reachability scanner
   `test_dream_jobs.py`'s family scan and `test_communities.py`'s detector
   scan already use for an identical shape of claim.

Both are mutation-proven: temporarily add a `COPY backend/scripts` line to
the Dockerfile, or a `from scripts.e2e import seed_facts` import anywhere
under `app/`, and each test fails on its own (verified by hand while writing
this file, not asserted from memory).
"""
from __future__ import annotations

from pathlib import Path

from tests._reachability_scan import ReachabilityRules, app_sources, find_forbidden_reach

BACKEND = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND.parent


def test_dockerfile_never_copies_backend_scripts_into_the_image():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    assert "backend/scripts" not in dockerfile, (
        "the Dockerfile now copies backend/scripts into the image — that "
        "would ship backend/scripts/e2e/seed_facts.py, which mints facts "
        "by calling fact_lift directly outside any HTTP door, into a "
        "deployed darkmem. The seeding path's production-unreachability "
        "(T2.90 clause 1) depends on this file never doing that."
    )


def test_dockerignore_still_excludes_backend_scripts():
    """Fix round 1, F2: the test above only holds while the Dockerfile's
    runtime stage never broadens its own COPY. A future `COPY backend/ ./`
    would pass the test above and still ship seed_facts.py unless
    `.dockerignore`'s `backend/scripts` line keeps excluding it — and until
    now nothing pinned that line, so a broadened COPY (green) followed by a
    later `.dockerignore` cleanup (green) could ship it with both guards
    still passing. Pin the line itself, not just its effect on today's
    Dockerfile, so either half of that two-step drift goes red on its own.
    """
    dockerignore = (REPO_ROOT / ".dockerignore").read_text()
    assert "backend/scripts" in dockerignore.splitlines(), (
        ".dockerignore no longer excludes backend/scripts — that line is "
        "the only thing that would still keep seed_facts.py out of the "
        "image if the Dockerfile's runtime stage were ever broadened to "
        "COPY all of backend/ (T2.90 clause 1's second line of defense)."
    )


_SEED_SCRIPT_RULES = ReachabilityRules(
    forbidden_modules=frozenset({"scripts.e2e"}),
    forbidden_attrs=frozenset({"seed_facts", "seed_fact_fixture"}),
    forbidden_literals=frozenset({"seed_fact_fixture"}),
)


def test_app_never_reaches_the_e2e_seed_scripts():
    paths = app_sources(BACKEND)
    offenders = find_forbidden_reach(paths, BACKEND, _SEED_SCRIPT_RULES)
    assert not offenders, (
        "app/ (the package the production image actually ships) reached "
        "backend/scripts/e2e, the fact-seeding path built for the "
        "knowledge e2e (T2.90). That path exists only to give a Playwright "
        "spec something to look at against a disposable, test-only "
        "database — it must never become reachable from the real, "
        "deployed API:\n" + "\n".join(offenders)
    )
