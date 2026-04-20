import pytest
from unittest.mock import patch, MagicMock

from app.services import system_metrics


def test_snapshot_without_psutil_returns_nulls(monkeypatch):
    monkeypatch.setattr(system_metrics, "_PSUTIL", None)
    monkeypatch.setattr(system_metrics, "_NVML_HANDLE", None)
    snap = system_metrics.snapshot()
    assert snap["cpu_percent"] is None
    assert snap["ram_used_mb"] is None
    assert snap["ram_total_mb"] is None
    assert snap["gpu_util_percent"] is None
    assert snap["vram_used_mb"] is None
    assert snap["vram_total_mb"] is None


def test_snapshot_with_mocked_psutil():
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent.return_value = 42.0
    fake_vm = MagicMock(used=8 * 1024 * 1024 * 1024, total=32 * 1024 * 1024 * 1024)
    fake_psutil.virtual_memory.return_value = fake_vm
    with patch.object(system_metrics, "_PSUTIL", fake_psutil):
        snap = system_metrics.snapshot()
    assert snap["cpu_percent"] == 42.0
    assert snap["ram_used_mb"] == 8192
    assert snap["ram_total_mb"] == 32768


def test_snapshot_with_mocked_nvml():
    fake_handle = object()
    fake_nvml = MagicMock()
    fake_nvml.nvmlDeviceGetUtilizationRates.return_value = MagicMock(gpu=73)
    fake_nvml.nvmlDeviceGetMemoryInfo.return_value = MagicMock(
        used=6 * 1024 * 1024 * 1024, total=12 * 1024 * 1024 * 1024
    )
    with patch.object(system_metrics, "_NVML", fake_nvml), \
         patch.object(system_metrics, "_NVML_HANDLE", fake_handle):
        snap = system_metrics.snapshot()
    assert snap["gpu_util_percent"] == 73
    assert snap["vram_used_mb"] == 6144
    assert snap["vram_total_mb"] == 12288
