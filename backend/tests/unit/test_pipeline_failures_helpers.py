from uuid import uuid4

from app.services.pipeline_failures import (
    RetryLockSet,
    derive_memory_failed_step,
    derive_code_failed_step,
)


class TestDeriveMemoryFailedStep:
    def test_returns_none_when_all_ok(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok"}
        assert derive_memory_failed_step(status) is None

    def test_returns_none_when_graph_skipped(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "skipped"}
        assert derive_memory_failed_step(status) is None

    def test_content_embedding_failure(self):
        status = {"embed": "error", "extract": "pending", "vector": "pending", "graph": "pending"}
        assert derive_memory_failed_step(status) == "content_embedding"

    def test_extraction_failure(self):
        status = {"embed": "ok", "extract": "error", "vector": "ok", "graph": "ok"}
        assert derive_memory_failed_step(status) == "extraction"

    def test_vector_write_failure(self):
        status = {"embed": "ok", "extract": "ok", "vector": "error", "graph": "ok"}
        assert derive_memory_failed_step(status) == "vector_write"

    def test_graph_write_failure(self):
        status = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "error"}
        assert derive_memory_failed_step(status) == "graph_write"

    def test_first_failed_step_wins(self):
        status = {"embed": "error", "extract": "error", "vector": "error", "graph": "error"}
        assert derive_memory_failed_step(status) == "content_embedding"


class TestDeriveCodeFailedStep:
    def test_empty_returns_other(self):
        assert derive_code_failed_step([]) == "other"

    def test_parse_prefix(self):
        assert derive_code_failed_step(["parse:src/foo.py:SyntaxError"]) == "parse"

    def test_embed_prefix(self):
        assert derive_code_failed_step(["embed:src/foo.py:RuntimeError"]) == "embeddings"

    def test_import_prefix(self):
        assert derive_code_failed_step(["import:src/foo.py:ModuleNotFound"]) == "import_resolution"

    def test_unknown_returns_other(self):
        assert derive_code_failed_step(["weird:something:Error"]) == "other"

    def test_first_matching_wins(self):
        errors = ["weird:x", "parse:src/foo.py:X"]
        assert derive_code_failed_step(errors) == "parse"


class TestRetryLockSet:
    def test_acquire_release(self):
        locks = RetryLockSet()
        uid = uuid4()
        assert locks.try_acquire(uid) is True
        assert locks.try_acquire(uid) is False
        locks.release(uid)
        assert locks.try_acquire(uid) is True

    def test_release_nonexistent_is_safe(self):
        locks = RetryLockSet()
        locks.release(uuid4())  # should not raise

    def test_is_locked(self):
        locks = RetryLockSet()
        uid = uuid4()
        assert locks.is_locked(uid) is False
        locks.try_acquire(uid)
        assert locks.is_locked(uid) is True


# ── _derive_outcome: the journal and the broadcast must agree ────────


def test_derive_outcome_is_shared_by_the_journal_and_the_broadcast():
    """T1.07 gave the durable `extracted` event and the `pipeline.*` broadcast
    one derivation. They were briefly computed separately, and the second copy
    read a variable bound only on the write path — so a memory whose Phase 1
    failed took an UnboundLocalError instead of an outcome."""
    from app.services.pipeline import _derive_outcome

    ok = {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok"}
    assert _derive_outcome(ok) == "completed"

    partial = {"embed": "ok", "extract": "error", "vector": "ok", "graph": "error"}
    assert _derive_outcome(partial) == "partial"

    failed = {"embed": "error", "extract": "error", "vector": "error", "graph": "error"}
    assert _derive_outcome(failed) == "failed"


def test_derive_outcome_ignores_skipped_and_pending_steps():
    from app.services.pipeline import _derive_outcome

    # A failed Phase 1 marks embed=error and skips the writes; the skips must
    # not be read as successes.
    phase1_failed = {
        "embed": "error", "extract": "error", "vector": "skipped", "graph": "skipped",
    }
    assert _derive_outcome(phase1_failed) == "failed"

    still_running = {
        "embed": "ok", "extract": "pending", "vector": "pending", "graph": "pending",
    }
    assert _derive_outcome(still_running) == "completed"

    # The shape process_batch stamps when a memory's whole write escaped as an
    # exception: `unknown` is not a skip, so it must not be filtered out of the
    # active set and quietly leave the outcome reading `completed`.
    escaped = {
        "embed": "unknown", "extract": "unknown", "vector": "error", "graph": "error",
    }
    assert _derive_outcome(escaped) == "failed"
