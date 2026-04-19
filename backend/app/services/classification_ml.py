"""ML-based memory-type classification service.

Drop-in replacement for :class:`app.services.classification_llm.ClassificationService`.
Uses the darkmem-classifier-v1 ModernBERT head, 7-class.

Contract is identical: returns ``{"hall", "summary", "emotions", "flags"}``.
``summary`` is always ``None`` from the ML path (same as the LLM error branch).
``emotions`` and ``flags`` are empty lists. ``enabled_areas``, ``system_prompt``,
and ``mode`` are accepted for signature parity and currently ignored.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import ml_pipeline_settings
from app.services.ml_models import MLModels, ensure_classification_loaded
from app.taxonomy import MEMORY_TYPES

logger = logging.getLogger(__name__)


def _classifier_id2label(model: Any) -> dict[int, str]:
    raw = getattr(model.config, "id2label", None) or {}
    mapped: dict[int, str] = {}
    for k, v in raw.items():
        try:
            mapped[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    if mapped and set(mapped.values()) == set(MEMORY_TYPES):
        return mapped
    return {i: l for i, l in enumerate(MEMORY_TYPES)}


def _classify_sync(content: str) -> str:
    import torch  # noqa: PLC0415

    ml: MLModels = ensure_classification_loaded()
    enc = ml.classifier_tok(
        content,
        return_tensors="pt",
        truncation=True,
        max_length=ml_pipeline_settings.classifier_max_length,
        padding=False,
    )
    if ml.device.startswith("cuda"):
        enc = {k: v.to(ml.device) for k, v in enc.items()}
    with torch.no_grad():
        logits = ml.classifier(**enc).logits
    top = int(logits[0].argmax().item())
    return _classifier_id2label(ml.classifier).get(top, "fact")


class ClassificationMLService:
    async def classify(
        self,
        content: str,
        enabled_areas: list[str],
        system_prompt: str,
        mode: str = "simple",
    ) -> dict:
        if not content or not content.strip():
            return {"hall": "fact", "summary": None, "emotions": [], "flags": []}

        try:
            classified = await asyncio.to_thread(_classify_sync, content)
        except Exception:
            logger.exception("ML classification failed")
            return {"hall": "fact", "summary": None, "emotions": [], "flags": []}

        if classified not in MEMORY_TYPES:
            logger.warning("Classifier returned unknown label %r, falling back to 'fact'", classified)
            classified = "fact"

        return {
            "hall": classified,
            "summary": None,
            "emotions": [],
            "flags": [],
        }
