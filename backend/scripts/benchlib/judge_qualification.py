"""Judge-qualification scoring, the G-D eligibility lock, and (T2.26) the
report/recorder plumbing for ``run_judge_qualification.py``.

Scoring is pure arithmetic over the gold's three-way verdicts. The binary
grounded/ungrounded numbers G-D bars on are derived through
``entailment_gold.GROUNDED_VERDICTS`` — never re-declared — and the
contradiction verdict is scored separately because the veto consumer (doc 08
§4.2) is qualified on it specifically: a judge that calls ``unsupported``
pairs ``contradicted`` manufactures disputes, and no binary aggregate would
show it.

``gate_eligibility`` is the mechanical half of the doc 17 §11 composition
rule: G-D's gate mode refuses a gold that is too small (< 200 live pairs),
majority-synthetic (``l2-fact`` premises below 50% of live pairs — ratified
by the owner 2026-07-31; §11's own clause says a ``199 synthetic / 1 real``
set must not pass), or not yet adjudicated (any live
``label_source == "author"``). The floor is 50% rather than 100% because
``temporal`` pairs *cannot* carry real premises today — ``fact_lift`` never
renders a validity window into fact text — and the windowed slice guards
the veto's window semantics, so it stays hand-authored inside the other
half. The counts are always surfaced (``l2-fact: 130/241``), never
collapsed into a boolean, so T2.41's human adjudication still sees the raw
composition.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchlib import entailment_gold, ledger
from benchlib.twin import EvalRun

from app.services import verification_judge
from app.services.verification_judge import (
    JUDGE_VERDICTS,
    ProbeVerdict,
    judge_identity_hash,
)

SANITY_PAIRS_PATH = entailment_gold.ENTAILMENT_DIR / "sanity_pairs.json"

INVALID = "invalid"


@dataclass(frozen=True)
class QualificationScore:
    n_pairs: int
    invalid: int
    confusion: dict[str, dict[str, int]]
    entailed_precision: float | None
    entailed_recall: float
    contradiction_precision: float | None
    contradiction_recall: float
    per_slice: dict[str, dict]
    majority_class_floor: float


def _precision_recall(
    pairs: list[dict], verdicts: dict[str, ProbeVerdict], accepted: frozenset[str],
) -> tuple[float | None, float]:
    """Precision/recall of the binary decision "verdict in ``accepted``".

    An invalid response never registers as an acceptance (it cannot create
    a false accept) and always misses its gold class (it costs recall).
    Precision over zero acceptances is undefined — ``None``, which every
    bar comparison downstream treats as failing, never as passing.
    """
    tp = fp = gold_positive = 0
    for pair in pairs:
        gold_hit = pair["verdict"] in accepted
        gold_positive += gold_hit
        probe = verdicts[pair["id"]]
        if probe.valid and probe.verdict in accepted:
            if gold_hit:
                tp += 1
            else:
                fp += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / gold_positive if gold_positive else 0.0
    return precision, recall


def score_judgments(
    pairs: list[dict], verdicts: dict[str, ProbeVerdict],
) -> QualificationScore:
    confusion: dict[str, dict[str, int]] = {}
    per_slice: dict[str, dict] = {}
    gold_counts: dict[str, int] = {}
    invalid = 0

    for pair in pairs:
        gold = pair["verdict"]
        probe = verdicts[pair["id"]]
        predicted = probe.verdict if probe.valid else INVALID
        if predicted == INVALID:
            invalid += 1

        confusion.setdefault(gold, {})
        confusion[gold][predicted] = confusion[gold].get(predicted, 0) + 1
        gold_counts[gold] = gold_counts.get(gold, 0) + 1

        for tag in pair.get("slice_tags", []):
            bucket = per_slice.setdefault(tag, {"n": 0, "correct": 0})
            bucket["n"] += 1
            bucket["correct"] += predicted == gold

    for bucket in per_slice.values():
        bucket["accuracy"] = bucket["correct"] / bucket["n"]

    entailed_precision, entailed_recall = _precision_recall(
        pairs, verdicts, frozenset(entailment_gold.GROUNDED_VERDICTS),
    )
    contradiction_precision, contradiction_recall = _precision_recall(
        pairs, verdicts, frozenset({"contradicted"}),
    )

    n_pairs = len(pairs)
    return QualificationScore(
        n_pairs=n_pairs,
        invalid=invalid,
        confusion=confusion,
        entailed_precision=entailed_precision,
        entailed_recall=entailed_recall,
        contradiction_precision=contradiction_precision,
        contradiction_recall=contradiction_recall,
        per_slice=per_slice,
        majority_class_floor=max(gold_counts.values()) / n_pairs if n_pairs else 0.0,
    )


# ── gate eligibility (doc 17 §11) ────────────────────────────────────────

MIN_GOLD_PAIRS = 200


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    live_pairs: int
    l2_fact_pairs: int
    author_labelled_pairs: int
    reasons: tuple[str, ...]


def gate_eligibility(gold_doc: dict) -> Eligibility:
    live = [p for p in gold_doc["pairs"] if not p.get("retired")]
    n_live = len(live)
    n_l2 = gold_doc.get("declared_provenance_counts", {}).get("l2-fact", 0)
    n_author = sum(p.get("label_source") == "author" for p in live)

    reasons = [
        f"composition: {n_live} live pairs; l2-fact: {n_l2}/{n_live}; "
        f"author-labelled: {n_author}/{n_live}"
    ]
    if n_live < MIN_GOLD_PAIRS:
        reasons.append(
            f"live pairs {n_live} < {MIN_GOLD_PAIRS} (doc 17 §11 size floor)"
        )
    if 2 * n_l2 < n_live:
        reasons.append(
            f"l2-fact premises {n_l2}/{n_live} sit below the >=50% floor "
            "(doc 17 §11, ratified 2026-07-31: a grown-but-still-synthetic "
            "set must not pass; temporal's hand-authored premises live "
            "inside the other half)"
        )
    if n_author > 0:
        reasons.append(
            f"author-labelled: {n_author}/{n_live} live pairs await "
            "adjudication (doc 17 §11; T2.54's re-adjudication flips them)"
        )

    eligible = len(reasons) == 1
    return Eligibility(
        eligible=eligible,
        live_pairs=n_live,
        l2_fact_pairs=n_l2,
        author_labelled_pairs=n_author,
        reasons=tuple(reasons),
    )


# ── the sanctioned recorder ──────────────────────────────────────────────


def record_qualification(score, twin, metadata: dict, path=ledger.DEFAULT_PATH) -> None:
    """The one accuracy-bearing ledger write on this path. ``EvalRun`` is
    constructed first so the no-twin-no-accuracy guard bites before any
    metadata merging can smuggle a twinless row past it."""
    eval_run = EvalRun(score=score, twin=twin)
    row = {"kind": "judge_qualification", **metadata, **eval_run.to_ledger_payload()}
    ledger.record(row, path=path)


# ── serving-invariant token totals ───────────────────────────────────────


def serving_invariant_tokens(tokens_by_purpose: dict) -> dict:
    """Totals that must not move when a call flips from live to warm
    replay: a live call with a usage envelope becomes ``cache_known`` on
    replay, and a live call without one becomes ``cache_unknown`` — so the
    cross-bucket sums are the same cost either way. The raw bucket split
    stays in the ledger row's full twin payload; only these totals may
    enter the reproducibility block, or a warm rerun's diff would fail on
    serving noise."""
    invariant = {}
    for purpose, usage in tokens_by_purpose.items():
        get = lambda key: usage.get(key, 0) or 0  # noqa: E731
        invariant[purpose] = {
            "calls": get("live_calls") + get("cache_known_calls") + get("cache_unknown_calls"),
            "prompt_tokens": get("live_prompt_tokens") + get("cache_known_prompt_tokens"),
            "completion_tokens": get("live_completion_tokens") + get("cache_known_completion_tokens"),
            "cached_prompt_tokens": get("live_cached_prompt_tokens") + get("cache_known_cached_prompt_tokens"),
            "unknown_calls": get("live_unknown_calls") + get("cache_unknown_calls"),
        }
    return invariant


# ── bar comparison, report, reproducibility block ────────────────────────


def bar_results(score: QualificationScore, bars: dict[str, float]) -> dict[str, dict]:
    results = {}
    for bar_key, metric_key in verification_judge.BAR_METRICS.items():
        value = getattr(score, metric_key)
        passed = isinstance(value, (int, float)) and value >= bars[bar_key]
        results[bar_key] = {"metric": metric_key, "bar": bars[bar_key],
                            "measured": value, "passed": bool(passed)}
    return results


def _gold_class_count(score: QualificationScore, verdict: str) -> int:
    return sum(score.confusion.get(verdict, {}).values())


def _granularity_lines(score: QualificationScore) -> list[str]:
    """The set-size arithmetic, computed from this score's own gold counts
    (never hardcoded): what one error does to each barred metric."""
    lines = []
    entailed = _gold_class_count(score, "entailed")
    contradicted = _gold_class_count(score, "contradicted")
    if entailed:
        lines.append(
            f"- {entailed} gold-entailed pairs: one false accept bounds "
            f"entailed-precision at {entailed}/{entailed + 1} "
            f"≈ {entailed / (entailed + 1):.3f}; one false reject puts recall at "
            f"{(entailed - 1)}/{entailed} ≈ {(entailed - 1) / entailed:.3f}."
        )
    if contradicted:
        lines.append(
            f"- {contradicted} gold-contradicted pairs: one manufactured "
            f"contradiction bounds contradiction-precision at "
            f"{contradicted}/{contradicted + 1} ≈ {contradicted / (contradicted + 1):.3f}."
        )
    return lines


def reproducible_metrics(score: QualificationScore, eligibility: Eligibility, meta: dict) -> dict:
    """The byte-identical-across-reruns subset. Deliberately excluded:
    latency (wall-clock noise), timestamps and run ids, and
    ``gold_touching_attempts`` — the attempt counter increments on every
    gold contact including the warm verification rerun, so including it
    would make the reproducibility diff fail by design."""
    return {
        "score": asdict(score),
        "eligibility": {
            "eligible": eligibility.eligible,
            "live_pairs": eligibility.live_pairs,
            "l2_fact_pairs": eligibility.l2_fact_pairs,
            "author_labelled_pairs": eligibility.author_labelled_pairs,
            "reasons": list(eligibility.reasons),
        },
        "bars": meta["bars"],
        "bar_results": bar_results(score, meta["bars"]),
        "gold_version": meta["gold_version"],
        "gold_sha256": meta["gold_sha256"],
        "identity_hash": meta["judge_identity"]["identity_hash"],
        "n_fixtures": meta["n_fixtures"],
        "fixture_tokens": serving_invariant_tokens(meta["fixture_tokens"]),
        "gold_tokens": serving_invariant_tokens(meta["gold_tokens"]),
    }


def render_report(
    score: QualificationScore, eligibility: Eligibility, twin, meta: dict,
) -> str:
    lines: list[str] = []
    lines.append(f"# Judge qualification — {meta['date']}")
    lines.append("")

    if not eligibility.eligible:
        lines.append(
            "> **INTERIM — this is not a qualification verdict and cannot open "
            "G-D.** The gold fails doc 17 §11's composition rule; the gate run "
            "is T2.41's, after T2.54 grows and adjudicates the gold:"
        )
        for reason in eligibility.reasons:
            lines.append(f"> - {reason}")
        lines.append("")

    lines.append(f"- run id: `{meta['run_id']}` (recorded {meta['timestamp']})")
    lines.append(f"- git sha: `{meta['git_sha']}`")
    identity = meta["judge_identity"]
    lines.append(
        f"- judge identity: `{identity['identity_hash']}` "
        f"(model `{identity.get('model')}`, prompt v{identity.get('prompt_version')}, "
        f"prompt_sha `{identity.get('prompt_sha')}`)"
    )
    lines.append(
        f"- gold: version {meta['gold_version']}, sha256 `{meta['gold_sha256']}`, "
        f"{score.n_pairs} pairs scored"
    )
    lines.append(
        f"- gold_touching_attempts: {meta['gold_touching_attempts']} — counts "
        "gold CONTACTS for this gold_sha256 across all judge identities, "
        "including warm cache replays (a verification rerun increments it on "
        "one live pass); live-vs-replay per contact is reconstructible from "
        "each scored row's twin. Resets only when the gold file itself "
        "changes (T2.54 growth)."
    )
    lines.append("")

    lines.append("## Bars (stated before the run; config defaults)")
    lines.append("")
    for bar_key, result in bar_results(score, meta["bars"]).items():
        measured = result["measured"]
        rendered = "undefined (no acceptances)" if measured is None else f"{measured:.4f}"
        verdict = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"- `{bar_key}` = {result['bar']:.2f} on `{result['metric']}`: "
            f"measured {rendered} → **{verdict}**"
        )
    lines.append("")
    lines.append("Granularity at this gold size:")
    lines.extend(_granularity_lines(score))
    lines.append("")

    lines.append("## Confusion (gold rows × predicted columns)")
    lines.append("")
    predicted_cols = sorted(JUDGE_VERDICTS) + [INVALID]
    lines.append("| gold \\ predicted | " + " | ".join(predicted_cols) + " |")
    lines.append("|---|" + "---|" * len(predicted_cols))
    for gold in sorted(JUDGE_VERDICTS):
        row = score.confusion.get(gold, {})
        cells = " | ".join(str(row.get(col, 0)) for col in predicted_cols)
        lines.append(f"| {gold} | {cells} |")
    lines.append("")
    lines.append(f"- invalid responses: {score.invalid}/{score.n_pairs}")
    lines.append(f"- majority-class floor (three-way): {score.majority_class_floor:.3f}")
    lines.append("")

    lines.append("## Per-slice accuracy (three-way exact match)")
    lines.append("")
    lines.append("| slice | n | correct | accuracy |")
    lines.append("|---|---|---|---|")
    for tag in sorted(score.per_slice):
        bucket = score.per_slice[tag]
        lines.append(
            f"| {tag} | {bucket['n']} | {bucket['correct']} | "
            f"{bucket['accuracy']:.3f} |"
        )
    lines.append("")

    lines.append("## Cost twin (doc 11 §6 Tier-C bound)")
    lines.append("")
    gold_tokens = serving_invariant_tokens(meta["gold_tokens"])
    fixture_tokens = serving_invariant_tokens(meta["fixture_tokens"])
    usage = gold_tokens.get("verification", {})
    total = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    per_claim = total / score.n_pairs if score.n_pairs else 0
    lines.append(
        f"- gold pass: {usage.get('calls', 0)} calls, {total} tokens → "
        f"**{per_claim:.1f} tokens/claim** (the per-claim bound; excludes the "
        "fixture stage)"
    )
    fx = fixture_tokens.get("verification", {})
    fx_total = fx.get("prompt_tokens", 0) + fx.get("completion_tokens", 0)
    lines.append(
        f"- fixture stage (plumbing overhead, {meta['n_fixtures']} pairs): "
        f"{fx.get('calls', 0)} calls, {fx_total} tokens"
    )
    lines.append("")
    lines.append("Latency by channel (live/cache populations, wall-clock — "
                 "expected to vary run to run):")
    lines.append("")
    lines.append("```")
    for name in sorted(twin.channels):
        stats = twin.channels[name]
        lines.append(
            f"{name}: live n={stats.live.n} powered={stats.live.powered} "
            f"p50={stats.live.p50} p95={stats.live.p95} | "
            f"cache n={stats.cache.n} powered={stats.cache.powered} "
            f"p50={stats.cache.p50} p95={stats.cache.p95}"
        )
    lines.append("```")
    lines.append("")

    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        "Two consecutive runs on an unchanged tree with a warm cache must "
        "reproduce this block byte-for-byte. Token figures are "
        "serving-invariant totals (live + cache_known) so a live-vs-warm "
        "diff cannot fail on bucket shift; latency, timestamps and the "
        "attempt counter are excluded on purpose."
    )
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(
        reproducible_metrics(score, eligibility, meta), indent=2, sort_keys=True,
    ))
    lines.append("```")
    return "\n".join(lines) + "\n"


# ── the app-side qualification record (only --gate may mint it) ──────────


def write_qualification_record(
    record_path: Path,
    *,
    gold_path: Path,
    identity: dict,
    score: QualificationScore,
    gold_doc: dict,
    ledger_run_id: str,
    bars: dict[str, float],
    git_sha: str,
    timestamp: str,
) -> None:
    """``gold_sha256`` is computed here from ``gold_path``'s bytes — never
    caller-supplied — and the canonical record path is refused unless the
    gold is the canonical one, so a rehearsal ``--gate`` run against an
    easy gold cannot mint a record the app-side guard honours."""
    record_path = Path(record_path)
    canonical_record = verification_judge.QUALIFICATION_RECORD_PATH.resolve()
    if record_path.resolve() == canonical_record \
            and Path(gold_path).resolve() != entailment_gold.GOLD_PATH.resolve():
        raise ValueError(
            "refusing to write the canonical qualification record from a "
            f"non-canonical gold ({gold_path}); rehearsals must use a "
            "non-default record path"
        )

    eligibility = gate_eligibility(gold_doc)
    record = {
        "judge_identity": {**identity, "identity_hash": judge_identity_hash(identity)},
        "metrics": {
            "entailed_precision": score.entailed_precision,
            "entailed_recall": score.entailed_recall,
            "contradiction_precision": score.contradiction_precision,
            "contradiction_recall": score.contradiction_recall,
            "invalid": score.invalid,
            "n_pairs": score.n_pairs,
        },
        "gate_eligible": eligibility.eligible,
        "eligibility": {
            "live_pairs": eligibility.live_pairs,
            "l2_fact_pairs": eligibility.l2_fact_pairs,
            "author_labelled_pairs": eligibility.author_labelled_pairs,
            "reasons": list(eligibility.reasons),
        },
        "bars_in_effect": bars,
        "gold_sha256": hashlib.sha256(Path(gold_path).read_bytes()).hexdigest(),
        "ledger_run_id": ledger_run_id,
        "git_sha": git_sha,
        "recorded_at": timestamp,
    }
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
