"""Lazy loader for the five production ML heads.

Three logical groups map to the pipeline stages:

  * ``extraction`` — GLiNER span detector + ModernBERT typer + REBEL relation head
  * ``classification`` — ModernBERT memory-type classifier
  * ``retriever`` — bge-base contrastive embedder

Each group loads on first use via ``ensure_extraction_loaded`` /
``ensure_classification_loaded`` / ``ensure_retriever_loaded``, and the
eviction task can drop any group that has been idle longer than
``ml_idle_ttl_minutes``.

Head source selection (local path vs HuggingFace Hub) is unchanged.
"""

from __future__ import annotations

import logging
import threading
import time
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
    """Build the common ``from_pretrained`` kwargs for a hub-sourced head."""
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


def _resolve_device(requested: str, cuda_index: int | None = None) -> str:
    """Translate a requested device setting to a concrete torch device string.

    Accepts ``"cpu"``, ``"cuda"``, ``"auto"`` or an explicit ``"cuda:N"``. When
    the caller picks a ``"cuda"``-family device and CUDA is available, the
    returned string is always ``"cuda:<index>"`` so model loading and tensor
    transfers can target a specific GPU on multi-GPU hosts.
    """
    if requested == "cpu":
        return "cpu"
    try:
        import torch  # noqa: PLC0415
    except Exception as exc:
        logger.warning("torch not importable, falling back to CPU: %s", exc)
        return "cpu"

    has_cuda = bool(getattr(torch, "cuda", None)) and torch.cuda.is_available()
    if not has_cuda:
        return "cpu"

    if isinstance(requested, str) and requested.startswith("cuda:"):
        try:
            cuda_index = int(requested.split(":", 1)[1])
        except ValueError:
            cuda_index = cuda_index if cuda_index is not None else 0

    if cuda_index is None or cuda_index < 0:
        cuda_index = 0
    device_count = torch.cuda.device_count()
    if device_count <= 0:
        return "cpu"
    if cuda_index >= device_count:
        logger.warning(
            "cuda_index=%d out of range (device_count=%d); falling back to cuda:0",
            cuda_index, device_count,
        )
        cuda_index = 0
    return f"cuda:{cuda_index}"


def list_available_devices() -> list[dict]:
    """Return the set of devices the ML pipeline can currently target."""
    devices: list[dict] = [{"id": "cpu", "label": "CPU", "kind": "cpu", "index": None}]
    try:
        import torch  # noqa: PLC0415
        if bool(getattr(torch, "cuda", None)) and torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                try:
                    name = torch.cuda.get_device_name(i)
                except Exception:
                    name = f"cuda:{i}"
                devices.append({
                    "id": f"cuda:{i}",
                    "label": f"{name} (cuda:{i})",
                    "kind": "cuda",
                    "index": i,
                })
    except Exception:
        pass
    return devices


def _to_inference_mode(model: Any) -> None:
    """Switch a torch nn.Module out of training mode."""
    if hasattr(model, "train"):
        model.train(False)


def _free_staged(staged: dict[str, Any], device: str) -> None:
    """Release partially loaded models and clear CUDA cache (best-effort)."""
    for key, value in list(staged.items()):
        try:
            del value
        except Exception:
            logger.debug("Could not free staged model %s", key, exc_info=True)
    if device.startswith("cuda"):
        try:
            import torch  # noqa: PLC0415
            torch.cuda.empty_cache()
        except Exception:
            logger.debug("cuda.empty_cache failed during staged-free", exc_info=True)


GROUPS = ("extraction", "classification", "retriever")


class MLModels:
    """Holds the production ML heads with per-group lazy loading.

    Groups load on demand via ``load_extraction`` / ``load_classification`` /
    ``load_retriever``. Each loader is atomic: partial failures free any
    staged tensors before re-raising, so a crashed load leaves the instance
    in a clean "not loaded" state for that group without affecting the others.
    Unloaders drop references and empty the CUDA cache.
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

    # -- loaded-state properties ------------------------------------------

    @property
    def extraction_loaded(self) -> bool:
        return all(
            x is not None
            for x in (self.span, self.typer, self.typer_tok, self.relation, self.relation_tok)
        )

    @property
    def classification_loaded(self) -> bool:
        return self.classifier is not None and self.classifier_tok is not None

    @property
    def retriever_loaded(self) -> bool:
        return self.retriever is not None

    @property
    def loaded(self) -> bool:
        """True iff all three groups are loaded."""
        return self.extraction_loaded and self.classification_loaded and self.retriever_loaded

    def group_loaded(self, group: str) -> bool:
        if group == "extraction":
            return self.extraction_loaded
        if group == "classification":
            return self.classification_loaded
        if group == "retriever":
            return self.retriever_loaded
        return False

    # -- per-group loaders -------------------------------------------------

    def load_extraction(self) -> None:
        """Stage and commit span + typer + relation. Idempotent."""
        if self.extraction_loaded:
            return
        from gliner import GLiNER  # noqa: PLC0415
        from transformers import (  # noqa: PLC0415
            AutoModelForSeq2SeqLM,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        device = self.device
        staged: dict[str, Any] = {}

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
            # rebel-base-v1 shipping path (see fine-tuning/models/PRODUCTION.md).
            # The large variant lives at ``darkmem-relation-v1/best`` and can be
            # opted into via ``ML_PIPELINE_HUB_RELATION_REPO`` for fat-GPU hosts.
            "darkmem-relation-base-v1/best",
            ml_pipeline_settings.hub_relation_repo,
            ml_pipeline_settings.hub_relation_revision,
        )
        try:
            logger.info("Loading GLiNER span detector from %s", span_src.display)
            span = GLiNER.from_pretrained(span_src.location, **_hf_kwargs(span_src))
            if device.startswith("cuda"):
                span = span.to(device)
            staged["span"] = span

            logger.info("Loading ModernBERT typer from %s", typer_src.display)
            typer_kwargs = _hf_kwargs(typer_src, extra={"trust_remote_code": True})
            typer_tok = AutoTokenizer.from_pretrained(typer_src.location, **typer_kwargs)
            typer = AutoModelForSequenceClassification.from_pretrained(typer_src.location, **typer_kwargs)
            if device.startswith("cuda"):
                typer = typer.to(device)
            _to_inference_mode(typer)
            staged["typer_tok"] = typer_tok
            staged["typer"] = typer

            logger.info("Loading REBEL relation extractor from %s", relation_src.display)
            relation_kwargs = _hf_kwargs(relation_src)
            relation_tok = AutoTokenizer.from_pretrained(relation_src.location, **relation_kwargs)
            relation = AutoModelForSeq2SeqLM.from_pretrained(relation_src.location, **relation_kwargs)
            if device.startswith("cuda"):
                relation = relation.to(device)
            _to_inference_mode(relation)
            staged["relation_tok"] = relation_tok
            staged["relation"] = relation
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_extraction failed: {exc}") from exc

        self.span = staged["span"]
        self.typer_tok = staged["typer_tok"]
        self.typer = staged["typer"]
        self.relation_tok = staged["relation_tok"]
        self.relation = staged["relation"]
        self.sources["span"] = span_src
        self.sources["typer"] = typer_src
        self.sources["relation"] = relation_src
        logger.info("MLModels.load_extraction complete on device=%s", device)

    def load_classification(self) -> None:
        """Stage and commit the memory-type classifier. Idempotent."""
        if self.classification_loaded:
            return
        from transformers import (  # noqa: PLC0415
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        device = self.device
        staged: dict[str, Any] = {}
        classifier_src = _resolve_source(
            "darkmem-classifier-v1/best",
            ml_pipeline_settings.hub_classifier_repo,
            ml_pipeline_settings.hub_classifier_revision,
        )
        try:
            logger.info("Loading ModernBERT classifier from %s", classifier_src.display)
            classifier_kwargs = _hf_kwargs(classifier_src, extra={"trust_remote_code": True})
            classifier_tok = AutoTokenizer.from_pretrained(classifier_src.location, **classifier_kwargs)
            classifier = AutoModelForSequenceClassification.from_pretrained(
                classifier_src.location, **classifier_kwargs,
            )
            if device.startswith("cuda"):
                classifier = classifier.to(device)
            _to_inference_mode(classifier)
            staged["classifier_tok"] = classifier_tok
            staged["classifier"] = classifier
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_classification failed: {exc}") from exc

        self.classifier_tok = staged["classifier_tok"]
        self.classifier = staged["classifier"]
        self.sources["classifier"] = classifier_src
        logger.info("MLModels.load_classification complete on device=%s", device)

    def load_retriever(self) -> None:
        """Stage the bge retriever + seed embedding_dims and fingerprint. Idempotent."""
        if self.retriever_loaded:
            return
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        device = self.device
        staged: dict[str, Any] = {}
        retriever_src = _resolve_source(
            "darkmem-retriever-v1",
            ml_pipeline_settings.hub_retriever_repo,
            ml_pipeline_settings.hub_retriever_revision,
        )
        try:
            logger.info("Loading bge retriever from %s", retriever_src.display)
            retriever = SentenceTransformer(
                retriever_src.location,
                device=device,
                **_sentence_transformer_kwargs(retriever_src),
            )
            staged["retriever"] = retriever
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_retriever failed: {exc}") from exc

        try:
            probe = staged["retriever"].encode(
                ml_pipeline_settings.retriever_query_prefix + "dimension probe",
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            embedding_dims = int(probe.shape[-1])
        except Exception as exc:
            _free_staged(staged, device)
            raise RuntimeError(f"MLModels.load_retriever probe failed: {exc}") from exc

        self.retriever = staged["retriever"]
        self.embedding_dims = embedding_dims
        self.sources["retriever"] = retriever_src
        self.fingerprint = f"{retriever_src.identifier}|{embedding_dims}"
        logger.info(
            "MLModels.load_retriever complete: device=%s embedding_dims=%d fingerprint=%s",
            device, embedding_dims, self.fingerprint,
        )

    def load_all(self) -> None:
        """Eagerly load every group. Retained for tooling and tests."""
        self.load_extraction()
        self.load_classification()
        self.load_retriever()

    # -- per-group unloaders ----------------------------------------------

    def unload_extraction(self) -> None:
        if self.span is None and self.typer is None and self.relation is None:
            return
        logger.info("Unloading extraction group (span + typer + relation)")
        self.span = None
        self.typer = None
        self.typer_tok = None
        self.relation = None
        self.relation_tok = None
        self._maybe_empty_cuda_cache()

    def unload_classification(self) -> None:
        if self.classifier is None and self.classifier_tok is None:
            return
        logger.info("Unloading classification group (classifier)")
        self.classifier = None
        self.classifier_tok = None
        self._maybe_empty_cuda_cache()

    def unload_retriever(self) -> None:
        if self.retriever is None:
            return
        logger.info("Unloading retriever group")
        self.retriever = None
        # Keep embedding_dims and fingerprint so obsolete-count calculations
        # are stable across idle cycles.
        self._maybe_empty_cuda_cache()

    def unload_all(self) -> None:
        self.unload_extraction()
        self.unload_classification()
        self.unload_retriever()

    def _maybe_empty_cuda_cache(self) -> None:
        if self.device.startswith("cuda"):
            try:
                import torch  # noqa: PLC0415
                torch.cuda.empty_cache()
            except Exception:
                logger.debug("torch.cuda.empty_cache failed during unload", exc_info=True)


# ---------------------------------------------------------------------------
# Module-level lazy-load + eviction state
# ---------------------------------------------------------------------------

_GROUP_LOCKS: dict[str, threading.Lock] = {g: threading.Lock() for g in GROUPS}
_GROUP_LAST_ACCESS: dict[str, float] = {g: 0.0 for g in GROUPS}


def _now() -> float:
    return time.monotonic()


def _instance_shell() -> "MLModels":
    """Return the singleton shell, creating it if absent. No heads loaded."""
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is None:
            device = _resolve_device(ml_pipeline_settings.device, None)
            _INSTANCE = MLModels(device=device, models_dir=ml_pipeline_settings.models_dir)
        return _INSTANCE


def _bump(group: str) -> None:
    _GROUP_LAST_ACCESS[group] = _now()


def ensure_extraction_loaded() -> "MLModels":
    """Lazy-load the extraction group and bump its last-access timestamp."""
    ml = _instance_shell()
    with _GROUP_LOCKS["extraction"]:
        if not ml.extraction_loaded:
            try:
                ml.load_extraction()
            except Exception as exc:
                if ml.device.startswith("cuda") and ml_pipeline_settings.cpu_fallback:
                    logger.warning("load_extraction CUDA failed, retrying on CPU: %s", exc)
                    ml.device = "cpu"
                    ml.load_extraction()
                else:
                    raise
    _bump("extraction")
    return ml


def ensure_classification_loaded() -> "MLModels":
    ml = _instance_shell()
    with _GROUP_LOCKS["classification"]:
        if not ml.classification_loaded:
            try:
                ml.load_classification()
            except Exception as exc:
                if ml.device.startswith("cuda") and ml_pipeline_settings.cpu_fallback:
                    logger.warning("load_classification CUDA failed, retrying on CPU: %s", exc)
                    ml.device = "cpu"
                    ml.load_classification()
                else:
                    raise
    _bump("classification")
    return ml


def ensure_retriever_loaded() -> "MLModels":
    ml = _instance_shell()
    with _GROUP_LOCKS["retriever"]:
        if not ml.retriever_loaded:
            try:
                ml.load_retriever()
            except Exception as exc:
                if ml.device.startswith("cuda") and ml_pipeline_settings.cpu_fallback:
                    logger.warning("load_retriever CUDA failed, retrying on CPU: %s", exc)
                    ml.device = "cpu"
                    ml.load_retriever()
                else:
                    raise
    _bump("retriever")
    return ml


def evict_idle(ttl_seconds: float) -> list[str]:
    """Unload every group whose last access is older than ``ttl_seconds``.

    ``ttl_seconds <= 0`` disables eviction entirely.

    Returns the list of group names that were evicted so callers can log.
    """
    if ttl_seconds <= 0:
        return []
    ml = _INSTANCE
    if ml is None:
        return []

    now = _now()
    evicted: list[str] = []
    for group in GROUPS:
        last = _GROUP_LAST_ACCESS.get(group, 0.0)
        if last <= 0:
            continue
        if (now - last) <= ttl_seconds:
            continue
        with _GROUP_LOCKS[group]:
            if group == "extraction" and ml.extraction_loaded:
                ml.unload_extraction()
                evicted.append(group)
            elif group == "classification" and ml.classification_loaded:
                ml.unload_classification()
                evicted.append(group)
            elif group == "retriever" and ml.retriever_loaded:
                ml.unload_retriever()
                evicted.append(group)
            _GROUP_LAST_ACCESS[group] = 0.0
    return evicted


def group_status() -> dict[str, dict]:
    """Snapshot of per-group load state + idle seconds for the UI/status endpoint."""
    ml = _INSTANCE
    now = _now()
    out: dict[str, dict] = {}
    for group in GROUPS:
        last = _GROUP_LAST_ACCESS.get(group, 0.0)
        idle = None
        if last > 0:
            idle = max(0, int(now - last))
        loaded = False
        if ml is not None:
            loaded = bool(getattr(ml, f"{group}_loaded", False))
        out[group] = {"loaded": loaded, "idle_seconds": idle}
    return out


# ---------------------------------------------------------------------------
# Back-compat surface
# ---------------------------------------------------------------------------

def load_ml_models(
    force: bool = False,
    device_override: str | None = None,
    cuda_index_override: int | None = None,
) -> "MLModels":
    """Ensure every group is loaded on the singleton and return it.

    Kept for the ML-device apply flow and for tests that want eager loading.
    In production the lazy ``ensure_*_loaded`` entry points are preferred.
    """
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is not None and _INSTANCE.loaded and not force:
            return _INSTANCE

        requested = device_override or ml_pipeline_settings.device
        device = _resolve_device(requested, cuda_index_override)
        candidate = MLModels(device=device, models_dir=ml_pipeline_settings.models_dir)
        try:
            candidate.load_all()
        except Exception as exc:
            if device.startswith("cuda") and ml_pipeline_settings.cpu_fallback:
                logger.warning("CUDA load failed, retrying on CPU: %s", exc)
                candidate = MLModels(device="cpu", models_dir=ml_pipeline_settings.models_dir)
                candidate.load_all()
            else:
                raise

        _INSTANCE = candidate
        now = _now()
        for g in GROUPS:
            _GROUP_LAST_ACCESS[g] = now
        return _INSTANCE


def reload_ml_models(
    device: str | None = None,
    cuda_index: int | None = None,
) -> "MLModels":
    """Force-reload the singleton on a specific device at runtime.

    Used by the ``PUT /config/ml-device`` endpoint after the UI switches
    between CPU / CUDA or between GPUs. Releases the previous instance and
    eagerly reloads every group on the new device so the reload is visible
    to callers immediately.
    """
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is not None:
            try:
                _INSTANCE.unload_all()
            except Exception:
                logger.debug("unload_all failed during reload", exc_info=True)
        _INSTANCE = None
        for g in GROUPS:
            _GROUP_LAST_ACCESS[g] = 0.0
    return load_ml_models(
        force=True,
        device_override=device,
        cuda_index_override=cuda_index,
    )


def get_ml_models() -> "MLModels":
    """Return the live singleton.

    Raises ``RuntimeError`` if no heads have been loaded yet. Hot paths should
    call ``ensure_<group>_loaded()`` before ``get_ml_models()``.
    """
    if _INSTANCE is None:
        raise RuntimeError(
            "MLModels singleton not initialised. Call ensure_*_loaded() or load_ml_models()."
        )
    return _INSTANCE


def models_available() -> bool:
    """Backward-compatible check: true iff all three groups are loaded."""
    return _INSTANCE is not None and _INSTANCE.loaded


def any_group_available() -> bool:
    """Looser check: true if at least one group is loaded on the singleton."""
    return _INSTANCE is not None and (
        _INSTANCE.extraction_loaded
        or _INSTANCE.classification_loaded
        or _INSTANCE.retriever_loaded
    )


def reset_ml_models() -> None:
    """Test hook: drop the cached instance so the next access reloads."""
    global _INSTANCE
    with _LOCK:
        _INSTANCE = None
        for g in GROUPS:
            _GROUP_LAST_ACCESS[g] = 0.0


def unload_group(name: str) -> None:
    if name not in GROUPS:
        raise ValueError(f"unknown ml group: {name!r}")
    ml = _INSTANCE
    if ml is None:
        return
    with _GROUP_LOCKS[name]:
        if getattr(ml, f"{name}_loaded"):
            getattr(ml, f"unload_{name}")()
        _GROUP_LAST_ACCESS[name] = 0.0
