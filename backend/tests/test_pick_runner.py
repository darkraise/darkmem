"""Verification prefers an online darkmem-linux runner and falls back to hosted."""
from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF_HOSTED = '["self-hosted","linux","x64","darkmem-linux"]'
HOSTED = '"ubuntu-latest"'


def _load():
    spec = importlib.util.spec_from_file_location("pick_runner", ROOT / "scripts/pick_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pick = _load()


def _runner(name="box-1", status="online", busy=False, labels=("self-hosted", "darkmem-linux")):
    return {"name": name, "status": status, "busy": busy, "labels": [{"name": n} for n in labels]}


def test_an_idle_labelled_runner_is_used():
    runs_on, reason = pick.choose([_runner()], "auto", True)
    assert runs_on == SELF_HOSTED
    assert "box-1" in reason


def test_a_busy_runner_falls_back():
    runs_on, reason = pick.choose([_runner(busy=True)], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-linux runner(s), 1 online, none idle"


def test_an_offline_runner_falls_back():
    runs_on, reason = pick.choose([_runner(status="offline")], "auto", True)
    assert runs_on == HOSTED
    assert reason == "1 darkmem-linux runner(s), 0 online, none idle"


def test_a_runner_without_the_label_is_ignored():
    runs_on, reason = pick.choose([_runner(labels=("self-hosted", "other"))], "auto", True)
    assert runs_on == HOSTED
    assert reason == "no darkmem-linux runner registered"


def test_an_empty_listing_falls_back():
    assert pick.choose([], "auto", True) == (HOSTED, "no darkmem-linux runner registered")


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
    env = _env(tmp_path, GH_TOKEN="t", REQUESTED="auto")
    assert pick.main(env, fetch=lambda url, token: {"total_count": 1, "runners": [_runner()]}) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == SELF_HOSTED
    assert "box-1" in out["reason"]
    assert SELF_HOSTED in (tmp_path / "summary").read_text()


def test_main_falls_back_when_the_api_fails(tmp_path):
    def fetch(url, token):
        raise urllib.error.URLError("timed out")

    assert pick.main(_env(tmp_path, GH_TOKEN="t", REQUESTED="auto"), fetch=fetch) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == HOSTED
    assert out["reason"].startswith("runner listing failed (URLError")


def test_main_falls_back_without_a_repository(tmp_path):
    env = _env(tmp_path, GH_TOKEN="t", REQUESTED="auto")
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

    pick.main(_env(tmp_path, GH_TOKEN="t", REQUESTED="auto"), fetch=fetch)
    assert len((tmp_path / "out").read_text().splitlines()) == 2


def test_outputs_are_valid_json():
    for requested in ("hosted", "self-hosted", "fallback"):
        runs_on, _ = pick.choose([], requested, True)
        json.loads(runs_on)


def test_the_label_matches_regardless_of_case():
    runs_on, _ = pick.choose([_runner(labels=("self-hosted", "DarkMem-Linux"))], "auto", True)
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

    assert pick.main(_env(tmp_path, REQUESTED="auto"), fetch=fetch) == 0
    assert _outputs(tmp_path) == {"runs-on": HOSTED, "reason": "RUNNER_PICKER_TOKEN is not set"}


def test_fallback_uses_an_idle_runner():
    runs_on, reason = pick.choose([_runner()], "fallback", True)
    assert runs_on == SELF_HOSTED
    assert "box-1" in reason


def test_fallback_queues_behind_a_busy_online_runner():
    runs_on, reason = pick.choose([_runner(busy=True)], "fallback", True)
    assert runs_on == SELF_HOSTED
    assert reason == "1 darkmem-linux runner(s) online, all busy, queuing"


def test_fallback_goes_hosted_when_every_runner_is_offline():
    runners = [_runner("box-1", status="offline"), _runner("box-2", status="offline", busy=True)]
    assert pick.choose(runners, "fallback", True) == (HOSTED, "2 darkmem-linux runner(s), none online")


def test_fallback_goes_hosted_when_no_runner_is_registered():
    runners = [_runner(labels=("self-hosted", "other"))]
    assert pick.choose(runners, "fallback", True) == (HOSTED, "no darkmem-linux runner registered")


def test_fallback_without_a_token_queues_on_self_hosted():
    runs_on, reason = pick.choose([], "fallback", False)
    assert runs_on == SELF_HOSTED
    assert "RUNNER_PICKER_TOKEN is not set" in reason


def test_default_is_fallback_and_lists_runners(tmp_path):
    seen = []

    def fetch(url, token):
        seen.append(url)
        return {"total_count": 1, "runners": [_runner(status="offline")]}

    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch, sleep=lambda s: None) == 0
    assert len(seen) == 2
    out = _outputs(tmp_path)
    assert out["runs-on"] == HOSTED
    assert out["reason"].endswith("(rechecked after 20s)")


def test_fallback_recheck_catches_a_runner_that_registers_in_the_gap(tmp_path):
    listings = iter([[], [_runner("ghr-next")]])
    naps = []

    def fetch(url, token):
        runners = next(listings)
        return {"total_count": len(runners), "runners": runners}

    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch, sleep=naps.append) == 0
    assert naps == [pick.RECHECK_SECONDS]
    out = _outputs(tmp_path)
    assert out["runs-on"] == SELF_HOSTED
    assert "ghr-next" in out["reason"]


def test_fallback_does_not_recheck_when_self_hosted_is_chosen(tmp_path):
    def sleep(seconds):
        raise AssertionError("no recheck when a runner is online")

    fetch = lambda url, token: {"total_count": 1, "runners": [_runner(busy=True)]}
    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch, sleep=sleep) == 0
    assert _outputs(tmp_path)["runs-on"] == SELF_HOSTED


def test_default_without_a_token_queues_on_self_hosted_without_a_call(tmp_path):
    def fetch(url, token):
        raise AssertionError("the API must not be called without a token")

    assert pick.main(_env(tmp_path), fetch=fetch) == 0
    assert _outputs(tmp_path)["runs-on"] == SELF_HOSTED


def test_default_falls_back_to_hosted_when_the_listing_fails(tmp_path):
    def fetch(url, token):
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)

    assert pick.main(_env(tmp_path, GH_TOKEN="t"), fetch=fetch, sleep=lambda s: None) == 0
    out = _outputs(tmp_path)
    assert out["runs-on"] == HOSTED
    assert out["reason"].startswith("runner listing failed (HTTPError")
