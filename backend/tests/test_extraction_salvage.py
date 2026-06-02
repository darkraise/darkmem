"""Extraction must survive reasoning-vendor response envelopes.

Reasoning-by-default vendors prepend chain-of-thought prose, wrap the JSON in a
fence that is not at position 0, or double-fence it. A single ``json.loads`` of
a position-0-only fence stripper turns all of these into a parse error and an
empty graph — and the deterministic per-content seed makes a reprocess fail
identically, so the gap never self-heals. These tests pin a brace-balanced
salvage plus a fence-anywhere stripper.
"""
from __future__ import annotations

import json

import httpx

from app.config import LLMPurposeConfig
from app.services.extraction import (
    ExtractionService,
    _salvage_json_object,
    _strip_json_fences,
)
from app.services.llm import LLMOrchestrator

_VALID = {
    "entities": [{"name": "PostgreSQL", "type": "technology", "properties": {}}],
    "relationships": [],
    "memory_type": "fact",
    "importance": 0.5,
}


def _make_service(raw_content: str) -> ExtractionService:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": raw_content}}]}
        )

    config = {
        p: LLMPurposeConfig(base_url="http://mock", model="test")
        for p in ("embedding", "extraction", "reasoning", "summarization")
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExtractionService(llm)


# ── extract()-level behaviour ─────────────────────────────────────────


async def test_extract_recovers_prose_prepended_fenced_json():
    raw = "Here is the JSON you asked for:\n```json\n" + json.dumps(_VALID) + "\n```"
    result = await _make_service(raw).extract("postgres note")
    assert not result.get("_error")
    assert any(e["name"] == "PostgreSQL" for e in result["entities"])


async def test_extract_recovers_prose_prepended_bare_json():
    raw = "Sure, here you go: " + json.dumps(_VALID) + " — let me know if you need more."
    result = await _make_service(raw).extract("postgres note")
    assert not result.get("_error")
    assert any(e["name"] == "PostgreSQL" for e in result["entities"])


async def test_extract_still_reports_error_on_unrecoverable_response():
    result = await _make_service("I could not produce JSON for this.").extract("x")
    assert result.get("_error")
    assert result["entities"] == []


# ── helper unit tests ─────────────────────────────────────────────────


def test_strip_json_fences_finds_fence_after_prose():
    raw = "blah blah\n```json\n{\"a\": 1}\n```"
    assert json.loads(_strip_json_fences(raw)) == {"a": 1}


def test_strip_json_fences_noop_for_plain_json():
    assert json.loads(_strip_json_fences('{"a": 1}')) == {"a": 1}


def test_salvage_extracts_first_balanced_object_ignoring_braces_in_strings():
    raw = 'prefix {"k": "a } b", "n": {"d": 1}} trailing'
    salvaged = _salvage_json_object(raw)
    assert json.loads(salvaged) == {"k": "a } b", "n": {"d": 1}}


def test_salvage_returns_none_without_an_object():
    assert _salvage_json_object("no json here") is None
