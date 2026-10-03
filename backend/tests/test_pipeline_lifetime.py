from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.config import LLMPurposeConfig
from app.services.llm import LLMOrchestrator
from tests.test_pipeline_savepoints import savepoint_bed


async def orchestrator(model, calls):
    config = {
        "embedding": LLMPurposeConfig(base_url="http://mock", model=model, dimensions=4),
        "extraction": LLMPurposeConfig(base_url="http://mock", model=f"{model}-extraction"),
        "classification": LLMPurposeConfig(base_url="http://mock", model=f"{model}-classification"),
    }
    llm = LLMOrchestrator(config)
    await llm._client.aclose()

    def handle(request):
        body = json.loads(request.content)
        calls.append(body["model"])
        if "input" in body:
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            return httpx.Response(200, json={"data": [{"index": index, "embedding": [1.0, 0.0, 0.0, 0.0]} for index, value in enumerate(inputs)]})
        payload = {"entities": [], "relationships": [], "memory_type": "fact", "type": "fact", "summary": "captured", "emotions": [], "flags": []}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})

    llm._client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    return llm


@pytest.mark.parametrize("operation", ["batch", "search"])
@pytest.mark.parametrize("outcome", ["success", "cancel", "error"])
async def test_pipeline_pins_generation_before_first_dispatch(setup_database, monkeypatch, operation, outcome):
    import app.services.feature_flags as feature_flags
    import app.services.pipeline as pipeline_module

    calls = []
    old = await orchestrator("pinned-pipeline", calls)
    new = await orchestrator("replacement-pipeline", calls)
    captured = asyncio.Event()
    proceed = asyncio.Event()
    real_flags = pipeline_module._get_feature_flags_cached if operation == "batch" else feature_flags.get_feature_flags_dict

    async def delayed_flags(source):
        captured.set()
        await proceed.wait()
        if outcome == "error":
            raise RuntimeError("flag lookup failed")
        flags = await real_flags(source)
        return {**flags, "classification_mode": "full"}

    monkeypatch.setattr(
        pipeline_module if operation == "batch" else feature_flags,
        "_get_feature_flags_cached" if operation == "batch" else "get_feature_flags_dict",
        delayed_flags,
    )
    work = None
    retiring = None
    try:
        async with savepoint_bed(["pinned work"], "pinned-pipeline|4", entity_names=()) as bed:
            bed.pipe.llm = old
            bed.pipe.extraction.llm = old
            bed.pipe.classification.llm = old
            if operation == "batch":
                from app.services.extraction import ExtractionService

                bed.pipe.extraction = ExtractionService(old)
                work = asyncio.create_task(bed.pipe.process_batch([bed.entry(content="pinned work")]))
            else:
                work = asyncio.create_task(bed.pipe.semantic_search("pinned work"))
            await asyncio.wait_for(captured.wait(), 5)
            bed.pipe.llm = new
            bed.pipe.extraction.llm = new
            bed.pipe.classification.llm = new
            retiring = asyncio.create_task(old.close())
            await asyncio.sleep(0)
            assert not old._client.is_closed
            if outcome == "cancel":
                work.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await work
            else:
                proceed.set()
                if outcome == "error" and operation == "search":
                    with pytest.raises(RuntimeError, match="flag lookup failed"):
                        await asyncio.wait_for(work, 5)
                else:
                    result = await asyncio.wait_for(work, 5)
                    if operation == "batch":
                        assert result[0]["graph"] == ("error" if outcome == "error" else "ok")
                if outcome == "success":
                    if operation == "batch":
                        assert "pinned-pipeline-extraction" in calls
                        assert "pinned-pipeline-classification" in calls
                    assert calls
                    assert all(model.startswith("pinned-pipeline") for model in calls)
            await asyncio.wait_for(retiring, 5)
            assert old._client.is_closed
    finally:
        if work is not None and not work.done():
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
        if retiring is not None:
            await retiring
        await old.close()
        await new.close()
