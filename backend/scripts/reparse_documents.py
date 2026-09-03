#!/usr/bin/env python
"""Re-parse filed documents in place (increment 5).

**Why this exists.** `content_hash` is the change gate, so re-pushing a
document's own bytes returns `unchanged` and never touches a block. That is
right for every ordinary filing and wrong after a *parser* change: the filed
blocks are stale while the bytes are identical, so nothing an operator can do
through a door replaces them. CLAUDE.md records the same trap for `divider` --
201 documents kept `---` in their content and no divider row -- and increment
5's list markers are the second instance.

It reads `documents.content`, which has been the stored source of record since
the round-trip increment, so this needs neither the original files nor a
login. A document filed from bytes stores NULL there and is reported as
skipped rather than silently passed over.

**The cost is real and is re-embedding, not parsing.** Filing replaces a
document's blocks with fresh ids, so every block is embedded again. Across a
475-document corpus that is tens of thousands of embed calls. They go to the
configured embedder, so on a local endpoint this is time rather than money --
but it is not free, and `--limit` exists so a run can be sized before it is
committed to.

Usage (inside the app container, or with DATABASE_URL pointed at the stack):

    python scripts/reparse_documents.py --dry-run
    python scripts/reparse_documents.py --project darkmem --limit 25
    python scripts/reparse_documents.py --project darkmem
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.database import async_session_factory  # noqa: E402
from app.services.document_door import put_document  # noqa: E402
from app.services.llm import LLMOrchestrator  # noqa: E402
from app.services.config import get_llm_config  # noqa: E402
from app.services.usage_recorder import UsageRecorder  # noqa: E402

_TARGETS = text(
    """
    SELECT CAST(id AS text) AS id, project, uri, title, source_type,
           content IS NULL AS no_content
    FROM documents
    WHERE (CAST(:project AS text) IS NULL OR project = CAST(:project AS text))
      AND (CAST(:uri AS text) IS NULL OR uri = CAST(:uri AS text))
    ORDER BY created_at
    """
)

_CONTENT = text("SELECT content FROM documents WHERE id = CAST(:id AS uuid)")


async def run(
    project: str | None, uri: str | None, limit: int | None, dry_run: bool,
) -> int:
    async with async_session_factory() as session:
        rows = (await session.execute(
            _TARGETS, {"project": project, "uri": uri},
        )).mappings().all()

    targets = [r for r in rows if not r["no_content"]]
    skipped = [r for r in rows if r["no_content"]]
    if limit is not None:
        targets = targets[:limit]

    print(f"{len(rows)} document(s) matched"
          f"{'' if project is None else f' in project {project!r}'}")
    print(f"  {len(targets)} will be reparsed")
    if skipped:
        print(f"  {len(skipped)} skipped: filed from bytes, no stored content")
    if dry_run:
        for row in targets[:20]:
            print(f"    would reparse {row['uri']}")
        if len(targets) > 20:
            print(f"    ... and {len(targets) - 20} more")
        return 0

    # Built the way `app.main` builds it, recorder included: an orchestrator
    # without one measures nothing while looking identical from outside, and a
    # corpus-wide re-embed is exactly the run worth having on the usage ledger.
    async with async_session_factory() as session:
        llm_config = await get_llm_config(session)
    llm = LLMOrchestrator(llm_config, recorder=UsageRecorder(async_session_factory))
    filed = failed = 0
    for index, row in enumerate(targets, start=1):
        async with async_session_factory() as session:
            content = (await session.execute(_CONTENT, {"id": row["id"]})).scalar_one()
            try:
                result = await put_document(
                    session, llm,
                    project=row["project"], uri=row["uri"], content=content,
                    title=row["title"], source_type=row["source_type"],
                    actor="reparse_documents", force_reparse=True,
                )
                await session.commit()
            except Exception as exc:  # per-document isolation, same posture
                await session.rollback()  # as the corpus importer's
                failed += 1
                print(f"  [{index}/{len(targets)}] FAILED {row['uri']}: {exc}")
                continue
        filed += 1
        print(f"  [{index}/{len(targets)}] {row['uri']}: "
              f"{result.blocks_filed} block(s), {result.blocks_embedded} embedded")

    print(f"\nreparsed {filed}, failed {failed}")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=None, help="limit to one project")
    ap.add_argument("--uri", default=None,
                    help="reparse exactly one document, for a spot check")
    ap.add_argument("--limit", type=int, default=None,
                    help="reparse at most N documents; size a run before committing to it")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be reparsed; no writes, no embed calls")
    args = ap.parse_args()
    return asyncio.run(run(args.project, args.uri, args.limit, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
