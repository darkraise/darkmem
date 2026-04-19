"""Tests for lazy per-group loading + idle eviction.

The actual model loads pull ~2 GB of weights off disk and ~1.6 GB onto GPU,
so these tests stub ``MLModels.load_*`` methods to run fast without torch.
The point is to exercise the lazy-ensure + evict_idle logic and the feature
flags around them.
"""
from __future__ import annotations

import pytest

from app.services import ml_models as mm


@pytest.fixture(autouse=True)
def _reset_ml_module():
    mm.reset_ml_models()
    yield
    mm.reset_ml_models()


def _install_stub_loaders(monkeypatch):
    """Replace the three heavy load_* methods with bookkeeping stubs."""
    calls: dict[str, int] = {"extraction": 0, "classification": 0, "retriever": 0}

    def _fake_load_extraction(self):
        calls["extraction"] += 1
        self.span = object()
        self.typer = object()
        self.typer_tok = object()
        self.relation = object()
        self.relation_tok = object()

    def _fake_load_classification(self):
        calls["classification"] += 1
        self.classifier = object()
        self.classifier_tok = object()

    def _fake_load_retriever(self):
        calls["retriever"] += 1
        self.retriever = object()
        self.embedding_dims = 1024
        self.fingerprint = "stub|1024"

    monkeypatch.setattr(mm.MLModels, "load_extraction", _fake_load_extraction)
    monkeypatch.setattr(mm.MLModels, "load_classification", _fake_load_classification)
    monkeypatch.setattr(mm.MLModels, "load_retriever", _fake_load_retriever)
    return calls


def test_instance_shell_creates_empty_singleton_without_loading(monkeypatch):
    _install_stub_loaders(monkeypatch)
    ml = mm._instance_shell()
    assert ml.span is None
    assert ml.classifier is None
    assert ml.retriever is None
    # models_available is all-or-nothing: false until every group is in.
    assert mm.models_available() is False
    assert mm.any_group_available() is False


def test_ensure_extraction_loads_only_that_group(monkeypatch):
    calls = _install_stub_loaders(monkeypatch)

    mm.ensure_extraction_loaded()
    assert calls == {"extraction": 1, "classification": 0, "retriever": 0}
    ml = mm.get_ml_models()
    assert ml.extraction_loaded is True
    assert ml.classification_loaded is False
    assert ml.retriever_loaded is False
    assert mm.any_group_available() is True
    assert mm.models_available() is False


def test_ensure_is_idempotent(monkeypatch):
    calls = _install_stub_loaders(monkeypatch)

    mm.ensure_classification_loaded()
    mm.ensure_classification_loaded()
    mm.ensure_classification_loaded()
    assert calls["classification"] == 1


def test_ensure_updates_last_access(monkeypatch):
    _install_stub_loaders(monkeypatch)
    assert mm._GROUP_LAST_ACCESS["retriever"] == 0.0
    mm.ensure_retriever_loaded()
    assert mm._GROUP_LAST_ACCESS["retriever"] > 0


def test_evict_idle_unloads_only_stale_groups(monkeypatch):
    calls = _install_stub_loaders(monkeypatch)

    mm.ensure_extraction_loaded()
    mm.ensure_classification_loaded()
    # Make extraction look old by rolling its last-access back in time.
    mm._GROUP_LAST_ACCESS["extraction"] -= 10_000.0
    evicted = mm.evict_idle(ttl_seconds=1.0)
    assert "extraction" in evicted
    assert "classification" not in evicted

    ml = mm.get_ml_models()
    assert ml.extraction_loaded is False
    assert ml.classification_loaded is True

    # The last-access timer for an evicted group resets to 0; a follow-up
    # ensure reloads it (call count increments).
    mm.ensure_extraction_loaded()
    assert calls["extraction"] == 2


def test_evict_idle_ttl_zero_is_no_op(monkeypatch):
    _install_stub_loaders(monkeypatch)
    mm.ensure_retriever_loaded()
    mm._GROUP_LAST_ACCESS["retriever"] -= 10_000.0

    assert mm.evict_idle(ttl_seconds=0) == []
    assert mm.get_ml_models().retriever_loaded is True


def test_group_status_reports_per_group(monkeypatch):
    _install_stub_loaders(monkeypatch)

    mm.ensure_extraction_loaded()
    status = mm.group_status()
    assert status["extraction"]["loaded"] is True
    assert status["classification"]["loaded"] is False
    assert status["retriever"]["loaded"] is False
    # Idle seconds is a non-negative int for loaded groups, None before first load.
    assert isinstance(status["extraction"]["idle_seconds"], int)
    assert status["classification"]["idle_seconds"] is None


def test_load_all_bumps_every_group(monkeypatch):
    _install_stub_loaders(monkeypatch)
    ml = mm.load_ml_models()
    assert ml.loaded is True
    for g in mm.GROUPS:
        assert mm._GROUP_LAST_ACCESS[g] > 0


def test_reload_ml_models_resets_then_eagerly_loads(monkeypatch):
    calls = _install_stub_loaders(monkeypatch)
    mm.ensure_extraction_loaded()
    assert calls["extraction"] == 1
    mm.reload_ml_models(device="cpu")
    # After reload every group is loaded (reload does load_all eagerly).
    ml = mm.get_ml_models()
    assert ml.loaded is True
    assert calls["extraction"] == 2
    assert calls["classification"] == 1
    assert calls["retriever"] == 1


# --- REST: feature flags expose the TTL knobs ----------------------------

@pytest.mark.asyncio
async def test_feature_flags_exposes_ttl_knobs(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "ml_idle_ttl_minutes" in body
    assert "ml_eviction_check_interval_seconds" in body
    # Defaults.
    assert body["ml_idle_ttl_minutes"] == 30
    assert body["ml_eviction_check_interval_seconds"] == 60


@pytest.mark.asyncio
async def test_feature_flags_validates_ttl_knobs(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_idle_ttl_minutes": -1},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_idle_ttl_minutes": 5000},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_eviction_check_interval_seconds": 5},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_idle_ttl_minutes": 0, "ml_eviction_check_interval_seconds": 120},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ml_idle_ttl_minutes"] == 0
    assert body["ml_eviction_check_interval_seconds"] == 120
