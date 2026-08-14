"""Deterministic premise assignment for the T2.54 authoring round (Rule A).

Composition is a function of pre-judge data only: the per-slice targets are
T2.25's slice proportions scaled to 200 by largest-remainder rounding
(frozen in LABELLING.md), and the premise-to-slot assignment below is a
pure function of the committed harvest manifest and the seed recorded in
its header -- no author, and no judge, chooses which fact meets which
slice. Re-running this module re-derives the exact assignment order, so a
reviewer can check that every authored ``l2-fact`` pair sits on its
assigned slot and every deviation is a logged skip, not silent curation.

``temporal`` takes no manifest premises: ``fact_lift`` renders no validity
window into fact text (measured fact M10), so the slice's premises are
hand-authored under doc 17 §11's exemption, whose sunset tripwire lives in
``entailment_gold.load_l2_harvest``.

Run from backend/:
  python scripts/benchlib/entailment_assignment.py [--batch N]
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from benchlib.entailment_gold import SLICE_VERDICTS, load_l2_harvest  # noqa: E402

# T2.25's 41-pair slice proportions scaled to 200 by largest-remainder
# rounding, ties broken alphabetically (LABELLING.md, "Frozen composition
# for the T2.54 authoring round"). The sum is exactly 200.
NEW_PAIR_SLICE_TARGETS: dict[str, int] = {
    "verbatim": 20,
    "paraphrase": 29,
    "weakening": 24,
    "temporal": 29,
    "direction": 25,
    "overreach": 29,
    "value-swap": 24,
    "unrelated": 20,
}

# Slot batches for the four authoring dispatches: contiguous ranges over the
# assignment order below, plus the hand-authored temporal block in batch 4.
BATCH_RANGES = ((0, 50), (50, 100), (100, 150), (150, 171))


# ── T2.110 growth round (round 2) ────────────────────────────────────────
#
# Census sizing, stated before any pair existed: `contradiction_recall_bar`
# is 0.95 = 19/20, and recall resolves in steps of 1/N over the
# gold-contradicted census N. At the prior N = 55 the achievable values
# bracket the bar at 52/55 ~= 0.9455 and 53/55 ~= 0.9636 -- 0.95 is not on
# the lattice, so the operative bar was 0.9636. The bar sits on the lattice
# only when N is a multiple of 20, and the resample protocol's full-census
# stratification caps N at RESAMPLE_N = 93. The one multiple of 20 in
# (55, 93] is 80, so the growth targets a contradicted census of exactly 80
# and scales every slice proportionally (241 -> 351 by largest-remainder
# rounding of the live slice counts).
#
# The seed is derived, never chosen: the first 8 hex digits of the
# pre-growth gold.json's SHA-256 (commit 53989628, 241 live pairs). An
# author cannot re-pick it without rewriting a committed file's history,
# which is what makes the premise-to-slot assignment unaimable.
ROUND2_BASE_GOLD_SHA256 = (
    "e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df"
)
ROUND2_SEED = int(ROUND2_BASE_GOLD_SHA256[:8], 16)

# Pairs whose premise usage predates round 2: everything up to the last
# T2.54 id. Counted regardless of a later `retired` flag, so the assignment
# re-derives identically forever (append-only makes the id range immutable).
ROUND2_MAX_EXISTING_ID = "eg-0241"

ROUND2_SLICE_TARGETS: dict[str, int] = {
    "verbatim": 11,
    "paraphrase": 16,
    "weakening": 13,
    "temporal": 16,
    "direction": 14,
    "overreach": 16,
    "value-swap": 13,
    "unrelated": 11,
}


def _round2_existing_usage(gold_doc: dict) -> dict[str, int]:
    usage: dict[str, int] = {}
    for pair in gold_doc["pairs"]:
        if pair["id"] <= ROUND2_MAX_EXISTING_ID:
            usage[pair["premise"]] = usage.get(pair["premise"], 0) + 1
    return usage


def build_round2_assignment(
    manifest: dict | None = None, gold_doc: dict | None = None,
) -> list[dict]:
    """The round-2 seeded (premise x slice) assignment.

    Unlike round 1, facts start with non-zero usage, so cycling alone would
    push a thrice-used premise past the cap. The cycle therefore skips
    exhausted facts: each slot takes the next fact in the seeded order with
    remaining capacity, decrementing as it goes. Deterministic in the
    manifest, the pre-growth usage and ROUND2_SEED alone.
    """
    manifest = manifest or load_l2_harvest()
    if gold_doc is None:
        import json

        gold_path = HERE / "entailment" / "gold.json"
        gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))

    facts = manifest["facts"]
    cap = manifest["header"]["pairs_per_premise_cap"]
    usage = _round2_existing_usage(gold_doc)
    remaining = {row["triple_key"]: cap - usage.get(row["fact"], 0) for row in facts}

    rng = random.Random(ROUND2_SEED)
    slots = [
        slice_name
        for slice_name in sorted(ROUND2_SLICE_TARGETS)
        if slice_name != "temporal"
        for _ in range(ROUND2_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    if sum(max(r, 0) for r in remaining.values()) < len(slots):
        raise RuntimeError(
            f"{len(slots)} slots exceed the harvest's remaining capacity "
            "under the pairs-per-premise cap -- the harvest is too small "
            "for this growth (do not widen the cap)"
        )

    assignment = []
    cursor = 0
    for slot, slice_name in enumerate(shuffled_slots):
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] > 0:
                break
        else:
            raise RuntimeError("no fact with remaining capacity")
        remaining[row["triple_key"]] -= 1
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
        })
    return assignment


# ── T2.115 lattice-resize round (round 3) ────────────────────────────────
#
# Not a growth round: the pooled contradicted census is held at 80 while
# Rule B's second population goes 25 -> 40, so 0.95 lands on its recall
# lattice (38/40) as it already does on the pooled one (76/80). Fifteen
# contacted contradicted pairs retire under LABELLING.md's lattice-retirement
# rule and fifteen are authored to replace them, with 51 companions keeping
# the second population's contradicted base rate at the gold's own ~23%.
#
# **Two decisions the plan review required be stated rather than inferred:**
#
# 1. **Usage counts LIVE pairs only.** LABELLING.md's cap is "<= 4 **live**
#    pairs per premise", and round 2's helper counted by id threshold
#    regardless of retirement -- correct there, because nothing had retired.
#    Here fifteen pairs have, and reading the cap literally is what lets
#    their premises take a replacement. Counting them would leave capacity
#    stranded behind pairs that no longer exist.
# 2. **The seed hashes the POST-retirement file.** Step 2 moves the sha, so
#    "the file's own hash" is ambiguous between the pre- and post-retirement
#    states; either is unchooseable, and two implementers reading the same
#    sentence would otherwise derive different assignments. The state that
#    *precedes the operation this seed drives* is the post-retirement one.
# Slices whose pairs are all contradicted, or whose verdict the
# reversal-exclusivity table may make contradicted. Named by slice, never by
# pair, so the priority cannot select for difficulty.
CONTRADICTED_FIRST_SLICES = ("value-swap", "direction")

ROUND3_SLICE_TARGETS: dict[str, int] = {
    # Contradicted replacements, mirroring the retirement draw's quota.
    # **This did NOT hold in execution and the comment used to claim it did**
    # ("unchanged end to end (rule clause 5)"): authoring returned one
    # `overreach`-contradicted pair and the temporal batch was sized at 2
    # rather than 3 to keep the census at 80, moving the pooled distribution
    # (temporal 15->14, overreach 0->1). Recorded in the gate ledger as C-1,
    # awaiting owner adjudication; do not re-assert preservation here.
    "value-swap": 8,
    "direction": 4 + 4,   # 4 contradicted + 4 unsupported companions
    # Companions, largest-remainder over the live non-contradicted
    # (slice, verdict) distribution -- the **cell-level** variant.
    #
    # **This is not the variant the plan review approved, and the deviation
    # went unrecorded until 2026-08-10** (branch review I-7). Plan v2 §6,
    # written to answer the plan review's own I7, states the 51 companions as
    # the **slice-marginal** largest remainder over the same population. Both
    # were re-derived from the pre-round file:
    #
    #     slice-marginal (approved):  temporal 7 / unrelated 6
    #     cell-level     (executed):  temporal 6 / unrelated 7
    #
    # Everything else is identical, so the whole deviation is one slot moved
    # from temporal to unrelated. Both algorithms are content-blind and name
    # slices rather than pairs, so neither can select for difficulty, and the
    # precision floor sits at 0.70 against a measured 0.90.
    #
    # What is not fine is how it was chosen: by the **contaminated**
    # controller -- the one that had read the slice-level failure attribution
    # -- and committed in `48ad7e8e` *together with the authored pairs*,
    # rather than before them the way the retirement module was. That is the
    # plan review's I1 procedure-shopping channel applied to the companion
    # quota. The round's "zero degrees of freedom" claim is overstated by
    # exactly this much. Recorded rather than re-run: re-executing on the
    # approved variant is gold surgery, which moves the sha and voids the
    # certification and the spent G-D attempt.
    "overreach": 10,
    "paraphrase": 10,
    "unrelated": 7,
    "verbatim": 6,
    "weakening": 8,
    # Temporal is hand-authored (doc 17 section 11's premise exemption) and
    # takes no l2 slot. Planned 3C/3E/3U; **shipped 2C/3E/4U**, sized after
    # authoring to land the census at 80 (see C-1 in the gate ledger).
    "temporal": 9,
}


def _live_premise_usage(gold_doc: dict) -> dict[str, int]:
    """Premise usage over **live** pairs, per LABELLING.md's cap wording."""
    usage: dict[str, int] = {}
    for pair in gold_doc["pairs"]:
        if pair.get("retired"):
            continue
        usage[pair["premise"]] = usage.get(pair["premise"], 0) + 1
    return usage


def build_round3_assignment(
    manifest: dict | None = None, gold_doc: dict | None = None,
) -> list[dict]:
    """The round-3 seeded (premise x slice) assignment.

    Same capacity-aware cycle as round 2 -- each slot takes the next fact in
    the seeded order with remaining capacity -- over live usage and a seed
    derived from the post-retirement file.
    """
    import json

    manifest = manifest or load_l2_harvest()
    gold_path = HERE / "entailment" / "gold.json"
    if gold_doc is None:
        gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))

    seed = int(hashlib.sha256(gold_path.read_bytes()).hexdigest()[:8], 16)
    facts = manifest["facts"]
    cap = manifest["header"]["pairs_per_premise_cap"]
    usage = _live_premise_usage(gold_doc)
    remaining = {row["triple_key"]: cap - usage.get(row["fact"], 0) for row in facts}

    rng = random.Random(seed)
    slots = [
        slice_name
        for slice_name in sorted(ROUND3_SLICE_TARGETS)
        if slice_name != "temporal"
        for _ in range(ROUND3_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    # **The harvest is exhausted, and the shortfall is allocated by a rule
    # stated before the draw** (owner ruling 2026-08-10). Round 2 could anchor
    # every non-temporal slot; after it, 19 of this round's 57 slots have
    # capacity. LABELLING.md already has the mechanism -- a slot with no usable
    # premise takes a hand-authored one with a recorded skip, "so slice targets
    # stay exact and only the `l2-fact` count moves" -- and doc 17 section 11's
    # >= 50% l2-fact floor still holds with margin (238/402 = 59.2%). This read
    # 248/402 = 61.7% until 2026-08-10: that assumed all 19 anchored slots
    # landed, and ten of them skipped, which is the very mechanism the sentence
    # above describes. The floor holds either way; the number did not.
    #
    # Scarce capacity goes to CONTRADICTED_FIRST_SLICES before anything else:
    # those pairs are the census the gate's truth-critical bar is computed over,
    # so they are where a real minted premise is worth most. The rule is
    # content-blind -- it names slices, never pairs -- and companions then take
    # what is left in the seeded shuffled order, so which companions get anchors
    # is decided by the seed rather than by anyone.
    capacity = sum(max(r, 0) for r in remaining.values())
    priority = [
        index for index, name in enumerate(shuffled_slots)
        if name in CONTRADICTED_FIRST_SLICES
    ]
    rest = [
        index for index, name in enumerate(shuffled_slots)
        if name not in CONTRADICTED_FIRST_SLICES
    ]
    anchored = set((priority + rest)[:capacity])
    if len(priority) > capacity:
        raise RuntimeError(
            f"{len(priority)} contradicted slots exceed the harvest's remaining "
            f"capacity ({capacity}); the round cannot anchor the census it "
            "measures and the corpus must grow first (do not widen the cap)"
        )

    assignment = []
    cursor = 0
    for slot, slice_name in enumerate(shuffled_slots):
        if slot not in anchored:
            # Recorded as a capacity skip, not an infeasible-shape one.
            assignment.append({
                "slot": slot,
                "slice": slice_name,
                "triple_key": None,
                "rel_type": None,
                "fact": None,
                "premise_source": "hand-authored (harvest capacity exhausted)",
            })
            continue
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] > 0:
                break
        else:
            raise RuntimeError("no fact with remaining capacity")
        remaining[row["triple_key"]] -= 1
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
            "premise_source": "l2-fact",
        })
    return assignment


# ── T2.124 fresh-gold round (round 4) ────────────────────────────────────
#
# The frame is `entailment/round4_frame.json`, emitted by the committed
# `benchlib.round4_frame` rule and ratified in two sittings; this assignment
# is a pure function of that file, the fresh harvest manifest, and the
# round-4 premise exclusion list. The seed is the committed frame file's own
# sha256 (round 3's precedent: the hash of the committed file that precedes
# the operation this seed drives), so re-picking it means rewriting a
# committed file's history.
#
# Two exclusions the earlier rounds did not need:
#
# 1. **Old premises are out entirely** (sitting 1, item 5: full exclusion).
#    Eligible facts are the manifest rows whose triple_key is NOT in
#    `round4_excluded_triple_keys.json` -- keys, not content.
# 2. **Determined slices never reuse a premise** (the T2.115 lesson, now a
#    rule): for a slice whose hypothesis the premise determines, a premise
#    already assigned a slot of that slice is ineligible for another. The
#    ruling's own characterisation names both cases: for `direction` the
#    hypothesis *is* the reversal, and for `verbatim` it is a near-literal
#    restatement whose only freedom is word order.
#
# `direction` slots additionally carry the verdict their relation class
# determines: the frame's contradicted/unsupported split is realised by
# drawing facts from the reversal-exclusivity table's classes per quota --
# mechanical, never a per-pair judgment. Symmetric relations are ineligible
# for the slice (the reversal would be entailed), so they are never drawn
# for it rather than becoming known-infeasible skips.

ROUND4_FRAME_PATH = Path(__file__).resolve().parent / "entailment" / "round4_frame.json"
ROUND4_EXCLUDED_KEYS_PATH = (
    Path(__file__).resolve().parent / "entailment" / "round4_excluded_triple_keys.json"
)

ROUND4_FIRST_FRESH_ID = "eg-0418"

ROUND4_DETERMINED_SLICES = frozenset({"direction", "verbatim"})

# LABELLING.md's ratified reversal-exclusivity table, by class. Copied as
# data because the table is prose; the round4 tests cross-check the union
# against RELATIONSHIP_TYPES so a taxonomy widening fails loudly here.
REVERSAL_EXCLUSIVE = frozenset({
    "HAS_PART", "IMPLEMENTS", "EXTENDS", "REPLACES", "IMPROVES_ON", "IS_A",
    "DEPLOYED_ON", "AUTHORED_BY", "HAPPENED_ON",
})
REVERSAL_NON_EXCLUSIVE = frozenset({
    "USES", "DEPENDS_ON", "CAUSES", "MENTIONS", "CITES", "INSPIRED_BY",
})
REVERSAL_SYMMETRIC = frozenset({"RELATED_TO"})


def round4_seed(frame_path: str | Path = ROUND4_FRAME_PATH) -> int:
    return int(hashlib.sha256(Path(frame_path).read_bytes()).hexdigest()[:8], 16)


def build_round4_assignment(
    manifest: dict | None = None,
    frame: dict | None = None,
    excluded: set[str] | None = None,
) -> list[dict]:
    """The round-4 seeded (premise x slice) assignment.

    One entry per non-temporal slot of the frame matrix (temporal stays
    hand-authored under doc 17 section 11's exemption). Deterministic in
    the committed frame file, the fresh manifest and the exclusion list
    alone; the fresh gold starts empty, so unlike rounds 2 and 3 there is
    no prior usage to count.
    """
    import json

    manifest = manifest or load_l2_harvest()
    if frame is None:
        frame = json.loads(ROUND4_FRAME_PATH.read_text(encoding="utf-8"))
    if excluded is None:
        excluded = set(
            json.loads(ROUND4_EXCLUDED_KEYS_PATH.read_text(encoding="utf-8"))
            ["triple_keys"]
        )

    facts = [row for row in manifest["facts"] if row["triple_key"] not in excluded]
    cap = manifest["header"]["pairs_per_premise_cap"]
    remaining = {row["triple_key"]: cap for row in facts}
    used_in_slice: dict[str, set[str]] = {s: set() for s in ROUND4_DETERMINED_SLICES}

    # Slot list: slice name, plus the relation class a direction slot must
    # draw from (the frame's C/U quota realised mechanically).
    slots: list[tuple[str, frozenset | None]] = []
    for slice_name in sorted(frame["matrix"]):
        if slice_name == "temporal":
            continue
        cells = frame["matrix"][slice_name]
        if slice_name == "direction":
            slots.extend([("direction", REVERSAL_EXCLUSIVE)] * cells.get("contradicted", 0))
            slots.extend([("direction", REVERSAL_NON_EXCLUSIVE)] * cells.get("unsupported", 0))
        else:
            slots.extend([(slice_name, None)] * sum(cells.values()))

    rng = random.Random(round4_seed())
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    if sum(remaining.values()) < len(slots):
        raise RuntimeError(
            f"{len(slots)} slots exceed the fresh harvest's capacity under "
            "the pairs-per-premise cap -- the corpus must grow (do not widen "
            "the cap, do not reuse an excluded premise)"
        )

    assignment = []
    cursor = 0
    for slot, (slice_name, rel_class) in enumerate(shuffled_slots):
        chosen = None
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] <= 0:
                continue
            if rel_class is not None and row["rel_type"] not in rel_class:
                continue
            if (
                slice_name in ROUND4_DETERMINED_SLICES
                and row["triple_key"] in used_in_slice[slice_name]
            ):
                continue
            chosen = row
            break
        if chosen is None:
            raise RuntimeError(
                f"slot {slot} ({slice_name}) has no eligible fresh fact -- "
                "the harvest cannot fund this cell's quota; stop for the "
                "owner rather than relaxing an exclusion"
            )
        remaining[chosen["triple_key"]] -= 1
        if slice_name in ROUND4_DETERMINED_SLICES:
            used_in_slice[slice_name].add(chosen["triple_key"])
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "reversal_class": (
                "exclusive" if rel_class is REVERSAL_EXCLUSIVE
                else "non-exclusive" if rel_class is REVERSAL_NON_EXCLUSIVE
                else None
            ),
            "triple_key": chosen["triple_key"],
            "rel_type": chosen["rel_type"],
            "fact": chosen["fact"],
        })
    return assignment


# ── round-5 exclusion rule (T2.124 step-9 finding; inert until round 5) ──
#
# Round 4 keyed premise exclusion per SLICE (`ROUND4_DETERMINED_SLICES`),
# and step 9's blind adjudication measured what that misses: every one of
# the 8 unanimous duplicate propositions sits on a premise the assignment
# handed two entailed slots -- across slices (verbatim x paraphrase) and
# within slices never listed (paraphrase, weakening). Determination is a
# property of the VERDICT, not the slice: an entailed hypothesis must be
# licensed by its premise, and a premise licenses a narrow set of claims,
# so two blind authors converge; contradicted and unsupported hypothesis
# spaces are open, and their shared-premise candidates adjudicated distinct
# (0 of 8 groups). Design and re-ratification requirements:
# docs/superpowers/plans/2026-08-14-t2.124-round5-frame-fix.md.
#
# The rule (R5): a premise may fund at most one slot whose determined
# verdict is `entailed`, across all slices; the `direction` per-slice
# exclusion stands; `verbatim`'s old per-slice rule is subsumed. Inert by
# construction here: the default frame path does not exist until the
# round-5 frame is derived and ratified, the round-4 builder is untouched,
# and nothing calls this for round 4.

ROUND5_FRAME_PATH = Path(__file__).resolve().parent / "entailment" / "round5_frame.json"
ROUND5_EXCLUDED_KEYS_PATH = (
    Path(__file__).resolve().parent / "entailment" / "round5_excluded_triple_keys.json"
)


def entailed_determined_slices() -> frozenset[str]:
    """Slices whose lawful verdict set is exactly {entailed}, derived from
    the committed ``SLICE_VERDICTS`` table -- never listed by hand."""
    return frozenset(
        s for s, verdicts in SLICE_VERDICTS.items()
        if verdicts == frozenset({"entailed"})
    )


def round5_seed(frame_path: str | Path = ROUND5_FRAME_PATH) -> int:
    return int(hashlib.sha256(Path(frame_path).read_bytes()).hexdigest()[:8], 16)


def build_round5_assignment(
    manifest: dict | None = None,
    frame_path: str | Path = ROUND5_FRAME_PATH,
    frame: dict | None = None,
    excluded: set[str] | None = None,
) -> list[dict]:
    """The round-5 seeded (premise x slice) assignment under R5.

    Round 4's builder with one exclusion replaced: instead of per-slice
    determined sets for {direction, verbatim}, a premise is ineligible for
    a second slot whose determined verdict is `entailed`, whatever the
    slice. The frame document and the seed both come from ``frame_path``
    (round 3's precedent: the committed file preceding the operation), so
    the counterfactual tests can run this rule against the ratified round-4
    inputs without touching the round-4 builder.
    """
    import json

    manifest = manifest or load_l2_harvest()
    if frame is None:
        frame = json.loads(Path(frame_path).read_text(encoding="utf-8"))
    if excluded is None:
        excluded = set(
            json.loads(ROUND5_EXCLUDED_KEYS_PATH.read_text(encoding="utf-8"))
            ["triple_keys"]
        )

    entailed_slices = entailed_determined_slices()
    for slice_name in frame["matrix"]:
        if slice_name == "temporal":
            continue
        lawful = SLICE_VERDICTS[slice_name]
        if "entailed" in lawful and slice_name not in entailed_slices:
            raise RuntimeError(
                f"slice {slice_name!r} draws manifest premises with a mixed "
                f"entailed-bearing verdict set {sorted(lawful)} -- R5 cannot "
                "determine its slots' verdicts at assignment time; stop for "
                "a rule amendment rather than under-excluding silently"
            )

    facts = [row for row in manifest["facts"] if row["triple_key"] not in excluded]
    cap = manifest["header"]["pairs_per_premise_cap"]
    remaining = {row["triple_key"]: cap for row in facts}
    used_entailed: set[str] = set()
    used_direction: set[str] = set()

    slots: list[tuple[str, frozenset | None]] = []
    for slice_name in sorted(frame["matrix"]):
        if slice_name == "temporal":
            continue
        cells = frame["matrix"][slice_name]
        if slice_name == "direction":
            slots.extend([("direction", REVERSAL_EXCLUSIVE)] * cells.get("contradicted", 0))
            slots.extend([("direction", REVERSAL_NON_EXCLUSIVE)] * cells.get("unsupported", 0))
        else:
            slots.extend([(slice_name, None)] * sum(cells.values()))

    entailed_slot_count = sum(1 for name, _ in slots if name in entailed_slices)
    if entailed_slot_count > len(facts):
        raise RuntimeError(
            f"{entailed_slot_count} entailed slots need that many distinct "
            f"premises under R5 and the fresh harvest holds {len(facts)} -- "
            "the corpus must grow (do not widen the cap, do not relax the "
            "exclusion)"
        )
    if sum(remaining.values()) < len(slots):
        raise RuntimeError(
            f"{len(slots)} slots exceed the fresh harvest's capacity under "
            "the pairs-per-premise cap -- the corpus must grow (do not widen "
            "the cap, do not reuse an excluded premise)"
        )

    rng = random.Random(round5_seed(frame_path))
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    assignment = []
    cursor = 0
    for slot, (slice_name, rel_class) in enumerate(shuffled_slots):
        chosen = None
        for _ in range(len(facts)):
            row = facts[fact_order[cursor % len(facts)]]
            cursor += 1
            if remaining[row["triple_key"]] <= 0:
                continue
            if rel_class is not None and row["rel_type"] not in rel_class:
                continue
            if slice_name in entailed_slices and row["triple_key"] in used_entailed:
                continue
            if slice_name == "direction" and row["triple_key"] in used_direction:
                continue
            chosen = row
            break
        if chosen is None:
            raise RuntimeError(
                f"slot {slot} ({slice_name}) has no eligible fresh fact -- "
                "the harvest cannot fund this cell's quota; stop for the "
                "owner rather than relaxing an exclusion"
            )
        remaining[chosen["triple_key"]] -= 1
        if slice_name in entailed_slices:
            used_entailed.add(chosen["triple_key"])
        if slice_name == "direction":
            used_direction.add(chosen["triple_key"])
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "reversal_class": (
                "exclusive" if rel_class is REVERSAL_EXCLUSIVE
                else "non-exclusive" if rel_class is REVERSAL_NON_EXCLUSIVE
                else None
            ),
            "triple_key": chosen["triple_key"],
            "rel_type": chosen["rel_type"],
            "fact": chosen["fact"],
        })
    return assignment


def l2_eligible_slices() -> list[str]:
    return sorted(s for s in NEW_PAIR_SLICE_TARGETS if s != "temporal")


def build_assignment(manifest: dict | None = None) -> list[dict]:
    """The seeded (premise x slice) assignment: one entry per non-temporal
    slot, in the shuffled order the seed derives. Facts cycle in a seeded
    order, so usage stays within the pairs-per-premise cap whenever
    ``ceil(slots / facts) <= cap`` -- asserted, not assumed."""
    manifest = manifest or load_l2_harvest()
    facts = manifest["facts"]
    header = manifest["header"]
    rng = random.Random(header["assignment_seed"])

    slots = [
        slice_name
        for slice_name in l2_eligible_slices()
        for _ in range(NEW_PAIR_SLICE_TARGETS[slice_name])
    ]
    shuffled_slots = rng.sample(slots, len(slots))
    fact_order = rng.sample(range(len(facts)), len(facts))

    max_usage = -(-len(slots) // len(facts))
    if max_usage > header["pairs_per_premise_cap"]:
        raise RuntimeError(
            f"{len(slots)} slots over {len(facts)} facts needs {max_usage} "
            f"pairs on some premise, above the cap "
            f"{header['pairs_per_premise_cap']} -- the harvest is too small "
            "for this composition (blocker B2 territory; do not widen the cap)"
        )

    assignment = []
    for slot, slice_name in enumerate(shuffled_slots):
        row = facts[fact_order[slot % len(facts)]]
        assignment.append({
            "slot": slot,
            "slice": slice_name,
            "triple_key": row["triple_key"],
            "rel_type": row["rel_type"],
            "fact": row["fact"],
        })
    return assignment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--batch", type=int, default=None,
        help=f"print only authoring batch 1..{len(BATCH_RANGES)} (round 1)",
    )
    parser.add_argument(
        "--round", type=int, default=1, choices=(1, 2),
        help="1 = the T2.54 authoring round, 2 = the T2.110 growth round",
    )
    args = parser.parse_args(argv)

    assignment = build_assignment() if args.round == 1 else build_round2_assignment()
    if args.batch is not None:
        start, end = BATCH_RANGES[args.batch - 1]
        assignment = assignment[start:end]
    for entry in assignment:
        print(
            f"{entry['slot']:3d}  {entry['slice']:<10}  "
            f"{entry['rel_type']:<12}  {entry['fact']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
