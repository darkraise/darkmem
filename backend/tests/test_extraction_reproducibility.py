"""Extraction determinism, and the one non-identity that is correct.

The seed is ``sha256(content)[:8]`` as a 32-bit int, forwarded on every
extraction call, so the same content under the same Phase-2 gate state
reproduces (doc 17 §7).

**The caveat, recorded here rather than papered over:** re-extracting the same
content under a *different* gate state — a ``classification_mode`` flip, or
``classifier_kind`` set or cleared — is **not** bit-identical even with the same
seed, because the gate changes the request the model sees. That non-identity is
expected behaviour, not a bug and not a broken seed: the seed is unchanged
across the flip, and only the user message differs. A future agent finding a
non-reproduction across a gate flip should confirm it looks like the assertions
below before treating it as a defect (CLAUDE.md "Pipeline phases" §2, doc 05 §6,
doc 11 §5).
"""
import sys
from pathlib import Path

import pytest

from app.services.extraction import ExtractionService
from app.services.extraction_clean import _content_seed

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "extraction_bench"))
from run_bench import request_cache_key  # noqa: E402

CONTENT = "darkmem uses pgvector for the HNSW index and RRF for hybrid search."
OTHER_CONTENT = "The Leiden algorithm improves on Louvain for code graph clustering."


def _build(content, with_classification):
    return ExtractionService.build_extraction_request(
        content, with_classification=with_classification,
    )


@pytest.mark.parametrize("with_classification", [False, True])
def test_same_content_and_gate_state_reproduces(with_classification):
    first = _build(CONTENT, with_classification)
    second = _build(CONTENT, with_classification)
    assert first.messages == second.messages
    assert first.seed == second.seed


def test_flipped_gate_state_differs_in_the_prompt_not_the_seed():
    extract_only = _build(CONTENT, False)
    merged = _build(CONTENT, True)
    assert extract_only.messages[1]["content"] != merged.messages[1]["content"]
    assert extract_only.messages[0] == merged.messages[0]
    assert extract_only.seed == merged.seed


def test_seed_is_derived_from_content_and_nothing_else():
    assert _build(CONTENT, False).seed == _build(CONTENT, True).seed == _content_seed(CONTENT)
    assert _build(OTHER_CONTENT, False).seed != _build(CONTENT, False).seed


def test_bench_cache_key_separates_gate_states():
    assert request_cache_key(_build(CONTENT, False)) != request_cache_key(_build(CONTENT, True))
    assert request_cache_key(_build(CONTENT, False)) == request_cache_key(_build(CONTENT, False))
