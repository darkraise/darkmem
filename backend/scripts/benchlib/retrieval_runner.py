"""Drives the real retriever over the retrieval-gold queries.

DB-backed and retrieval-aware, deliberately kept apart from
``retrieval_scorer.py`` (T0.07 brief §7): that module is pure arithmetic and
must not know how its ranked ids were produced. This module's whole job is
to produce them -- by calling ``ProcessingPipeline.semantic_search``, the
same composition entry point ``process_batch``'s own callers use, never a
reimplementation of ranking (the rule T0.03 was already held to). Compose
the two: ``run_retrieval``'s return value is exactly what
``retrieval_scorer.score_retrieval`` expects for its ``ranked_ids_by_pair``
argument.

Requires an already-ingested bench DB (``benchlib.ingest.run_ingest`` /
``benchlib.retrieval_gold.seed_memory_rows``) -- this module only queries.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from benchlib import bench_db  # noqa: F401  (ensures DATABASE_URL override first)

from app.services.llm import LLMOrchestrator
from app.services.pipeline import ProcessingPipeline


async def run_retrieval(
    llm: LLMOrchestrator,
    session_factory,
    gold_pairs: Iterable[Mapping],
    limit: int = 10,
    filters=None,
) -> dict[str, list]:
    """Run every live gold pair's query through the shipping retriever.

    Returns ``{pair_id: ranked_ids}``, skipping retired pairs the same way
    ``retrieval_scorer.score_retrieval`` does -- a retired pair was never
    meant to be scored, so it is never worth the (free but non-zero) query
    call either.

    Ranked ids come back exactly as ``semantic_search`` returns them: a
    ``str`` under the hybrid path, a ``UUID`` under the vector-repo-only
    fallback (``hybrid_search_enabled=False``) -- CLAUDE.md's memory_id type
    drift. This module passes them through untouched; normalising them is
    ``retrieval_scorer``'s job, not this one's.

    One ``ProcessingPipeline`` instance is reused across every query in the
    call -- cheap, since ``semantic_search`` opens its own session per call
    and this class holds no per-query state.

    ``filters`` defaults to ``None``, which is the unscoped read every
    baseline row in the ledger was measured under; it is **not** widened to a
    default scope, because changing what the default path retrieves would
    silently invalidate every prior recorded number (ruling 3). The
    arm-ablation path passes a scope only for arms whose signal is itself
    project-scoped -- today the PPR list arm, whose cached snapshot has no
    defined meaning across two projects -- and applies the same scope to both
    of its legs, so the delta it reports stays internally consistent.
    """
    pipeline = ProcessingPipeline(llm, session_factory)
    results: dict[str, list] = {}
    for pair in gold_pairs:
        if pair.get("retired"):
            continue
        hits = await pipeline.semantic_search(
            pair["query"], limit=limit, filters=filters,
        )
        results[pair["id"]] = [hit["memory_id"] for hit in hits]
    return results
