"""Harvest Layer-2 facts into the entailment gold's anchor manifest (T2.54).

One recorded run: reset the assigned bench database, seed the pinned LLM
purpose rows, ingest the fixed-id retrieval corpus through the real
ProcessingPipeline against the warm disk cache, run the shipping
``fact_lift.run_lift`` to exhaustion, and write
``entailment/l2_harvest.json`` -- the committed manifest every ``l2-fact``
gold pair anchors to (doc 17 §11's 2026-07-31 "what 'real' means" clause).
A premise is real because THIS run minted it through the production code
path; the manifest row is the machine-checkable evidence, so the loader
validates pairs against the manifest, never against the pair's own claims.

Reproducibility is the manifest's anti-forgery property: warm cache ->
byte-identical extraction -> identical canonicalisation -> identical
``triple_key`` set, so re-running this script and diffing the sorted,
timestamp-free ``facts`` section byte-for-byte detects a hand-written row
in one command. ``tests/test_harvest_l2_facts.py`` runs the harvest twice
in-process and asserts exactly that, so the detector is exercised on every
floor run of this suite rather than merely promised.

Database discipline: the harvest writes only an assigned numbered bench
database (``darkmem_bench_<n>``); the bare ``darkmem_bench`` needs an
explicit flag, and any other database name -- ``darkmem``, any
``darkmem_test*`` -- is refused outright, before any connection is made.

Run from backend/ with the key inline (never exported shell-wide):
  DEEPSEEK_API_KEY=... BENCH_DATABASE_URL=... \
      python scripts/benchlib/harvest_l2_facts.py
Expected ``live_calls == 0`` against the warm retrieval cache; a run that
suddenly wants live calls at scale means the cache key changed -- find out
why instead of paying through it.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
# Standalone execution (`python scripts/benchlib/harvest_l2_facts.py`) only
# puts this file's own directory on sys.path -- unlike pytest, which inserts
# SCRIPTS_DIR itself because backend/scripts/ has no __init__.py. Both
# `benchlib` (under SCRIPTS_DIR) and `app` (under BACKEND_DIR) need to
# resolve, so both go on sys.path explicitly before either is imported.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import text  # noqa: E402

from benchlib import bench_db  # noqa: E402  (ensures DATABASE_URL override first)
from benchlib import retrieval_gold, run_smoke  # noqa: E402
from benchlib.caching_llm import CachingLLMOrchestrator  # noqa: E402
from benchlib.ingest import GateConfig, run_ingest  # noqa: E402

from app.services import fact_lift  # noqa: E402
from app.services.config import get_llm_config  # noqa: E402
from app.services.fact_provenance import MEMORY_SOURCE_KIND  # noqa: E402

MANIFEST_PATH = HERE / "entailment" / "l2_harvest.json"
CACHE_DIR = retrieval_gold.RETRIEVAL_DIR / "cache"

# Rule A's assignment RNG seed: a fixed literal, chosen here and committed
# with the manifest, BEFORE any pair exists. The Step 4 premise assignment
# (LABELLING.md's procedure) is a deterministic function of this seed and the
# sorted facts below, so the assignment order is re-derivable by anyone.
ASSIGNMENT_SEED = 20260731

# The authoring target's feasibility bound: >= 130 l2-fact pairs at the
# <= 4 pairs-per-premise cap. Both literals come from the T2.54 plan and
# doc 17 §11's 50% floor arithmetic; they are reported, never auto-widened.
PAIRS_PER_PREMISE_CAP = 4
L2_FACT_AUTHORING_TARGET = 130

_NUMBERED_BENCH = re.compile(r"^darkmem_bench_[a-z0-9]+$")

# The lift-to-exhaustion ceiling. One tick at MAX_LIFT_BATCH covers every
# group this corpus can produce several times over; needing more than this
# many ticks means the pending predicate is not converging.
MAX_LIFT_TICKS = 20

_MANIFEST_FACTS = text(f"""
    SELECT kt.triple_key,
           kt.subject_name,
           kt.rel_type,
           kt.object_name,
           kt.project,
           kt.fact,
           kt.verification_status,
           COALESCE(
               array_agg(fs.source_ref ORDER BY fs.source_ref)
                   FILTER (WHERE fs.source_ref IS NOT NULL),
               CAST('{{}}' AS text[])
           ) AS source_memory_ids
    FROM knowledge_triples kt
    LEFT JOIN fact_sources fs
      ON fs.fact_id = kt.id
     AND fs.source_kind = CAST(:kind AS text)
    GROUP BY kt.triple_key, kt.subject_name, kt.rel_type, kt.object_name,
             kt.project, kt.fact, kt.verification_status
    ORDER BY kt.triple_key
""")


def bench_db_name(url: str = bench_db.BENCH_DATABASE_URL) -> str:
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def assert_bench_db_allowed(name: str, *, allow_unnumbered: bool = False) -> None:
    """Refuse every database this harvest may not write, by name, before any
    connection exists. ``darkmem`` and ``darkmem_test*`` are never lawful --
    a harness pointed at a test database is a defect even when it passes."""
    if _NUMBERED_BENCH.fullmatch(name):
        return
    if name == "darkmem_bench":
        if allow_unnumbered:
            return
        raise RuntimeError(
            "BENCH_DATABASE_URL points at the unnumbered 'darkmem_bench'; "
            "harvest runs use an assigned 'darkmem_bench_<n>' (pass "
            "--allow-unnumbered only for a deliberate single-checkout run)"
        )
    raise RuntimeError(
        f"refusing to harvest against database {name!r}: only an assigned "
        "'darkmem_bench_<n>' (or 'darkmem_bench' with --allow-unnumbered) is "
        "lawful; 'darkmem' and 'darkmem_test*' must never see harness writes"
    )


@dataclass(frozen=True)
class HarvestResult:
    manifest: dict
    live_calls: int
    n_facts: int
    capacity: int
    capacity_ok: bool


async def _lift_to_exhaustion(session_factory) -> dict:
    """Run the shipping lift until a tick reports no outstanding groups.

    A tick that reports candidates but writes nothing is the documented
    stalled-group signature (``fact_lift._lift_one``); looping on it would
    never terminate, so it breaks with the count recorded instead.
    """
    ticks = facts_created = sources_added = 0
    stalled_candidates = 0
    while True:
        async with session_factory() as session:
            outcome = await fact_lift.run_lift(
                session, batch_size=fact_lift.MAX_LIFT_BATCH
            )
            await session.commit()
        ticks += 1
        facts_created += outcome.facts_created
        sources_added += outcome.sources_added
        if outcome.candidates == 0:
            break
        if outcome.facts_created == 0 and outcome.sources_added == 0:
            stalled_candidates = outcome.candidates
            break
        if ticks >= MAX_LIFT_TICKS:
            raise RuntimeError(
                f"fact lift did not exhaust in {MAX_LIFT_TICKS} ticks; the "
                "pending predicate is not converging on this corpus"
            )
    return {
        "ticks": ticks,
        "facts_created": facts_created,
        "sources_added": sources_added,
        "stalled_candidates": stalled_candidates,
        "salience_min_asserting_memories": fact_lift.DEFAULT_MIN_ASSERTING_MEMORIES,
    }


async def _manifest_facts(session_factory) -> list[dict]:
    async with session_factory() as session:
        result = await session.execute(
            _MANIFEST_FACTS, {"kind": MEMORY_SOURCE_KIND}
        )
        rows = result.mappings().all()
    return [
        {
            "triple_key": row["triple_key"],
            "subject_name": row["subject_name"],
            "rel_type": row["rel_type"],
            "object_name": row["object_name"],
            "project": row["project"],
            "fact": row["fact"],
            "verification_status": row["verification_status"],
            "source_memory_ids": list(row["source_memory_ids"]),
        }
        for row in rows
    ]


def facts_json(facts: list[dict]) -> str:
    """The byte-comparison spelling of the ``facts`` section -- what the
    reproducibility test and T2.41's re-harvest diff both compare."""
    return json.dumps(facts, indent=2, sort_keys=True, ensure_ascii=False)


async def run_harvest(
    *,
    api_key: str,
    allow_unnumbered: bool = False,
    session_factory=bench_db.session_factory,
    cache_dir: str | Path = CACHE_DIR,
    corpus_path: str | Path = retrieval_gold.CORPUS_PATH,
    manifest_path: str | Path = MANIFEST_PATH,
    write: bool = False,
) -> HarvestResult:
    db_name = bench_db_name()
    assert_bench_db_allowed(db_name, allow_unnumbered=allow_unnumbered)

    corpus_bytes = Path(corpus_path).read_bytes()
    entries = retrieval_gold.load_retrieval_corpus(corpus_path)

    await bench_db.reset_bench_db()
    await run_smoke.seed_llm_purpose_configs(session_factory, api_key)

    async with session_factory() as session:
        llm_config = await get_llm_config(session)

    prepared = await retrieval_gold.seed_memory_rows(session_factory, entries)
    llm = CachingLLMOrchestrator(llm_config, cache_dir=str(cache_dir))
    ingest_result = await run_ingest(llm, prepared, GateConfig(), session_factory)

    lift = await _lift_to_exhaustion(session_factory)
    facts = await _manifest_facts(session_factory)

    manifest = {
        "_reproducible": (
            "Everything in this file except header.generated_at and "
            "header.git_sha is byte-identical across re-runs on an unchanged "
            "tree with a warm cache; the sorted 'facts' section is the "
            "forgery detector T2.41's --gate evidence re-derives and diffs."
        ),
        "header": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_sha": run_smoke.git_sha(),
            "bench_db": db_name,
            "corpus_path": str(Path(corpus_path).name),
            "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
            "corpus_entries": len(entries),
            "gate_config": ingest_result.gate_config,
            "embedder_fingerprint": ingest_result.fingerprint,
            "ingest_live_calls": ingest_result.live_calls,
            "lift": lift,
            "assignment_seed": ASSIGNMENT_SEED,
            "pairs_per_premise_cap": PAIRS_PER_PREMISE_CAP,
        },
        "facts": facts,
    }

    if write:
        Path(manifest_path).write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    capacity = PAIRS_PER_PREMISE_CAP * len(facts)
    return HarvestResult(
        manifest=manifest,
        live_calls=ingest_result.live_calls,
        n_facts=len(facts),
        capacity=capacity,
        capacity_ok=capacity >= L2_FACT_AUTHORING_TARGET,
    )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Harvest Layer-2 facts into entailment/l2_harvest.json."
    )
    parser.add_argument(
        "--allow-unnumbered", action="store_true",
        help="permit the bare 'darkmem_bench' database name",
    )
    args = parser.parse_args(argv)

    api_key = run_smoke.require_deepseek_api_key()
    result = await run_harvest(
        api_key=api_key, allow_unnumbered=args.allow_unnumbered, write=True,
    )
    header = result.manifest["header"]
    print(f"bench_db: {header['bench_db']}")
    print(f"ingest live_calls: {result.live_calls}")
    print(f"embedder fingerprint: {header['embedder_fingerprint']}")
    print(f"lift: {header['lift']}")
    print(f"facts harvested: {result.n_facts}")
    print(
        f"capacity check: {PAIRS_PER_PREMISE_CAP} x {result.n_facts} = "
        f"{result.capacity} >= {L2_FACT_AUTHORING_TARGET}: "
        f"{'PASS' if result.capacity_ok else 'FAIL'}"
    )
    print(f"manifest written: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
