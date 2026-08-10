"""Judge-qualification runner (T2.26) — interim by default, ``--gate`` for T2.41.

Measures the ONE app-side ``verification`` judge
(``app/services/verification_judge.py`` — the exact prompt, parser and call
construction every consumer will run) against the claim/fact entailment gold,
and emits a dated report under ``docs/eval/`` plus ledger rows through the
sanctioned recorder. **No database is read or written anywhere in this
runner** — premises come from the gold file, the judge config is built
in-memory, and the bars are the code defaults
(``verification_judge.VERIFICATION_BAR_DEFAULTS``), stamped into the output.

Stage order, and why it is load-bearing:

1. **``--gate`` eligibility refusal first, before any model call.** G-D's
   gate mode refuses a gold that fails doc 17 §11's composition rule
   (< 200 live pairs, zero ``l2-fact`` premises, or unadjudicated pairs), so
   the gate structurally cannot be claimed on an ineligible gold.
2. **The fixture sanity stage** probes ``entailment/sanity_pairs.json``
   (never gold material) and aborts on an invalid-rate >= 10% or a
   single-verdict-class collapse — live plumbing shakeout happens here, and
   the prompt freezes at fixture-pass, BEFORE first gold contact.
3. **The write-ahead intent marker**: once fixtures pass and the gold is
   loaded, an attempt row is appended to the ledger and only then is the
   first gold pair sent — a crash, kill or transport death mid-pass still
   leaves its marker, so ``gold_touching_attempts`` counts the untidy
   failures too. The counter keys on ``gold_sha256`` across ALL judge
   identities, so a prompt-version bump can never reset it.
4. The gold pass, the scorer, the gold backstop (same predicate; a trip
   here permits transport/IO fixes only — a prompt or mapping edit after
   gold contact bumps ``JUDGE_PROMPT_VERSION`` and is disclosed), the twin,
   the report, and the scored ledger row referencing its intent row.

The default (no ``--gate``) run is an **interim** measurement: its report and
ledger row are stamped with the eligibility refusal, and it can never write
the app-side qualification record — only a ``--gate`` run against the
canonical gold can, which is what keeps "qualified" unreachable from this
gold no matter what the numbers say.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import sys
import time
import uuid

import httpx
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
# Standalone execution (`python scripts/benchlib/run_judge_qualification.py`)
# only puts this file's own directory on sys.path -- unlike pytest, which
# inserts SCRIPTS_DIR itself because backend/scripts/ has no __init__.py.
# Both `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import entailment_gold, judge_qualification as jq, ledger, run_smoke  # noqa: E402
from benchlib.twin import (  # noqa: E402
    LatencyRecorder,
    Twin,
    TwinningOrchestrator,
    live_call_count,
    served_by_label,
)

from app.config import LLMPurposeConfig  # noqa: E402
from app.services import verification_judge as vj  # noqa: E402

CACHE_DIR = entailment_gold.ENTAILMENT_DIR / "cache"

# **Per-pair verdicts, in the same contaminated category as the cache above.**
#
# Written because T2.115 could not compute the disclosure its own plan review
# required -- "how many of the retired pairs were misses in the last attempt",
# without which a re-measure's recall moves for census-content reasons and
# nobody can tell that from a judge change. Three routes were closed: the cache
# is keyed on a `base_url`/`params` identity no run records, the report withholds
# the per-pair census by design, and matching cached reasons by token collides
# across pairs.
#
# The tension that made it unanswerable is real: the census is withheld so a
# later *author* cannot aim at it, and that withholding is what makes the
# controller's join impossible. This artifact resolves it by separating the two
# readers rather than by publishing anything -- a controller gets the join, an
# author never sees the file, because it lives beside `cache/` under the same
# gitignore and the same quarantine-before-authoring rule (LABELLING.md's
# allowlist names what an author may read, and this is not on it).
#
# Never commit it, never cite a pair id from it in a report or the ledger.
VERDICTS_DIR = entailment_gold.ENTAILMENT_DIR / "verdicts"
REPORT_DIR = REPO_ROOT / "docs" / "eval"

ATTEMPT_KIND = "judge_qualification_attempt"
SANITY_INVALID_RATE_MAX = 0.10
DECLARED_CHANNELS = ("fixture_call", "judge_call")


DEFAULT_JUDGE = {
    "model": run_smoke.DEEPSEEK_MODEL,
    "base_url": run_smoke.DEEPSEEK_BASE_URL,
    "api_kind": "deepseek",
    "params": {"temperature": 0, "max_tokens": 256, "thinking": {"type": "disabled"}},
}


def judge_purpose_config(
    api_key: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_kind: str | None = None,
    params: dict | None = None,
) -> dict[str, LLMPurposeConfig]:
    """The judge identity for this run.

    Defaults to the identity the ledger fixed for T2.26's interim measurement:
    ``deepseek-v4-flash`` (a ``-pro`` run is not comparable), thinking disabled
    per the DeepSeek quirk, temperature 0 for a deterministic structured
    verdict.

    Overridable because a missed bar has exactly two honest remedies and one of
    them is a different judge model at the **same frozen prompt** (doc 17 §6;
    the other is gold growth). Editing the prompt instead moves ``prompt_sha``,
    hence the identity, and tunes against the set that measured the failure.
    Every override lands in the identity hash, so a swap can never be mistaken
    for a re-run of the same judge -- and ``gold_touching_attempts`` counts the
    contacts either way, which is what makes model-shopping visible rather than
    silent.
    """
    return {"verification": LLMPurposeConfig(
        model=model or DEFAULT_JUDGE["model"],
        base_url=base_url or DEFAULT_JUDGE["base_url"],
        api_key=api_key,
        api_kind=api_kind or DEFAULT_JUDGE["api_kind"],
        params=dict(params if params is not None else DEFAULT_JUDGE["params"]),
    )}


@dataclass
class RunResult:
    score: jq.QualificationScore
    eligibility: jq.Eligibility
    twin: Twin
    meta: dict
    report_text: str
    report_path: Path
    ledger_path: Path


async def _probe_set(judge, recorder, llm, channel, pairs) -> dict:
    verdicts = {}
    for pid, premise, hypothesis in pairs:
        before = live_call_count(llm)
        started = time.perf_counter()
        verdicts[pid] = await judge.qualification_probe(premise, hypothesis)
        recorder.record(
            channel, time.perf_counter() - started,
            served_by_label(before, live_call_count(llm)),
        )
    return verdicts


def _sanity_check(verdicts: dict, stage: str) -> None:
    """The pre-stated plumbing predicate: invalid-rate < 10% and at least
    two distinct valid verdict classes. On the fixture stage a failure is a
    free retry (no gold was touched); on the gold backstop it aborts with
    the intent row already durable, so the contact stays counted."""
    n = len(verdicts)
    invalid = sum(1 for v in verdicts.values() if not v.valid)
    classes = {v.verdict for v in verdicts.values() if v.valid}
    problems = []
    if n and invalid / n >= SANITY_INVALID_RATE_MAX:
        problems.append(f"invalid-verdict rate {invalid}/{n} >= 10%")
    if len(classes) < 2:
        problems.append(f"only {sorted(classes)} verdict class(es) emitted")
    if problems:
        raise RuntimeError(f"{stage} sanity check failed: " + "; ".join(problems))


def _diff_tokens(final: dict, snapshot: dict) -> dict:
    gold = {}
    for purpose, usage in final.items():
        base = snapshot.get(purpose, {})
        gold[purpose] = {
            key: value - base.get(key, 0) for key, value in usage.items()
        }
    return gold


async def run_qualification(
    *,
    deepseek_api_key: str | None = None,
    gold_path: str | Path = entailment_gold.GOLD_PATH,
    sanity_path: str | Path = jq.SANITY_PAIRS_PATH,
    cache_dir: str | Path = CACHE_DIR,
    report_dir: str | Path = REPORT_DIR,
    ledger_path: str | Path = ledger.DEFAULT_PATH,
    record_path: str | Path | None = None,
    gate: bool = False,
    judge_model: str | None = None,
    judge_base_url: str | None = None,
    judge_api_kind: str | None = None,
    judge_params: dict | None = None,
    fixtures_only: bool = False,
    orchestrator_cls=TwinningOrchestrator,
    now: datetime | None = None,
) -> RunResult | None:
    api_key = deepseek_api_key or run_smoke.require_deepseek_api_key()
    gold_path = Path(gold_path)
    ledger_path = Path(ledger_path)

    if gate:
        eligibility = jq.gate_eligibility(entailment_gold.load_entailment_gold(gold_path))
        if not eligibility.eligible:
            raise RuntimeError(
                "--gate refused before any model call — the gold fails doc 17 "
                "§11's composition rule (G-D opens only through T2.41 after "
                "T2.54):\n  " + "\n  ".join(eligibility.reasons)
            )

    config = judge_purpose_config(
        api_key, model=judge_model, base_url=judge_base_url,
        api_kind=judge_api_kind, params=judge_params,
    )
    llm = orchestrator_cls(config, cache_dir=str(cache_dir))
    judge = vj.VerificationJudge(llm)
    recorder = LatencyRecorder()

    sanity_pairs = json.loads(Path(sanity_path).read_text(encoding="utf-8"))["pairs"]
    print(f"[1/4] fixture sanity stage: {len(sanity_pairs)} pairs (no gold contact)...")
    fixture_verdicts = await _probe_set(
        judge, recorder, llm, "fixture_call",
        [(p["id"], p["premise"], p["hypothesis"]) for p in sanity_pairs],
    )
    _sanity_check(fixture_verdicts, "fixture stage")
    if fixtures_only:
        print("fixture stage PASSED — prompt and parser are now frozen; the "
              "gold was never opened (--fixtures-only). Nothing written.")
        return None

    gold_doc = entailment_gold.load_entailment_gold(gold_path)
    live_pairs = [p for p in gold_doc["pairs"] if not p.get("retired")]
    eligibility = jq.gate_eligibility(gold_doc)
    gold_sha256 = hashlib.sha256(gold_path.read_bytes()).hexdigest()

    identity = vj.judge_identity(config["verification"])
    identity_hash = vj.judge_identity_hash(identity)
    fixture_tokens = copy.deepcopy(llm.tokens.as_dict())

    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    intent_row_id = str(uuid.uuid4())
    # The write-ahead intent marker: on disk BEFORE the first gold pair is
    # sent, so a crash mid-pass still counts as a gold contact.
    ledger.record({
        "kind": ATTEMPT_KIND,
        "intent_row_id": intent_row_id,
        "identity_hash": identity_hash,
        # The whole identity, not only its hash: a missed run mints no
        # qualification record, so without this the ledger cannot say what was
        # actually run (see the report's "judge invocation" line).
        "judge_identity": {**identity, "identity_hash": identity_hash},
        "prompt_sha": identity["prompt_sha"],
        "gold_sha256": gold_sha256,
        "timestamp": timestamp,
    }, path=ledger_path)

    print(f"[2/4] gold pass: {len(live_pairs)} live pairs (intent row {intent_row_id})...")
    verdicts = await _probe_set(
        judge, recorder, llm, "judge_call",
        [(p["id"], p["premise"], p["hypothesis"]) for p in live_pairs],
    )
    pair_by_id = {p["id"]: p for p in live_pairs}
    score = jq.score_judgments(live_pairs, verdicts)

    # Rule B's second population, from the verdicts already in hand: no extra
    # model call and no extra gold contact. Scoring only the pool would blend
    # pairs this judge's model has already been measured on with the pairs the
    # growth round added precisely because it had.
    nc_pairs = jq.rule_b_population(live_pairs)
    nc_score = jq.score_judgments(nc_pairs, verdicts) if nc_pairs else None
    _sanity_check(verdicts, "gold backstop")

    gold_touching_attempts = sum(
        1 for row in ledger.read_runs(ledger_path)
        if row.get("kind") == ATTEMPT_KIND and row.get("gold_sha256") == gold_sha256
    )

    gold_tokens = _diff_tokens(llm.tokens.as_dict(), fixture_tokens)
    twin = Twin.capture(recorder, llm.tokens, declared_channels=DECLARED_CHANNELS)

    run_date = (now or datetime.now()).date()
    meta = {
        "gate_run": gate,
        "date": run_date.isoformat(),
        "run_id": run_id,
        "timestamp": timestamp,
        "git_sha": run_smoke.git_sha(),
        "judge_identity": {**identity, "identity_hash": identity_hash},
        "bars": dict(vj.VERIFICATION_BAR_DEFAULTS),
        "gold_version": gold_doc.get("version", "unknown"),
        "gold_sha256": gold_sha256,
        "gold_touching_attempts": gold_touching_attempts,
        "n_fixtures": len(sanity_pairs),
        "fixture_tokens": fixture_tokens,
        "gold_tokens": gold_tokens,
        "rule_b_score": nc_score,
    }

    print("[3/4] rendering report + recording ledger row...")
    report_text = jq.render_report(score, eligibility, twin, meta)
    # Keyed on the judge identity, not the date alone. Two attempts on one day
    # is the normal shape of a missed bar -- doc 17 §6's remedy is a different
    # judge model at the frozen prompt -- and a date-only name means the second
    # run silently overwrites the first's evidence. That happened on 2026-08-08:
    # the gpt-5.5 attempt clobbered the deepseek-v4-flash report, which survived
    # only because it had already been committed. A gate ledger cites these.
    report_path = (
        Path(report_dir)
        / f"{run_date.isoformat()}-judge-qualification-{identity_hash[:8]}.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")

    # The join a later round needs, keyed by pair id and by this run's identity
    # so two attempts never overwrite each other's evidence.
    verdicts_path = Path(VERDICTS_DIR) / (
        f"{run_date.isoformat()}-{identity_hash[:8]}-{gold_sha256[:8]}.json"
    )
    verdicts_path.parent.mkdir(parents=True, exist_ok=True)
    verdicts_path.write_text(json.dumps({
        "_notes": (
            "Per-pair judge verdicts. CONTAMINATED ARTIFACT: quarantine this "
            "directory before any authoring or adjudication dispatch, exactly "
            "as entailment/cache/ is quarantined, and never publish a pair id "
            "from it. It exists so a controller can attribute a re-measure's "
            "delta to census content versus judge behaviour."
        ),
        "gold_sha256": gold_sha256,
        "judge_identity": identity_hash,
        "date": run_date.isoformat(),
        "verdicts": {
            pid: {"gold": pair_by_id[pid]["verdict"], "judged": v.verdict}
            for pid, v in verdicts.items()
        },
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[3/4] per-pair verdicts: {verdicts_path}")

    jq.record_qualification(score, twin, metadata={
        "run_id": run_id,
        "timestamp": timestamp,
        "git_sha": meta["git_sha"],
        "gold_sha256": gold_sha256,
        "identity_hash": identity_hash,
        "gold_touching_attempts": gold_touching_attempts,
        "intent_row_id": intent_row_id,
        "gate_eligible": eligibility.eligible,
    }, path=ledger_path)

    if gate:
        results = jq.bar_results(score, meta["bars"])
        for bar_key, result in results.items():
            print(f"  {bar_key}: measured={result['measured']} bar={result['bar']} "
                  f"-> {'PASS' if result['passed'] else 'FAIL'}")
        missed = [k for k, r in results.items() if not r["passed"]]
        # Rule B: "the gate verdict required to hold on both". A bar cleared on
        # the pool and missed on Rule B's second population is a bar cleared on
        # pairs the judge had already been measured against, which is the one
        # reading the rule exists to forbid.
        if nc_score is not None:
            nc_results = jq.bar_results(nc_score, meta["bars"])
            for bar_key, result in nc_results.items():
                print(f"  [Rule B, n={nc_score.n_pairs}] {bar_key}: "
                      f"measured={result['measured']} bar={result['bar']} "
                      f"-> {'PASS' if result['passed'] else 'FAIL'}")
            missed += [f"{k} (Rule B population)"
                       for k, r in nc_results.items() if not r["passed"]]
        if missed:
            # A failed gate leaves its report and its ledger rows, and nothing
            # else. Until 2026-08-08 it also wrote the qualification record --
            # the very artifact that opens G-D -- carrying its own failing
            # numbers. `qualification_state` re-checks every metric at read
            # time, so nothing was qualified by it; but it left a key in the
            # door that turns the moment a bar is loosened, and a bar is a
            # config row. The G-C driver states the opposite rule for its own
            # record ("written only by a run whose verdict cleared, and only by
            # the gate owner deliberately, never as a side effect of
            # measuring"); the two gates now agree.
            print(f"[4/4] gate run MISSED {len(missed)} bar(s): "
                  f"{', '.join(missed)} — no qualification record written. "
                  f"G-D stays closed.")
        else:
            target = Path(record_path) if record_path is not None else vj.QUALIFICATION_RECORD_PATH
            jq.write_qualification_record(
                target, gold_path=gold_path, identity=identity, score=score,
                gold_doc=gold_doc, ledger_run_id=run_id, bars=meta["bars"],
                git_sha=meta["git_sha"], timestamp=timestamp,
            )
            print(f"[4/4] gate run CLEARED every bar: record written to {target}")
    else:
        print("[4/4] interim run complete — not a qualification verdict; "
              "no app-side record written.")

    return RunResult(
        score=score, eligibility=eligibility, twin=twin, meta=meta,
        report_text=report_text, report_path=report_path, ledger_path=ledger_path,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the verification judge on the claim/fact entailment gold "
            "(interim by default; --gate is T2.41's G-D evidence mode)."
        ),
    )
    parser.add_argument("--gate", action="store_true", help=(
        "G-D evidence mode: refuse an ineligible gold before any model call, "
        "and on success write the app-side qualification record (canonical "
        "gold only)."
    ))
    parser.add_argument("--fixtures-only", action="store_true", help=(
        "Run only the fixture sanity stage and stop — the live shakeout "
        "door; the gold file is never opened and nothing is written."
    ))
    parser.add_argument("--gold", default=None, metavar="PATH",
                        help="Gold file (default: the canonical claim/fact gold).")
    parser.add_argument("--cache-dir", default=None, metavar="PATH",
                        help="LLM disk cache directory (default: entailment/cache).")
    parser.add_argument("--judge-model", default=None, metavar="NAME", help=(
        "swap the judge model at the frozen prompt (doc 17 §6's sanctioned "
        "remedy for a missed bar). Lands in the identity hash."
    ))
    parser.add_argument("--judge-base-url", default=None, metavar="URL")
    parser.add_argument("--judge-api-kind", default=None, metavar="KIND")
    parser.add_argument("--judge-params", default=None, metavar="JSON", help=(
        "JSON object of per-call params for the judge purpose. Stated by the "
        "caller rather than derived here: vendors differ on what they accept "
        "(the GPT-5 line refuses temperature=0), and a runner that guessed "
        "would be comparing api_kind to a vendor name, which this codebase "
        "forbids at call sites."
    ))
    parser.add_argument("--record-path", default=None, metavar="PATH", help=(
        "Where --gate writes the qualification record (default: the "
        "canonical app-side path; rehearsals must point elsewhere)."
    ))
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    result = await run_qualification(
        gold_path=args.gold or entailment_gold.GOLD_PATH,
        cache_dir=args.cache_dir or CACHE_DIR,
        record_path=args.record_path,
        gate=args.gate,
        judge_model=args.judge_model,
        judge_base_url=args.judge_base_url,
        judge_api_kind=args.judge_api_kind,
        judge_params=json.loads(args.judge_params) if args.judge_params else None,
        fixtures_only=args.fixtures_only,
    )
    if result is not None:
        print(result.report_text)
        print(f"report written to {result.report_path}")
        print(f"ledger appended: {result.ledger_path}")
    return 0


def _run() -> int:
    try:
        return asyncio.run(main())
    except (RuntimeError, ValueError, OSError, httpx.HTTPError) as exc:
        print(f"run_judge_qualification.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_run())
