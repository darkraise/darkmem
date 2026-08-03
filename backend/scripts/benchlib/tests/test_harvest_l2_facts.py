"""The harvest's two machine-checkable properties (T2.54 Step 1).

Database-name discipline is pure and always runs. The reproducibility half
is the anti-forgery detector Ruling 2 leans on: the harvest runs TWICE
in-process and the two ``facts`` sections must be byte-identical -- warm
cache -> byte-identical extraction -> identical canonicalisation ->
identical triple_key set. It needs the warm retrieval cache (gitignored,
machine-local) and the bench Postgres; a checkout without the cache skips
loudly rather than paying live model calls from a test floor.

The reproducibility test **selects its own bench database** -- a numbered
name derived from this checkout's path -- instead of reading
``BENCH_DATABASE_URL``. An in-process double run exists only for the byte
comparison, so it has no reason to care what a human exported; reading the
environment made its result depend on the invocation (green in a lane with
an assigned database, red under ``./scripts/gate.sh`` where the default is
the guarded unnumbered ``darkmem_bench``, and -- worse -- a silent reset of
a sibling lane's database wherever one was exported). Only the server
coordinates come from the environment default; the database is the test's
own, per checkout, so concurrent worktree floors cannot collide.
"""
import hashlib
import json
from pathlib import Path

import pytest

from benchlib import bench_db, harvest_l2_facts
from benchlib.harvest_l2_facts import (
    CACHE_DIR,
    MANIFEST_PATH,
    assert_bench_db_allowed,
    bench_db_name,
    facts_json,
    run_harvest,
)

BACKEND_DIR = Path(__file__).resolve().parents[3]


def dedicated_bench_url() -> str:
    checkout = hashlib.sha256(str(BACKEND_DIR).encode("utf-8")).hexdigest()[:10]
    server = bench_db.BENCH_DATABASE_URL.rsplit("/", 1)[0]
    return f"{server}/darkmem_bench_t{checkout}"


# ---------------------------------------------------------------------------
# Database-name guard: every unlawful target refused by name, before any
# connection exists.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["darkmem_bench_1", "darkmem_bench_c3"])
def test_numbered_bench_databases_are_allowed(name):
    assert_bench_db_allowed(name)


def test_unnumbered_bench_needs_the_explicit_flag():
    with pytest.raises(RuntimeError, match="allow-unnumbered"):
        assert_bench_db_allowed("darkmem_bench")
    assert_bench_db_allowed("darkmem_bench", allow_unnumbered=True)


@pytest.mark.parametrize(
    "name", ["darkmem", "darkmem_test", "darkmem_test_1", "postgres", ""]
)
def test_real_and_test_databases_are_never_lawful(name):
    with pytest.raises(RuntimeError, match="refusing"):
        assert_bench_db_allowed(name, allow_unnumbered=True)


def test_bench_db_name_reads_the_url_tail():
    assert bench_db_name(
        "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_bench_1"
    ) == "darkmem_bench_1"


# ---------------------------------------------------------------------------
# The committed manifest's cheap structural pins (no database needed).
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def committed_manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def test_committed_manifest_facts_are_sorted_by_triple_key(committed_manifest):
    keys = [f["triple_key"] for f in committed_manifest["facts"]]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_committed_manifest_header_records_the_run_identity(committed_manifest):
    header = committed_manifest["header"]
    for field in (
        "corpus_sha256", "git_sha", "bench_db", "gate_config",
        "embedder_fingerprint", "ingest_live_calls", "lift", "assignment_seed",
    ):
        assert field in header, field
    assert header["assignment_seed"] == harvest_l2_facts.ASSIGNMENT_SEED


def test_every_committed_fact_carries_its_traceability_fields(committed_manifest):
    for fact in committed_manifest["facts"]:
        for field in (
            "triple_key", "subject_name", "rel_type", "object_name",
            "project", "fact", "verification_status", "source_memory_ids",
        ):
            assert field in fact, (fact.get("triple_key"), field)
        assert fact["source_memory_ids"], fact["triple_key"]
        assert fact["verification_status"] == "candidate"


# ---------------------------------------------------------------------------
# Reproducibility: the harvest, twice in-process, byte-identical facts.
# ---------------------------------------------------------------------------

def test_the_dedicated_database_name_passes_the_guard():
    url = dedicated_bench_url()
    name = url.rsplit("/", 1)[-1]
    assert name.startswith("darkmem_bench_t")
    assert_bench_db_allowed(name)


@pytest.mark.asyncio
async def test_harvest_is_byte_reproducible_and_fully_cached():
    if not CACHE_DIR.is_dir() or not any(CACHE_DIR.iterdir()):
        pytest.skip(
            "warm retrieval cache absent (gitignored); copy it in from the "
            "main checkout before running the harvest reproducibility test"
        )

    # The key is a sentinel on purpose: a warm cache makes zero live calls,
    # and a cache miss must fail loudly at the vendor rather than be paid
    # for silently from a test floor. The bench database is the test's own
    # per-checkout one -- never the environment's.
    url = dedicated_bench_url()
    first = await run_harvest(api_key="offline-warm-cache-only", bench_url=url)
    second = await run_harvest(api_key="offline-warm-cache-only", bench_url=url)

    assert first.live_calls == 0, (
        "harvest made live LLM calls against a cache that was expected to be "
        "warm -- the cache key changed; find out why instead of paying"
    )
    assert second.live_calls == 0

    assert facts_json(first.manifest["facts"]) == facts_json(second.manifest["facts"])

    headers = [dict(r.manifest["header"]) for r in (first, second)]
    for header in headers:
        header.pop("generated_at")
    assert headers[0] == headers[1]

    assert first.n_facts > 0
