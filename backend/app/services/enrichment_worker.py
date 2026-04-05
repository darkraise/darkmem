import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeSymbol
from app.services.llm import LLMOrchestrator
from app.services.prompt import PromptService

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Summarize what this {kind} does in 1-2 sentences. Be specific about inputs, outputs, and side effects. Do not include the code itself.

```
{source_code}
```"""

MAX_SOURCE_CHARS = 3000


class EnrichmentWorker:
    def __init__(self, session: AsyncSession, llm: LLMOrchestrator):
        self.session = session
        self.llm = llm
        self._running = False
        self.batch_size = 5
        self.interval = 10

    async def process_batch(self, batch_size: int | None = None) -> int:
        batch_size = batch_size if batch_size is not None else self.batch_size
        stmt = (
            select(CodeSymbol)
            .where(CodeSymbol.enrichment_status == "pending")
            .order_by(CodeSymbol.enrichment_priority.desc())
            .limit(batch_size)
        )
        result = await self.session.execute(stmt)
        symbols = result.scalars().all()

        processed = 0
        for symbol in symbols:
            try:
                prompt = SUMMARY_PROMPT.format(
                    kind=symbol.kind,
                    source_code=symbol.source_code[:MAX_SOURCE_CHARS],
                )
                system_prompt = await PromptService.get("summarization", self.session)
                summary = await self.llm.chat_completion(
                    "summarization",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                symbol.summary = summary
                symbol.enrichment_status = "completed"
                processed += 1
            except Exception:
                logger.exception("Failed to enrich symbol %s", symbol.id)
                symbol.enrichment_status = "failed"

        await self.session.flush()
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
