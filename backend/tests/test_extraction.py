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
