# darkmem extraction pipeline integration plan — v2

Last updated: 2026-04-17
Supersedes: `INTEGRATION_PLAN.md` (v1)

Rewrite of v1 after reading the actual backend files. v1 had unverified assumptions about `hybrid_search.py`, `extraction.py`, the feature-flag system, the config layout, and the embedding dimensions. v2 is grounded in real extension points.

## What v1 got wrong

1. **Embedding dimension mismatch.** Current default is **1024 dims** (`nomic-embed-text`); `darkmem-retriever-v1` is **bge-base at 768 dims**. The pgvector columns are sized to 1024. Swapping the retriever is a schema-breaking change that requires either re-embedding everything or picking a different retriever checkpoint.
2. **Extraction is called via `ProcessingPipeline`, not `extraction.py` directly.** The top-level orchestrator is `app/services/pipeline.py::ProcessingPipeline`. It holds an `ExtractionService(llm)` and a `ClassificationService(llm)` plus the regex `memory_classifier.classify`. We wire the new heads at the pipeline layer, not below.
3. **`hybrid_search.py` calls `self.llm.embed()` directly.** Not pluggable. To swap embedders we either route through `LLMOrchestrator` (make embed() dispatch between ollama and the fine-tuned retriever) or pass a separate embedder function into `HybridSearchService`.
4. **Feature flags live in the DB**, not env vars. `Config` model with key `feature_flags`, merged against `FEATURE_FLAGS_DEFAULTS` in `app/config.py`. Runtime-toggleable, which is good.
5. **Config is `app/config.py`, not `app/config/`.** Single file.
6. **`LLMOrchestrator` is fully async** (httpx.AsyncClient). Our ML inference is synchronous and GPU-bound. Integration needs `asyncio.to_thread()` wrapping or a dedicated worker queue.
7. **Pipeline has an embedding cache** keyed by `embedding_fingerprint = f"{model}|{dims}"`. Swapping the embedder invalidates every cached vector; cache busts itself naturally by fingerprint, but stored embeddings in the DB still reference the old model.

## Decision: retriever stays on bge-large, not bge-base

Given the 1024-dim schema constraint, the production retriever should be **bge-large-7500clean-hn-ep5-b16** (1024 dims, MRR 0.895, 1,342 MB VRAM) instead of **bge-base-7500clean-hn** (768 dims, MRR 0.884, 439 MB VRAM).

Trade-offs:
- +0.011 MRR (actually better than bge-base on our test)
- +900 MB VRAM vs bge-base
- No schema migration needed; drops in as a replacement for `nomic-embed-text`
- Still fits the 4-head budget: `619 + 1342 + 613 + 618 + 1625 = 4,817 MB` for the heads + `~3,000 MB` qwen3.5:4b + CUDA overhead × 2 contexts ≈ `~8,000 MB` on the 8,151 MB card.

Cost: ~50 MB of real headroom under concurrent load. **This is tight.** If it proves too tight in production, fall back to bge-base with a 1024→768 schema migration done in one maintenance window.

Action item: rename `_experiments/retriever-bge-large-7500clean-hn-ep5-b16` → `darkmem-retriever-v1` (replacing the current bge-base pick). Update `PRODUCTION.md`.

## Real integration points

```
backend/app/main.py (lifespan)
    └── ProcessingPipeline(llm, session_factory, embedding_dims, broadcast)
         ├── self.llm                       = LLMOrchestrator        (ollama, unchanged)
         ├── self.extraction                = ExtractionService(llm) ← REPLACE
         ├── self.classification            = ClassificationService(llm) ← REPLACE
         └── (indirectly) memory_classifier.classify                 ← KEEP as fallback

backend/app/services/hybrid_search.py
    └── HybridSearchService(llm, session, embedding_dims)
         └── self.llm.embed(query) ← ROUTE through LLMOrchestrator to the ML retriever
```

**No replacement of `main.py` lifespan logic needed.** We extend it. No replacement of `pipeline.py`'s outer structure; we swap the services it holds.

## Files to create

### 1. `backend/app/config.py` — extend existing file

Add below the existing `Settings` class:

```python
# ML pipeline settings
class MLPipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = True  # master switch; falls back to LLM path if False
    models_dir: Path = Path("/opt/darkmem/models")  # override with DARKMEM_MODELS_DIR
    device: str = "cuda"  # 'cuda' | 'cpu'
    cpu_fallback: bool = True  # if CUDA init fails, log warning and use CPU
    inference_concurrency: int = 4  # semaphore-bounded concurrent GPU ops
    span_threshold: float = 0.5
    nms_iou: float = 0.3
    rebel_num_beams: int = 4
    rebel_max_source_tokens: int = 256
    rebel_max_target_tokens: int = 128
    long_text_chunk_tokens: int = 200  # chunk inputs above this
    long_text_chunk_overlap: int = 40
    inference_timeout_ms: int = 10_000  # per-call hard timeout
```

Keep a `ml_pipeline_settings = MLPipelineSettings()` singleton next to `settings = Settings()`.

### 2. `backend/app/config/taxonomy.py` — NEW DIRECTORY + module

Currently `app/config.py` is a single file. Introduce `app/config/` as a package. Move `config.py` content into `app/config/__init__.py`, then add:

- `app/config/taxonomy.py`:

```python
ENTITY_TYPES = [
    "tool", "service", "database", "language", "protocol",
    "project", "algorithm", "artifact", "concept", "entity",
]
RELATION_TYPES = [
    "USES", "DEPENDS_ON", "REPLACES", "IS_A", "HAS_PART",
    "DEPLOYED_ON", "CAUSES", "AUTHORED_BY", "HAPPENED_ON", "RELATED_TO",
]
MEMORY_TYPES = [
    "fact", "decision", "preference", "problem",
    "reference", "architecture", "milestone",
]

# REBEL 30 → 10 post-hoc map (from fine-tuning/scripts/_build_rebel_coding10_splits.py)
REL_MAP: dict[str, str] = {
    "USES": "USES", "CONFIGURES": "USES", "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES", "IMPLEMENTS": "USES",
    "DEPENDS_ON": "DEPENDS_ON",
    "REPLACES": "REPLACES", "IMPROVES_ON": "REPLACES", "BUILDS_ON": "REPLACES",
    "IS_A": "IS_A",
    "HAS_PART": "HAS_PART", "EXTENDS": "HAS_PART",
    "DEPLOYED_ON": "DEPLOYED_ON", "LOCATED_IN": "DEPLOYED_ON",
    "CAUSES": "CAUSES", "PRODUCES": "CAUSES", "FIXES": "CAUSES",
    "AUTHORED_BY": "AUTHORED_BY", "PUBLISHED_IN": "AUTHORED_BY",
    "WORKS_AT": "AUTHORED_BY",
    "HAPPENED_ON": "HAPPENED_ON", "VISITED": "HAPPENED_ON",
    "LIVES_IN": "HAPPENED_ON",
    "RELATED_TO": "RELATED_TO", "KNOWS": "RELATED_TO",
    "SUPPORTS": "RELATED_TO", "CONTRADICTS": "RELATED_TO",
    "PREFERS": "RELATED_TO", "FEELS_ABOUT": "RELATED_TO",
    "PLANS_TO": "RELATED_TO",
}

# Legacy 18-type backend → new 10-type
LEGACY_ENTITY_TYPE_MAP = {
    "person": "entity", "organization": "entity", "team": "entity",
    "technology": "tool", "framework": "tool", "library": "tool",
    "pattern": "tool",
    "service": "service", "platform": "service", "infrastructure": "service",
    "standard": "protocol", "specification": "protocol",
    "concept": "concept", "algorithm": "algorithm", "protocol": "protocol",
    "language": "language", "project": "project", "database": "database",
}
LEGACY_RELATION_TYPE_MAP = {
    "USES": "USES", "DEPENDS_ON": "DEPENDS_ON",
    "IS_A": "IS_A", "HAS_PART": "HAS_PART",
    "IMPLEMENTS": "USES", "REPLACES": "REPLACES",
    "IMPROVES_ON": "REPLACES", "EXTENDS": "HAS_PART",
    "CONFIGURES": "USES", "PRODUCES": "CAUSES",
    "COMMUNICATES_WITH": "USES", "DEPLOYED_ON": "DEPLOYED_ON",
    "ALTERNATIVE_TO": "RELATED_TO", "RELATED_TO": "RELATED_TO",
}
```

### 3. `backend/app/services/ml_models.py` — singleton model holder

```python
"""Singleton loader for the 5 darkmem fine-tuned heads.

Thread-safe lazy init. Supports CPU fallback on CUDA failure.
Loaded at FastAPI startup via main.py lifespan.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

from app.config import ml_pipeline_settings, settings

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_INSTANCE: "MLModels | None" = None


class MLModels:
    def __init__(self, device: str):
        self.device = device
        self.span = None
        self.typer_tok = None
        self.typer = None
        self.relation_tok = None
        self.relation = None
        self.classifier_tok = None
        self.classifier = None
        self.retriever = None
        self.fingerprint = "darkmem-v1|1024"  # for embedding cache key

    def load_all(self) -> None:
        import torch
        from gliner import GLiNER
        from sentence_transformers import SentenceTransformer
        from transformers import (
            AutoModelForSequenceClassification, AutoTokenizer,
            AutoModelForSeq2SeqLM,
        )

        mdir = ml_pipeline_settings.models_dir
        if not mdir.exists():
            raise RuntimeError(f"Models directory not found: {mdir}")

        if self.device == "cuda" and not torch.cuda.is_available():
            if ml_pipeline_settings.cpu_fallback:
                logger.warning("CUDA unavailable; falling back to CPU")
                self.device = "cpu"
            else:
                raise RuntimeError("CUDA requested but unavailable, cpu_fallback=False")

        logger.info(f"loading darkmem ML models on {self.device} from {mdir}")

        self.span = GLiNER.from_pretrained(str(mdir / "darkmem-span-v1" / "best"))
        if self.device == "cuda":
            self.span = self.span.to("cuda")

        tok_path = mdir / "darkmem-typer-v1" / "best"
        self.typer_tok = AutoTokenizer.from_pretrained(str(tok_path), trust_remote_code=True)
        self.typer = AutoModelForSequenceClassification.from_pretrained(str(tok_path), trust_remote_code=True)
        if self.device == "cuda":
            self.typer = self.typer.to("cuda")
        self.typer.train(False)

        rel_path = mdir / "darkmem-relation-v1" / "best"
        self.relation_tok = AutoTokenizer.from_pretrained(str(rel_path))
        self.relation = AutoModelForSeq2SeqLM.from_pretrained(str(rel_path))
        if self.device == "cuda":
            self.relation = self.relation.to("cuda")
        self.relation.train(False)

        cls_path = mdir / "darkmem-classifier-v1" / "best"
        self.classifier_tok = AutoTokenizer.from_pretrained(str(cls_path), trust_remote_code=True)
        self.classifier = AutoModelForSequenceClassification.from_pretrained(str(cls_path), trust_remote_code=True)
        if self.device == "cuda":
            self.classifier = self.classifier.to("cuda")
        self.classifier.train(False)

        self.retriever = SentenceTransformer(str(mdir / "darkmem-retriever-v1"), device=self.device)

        logger.info("darkmem ML models loaded")


def get_ml_models() -> MLModels:
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE
    with _LOCK:
        if _INSTANCE is not None:
            return _INSTANCE
        m = MLModels(ml_pipeline_settings.device)
        m.load_all()
        _INSTANCE = m
        return _INSTANCE


async def get_ml_models_async() -> MLModels:
    """Load models in a worker thread so FastAPI startup isn't blocked by
    the 15-20 s initial load."""
    return await asyncio.to_thread(get_ml_models)
```

### 4. `backend/app/services/extraction_ml.py` — replaces `extraction.py` path

New service class that matches the `ExtractionService` interface (`extract(content, system_prompt=None) -> dict`) so the pipeline can swap between LLM-based and ML-based by feature flag.

```python
"""ML-based extraction service. Matches ExtractionService's interface so
ProcessingPipeline can swap between LLM and ML paths via a feature flag.
"""
from __future__ import annotations

import asyncio
import logging
import re

import torch
import torch.nn.functional as F

from app.config import ml_pipeline_settings
from app.config.taxonomy import ENTITY_TYPES, REL_MAP
from app.services.ml_models import get_ml_models

logger = logging.getLogger(__name__)

_SEMAPHORE = asyncio.Semaphore(ml_pipeline_settings.inference_concurrency)


class ExtractionMLService:
    """Drop-in replacement for ExtractionService, but routes through the ML
    pipeline rather than the LLM orchestrator."""

    async def extract(self, content: str, system_prompt: str | None = None) -> dict:
        """Keeps the same return shape as ExtractionService.extract for
        downstream compatibility: {'entities': [...], 'relationships': [...]}.
        """
        if not content or not content.strip():
            return {"entities": [], "relationships": []}

        async with _SEMAPHORE:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_extract_sync, content),
                    timeout=ml_pipeline_settings.inference_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"ML extraction timeout after {ml_pipeline_settings.inference_timeout_ms}ms "
                    f"(content length {len(content)})"
                )
                return {"entities": [], "relationships": []}
            except Exception as exc:
                logger.exception(f"ML extraction failed: {exc}")
                return {"entities": [], "relationships": []}


def _extract_sync(text: str) -> dict:
    """Synchronous inference. Wrapped by asyncio.to_thread above."""
    ml = get_ml_models()

    # Stage 1 — span detection with NMS
    raw_spans = ml.span.predict_entities(
        text, ["entity"], threshold=ml_pipeline_settings.span_threshold
    )
    raw_spans = _nms_spans(raw_spans, ml_pipeline_settings.nms_iou)

    entities: list[dict] = []
    if raw_spans:
        entities = _type_classify(text, raw_spans, ml)

    relationships: list[dict] = []
    if len(entities) >= 2:
        # REBEL — handle long text via truncation (fine-tuned at 256 tokens)
        relationships = _relation_extract(text, entities, ml)

    return {"entities": entities, "relationships": relationships}


def _nms_spans(spans, iou):
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: -s.get("score", 0.0))
    kept = []
    for s in sorted_spans:
        s_len = max(1, s["end"] - s["start"])
        overlap = False
        for k in kept:
            inter = max(0, min(s["end"], k["end"]) - max(s["start"], k["start"]))
            union = s_len + (k["end"] - k["start"]) - inter
            if union > 0 and inter / union > iou:
                overlap = True
                break
        if not overlap:
            kept.append(s)
    return kept


def _type_classify(text, raw_spans, ml) -> list[dict]:
    marked = [
        text[:s["start"]] + "[ENT]" + text[s["start"]:s["end"]] + "[/ENT]" + text[s["end"]:]
        for s in raw_spans
    ]
    preds: list[int] = []
    scores: list[float] = []
    BATCH = 16
    for i in range(0, len(marked), BATCH):
        chunk = marked[i:i + BATCH]
        enc = ml.typer_tok(chunk, return_tensors="pt", truncation=True, max_length=256, padding=True)
        enc = {k: v.to(ml.device) for k, v in enc.items()}
        with torch.no_grad():
            logits = ml.typer(**enc).logits
        probs = F.softmax(logits, dim=-1)
        top = probs.argmax(dim=-1)
        preds.extend(top.tolist())
        scores.extend(probs.max(dim=-1).values.tolist())

    out = []
    for span, pid, sc in zip(raw_spans, preds, scores):
        out.append({
            "name": text[span["start"]:span["end"]],
            "type": ENTITY_TYPES[pid],
            "start": span["start"],
            "end": span["end"],
            "score": float(sc),
            "properties": {},
        })
    return out


def _relation_extract(text, entities, ml) -> list[dict]:
    ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
    rebel_input = f"{text} | Entities: {ent_str}"

    enc = ml.relation_tok(
        rebel_input, return_tensors="pt", truncation=True,
        max_length=ml_pipeline_settings.rebel_max_source_tokens,
    )
    enc = {k: v.to(ml.device) for k, v in enc.items()}
    with torch.no_grad():
        out = ml.relation.generate(
            **enc,
            max_length=ml_pipeline_settings.rebel_max_target_tokens,
            num_beams=ml_pipeline_settings.rebel_num_beams,
        )
    decoded = ml.relation_tok.decode(out[0], skip_special_tokens=False)

    rels: list[dict] = []
    entity_names = {e["name"] for e in entities}
    for chunk in decoded.split("<triplet>"):
        chunk = chunk.strip()
        if not chunk or chunk == "NONE":
            continue
        a = chunk.split("<subj>")
        if len(a) != 2:
            continue
        source = a[0].strip()
        b = a[1].split("<obj>")
        if len(b) != 2:
            continue
        target = b[0].strip()
        rtype = b[1].strip().split("<")[0].strip()
        if not (source and target and rtype):
            continue
        mapped = REL_MAP.get(rtype)
        if not mapped:
            continue
        if source not in entity_names or target not in entity_names:
            continue  # filter REBEL hallucinations
        rels.append({
            "source": source, "target": target,
            "type": mapped, "properties": {}, "weight": 0.8,
        })
    return rels
```

### 5. `backend/app/services/classification_ml.py` — drop-in for `ClassificationService`

```python
"""ML-based memory classification. Same interface as ClassificationService.classify()."""
from __future__ import annotations

import asyncio
import logging

import torch
import torch.nn.functional as F

from app.config.taxonomy import MEMORY_TYPES
from app.services.ml_models import get_ml_models

logger = logging.getLogger(__name__)


class ClassificationMLService:
    async def classify(
        self,
        content: str,
        enabled_areas: list[str] | None = None,
        system_prompt: str | None = None,
        mode: str = "simple",
    ) -> dict:
        if not content or not content.strip():
            return {"type": "fact", "summary": "", "emotions": [], "flags": []}
        try:
            return await asyncio.to_thread(_classify_sync, content)
        except Exception as exc:
            logger.exception(f"ML classify failed: {exc}")
            return {"type": "fact", "summary": "", "emotions": [], "flags": []}


def _classify_sync(text: str) -> dict:
    ml = get_ml_models()
    enc = ml.classifier_tok(text, return_tensors="pt", truncation=True, max_length=256, padding=False)
    enc = {k: v.to(ml.device) for k, v in enc.items()}
    with torch.no_grad():
        logits = ml.classifier(**enc).logits
    probs = F.softmax(logits, dim=-1)
    top = probs[0].argmax().item()
    return {
        "type": MEMORY_TYPES[top],
        "summary": "",  # summary was previously produced by the LLM; the ML classifier doesn't do this
        "emotions": [],
        "flags": [],
    }
```

**Note on the `summary` field:** the existing `ClassificationService` asks the LLM to produce both a type AND a summary in one call. The ML classifier only predicts type. If summary is required, a small additional LLM call (or a fine-tuned summarizer) can fill it — out of scope for this integration, but flagged.

### 6. Retriever integration — extend `LLMOrchestrator` instead of replacing it

Instead of swapping `hybrid_search.py`'s embedder, extend `LLMOrchestrator` to dispatch `embed()` calls. When the ML pipeline is enabled, `embed()` routes to the fine-tuned retriever. When disabled, it routes to the ollama embedding endpoint as today.

Patch in `backend/app/services/llm.py`:

```python
# at the top of LLMOrchestrator.embed / embed_batch, before the HTTP call:
from app.config import ml_pipeline_settings
if ml_pipeline_settings.enabled:
    from app.services.ml_models import get_ml_models
    ml = get_ml_models()
    # bge query prefix convention
    prefixed = "Represent this sentence for searching relevant passages: " + text
    import asyncio
    emb = await asyncio.to_thread(
        lambda: ml.retriever.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True).tolist()
    )
    return emb
```

This keeps `hybrid_search.py` unchanged and lets the retriever be controlled by the same feature flag as extraction.

## Files to modify

### `backend/app/services/pipeline.py`

`ProcessingPipeline.__init__` currently hard-wires `ExtractionService(llm)` and `ClassificationService(llm)`. Change to feature-flag-driven:

```python
from app.config import ml_pipeline_settings

class ProcessingPipeline:
    def __init__(self, llm, session_factory, embedding_dims, broadcast=None):
        self.llm = llm
        if ml_pipeline_settings.enabled:
            from app.services.extraction_ml import ExtractionMLService
            from app.services.classification_ml import ClassificationMLService
            self.extraction = ExtractionMLService()
            self.classification = ClassificationMLService()
            logger.info("ProcessingPipeline: ML extraction path active")
        else:
            from app.services.extraction import ExtractionService
            from app.services.classification_llm import ClassificationService
            self.extraction = ExtractionService(llm)
            self.classification = ClassificationService(llm)
            logger.info("ProcessingPipeline: LLM extraction path active")
        ...
```

If either service is called via explicit method signatures downstream (e.g. `self.classification.classify(content, enabled_areas=..., system_prompt=...)`), the ML service must match that exact signature. Check every call site in `pipeline.py`. The `ClassificationMLService.classify` above already does this.

### `backend/app/main.py` lifespan

Add model warm-load before pipeline init:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    if ml_pipeline_settings.enabled:
        from app.services.ml_models import get_ml_models_async
        try:
            await get_ml_models_async()
            logger.info("darkmem ML models loaded")
        except Exception as exc:
            logger.exception(f"ML models failed to load: {exc}")
            if not ml_pipeline_settings.cpu_fallback:
                raise
    ...
```

### `backend/app/services/extraction_tools.py`

Keep `_NOISE_NAMES`, `_TRAILING_SUFFIXES`, `_is_acronym_of`, `_FILENAME_PATTERN`, `normalize_entity_type` — they are post-processing helpers used by downstream graph-dedup code and are still useful. Update `ENTITY_TYPES` and `RELATIONSHIP_TYPES` to import from `app.config.taxonomy`:

```python
from app.config.taxonomy import ENTITY_TYPES, RELATION_TYPES as RELATIONSHIP_TYPES, LEGACY_ENTITY_TYPE_MAP
# Keep _ENTITY_TYPE_MAP extended with LEGACY_ENTITY_TYPE_MAP for backwards compat
_ENTITY_TYPE_MAP = {**LEGACY_ENTITY_TYPE_MAP, ...existing llm synonyms...}
```

### DB migration — pgvector schema

Two cases, depending on retriever choice:
- **bge-large (1024 dims)**: no schema change. `embedding` column stays at 1024. `LLMOrchestrator.embed()` now returns 1024-dim vectors from bge-large instead of 1024-dim from nomic. Cache busts automatically via `embedding_fingerprint`.
- **bge-base (768 dims)**: write Alembic migration at `backend/alembic/versions/<timestamp>_resize_embedding_768.py` that:
  1. Creates a new 768-dim column `embedding_v2`.
  2. Backfills by re-embedding all existing memories through the new retriever (batch of 64 per request).
  3. Swaps columns and drops the old one.
  4. Updates `settings.embedding_dimensions = 768` default.

Since bge-large is MRR 0.895 > bge-base 0.884, default to bge-large and skip the migration.

### Legacy entity type migration

`backend/scripts/migrate_entity_types.py`:

```python
"""One-time migration: rename old 18-type entity labels to the new 10-type set."""
import asyncio, logging
from app.database import async_session_factory
from app.repositories.graph import PostgresGraphRepository
from app.config.taxonomy import LEGACY_ENTITY_TYPE_MAP, LEGACY_RELATION_TYPE_MAP

async def main():
    async with async_session_factory() as session:
        repo = PostgresGraphRepository(session)
        # Rename entity types
        for old, new in LEGACY_ENTITY_TYPE_MAP.items():
            if old == new:
                continue
            n = await repo.bulk_rename_entity_type(old, new)  # new repo method
            logging.info(f"entity type {old} -> {new}: {n} rows")
        # Rename relation types
        for old, new in LEGACY_RELATION_TYPE_MAP.items():
            if old == new:
                continue
            n = await repo.bulk_rename_relation_type(old, new)
            logging.info(f"relation type {old} -> {new}: {n} rows")
        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
```

Requires two new methods on `PostgresGraphRepository`: `bulk_rename_entity_type` and `bulk_rename_relation_type`. SQL template: `UPDATE entity_nodes SET type = :new WHERE type = :old`.

## Feature flag wiring

The existing `FEATURE_FLAGS_DEFAULTS` dict in `app/config.py` already has DB-driven runtime-toggleable flags. Add:

```python
FEATURE_FLAGS_DEFAULTS = {
    ...,
    "ml_extraction": False,         # new — flip to True to enable ML extraction path
    "ml_classification": False,     # ML memory classifier (vs LLM-based)
    "ml_retrieval": False,          # ML retriever via LLMOrchestrator.embed
    "ml_shadow_mode": False,        # run both LLM and ML, store ML as shadow
}
```

Three separate flags so retrieval, extraction, and classification can be flipped independently. `ml_shadow_mode` enables dual-run for agreement-rate monitoring.

`ml_pipeline_settings.enabled` in the Pydantic config is a *startup* flag (loads models or not). The DB flags are *runtime* (which path actually gets called on each request).

## Testing strategy

### Unit — `backend/tests/services/test_extraction_ml.py`

- `test_empty_text_returns_empty`: `extract("")` returns `{"entities": [], "relationships": []}`.
- `test_smoke`: text "darkmem uses Tree-sitter for parsing" produces at least darkmem (project) + Tree-sitter (tool) + USES relation.
- `test_nms_suppresses_overlap`: mock span detector returns overlapping candidates at scores 0.9, 0.7; assert only the 0.9 survives.
- `test_rel_map_applied`: mock REBEL to emit `IMPROVES_ON`; assert output has `REPLACES`.
- `test_rebel_hallucination_filter`: mock REBEL to emit a relation with `source` not in entities; assert it's filtered.
- `test_timeout_returns_empty`: monkeypatch `_extract_sync` to sleep; assert timeout returns `{"entities": [], "relationships": []}` and logs.
- `test_cpu_fallback`: mock `torch.cuda.is_available()` to False with `cpu_fallback=True`; assert `MLModels.device == "cpu"` after load.

### Integration — `backend/tests/integration/test_pipeline_ml_mode.py`

- Flip `ml_extraction = True` and `ml_classification = True` in the in-memory feature flag override.
- Ingest 10 hand-labeled fixture memories from `tests/fixtures/darkmem_golden.jsonl`.
- Assert lenient entity F1 ≥ 0.88, relation F1 ≥ 0.55 (these mirror the production F1 measured in development, with a small margin).
- Assert p95 latency per ingest < 800 ms (accounting for DB writes on top of model inference).

### Benchmark — `backend/tests/bench/bench_extraction.py`

- Runs the 90-example historical gold against the *production pipeline* (through `ProcessingPipeline`, not directly against `extraction_ml.py`).
- Apply `TYPE_MAP` to both predictions and gold to normalise to the 10-type space before scoring.
- Target: entity F1 ≥ 0.90 lenient, relation F1 ≥ 0.60.

## Rollout — DB-flag-driven, no redeploy per stage

### Stage 0 — ship dark (week 1)

- Deploy the new services and feature flags. Defaults are all `False`.
- ML models are loaded at startup if `ml_pipeline_settings.enabled = True` (env var), but NOT called on any request until the DB flags flip.
- Run the integration test suite in staging with flags on.

### Stage 1 — shadow mode (week 2)

- Flip `ml_shadow_mode = True` in prod. LLM path stays authoritative; ML path runs in parallel and stores outputs for comparison.
- Monitor agreement rate daily. Target:
  - Entity name-level agreement ≥ 85% (lower-bound because LLM and ML will disagree on boundary cases; calibrate after first week)
  - Relation triple-level agreement ≥ 55%

### Stage 2 — promote extraction (week 3)

- Flip `ml_extraction = True`, `ml_classification = True`. LLM path remains as fallback — `ExtractionMLService.extract()` catches exceptions and returns empty; the pipeline can still fall back to LLM in that case with a second try.
- Keep `ml_shadow_mode = False` now (reverse roles). LLM runs as shadow if desired.

### Stage 3 — promote retrieval (week 4)

- Flip `ml_retrieval = True`. `LLMOrchestrator.embed()` starts routing to bge-large.
- **Critical**: existing embeddings in the DB were made by nomic-embed-text. Cache fingerprint changes, so new embeddings won't collide with old. However, semantic search queries will embed with bge-large but compare against nomic-embedded passages in the DB — **this breaks retrieval quality until re-embedding completes**.
- Run `backend/scripts/reembed_all.py` (new): batch-re-embed every memory with the new retriever. Needs to happen before flipping the flag, not after.

### Stage 4 — LLM path fallback (ongoing)

- Keep the LLM extraction path available indefinitely. Set `ml_extraction = False` to revert at any time.
- Don't delete `extraction.py` or `classification_llm.py`. They're safety nets.

## Monitoring

Metrics to add (Prometheus style):

- `darkmem_ml_extraction_latency_ms{stage}` — histogram, buckets `[25, 50, 100, 200, 500, 1000, 5000]`, stages `span`, `typer`, `relation`, `total`.
- `darkmem_ml_extraction_entity_count` — histogram.
- `darkmem_ml_extraction_relation_count` — histogram.
- `darkmem_ml_extraction_timeouts_total` — counter.
- `darkmem_ml_extraction_empty_result_total` — counter (numerator of empty-result rate).
- `darkmem_ml_classification_latency_ms` — histogram.
- `darkmem_ml_retrieval_latency_ms` — histogram.
- `darkmem_ml_vram_allocated_mb` — gauge, sampled every 60 s.
- `darkmem_ml_shadow_agreement_rate{kind}` — gauge, kinds `entity_name`, `entity_name_type`, `relation_triple` (shadow phase only).

SLO: **extraction p95 latency < 800 ms**, **empty-result rate < 15%** over a 1-hour rolling window.

## Risks

| risk | likelihood | impact | mitigation |
|---|---|---|---|
| VRAM OOM under concurrent load | medium | high | semaphore at 4 concurrent inferences; alert on VRAM > 7.8 GB; if triggered, drop classifier to CPU (−619 MB from GPU) |
| ML models fail to load on startup | low | high | `cpu_fallback=True` default; if that fails too, the feature flags are still False so pipeline runs LLM path |
| REBEL generation hangs | low | medium | 10s timeout per call; returns empty on timeout |
| Embedding re-embedding hits DB bandwidth limits | medium | medium | `reembed_all.py` respects a configurable rate limit; run during low-traffic hours |
| Shadow-mode agreement drops below thresholds | medium | — | do not promote; investigate dead relation types, per-domain mismatches |
| Legacy type migration breaks existing queries | medium | high | dry-run first: script prints planned changes without committing; manually review before commit |
| Singleton race at startup | low | low | `threading.Lock` double-checked-locking in `get_ml_models()` |
| `trust_remote_code=True` risks | accepted | medium | acknowledged for ModernBERT; in future, vendor the modeling file into the repo and set `trust_remote_code=False` pointing at the vendored path |
| Long memories (> 256 source tokens) get truncated by REBEL | known | medium | phase 1 accepts the truncation; future: chunk with `long_text_chunk_tokens=200`, overlap `40`, merge triplets across chunks with a dedup step |
| Classifier summary field missing | known | low | stage 2/3 populates summary via a small LLM call after classification if the consumer requires it |

## Estimated effort (revised)

| step | time |
|---|---|
| Convert `app/config.py` → `app/config/` package; add `taxonomy.py` and `MLPipelineSettings` | 0.5 day |
| `ml_models.py` singleton + CPU fallback + async warm-load | 0.5 day |
| `extraction_ml.py` with timeouts, semaphore, async wrapping | 0.5 day |
| `classification_ml.py` + `LLMOrchestrator.embed()` routing | 0.5 day |
| Modify `pipeline.py` to dispatch by flag; modify `main.py` lifespan | 0.25 day |
| Legacy type migration script + repo methods | 0.5 day |
| `reembed_all.py` script + sanity test in dev | 0.5 day |
| Unit + integration tests + benchmark | 1 day |
| Observability (Prometheus metrics) | 0.5 day |
| **subtotal dev work** | **~4.75 days** |
| Staging soak with shadow mode | 3-5 elapsed days (passive) |
| Gradual prod flag flips (each stage 1 week) | 3-4 weeks elapsed |

Realistic "fully landed" timeline: **~5 weeks of elapsed time, ~5 days of focused dev work.**

## Verification checklist (revised)

Before flipping prod flags:
- [ ] All 5 models load at startup with VRAM ≤ 7.6 GB total (qwen warm, one request in flight)
- [ ] Unit suite green
- [ ] Integration suite green with `ml_extraction=True`, `ml_classification=True`
- [ ] Benchmark hits entity F1 ≥ 0.90 lenient and relation F1 ≥ 0.60 on 90-gold
- [ ] Legacy type migration dry-run looks correct (no mass type-moves to `entity` that should have been specific)
- [ ] `reembed_all.py` succeeds on the staging DB; retrieval quality measured before/after
- [ ] Shadow mode agreement rate stabilises above thresholds for 72 h
- [ ] Grafana dashboard deployed and p95 latency observed on real traffic
- [ ] Documentation: update `backend/README.md` with a "ML pipeline" section describing the flags and how to revert

## Open questions (flag with product)

1. **Classification summary field** — existing `ClassificationService` produces a one-line summary via the LLM. The ML path doesn't. Is summary load-bearing downstream (UI surface? memory title generation? graph node display name?), or can it be null for the ML-classified path?
2. **Agreement-rate thresholds for promotion** — 85% entity / 55% relation are placeholder. What's the actual acceptable error rate for darkmem's agent queries? Calibrate with product.
3. **Long-memory strategy** — memories > 256 tokens get truncated by REBEL in phase 1. Do we need chunking now (phase 1) or can we ship truncation and add chunking later?
4. **bge-large vs bge-base choice** — plan defaults to bge-large (1024 dims, no schema change). Willing to do a 1024→768 schema migration for bge-base's 900 MB VRAM savings? That's the opposite tradeoff.
5. **Feature flag granularity** — is `ml_extraction / ml_classification / ml_retrieval` as three separate flags right, or should they be one combined flag? Three gives more control; one is simpler ops.
