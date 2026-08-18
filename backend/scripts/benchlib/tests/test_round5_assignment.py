"""R5, the round-5 entailed-determined premise exclusion, bites and stays inert.

The counterfactual tests run the R5 builder against the ratified ROUND-4
inputs (frame, harvest, exclusion list) -- the round-4 assignment itself is
never regenerated or altered; ``build_round4_assignment`` and its pins are
untouched. Design: docs/superpowers/plans/2026-08-14-t2.124-round5-frame-fix.md.
"""
import json
from collections import Counter

import pytest

from benchlib import entailment_assignment
from benchlib.entailment_assignment import (
    ROUND4_EXCLUDED_KEYS_PATH,
    ROUND4_FRAME_PATH,
    ROUND5_EXCLUDED_KEYS_PATH,
    ROUND5_FRAME_PATH,
    build_round4_assignment,
    build_round5_assignment,
    entailed_determined_slices,
)
from benchlib.entailment_gold import ENTAILMENT_DIR, SLICE_VERDICTS

# The 8 unanimous duplicate propositions from the step-9 blind adjudication
# (dispatch/2026-08-14-t2124-step9/, both adjudicators, all controls
# recovered). Ids only -- the premises are resolved from the gold at run time.
CONFIRMED_DUPLICATE_ID_PAIRS = (
    ("eg-0418", "eg-0554"),
    ("eg-0422", "eg-0556"),
    ("eg-0423", "eg-0557"),
    ("eg-0424", "eg-0558"),
    ("eg-0425", "eg-0559"),
    ("eg-0427", "eg-0561"),
    ("eg-0463", "eg-0590"),
    ("eg-0504", "eg-0634"),
)


@pytest.fixture(scope="module")
def round4_inputs():
    frame = json.loads(ROUND4_FRAME_PATH.read_text(encoding="utf-8"))
    excluded = set(
        json.loads(ROUND4_EXCLUDED_KEYS_PATH.read_text(encoding="utf-8"))
        ["triple_keys"]
    )
    return frame, excluded


@pytest.fixture(scope="module")
def counterfactual(round4_inputs):
    frame, excluded = round4_inputs
    return build_round5_assignment(
        frame_path=ROUND4_FRAME_PATH, frame=frame, excluded=excluded,
    )


def test_the_determined_set_derives_from_slice_verdicts():
    derived = entailed_determined_slices()
    assert derived == {"verbatim", "paraphrase", "weakening"}
    for slice_name in derived:
        assert SLICE_VERDICTS[slice_name] == frozenset({"entailed"})
    assert "temporal" not in derived  # mixed set, hand-authored exemption


def test_round5_default_inputs_do_not_exist_yet():
    """Inert by construction: the builder's default frame and exclusion
    list are round-5 chartering artifacts. When they land (after the
    sitting-1 rule ratification), this test flips and is replaced by the
    round-5 conformance suite."""
    assert not ROUND5_FRAME_PATH.exists()
    assert not ROUND5_EXCLUDED_KEYS_PATH.exists()
    with pytest.raises(FileNotFoundError):
        build_round5_assignment()


def test_counterfactual_is_deterministic_and_frame_conformant(
    round4_inputs, counterfactual,
):
    frame, excluded = round4_inputs
    again = build_round5_assignment(
        frame_path=ROUND4_FRAME_PATH, frame=frame, excluded=excluded,
    )
    assert again == counterfactual

    non_temporal = {
        s: sum(cells.values())
        for s, cells in frame["matrix"].items() if s != "temporal"
    }
    by_slice = Counter(e["slice"] for e in counterfactual)
    assert dict(by_slice) == non_temporal

    cap = 4
    usage = Counter(e["triple_key"] for e in counterfactual)
    assert max(usage.values()) <= cap
    assert not {e["triple_key"] for e in counterfactual} & excluded

    direction = Counter(
        e["reversal_class"] for e in counterfactual if e["slice"] == "direction"
    )
    assert direction["exclusive"] == frame["matrix"]["direction"]["contradicted"]
    assert direction["non-exclusive"] == frame["matrix"]["direction"]["unsupported"]


def test_no_premise_funds_two_entailed_slots(counterfactual):
    """R5 itself: at most one entailed-determined slot per premise."""
    entailed_usage = Counter(
        e["triple_key"] for e in counterfactual
        if e["slice"] in entailed_determined_slices()
    )
    assert max(entailed_usage.values()) == 1


def test_r5_would_have_excluded_a_slot_of_every_confirmed_duplicate(
    counterfactual,
):
    """The predicate bites where step 9 measured the defect: round 4's
    assignment handed every confirmed duplicate's premise two or more
    entailed slots; under R5 no premise holds two, so one slot of each
    duplicate pair is never assigned."""
    gold = json.loads((ENTAILMENT_DIR / "gold.json").read_text(encoding="utf-8"))
    pairs = {p["id"]: p for p in gold["pairs"]}
    duplicate_premises = set()
    for left, right in CONFIRMED_DUPLICATE_ID_PAIRS:
        assert pairs[left]["premise"] == pairs[right]["premise"]
        assert pairs[left]["verdict"] == pairs[right]["verdict"] == "entailed"
        duplicate_premises.add(pairs[left]["premise"])
    assert len(duplicate_premises) == 8

    entailed_slices = entailed_determined_slices()
    round4_entailed = Counter(
        e["fact"] for e in build_round4_assignment()
        if e["slice"] in entailed_slices
    )
    for premise in duplicate_premises:
        assert round4_entailed[premise] >= 2, (
            "the round-4 assignment no longer reproduces the measured "
            "collision; the counterfactual premise of this suite is broken"
        )

    round5_entailed = Counter(
        e["fact"] for e in counterfactual if e["slice"] in entailed_slices
    )
    for premise in duplicate_premises:
        assert round5_entailed[premise] <= 1


def test_direction_keeps_its_per_slice_exclusion(counterfactual):
    direction_usage = Counter(
        e["triple_key"] for e in counterfactual if e["slice"] == "direction"
    )
    assert max(direction_usage.values()) == 1


def test_the_guard_raises_on_a_mixed_entailed_bearing_manifest_slice(
    round4_inputs, monkeypatch,
):
    """If a slice drawing manifest premises ever carries `entailed` inside
    a mixed lawful set, R5 cannot determine its slots' verdicts and must
    stop loudly rather than under-exclude the way round 4 did."""
    frame, excluded = round4_inputs
    widened = dict(SLICE_VERDICTS)
    widened["paraphrase"] = frozenset({"entailed", "unsupported"})
    monkeypatch.setattr(entailment_assignment, "SLICE_VERDICTS", widened)
    with pytest.raises(RuntimeError, match="mixed"):
        build_round5_assignment(
            frame_path=ROUND4_FRAME_PATH, frame=frame, excluded=excluded,
        )


def test_infeasible_entailed_row_stops_before_assigning(round4_inputs):
    """The R5 capacity gate: more entailed slots than distinct fresh
    premises is a stop, not a silent relaxation."""
    frame, excluded = round4_inputs
    manifest = {
        "header": {"pairs_per_premise_cap": 4},
        "facts": [
            {"triple_key": f"k{i}", "rel_type": "USES", "fact": f"fact {i}"}
            for i in range(50)
        ],
    }
    with pytest.raises(RuntimeError, match="distinct"):
        build_round5_assignment(
            manifest=manifest, frame_path=ROUND4_FRAME_PATH,
            frame=frame, excluded=excluded,
        )
