"""Faithfulness-gate scoring (TH1.17) — the plumbing behind TH1.10's verify.

Scores the ONE app-side ``verification`` judge
(``app/services/verification_judge.py``) against the **claim/span**
entailment gold doc 16 §4 / doc 17 §6 name, and reports span-support
coverage per doc 16 §4's formula. TH1.01 (`docs/superpowers/specs/`
`2026-08-15-faithfulness-metric-and-bar-design.md`) defined the metric and
committed the bars in ``app/services/faithfulness_bars.py`` before this
module existed; every number this module compares against a bar is
**imported** from there, never restated — ``tests/test_faithfulness_bar_``
``restatement_scan.py`` is the executable half of that rule.

**The real gold does not exist yet.** Doc 20 §4's ordering rule and TH1.01
§5 are explicit: authoring claim/span pairs is a task this module's own
build may never perform. ``SPAN_GOLD_PATH`` names where the sibling file
(next to ``entailment/gold.json``, never mixed into it) will live once that
task lands; ``load_span_gold`` raises ``SpanGoldAbsent`` when it does not,
and every caller in this module is built to report that honestly rather
than score an empty set as a pass. The scoring and coverage functions below
are exercised today only against a **fixture** gold under
``tests/fixtures/faithfulness_gate/`` — clearly labelled as a fixture, not
a sixth gold set.

**No live judge call happens by default.** ``score_via_live_judge`` is real
plumbing (mirrors ``run_judge_qualification.py``'s ``_probe_set``), but the
runner never reaches it while the gold is absent, and this module's own
tests only ever drive it through a stub orchestrator — never a network
call, never a measurement attempt, per the task's own prohibition.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from benchlib import entailment_gold
from benchlib.twin import (
    LatencyRecorder,
    Twin,
    TwinningOrchestrator,
    live_call_count,
    served_by_label,
)

from app.config import LLMPurposeConfig
from app.services import faithfulness_bars as fb
from app.services.verification_judge import ProbeVerdict, VerificationJudge

# ── the gold this module scores against — a future sibling, not this file's to author ──

SPAN_GOLD_PATH = entailment_gold.ENTAILMENT_DIR / "span_gold.json"
# A sibling of judge_qualification's CACHE_DIR, not the same directory: the
# span variant's premises are document bytes, not l2-fact text, so a shared
# cache would key two different call distributions under one namespace.
SPAN_CACHE_DIR = entailment_gold.ENTAILMENT_DIR / "cache_span"

SPAN_VARIANT = "claim-span"

# TH1.01 §5 item 3: binary, on purpose — no consumer here makes a
# contradiction discrimination over spans, unlike the claim/fact gold.
SPAN_VERDICTS = frozenset({"entailed", "not-entailed"})

# TH1.01 §5 item 5. `document-span` and `qa-draft` were reserved at zero
# "until their producer task exists" — TH1.02 (documents/blocks writer) and
# TH1.08 (grounded Q&A) both shipped in v1.0, and **the owner ruled on
# 2026-08-17 that the gold uses real block spans and real QA drafts**, so the
# reservation is lifted rather than merely expired.
#
# The reservation was not arbitrary and lifting it is not a relaxation: doc 17
# §6's recorded stance is that this gold is seeded from real block answers and
# that *synthetic-only entailment gold is rejected as unrepresentative*. While
# the producers did not exist, `hand-authored-fixture-span` was the only honest
# option; now that they do, authoring only fixtures would produce exactly the
# gold that stance rejects. Nothing here forbids a fixture pair — the
# distribution is the owner's to compose — but a real span is no longer a
# structural violation.
PROVENANCE_VALUES = frozenset(
    {"hand-authored-fixture-span", "document-span", "qa-draft"}
)
RESERVED_ZERO_PROVENANCE: frozenset[str] = frozenset()

# The collapsing rule G-D's own scorer uses for the claim/fact gold,
# imported rather than re-declared: "entailed" is the only grounded verdict.
_ACCEPTED = frozenset(entailment_gold.GROUNDED_VERDICTS)


class SpanGoldAbsent(Exception):
    """Raised with the path that was checked — never with a bare message —
    so a caller can report exactly where it looked without re-deriving the
    default."""

    def __init__(self, path: Path):
        self.path = path
        super().__init__(str(path))


class SpanAnchorDrift(Exception):
    """A pair's recorded span text no longer matches the fixture document
    it claims to cite — content moved out from under an anchored pair, the
    same class of failure the claim/fact gold's ``fact_key`` byte-bind
    guards against, reinterpreted for document bytes instead of a harvest
    manifest row."""


# ── span anchors: TH1.01 §5 item 1 ───────────────────────────────────────


@dataclass(frozen=True)
class SpanAnchor:
    fixture_path: str
    content_hash: str
    block_id: str
    char_span: tuple[int, int]


def _anchor_from_dict(raw: dict) -> SpanAnchor:
    start, end = raw["char_span"]
    return SpanAnchor(
        fixture_path=raw["fixture_path"],
        content_hash=raw["content_hash"],
        block_id=raw["block_id"],
        char_span=(int(start), int(end)),
    )


def resolve_anchor_text(anchor: SpanAnchor, base_dir: Path) -> str:
    """Re-derive the premise bytes from the anchored fixture document and
    byte-compare against its recorded hash — drift fails loudly rather than
    silently serving a stale span, exactly as the claim/fact gold's
    harvest-manifest byte-bind does for ``l2-fact`` premises."""
    doc_path = base_dir / anchor.fixture_path
    content = doc_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if digest != anchor.content_hash:
        raise SpanAnchorDrift(
            f"{anchor.fixture_path}: content_hash {anchor.content_hash} does "
            f"not match the fixture document's current hash {digest} — the "
            f"document moved under this anchor; retire and re-anchor the pair"
        )
    start, end = anchor.char_span
    # Bounds only -- an out-of-range span on a hash-matching document must
    # refuse rather than silently slice a truncated or empty premise. Note
    # `end == start` (an empty range) is deliberately NOT refused here: that
    # is a known, separate defect in `_span_literal`'s storage (TH1.04) and
    # is the owner's to fix, not this loader's.
    if start < 0 or end < start or end > len(content):
        raise ValueError(
            f"{anchor.fixture_path}: char_span {anchor.char_span} is out of "
            f"bounds for a document of length {len(content)} — refusing to "
            f"resolve a span this loader cannot read faithfully"
        )
    return content[start:end]


def build_premise(pair: dict, base_dir: Path) -> str:
    """The ordered concatenation of exactly the cited span bytes, and
    nothing else (TH1.01 §1) — no surrounding block context, no
    whole-document fallback."""
    anchors = [_anchor_from_dict(raw) for raw in pair["premise_spans"]]
    if not anchors:
        raise ValueError(f"pair {pair.get('id')!r} carries no premise spans")
    return "\n\n".join(resolve_anchor_text(a, base_dir) for a in anchors)


def validate_pair_shape(pair: dict) -> None:
    verdict = pair.get("verdict")
    if verdict not in SPAN_VERDICTS:
        raise ValueError(
            f"pair {pair.get('id')!r} carries verdict {verdict!r}, not one "
            f"of {sorted(SPAN_VERDICTS)}"
        )
    provenance = pair.get("provenance")
    if provenance not in PROVENANCE_VALUES:
        raise ValueError(
            f"pair {pair.get('id')!r} carries provenance {provenance!r}, "
            f"not one of {sorted(PROVENANCE_VALUES)}"
        )
    if provenance in RESERVED_ZERO_PROVENANCE:
        raise ValueError(
            f"pair {pair.get('id')!r} claims provenance {provenance!r}, "
            "which TH1.01 §5 reserves at zero pairs until its producer "
            "task exists"
        )
    if not pair.get("premise_spans"):
        raise ValueError(f"pair {pair.get('id')!r} carries no premise spans")

    # `slice_tags` was checked nowhere while `score_span_judgments` read it as
    # `pair.get("slice_tags", [])`. Two silent failures followed from that, and
    # both are invisible in the report rather than loud: a pair with the field
    # MISSING scored into the aggregate and into no slice at all, and a typo'd
    # tag minted a phantom slice of one. Ledger rule 4 is that per-slice numbers
    # are never collapsed — a gold that quietly drops pairs out of every slice
    # collapses them by omission, which is the same dishonesty arriving through
    # a hole instead of a decision. The vocabulary itself stays the gold's to
    # define (its LABELLING.md), so this checks shape and non-emptiness, not
    # membership.
    tags = pair.get("slice_tags")
    if not isinstance(tags, list) or not tags:
        raise ValueError(
            f"pair {pair.get('id')!r} carries slice_tags {tags!r}; it must be a "
            "non-empty list. A missing or empty value scores into the aggregate "
            "and into no slice, which hides the pair from every per-slice number"
        )
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(
                f"pair {pair.get('id')!r} carries a non-string or blank slice "
                f"tag {tag!r}; a blank tag becomes its own phantom slice"
            )


def load_span_gold(path: str | Path = SPAN_GOLD_PATH) -> dict:
    """The real gold, loaded and shape-validated. Raises ``SpanGoldAbsent``
    — never returns an empty structure — when the file does not exist, so a
    caller cannot mistake "nothing to load" for "loaded zero pairs".

    Beyond ``validate_pair_shape``'s per-pair checks (verdict, provenance,
    premise spans), this also refuses a document with no ``"pairs"`` key at
    all, a pair with no usable ``id``, a duplicate ``id`` (which would
    silently overwrite an earlier verdict in every ``dict[id, ...]`` this
    module builds and double-count that pair's slice), and a pair missing
    ``answer_id`` or ``hypothesis`` — both are read unguarded downstream by
    ``score_answer_coverage`` and ``score_via_live_judge``."""
    path = Path(path)
    if not path.exists():
        raise SpanGoldAbsent(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if "pairs" not in doc:
        raise ValueError(f"{path}: gold document carries no 'pairs' key")

    seen_ids: set[str] = set()
    for pair in doc["pairs"]:
        validate_pair_shape(pair)
        pair_id = pair.get("id")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError(f"pair carries no usable 'id': {pair!r}")
        if pair_id in seen_ids:
            raise ValueError(
                f"duplicate pair id {pair_id!r} in {path} — ids must be "
                f"unique, or a repeated id silently overwrites an earlier "
                f"verdict and double-counts that pair's slice"
            )
        seen_ids.add(pair_id)
        if not pair.get("answer_id"):
            raise ValueError(f"pair {pair_id!r} carries no 'answer_id'")
        if not pair.get("hypothesis"):
            raise ValueError(f"pair {pair_id!r} carries no 'hypothesis'")
    return doc


# ── scoring: judge accuracy against the gold's own binary verdicts ───────


@dataclass(frozen=True)
class FaithfulnessScore:
    n_pairs: int
    invalid: int
    confusion: dict[str, dict[str, int]]
    entailed_precision: float | None
    entailed_recall: float | None
    per_slice: dict[str, dict]


def score_span_judgments(
    pairs: Sequence[dict], verdicts: dict[str, ProbeVerdict]
) -> FaithfulnessScore:
    """Precision/recall of the judge's ``entailed`` call against the gold's
    binary verdict, plus per-slice accuracy. An invalid or missing verdict
    never registers as an acceptance (TH1.01: "an unmeasurable claim is not
    an entailed claim") — it costs recall like any other miss and can never
    manufacture a false accept."""
    confusion: dict[str, dict[str, int]] = {}
    per_slice: dict[str, dict] = {}
    invalid = 0
    tp = fp = gold_positive = 0

    for pair in pairs:
        gold = pair["verdict"]
        probe = verdicts[pair["id"]]
        predicted = (
            "entailed" if (probe.valid and probe.verdict in _ACCEPTED)
            else "not-entailed"
        )
        if not probe.valid:
            invalid += 1

        confusion.setdefault(gold, {})
        confusion[gold][predicted] = confusion[gold].get(predicted, 0) + 1

        gold_hit = gold == "entailed"
        gold_positive += gold_hit
        if predicted == "entailed":
            if gold_hit:
                tp += 1
            else:
                fp += 1

        for tag in pair.get("slice_tags", []):
            bucket = per_slice.setdefault(tag, {"n": 0, "correct": 0})
            bucket["n"] += 1
            bucket["correct"] += predicted == gold

    for bucket in per_slice.values():
        bucket["accuracy"] = bucket["correct"] / bucket["n"]

    precision = tp / (tp + fp) if (tp + fp) else None
    # Symmetric with precision: "unmeasured is not zero" applies to both
    # sides. A gold with no entailed pairs at all leaves recall undefined,
    # not fabricated as a real 0.0 the judge somehow earned.
    recall = tp / gold_positive if gold_positive else None

    return FaithfulnessScore(
        n_pairs=len(pairs),
        invalid=invalid,
        confusion=confusion,
        entailed_precision=precision,
        entailed_recall=recall,
        per_slice=per_slice,
    )


# ── span-support coverage: TH1.01 §1's per-answer predicate, imported ────


@dataclass(frozen=True)
class AnswerCoverage:
    answer_id: str
    entailed: int
    total: int
    grounded: bool


def score_answer_coverage(
    pairs: Sequence[dict], verdicts: dict[str, ProbeVerdict], bars: dict[str, float],
) -> list[AnswerCoverage]:
    """Group sentence-claim pairs by ``answer_id`` (the sentence-grained
    counting unit TH1.01 §1 fixes) and decide each synthetic answer's
    grounded/not-grounded boundary through ``faithfulness_bars.answer_grounded``
    — never a locally re-derived ratio-and-threshold, so the boundary this
    module reports and the boundary TH1.09's serving check will enforce are
    one predicate."""
    by_answer: dict[str, list[dict]] = {}
    for pair in pairs:
        by_answer.setdefault(pair["answer_id"], []).append(pair)

    out = []
    for answer_id, group in by_answer.items():
        entailed = sum(
            1 for p in group
            if verdicts[p["id"]].valid and verdicts[p["id"]].verdict in _ACCEPTED
        )
        total = len(group)
        out.append(AnswerCoverage(
            answer_id=answer_id, entailed=entailed, total=total,
            grounded=fb.answer_grounded(entailed, total, bars),
        ))
    return sorted(out, key=lambda a: a.answer_id)


# ── bar visibility: T2.128's obligation, built only on the imported resolver ──


def bar_visibility_rows(rows: dict[str, object]) -> list[dict]:
    """Per bar: committed, effective, requested and a three-way status —
    ``no config row`` / ``honoured`` / ``CLAMPED``. Computed entirely from
    ``fb.FAITHFULNESS_BARS`` (defaults + direction) and
    ``fb.resolve_faithfulness_bars`` (the one function that already knows
    how to clamp), so this can report a number only if the canonical
    resolver already produced it — there is no second arithmetic path that
    could drift from it. Raises exactly when ``resolve_faithfulness_bars``
    raises: an unreadable row fails closed, not silently to the default."""
    effective_bars = fb.resolve_faithfulness_bars(rows)
    out = []
    for key, spec in fb.FAITHFULNESS_BARS.items():
        raw = rows.get(key)
        requested = raw.get("value") if isinstance(raw, dict) else raw
        effective = effective_bars[key]
        if key not in rows:
            status = "no config row"
        elif requested is not None and float(requested) == effective:
            status = "honoured"
        else:
            status = "CLAMPED"
        out.append({
            "key": key,
            "committed": spec.default,
            "effective": effective,
            "requested": requested,
            "status": status,
        })
    return out


def render_bar_visibility(rows: dict[str, object]) -> str:
    visibility = bar_visibility_rows(rows)
    lines = [
        "== bars in force (faithfulness_bars, imported — never restated) ==",
    ]
    width = max(len(v["key"]) for v in visibility)
    lines.append(f"{'bar'.ljust(width)}  committed  effective  status")
    for v in visibility:
        lines.append(
            f"{v['key'].ljust(width)}  {v['committed']!s:<9}  "
            f"{v['effective']!s:<9}  {v['status']}"
        )
    return "\n".join(lines)


def render_per_slice(score: FaithfulnessScore) -> str:
    lines = ["== per-slice accuracy =="]
    if not score.per_slice:
        lines.append("no slice tags present on any scored pair")
    for tag in sorted(score.per_slice):
        bucket = score.per_slice[tag]
        lines.append(
            f"{tag}: {bucket['correct']}/{bucket['n']} "
            f"({bucket['accuracy']:.3f})"
        )
    return "\n".join(lines)


# ── the cost twin: latency + tokens, honest about "not measured" ─────────


def render_cost_twin(twin: Twin | None) -> str:
    """``twin is None`` means no judge call was ever attempted — printed in
    words, never as a zero. A recent report in this repo printed its token
    columns as 0 unconditionally when nothing had run, and the adversarial
    review caught it; this is the guard against repeating that."""
    if twin is None:
        return (
            "== cost twin ==\n"
            "not measured: no judge calls were made this run (gold absent "
            "or scoring never reached the live judge)"
        )
    lines = ["== cost twin =="]
    for name, stats in sorted(twin.channels.items()):
        live, cache = stats.live, stats.cache
        lines.append(
            f"{name}: live n={live.n} p50={live.p50} p95={live.p95}; "
            f"cache n={cache.n} p50={cache.p50} p95={cache.p95}"
        )
    if not twin.tokens_by_purpose:
        lines.append("tokens: not measured (no purpose recorded usage)")
    for purpose, usage in sorted(twin.tokens_by_purpose.items()):
        lines.append(f"tokens[{purpose}]: {usage}")
    return "\n".join(lines)


# ── live judge invocation — real plumbing, dead code until real gold exists ──

DEFAULT_JUDGE = {
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1",
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
    """The judge identity for a live run. Merges per field against
    ``DEFAULT_JUDGE`` (mirroring ``run_judge_qualification.py``'s
    ``judge_purpose_config``) rather than a blanket ``{**DEFAULT_JUDGE,
    **overrides}`` — a caller passing one override (e.g. ``--model``) with
    the rest left at their argparse default of ``None`` must not have those
    explicit ``None``s stomp the other two defaults."""
    return {"verification": LLMPurposeConfig(
        model=model or DEFAULT_JUDGE["model"],
        base_url=base_url or DEFAULT_JUDGE["base_url"],
        api_key=api_key,
        api_kind=api_kind or DEFAULT_JUDGE["api_kind"],
        params=dict(params if params is not None else DEFAULT_JUDGE["params"]),
    )}


async def score_via_live_judge(
    pairs: Sequence[dict],
    base_dir: Path,
    config: dict[str, LLMPurposeConfig],
    *,
    cache_dir: str | Path = SPAN_CACHE_DIR,
    orchestrator_cls=TwinningOrchestrator,
) -> tuple[FaithfulnessScore, Twin, dict[str, ProbeVerdict]]:
    """Probe every pair through the ungated ``qualification_probe`` door —
    the measurement door, never the app-facing gated ``judge()`` — timed
    and token-counted exactly as ``run_judge_qualification.py``'s
    ``_probe_set`` does. Structurally identical shape so the two runners'
    numbers are comparable, deliberately not shared code, because the two
    gates score different gold shapes. Returns the verdicts too, so a
    caller can also compute per-answer coverage without a second pass over
    the judge."""
    llm = orchestrator_cls(config, str(cache_dir))
    judge = VerificationJudge(llm)
    recorder = LatencyRecorder()
    verdicts: dict[str, ProbeVerdict] = {}

    for pair in pairs:
        premise = build_premise(pair, base_dir)
        before = live_call_count(llm)
        started = time.perf_counter()
        verdicts[pair["id"]] = await judge.qualification_probe(premise, pair["hypothesis"])
        recorder.record(
            "judge_call", time.perf_counter() - started,
            served_by_label(before, live_call_count(llm)),
        )

    score = score_span_judgments(pairs, verdicts)
    twin = Twin.capture(recorder, llm.tokens, declared_channels=("judge_call",))
    return score, twin, verdicts
