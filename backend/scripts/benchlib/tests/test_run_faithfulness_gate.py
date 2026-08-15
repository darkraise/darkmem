"""CLI-level tests for ``run_faithfulness_gate.py`` — the honest-reporting
paths a bare ``python scripts/benchlib/run_faithfulness_gate.py`` actually
takes. No database dependency: every case here either supplies no
``--database-url`` (bars resolve to committed defaults) or is refused
before any connection is attempted."""
from __future__ import annotations

import json

import pytest

from benchlib import faithfulness_gate as fg, run_faithfulness_gate as rfg
from benchlib.tests.fixtures import faithfulness_gate_fixture as fx

from app.services.verification_judge import JUDGE_ROLES


async def test_default_run_reports_gold_absent_and_exits_zero(capsys):
    code = await rfg._run([])
    out = capsys.readouterr().out
    assert code == 0
    assert "FAIL_CLOSED (gold absent)" in out
    assert str(fg.SPAN_GOLD_PATH) in out
    assert "not measured" in out


async def test_missing_gold_at_an_explicit_path_names_that_path(capsys, tmp_path):
    missing = tmp_path / "nope.json"
    code = await rfg._run(["--gold", str(missing)])
    out = capsys.readouterr().out
    assert code == 0
    assert str(missing) in out


async def test_a_present_gold_is_reported_but_not_scored_without_live(capsys, tmp_path):
    gold_path = tmp_path / "span_gold.json"
    gold_path.write_text(json.dumps({"pairs": fx.build_fixture_pairs()}))

    code = await rfg._run(["--gold", str(gold_path)])
    out = capsys.readouterr().out

    assert code == 0
    assert "gold present" in out
    assert "8 pairs" in out
    assert "--live" in out
    # never scored -- no precision/recall numbers printed
    assert "entailed_precision" not in out


async def test_live_without_an_api_key_is_refused(capsys, tmp_path):
    gold_path = tmp_path / "span_gold.json"
    gold_path.write_text(json.dumps({"pairs": fx.build_fixture_pairs()}))

    code = await rfg._run(["--gold", str(gold_path), "--live"])
    out = capsys.readouterr().out

    assert code == 1
    assert "FAIL_CLOSED (--live given with no --api-key)" in out


def test_forbidden_database_is_refused_before_any_connection():
    with pytest.raises(RuntimeError, match="darkmem_test"):
        rfg._assert_not_forbidden(
            "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
        )
    with pytest.raises(RuntimeError, match="darkmem_test_5"):
        rfg._assert_not_forbidden(
            "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_5"
        )


def test_a_real_or_bench_database_is_allowed_through_the_name_check():
    rfg._assert_not_forbidden(
        "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench"
    )  # must not raise


async def test_an_unreadable_bar_row_fails_closed_and_never_reads_as_a_clean_run(
    capsys, monkeypatch, tmp_path,
):
    """The three-way visibility obligation's failure branch: a bar row this
    module cannot read must say so, not silently fall back to the default
    and print a report that looks exactly like a healthy one. Simulated by
    monkeypatching `render_bar_visibility` to raise, since driving it for
    real needs a live database row this test suite has none of."""
    def _boom(_rows):
        raise ValueError("config row faithfulness_gate_recall_bar is unreadable")

    monkeypatch.setattr(rfg.fg, "render_bar_visibility", _boom)
    missing = tmp_path / "nope.json"

    code = await rfg._run(["--gold", str(missing)])
    out = capsys.readouterr().out

    assert code == 1
    assert "FAIL_CLOSED (unreadable bar row)" in out


# ── I-1: the qualification banner tracks the registry, never frozen prose ──


def test_missing_qualification_banner_matches_todays_registry_state():
    """Today "faithfulness" is not in JUDGE_ROLES, so the banner must say
    FAIL_CLOSED -- this is the state the frozen-prose defect happened to be
    correct about by accident."""
    assert "faithfulness" not in JUDGE_ROLES


def test_qualification_banner_flips_the_moment_the_role_is_wired(
    monkeypatch, capsys,
):
    """The pin: if this guard were still frozen prose (as it was before this
    fix round), this test would fail, because the banner would keep printing
    FAIL_CLOSED even after the role landed in JUDGE_ROLES -- exactly the
    false report TH1.09 would trigger on every gate run, including TH1.10's."""
    monkeypatch.setitem(rfg.JUDGE_ROLES, "faithfulness", ("some_bar",))
    rfg._print_missing_qualification()
    out = capsys.readouterr().out
    assert "FAIL_CLOSED" not in out
    assert "role wired" in out


def test_qualification_banner_still_fails_closed_when_role_is_absent(capsys):
    rfg._print_missing_qualification()
    out = capsys.readouterr().out
    assert "FAIL_CLOSED (missing qualification)" in out


# ── I-2: an unreadable bar row refuses a live run before spending it ────────


async def test_unreadable_bars_refuse_a_live_run_before_any_judge_call(
    capsys, monkeypatch, tmp_path,
):
    """The pre-spend guard. Simulates the unreadable-bar path the same way
    the existing bars test does (`render_bar_visibility` raises), then
    proves the live path never reaches `score_via_live_judge` at all --
    the mutation this guards against is exactly "continue past bars_ok and
    let the live probe spend the attempt before dying on a second raise"."""
    def _boom(_rows):
        raise ValueError("config row faithfulness_gate_recall_bar is unreadable")

    monkeypatch.setattr(rfg.fg, "render_bar_visibility", _boom)

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError(
            "score_via_live_judge was called with unreadable bars -- the "
            "pre-spend refusal did not fire"
        )

    monkeypatch.setattr(rfg.fg, "score_via_live_judge", _must_not_be_called)

    gold_path = tmp_path / "span_gold.json"
    gold_path.write_text(json.dumps({"pairs": fx.build_fixture_pairs()}))

    code = await rfg._run(["--gold", str(gold_path), "--live", "--api-key", "k"])
    out = capsys.readouterr().out

    assert code == 1
    assert "FAIL_CLOSED (unreadable bar row)" in out
    assert "refusing to spend" in out
