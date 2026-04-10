import asyncio
import logging
import time
from uuid import UUID

from sqlalchemy import select

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.classification_llm import ClassificationService
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator
from app.services.memory_classifier import classify as regex_classify
from app.services import prompt

logger = logging.getLogger(__name__)

async def _get_feature_flags(session_factory) -> dict:
    async with session_factory() as session:
        result = await session.execute(
            select(Config).where(Config.key == "feature_flags")
        )
        config = result.scalar_one_or_none()
        if not config:
            return dict(FEATURE_FLAGS_DEFAULTS)
        merged = dict(FEATURE_FLAGS_DEFAULTS)
        merged.update(config.value)
        return merged


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, session_factory, embedding_dims: int, broadcast=None):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.classification = ClassificationService(llm)
        self.session_factory = session_factory
        self.embedding_dims = embedding_dims
        self._broadcast = broadcast
        self.embedding_fingerprint = f"{llm.config['embedding'].model}|{embedding_dims}"
        self._entity_cache: dict[tuple[str, str], tuple[list[float], float]] = {}
        self._entity_cache_lock = asyncio.Lock()

    async def _lookup_entity_embeddings(
        self,
        name_lowers: list[str],
        ttl_seconds: float,
        use_memory_cache: bool,
    ) -> tuple[dict[str, list[float]], list[str]]:
        """Return (hits, misses). Hits map name_lower to embedding.
        Misses are names needing fresh embedding."""
        hits: dict[str, list[float]] = {}
        still_missing: list[str] = []
        now = time.monotonic()
        fp = self.embedding_fingerprint

        if use_memory_cache:
            async with self._entity_cache_lock:
                for name in name_lowers:
                    entry = self._entity_cache.get((name, fp))
                    if entry is not None:
                        emb, cached_at = entry
                        if now - cached_at <= ttl_seconds:
                            hits[name] = emb
                            continue
                        else:
                            del self._entity_cache[(name, fp)]
                    still_missing.append(name)
        else:
            still_missing = list(name_lowers)

        if still_missing:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                db_hits = await repo.get_cached_entity_embeddings(still_missing, fp)
            if db_hits:
                if use_memory_cache:
                    async with self._entity_cache_lock:
                        for name, emb in db_hits.items():
                            self._entity_cache[(name, fp)] = (emb, now)
                hits.update(db_hits)
                still_missing = [n for n in still_missing if n not in db_hits]

        return hits, still_missing

    async def _store_entity_embeddings(
        self,
        name_to_embedding: dict[str, list[float]],
        use_memory_cache: bool,
    ) -> None:
        """Write new embeddings to DB cache and (optionally) in-memory cache."""
        if not name_to_embedding:
            return
        fp = self.embedding_fingerprint

        try:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                await repo.upsert_entity_embeddings_cache(name_to_embedding, fp)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist entity embedding cache to DB", exc_info=True)
            return

        if use_memory_cache:
            now = time.monotonic()
            async with self._entity_cache_lock:
                for name, emb in name_to_embedding.items():
                    self._entity_cache[(name, fp)] = (emb, now)

    async def process_memory(self, memory_id: UUID, content: str, source: str, tags: list[str], memory_type: str | None, created_at: str, vector: list[float] | None = None, flags: dict | None = None) -> dict:
        status = {
            "memory_id": str(memory_id),
            "embed": "pending",
            "extract": "pending",
            "vector": "pending",
            "graph": "pending",
            "entities_count": 0,
            "relations_count": 0,
            "error": None,
        }

        if flags is None:
            flags = await _get_feature_flags(self.session_factory)
        areas = flags.get("classification_areas", ["general"])
        mode = flags.get("classification_mode", "simple")
        llm_enrichment = flags.get("llm_enrichment_enabled", False)

        llm_classification = None
        tasks: list = []
        task_names: list[str] = []

        ext_prompt = prompt.get("extraction")
        cls_prompt = prompt.get("classification") if llm_enrichment else ""

        if vector is not None:
            status["embed"] = "ok"
        else:
            tasks.append(self.llm.embed(content))
            task_names.append("embed")

        tasks.append(self.extraction.extract(content, system_prompt=ext_prompt))
        task_names.append("extract")

        if llm_enrichment:
            tasks.append(self.classification.classify(content, areas, cls_prompt, mode=mode))
            task_names.append("classify")

        logger.debug("process_memory %s: launching %s", memory_id, task_names)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        result_map = dict(zip(task_names, results))

        if "embed" in result_map:
            embed_result = result_map["embed"]
            if isinstance(embed_result, Exception):
                status["embed"] = "error"
                status["error"] = f"Embedding failed: {embed_result}"
                logger.error(f"Embedding failed for {memory_id}: {embed_result}")
            else:
                vector = embed_result
                status["embed"] = "ok"

        extraction = result_map["extract"]
        if isinstance(extraction, Exception):
            status["extract"] = "error"
            status["error"] = status["error"] or f"Extraction failed: {extraction}"
            logger.error(f"Extraction failed for {memory_id}: {extraction}")
        elif isinstance(extraction, dict):
            status["extract"] = "ok"
            status["entities_count"] = len(extraction.get("entities", []))
            status["relations_count"] = len(extraction.get("relationships", []))
            if extraction.get("_error"):
                status["extract"] = "partial"
                status["error"] = status["error"] or f"Extraction degraded: {extraction['_error']}"
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"

        if "classify" in result_map:
            cls_result = result_map["classify"]
            if isinstance(cls_result, dict):
                llm_classification = cls_result
            elif isinstance(cls_result, Exception):
                logger.warning(f"LLM classification failed for {memory_id}: {cls_result}")

        # Entity embedding dedup (outside savepoint — calls LLM embed)
        entity_embeddings: dict[str, list[float]] = {}
        if status["extract"] == "ok" and isinstance(extraction, dict):
            canonical_map: dict[str, str] = {}
            try:
                async with self.session_factory() as dedup_session:
                    dedup_repo = PostgresGraphRepository(dedup_session)
                    for entity in extraction.get("entities", []):
                        name = entity["name"]
                        try:
                            emb = await self.llm.embed(name)
                            entity_embeddings[name] = emb
                            match = await dedup_repo.find_similar_entity(emb, threshold=0.85)
                            if match and match["name"] != name:
                                canonical_map[name] = match["name"]
                        except Exception:
                            pass
                if canonical_map:
                    for entity in extraction["entities"]:
                        if entity["name"] in canonical_map:
                            entity["name"] = canonical_map[entity["name"]]
                    for rel in extraction.get("relationships", []):
                        if rel.get("source") in canonical_map:
                            rel["source"] = canonical_map[rel["source"]]
                        if rel.get("target") in canonical_map:
                            rel["target"] = canonical_map[rel["target"]]
            except Exception as e:
                logger.warning(f"Entity dedup failed for {memory_id}: {e}")

        async with self.session_factory() as session:
            vector_repo = PostgresVectorRepository(session, self.embedding_dims)
            graph_repo = PostgresGraphRepository(session)

            if status["embed"] == "ok":
                regex_result = regex_classify(content, enabled_areas=areas, mode=mode)

                try:
                    async with session.begin_nested():
                        payload = {
                            "memory_id": str(memory_id), "content": content,
                            "source": source, "tags": tags,
                            "memory_type": memory_type or (extraction.get("memory_type") if isinstance(extraction, dict) else None),
                            "created_at": created_at,
                            "classified_type": regex_result.get("hall", ""),
                            "classified_confidence": regex_result.get("confidence", 0.0),
                        }
                        if llm_classification:
                            payload["llm_classified_type"] = llm_classification.get("hall", "")
                            payload["llm_summary"] = llm_classification.get("summary", "")
                            payload["llm_emotions"] = llm_classification.get("emotions", [])
                            payload["llm_flags"] = llm_classification.get("flags", [])

                        await vector_repo.upsert(
                            memory_id=memory_id, vector=vector, payload=payload,
                        )
                        status["vector"] = "ok"

                        from sqlalchemy import select as sa_select
                        from app.models.memory import Memory
                        mem_result = await session.execute(
                            sa_select(Memory).where(Memory.id == memory_id)
                        )
                        mem_record = mem_result.scalar_one_or_none()
                        if mem_record:
                            mem_record.classified_type = regex_result.get("hall") or None
                            mem_record.classified_confidence = regex_result.get("confidence")
                            if llm_classification:
                                mem_record.llm_classified_type = llm_classification.get("hall") or None
                                mem_record.llm_summary = llm_classification.get("summary") or None
                                mem_record.llm_emotions = llm_classification.get("emotions") or None
                                mem_record.llm_flags = llm_classification.get("flags") or None

                        if status["extract"] == "ok" and isinstance(extraction, dict):
                            for entity in extraction.get("entities", []):
                                created = await graph_repo.create_entity(
                                    name=entity["name"], entity_type=entity["type"],
                                    properties=entity.get("properties", {}), memory_id=memory_id,
                                )
                                emb = entity_embeddings.get(entity["name"])
                                if emb and created:
                                    await graph_repo.upsert_entity_embedding(created["id"], emb)
                            for rel in extraction.get("relationships", []):
                                await graph_repo.create_relationship(
                                    source_name=rel["source"], target_name=rel["target"],
                                    rel_type=rel["type"], properties=rel.get("properties", {}),
                                    weight=rel.get("weight", 0.5), memory_id=memory_id,
                                )
                            status["graph"] = "ok"
                        else:
                            status["graph"] = "skipped"

                except Exception as e:
                    status["vector"] = "error"
                    status["graph"] = "error"
                    status["error"] = status["error"] or f"Pipeline DB write failed: {e}"
                    logger.error(f"Pipeline DB write failed for {memory_id}: {e}")
            else:
                status["vector"] = "skipped"
                status["graph"] = "skipped"

            await session.commit()

        if status["vector"] == "ok":
            try:
                async with self.session_factory() as xref_session:
                    xref_repo = PostgresVectorRepository(xref_session, self.embedding_dims)
                    similar = await xref_repo.find_similar_memories(memory_id, top_k=5, min_score=0.4)
                    await xref_repo.store_crossrefs(memory_id, similar)
                    await xref_session.commit()
            except Exception as e:
                logger.warning(f"Crossref computation failed for {memory_id}: {e}")

        steps = [status["embed"], status["extract"], status["vector"], status["graph"]]
        active_steps = [s for s in steps if s != "skipped" and s != "pending"]
        if all(s == "ok" for s in active_steps):
            event_type = "pipeline.completed"
        elif any(s == "ok" for s in active_steps):
            event_type = "pipeline.partial"
        else:
            event_type = "pipeline.failed"

        if self._broadcast:
            try:
                await self._broadcast(event_type, status)
            except Exception as e:
                logger.warning(f"Pipeline broadcast failed: {e}")

        return status

    async def process_batch(
        self,
        entries: list[dict],
    ) -> list[dict]:
        """Process multiple memories concurrently with a configurable semaphore.

        Embeddings are computed in a single batch request upfront, then each
        memory runs extraction + DB writes concurrently with the semaphore.

        Each entry dict has: memory_id, content, source, tags, memory_type, created_at.
        """
        flags = await _get_feature_flags(self.session_factory)
        concurrency = flags.get("pipeline_concurrency", 5)
        semaphore = asyncio.Semaphore(concurrency)

        vectors: list[list[float] | None] = [None] * len(entries)
        try:
            contents = [e["content"] for e in entries]
            logger.info("Batch embedding %d texts...", len(contents))
            batch_vectors = await self.llm.embed_batch(contents)
            vectors = batch_vectors
            logger.info("Batch-embedded %d texts in one request", len(contents))
        except Exception as e:
            logger.warning("Batch embedding failed, falling back to per-memory: %s: %s", type(e).__name__, e)

        logger.info("Starting pipeline processing for %d memories (concurrency=%d, llm_enrichment=%s)", len(entries), concurrency, flags.get("llm_enrichment_enabled"))

        async def _process_one(entry: dict, vec: list[float] | None) -> dict:
            async with semaphore:
                return await self.process_memory(
                    memory_id=entry["memory_id"],
                    content=entry["content"],
                    source=entry.get("source", "mcp"),
                    tags=entry.get("tags", []),
                    memory_type=entry.get("memory_type"),
                    created_at=entry.get("created_at", ""),
                    vector=vec,
                    flags=flags,
                )

        results = await asyncio.gather(
            *[_process_one(e, vectors[i] if i < len(vectors) else None) for i, e in enumerate(entries)],
            return_exceptions=True,
        )

        statuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                statuses.append({
                    "memory_id": str(entries[i]["memory_id"]),
                    "error": str(result),
                })
            else:
                statuses.append(result)
        return statuses

    async def delete_memory(self, memory_id: UUID):
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session, self.embedding_dims)
                graph_repo = PostgresGraphRepository(session)
                await vector_repo.delete(memory_id)
                await graph_repo.delete_by_memory_id(memory_id)
                await session.commit()
            if self._broadcast:
                try:
                    await self._broadcast("memory.deleted", {"memory_id": str(memory_id)})
                except Exception as broadcast_err:
                    logger.warning(f"WebSocket broadcast failed: {broadcast_err}")
        except Exception as e:
            logger.exception(f"Cleanup failed for {memory_id}")

    async def semantic_search(self, query: str, limit: int = 20, semantic_weight: float = 0.7) -> list[dict]:
        try:
            flags = await _get_feature_flags(self.session_factory)
            if flags["hybrid_search_enabled"]:
                from app.services.hybrid_search import HybridSearchService
                async with self.session_factory() as session:
                    hybrid = HybridSearchService(self.llm, session, self.embedding_dims)
                    results = await hybrid.search(query, limit=limit, semantic_weight=semantic_weight)

                    if flags["reranker_enabled"]:
                        from app.services.reranker import RerankerService
                        reranker = RerankerService(self.llm)
                        results = await reranker.rerank(query, results, top_k=limit)

                    return results
            else:
                vector = await self.llm.embed(query)
                async with self.session_factory() as session:
                    vector_repo = PostgresVectorRepository(session, self.embedding_dims)
                    return await vector_repo.search(vector, limit=limit)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session, self.embedding_dims)
                return await vector_repo.find_similar(memory_id, threshold=threshold)
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            raise
