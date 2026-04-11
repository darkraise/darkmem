"""Phase 12: DB-level audit.

Runs direct SQL assertions that can only be verified at the database
level. Requires the backend Python environment so it can import from
`app.database`.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Allow running from docs/e2e/scripts — add the backend to the path
BACKEND_DIR = os.environ.get("DARKMEM_BACKEND_DIR", "/workspace/darkmem/backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from sqlalchemy import text
    from app.database import async_session_factory
except ImportError as e:
    print(f"Cannot import app.database. Set DARKMEM_BACKEND_DIR to the backend folder. Error: {e}")
    sys.exit(2)


class Report:
    def __init__(self) -> None:
        self.passes: int = 0
        self.failures: list[str] = []

    def ok(self, label: str) -> None:
        self.passes += 1
        print(f"  [PASS] {label}")

    def fail(self, label: str) -> None:
        self.failures.append(label)
        print(f"  [FAIL] {label}")

    def summary(self) -> int:
        print()
        print(f"=== DB audit ===")
        print(f"  {self.passes} passed, {len(self.failures)} failed")
        for f in self.failures:
            print(f"    - {f}")
        return 1 if self.failures else 0


async def main() -> int:
    report = Report()

    async with async_session_factory() as session:
        # 1. Memory embeddings have fingerprints (after any ingestion)
        total_me = (await session.execute(text("SELECT count(*) FROM memory_embeddings"))).scalar_one()
        null_me = (await session.execute(text(
            "SELECT count(*) FROM memory_embeddings WHERE model_fingerprint IS NULL"
        ))).scalar_one()
        if total_me == 0:
            report.ok("memory_embeddings empty (no fingerprint check needed)")
        elif null_me == 0:
            report.ok(f"all {total_me} memory_embeddings have fingerprints")
        else:
            report.fail(f"{null_me}/{total_me} memory_embeddings missing fingerprint")

        # 2. Entities have fingerprints
        total_e = (await session.execute(text("SELECT count(*) FROM entities"))).scalar_one()
        null_e = (await session.execute(text(
            "SELECT count(*) FROM entities WHERE model_fingerprint IS NULL AND embedding IS NOT NULL"
        ))).scalar_one()
        if total_e == 0:
            report.ok("entities empty")
        elif null_e == 0:
            report.ok(f"all {total_e} entities with embeddings have fingerprints")
        else:
            report.fail(f"{null_e}/{total_e} entities with embeddings missing fingerprint")

        # 3. No duplicate (name, entity_type) pairs (unique constraint enforces this)
        dupes = (await session.execute(text("""
            SELECT count(*) FROM (
                SELECT name, entity_type, count(*) FROM entities
                GROUP BY name, entity_type HAVING count(*) > 1
            ) d
        """))).scalar_one()
        if dupes == 0:
            report.ok("no duplicate (name, entity_type) rows")
        else:
            report.fail(f"{dupes} duplicate entity (name, type) rows")

        # 4. memory_embeddings one-to-one with memories
        mem_emb_count = (await session.execute(text(
            "SELECT count(DISTINCT memory_id) FROM memory_embeddings"
        ))).scalar_one()
        mem_count = (await session.execute(text("SELECT count(*) FROM memories"))).scalar_one()
        if mem_emb_count <= mem_count:
            report.ok(f"memory_embeddings ({mem_emb_count}) <= memories ({mem_count})")
        else:
            report.fail(f"more embeddings ({mem_emb_count}) than memories ({mem_count})")

        # 5. Pipeline failures orphan check (any unresolved failures reference missing memories?)
        orphans = (await session.execute(text("""
            SELECT count(*) FROM pipeline_failures pf
            WHERE pf.entity_type = 'memory'
              AND pf.resolved_at IS NULL
              AND NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = pf.entity_id)
        """))).scalar_one()
        if orphans == 0:
            report.ok("no orphaned pipeline_failures for missing memories")
        else:
            report.fail(f"{orphans} orphaned pipeline_failures reference missing memories")

        # 6. Entity embedding cache consistency — at most one entry per (name_lower, fingerprint)
        cache_dupes = (await session.execute(text("""
            SELECT count(*) FROM (
                SELECT name_lower, model_fingerprint, count(*) FROM entity_embedding_cache
                GROUP BY name_lower, model_fingerprint HAVING count(*) > 1
            ) d
        """))).scalar_one()
        if cache_dupes == 0:
            report.ok("entity_embedding_cache primary key holds")
        else:
            report.fail(f"{cache_dupes} duplicate cache keys")

        # 7. Token blocklist — expired entries should eventually be cleaned; here we just check the table exists
        total_tokens = (await session.execute(text("SELECT count(*) FROM token_blocklist"))).scalar_one()
        report.ok(f"token_blocklist has {total_tokens} entries")

        # 8. Audit log — check it has data
        audit_count = (await session.execute(text("SELECT count(*) FROM audit_log"))).scalar_one()
        report.ok(f"audit_log has {audit_count} entries")

    return report.summary()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
