"""The one place application-generated UUIDs are minted.

Doc 04 §2 makes every application-generated uuid primary key a **UUIDv7**:
time-ordered, so B-tree inserts stay local instead of fragmenting the index the
way v4's randomness does. `entities` and `entity_relations` are the deliberate
exceptions — they keep server-side `gen_random_uuid()` because they are
ANN-probed and sweep-churned rather than range-scanned, so insert locality buys
them nothing.

**Why the `uuid6` package rather than the stdlib.** `uuid.uuid7` landed in
CPython 3.14; `pyproject.toml` pins `requires-python = ">=3.12"` and this
environment runs 3.13. Raising that floor is a toolchain migration — the Docker
image, a universal lock regeneration, and a 3.14 wheel for every dependency
including the twenty-odd tree-sitter grammars — which is a great deal of blast
radius to buy one function. This module is the only call site, so when the floor
does move the swap is one import.
"""
from __future__ import annotations

import uuid

from uuid6 import uuid7


def new_id() -> uuid.UUID:
    """Mint a time-ordered UUIDv7.

    Callers that need the id *before* the row exists — capture mints one at
    accept so a 202 can hand the caller a real handle — take it from here and
    carry that exact value through to the row.
    """
    return uuid7()
