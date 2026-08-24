"""Purge eval memories AND orphaned graph entities so a re-run isn't poisoned by
stale entities from earlier (pre-fix) runs. Phase-4 ANN dedup was collapsing
fresh correct entities ('february outage') onto leftover ghosts ('march outage')
that survived prior memory deletes because their memory_ids still held ids from
already-deleted memories.

Run from backend/:  <python> scripts/eval_round3/purge_eval.py
"""
import asyncio
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, BACKEND)

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import async_session_factory  # noqa: E402
from scripts.benchlib.db_target import assert_destructive_target_allowed  # noqa: E402


async def main():
    # Statement 0 below resurrects every superseded memory in whatever database
    # DATABASE_URL resolves to, which on the host that runs the live instance is
    # production. The lineage it destroys is decided at ingest and is not
    # recomputed on read, so there is nothing to rebuild it from.
    assert_destructive_target_allowed(
        settings.database_url, actor="eval_round3/purge_eval"
    )
    async with async_session_factory() as s:
        # 0) Resurrect any superseded memory first, so deleting its superseder
        #    (FK superseded_by -> SET NULL) doesn't leave it status='superseded'
        #    with a null pointer (violates chk_superseded_has_pointer).
        d0 = await s.execute(text(
            "UPDATE memories SET status='active', superseded_by=NULL WHERE status='superseded'"
        ))
        # 1) Delete the eval-session memories (current + the prior contaminating
        #    session that created the ghost entities). Keep the 4 'claude-code'
        #    sample memories.
        d1 = await s.execute(text(
            "DELETE FROM memories WHERE source_agent IN ('eval-r3', 'claude-code-eval')"
        ))
        # 2) Delete entities none of whose memory_ids reference a live memory
        #    (the ghosts). entity_relations FK is ON DELETE CASCADE.
        d2 = await s.execute(text(
            "DELETE FROM entities e WHERE NOT EXISTS ("
            " SELECT 1 FROM memories m WHERE m.id = ANY(e.memory_ids))"
        ))
        # 3) Belt-and-suspenders: drop any relations now dangling.
        d3 = await s.execute(text(
            "DELETE FROM entity_relations r WHERE NOT EXISTS ("
            " SELECT 1 FROM entities e WHERE e.id = r.source_entity_id) "
            " OR NOT EXISTS (SELECT 1 FROM entities e WHERE e.id = r.target_entity_id)"
        ))
        await s.commit()
        print(f"resurrected superseded rows: {d0.rowcount}")
        print(f"deleted eval memories: {d1.rowcount}")
        print(f"deleted orphan entities: {d2.rowcount}")
        print(f"deleted dangling relations: {d3.rowcount}")
        # sanity: confirm ghosts gone
        for nm in ("march outage", "api", "2026-05-12", "auth module shipment"):
            n = (await s.execute(text("SELECT count(*) FROM entities WHERE name = :n"), {"n": nm})).scalar()
            print(f"  remaining '{nm}': {n}")


if __name__ == "__main__":
    asyncio.run(main())
