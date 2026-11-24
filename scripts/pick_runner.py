#!/usr/bin/env python3
"""Pick the verification runner: self-hosted unless hosted is requested.

Self-hosted runners come from ghr, which starts a single-use runner for each
queued job. No runner is registered while no job is queued, so there is
nothing to list in advance: a self-hosted job waits in the queue until ghr
starts its runner. `hosted` sends the checks to GitHub-hosted runners, for
when the ghr host is down. A pull request from a fork
(`FORK_PULL_REQUEST=true`) is sent hosted whatever the request, so outside
code never reaches the LAN host. Every path exits 0. Stdlib only, so the
picker job needs no install step.
"""
from __future__ import annotations

import json
import os
import sys

# The labels every ghr runner carries, whatever else ghr is configured to add.
SELF_HOSTED = json.dumps(["self-hosted", "linux", "x64"], separators=(",", ":"))
HOSTED = json.dumps("ubuntu-latest")


def choose(requested: str, fork_pull_request: bool) -> tuple[str, str]:
    if fork_pull_request:
        return HOSTED, "pull request from a fork"
    if requested == "self-hosted":
        return SELF_HOSTED, "self-hosted requested; ghr starts a runner for each queued job"
    if requested == "hosted":
        return HOSTED, "hosted requested"
    return HOSTED, f"unknown runner request {requested!r}"


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def main(env=os.environ) -> int:
    requested = (env.get("REQUESTED") or "").strip() or "self-hosted"
    fork = (env.get("FORK_PULL_REQUEST") or "").strip().lower() == "true"
    runs_on, reason = choose(requested, fork)
    reason = " ".join(reason.split())
    _append(env.get("GITHUB_OUTPUT"), f"runs-on={runs_on}\nreason={reason}\n")
    _append(env.get("GITHUB_STEP_SUMMARY"), f"Runner: `{runs_on}` ({reason})\n")
    print(f"runs-on={runs_on} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
