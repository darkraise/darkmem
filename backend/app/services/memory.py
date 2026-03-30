import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.relational import PostgresAuditRepository, PostgresMemoryRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, session: AsyncSession, pipeline: ProcessingPipeline | None = None):
        self.memory_repo = PostgresMemoryRepository(session)
        self.audit_repo = PostgresAuditRepository(session)
        self.session = session
        self.pipeline = pipeline

    async def create_memory(self, data: MemoryCreate, api_key_id: UUID | None) -> Memory:
        memory = await self.memory_repo.create(
            content=data.content, source=data.source, source_agent=data.source_agent,
            memory_type=data.memory_type, importance=data.importance,
            metadata=data.metadata, expires_at=data.expires_at,
        )
        if data.tags:
            await self.memory_repo.set_tags(memory.id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("create", memory.id, api_key_id, {"source": data.source})

        # Process through pipeline (embedding + extraction)
        if self.pipeline:
            await self.pipeline.process_memory(
                memory_id=memory.id, content=memory.content, source=memory.source,
                tags=[t.name for t in memory.tags], memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            )

        return memory

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        return await self.memory_repo.get(memory_id)

    async def update_memory(self, memory_id: UUID, data: MemoryUpdate, api_key_id: UUID | None) -> Memory | None:
        update_fields = data.model_dump(exclude_unset=True, exclude={"tags"})
        memory = await self.memory_repo.update(memory_id, **update_fields)
        if not memory:
            return None

        if data.tags is not None:
            await self.memory_repo.set_tags(memory_id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("update", memory_id, api_key_id, {"fields": list(update_fields.keys())})

        # Re-process if content changed
        if self.pipeline and "content" in update_fields:
            await self.pipeline.process_memory(
                memory_id=memory.id, content=memory.content, source=memory.source,
                tags=[t.name for t in memory.tags], memory_type=memory.memory_type,
                created_at=memory.created_at.isoformat(),
            )

        return memory

    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
            if self.pipeline:
                await self.pipeline.delete_memory(memory_id)
        return result

    async def search_memories(self, params: MemorySearchRequest) -> list[Memory]:
        # If we have a query and pipeline, try semantic search first
        if params.query and self.pipeline:
            semantic_results = await self.pipeline.semantic_search(params.query, limit=params.limit)
            if semantic_results:
                memory_ids = [r["memory_id"] for r in semantic_results]
                memories = []
                for mid in memory_ids:
                    m = await self.memory_repo.get(mid)
                    if m and not m.is_archived:
                        # Apply additional filters
                        if params.memory_type and m.memory_type != params.memory_type:
                            continue
                        if params.source and m.source != params.source:
                            continue
                        if params.tags_any:
                            tag_names = [t.name for t in m.tags]
                            if not any(t in tag_names for t in params.tags_any):
                                continue
                        memories.append(m)
                return memories[:params.limit]

        # Fallback: Postgres text/tag search
        return await self.memory_repo.search_by_tags(
            query=params.query, tags_any=params.tags_any, tags_all=params.tags_all,
            memory_type=params.memory_type, source=params.source, limit=params.limit,
        )

    async def list_memories(self, offset: int = 0, limit: int = 50) -> tuple[list[Memory], int]:
        return await self.memory_repo.list_memories(offset=offset, limit=limit)

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        if not self.pipeline:
            return []
        return await self.pipeline.find_duplicates(memory_id, threshold)

    async def reason(self, question: str, limit: int = 10) -> dict:
        if not self.pipeline:
            return {"answer": "Reasoning not available (no LLM pipeline configured)", "sources": []}

        # Step 1: Semantic search for relevant memories
        semantic_results = await self.pipeline.semantic_search(question, limit=limit)
        if not semantic_results:
            return {"answer": "No relevant memories found to answer this question.", "sources": []}

        # Step 2: Fetch full memory content
        sources = []
        context_parts = []
        for i, result in enumerate(semantic_results):
            memory = await self.memory_repo.get(result["memory_id"])
            if memory and not memory.is_archived:
                context_parts.append(f"[{i+1}] {memory.content}")
                sources.append({
                    "memory_id": str(memory.id),
                    "content": memory.content[:200],
                    "score": result["score"],
                    "tags": [t.name for t in memory.tags],
                })

        if not context_parts:
            return {"answer": "No relevant memories found.", "sources": []}

        # Step 3: Ask LLM with context
        context = "\n\n".join(context_parts)
        prompt = f"""Based on the following stored memories, answer the question.
If the memories don't contain enough information, say so.
Reference the memory numbers [1], [2], etc. when citing sources.

Memories:
{context}

Question: {question}"""

        answer = await self.pipeline.llm.chat_completion(
            "reasoning",
            messages=[
                {"role": "system", "content": "You are a knowledge retrieval assistant. Answer questions using only the provided memory context. Be concise and accurate."},
                {"role": "user", "content": prompt},
            ],
        )

        return {"answer": answer, "sources": sources}

    async def merge_memories(self, source_id: UUID, target_id: UUID, api_key_id: UUID | None) -> Memory | None:
        source = await self.memory_repo.get(source_id)
        target = await self.memory_repo.get(target_id)
        if not source or not target:
            return None

        merged_content = f"{target.content}\n\n---\n\n{source.content}"
        merged_tags = list({t.name for t in target.tags} | {t.name for t in source.tags})

        await self.memory_repo.update(target_id, content=merged_content)
        await self.memory_repo.set_tags(target_id, merged_tags)
        await self.memory_repo.delete(source_id)

        if self.pipeline:
            await self.pipeline.delete_memory(source_id)
            await self.pipeline.process_memory(
                memory_id=target_id, content=merged_content, source=target.source,
                tags=merged_tags, memory_type=target.memory_type,
                created_at=target.created_at.isoformat(),
            )

        await self.audit_repo.log("merge", target_id, api_key_id, {"source_id": str(source_id)})
        await self.session.refresh(target, ["tags"])
        return await self.memory_repo.get(target_id)
