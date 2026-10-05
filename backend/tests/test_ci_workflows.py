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
    ("ci.yml", {"pick-runner", "images"}, {"backend", "frontend", "frontend-tests", "image-smoke"}),
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


def test_smoke_loads_the_hosted_build_artifact():
    jobs = _jobs("ci.yml")
    assert "images" in _needs(jobs["image-smoke"])
    uploads = [s for s in jobs["images"]["steps"] if s.get("uses", "").startswith("actions/upload-artifact@")]
    downloads = [s for s in jobs["image-smoke"]["steps"] if s.get("uses", "").startswith("actions/download-artifact@")]
    assert len(uploads) == len(downloads) == 1
    assert downloads[0]["with"]["artifact-ids"] == "${{ needs.images.outputs.artifact-id }}"
    assert jobs["images"]["outputs"]["artifact-id"] == "${{ steps.upload.outputs.artifact-id }}"


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


REPO = WORKFLOWS.parents[1]


def _steps(workflow: str):
    for key, job in _jobs(workflow).items():
        for step in job.get("steps", []):
            yield f"{workflow}:{key}", step


def test_toolchains_name_a_version_line_never_a_patch():
    # Self-hosted runners keep every toolchain they download. Naming only a
    # major/minor line and leaving check-latest off lets a runner reuse the
    # build already in its tool cache, so it holds one per line, not one per
    # patch. Node's line lives in frontend/.nvmrc beside the Dockerfile's.
    nvmrc = (REPO / "frontend" / ".nvmrc").read_text().strip()
    assert re.fullmatch(r"\d+", nvmrc), f"frontend/.nvmrc must be a bare major, got {nvmrc!r}"
    dockerfile = (REPO / "Dockerfile").read_text()
    assert re.search(rf"^FROM node:{nvmrc}-", dockerfile, re.M), "Dockerfile node line drifted from .nvmrc"
    python_line = re.search(r"^FROM python:(\d+\.\d+)-", dockerfile, re.M).group(1)

    for workflow in ("ci.yml", "release.yml"):
        for where, step in _steps(workflow):
            uses, with_ = step.get("uses", ""), step.get("with") or {}
            if uses.startswith("actions/setup-"):
                assert with_.get("check-latest") in (None, False), where
            if uses.startswith("actions/setup-node@"):
                assert with_.get("node-version-file") == "frontend/.nvmrc", where
                assert "node-version" not in with_, where
            if uses.startswith("actions/setup-python@"):
                assert str(with_["python-version"]) == python_line, where
        for key, job in _jobs(workflow).items():
            image = job.get("container")
            if isinstance(image, str) and image.startswith("python:"):
                assert image.split(":")[1].startswith(f"{python_line}-"), f"{workflow}:{key}"
