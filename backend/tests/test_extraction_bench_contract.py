"""The F1 bench measures the shipping path, or it measures nothing.

Guards the three properties that make the bench number mean something:
the pinned gate state is the default shipping one, a cache generation that
no longer describes the current assembly is refused rather than replayed, and
the served-stack fingerprint is pinned so a vendor rotation cannot fold fresh
model drift into a measured delta.
"""
import json
import sys
from pathlib import Path

import pytest

from app.config import FEATURE_FLAGS_DEFAULTS

BENCH_DIR = Path(__file__).resolve().parents[1] / "scripts" / "extraction_bench"
sys.path.insert(0, str(BENCH_DIR))
import run_bench  # noqa: E402


def test_default_gate_is_the_shipping_merged_configuration():
    """``can_merge`` is LLM-backed classifier AND ``classification_mode == 'simple'``.

    The bench pins the *default* configuration: there is no single deployed
    gate state, since an operator can change ``classification_mode`` at runtime.
    """
    ap_default = run_bench.GATES["merged"]
    assert ap_default is True
    classifier_kind = None  # the seeded default; anything but 'local' is LLM-backed
    can_merge = (
        classifier_kind != "local"
        and FEATURE_FLAGS_DEFAULTS["classification_mode"] == "simple"
    )
    assert can_merge is ap_default


def test_extract_only_gate_is_available_for_the_local_classifier_path():
    assert run_bench.GATES["extract-only"] is False


def test_cache_key_covers_the_system_message(monkeypatch):
    from app.services.extraction import ExtractionService

    base = ExtractionService.build_extraction_request("hello world")
    edited = ExtractionService.build_extraction_request("hello world", system_prompt="other")
    assert run_bench.request_cache_key(base) != run_bench.request_cache_key(edited)


def test_algo_only_refuses_a_stale_generation(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    identity = run_bench.assembly_identity(True)
    manifest.write_text(json.dumps({
        **identity, "prompt_sha16": "0" * 16, "gate": "merged", "model": "deepseek-v4-flash",
    }), encoding="utf-8")
    monkeypatch.setattr(run_bench, "MANIFEST", str(manifest))

    with pytest.raises(SystemExit) as excinfo:
        run_bench.assert_manifest_current(True, "merged")
    assert "prompt_sha16" in str(excinfo.value)


def test_algo_only_refuses_a_missing_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(run_bench, "MANIFEST", str(tmp_path / "absent.json"))
    with pytest.raises(SystemExit):
        run_bench.assert_manifest_current(True, "merged")


def test_algo_only_accepts_a_matching_generation(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        **run_bench.assembly_identity(True), "gate": "merged", "model": "deepseek-v4-flash",
    }), encoding="utf-8")
    monkeypatch.setattr(run_bench, "MANIFEST", str(manifest))
    run_bench.assert_manifest_current(True, "merged")


def test_algo_only_refuses_a_gate_flip(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        **run_bench.assembly_identity(True), "gate": "merged", "model": "deepseek-v4-flash",
    }), encoding="utf-8")
    monkeypatch.setattr(run_bench, "MANIFEST", str(manifest))
    with pytest.raises(SystemExit):
        run_bench.assert_manifest_current(False, "extract-only")


def test_legacy_bare_dict_and_enveloped_entries_read_the_same():
    raw = {"entities": [{"name": "pgvector", "type": "tool"}], "relationships": []}
    assert run_bench.read_entry(raw) == raw
    assert run_bench.read_entry({"raw": raw, "meta": {"model": "deepseek-v4-flash"}}) == raw


class _FakeService:
    def __init__(self, fingerprint):
        self._fingerprint = fingerprint

    async def extract_raw(self, content, *, with_classification, return_meta):
        return {"entities": [], "relationships": []}, {
            "model": "deepseek-v4-flash", "system_fingerprint": self._fingerprint,
        }


async def _record(tmp_path, monkeypatch, served):
    monkeypatch.setattr(run_bench, "CACHE", str(tmp_path))
    return await run_bench.get_raw(
        _FakeService(served), "some content", with_classification=True,
        algo_only=False, expect_fingerprint=run_bench.EXPECTED_SYSTEM_FINGERPRINT,
        seen=set(),
    )


@pytest.mark.asyncio
async def test_a_rotated_serving_stack_stops_the_measurement(tmp_path, monkeypatch):
    """A mid-task vendor rotation folds fresh model drift into the measured delta.

    Lane D measured one fingerprint stable across 159 calls, so a change is
    signal. Every pass of a multi-pass measurement pins the same value, which is
    what makes Pass A and Pass B comparable to each other.
    """
    with pytest.raises(SystemExit) as excinfo:
        await _record(tmp_path, monkeypatch, "fp_something_else")
    assert "system_fingerprint changed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_pinned_serving_stack_records_normally(tmp_path, monkeypatch):
    raw = await _record(tmp_path, monkeypatch, run_bench.EXPECTED_SYSTEM_FINGERPRINT)
    assert raw == {"entities": [], "relationships": []}
    written = list(tmp_path.glob("*.json"))
    assert len(written) == 1
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert payload["meta"]["system_fingerprint"] == run_bench.EXPECTED_SYSTEM_FINGERPRINT
    assert payload["meta"]["model"] == "deepseek-v4-flash"


def test_served_fingerprint_is_pinned_to_the_measured_stack():
    assert run_bench.EXPECTED_SYSTEM_FINGERPRINT == "a26a7955944dc5c60445bff77fac9c8e"


def test_pinned_model_matches_the_gate_ledger():
    assert run_bench.PINNED_MODEL == "deepseek-v4-flash"
