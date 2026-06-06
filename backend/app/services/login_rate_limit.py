"""In-process per-IP login rate limiter.

The whole system authenticates against one admin password, so unlimited
attempts make it brute-forceable over the network (the deployment is a shared
LAN per the contract). bcrypt slows each guess but does not bound the attempt
rate. This adds a per-IP failure counter with a short lockout after a threshold.

State is in-memory, which suits the single-process deployment; a multi-process
or HA deployment would back this with Redis instead.
"""
from __future__ import annotations

import time
from typing import Callable


class LoginRateLimiter:
    # Scope is one process: the failure map lives in this instance's memory and
    # is not shared across workers or replicas (a multi-process / HA deployment
    # would back it with Redis). The ``ip`` key is supplied by the caller —
    # auth.py's ``_client_ip`` derives it proxy-aware (honoring a trusted
    # X-Forwarded-For) — so this class never inspects the request itself.
    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 300.0,
        lockout_seconds: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        # ip -> {"failures": list[float], "locked_until": float}
        self._state: dict[str, dict] = {}

    def retry_after(self, ip: str) -> int | None:
        """Seconds until ``ip`` may try again, or None when not locked out."""
        st = self._state.get(ip)
        if not st:
            return None
        remaining = st.get("locked_until", 0.0) - self._clock()
        if remaining > 0:
            return int(remaining) + 1
        return None

    def record_failure(self, ip: str) -> None:
        now = self._clock()
        st = self._state.setdefault(ip, {"failures": [], "locked_until": 0.0})
        st["failures"] = [t for t in st["failures"] if now - t < self.window_seconds]
        st["failures"].append(now)
        if len(st["failures"]) >= self.max_failures:
            st["locked_until"] = now + self.lockout_seconds
            st["failures"] = []

    def record_success(self, ip: str) -> None:
        self._state.pop(ip, None)

    def reset(self) -> None:
        """Test hook: drop all tracked state."""
        self._state.clear()


login_rate_limiter = LoginRateLimiter()
