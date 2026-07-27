"""T1.31 — the three future rank_fusion_factor arms wired at zero (doc 07 §3).

``w_importance``, ``w_heat``, and ``w_recency`` land as formula slots in
``RANK_ARMS``, each defaulting to weight 0 in the ``config`` defaults dict.
Landing them is the whole deliverable: the composed factor must be exactly
what it is today, not merely close to it, until each arm's activation task
(T2.30 for importance, T2.31 for heat/recency) turns it on.

Bit-identity is asserted with ``.hex()`` on the float, never
``pytest.approx`` — approx passes on a value that is merely close, which is
exactly what "bit-identical" excludes and the only failure mode that matters
here is an arm quietly contributing a non-1.0 factor.
"""
from __future__ import annotations

from app.config import FEATURE_FLAGS_DEFAULTS
from app.services.rank_fusion import (
    RANK_ARMS,
    RankArm,
    arm_factor,
    rank_fusion_factor,
)

FUTURE_FLAGS = ("w_importance", "w_heat", "w_recency")


# ── each arm reads its weight from config, default 0 ─────────────────


def test_future_arm_flags_are_declared_in_feature_flags_defaults():
    # Presence in the single `config` defaults dict matters, not just the
    # implicit fallback inside `_weight()`: a flag absent here can never be
    # durably set through the feature-flags API (the PUT route strips any
    # key that isn't a FEATURE_FLAGS_DEFAULTS member before storing).
    for flag in FUTURE_FLAGS:
        assert flag in FEATURE_FLAGS_DEFAULTS, f"{flag} must be a declared config default"


def test_future_arm_flags_default_to_zero():
    for flag in FUTURE_FLAGS:
        assert FEATURE_FLAGS_DEFAULTS[flag] == 0.0, flag


def test_rank_arms_flags_match_the_declared_defaults():
    arm_flags = {arm.flag for arm in RANK_ARMS if arm.name != "confidence"}
    assert arm_flags == set(FUTURE_FLAGS)


# ── labelled inert with its activation task id ────────────────────────


def test_future_arms_name_their_activation_task_id():
    by_flag = {arm.flag: arm for arm in RANK_ARMS}
    assert by_flag["w_importance"].activation == "T2.30"
    assert by_flag["w_heat"].activation == "T2.31"
    assert by_flag["w_recency"].activation == "T2.31"


def test_the_spent_arm_carries_no_activation_id():
    # Confidence is live today; an activation id on it would say a shipped
    # arm is still dormant.
    confidence_arm = next(a for a in RANK_ARMS if a.name == "confidence")
    assert confidence_arm.activation is None


def test_activation_id_is_a_field_on_the_arm_not_only_in_a_comment():
    # RankArm.activation is a real dataclass field, so any caller that reads
    # RANK_ARMS programmatically (T1.57's UI surface, a future config route)
    # can render "inactive: activates at T2.30" without parsing source. A
    # docstring-only label would be readable to a human but invisible here.
    assert "activation" in {f for f in RankArm.__dataclass_fields__}


# ── the bit-identity guard itself (Ruling 1) ──────────────────────────


def test_arms_at_zero_are_bit_identical_to_arms_absent():
    signals = {"confidence": 0.83, "importance": 0.91, "heat": 1.0, "recency": 1.0}
    absent = {"confidence_rank_gamma": 2.3}
    at_zero = {**absent, "w_importance": 0.0, "w_heat": 0.0, "w_recency": 0.0}

    confidence_only = arm_factor(RANK_ARMS[0], signals, absent)
    factor_absent = rank_fusion_factor(signals, absent)
    factor_at_zero = rank_fusion_factor(signals, at_zero)

    # pytest.approx would pass on a value merely close to confidence_only —
    # exactly the drift this guard exists to catch. .hex() compares the
    # literal IEEE-754 bit pattern.
    assert factor_absent.hex() == confidence_only.hex()
    assert factor_at_zero.hex() == confidence_only.hex()
    assert factor_at_zero.hex() == factor_absent.hex()


def test_arms_at_zero_are_bit_identical_across_every_repo_default_config():
    # The exact shape `get_feature_flags_dict` hands the pipeline when no DB
    # row overrides anything: dict(FEATURE_FLAGS_DEFAULTS).
    signals = {"confidence": 0.5, "importance": 0.5, "heat": 0.0, "recency": 0.0}
    only_confidence_key = {"confidence_rank_gamma": FEATURE_FLAGS_DEFAULTS["confidence_rank_gamma"]}

    factor_defaults = rank_fusion_factor(signals, dict(FEATURE_FLAGS_DEFAULTS))
    factor_confidence_only = rank_fusion_factor(signals, only_confidence_key)

    assert factor_defaults.hex() == factor_confidence_only.hex()
    assert factor_defaults.hex() == (1.0).hex()  # gamma is also 0 at repo defaults


def test_a_nonzero_future_weight_breaks_bit_identity():
    # The converse of the guard above: prove it actually detects a
    # contributing arm rather than being vacuously true for any input.
    signals = {"confidence": 0.5, "importance": 0.9}
    at_zero = rank_fusion_factor(signals, {"w_importance": 0.0})
    activated = rank_fusion_factor(signals, {"w_importance": 2.0})
    assert at_zero.hex() != activated.hex()
