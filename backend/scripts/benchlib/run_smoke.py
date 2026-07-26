"""CI/human entry point: proves the harness is affordable to re-run.

Resets the bench database, ingests the smoke corpus twice through the real
ProcessingPipeline, and asserts the second pass makes zero live LLM calls --
the disk cache in benchlib.caching_llm must absorb every embed/embed_batch/
chat_completion call the pipeline makes the second time around. See
FROZEN.md for the ingestion-granularity decision this script exercises and
the bench-DB LLM seeding this module performs.

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

    print("[1/5] resetting bench DB and seeding LLM purpose configs...")
    await bench_db.reset_bench_db()
    await seed_llm_purpose_configs(bench_db.session_factory, deepseek_api_key)

    async with bench_db.session_factory() as session:
        llm_config = await get_llm_config(session)

    entries = corpus.load_corpus(CORPUS_PATH)
    gate = GateConfig()
    # One orchestrator, reused sequentially across both passes: IngestResult
    # .live_calls is a delta since run_ingest's own call, computed off this
    # instance's running counter, so reuse is what lets pass 2 report 0
    # against pass 1's genuine cost. Never share this instance across
    # concurrent run_ingest calls -- the before/after window would race.
    orchestrator = CachingLLMOrchestrator(llm_config, cache_dir=str(CACHE_DIR))

    print(f"[2/5] pass 1 (live): ingesting {len(entries)} smoke entries...")
    first = await run_ingest(orchestrator, entries, gate)
    print(f"pass 1 live LLM calls: {first.live_calls}")

    print("[3/5] resetting bench DB for pass 2 (clean database, warm cache)...")
    await bench_db.reset_bench_db()
    await seed_llm_purpose_configs(bench_db.session_factory, deepseek_api_key)

    print(f"[4/5] pass 2 (should be fully cached): ingesting {len(entries)} smoke entries...")
    second = await run_ingest(orchestrator, entries, gate)
    print(f"live LLM calls: {second.live_calls}")

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
