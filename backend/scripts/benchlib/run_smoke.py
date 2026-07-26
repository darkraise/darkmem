"""CI/human entry point: proves the harness is affordable to re-run.

Resets the bench database, ingests the smoke corpus twice through the real
ProcessingPipeline, and asserts the second pass makes zero live LLM calls --
the disk cache in benchlib.caching_llm must absorb every embed/embed_batch/
chat_completion call the pipeline makes the second time around. See
FROZEN.md for the ingestion-granularity decision this script exercises and
the bench-DB LLM seeding this module performs.

A zero live-call count only proves the cache was used; it says nothing
about whether the pipeline's own writes actually succeeded underneath it.
Both passes are also checked with find_outcome_failures(), independent of
the live-call count, so a pass that silently failed to write its memories
(a broken embedder partition, a bad graph write, ...) fails the gate even
when nothing was billed for it. Outcomes that are clean but thin fail too:
find_work_shortfalls() holds each pass to the expected memory/entity/
relation counts the corpus file declares, so a valid-but-degraded cached
response cannot pass the gate by erroring nowhere.

Run from backend/: python scripts/benchlib/run_smoke.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
# Standalone execution (`python scripts/benchlib/run_smoke.py`) only puts
# this file's own directory on sys.path -- unlike pytest, which inserts
# SCRIPTS_DIR itself because backend/scripts/ has no __init__.py. Both
# `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import select  # noqa: E402

from benchlib import bench_db  # noqa: E402,F401  (ensures DATABASE_URL override first)
from benchlib import corpus, ledger  # noqa: E402
from benchlib.caching_llm import CachingLLMOrchestrator  # noqa: E402
from benchlib.ingest import GateConfig, IngestResult, run_ingest  # noqa: E402

from app.models.llm_config import LLMPurposeConfigRow  # noqa: E402
from app.services.config import get_llm_config  # noqa: E402

CORPUS_ID = "smoke"
CORPUS_PATH = HERE / "smoke" / "corpus.json"
CACHE_DIR = HERE / "smoke" / "cache"

# Live LLM stack pinned in GLOBAL.md (verified reachable by the controller,
# 2026-07-26). Embedding has no credential -- Ollama is unauthenticated on
# this network. Extraction/classification share one DeepSeek key, read from
# the environment so it never lands in source, a fixture, or this file.
OLLAMA_EMBEDDING_BASE_URL = "http://192.168.0.196:11434"
OLLAMA_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
OLLAMA_EMBEDDING_DIMENSIONS = 1024
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def require_deepseek_api_key(env: Mapping[str, str] | None = None) -> str:
    """Read DEEPSEEK_API_KEY from the environment or fail loud and readable.

    The bench DB is reset (DROP SCHEMA) on every run, so there is never a
    stored key to fall back to -- an unset key must not be allowed to reach
    the vendor as a bare 401.
    """
    env = os.environ if env is None else env
    key = env.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. The extraction and classification "
            "purposes run against DeepSeek for this smoke run; export a real "
            "key (never commit it) before running scripts/benchlib/run_smoke.py."
        )
    return key


def purpose_config_specs(deepseek_api_key: str) -> list[dict]:
    """The embedding/extraction/classification connection rows this run
    seeds, inline (no provider_id/profile_id) -- LLMPurposeConfigRow
    supports a purpose running standalone this way (CLAUDE.md's LLM
    configuration section), so a bench seed doesn't need the setup wizard's
    provider/profile bookkeeping to reach a working purpose config.
    """
    return [
        {
            "purpose": "embedding",
            "api_kind": "ollama",
            "provider": "ollama",
            "base_url": OLLAMA_EMBEDDING_BASE_URL,
            "model": OLLAMA_EMBEDDING_MODEL,
            "dimensions": OLLAMA_EMBEDDING_DIMENSIONS,
            "api_key": None,
            "params": {},
        },
        {
            "purpose": "extraction",
            "api_kind": "deepseek",
            "provider": "deepseek",
            "base_url": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_MODEL,
            "dimensions": None,
            "api_key": deepseek_api_key,
            "params": {},
        },
        {
            "purpose": "classification",
            "api_kind": "deepseek",
            "provider": "deepseek",
            "base_url": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_MODEL,
            "dimensions": None,
            "api_key": deepseek_api_key,
            "params": {},
        },
    ]


async def seed_llm_purpose_configs(session_factory, deepseek_api_key: str) -> None:
    """Write the pinned embedding/extraction/classification rows.

    Update-or-insert per purpose, not a blind insert: reset_bench_db()
    guarantees an empty table on a genuinely fresh schema, but this also
    has to be safe to call against a schema this same run already seeded
    (called once per pass, and the two passes share one reset cycle each).
    """
    async with session_factory() as session:
        for spec in purpose_config_specs(deepseek_api_key):
            existing = (await session.execute(
                select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == spec["purpose"])
            )).scalar_one_or_none()
            if existing is not None:
                for field, value in spec.items():
                    setattr(existing, field, value)
            else:
                session.add(LLMPurposeConfigRow(**spec))
        await session.commit()


def find_outcome_failures(outcomes: list[dict], expected_count: int) -> list[str]:
    """Return one human-readable failure description per problem found in
    a pass's outcomes; empty means the pass genuinely did its work.

    A live-call count of 0 only proves the disk cache was used for every
    embed/chat call attempted -- it says nothing about whether the write
    that call was feeding actually landed. The stale embedder_registry bug
    this task's bench_db.py fix addresses left live_calls == 0 (correctly,
    from a warm cache) while every memory's vector/graph write silently
    failed underneath it; this check is independent of live_calls by
    design so it catches that shape of failure regardless of what the
    call counter says.
    """
    failures: list[str] = []
    if len(outcomes) != expected_count:
        failures.append(f"expected {expected_count} outcomes, got {len(outcomes)}")
    for outcome in outcomes:
        memory_id = outcome.get("memory_id", "<unknown>")
        for step in ("embed", "extract", "vector", "graph"):
            if outcome.get(step) == "error":
                failures.append(f"memory {memory_id}: {step} == 'error'")
        if outcome.get("error"):
            failures.append(f"memory {memory_id}: error={outcome['error']!r}")
    return failures


def count_work(outcomes: list[dict]) -> dict:
    return {
        "memories": len(outcomes),
        "entities": sum(o.get("entities_count", 0) for o in outcomes),
        "relations": sum(o.get("relations_count", 0) for o in outcomes),
    }


def find_work_shortfalls(outcomes: list[dict], expected: dict | None) -> list[str]:
    """Return one failure per count that fell below what the corpus declared.

    All-ok outcomes only prove nothing errored. A cached chat entry replaced
    by *valid* JSON carrying empty entities/relationships, a silently
    regressed extraction, or a model swap replaying another model's answers
    all produce a clean pass that did less work than the corpus says it
    should. This is the floor that catches them; the counts live in the
    corpus file (benchlib.corpus.load_expectations), because the corpus is
    what declares what ingesting it produces.

    A corpus that declares nothing (every gold file) has no floor to fail.
    """
    if not expected:
        return []
    actual = count_work(outcomes)
    return [
        f"expected at least {expected[key]} {key}, got {actual[key]}"
        for key in sorted(expected)
        if actual[key] < expected[key]
    ]


def summarize_pass(outcomes: list[dict]) -> str:
    work = count_work(outcomes)
    return (
        f"{work['memories']} memories ingested, {work['entities']} entities written, "
        f"{work['relations']} relations written"
    )


def _print_pass_failures(label: str, failures: list[str]) -> None:
    print(
        f"AFFORDABILITY GATE FAILED: {label} did not do its work cleanly "
        "(this is independent of the live-call count):",
        file=sys.stderr,
    )
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)


async def _reset_and_seed(deepseek_api_key: str) -> None:
    await bench_db.reset_bench_db()
    await seed_llm_purpose_configs(bench_db.session_factory, deepseek_api_key)


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(BACKEND_DIR), capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def build_run_record(result: IngestResult, pass1_live_calls: int, sha: str) -> dict:
    return {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_id": CORPUS_ID,
        "fingerprint": result.fingerprint,
        "git_sha": sha,
        "metrics": {
            "pass1_live_calls": pass1_live_calls,
            "pass2_live_calls": result.live_calls,
            "gate_config": result.gate_config,
        },
    }


async def main() -> int:
    deepseek_api_key = require_deepseek_api_key()

    # Load before the reset: a corpus that certifies nothing must fail
    # before the run spends a DB reset and a live model call on it.
    entries = corpus.load_corpus(CORPUS_PATH)
    expected_work = corpus.load_expectations(CORPUS_PATH)
    expected_count = len(entries)
    if expected_count == 0:
        print(
            f"AFFORDABILITY GATE FAILED: {CORPUS_PATH} yielded zero entries, so "
            "every count below is trivially satisfied and the gate would "
            "certify nothing.",
            file=sys.stderr,
        )
        return 1

    print("[1/5] resetting bench DB and seeding LLM purpose configs...")
    await _reset_and_seed(deepseek_api_key)

    async with bench_db.session_factory() as session:
        llm_config = await get_llm_config(session)

    gate = GateConfig()
    # One orchestrator, reused sequentially across both passes: IngestResult
    # .live_calls is a delta since run_ingest's own call, computed off this
    # instance's running counter, so reuse is what lets pass 2 report 0
    # against pass 1's genuine cost. Never share this instance across
    # concurrent run_ingest calls -- the before/after window would race.
    orchestrator = CachingLLMOrchestrator(llm_config, cache_dir=str(CACHE_DIR))

    print(f"[2/5] pass 1 (live): ingesting {expected_count} smoke entries...")
    first = await run_ingest(orchestrator, entries, gate)
    print(f"pass 1 live LLM calls: {first.live_calls}")
    print(f"pass 1 work: {summarize_pass(first.outcomes)}")
    # first.live_calls is reported, deliberately never asserted -- see
    # FROZEN.md ("why pass 1's live-call count isn't asserted"): on a
    # rerun against an already-warm cache pass 1 legitimately makes zero
    # live calls too, and the outcomes check below is what actually
    # detects a broken pipeline, independent of what got billed.
    pass1_failures = (
        find_outcome_failures(first.outcomes, expected_count)
        + find_work_shortfalls(first.outcomes, expected_work)
    )
    if pass1_failures:
        _print_pass_failures("pass 1", pass1_failures)
        return 1

    print("[3/5] resetting bench DB for pass 2 (clean database, warm cache)...")
    await _reset_and_seed(deepseek_api_key)

    print(f"[4/5] pass 2 (should be fully cached): ingesting {expected_count} smoke entries...")
    second = await run_ingest(orchestrator, entries, gate)
    print(f"live LLM calls: {second.live_calls}")
    print(f"pass 2 work: {summarize_pass(second.outcomes)}")
    pass2_failures = (
        find_outcome_failures(second.outcomes, expected_count)
        + find_work_shortfalls(second.outcomes, expected_work)
    )
    if pass2_failures:
        _print_pass_failures("pass 2", pass2_failures)
        return 1

    record = build_run_record(second, first.live_calls, git_sha())
    ledger.record(record)
    print(f"[5/5] ledger: recorded run {record['run_id']} (fingerprint={record['fingerprint']})")

    if second.live_calls != 0:
        print(
            f"AFFORDABILITY GATE FAILED: pass 2 made {second.live_calls} live "
            "LLM call(s) against a warm cache. The cache is not wrapping "
            "every path the pipeline uses to reach the model.",
            file=sys.stderr,
        )
        return 1
    return 0


def _run() -> int:
    """Thin wrapper so a pre-flight RuntimeError (missing key, alembic
    failure, ...) prints as one readable line instead of a Python
    traceback. main() itself still raises -- unit tests call main()
    directly and assert on the raise."""
    try:
        return asyncio.run(main())
    except RuntimeError as exc:
        print(f"run_smoke.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_run())
