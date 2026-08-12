"""Judge-qualification scoring, the G-D eligibility lock, and (T2.26) the
report/recorder plumbing for ``run_judge_qualification.py``.

Scoring is pure arithmetic over the gold's three-way verdicts. The binary
grounded/ungrounded numbers G-D bars on are derived through
``entailment_gold.GROUNDED_VERDICTS`` — never re-declared — and the
contradiction verdict is scored separately because its consumer (doc 08 §4.2)
is qualified on it specifically, on **both** its precision and its recall: a
judge that calls ``unsupported`` pairs ``contradicted`` loads a review queue
with noise, one that calls ``contradicted`` pairs ``unsupported`` surfaces
nothing at all, and no binary aggregate would show either. Both numbers were
computed here from the start; until 2026-08-08 only precision carried a bar,
and a judge scoring recall 0.0182 passed the gate. Which of the two is
truth-critical follows from what the consumer does with the verdict, and doc
17 §6's amendment records the inversion: the finding now opens review rather
than disputing, so recall is the truth-critical one.

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
import math
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


# ── census independence, disclosed per run (2026-08-12) ──────────────────


def census_independence(pairs: list[dict], verdict: str, bar: float) -> dict:
    """What a verdict class's census can actually express against ``bar``.

    A recall bar is a fraction of *propositions*, and this gold counts rows.
    Where two rows assert one proposition the two diverge, and the gap runs
    the dangerous way: a judge that catches a correlated pair banks two
    correlated hits, so the per-item tolerance is wider than the bar says.

    Disclosed on every run because the 2026-08-10 attempt was spent against
    a contradicted census of 80 rows over 78 independent propositions and
    **no artifact said so** — the finding arrived afterwards, in review, by
    which point the attempt was gone. `duplicate_propositions` existed and
    was wired into nothing but its own test.

    Reports rather than judges: no number here changes a score or a verdict.
    """
    from benchlib.duplicate_propositions import find_duplicate_propositions

    rows = [p for p in pairs if p.get("verdict") == verdict]
    row_ids = {p["id"] for p in rows}
    dupes = [
        f for f in find_duplicate_propositions(pairs)
        if f.left in row_ids and f.right in row_ids
    ]
    # Rows collapse by connected *component*, not by finding. A component of k
    # mutually-duplicate rows yields k(k-1)/2 findings and collapses k-1 rows,
    # so subtracting the finding count agrees with the truth only while every
    # component is exactly two wide — true of the contradicted census, false of
    # the entailed one, whose three-row component (T2.118) made this print one
    # proposition fewer than exist.
    parent: dict[str, str] = {}

    def _find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for finding in dupes:
        left, right = _find(finding.left), _find(finding.right)
        if left != right:
            parent[left] = right
    collapsed = sum(1 for node in list(parent) if _find(node) != node)
    independent = len(rows) - collapsed

    def _min_passing(n: int) -> tuple[int, float]:
        if n <= 0:
            return 0, 0.0
        need = math.ceil(bar * n)
        return need, need / n

    need_rows, eff_rows = _min_passing(len(rows))
    need_ind, eff_ind = _min_passing(independent)
    return {
        "verdict": verdict,
        "bar": bar,
        "rows": len(rows),
        "independent_propositions": independent,
        "duplicate_pairs": [[f.left, f.right] for f in dupes],
        "min_passing_rows": need_rows,
        "effective_bar_on_rows": round(eff_rows, 4),
        "min_passing_independent": need_ind,
        "effective_bar_on_independent": round(eff_ind, 4),
        "bar_expressible_on_rows": abs(eff_rows - bar) < 1e-9,
    }


# ── gate eligibility (doc 17 §11) ────────────────────────────────────────

MIN_GOLD_PAIRS = 200


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    live_pairs: int
    l2_fact_pairs: int
    author_labelled_pairs: int
    reasons: tuple[str, ...]



# The resample certification, and why the lock has to carry it.
#
# `LABELLING.md`'s Layer 3 requires a seeded blind resample (n = 93, bar <= 1
# disagreement) before the gold is trustworthy, and the Steps 0-5 review
# established that it is the **first independent accuracy measurement** this
# gold ever receives: the two blind passes are Claude-family agents labelling
# work Claude-family agents authored, and pass B "added ~zero bits and diverged
# identically to pass A".
#
# Until 2026-08-06 this lock checked size, the l2-fact floor and author-labels
# and **nothing else** — so a gold whose escalations were resolved read as
# eligible with its label error uncertified, and the one artifact standing
# between it and a gate claim was a policy no code enforced. T2.54's Step-6
# sitting cleared the author-label condition and made that reachable, so the
# condition is now enforced rather than remembered.
RESAMPLE_N = 93
RESAMPLE_MAX_DISAGREEMENTS = 1


# How many moved ids a refusal spells out before it summarises. A label
# flip is one or two pairs and must be named exactly; a re-authored gold
# moves hundreds and the list stops being the message.
_NAMED_MOVED_LIMIT = 12


def _describe_moved(recorded: dict, derived: dict) -> list[str]:
    """Name *which* pairs moved, not merely that something did.

    Split three ways because the three mean different things to a reader:
    a changed digest is a label (or premise, or hypothesis) flip on a pair
    the certification saw; a missing id is a pair deleted out from under
    it; a new id is a pair the sitting never judged.
    """
    changed = sorted(
        pid for pid, digest in recorded.items()
        if pid in derived and derived[pid] != digest
    )
    removed = sorted(set(recorded) - set(derived))
    added = sorted(set(derived) - set(recorded))

    out: list[str] = []
    for label, ids in (
        ("changed since certification", changed),
        ("removed since certification", removed),
        ("added since certification", added),
    ):
        if not ids:
            continue
        shown = ", ".join(ids[:_NAMED_MOVED_LIMIT])
        if len(ids) > _NAMED_MOVED_LIMIT:
            shown += f", … and {len(ids) - _NAMED_MOVED_LIMIT} more"
        out.append(f"{len(ids)} {label}: {shown}")
    return out


def _content_hash_reasons(resample: dict, pairs: list[dict]) -> list[str]:
    """Re-derive the certification's content basis and refuse a mismatch.

    This is the half D-7 was missing. The other resample checks read what
    the block *says*; this one reads what the gold *is* and asks whether
    the two describe the same pair set.
    """
    recorded_hash = resample.get("pairs_sha256")
    recorded_digests = resample.get("pair_digests")

    if not isinstance(recorded_hash, str) or not recorded_hash:
        return [
            "resample: 'pairs_sha256' missing — the block certifies a label "
            "error rate without naming the labels it saw, so a verdict "
            "flipped after the sitting would leave this lock green "
            "(T2.116). Re-score the sitting, or re-stamp the basis only if "
            "the current pairs are demonstrably the certified ones"
        ]
    if not isinstance(recorded_digests, dict) or not recorded_digests:
        return [
            "resample: 'pair_digests' missing — without the per-pair map a "
            "mismatch could say only that something moved, never which "
            "pairs did"
        ]

    # The aggregate is the authority and the map is diagnostic, so the map
    # deriving the aggregate is checked before the map is trusted to
    # explain anything. Editing one to match the pairs while leaving the
    # other stale lands here rather than passing.
    if entailment_gold.digest_map_hash(recorded_digests) != recorded_hash:
        return [
            "resample: the block's own 'pair_digests' do not derive its "
            "'pairs_sha256' — the certification is internally inconsistent "
            "and certifies nothing. Re-score the sitting rather than "
            "repairing either field by hand"
        ]

    derived_digests = entailment_gold.pair_digests(pairs)
    derived_hash = entailment_gold.pairs_content_hash(pairs)
    if derived_hash == recorded_hash:
        return []

    detail = _describe_moved(recorded_digests, derived_digests)
    return [
        "resample: the gold's pairs have moved since this sitting certified "
        f"them — certified {recorded_hash[:8]}, current {derived_hash[:8]}. "
        "A certification describes one pair set and this is a different "
        "one; the recorded disagreement count says nothing about the "
        "labels now on disk. " + "; ".join(detail)
    ]


def _resample_reasons(resample: object, pairs: list[dict]) -> list[str]:
    if not isinstance(resample, dict):
        return [
            "resample: absent — LABELLING.md Layer 3 requires a seeded blind "
            f"resample (n = {RESAMPLE_N}, bar <= {RESAMPLE_MAX_DISAGREEMENTS} "
            "disagreement) before this gold certifies anything. It is the "
            "first independent accuracy measurement the set receives and must "
            "come from outside the family that labelled it"
        ]
    out: list[str] = []
    n = resample.get("n")
    disagreements = resample.get("disagreements")
    if not isinstance(n, int) or n < RESAMPLE_N:
        out.append(f"resample: n = {n!r} below the ratified floor {RESAMPLE_N}")
    if not isinstance(disagreements, int) or disagreements > RESAMPLE_MAX_DISAGREEMENTS:
        out.append(
            f"resample: {disagreements!r} disagreements exceeds the ratified "
            f"bar of {RESAMPLE_MAX_DISAGREEMENTS}"
        )
    for field in ("seed", "performed_by", "date"):
        if not resample.get(field):
            out.append(f"resample: {field!r} missing — an uncitable resample certifies nothing")
    out.extend(_content_hash_reasons(resample, pairs))
    return out


def gate_eligibility(gold_doc: dict) -> Eligibility:
    live = [p for p in gold_doc["pairs"] if not p.get("retired")]
    n_live = len(live)
    n_l2 = gold_doc.get("declared_provenance_counts", {}).get("l2-fact", 0)
    n_author = sum(p.get("label_source") == "author" for p in live)
    resample = gold_doc.get("resample")

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
    reasons.extend(_resample_reasons(resample, gold_doc["pairs"]))

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
    """Every gated metric against its bar. A bar with no stated value is
    reported ``bar=None, passed=False``: ``BAR_METRICS`` is what declares a
    metric truth-critical, and a declared bar nobody has stated a number for
    cannot be cleared by any measurement (doc 17 §6, T2.109). Skipping it
    instead would let the unstated bar read as no bar at all, which is the
    silence this gate's whole redesign is about."""
    results = {}
    for bar_key, metric_key in verification_judge.BAR_METRICS.items():
        value = getattr(score, metric_key)
        bar = bars.get(bar_key)
        passed = (
            bar is not None
            and isinstance(value, (int, float))
            and value >= bar
        )
        results[bar_key] = {"metric": metric_key, "bar": bar,
                            "measured": value, "passed": bool(passed)}
    return results


# LABELLING.md's contacted-pairs rule (Rule B), stated before any number
# existed: T2.41 "must report every barred metric on **both** populations — all
# live pairs, and the second population — with the gate verdict required to
# hold on both".
#
# **The population is no longer "never contacted", and the name says so
# (LABELLING.md amendment 2026-08-10, ruling R3).** The 2026-08-08 re-measure
# ran fresh inference on every live pair, so a literal never-contacted set has
# not existed since; and because every run scores all live pairs, a strict
# reading would empty after each attempt. What the population *is*: pairs not
# contacted before the grown-gold attempt, with the per-pair miss census
# withheld — the withholding is what keeps it meaningful, since the ledger
# publishes slice-level attribution only.
#
# The boundary lives here rather than in `gold.json` because the gold's sha256
# is what the Layer-3 resample draw is pinned to: adding a per-pair marker
# would move the sha and void the certification the same file just received.
# LABELLING.md's History is the source of record for the range; the test suite
# pins the two together.
#
# **The constant does not move when a round appends pairs**, and that is the
# correction T2.115's plan review forced: the filter is `id >= …` and
# open-ended, so appended pairs join the population automatically. Moving it
# forward would shrink the gated population to the appending round's own pairs
# — which is how a growth round would silently make its own bar
# unrepresentable. Only LABELLING.md's range *text* extends its end.
RULE_B_FIRST_ID = "eg-0242"


def rule_b_population(live_pairs: list[dict]) -> list[dict]:
    """Rule B's second population: pairs not contacted before the grown-gold
    attempt, with the per-pair miss census withheld.

    Pooling matters here rather than being a formality. The 241 pairs below the
    boundary were contacted three times across two judge identities, so a
    single pooled number blends pairs a judge has already seen with pairs it
    has not — which is the contamination the growth round existed to escape.
    Scoring the subset costs nothing: the caller already holds every verdict
    keyed by pair id, so this is a second call to ``score_judgments`` and not a
    second gold contact.
    """
    return [p for p in live_pairs if p["id"] >= RULE_B_FIRST_ID]


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

    if not meta.get("gate_run"):
        # Keyed on the run mode, not on the gold. Until 2026-08-08 the only
        # banner was the eligibility one below, and an ineligible gold made
        # every interim run carry it -- so "no banner" and "gate run" were the
        # same thing by accident. The moment the gold became eligible an
        # interim report started rendering indistinguishably from a gate
        # verdict, while minting no record and claiming nothing. A report is
        # what a human reads; it has to say which kind it is on its own face.
        lines.append(
            "> **INTERIM — not a gate run.** No qualification record was "
            "minted and G-D is not opened by this report. Re-run with "
            "`--gate` for T2.41's evidence mode."
        )
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
    # The full invocation, not just the hash. The hash is not invertible, and
    # on a MISS no qualification record is written -- so before 2026-08-08 a
    # failed run recorded the model and nothing else. The G-D spike had to
    # probe ~18k candidate configs trying to reconstruct one, then fall back to
    # attributing cached calls by token checksum. Evidence a later reader
    # cannot reproduce the invocation for is weaker evidence than it looks.
    lines.append(
        f"- judge invocation: `base_url={identity.get('base_url')}` "
        f"`api_kind={identity.get('api_kind')}` "
        f"`params={json.dumps(identity.get('params'), sort_keys=True)}` "
        f"`dimensions={identity.get('dimensions')}` "
        f"`reasoning={identity.get('reasoning')}`"
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
        "each scored row's twin. Keyed on the gold's PAIRS since 2026-08-12, "
        "so an edit to something no judge was shown cannot reset it."
    )
    ci = meta.get("census_independence")
    if ci:
        note = (
            "rows == propositions"
            if ci["rows"] == ci["independent_propositions"]
            else f"{ci['rows'] - ci['independent_propositions']} duplicated "
                 f"proposition(s): {ci['duplicate_pairs']}"
        )
        lines.append(
            f"- census independence ({ci['verdict']}): {ci['rows']} rows over "
            f"{ci['independent_propositions']} independent propositions — {note}. "
            f"Against a bar of {ci['bar']}, the minimum passing score is "
            f"{ci['min_passing_rows']}/{ci['rows']} = "
            f"{ci['effective_bar_on_rows']} on rows and "
            f"{ci['min_passing_independent']}/{ci['independent_propositions']} = "
            f"{ci['effective_bar_on_independent']} on independent propositions. "
            + ("The bar is expressible on this census."
               if ci["bar_expressible_on_rows"] else
               "**The bar is NOT expressible on this census** — the effective "
               "bar differs from the stated one by quantisation alone, which "
               "is a bar nobody argued for.")
        )
    lines.append("")

    lines.append("## Bars (stated before the run; config defaults)")
    lines.append("")
    for bar_key, result in bar_results(score, meta["bars"]).items():
        measured = result["measured"]
        rendered = "undefined (no acceptances)" if measured is None else f"{measured:.4f}"
        bar = result["bar"]
        stated = "UNSTATED (owner has not set it)" if bar is None else f"{bar:.2f}"
        verdict = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"- `{bar_key}` = {stated} on `{result['metric']}`: "
            f"measured {rendered} → **{verdict}**"
        )
    lines.append("")
    lines.append("Granularity at this gold size:")
    lines.extend(_granularity_lines(score))
    lines.append("")

    nc_score = meta.get("rule_b_score")
    if nc_score is not None:
        lines.append(
            "## Bars on Rule B's second population"
        )
        lines.append("")
        lines.append(
            "LABELLING.md's contacted-pairs rule requires every barred metric "
            "on **both** populations, with the gate verdict required to hold on "
            f"both. The pairs above are all {score.n_pairs} live ones, of which "
            f"{score.n_pairs - nc_score.n_pairs} were contacted before; these "
            f"are the {nc_score.n_pairs} pairs "
            f"(`{RULE_B_FIRST_ID}`+) not contacted before the grown-gold attempt."
        )
        lines.append("")
        for bar_key, result in bar_results(nc_score, meta["bars"]).items():
            measured = result["measured"]
            rendered = "undefined (no acceptances)" if measured is None else f"{measured:.4f}"
            bar = result["bar"]
            stated = "UNSTATED (owner has not set it)" if bar is None else f"{bar:.2f}"
            verdict = "PASS" if result["passed"] else "FAIL"
            lines.append(
                f"- `{bar_key}` = {stated} on `{result['metric']}`: "
                f"measured {rendered} → **{verdict}**"
            )
        lines.append("")
        lines.append("Granularity on this subset — **read this before the numbers above**:")
        lines.extend(_granularity_lines(nc_score))
        lines.append(
            "  A bar can only be met at a value the lattice contains. T2.110 "
            "sized the *pooled* contradicted census at 80 so that 76/80 = 0.9500 "
            "sits exactly on `contradiction_recall_bar`; that analysis was never "
            "run for this subset, whose smaller census may place the bar between "
            "two attainable values and so enforce a stricter number than the one "
            "stated. Where it does, the subset verdict is evidence about the "
            "census, not only about the judge."
        )
        lines.append("")

    ci = meta.get("census_independence")
    if ci and ci["rows"] != ci["independent_propositions"]:
        # The owner ruled 2026-08-12 that independence is handled by
        # reporting rather than retiring, which puts the whole weight of that
        # ruling here: the bar is applied to rows, and a row-pass that the
        # independent reading would fail must say so rather than read as a
        # clear pass. Computed here rather than in `census_independence`,
        # which takes no judge output by construction.
        hits = round(score.contradiction_recall * ci["rows"])
        collapsed = ci["rows"] - ci["independent_propositions"]
        worst_independent = (hits - collapsed) / ci["independent_propositions"]
        lines.append("## Census independence — read with the recall verdict")
        lines.append("")
        lines.append(
            f"- {ci['rows']} contradicted rows over "
            f"{ci['independent_propositions']} independent propositions "
            f"({collapsed} duplicated: {ci['duplicate_pairs']})."
        )
        lines.append(
            f"- Measured contradiction-recall {score.contradiction_recall:.4f} "
            f"is {hits}/{ci['rows']} on rows. If the judge caught every "
            f"correlated pair, the independent reading is at worst "
            f"{max(hits - collapsed, 0)}/{ci['independent_propositions']} = "
            f"{max(worst_independent, 0.0):.4f}."
        )
        if score.contradiction_recall >= ci["bar"] > worst_independent:
            lines.append(
                f"- **This pass is not robust to the independence reading.** It "
                f"clears {ci['bar']} on rows and falls below it on independent "
                f"propositions. The duplicate eases the bar in exactly this "
                f"case, which is why the ruling that kept it also required this "
                f"line to exist."
            )
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
