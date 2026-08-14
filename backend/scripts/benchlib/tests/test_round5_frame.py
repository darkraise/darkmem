"""T2.124 round-5 frame — the amendment, and the property it exists to add.

Rules 1-2 are round 4's, imported. What is new is rule 3's second gate, stated
in rows rather than uses, and these tests pin it against the round-4 inputs it
was derived from — the counterfactual, since round 5 has no artifacts yet.
"""
import json

import pytest

from benchlib import round4_frame as r4
from benchlib import round5_frame as r5
from benchlib.entailment_gold import ENTAILMENT_DIR, SLICE_VERDICTS

ROUND4_FRAME = json.loads(
    (ENTAILMENT_DIR / "round4_frame.json").read_text(encoding="utf-8")
)
ROUND4_CELLS = {s: dict(v) for s, v in ROUND4_FRAME["matrix"].items()}


def test_the_ratified_rule_is_imported_not_restated():
    """Two copies of one ratified rule is the drift this repo fails builds on.

    The diff between the rounds should be exactly the amendment, so a reviewer
    can read the amendment by reading the round-5 file.
    """
    for name in (
        "T2_25_PROPORTIONS", "T2_25_SPLITS_PINNED", "NEAR_MISS_SLICES",
        "CONTRADICTED_TARGET", "PAIRS_PER_PREMISE_CAP", "SKIP_MARGIN", "T_MIN",
    ):
        assert not hasattr(r5, name), (
            f"round5_frame defines its own {name}; it must use round4_frame's"
        )
    assert r5.r4 is r4


def test_manifest_drawing_slices_are_derived_and_exclude_only_temporal():
    drawing = r5.manifest_drawing_slices()
    assert drawing == frozenset(SLICE_VERDICTS) - {"temporal"}
    # Derived from the table, so a new slice joins without editing this module.
    assert "temporal" not in drawing
    assert {"paraphrase", "verbatim", "weakening"} <= drawing


def test_e_manifest_on_the_ratified_round_four_matrix():
    """102 of round 4's 110 entailed rows draw a manifest premise; 8 are
    temporal and hand-authored."""
    assert ROUND4_FRAME["census"]["entailed"] == 110
    assert ROUND4_CELLS["temporal"].get("entailed", 0) == 8
    assert r5.manifest_entailed(ROUND4_CELLS) == 102


def test_the_row_floor_is_the_skip_margin_applied_to_rows():
    assert r5.entailed_row_floor(102) == 128        # ceil(102 * 5/4)
    assert r5.entailed_row_floor(0) == 0
    # Same margin rule 3 already applies to uses — imported, not re-typed.
    assert r5.entailed_row_floor(4) == 5


def test_the_row_gate_is_the_binding_one_which_is_the_whole_amendment():
    """Round 4's capacity gate was blind to distinctness, and by a wide margin.

    At the ratified T = 280 it demanded 44 facts while the matrix needed 102
    distinct entailed premises. That gap is where the 8 duplicates lived.
    """
    capacity = r4.fact_floor(ROUND4_FRAME["total"])
    rows = r5.entailed_row_floor(r5.manifest_entailed(ROUND4_CELLS))
    assert capacity == 44
    assert rows == 128
    assert rows > capacity


def test_round_four_would_have_survived_its_own_amendment():
    """The amendment must not retroactively condemn the round it came from —
    that would make it a fit rather than a fix. 163 fresh facts >= 128."""
    assert 163 >= r5.entailed_row_floor(r5.manifest_entailed(ROUND4_CELLS))


def test_the_gate_stops_a_round_whose_harvest_cannot_fund_distinct_premises(monkeypatch):
    """The failing side. A harvest clearing capacity and failing rows is
    exactly the state round 4 shipped in blind."""
    monkeypatch.setattr(r5, "ROUND4_ARCHIVE_PATH", r4.RETIRED_GOLD_ARCHIVE_PATH)
    # 100 clears the use floor (44) and fails the row floor (128).
    with pytest.raises(RuntimeError, match="STOP \\(R5 rows\\)"):
        r5.derive_frame(100)


def test_a_harvest_below_even_the_use_floor_stops_earlier_and_says_so(monkeypatch):
    monkeypatch.setattr(r5, "ROUND4_ARCHIVE_PATH", r4.RETIRED_GOLD_ARCHIVE_PATH)
    with pytest.raises(RuntimeError, match="STOP \\(capacity\\)"):
        r5.derive_frame(10)


def test_a_sufficient_harvest_derives_and_reports_which_gate_bound_it(monkeypatch):
    monkeypatch.setattr(r5, "ROUND4_ARCHIVE_PATH", r4.RETIRED_GOLD_ARCHIVE_PATH)
    frame = r5.derive_frame(163)
    assert frame["census"] == ROUND4_FRAME["census"]      # rules 1-2 unchanged
    assert frame["total"] == ROUND4_FRAME["total"]
    assert frame["feasibility"]["manifest_entailed_rows"] == 102
    assert frame["feasibility"]["entailed_row_floor"] == 128
    assert frame["feasibility"]["binding_gate"] == "rows"


def test_the_guard_refuses_a_mixed_entailed_slice_it_cannot_decide(monkeypatch):
    """If a manifest slice ever offered `entailed` among other verdicts, the
    slot's verdict would stop being decidable at assignment time and R5's
    exclusion could not be applied as ratified."""
    monkeypatch.setitem(SLICE_VERDICTS, "unrelated", ("entailed", "unsupported"))
    with pytest.raises(ValueError, match="mixed"):
        r5.assert_amendment_is_expressible()


def test_round_five_is_inert_until_its_own_artifacts_exist():
    """The rule is ratified; the round is not chartered. The script must refuse
    rather than invent inputs, and the emitted frame is a new file."""
    for path in (r5.ROUND5_FRAME_PATH, r5.ROUND5_HARVEST_PATH,
                 r5.ROUND5_EXCLUDED_KEYS_PATH, r5.ROUND4_ARCHIVE_PATH):
        assert not path.exists(), f"{path} exists; round 5 has been chartered"
    assert r5.main([]) == 2
    # Never the ratified round-4 file.
    assert r5.ROUND5_FRAME_PATH.name == "round5_frame.json"
