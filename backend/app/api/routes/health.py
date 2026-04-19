"""ML pipeline health endpoint.

Exposes ``GET /api/health/ml_models`` reporting whether each fine-tuned head
is loaded, what device they are on, and current CUDA VRAM if applicable.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.config import ml_pipeline_settings
from app.services import ml_models as _ml_module
from app.services.ml_models import any_group_available, group_status, models_available

logger = logging.getLogger(__name__)

router = APIRouter()


def _head_status(instance) -> dict[str, bool]:
    if instance is None:
        return {
            "span": False,
            "typer": False,
            "relation": False,
            "classifier": False,
            "retriever": False,
        }
    return {
        "span": instance.span is not None,
        "typer": instance.typer is not None and instance.typer_tok is not None,
        "relation": instance.relation is not None and instance.relation_tok is not None,
        "classifier": instance.classifier is not None and instance.classifier_tok is not None,
        "retriever": instance.retriever is not None,
    }


def _head_sources(instance) -> dict[str, dict[str, str | None]]:
    """Return each head's source (kind=local|hub, location, revision)."""
    empty = {"kind": None, "location": None, "revision": None}
    if instance is None or not getattr(instance, "sources", None):
        return {name: dict(empty) for name in ("span", "typer", "relation", "classifier", "retriever")}
    return {
        name: {
            "kind": src.kind,
            "location": src.location,
            "revision": src.revision,
        }
        for name, src in instance.sources.items()
    }


@router.get("/api/health/ml_models")
async def ml_models_health() -> dict:
    status: dict = {
        "enabled": ml_pipeline_settings.enabled,
        "device": ml_pipeline_settings.device,
        "models_dir": str(ml_pipeline_settings.models_dir),
        "loaded": False,
        "heads": _head_status(None),
        "sources": _head_sources(None),
        "embedding_dims": None,
        "fingerprint": None,
        "vram_allocated_mb": None,
    }

    if not ml_pipeline_settings.enabled:
        status["note"] = "ml pipeline disabled by startup setting"
        return status

    instance = getattr(_ml_module, "_INSTANCE", None)
    if instance is None:
        status["note"] = "models not yet loaded"
        return status

    status["loaded"] = models_available()
    status["any_loaded"] = any_group_available()
    status["device"] = instance.device
    status["heads"] = _head_status(instance)
    status["sources"] = _head_sources(instance)
    status["groups"] = group_status()
    status["embedding_dims"] = instance.embedding_dims
    status["fingerprint"] = instance.fingerprint

    try:
        import torch  # noqa: PLC0415
        if torch.cuda.is_available():
            status["vram_allocated_mb"] = torch.cuda.memory_allocated() / 1e6
    except Exception:
        logger.debug("Could not read CUDA VRAM", exc_info=True)

    return status
