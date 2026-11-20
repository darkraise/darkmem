import asyncio
import logging
import time
from collections import OrderedDict
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select

from app.repositories.graph import PostgresGraphRepository
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.schemas.memory import MemoryCreate
from app.services.classification_llm import ClassificationService
from app.services.extraction import ExtractionService
from app.services.llm import LLMOrchestrator, lease_llm
from app.services.confidence import CONFIDENCE_DEFAULT, estimate_confidence
from app.services.events import record_event
from app.services.feature_flags import get_feature_flags_dict
from app.services.stated_expiry import derive_stated_expiry
from app.services.usage_recorder import UsageSubject, subject_scope
from app.services.fact_provenance import (
    reconcile_memory_sources,
    withdraw_memory_sources,
)
from app.services.relations import names_distinct
from app.services.supersession import detect_supersessions, is_supersession_trigger
from app.services import ml_runtime, prompt
from app.taxonomy import normalize_memory_type

if TYPE_CHECKING:
    from app.models.memory import Memory

logger = logging.getLogger(__name__)

# A capture that sent no importance stores the schema default; only then does
# the extractor's estimate replace it.
_DEFAULT_IMPORTANCE = MemoryCreate.model_fields["importance"].default

async def _get_feature_flags(session_factory) -> dict:
    async with session_factory() as session:
        return await get_feature_flags_dict(session)


def build_pipeline_entry(memory: "Memory") -> dict:
    """The `process_batch` entry that replays a stored memory."""
    return {
        "memory_id": memory.id,
        "content": memory.content,
        "source": memory.source,
        "project": memory.project,
        "tags": [t.name for t in memory.tags],
        "memory_type": memory.memory_type,
        "created_at": memory.created_at.isoformat() if memory.created_at else "",
    }


async def load_pipeline_entry(session_factory, memory_id) -> dict | None:
    """`build_pipeline_entry` for one memory id, or None once it is deleted."""
    from sqlalchemy.orm import selectinload
    from app.models.memory import Memory

    async with session_factory() as session:
        memory = (await session.execute(
            select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        )).scalar_one_or_none()
        return build_pipeline_entry(memory) if memory else None


def memory_retry_handler(pipeline, session_factory):
    """The `memory_ingest` retry handler: replay one memory through `pipeline`."""

    async def retry(memory_id) -> None:
        entry = await load_pipeline_entry(session_factory, memory_id)
        if entry is not None:
            await pipeline.process_batch([entry])

    return retry


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

DUPLICATE_STATUSES: tuple[str, ...] = ("active",)


# A stored `local` row on an install without the `[ml]` extra classifies
# through the LLM-backed classifier; one error per process says so.
_local_classifier_unavailable_logged = False


def _log_local_classifier_unavailable() -> None:
    global _local_classifier_unavailable_logged
    if _local_classifier_unavailable_logged:
        return
    _local_classifier_unavailable_logged = True
    logger.error(
        "classifier_kind=local is stored but torch and transformers (the [ml] "
        "extra) are not installed; classifying with the LLM-backed classifier"
    )


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
        # doesn't open a session and re-read the config on every batch just to
        # learn whether the (rarely-set) classifier_kind points it at the
        # in-process ML classifier. None means "use self.classification".
        self._classifier_cache: tuple[float, object | None] | None = None
        self._classifier_cache_ttl = 30.0

    @contextmanager
    def _pinned(self):
        """Keep one provider generation alive through all pre-dispatch awaits."""
        with lease_llm(self.llm):
            pinned = copy(self)
            pinned.extraction = copy(self.extraction)
            pinned.classification = copy(self.classification)
            try:
                yield pinned
            finally:
                self.last_entity_cache_stats = pinned.last_entity_cache_stats
                if self.llm is pinned.llm:
                    self._classifier_cache = pinned._classifier_cache

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
                if ml_runtime.ml_extra_available():
                    from app.services.classification_ml import MLClassificationService
                    from app.services.ml_runtime import ml_model_manager
                    resolved = MLClassificationService(
                        ml_model_manager,
                        _LOCAL_CLASSIFIER_MODEL_REPO,
                        _LOCAL_CLASSIFIER_TTL_SECONDS,
                    )
                else:
                    _log_local_classifier_unavailable()
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
            db_hits: dict[str, list[float]] = {}
            try:
                async with self.session_factory() as session:
                    repo = PostgresGraphRepository(session)
                    db_hits = await repo.get_cached_entity_embeddings(
                        still_missing, fingerprint,
                    )
            except Exception:
                # The DB cache is an optimisation. Losing it must cost latency —
                # every name becomes a miss and gets re-embedded — not the batch.
                logger.warning(
                    "Failed to read entity embedding cache from DB", exc_info=True,
                )
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
        batch_memory_ids: list[UUID] | None = None,
        embed_error: str | None = None,
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
            "error": None if vector is not None else (embed_error or "Content embedding failed"),
        }
        if isinstance(extraction, dict):
            status["extract"] = "ok"
            status["entities_count"] = len(extraction.get("entities", []))
            status["relations_count"] = len(extraction.get("relationships", []))
            if extraction.get("_error"):
                # The buffer retries a transient failure and settles a
                # deterministic one, which a retry would only repeat.
                kind = extraction.get("_error_kind", "deterministic")
                status["extract"] = "error"
                status["extract_failure"] = kind
                status["error"] = status["error"] or (
                    f"Extraction failed ({kind}): {extraction['_error']}"
                )

            # Apply canonical_map to entity names and relationship endpoints.
            # The map is keyed by (name_lower, entity_type) so a canonical rewrite
            # only collapses same-typed entities — a `concept` "react" must not be
            # renamed onto a `tool` "react". Relationship endpoints carry no type,
            # so resolve each endpoint's type from this extraction's own entities;
            # if unknown, leave the endpoint untouched.
            # Built to completion BEFORE the rewrite loop below mutates any
            # entity["name"]: built afterwards it would look endpoints up under
            # already-rewritten names and silently resolve nothing.
            ent_types: dict[str, set[str]] = {}
            for e in extraction.get("entities", []):
                etype = e.get("type")
                if etype:
                    ent_types.setdefault((e.get("name") or "").lower(), set()).add(etype)

            def _endpoint_type(name_lower: str) -> str | None:
                # A name emitted under two types in one extraction is a name
                # whose type cannot be recovered. Picking one of them rewrites
                # the endpoint under a type it may not have, which is the
                # cross-type rebinding the (name, type) key exists to prevent.
                types = ent_types.get(name_lower) or set()
                return next(iter(types)) if len(types) == 1 else None

            try:
                for entity in extraction.get("entities", []):
                    low = entity["name"].lower()
                    key = (low, entity.get("type"))
                    if key in canonical_map:
                        entity["name"] = canonical_map[key]
                for rel in extraction.get("relationships", []):
                    src_low = (rel.get("source") or "").lower()
                    tgt_low = (rel.get("target") or "").lower()
                    src_key = (src_low, _endpoint_type(src_low))
                    tgt_key = (tgt_low, _endpoint_type(tgt_low))
                    if src_key in canonical_map:
                        rel["source"] = canonical_map[src_key]
                    if tgt_key in canonical_map:
                        rel["target"] = canonical_map[tgt_key]
            except (AttributeError, KeyError, TypeError) as e:
                # A malformed entity dict is the extractor's failure, not the
                # writer's; attributing it to the vector step would report a
                # write that was never attempted.
                status["extract"] = "error"
                status["error"] = f"Extraction returned a malformed entity: {e}"
                status["entities_count"] = 0
                status["relations_count"] = 0
                extraction = None
        else:
            status["extract"] = "error"
            status["error"] = status["error"] or "Extraction returned invalid data"
            extraction = None

        async with self.session_factory() as session:
            # Bound here, not inside savepoint A: a failed Phase 1 skips the
            # writes entirely, and the per-memory journal below still reads this.
            mem_record = None
            # Plain copies of everything read AFTER the savepoints. A savepoint-B
            # rollback expires ``mem_record`` wholesale, and an expired attribute
            # read outside an ``await`` triggers a synchronous lazy load that
            # raises MissingGreenlet — which would escape before session.commit()
            # and discard savepoint A's already-successful write.
            mem_project = entry.get("project")
            mem_created_at = None
            vector_repo = PostgresVectorRepository(session)
            graph_repo = PostgresGraphRepository(session)

            if status["embed"] == "ok":
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
                        # Loaded before the upsert so a vector-write failure
                        # still leaves the journal below with a real project.
                        from sqlalchemy import select as sa_select
                        from app.models.memory import Memory
                        mem_result = await session.execute(
                            sa_select(Memory).where(Memory.id == memory_id)
                        )
                        mem_record = mem_result.scalar_one_or_none()
                        if mem_record:
                            mem_project = mem_record.project
                            mem_created_at = mem_record.created_at

                        payload = {
                            "memory_id": str(memory_id), "content": content,
                            "source": source, "tags": tags,
                            "memory_type": resolved_memory_type,
                            "created_at": created_at,
                        }
                        if llm_classification:
                            payload["classified_type"] = llm_classification.get("hall", "")
                            payload["summary"] = llm_classification.get("summary", "")
                            payload["emotions"] = llm_classification.get("emotions", [])
                            payload["flags"] = llm_classification.get("flags", [])

                        await vector_repo.upsert(
                            memory_id=memory_id, vector=vector, payload=payload,
                            fingerprint=content_fingerprint,
                        )
                        status["vector"] = "ok"

                        if mem_record:
                            if llm_classification:
                                mem_record.classified_type = llm_classification.get("hall") or None
                                mem_record.summary = llm_classification.get("summary") or None
                                mem_record.emotions = llm_classification.get("emotions") or None
                                mem_record.flags = llm_classification.get("flags") or None

                            mem_record.memory_type = resolved_memory_type
                            if (
                                extracted_importance is not None
                                and mem_record.importance == _DEFAULT_IMPORTANCE
                            ):
                                try:
                                    mem_record.importance = float(extracted_importance)
                                except (TypeError, ValueError):
                                    pass
                            mem_record.confidence = estimate_confidence(content, resolved_memory_type)

                            # Doc 08 §2.3's activation (T2.34): a memory that
                            # states its own retention self-expires without the
                            # caller setting a TTL. Only ever fills a NULL — an
                            # explicit `expires_at` is the caller's instruction
                            # and a derivation that overrode it would be the
                            # same defect as a wrong parse, in the other
                            # direction. `created_at` is the anchor, so a
                            # reprocess derives the same instant it did at
                            # capture rather than sliding with wall time.
                            if mem_record.expires_at is None:
                                stated = derive_stated_expiry(
                                    content,
                                    reference_time=mem_created_at or datetime.now(timezone.utc),
                                )
                                if stated is not None:
                                    mem_record.expires_at = stated
                except Exception as e:
                    status["vector"] = "error"
                    status["graph"] = "skipped"
                    status["error"] = status["error"] or f"Vector write failed: {e}"
                    logger.error(f"Vector write failed for {memory_id}: {e}")
                    mem_record = None

                # Savepoint B: the entity/relationship graph. A failure here rolls
                # back only the graph; the embedding from savepoint A survives and
                # the failure is attributed to the graph step, not the vector one.
                # A failed extraction is the extractor's own failure result
                # (`ExtractionService._error_result`: no entities, no relations),
                # so it has nothing to write and must not enter the savepoint:
                # the strip below would replace a good graph with nothing.
                if status["vector"] == "ok" and status["extract"] == "ok" and isinstance(extraction, dict):
                    try:
                        async with session.begin_nested():
                            # Idempotent re-extraction: strip any prior
                            # contributions of this memory_id from the entity
                            # graph before writing the new set. Otherwise
                            # re-running with a different model just accumulates
                            # duplicate-by-type rows on top of the previous
                            # extraction. ``delete_by_memory_id`` removes a
                            # relation only when no live memory still asserts it
                            # and an entity only when no live memory asserts it
                            # AND no surviving relation references it, so
                            # entities shared with other memories are preserved
                            # and no other memory's edge is cascaded away.
                            #
                            # Inside savepoint B rather than ahead of it, so
                            # strip-and-write is one atomic replace: a failure
                            # here rolls the strip back and the memory keeps its
                            # previous graph, instead of the outer commit making
                            # the deletion durable and leaving it with no graph
                            # at all and a technologies denorm matching nothing.
                            # For the same reason an ordinary extraction failure,
                            # which never enters this savepoint, no longer empties
                            # a good graph.
                            await graph_repo.delete_by_memory_id(memory_id)

                            # Map each canonical (lower-cased) entity name to the
                            # type it was written with, so relationships resolve
                            # endpoints by (name, entity_type) — entity uniqueness
                            # — instead of name alone, which can bind to a
                            # same-named entity of a different type.
                            name_to_type: dict[str, str] = {
                                entity["name"].strip().lower(): entity["type"]
                                for entity in extraction.get("entities", [])
                            }
                            # Concurrent writers upsert shared rows and hold
                            # the locks until commit, so every writer takes
                            # them in one global order or two can deadlock.
                            entities = sorted(
                                extraction.get("entities", []),
                                key=lambda e: (e["name"].strip().lower(), e["type"]),
                            )
                            relationships = sorted(
                                extraction.get("relationships", []),
                                key=lambda r: (
                                    (r["source"] or "").strip().lower(),
                                    (r["target"] or "").strip().lower(),
                                    r["type"],
                                ),
                            )
                            # Build a display-name map keyed by the canonical
                            # lower-cased name. The canonical name is what we
                            # write to ``entities.name``; the original casing
                            # is preserved in properties so the UI can render
                            # ``Darkmem`` instead of ``darkmem``.
                            for entity in entities:
                                display_name = entity["name"]
                                canonical_name = display_name.strip().lower()
                                props = dict(entity.get("properties") or {})
                                if display_name != canonical_name:
                                    props.setdefault("display_name", display_name)
                                created = await graph_repo.create_entity(
                                    name=canonical_name, entity_type=entity["type"],
                                    properties=props, memory_id=memory_id,
                                )
                                # Keyed by ``canonical_name`` — the name this row is
                                # actually written under — never by the pre-rewrite
                                # variant name. Phase 3 embeds raw extracted names,
                                # so a canonicalized variant's survivor name is
                                # usually absent from ``name_to_embedding``; when it
                                # is, this looks up nothing and the survivor's
                                # stored embedding is left alone instead of being
                                # overwritten with a vector computed for a
                                # different name. A name that stays distinct still
                                # resolves here, since its own canonical_name is
                                # its own extracted name.
                                emb = name_to_embedding.get(canonical_name)
                                if emb and created:
                                    await graph_repo.upsert_entity_embedding(
                                        created["id"], emb, fingerprint=entity_fingerprint,
                                    )
                            for rel in relationships:
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
                                # Denormalised onto the memory row so the GIN index
                                # on `memories.technologies` answers the supersession
                                # overlap test and the retrieval filter without
                                # joining `entities`. Assigned whole, from the graph
                                # as it stands after this savepoint's strip and
                                # write: a partial update would leave a memory whose
                                # denorm covers some of its entities and not others,
                                # and supersession would then fire on some REPLACES
                                # targets and silently not on the rest.
                                mem_record.technologies = (
                                    await graph_repo.technologies_for_memory(memory_id)
                                )
                                # Trigger on a REPLACES-family relation, not on
                                # this memory's own technologies: the detector keys
                                # off the replacement *target* overlapping a
                                # candidate's technologies, which is independent of
                                # whether the new memory produced a tech entity of
                                # its own. The predicate is shared with the detector
                                # so this gate and its filter can never disagree.
                                if any(
                                    is_supersession_trigger(r.get("type"))
                                    for r in extraction.get("relationships", [])
                                ):
                                    await session.flush([mem_record])
                                    await detect_supersessions(
                                        session,
                                        new_memory_id=memory_id,
                                        new_memory_text=content,
                                        new_memory_created_at=mem_created_at,
                                        project=mem_project,
                                        new_relations=extraction.get("relationships", []),
                                        excluded_memory_ids=batch_memory_ids,
                                    )

                            # The vault enqueue hook (doc 05 §8.4). Inside
                            # savepoint B, not after the commit: the withdrawal
                            # and the inline expiry are justified *by* the graph
                            # replace, so they have to share its atomicity: a B
                            # failure unwinds the withdrawal, the expiry and the
                            # append-only event together, never a half-applied
                            # subset. Post-commit would open the opposite
                            # window — a crash between the commit and the
                            # reconcile leaves a new graph with stale
                            # provenance, no event, and nothing to notice it.
                            # (It would *not* strand an expiry for a write that
                            # never landed, as an earlier draft of this comment
                            # claimed: the reconcile reads the asserted set back
                            # from disk, so after a B rollback it would see the
                            # prior graph and no-op.)
                            # Phase 5 only enqueues; it never recomputes a
                            # verification status (invariant 15).
                            await reconcile_memory_sources(session, memory_id=memory_id)

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
            if not batch_memory_ids:
                await record_event(
                    session,
                    event_type="extracted",
                    object_type="memory",
                    object_id=memory_id,
                    project=mem_project,
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
                    # Normalized here rather than left to the CAST: ids cross
                    # this boundary as either str or UUID depending on which
                    # probe answered, and a mismatch drops matches silently.
                    normalized = [
                        {"memory_id": UUID(str(ref["memory_id"])),
                         "score": float(ref["score"])}
                        for ref in similar
                    ]
                    await xref_repo.store_crossrefs(memory_id, normalized)
                    await xref_session.commit()
            except Exception as e:
                logger.warning(f"Crossref computation failed for {memory_id}: {e}")

        return status

    async def process_memory(
        self,
        memory_id,
        content: str,
        source: str,
        tags: list[str],
        memory_type: str | None,
        created_at: str,
        project: str | None = None,
    ) -> dict:
        """Process a single memory. Delegates to process_batch for consistent phasing."""
        entry = {
            "memory_id": memory_id,
            "content": content,
            "source": source,
            "project": project,
            "tags": tags,
            "memory_type": memory_type,
            "created_at": created_at,
        }
        results = await self.process_batch([entry])
        return results[0]

    async def process_batch(self, entries: list[dict]) -> list[dict]:
        """Process a batch using one captured provider generation."""
        if not entries:
            return []
        with self._pinned() as pipeline:
            return await pipeline._process_batch(entries)

    async def _process_batch(self, entries: list[dict]) -> list[dict]:
        """Process multiple memories through phased pipeline.

        Phases:
          1. Content embedding (chunked, concurrent)
          2. Extraction and LLM classification (per-memory, concurrent)
          3. Entity embedding with cache
          4. Dedup lookup (per unique name)
          5. Per-memory writes (concurrent)

        Returns a list the same length as ``entries`` on every path, and every
        entry gets a ``pipeline_failures`` row (or a resolution) and exactly one
        ``pipeline.*`` broadcast.
        """
        if not entries:
            return []

        try:
            normalized = await self._run_phases(entries)
        except Exception as e:
            # The backstop that makes "no memory leaves process_batch without a
            # status" a property rather than a coincidence. Guarding each phase
            # individually re-opens the hole on the next phase edit, and an
            # exception escaping here records NO failure row at all — the whole
            # batch becomes invisible to triage rather than mislabelled.
            logger.exception("Batch pipeline failed before the write: %s", e)
            normalized = [
                {
                    "memory_id": str(entry.get("memory_id")),
                    "embed": "unknown", "extract": "unknown",
                    "vector": "error", "graph": "error",
                    "entities_count": 0, "relations_count": 0,
                    "error": str(e),
                }
                for entry in entries
            ]

        await self._record_batch_outcomes(entries, normalized)
        return normalized

    async def _run_phases(self, entries: list[dict]) -> list[dict]:
        # The unit of work the batched embeds belong to. Phase 1 embeds every
        # content in one call and Phase 3 embeds a set of entity names deduped
        # and cache-hit across the whole batch, so neither has a per-memory
        # share to divide -- an undefined quantity, not merely an imprecise one.
        # A mixed-project batch claims no project rather than the first entry's,
        # which would be a wrong answer where None is a missing one.
        batch_projects = {e.get("project") for e in entries}
        batch_subject = UsageSubject(
            "batch",
            str(uuid4()),
            batch_projects.pop() if len(batch_projects) == 1 else None,
        )
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
        embed_error: str | None = None
        try:
            with subject_scope(batch_subject):
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
            embed_error = f"Content embedding failed: {type(e).__name__}: {e}"
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
                embed_error = f"Embedder registration failed: {type(e).__name__}: {e}"
                vectors = [None] * len(entries)
                embedding_fingerprint = None

        # Phase 2: Extraction and LLM classification. Classification always runs
        # alongside extraction — the regex classifier it used to A/B against is
        # gone, so the LLM (or the in-process ML classifier when the
        # classification purpose's classifier_kind is 'local') is the sole
        # source of the enrichment columns.
        ext_prompt = prompt.get("extraction")
        cls_prompt = prompt.get("classification")
        semaphore = asyncio.Semaphore(pipeline_concurrency)

        def _entry_subject(entry: dict) -> UsageSubject:
            """Passed explicitly, never scoped.

            ``asyncio.gather`` wraps each coroutine in a Task and every Task
            copies the *same* parent context, so a subject set around the gather
            reaches all of them identically. Only a value carried into the call
            can say which memory paid for it.
            """
            return UsageSubject(
                "memory", str(entry.get("memory_id")), entry.get("project"),
            )

        async def run_extract(entry: dict, with_classification: bool = False):
            async with semaphore:
                return await self.extraction.extract(
                    entry["content"], system_prompt=ext_prompt,
                    relation_rescue=relation_rescue,
                    with_classification=with_classification,
                    usage_subject=_entry_subject(entry),
                )

        # Pick the classifier implementation (LLM-backed, or in-process ML when
        # the classification purpose's classifier_kind is 'local'). Cached for a
        # short TTL so it isn't re-resolved with a DB round-trip on every batch.
        classifier = await self._resolve_classifier()

        async def run_classify(entry: dict):
            async with semaphore:
                try:
                    areas = flags.get("classification_areas", ["general"])
                    mode = flags.get("classification_mode", "simple")
                    return await classifier.classify(
                        entry["content"], areas, cls_prompt, mode=mode,
                        usage_subject=_entry_subject(entry),
                    )
                except Exception as exc:
                    logger.warning("Classification failed: %s", exc)
                    return None

        # Fold classification into the single extraction call when the classifier
        # is the LLM-backed one AND the type vocabulary is the fixed simple-7
        # set. In that regime extraction's ``memory_type`` already
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
                *[run_extract(e, with_classification=True) for e in entries]
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
            extract_tasks = [run_extract(e) for e in entries]
            classify_tasks = [run_classify(e) for e in entries]
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
            with subject_scope(batch_subject):
                name_to_embedding, entity_fingerprint = await self._embed_entity_names(
                    unique_names_list, entity_fingerprint, ttl_seconds,
                    embed_chunk_size, embed_concurrency,
                )
        else:
            logger.info("Phase 3 skipped: no entities to embed")

        # Phase 4: Dedup lookup (one call per unique (name, entity_type)).
        #
        # ``canonical_map`` is the contract with Phase 5:
        #   key   (name_lower, entity_type) — the extraction's own lowercased
        #         name and its normalized taxonomy type, which together are the
        #         entity uniqueness key
        #   value the surviving entity's name, lowercase (entity names are
        #         lowercase on disk; the original casing lives in
        #         properties.display_name)
        # Only canonicalized names appear; a name that stays distinct is absent
        # rather than mapped to itself, so ``key in canonical_map`` means
        # "rewrite this one". Phase 5 must resolve entity names *and* relation
        # endpoints by that same key — an endpoint resolved by name alone can
        # bind to a same-named entity of another type.
        #
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
                        # An ANN hit is necessary but not sufficient. Cosine at
                        # 0.85 recalls surface variants (postgres/postgresql,
                        # ~0.974) and also names that differ only by a
                        # discriminating token yet embed almost identically
                        # ("february outage"/"march outage", ~0.885).
                        # ``names_distinct`` is the precision gate on the second
                        # class, and it is deliberately the stricter side of the
                        # trade: a false merge cannot be undone by
                        # re-extraction, because the graph then records only the
                        # merged form.
                        if (
                            match
                            and match["name"].lower() != lower_name
                            and not names_distinct(lower_name, match["name"])
                        ):
                            return (lower_name, etype), match["name"].lower()
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
        batch_memory_ids = [UUID(str(entry["memory_id"])) for entry in entries] if len(entries) > 1 else None

        async def run_write(entry: dict, vector: list[float] | None, extraction, classification):
            async with semaphore:
                return await self._write_memory(
                    entry, vector, content_write_fingerprint, entity_write_fingerprint,
                    extraction, classification,
                    name_to_embedding, canonical_map,
                    batch_memory_ids=batch_memory_ids,
                    embed_error=embed_error,
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

        if batch_memory_ids:
            from app.models.memory import Memory

            statuses = {result["memory_id"]: result for result in normalized}
            replacements = {
                str(entry["memory_id"]): extraction.get("relationships", [])
                for entry, extraction in zip(entries, extractions)
                if isinstance(extraction, dict)
                and statuses[str(entry["memory_id"])]["graph"] == "ok"
            }
            # Every status here was committed by its own Phase 5 write; a
            # failure reading them back must not relabel them as failed writes.
            try:
                async with self.session_factory() as session:
                    stored = (await session.execute(
                        select(Memory.id, Memory.content, Memory.created_at, Memory.project)
                        .where(Memory.id.in_(batch_memory_ids))
                        .order_by(Memory.created_at, Memory.id)
                    )).all()
                    for memory_id, content, created_at, project in stored:
                        relations = replacements.get(str(memory_id), [])
                        if not any(is_supersession_trigger(relation.get("type")) for relation in relations):
                            continue
                        try:
                            async with session.begin_nested():
                                await detect_supersessions(
                                    session, new_memory_id=memory_id,
                                    new_memory_text=content, new_memory_created_at=created_at,
                                    project=project, new_relations=relations,
                                    candidate_memory_ids=batch_memory_ids,
                                )
                        except Exception as error:
                            status = statuses[str(memory_id)]
                            status["graph"] = "error"
                            status["error"] = status["error"] or f"Batch supersession failed: {error}"
                            logger.exception("Batch supersession failed for %s", memory_id)
                    projects = {str(row.id): row.project for row in stored}
                    for entry, status in zip(entries, normalized):
                        await record_event(
                            session, event_type="extracted", object_type="memory",
                            object_id=UUID(str(entry["memory_id"])),
                            project=projects.get(str(entry["memory_id"]), entry.get("project")),
                            payload={**status, "outcome": _derive_outcome(status)},
                        )
                    await session.commit()
            except Exception:
                logger.exception("Same-batch reconciliation failed; keeping the committed statuses")

        return normalized

    async def _record_batch_outcomes(
        self, entries: list[dict], normalized: list[dict],
    ) -> None:
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
                    # Per memory in its own savepoint: one bad row must not
                    # abort the rest of the batch's failure records, which is
                    # the batch's only route into triage.
                    try:
                        async with failure_session.begin_nested():
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
                    except Exception as e:
                        logger.warning(
                            "Failed to record pipeline failure for %s: %s",
                            mem_id_str, e,
                        )
                await failure_session.commit()
        except Exception as e:
            logger.warning("Failed to record pipeline failures for batch: %s", e)

        # Doc 05 §10: exactly one pipeline.{completed,partial,failed} per memory
        # per batch, on EVERY path. Emitted here rather than from _write_memory,
        # which cannot fire for a memory whose own write raised — that path
        # produced a normalised status and no broadcast at all. Emitting after
        # the pipeline_failures commit also means a UI reacting to
        # pipeline.failed by fetching the failure list cannot race an unwritten
        # row.
        if self._broadcast:
            for status in normalized:
                try:
                    await self._broadcast(
                        f"pipeline.{_derive_outcome(status)}", status,
                    )
                except Exception as e:
                    logger.warning(f"Pipeline broadcast failed: {e}")

    async def delete_memory(self, memory_id: UUID, broadcast: bool = True):
        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
                graph_repo = PostgresGraphRepository(session)
                await vector_repo.delete(memory_id)
                await graph_repo.delete_by_memory_id(memory_id)
                # A deleted memory sources nothing, so the whole set goes
                # (doc 05 §8.4). Same transaction as the graph strip for the
                # same reason Phase 5's hook sits inside savepoint B.
                await withdraw_memory_sources(session, memory_id=memory_id)
                await session.commit()
            if broadcast and self._broadcast:
                try:
                    await self._broadcast("memory.deleted", {"memory_id": str(memory_id)})
                except Exception as broadcast_err:
                    logger.warning(f"WebSocket broadcast failed: {broadcast_err}")
        except Exception:
            logger.exception(f"Cleanup failed for {memory_id}")

    async def semantic_search(
        self,
        query: str,
        limit: int = 20,
        semantic_weight: float = 0.7,
        filters: MemoryFilter | None = None,
    ) -> list[dict]:
        with self._pinned() as pipeline:
            return await pipeline._semantic_search(query, limit, semantic_weight, filters)

    async def _semantic_search(
        self, query: str, limit: int, semantic_weight: float, filters: MemoryFilter | None,
    ) -> list[dict]:
        try:
            from app.services.feature_flags import get_feature_flags_dict
            from app.services.hybrid_search import HybridSearchService

            async with self.session_factory() as session:
                flags = await get_feature_flags_dict(session)
                return await HybridSearchService(self.llm, session).search_ranked(
                    query, limit=limit, semantic_weight=semantic_weight,
                    filters=filters, flags=flags,
                )
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise

    async def find_duplicates(self, memory_id: UUID, threshold: float = 0.9) -> list[dict]:
        """Find memories whose vectors are above ``threshold`` against this one.

        Compares within whichever fingerprint already holds an embedding for
        the source memory. If none exist, returns an empty list.

        The scope is derived from the source memory rather than supplied by the
        caller: a duplicate is only actionable inside the project that owns the
        supersession and merge decisions, and a superseded near-twin returned as
        a peer invites a merge into a row the corpus has already replaced.
        """
        from app.models.memory import Memory

        try:
            async with self.session_factory() as session:
                vector_repo = PostgresVectorRepository(session)
                fp = await vector_repo.find_fingerprint_for_memory(memory_id)
                if not fp:
                    return []
                project = (
                    await session.execute(
                        select(Memory.project).where(Memory.id == memory_id)
                    )
                ).scalar_one_or_none()
                if project is None:
                    return []
                filters = MemoryFilter(project=project, statuses=DUPLICATE_STATUSES)
                return await vector_repo.find_similar(
                    memory_id, fingerprint=fp, threshold=threshold, filters=filters,
                )
        except Exception as e:
            logger.error(f"Duplicate search failed: {e}")
            raise
