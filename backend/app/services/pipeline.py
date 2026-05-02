import asyncio
import logging
import time
from uuid import UUID

from sqlalchemy import select, text

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.classification_llm import ClassificationService
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator
from app.services.confidence import estimate_confidence, rank_fusion_factor
from app.services.memory_classifier import classify as regex_classify
from app.services.relations import TECH_TYPES
from app.services.supersession import detect_supersessions
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


_FLAG_CACHE_TTL = 5.0
_flag_cache: dict[str, object] = {"value": None, "at": 0.0}
_flag_cache_lock = asyncio.Lock()
_flag_refresh_task: asyncio.Task | None = None


async def _refresh_flag_cache(session_factory) -> dict:
    flags = await _get_feature_flags(session_factory)
    _flag_cache["value"] = flags
    _flag_cache["at"] = time.monotonic()
    return flags


async def _get_feature_flags_cached(session_factory) -> dict:
    """Read feature flags with a short in-process TTL so per-call dispatching
    does not hammer the DB.

    Single-flight: when the cache expires and N coroutines race to refresh, the
    first one spawns a task and the rest await that same task. The DB call
    happens outside any lock so the critical section is tiny.
    """
    now = time.monotonic()
    value = _flag_cache.get("value")
    at = float(_flag_cache.get("at") or 0.0)
    if value is not None and now - at < _FLAG_CACHE_TTL:
        return value  # type: ignore[return-value]

    global _flag_refresh_task
    async with _flag_cache_lock:
        # Re-check under lock; another coroutine may have just refreshed.
        value = _flag_cache.get("value")
        at = float(_flag_cache.get("at") or 0.0)
        if value is not None and now - at < _FLAG_CACHE_TTL:
            return value  # type: ignore[return-value]
        if _flag_refresh_task is None or _flag_refresh_task.done():
            _flag_refresh_task = asyncio.create_task(_refresh_flag_cache(session_factory))
        task = _flag_refresh_task

    return await task


def _flag_cache_reset() -> None:
    """Test hook: drop the cached flag value so the next read hits the DB."""
    global _flag_refresh_task
    _flag_cache["value"] = None
    _flag_cache["at"] = 0.0
    _flag_refresh_task = None


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, session_factory, broadcast=None):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.classification = ClassificationService(llm)
        self.session_factory = session_factory
        self._broadcast = broadcast
        # Cache key is (name_lower, fingerprint); fingerprint is provided per
        # call rather than frozen at __init__, so flag flips don't poison the
        # cache.
        self._entity_cache: dict[tuple[str, str], tuple[list[float], float]] = {}
        self._entity_cache_lock = asyncio.Lock()

    async def _register_fingerprint(self, fingerprint: str) -> None:
        """Idempotently register the fingerprint so its partition exists."""
        from app.services.embedder_registry import (  # noqa: PLC0415
            EmbedderInfo, embedder_registry, parse_fingerprint,
        )
        if embedder_registry.is_known(fingerprint):
            return
        model_id, dims = parse_fingerprint(fingerprint)
        async with self.session_factory() as session:
            await embedder_registry.register(
                session,
                EmbedderInfo(
                    fingerprint=fingerprint,
                    model_id=model_id,
                    dims=dims,
                    source="llm",
                ),
            )

    async def _lookup_entity_embeddings(
        self,
        name_lowers: list[str],
        fingerprint: str,
        ttl_seconds: float,
        use_memory_cache: bool,
    ) -> tuple[dict[str, list[float]], list[str]]:
        """Return (hits, misses). Hits map name_lower to embedding.
        Misses are names needing fresh embedding."""
        hits: dict[str, list[float]] = {}
        still_missing: list[str] = []
        now = time.monotonic()

        if use_memory_cache:
            async with self._entity_cache_lock:
                for name in name_lowers:
                    entry = self._entity_cache.get((name, fingerprint))
                    if entry is not None:
                        emb, cached_at = entry
                        if now - cached_at <= ttl_seconds:
                            hits[name] = emb
                            continue
                        else:
                            del self._entity_cache[(name, fingerprint)]
                    still_missing.append(name)
        else:
            still_missing = list(name_lowers)

        if still_missing:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                db_hits = await repo.get_cached_entity_embeddings(still_missing, fingerprint)
            if db_hits:
                if use_memory_cache:
                    async with self._entity_cache_lock:
                        for name, emb in db_hits.items():
                            self._entity_cache[(name, fingerprint)] = (emb, now)
                hits.update(db_hits)
                still_missing = [n for n in still_missing if n not in db_hits]

        return hits, still_missing

    async def _store_entity_embeddings(
        self,
        name_to_embedding: dict[str, list[float]],
        fingerprint: str,
        use_memory_cache: bool,
    ) -> None:
        """Write new embeddings to DB cache and (optionally) in-memory cache."""
        if not name_to_embedding:
            return

        try:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                await repo.upsert_entity_embeddings_cache(name_to_embedding, fingerprint)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist entity embedding cache to DB", exc_info=True)
            return

        if use_memory_cache:
            now = time.monotonic()
            async with self._entity_cache_lock:
                for name, emb in name_to_embedding.items():
                    self._entity_cache[(name, fingerprint)] = (emb, now)

    async def _write_memory(
        self,
        entry: dict,
        vector: list[float] | None,
        fingerprint: str,
        extraction: dict | Exception,
        llm_classification: dict | None,
        name_to_embedding: dict[str, list[float]],
        canonical_map: dict[str, str],
        flags: dict,
    ) -> dict:
        memory_id = entry["memory_id"]
        content = entry["content"]
        source = entry.get("source", "mcp")
        tags = entry.get("tags", [])
        memory_type = entry.get("memory_type")
        created_at = entry.get("created_at", "")

        areas = flags.get("classification_areas", ["general"])
        mode = flags.get("classification_mode", "simple")

        status = {
            "memory_id": str(memory_id),
            "embed": "ok" if vector is not None else "error",
            "extract": "pending",
            "vector": "pending",
            "graph": "pending",
            "entities_count": 0,
            "relations_count": 0,
            "error": None,
        }
        if isinstance(extraction, Exception):
            status["extract"] = "error"
            status["error"] = f"Extraction failed: {extraction}"
            extraction = None
        elif isinstance(extraction, dict):
            status["extract"] = "ok"
            status["entities_count"] = len(extraction.get("entities", []))
            status["relations_count"] = len(extraction.get("relationships", []))
            if extraction.get("_error"):
                status["extract"] = "partial"
                status["error"] = status["error"] or f"Extraction degraded: {extraction['_error']}"

            # Apply canonical_map to entity names and relationship endpoints
            for entity in extraction.get("entities", []):
                low = entity["name"].lower()
                entity["_orig_lower"] = low
                if low in canonical_map:
                    entity["name"] = canonical_map[low]
            for rel in extraction.get("relationships", []):
                src_low = rel.get("source", "").lower()
                tgt_low = rel.get("target", "").lower()
                if src_low in canonical_map:
                    rel["source"] = canonical_map[src_low]
                if tgt_low in canonical_map:
                    rel["target"] = canonical_map[tgt_low]
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"
            extraction = None

        async with self.session_factory() as session:
            vector_repo = PostgresVectorRepository(session)
            graph_repo = PostgresGraphRepository(session)

            if status["embed"] == "ok":
                regex_result = regex_classify(content, enabled_areas=areas, mode=mode)

                # Idempotent re-extraction: strip any prior contributions of
                # this memory_id from the entity graph before writing the new
                # set. Otherwise re-running with a different model just
                # accumulates duplicate-by-type rows on top of the previous
                # extraction. ``delete_by_memory_id`` only removes entities
                # whose memory_ids array becomes empty after the strip, so
                # entities shared with other memories are preserved.
                try:
                    await graph_repo.delete_by_memory_id(memory_id)
                except Exception as exc:
                    logger.warning(
                        "Failed to strip prior graph contributions for %s: %s",
                        memory_id, exc,
                    )

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
                            fingerprint=fingerprint,
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

                            resolved_memory_type = (
                                memory_type
                                or (extraction.get("memory_type") if isinstance(extraction, dict) else None)
                            )
                            mem_record.confidence = estimate_confidence(content, resolved_memory_type)

                        if status["extract"] in ("ok", "partial") and isinstance(extraction, dict):
                            # Technologies are denormalised to the memory row so the
                            # GIN index on `memories.technologies` can answer retrieval
                            # filters without joining. Store lowercase so case drift in
                            # canonical_map (e.g., "pgvector" vs "PgVector") does not
                            # cause the supersession detector or search filter to miss.
                            tech_names: set[str] = set()
                            # Build a display-name map keyed by the canonical
                            # lower-cased name. The canonical name is what we
                            # write to ``entities.name``; the original casing
                            # is preserved in properties so the UI can render
                            # ``Darkmem`` instead of ``darkmem``.
                            for entity in extraction.get("entities", []):
                                display_name = entity["name"]
                                canonical_name = display_name.strip().lower()
                                props = dict(entity.get("properties") or {})
                                if display_name != canonical_name:
                                    props.setdefault("display_name", display_name)
                                created = await graph_repo.create_entity(
                                    name=canonical_name, entity_type=entity["type"],
                                    properties=props, memory_id=memory_id,
                                )
                                emb = name_to_embedding.get(entity.get("_orig_lower", canonical_name))
                                if emb and created:
                                    await graph_repo.upsert_entity_embedding(
                                        created["id"], emb, fingerprint=fingerprint,
                                    )
                                if entity.get("type") in TECH_TYPES:
                                    tech_names.add(canonical_name)
                            for rel in extraction.get("relationships", []):
                                await graph_repo.create_relationship(
                                    source_name=(rel["source"] or "").strip().lower(),
                                    target_name=(rel["target"] or "").strip().lower(),
                                    rel_type=rel["type"], properties=rel.get("properties", {}),
                                    weight=rel.get("weight", 0.5), memory_id=memory_id,
                                )

                            if mem_record is not None:
                                mem_record.technologies = sorted(tech_names)
                                if mem_record.technologies:
                                    await session.flush([mem_record])
                                    await detect_supersessions(
                                        session,
                                        new_memory_id=memory_id,
                                        new_memory_text=content,
                                        new_memory_created_at=mem_record.created_at,
                                        project=mem_record.project,
                                        new_relations=extraction.get("relationships", []),
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
                    xref_repo = PostgresVectorRepository(xref_session)
                    similar = await xref_repo.find_similar_memories(
                        memory_id, fingerprint=fingerprint, top_k=5, min_score=0.4,
                    )
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

    async def process_memory(
        self,
        memory_id,
        content: str,
        source: str,
        tags: list[str],
        memory_type: str | None,
        created_at: str,
    ) -> dict:
        """Process a single memory. Delegates to process_batch for consistent phasing."""
        entry = {
            "memory_id": memory_id,
            "content": content,
            "source": source,
            "tags": tags,
            "memory_type": memory_type,
            "created_at": created_at,
        }
        results = await self.process_batch([entry])
        return results[0]

    async def process_batch(self, entries: list[dict]) -> list[dict]:
        """Process multiple memories through phased pipeline.

        Phases:
          1. Content embedding (chunked, concurrent)
          2. Extraction and LLM classification (per-memory, concurrent)
          3. Entity embedding with cache
          4. Dedup lookup (per unique name)
          5. Per-memory writes (concurrent)
        """
        flags = await _get_feature_flags(self.session_factory)
        pipeline_concurrency = flags.get("pipeline_concurrency", 5)
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)
        ttl_seconds = flags.get("entity_cache_ttl_minutes", 60) * 60
        classification_on = flags.get("llm_enrichment_enabled", False)
        relation_rescue = flags.get("relation_rescue", True)

        logger.info(
            "Starting batch pipeline: %d memories, pipeline_concurrency=%d, embed_chunk_size=%d, embed_concurrency=%d",
            len(entries), pipeline_concurrency, embed_chunk_size, embed_concurrency,
        )

        # Phase 1: Content embedding
        contents = [e["content"] for e in entries]
        embedding_fingerprint: str | None = None
        try:
            vectors, embedding_fingerprint = await self.llm.embed_batch_chunked(
                contents, embed_chunk_size, embed_concurrency,
            )
            logger.info(
                "Phase 1 complete: embedded %d contents under %s",
                len(vectors), embedding_fingerprint,
            )
        except Exception as e:
            logger.error("Phase 1 content embedding failed: %s: %s", type(e).__name__, e)
            vectors = [None] * len(entries)

        # Register the producing embedder before any partition write. Skipped
        # when Phase 1 failed entirely; downstream writes will be marked as
        # error in that case.
        if embedding_fingerprint and any(v is not None for v in vectors):
            await self._register_fingerprint(embedding_fingerprint)

        # Phase 2: Extraction and LLM classification
        ext_prompt = prompt.get("extraction")
        cls_prompt = prompt.get("classification") if classification_on else ""
        semaphore = asyncio.Semaphore(pipeline_concurrency)

        async def run_extract(content: str):
            async with semaphore:
                try:
                    return await self.extraction.extract(
                        content, system_prompt=ext_prompt,
                        relation_rescue=relation_rescue,
                    )
                except Exception as exc:
                    return exc

        # Pick the classifier implementation: if the classifier purpose
        # config has an ml_profile_ref set, dispatch to the in-process
        # MLClassificationService instead of the LLM-backed one. The
        # surface (``classify(content, areas, prompt, mode)`` returning
        # ``{hall, summary, emotions, flags}``) is identical.
        classifier = self.classification
        try:
            from app.services.config import get_llm_config as _fetch_cfg
            from app.models.llm_config import MLProfile as _MLProfile
            from sqlalchemy import select as _sa_select
            async with self.session_factory() as _classifier_session:
                _live_cfg = await _fetch_cfg(_classifier_session)
                _classifier_cfg = _live_cfg.get("classification")
                _ml_ref = getattr(_classifier_cfg, "ml_profile_ref", None) if _classifier_cfg else None
                if _ml_ref:
                    _ml_row = (await _classifier_session.execute(
                        _sa_select(_MLProfile).where(_MLProfile.name == _ml_ref)
                    )).scalar_one_or_none()
                    if _ml_row is not None:
                        from app.services.classification_ml import MLClassificationService
                        from app.services.ml_runtime import ml_model_manager
                        classifier = MLClassificationService(
                            ml_model_manager,
                            _ml_row.model_repo,
                            _ml_row.ttl_seconds,
                        )
        except Exception:
            logger.exception("Failed to resolve classifier; falling back to LLM service")

        async def run_classify(content: str):
            async with semaphore:
                try:
                    areas = flags.get("classification_areas", ["general"])
                    mode = flags.get("classification_mode", "simple")
                    return await classifier.classify(content, areas, cls_prompt, mode=mode)
                except Exception as exc:
                    logger.warning("Classification failed: %s", exc)
                    return None

        if classification_on:
            extract_tasks = [run_extract(e["content"]) for e in entries]
            classify_tasks = [run_classify(e["content"]) for e in entries]
            all_results = await asyncio.gather(*extract_tasks, *classify_tasks)
            extractions = all_results[: len(entries)]
            classifications: list[dict | None] = all_results[len(entries) :]
        else:
            extractions = await asyncio.gather(*[run_extract(e["content"]) for e in entries])
            classifications = [None] * len(entries)
        logger.info(
            "Phase 2 complete: extractions=%d, classifications=%s",
            len(extractions),
            "llm" if classification_on else "off",
        )

        # Phase 3: Entity embedding with cache
        unique_names: set[str] = set()
        for ext in extractions:
            if isinstance(ext, dict):
                for entity in ext.get("entities", []):
                    name = entity.get("name")
                    if name:
                        unique_names.add(name.lower())

        unique_names_list = sorted(unique_names)
        name_to_embedding: dict[str, list[float]] = {}
        # Default the entity-embedding fingerprint to the content one. When
        # Phase 1 failed but Phase 3 still runs (cache hits), there is no new
        # producer to ask, so we keep the prior fingerprint.
        entity_fingerprint = embedding_fingerprint

        if unique_names_list and entity_fingerprint:
            hits, misses = await self._lookup_entity_embeddings(
                unique_names_list, entity_fingerprint, ttl_seconds, use_memory_cache=True,
            )
            name_to_embedding.update(hits)
            logger.info("Phase 3 cache lookup: %d hits, %d misses", len(hits), len(misses))

            if misses:
                try:
                    new_embeddings_list, new_fp = await self.llm.embed_batch_chunked(
                        misses, embed_chunk_size, embed_concurrency,
                    )
                    if new_fp != entity_fingerprint:
                        # Active embedder changed between Phase 1 and Phase 3.
                        # Register the new one and use it as the entity-cache key.
                        await self._register_fingerprint(new_fp)
                        entity_fingerprint = new_fp
                    new_map = dict(zip(misses, new_embeddings_list))
                    await self._store_entity_embeddings(new_map, entity_fingerprint, use_memory_cache=True)
                    name_to_embedding.update(new_map)
                    logger.info("Phase 3 complete: embedded %d new entity names", len(new_map))
                except Exception as e:
                    logger.warning("Phase 3 entity embedding failed: %s: %s", type(e).__name__, e)
        else:
            logger.info("Phase 3 skipped: no entities to embed")

        # Phase 4: Dedup lookup (one call per unique name).
        # Probes are independent ANN queries — fan them out concurrently
        # bounded by ``pipeline_concurrency`` so a batch of 20 distinct
        # entity names doesn't serialize 20 round-trips.
        canonical_map: dict[str, str] = {}
        if name_to_embedding and entity_fingerprint:
            dedup_sem = asyncio.Semaphore(pipeline_concurrency)

            async def _probe(lower_name: str, emb: list[float]) -> tuple[str, str | None]:
                async with dedup_sem:
                    try:
                        async with self.session_factory() as probe_session:
                            probe_repo = PostgresGraphRepository(probe_session)
                            match = await probe_repo.find_similar_entity(
                                emb, fingerprint=entity_fingerprint, threshold=0.85,
                            )
                        if match and match["name"].lower() != lower_name:
                            return lower_name, match["name"]
                    except Exception as e:
                        logger.warning("Dedup lookup failed for %s: %s", lower_name, e)
                    return lower_name, None

            results = await asyncio.gather(
                *[_probe(n, e) for n, e in name_to_embedding.items()]
            )
            for lower_name, canonical in results:
                if canonical:
                    canonical_map[lower_name] = canonical
            logger.info("Phase 4 complete: %d canonical remappings", len(canonical_map))

        # Phase 5: Per-memory writes
        write_fingerprint = entity_fingerprint or embedding_fingerprint or ""

        async def run_write(entry: dict, vector: list[float] | None, extraction, classification):
            async with semaphore:
                return await self._write_memory(
                    entry, vector, write_fingerprint, extraction, classification,
                    name_to_embedding, canonical_map, flags,
                )

        results = await asyncio.gather(
            *[
                run_write(e, v, ext, cls)
                for e, v, ext, cls in zip(entries, vectors, extractions, classifications)
            ],
            return_exceptions=True,
        )
        logger.info("Phase 5 complete: wrote %d memories", len(results))

        # Normalize any exception returns into error dicts
        normalized: list[dict] = []
        for entry, result in zip(entries, results):
            if isinstance(result, Exception):
                logger.error("Memory %s write failed: %s", entry.get("memory_id"), result)
                normalized.append({
                    "memory_id": str(entry.get("memory_id")),
                    "embed": "unknown", "extract": "unknown",
                    "vector": "error", "graph": "error",
                    "entities_count": 0, "relations_count": 0,
                    "error": str(result),
                })
            else:
                normalized.append(result)

        # Feature 2: record pipeline failure state for each memory
        try:
            from app.services.pipeline_failures import (
                PipelineFailureService, derive_memory_failed_step,
            )
            from app.api.websocket import event_manager

            async with self.session_factory() as failure_session:
                failure_svc = PipelineFailureService(
                    failure_session, broadcast=event_manager.broadcast,
                )
                for entry, result in zip(entries, normalized):
                    if not isinstance(result, dict):
                        continue
                    mem_id_str = result.get("memory_id")
                    if not mem_id_str:
                        continue
                    try:
                        entity_id = UUID(mem_id_str) if isinstance(mem_id_str, str) else mem_id_str
                    except (ValueError, TypeError):
                        continue
                    failed_step = derive_memory_failed_step(result)
                    if failed_step is not None:
                        await failure_svc.record(
                            entity_type="memory",
                            entity_id=entity_id,
                            pipeline_name="memory_ingest",
                            failed_step=failed_step,
                            error_message=result.get("error") or "Unknown error",
                        )
                    else:
                        await failure_svc.resolve(
                            entity_type="memory",
                            entity_id=entity_id,
                            pipeline_name="memory_ingest",
                        )
                await failure_session.commit()
        except Exception as e:
            logger.warning("Failed to record pipeline failures for batch: %s", e)

        return normalized

    async def delete_memory(self, memory_id: UUID):
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
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
                    hybrid = HybridSearchService(self.llm, session)
                    results = await hybrid.search(query, limit=limit, semantic_weight=semantic_weight)

                    if flags["reranker_enabled"]:
                        from app.services.reranker import RerankerService
                        reranker = RerankerService(self.llm)
                        results = await reranker.rerank(query, results, top_k=limit)

                    results = await self._apply_confidence_weighting(session, results, flags)
                    return results
            else:
                vector, fingerprint = await self.llm.embed(query)
                async with self.session_factory() as session:
                    vector_repo = PostgresVectorRepository(session)
                    results = await vector_repo.search(vector, fingerprint=fingerprint, limit=limit)
                    results = await self._apply_confidence_weighting(session, results, flags)
                    return results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    async def _apply_confidence_weighting(
        self,
        session,
        results: list[dict],
        flags: dict,
    ) -> list[dict]:
        """Rescale retrieval scores by memory confidence, multiplicatively.

        ``final = base * (1 + gamma * (confidence - 0.75))``. With ``gamma=0``
        (the default) the call is a no-op, so this stays behind the
        ``confidence_rank_gamma`` flag until we have evidence that the signal
        improves MRR.
        """
        gamma = float(flags.get("confidence_rank_gamma", 0.0) or 0.0)
        if gamma == 0.0 or not results:
            return results

        # Coerce every retrieval row's id to a real UUID so the bound
        # parameter is uuid[] rather than text[]. PG won't use the PK
        # index on memories.id when the operand is text.
        raw_ids = [r.get("memory_id") or r.get("id") for r in results]
        memory_ids: list[UUID] = []
        for raw in raw_ids:
            if not raw:
                continue
            try:
                memory_ids.append(raw if isinstance(raw, UUID) else UUID(str(raw)))
            except (ValueError, TypeError):
                continue
        if not memory_ids:
            return results

        from sqlalchemy import text as sa_text
        row_result = await session.execute(
            sa_text("SELECT id, confidence FROM memories WHERE id = ANY(:ids)"),
            {"ids": memory_ids},
        )
        conf_map: dict[str, float] = {str(row[0]): float(row[1]) for row in row_result}

        score_key = "rrf_score" if results and "rrf_score" in results[0] else "score"
        for r in results:
            mid = str(r.get("memory_id") or r.get("id") or "")
            conf = conf_map.get(mid, 0.75)
            base = float(r.get(score_key, 0.0) or 0.0)
            r[score_key] = base * rank_fusion_factor(conf, gamma)

        return sorted(results, key=lambda r: float(r.get(score_key, 0.0) or 0.0), reverse=True)

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        """Find memories whose vectors are above ``threshold`` against this one.

        Compares within whichever fingerprint already holds an embedding for
        the source memory. If none exist, returns an empty list.
        """
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
                fp_row = await session.execute(
                    text("""
                        SELECT fingerprint FROM memory_embeddings
                        WHERE memory_id = :id
                        ORDER BY created_at DESC LIMIT 1
                    """),
                    {"id": memory_id},
                )
                fp = fp_row.scalar_one_or_none()
                if not fp:
                    return []
                return await vector_repo.find_similar(memory_id, fingerprint=fp, threshold=threshold)
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            raise
