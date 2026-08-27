from app.schemas.memory import MemoryCreate
from app.services.memory import MemoryService


class _StubLLM:
    async def chat_completion(self, role, messages):
        return "stub answer"


class _StubPipeline:
    def __init__(self):
        self.llm = _StubLLM()

    async def semantic_search(self, question, limit=10, semantic_weight=0.7, filters=None):
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


def test_sources_never_name_a_memory_that_was_truncated_away():
    """Every cited source must have actually reached the model.

    Truncating the joined context while returning the full sources list
    invites a citation to a memory the model never saw.
    """
    from app.services.memory import _fit_context

    parts = [f"[{i+1}] " + "x" * 500 for i in range(10)]
    sources = [{"memory_id": f"m{i}"} for i in range(10)]

    kept_parts, kept_sources = _fit_context(parts, sources, budget=1200)

    assert len(kept_parts) == len(kept_sources)
    assert len("\n\n".join(kept_parts)) <= 1200
    assert len(kept_parts) < len(parts), "the budget must actually bite here"


def test_fit_context_keeps_everything_when_it_fits():
    from app.services.memory import _fit_context

    parts = ["[1] short", "[2] also short"]
    sources = [{"memory_id": "a"}, {"memory_id": "b"}]
    kept_parts, kept_sources = _fit_context(parts, sources, budget=10_000)
    assert kept_parts == parts
    assert kept_sources == sources
