# darkmem extraction pipeline integration plan — v3

Last updated: 2026-04-18
Supersedes: INTEGRATION_PLAN.md (v1) and INTEGRATION_PLAN_v2.md (v2)

Rewrite after the v2 self-review exposed four critical bugs and six medium issues. v3 fixes each against real code read from `backend/app/services/pipeline.py`, `backend/app/services/extraction.py`, `backend/app/services/classification_llm.py`, `backend/app/repositories/graph.py`, and the migrations directory at `backend/migrations/versions/`.

## What v2 got wrong — grounded fixes

### Fix 1 — ExtractionMLService return shape must match ExtractionService

Real contract from `extraction.py` line 215:
```python
return {**result, "entities": entities, "relationships": relationships}
```
`result` is the full LLM JSON which includes `memory_type`, `importance`, and any other top-level keys the prompt schema emits. Downstream consumers (pipeline.py, graph upserters) read these keys directly.

**v3 ExtractionMLService.extract() contract:**
```python
async def extract(self, content: str, system_prompt: str | None = None) -> dict:
    if not content or not content.strip():
        return {"entities": [], "relationships": [], "memory_type": "fact", "importance": 0.3}
    # ... inference ...
    return {
        "memory_type": "fact",       # placeholder; set by classifier step downstream
        "importance": 0.5,           # placeholder; product can tune or drop this key
        "entities": entities,
        "relationships": relationships,
    }
```

Plus: run the output through the existing `clean_extraction()` helper from `extraction.py` so downstream graph dedup sees canonicalized output:

```python
from app.services.extraction import clean_extraction

raw = {"memory_type": "fact", "importance": 0.5, "entities": entities_raw, "relationships": relationships_raw}
cleaned = clean_extraction(raw, content, is_tool_call=False)
return cleaned
```

This fixes both the return-shape mismatch AND the bypassed post-processing (v2 bug #1 and #4).

### Fix 2 — ClassificationMLService returns `"hall"` not `"type"`

Real contract from `classification_llm.py` line 62-67:
```python
return {
    "hall": classified_type,
    "summary": result.get("summary"),
    "emotions": result.get("emotions") or [],
    "flags": result.get("flags") or [],
}
```
The key is **`"hall"`** (typo in the original — must preserve). Also: `summary` is `None`-able in the LLM path (line 70-73 error branch returns `summary: None`); UI code tolerates that.

**v3 ClassificationMLService.classify() contract:**
```python
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
        return await asyncio.to_thread(_classify_sync, content)
    except Exception:
        logger.exception("ML classify failed")
        return {"hall": "fact", "summary": None, "emotions": [], "flags": []}


def _classify_sync(text: str) -> dict:
    ml = get_ml_models()
    enc = ml.classifier_tok(text, return_tensors="pt", truncation=True, max_length=256, padding=False)
    enc = {k: v.to(ml.device) for k, v in enc.items()}
    with torch.no_grad():
        logits = ml.classifier(**enc).logits
    top = logits[0].argmax().item()
    return {
        "hall": MEMORY_TYPES[top],
        "summary": None,    # ML classifier doesn't summarize; same as the LLM error branch
        "emotions": [],
        "flags": [],
    }
```

Matches the positional arg signature too (`content, enabled_areas, system_prompt, mode`), including `enabled_areas` and `system_prompt` being non-optional. Fixes v2 bug #2.

### Fix 3 — flag check per-call, not per-init

v2 had `ProcessingPipeline.__init__` select ML vs LLM service once at startup. That contradicts runtime-toggleable feature flags.

**v3 pattern:** keep BOTH services instantiated on the pipeline, dispatch per-call based on the live DB flag.

```python
# pipeline.py
class ProcessingPipeline:
    def __init__(self, llm, session_factory, embedding_dims, broadcast=None):
        from app.services.extraction import ExtractionService
        from app.services.classification_llm import ClassificationService
        from app.services.extraction_ml import ExtractionMLService
        from app.services.classification_ml import ClassificationMLService

        self.llm = llm
        self.session_factory = session_factory
        self._extraction_llm = ExtractionService(llm)
        self._extraction_ml = ExtractionMLService()  # no-op until ML flag flips
        self._classification_llm = ClassificationService(llm)
        self._classification_ml = ClassificationMLService()
        # ... rest unchanged ...

    async def _should_use_ml(self, subsystem: str) -> bool:
        """Read the DB feature flag. Returns False if Config row missing or key absent."""
        flags = await _get_feature_flags(self.session_factory)
        return bool(flags.get(f"ml_{subsystem}", False))

    @property
    def extraction(self):
        """Lazy property that returns the active extraction service for this
        request. Checked on every call so flag flips take effect without restart."""
        # NOTE: The @property triggers an await, which isn't valid. Use a
        # dispatching wrapper instead — see _Dispatcher below.
        raise NotImplementedError("use self.extract_dispatch")
```

Actually, `@property` can't be async. The cleanest dispatch is a wrapper object:

```python
class _ExtractionDispatcher:
    def __init__(self, pipeline):
        self._p = pipeline
    async def extract(self, content: str, system_prompt: str | None = None) -> dict:
        if await self._p._should_use_ml("extraction"):
            return await self._p._extraction_ml.extract(content, system_prompt)
        return await self._p._extraction_llm.extract(content, system_prompt)

class _ClassificationDispatcher:
    def __init__(self, pipeline):
        self._p = pipeline
    async def classify(self, content, enabled_areas, system_prompt, mode="simple"):
        if await self._p._should_use_ml("classification"):
            return await self._p._classification_ml.classify(content, enabled_areas, system_prompt, mode)
        return await self._p._classification_llm.classify(content, enabled_areas, system_prompt, mode)
```

Then in `__init__`:
```python
self.extraction = _ExtractionDispatcher(self)
self.classification = _ClassificationDispatcher(self)
```

Callers (`pipeline.py` line 336 and 345) don't change — they still call `self.extraction.extract(...)`. Flag flip on the next call takes effect immediately.

**Cache the flag read** to avoid hammering the DB:
```python
# At pipeline top
_FLAG_CACHE_TTL = 5.0  # seconds
async def _get_feature_flags_cached(session_factory):
    now = time.monotonic()
    cached = _flag_cache.get("flags")
    if cached and now - cached["at"] < _FLAG_CACHE_TTL:
        return cached["value"]
    flags = await _get_feature_flags(session_factory)
    _flag_cache["flags"] = {"value": flags, "at": now}
    return flags
```

Fixes v2 bug #3.

### Fix 4 — ML extractor runs clean_extraction

Already covered in Fix 1 above (the ML extract calls `clean_extraction(raw, content, is_tool_call=False)` before returning). Fixes v2 bug #4.

### Fix 5 — Retrieval routing uses DB flag + all three embed methods

Patch `LLMOrchestrator.embed`, `.embed_batch`, and `.embed_batch_chunked` consistently:

```python
async def embed(self, text: str) -> list[float]:
    if await self._is_ml_retrieval_enabled():
        return await self._embed_ml(text)
    # existing ollama path
    ...

async def embed_batch(self, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if await self._is_ml_retrieval_enabled():
        return await self._embed_batch_ml(texts)
    ...

async def embed_batch_chunked(self, texts, chunk_size, concurrency):
    # unchanged — falls through to embed_batch which now routes by flag
    ...

async def _is_ml_retrieval_enabled(self) -> bool:
    # Cached session-less flag read — pipeline already caches; we just reuse
    from app.database import async_session_factory
    flags = await _get_feature_flags_cached(async_session_factory)
    return bool(flags.get("ml_retrieval", False))

async def _embed_ml(self, text: str) -> list[float]:
    from app.services.ml_models import get_ml_models
    ml = get_ml_models()
    prefixed = "Represent this sentence for searching relevant passages: " + text
    emb = await asyncio.to_thread(
        lambda: ml.retriever.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True).tolist()
    )
    return emb

async def _embed_batch_ml(self, texts: list[str]) -> list[list[float]]:
    from app.services.ml_models import get_ml_models
    ml = get_ml_models()
    prefixed = ["Represent this sentence for searching relevant passages: " + t for t in texts]
    emb = await asyncio.to_thread(
        lambda: ml.retriever.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True, batch_size=32).tolist()
    )
    return emb
```

Fixes v2 bug #5 and extends to the batch methods (v2 issue #5 addendum).

### Fix 6 — correct migrations path

Migration lives at `backend/migrations/versions/` (alembic is configured to use `%(here)s/migrations` via `alembic.ini`). New migrations created with:

```bash
cd backend
alembic revision -m "ml_pipeline_taxonomy_migration"
```

Template for the file (`backend/migrations/versions/<rev>_ml_pipeline_taxonomy_migration.py`):

```python
"""ml_pipeline_taxonomy_migration

Replaces 18-type entity_type values with the 10-type coding taxonomy.
Bumps model_fingerprint on entities that reference the old embedding model.
"""
from alembic import op
from sqlalchemy import text

LEGACY_ENTITY_TYPE_MAP = {
    "person": "entity", "organization": "entity", "team": "entity",
    "technology": "tool", "framework": "tool", "library": "tool",
    "pattern": "tool",
    "platform": "service", "infrastructure": "service",
    "standard": "protocol", "specification": "protocol",
    # identity-preserving rows intentionally omitted (service, database, concept, algorithm,
    #  protocol, language, project stay the same)
}

revision = "<generated>"
down_revision = "<previous>"

def upgrade():
    conn = op.get_bind()
    for old, new in LEGACY_ENTITY_TYPE_MAP.items():
        result = conn.execute(
            text("UPDATE entities SET entity_type = :new WHERE entity_type = :old"),
            {"old": old, "new": new},
        )
        print(f"entity_type {old} -> {new}: {result.rowcount} rows")

def downgrade():
    # No-op: type collapse is not invertible (many old types map to one new)
    pass
```

Fixes v2 issue #6. Column is `entity_type` on table `entities` (both confirmed from `app/repositories/graph.py`).

### Fix 7 — verified repository methods

`PostgresGraphRepository` already has table-level operations. For the migration we don't need new repo methods — we run raw SQL in the Alembic migration directly (as shown in Fix 6). For the reembed script, `upsert_entity_embedding(entity_id, embedding, model_fingerprint)` exists at line 32 of graph.py and is exactly what we need.

```python
# backend/scripts/reembed_all.py
import argparse, asyncio, logging
from app.database import async_session_factory
from app.repositories.graph import PostgresGraphRepository
from app.services.ml_models import get_ml_models

async def main(dry_run: bool, batch_size: int = 64):
    ml = get_ml_models()
    new_fp = ml.fingerprint
    async with async_session_factory() as session:
        # count first
        result = await session.execute(text("SELECT COUNT(*) FROM entities WHERE model_fingerprint != :fp"), {"fp": new_fp})
        n = result.scalar_one()
        print(f"{n} entities need re-embedding with fingerprint={new_fp}")
        if dry_run:
            return
        # loop in batches
        # ... (full implementation) ...

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--commit", dest="dry_run", action="store_false")
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()
    asyncio.run(main(args.dry_run, args.batch_size))
```

Fixes v2 issue #7.

### Fix 8 — MLModels partial-load recovery

```python
class MLModels:
    def __init__(self, device):
        self.device = device
        # ... fields start as None ...

    def load_all(self) -> None:
        """Load atomically. Populate a staging struct first, only assign to
        self.* fields after every load succeeded. On failure, caller sees
        None-everywhere and retries are safe."""
        import torch
        from gliner import GLiNER
        from sentence_transformers import SentenceTransformer
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoModelForSeq2SeqLM

        staged = {}
        mdir = ml_pipeline_settings.models_dir

        try:
            staged["span"] = GLiNER.from_pretrained(str(mdir / "darkmem-span-v1" / "best"))
            if self.device == "cuda":
                staged["span"] = staged["span"].to("cuda")

            tok_path = mdir / "darkmem-typer-v1" / "best"
            staged["typer_tok"] = AutoTokenizer.from_pretrained(str(tok_path), trust_remote_code=True)
            staged["typer"] = AutoModelForSequenceClassification.from_pretrained(str(tok_path), trust_remote_code=True)
            if self.device == "cuda":
                staged["typer"] = staged["typer"].to("cuda")
            staged["typer"].train(False)

            # 2026-04-19: swapped from darkmem-relation-v1 (rebel-large, 1.6 GB VRAM,
            # F1 0.660 on 5-type) to darkmem-relation-base-v1 (rebel-base, 606 MB,
            # F1 0.618 on 5-type) — deliberate Pareto trade-off for the 12 GB LXC.
            # See fine-tuning/models/PRODUCTION.md for the full metric record.
            rel_path = mdir / "darkmem-relation-base-v1" / "best"
            staged["relation_tok"] = AutoTokenizer.from_pretrained(str(rel_path))
            staged["relation"] = AutoModelForSeq2SeqLM.from_pretrained(str(rel_path))
            if self.device == "cuda":
                staged["relation"] = staged["relation"].to("cuda")
            staged["relation"].train(False)

            cls_path = mdir / "darkmem-classifier-v1" / "best"
            staged["classifier_tok"] = AutoTokenizer.from_pretrained(str(cls_path), trust_remote_code=True)
            staged["classifier"] = AutoModelForSequenceClassification.from_pretrained(str(cls_path), trust_remote_code=True)
            if self.device == "cuda":
                staged["classifier"] = staged["classifier"].to("cuda")
            staged["classifier"].train(False)

            staged["retriever"] = SentenceTransformer(str(mdir / "darkmem-retriever-v1"), device=self.device)
        except Exception as exc:
            # Free any partial GPU memory we allocated
            for m in staged.values():
                try:
                    del m
                except Exception:
                    pass
            if self.device == "cuda":
                import torch
                torch.cuda.empty_cache()
            raise RuntimeError(f"MLModels.load_all failed during {exc}") from exc

        # Atomic commit
        for k, v in staged.items():
            setattr(self, k, v)
```

Fixes v2 issue #8.

### Fix 9 — dry-run on migration + reembed

Already in Fix 6 (Alembic migration is dry-run by default until you `alembic upgrade head`) and Fix 7 (`reembed_all.py` has `--dry-run` default, explicit `--commit` flag). v3 also adds:

```python
# migrate_entity_types_dry_run.py — ad-hoc preview before running Alembic
import asyncio
from app.database import async_session_factory
from sqlalchemy import text

LEGACY_ENTITY_TYPE_MAP = {...}

async def main():
    async with async_session_factory() as session:
        for old, new in LEGACY_ENTITY_TYPE_MAP.items():
            if old == new:
                continue
            r = await session.execute(
                text("SELECT COUNT(*) FROM entities WHERE entity_type = :old"),
                {"old": old},
            )
            n = r.scalar_one()
            print(f"would rename {n:5d} entities: {old} -> {new}")

asyncio.run(main())
```

Fixes v2 issue #9.

### Fix 10 — ML summary defaults to None, not crash-vector

Classification-ML path returns `"summary": None` (same as the LLM's error branch — preserves UI compatibility). Downstream UI/graph code that reads summary should already handle `None` since the LLM path produces it on errors. Fixes v2 issue #9 / #10.

### Fix 11 — health check endpoint

Add at `backend/app/api/routes/health.py`:

```python
from fastapi import APIRouter, Request
from app.config import ml_pipeline_settings

router = APIRouter()

@router.get("/api/health/ml_models")
async def ml_models_health(request: Request):
    status = {
        "enabled": ml_pipeline_settings.enabled,
        "device": ml_pipeline_settings.device,
        "loaded": False,
        "vram_allocated_mb": None,
    }
    if not ml_pipeline_settings.enabled:
        status["note"] = "ml pipeline disabled by startup setting"
        return status
    from app.services.ml_models import _INSTANCE
    if _INSTANCE is None:
        status["note"] = "models not yet loaded"
        return status
    status["loaded"] = True
    status["device"] = _INSTANCE.device
    try:
        import torch
        if torch.cuda.is_available():
            status["vram_allocated_mb"] = torch.cuda.memory_allocated() / 1e6
    except Exception:
        pass
    return status
```

Wire into `app/main.py`:
```python
from app.api.routes import health
app.include_router(health.router)
```

Fixes v2 issue missing.

## Verified ground truth (things v3 depends on)

- `ExtractionService.extract(content, system_prompt=None)` returns `{**result, "entities": [...], "relationships": [...]}` — extraction.py:228-234
- `ClassificationService.classify(content, enabled_areas, system_prompt, mode="simple")` returns `{"hall", "summary", "emotions", "flags"}` — classification_llm.py:62-73
- `clean_extraction(result, content, is_tool_call=False)` is the canonical post-processing chain, calls `_normalize_names`, `_filter_noise`, `_dedup_entities`, `_build_name_remap`, `_remap_relationships`, `_validate_directions` — extraction.py:205-220
- Entity table: `entities`, column `entity_type`, unique `(name, entity_type)`, has `embedding`, `model_fingerprint`, `properties`, `memory_ids` — graph.py:17 onwards
- Entity embedding cache: `entity_embedding_cache`, columns `name_lower`, `embedding`, `model_fingerprint` — graph.py:47-60
- Migrations path: `backend/migrations/versions/` (not `backend/alembic/versions/`) — alembic.ini
- `_get_feature_flags(session_factory)` reads `Config` row with key `feature_flags`, merges with `FEATURE_FLAGS_DEFAULTS` — pipeline.py:21-30
- Pipeline dispatches extraction at `pipeline.py:336` via `self.extraction.extract(content, system_prompt=ext_prompt)` and classification at `pipeline.py:345` via `self.classification.classify(content, areas, cls_prompt, mode=mode)`
- Main lifespan uses `@asynccontextmanager async def lifespan`, not `@app.on_event("startup")` — main.py:21

## Files to create or modify — concrete list

| action | path | what |
|---|---|---|
| modify | `backend/app/config.py` | add `MLPipelineSettings` class + module-level `ml_pipeline_settings` singleton |
| create | `backend/app/config/__init__.py` (if converting to package) or `backend/app/taxonomy.py` (if keeping flat) | taxonomy constants |
| create | `backend/app/services/ml_models.py` | singleton loader with atomic partial-load recovery, CPU fallback, DCL locking |
| create | `backend/app/services/extraction_ml.py` | ExtractionMLService + `_extract_sync` + post-processing via `clean_extraction` |
| create | `backend/app/services/classification_ml.py` | ClassificationMLService returning `{"hall", "summary", "emotions", "flags"}` |
| modify | `backend/app/services/pipeline.py` | swap `self.extraction` / `self.classification` to the dispatcher wrappers |
| modify | `backend/app/services/llm.py` | add `_is_ml_retrieval_enabled()` + `_embed_ml` + `_embed_batch_ml`; patch `embed` and `embed_batch` |
| modify | `backend/app/main.py` | warm-load ML models in lifespan; include health router |
| create | `backend/app/api/routes/health.py` | `/api/health/ml_models` endpoint |
| create | `backend/migrations/versions/<rev>_ml_pipeline_taxonomy_migration.py` | Alembic migration for `entities.entity_type` renames |
| create | `backend/scripts/reembed_all.py` | dry-run-default re-embed of all existing entities |
| create | `backend/scripts/migrate_entity_types_dry_run.py` | preview of the Alembic migration without commit |
| modify | `backend/app/services/extraction_tools.py` | optional: migrate `ENTITY_TYPES`/`RELATIONSHIP_TYPES` to import from taxonomy module; keep helpers intact |
| add flags | `backend/app/config.py::FEATURE_FLAGS_DEFAULTS` | `ml_extraction=False`, `ml_classification=False`, `ml_retrieval=False`, `ml_shadow_mode=False` |
| create | `backend/tests/services/test_extraction_ml.py` | unit tests covering NMS, REL_MAP, timeout, hallucination filter, empty text, CPU fallback, clean_extraction pass-through |
| create | `backend/tests/services/test_classification_ml.py` | unit tests covering empty text, return-shape with `"hall"` key |
| create | `backend/tests/integration/test_pipeline_ml_mode.py` | integration test with DB flag flipped |
| create | `backend/tests/bench/bench_extraction.py` | 90-gold benchmark suite through the full pipeline |

## Rollout — unchanged from v2 but using DB flags correctly

Four stages (shipped-dark → shadow → promote extraction/classification → promote retrieval + reembed). Flags flip without restart because the dispatcher reads DB flags per-call (5-second cache). Full details in v2 §Rollout.

## Verification checklist

Before promoting any flag to `True` in prod:
- [ ] All five models load at startup; `/api/health/ml_models` returns `loaded=true` and VRAM ≤ 7.6 GB
- [ ] `tests/services/test_extraction_ml.py` — green, including return-shape match (`memory_type` present, `importance` present, `entities`/`relationships` present)
- [ ] `tests/services/test_classification_ml.py` — green, including `result["hall"]` access on the output (not `result["type"]`)
- [ ] `tests/integration/test_pipeline_ml_mode.py` — green with both `ml_extraction=True` and `ml_classification=True` set on a test Config row
- [ ] `bench_extraction.py` — entity F1 ≥ 0.90 lenient on 90-gold, relation F1 ≥ 0.60
- [ ] `migrate_entity_types_dry_run.py` — output reviewed, no unexpected mass-renames to `entity`
- [ ] Alembic migration applied in staging, `SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type` matches the expected 10-type distribution
- [ ] `reembed_all.py --dry-run` shows expected row count; `--commit` run completes on staging
- [ ] Flag flip in staging takes effect on next request (verify via `/api/health/ml_models` logs + integration test)
- [ ] Shadow mode agreement rate above threshold for 72 h continuous
- [ ] Grafana p95 latency < 800 ms on real traffic

## Estimated effort (v3)

Same 5 days of focused dev as v2, but no rework-and-fix cycle on integration day 1 because v3's contracts are verified against code, not assumed.

| step | time |
|---|---|
| config/taxonomy + MLPipelineSettings | 0.5 d |
| ml_models.py (atomic load + DCL + CPU fallback) | 0.5 d |
| extraction_ml.py (with clean_extraction post-processing) | 0.5 d |
| classification_ml.py (with `"hall"` key) | 0.25 d |
| pipeline.py dispatchers + cached flag reads | 0.5 d |
| LLMOrchestrator embed/embed_batch routing | 0.5 d |
| main.py lifespan + health endpoint | 0.25 d |
| Alembic migration + dry-run preview | 0.5 d |
| reembed_all.py | 0.5 d |
| tests (unit + integration + bench) | 1 d |
| **total focused dev** | **~5 days** |

Elapsed rollout time (staging soak, shadow window, progressive flag flips): **~5 weeks**, unchanged from v2.

## Open questions still requiring product input

1. **`summary` field**: ML classifier returns `None`. LLM path sometimes returns `None` on error. UI must handle; confirm.
2. **Agreement-rate thresholds**: 85% entity / 55% relation are v2 placeholders. Need product calibration.
3. **Long-memory strategy**: phase 1 accepts 256-token truncation for REBEL. Defer chunking to phase 2.
4. **Feature flag granularity**: three flags (`ml_extraction`, `ml_classification`, `ml_retrieval`) + shadow flag. Confirm independent control is desired.
5. **`memory_type` / `importance` defaults in ExtractionMLService**: v3 emits placeholders `memory_type="fact"`, `importance=0.5`. These are overwritten by the classifier step in the pipeline anyway, but if any downstream code reads `extraction_result["memory_type"]` before the classifier runs, the placeholder may be wrong. Verify with product.
