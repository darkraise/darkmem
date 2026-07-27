from app.schemas.memory import MemoryCreate
from app.services.memory import MemoryService


class _StubLLM:
    async def chat_completion(self, role, messages):
        return "stub answer"


class _StubPipeline:
    def __init__(self):
        self.llm = _StubLLM()

    async def semantic_search(self, question, limit=10):
        # Simulate the bug: semantic search returns unrelated memories
        # (it never returns the decision memories naturally).
        return []

    async def process_memory(self, **kwargs):
        return {"status": "skipped", "reason": "stub"}


async def test_reason_does_not_boost_on_substring_false_positive(session):
    """A question about "artifacts" must not boost memory_type=fact rows."""
    pipeline = _StubPipeline()
    svc = MemoryService(session, pipeline=pipeline)

    # A fact memory that MUST NOT leak into a question about artifacts.
    await svc.create_memory(
        MemoryCreate(
            content="Water boils at 100 degrees Celsius at sea level",
            memory_type="fact",
            source="test",
        ),
        api_key_id=None, wait_process=True,
    )

    result = await svc.reason("List the artifacts we shipped this week", limit=5)

    # Semantic search is stubbed to return []. With loose substring matching,
    # "fact" in "artifacts" fires and the decoy memory gets prepended. With
    # word-boundary matching, no boost, no sources, clean miss.
    contents = " ".join(s["content"] for s in result["sources"]).lower()
    assert "water boils" not in contents, (
        f"substring false positive: fact memory was boosted for 'artifacts' query; "
        f"sources={result['sources']}"
    )


async def test_reason_finds_decision_memories_for_decisions_query(session):
    pipeline = _StubPipeline()
    svc = MemoryService(session, pipeline=pipeline)

    await svc.create_memory(
        MemoryCreate(
            content="Chose pgvector over Qdrant for simpler ops in the new architecture",
            tags=["project/decisions"],
            memory_type="decision",
            source="test",
        ),
        api_key_id=None, wait_process=True,
    )
    await svc.create_memory(
        MemoryCreate(
            content="Adopted Docker Compose for the homelab stack to keep deploys reproducible",
            tags=["project/decisions"],
            memory_type="decision",
            source="test",
        ),
        api_key_id=None, wait_process=True,
    )
    # Decoy memory that should NOT be cited
    await svc.create_memory(
        MemoryCreate(
            content="Circuit breakers prevent cascading failures in distributed systems",
            tags=["topic/reliability"],
            memory_type="fact",
            source="test",
        ),
        api_key_id=None, wait_process=True,
    )

    result = await svc.reason("Summarize recent decisions", limit=5)

    assert len(result["sources"]) >= 2, f"expected >=2 sources, got {result['sources']}"
    contents = " ".join(s["content"] for s in result["sources"]).lower()
    assert "pgvector" in contents
    assert "docker compose" in contents
