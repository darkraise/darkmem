"""The harvest's two machine-checkable properties (T2.54 Step 1).

Database-name discipline is pure and always runs. The reproducibility half
is the anti-forgery detector Ruling 2 leans on: the harvest runs TWICE
in-process and the two ``facts`` sections must be byte-identical -- warm
cache -> byte-identical extraction -> identical canonicalisation ->
identical triple_key set.

**T2.79.** This test used to read its cache from the shared, gitignored
``retrieval/cache/`` and skip when that directory was empty -- which is
every lane worktree and every fresh clone, because ``git worktree add``
never populates a gitignored path. The skip was silent (exit 0, "1
skipped" easy to misread as informational) and it was skipping exactly the
guarantee this file exists to prove: T2.54's byte-identical-manifest
anchor, which the entailment gold's reviewer relied on as evidence the
``facts`` section is reproducible, gating G-D and transitively G-C. A
green run in that state was not evidence the guarantee held.

Fix chosen: **stop the input being gitignored**, scoped to exactly what
this test touches rather than the whole shared cache. ``harvest_l2_cache_fixture/``
next to this file is a **committed** (not gitignored) copy of the ~300
cache entries ``run_harvest`` actually reads for this corpus -- collected
by wrapping ``CachingLLMOrchestrator._read`` to copy every file it served
during one real, warm-cache run, then verified to reproduce
``live_calls == 0`` from the fixture alone with nothing else on disk. It
is deliberately not the whole 6.9 MB shared ``retrieval/cache/`` (which
also serves ``run_retrieval_eval.py`` and ``arm_ablation.py`` for the
``--full`` gate and stays gitignored and dev-warmed): committing only the
subset this test needs keeps the artifact bounded (~3.7 MB, plain JSON)
and keeps the shared dev cache's "gitignored, regenerate freely" contract
intact for everyone else. Consequence of this choice, stated rather than
hidden: the fixture must be re-collected the same way (instrument
``_read``, run the harvest once against the warm shared cache, copy the
touched keys here) if the retrieval corpus, the extraction/classification
prompts, or the pinned model changes, because the cache key folds in
content and resolved purpose config. A stale fixture does not skip and
does not silently pass, but ``run_harvest`` itself does not raise: the
pipeline swallows a stale chat key's 401 per memory (``extraction_clean``
logs ``Extraction failed: ... 401`` and returns an empty graph for that
memory) and completes with ``n_facts=0``. The loud failure is this test's
own ``live_calls == 0`` assertion below (F2, fix round 2026-08-04a --
corrected; the prior wording here misattributed the failure to
``run_harvest`` raising). A stale *embed* key is different again and is
F1/F3 below: the embedding purpose targets a live, keyless LAN endpoint,
so a miss there succeeds as a real network call rather than erroring, and
that live result must never be allowed to land back inside the committed
fixture (F1's fix: ``cache_dir`` is a copy, made fresh per test run).

**Why not the other two shapes.** A hard failure with no fixture (make the
missing prerequisite loud, full stop) would turn every fresh clone red
until someone manually copies a gitignored directory in -- trading a
silent false-green for a mandatory manual step nobody would remember
correctly, which just relocates the defect. Counting the skip somewhere a
reader sees it (a distinct exit code, a summary banner) was rejected per
R3: it still does not run the test, and the acceptance bar here is that
the guarantee is actually checked in the environment every lane and every
fresh clone uses -- not that its absence is merely better advertised.

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
import shutil
from pathlib import Path

import pytest

from benchlib import bench_db, harvest_l2_facts
from benchlib.harvest_l2_facts import (
    MANIFEST_PATH,
    assert_bench_db_allowed,
    bench_db_name,
    facts_json,
    run_harvest,
)

BACKEND_DIR = Path(__file__).resolve().parents[3]
FIXTURE_CACHE_DIR = Path(__file__).resolve().parent / "harvest_l2_cache_fixture"


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


def test_fixture_cache_is_committed_and_present():
    """The committed fixture is the whole fix: if this fails, the test below
    is not proving anything and must not be read as having run. Unlike the
    old gitignored-cache check, this is not a skip condition -- an absent or
    empty fixture is a hard failure, because after T2.79 there is no lawful
    reason for it to be missing in any checkout that has this file at all."""
    assert FIXTURE_CACHE_DIR.is_dir(), FIXTURE_CACHE_DIR
    assert any(FIXTURE_CACHE_DIR.iterdir()), FIXTURE_CACHE_DIR


@pytest.mark.asyncio
async def test_harvest_is_byte_reproducible_and_fully_cached(tmp_path):
    # The key is a sentinel on purpose: a warm cache makes zero live calls.
    # A cache miss does NOT fail loudly at the vendor -- the pipeline
    # swallows the per-memory 401 (extraction_clean logs it and the memory
    # comes back with an empty graph), so `run_harvest` itself completes;
    # the loud failure is this test's own `live_calls == 0` assertion below
    # (F2, fix round 2026-08-04a -- the previous wording here was wrong).
    # The bench database is the test's own per-checkout one -- never the
    # environment's.
    #
    # F1 (same round): `cache_dir` is a throwaway copy of the committed
    # fixture, never the fixture itself. `CachingLLMOrchestrator._write`
    # targets whatever `cache_dir` it is given, and an embed-side cache miss
    # is a real, successful call against the LAN Ollama embedder (api_key is
    # ignored there, so the offline sentinel above does not stop it) --
    # which used to land inside the committed
    # `harvest_l2_cache_fixture/` directory. That let an embed-only
    # staleness go red once and then self-heal to green from
    # machine-locally regenerated state a fresh clone never has, reopening
    # the exact worktree-vs-clone divergence T2.79 was minted to kill.
    # Copying first makes the fixture read-only in this test path: whatever
    # `_write` does lands in `tmp_path` and is discarded when the test ends,
    # so a stale fixture stays red on every subsequent run, in every
    # checkout, forever -- it can never repair its own evidence.
    cache_dir = tmp_path / "harvest_l2_cache_fixture"
    shutil.copytree(FIXTURE_CACHE_DIR, cache_dir)

    url = dedicated_bench_url()
    first = await run_harvest(
        api_key="offline-warm-cache-only", bench_url=url, cache_dir=cache_dir
    )
    second = await run_harvest(
        api_key="offline-warm-cache-only", bench_url=url, cache_dir=cache_dir
    )

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
