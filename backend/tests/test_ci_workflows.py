"""The CI workflows' runner routing and self-hosted isolation, read as YAML.

Every job must take its runner from `pick-runner`, and no job may hold a fixed
host port, host networking or a fixed container name. A job breaking either
rule still passes every GitHub-hosted run; it bypasses the self-hosted runner
or collides with a concurrent job only on the shared machine, so nothing but
this check catches it.
"""
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


@pytest.mark.parametrize("workflow", ["ci.yml", "release.yml"])
def test_every_job_takes_its_runner_from_the_picker(workflow):
    jobs = _jobs(workflow)
    assert jobs["pick-runner"]["runs-on"] == "ubuntu-latest"
    for key, job in jobs.items():
        if key == "pick-runner":
            continue
        assert "pick-runner" in _needs(job), f"{workflow}:{key} does not need pick-runner"
        if "uses" in job:
            assert job.get("with", {}).get("runs-on") == PASSED_THROUGH, f"{workflow}:{key}"
        else:
            assert job["runs-on"] == ROUTED, f"{workflow}:{key}"


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
