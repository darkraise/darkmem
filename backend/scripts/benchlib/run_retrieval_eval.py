"""Retrieval eval runner + dated report (T0.10).

The one command Lane B has been built toward: reset the bench DB, seed the
LLM purpose configs, ingest the fixed-id retrieval corpus, drive both arms
(the shipping retriever and the T0.09 full-context baseline) over the live
gold pairs, score them under the same protocol, and emit two artifacts from
a single composed run -- a dated human-readable report under ``docs/eval/``
and one ledger row -- never a hand-rolled dict fed straight to
``ledger.record`` (brief ruling 1: that call boundary is the only place the
no-twin-no-accuracy guard actually bites). The default (no ``--arm``) path
below reaches the ledger through exactly one sanctioned recorder,
``full_context.record_comparison``; T2.44's ``--arm`` path is a second,
independent command reaching the ledger through its own sanctioned
recorder, ``arm_ablation.record_arm_comparison`` (see that module's
docstring for why it is a parallel recorder rather than a caller of this
one) -- benchlib also had a third, ``twin.record_eval_run``, before either
of these two existed. "One boundary" was never a benchlib-wide rule; it is
a per-path guarantee each sanctioned recorder holds on its own.

Corpus size, gold version, live-pair count and the full-corpus fetch depth
are all read from the gold files at run time, never hardcoded: this corpus
has already grown twice under this epic (T0.06a, twice), and a runner that
bakes in "94 memories" would silently misreport the next growth instead of
failing loudly.

Reproducibility (ruling 3) is the checkbox with teeth. Two consecutive runs
on an unchanged tree -- and an unchanged warm LLM cache -- must reproduce
every accuracy figure, every token-cost figure, the full-context id audit,
the context description and the caveat kinds byte-for-byte;
``reproducible_metrics()`` is the exact, deliberately narrow subset that
promise covers. Latency is excluded on purpose: a p50/p95 is a wall-clock
measurement of a disk read or a live model round trip and is expected to
differ run to run even when nothing else does. The report renders both --
the full human-readable comparison (which includes latency) and a separate
canonical JSON block (which does not) -- so a reader can diff the second
without the first's expected jitter drowning out a real regression.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
# Standalone execution (`python scripts/benchlib/run_retrieval_eval.py`) only
# puts this file's own directory on sys.path -- unlike pytest, which inserts
# SCRIPTS_DIR itself because backend/scripts/ has no __init__.py. Both
# `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib import bench_db, full_context, ledger, retrieval_gold, run_smoke  # noqa: E402
from benchlib.ingest import GateConfig, run_ingest  # noqa: E402
from benchlib.retrieval_runner import run_retrieval  # noqa: E402
from benchlib.retrieval_scorer import ScoreReport, score_retrieval  # noqa: E402
from benchlib.twin import EvalRun, Twin, TwinningOrchestrator, instrument_retrieval  # noqa: E402

from app.services.config import get_llm_config  # noqa: E402

# Pinned protocol constants (brief §5, verbatim): changing k/min_pairs never
# invalidates the LLM disk cache (they only affect scoring, a pure function
# over already-produced rankings), but they DO change the reported numbers,
# so they are fixed here rather than left as ambient caller choices.
K = 10
MIN_PAIRS = 10
# The full-context arm's fetch depth. UNLIKE k/min_pairs, this DOES sit
# inside the arm's chat cache key (build_user_prompt embeds it in the
# message text -- full_context.build_user_prompt), so changing it would
# invalidate all 102 warm full-context cache entries and force 102 live
# DeepSeek calls for a number that changes nothing about what's measured
# (k=10 only ever reads the top-10 prefix regardless of fetch depth; see
# task-T0.09-report.md §3.3). Pinned to match the existing warm cache.
FULL_CONTEXT_LIMIT = 10

CACHE_DIR = retrieval_gold.RETRIEVAL_DIR / "cache"
REPORT_DIR = REPO_ROOT / "docs" / "eval"
GATE_LEDGER_PATH = REPO_ROOT / "docs" / "planning" / "gate-ledger.md"


def report_path(run_date, report_dir: Path = REPORT_DIR) -> Path:
    """``docs/eval/<date>-retrieval-eval.md`` for the given date.

    Overwriting an existing same-date report (rather than minting a variant)
    is the caller's job -- ``Path.write_text`` already does that, and ruling
    4 says a same-day re-run is a correction, not a second artifact. That
    ruling is about UNCITED reports, i.e. still-working files. Once
    ``gate-ledger.md`` cites a report as a cleared gate's evidence it is no
    longer scratch output, and ``run_eval`` (below) refuses to overwrite it
    via ``_refuse_if_cited`` -- a check this function deliberately does not
    make itself, since it has no caller/ledger context, only a date.
    """
    return Path(report_dir) / f"{run_date.isoformat()}-retrieval-eval.md"


def find_ledger_citations(rel_path: str, ledger_path: Path = GATE_LEDGER_PATH) -> list[str]:
    """Lines in ``gate-ledger.md`` that mention ``rel_path`` verbatim.

    A literal-substring search over the raw text, not a markdown parser: it
    matches the path however the ledger happens to write it -- backticked,
    bare, mid-sentence, inside a table cell -- at the cost of being blind to
    any citation form that does not contain this exact string (a glob, a
    renamed variable, a path written relative to a different root). A
    citation that dodges this search reads as UNCITED, which is the unsafe
    direction for a refusal check: prefer keeping the ledger's citation
    style literal (as it is today, exclusively ``docs/eval/...`` paths) over
    trusting this function's silence as proof nothing points at a file.
    """
    if not Path(ledger_path).exists():
        return []
    hits = []
    text = Path(ledger_path).read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if rel_path in line:
            hits.append(f"{Path(ledger_path).name}:{lineno}: {line.strip()}")
    return hits


def _refuse_if_cited(out_path: Path, ledger_path: Path = GATE_LEDGER_PATH) -> None:
    """Refuse to overwrite ``out_path`` if ``gate-ledger.md`` cites it.

    Only fires when ``out_path`` already exists (nothing to protect on a
    file's first write) and sits inside the repo (a scratch ``report_dir``
    outside ``REPO_ROOT`` -- e.g. a test's ``tmp_path`` -- cannot be named
    by a ledger that cites repo-relative paths, so it is out of scope for
    this check by construction, not by accident). This is what keeps ruling
    4 intact: a same-day re-run of an UNCITED report still overwrites freely,
    since it never matches any line here.
    """
    if not out_path.exists():
        return
    try:
        rel_path = out_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return
    hits = find_ledger_citations(rel_path, ledger_path)
    if hits:
        raise RuntimeError(
            f"refusing to overwrite {out_path} -- gate-ledger.md cites it as "
            "gate evidence:\n" + "\n".join(hits) + "\n"
            "This file is no longer scratch output; a same-day re-run "
            "correcting an UNCITED report is still fine (ruling 4), but this "
            "one backs a ratified gate verdict and overwriting it would "
            "silently detach that verdict from the artifact it names. If "
            "the eval genuinely needs re-running, mint a differently-named "
            "report by hand (pass a distinct report_dir or rename after "
            "writing) and update the ledger's citation to it in the same "
            "commit -- never overwrite the cited file."
        )


def _score_summary(score: ScoreReport) -> dict:
    """Per-slice + aggregate accuracy, deliberately WITHOUT ``pair_scores``.

    Pair-level detail is the ledger's job (``to_ledger_payload`` still
    carries it in full, unmodified) -- the report's reproducibility
    contract is the slice table doc 17 §4 asks for, "never collapsed into
    an aggregate", not a 100+-row per-pair dump.
    """
    return {
        "k": score.k,
        "retrieval_limit": score.retrieval_limit,
        "min_pairs": score.min_pairs,
        "n_pairs": score.n_pairs,
        "slices": {
            tag: {
                "n_pairs": s.n_pairs, "powered": s.powered,
                "mrr": s.mrr, "hit_at_k": s.hit_at_k,
            }
            for tag, s in sorted(score.slices.items())
        },
        "aggregate_powered": score.aggregate_powered,
        "aggregate_mrr": score.aggregate_mrr,
        "aggregate_hit_at_k": score.aggregate_hit_at_k,
    }


def reproducible_metrics(comparison: full_context.Comparison) -> dict:
    """The subset of a ``Comparison`` that MUST be byte-identical across two
    runs on an unchanged tree with a warm LLM cache (ruling 3): per-slice and
    aggregate accuracy for both arms, token cost by purpose for both arms,
    the full-context id audit, the context description, and the caveat
    KINDS (sorted, so an unrelated derivation-order change can never move
    this). Latency lives only in ``full_context.render_comparison``'s text
    and is deliberately absent here -- see ``render_report``'s
    "Reproducibility" section for why.
    """
    payload = comparison.to_ledger_payload()["comparison"]
    return {
        "k": payload["k"], "min_pairs": payload["min_pairs"], "n_pairs": payload["n_pairs"],
        "retrieval_score": _score_summary(comparison.retrieval.score),
        "full_context_score": _score_summary(comparison.full_context.score),
        "retrieval_tokens_by_purpose": payload["arms"]["retrieval"]["twin"]["tokens_by_purpose"],
        "full_context_tokens_by_purpose": payload["arms"]["full_context"]["twin"]["tokens_by_purpose"],
        "deltas": payload["deltas"],
        "full_context_id_audit": payload["full_context_id_audit"],
        "full_context_context": payload["full_context_context"],
        "caveat_kinds": sorted(c["kind"] for c in payload["caveats"]),
    }


def _total_chat_calls(tokens_by_purpose: dict) -> int:
    """Every chat call an arm billed, live or replayed, across every
    purpose -- the same sum ``full_context._chat_calls_by_purpose`` computes
    per purpose, collapsed to one arm-level total."""
    return sum(
        usage.get("live_calls", 0) + usage.get("cache_known_calls", 0)
        + usage.get("cache_unknown_calls", 0)
        for usage in tokens_by_purpose.values()
    )


def _any_cache_unknown(tokens_by_purpose: dict) -> bool:
    return any(usage.get("cache_unknown_calls", 0) for usage in tokens_by_purpose.values())


def _expected_caveat_kinds(
    *,
    retrieval_end_to_end_live: bool,
    full_context_end_to_end_live: bool,
    retrieval_cache_unknown: bool,
    full_context_cache_unknown: bool,
    retrieval_chat_calls: int,
    full_context_chat_calls: int,
) -> set[str]:
    """The caveat kinds THIS run structurally guarantees (fix round 1, F1).

    Deliberately NOT a re-run of ``Comparison``'s own per-purpose
    ``sum(...) == n_pairs`` heuristic (``full_context.py``, out of bounds
    per ruling 8) -- re-deriving the same computation would always agree
    with itself and could never catch that heuristic's own blind spot. The
    named trap is exactly that blind spot: the heuristic reads "did this
    arm bill exactly n_pairs calls", which goes silently false the moment
    the retrieval arm's ingest call count coincidentally equals the live
    pair count (today 94 vs 102; eight gold retirements away). This
    function instead asserts a fact this runner knows about its OWN
    composition, independent of that coincidence: ``run_ingest`` bills
    ONE-TIME indexing work and ``run_full_context`` bills exactly one call
    per scored pair, so the two are ALWAYS a kind-mismatched pair whenever
    both billed anything at all -- regardless of what the raw counts
    happen to equal. See ``run_eval``'s caveat-kind guard for how a
    mismatch between this and the real ``comparison.caveats`` is handled:
    raised before the report or ledger is written, never rendered as
    "nothing to qualify".

    The latency portion IS an exact reproduction of
    ``Comparison._latency_caveats``'s three-way branch, not a heuristic --
    "did this arm's end_to_end channel see a live sample" is a fact this
    runner already knows precisely (a live call within a query's window is
    exactly what labels that query's sample "live"), so there is no
    coincidence for it to be blind to.
    """
    expected: set[str] = set()

    if retrieval_end_to_end_live and full_context_end_to_end_live:
        pass
    elif retrieval_end_to_end_live != full_context_end_to_end_live:
        expected.add(full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE)
    else:
        expected.add(full_context.CAVEAT_LATENCY_NO_LIVE_SAMPLES)

    if retrieval_cache_unknown or full_context_cache_unknown:
        expected.add(full_context.CAVEAT_COST_UNMEASURED)

    if retrieval_chat_calls > 0 and full_context_chat_calls > 0:
        expected.add(full_context.CAVEAT_COST_KIND_ASYMMETRY)

    return expected


def _assert_expected_caveats(comparison: full_context.Comparison, expected: set[str]) -> None:
    actual = {c.kind for c in comparison.caveats}
    missing = expected - actual
    if missing:
        raise RuntimeError(
            f"expected caveat kind(s) {sorted(missing)} to fire on this run but "
            f"Comparison.caveats produced only {sorted(actual)}. Ruling 2: a "
            "caveat this run structurally warrants must never silently vanish "
            "from the report -- refusing rather than writing a report or "
            "ledger row that would read as \"nothing to qualify\". Investigate "
            "before re-running: either the two arms' call counts have moved "
            "into a state the caveat-derivation heuristic in full_context.py "
            "is blind to (e.g. ingest calls now equal the live pair count), or "
            "the derivation itself changed."
        )


def _designed_state_note(comparison: full_context.Comparison) -> str:
    """Two results that look like problems and are not (brief §3), stated
    from the numbers THIS run actually measured -- never a hardcoded figure,
    since both are read off ``comparison`` at render time.

    The multi-hop line is NOT an unconditional claim (fix round 1, F2): the
    "designed state" is specifically hit@k == 0.000 (T0.06a's desaturation
    guarantees every live pair's consequence memory ranks worse than k).
    Any OTHER value falsifies that guarantee and must read as drift a
    reader is told to investigate, never as "by design" -- a note that
    stamped every possible value as designed would launder a future
    regression into the one artifact chartered to catch it.
    """
    rs = comparison.retrieval.score
    deltas = comparison.deltas()["aggregate"]
    lines: list[str] = []

    mh = rs.slices.get("multi-hop")
    if mh is not None and mh.hit_at_k is not None:
        if mh.hit_at_k == 0.0:
            lines.append(
                f"- **multi-hop hit@{rs.k} = {mh.hit_at_k:.4f} on the retrieval "
                "arm is the DESIGNED state (T0.06a), not a defect.** Every live "
                "multi-hop pair is built so its consequence memory ranks worse "
                "than k in the hybrid-only baseline -- this is the headroom a "
                "future graph-aware arm exists to close, not a bug for this "
                "runner to flag."
            )
        else:
            lines.append(
                f"- **multi-hop hit@{rs.k} = {mh.hit_at_k:.4f} on the retrieval "
                "arm is NOT the designed 0.0000 baseline -- this is DRIFT to "
                "investigate, not a result to file as \"by design\".** T0.06a's "
                "desaturation built every live multi-hop pair so its "
                "consequence memory ranks worse than k in the hybrid-only "
                "baseline; a nonzero hit@k here means either a pair "
                "re-saturated (a corpus/gold change) or the retriever itself "
                "changed, and either should be adjudicated before this run's "
                "numbers are trusted."
            )

    if deltas["mrr"] is not None and deltas["hit_at_k"] is not None and deltas["mrr"] > 0:
        lines.append(
            f"- **full context beats retrieval on pooled accuracy this run** "
            f"(ΔMRR={deltas['mrr']:+.4f}, Δhit@{rs.k}={deltas['hit_at_k']:+.4f}, "
            "full-context minus retrieval) -- the honest measured result of "
            "the T0.09 comparator, stated plainly rather than buried or "
            "reframed as a cost-only win. See the cost caveats below for why "
            "the two arms' token costs are not directly subtractable."
        )

    return "\n".join(lines)


def _fmt_gate_config(gate_config: dict) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in sorted(gate_config.items()))


def render_report(comparison: full_context.Comparison, meta: dict) -> str:
    """The dated report: header metadata, the full human-readable
    comparison (per-slice accuracy, both twins, the baseline comparison --
    doc 17 §4/§9, brief ruling 5), then the reproducibility contract as its
    own diffable JSON block (ruling 3).
    """
    lines: list[str] = []
    lines.append(f"# Retrieval eval — {meta['date']}")
    lines.append("")
    lines.append(f"- run id: `{meta['run_id']}` (recorded {meta['timestamp']})")
    lines.append(f"- git sha: `{meta['git_sha']}`")
    lines.append(f"- embedder fingerprint: `{meta['fingerprint']}`")
    lines.append(f"- gate configuration: `{_fmt_gate_config(meta['gate_config'])}`")
    lines.append(
        f"- corpus: {meta['corpus_entries']} memories, gold v{meta['gold_version']}, "
        f"{meta['n_pairs_authored']} pairs authored ({meta['n_pairs_live']} live)"
    )
    lines.append(
        f"- protocol: k={meta['k']}, min_pairs={meta['min_pairs']}, retrieval "
        f"retrieval_limit={meta['retrieval_limit']}, full_context "
        f"retrieval_limit={meta['full_context_limit']}"
    )
    lines.append(
        f"- live LLM calls this run: ingest={meta['ingest_live_calls']}, "
        f"retrieval={meta['retrieval_live_calls']}, "
        f"full_context={meta['full_context_live_calls']} "
        f"(total={meta['total_live_calls']})"
    )
    lines.append("")

    note = _designed_state_note(comparison)
    if note:
        lines.append(note)
        lines.append("")

    lines.append("## Comparison (human-readable)")
    lines.append("")
    lines.append(
        "Includes latency by channel for both arms -- see Reproducibility "
        "below for which parts of this section are expected to vary run to "
        "run and which are not."
    )
    lines.append("")
    lines.append("```")
    lines.append(full_context.render_comparison(comparison))
    lines.append("```")
    lines.append("")

    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        "Two consecutive runs on an unchanged tree, against an unchanged warm "
        "LLM cache, must reproduce the JSON block below byte-for-byte: every "
        "accuracy figure (per slice and aggregate, both arms), every "
        "token-cost figure, the full-context id audit, the context "
        "description, and the set of caveat kinds. **Latency is excluded on "
        "purpose** (p50/p95 by channel, in the comparison above): it is a "
        "wall-clock measurement of a cache read or a live model round trip, "
        "and is expected to differ run to run even when nothing else does -- "
        "only its live-vs-cache population membership is a claim this "
        "report makes, never the exact figure."
    )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(reproducible_metrics(comparison), indent=2, sort_keys=True))
    lines.append("```")
    return "\n".join(lines) + "\n"


@dataclass
class EvalRunResult:
    comparison: full_context.Comparison
    meta: dict
    report_text: str
    report_path: Path
    ledger_path: Path


async def run_eval(
    *,
    deepseek_api_key: str | None = None,
    session_factory=bench_db.session_factory,
    cache_dir: str | Path = CACHE_DIR,
    corpus_path: str | Path = retrieval_gold.CORPUS_PATH,
    gold_path: str | Path = retrieval_gold.GOLD_PATH,
    k: int = K,
    min_pairs: int = MIN_PAIRS,
    full_context_limit: int = FULL_CONTEXT_LIMIT,
    report_dir: str | Path = REPORT_DIR,
    ledger_path: str | Path = ledger.DEFAULT_PATH,
    gate_ledger_path: str | Path = GATE_LEDGER_PATH,
    now: datetime | None = None,
) -> EvalRunResult:
    """Run the full eval end to end and emit the report + one ledger row.

    Established protocol (brief §5): reset_bench_db() against darkmem_bench
    -> seed_llm_purpose_configs -> seed_memory_rows + run_ingest(GateConfig())
    -> instrumented run_retrieval at the full-corpus fetch depth ->
    score_retrieval(k, min_pairs) -> the T0.09 comparator -> the report ->
    the ledger. Every accuracy-bearing ledger write goes through
    full_context.record_comparison (ruling 1) -- there is no ledger.record
    call anywhere in this module with a metric in hand.
    """
    api_key = deepseek_api_key or run_smoke.require_deepseek_api_key()
    # The LOCAL system date, not UTC: ruling 4 wants "the run's real date" as
    # a human filing it would read it (this machine runs UTC+7, where a late
    # evening UTC run already reads as tomorrow), never the clock skew of an
    # arbitrarily-chosen timezone. Every other timestamp in this module
    # stays UTC (git sha, ledger rows) -- only the report FILENAME's date
    # uses local time.
    run_date = (now or datetime.now()).date()

    print("[1/6] resetting darkmem_bench and seeding LLM purpose configs...")
    await bench_db.reset_bench_db()
    await run_smoke.seed_llm_purpose_configs(session_factory, api_key)

    entries = retrieval_gold.load_retrieval_corpus(corpus_path)
    gold = retrieval_gold.load_retrieval_gold(gold_path)
    retrieval_gold.validate_gold_against_corpus(gold, entries)
    pairs = gold["pairs"]
    retrieval_limit = len(entries)
    print(
        f"[2/6] {len(entries)} corpus entries, {len(pairs)} gold pairs, "
        f"gold version {gold.get('version', 'unknown')}."
    )

    async with session_factory() as session:
        llm_config = await get_llm_config(session)

    prepared = await retrieval_gold.seed_memory_rows(session_factory, entries)

    retrieval_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    ingest_result = await run_ingest(retrieval_llm, prepared, GateConfig(), session_factory)
    print(
        f"[3/6] ingested {len(entries)} entries -- live LLM calls: "
        f"{ingest_result.live_calls}, fingerprint: {ingest_result.fingerprint}"
    )

    live_before_retrieval = retrieval_llm.live_calls
    with instrument_retrieval(retrieval_llm) as recorder:
        ranked = await run_retrieval(retrieval_llm, session_factory, pairs, limit=retrieval_limit)
    retrieval_only_live = retrieval_llm.live_calls - live_before_retrieval
    retrieval_score = score_retrieval(
        ranked, pairs, retrieval_limit=retrieval_limit, k=k, min_pairs=min_pairs,
    )
    retrieval_run = EvalRun(score=retrieval_score, twin=Twin.capture(recorder, retrieval_llm.tokens))
    print(
        f"[4/6] retrieval over {retrieval_score.n_pairs} live pairs "
        f"(limit={retrieval_limit}) -- live LLM calls this stage: {retrieval_only_live}"
    )

    fc_llm = TwinningOrchestrator(llm_config, cache_dir=str(cache_dir))
    fc = await full_context.run_full_context(fc_llm, entries, pairs, limit=full_context_limit)
    fc_score = score_retrieval(
        fc.ranked_ids_by_pair, pairs, retrieval_limit=full_context_limit, k=k, min_pairs=min_pairs,
    )
    fc_run = EvalRun(
        score=fc_score,
        twin=Twin.capture(fc.recorder, fc_llm.tokens, declared_channels=full_context.CHANNELS),
    )
    print(
        f"[5/6] full-context arm over {fc_score.n_pairs} live pairs "
        f"(limit={full_context_limit}) -- live LLM calls this stage: {fc_llm.live_calls}"
    )

    comparison = full_context.Comparison(
        retrieval=retrieval_run, full_context=fc_run, id_audit=fc.audit, context=fc.context,
    )

    # Ruling 2's guard (fix round 1, F1): assert the caveat kinds THIS run
    # structurally warrants before either artifact is written, rather than
    # rendering whatever Comparison.caveats happens to produce. Runs before
    # any print, report write or ledger append -- a mismatch leaves no
    # partial report and no ledger row.
    expected_caveats = _expected_caveat_kinds(
        retrieval_end_to_end_live=retrieval_only_live > 0,
        full_context_end_to_end_live=fc_llm.live_calls > 0,
        retrieval_cache_unknown=_any_cache_unknown(retrieval_llm.tokens.as_dict()),
        full_context_cache_unknown=_any_cache_unknown(fc_llm.tokens.as_dict()),
        retrieval_chat_calls=_total_chat_calls(retrieval_llm.tokens.as_dict()),
        full_context_chat_calls=_total_chat_calls(fc_llm.tokens.as_dict()),
    )
    _assert_expected_caveats(comparison, expected_caveats)

    total_live_calls = ingest_result.live_calls + retrieval_only_live + fc_llm.live_calls
    meta = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": run_date.isoformat(),
        "git_sha": run_smoke.git_sha(),
        "fingerprint": ingest_result.fingerprint,
        "gate_config": ingest_result.gate_config,
        "corpus_entries": len(entries),
        "gold_version": gold.get("version", "unknown"),
        "n_pairs_authored": len(pairs),
        "n_pairs_live": retrieval_score.n_pairs,
        "retrieval_limit": retrieval_limit,
        "full_context_limit": full_context_limit,
        "k": k,
        "min_pairs": min_pairs,
        "ingest_live_calls": ingest_result.live_calls,
        "retrieval_live_calls": retrieval_only_live,
        "full_context_live_calls": fc_llm.live_calls,
        "total_live_calls": total_live_calls,
    }

    print(f"[6/6] comparing, writing report, recording ledger... (total live calls: {total_live_calls})")
    report_text = render_report(comparison, meta)
    out_path = report_path(run_date, report_dir)
    # T0.18: refuse before writing or appending to the JSONL ledger below, so
    # a refusal leaves no partial artifact either -- same discipline as the
    # F1 caveat-kind guard above.
    _refuse_if_cited(out_path, gate_ledger_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")

    full_context.record_comparison(
        comparison, path=ledger_path,
        metadata={
            "run_id": meta["run_id"], "timestamp": meta["timestamp"],
            "git_sha": meta["git_sha"], "fingerprint": meta["fingerprint"],
        },
    )

    return EvalRunResult(
        comparison=comparison, meta=meta, report_text=report_text,
        report_path=out_path, ledger_path=Path(ledger_path),
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    """No flags at all until T2.44: this file's whole entry chain used to be
    ``_run() -> main() -> run_eval(...)`` with nothing to parse. ``--arm``
    is genuinely new plumbing, not a flag added to an existing parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Drive the retrieval eval: the T0.09 full-context comparison by "
            "default, or (with --arm) the T2.44 on/off ablation of one "
            "rank_fusion_factor arm."
        ),
    )
    parser.add_argument(
        "--arm", default=None, metavar="FLAG",
        help=(
            "Run the on/off ablation for one ranking arm instead of the "
            "full-context comparison. Takes the arm's config FLAG spelling "
            "(e.g. w_importance). All three signal classes are accepted: the "
            "rank_fusion_factor arms (RANK_ARMS), the RRF list weights "
            "(w_ppr, w_dual) and the applies_when boost (w_context_boost); "
            "arm_ablation.resolve_ablatable() validates against all of them "
            "at run time. An arm whose signal cannot be present on this "
            "harness refuses with the reason rather than reporting a zero "
            "delta that reads like a measured 'no win'."
        ),
    )
    parser.add_argument(
        "--weight", type=float, default=None,
        help=(
            "The arm's 'on' weight, only meaningful with --arm. Defaults to "
            "arm_ablation.DEFAULT_PROBE_WEIGHT when omitted; must be nonzero "
            "(weight 0.0 is the off leg, not an ablation)."
        ),
    )
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.arm is not None:
        # Imported lazily (not at module top): arm_ablation.py deliberately
        # does not import from this module (see its own docstring on why its
        # ingest preamble is a separate copy, not a shared helper), but a
        # top-level import here would still be the first thing this file
        # does on every invocation, including the default (no --arm) path
        # that never touches arm ablation at all.
        from benchlib import arm_ablation
        result = await arm_ablation.run_arm_ablation(arm_flag=args.arm, weight=args.weight)
    else:
        result = await run_eval()
    print(result.report_text)
    print(f"report written to {result.report_path}")
    print(f"ledger appended: {result.ledger_path}")
    return 0


def _run() -> int:
    """Thin wrapper so a pre-flight RuntimeError (missing key, alembic
    failure, ...) or a ValueError (an unknown --arm, a zero --weight, a
    cross-fingerprint refusal) prints as one readable line instead of a
    Python traceback -- main() itself still raises, so a test can assert on
    it."""
    try:
        return asyncio.run(main())
    except (RuntimeError, ValueError) as exc:
        print(f"run_retrieval_eval.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_run())
