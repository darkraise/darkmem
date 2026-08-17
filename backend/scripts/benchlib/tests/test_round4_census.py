"""The finished round-4 gold is pinned to the ratified frame, cell by cell.

This is the pin D5 promises ("the gold's declared counts are pinned to the
frame by test") in the only form that could exist once a gold sits at the
canonical path again: it reads both committed files and compares the live
census against ``round4_frame.json``'s matrix. A deviation absorbed through
``absorb_shortfall`` would land here as a visible red, which is the step-8
stopping rule -- composition never drifts silently.
"""
import json
from collections import Counter

from benchlib import round4_frame
from benchlib.entailment_gold import load_entailment_gold


def _live_pairs():
    return [p for p in load_entailment_gold()["pairs"] if not p.get("retired")]


def test_live_census_equals_the_frame_matrix_cell_by_cell():
    frame = json.loads(round4_frame.FRAME_PATH.read_text(encoding="utf-8"))
    cells = Counter((p["slice_tags"][0], p["verdict"]) for p in _live_pairs())
    expected = {
        (slice_name, verdict): n
        for slice_name, row in frame["matrix"].items()
        for verdict, n in row.items()
        if n
    }
    assert dict(cells) == expected


def test_live_verdict_census_equals_the_frame_census():
    frame = json.loads(round4_frame.FRAME_PATH.read_text(encoding="utf-8"))
    census = Counter(p["verdict"] for p in _live_pairs())
    assert dict(census) == frame["census"]
