"""The chat cache key folds what changes the answer, and nothing else.

G-C's clear rests on an independent party replaying a run byte-identically at
zero live calls. Any argument that varies per run and reaches the key destroys
that property silently -- the replay simply misses every entry and calls the
vendor, which looks like a cold cache rather than like a bug.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchlib.caching_llm import CachingLLMOrchestrator


def _orch(tmp_path):
    return CachingLLMOrchestrator({}, cache_dir=str(tmp_path))


def test_the_attribution_subject_does_not_fork_the_cache(tmp_path):
    """Two memories with identical content pay for identical calls. Keying on
    which memory paid would give a fresh corpus a fresh key for every entry."""
    o = _orch(tmp_path)
    messages = [{"role": "user", "content": "same text"}]
    a = o._chat_key("extraction", messages,
                    {"usage_subject": ("memory", "id-a", "proj")})
    b = o._chat_key("extraction", messages,
                    {"usage_subject": ("memory", "id-b", "proj")})
    assert a == b


def test_a_metering_note_does_not_fork_the_cache(tmp_path):
    o = _orch(tmp_path)
    messages = [{"role": "user", "content": "same text"}]
    assert o._chat_key("extraction", messages, {}) == o._chat_key(
        "extraction", messages, {"usage_extra": {"merged_classification": True}}
    )


def test_an_argument_that_changes_the_request_still_forks_the_cache(tmp_path):
    """The exclusion is a named list, not a general 'ignore what I do not
    recognise': a kwarg the vendor sees must keep its own entry."""
    o = _orch(tmp_path)
    messages = [{"role": "user", "content": "same text"}]
    assert o._chat_key("extraction", messages, {"seed": 1}) != o._chat_key(
        "extraction", messages, {"seed": 2}
    )
    assert o._chat_key("extraction", messages, {}) != o._chat_key(
        "extraction", messages, {"response_format": {"type": "json_object"}}
    )
