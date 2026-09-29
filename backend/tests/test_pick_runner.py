"""`scripts/pick_runner.py` routes every CI job, so its one promise is tested
from each side: an idle darkmem-ci runner is used, and anything else falls back
to GitHub-hosted without failing the run."""
from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF_HOSTED = '["self-hosted","linux","x64","darkmem-ci"]'
HOSTED = '"ubuntu-latest"'


def _load():
    spec = importlib.util.spec_from_file_location("pick_runner", ROOT / "scripts/pick_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pick = _load()


def _runner(name="box-1", status="online", busy=False, labels=("self-hosted", "darkmem-ci")):
    return {"name": name, "status": status, "busy": busy, "labels": [{"name": n} for n in labels]}


def test_an_idle_labelled_runner_is_used():
    runs_on, reason = pick.choose([_runner()], "auto", True)
    assert runs_on == SELF_HOSTED
    assert "box-1" in reason


def test_a_busy_runner_falls_back():
    runs_on, reason = pick.choose([_runner(busy=True)], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-ci runner(s), 1 online, none idle"


def test_an_offline_runner_falls_back():
    runs_on, reason = pick.choose([_runner(status="offline")], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-ci runner(s), 0 online, none idle"


def test_a_runner_without_the_label_is_ignored():
    runs_on, reason = pick.choose([_runner(labels=("self-hosted", "other"))], "auto", True)
    assert runs_on == HOSTED
    assert reason == "no darkmem-ci runner registered"


def test_an_empty_listing_falls_back():
    assert pick.choose([], "auto", True) == (HOSTED, "no darkmem-ci runner registered")


def test_a_missing_token_falls_back():
    assert pick.choose([_runner()], "auto", False) == (HOSTED, "RUNNER_PICKER_TOKEN is not set")


def test_hosted_can_be_forced():
    assert pick.choose([_runner()], "hosted", True) == (HOSTED, "hosted requested")


def test_self_hosted_can_be_forced_without_a_listing():
    assert pick.choose([], "self-hosted", False) == (SELF_HOSTED, "self-hosted requested")


def test_an_unknown_request_falls_back():
    assert pick.choose([_runner()], "gpu", True) == (HOSTED, "unknown runner request 'gpu'")


def test_the_second_idle_runner_is_found_past_a_busy_one():
    runners = [_runner("box-1", busy=True), _runner("box-2")]
    runs_on, reason = pick.choose(runners, "auto", True)
    assert runs_on == SELF_HOSTED
    assert "box-2" in reason


def test_listing_follows_pages():
    first = [_runner(f"r{i}", labels=("self-hosted",)) for i in range(100)]
    pages = {1: {"total_count": 101, "runners": first}, 2: {"total_count": 101, "runners": [_runner("last")]}}
    seen = []

    def fetch(url, token):
        page = int(url.rsplit("page=", 1)[1])
        seen.append(page)
        return pages[page]

    runners = pick.list_runners("darkraise/darkmem", "t", fetch)
    assert seen == [1, 2]
    assert [r["name"] for r in runners][-1] == "last"
    assert len(runners) == 101


def _env(tmp_path, **extra):
    env = {
        "GITHUB_OUTPUT": str(tmp_path / "out"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "GITHUB_REPOSITORY": "darkraise/darkmem",
    }
    env.update(extra)
    return env


def _outputs(tmp_path):
    lines = (tmp_path / "out").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_main_writes_both_outputs_for_an_idle_runner(tmp_path):
    env = _env(tmp_path, GH_TOKEN="t")
    assert pick.main(env, fetch=lambda url, token: {"total_count": 1, "runners": [_runner()]}) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == SELF_HOSTED
    assert "box-1" in out["reason"]
    assert SELF_HOSTED in (tmp_path / "summary").read_text()


def test_main_falls_back_when_the_api_fails(tmp_path):
    def fetch(url, token):
        raise urllib.error.URLError("timed out")

    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == HOSTED
    assert out["reason"].startswith("runner listing failed (URLError")


def test_main_falls_back_without_a_repository(tmp_path):
    env = _env(tmp_path, GH_TOKEN="t")
    del env["GITHUB_REPOSITORY"]
    assert pick.main(env, fetch=lambda url, token: {"total_count": 0, "runners": []}) == 0
    assert _outputs(tmp_path)["runs-on"] == HOSTED


def test_main_makes_no_call_when_hosted_is_forced(tmp_path):
    def fetch(url, token):
        raise AssertionError("the API must not be called")

    assert pick.main(_env(tmp_path, GH_TOKEN="t", REQUESTED="hosted"), fetch=fetch) == 0
    assert _outputs(tmp_path) == {"runs-on": HOSTED, "reason": "hosted requested"}


def test_main_keeps_a_multiline_error_on_one_output_line(tmp_path):
    def fetch(url, token):
        raise RuntimeError("line one\nline two")

    pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch)
    assert len((tmp_path / "out").read_text().splitlines()) == 2


def test_outputs_are_valid_json():
    for requested in ("hosted", "self-hosted"):
        runs_on, _ = pick.choose([], requested, True)
        json.loads(runs_on)


def test_the_label_matches_regardless_of_case():
    runs_on, _ = pick.choose([_runner(labels=("self-hosted", "DarkMem-CI"))], "auto", True)
    assert runs_on == SELF_HOSTED


def test_listing_stops_on_an_empty_page_despite_a_wrong_total():
    calls = []

    def fetch(url, token):
        calls.append(url)
        return {"total_count": 500, "runners": [_runner()] if len(calls) == 1 else []}

    assert len(pick.list_runners("darkraise/darkmem", "t", fetch)) == 1
    assert len(calls) == 2


def test_main_without_a_token_makes_no_call(tmp_path):
    def fetch(url, token):
        raise AssertionError("the API must not be called")

    assert pick.main(_env(tmp_path), fetch=fetch) == 0
    assert _outputs(tmp_path) == {"runs-on": HOSTED, "reason": "RUNNER_PICKER_TOKEN is not set"}
