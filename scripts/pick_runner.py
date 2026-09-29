#!/usr/bin/env python3
"""Pick the runner a CI run uses: an idle self-hosted `darkmem-ci` runner when
one exists, GitHub-hosted otherwise.

Every picking path answers GitHub-hosted on doubt and exits 0: the fallback
must never be the thing that fails a run. Stdlib only, so the picker job needs
no install step.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

LABEL = "darkmem-ci"
SELF_HOSTED = json.dumps(["self-hosted", "linux", "x64", LABEL], separators=(",", ":"))
HOSTED = json.dumps("ubuntu-latest")
API = "https://api.github.com"
TIMEOUT_SECONDS = 10


def choose(runners: list[dict], requested: str, token_present: bool) -> tuple[str, str]:
    if requested == "hosted":
        return HOSTED, "hosted requested"
    if requested == "self-hosted":
        return SELF_HOSTED, "self-hosted requested"
    if requested != "auto":
        return HOSTED, f"unknown runner request {requested!r}"
    if not token_present:
        return HOSTED, "RUNNER_PICKER_TOKEN is not set"
    labelled = [
        r for r in runners if any(label.get("name") == LABEL for label in r.get("labels", []))
    ]
    for runner in labelled:
        if runner.get("status") == "online" and not runner.get("busy"):
            return SELF_HOSTED, f"idle self-hosted runner {runner.get('name')}"
    if not labelled:
        return HOSTED, f"no {LABEL} runner registered"
    online = sum(1 for r in labelled if r.get("status") == "online")
    return HOSTED, f"{len(labelled)} {LABEL} runner(s), {online} online, none idle"


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
    requested = (env.get("REQUESTED") or "auto").strip()
    token = (env.get("GH_TOKEN") or "").strip()
    runners: list[dict] = []
    error = None
    if requested == "auto" and token:
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
