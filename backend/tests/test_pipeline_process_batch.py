"""Placeholder for an end-to-end ProcessingPipeline.process_batch smoke test.

Deferred deliberately. The achievable, high-value slices of the pipeline are
already covered elsewhere:

* Phase-5 supersession: ``test_schema_v2_metadata.py`` and
  ``test_replaces_family.py`` (the ``detect_supersessions`` entry point).
* Confidence weighting / RRF math: ``test_schema_v2_metadata.py``
  (``rank_fusion_factor``) and ``test_hybrid_search.py`` (``_rrf_fuse``).
* Failure-state derivation helpers: ``tests/unit/test_pipeline_failures_helpers.py``.
* Aggregator: ``test_pipeline_aggregator.py``.

A full ``process_batch`` integration test is intentionally not written in this
pass because it does not fit the existing rolled-back ``session`` fixture and
would be brittle:

1. ``process_batch`` builds its OWN sessions from ``session_factory`` and
   commits them (Phases 1, 3, 5, and the failure-state write). Those commits
   land outside the conftest ``session`` fixture's nested-savepoint rollback,
   so every run would leave committed memory rows, embedding-partition rows,
   entity/relation rows, and ``pipeline_failures`` rows in ``darkmem_test``
   unless the test tears them all down by hand.
2. The embedder registry keeps PROCESS-GLOBAL state
   (``embedder_registry._known``) and creates per-fingerprint child tables via
   its own committed session. A test that registers a fingerprint pollutes
   that singleton for every later test in the session unless it calls
   ``embedder_registry.forget(fp)`` in teardown.
3. The real work requires mocking ``LLMOrchestrator.embed_batch_chunked`` and
   the extraction LLM call, plus a live DB for the partition writes.

What a complete test needs (for whoever picks this up):

* A ``session_factory`` bound to ``tests.conftest.test_engine`` and passed to
  ``ProcessingPipeline(llm, session_factory)``.
* A fake/mock ``llm`` exposing ``embed_batch_chunked(texts, chunk, conc)`` ->
  ``([vec, ...], "fake|<dims>")`` and whatever the ``ExtractionService`` calls
  (mock ``pipeline.extraction.extract`` to return a small entities/relationships
  dict directly to avoid wiring the LLM JSON path).
* A pre-committed ``memories`` row whose id is passed in the entry dict
  (``{"memory_id": id, "content": ...}``); ``process_batch`` updates an
  existing row, it does not create one.
* Assertions: the returned status dict reports ``embed=="ok"`` and
  ``vector=="ok"``/``graph=="ok"``; a row exists in
  ``memory_embeddings__<slug>`` for that memory_id; the websocket/failure path
  recorded ``completed``.
* Teardown: delete the memory row (cascades the embedding), delete any seeded
  entities/relations and ``pipeline_failures`` rows, drop the child table, and
  ``embedder_registry.forget(fp)``.
"""
import pytest


@pytest.mark.skip(
    reason="Deferred: process_batch commits via its own session_factory "
    "outside the rolled-back test fixture and mutates the process-global "
    "embedder_registry; a faithful smoke test needs explicit DB teardown + "
    "embedder_registry.forget and is too brittle for this pass. See module "
    "docstring for the full recipe."
)
@pytest.mark.asyncio
async def test_process_batch_writes_memory_and_reports_completion():
    raise NotImplementedError
