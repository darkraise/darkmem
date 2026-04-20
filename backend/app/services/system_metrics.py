"""Host-level CPU/RAM/GPU metrics with graceful degradation.

`psutil` and `pynvml` imports and NVML init happen once at module load.
If either is unavailable (or pynvml init raises on a non-Nvidia host),
the corresponding fields in `snapshot()` return None and the rest of the
snapshot still works.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import psutil as _PSUTIL
    # psutil.cpu_percent's first non-blocking call always returns 0.0;
    # prime it here so the first snapshot() reports a real number.
    _PSUTIL.cpu_percent(interval=None)
except Exception as exc:
    logger.warning("psutil unavailable: %s", exc)
    _PSUTIL = None

try:
    import pynvml as _NVML
    _NVML.nvmlInit()
    _NVML_HANDLE = _NVML.nvmlDeviceGetHandleByIndex(0)
except Exception as exc:
    logger.warning("pynvml unavailable or no Nvidia device: %s", exc)
    _NVML = None
    _NVML_HANDLE = None


def snapshot() -> dict:
    """Return a one-shot read of host CPU/RAM and GPU util/VRAM.

    All fields are None when their source is unavailable. Numbers are
    reported in whole megabytes for byte-sized values; percents are 0-100.
    """
    out: dict = {
        "cpu_percent": None,
        "ram_used_mb": None,
        "ram_total_mb": None,
        "gpu_util_percent": None,
        "vram_used_mb": None,
        "vram_total_mb": None,
    }
    if _PSUTIL is not None:
        try:
            out["cpu_percent"] = float(_PSUTIL.cpu_percent(interval=None))
            vm = _PSUTIL.virtual_memory()
            out["ram_used_mb"] = int(vm.used // (1024 * 1024))
            out["ram_total_mb"] = int(vm.total // (1024 * 1024))
        except Exception:
            logger.exception("psutil snapshot failed")

    if _NVML is not None and _NVML_HANDLE is not None:
        try:
            util = _NVML.nvmlDeviceGetUtilizationRates(_NVML_HANDLE)
            mem = _NVML.nvmlDeviceGetMemoryInfo(_NVML_HANDLE)
            out["gpu_util_percent"] = int(util.gpu)
            out["vram_used_mb"] = int(mem.used // (1024 * 1024))
            out["vram_total_mb"] = int(mem.total // (1024 * 1024))
        except Exception:
            logger.exception("pynvml snapshot failed")

    return out
