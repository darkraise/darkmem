"""G-E's bars, pinned by value — the two-file-diff rule.

The v0.4 branch review found the corpus share stated in the gate ledger and
pinned by nothing at all: a bar that lives only in prose can be moved by
editing the prose, which is the one thing the ledger's own rule forbids.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
for path in (str(BACKEND), str(BACKEND / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from benchlib.coverage_bars import COVERAGE_BAR_DEFAULTS  # noqa: E402


def test_the_threshold_is_the_truth_critical_side_of_the_rule():
    """Doc 17 §6 bars the truth-critical metric at 0.95. Pinned *against* 0.90
    for the same reason the contradiction-recall bar is: 0.90 is where this
    would sit if coverage were re-read as not truth-critical, which is the one
    move that could lower it without arguing the number itself."""
    assert COVERAGE_BAR_DEFAULTS["article_coverage_threshold"] == 0.95
    assert COVERAGE_BAR_DEFAULTS["article_coverage_threshold"] != 0.90


def test_the_corpus_share_is_the_other_side():
    """An article below the threshold is handled — withheld and routed to
    review — so the share prices viability, not truth."""
    assert COVERAGE_BAR_DEFAULTS["article_coverage_corpus_share"] == 0.90


def test_the_threshold_is_the_one_the_runtime_enforces():
    """A probe measuring a threshold the running system does not apply would
    report against a bar nobody enforces. One number, two readers."""
    from app.services.claim_entailment import DEFAULT_COVERAGE_THRESHOLD

    assert (
        COVERAGE_BAR_DEFAULTS["article_coverage_threshold"]
        == DEFAULT_COVERAGE_THRESHOLD
    )
