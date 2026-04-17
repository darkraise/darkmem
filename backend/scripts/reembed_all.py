"""Re-embed every entity whose cached vector is stale vs the current retriever.

Dry-run by default; pass ``--commit`` to actually write. Uses the ML retriever
only — the assumption is that this script runs AFTER ml_retrieval has been
promoted and the MLModels singleton is loaded.

Run from the backend/ directory:
    python -m scripts.reembed_all              # dry-run count only
    python -m scripts.reembed_all --commit     # write new embeddings
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text

from app.config import ml_pipeline_settings
from app.database import async_session_factory
from app.repositories.graph import PostgresGraphRepository
from app.services.ml_models import load_ml_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger("reembed_all")


async def count_stale(fingerprint: str) -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM entities WHERE embedding IS NOT NULL "
                "AND (model_fingerprint IS NULL OR model_fingerprint != :fp)"
            ),
            {"fp": fingerprint},
        )
        return int(result.scalar_one() or 0)


async def fetch_batch(fingerprint: str, batch_size: int) -> list[tuple[str, str]]:
    """Return up to ``batch_size`` (id, name) pairs that need re-embedding."""
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT id::text AS id, name FROM entities "
                "WHERE embedding IS NOT NULL "
                "  AND (model_fingerprint IS NULL OR model_fingerprint != :fp) "
                "LIMIT :limit"
            ),
            {"fp": fingerprint, "limit": batch_size},
        )
        return [(row["id"], row["name"]) for row in result.mappings().all()]


async def write_embeddings(
    pairs: list[tuple[str, str]],
    vectors: list[list[float]],
    fingerprint: str,
) -> None:
    async with async_session_factory() as session:
        repo = PostgresGraphRepository(session)
        for (eid, _name), vec in zip(pairs, vectors):
            await repo.upsert_entity_embedding(eid, vec, model_fingerprint=fingerprint)
        await session.commit()


async def main(dry_run: bool, batch_size: int) -> int:
    ml = load_ml_models()
    fingerprint = ml.fingerprint
    logger.info("retriever fingerprint=%s", fingerprint)

    total_stale = await count_stale(fingerprint)
    logger.info("stale entities needing re-embedding: %d", total_stale)
    if dry_run:
        logger.info("dry-run (no writes). Pass --commit to apply.")
        return 0

    done = 0
    prefix = ml_pipeline_settings.retriever_query_prefix
    log_every = max(1, total_stale // 50) if total_stale else 1
    while True:
        pairs = await fetch_batch(fingerprint, batch_size)
        if not pairs:
            break
        names = [name for _eid, name in pairs]
        prefixed = [prefix + n for n in names]
        encoded = await asyncio.to_thread(
            lambda: ml.retriever.encode(
                prefixed,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=batch_size,
            ).tolist()
        )
        await write_embeddings(pairs, encoded, fingerprint)
        done += len(pairs)
        if done % log_every < batch_size or done >= total_stale:
            logger.info("wrote %d/%d (%.0f%%)", done, total_stale, 100 * done / max(1, total_stale))

    logger.info("reembed_all done: %d entities", done)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--commit", dest="dry_run", action="store_false")
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()
    raise SystemExit(asyncio.run(main(args.dry_run, args.batch_size)))
