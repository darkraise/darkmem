#!/usr/bin/env python3
"""Pick the verification runner: self-hosted `darkmem-linux` when one is up.

The default `fallback` request uses `darkmem-linux` whenever a labelled runner
is online (queuing behind its current job when busy) and falls back to hosted
only when none is online or the listing fails. Without `RUNNER_PICKER_TOKEN`
it cannot see the runners, so it queues on self-hosted as before.

An explicit `auto` request prefers an idle runner and falls back to hosted,
also when the token is missing. Explicit self-hosted and hosted modes need no
token or API call. Every path exits 0. Stdlib only, so the picker job needs no
install step.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

LABEL = "darkmem-linux"
SELF_HOSTED = json.dumps(["self-hosted", "linux", "x64", LABEL], separators=(",", ":"))
HOSTED = json.dumps("ubuntu-latest")
API = "https://api.github.com"
TIMEOUT_SECONDS = 10


LISTING_MODES = ("auto", "fallback")


def _labelled(runners: list[dict]) -> list[dict]:
    # GitHub matches runs-on labels case-insensitively, so a runner registered
    # as `DarkMem-Linux` still takes the jobs this picker routes to it.
    return [
        r
        for r in runners
        if any((label.get("name") or "").lower() == LABEL for label in r.get("labels", []))
    ]


def choose(runners: list[dict], requested: str, token_present: bool) -> tuple[str, str]:
    if requested == "hosted":
        return HOSTED, "hosted requested"
    if requested == "self-hosted":
        return SELF_HOSTED, "self-hosted requested"
    if requested not in LISTING_MODES:
        return HOSTED, f"unknown runner request {requested!r}"
    if requested == "fallback":
        return _choose_fallback(runners, token_present)
    if not token_present:
        return HOSTED, "RUNNER_PICKER_TOKEN is not set"
    labelled = _labelled(runners)
    for runner in labelled:
        if runner.get("status") == "online" and not runner.get("busy"):
            return SELF_HOSTED, f"idle self-hosted runner {runner.get('name')}"
    if not labelled:
        return HOSTED, f"no {LABEL} runner registered"
    online = sum(1 for r in labelled if r.get("status") == "online")
    return HOSTED, f"{len(labelled)} {LABEL} runner(s), {online} online, none idle"


def _choose_fallback(runners: list[dict], token_present: bool) -> tuple[str, str]:
    if not token_present:
        return SELF_HOSTED, "RUNNER_PICKER_TOKEN is not set, so queuing on self-hosted"
    labelled = _labelled(runners)
    online = [r for r in labelled if r.get("status") == "online"]
    for runner in online:
        if not runner.get("busy"):
            return SELF_HOSTED, f"idle self-hosted runner {runner.get('name')}"
    if online:
        return SELF_HOSTED, f"{len(online)} {LABEL} runner(s) online, all busy, queuing"
    if not labelled:
        return HOSTED, f"no {LABEL} runner registered"
    return HOSTED, f"{len(labelled)} {LABEL} runner(s), none online"


def _fetch(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def list_runners(repo: str, token: str, fetch=_fetch) -> list[dict]:
    runners: list[dict] = []
    page = 1
    while True:
        body = fetch(f"{API}/repos/{repo}/actions/runners?per_page=100&page={page}", token)
        batch = body.get("runners", [])
        runners.extend(batch)
        if not batch or len(runners) >= body.get("total_count", 0):
            return runners
        page += 1


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def main(env=os.environ, fetch=_fetch) -> int:
    requested = (env.get("REQUESTED") or "fallback").strip()
    token = (env.get("GH_TOKEN") or "").strip()
    runners: list[dict] = []
    error = None
    if requested in LISTING_MODES and token:
        try:
            runners = list_runners(env["GITHUB_REPOSITORY"], token, fetch)
        except Exception as exc:  # any listing failure falls back to hosted
            error = f"runner listing failed ({type(exc).__name__}: {exc})"
    if error:
        runs_on, reason = HOSTED, error
    else:
        runs_on, reason = choose(runners, requested, bool(token))
    reason = " ".join(reason.split())
    _append(env.get("GITHUB_OUTPUT"), f"runs-on={runs_on}\nreason={reason}\n")
    _append(env.get("GITHUB_STEP_SUMMARY"), f"Runner: `{runs_on}` ({reason})\n")
    print(f"runs-on={runs_on} ({reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
