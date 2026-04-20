"""Tests for the UI-facing ML device picker.

Exercises :func:`_resolve_device` with cuda_index, :func:`list_available_devices`,
and the two REST endpoints that back the UI (``GET /api/v1/config/ml-devices``,
``POST /api/v1/config/ml-device/apply``).
"""
from __future__ import annotations

import pytest

from app.services.ml_models import _resolve_device, list_available_devices


# --- _resolve_device -------------------------------------------------------

def test_resolve_device_cpu_is_always_cpu():
    assert _resolve_device("cpu") == "cpu"
    assert _resolve_device("cpu", cuda_index=3) == "cpu"


def test_resolve_device_auto_without_cuda(monkeypatch):
    """When CUDA is unavailable, `auto` and `cuda` both resolve to cpu."""
    import app.services.ml_models as mm

    class _FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return False

    monkeypatch.setattr(
        mm, "_resolve_device",
        _resolve_device.__wrapped__ if hasattr(_resolve_device, "__wrapped__") else _resolve_device,
        raising=False,
    )

    import sys
    original_torch = sys.modules.get("torch")
    sys.modules["torch"] = _FakeTorch  # type: ignore[assignment]
    try:
        assert _resolve_device("auto") == "cpu"
        assert _resolve_device("cuda") == "cpu"
    finally:
        if original_torch is not None:
            sys.modules["torch"] = original_torch
        else:
            sys.modules.pop("torch", None)


def test_resolve_device_picks_specific_cuda_index(monkeypatch):
    class _FakeTorch:
        class cuda:
            _count = 3

            @staticmethod
            def is_available():
                return True

            @classmethod
            def device_count(cls):
                return cls._count

    import sys
    original_torch = sys.modules.get("torch")
    sys.modules["torch"] = _FakeTorch  # type: ignore[assignment]
    try:
        assert _resolve_device("auto", cuda_index=0) == "cuda:0"
        assert _resolve_device("cuda", cuda_index=1) == "cuda:1"
        assert _resolve_device("cuda", cuda_index=2) == "cuda:2"
    finally:
        if original_torch is not None:
            sys.modules["torch"] = original_torch
        else:
            sys.modules.pop("torch", None)


def test_resolve_device_clamps_out_of_range(monkeypatch):
    class _FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return True

            @staticmethod
            def device_count():
                return 2

    import sys
    original_torch = sys.modules.get("torch")
    sys.modules["torch"] = _FakeTorch  # type: ignore[assignment]
    try:
        # Asking for cuda:5 on a 2-GPU host should fall back to cuda:0, not crash.
        assert _resolve_device("cuda", cuda_index=5) == "cuda:0"
    finally:
        if original_torch is not None:
            sys.modules["torch"] = original_torch
        else:
            sys.modules.pop("torch", None)


def test_resolve_device_parses_explicit_cuda_n_string(monkeypatch):
    class _FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return True

            @staticmethod
            def device_count():
                return 4

    import sys
    original_torch = sys.modules.get("torch")
    sys.modules["torch"] = _FakeTorch  # type: ignore[assignment]
    try:
        assert _resolve_device("cuda:2") == "cuda:2"
        # Malformed cuda_index in the string falls through to the kw default.
        assert _resolve_device("cuda:xyz", cuda_index=1) == "cuda:1"
    finally:
        if original_torch is not None:
            sys.modules["torch"] = original_torch
        else:
            sys.modules.pop("torch", None)


# --- list_available_devices ------------------------------------------------

def test_list_available_devices_always_includes_cpu():
    devices = list_available_devices()
    ids = [d["id"] for d in devices]
    assert "cpu" in ids
    # Every CUDA entry must carry an index so the UI can render a picker.
    for d in devices:
        if d["kind"] == "cuda":
            assert isinstance(d["index"], int)
            assert d["id"] == f"cuda:{d['index']}"


# --- REST surface: GET /api/v1/config/ml-devices --------------------------

@pytest.mark.asyncio
async def test_get_ml_devices_returns_available_and_current(client, auth_headers):
    resp = await client.get("/api/v1/config/ml-devices", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "available" in body and "current" in body
    assert any(d["id"] == "cpu" for d in body["available"])
    cur = body["current"]
    assert cur["ml_device"] in ("auto", "cpu", "cuda")
    assert isinstance(cur["ml_cuda_index"], int)
    assert "loaded" in cur
    assert "cpu_fallback" in cur


# --- REST surface: PUT /api/v1/config/feature-flags validation ------------

@pytest.mark.asyncio
async def test_feature_flags_validates_ml_device(client, auth_headers):
    # Invalid device string is rejected.
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_device": "mps"},
    )
    assert resp.status_code == 422

    # Valid device string is accepted and round-tripped.
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_device": "cpu", "ml_cuda_index": 0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ml_device"] == "cpu"
    assert body["ml_cuda_index"] == 0


@pytest.mark.asyncio
async def test_feature_flags_rejects_bad_cuda_index(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_cuda_index": -1},
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ml_cuda_index": 99},
    )
    assert resp.status_code == 422


# --- REST surface: POST /api/v1/config/ml-device/apply --------------------

@pytest.mark.asyncio
async def test_apply_ml_device_persists_and_unloads(client, auth_headers, monkeypatch):
    from app.services import ml_models as mm

    unload_calls = {"n": 0}

    def _fake_unload() -> None:
        unload_calls["n"] += 1

    monkeypatch.setattr(mm, "unload_ml_models", _fake_unload)
    monkeypatch.setattr(mm, "models_available", lambda: False)

    resp = await client.post(
        "/api/v1/config/ml-device/apply",
        headers=auth_headers,
        json={"ml_device": "cpu", "ml_cuda_index": 0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ml_device"] == "cpu"
    assert body["ml_cuda_index"] == 0
    assert body["effective_device"] == "cpu"
    assert body["reloaded"] is False
    assert body["loaded"] is False
    assert unload_calls["n"] == 1

    # The choice round-trips through feature-flags.
    follow = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert follow.status_code == 200
    assert follow.json()["ml_device"] == "cpu"
    assert follow.json()["ml_cuda_index"] == 0


@pytest.mark.asyncio
async def test_apply_ml_device_cuda_reports_indexed_effective(client, auth_headers, monkeypatch):
    from app.services import ml_models as mm

    monkeypatch.setattr(mm, "unload_ml_models", lambda: None)
    monkeypatch.setattr(mm, "models_available", lambda: False)

    resp = await client.post(
        "/api/v1/config/ml-device/apply",
        headers=auth_headers,
        json={"ml_device": "cuda", "ml_cuda_index": 2},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["effective_device"] == "cuda:2"


@pytest.mark.asyncio
async def test_apply_ml_device_rejects_bad_payload(client, auth_headers):
    resp = await client.post(
        "/api/v1/config/ml-device/apply",
        headers=auth_headers,
        json={"ml_device": "tpu"},
    )
    assert resp.status_code == 422
