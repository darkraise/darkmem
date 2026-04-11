"""Shared HTTP client for darkmem E2E scripts.

Handles session cookies, base URL, and common error handling.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = os.environ.get("DARKMEM_BASE_URL", "http://localhost:8000")
DEFAULT_PASSWORD = os.environ.get("DARKMEM_PASSWORD", "e2e-admin-pw")


@dataclass
class E2EArgs:
    base_url: str
    password: str
    setup: bool
    verbose: bool


def parse_args(description: str = "darkmem E2E script") -> E2EArgs:
    """Parse common CLI args used by every script."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--base-url", default=DEFAULT_BASE_URL,
                   help=f"Backend base URL (default {DEFAULT_BASE_URL})")
    p.add_argument("--password", default=DEFAULT_PASSWORD,
                   help="Admin password")
    p.add_argument("--setup", action="store_true",
                   help="Run first-time admin setup before other actions")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Print request/response details")
    a = p.parse_args()
    return E2EArgs(
        base_url=a.base_url.rstrip("/"),
        password=a.password,
        setup=a.setup,
        verbose=a.verbose,
    )


class DarkmemClient:
    """Auth-aware HTTP client. Login once, reuse for the whole script.

    Usage:
        client = DarkmemClient(args.base_url, args.password)
        await client.login()
        r = await client.get("/api/v1/memories")
    """

    def __init__(self, base_url: str, password: str, verbose: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.password = password
        self.verbose = verbose
        self._client = httpx.AsyncClient(timeout=180.0, follow_redirects=False)
        self._cookie: str | None = None

    async def __aenter__(self) -> "DarkmemClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    # ---------- auth ----------

    async def auth_status(self) -> dict:
        r = await self._client.get(f"{self.base_url}/api/v1/auth/status")
        r.raise_for_status()
        return r.json()

    async def setup(self) -> None:
        r = await self._client.post(
            f"{self.base_url}/api/v1/auth/setup",
            json={"password": self.password},
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Setup failed ({r.status_code}): {r.text}")
        self._cookie = r.cookies.get("darkmem_session")
        if not self._cookie:
            raise RuntimeError("Setup did not return a session cookie")
        if self.verbose:
            print(f"  [setup] ok, cookie set")

    async def login(self) -> None:
        status = await self.auth_status()
        if not status.get("initialized"):
            if self.verbose:
                print("  [login] not initialized, running setup first")
            await self.setup()
            return
        r = await self._client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"password": self.password},
        )
        if r.status_code != 200:
            raise RuntimeError(f"Login failed ({r.status_code}): {r.text}")
        self._cookie = r.cookies.get("darkmem_session")
        if not self._cookie:
            raise RuntimeError("Login did not return a session cookie")
        if self.verbose:
            print(f"  [login] ok, cookie set")

    def cookies(self) -> dict[str, str]:
        return {"darkmem_session": self._cookie} if self._cookie else {}

    # ---------- HTTP helpers ----------

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self._request("DELETE", path, **kwargs)

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        cookies = kwargs.pop("cookies", self.cookies())
        if self.verbose:
            print(f"  [{method}] {url}")
        r = await self._client.request(method, url, cookies=cookies, **kwargs)
        if self.verbose:
            print(f"    -> {r.status_code}")
        return r


class TestReport:
    """Collects pass/fail results for a single phase script."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.passes: list[str] = []
        self.failures: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def ok(self, label: str) -> None:
        self.passes.append(label)
        print(f"  [PASS] {label}")

    def fail(self, label: str, detail: str = "") -> None:
        self.failures.append((label, detail))
        print(f"  [FAIL] {label}" + (f" - {detail}" if detail else ""))

    def warn(self, label: str) -> None:
        self.warnings.append(label)
        print(f"  [WARN] {label}")

    def summary(self) -> int:
        """Print summary and return exit code (0 if all pass)."""
        print()
        print(f"=== {self.name} ===".encode("ascii", "replace").decode("ascii"))
        print(f"  {len(self.passes)} passed, {len(self.failures)} failed, {len(self.warnings)} warnings")
        if self.failures:
            print("  Failures:")
            for label, detail in self.failures:
                print(f"    - {label}: {detail}")
        return 1 if self.failures else 0
