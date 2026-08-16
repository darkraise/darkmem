"""Invariant 13's knob must not appear on any launch path (T4.18).

T4.10 re-decided single-worker on T4.09's audit — 38 in-process assumptions,
17 of which BREAK at N = 2, across five unrelated mechanism classes with no
cross-process serialisation primitive in `backend/app` to build on — and
recorded a tripwire test as a recommendation it deliberately left unarmed.
This arms it.

**The knob has three silent spellings and the third is why a test is worth
more than a review.** `--workers` is the obvious one; `WEB_CONCURRENCY` is the
environment variable uvicorn reads *when the flag is absent*, so it raises the
worker count while every launch command still reads as single-worker; and
compose `deploy.replicas` raises it without touching uvicorn at all. T4.10
found the second one, which no prior document named. A reviewer scanning for
"--workers" passes all three.

**The scanned set is derived, not listed.** A tripwire that hardcodes today's
launch paths goes quiet the moment someone adds a fourth, which is the failure
mode it exists to prevent. So the shell scripts and compose files are
discovered, the discovery is asserted non-empty, and the three known launchers
are additionally asserted present by name — a rename reds this file rather
than silently shrinking its coverage.

`deploy:` itself is legitimate and must stay allowed: both compose files use it
for `resources.limits.memory`. Only `replicas` under it is the knob.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]

# The three uvicorn launch paths CLAUDE.md's invariant-13 entry names. Asserted
# present so a rename fails loudly instead of removing itself from the sweep.
KNOWN_LAUNCHERS = (
    REPO_ROOT / "entrypoint.sh",
    REPO_ROOT / "scripts" / "start_dev_server.sh",
    REPO_ROOT / "docker-compose.dev.yml",
)

WORKERS_FLAG = re.compile(r"--workers\b")
WEB_CONCURRENCY = re.compile(r"\bWEB_CONCURRENCY\b")
REPLICAS = re.compile(r"^\s*replicas\s*:", re.M)


def _scanned_files() -> list[Path]:
    found = sorted(
        {
            *REPO_ROOT.glob("docker-compose*.yml"),
            *REPO_ROOT.glob("*.sh"),
            *(REPO_ROOT / "scripts").glob("*.sh"),
        }
    )
    return [p for p in found if p.is_file()]


def test_the_sweep_actually_finds_files():
    """A scan over an empty set passes every assertion below it."""
    scanned = _scanned_files()
    assert len(scanned) >= 4, f"launch-path discovery collapsed to {scanned}"


@pytest.mark.parametrize("launcher", KNOWN_LAUNCHERS, ids=lambda p: p.name)
def test_every_named_launch_path_still_exists_and_launches(launcher):
    assert launcher.exists(), (
        f"{launcher.name} is gone or renamed — re-point this sweep rather than "
        "deleting it; invariant 13 binds whatever replaced it"
    )
    assert "uvicorn" in launcher.read_text(encoding="utf-8"), (
        f"{launcher.name} no longer launches uvicorn — the sweep below would "
        "still pass while scanning something that is not a launch path"
    )


@pytest.mark.parametrize("path", _scanned_files(), ids=lambda p: p.name)
def test_no_launch_path_carries_a_worker_or_replica_knob(path):
    """All three spellings, on every discovered launch path.

    Raising the count is a flagged decision through the T4.10 record
    (`docs/planning/analyses/2026-08-16-t4.10-replica-decision.md`, which states
    what would flip it) — never a side effect of a deployment task. That record
    is the thing to change first; this test is what makes changing it necessary.
    """
    body = path.read_text(encoding="utf-8")

    assert not WORKERS_FLAG.search(body), (
        f"{path.name} passes --workers: invariant 13 is exactly one uvicorn "
        "worker on every launch path (T4.09: 17 BREAKS at N = 2)"
    )
    assert not WEB_CONCURRENCY.search(body), (
        f"{path.name} sets WEB_CONCURRENCY: uvicorn reads it when --workers is "
        "absent, so this raises the worker count while the launch command "
        "still reads as single-worker"
    )
    assert not REPLICAS.search(body), (
        f"{path.name} sets replicas: this raises the process count without "
        "touching uvicorn at all. `deploy:` for resource limits is fine — it "
        "is `replicas` under it that is the knob"
    )
