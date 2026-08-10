"""Truth-first content fill under a token budget (T3.10, doc 15 §3.4).

Turns a composed F3 selection into the ``list[str]`` that
:func:`app.services.inject_block.render_block` takes. This module adds a
**budget** and a **layer priority** and nothing else — doc 15 §3.1 reserves
ranking to the composition, and inject "adds a transport and a budget".

**Regrouping by layer IS a reorder** of ``compose``'s interleaved
``(band, -tier, key)`` order, and it is the one reorder doc 15 §3.4 owns.
Order *within* a layer stays exactly as composition left it.

**The label path is the part that matters.** Labels are read off
``ComposedRow.labels``, which ``compose`` already produced through
``fact_badge.row_labels``/``claim_gates.served_status``. ``row_labels`` is
never called here — ``layer_composition._badge_labels``'s docstring forbids a
second label-assembly site — and ``ComposedRow.verification_status`` is never
read for anything emitted: it is the raw rung wrapped in
``claim_gates.unserved_status``, a written declaration that no reader receives
it. Rendering it would put an ungated ``corroborated`` into text a model reads
while G-C is open.

Plan and its review rounds:
``docs/superpowers/plans/2026-08-11-t3.10-truth-first-inject-fill.md``.
"""
from dataclasses import dataclass, field
from typing import Any, Mapping

from app.services.inject_block import MARKER_BEGIN, MARKER_END
from app.services.layer_composition import ComposedResult, ComposedRow

__all__ = ["HEADER_RESERVE", "FillResult", "estimate_tokens", "fill"]

# Truth-first: L2 verified facts, then L3 servable articles, then L0 memory
# summaries (doc 15 §3.4).
LAYER_ORDER: tuple[str, ...] = ("L2", "L3", "L0")

# `render_block` emits a provenance header and joins items with newlines, and
# the fill never sees either. The header is ~65-75 chars (~22-25 estimator
# tokens at the divisor below), but the newlines scale with item count, so a
# constant sized to the header alone runs short at realistic item counts — 64
# plus the per-item newline counted in `_spend` covers both.
HEADER_RESERVE = 64


def estimate_tokens(text: str) -> int:
    """Estimator tokens for ``text``.

    A heuristic that **under-counts punctuation-dense text**, which is most of
    what lands here: badge claims, entity names, code identifiers and dates cut
    nearer 2.5-3.5 chars per token under a real BPE tokenizer. The budget is
    therefore exact only in estimator units, and is a soft bound whose job is
    keeping the block small — not a promise about any vendor's count.

    This repo ships no tokenizer and adding one is a dependency decision, so
    the approximation is deliberate and lives in exactly one function: swapping
    a real tokenizer in later is a one-line change.
    """
    return -(-len(text) // 3)


@dataclass(frozen=True)
class FillResult:
    """The items plus what the caller owes its journal.

    ``inject_journal.record_inject`` takes ``tokens_used``; returning a bare
    list would force the caller to re-estimate with a second authority or
    journal ``None``.
    """

    items: list[str]
    tokens_used: int
    per_layer: dict[str, int] = field(default_factory=dict)
    dropped_markers: int = 0


def _labels(row: ComposedRow) -> Mapping[str, Any]:
    return row.labels or {}


def _claim(labels: Mapping[str, Any]) -> str | None:
    """The badge's own sentence, or ``None`` when the gate withheld it.

    A ``badge`` key that is *absent* is the ``compose(badges=None)`` path — a
    caller that never assembled badges — and raises. A badge that is present
    and ``None`` is **suppression**: ``row_labels`` drops the badge whenever
    the serving boundary withholds the status, because the sentence names the
    corroboration the status was withheld for. The two must not read alike, or
    the gate working becomes indistinguishable from a bug.
    """
    badge = labels["badge"]
    return None if badge is None else badge["claim"]


def _render(row: ComposedRow) -> str | None:
    """One item's line, or ``None`` when the row has nothing servable."""
    labels = _labels(row)
    if row.id_kind == "memory":
        summary = (row.row or {}).get("summary")
        if not summary:
            # Classification can leave a memory with no digest. The budget
            # cannot afford full prose (doc 15 §3.4), and falling back to
            # `content` would spend it on exactly what the summary exists to
            # avoid — so the row is skipped rather than substituted.
            return None
        lifecycle = labels.get("lifecycle")
        tail = f" [{lifecycle}]" if lifecycle else ""
        return f"- (L0 memory{tail}) {summary}"

    served = labels.get("verification_status")
    claim = _claim(labels)
    if claim is None:
        # Suppressed: render the served status and the reason, never a claim
        # sentence. There is no claim to render, and inventing one is the
        # over-claim the suppression exists to prevent.
        return f"- ({row.layer} {served}, withheld: {labels.get('label_suppressed')})"
    return f"- ({row.layer} {served}) {claim}"


def _is_verified(row: ComposedRow) -> bool:
    """The **served** verdict, never the raw rung."""
    return _labels(row).get("unverified") is False


def _carries_marker(text: str) -> bool:
    return MARKER_BEGIN in text or MARKER_END in text


def fill(result: ComposedResult, *, token_budget: int) -> FillResult:
    """Budget-bounded, truth-first items for the managed block.

    Cold start (doc 15 §3.4): the primary pass admits an L2 row only when its
    served labels say verified. If nothing verified lands, the pass runs once
    more with candidates admitted — under the *same* budget, so a cold-start
    block is never an over-budget block.
    """
    budget = max(0, token_budget - HEADER_RESERVE)

    landed = _pass(result.rows, budget, verified_only=True)
    if not any(count for layer, count in landed.per_layer.items() if layer == "L2"):
        cold = _pass(result.rows, budget, verified_only=False)
        if cold.items:
            return cold
    return landed


def _pass(rows: list[ComposedRow], budget: int, *, verified_only: bool) -> FillResult:
    items: list[str] = []
    per_layer = {layer: 0 for layer in LAYER_ORDER}
    spent = 0
    dropped = 0

    for layer in LAYER_ORDER:
        for row in rows:
            if row.layer != layer:
                continue
            if layer == "L2" and verified_only and not _is_verified(row):
                continue
            text = _render(row)
            if text is None:
                continue
            if _carries_marker(text):
                # `render_block` refuses an embedded marker, and darkmem stores
                # memories about darkmem — one such row would fail every
                # session-start inject until it rotated out of the selection.
                # This is a safety exclusion, not the size-based scan-on the
                # budget rule forbids.
                dropped += 1
                continue
            cost = estimate_tokens(text) + 1  # the newline `render_block` joins on
            if spent + cost > budget:
                # Stop rather than scanning on for something smaller: that
                # would silently reorder by size, a ranking this module may
                # not invent.
                return FillResult(items, spent, per_layer, dropped)
            items.append(text)
            per_layer[layer] += 1
            spent += cost

    return FillResult(items, spent, per_layer, dropped)
