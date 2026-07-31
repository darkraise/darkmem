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
synthetic-only (zero ``l2-fact`` premises), or not yet adjudicated (any live
``label_source == "author"``). The ``>= 1`` real-pair floor is deliberately
the minimum decodable reading — it blocks the named vector (a
grown-but-still-synthetic set) in code, while the adequacy of a barely-real
composition is T2.41's human adjudication, which is why the counts are always
surfaced (``l2-fact: 1/200``), never collapsed into a boolean.
"""
from __future__ import annotations

from dataclasses import dataclass

from benchlib import entailment_gold

from app.services.verification_judge import JUDGE_VERDICTS, ProbeVerdict

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
    if n_l2 == 0:
        reasons.append(
            f"synthetic-only gold rejected: l2-fact: {n_l2}/{n_live} "
            "(doc 17 §11; real premises land with T2.54 after T2.10)"
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
