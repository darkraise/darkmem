"""T2.26 — the `verification`-purpose judge: probe, parsing, bars, and (Task 2+)
the computed qualification gate and its source scans."""
import json
import logging

import pytest

from app.models.config import Config
from app.services.extraction_clean import _content_seed
from app.services import verification_judge as vj


class StubLLM:
    """Minimal orchestrator stand-in: records every chat_completion call's
    arguments and replays canned responses in order."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, purpose, messages, response_format=None, seed=None):
        self.calls.append({
            "purpose": purpose,
            "messages": messages,
            "response_format": response_format,
            "seed": seed,
        })
        return self.responses.pop(0)


# ── probe + parsing ──────────────────────────────────────────────────────


@pytest.mark.parametrize("verdict", ["entailed", "contradicted", "unsupported"])
async def test_probe_parses_each_lawful_verdict(verdict):
    llm = StubLLM([json.dumps({"verdict": verdict, "reason": "because"})])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p is true", "h follows")
    assert result.valid is True
    assert result.verdict == verdict
    assert result.reason == "because"


@pytest.mark.parametrize("raw", [
    '{"verdict": "supported", "reason": "untabled verdict"}',
    "this is not json at all",
    "",
])
async def test_probe_never_raises_on_malformed_output(raw):
    llm = StubLLM([raw])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is False
    assert result.verdict is None
    assert result.raw == raw


async def test_probe_fallback_accepts_a_bare_verdict_token():
    llm = StubLLM(["The verdict is: contradicted"])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is True
    assert result.verdict == "contradicted"


async def test_probe_fallback_rejects_ambiguous_multi_token_output():
    llm = StubLLM(["either entailed or unsupported, hard to say"])
    judge = vj.VerificationJudge(llm)
    result = await judge.qualification_probe("p", "h")
    assert result.valid is False
    assert result.verdict is None


# ── call construction ────────────────────────────────────────────────────


async def test_probe_dispatches_on_the_verification_purpose_with_seed():
    llm = StubLLM([json.dumps({"verdict": "entailed", "reason": "r"})])
    judge = vj.VerificationJudge(llm)
    premise, hypothesis = "Postgres runs on 5433", "Postgres is reachable"
    await judge.qualification_probe(premise, hypothesis)

    call = llm.calls[0]
    assert call["purpose"] == "verification"
    assert call["response_format"] == {"type": "json_object"}
    assert call["seed"] == _content_seed(premise + "\n" + hypothesis)


def test_messages_are_byte_stable_for_the_same_pair():
    first = vj.build_messages("p text", "h text")
    second = vj.build_messages("p text", "h text")
    assert first == second
    assert first[0]["role"] == "system"
    assert first[1]["role"] == "user"
    assert "p text" in first[1]["content"]
    assert "h text" in first[1]["content"]


def test_system_prompt_names_all_three_verdicts():
    for token in ("entailed", "contradicted", "unsupported"):
        assert f'"{token}"' in vj.SYSTEM_PROMPT


def test_verdict_vocabulary_is_the_gold_three():
    # app/ must not import benchlib, so the set is declared here; the drift
    # guard against entailment_gold.VERDICTS lives in the benchlib suite.
    assert vj.JUDGE_VERDICTS == frozenset({"entailed", "contradicted", "unsupported"})


# ── bars: config rows over stated defaults ───────────────────────────────


RECALL_BAR = "contradiction_recall_bar"


def _state_the_recall_bar(session, value=0.95):
    """T2.109 barred contradiction-recall with no default, so every test that
    wanted a resolvable bar set had to state it. The bar has carried a default
    since 2026-08-08, so the row is now the same act a deployment performs
    rather than the thing that makes the set resolvable — and since T2.126 it
    states the bar at its floor, because a row below the floor clamps."""
    session.add(Config(key=RECALL_BAR, value={"value": value}))


def test_bar_defaults_are_the_stated_values():
    assert vj.VERIFICATION_BAR_DEFAULTS == {
        # Truth-critical metrics at 0.95, the other at 0.90 — doc 17 §6's rule,
        # which predates every judge run. The amendment moved which
        # contradiction metric is truth-critical; it did not move the rule.
        "groundedness_gate_precision_bar": 0.95,
        "groundedness_gate_recall_bar": 0.90,
        "contradiction_recall_bar": 0.95,
        # Not a truth number since 2026-08-08: a review-load floor.
        "contradiction_precision_bar": 0.70,
    }


def test_contradiction_recall_is_gated_and_barred_by_derivation():
    """Doc 17 §6's 2026-08-08 amendment plus the bars stated under it.

    Recall is barred (so it cannot be ignored) at **0.95**, the value the
    section's own rule gives the truth-critical metric — the rule predates
    every judge run, and the amendment is what made recall truth-critical.

    The second assertion is the one that matters. 0.90 is where a bar chosen
    to clear the measured judge would sit: gpt-5.5 scored contradiction-recall
    0.945, so 0.90 passes it and 0.95 does not. Pinning *against* that value
    is how this file records that the bar was derived rather than fitted.
    """
    assert vj.BAR_METRICS[RECALL_BAR] == "contradiction_recall"
    assert vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR] == 0.95
    assert vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR] != 0.90


def test_contradiction_precision_is_a_review_load_floor_not_a_truth_bar():
    """It moved 0.95 -> 0.70 because its consumer changed, not because it was
    missed. A false flag now costs a reviewer a minute rather than a wrong
    belief, so the bar only has to keep the queue workable — noise a clear
    minority. Left at 0.95 it would price precision as truth after §6 stopped
    doing so, and block the gate for a reason unrelated to being right."""
    assert vj.VERIFICATION_BAR_DEFAULTS["contradiction_precision_bar"] == 0.70


async def test_bars_fall_back_to_defaults_on_an_empty_config_table(session):
    bars = await vj.get_verification_bars(session)
    assert bars == vj.VERIFICATION_BAR_DEFAULTS


async def test_an_unstated_bar_raises_rather_than_resolving(session, monkeypatch):
    """The mechanism, exercised on a barred key that genuinely has no default.

    It used to be exercised on `contradiction_recall_bar`, which was unstated
    by design until 2026-08-08. Stating that bar would have retired this guard
    silently — the mechanism is for *any* future barred metric, not for that
    one, so it is tested against a synthetic key instead.
    """
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    with pytest.raises(ValueError, match="a_future_bar"):
        await vj.get_verification_bars(session)


async def test_a_db_bar_row_wins_per_key(session):
    # A *tightening* row: since T2.126 the loosening direction is the clamp's,
    # and testing "DB wins" with a loosened value would test the escape hatch
    # instead of the merge.
    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 0.96}))
    _state_the_recall_bar(session)
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["groundedness_gate_recall_bar"] == 0.96
    assert bars["groundedness_gate_precision_bar"] == 0.95
    assert bars["contradiction_precision_bar"] == 0.70


async def test_a_bare_scalar_bar_row_is_also_read(session):
    session.add(Config(key="contradiction_precision_bar", value=0.97))
    session.add(Config(key=RECALL_BAR, value=0.99))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["contradiction_precision_bar"] == 0.97
    assert bars[RECALL_BAR] == 0.99


async def test_a_malformed_bar_row_raises_not_silently_defaults(session):
    # Falling back to the default would ignore an operator's attempt to
    # move a bar — conservative relative to defaults, not to intent.
    session.add(Config(key="groundedness_gate_precision_bar", value={"value": "0.99"}))
    _state_the_recall_bar(session)
    await session.commit()
    with pytest.raises(ValueError, match="groundedness_gate_precision_bar"):
        await vj.get_verification_bars(session)


# ── T2.126: the defaults are floors, and a licence is the only way under ─


LOOSENINGS = [
    ("groundedness_gate_precision_bar", 0.90),
    ("groundedness_gate_recall_bar", 0.80),
    ("contradiction_precision_bar", 0.50),
    ("contradiction_recall_bar", 0.90),
]

TIGHTENINGS = [
    ("groundedness_gate_precision_bar", 0.99),
    ("groundedness_gate_recall_bar", 0.96),
    ("contradiction_precision_bar", 0.85),
    ("contradiction_recall_bar", 1.0),
]

LEDGER_CITATION = "gate-ledger.md, 'G-D redesign'"


def _licence(session, entries):
    session.add(Config(key=vj.VERIFICATION_BAR_LICENCES_KEY,
                       value={"licensed": entries}))


@pytest.mark.parametrize("key,loosened", LOOSENINGS)
async def test_every_bar_clamps_an_unlicensed_loosening(
    session, caplog, key, loosened
):
    """All four clamp, not just the one the implementer was thinking about.

    A one-bar clamp would leave `contradiction_recall_bar` — the truth-critical
    one, and the number three G-D runs failed against — movable by the config
    write this task exists to close.
    """
    session.add(Config(key=key, value={"value": loosened}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[key] == vj.VERIFICATION_BAR_DEFAULTS[key]
    assert key in caplog.text
    assert vj.VERIFICATION_BAR_LICENCES_KEY in caplog.text, (
        "the warning must name what is missing, or the operator cannot tell "
        "why their value was ignored"
    )


@pytest.mark.parametrize("key,tightened", TIGHTENINGS)
async def test_every_bar_honours_a_tightening_row(session, caplog, key, tightened):
    """The negative control. A clamp that also caught tightenings would pin
    every bar to its default and read as working."""
    session.add(Config(key=key, value={"value": tightened}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[key] == tightened
    assert "clamping" not in caplog.text


@pytest.mark.parametrize("key,floor", sorted(vj.VERIFICATION_BAR_DEFAULTS.items()))
async def test_a_row_exactly_at_the_floor_is_honoured_not_clamped(
    session, caplog, key, floor
):
    session.add(Config(key=key, value={"value": floor}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[key] == floor
    assert "clamping" not in caplog.text


async def test_the_floor_is_the_shipped_default_itself_not_a_second_mapping(
    session, monkeypatch
):
    """Moving a default must move its floor with it — one statement of "what
    ships" and "what may not be gone below", so the two cannot drift."""
    monkeypatch.setitem(vj.VERIFICATION_BAR_DEFAULTS, "contradiction_precision_bar", 0.60)
    session.add(Config(key="contradiction_precision_bar", value={"value": 0.65}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["contradiction_precision_bar"] == 0.65


async def test_a_barred_metric_with_no_default_has_no_floor(
    session, monkeypatch, caplog
):
    """Nothing to have been lowered from: the row is the only statement of
    that number, and the unstated-bar rule already governs stating it."""
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    session.add(Config(key="a_future_bar", value={"value": 0.01}))
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars["a_future_bar"] == 0.01
    assert "clamping" not in caplog.text


async def test_no_licence_row_licenses_nothing(session):
    assert await vj.get_verification_bar_licences(session) == {}


async def test_a_licence_naming_the_parameter_honours_the_loosening(session):
    session.add(Config(key=RECALL_BAR, value={"value": 0.90}))
    _licence(session, {RECALL_BAR: {"value": 0.90, "argument": LEDGER_CITATION}})
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[RECALL_BAR] == 0.90


@pytest.mark.asyncio
@pytest.mark.parametrize("bound", [0, 0.0, -0.1, 1.5])
async def test_a_licence_outside_the_bar_range_licenses_nothing(session, caplog, bound):
    """A licence of zero or below unlocks its parameter outright *and
    silently* — no candidate can fall below it, so the out-of-bound warning
    that would otherwise fire never does. A bound that bounds nothing is the
    one shape this design exists not to be. Above 1.0 is incoherent for a
    [0,1] metric and refused on the same terms."""
    session.add(Config(key=vj.VERIFICATION_BAR_LICENCES_KEY, value={
        "licensed": {"contradiction_recall_bar": {
            "value": bound, "argument": "gate-ledger.md, 'G-D ruling'"}},
    }))
    session.add(Config(key="contradiction_recall_bar", value=0.10))
    await session.flush()

    with caplog.at_level(logging.WARNING):
        bars = await vj.get_verification_bars(session)

    assert bars["contradiction_recall_bar"] == vj.VERIFICATION_BAR_DEFAULTS[
        "contradiction_recall_bar"
    ], "an incoherent licence must leave the bar at its floor"
    assert "not a bar value" in caplog.text


@pytest.mark.asyncio
async def test_a_licence_at_the_ceiling_is_admitted_and_inert(session):
    """1.0 is coherent and licenses no loosening any floor would refuse, so it
    is admitted rather than refused — the guard rejects incoherence, not
    values it merely considers pointless."""
    session.add(Config(key=vj.VERIFICATION_BAR_LICENCES_KEY, value={
        "licensed": {"contradiction_recall_bar": {
            "value": 1.0, "argument": "gate-ledger.md, 'G-D ruling'"}},
    }))
    await session.flush()

    licences = await vj.get_verification_bar_licences(session)
    assert licences["contradiction_recall_bar"] == 1.0


async def test_a_licence_bounds_how_far_the_bar_may_move(session, caplog):
    """The anti-ratchet property, and the reason the licence states a value.

    A licence that unlocked *whatever the bar row says* would be the bar row
    licensing itself with one extra hop: written once, it would bless every
    later loosening. So a value below what the argument was recorded as
    supporting clamps to the floor — not to the licensed value, which would
    adopt a number the operator never wrote.
    """
    session.add(Config(key=RECALL_BAR, value={"value": 0.60}))
    _licence(session, {RECALL_BAR: {"value": 0.90, "argument": LEDGER_CITATION}})
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[RECALL_BAR] == vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR]
    assert "lowest licensed value 0.9;" in caplog.text


async def test_permission_is_per_parameter_not_row_presence(session):
    """A reader treating the licence row's existence as permission passes
    every single-parameter test above; only a mixed row catches it."""
    session.add(Config(key=RECALL_BAR, value={"value": 0.90}))
    session.add(Config(key="groundedness_gate_precision_bar", value={"value": 0.90}))
    _licence(session, {RECALL_BAR: {"value": 0.90, "argument": LEDGER_CITATION}})
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[RECALL_BAR] == 0.90, "the licensed parameter must be honoured"
    assert bars["groundedness_gate_precision_bar"] == 0.95, (
        "the unlicensed parameter must still clamp"
    )


@pytest.mark.parametrize("entry,missing", [
    ({"value": 0.90}, "argument"),
    ({"value": 0.90, "argument": "   "}, "argument"),
    ({"value": 0.90, "argument": ""}, "argument"),
    ({"argument": LEDGER_CITATION}, "value"),
    ({"value": "0.90", "argument": LEDGER_CITATION}, "value"),
    # bool is an int subclass, so `False` would read as a licence down to 0.0 —
    # a total unlock of that bar, and the one malformed value whose damage is
    # not the same as clamping.
    ({"value": False, "argument": LEDGER_CITATION}, "value"),
    ("licensed", "value"),
])
async def test_a_malformed_licence_entry_licenses_nothing(
    session, caplog, entry, missing
):
    session.add(Config(key=RECALL_BAR, value={"value": 0.90}))
    _licence(session, {RECALL_BAR: entry})
    await session.commit()
    bars = await vj.get_verification_bars(session)
    assert bars[RECALL_BAR] == vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR]
    assert missing in caplog.text


@pytest.mark.parametrize("row_value", [
    {"licensed": "*"},
    {"licensed": True},
    {"licensed": [RECALL_BAR]},
    {"measured": [RECALL_BAR]},
    "*",
])
async def test_no_blanket_shape_unlocks_a_bar(session, caplog, row_value):
    """The fail-open shape: a row that reads as "everything is licensed".

    Each of these is a plausible operator guess at the schema (including the
    ladder's own `measured` list, which is the nearest neighbour), and every
    one of them must license nothing rather than everything.
    """
    session.add(Config(key=RECALL_BAR, value={"value": 0.90}))
    session.add(Config(key=vj.VERIFICATION_BAR_LICENCES_KEY, value=row_value))
    await session.commit()
    assert await vj.get_verification_bar_licences(session) == {}
    bars = await vj.get_verification_bars(session)
    assert bars[RECALL_BAR] == vj.VERIFICATION_BAR_DEFAULTS[RECALL_BAR]
    assert vj.VERIFICATION_BAR_LICENCES_KEY in caplog.text


async def test_a_licence_for_an_unbarred_key_is_ignored(session, caplog):
    _licence(session, {"promotion_rate_floor": {"value": 0.1, "argument": "x"}})
    await session.commit()
    assert await vj.get_verification_bar_licences(session) == {}
    assert "promotion_rate_floor" in caplog.text


# ── R1: the roles, their bars, and the two tripwires (2026-08-12) ────────


def test_the_roles_partition_the_barred_metrics():
    """Symmetry, machine-checked: every barred metric enters exactly one
    role's gate.

    A bar in **no** role gates nothing, which is a quietly weaker instrument
    than the one before the split; a bar in **both** re-couples the two roles
    through the back door, which is the split undone. Neither can be spotted by
    reading a passing test suite, so the partition is asserted rather than
    intended.
    """
    assigned = [key for keys in vj.JUDGE_ROLES.values() for key in keys]
    assert sorted(assigned) == sorted(set(assigned)), "a bar gates two roles"
    assert set(assigned) == set(vj.BAR_METRICS), (
        "the role bar tuples and BAR_METRICS have drifted apart"
    )
    assert vj.JUDGE_ROLES[vj.ENTAILMENT_ROLE] == (
        "groundedness_gate_precision_bar", "groundedness_gate_recall_bar",
    )
    assert vj.JUDGE_ROLES[vj.CONTRADICTION_ROLE] == (
        "contradiction_precision_bar", "contradiction_recall_bar",
    )
    # Every role-keyed table covers every role. A role missing from one of them
    # would read as "this role owes no disclosure" or "this role has no record",
    # both of which are quieter than they should be.
    assert set(vj.ROLE_REQUIRED_DISCLOSURES) == set(vj.JUDGE_ROLES)
    assert set(vj.QUALIFICATION_RECORD_PATHS) == set(vj.JUDGE_ROLES)


async def test_a_role_is_gated_on_its_own_bars_and_not_the_others(
    session, tmp_path,
):
    """The split's behavioural content, in the direction a revert would break.

    One measurement, two verdicts: a judge that discriminates entailment
    perfectly and contradiction near not at all qualifies the entailment role
    and not the contradiction role, and the mirror case holds the other way.
    Restoring the bar loop to sweep all four bars — the pre-amendment shape —
    reddens both halves.
    """
    cfg = _judge_config()
    _state_the_recall_bar(session)
    await session.commit()

    entailment_only = {
        "entailed_precision": 1.0,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1 / 55,
    }
    entailment_record = _write_record(tmp_path / "a", _record(
        cfg, metrics=dict(entailment_only), role=vj.ENTAILMENT_ROLE,
    ))
    assert (await vj.qualification_state(
        session, cfg, role=vj.ENTAILMENT_ROLE, record_path=entailment_record,
    )).qualified is True

    contradiction_only = {
        "entailed_precision": 0.10,
        "entailed_recall": 0.10,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }
    contradiction_record = _write_record(tmp_path / "b", _record(
        cfg, metrics=dict(contradiction_only), role=vj.CONTRADICTION_ROLE,
    ))
    assert (await vj.qualification_state(
        session, cfg, role=vj.CONTRADICTION_ROLE, record_path=contradiction_record,
    )).qualified is True


async def test_a_role_naming_an_undeclared_bar_fails_closed(
    session, tmp_path, monkeypatch,
):
    """The enforcement path stays total. A role tuple naming a bar the judge
    does not declare is a mistake, and a consumer call must refuse rather than
    raise a KeyError out of the gate."""
    monkeypatch.setitem(
        vj.JUDGE_ROLES, vj.ENTAILMENT_ROLE,
        vj.JUDGE_ROLES[vj.ENTAILMENT_ROLE] + ("a_bar_nobody_declared",),
    )
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path,
    )
    assert state.qualified is False
    assert any("does not declare" in r for r in state.reasons)


def test_each_role_is_gated_on_the_discrimination_its_consumer_makes():
    """The derivation's premise, stated as data.

    The entailment consumer branches on `entailed` and gates on the entailed
    pair; the contradiction consumer branches on `contradicted` and gates on
    the contradiction pair. The consumer scan below proves the branching half
    against the parsed source; this pins the mapping the scan compares against.
    """
    assert vj.ROLE_VERDICTS == {
        vj.ENTAILMENT_ROLE: "entailed",
        vj.CONTRADICTION_ROLE: "contradicted",
    }
    assert set(vj.ROLE_VERDICTS) == set(vj.JUDGE_ROLES)
    assert set(vj.ROLE_VERDICTS.values()) <= vj.JUDGE_VERDICTS
    for role, verdict in vj.ROLE_VERDICTS.items():
        gated = {vj.BAR_METRICS[bar] for bar in vj.JUDGE_ROLES[role]}
        assert all(metric.startswith(("entailed", "contradiction")) for metric in gated)
        stem = "entailed" if verdict == "entailed" else "contradiction"
        assert all(metric.startswith(stem) for metric in gated), (
            f"the {role!r} role is gated on metrics that do not measure "
            f"{verdict!r}, which is the pairing R1 exists to undo"
        )


def test_tripwire_the_contradiction_roles_bars_were_not_relaxed():
    """**R1's first post-hoc tripwire, from the spec: the split is proven a
    fit if the contradiction role's bars are later relaxed.**

    The ratification rests on one distinction — re-cutting *to scope* rather
    than *to pass* — and the evidence for it is that the failed bar never
    moved. A later relaxation would retroactively convert the split into the
    third attempt the owner ruled it was not, so it fails the build here rather
    than being noticed in a review.

    Both values are the owner's to move with a recorded argument; moving one
    means editing this test, which is the visible diff that argument needs. The
    0.95 is pinned *against* 0.90 for the same reason it always was: a bar
    fitted to the measured judge (contradiction-recall 0.945) would sit there.
    """
    for bar_key in vj.JUDGE_ROLES[vj.CONTRADICTION_ROLE]:
        assert bar_key in vj.BAR_METRICS
        assert bar_key in vj.VERIFICATION_BAR_DEFAULTS
    assert vj.VERIFICATION_BAR_DEFAULTS["contradiction_recall_bar"] == 0.95
    assert vj.VERIFICATION_BAR_DEFAULTS["contradiction_recall_bar"] != 0.90
    assert vj.VERIFICATION_BAR_DEFAULTS["contradiction_precision_bar"] == 0.70


def test_tripwire_the_retired_pair_set_is_refused_for_every_role():
    """**R1's second post-hoc tripwire: the split is proven a fit if it is used
    to license another model attempt on pair set `4975c5cc`.**

    The predicate is role-blind on purpose. A per-role reading of the stopping
    rule — "those pairs are spent for the contradiction role, so the entailment
    role may sit on them once" — is the single most available misuse of this
    amendment, and it is refused in code rather than in prose.
    """
    retired = next(iter(vj.RETIRED_PAIR_SETS))
    assert retired.startswith("4975c5cc")
    assert vj.is_retired_pair_set(retired)
    assert vj.is_retired_pair_set(retired[:8]), "the abbreviated form must match"
    assert vj.is_retired_pair_set(retired.upper()), "case must not evade it"
    assert not vj.is_retired_pair_set("b" * 64)
    assert not vj.is_retired_pair_set(None)
    assert not vj.is_retired_pair_set("4975c5c")  # shorter than a prefix


@pytest.mark.parametrize("role", sorted(vj.JUDGE_ROLES))
async def test_a_record_on_the_retired_pair_set_qualifies_no_role(
    session, tmp_path, role,
):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(
        cfg, role=role, gold_pairs_sha256=next(iter(vj.RETIRED_PAIR_SETS)),
    ))
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=role, record_path=path,
    )
    assert state.qualified is False
    assert any("retired pair set" in r for r in state.reasons)


@pytest.mark.parametrize("role", sorted(vj.JUDGE_ROLES))
async def test_a_record_that_names_no_pair_set_fails_closed(session, tmp_path, role):
    """Provenance is not optional on the one artifact that opens a gate: a
    record that does not say which pairs produced it cannot be checked against
    the retired sets at all."""
    cfg = _judge_config()
    record = _record(cfg, role=role)
    record.pop("gold_pairs_sha256")
    path = _write_record(tmp_path, record)
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=role, record_path=path,
    )
    assert state.qualified is False
    assert any("gold_pairs_sha256" in r for r in state.reasons)


async def test_an_entailment_record_must_disclose_the_leak_cell(session, tmp_path):
    """The cost R1 incurs, made enforceable rather than aspirational.

    Contradiction-recall >= 0.95 was the only bar bounding contradicted pairs
    judged `entailed` — the ones that ship contradicted material under a
    grounded badge. After the split nothing bounds that cell, so an entailment
    record that does not at least *state* it fails closed.
    """
    cfg = _judge_config()
    metrics = {
        "entailed_precision": 1.0,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }
    path = _write_record(tmp_path, _record(cfg, metrics=dict(metrics)))
    _state_the_recall_bar(session)
    await session.commit()
    assert (await vj.qualification_state(
        session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path,
    )).qualified is True

    silent = _record(cfg, metrics=dict(metrics))
    silent["metrics"].pop(vj.LEAK_DISCLOSURE_METRIC)
    silent_path = tmp_path / "silent.json"
    silent_path.write_text(json.dumps(silent), encoding="utf-8")
    state = await vj.qualification_state(
        session, cfg, role=vj.ENTAILMENT_ROLE, record_path=silent_path,
    )
    assert state.qualified is False
    assert any(vj.LEAK_DISCLOSURE_METRIC in r for r in state.reasons)


async def test_a_barred_metric_in_no_role_fails_every_role_closed(
    session, tmp_path, monkeypatch,
):
    """The runtime half of the partition pin.

    A future barred metric added to ``BAR_METRICS`` and to no role's tuple
    would gate nothing at all — a strictly weaker instrument than before the
    split, arrived at by omission. It fails closed instead, on the same posture
    an unstated bar has.
    """
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    monkeypatch.setitem(vj.VERIFICATION_BAR_DEFAULTS, "a_future_bar", 0.5)
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path,
    )
    assert state.qualified is False
    assert any("belong to no judge role" in r for r in state.reasons)


async def test_an_unknown_role_raises_rather_than_reading_a_record(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    with pytest.raises(ValueError, match="unknown judge role"):
        await vj.qualification_state(
            session, cfg, role="faithfulness", record_path=path,
        )


# ── qualification state: computed, never remembered (Task 2) ─────────────


def _judge_config(**overrides):
    from app.config import LLMPurposeConfig
    fields = {
        "model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-test",
        "api_kind": "deepseek",
        "params": {"temperature": 0, "max_tokens": 256, "thinking": {"type": "disabled"}},
    }
    fields.update(overrides)
    return {"verification": LLMPurposeConfig(**fields)}


def _record(llm_config, metrics=None, gate_eligible=True,
            role=vj.ENTAILMENT_ROLE, **extra):
    identity = vj.judge_identity(llm_config["verification"])
    base_metrics = {
        "entailed_precision": 1.0,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }
    if metrics is not None:
        base_metrics = dict(metrics)
    # The disclosure an entailment-role record owes (R1): the confusion cell
    # nothing bounds any more. Defaulted here so every unrelated test states a
    # lawful record; the tests that care about the disclosure pass it away.
    base_metrics.setdefault(vj.LEAK_DISCLOSURE_METRIC, 0)
    payload = {
        "role": role,
        "judge_identity": {**identity, "identity_hash": vj.judge_identity_hash(identity)},
        "metrics": base_metrics,
        "gate_eligible": gate_eligible,
        "gold_sha256": "0" * 64,
        "gold_pairs_sha256": "a" * 64,
        "ledger_run_id": "test-run",
        "recorded_at": "2026-07-31T00:00:00+00:00",
        "git_sha": "deadbeef",
    }
    payload.update(extra)
    return payload


def _write_record(tmp_path, payload):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"verification_qualification.{payload.get('role')}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


async def test_no_record_means_unqualified(session, tmp_path):
    state = await vj.qualification_state(
        session, _judge_config(), role=vj.ENTAILMENT_ROLE,
        record_path=tmp_path / "absent.json",
    )
    assert state.qualified is False
    assert any("no qualification record" in r for r in state.reasons)


async def test_a_malformed_record_fails_closed(session, tmp_path):
    path = tmp_path / "verification_qualification.json"
    path.write_text("{not json", encoding="utf-8")
    state = await vj.qualification_state(session, _judge_config(), role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False


async def test_gate_ineligible_record_is_unqualified(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, gate_eligible=False))
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("gate_eligible" in r for r in state.reasons)


async def test_a_matching_clearing_record_qualifies(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is True
    assert state.reasons == ()


async def test_an_unstated_bar_fails_closed_naming_it(session, tmp_path, monkeypatch):
    """The posture the malformed-bar-row test already establishes, applied to
    any barred metric with no value: the module fails loud rather
    than defaulting, and the reason says which number is missing so an operator
    is not left guessing at a gate that will not open."""
    monkeypatch.setitem(vj.BAR_METRICS, "a_future_bar", "some_metric")
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("a_future_bar" in r and "failing closed" in r for r in state.reasons)


async def test_the_gate_cannot_qualify_a_near_mute_judge(session, tmp_path):
    """The incoherence that forced doc 08 §4.2's redesign, asserted here.

    Measured against the shipped scorer on 2026-08-08: a judge emitting
    ``contradicted`` on exactly one correct pair of the gold's 55 and
    ``unsupported`` everywhere else scores contradiction-precision 1.0, leaves
    entailed precision/recall untouched, and passed all three then-gated bars
    at contradiction-recall 1/55 = 0.0182 — qualifying a judge that finds
    nothing to hold an absolute veto.

    Every metric below except the recall is the near-mute judge's *best* case,
    so nothing but the new bar can be what refuses it. Removing
    ``contradiction_recall_bar`` from ``BAR_METRICS`` — or from the
    contradiction role's bar tuple — reddens this test.

    **Asked as the contradiction role since the 2026-08-12 split**, which
    sharpens the assertion rather than weakening it: on this same record the
    near-mute judge now *passes* the entailment role, because it never
    misclassifies an entailed pair. The veto's role is the one that has to
    refuse it, and that is the role the veto's consumer asks as.
    """
    cfg = _judge_config()
    metrics = {
        "entailed_precision": 1.0,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1 / 55,
    }
    path = _write_record(tmp_path, _record(
        cfg, metrics=metrics, role=vj.CONTRADICTION_ROLE,
    ))
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=vj.CONTRADICTION_ROLE, record_path=path,
    )
    assert state.qualified is False
    assert any("contradiction_recall" in r for r in state.reasons)


async def test_a_model_swap_is_detected_not_remembered(session, tmp_path):
    path = _write_record(tmp_path, _record(_judge_config()))
    swapped = _judge_config(model="deepseek-v4-pro")
    state = await vj.qualification_state(session, swapped, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("identity" in r for r in state.reasons)


async def test_metrics_below_the_default_bar_are_unqualified(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 0.94,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("groundedness_gate_precision_bar" in r for r in state.reasons)


async def test_raising_a_db_bar_flips_a_qualified_record_back(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 1.0,
        "entailed_recall": 0.95,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is True

    session.add(Config(key="groundedness_gate_recall_bar", value={"value": 1.0}))
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False


async def test_lowering_a_db_bar_cannot_qualify_a_record_the_floor_refuses(
    session, tmp_path
):
    """T2.126 through the enforcement path, which is the only place it counts.

    The clamp is not a property of the reader — a record measuring 0.92 against
    a 0.95 floor must stay unqualified after an operator writes 0.90, and the
    refusal must still cite the floor, not the row.
    """
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 0.92,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    session.add(Config(key="groundedness_gate_precision_bar", value={"value": 0.90}))
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("groundedness_gate_precision_bar=0.95" in r for r in state.reasons)


async def test_a_licensed_loosening_does_reach_the_enforcement_path(
    session, tmp_path
):
    """The escape hatch is real rather than decorative — which is what makes
    the clamp a discipline on how a bar moves and not a freeze."""
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics={
        "entailed_precision": 0.92,
        "entailed_recall": 1.0,
        "contradiction_precision": 1.0,
        "contradiction_recall": 1.0,
    }))
    session.add(Config(key="groundedness_gate_precision_bar", value={"value": 0.90}))
    _licence(session, {"groundedness_gate_precision_bar": {
        "value": 0.90, "argument": LEDGER_CITATION,
    }})
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is True


@pytest.mark.parametrize("metrics", [
    {"entailed_recall": 1.0, "contradiction_precision": 1.0,
     "contradiction_recall": 1.0},                                         # absent
    {"entailed_precision": None, "entailed_recall": 1.0,
     "contradiction_precision": 1.0, "contradiction_recall": 1.0},         # None
])
async def test_missing_or_null_metrics_fail_closed(session, tmp_path, metrics):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg, metrics=metrics))
    _state_the_recall_bar(session)
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("entailed_precision" in r for r in state.reasons)


async def test_unreadable_bars_fail_the_qualification_closed(session, tmp_path):
    cfg = _judge_config()
    path = _write_record(tmp_path, _record(cfg))
    session.add(Config(key="groundedness_gate_recall_bar", value="not-a-number"))
    await session.commit()
    state = await vj.qualification_state(session, cfg, role=vj.ENTAILMENT_ROLE, record_path=path)
    assert state.qualified is False
    assert any("failing closed" in r for r in state.reasons)


# ── the gated door ───────────────────────────────────────────────────────


def _point_role_record(monkeypatch, role, path):
    monkeypatch.setitem(vj.QUALIFICATION_RECORD_PATHS, role, path)


@pytest.mark.parametrize("role", sorted(vj.JUDGE_ROLES))
async def test_judge_refuses_when_unqualified(session, tmp_path, monkeypatch, role):
    _point_role_record(monkeypatch, role, tmp_path / "absent.json")
    llm = StubLLM([json.dumps({"verdict": "entailed", "reason": "r"})])
    llm.config = _judge_config()
    judge = vj.VerificationJudge(llm)
    with pytest.raises(vj.JudgeNotQualifiedError):
        await judge.judge(session, "p", "h", role=role)
    assert llm.calls == []


async def test_judge_answers_when_qualified(session, tmp_path, monkeypatch):
    llm = StubLLM([json.dumps({"verdict": "contradicted", "reason": "r"})])
    llm.config = _judge_config()
    path = _write_record(tmp_path, _record(llm.config))
    _point_role_record(monkeypatch, vj.ENTAILMENT_ROLE, path)
    _state_the_recall_bar(session)
    await session.commit()
    judge = vj.VerificationJudge(llm)
    result = await judge.judge(session, "p", "h", role=vj.ENTAILMENT_ROLE)
    assert result.valid is True
    assert result.verdict == "contradicted"


async def test_one_roles_record_never_opens_the_other_role(
    session, tmp_path, monkeypatch,
):
    """The split's whole content, asserted at the door rather than the record.

    A minted, clearing record for one role must not admit a consumer asking as
    the other — otherwise the entailment record a fresh gold is expected to
    produce would silently re-arm the Tier-C scan, whose role the stopping rule
    leaves unqualified.
    """
    llm = StubLLM([json.dumps({"verdict": "contradicted", "reason": "r"})])
    llm.config = _judge_config()
    path = _write_record(tmp_path, _record(llm.config))
    _point_role_record(monkeypatch, vj.ENTAILMENT_ROLE, path)
    _point_role_record(monkeypatch, vj.CONTRADICTION_ROLE, tmp_path / "absent.json")
    _state_the_recall_bar(session)
    await session.commit()

    judge = vj.VerificationJudge(llm)
    assert (await judge.judge(session, "p", "h", role=vj.ENTAILMENT_ROLE)).valid
    with pytest.raises(vj.JudgeNotQualifiedError):
        await judge.judge(session, "p", "h", role=vj.CONTRADICTION_ROLE)


async def test_a_records_role_is_checked_not_only_its_location(
    session, tmp_path, monkeypatch,
):
    """Copying one role's record onto the other's path qualifies nothing.

    Without this the split is a filename convention: the file that opens the
    entailment gate would open the contradiction gate too, one `cp` away, and
    the numbers inside it were never measured against that role's bars.
    """
    cfg = _judge_config()
    entailment_record = _record(cfg, role=vj.ENTAILMENT_ROLE)
    copied = tmp_path / "copied-onto-the-contradiction-path.json"
    copied.write_text(json.dumps(entailment_record), encoding="utf-8")
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=vj.CONTRADICTION_ROLE, record_path=copied,
    )
    assert state.qualified is False
    assert any("names role" in r for r in state.reasons)


@pytest.mark.parametrize("role", sorted(vj.JUDGE_ROLES))
async def test_a_pre_split_bundled_record_qualifies_no_role(
    session, tmp_path, monkeypatch, role,
):
    """The migration hazard, closed in the direction that matters.

    A pre-amendment record carries all four metrics and names no role. Read as
    "whatever role you asked for", it would qualify the contradiction role from
    an artifact whose contradiction bar was never the thing that cleared —
    which is exactly the outcome the ruling refused. It qualifies nothing.
    """
    cfg = _judge_config()
    bundled = _record(cfg)
    bundled.pop("role")
    path = tmp_path / "verification_qualification.json"
    path.write_text(json.dumps(bundled), encoding="utf-8")
    _state_the_recall_bar(session)
    await session.commit()

    state = await vj.qualification_state(
        session, cfg, role=role, record_path=path,
    )
    assert state.qualified is False
    assert any("pre-amendment bundle" in r for r in state.reasons)


def test_the_gated_door_accepts_no_record_path_and_demands_a_role():
    # A caller-supplied record path would reopen the rehearsal-record bypass
    # one level above the writer's minting lock: a --gate rehearsal may
    # legitimately write a qualifying record from an easy gold to any
    # non-default path, and a consumer pointing the door at it would run as
    # qualified with nothing flagging it. Only the canonical, minting-locked
    # record may qualify a consumer call.
    #
    # `role` is keyword-only with no default: a consumer that does not name the
    # discrimination it makes must not inherit whichever record happens to
    # exist, which is what a defaulted role would give it.
    import inspect
    signature = inspect.signature(vj.VerificationJudge.judge)
    assert list(signature.parameters) == [
        "self", "session", "premise", "hypothesis", "role",
    ]
    role = signature.parameters["role"]
    assert role.kind is inspect.Parameter.KEYWORD_ONLY
    assert role.default is inspect.Parameter.empty


# ── identity: what moves the hash, and what must not ─────────────────────


def test_api_key_never_affects_the_identity():
    a = vj.judge_identity(_judge_config()["verification"])
    b = vj.judge_identity(_judge_config(api_key="sk-rotated")["verification"])
    assert vj.judge_identity_hash(a) == vj.judge_identity_hash(b)


def test_prompt_version_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    # Relative to whatever the current version is, not a literal: pinning "2"
    # here made this test pass only while the shipped version was 1, and it
    # went red the first time the prompt was legitimately revised.
    monkeypatch.setattr(vj, "JUDGE_PROMPT_VERSION", vj.JUDGE_PROMPT_VERSION + 1)
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_system_prompt_text_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", vj.SYSTEM_PROMPT + " ")
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


def test_prompt_sha_separates_the_two_texts(monkeypatch):
    # sha256(system + template) without a separator would let text migrate
    # across the boundary while keeping the hash.
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", "AB")
    monkeypatch.setattr(vj, "USER_TEMPLATE", "C")
    moved_boundary = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "SYSTEM_PROMPT", "A")
    monkeypatch.setattr(vj, "USER_TEMPLATE", "BC")
    assert moved_boundary != vj.judge_identity_hash(
        vj.judge_identity(_judge_config()["verification"])
    )


def test_user_template_text_moves_the_identity(monkeypatch):
    before = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    monkeypatch.setattr(vj, "USER_TEMPLATE", vj.USER_TEMPLATE + " ")
    after = vj.judge_identity_hash(vj.judge_identity(_judge_config()["verification"]))
    assert before != after


@pytest.mark.parametrize("role", sorted(vj.JUDGE_ROLES))
def test_the_canonical_records_are_absent_on_this_branch(role):
    """The zero-pin, per role, and this IS the deliberate diff it demanded.

    Only a gate-eligible `--gate` run may mint a record, so the first
    appearance of one had to be a change that consciously edits this test.
    T2.125 is that appearance (2026-08-17): `gpt-5.5` on T2.124's fresh gold
    cleared both bars gating the **entailment** role — precision 0.9906 against
    0.95, recall 0.9545 against 0.90, on both Rule-B populations — so that
    record now exists and is asserted rather than forbidden.

    **The contradiction role stays absent, and that is the load-bearing half.**
    Its recall measured 0.7875 against an unmoved 0.95, the fourth such miss
    across two vendors (0.7937 / 0.8814 / 0.8875 / 0.7875). The 2026-08-12
    ruling holds: the bar does not move, the role stays NOT CLEARED, and the
    Tier-C scan stays dead. A record appearing here for `contradiction` without
    a cleared run is the failure this pin exists for.
    """
    import json

    path = vj.qualification_record_path(role)
    if role == "contradiction":
        assert not path.exists(), (
            "a contradiction-role record exists; its bar has never been met, so "
            "nothing may have minted this"
        )
        return

    assert path.exists(), "T2.125 minted the entailment record; see the ledger"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["role"] == "entailment"
    assert record["gate_eligible"] is True
    # It qualifies against ONE pair set, and carries that set's content hash.
    # The cross-check against the live gold lives in the benchlib suite, where
    # `pairs_content_hash` is importable — `benchlib` is not on the path here.
    assert len(record["gold_pairs_sha256"]) == 64
    int(record["gold_pairs_sha256"], 16)
    # Only the two bars that gate this role, never the contradiction pair.
    assert set(record["bars_gating_this_role"]) == {
        "groundedness_gate_precision_bar",
        "groundedness_gate_recall_bar",
    }


def test_the_pre_split_bundled_record_path_is_not_resurrected():
    # A pre-amendment bundle qualified every consumer at once. Nothing reads
    # that path any more and nothing may start: a file left there is inert, and
    # an author reaching for the old module constant gets a red test rather
    # than a working bypass.
    bundled = (
        vj.qualification_record_path(vj.ENTAILMENT_ROLE).parent
        / "verification_qualification.json"
    )
    assert not bundled.exists()
    assert not hasattr(vj, "QUALIFICATION_RECORD_PATH")


# ── source scans: one door to the purpose, and off the hot path ──────────

import re as _re  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_BACKEND = _Path(__file__).resolve().parent.parent

# The exact quoted token, single- or double-quoted. Matching the token itself
# (not a same-line co-occurrence with chat_completion) is what closes the
# two-line bypass: PURPOSE = "verification" / chat_completion(PURPOSE, msgs).
# Identifier substrings (verification_status, verification_recompute) carry
# no closing quote after "verification" and cannot match.
_QUOTED_VERIFICATION = _re.compile(r"""["']verification["']""")

# The only modules under app/ where the quoted purpose token is lawful today.
# Extend ONLY with a written justification here — never by loosening the
# match rule. (app/config.py was verified to carry no quoted token; it is
# deliberately NOT pre-opened.)
_QUOTED_TOKEN_ALLOWLIST = {
    "app/services/verification_judge.py",   # the judge itself
    "app/services/llm_seed.py",             # the purpose seed row
    "app/services/config.py",               # PURPOSES + get_llm_config defaults
}

# Modules that may reference the judge module or its ungated probe. A consumer
# joins here consciously — and must use judge(), never the probe. For the one
# member below that is re-proved against the parsed tree by
# `test_the_ungated_probe_is_unreachable` and
# `test_the_only_adjudicating_call_is_the_gated_door`, both in
# tests/test_contradiction_scan.py.
_JUDGE_REFERENCE_ALLOWLIST = {
    "app/services/verification_judge.py",
    # T2.11's Tier-C contradiction scan: the first consumer, and gated by the
    # judge's own refusal rather than by this list.
    "app/services/contradiction_scan.py",
    # T3.02's review-queue articles arm. It imports `article_claim_gate` — the
    # judge's *qualification-record* accessor — and never the purpose, the
    # probe or `judge()`. It is here rather than exempted because the reason
    # the single door exists is that two modules must not decide whether the
    # judge is qualified: the queue asks this module and serves the answer, so
    # the door is honoured rather than bypassed. `test_the_article_gate_reads_
    # the_record_and_never_the_purpose` below re-proves the narrow form against
    # the parsed tree, the way the contradiction scan's membership is re-proved.
    "app/services/review_queue.py",
    # T3.06's articles read door, on exactly the same terms as the review
    # queue's arm above and for the same reason: it serves a rung, so it must
    # ask the one door whether the rung may be served. It imports
    # `article_claim_gate` and nothing else — re-proved narrowly below beside
    # the queue's.
    "app/services/articles_read.py",
    # T3.03's claim-entailment pass: the second real consumer of the judge,
    # and gated the same way the contradiction scan is — by `judge()`'s own
    # refusal rather than by this list. Re-proved narrowly below.
    "app/services/claim_entailment.py",
    # T3.02/T3.03's synthesis tick constructs the judge and hands it down to
    # the pass. It never calls `judge()` itself and never touches the probe;
    # the construction is here because the judge is built per tick rather
    # than held, so a configuration an operator changed takes effect on the
    # next run. Re-proved narrowly below.
    "app/services/article_synthesis.py",
}

# Capture/retrieval-path modules the judge may NEVER be reachable from
# (invariant 15) — even once consumers exist and the reference allowlist
# grows. This list is a floor with a maintenance duty: any new capture- or
# retrieval-path service (T2.42's facts channel is already minted as a task)
# joins it, and the whole-branch review checks it.
_HOT_PATH_MODULES = {
    "app/services/pipeline.py",
    "app/services/hybrid_search.py",
    "app/services/memory_buffer.py",
    "app/services/memory.py",
    "app/services/code_query.py",
    "app/services/reranker.py",
    "app/services/layer_composition.py",
    "app/services/verified_evidence.py",
}


def _app_sources() -> list[_Path]:
    return [p for p in (_BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def _rel(path: _Path, root: _Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _single_door_offenders(paths: list[_Path], root: _Path) -> list[str]:
    offenders = []
    for path in paths:
        rel = _rel(path, root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _QUOTED_VERIFICATION.search(line) and rel not in _QUOTED_TOKEN_ALLOWLIST:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
            if ("qualification_probe" in line or "verification_judge" in line) \
                    and rel not in _JUDGE_REFERENCE_ALLOWLIST:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


def _hot_path_offenders(paths: list[_Path], root: _Path) -> list[str]:
    offenders = []
    for path in paths:
        rel = _rel(path, root)
        if rel not in _HOT_PATH_MODULES and not rel.startswith("app/api/"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "verification_judge" in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


def _assert_scan_floor(paths: list[_Path]) -> None:
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the source scan would "
        "pass vacuously; check _BACKEND / the glob path"
    )


def test_only_the_judge_module_reaches_the_verification_purpose():
    paths = _app_sources()
    _assert_scan_floor(paths)
    offenders = _single_door_offenders(paths, _BACKEND)
    assert not offenders, (
        "a module outside the judge reached the verification purpose or its "
        "ungated probe — every consumer must go through "
        "VerificationJudge.judge(), the gated door (doc 17 §6):\n"
        + "\n".join(offenders)
    )


def test_single_door_scan_flags_a_direct_dispatch(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        'async def check(llm, msgs):\n'
        '    return await llm.chat_completion("verification", msgs)\n'
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders and "verification" in offenders[0]


def test_single_door_scan_flags_the_two_line_indirection(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        'PURPOSE = "verification"\n'
        "async def check(llm, msgs):\n"
        "    return await llm.chat_completion(PURPOSE, msgs)\n"
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders, "the two-line indirection must still be flagged"


def test_single_door_scan_flags_a_probe_call(tmp_path):
    offending = tmp_path / "app" / "services" / "sneaky.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "async def check(judge, p, h):\n"
        "    return await judge.qualification_probe(p, h)\n"
    )
    offenders = _single_door_offenders([offending], tmp_path)
    assert offenders and "qualification_probe" in offenders[0]


def test_single_door_scan_ignores_identifier_substrings(tmp_path):
    clean = tmp_path / "app" / "services" / "fine.py"
    clean.parent.mkdir(parents=True)
    clean.write_text(
        'JOB = "verification_recompute"\n'
        "verification_status = 'candidate'\n"
    )
    assert _single_door_offenders([clean], tmp_path) == []


def test_the_judge_is_unreachable_from_capture_and_retrieval():
    paths = _app_sources()
    _assert_scan_floor(paths)
    offenders = _hot_path_offenders(paths, _BACKEND)
    assert not offenders, (
        "a capture/retrieval-path module reached the verification judge — "
        "invariant 15: Tier-C only, never the hot path:\n" + "\n".join(offenders)
    )


def test_hot_path_scan_flags_a_planted_route_import(tmp_path):
    offending = tmp_path / "app" / "api" / "routes" / "articles.py"
    offending.parent.mkdir(parents=True)
    offending.write_text(
        "from app.services.verification_judge import VerificationJudge\n"
    )
    offenders = _hot_path_offenders([offending], tmp_path)
    assert offenders and "verification_judge" in offenders[0]


def test_hot_path_scan_flags_a_planted_pipeline_import(tmp_path):
    offending = tmp_path / "app" / "services" / "pipeline.py"
    offending.parent.mkdir(parents=True)
    offending.write_text("from app.services import verification_judge\n")
    offenders = _hot_path_offenders([offending], tmp_path)
    assert offenders


@pytest.mark.parametrize(
    "module",
    ["app/services/review_queue.py", "app/services/articles_read.py"],
)
def test_the_article_gate_reads_the_record_and_never_the_purpose(module):
    """Both article-serving surfaces' allowlist membership, re-proved narrowly.

    Joining `_JUDGE_REFERENCE_ALLOWLIST` buys a module the right to reference
    the judge; it must not buy the right to dispatch it. An articles surface
    may read the qualification record through `article_claim_gate` and nothing
    else — no `judge(`, no probe, no `verification` purpose string.
    """
    import ast as _ast

    root = _Path(__file__).resolve().parents[1]
    source = (root / module).read_text(encoding="utf-8")
    tree = _ast.parse(source)

    imported: list[str] = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom) and node.module == (
            "app.services.verification_judge"
        ):
            imported.extend(alias.name for alias in node.names)

    assert imported == ["article_claim_gate"], (
        f"{module} may read the qualification record and nothing else; "
        f"it imports {imported}"
    )
    assert "judge(" not in source
    assert "qualification_probe" not in source


def test_the_entailment_consumers_use_the_gated_door_and_never_the_probe():
    """Allowlist membership buys the right to *reference* the judge; it must
    not buy the right to bypass it.

    `claim_entailment` calls `judge()` — the qualification-gated door whose
    refusal is what makes T3.03 safe to build before G-D clears — and
    `article_synthesis` only constructs the judge and hands it down. Neither
    may reach `qualification_probe`, which is scan-pinned to the harness
    precisely because it is ungated.
    """
    root = _Path(__file__).resolve().parents[1]

    entailment = (root / "app/services/claim_entailment.py").read_text(encoding="utf-8")
    assert "judge.judge(" in entailment, "the pass must enter through the gated door"
    assert "qualification_probe" not in entailment
    assert "qualification_state" not in entailment, (
        "the pass asks the door, never the record — two modules deciding "
        "whether the judge is qualified is the drift the single door prevents"
    )

    synthesis = (root / "app/services/article_synthesis.py").read_text(encoding="utf-8")
    assert "VerificationJudge(llm)" in synthesis
    assert "qualification_probe" not in synthesis
    assert ".judge(" not in synthesis, (
        "the tick hands the judge down; the pass is what asks it"
    )


# ── R1's consumer scan: the derivation's premise, machine-checked ────────
#
# The amendment derives from "each consumer's gate depends on a discrimination
# it never makes", and that premise is a property of two source files. Read
# once and asserted in prose, it rots the first time a consumer grows a second
# branch — at which point the amendment silently stops being true while every
# test stays green. So it is scanned the way the second-RRF-constant scan is:
# against the parsed tree, checking the binding rather than the wording.

import ast as _ast  # noqa: E402

# module -> the role it may ask as, and therefore the ONE judge verdict it may
# name. Extending this dict means a third consumer, which is a doc 17 §6
# question before it is a code change.
_ROLE_CONSUMERS = {
    "app/services/claim_entailment.py": "entailment",
    "app/services/contradiction_scan.py": "contradiction",
}


def _judge_calls(tree) -> list[_ast.Call]:
    return [
        node for node in _ast.walk(tree)
        if isinstance(node, _ast.Call)
        and isinstance(node.func, _ast.Attribute)
        and node.func.attr == "judge"
    ]


def _verdict_literals(tree) -> set[str]:
    return {
        node.value for node in _ast.walk(tree)
        if isinstance(node, _ast.Constant)
        and isinstance(node.value, str)
        and node.value in vj.JUDGE_VERDICTS
    }


def _role_keyword(call: _ast.Call) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "role" and isinstance(keyword.value, _ast.Name):
            return keyword.value.id
    return None


_ROLE_CONSTANTS = ("ENTAILMENT_ROLE", "CONTRADICTION_ROLE")


def _role_bindings(tree) -> dict[str, str]:
    """Local name -> the judge-module constant it is bound to.

    Resolved rather than pattern-matched on the call site, because the call
    site's spelling is not the binding. `from … import CONTRADICTION_ROLE as
    ENTAILMENT_ROLE` reads as the entailment role at every call and is the
    contradiction one — a one-token change that would flip which qualification
    admits the article pass while a name-only scan stayed green. This was found
    by breaking the scan on purpose, not by reading it.
    """
    bindings = {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ImportFrom) and node.module == (
            "app.services.verification_judge"
        ):
            for alias in node.names:
                if alias.name in _ROLE_CONSTANTS:
                    bindings[alias.asname or alias.name] = alias.name
    return bindings


def _rebound_role_names(tree) -> set[str]:
    """Role names the module assigns to after importing them — the other way a
    call site's spelling stops meaning what it imported."""
    rebound = set()
    for node in _ast.walk(tree):
        targets = []
        if isinstance(node, _ast.Assign):
            targets = node.targets
        elif isinstance(node, (_ast.AnnAssign, _ast.AugAssign)):
            targets = [node.target]
        for target in targets:
            if isinstance(target, _ast.Name) and target.id in _ROLE_CONSTANTS:
                rebound.add(target.id)
    return rebound


@pytest.mark.parametrize("module,role", sorted(_ROLE_CONSUMERS.items()))
def test_each_consumer_names_one_discrimination_and_asks_as_its_role(module, role):
    """`claim_entailment` consumes only the entailed discrimination and
    `contradiction_scan` only the contradicted one — the premise R1 derives
    from, checked against the source rather than asserted about it.

    Two halves, both necessary. The *literals* half proves the consumer cannot
    branch on a verdict it is not qualified for: `contradicted` and
    `unsupported` are genuinely one bucket to the entailment pass, and
    `entailed` and `unsupported` genuinely one to the scan. The *role* half
    proves it asks the judge as the role that measures that verdict — a
    consumer branching correctly while asking as the other role would ship on a
    qualification nobody measured for it.
    """
    root = _Path(__file__).resolve().parents[1]
    tree = _ast.parse((root / module).read_text(encoding="utf-8"))

    assert _verdict_literals(tree) == {vj.ROLE_VERDICTS[role]}, (
        f"{module} names a judge verdict outside its {role!r} role's "
        f"discrimination; R1's derivation rests on it naming exactly one"
    )

    calls = _judge_calls(tree)
    assert calls, f"{module} no longer calls the gated door"
    expected = {"entailment": "ENTAILMENT_ROLE", "contradiction": "CONTRADICTION_ROLE"}[role]

    # The binding, not the spelling: an aliased import or a later assignment
    # makes `role=ENTAILMENT_ROLE` mean whatever the module wants it to.
    bindings = _role_bindings(tree)
    assert bindings == {expected: expected}, (
        f"{module} must import exactly {expected} from the judge module, "
        f"unaliased; it binds {bindings}"
    )
    assert not _rebound_role_names(tree), (
        f"{module} reassigns a judge role constant after importing it"
    )

    for call in calls:
        assert _role_keyword(call) == expected, (
            f"{module} calls judge() without role={expected}; a consumer must "
            "ask as the role whose bars measure the verdict it branches on"
        )


def test_no_module_under_app_reaches_the_judge_without_naming_a_role():
    """The floor under the per-module scan above: a third consumer cannot
    appear with no role, or with a role spelled as a bare string that dodges
    the constant."""
    role_constants = {"ENTAILMENT_ROLE", "CONTRADICTION_ROLE"}
    offenders = []
    for path in _app_sources():
        rel = _rel(path, _BACKEND)
        if rel == "app/services/verification_judge.py":
            continue
        tree = _ast.parse(path.read_text(encoding="utf-8"))
        for call in _judge_calls(tree):
            if _role_keyword(call) not in role_constants:
                offenders.append(f"{rel}:{call.lineno}")
    assert not offenders, (
        "a consumer called VerificationJudge.judge() without one of the "
        f"module's role constants: {offenders}"
    )


def test_the_consumer_scan_flags_a_second_discrimination(tmp_path):
    offending = tmp_path / "consumer.py"
    offending.write_text(
        'from app.services.verification_judge import ENTAILMENT_ROLE\n'
        'CONTRADICTED = "contradicted"\n'
        "async def check(judge, session, p, h):\n"
        "    return await judge.judge(session, p, h, role=ENTAILMENT_ROLE)\n"
    )
    tree = _ast.parse(offending.read_text(encoding="utf-8"))
    assert _verdict_literals(tree) == {"contradicted"}


def test_the_consumer_scan_flags_an_aliased_role_import(tmp_path):
    """The bypass the scan missed until it was broken on purpose: the call site
    still reads `role=ENTAILMENT_ROLE` and is the other role."""
    offending = tmp_path / "consumer.py"
    offending.write_text(
        "from app.services.verification_judge import (\n"
        "    CONTRADICTION_ROLE as ENTAILMENT_ROLE,\n"
        ")\n"
        "async def check(judge, session, p, h):\n"
        "    return await judge.judge(session, p, h, role=ENTAILMENT_ROLE)\n"
    )
    tree = _ast.parse(offending.read_text(encoding="utf-8"))
    calls = _judge_calls(tree)
    assert calls and _role_keyword(calls[0]) == "ENTAILMENT_ROLE"
    assert _role_bindings(tree) == {"ENTAILMENT_ROLE": "CONTRADICTION_ROLE"}


def test_the_consumer_scan_flags_a_rebound_role_constant(tmp_path):
    offending = tmp_path / "consumer.py"
    offending.write_text(
        "from app.services.verification_judge import ENTAILMENT_ROLE\n"
        'ENTAILMENT_ROLE = "contradiction"\n'
        "async def check(judge, session, p, h):\n"
        "    return await judge.judge(session, p, h, role=ENTAILMENT_ROLE)\n"
    )
    tree = _ast.parse(offending.read_text(encoding="utf-8"))
    assert _rebound_role_names(tree) == {"ENTAILMENT_ROLE"}


def test_the_consumer_scan_flags_a_role_free_call(tmp_path):
    offending = tmp_path / "consumer.py"
    offending.write_text(
        "async def check(judge, session, p, h):\n"
        "    return await judge.judge(session, p, h)\n"
    )
    tree = _ast.parse(offending.read_text(encoding="utf-8"))
    calls = _judge_calls(tree)
    assert calls and _role_keyword(calls[0]) is None


def test_the_consumer_scan_flags_a_string_literal_role(tmp_path):
    offending = tmp_path / "consumer.py"
    offending.write_text(
        "async def check(judge, session, p, h):\n"
        '    return await judge.judge(session, p, h, role="entailment")\n'
    )
    tree = _ast.parse(offending.read_text(encoding="utf-8"))
    calls = _judge_calls(tree)
    assert calls and _role_keyword(calls[0]) is None
