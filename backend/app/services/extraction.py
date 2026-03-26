import json
import logging

from app.services.llm import LLMOrchestrator

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a knowledge extraction engine. Extract structured information from text.
Return ONLY valid JSON with no additional text."""

EXTRACTION_PROMPT = """Analyze this text and extract:
1. Named entities (people, services, projects, technologies, concepts)
2. Relationships between entities
3. Memory type classification
4. Importance score (0.0 to 1.0)

Return JSON in this exact format:
{
  "entities": [{"name": "string", "type": "person|service|project|technology|concept|organization", "properties": {}}],
  "relationships": [{"source": "entity_name", "target": "entity_name", "type": "USES|DEPENDS_ON|WORKS_ON|IS_A|HAS_PART|RELATED_TO", "properties": {}, "weight": 0.8}],
  "memory_type": "fact|decision|preference|debug|session|architecture|workflow",
  "importance": 0.7
}

Text:
"""


class ExtractionService:
    def __init__(self, llm: LLMOrchestrator):
        self.llm = llm

    async def extract(self, content: str) -> dict:
        try:
            response = await self.llm.chat_completion(
                "extraction",
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM},
                    {"role": "user", "content": EXTRACTION_PROMPT + content},
                ],
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Extraction failed: {e}")
            return {"entities": [], "relationships": [], "memory_type": "fact", "importance": 0.5}
