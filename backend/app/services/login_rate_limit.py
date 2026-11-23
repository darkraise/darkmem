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
from typing import Callable, Literal, NamedTuple


RefusalGate = Literal["failures", "in_flight"]
REFUSED_FAILURES: RefusalGate = "failures"
REFUSED_IN_FLIGHT: RefusalGate = "in_flight"


class LoginRefusal(NamedTuple):
    retry_after: int
    gate: RefusalGate


class LoginRateLimiter:
    # Scope is one process: the failure map lives in this instance's memory and
    # is not shared across workers or replicas (a multi-process / HA deployment
    # would back it with Redis). The ``ip`` key is supplied by the caller —
    # auth.py's ``_client_ip`` derives it from whichever posture is configured
    # (the transport peer by default, or a trusted proxy's own view when
    # ``trust_proxy_headers`` is on) — so this class never inspects the
    # request itself.
    # Cap on tracked IPs. The key space is hostile (every spoofable
    # X-Forwarded-For value), so sweep expired entries once the map grows past
    # this rather than letting it accumulate one permanent entry per IP that
    # ever failed a single login and then went quiet.
    _MAX_TRACKED: int = 10_000

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
        # ip -> {"failures": list[float], "locked_until": float, "in_flight": int}
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

    def acquire(self, ip: str) -> LoginRefusal | None:
        """Reserve an attempt slot for ``ip``, or return the 429's Retry-After
        and the gate that refused.

        Called before the handler's first ``await``: attempts already in flight
        count against the threshold, so concurrent guesses cannot all pass a
        gate that only sees failures recorded so far. Every ``None`` must be
        paired with one :meth:`release`.
        """
        locked = self.retry_after(ip)
        if locked is not None:
            return LoginRefusal(locked, REFUSED_FAILURES)
        now = self._clock()
        self._maybe_sweep(now)
        st = self._state.setdefault(ip, {"failures": [], "locked_until": 0.0})
        st["failures"] = [t for t in st["failures"] if now - t < self.window_seconds]
        in_flight = st.get("in_flight", 0)
        if len(st["failures"]) + in_flight >= self.max_failures:
            return LoginRefusal(1, REFUSED_IN_FLIGHT if in_flight else REFUSED_FAILURES)
        st["in_flight"] = in_flight + 1
        return None

    def release(self, ip: str) -> None:
        st = self._state.get(ip)
        if not st:
            return
        st["in_flight"] = max(0, st.get("in_flight", 0) - 1)
        if not st["in_flight"] and not st["failures"] and st.get("locked_until", 0.0) <= self._clock():
            self._state.pop(ip, None)

    def in_flight(self, ip: str) -> int:
        st = self._state.get(ip)
        return st.get("in_flight", 0) if st else 0

    def record_failure(self, ip: str) -> None:
        now = self._clock()
        self._maybe_sweep(now)
        st = self._state.setdefault(ip, {"failures": [], "locked_until": 0.0})
        st["failures"] = [t for t in st["failures"] if now - t < self.window_seconds]
        st["failures"].append(now)
        if len(st["failures"]) >= self.max_failures:
            st["locked_until"] = now + self.lockout_seconds
            st["failures"] = []

    def record_success(self, ip: str) -> None:
        st = self._state.get(ip)
        if st is None:
            return
        if st.get("in_flight", 0):
            st["failures"] = []
            st["locked_until"] = 0.0
        else:
            self._state.pop(ip, None)

    def _maybe_sweep(self, now: float) -> None:
        """Drop entries whose lockout has passed and whose failures have all
        aged out of the window. Runs only once the map exceeds the cap, so the
        common path stays O(1)."""
        if len(self._state) <= self._MAX_TRACKED:
            return
        stale = [
            ip
            for ip, st in self._state.items()
            if st.get("locked_until", 0.0) <= now
            and not st.get("in_flight", 0)
            and not any(now - t < self.window_seconds for t in st.get("failures", ()))
        ]
        for ip in stale:
            self._state.pop(ip, None)

    def reset(self) -> None:
        """Test hook: drop all tracked state."""
        self._state.clear()


login_rate_limiter = LoginRateLimiter()
