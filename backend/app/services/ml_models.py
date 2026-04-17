"""Singleton loader for the five production ML heads.

Loaded once at application startup via :func:`load_ml_models`. Callers fetch
the live instance with :func:`get_ml_models`; loading is guarded with
double-checked locking and the load itself stages every model into a private
dict before committing them on ``self`` so a partial failure leaves the
instance in a clean "not loaded" state.

Models (see ``fine-tuning/models/PRODUCTION.md``):

  * ``darkmem-span-v1``       — GLiNER single-label span detector
  * ``darkmem-typer-v1``      — ModernBERT 10-class typer (``[ENT]…[/ENT]`` markers)
  * ``darkmem-relation-v1``   — rebel-large seq2seq, 30 types collapsed to 10 via REL_MAP
  * ``darkmem-classifier-v1`` — ModernBERT 7-class memory-type classifier
  * ``darkmem-retriever-v1``  — bge-base-en-v1.5 contrastively fine-tuned
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.config import ml_pipeline_settings

logger = logging.getLogger(__name__)


_INSTANCE: "MLModels | None" = None
_LOCK = threading.Lock()


def _resolve_device(requested: str) -> str:
    """Translate a requested device setting ('cuda'/'cpu'/'auto') to a concrete value."""
    if requested == "cpu":
        return "cpu"
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:
        logger.warning("torch not importable, falling back to CPU: %s", exc)
        return "cpu"

    has_cuda = bool(getattr(torch, "cuda", None)) and torch.cuda.is_available()
    if requested == "cuda":
        return "cuda" if has_cuda else "cpu"
    return "cuda" if has_cuda else "cpu"


def _to_inference_mode(model: Any) -> None:
    """Switch a torch nn.Module out of training mode without using the reserved name ``eval``."""
    if hasattr(model, "train"):
        model.train(False)


class MLModels:
    """Holds the five fine-tuned heads plus tokenizers and a model fingerprint.

    Fields are ``None`` before :meth:`load_all` succeeds so callers can always
    introspect an instance safely.
    """

    def __init__(self, device: str, models_dir: Path):
        self.device = device
        self.models_dir = models_dir
        self.span: Any = None
        self.typer_tok: Any = None
        self.typer: Any = None
        self.relation_tok: Any = None
        self.relation: Any = None
        self.classifier_tok: Any = None
        self.classifier: Any = None
        self.retriever: Any = None
        self.embedding_dims: int | None = None
        self.fingerprint: str = ""

    @property
    def loaded(self) -> bool:
        return all(
            x is not None
            for x in (
                self.span,
                self.typer,
                self.typer_tok,
                self.relation,
                self.relation_tok,
                self.classifier,
                self.classifier_tok,
                self.retriever,
            )
        )

    def load_all(self) -> None:
        """Load every head into memory atomically.

        On any failure the ``self.*`` slots remain ``None`` and any partially
        allocated GPU tensors are freed before re-raising. This makes retries
        safe even if the first attempt OOMs.
        """
        import torch  # noqa: PLC0415
        from gliner import GLiNER  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        from transformers import (  # noqa: PLC0415
            AutoModelForSeq2SeqLM,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        staged: dict[str, Any] = {}
        mdir = self.models_dir
        device = self.device

        try:
            span_path = mdir / "darkmem-span-v1" / "best"
            logger.info("Loading GLiNER span detector from %s", span_path)
            span = GLiNER.from_pretrained(str(span_path))
            if device == "cuda":
                span = span.to("cuda")
            staged["span"] = span

            typer_path = mdir / "darkmem-typer-v1" / "best"
            logger.info("Loading ModernBERT typer from %s", typer_path)
            typer_tok = AutoTokenizer.from_pretrained(str(typer_path), trust_remote_code=True)
            typer = AutoModelForSequenceClassification.from_pretrained(str(typer_path), trust_remote_code=True)
            if device == "cuda":
                typer = typer.to("cuda")
            _to_inference_mode(typer)
            staged["typer_tok"] = typer_tok
            staged["typer"] = typer

            relation_path = mdir / "darkmem-relation-v1" / "best"
            logger.info("Loading REBEL relation extractor from %s", relation_path)
            relation_tok = AutoTokenizer.from_pretrained(str(relation_path))
            relation = AutoModelForSeq2SeqLM.from_pretrained(str(relation_path))
            if device == "cuda":
                relation = relation.to("cuda")
            _to_inference_mode(relation)
            staged["relation_tok"] = relation_tok
            staged["relation"] = relation

            classifier_path = mdir / "darkmem-classifier-v1" / "best"
            logger.info("Loading ModernBERT classifier from %s", classifier_path)
            classifier_tok = AutoTokenizer.from_pretrained(str(classifier_path), trust_remote_code=True)
            classifier = AutoModelForSequenceClassification.from_pretrained(str(classifier_path), trust_remote_code=True)
            if device == "cuda":
                classifier = classifier.to("cuda")
            _to_inference_mode(classifier)
            staged["classifier_tok"] = classifier_tok
            staged["classifier"] = classifier

            retriever_path = mdir / "darkmem-retriever-v1"
            logger.info("Loading bge retriever from %s", retriever_path)
            retriever = SentenceTransformer(str(retriever_path), device=device)
            staged["retriever"] = retriever
        except Exception as exc:
            for key, value in list(staged.items()):
                try:
                    del value
                except Exception:
                    logger.debug("Could not free staged model %s", key, exc_info=True)
            if device == "cuda":
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    logger.debug("cuda.empty_cache failed after partial load", exc_info=True)
            raise RuntimeError(f"MLModels.load_all failed: {exc}") from exc

        self.span = staged["span"]
        self.typer_tok = staged["typer_tok"]
        self.typer = staged["typer"]
        self.relation_tok = staged["relation_tok"]
        self.relation = staged["relation"]
        self.classifier_tok = staged["classifier_tok"]
        self.classifier = staged["classifier"]
        self.retriever = staged["retriever"]

        try:
            probe = staged["retriever"].encode(
                ml_pipeline_settings.retriever_query_prefix + "dimension probe",
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            self.embedding_dims = int(probe.shape[-1])
        except Exception:
            logger.warning("Could not probe retriever embedding dims", exc_info=True)
            self.embedding_dims = None

        self.fingerprint = f"darkmem-retriever-v1|{self.embedding_dims or 'unknown'}"
        logger.info(
            "MLModels.load_all complete: device=%s embedding_dims=%s fingerprint=%s",
            device, self.embedding_dims, self.fingerprint,
        )


def load_ml_models(force: bool = False) -> MLModels:
    """Ensure the singleton is loaded and return it.

    If ``force`` is true the existing instance is discarded and reloaded. The
    requested device from :data:`ml_pipeline_settings` is resolved, with an
    automatic CPU fallback if a CUDA load fails and ``cpu_fallback`` is true.
    """
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is not None and _INSTANCE.loaded and not force:
            return _INSTANCE

        device = _resolve_device(ml_pipeline_settings.device)
        candidate = MLModels(device=device, models_dir=ml_pipeline_settings.models_dir)
        try:
            candidate.load_all()
        except Exception as exc:
            if device == "cuda" and ml_pipeline_settings.cpu_fallback:
                logger.warning("CUDA load failed, retrying on CPU: %s", exc)
                candidate = MLModels(device="cpu", models_dir=ml_pipeline_settings.models_dir)
                candidate.load_all()
            else:
                raise

        _INSTANCE = candidate
        return _INSTANCE


def get_ml_models() -> MLModels:
    """Return the loaded singleton. Raises if :func:`load_ml_models` has not run."""
    if _INSTANCE is None or not _INSTANCE.loaded:
        raise RuntimeError(
            "MLModels singleton not loaded. Call load_ml_models() at application startup."
        )
    return _INSTANCE


def models_available() -> bool:
    """Return True if the singleton is loaded and usable. Never raises."""
    return _INSTANCE is not None and _INSTANCE.loaded


def reset_ml_models() -> None:
    """Test hook: drop the cached instance so the next access reloads."""
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
