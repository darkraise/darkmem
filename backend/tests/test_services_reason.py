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
        api_key_id=None,
    )
    await svc.create_memory(
        MemoryCreate(
            content="Adopted Docker Compose for the homelab stack to keep deploys reproducible",
            tags=["project/decisions"],
            memory_type="decision",
            source="test",
        ),
        api_key_id=None,
    )
    # Decoy memory that should NOT be cited
    await svc.create_memory(
        MemoryCreate(
            content="Circuit breakers prevent cascading failures in distributed systems",
            tags=["topic/reliability"],
            memory_type="fact",
            source="test",
        ),
        api_key_id=None,
    )

    result = await svc.reason("Summarize recent decisions", limit=5)

    assert len(result["sources"]) >= 2, f"expected >=2 sources, got {result['sources']}"
    contents = " ".join(s["content"] for s in result["sources"]).lower()
    assert "pgvector" in contents
    assert "docker compose" in contents
