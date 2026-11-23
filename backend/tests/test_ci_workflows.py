"""CI keeps builds/publishing hosted and delegates verification safely."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
ROUTED = "${{ fromJSON(needs.pick-runner.outputs.runs-on) }}"
PASSED_THROUGH = "${{ needs.pick-runner.outputs.runs-on }}"


def _jobs(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())["jobs"]


def _needs(job: dict) -> list[str]:
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


@pytest.mark.parametrize("workflow,hosted,routed", [
    ("ci.yml", {"pick-runner", "images"}, {"backend", "frontend", "frontend-tests", "clients"}),
    ("release.yml", {"pick-runner", "plan", "prepare", "publish", "tag", "github-release"}, set()),
])
def test_builds_and_releases_stay_hosted_while_checks_use_the_picker(workflow, hosted, routed):
    jobs = _jobs(workflow)
    for key in hosted:
        assert jobs[key]["runs-on"] == "ubuntu-latest", f"{workflow}:{key}"
    for key in routed:
        assert "pick-runner" in _needs(jobs[key]), f"{workflow}:{key}"
        assert jobs[key]["runs-on"] == ROUTED, f"{workflow}:{key}"
    if workflow == "release.yml":
        assert "pick-runner" in _needs(jobs["verify"])
        assert jobs["verify"]["with"]["runs-on"] == PASSED_THROUGH
        assert "verify" in _needs(jobs["prepare"])
        assert "prepare" in _needs(jobs["publish"])


def test_e2e_suites_have_private_networks_and_databases_on_self_hosted():
    job = _jobs("ci.yml")["e2e"]
    assert job["runs-on"] == ["self-hosted", "linux", "x64", "darkmem-linux"]
    assert set(job["strategy"]["matrix"]["suite"]) == {"api", "playwright"}
    assert job["container"]
    assert not job["services"]["postgres"].get("ports")
    assert job["services"]["postgres"]["env"]["POSTGRES_DB"] == "darkmem_e2e"
    assert job["env"]["TEST_DATABASE_URL"].endswith("@postgres:5432/darkmem_e2e")


def test_backend_suites_run_in_a_container_with_private_databases():
    # setup-python has no build for the darkmem-linux runners' OS, so the
    # backend suites bring their interpreter in a job container instead.
    job = _jobs("ci.yml")["backend"]
    assert job["container"] == "python:3.12-bookworm"
    assert not any(
        s.get("uses", "").startswith("actions/setup-python@") for s in job["steps"]
    )
    assert not job["services"]["postgres"].get("ports")
    assert job["env"]["TEST_DATABASE_URL"].endswith("@postgres:5432/darkmem_test")
    assert job["env"]["BENCH_DATABASE_URL"].endswith("@postgres:5432/darkmem_bench")
    restore = job["steps"][-1]
    assert restore["if"] == "always()" and "chown" in restore["run"]


def test_the_image_boots_in_the_job_that_built_it():
    # An 830 MB image artifact per run filled the account's Actions storage
    # (2026-10-06); building and booting in one job stores none.
    job = _jobs("ci.yml")["images"]
    names = [s.get("name", "") for s in job["steps"]]
    assert "Build image" in names and "Boot the image and probe /health" in names
    assert names.index("Build image") < names.index("Boot the image and probe /health")
    assert "postgres" in job["services"]


def test_the_image_job_uploads_no_artifact():
    for step in _jobs("ci.yml")["images"]["steps"]:
        assert not step.get("uses", "").startswith("actions/upload-artifact@")
    build = next(s for s in _jobs("ci.yml")["images"]["steps"] if s.get("name") == "Build image")
    assert build["env"]["DOCKER_BUILD_RECORD_UPLOAD"] is False


def test_cancelled_tag_job_creates_no_release():
    job = _jobs("release.yml")["github-release"]
    condition = " ".join(job["if"].split())
    assert "needs.tag.result == 'success'" in condition
    assert "!= 'failure'" not in condition
    # A hand-cut tag skips the tag job; only that run may release without it.
    assert "(github.ref_type == 'tag' && needs.tag.result == 'skipped')" in condition
    create = next(s for s in job["steps"] if "gh release create" in s.get("run", ""))
    assert "--verify-tag" in create["run"]


def test_ci_runs_extension_and_sdk_suites():
    jobs = _jobs("ci.yml")
    steps = [
        (step.get("working-directory", ""), step.get("run", ""))
        for job in jobs.values()
        for step in job.get("steps", [])
    ]

    def runs(directory: str, command: str) -> bool:
        return any(
            command in script and (where == directory or f"cd {directory}" in script or f"-C {directory}" in script)
            for where, script in steps
        )

    assert runs("extension", "npm test")
    assert runs("sdks/python", "pytest")
    assert runs("sdks/ts", "npm test")
    assert runs("sdks", "make build")


@pytest.mark.parametrize("workflow", ["ci.yml", "release.yml"])
def test_no_job_holds_a_fixed_host_resource(workflow):
    for key, job in _jobs(workflow).items():
        for service in job.get("services", {}).values():
            for port in service.get("ports", []):
                assert ":" not in str(port), f"{workflow}:{key} publishes a fixed host port {port!r}"
        for step in job.get("steps", []):
            script = step.get("run", "")
            assert not re.search(r"--network[ =]host\b", script), f"{workflow}:{key}"
            for name in re.findall(r"--name[ =](\S+)", script):
                assert "$" in name, f"{workflow}:{key} names a container {name!r}"


def test_the_ci_image_tag_is_per_run():
    for step in _jobs("ci.yml")["images"]["steps"]:
        tags = step.get("with", {}).get("tags")
        if tags is not None:
            assert "${{" in tags, f"fixed image tag {tags!r}"


SELF_HOSTED_LABELS = {"self-hosted", "darkmem-linux"}


def _evaluate(expression: str, context: dict) -> bool:
    """Evaluate the small GitHub expression subset the fork condition uses."""
    body = expression.strip()
    if body.startswith("${{") and body.endswith("}}"):
        body = body[3:-2]
    names = sorted(context, key=len, reverse=True)
    for i, name in enumerate(names):
        body = body.replace(name, f"_v{i}")
    body = re.sub(r"!(?!=)", " not ", body).replace("||", " or ").replace("&&", " and ")
    residue = re.sub(r"'[^']*'|_v\d+|\bnot\b|\bor\b|\band\b|==|!=|[()\s]", "", body)
    assert not residue, f"unsupported expression text {residue!r}"
    return bool(eval(body, {"__builtins__": {}}, {f"_v{i}": context[n] for i, n in enumerate(names)}))


def _events() -> list[tuple[str, dict, bool]]:
    def ctx(event, head=None):
        return {
            "github.event.pull_request.head.repo.full_name": head,
            "github.event_name": event,
            "github.repository": "darkraise/darkmem",
        }

    return [
        ("fork pull request", ctx("pull_request", "someone/darkmem"), False),
        ("same-repository pull request", ctx("pull_request", "darkraise/darkmem"), True),
        ("push to master", ctx("push"), True),
        ("workflow_dispatch", ctx("workflow_dispatch"), True),
    ]


def _literal_labels(runs_on) -> set[str]:
    labels = runs_on if isinstance(runs_on, list) else [runs_on]
    return {label for label in labels if isinstance(label, str) and "${{" not in label}


def test_fork_pull_request_never_reaches_self_hosted():
    guarded = set()
    for workflow in ("ci.yml", "release.yml", "cache-cleanup.yml"):
        for key, job in _jobs(workflow).items():
            runs_on = job.get("runs-on", "")
            labels = runs_on if isinstance(runs_on, list) else [runs_on]
            for label in labels:
                # A computed runner must come from the picker, whose fork
                # marker is checked below; anything else is unchecked routing.
                if isinstance(label, str) and "${{" in label:
                    assert "needs.pick-runner.outputs" in label, f"{workflow}:{key} runs-on {label}"
            if not _literal_labels(runs_on) & SELF_HOSTED_LABELS:
                continue
            guarded.add(f"{workflow}:{key}")
            condition = job.get("if")
            assert condition, f"{workflow}:{key} runs on a self-hosted label with no fork guard"
            for label, context, expected in _events():
                assert _evaluate(condition, context) is expected, f"{workflow}:{key}: {label}"
    assert "ci.yml:e2e" in guarded

    jobs = _jobs("ci.yml")
    for key in ("backend", "frontend", "frontend-tests"):
        assert "if" not in jobs[key], f"ci.yml:{key} runs on a picked runner and must still run for forks"
    pick_env = next(s for s in jobs["pick-runner"]["steps"] if s.get("id") == "pick")["env"]
    marker = pick_env["FORK_PULL_REQUEST"]
    for label, context, trusted in _events():
        assert _evaluate(marker, context) is (not trusted), f"fork marker: {label}"


def _third_party_uses() -> list[tuple[str, str, str]]:
    found = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for line in path.read_text().splitlines():
            match = re.match(r"\s*(?:-\s*)?uses:\s*(\S+)(.*)$", line)
            if not match or match.group(1).startswith("./"):
                continue
            action = match.group(1)
            if action.split("/", 1)[0] in {"actions", "github"}:
                continue
            found.append((path.name, action, match.group(2)))
    return found


def test_third_party_actions_are_pinned_to_shas():
    uses = _third_party_uses()
    assert uses
    for workflow, action, rest in uses:
        assert "@" in action, f"{workflow}: {action} is not pinned to a commit sha"
        ref = action.rsplit("@", 1)[1]
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{workflow}: {action} is not pinned to a commit sha"
        assert re.fullmatch(r"\s*#\s*v\d[\w.-]*\s*", rest), f"{workflow}: {action} names no tag comment"


def _gha_scope(value: str | None) -> str | None:
    if not value:
        return None
    fields = dict(part.split("=", 1) for part in value.split(",") if "=" in part)
    return fields.get("scope", "buildkit")


def test_scan_job_does_not_write_the_publish_cache():
    scan = next(s for s in _jobs("ci.yml")["images"]["steps"] if s.get("name") == "Build image")
    publish = next(s for s in _jobs("release.yml")["publish"]["steps"] if s.get("name") == "Build and push")
    written = _gha_scope(scan["with"].get("cache-to"))
    read = _gha_scope(publish["with"].get("cache-from"))
    assert written is None or written != read
