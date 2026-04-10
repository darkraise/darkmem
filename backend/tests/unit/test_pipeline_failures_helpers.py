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

    def test_returns_none_when_extract_partial(self):
        # Partial extractions are not counted as failed
        status = {"embed": "ok", "extract": "partial", "vector": "ok", "graph": "ok"}
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
