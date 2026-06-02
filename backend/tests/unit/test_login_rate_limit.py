"""Unit tests for the in-process login rate limiter."""
from __future__ import annotations

from app.services.login_rate_limit import LoginRateLimiter


def _limiter(**kw):
    t = {"now": 0.0}
    kw.setdefault("clock", lambda: t["now"])
    return LoginRateLimiter(**kw), t


def test_not_limited_before_threshold():
    rl, _ = _limiter(max_failures=3, lockout_seconds=60)
    rl.record_failure("ip")
    rl.record_failure("ip")
    assert rl.retry_after("ip") is None


def test_locks_after_max_failures():
    rl, _ = _limiter(max_failures=3, lockout_seconds=60)
    for _ in range(3):
        rl.record_failure("ip")
    ra = rl.retry_after("ip")
    assert ra is not None and ra > 0


def test_lockout_expires_after_cooldown():
    rl, t = _limiter(max_failures=2, lockout_seconds=60)
    rl.record_failure("ip")
    rl.record_failure("ip")
    assert rl.retry_after("ip") is not None
    t["now"] = 61.0
    assert rl.retry_after("ip") is None


def test_success_clears_failures():
    rl, _ = _limiter(max_failures=2, lockout_seconds=60)
    rl.record_failure("ip")
    rl.record_success("ip")
    rl.record_failure("ip")
    assert rl.retry_after("ip") is None


def test_failures_outside_window_are_pruned():
    rl, t = _limiter(max_failures=3, window_seconds=10, lockout_seconds=60)
    rl.record_failure("ip")  # t=0
    t["now"] = 20.0
    rl.record_failure("ip")  # prunes the t=0 failure
    rl.record_failure("ip")
    assert rl.retry_after("ip") is None  # only 2 within the window


def test_per_ip_isolation():
    rl, _ = _limiter(max_failures=2, lockout_seconds=60)
    rl.record_failure("a")
    rl.record_failure("a")
    assert rl.retry_after("a") is not None
    assert rl.retry_after("b") is None
