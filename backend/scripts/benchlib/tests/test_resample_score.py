"""``resample_score.py`` (T2.107): the scorer that turns a completed
resample into the ``resample`` block the eligibility lock requires.

Every gold pair and every verdict here is synthetic (``s-N`` ids, made-up
premises, made-up verdicts) -- this is the module that DOES touch the gold
in production, so its tests must not smuggle in any real verdict from
``entailment/gold.json`` even incidentally. Where this suite proves the
real lock accepts the written block, it calls the real
``judge_qualification`` functions against a synthetic gold document, never
against the real one.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from benchlib import judge_qualification as jq, resample_score


def _gold_bytes(pairs: list[dict]) -> bytes:
    return json.dumps({"pairs": pairs}).encode("utf-8")


def _manifest(gold_bytes: bytes, **overrides) -> dict:
    manifest = {
        "n": 3,
        "bar_max_disagreements": 1,
        "gold_sha256": hashlib.sha256(gold_bytes).hexdigest(),
        "seed": 987654321,
    }
    manifest.update(overrides)
    return manifest


_SYNTHETIC_PAIRS = [
    {"id": "s-1", "verdict": "entailed"},
    {"id": "s-2", "verdict": "contradicted"},
    {"id": "s-3", "verdict": "unsupported"},
]
_SYNTHETIC_GOLD_BYTES = _gold_bytes(_SYNTHETIC_PAIRS)
_SYNTHETIC_BLIND_IDS = {"s-1", "s-2", "s-3"}


def _all_agree_verdicts() -> dict[str, dict]:
    return {
        "s-1": {"verdict": "entailed", "rule": "verbatim"},
        "s-2": {"verdict": "contradicted", "rule": "exclusive-slot rule"},
        "s-3": {"verdict": "unsupported", "rule": "unrelated"},
    }


# ── score(): the comparison ───────────────────────────────────────────


def test_perfect_agreement_yields_zero_disagreements():
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    block, disagreements = resample_score.score(
        _all_agree_verdicts(),
        gold_bytes=_SYNTHETIC_GOLD_BYTES,
        gold_pairs=_SYNTHETIC_PAIRS,
        manifest=manifest,
        blind_ids=_SYNTHETIC_BLIND_IDS,
        performed_by="owner",
        date="2026-08-07",
    )
    assert block == {
        "n": 3, "disagreements": 0, "seed": manifest["seed"],
        "performed_by": "owner", "date": "2026-08-07",
    }
    assert disagreements == []


def test_a_single_miss_is_reported_by_id_with_both_verdicts():
    verdicts = _all_agree_verdicts()
    verdicts["s-2"] = {"verdict": "unsupported", "rule": "wrong rule"}
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    block, disagreements = resample_score.score(
        verdicts,
        gold_bytes=_SYNTHETIC_GOLD_BYTES,
        gold_pairs=_SYNTHETIC_PAIRS,
        manifest=manifest,
        blind_ids=_SYNTHETIC_BLIND_IDS,
        performed_by="owner",
        date="2026-08-07",
    )
    assert block["disagreements"] == 1
    assert disagreements == [{
        "id": "s-2", "gold_verdict": "contradicted",
        "resample_verdict": "unsupported", "rule_cited": "wrong rule",
    }]


def test_the_seed_is_read_from_the_manifest_never_recomputed():
    """The manifest's seed is an arbitrary marker here, deliberately unequal
    to anything derivable from the gold bytes -- proving the scorer copies
    it rather than re-deriving one from `resample_draw.derive_seed`."""
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES, seed=13)
    block, _ = resample_score.score(
        _all_agree_verdicts(),
        gold_bytes=_SYNTHETIC_GOLD_BYTES,
        gold_pairs=_SYNTHETIC_PAIRS,
        manifest=manifest,
        blind_ids=_SYNTHETIC_BLIND_IDS,
        performed_by="owner",
        date="2026-08-07",
    )
    assert block["seed"] == 13


def test_a_stale_gold_sha_is_refused():
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    changed_bytes = _gold_bytes([*_SYNTHETIC_PAIRS, {"id": "s-4", "verdict": "entailed"}])
    with pytest.raises(ValueError, match="changed since this resample was drawn"):
        resample_score.score(
            _all_agree_verdicts(),
            gold_bytes=changed_bytes,
            gold_pairs=_SYNTHETIC_PAIRS,
            manifest=manifest,
            blind_ids=_SYNTHETIC_BLIND_IDS,
            performed_by="owner",
            date="2026-08-07",
        )


def test_a_missing_id_is_refused():
    verdicts = _all_agree_verdicts()
    del verdicts["s-3"]
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    with pytest.raises(ValueError, match="missing=\\['s-3'\\]"):
        resample_score.score(
            verdicts,
            gold_bytes=_SYNTHETIC_GOLD_BYTES,
            gold_pairs=_SYNTHETIC_PAIRS,
            manifest=manifest,
            blind_ids=_SYNTHETIC_BLIND_IDS,
            performed_by="owner",
            date="2026-08-07",
        )


def test_a_surplus_id_is_refused():
    verdicts = _all_agree_verdicts()
    verdicts["s-99"] = {"verdict": "entailed", "rule": "n/a"}
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    with pytest.raises(ValueError, match="surplus=\\['s-99'\\]"):
        resample_score.score(
            verdicts,
            gold_bytes=_SYNTHETIC_GOLD_BYTES,
            gold_pairs=_SYNTHETIC_PAIRS,
            manifest=manifest,
            blind_ids=_SYNTHETIC_BLIND_IDS,
            performed_by="owner",
            date="2026-08-07",
        )


def test_an_untabled_verdict_is_refused():
    verdicts = _all_agree_verdicts()
    verdicts["s-1"] = {"verdict": "maybe", "rule": ""}
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    with pytest.raises(ValueError, match="not one of"):
        resample_score.score(
            verdicts,
            gold_bytes=_SYNTHETIC_GOLD_BYTES,
            gold_pairs=_SYNTHETIC_PAIRS,
            manifest=manifest,
            blind_ids=_SYNTHETIC_BLIND_IDS,
            performed_by="owner",
            date="2026-08-07",
        )


def test_a_blank_verdict_is_refused_as_incomplete():
    verdicts = _all_agree_verdicts()
    verdicts["s-1"] = {"verdict": "", "rule": ""}
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES)
    with pytest.raises(ValueError, match="not one of"):
        resample_score.score(
            verdicts,
            gold_bytes=_SYNTHETIC_GOLD_BYTES,
            gold_pairs=_SYNTHETIC_PAIRS,
            manifest=manifest,
            blind_ids=_SYNTHETIC_BLIND_IDS,
            performed_by="owner",
            date="2026-08-07",
        )


# ── write_resample(): the gold-file mutation and its refusals ───────────


def test_write_resample_adds_the_block_and_touches_nothing_else(tmp_path):
    gold_path = tmp_path / "gold.json"
    original = {"pairs": _SYNTHETIC_PAIRS, "other_top_level_key": "untouched"}
    gold_path.write_text(json.dumps(original), encoding="utf-8")

    block = {"n": 3, "disagreements": 0, "seed": 1, "performed_by": "owner", "date": "2026-08-07"}
    doc = resample_score.write_resample(gold_path, block)

    assert doc["resample"] == block
    assert doc["pairs"] == _SYNTHETIC_PAIRS
    assert doc["other_top_level_key"] == "untouched"

    reloaded = json.loads(gold_path.read_text(encoding="utf-8"))
    assert reloaded["resample"] == block
    assert reloaded["pairs"] == _SYNTHETIC_PAIRS


def test_a_second_write_without_force_is_refused_even_if_it_would_improve_the_number(tmp_path):
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps({"pairs": _SYNTHETIC_PAIRS}), encoding="utf-8")

    first = {"n": 3, "disagreements": 2, "seed": 1, "performed_by": "owner", "date": "2026-08-07"}
    resample_score.write_resample(gold_path, first)

    better = {"n": 3, "disagreements": 0, "seed": 1, "performed_by": "owner", "date": "2026-08-08"}
    with pytest.raises(ValueError, match="cannot improve the number"):
        resample_score.write_resample(gold_path, better)

    # The refused write must not have touched the file.
    reloaded = json.loads(gold_path.read_text(encoding="utf-8"))
    assert reloaded["resample"] == first


def test_force_keeps_the_superseded_block_visible(tmp_path):
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps({"pairs": _SYNTHETIC_PAIRS}), encoding="utf-8")

    first = {"n": 3, "disagreements": 2, "seed": 1, "performed_by": "owner", "date": "2026-08-07"}
    resample_score.write_resample(gold_path, first)

    correction = {"n": 3, "disagreements": 1, "seed": 1, "performed_by": "owner", "date": "2026-08-08"}
    doc = resample_score.write_resample(gold_path, correction, force=True)

    assert doc["resample"]["disagreements"] == 1
    assert doc["resample"]["supersedes"] == [first]

    # A second forced correction keeps the whole chain, not just the latest.
    second_correction = {"n": 3, "disagreements": 0, "seed": 1, "performed_by": "owner", "date": "2026-08-09"}
    doc2 = resample_score.write_resample(gold_path, second_correction, force=True)
    assert doc2["resample"]["supersedes"] == [first, correction]


# ── integration with the real lock (not a mock) ──────────────────────────


def _synthetic_eligible_gold(resample: dict) -> dict:
    """A minimal synthetic gold shaped to clear every OTHER eligibility
    condition, isolating the resample condition this task's block feeds --
    the same construction `test_judge_qualification.py::_synthetic_gold`
    uses, rebuilt here so this suite does not depend on that file's
    private helper."""
    pairs = [
        {"id": f"g-{i:04d}", "verdict": "entailed", "label_source": "adjudicated"}
        for i in range(200)
    ]
    return {
        "pairs": pairs,
        "declared_provenance_counts": {
            "hand-authored-synthetic-fact": 100,
            "hand-authored-bench-corpus": 0,
            "synthesis-draft": 0,
            "l2-fact": 100,
        },
        "resample": resample,
    }


def test_the_real_lock_accepts_the_block_the_scorer_writes():
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES, seed=555)
    block, _ = resample_score.score(
        _all_agree_verdicts(),
        gold_bytes=_SYNTHETIC_GOLD_BYTES,
        gold_pairs=_SYNTHETIC_PAIRS,
        manifest=manifest,
        blind_ids=_SYNTHETIC_BLIND_IDS,
        performed_by="owner",
        date="2026-08-07",
    )
    # This block's own n=3 is below the ratified floor (93) by construction
    # of the synthetic 3-pair fixture; pad it to the ratified size to prove
    # the *shape* the scorer writes is what the real lock wants, without
    # smuggling a real 93-pair draw into this synthetic-only suite.
    padded_block = {**block, "n": jq.RESAMPLE_N, "disagreements": 0}
    eligibility = jq.gate_eligibility(_synthetic_eligible_gold(padded_block))
    assert eligibility.eligible is True
    assert len(eligibility.reasons) == 1  # only the composition summary line, no refusal ground


def test_the_real_lock_still_refuses_an_undersized_block():
    manifest = _manifest(_SYNTHETIC_GOLD_BYTES, seed=555)
    block, _ = resample_score.score(
        _all_agree_verdicts(),
        gold_bytes=_SYNTHETIC_GOLD_BYTES,
        gold_pairs=_SYNTHETIC_PAIRS,
        manifest=manifest,
        blind_ids=_SYNTHETIC_BLIND_IDS,
        performed_by="owner",
        date="2026-08-07",
    )
    eligibility = jq.gate_eligibility(_synthetic_eligible_gold(block))
    assert eligibility.eligible is False
    assert any("below the ratified floor" in reason for reason in eligibility.reasons)


# ── CLI wiring end to end ────────────────────────────────────────────────


def test_main_reads_a_completed_sheet_scores_and_writes_the_block(tmp_path):
    from benchlib import resample_sheet

    rows = [
        {"id": "s-1", "premise": "p1", "hypothesis": "h1"},
        {"id": "s-2", "premise": "p2", "hypothesis": "h2"},
        {"id": "s-3", "premise": "p3", "hypothesis": "h3"},
    ]
    blind_export_path = tmp_path / "resample_blind.json"
    blind_export_path.write_text(json.dumps(rows), encoding="utf-8")

    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps({"pairs": _SYNTHETIC_PAIRS}), encoding="utf-8")

    manifest = _manifest(gold_path.read_bytes())
    manifest_path = tmp_path / "resample_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    sheet_text = resample_sheet.render_sheet(rows, "## rulebook\n\nbody")
    sheet_text = sheet_text.replace(
        "## Item 1 — s-1\n\n**Premise:** p1\n\n**Hypothesis:** h1\n\n**Verdict:** \n\n**Rule cited:** ",
        "## Item 1 — s-1\n\n**Premise:** p1\n\n**Hypothesis:** h1\n\n**Verdict:** entailed\n\n**Rule cited:** verbatim",
    ).replace(
        "## Item 2 — s-2\n\n**Premise:** p2\n\n**Hypothesis:** h2\n\n**Verdict:** \n\n**Rule cited:** ",
        "## Item 2 — s-2\n\n**Premise:** p2\n\n**Hypothesis:** h2\n\n**Verdict:** contradicted\n\n**Rule cited:** exclusive-slot rule",
    ).replace(
        "## Item 3 — s-3\n\n**Premise:** p3\n\n**Hypothesis:** h3\n\n**Verdict:** \n\n**Rule cited:** ",
        "## Item 3 — s-3\n\n**Premise:** p3\n\n**Hypothesis:** h3\n\n**Verdict:** unsupported\n\n**Rule cited:** unrelated",
    )
    sheet_path = tmp_path / "resample_sheet.md"
    sheet_path.write_text(sheet_text, encoding="utf-8")

    disagreements_path = tmp_path / "resample_disagreements.json"

    exit_code = resample_score.main([
        "--sheet", str(sheet_path),
        "--gold", str(gold_path),
        "--manifest", str(manifest_path),
        "--blind-export", str(blind_export_path),
        "--disagreements-out", str(disagreements_path),
        "--performed-by", "test-owner",
        "--date", "2026-08-07",
    ])
    assert exit_code == 0

    written = json.loads(gold_path.read_text(encoding="utf-8"))
    assert written["resample"] == {
        "n": 3, "disagreements": 0, "seed": manifest["seed"],
        "performed_by": "test-owner", "date": "2026-08-07",
    }
    assert json.loads(disagreements_path.read_text(encoding="utf-8")) == []


def test_main_refuses_on_stale_gold_and_writes_nothing(tmp_path):
    from benchlib import resample_sheet

    rows = [{"id": "s-1", "premise": "p1", "hypothesis": "h1"}]
    blind_export_path = tmp_path / "resample_blind.json"
    blind_export_path.write_text(json.dumps(rows), encoding="utf-8")

    gold_path = tmp_path / "gold.json"
    gold_path.write_text(json.dumps({"pairs": [{"id": "s-1", "verdict": "entailed"}]}), encoding="utf-8")

    # Manifest pins a SHA that does not match the gold file on disk.
    manifest = _manifest(b"not the real gold bytes")
    manifest_path = tmp_path / "resample_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    sheet_text = resample_sheet.render_sheet(rows, "## rulebook\n\nbody").replace(
        "**Verdict:** \n\n**Rule cited:** ", "**Verdict:** entailed\n\n**Rule cited:** verbatim",
    )
    sheet_path = tmp_path / "resample_sheet.md"
    sheet_path.write_text(sheet_text, encoding="utf-8")

    with pytest.raises(ValueError, match="changed since this resample was drawn"):
        resample_score.main([
            "--sheet", str(sheet_path),
            "--gold", str(gold_path),
            "--manifest", str(manifest_path),
            "--blind-export", str(blind_export_path),
            "--performed-by", "test-owner",
        ])

    reloaded = json.loads(gold_path.read_text(encoding="utf-8"))
    assert "resample" not in reloaded
