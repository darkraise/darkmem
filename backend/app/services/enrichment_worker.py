import asyncio
import logging

from sqlalchemy import func, select

from app.models.code import CodeSymbol
from app.services.llm import LLMOrchestrator
from app.services import prompt

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Summarize what this {kind} does in 1-2 sentences. Be specific about inputs, outputs, and side effects. Do not include the code itself.

```
{source_code}
```"""

MAX_SOURCE_CHARS = 3000


class EnrichmentWorker:
    def __init__(self, llm: LLMOrchestrator, broadcast=None):
        self.llm = llm
        self._running = False
        self.batch_size = 5
        self.interval = 10
        self._broadcast = broadcast

    async def process_batch(self, batch_size: int | None = None) -> int:
        from app.database import async_session_factory
        from app.config import FEATURE_FLAGS_DEFAULTS
        from app.models.config import Config

        size = batch_size if batch_size is not None else self.batch_size

        async with async_session_factory() as session:
            stmt = (
                select(CodeSymbol)
                .where(CodeSymbol.enrichment_status == "pending")
                .order_by(CodeSymbol.enrichment_priority.desc())
                .limit(size)
            )
            result = await session.execute(stmt)
            symbols = result.scalars().all()

            if not symbols:
                return 0

            flags_result = await session.execute(select(Config).where(Config.key == "feature_flags"))
            config_row = flags_result.scalar_one_or_none()
            concurrency = (config_row.value if config_row else FEATURE_FLAGS_DEFAULTS).get("pipeline_concurrency", 5)
            sem = asyncio.Semaphore(concurrency)

            system_prompt = prompt.get("summarization")

            summaries: dict[int, str | Exception] = {}

            async def _enrich_one(idx: int, symbol) -> None:
                async with sem:
                    prompt = SUMMARY_PROMPT.format(
                        kind=symbol.kind,
                        source_code=symbol.source_code[:MAX_SOURCE_CHARS],
                    )
                    summaries[idx] = await self.llm.chat_completion(
                        "summarization",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                    )

            await asyncio.gather(
                *[_enrich_one(i, sym) for i, sym in enumerate(symbols)],
                return_exceptions=True,
            )

            processed = 0
            for i, symbol in enumerate(symbols):
                result_val = summaries.get(i)
                if isinstance(result_val, str):
                    symbol.summary = result_val
                    symbol.enrichment_status = "completed"
                    processed += 1
                else:
                    if isinstance(result_val, Exception):
                        logger.exception("Failed to enrich symbol %s: %s", symbol.id, result_val)
                    symbol.enrichment_status = "failed"

            await session.commit()

            pending_count = (await session.execute(
                select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "pending")
            )).scalar() or 0
            if self._broadcast:
                await self._broadcast("enrichment.batch_completed", {"processed": processed, "pending_remaining": pending_count})
        return processed

    async def run_loop(self) -> None:
        self._running = True
        logger.info("Enrichment worker started (interval=%ds, batch_size=%d)", self.interval, self.batch_size)

        while self._running:
            try:
                processed = await self.process_batch()
                if processed > 0:
                    logger.info("Enriched %d symbols", processed)
                else:
                    await asyncio.sleep(self.interval)
            except Exception:
                logger.exception("Enrichment loop error")
                await asyncio.sleep(self.interval)

        logger.info("Enrichment worker stopped")

    def stop(self) -> None:
        self._running = False
