"""Verification queues on ghr's self-hosted runners unless hosted is asked for."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF_HOSTED = '["self-hosted","linux","x64"]'
HOSTED = '"ubuntu-latest"'


def _load():
    spec = importlib.util.spec_from_file_location("pick_runner", ROOT / "scripts/pick_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pick = _load()


def _env(tmp_path, **extra):
    env = {
        "GITHUB_OUTPUT": str(tmp_path / "out"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }
    env.update(extra)
    return env


def _outputs(tmp_path):
    lines = (tmp_path / "out").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_self_hosted_asks_only_for_the_labels_every_ghr_runner_carries():
    runs_on, _ = pick.choose("self-hosted", False)
    assert json.loads(runs_on) == ["self-hosted", "linux", "x64"]


def test_hosted_can_be_forced():
    assert pick.choose("hosted", False) == (HOSTED, "hosted requested")


def test_an_unknown_request_goes_hosted():
    assert pick.choose("gpu", False) == (HOSTED, "unknown runner request 'gpu'")


def test_the_default_is_self_hosted(tmp_path):
    assert pick.main(_env(tmp_path)) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == SELF_HOSTED
    assert "ghr" in out["reason"]
    assert SELF_HOSTED in (tmp_path / "summary").read_text()


def test_a_blank_request_is_the_default(tmp_path):
    assert pick.main(_env(tmp_path, REQUESTED="  ")) == 0
    assert _outputs(tmp_path)["runs-on"] == SELF_HOSTED


def test_main_writes_both_outputs_on_one_line_each(tmp_path):
    assert pick.main(_env(tmp_path, REQUESTED="hosted")) == 0
    assert _outputs(tmp_path) == {"runs-on": HOSTED, "reason": "hosted requested"}


def test_outputs_are_valid_json():
    for requested in ("hosted", "self-hosted", "unknown"):
        for fork in (True, False):
            runs_on, _ = pick.choose(requested, fork)
            json.loads(runs_on)


def test_picker_routes_a_fork_to_hosted(tmp_path):
    for requested in ("self-hosted", "hosted", ""):
        out = tmp_path / (requested or "default")
        out.mkdir()
        env = _env(out, REQUESTED=requested, FORK_PULL_REQUEST="true")
        assert pick.main(env) == 0
        assert _outputs(out) == {"runs-on": HOSTED, "reason": "pull request from a fork"}, requested
