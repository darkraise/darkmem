"""G-E's bars, stated and committed before any measurement runs.

The same discipline `promotion_bars` holds for G-C, and for the same reason:
a bar written after seeing the number is not a bar, and a default edited to
fit a result is the same thing one file over. Both values below were derived
from doc 17 §6's rule and owner-ratified on 2026-08-11, at a moment when no
coverage number had ever been produced anywhere in this corpus — the
entailment pass refuses without a qualified judge, and G-D is open — so
fitting them was impossible rather than merely avoided.

**Two numbers, answering different questions.**

`article_coverage_threshold` is the **per-article** routing bar the running
system already applies: an article at or above it may carry the grounded
label, one below it goes to review. Its home is
`app.services.claim_entailment.DEFAULT_COVERAGE_THRESHOLD` over the
`article_coverage` config row, and it is pinned there by the suite that owns
that module. It is restated here because G-E's distribution probe is defined
*against* it, and a probe whose threshold could drift from the runtime's
would be measuring a bar nobody enforces.

`article_coverage_corpus_share` is **G-E's own** bar and has no runtime
consumer: the share of live articles that must sit at or above the threshold
for the layer to count as shipped. T3.24's runner is what will read it.

**Why they sit on opposite sides of doc 17 §6's rule.** The truth-critical
metric is barred at 0.95 and the other at 0.90. Coverage is truth-critical —
a false pass ships a fluent ungrounded sentence under a corroborated badge,
the worst failure in the maintainer's ordering — so the threshold takes 0.95.
The corpus share is not: an article below the threshold is *handled*, withheld
from the corroborated view and routed to review, so the share prices whether
the layer is viable enough to ship rather than whether a reader can be misled.
It takes 0.90.

Neither may be moved to make a run pass. Both are the owner's to move with a
recorded argument, and `tests/test_coverage_bars.py` pins each by value so
moving one is a visible two-file diff rather than a quiet constant tweak.
"""

from __future__ import annotations

COVERAGE_BAR_DEFAULTS: dict[str, float] = {
    # Truth-critical side of doc 17 §6's rule. Mirrors — and is pinned equal
    # to — `claim_entailment.DEFAULT_COVERAGE_THRESHOLD`, which is what the
    # running system enforces per article.
    "article_coverage_threshold": 0.95,
    # The non-truth-critical side. G-E's own bar; nothing enforces it at
    # runtime, and nothing has measured it.
    "article_coverage_corpus_share": 0.90,
}

__all__ = ["COVERAGE_BAR_DEFAULTS"]
