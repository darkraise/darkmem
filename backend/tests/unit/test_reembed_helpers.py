from app.services.reembed import ReembedLockSet


class TestReembedLockSet:
    def test_acquire_release(self):
        locks = ReembedLockSet()
        assert locks.try_acquire("memories") is True
        assert locks.try_acquire("memories") is False
        locks.release("memories")
        assert locks.try_acquire("memories") is True

    def test_release_nonexistent_is_safe(self):
        locks = ReembedLockSet()
        locks.release("memories")  # should not raise

    def test_is_locked(self):
        locks = ReembedLockSet()
        assert locks.is_locked("entities") is False
        locks.try_acquire("entities")
        assert locks.is_locked("entities") is True

    def test_multiple_categories_independent(self):
        locks = ReembedLockSet()
        assert locks.try_acquire("memories") is True
        assert locks.try_acquire("entities") is True
        assert locks.try_acquire("code_chunks") is True
        locks.release("entities")
        assert locks.is_locked("memories") is True
        assert locks.is_locked("entities") is False
        assert locks.is_locked("code_chunks") is True
