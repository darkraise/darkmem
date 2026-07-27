import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config
from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.classification_llm import ClassificationService
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator
from app.services.confidence import estimate_confidence, rank_fusion_factor
from app.services.events import record_event
from app.services.relations import TECH_TYPES, names_distinct
from app.services.supersession import detect_supersessions
from app.services import prompt
from app.taxonomy import normalize_memory_type

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


# The one local classifier the optional `[ml]` extra loads (doc 03 §3.3);
# `classifier_kind='local'` no longer references a named `ml_profiles` row
# (T1.01 dropped that table), so there is exactly one in-process model rather
# than a user-selectable set.
_LOCAL_CLASSIFIER_MODEL_REPO = "darkraise/darkmem-classifier-v1"
_LOCAL_CLASSIFIER_TTL_SECONDS = 0

# How many times Phase 3 will re-resolve its entity names after the active
# embedder rotates under it. Two is already pathological; the bound only exists
# so an embedder that hands back a new fingerprint on every call cannot spin.
_ENTITY_EMBED_ROTATION_ATTEMPTS = 3


def _ml_extra_available() -> bool:
    """Whether the optional CPU-only ``[ml]`` extra (torch + transformers) is
    importable here. Only imports the packages — never loads a model — so
    this is cheap enough to call on every classifier resolution."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class EntityCacheStats:
    """Phase 3's two-level cache outcome, split by which level answered.

    The split is the point: a cache that reports only "hits" cannot tell a warm
    process from a cold one that is paying a DB round-trip per name, and a cache
    stuck at a 0% hit rate is functionally correct while paying full embedding
    cost forever. Recorded per batch and accumulated per pipeline instance.
    """

    memory_hits: int = 0
    db_hits: int = 0
    misses: int = 0

    @property
    def lookups(self) -> int:
        return self.memory_hits + self.db_hits + self.misses

    @property
    def hits(self) -> int:
        return self.memory_hits + self.db_hits

    @property
    def hit_rate(self) -> float:
        return self.hits / self.lookups if self.lookups else 0.0

    def add(self, other: "EntityCacheStats") -> None:
        self.memory_hits += other.memory_hits
        self.db_hits += other.db_hits
        self.misses += other.misses

    def as_dict(self) -> dict:
        return {
            "memory_hits": self.memory_hits,
            "db_hits": self.db_hits,
            "misses": self.misses,
            "lookups": self.lookups,
            "hit_rate": round(self.hit_rate, 4),
        }


def _derive_outcome(status: dict) -> str:
    """`completed` / `partial` / `failed` from a memory's per-step statuses.

    Shared by the durable `extracted` event and the `pipeline.*` broadcast so the
    journal and the websocket can never disagree about the same memory.
    """
    steps = [status["embed"], status["extract"], status["vector"], status["graph"]]
    active = [s for s in steps if s not in ("skipped", "pending")]
    if all(s == "ok" for s in active):
        return "completed"
    if any(s == "ok" for s in active):
        return "partial"
    return "failed"


class ProcessingPipeline:
    def __init__(self, llm: LLMOrchestrator, session_factory, broadcast=None):
        self.llm = llm
        self.extraction = ExtractionService(llm)
        self.classification = ClassificationService(llm)
        self.session_factory = session_factory
        self._broadcast = broadcast
        # Cache key is (name_lower, fingerprint); fingerprint is provided per
        # call rather than frozen at __init__, so flag flips don't poison the
        # cache. Bounded LRU: this pipeline is a process-lifetime singleton, so
        # an unbounded dict here leaks a float vector per distinct entity name
        # for the life of the process. The DB cache backstops any eviction.
        self._entity_cache: "OrderedDict[tuple[str, str], tuple[list[float], float]]" = OrderedDict()
        self._entity_cache_max = 10_000
        self._entity_cache_lock = asyncio.Lock()
        # Phase 3's whole value is not re-embedding entity names, and a cache
        # nobody can see the hit rate of is a cache nobody can tell is broken.
        # ``entity_cache_stats`` accumulates for the life of this pipeline (a
        # run's aggregate); ``last_entity_cache_stats`` is the latest batch.
        self.entity_cache_stats = EntityCacheStats()
        self.last_entity_cache_stats = EntityCacheStats()
        # Short-TTL cache of the per-batch classifier resolution so process_batch
        # doesn't open a session + run two queries on every batch just to learn
        # whether the (rarely-set) ml_profile_ref points it at the in-process ML
        # classifier. None means "use self.classification".
        self._classifier_cache: tuple[float, object | None] | None = None
        self._classifier_cache_ttl = 30.0

    def _cache_put(
        self,
        key: tuple[str, str],
        value: tuple[list[float], float],
    ) -> None:
        """Insert/refresh an entity-cache entry as most-recently-used and evict
        the oldest entries past the cap. Caller holds ``_entity_cache_lock``."""
        self._entity_cache[key] = value
        self._entity_cache.move_to_end(key)
        while len(self._entity_cache) > self._entity_cache_max:
            self._entity_cache.popitem(last=False)

    async def _resolve_classifier(self):
        """Pick the batch classifier from the classification purpose's inline
        ``classifier_kind`` (doc 11 §2): ``local`` selects the in-process
        ``MLClassificationService`` when the optional ``[ml]`` extra is
        importable; anything else — ``llm``, an absent row, or ``local``
        with ``[ml]`` unavailable — uses the LLM-backed
        ``ClassificationService``. Both share the same surface
        (``classify(content, areas, prompt, mode)`` returning
        ``{hall, summary, emotions, flags}``). Resolved once per
        ``_classifier_cache_ttl`` so a settings flip is picked up within that
        window without a per-batch DB round-trip."""
        now = time.monotonic()
        if self._classifier_cache is not None:
            cached_at, cached = self._classifier_cache
            if now - cached_at <= self._classifier_cache_ttl:
                return cached if cached is not None else self.classification
        resolved: object | None = None
        try:
            from app.services.config import get_llm_config as _fetch_cfg
            async with self.session_factory() as session:
                live_cfg = await _fetch_cfg(session)
            classifier_cfg = live_cfg.get("classification")
            classifier_kind = getattr(classifier_cfg, "classifier_kind", None) if classifier_cfg else None
            if classifier_kind == "local":
                if _ml_extra_available():
                    from app.services.classification_ml import MLClassificationService
                    from app.services.ml_runtime import ml_model_manager
                    resolved = MLClassificationService(
                        ml_model_manager,
                        _LOCAL_CLASSIFIER_MODEL_REPO,
                        _LOCAL_CLASSIFIER_TTL_SECONDS,
                    )
                else:
                    logger.info(
                        "classifier_kind=local but the [ml] extra is not "
                        "installed; using the LLM-backed classifier"
                    )
        except Exception:
            logger.exception("Failed to resolve classifier; falling back to LLM service")
            resolved = None
        self._classifier_cache = (now, resolved)
        return resolved if resolved is not None else self.classification

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

    def _record_entity_cache_stats(self, stats: EntityCacheStats) -> None:
        self.last_entity_cache_stats = stats
        self.entity_cache_stats.add(stats)

    async def _lookup_entity_embeddings(
        self,
        name_lowers: list[str],
        fingerprint: str,
        ttl_seconds: float,
        use_memory_cache: bool,
    ) -> tuple[dict[str, list[float]], list[str], EntityCacheStats]:
        """Return (hits, misses, stats), all keyed by ``(name_lower, fingerprint)``.

        Hits map name_lower to embedding; misses are names needing a fresh
        embedding call. ``stats`` reports which level answered each name.
        """
        hits: dict[str, list[float]] = {}
        still_missing: list[str] = []
        stats = EntityCacheStats()
        now = time.monotonic()

        if use_memory_cache:
            async with self._entity_cache_lock:
                for name in name_lowers:
                    entry = self._entity_cache.get((name, fingerprint))
                    if entry is not None:
                        emb, cached_at = entry
                        if now - cached_at <= ttl_seconds:
                            self._entity_cache.move_to_end((name, fingerprint))
                            hits[name] = emb
                            continue
                        else:
                            del self._entity_cache[(name, fingerprint)]
                    still_missing.append(name)
        else:
            still_missing = list(name_lowers)
        stats.memory_hits = len(hits)

        if still_missing:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                db_hits = await repo.get_cached_entity_embeddings(still_missing, fingerprint)
            if db_hits:
                if use_memory_cache:
                    async with self._entity_cache_lock:
                        for name, emb in db_hits.items():
                            self._cache_put((name, fingerprint), (emb, now))
                hits.update(db_hits)
                still_missing = [n for n in still_missing if n not in db_hits]
                stats.db_hits = len(db_hits)

        stats.misses = len(still_missing)
        return hits, still_missing, stats

    async def _store_entity_embeddings(
        self,
        name_to_embedding: dict[str, list[float]],
        fingerprint: str,
        use_memory_cache: bool,
    ) -> None:
        """Write new embeddings to DB cache and (optionally) in-memory cache.

        The DB write is one batched statement for the whole map: a per-entity
        write loop is just as correct and costs a round-trip per name, which is
        the cost this phase exists to avoid. A DB failure still populates the
        in-memory level — the vectors are valid for this fingerprint either way,
        and letting the persistence failure disable the memory cache too would
        re-embed the same names on every subsequent batch.
        """
        if not name_to_embedding:
            return

        try:
            async with self.session_factory() as session:
                repo = PostgresGraphRepository(session)
                await repo.upsert_entity_embeddings_cache(name_to_embedding, fingerprint)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist entity embedding cache to DB", exc_info=True)

        if use_memory_cache:
            now = time.monotonic()
            async with self._entity_cache_lock:
                for name, emb in name_to_embedding.items():
                    self._cache_put((name, fingerprint), (emb, now))

    async def _embed_entity_names(
        self,
        name_lowers: list[str],
        fingerprint: str,
        ttl_seconds: float,
        chunk_size: int,
        concurrency: int,
    ) -> tuple[dict[str, list[float]], str]:
        """Phase 3: resolve entity names to vectors under a single fingerprint.

        Memory cache → DB cache → embed the misses, writing anything newly
        embedded back to both levels. Returns the resolved map and the
        fingerprint every vector in it belongs to, which is not necessarily the
        one passed in: the active embedder can rotate between Phase 1 and here,
        in which case the new one is registered before anything is written into
        its partition.

        A rotation discards everything resolved so far and restarts, because
        the hits were read out of the pre-rotation partition and belong to a
        different embedding space — Phase 4 probes and Phase 5 writes them
        against the returned fingerprint, so carrying them across would put one
        embedder's vectors in another's ``vector(N)`` column. That is silent
        whenever the two embedders share a width. Bounded: an embedder that
        rotates on every call gets no entity vectors at all rather than a
        mixed partition or an endless retry.
        """
        for _ in range(_ENTITY_EMBED_ROTATION_ATTEMPTS):
            hits, misses, stats = await self._lookup_entity_embeddings(
                name_lowers, fingerprint, ttl_seconds, use_memory_cache=True,
            )
            self._record_entity_cache_stats(stats)
            logger.info(
                "Phase 3 cache lookup: %d memory hits, %d db hits, %d misses "
                "(batch hit rate %.1f%%, run hit rate %.1f%%)",
                stats.memory_hits, stats.db_hits, stats.misses,
                stats.hit_rate * 100, self.entity_cache_stats.hit_rate * 100,
            )
            if not misses:
                return dict(hits), fingerprint

            try:
                new_vectors, new_fp = await self.llm.embed_batch_chunked(
                    misses, chunk_size, concurrency,
                )
            except Exception as e:
                logger.warning(
                    "Phase 3 entity embedding failed: %s: %s", type(e).__name__, e
                )
                return dict(hits), fingerprint

            if new_fp != fingerprint:
                # Active embedder changed between Phase 1 and Phase 3. Register
                # the new one and use it as the entity-cache key.
                try:
                    await self._register_fingerprint(new_fp)
                except Exception as e:
                    logger.warning(
                        "Phase 3 fingerprint registration failed for %s: %s: %s",
                        new_fp, type(e).__name__, e,
                    )
                    return dict(hits), fingerprint
                logger.info(
                    "Phase 3 embedder rotated %s -> %s; re-resolving %d entity "
                    "names under the new fingerprint",
                    fingerprint, new_fp, len(name_lowers),
                )
                fingerprint = new_fp
                continue

            if len(new_vectors) != len(misses):
                logger.warning(
                    "Phase 3 embedder returned %d vectors for %d names; "
                    "%d entity names will go unembedded this batch",
                    len(new_vectors), len(misses), abs(len(misses) - len(new_vectors)),
                )
            new_map = dict(zip(misses, new_vectors))
            await self._store_entity_embeddings(new_map, fingerprint, use_memory_cache=True)
            logger.info("Phase 3 complete: embedded %d new entity names", len(new_map))
            return {**hits, **new_map}, fingerprint

        logger.warning(
            "Phase 3 gave up after %d embedder rotations; this batch gets no "
            "entity embeddings", _ENTITY_EMBED_ROTATION_ATTEMPTS,
        )
        return {}, fingerprint

    async def _write_memory(
        self,
        entry: dict,
        vector: list[float] | None,
        content_fingerprint: str,
        entity_fingerprint: str,
        extraction: dict | Exception,
        llm_classification: dict | None,
        name_to_embedding: dict[str, list[float]],
        canonical_map: dict[tuple[str, str], str],
        flags: dict,
    ) -> dict:
        memory_id = entry["memory_id"]
        content = entry["content"]
        source = entry.get("source", "mcp")
        tags = entry.get("tags", [])
        memory_type = entry.get("memory_type")
        created_at = entry.get("created_at", "")

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

            # Apply canonical_map to entity names and relationship endpoints.
            # The map is keyed by (name_lower, entity_type) so a canonical rewrite
            # only collapses same-typed entities — a `concept` "react" must not be
            # renamed onto a `tool` "react". Relationship endpoints carry no type,
            # so resolve each endpoint's type from this extraction's own entities;
            # if unknown, leave the endpoint untouched.
            ent_types = {
                (e.get("name") or "").lower(): e.get("type")
                for e in extraction.get("entities", [])
            }
            for entity in extraction.get("entities", []):
                low = entity["name"].lower()
                entity["_orig_lower"] = low
                key = (low, entity.get("type"))
                if key in canonical_map:
                    entity["name"] = canonical_map[key]
            for rel in extraction.get("relationships", []):
                src_low = rel.get("source", "").lower()
                tgt_low = rel.get("target", "").lower()
                src_key = (src_low, ent_types.get(src_low))
                tgt_key = (tgt_low, ent_types.get(tgt_low))
                if src_key in canonical_map:
                    rel["source"] = canonical_map[src_key]
                if tgt_key in canonical_map:
                    rel["target"] = canonical_map[tgt_key]
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"
            extraction = None

        async with self.session_factory() as session:
            # Bound here, not inside savepoint A: a failed Phase 1 skips the
            # writes entirely, and the per-memory journal below still reads this.
            mem_record = None
            vector_repo = PostgresVectorRepository(session)
            graph_repo = PostgresGraphRepository(session)

            if status["embed"] == "ok":
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

                extracted_type = (
                    extraction.get("memory_type") if isinstance(extraction, dict) else None
                )
                resolved_memory_type = normalize_memory_type(memory_type or extracted_type)
                extracted_importance = (
                    extraction.get("importance") if isinstance(extraction, dict) else None
                )

                # Savepoint A: the content embedding + memory-row enrichment.
                # Released independently of the graph write below so a graph
                # failure can't roll back a successfully embedded memory (which
                # would leave it unsearchable and misreport the failed step).
                try:
                    async with session.begin_nested():
                        payload = {
                            "memory_id": str(memory_id), "content": content,
                            "source": source, "tags": tags,
                            "memory_type": resolved_memory_type,
                            "created_at": created_at,
                        }
                        if llm_classification:
                            payload["llm_classified_type"] = llm_classification.get("hall", "")
                            payload["llm_summary"] = llm_classification.get("summary", "")
                            payload["llm_emotions"] = llm_classification.get("emotions", [])
                            payload["llm_flags"] = llm_classification.get("flags", [])

                        await vector_repo.upsert(
                            memory_id=memory_id, vector=vector, payload=payload,
                            fingerprint=content_fingerprint,
                        )
                        status["vector"] = "ok"

                        from sqlalchemy import select as sa_select
                        from app.models.memory import Memory
                        mem_result = await session.execute(
                            sa_select(Memory).where(Memory.id == memory_id)
                        )
                        mem_record = mem_result.scalar_one_or_none()
                        if mem_record:
                            if llm_classification:
                                mem_record.classified_type = llm_classification.get("hall") or None
                                mem_record.summary = llm_classification.get("summary") or None
                                mem_record.emotions = llm_classification.get("emotions") or None
                                mem_record.flags = llm_classification.get("flags") or None

                            mem_record.memory_type = resolved_memory_type
                            if extracted_importance is not None:
                                try:
                                    mem_record.importance = float(extracted_importance)
                                except (TypeError, ValueError):
                                    pass
                            mem_record.confidence = estimate_confidence(content, resolved_memory_type)
                except Exception as e:
                    status["vector"] = "error"
                    status["graph"] = "skipped"
                    status["error"] = status["error"] or f"Vector write failed: {e}"
                    logger.error(f"Vector write failed for {memory_id}: {e}")
                    mem_record = None

                # Savepoint B: the entity/relationship graph. A failure here rolls
                # back only the graph; the embedding from savepoint A survives and
                # the failure is attributed to the graph step, not the vector one.
                if status["vector"] == "ok" and status["extract"] in ("ok", "partial") and isinstance(extraction, dict):
                    try:
                        async with session.begin_nested():
                            # Technologies are denormalised to the memory row so the
                            # GIN index on `memories.technologies` can answer retrieval
                            # filters without joining. Store lowercase so case drift in
                            # canonical_map (e.g., "pgvector" vs "PgVector") does not
                            # cause the supersession detector or search filter to miss.
                            tech_names: set[str] = set()
                            # Map each canonical (lower-cased) entity name to the
                            # type it was written with, so relationships resolve
                            # endpoints by (name, entity_type) — entity uniqueness
                            # — instead of name alone, which can bind to a
                            # same-named entity of a different type.
                            name_to_type: dict[str, str] = {}
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
                                name_to_type[canonical_name] = entity["type"]
                                emb = name_to_embedding.get(entity.get("_orig_lower", canonical_name))
                                if emb and created:
                                    await graph_repo.upsert_entity_embedding(
                                        created["id"], emb, fingerprint=entity_fingerprint,
                                    )
                                if entity.get("type") in TECH_TYPES:
                                    tech_names.add(canonical_name)
                            for rel in extraction.get("relationships", []):
                                source_name = (rel["source"] or "").strip().lower()
                                target_name = (rel["target"] or "").strip().lower()
                                await graph_repo.create_relationship(
                                    source_name=source_name,
                                    target_name=target_name,
                                    rel_type=rel["type"], properties=rel.get("properties", {}),
                                    weight=rel.get("weight", 0.5), memory_id=memory_id,
                                    source_type=name_to_type.get(source_name),
                                    target_type=name_to_type.get(target_name),
                                )

                            if mem_record is not None:
                                mem_record.technologies = sorted(tech_names)
                                # Trigger on a REPLACES relation, not on this
                                # memory's own technologies: the detector keys off
                                # the REPLACES *target* overlapping a candidate's
                                # technologies, which is independent of whether the
                                # new memory produced a tech entity of its own.
                                if any(
                                    r.get("type") == "REPLACES"
                                    for r in extraction.get("relationships", [])
                                ):
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
                    except Exception as e:
                        status["graph"] = "error"
                        status["error"] = status["error"] or f"Graph write failed: {e}"
                        logger.error(f"Graph write failed for {memory_id}: {e}")
                elif status["vector"] == "ok":
                    status["graph"] = "skipped"
            else:
                status["vector"] = "skipped"
                status["graph"] = "skipped"

            outcome = _derive_outcome(status)

            # Doc 05 §2.3: the flush's durable twin of the pipeline.completed/
            # partial/failed broadcast below. record_event never raises, so a
            # broken journal degrades loudly (its own log line) without
            # failing extraction or rolling back the writes above it.
            await record_event(
                session,
                event_type="extracted",
                object_type="memory",
                object_id=memory_id,
                project=mem_record.project if mem_record is not None else entry.get("project"),
                payload={**status, "outcome": outcome},
            )

            await session.commit()

        if status["vector"] == "ok":
            try:
                async with self.session_factory() as xref_session:
                    xref_repo = PostgresVectorRepository(xref_session)
                    similar = await xref_repo.find_similar_memories(
                        memory_id, fingerprint=content_fingerprint, top_k=5, min_score=0.4,
                    )
                    await xref_repo.store_crossrefs(memory_id, similar)
                    await xref_session.commit()
            except Exception as e:
                logger.warning(f"Crossref computation failed for {memory_id}: {e}")

        # Derived again here rather than reused from the write block above:
        # that block is skipped whenever the writes are (a failed Phase 1 marks
        # every memory embed=error and skips them), which would leave this
        # reading the PREVIOUS memory's outcome — or nothing at all on the first.
        event_type = f"pipeline.{_derive_outcome(status)}"

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
        if not entries:
            return []

        flags = await _get_feature_flags_cached(self.session_factory)
        pipeline_concurrency = flags.get("pipeline_concurrency", 5)
        embed_chunk_size = flags.get("embedding_batch_size", 20)
        embed_concurrency = flags.get("embedding_concurrency", 1)
        ttl_seconds = flags.get("entity_cache_ttl_minutes", 60) * 60
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
            if len(vectors) != len(entries):
                # Position is the only thing binding a vector to its content, so
                # a short or long return leaves us unable to say which vector
                # belongs to which memory. Pairing them anyway would either zip
                # the tail of the batch away — no status, no failure row, a
                # caller silently handed fewer results than entries — or store
                # one memory's embedding under another memory's id.
                raise RuntimeError(
                    f"embed_batch_chunked returned {len(vectors)} vectors for "
                    f"{len(entries)} contents"
                )
            logger.info(
                "Phase 1 complete: embedded %d contents under %s",
                len(vectors), embedding_fingerprint,
            )
        except Exception as e:
            logger.error("Phase 1 content embedding failed: %s: %s", type(e).__name__, e)
            vectors = [None] * len(entries)
            embedding_fingerprint = None

        # Register the producing embedder before any partition write. Phase 5's
        # content vectors and Phase 3's entity-cache rows both land in tables
        # this call creates, so a registration failure has to degrade to the
        # Phase-1-failure state rather than escape the batch: drop the vectors
        # and the fingerprint so nothing downstream writes into or probes a
        # partition that was never registered.
        if embedding_fingerprint and any(v is not None for v in vectors):
            try:
                await self._register_fingerprint(embedding_fingerprint)
            except Exception as e:
                logger.error(
                    "Phase 1 fingerprint registration failed for %s: %s: %s",
                    embedding_fingerprint, type(e).__name__, e,
                )
                vectors = [None] * len(entries)
                embedding_fingerprint = None

        # Phase 2: Extraction and LLM classification. Classification always runs
        # alongside extraction — the regex classifier it used to A/B against is
        # gone, so the LLM (or the in-process ML classifier when an ml_profile_ref
        # is set) is the sole source of the llm_* enrichment columns.
        ext_prompt = prompt.get("extraction")
        cls_prompt = prompt.get("classification")
        semaphore = asyncio.Semaphore(pipeline_concurrency)

        async def run_extract(content: str, with_classification: bool = False):
            async with semaphore:
                try:
                    return await self.extraction.extract(
                        content, system_prompt=ext_prompt,
                        relation_rescue=relation_rescue,
                        with_classification=with_classification,
                    )
                except Exception as exc:
                    return exc

        # Pick the classifier implementation (LLM-backed, or in-process ML when
        # the classification purpose has an ml_profile_ref). Cached for a short
        # TTL so it isn't re-resolved with a DB round-trip on every batch.
        classifier = await self._resolve_classifier()

        async def run_classify(content: str):
            async with semaphore:
                try:
                    areas = flags.get("classification_areas", ["general"])
                    mode = flags.get("classification_mode", "simple")
                    return await classifier.classify(content, areas, cls_prompt, mode=mode)
                except Exception as exc:
                    logger.warning("Classification failed: %s", exc)
                    return None

        # Fold classification into the single extraction call when the classifier
        # is the LLM-backed one (no ml_profile_ref) AND the type vocabulary is the
        # fixed simple-7 set. In that regime extraction's ``memory_type`` already
        # covers the classification label, so the standalone classification call
        # only re-predicts the same type plus summary/emotions/flags — fold those
        # onto the extraction response and save a round-trip. The in-process ML
        # classifier (which can't extract) and the area-grained non-simple mode
        # (whose larger label space the extraction schema doesn't carry) keep the
        # two-call path.
        can_merge = (
            classifier is self.classification
            and flags.get("classification_mode", "simple") == "simple"
        )
        classifications: list[dict | None]
        if can_merge:
            extractions = await asyncio.gather(
                *[run_extract(e["content"], with_classification=True) for e in entries]
            )
            classifications = []
            for ext in extractions:
                if not isinstance(ext, dict) or ext.get("_error"):
                    classifications.append(None)
                    continue
                emotions = ext.get("emotions")
                ext_flags = ext.get("flags")
                classifications.append({
                    "hall": normalize_memory_type(ext.get("memory_type")),
                    "summary": ext.get("summary"),
                    "emotions": emotions if isinstance(emotions, list) else [],
                    "flags": ext_flags if isinstance(ext_flags, list) else [],
                })
        else:
            extract_tasks = [run_extract(e["content"]) for e in entries]
            classify_tasks = [run_classify(e["content"]) for e in entries]
            all_results = await asyncio.gather(*extract_tasks, *classify_tasks)
            extractions = all_results[: len(entries)]
            classifications = all_results[len(entries) :]
        logger.info(
            "Phase 2 complete: extractions=%d, classifications=%d, merged=%s",
            len(extractions), len(classifications), can_merge,
        )

        # Phase 3: Entity embedding with cache
        unique_names: set[str] = set()
        # Each name's set of types, so Phase 4 can probe per (name, type) and
        # keep the dedup from collapsing same-named entities of different types.
        name_types: dict[str, set[str]] = {}
        for ext in extractions:
            if isinstance(ext, dict):
                for entity in ext.get("entities", []):
                    name = entity.get("name")
                    if name:
                        low = name.lower()
                        unique_names.add(low)
                        etype = entity.get("type")
                        if etype:
                            name_types.setdefault(low, set()).add(etype)

        unique_names_list = sorted(unique_names)
        name_to_embedding: dict[str, list[float]] = {}
        # Default the entity-embedding fingerprint to the content one. When
        # Phase 1 failed but Phase 3 still runs (cache hits), there is no new
        # producer to ask, so we keep the prior fingerprint.
        entity_fingerprint = embedding_fingerprint

        if unique_names_list and entity_fingerprint:
            name_to_embedding, entity_fingerprint = await self._embed_entity_names(
                unique_names_list, entity_fingerprint, ttl_seconds,
                embed_chunk_size, embed_concurrency,
            )
        else:
            logger.info("Phase 3 skipped: no entities to embed")

        # Phase 4: Dedup lookup (one call per unique name).
        # Probes are independent ANN queries — fan them out concurrently
        # bounded by ``pipeline_concurrency`` so a batch of 20 distinct
        # entity names doesn't serialize 20 round-trips.
        canonical_map: dict[tuple[str, str], str] = {}
        if name_to_embedding and entity_fingerprint:
            dedup_sem = asyncio.Semaphore(pipeline_concurrency)

            async def _probe(
                lower_name: str, etype: str, emb: list[float]
            ) -> tuple[tuple[str, str], str | None]:
                async with dedup_sem:
                    try:
                        async with self.session_factory() as probe_session:
                            probe_repo = PostgresGraphRepository(probe_session)
                            match = await probe_repo.find_similar_entity(
                                emb, fingerprint=entity_fingerprint, threshold=0.85,
                                entity_type=etype,
                            )
                        if (
                            match
                            and match["name"].lower() != lower_name
                            and not names_distinct(lower_name, match["name"])
                        ):
                            return (lower_name, etype), match["name"]
                    except Exception as e:
                        logger.warning("Dedup lookup failed for %s: %s", lower_name, e)
                    return (lower_name, etype), None

            # One probe per (name, type) — a name embedded once may appear under
            # more than one type across the batch, and each type dedups separately.
            probe_args = [
                (low, etype, name_to_embedding[low])
                for low, types in name_types.items()
                if low in name_to_embedding
                for etype in types
            ]
            results = await asyncio.gather(
                *[_probe(low, etype, emb) for low, etype, emb in probe_args]
            )
            for key, canonical in results:
                if canonical:
                    canonical_map[key] = canonical
            logger.info("Phase 4 complete: %d canonical remappings", len(canonical_map))

        # Phase 5: Per-memory writes.
        # Content vectors were produced in Phase 1 under ``embedding_fingerprint``;
        # entity embeddings live under ``entity_fingerprint``, which differs when
        # the embedder rotated mid-batch. Each vector must land in the partition
        # matching the fingerprint it was produced under — writing the content
        # vector into the rotated entity partition mixes dimensions across
        # fingerprints (and breaks the cross-fingerprint-join invariant).
        content_write_fingerprint = embedding_fingerprint or entity_fingerprint or ""
        entity_write_fingerprint = entity_fingerprint or embedding_fingerprint or ""

        async def run_write(entry: dict, vector: list[float] | None, extraction, classification):
            async with semaphore:
                return await self._write_memory(
                    entry, vector, content_write_fingerprint, entity_write_fingerprint,
                    extraction, classification,
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

    async def delete_memory(self, memory_id: UUID, broadcast: bool = True):
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
                graph_repo = PostgresGraphRepository(session)
                await vector_repo.delete(memory_id)
                await graph_repo.delete_by_memory_id(memory_id)
                await session.commit()
            if broadcast and self._broadcast:
                try:
                    await self._broadcast("memory.deleted", {"memory_id": str(memory_id)})
                except Exception as broadcast_err:
                    logger.warning(f"WebSocket broadcast failed: {broadcast_err}")
        except Exception as e:
            logger.exception(f"Cleanup failed for {memory_id}")

    async def semantic_search(self, query: str, limit: int = 20, semantic_weight: float = 0.7) -> list[dict]:
        try:
            flags = await _get_feature_flags_cached(self.session_factory)
            if flags["hybrid_search_enabled"]:
                from app.services.hybrid_search import HybridSearchService
                async with self.session_factory() as session:
                    hybrid = HybridSearchService(self.llm, session)
                    results = await hybrid.search(query, limit=limit, semantic_weight=semantic_weight)

                    reranked = bool(flags["reranker_enabled"])
                    if reranked:
                        from app.services.reranker import RerankerService
                        reranker = RerankerService(self.llm)
                        results = await reranker.rerank(query, results, top_k=limit)

                    results = await self._apply_confidence_weighting(
                        session, results, flags, preserve_order=reranked,
                    )
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
        preserve_order: bool = False,
    ) -> list[dict]:
        """Rescale retrieval scores by memory confidence, multiplicatively.

        ``final = base * (1 + gamma * (confidence - 0.75))``. With ``gamma=0``
        (the default) the call is a no-op, so this stays behind the
        ``confidence_rank_gamma`` flag until we have evidence that the signal
        improves MRR.

        When ``preserve_order`` is set (the reranker has already imposed a
        ranking), scores are still rescaled but the input order is kept — the
        reranker's order is authoritative and must not be sorted away.
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
            sa_text("SELECT id, confidence FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": memory_ids},
        )
        conf_map: dict[str, float] = {str(row[0]): float(row[1]) for row in row_result}

        score_key = "rrf_score" if results and "rrf_score" in results[0] else "score"
        for r in results:
            mid = str(r.get("memory_id") or r.get("id") or "")
            conf = conf_map.get(mid, 0.75)
            base = float(r.get(score_key, 0.0) or 0.0)
            r[score_key] = base * rank_fusion_factor(conf, gamma)

        if preserve_order:
            return results
        return sorted(results, key=lambda r: float(r.get(score_key, 0.0) or 0.0), reverse=True)

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        """Find memories whose vectors are above ``threshold`` against this one.

        Compares within whichever fingerprint already holds an embedding for
        the source memory. If none exist, returns an empty list.
        """
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
                fp = await vector_repo.find_fingerprint_for_memory(memory_id)
                if not fp:
                    return []
                return await vector_repo.find_similar(memory_id, fingerprint=fp, threshold=threshold)
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            raise
