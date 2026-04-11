"""Reusable assertion helpers for darkmem E2E scripts."""

from __future__ import annotations

from typing import Any

import httpx


def assert_status(r: httpx.Response, expected: int, label: str) -> bool:
    """Return True if status matches, otherwise print and return False."""
    if r.status_code == expected:
        return True
    print(f"  [FAIL] {label}: expected {expected}, got {r.status_code} - {r.text[:200]}")
    return False


def assert_json_key(data: dict, key: str, label: str) -> bool:
    if key in data:
        return True
    print(f"  [FAIL] {label}: missing key '{key}' in {list(data.keys())}")
    return False


def assert_eq(actual: Any, expected: Any, label: str) -> bool:
    if actual == expected:
        return True
    print(f"  [FAIL] {label}: expected {expected!r}, got {actual!r}")
    return False


def assert_nonempty(value: Any, label: str) -> bool:
    if value:
        return True
    print(f"  [FAIL] {label}: value is empty ({value!r})")
    return False


def assert_ge(actual: float, minimum: float, label: str) -> bool:
    if actual >= minimum:
        return True
    print(f"  [FAIL] {label}: {actual} < {minimum}")
    return False


def assert_le(actual: float, maximum: float, label: str) -> bool:
    if actual <= maximum:
        return True
    print(f"  [FAIL] {label}: {actual} > {maximum}")
    return False
