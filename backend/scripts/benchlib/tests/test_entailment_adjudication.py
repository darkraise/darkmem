"""The blind-export and merge tool (T2.54 Ruling 3, Layer 2).

The export must leak nothing that constrains a verdict, and the merge rule
must flip label_source only on double agreement with the recorded label --
everything else escalates untouched. Each guard is exercised by feeding it
exactly the shape it exists to refuse.
"""
import json

import pytest

from benchlib.entailment_adjudication import (
    BLIND_FIELDS,
    load_pass,
    merge_blind_passes,
    strip_for_blind,
)


def _doc():
    def pair(i, verdict, slice_name, retired=False):
        p = {
            "id": f"eg-{i:04d}",
            "premise": f"premise {i}",
            "hypothesis": f"hypothesis {i}",
            "verdict": verdict,
            "slice_tags": [slice_name],
            "provenance": "hand-authored-synthetic-fact",
            "label_source": "author",
            "rationale": f"rationale {i}",
        }
        if retired:
            p["retired"] = True
        return p

    return {
        "pairs": [
            pair(1, "entailed", "verbatim"),
            pair(2, "contradicted", "value-swap"),
            pair(3, "unsupported", "unrelated"),
            pair(4, "entailed", "weakening", retired=True),
        ]
    }


def _pass(mapping):
    return {pid: {"verdict": v, "rule": "cited-rule"} for pid, v in mapping.items()}


def test_strip_exports_only_the_blind_fields_of_live_pairs():
    stripped = strip_for_blind(_doc())
    assert [e["id"] for e in stripped] == ["eg-0001", "eg-0002", "eg-0003"]
    for entry in stripped:
        assert set(entry) == set(BLIND_FIELDS)


def test_double_agreement_flips_label_source_and_nothing_else_does():
    doc = _doc()
    pass_a = _pass({"eg-0001": "entailed", "eg-0002": "contradicted",
                    "eg-0003": "entailed"})
    pass_b = _pass({"eg-0001": "entailed", "eg-0002": "unsupported",
                    "eg-0003": "unsupported"})
    outcome = merge_blind_passes(doc, pass_a, pass_b)

    by_id = {p["id"]: p for p in outcome.doc["pairs"]}
    assert by_id["eg-0001"]["label_source"] == "adjudicated"
    # pass B disagreed with the recorded verdict.
    assert by_id["eg-0002"]["label_source"] == "author"
    # the passes disagreed with each other; recorded label untouched.
    assert by_id["eg-0003"]["label_source"] == "author"
    assert by_id["eg-0003"]["verdict"] == "unsupported"

    assert outcome.adjudicated == 1
    assert [e["id"] for e in outcome.escalations] == ["eg-0002", "eg-0003"]
    escalation = outcome.escalations[0]
    assert escalation["recorded_verdict"] == "contradicted"
    assert escalation["pass_a"]["verdict"] == "contradicted"
    assert escalation["pass_b"]["verdict"] == "unsupported"
    assert escalation["slice"] == "value-swap"

    assert outcome.n_live == 3
    assert outcome.agreement_a == pytest.approx(2 / 3)
    assert outcome.agreement_b == pytest.approx(2 / 3)
    assert outcome.agreement_ab == pytest.approx(1 / 3)


def test_merge_never_mutates_the_input_document():
    doc = _doc()
    before = json.dumps(doc, sort_keys=True)
    verdicts = _pass({"eg-0001": "entailed", "eg-0002": "contradicted",
                      "eg-0003": "unsupported"})
    merge_blind_passes(doc, verdicts, verdicts)
    assert json.dumps(doc, sort_keys=True) == before


def test_a_pass_missing_a_live_pair_is_refused():
    verdicts = _pass({"eg-0001": "entailed", "eg-0002": "contradicted"})
    full = _pass({"eg-0001": "entailed", "eg-0002": "contradicted",
                  "eg-0003": "unsupported"})
    with pytest.raises(ValueError, match="missing=\\['eg-0003'\\]"):
        merge_blind_passes(_doc(), verdicts, full)


def test_a_pass_labelling_a_retired_or_unknown_pair_is_refused():
    full = _pass({"eg-0001": "entailed", "eg-0002": "contradicted",
                  "eg-0003": "unsupported"})
    surplus = dict(full)
    surplus["eg-0004"] = {"verdict": "entailed", "rule": "r"}
    with pytest.raises(ValueError, match="surplus=\\['eg-0004'\\]"):
        merge_blind_passes(_doc(), full, surplus)


def test_load_pass_refuses_untabled_verdicts_and_duplicates(tmp_path):
    path = tmp_path / "pass.json"
    path.write_text(json.dumps([
        {"id": "eg-0001", "verdict": "grounded", "rule": "r"},
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="not in"):
        load_pass(path)

    path.write_text(json.dumps([
        {"id": "eg-0001", "verdict": "entailed", "rule": "r"},
        {"id": "eg-0001", "verdict": "entailed", "rule": "r"},
    ]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate id"):
        load_pass(path)


def test_load_pass_round_trips(tmp_path):
    path = tmp_path / "pass.json"
    path.write_text(json.dumps([
        {"id": "eg-0001", "verdict": "entailed", "rule": "verbatim"},
        {"id": "eg-0002", "verdict": "contradicted", "rule": "exclusive-slot"},
    ]), encoding="utf-8")
    verdicts = load_pass(path)
    assert verdicts["eg-0002"] == {"verdict": "contradicted",
                                   "rule": "exclusive-slot"}
