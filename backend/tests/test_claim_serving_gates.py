"""Evidence records gate the label, never the code (T2.95).

This is the load-bearing task of the M1 split. Implementation is allowed to run
arbitrarily far ahead of measurement *because* no code path can serve a claim
whose evidence does not exist — if that is wrong, running ahead stops being
safe, and everything built before M1 is shipping unbacked assertions.

Two properties carry it. **Suppression must be total** — no serving path may
reach a promoted status without the record. And **suppression must be
visible** — a withheld label and a genuinely-`candidate` one must not read
alike, or a missing measurement silently becomes an apparent property of the
corpus: the reader concludes the data is unverified when the truth is that the
*verifier* is unmeasured.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.services import claim_gates
from app.services.fact_badge import row_labels

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def cleared_record(tmp_path):
    path = tmp_path / "promotion_metrics_record.json"
    path.write_text(json.dumps({"gate_eligible": True, "promotion_rate": 0.4}))
    return path


# ── the gate itself ──────────────────────────────────────────────────


def test_no_record_closes_the_gate(tmp_path):
    gate = claim_gates.corroboration_gate(tmp_path / "absent.json")
    assert gate.open is False
    assert "verification_unmeasured" in gate.reason


def test_an_unreadable_record_fails_closed(tmp_path):
    """A parse error must not crash the read path *open*. Serving the label
    because the gate itself broke is the one failure that would make this
    module worse than useless."""
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json at all")
    assert claim_gates.corroboration_gate(corrupt).open is False


def test_an_interim_record_does_not_open_the_gate(tmp_path):
    """T2.26's own 0.8182 was branded INTERIM by its artifact and would read as
    a pass to anything checking only for presence."""
    interim = tmp_path / "interim.json"
    interim.write_text(json.dumps({"gate_eligible": False, "note": "rehearsal"}))
    assert claim_gates.corroboration_gate(interim).open is False


def test_a_cleared_record_opens_the_gate(cleared_record):
    assert claim_gates.corroboration_gate(cleared_record).open is True


# ── what is gated, and what is deliberately not ──────────────────────


@pytest.mark.parametrize("status", sorted(claim_gates.PROMOTED_STATUSES))
def test_promoted_statuses_are_withheld_without_a_record(status):
    served, reason = claim_gates.served_status(status)
    assert served == "candidate"
    assert reason is not None


@pytest.mark.parametrize("status", ["candidate", "disputed", None])
def test_unpromoted_statuses_pass_through_untouched(status):
    """`disputed` asserts a two-sided conflict, which is honest without a
    promotion record; gating it would withhold an honest statement."""
    served, reason = claim_gates.served_status(status)
    assert served == status
    assert reason is None


# ── the producer applies it, so consumers cannot forget to ───────────


def test_the_badge_producer_withholds_the_promoted_label():
    labels = row_labels(id_kind="fact", verification_status="corroborated")
    assert labels["verification_status"] == "candidate"
    assert labels["unverified"] is True
    assert labels["label_suppressed"] is not None


def test_a_withheld_status_carries_no_badge():
    """The badge sentence names the origin count and the absence of
    contradiction — precisely the claim under gate. Serving it beside a
    withheld status would leak the assertion the status withheld."""
    from app.services.fact_badge import Badge

    badge = Badge(status="corroborated", claim="asserted by 3 distinct origins",
                  as_of=None) if hasattr(Badge, "status") else None
    labels = row_labels(id_kind="fact", verification_status="corroborated",
                        badge=badge)
    assert labels["badge"] is None


def test_suppressed_is_distinguishable_from_genuinely_candidate():
    """The property that keeps a missing measurement from reading as a fact
    about the corpus."""
    withheld = row_labels(id_kind="fact", verification_status="corroborated")
    genuine = row_labels(id_kind="fact", verification_status="candidate")
    assert withheld["verification_status"] == genuine["verification_status"]
    assert withheld["label_suppressed"] is not None
    assert genuine["label_suppressed"] is None


def test_minting_a_record_lights_the_label_with_no_code_change(monkeypatch, cleared_record):
    """The reversibility claim the M1 split rests on, proven with a fixture
    rather than asserted."""
    before = row_labels(id_kind="fact", verification_status="corroborated")
    assert before["verification_status"] == "candidate"

    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", cleared_record)
    after = row_labels(id_kind="fact", verification_status="corroborated")

    assert after["verification_status"] == "corroborated"
    assert after["label_suppressed"] is None
    assert after["unverified"] is False


# ── structural: no serving path may bypass the producer ──────────────


def test_no_serving_module_writes_a_promoted_status_itself():
    """A gate applied at each consumer is a convention; applied at the one
    producer it is a property. This is what keeps it one."""
    offenders = []
    for name in ("facts_read.py", "layer_composition.py"):
        source = (BACKEND / "app" / "services" / name).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant)
                        and key.value == "verification_status"
                        and isinstance(value, ast.Constant)
                        and value.value in claim_gates.PROMOTED_STATUSES):
                    offenders.append(f"{name}:{node.lineno}")
    assert not offenders, (
        "a serving module emits a promoted verification_status literal instead "
        "of routing through fact_badge.row_labels: " + ", ".join(offenders)
    )


def test_this_module_never_reaches_the_judge():
    """The groundedness question belongs to `verification_judge`, which owns the
    record and is scan-enforced as the only door. Re-asking it here would put
    two modules in the business of deciding whether the judge is qualified —
    the drift that scan exists to prevent, and it caught this module's first
    version doing exactly that."""
    source = (BACKEND / "app" / "services" / "claim_gates.py").read_text()
    assert "from app.services.verification_judge import" not in source
    assert "import verification_judge" not in source


def test_a_human_ratification_is_never_suppressed():
    """`confirmed` is human-ratified: a person looked at the fact and said yes.
    G-C certifies the *automatic* ladder, so withholding a human's ratification
    because an automated ladder is unmeasured would suppress the one label that
    never depended on the ladder. This module's first version got it wrong."""
    served, reason = claim_gates.served_status("confirmed")
    assert served == "confirmed"
    assert reason is None


def test_no_article_path_serves_a_grounded_label_today():
    """The article channel is not built (T3.02/T3.23). This pins that nothing
    serves the label *before* the channel exists, so the gate lands with the
    channel rather than after it."""
    services = (BACKEND / "app" / "services")
    offenders = [
        p.name for p in services.glob("*.py")
        if '"grounded"' in p.read_text() and p.name != "claim_gates.py"
    ]
    assert not offenders, f"a service emits a grounded label ungated: {offenders}"
