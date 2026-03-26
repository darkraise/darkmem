import asyncio
import logging
from uuid import UUID

from app.repositories.graph import Neo4jGraphRepository
from app.repositories.vector import QdrantVectorRepository
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, vector_repo: QdrantVectorRepository, graph_repo: Neo4jGraphRepository):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    async def process_memory(self, memory_id: UUID, content: str, source: str, tags: list[str], memory_type: str | None, created_at: str):
        try:
            embed_task = self.llm.embed(content)
            extract_task = self.extraction.extract(content)
            results = await asyncio.gather(embed_task, extract_task, return_exceptions=True)
            vector, extraction = results[0], results[1]

            if not isinstance(vector, Exception):
                await self.vector_repo.upsert(
                    memory_id=memory_id, vector=vector,
                    payload={
                        "memory_id": str(memory_id), "content": content,
                        "source": source, "tags": tags,
                        "memory_type": memory_type or (extraction.get("memory_type") if isinstance(extraction, dict) else None),
                        "created_at": created_at,
                    },
                )
            else:
                logger.error(f"Embedding failed for {memory_id}: {vector}")

            if isinstance(extraction, dict):
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
            else:
                logger.error(f"Extraction failed for {memory_id}: {extraction}")
        except Exception as e:
            logger.error(f"Pipeline failed for {memory_id}: {e}")

    async def delete_memory(self, memory_id: UUID):
        try:
            await asyncio.gather(
                self.vector_repo.delete(memory_id),
                self.graph_repo.delete_by_memory_id(memory_id),
                return_exceptions=True,
            )
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
