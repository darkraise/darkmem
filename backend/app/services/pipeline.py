import asyncio
import logging
from uuid import UUID

from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator
from app.api.websocket import event_manager

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, vector_repo: QdrantVectorRepository, graph_repo: Neo4jGraphRepository):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    async def process_memory(self, memory_id: UUID, content: str, source: str, tags: list[str], memory_type: str | None, created_at: str) -> dict:
        status = {
            "memory_id": str(memory_id),
            "embed": "pending",
            "extract": "pending",
            "qdrant": "pending",
            "neo4j": "pending",
            "entities_count": 0,
            "relations_count": 0,
            "error": None,
        }

        # Run embedding and extraction in parallel
        embed_task = self.llm.embed(content)
        extract_task = self.extraction.extract(content)
        results = await asyncio.gather(embed_task, extract_task, return_exceptions=True)
        vector, extraction = results[0], results[1]

        # Track embed result
        if isinstance(vector, Exception):
            status["embed"] = "error"
            status["error"] = f"Embedding failed: {vector}"
            logger.error(f"Embedding failed for {memory_id}: {vector}")
        else:
            status["embed"] = "ok"

        # Track extraction result
        if isinstance(extraction, Exception):
            status["extract"] = "error"
            status["error"] = status["error"] or f"Extraction failed: {extraction}"
            logger.error(f"Extraction failed for {memory_id}: {extraction}")
        elif isinstance(extraction, dict):
            status["extract"] = "ok"
            status["entities_count"] = len(extraction.get("entities", []))
            status["relations_count"] = len(extraction.get("relationships", []))
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"

        # Store embedding in Qdrant
        if status["embed"] == "ok":
            try:
                await self.vector_repo.upsert(
                    memory_id=memory_id, vector=vector,
                    payload={
                        "memory_id": str(memory_id), "content": content,
                        "source": source, "tags": tags,
                        "memory_type": memory_type or (extraction.get("memory_type") if isinstance(extraction, dict) else None),
                        "created_at": created_at,
                    },
                )
                status["qdrant"] = "ok"
            except Exception as e:
                status["qdrant"] = "error"
                status["error"] = status["error"] or f"Qdrant upsert failed: {e}"
                logger.error(f"Qdrant upsert failed for {memory_id}: {e}")
        else:
            status["qdrant"] = "skipped"

        # Store entities and relationships in Neo4j
        if status["extract"] == "ok" and isinstance(extraction, dict):
            try:
                for entity in extraction.get("entities", []):
                    await self.graph_repo.create_entity(
                        name=entity["name"], entity_type=entity["type"],
                        properties=entity.get("properties", {}), memory_id=memory_id,
                    )
                for rel in extraction.get("relationships", []):
                    await self.graph_repo.create_relationship(
                        source_name=rel["source"], target_name=rel["target"],
                        rel_type=rel["type"], properties=rel.get("properties", {}),
                        weight=rel.get("weight", 0.5), memory_id=memory_id,
                    )
                status["neo4j"] = "ok"
            except Exception as e:
                status["neo4j"] = "error"
                status["error"] = status["error"] or f"Neo4j write failed: {e}"
                logger.error(f"Neo4j write failed for {memory_id}: {e}")
        else:
            status["neo4j"] = "skipped"

        # Determine event type
        steps = [status["embed"], status["extract"], status["qdrant"], status["neo4j"]]
        active_steps = [s for s in steps if s != "skipped" and s != "pending"]
        if all(s == "ok" for s in active_steps):
            event_type = "pipeline.completed"
        elif any(s == "ok" for s in active_steps):
            event_type = "pipeline.partial"
        else:
            event_type = "pipeline.failed"

        try:
            await event_manager.broadcast(event_type, status)
        except Exception:
            pass

        return status

    async def delete_memory(self, memory_id: UUID):
        try:
            await asyncio.gather(
                self.vector_repo.delete(memory_id),
                self.graph_repo.delete_by_memory_id(memory_id),
                return_exceptions=True,
            )
            try:
                await event_manager.broadcast("memory.deleted", {"memory_id": str(memory_id)})
            except Exception as broadcast_err:
                logger.warning(f"WebSocket broadcast failed: {broadcast_err}")
        except Exception as e:
            logger.error(f"Cleanup failed for {memory_id}: {e}")

    async def semantic_search(self, query: str, limit: int = 20) -> list[dict]:
        try:
            vector = await self.llm.embed(query)
            return await self.vector_repo.search(vector, limit=limit)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        try:
            return await self.vector_repo.find_similar(memory_id, threshold=threshold)
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            return []
