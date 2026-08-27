"""The prompt-override cap must admit every prompt it is meant to override.

A cap below the largest shipped default makes the editing feature unusable
for exactly the prompt most worth tuning: copy the default, edit it, save,
422.
"""
from __future__ import annotations

from app.api.routes.config import PROMPT_OVERRIDE_MAX_CHARS
from app.services import prompt


def test_the_cap_admits_every_shipped_default():
    largest = max(len(v) for v in prompt.PROMPTS.values())
    assert PROMPT_OVERRIDE_MAX_CHARS > largest, (
        f"cap {PROMPT_OVERRIDE_MAX_CHARS} rejects the largest default ({largest})"
    )


def test_the_cap_is_still_a_bound():
    """Raising it must not mean removing it - the guard against storing a
    500KB blob that would blow a small-context model's budget still stands."""
    assert PROMPT_OVERRIDE_MAX_CHARS < 500_000
