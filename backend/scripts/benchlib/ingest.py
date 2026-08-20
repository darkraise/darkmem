"""Drives darkmem's real ProcessingPipeline over a loaded corpus against the
bench database, pinning the gate-state configuration the run measures under.

No forked phase logic lives here -- every memory is written by the shipping
ProcessingPipeline.process_batch, never a reimplementation of it. Compose
this module with benchlib.corpus.load_corpus() for entries and
benchlib.caching_llm.CachingLLMOrchestrator for the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from benchlib import bench_db  # noqa: F401  (ensures DATABASE_URL override first)
from benchlib.caching_llm import CachingLLMOrchestrator

from app.config import FEATURE_FLAGS_DEFAULTS, settings
from app.models.config import Config
from app.models.llm_config import LLMPurposeConfigRow
from app.repositories.relational import PostgresMemoryRepository
from app.schemas.memory import MemoryCreate
from app.services.feature_flags import FEATURE_FLAGS_KEY
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset


@dataclass(frozen=True)
class GateConfig:
    """The subset of today's real gate-state fields a bench run must pin
    explicitly, not inherit from whatever the DB happens to hold (doc 17
    §7's gate-state caveat; CLAUDE.md's Pipeline-phases section).

    classifier_kind: ``'local'`` -> the pipeline swaps in the in-process
        classifier for the classification purpose; ``'llm'`` or None -> the
        LLM classifier.
    classification_mode: folds into extraction's schema and the
        extraction/classification merge gate.
    relation_rescue: the only surviving ingestion-side behavioural flag
        (CLAUDE.md) -- it changes the graph the bench measures.

    This field was ``ml_profile_ref`` until T0.12c, which dropped the
    ``ml_profiles`` table and re-homed the choice inline on the
    classification purpose row as ``classifier_kind`` (doc 04 §7). Doc 17 §7
    named ``classifier_kind`` all along; it simply did not exist yet.
    """
    CLASSIFIER_KINDS = ("llm", "local")

    classifier_kind: str | None = None
    classification_mode: str = "simple"
    relation_rescue: bool = True


@dataclass
class IngestResult:
    outcomes: list[dict]
    fingerprint: str
    gate_config: dict
    live_calls: int


async def pin_gate_config(session_factory, gate: GateConfig) -> dict:
    """Write ``gate``'s fields to the DB explicitly and return them as a
    plain dict, ready for the ledger.

    This SETS the values -- it does not read whatever the DB already holds
    and log that. A flag flip elsewhere (another process, a leftover value
    from a prior run) is overwritten here rather than silently inherited.

    That promise covers the WHOLE feature-flags row, not just the two flags
    GateConfig names: the row is rewritten as FEATURE_FLAGS_DEFAULTS plus
    ``gate``'s overrides. ``process_batch`` reads flags GateConfig does not
    model -- ``classification_areas`` (pipeline.py:605) builds the
    classification prompt's allowed-type list, and the concurrency/batch
    flags shape how calls are chunked -- so merging over an ambient row
    would let a leftover value change what the run measures while the
    recorded ``gate_config`` stayed identical to a clean run's.
    """
    async with session_factory() as session:
        if gate.classifier_kind is not None and gate.classifier_kind not in GateConfig.CLASSIFIER_KINDS:
            raise ValueError(
                f"gate.classifier_kind={gate.classifier_kind!r} is not one of "
                f"{GateConfig.CLASSIFIER_KINDS}; pin a kind that exists before running"
            )

        result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
        flags_row = result.scalar_one_or_none()
        pinned_flags = dict(FEATURE_FLAGS_DEFAULTS)
        pinned_flags["classification_mode"] = gate.classification_mode
        pinned_flags["relation_rescue"] = gate.relation_rescue
        if flags_row is not None:
            flags_row.value = pinned_flags
        else:
            session.add(Config(key=FEATURE_FLAGS_KEY, value=pinned_flags))

        purpose_row = (await session.execute(
            select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == "classification")
        )).scalar_one_or_none()
        if purpose_row is not None:
            purpose_row.classifier_kind = gate.classifier_kind
        else:
            from app.models.llm_provider import LLMProviderRow

            defaults = settings.llm_classification
            if (await session.execute(
                select(LLMProviderRow).where(LLMProviderRow.name == "bench-settings-default")
            )).scalar_one_or_none() is None:
                session.add(LLMProviderRow(
                    name="bench-settings-default",
                    api_kind=defaults.api_kind,
                    base_url=defaults.base_url,
                    api_key=defaults.api_key,
                ))
                await session.flush()

            session.add(LLMPurposeConfigRow(
                purpose="classification",
                provider_name="bench-settings-default",
                model=defaults.model,
                dimensions=defaults.dimensions,
                reasoning=defaults.reasoning,
                params=defaults.params,
                classifier_kind=gate.classifier_kind,
            ))

        await session.commit()

    # process_batch reads feature flags through a 5s TTL single-flight cache
    # (app.services.pipeline._get_feature_flags_cached), keyed at module
    # scope, not per-pipeline-instance. Without this reset, a run started
    # within 5s of a previous pin in the same process would silently
    # measure the PRIOR gate state instead of the one just written.
    _flag_cache_reset()

    return {
        "classifier_kind": gate.classifier_kind,
        "classification_mode": gate.classification_mode,
        "relation_rescue": gate.relation_rescue,
    }


def _parse_created_at(value, entry_idx: int) -> datetime:
    if not isinstance(value, str):
        raise ValueError(
            f"entry {entry_idx}: created_at must be an ISO-8601 string, got {value!r}"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"entry {entry_idx}: created_at {value!r} is not ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


async def _create_memory_rows(session_factory, entries: list[dict]) -> list[dict]:
    """Pre-create a bare ``memories`` row per entry and return process_batch
    entries carrying the DB-assigned ``memory_id``.

    process_batch enriches an EXISTING memory (vector upsert + memory-row
    update); it never inserts the base row itself -- entries[i]["memory_id"]
    is read, not generated (pipeline.py:259, KeyError if absent), and the
    per-fingerprint embedding table FKs to ``memories(id)``, so writing
    against an id with no backing row fails with ForeignKeyViolationError.
    app.services.memory.MemoryService.batch_create_memories shows this is
    the real, production shape: create + commit the rows first (their own
    session/transaction), THEN call process_batch (which opens its own
    sessions per phase) -- never interleave the two in one transaction
    (CLAUDE.md's async-session-lifetime invariant).

    An entry that already carries a memory_id is passed through unchanged,
    for callers re-driving an already-created memory.

    A corpus ``created_at`` is honoured by overwriting the server-stamped
    default before the commit, so the row carries the date the corpus
    declared. detect_supersessions orders candidates by ``created_at``
    (pipeline.py:463-470) -- discarding it would silently reduce a corpus
    written to exercise the date rules to a test of the id tie-break.
    """
    prepared: list[dict] = []
    async with session_factory() as session:
        repo = PostgresMemoryRepository(session)
        for idx, entry in enumerate(entries):
            if "memory_id" in entry:
                prepared.append(entry)
                continue
            data = MemoryCreate(
                content=entry["content"],
                tags=entry.get("tags", []),
                source=entry.get("source", "bench"),
                memory_type=entry.get("memory_type"),
                importance=entry.get("importance", 0.5),
                metadata=entry.get("metadata", {}),
                project=entry.get("project"),
            )
            memory = await repo.create(
                content=data.content, source=data.source, source_agent=data.source_agent,
                memory_type=data.memory_type, importance=data.importance,
                metadata=data.metadata, expires_at=data.expires_at, project=data.project,
            )
            declared_created_at = entry.get("created_at")
            if declared_created_at:
                memory.created_at = _parse_created_at(declared_created_at, idx)
            if data.tags:
                await repo.set_tags(memory.id, data.tags)
                await session.refresh(memory, ["tags"])
            prepared.append({
                "memory_id": memory.id,
                "content": memory.content,
                "source": memory.source,
                "tags": [t.name for t in memory.tags],
                "memory_type": memory.memory_type,
                "created_at": memory.created_at.isoformat() if memory.created_at else "",
            })
        await session.commit()
    return prepared


async def run_ingest(
    llm: CachingLLMOrchestrator,
    entries: list[dict],
    gate: GateConfig,
    session_factory=bench_db.session_factory,
) -> IngestResult:
    """Compose the bench DB + caching LLM + the real ProcessingPipeline and
    drive ``entries`` through process_batch end to end.

    A fresh ProcessingPipeline is constructed on every call: its classifier
    resolution cache (self._classifier_cache) is instance-scoped, so a new
    instance always re-resolves classifier_kind against the DB row
    pin_gate_config just wrote, instead of risking a stale resolution
    carried over from a previous pipeline instance in the same process.
    """
    gate_config = await pin_gate_config(session_factory, gate)

    prepared_entries = await _create_memory_rows(session_factory, entries)

    # Reset so the fingerprints recorded below reflect only this run, not a
    # prior process_batch call this llm instance may have served earlier in
    # the same process (e.g. two run_ingest calls sharing one cache-backed
    # orchestrator to prove the second is fully cached).
    llm.fingerprints_seen.clear()
    live_calls_before = llm.live_calls

    pipeline = ProcessingPipeline(llm, session_factory)
    outcomes = await pipeline.process_batch(prepared_entries)

    live_calls = llm.live_calls - live_calls_before

    # embed_batch_chunked already raises RuntimeError when its own chunk
    # calls disagree on fingerprint (app/services/llm.py:232-238); that
    # catches mixing WITHIN one embed_batch_chunked call (Phase 1 alone, or
    # Phase 3 alone). It cannot catch Phase 1 vs Phase 3 landing on
    # different fingerprints -- that's a documented-tolerated rotation in
    # the production pipeline (CLAUDE.md) but forbidden for a bench run
    # (invariant 2), so it's asserted here instead of assumed.
    fingerprints = llm.fingerprints_seen
    if len(fingerprints) > 1:
        raise RuntimeError(
            f"run mixed embedder fingerprints, which invariant 2 forbids: "
            f"{sorted(fingerprints)}"
        )
    fingerprint = next(iter(fingerprints)) if fingerprints else llm.llm_fingerprint()

    return IngestResult(
        outcomes=outcomes,
        fingerprint=fingerprint,
        gate_config=gate_config,
        live_calls=live_calls,
    )
