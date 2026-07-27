"""Unit coverage of the isolation probe's metric (T1.35).

``benchlib.isolation_rules`` is pure logic — no app or database imports — so
it is tested here in the ordinary floor. The classification rules are the
gate's bar in code: these tests pin what counts as a leak, so a later edit
cannot quietly widen the bar to fit a result.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pytest

from benchlib.isolation_rules import (
    ProbeReport,
    Sighting,
    Verdict,
    classify,
    scan_sentinels,
    sentinel,
)

OBSERVER = "alpha"


def _sighting(**overrides) -> Sighting:
    base = dict(
        surface="s", door="d", case="c", row="r", kind="content",
        true_project=OBSERVER, true_status="active", archived=False,
        requested_project=None, requested_statuses=None,
        label_project=False, label_status=False,
    )
    base.update(overrides)
    return Sighting(**base)


def test_scoped_project_breach_is_v1():
    c = classify(_sighting(true_project="beta", requested_project=OBSERVER), OBSERVER)
    assert c.verdict is Verdict.V1


def test_scoped_status_breach_is_v1():
    c = classify(
        _sighting(true_status="superseded", requested_statuses=("active",)), OBSERVER,
    )
    assert c.verdict is Verdict.V1


def test_archived_row_is_always_v1():
    c = classify(_sighting(archived=True), OBSERVER)
    assert c.verdict is Verdict.V1


def test_labels_never_excuse_a_scope_breach():
    c = classify(
        _sighting(
            true_project="beta", requested_project=OBSERVER,
            label_project=True, label_status=True,
        ),
        OBSERVER,
    )
    assert c.verdict is Verdict.V1


def test_wide_cross_project_unlabelled_is_v2():
    c = classify(_sighting(true_project="beta"), OBSERVER)
    assert c.verdict is Verdict.V2


def test_wide_cross_project_labelled_is_ok():
    c = classify(_sighting(true_project="beta", label_project=True), OBSERVER)
    assert c.verdict is Verdict.OK


def test_wide_superseded_unlabelled_is_v2():
    c = classify(_sighting(true_status="superseded"), OBSERVER)
    assert c.verdict is Verdict.V2


def test_wide_superseded_labelled_is_ok():
    """Ruling 5: a labelled superseded row is the design, not a violation —
    hiding superseded rows is what once made two memories silently vanish."""
    c = classify(_sighting(true_status="superseded", label_status=True), OBSERVER)
    assert c.verdict is Verdict.OK


def test_requested_superseded_is_in_scope():
    c = classify(
        _sighting(true_status="superseded", requested_statuses=("active", "superseded")),
        OBSERVER,
    )
    assert c.verdict is Verdict.OK


def test_row_without_lifecycle_never_fails_the_status_axis():
    c = classify(_sighting(true_status=None), OBSERVER)
    assert c.verdict is Verdict.OK


def test_id_only_exposure_is_informational_even_out_of_scope():
    """Ruling 4 requires the decision stated: id-only exposure (memory_ids
    arrays, crossrefs, relation edges) is reported, not counted — T1.29d/e
    parked it as an open product question, and the probe keeps it visible
    without converting the parked question into a gate failure by fiat."""
    c = classify(
        _sighting(kind="id", true_project="beta", requested_project=OBSERVER),
        OBSERVER,
    )
    assert c.verdict is Verdict.I1


def test_retention_snapshot_is_informational():
    c = classify(_sighting(retention=True, true_project="beta"), OBSERVER)
    assert c.verdict is Verdict.I2


def test_forced_reason_is_v1_regardless_of_axes():
    c = classify(
        _sighting(true_project=OBSERVER, forced_v1_reason="sentinel outside rows"),
        OBSERVER,
    )
    assert c.verdict is Verdict.V1
    assert c.reasons == ("sentinel outside rows",)


def test_sentinel_roundtrip_and_scan():
    text = f"prefix {sentinel('a_super')} middle {sentinel('b_active')} end"
    assert scan_sentinels(text) == {"a_super", "b_active"}


def test_sentinel_rejects_keys_the_scan_would_truncate():
    with pytest.raises(ValueError):
        sentinel("repo-alpha")


def test_report_counts_only_v1_and_v2():
    report = ProbeReport(observer_project=OBSERVER)
    report.surfaces_driven = ["s"]
    report.add([
        _sighting(true_project="beta", requested_project=OBSERVER),  # V1
        _sighting(true_status="superseded"),                          # V2
        _sighting(kind="id", true_project="beta"),                    # I1
        _sighting(retention=True),                                    # I2
        _sighting(label_project=True),                                # OK
    ])
    assert report.count() == 2
    rendered = report.render()
    assert rendered.strip().endswith("ISOLATION PROBE VIOLATIONS: 2")


def test_report_ordering_is_stable():
    report_a = ProbeReport(observer_project=OBSERVER)
    report_b = ProbeReport(observer_project=OBSERVER)
    rows = [
        _sighting(row="z", true_project="beta"),
        _sighting(row="a", true_project="beta"),
    ]
    report_a.add(rows)
    report_b.add(list(reversed(rows)))
    report_a.surfaces_driven = report_b.surfaces_driven = ["s"]
    assert report_a.render() == report_b.render()
