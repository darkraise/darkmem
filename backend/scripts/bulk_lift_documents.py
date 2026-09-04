"""Lift filed documents into memories, priced before it is spent (spec §6.3).

`lift_document` extracts propositions per document through the LLM, so lifting
the existing corpus is a **real spend, not a migration**. 475 documents over
49,310 blocks is the largest single LLM expenditure this project has proposed
and nothing in this tree had measured it.

So this script will not do it by default. It runs a **sample** first, reports
live calls, tokens and wall-clock, and refuses the full run unless the caller
passes `--all` having seen that number. A run that quietly spends an unmeasured
amount on a corpus nobody has priced is exactly the shape this project's gate
ledger refuses elsewhere.

Two mitigations that are properties of the code rather than hopes:

- the lift is **idempotent** (`strip_document_lift` is keyed on `document_id`,
  so a re-run replaces rather than doubles), and
- it is **per-document**, so a partial run is not a broken state -- it is a
  smaller corpus.

    # measure, and stop
    python scripts/bulk_lift_documents.py --project darkmem

    # what it would touch, spending nothing
    python scripts/bulk_lift_documents.py --project darkmem --dry-run

    # the full run, after reading the sample's number
    python scripts/bulk_lift_documents.py --project darkmem --all
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

from sqlalchemy import text

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.database import async_session_factory  # noqa: E402
from app.services.config import get_llm_config  # noqa: E402
from app.services.llm import LLMOrchestrator  # noqa: E402
from app.services.memory import MemoryService  # noqa: E402
from app.services.proposition_lift import lift_document  # noqa: E402
from app.services.usage_recorder import UsageRecorder  # noqa: E402

DEFAULT_SAMPLE = 20

# The measurement reads the `llm_usage` ledger the recorder writes, NOT
# counters on the orchestrator: `LLMOrchestrator` carries no `live_calls` or
# `prompt_tokens` attribute -- those belong to benchlib's caching twin -- so a
# `getattr(llm, "live_calls", 0)` would report a confident zero for every run
# and look exactly like a measured one. This is the ledger the Usage page
# reads, which is also what makes the number checkable after the fact.
_USAGE = text(
    """
    SELECT count(*)                            AS calls,
           coalesce(sum(prompt_tokens), 0)     AS prompt_tokens,
           coalesce(sum(completion_tokens), 0) AS completion_tokens,
           coalesce(sum(cost_micros), 0)       AS cost_micros,
           bool_and(tokens_measured)           AS all_measured
    FROM llm_usage
    WHERE occurred_at >= :since
    """
)

_TARGETS = text(
    """
    SELECT CAST(d.id AS text) AS id, d.project, d.uri,
           (SELECT count(*) FROM blocks b WHERE b.document_id = d.id) AS blocks
    FROM documents d
    WHERE (CAST(:project AS text) IS NULL OR d.project = CAST(:project AS text))
    ORDER BY d.created_at
    """
)


def _report(label: str, lifted: int, docs: int, blocks: int, elapsed: float,
            usage: dict) -> None:
    calls = usage["calls"]
    prompt = usage["prompt_tokens"]
    completion = usage["completion_tokens"]
    print(f"\n── {label} ──")
    print(f"  documents      {docs}")
    print(f"  blocks         {blocks}")
    print(f"  propositions   {lifted}")
    print(f"  live calls     {calls}")
    print(f"  prompt tokens  {prompt}")
    print(f"  output tokens  {completion}")
    if usage["cost_micros"]:
        print(f"  cost           ${usage['cost_micros'] / 1_000_000:.4f}")
    if not usage["all_measured"]:
        # Said plainly: a vendor that returns no usage block leaves the token
        # columns null, and a total summed over those reads low rather than
        # missing.
        print("  NOTE: at least one call reported no usage — tokens read LOW")
    print(f"  wall clock     {elapsed:.1f}s")
    if docs:
        print(f"  per document   {calls / docs:.1f} calls, "
              f"{(prompt + completion) / docs:.0f} tokens, {elapsed / docs:.1f}s")


def _extrapolate(total_docs: int, sampled: int, usage: dict, elapsed: float) -> None:
    """What the whole corpus would cost at the sample's rate.

    Stated as an estimate and nothing more: proposition count per document is
    the variable this cannot know, and a sample taken in filing order is not a
    random one.
    """
    if sampled == 0:
        return
    factor = total_docs / sampled
    tokens = usage["prompt_tokens"] + usage["completion_tokens"]
    print(f"\n── extrapolated to all {total_docs} document(s) ──")
    print(f"  live calls     ~{round(usage['calls'] * factor):,}")
    print(f"  tokens         ~{round(tokens * factor):,}")
    if usage["cost_micros"]:
        print(f"  cost           ~${usage['cost_micros'] * factor / 1_000_000:.2f}")
    print(f"  wall clock     ~{elapsed * factor / 60:.0f} min")
    print("\n  An estimate, not a quote: propositions per document is exactly")
    print("  what varies, and a sample in filing order is not a random one.")


async def run(project: str | None, sample: int, run_all: bool, dry_run: bool) -> int:
    async with async_session_factory() as session:
        rows = (await session.execute(_TARGETS, {"project": project})).mappings().all()

    total = len(rows)
    targets = list(rows) if run_all else list(rows[:sample])
    blocks = sum(r["blocks"] for r in targets)

    scope = "" if project is None else f" in project {project!r}"
    print(f"{total} document(s) filed{scope}")
    print(f"  {len(targets)} will be lifted "
          f"({'FULL RUN' if run_all else f'sample of {sample}'})")
    print(f"  {blocks} block(s) in scope")

    if dry_run:
        for row in targets[:20]:
            print(f"    would lift {row['uri']} ({row['blocks']} blocks)")
        if len(targets) > 20:
            print(f"    ... and {len(targets) - 20} more")
        print("\nDry run: nothing was lifted and nothing was spent.")
        return 0

    # Built the way `app.main` builds it, recorder included: an orchestrator
    # without one measures nothing while looking identical from outside, and
    # this is the run most worth having on the usage ledger.
    async with async_session_factory() as session:
        llm_config = await get_llm_config(session)
    llm = LLMOrchestrator(llm_config, recorder=UsageRecorder(async_session_factory))

    # The ledger is time-keyed, so the window opens before the first call.
    async with async_session_factory() as session:
        since = (await session.execute(text("SELECT now()"))).scalar_one()

    started = time.monotonic()
    lifted = failed = empty = 0
    for index, row in enumerate(targets, start=1):
        async with async_session_factory() as session:
            memory_service = MemoryService(session)
            try:
                result = await lift_document(
                    session, llm, memory_service,
                    document_id=row["id"], actor="bulk_lift_documents",
                )
                await session.commit()
            except Exception as exc:  # noqa: BLE001 - one document must not stop the run
                await session.rollback()
                failed += 1
                print(f"  [{index}/{len(targets)}] FAILED {row['uri']}: {exc}")
                continue
        if result is None:
            empty += 1
        else:
            lifted += result.lifted
        # Flushed per document: a run killed at document 300 must still have
        # reported the 299 before it.
        print(f"  [{index}/{len(targets)}] {row['uri']} -> "
              f"{0 if result is None else result.lifted} proposition(s)",
              flush=True)

    elapsed = time.monotonic() - started
    async with async_session_factory() as session:
        usage = dict((await session.execute(
            _USAGE, {"since": since}
        )).mappings().one())

    _report(
        "FULL RUN" if run_all else "SAMPLE",
        lifted, len(targets), blocks, elapsed, usage,
    )
    if empty:
        print(f"  {empty} document(s) held no blocks and were skipped")
    if failed:
        print(f"  {failed} document(s) FAILED — the corpus is smaller, not broken")

    if not run_all:
        _extrapolate(total, len(targets), usage, elapsed)
        print("\nThe sample stops here by design. Re-run with --all to lift the")
        print("rest, with that number in hand. The lift is idempotent, so the")
        print("sampled documents are replaced rather than doubled.")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=None, help="restrict to one project")
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE,
                    help=f"documents to price before stopping (default {DEFAULT_SAMPLE})")
    ap.add_argument("--all", dest="run_all", action="store_true",
                    help="lift every matching document — only after reading a sample")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be lifted and spend nothing")
    args = ap.parse_args()
    return asyncio.run(run(args.project, args.sample, args.run_all, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
