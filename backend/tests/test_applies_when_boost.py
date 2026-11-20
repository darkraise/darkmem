"""The ``applies_when`` context-boost slot (doc 07 §6, doc 12 §5 contract 3).

Two rules here are hard and are never tuned: a boosted row always carries
the label explaining its boost, and context conflicts are always counted.
The magnitude that scales the boost *is* tuned — it is a ``config`` row that
Phase 2 will move, including to zero for an experiment.

So every test of the two hard rules runs across a magnitude sweep that
includes zero. A labelling test that only fires when the boost is non-zero
would stop covering anything the moment the magnitude is turned off, which
is the one setting the tuning pass is most likely to try.
"""
from __future__ import annotations

import inspect
from dataclasses import fields

import pytest
from sqlalchemy import select

from app.config import FEATURE_FLAGS_DEFAULTS
from app.models.config import Config
from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict
from app.services.rank_fusion import (
    CONFLICT_AXES,
    CONTEXT_AXES,
    CONTEXT_BOOST_FLAG,
    CONTEXT_OUTCOME_KEY,
    LIST_WEIGHT_KEYS,
    RANK_ARMS,
    ContextComposition,
    ContextMatch,
    ContextOutcome,
    ContextProvenance,
    DeclaredContext,
    RowContext,
    apply_context_boost,
    context_boost_magnitude,
    declared_context_from_wire,
    match_context,
    partition_by_context,
    rank_fusion_factor,
    row_context_from_applies_when,
    rrf_fuse,
)

# Zero first: it is the default, and it is what a Phase-2 experiment sets.
MAGNITUDES = (0.0, 0.25, 3.0)


def _weights(magnitude: float) -> dict:
    return {CONTEXT_BOOST_FLAG: magnitude}


# ── the stub for the context chain T1.42a owns ───────────────────────


class _StubContextChain:
    """Stands in for doc 12 §5's precedence chain, which is not built yet.

    The chain's only obligation to this slot is to hand it the winning raw
    declaration and its provenance — or nothing at all. It resolves
    precedence; this module resolves meaning.
    """

    def __init__(self, *, call_arg=None, header=None, project_default=None):
        self._call_arg = call_arg
        self._header = header
        self._project_default = project_default

    def resolve(self, provenance=ContextProvenance.HUMAN) -> DeclaredContext | None:
        raw = self._call_arg or self._header or self._project_default
        return declared_context_from_wire(raw, provenance)


# ── the magnitude: a config row with a stated default ────────────────


def test_magnitude_default_is_a_stated_no_op():
    assert FEATURE_FLAGS_DEFAULTS[CONTEXT_BOOST_FLAG] == 0.0
    assert context_boost_magnitude(FEATURE_FLAGS_DEFAULTS) == 0.0


@pytest.mark.asyncio
async def test_magnitude_reads_from_the_config_row(session):
    session.add(Config(key=FEATURE_FLAGS_KEY, value={CONTEXT_BOOST_FLAG: 0.4}))
    await session.flush()

    flags = await get_feature_flags_dict(session)

    assert context_boost_magnitude(flags) == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_a_tuned_magnitude_survives_a_settings_write(session):
    """The magnitude is only tunable if a settings PUT cannot silently drop it.

    The route rewrites the row as ``{k: current[k] for k in
    FEATURE_FLAGS_DEFAULTS}``, so a magnitude absent from the defaults would
    be erased the next time anyone toggled an unrelated flag.
    """
    session.add(Config(key=FEATURE_FLAGS_KEY, value={CONTEXT_BOOST_FLAG: 0.4}))
    await session.flush()

    current = await get_feature_flags_dict(session)
    stored = {k: current[k] for k in FEATURE_FLAGS_DEFAULTS if k in current}
    row = (
        await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    ).scalar_one()
    row.value = stored
    await session.flush()

    reread = await get_feature_flags_dict(session)
    assert context_boost_magnitude(reread) == pytest.approx(0.4)


def test_a_junk_magnitude_degrades_to_the_no_op():
    assert context_boost_magnitude({CONTEXT_BOOST_FLAG: None}) == 0.0
    assert context_boost_magnitude({CONTEXT_BOOST_FLAG: "wat"}) == 0.0
    assert context_boost_magnitude({}) == 0.0


# ── hard rule 1: no unlabelled boost is representable ────────────────


def test_boost_is_derived_from_the_label_not_stored_beside_it():
    """The structural half of the rule.

    If ``boost`` were a field, a later edit could set it without touching
    ``match`` and the label would stop explaining the number. It is a
    property whose only input is the verdict, so the two cannot diverge.
    """
    field_names = {f.name for f in fields(ContextOutcome)}
    assert "boost" not in field_names
    assert isinstance(inspect.getattr_static(ContextOutcome, "boost"), property)


def test_an_outcome_cannot_be_constructed_without_its_verdict():
    with pytest.raises(TypeError):
        ContextOutcome()  # type: ignore[call-arg]


def test_an_outcome_is_frozen():
    outcome = ContextOutcome(ContextMatch.MATCHED, magnitude=1.0)
    with pytest.raises(Exception):
        outcome.match = ContextMatch.NEUTRAL  # type: ignore[misc]


@pytest.mark.parametrize("magnitude", MAGNITUDES)
def test_every_surviving_row_carries_a_label_at_any_magnitude(magnitude):
    rows = [
        {"memory_id": "matching", "rrf_score": 0.01},
        {"memory_id": "unstated", "rrf_score": 0.01},
        {"memory_id": "other-axis", "rrf_score": 0.01},
    ]
    contexts = {
        "matching": row_context_from_applies_when({"env": "prod"}),
        "unstated": None,
        "other-axis": row_context_from_applies_when({"situation": "debugging"}),
    }
    declared = declared_context_from_wire({"env": "prod"})

    composed = partition_by_context(rows, declared, contexts, _weights(magnitude))

    assert len(composed.rows) == 3
    for row in composed.rows:
        outcome = row[CONTEXT_OUTCOME_KEY]
        assert isinstance(outcome, ContextOutcome)
        assert outcome.match in set(ContextMatch)
        trace = outcome.to_trace()
        assert set(trace) == {"match", "boost", "applies_when", "provenance"}
        assert trace["match"] == outcome.match.value


@pytest.mark.parametrize("magnitude", MAGNITUDES)
def test_a_boost_can_only_reach_a_score_through_a_labelled_outcome(magnitude):
    """A bare number is not a boost. There is no path from one to a score."""
    smuggled = [{"memory_id": "a", "rrf_score": 0.01, CONTEXT_OUTCOME_KEY: {"boost": 1.0 + magnitude}}]
    with pytest.raises(TypeError):
        apply_context_boost(smuggled)

    unstamped = [{"memory_id": "a", "rrf_score": 0.01, "boost": 1.0 + magnitude}]
    with pytest.raises(TypeError):
        apply_context_boost(unstamped)


@pytest.mark.parametrize("magnitude", MAGNITUDES)
def test_the_boost_a_row_receives_is_exactly_the_one_its_label_reports(magnitude):
    rows = [{"memory_id": "a", "rrf_score": 0.01}]
    contexts = {"a": row_context_from_applies_when({"env": "prod"})}
    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(magnitude),
    )

    boosted = apply_context_boost(composed.rows)
    reported = boosted[0][CONTEXT_OUTCOME_KEY].to_trace()

    assert boosted[0]["rrf_score"] == pytest.approx(0.01 * reported["boost"])
    assert reported["match"] == ContextMatch.MATCHED.value


# ── hard rule 2: conflicts are always counted ────────────────────────


@pytest.mark.parametrize("magnitude", MAGNITUDES)
def test_conflicts_are_excluded_and_counted_at_any_magnitude(magnitude):
    rows = [
        {"memory_id": "prod-row", "rrf_score": 0.02},
        {"memory_id": "dev-row", "rrf_score": 0.01},
        {"memory_id": "other-dev-row", "rrf_score": 0.01},
    ]
    contexts = {
        "prod-row": row_context_from_applies_when({"env": "prod"}),
        "dev-row": row_context_from_applies_when({"env": "dev"}),
        "other-dev-row": row_context_from_applies_when({"env": "dev"}),
    }

    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(magnitude),
    )

    assert [r["memory_id"] for r in composed.rows] == ["prod-row"]
    assert composed.excluded_by_context_conflict == 2


def test_the_count_is_identical_across_the_whole_magnitude_sweep():
    rows = [{"memory_id": "dev-row", "rrf_score": 0.01}]
    contexts = {"dev-row": row_context_from_applies_when({"env": "dev"})}
    declared = declared_context_from_wire({"env": "prod"})

    counts = {
        magnitude: partition_by_context(rows, declared, contexts, _weights(magnitude))
        .excluded_by_context_conflict
        for magnitude in (*MAGNITUDES, -1.0, 100.0)
    }
    assert set(counts.values()) == {1}


def test_counting_is_reachable_with_no_weights_at_all():
    """No flag, no magnitude, no config — the tally still happens."""
    rows = [{"memory_id": "dev-row", "rrf_score": 0.01}]
    contexts = {"dev-row": row_context_from_applies_when({"env": "dev"})}

    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, {},
    )
    assert composed.excluded_by_context_conflict == 1


def test_no_parameter_can_switch_counting_off():
    params = set(inspect.signature(partition_by_context).parameters)
    assert params == {"rows", "declared", "row_contexts", "weights"}
    assert "excluded_by_context_conflict" in {f.name for f in fields(ContextComposition)}


def test_conflict_counting_is_not_gated_by_any_feature_flag():
    """The four surviving behavioural flags stay four (doc 07, CLAUDE.md)."""
    behavioural = {
        "hybrid_search_enabled",
        "reranker_enabled",
        "relation_rescue",
        "confidence_rank_gamma",
    }
    rows = [{"memory_id": "dev-row", "rrf_score": 0.01}]
    contexts = {"dev-row": row_context_from_applies_when({"env": "dev"})}
    declared = declared_context_from_wire({"env": "prod"})

    for flag in behavioural:
        for value in (True, False, 0.0, 1.0):
            composed = partition_by_context(rows, declared, contexts, {flag: value})
            assert composed.excluded_by_context_conflict == 1, flag


# ── the three outcomes (doc 07 §6) ───────────────────────────────────


def test_a_compatible_row_matches():
    outcome = match_context(
        declared_context_from_wire({"env": "prod"}),
        row_context_from_applies_when({"env": "prod"}),
        _weights(0.5),
    )
    assert outcome.match is ContextMatch.MATCHED
    assert outcome.boost == pytest.approx(1.5)


def test_an_unstated_row_is_neutral_and_keeps_its_place():
    outcome = match_context(
        declared_context_from_wire({"env": "prod"}), None, _weights(3.0),
    )
    assert outcome.match is ContextMatch.NEUTRAL
    assert outcome.boost == 1.0
    assert outcome.to_trace()["applies_when"] is None


def test_an_llm_guessed_row_context_never_excludes_and_never_boosts():
    """Displayed provenance, not an exclusion basis (doc 01 §3.4)."""
    conflicting = match_context(
        declared_context_from_wire({"env": "prod"}),
        row_context_from_applies_when({"env": "dev"}, ContextProvenance.LLM_GUESSED),
        _weights(1.0),
    )
    assert conflicting.match is ContextMatch.NEUTRAL
    assert conflicting.to_trace()["provenance"] == "llm_guessed"
    assert conflicting.to_trace()["applies_when"] == {"env": "dev"}

    agreeing = match_context(
        declared_context_from_wire({"env": "prod"}),
        row_context_from_applies_when({"env": "prod"}, ContextProvenance.LLM_GUESSED),
        _weights(1.0),
    )
    assert agreeing.match is ContextMatch.NEUTRAL
    assert agreeing.boost == 1.0


def test_a_conflict_on_one_axis_beats_a_match_on_another():
    outcome = match_context(
        declared_context_from_wire({"env": "prod", "situation": "incident"}),
        row_context_from_applies_when({"env": "prod", "situation": "onboarding"}),
        _weights(1.0),
    )
    assert outcome.match is ContextMatch.CONFLICT


def test_a_version_difference_is_never_an_explicit_conflict():
    """``version`` is a free string compared app-side, so a difference is
    "not the same", never proof of incompatibility."""
    assert "version" in CONTEXT_AXES
    assert "version" not in CONFLICT_AXES
    outcome = match_context(
        declared_context_from_wire({"version": "15"}),
        row_context_from_applies_when({"version": "16"}),
        _weights(1.0),
    )
    assert outcome.match is ContextMatch.NEUTRAL


def test_axis_values_normalise_before_matching():
    outcome = match_context(
        declared_context_from_wire({"env": "  PROD "}),
        row_context_from_applies_when({"ENV": "prod"}),
        _weights(1.0),
    )
    assert outcome.match is ContextMatch.MATCHED


def test_an_axis_the_caller_did_not_state_cannot_conflict():
    outcome = match_context(
        declared_context_from_wire({"env": "prod"}),
        row_context_from_applies_when({"situation": "onboarding"}),
        _weights(1.0),
    )
    assert outcome.match is ContextMatch.NEUTRAL


# ── undeclared is not "declared and matched nothing" (T1.65) ─────────


def test_an_undeclared_context_is_representable_only_as_none():
    assert declared_context_from_wire(None) is None
    assert declared_context_from_wire({}) is None
    assert declared_context_from_wire({"env": "  "}) is None
    with pytest.raises(ValueError):
        DeclaredContext({})
    with pytest.raises(ValueError):
        RowContext({})


def test_undeclared_and_matched_nothing_are_distinct_facts():
    rows = [{"memory_id": "a", "rrf_score": 0.01}]
    contexts = {"a": row_context_from_applies_when({"situation": "onboarding"})}

    undeclared = partition_by_context(rows, None, contexts, _weights(1.0))
    declared_no_match = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(1.0),
    )

    assert undeclared.declared is None
    assert declared_no_match.declared == DeclaredContext({"env": "prod"})
    # Both leave every row neutral — the difference lives on the envelope,
    # which is exactly why the envelope has to carry it.
    assert undeclared.rows[0][CONTEXT_OUTCOME_KEY].match is ContextMatch.NEUTRAL
    assert declared_no_match.rows[0][CONTEXT_OUTCOME_KEY].match is ContextMatch.NEUTRAL


def test_a_declared_context_is_not_the_project_scope():
    """The isolation boundary and the context hint are different axes."""
    assert "project" not in {f.name for f in fields(DeclaredContext)}
    assert "project" not in CONTEXT_AXES
    assert declared_context_from_wire({}) is None


# ── the interface T1.42a has to honour ───────────────────────────────


def test_the_chain_stub_resolves_precedence_and_this_slot_resolves_meaning():
    chain = _StubContextChain(
        call_arg={"env": "prod"}, header={"env": "dev"}, project_default={"env": "staging"},
    )
    assert chain.resolve() == DeclaredContext({"env": "prod"})

    header_only = _StubContextChain(header={"env": "dev"}, project_default={"env": "staging"})
    assert header_only.resolve() == DeclaredContext({"env": "dev"})

    assert _StubContextChain().resolve() is None


def test_the_chain_may_declare_its_provenance():
    chain = _StubContextChain(project_default={"env": "prod"})
    guessed = chain.resolve(ContextProvenance.LLM_GUESSED)
    assert guessed is not None
    assert guessed.provenance is ContextProvenance.LLM_GUESSED


# ── post-fusion, never a ranked-list arm (doc 07 §3, §5) ─────────────


def test_the_boost_flag_is_neither_a_list_weight_nor_a_rank_arm():
    assert CONTEXT_BOOST_FLAG not in LIST_WEIGHT_KEYS
    assert CONTEXT_BOOST_FLAG not in {arm.flag for arm in RANK_ARMS}
    assert "context" not in {arm.name for arm in RANK_ARMS}


def test_the_boost_cannot_reach_the_fusion_or_the_arm_factor():
    assert set(inspect.signature(rrf_fuse).parameters) == {"lists", "limit", "key"}
    for magnitude in MAGNITUDES:
        assert rank_fusion_factor({"confidence": 0.9}, _weights(magnitude)) == 1.0


def test_a_per_row_context_cannot_move_the_fusion_order():
    rows = [
        {"memory_id": "a", "rrf_score": 0.02},
        {"memory_id": "b", "rrf_score": 0.01},
    ]
    contexts = {"b": row_context_from_applies_when({"env": "prod"})}
    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(5.0),
    )
    # The boost reorders after fusion; it never re-ran the fusion itself.
    assert [r["memory_id"] for r in composed.rows] == ["a", "b"]
    boosted = apply_context_boost(composed.rows)
    assert [r["memory_id"] for r in boosted] == ["b", "a"]


def test_a_zero_magnitude_boost_is_bit_identical_to_no_boost():
    rows = [{"memory_id": "a", "rrf_score": 0.017}]
    contexts = {"a": row_context_from_applies_when({"env": "prod"})}
    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(0.0),
    )
    boosted = apply_context_boost(composed.rows)
    assert boosted[0]["rrf_score"].hex() == (0.017).hex()


def test_a_pathological_magnitude_cannot_invert_the_order():
    outcome = ContextOutcome(ContextMatch.MATCHED, magnitude=-10.0)
    assert outcome.boost == 0.0


def test_boosting_preserves_a_reranked_order_while_rescaling():
    rows = [
        {"memory_id": "reranked-first", "rrf_score": 0.01},
        {"memory_id": "reranked-second", "rrf_score": 0.02},
    ]
    contexts = {"reranked-second": row_context_from_applies_when({"env": "prod"})}
    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(1.0),
    )

    kept = apply_context_boost(composed.rows, preserve_order=True)
    assert [r["memory_id"] for r in kept] == ["reranked-first", "reranked-second"]
    assert kept[1]["rrf_score"] == pytest.approx(0.04)

    resorted = apply_context_boost(composed.rows, preserve_order=False)
    assert [r["memory_id"] for r in resorted] == ["reranked-second", "reranked-first"]


def test_the_semantic_only_score_key_is_boosted_when_there_is_no_rrf_score():
    rows = [{"memory_id": "a", "score": 0.5}]
    contexts = {"a": row_context_from_applies_when({"env": "prod"})}
    composed = partition_by_context(
        rows, declared_context_from_wire({"env": "prod"}), contexts, _weights(1.0),
    )
    boosted = apply_context_boost(composed.rows)
    assert boosted[0]["score"] == pytest.approx(1.0)


def test_partitioning_does_not_mutate_the_caller_rows():
    rows = [{"memory_id": "a", "rrf_score": 0.01}]
    partition_by_context(rows, None, {}, _weights(1.0))
    assert rows == [{"memory_id": "a", "rrf_score": 0.01}]
