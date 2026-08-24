"""ML-based classification — alternate implementation for the
classifier purpose.

Mirrors the surface of ``ClassificationService`` so the pipeline's
``run_classify`` can dispatch to either implementation without
caring which is configured. Returns the same ``{hall, summary,
emotions, flags}`` shape; ML inference doesn't produce a summary or
emotions, so those come back as ``None`` / empty.

Resolution rule:

* If the model's predicted label is in the area-allowed-types set
  for the current ``classification_areas`` flag, return it.
* Otherwise fall back to ``"fact"`` — the same conservative default
  the LLM service uses when the model returns a stray label.
"""
from __future__ import annotations

import logging

from app.services.classification_areas import (
    SIMPLE_NORMALIZATION,
    get_merged_llm_types,
)
from app.services.ml_runtime import MLModelManager, MLRuntimeUnavailable

logger = logging.getLogger(__name__)


class MLClassificationService:
    """In-process HF classifier dispatch for the classification purpose.

    IMPORTANT: ML inference produces only a memory-type label. Setting
    ``classifier_kind='local'`` on the classification purpose therefore
    DISABLES summary and emotion/flag enrichment — ``classify`` always
    returns ``summary=None`` with empty ``emotions``/``flags``, so the
    enrichment columns those would populate stay null even though
    classification always runs. Use the LLM-backed ``ClassificationService`` if you need summaries.
    """

    def __init__(self, manager: MLModelManager, model_repo: str, ttl_seconds: int) -> None:
        self.manager = manager
        self.model_repo = model_repo
        self.ttl_seconds = ttl_seconds

    async def classify(
        self,
        content: str,
        enabled_areas: list[str],
        system_prompt: str,  # unused; kept for interface parity with LLM service
        mode: str = "simple",
        usage_subject=None,  # unused; this classifier spends no tokens
    ) -> dict:
        valid_names = sorted(get_merged_llm_types(enabled_areas, mode=mode).keys())
        try:
            label, _score = await self.manager.classify(
                self.model_repo, self.ttl_seconds, content,
            )
        except MLRuntimeUnavailable as exc:
            logger.warning("ML classifier unavailable: %s", exc)
            return {"hall": "fact", "summary": None, "emotions": [], "flags": []}
        except Exception as exc:
            logger.error("ML classifier inference failed: %s", exc)
            return {"hall": "fact", "summary": None, "emotions": [], "flags": []}

        normalised = label.strip().lower()
        if mode == "simple" and normalised not in valid_names:
            normalised = SIMPLE_NORMALIZATION.get(normalised, normalised)
        if normalised not in valid_names:
            logger.info(
                "ML classifier returned label %r not in allowed types; defaulting to 'fact'",
                label,
            )
            normalised = "fact"
        return {"hall": normalised, "summary": None, "emotions": [], "flags": []}
