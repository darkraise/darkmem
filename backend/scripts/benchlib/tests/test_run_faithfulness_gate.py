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


async def test_default_run_reports_the_present_gold_and_never_scores_it(capsys):
    """This asserted `FAIL_CLOSED (gold absent)` until 2026-08-17, and the gold
    landing IS the deliberate diff that assertion demanded — the same shape as
    the qualification-record zero-pin. It is inverted rather than deleted: a
    test that silently stopped applying would leave the default path unpinned.

    What must hold now: the runner sees the gold, reports its LIVE pair count
    (260, not the 277 entries the file carries — 17 are retired in place and
    nothing may score a retired pair), and still spends nothing without --live.
    """
    code = await rfg._run([])
    out = capsys.readouterr().out
    assert code == 0
    assert "gold present" in out
    assert str(fg.SPAN_GOLD_PATH) in out
    assert "260 pairs" in out
    # the load-bearing half: a present gold must NOT be scored by a bare run
    assert "not measured" in out
    assert "--live" in out


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
    assert f"{len(fx.build_fixture_pairs())} pairs" in out
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


def test_missing_qualification_banner_matches_todays_registry_state(capsys):
    """TH1.09 wired the role, so today's banner is the *other* branch.

    This assertion was `"faithfulness" not in JUDGE_ROLES` until that landed —
    which is the whole reason the banner was derived from the registry rather
    than written as prose. The test tracks the same fact and had to move with
    it; what it must never become is an assertion that passes in both states.
    """
    assert "faithfulness" in JUDGE_ROLES
    rfg._print_missing_qualification()
    out = capsys.readouterr().out
    assert "FAIL_CLOSED" not in out
    assert "role wired" in out


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


def test_qualification_banner_still_fails_closed_when_role_is_absent(
    monkeypatch, capsys,
):
    """The other direction, now reachable only by simulation: with the role
    removed the banner must fail closed again. Kept rather than deleted — a
    banner that can only ever print one branch is not derived from anything."""
    monkeypatch.delitem(rfg.JUDGE_ROLES, "faithfulness")
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


# ── I-3: a partial judge override no longer crashes ─────────────────────────


def test_judge_purpose_config_merges_a_single_override_per_field():
    """The reproduced defect: `--model` alone used to pass `base_url=None,
    api_kind=None` through a blanket dict-merge, which pydantic rejected.
    A single-field override must fall back to the other two defaults, not
    stomp them with an explicit None."""
    config = fg.judge_purpose_config("k", model="gpt-5.5")
    purpose = config["verification"]
    assert purpose.model == "gpt-5.5"
    assert purpose.base_url == fg.DEFAULT_JUDGE["base_url"]
    assert purpose.api_kind == fg.DEFAULT_JUDGE["api_kind"]


def test_judge_purpose_config_with_no_overrides_matches_default_judge():
    config = fg.judge_purpose_config("k")
    purpose = config["verification"]
    assert purpose.model == fg.DEFAULT_JUDGE["model"]
    assert purpose.base_url == fg.DEFAULT_JUDGE["base_url"]
    assert purpose.api_kind == fg.DEFAULT_JUDGE["api_kind"]


async def test_run_live_with_only_model_override_does_not_crash(monkeypatch, tmp_path):
    """CLI-level reproduction of the reviewer's exact repro:
    `--live --api-key K --model gpt-5.5` with base-url/api-kind left at
    their argparse None default."""
    gold_path = tmp_path / "span_gold.json"
    gold_path.write_text(json.dumps({"pairs": fx.build_fixture_pairs()}))

    async def _stub_live_judge(pairs, base_dir, config, *, cache_dir):
        from benchlib.twin import LatencyRecorder, Twin
        from app.services.verification_judge import ProbeVerdict

        verdicts = {
            p["id"]: ProbeVerdict(verdict="entailed", reason="stub", raw="{}", valid=True)
            for p in pairs
        }
        score = fg.score_span_judgments(pairs, verdicts)
        recorder = LatencyRecorder()
        recorder.record("judge_call", 0.01, "live")
        from benchlib.twin import TokenLedger
        twin = Twin.capture(recorder, TokenLedger(), declared_channels=("judge_call",))
        return score, twin, verdicts

    monkeypatch.setattr(rfg.fg, "score_via_live_judge", _stub_live_judge)

    code = await rfg._run([
        "--gold", str(gold_path), "--live", "--api-key", "k", "--model", "gpt-5.5",
        "--manifest", str(fx.MANIFEST_PATH),
    ])
    assert code == 0


# ── m4: the read-only DB posture is proved, not merely asserted ─────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("_bench_db")
async def test_fetch_bar_rows_actually_refuses_a_write(monkeypatch):
    """Done-when proved rather than asserted, and proved *of this function*.

    The probe engine is built from the `connect_args` `_fetch_bar_rows`
    actually passed, captured off `create_async_engine` -- never from a
    copy written here. That binding is the whole point: an earlier draft
    hardcoded the read-only setting in the test, so stripping it from
    `_fetch_bar_rows` left the test green. It proved Postgres honours the
    setting, which nobody doubted, rather than that this function sends it.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from benchlib import bench_db

    captured: dict[str, object] = {}
    real_create = rfg.create_async_engine

    def _capturing(url, **kwargs):
        captured.update(kwargs)
        return real_create(url, **kwargs)

    monkeypatch.setattr(rfg, "create_async_engine", _capturing)
    rows = await rfg._fetch_bar_rows(bench_db.BENCH_DATABASE_URL)
    monkeypatch.undo()
    assert isinstance(rows, dict)

    # Whatever the function sent is what gets probed. Drop the setting from
    # the function and this engine accepts the INSERT, failing the test.
    engine = create_async_engine(
        bench_db.BENCH_DATABASE_URL,
        **{k: v for k, v in captured.items() if k == "connect_args"},
    )
    try:
        async with async_sessionmaker(engine)() as session:
            await session.execute(text("SELECT count(*) FROM config"))
            with pytest.raises(DBAPIError) as caught:
                await session.execute(
                    text("INSERT INTO config (key, value) "
                         "VALUES ('th1_17_ro_probe', '1')")
                )
    finally:
        await engine.dispose()
    assert "read-only" in str(caught.value).lower()


# ── minting, behind an explicit gate flag (2026-09-03) ───────────────────


def test_the_runner_mints_nothing_without_the_gate_flag(tmp_path, monkeypatch):
    """Scoring a gold is not the same act as minting a record. The claim/fact
    runner has always required --gate; this one had no mint path at all, so
    the flag has to arrive with it rather than after it."""
    import benchlib.run_faithfulness_gate as rfg
    assert "--gate" in _flags(rfg)
    assert "--record-dir" in _flags(rfg)


def _flags(mod):
    import argparse, contextlib, io
    parser_flags = []
    real = argparse.ArgumentParser.add_argument

    def spy(self, *a, **k):
        parser_flags.extend([x for x in a if isinstance(x, str)])
        return real(self, *a, **k)

    argparse.ArgumentParser.add_argument = spy
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.suppress(SystemExit):
            mod.main(["--help"])
    finally:
        argparse.ArgumentParser.add_argument = real
    return parser_flags
