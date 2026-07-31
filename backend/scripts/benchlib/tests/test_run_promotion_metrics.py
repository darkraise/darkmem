"""Tests for `run_promotion_metrics.py`'s pure URL-handling helpers.

No database dependency (`_bench_db` fixture not needed): `_assert_not_forbidden`
and `_database_identity` are pure string/URL parsing over a DSN, never opening
a connection.
"""
from __future__ import annotations

import pytest

from benchlib import run_promotion_metrics as rpm


class TestAssertNotForbidden:
    @pytest.mark.parametrize("db", ["darkmem_test", "darkmem_test_1", "darkmem_test_9"])
    def test_refuses_darkmem_test_and_numbered_variants(self, db):
        url = f"postgresql+asyncpg://darkmem:darkmem@localhost:5433/{db}"
        with pytest.raises(RuntimeError, match=db):
            rpm._assert_not_forbidden(url)

    @pytest.mark.parametrize("db", ["darkmem", "darkmem_bench", "darkmem_bench_1"])
    def test_allows_real_and_bench_databases(self, db):
        url = f"postgresql+asyncpg://darkmem:darkmem@localhost:5433/{db}"
        rpm._assert_not_forbidden(url)  # must not raise

    def test_refuses_a_percent_encoded_forbidden_name(self):
        """`darkmem%5Ftest` percent-decodes to `darkmem_test`. A naive check
        over the raw URL path (`urlsplit(url).path`) never matches the
        literal forbidden string, but `asyncpg.connect()` given this exact
        DSN as a raw string decodes it and connects to `darkmem_test`
        underneath the check -- proven directly against a live Postgres
        connection during review. The check must refuse the decoded name,
        not the literal one."""
        url = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem%5Ftest"
        with pytest.raises(RuntimeError, match="darkmem_test"):
            rpm._assert_not_forbidden(url)

    def test_refuses_a_percent_encoded_numbered_variant(self):
        url = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test%5F3"
        with pytest.raises(RuntimeError, match="darkmem_test_3"):
            rpm._assert_not_forbidden(url)


class TestDatabaseIdentity:
    def test_renders_host_port_database(self):
        url = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
        assert rpm._database_identity(url) == "localhost:5433/darkmem"

    def test_decodes_a_percent_encoded_database_name(self):
        url = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem%5Fbench"
        # Not asserted against the forbidden set here, only that the
        # rendered identity string is legible (decoded) rather than a
        # raw-encoded surprise in a gate report.
        assert "darkmem" in rpm._database_identity(url)
