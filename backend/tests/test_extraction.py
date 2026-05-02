import json

import httpx

from app.config import LLMPurposeConfig
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator


def _make_extraction_service(llm_response: dict):
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(llm_response)}}]
        })

    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model="test"),
        "extraction": LLMPurposeConfig(base_url="http://mock", model="test"),
        "reasoning": LLMPurposeConfig(base_url="http://mock", model="test"),
        "summarization": LLMPurposeConfig(base_url="http://mock", model="test"),
    }
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return ExtractionService(llm)


async def test_extract_entities():
    svc = _make_extraction_service({
        "entities": [
            {"name": "PostgreSQL", "type": "technology", "properties": {"version": "17"}},
            {"name": "darkmem", "type": "project", "properties": {}},
        ],
        "relationships": [
            {"source": "darkmem", "target": "PostgreSQL", "type": "USES", "properties": {}, "weight": 0.9},
        ],
        "memory_type": "architecture",
        "importance": 0.8,
    })

    result = await svc.extract("darkmem uses PostgreSQL 17 for its relational storage")
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "PostgreSQL"
    assert len(result["relationships"]) == 1
    assert result["memory_type"] == "architecture"
    assert result["importance"] == 0.8
    await svc.llm.close()


async def test_extract_handles_invalid_json():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "not valid json {{"}}]
        })

    config = {k: LLMPurposeConfig(base_url="http://mock", model="test") for k in ["embedding", "extraction", "reasoning", "summarization"]}
    llm = LLMOrchestrator(config)
    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    svc = ExtractionService(llm)

    result = await svc.extract("some text")
    assert result["entities"] == []
    assert result["relationships"] == []
    assert result["memory_type"] == "fact"
    await llm.close()


# --- _drop_uses_when_replaces_exists ----------------------------------


def test_drop_uses_when_replaces_present_same_direction():
    """The exact ``promtail USES grafana alloy`` false positive from real
    runs: REPLACES says ``grafana alloy REPLACES promtail``, the rescue
    layer adds ``promtail USES grafana alloy``. The USES should drop."""
    from app.services.extraction import _drop_uses_when_replaces_exists

    rels = [
        {"source": "grafana alloy", "target": "promtail", "type": "REPLACES"},
        {"source": "promtail", "target": "grafana alloy", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "REPLACES"


def test_drop_uses_when_replaces_present_reverse_direction():
    """Drop USES even when its source/target match REPLACES exactly,
    not just the swap. Pair-based dedup handles both directions."""
    from app.services.extraction import _drop_uses_when_replaces_exists

    rels = [
        {"source": "alloy", "target": "promtail", "type": "REPLACES"},
        {"source": "alloy", "target": "promtail", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "REPLACES"


def test_drop_uses_keeps_uses_when_no_replaces_for_pair():
    """A USES with no matching REPLACES survives untouched."""
    from app.services.extraction import _drop_uses_when_replaces_exists

    rels = [
        {"source": "darkmem", "target": "pgvector", "type": "USES"},
        {"source": "alloy", "target": "promtail", "type": "REPLACES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 2


def test_drop_uses_treats_improves_on_as_replaces_family():
    """IMPROVES_ON collapses to REPLACES in the 5-type schema, so it
    blocks USES dedup just like REPLACES does."""
    from app.services.extraction import _drop_uses_when_replaces_exists

    rels = [
        {"source": "alloy", "target": "promtail", "type": "IMPROVES_ON"},
        {"source": "promtail", "target": "alloy", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "IMPROVES_ON"


def test_dedup_by_target_predicate_keeps_highest_weight():
    """The exact failure mode from the dense memo: extractor emits
    both ``darkmem USES rrf`` (correct, high weight) and
    ``qwen3-embedding USES rrf`` (wrong subject, low weight). Dedup
    must keep the higher-weight one."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.7},
        {"source": "qwen3-embedding", "target": "rrf", "type": "USES", "weight": 0.6},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 1
    assert out[0]["source"] == "darkmem"
    assert out[0]["weight"] == 0.7


def test_dedup_by_target_predicate_keeps_distinct_predicates():
    """A target with two distinct predicates from different sources
    should NOT be merged — they describe different relationships."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "darkmem", "target": "pgvector", "type": "USES", "weight": 0.8},
        {"source": "alloy", "target": "pgvector", "type": "DEPENDS_ON", "weight": 0.6},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 2


def test_dedup_by_target_predicate_passes_through_partial_rows():
    """Rows missing source/target/type should not be touched so other
    extractor paths producing partial data don't get silently dropped."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.7},
        {"source": "", "target": "rrf", "type": "USES", "weight": 0.9},  # missing source
    ]
    out = _dedup_by_target_predicate(rels)
    # The partial row goes through untouched; the well-formed row is kept.
    assert len(out) == 2


# --- Rescue-prefer tie-break (production fix for direction-sensitive predicates) ---


def test_dedup_prefers_rescue_tagged_over_non_tagged_replaces():
    """The exact bug from the glm-4.5-flash extraction memo: LLM emits
    ``darkmem REPLACES qdrant`` (wrong subject, weight 0.9) while the
    rescue layer's pattern A emits ``pgvector REPLACES qdrant`` (correct
    subject, weight 0.85, properties.rescue=True). The prior dedup kept
    the higher-weight LLM emission and silently dropped the correct one.
    The rescue-prefer tie-break flips this so the regex-grounded triple
    wins regardless of weight."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "darkmem", "target": "qdrant", "type": "REPLACES", "weight": 0.9},
        {"source": "pgvector", "target": "qdrant", "type": "REPLACES", "weight": 0.85,
         "properties": {"rescue": True}},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 1
    assert out[0]["source"] == "pgvector"
    assert out[0].get("properties", {}).get("rescue") is True


def test_dedup_falls_back_to_weight_when_no_rescue_tag():
    """The original USES anchoring fix is preserved: when neither
    candidate is rescue-tagged, the higher-weight triple still wins."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "darkmem", "target": "rrf", "type": "USES", "weight": 0.7},
        {"source": "qwen3-embedding", "target": "rrf", "type": "USES", "weight": 0.5},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 1
    assert out[0]["source"] == "darkmem"


def test_dedup_falls_back_to_weight_when_both_rescue_tagged():
    """When both candidates are rescue-tagged (rare but possible if two
    rescue patterns fire on the same pair), the higher-weight one
    wins."""
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        {"source": "x", "target": "y", "type": "USES", "weight": 0.6,
         "properties": {"rescue": True}},
        {"source": "z", "target": "y", "type": "USES", "weight": 0.8,
         "properties": {"rescue": True}},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 1
    assert out[0]["source"] == "z"


import pytest


@pytest.mark.parametrize(
    "predicate",
    ["REPLACES", "IMPLEMENTS", "EXTENDS", "DEPLOYED_ON", "AUTHORED_BY",
     "CAUSES", "HAS_PART", "DEPENDS_ON", "INSPIRED_BY"],
)
def test_dedup_rescue_preference_generic_across_direction_sensitive_predicates(predicate):
    """Direction-sensitive predicates carry their semantic in the
    source. When a rescue layer pattern-matches one and the LLM emits
    a wrong-direction sibling, the rescue triple must win regardless
    of weight. Parametrized to cover the whole class — even if a given
    rescue path doesn't exist today, the policy is uniform.
    """
    from app.services.extraction import _dedup_by_target_predicate

    rels = [
        # LLM emission with wrong subject, high weight.
        {"source": "wrong-source", "target": "shared-target",
         "type": predicate, "weight": 0.95},
        # Rescue emission with correct subject, lower weight.
        {"source": "correct-source", "target": "shared-target",
         "type": predicate, "weight": 0.7,
         "properties": {"rescue": True}},
    ]
    out = _dedup_by_target_predicate(rels)
    assert len(out) == 1
    assert out[0]["source"] == "correct-source", (
        f"rescue-tagged triple should win for {predicate} regardless of weight"
    )


def test_strip_json_fences_handles_anthropic_markdown_wrapping():
    """Anthropic's OpenAI-compat shim does not accept
    ``response_format=json_object`` so extraction runs without a
    JSON-mode hint against Anthropic, and the model sometimes wraps
    JSON in a markdown code fence. The parser must strip the fence
    so json.loads succeeds.
    """
    from app.services.extraction import _strip_json_fences

    fenced = '```json\n{"entities": [], "relationships": []}\n```'
    assert _strip_json_fences(fenced) == '{"entities": [], "relationships": []}'

    bare_fence = '```\n{"x": 1}\n```'
    assert _strip_json_fences(bare_fence) == '{"x": 1}'

    no_fence = '{"x": 1}'
    assert _strip_json_fences(no_fence) == '{"x": 1}'

    surrounded_whitespace = '   ```json\n{"x": 1}\n```\n  '
    assert _strip_json_fences(surrounded_whitespace) == '{"x": 1}'


def test_filter_noise_drops_year_month_dates():
    """Bare year-month strings like ``2026-04`` are values, not entities.
    Bug: the original ``_VALUE_PATTERN`` only matched the full
    ``YYYY-MM-DD`` form, so the LLM was extracting ``2026-04`` as a
    ``concept`` and a downstream rescue pattern dragged it into a
    ``DEPLOYED_ON 2026-04`` triple. Fixed by extending the pattern to
    year-month and bare year forms."""
    from app.services.extraction import _filter_noise

    raw = [
        {"name": "2026-04", "type": "concept", "properties": {}},
        {"name": "2026-04-30", "type": "concept", "properties": {}},
        {"name": "2026", "type": "concept", "properties": {}},
        {"name": "darkmem", "type": "project", "properties": {}},
    ]
    out = _filter_noise(raw)
    names = {e["name"] for e in out}
    assert names == {"darkmem"}


def test_drop_uses_self_loop_ignored():
    """A self-loop REPLACES (degenerate) doesn't block any USES."""
    from app.services.extraction import _drop_uses_when_replaces_exists

    rels = [
        {"source": "alloy", "target": "alloy", "type": "REPLACES"},
        {"source": "darkmem", "target": "alloy", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 2
