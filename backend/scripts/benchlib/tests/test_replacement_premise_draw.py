"""The repair draw's filters, pinned before the draw executes.

`replacement_premise_draw`'s whole contract is that it has no free
parameters: the premises a repair authors against are chosen mechanically and
the module lands in a commit *before* it runs, because the party running a
repair has read the review that condemned the pairs. A filter added without a
test is a free parameter with extra steps.

These cover the 2026-08-17 entailed repair's three filters. The direction
round's own pool function predates this file and is exercised by the artifacts
it produced; what is new — and what shipped a defect once already — is the
exclusion filter.
"""
from __future__ import annotations

import json

import pytest

from benchlib import replacement_premise_draw as draw
from benchlib.entailment_gold import ENTAILMENT_DIR, load_entailment_gold, load_l2_harvest


@pytest.fixture(scope="module")
def gold():
    return json.loads((ENTAILMENT_DIR / "gold.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def harvest():
    return load_l2_harvest()["facts"]


def test_the_exclusion_list_is_read_from_the_rounds_own_artifact():
    """Not recomputed. The 62 keys are a ratified input to the frame, and a
    second derivation could disagree with the one the assignment honoured."""
    keys = draw.excluded_triple_keys()
    assert len(keys) == 62
    committed = json.loads(
        (ENTAILMENT_DIR / "round4_excluded_triple_keys.json").read_text(encoding="utf-8")
    )
    assert keys == frozenset(
        committed["triple_keys"] if isinstance(committed, dict) else committed
    )


def test_no_eligible_premise_is_a_retired_harvest_one(gold, harvest):
    """Filter 1, and the whole reason this repair exists. Ten replacements were
    authored on excluded premises — five restating a published proposition in
    new words — so the repair must be unable to reproduce the defect it is
    repairing."""
    excluded = draw.excluded_triple_keys()
    pool = draw.eligible_entailed_premises(gold, harvest)

    assert pool, "an empty pool would make the assertion below vacuous"
    assert [f for f in pool if f["triple_key"] in excluded] == []


def test_no_eligible_premise_already_funds_an_entailed_slot(gold, harvest):
    """Filter 2. Load-bearing for `paraphrase` rather than tidy: a second
    paraphrase of one premise asserts the same proposition in every wording,
    which is exactly the collision the round's skip log records."""
    pool = draw.eligible_entailed_premises(gold, harvest)
    entailed_keys = {
        p.get("fact_key", {}).get("triple_key")
        for p in gold["pairs"]
        if "retired" not in p and p["verdict"] == "entailed"
    }

    assert [f for f in pool if f["triple_key"] in entailed_keys] == []


def test_retiring_frees_the_capacity_its_pairs_held(gold, harvest):
    """`retiring` is not decoration here. All ten condemned pairs are
    `entailed`, so without it filter 2 would hold their premises occupied by
    the very pairs being retired — and the draw would refuse to reuse a premise
    it has just freed. (It must not *want* to reuse them, since they are also
    excluded; this asserts the mechanism, not a licence.)"""
    from collections import Counter

    entailed = [
        p for p in gold["pairs"]
        if "retired" not in p and p["verdict"] == "entailed" and p.get("fact_key")
    ]
    # A premise funding TWO entailed slots stays occupied when one retires, and
    # round 4 has them — which is precisely the shape R5 was ratified to stop in
    # round 5. So the victim has to be a premise funding exactly one, or this
    # asserts the filter's correct refusal and calls it a bug.
    per_key = Counter(p["fact_key"]["triple_key"] for p in entailed)
    victim = next(p for p in entailed if per_key[p["fact_key"]["triple_key"]] == 1)
    key = victim["fact_key"]["triple_key"]

    without = {f["triple_key"] for f in draw.eligible_entailed_premises(gold, harvest)}
    freed = {
        f["triple_key"] for f in draw.eligible_entailed_premises(
            gold, harvest, retiring=frozenset({victim["id"]}),
            # Neutralise filter 1 so this asserts filter 2's release alone.
            excluded=frozenset(),
        )
    }

    assert key not in without
    assert key in freed


def test_the_pool_is_id_sorted_so_dict_order_cannot_move_the_draw(gold, harvest):
    pool = draw.eligible_entailed_premises(gold, harvest)
    assert [f["triple_key"] for f in pool] == sorted(f["triple_key"] for f in pool)

    shuffled = list(reversed(harvest))
    assert draw.eligible_entailed_premises(gold, shuffled) == pool


def test_the_draw_is_a_pure_function_of_the_file_and_the_count(tmp_path, gold, harvest):
    """Same bytes, same n, same premises — the property that lets a reader who
    does not trust the executor reproduce the draw from the committed file."""
    gold_path = ENTAILMENT_DIR / "gold.json"
    harvest_path = ENTAILMENT_DIR / "l2_harvest.json"

    first = draw.draw_premises(
        gold_path, harvest_path, 10, pool_fn=draw.eligible_entailed_premises
    )
    second = draw.draw_premises(
        gold_path, harvest_path, 10, pool_fn=draw.eligible_entailed_premises
    )

    assert first == second
    assert first["exhausted"] is False
    assert len(first["drawn"]) == 10
    assert first["seed"] == draw.derive_seed(gold_path)
    # And it drew from the filtered pool, not the raw harvest.
    excluded = draw.excluded_triple_keys()
    assert [d for d in first["drawn"] if d["triple_key"] in excluded] == []


def test_an_exhausted_pool_returns_a_short_draw_rather_than_inventing_one(gold, harvest):
    """Exhaustion is an outcome the skip mechanism already answers, so it is
    reported rather than raised — but it must never be reported as a draw."""
    result = draw.draw_premises(
        ENTAILMENT_DIR / "gold.json",
        ENTAILMENT_DIR / "l2_harvest.json",
        10_000,
        pool_fn=draw.eligible_entailed_premises,
    )
    assert result["exhausted"] is True
    assert result["drawn"] == []
