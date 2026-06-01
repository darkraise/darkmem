"""Unit tests for the cron parsing helpers on JobRegistry."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.job_registry import (
    Job,
    JobConfig,
    is_valid_cron,
    next_fire_delta_seconds,
)


def test_is_valid_cron_accepts_five_field():
    assert is_valid_cron("*/5 * * * *") is True
    assert is_valid_cron("0 0 * * *") is True
    assert is_valid_cron("0 9-17 * * 1-5") is True


def test_is_valid_cron_accepts_six_field_with_seconds():
    assert is_valid_cron("*/10 * * * * *") is True
    assert is_valid_cron("0 0 0 * * *") is True


def test_is_valid_cron_rejects_garbage():
    assert is_valid_cron("not a cron") is False
    assert is_valid_cron("") is False
    assert is_valid_cron("60 * * * *") is False  # minute > 59


def test_next_fire_delta_respects_floor():
    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("*/1 * * * * *", now, floor=10)
    assert delta >= 10


def test_next_fire_delta_minute_precision():
    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("*/5 * * * *", now, floor=1)
    assert 0 < delta <= 300


def test_next_fire_delta_hourly():
    now = datetime(2026, 5, 3, 12, 30, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds("0 * * * *", now, floor=1)
    assert 1750 <= delta <= 1850


def test_job_config_round_trip():
    cfg = JobConfig(
        enabled=True,
        cron="*/5 * * * *",
        min_interval_seconds=30,
    )
    serialised = cfg.to_dict()
    restored = JobConfig.from_dict(serialised)
    assert restored.enabled is True
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 30


def test_job_config_from_dict_supplies_defaults():
    restored = JobConfig.from_dict({})
    assert restored.cron == "*/5 * * * *"
    assert restored.min_interval_seconds == 1


def test_job_config_round_trips_config_dict():
    from app.services.job_registry import JobConfig

    cfg = JobConfig(enabled=True, cron="*/5 * * * *", min_interval_seconds=1,
                    config={"batch_size": 17})
    assert cfg.to_dict()["config"] == {"batch_size": 17}
    assert JobConfig.from_dict(cfg.to_dict()).config == {"batch_size": 17}


def test_job_config_from_dict_defaults_config_to_empty():
    from app.services.job_registry import JobConfig

    cfg = JobConfig.from_dict({"enabled": True, "cron": "*/5 * * * *",
                               "min_interval_seconds": 1})
    assert cfg.config == {}


def test_job_register_rejects_invalid_default_cron():
    from app.services.job_registry import JobRegistry

    async def _noop():
        return None

    registry = JobRegistry(session_factory=lambda: None)  # session unused for this path
    with pytest.raises(ValueError, match="not a valid"):
        registry.register(Job(
            key="bad",
            display_name="Bad",
            description="",
            default_cron="garbage",
            min_interval_seconds=1,
            runner=_noop,
        ))
