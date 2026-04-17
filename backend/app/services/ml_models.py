"""Singleton loader for the five production ML heads.

Loaded once at application startup via :func:`load_ml_models`. Callers fetch
the live instance with :func:`get_ml_models`; loading is guarded with
double-checked locking and the load itself stages every model into a private
dict before committing them on ``self`` so a partial failure leaves the
instance in a clean "not loaded" state.

Each head can come from a local path under ``ml_pipeline_settings.models_dir``
or a HuggingFace Hub repo via ``hub_*_repo`` + ``hub_*_revision``. The Hub
wins when set; otherwise we fall back to the local path. This keeps dev
loops on local checkpoints while production can rely on versioned Hub pulls.

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import ml_pipeline_settings

logger = logging.getLogger(__name__)


_INSTANCE: "MLModels | None" = None
_LOCK = threading.Lock()


@dataclass(frozen=True)
class HeadSource:
    """Where a single ML head is sourced from.

    ``kind`` is ``"local"`` or ``"hub"``. For ``"local"``, ``location`` is a
    filesystem path. For ``"hub"``, ``location`` is a repo ID like
    ``user/darkmem-span-v1`` and ``revision`` pins a branch or SHA.
    """

    kind: str
    location: str
    revision: str | None = None

    @property
    def display(self) -> str:
        if self.kind == "hub":
            return f"hub:{self.location}@{self.revision or 'main'}"
        return f"local:{self.location}"

    @property
    def identifier(self) -> str:
        """A stable, compact identifier for use in fingerprints."""
        if self.kind == "hub":
            rev = self.revision or "main"
            suffix = "" if rev == "main" else f"@{rev[:12]}"
            return f"{self.location}{suffix}"
        return Path(self.location).name


def _resolve_source(local_subpath: str, hub_repo: str | None, hub_revision: str) -> HeadSource:
    if hub_repo:
        return HeadSource(kind="hub", location=hub_repo, revision=hub_revision)
    local_path = ml_pipeline_settings.models_dir / local_subpath
    return HeadSource(kind="local", location=str(local_path))


def _hf_kwargs(source: HeadSource, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the common ``from_pretrained`` kwargs for a hub-sourced head.

    Local-sourced heads get no extra kwargs beyond whatever the caller passes
    via ``extra``. Hub-sourced heads additionally get ``revision``, ``cache_dir``,
    and ``token`` (if configured).
    """
    kwargs: dict[str, Any] = {}
    if source.kind == "hub":
        if source.revision:
            kwargs["revision"] = source.revision
        if ml_pipeline_settings.hub_cache_dir:
            kwargs["cache_dir"] = str(ml_pipeline_settings.hub_cache_dir)
        if ml_pipeline_settings.hub_token:
            kwargs["token"] = ml_pipeline_settings.hub_token
    if extra:
        kwargs.update(extra)
    return kwargs


def _sentence_transformer_kwargs(source: HeadSource) -> dict[str, Any]:
    """SentenceTransformer uses slightly different kwarg names from transformers."""
    kwargs: dict[str, Any] = {}
    if source.kind == "hub":
        if source.revision:
            kwargs["revision"] = source.revision
        if ml_pipeline_settings.hub_cache_dir:
            kwargs["cache_folder"] = str(ml_pipeline_settings.hub_cache_dir)
        if ml_pipeline_settings.hub_token:
            kwargs["token"] = ml_pipeline_settings.hub_token
    return kwargs


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


def _free_staged(staged: dict[str, Any], device: str) -> None:
    """Release partially loaded models and clear CUDA cache (best-effort)."""
    for key, value in list(staged.items()):
        try:
            del value
        except Exception:
            logger.debug("Could not free staged model %s", key, exc_info=True)
    if device == "cuda":
        try:
            import torch  # noqa: PLC0415
            torch.cuda.empty_cache()
        except Exception:
            logger.debug("cuda.empty_cache failed during staged-free", exc_info=True)


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
        self.sources: dict[str, HeadSource] = {}

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
        allocated GPU tensors are freed before re-raising. Retries are safe
        even if the first attempt OOMs.
        """
        from gliner import GLiNER  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        from transformers import (  # noqa: PLC0415
            AutoModelForSeq2SeqLM,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        staged: dict[str, Any] = {}
        device = self.device

        span_src = _resolve_source(
            "darkmem-span-v1/best",
            ml_pipeline_settings.hub_span_repo,
            ml_pipeline_settings.hub_span_revision,
        )
        typer_src = _resolve_source(
            "darkmem-typer-v1/best",
            ml_pipeline_settings.hub_typer_repo,
            ml_pipeline_settings.hub_typer_revision,
        )
        relation_src = _resolve_source(
            "darkmem-relation-v1/best",
            ml_pipeline_settings.hub_relation_repo,
            ml_pipeline_settings.hub_relation_revision,
        )
        classifier_src = _resolve_source(
            "darkmem-classifier-v1/best",
            ml_pipeline_settings.hub_classifier_repo,
            ml_pipeline_settings.hub_classifier_revision,
        )
        retriever_src = _resolve_source(
            "darkmem-retriever-v1",
            ml_pipeline_settings.hub_retriever_repo,
            ml_pipeline_settings.hub_retriever_revision,
        )
        sources = {
            "span": span_src,
            "typer": typer_src,
            "relation": relation_src,
            "classifier": classifier_src,
            "retriever": retriever_src,
        }

        try:
            logger.info("Loading GLiNER span detector from %s", span_src.display)
            span = GLiNER.from_pretrained(span_src.location, **_hf_kwargs(span_src))
            if device == "cuda":
                span = span.to("cuda")
            staged["span"] = span

            logger.info("Loading ModernBERT typer from %s", typer_src.display)
            typer_kwargs = _hf_kwargs(typer_src, extra={"trust_remote_code": True})
            typer_tok = AutoTokenizer.from_pretrained(typer_src.location, **typer_kwargs)
            typer = AutoModelForSequenceClassification.from_pretrained(typer_src.location, **typer_kwargs)
            if device == "cuda":
                typer = typer.to("cuda")
            _to_inference_mode(typer)
            staged["typer_tok"] = typer_tok
            staged["typer"] = typer

            logger.info("Loading REBEL relation extractor from %s", relation_src.display)
            relation_kwargs = _hf_kwargs(relation_src)
            relation_tok = AutoTokenizer.from_pretrained(relation_src.location, **relation_kwargs)
            relation = AutoModelForSeq2SeqLM.from_pretrained(relation_src.location, **relation_kwargs)
            if device == "cuda":
                relation = relation.to("cuda")
            _to_inference_mode(relation)
            staged["relation_tok"] = relation_tok
            staged["relation"] = relation

            logger.info("Loading ModernBERT classifier from %s", classifier_src.display)
            classifier_kwargs = _hf_kwargs(classifier_src, extra={"trust_remote_code": True})
            classifier_tok = AutoTokenizer.from_pretrained(classifier_src.location, **classifier_kwargs)
            classifier = AutoModelForSequenceClassification.from_pretrained(classifier_src.location, **classifier_kwargs)
            if device == "cuda":
                classifier = classifier.to("cuda")
            _to_inference_mode(classifier)
            staged["classifier_tok"] = classifier_tok
            staged["classifier"] = classifier

            logger.info("Loading bge retriever from %s", retriever_src.display)
            retriever = SentenceTransformer(
                retriever_src.location,
                device=device,
                **_sentence_transformer_kwargs(retriever_src),
            )
            staged["retriever"] = retriever
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_all failed: {exc}") from exc

        try:
            probe = staged["retriever"].encode(
                ml_pipeline_settings.retriever_query_prefix + "dimension probe",
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            embedding_dims = int(probe.shape[-1])
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_all probe failed: {exc}") from exc

        self.span = staged["span"]
        self.typer_tok = staged["typer_tok"]
        self.typer = staged["typer"]
        self.relation_tok = staged["relation_tok"]
        self.relation = staged["relation"]
        self.classifier_tok = staged["classifier_tok"]
        self.classifier = staged["classifier"]
        self.retriever = staged["retriever"]
        self.embedding_dims = embedding_dims
        self.sources = sources
        self.fingerprint = f"{retriever_src.identifier}|{embedding_dims}"
        logger.info(
            "MLModels.load_all complete: device=%s embedding_dims=%d fingerprint=%s",
            device, embedding_dims, self.fingerprint,
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
