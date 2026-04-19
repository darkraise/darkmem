# darkmem extraction pipeline integration plan

Last updated: 2026-04-17

This plan wires the five fine-tuned checkpoints in `fine-tuning/models/darkmem-*-v1/` into the darkmem backend service. The current `backend/app/services/extraction.py` uses LLM-based extraction via qwen3.5:4b; after this plan, entity extraction, relation extraction, memory classification, and retrieval are all served by the specialist fine-tuned heads, with qwen3.5:4b reserved for reasoning / chat.

## Context

Why this change:
- Current extraction pipeline is LLM-only. It hits ~0.75 entity F1 on production-style coding memories and ~4.5 s per row, both measured in the 2026-04-17 session.
- The five specialist heads hit 0.94 lenient F1 / 0.73 strict pair F1 on entity extraction, 0.64 F1 on relation extraction, 0.975 on memory-type classification, and 0.884 MRR@10 on retrieval. Combined pipeline latency is ~260 ms/row — **~17× faster** than qwen-only extraction.
- Freeing qwen3.5:4b from extraction duty lets it focus on reasoning where it adds real value (memory synthesis, agent decisions, conversational responses).

## Current state of `backend/app/services/`

| file | role | change needed |
|---|---|---|
| `extraction.py` | orchestrates LLM-based entity/relation extraction via `LLMOrchestrator` | **replace body** with a `FineTunedExtractionPipeline` that calls the span + typer + relation heads |
| `extraction_tools.py` | defines 18 entity types, 14 relation types | **rewrite taxonomy** to the 10-type coding set (or add reconciliation layer) |
| `memory_classifier.py` | rule-based (regex-only) memory classifier | **replace** with `darkmem-classifier-v1` inference |
| `hybrid_search.py` | retrieval with existing embedder (pre-fine-tune) | **swap embedder** to `darkmem-retriever-v1` |
| `llm.py` | LLMOrchestrator (qwen3.5:4b via Ollama) | **no change** — keeps serving reasoning/chat |
| `memory.py`, `graph.py`, `knowledge_graph.py` | consume entity/relation outputs | **check schema compatibility** — rename fields if necessary |
| `prompt.py` | LLM extraction prompts | **remove** extraction-related prompts; keep reasoning prompts |

New files needed:
- `app/services/ml_models.py` — singleton model loader (loads all 5 heads once at startup)
- `app/services/extraction_pipeline.py` — new 2-stage entity + relation orchestration
- `app/services/memory_classifier_ml.py` — ModernBERT-based memory type classifier
- `app/services/retrieval_embedder.py` — bge-base-7500clean-hn wrapper
- `app/config/taxonomy.py` — 10-type entity + 10-type relation constants + REL_MAP

## Target architecture

```
POST /api/memories/ingest
    { text, metadata }
        │
        ▼
  memory_classifier_ml  (darkmem-classifier-v1, ModernBERT-base)
    returns: memory_type ∈ {fact, decision, preference, problem, reference, architecture, milestone}
        │
        ▼
  extraction_pipeline.extract(text)
    ├── stage 1: darkmem-span-v1  (GLiNER, 10-type label collapsed to single "entity")
    │     returns: [(start, end, score), …]
    │     applies NMS (IoU 0.3) to suppress overlapping spans
    ├── stage 2: darkmem-typer-v1 (ModernBERT, 10-class classifier)
    │     input: text with [ENT]span[/ENT] markers
    │     returns: [(start, end, name, type), …]
    └── relation: darkmem-relation-v1 (REBEL seq2seq)
          input: text + entity-hint string
          output: [<triplet> A <subj> B <obj> rel_type …]
          post-process: REL_MAP collapses 30 emitted types → 10 canonical types
          returns: [(source_name, target_name, relation_type), …]
        │
        ▼
  retrieval_embedder.embed(text)  (darkmem-retriever-v1, bge-base)
    returns: 768-dim vector
        │
        ▼
  graph/knowledge_graph upsert with {entities, relations, memory_type, embedding}
        │
        ▼
  LLMOrchestrator (qwen3.5:4b, unchanged)
    for: memory summarization, agent responses, clarifying questions
```

Critical: qwen3.5:4b stays loaded in ollama for the reasoning step. The extraction heads load separately in the FastAPI process. Both coexist within the 8 GB budget (~7.5 GB total, measured).

## Files to create (ordered by implementation sequence)

### 1. `backend/app/config/taxonomy.py`

Single source of truth for entity and relation types used by the fine-tuned pipeline. Replaces the 18/14 type lists in `extraction_tools.py`.

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

# REBEL emits 30 relation types natively; this map collapses to our 10.
# Copied from fine-tuning/scripts/_build_rebel_coding10_splits.py
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

# Old 18-type backend taxonomy → new 10-type (forward migration)
LEGACY_ENTITY_TYPE_MAP = {
    "person": "entity", "organization": "entity", "team": "entity",
    "technology": "tool", "framework": "tool", "library": "tool",
    "pattern": "tool",
    "service": "service", "platform": "service", "infrastructure": "service",
    "standard": "protocol", "specification": "protocol",
}
```

### 2. `backend/app/services/ml_models.py`

Singleton loader that holds all five checkpoints resident. Called once at FastAPI startup.

```python
from pathlib import Path
import torch
from gliner import GLiNER
from sentence_transformers import SentenceTransformer
from transformers import (
    AutoModelForSequenceClassification, AutoTokenizer,
    AutoModelForSeq2SeqLM,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "fine-tuning" / "models"

class MLModels:
    """Singleton holder for the 5 darkmem heads. Loaded once at startup."""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.span = None          # GLiNER
        self.typer_tok = None     # AutoTokenizer
        self.typer = None         # AutoModelForSequenceClassification
        self.relation_tok = None  # AutoTokenizer
        self.relation = None      # AutoModelForSeq2SeqLM
        self.classifier_tok = None
        self.classifier = None    # AutoModelForSequenceClassification
        self.retriever = None     # SentenceTransformer

    def load_all(self) -> None:
        self.span = GLiNER.from_pretrained(str(MODELS_DIR / "darkmem-span-v1" / "best"))
        self.span = self.span.to(self.device) if self.device == "cuda" else self.span

        self.typer_tok = AutoTokenizer.from_pretrained(
            str(MODELS_DIR / "darkmem-typer-v1" / "best"), trust_remote_code=True)
        self.typer = AutoModelForSequenceClassification.from_pretrained(
            str(MODELS_DIR / "darkmem-typer-v1" / "best"), trust_remote_code=True)
        if self.device == "cuda":
            self.typer = self.typer.to("cuda")
        self.typer.train(False)

        self.relation_tok = AutoTokenizer.from_pretrained(
            str(MODELS_DIR / "darkmem-relation-v1" / "best"))
        self.relation = AutoModelForSeq2SeqLM.from_pretrained(
            str(MODELS_DIR / "darkmem-relation-v1" / "best"))
        if self.device == "cuda":
            self.relation = self.relation.to("cuda")
        self.relation.train(False)

        self.classifier_tok = AutoTokenizer.from_pretrained(
            str(MODELS_DIR / "darkmem-classifier-v1" / "best"), trust_remote_code=True)
        self.classifier = AutoModelForSequenceClassification.from_pretrained(
            str(MODELS_DIR / "darkmem-classifier-v1" / "best"), trust_remote_code=True)
        if self.device == "cuda":
            self.classifier = self.classifier.to("cuda")
        self.classifier.train(False)

        self.retriever = SentenceTransformer(
            str(MODELS_DIR / "darkmem-retriever-v1"), device=self.device)


_ml_models_singleton: MLModels | None = None

def get_ml_models() -> MLModels:
    global _ml_models_singleton
    if _ml_models_singleton is None:
        _ml_models_singleton = MLModels()
        _ml_models_singleton.load_all()
    return _ml_models_singleton
```

### 3. `backend/app/services/extraction_pipeline.py`

Orchestration: span → typer → relation with NMS + REL_MAP. Replaces `extraction.py`'s LLM-based path.

```python
from __future__ import annotations
import re
import torch
import torch.nn.functional as F

from app.config.taxonomy import ENTITY_TYPES, REL_MAP
from app.services.ml_models import get_ml_models

SPAN_THRESHOLD = 0.5
NMS_IOU = 0.3
TYPE_BATCH = 16
REBEL_NUM_BEAMS = 4
REBEL_MAX_TGT = 128
REBEL_MAX_SRC = 256


def _nms_spans(spans: list[dict], iou: float = NMS_IOU) -> list[dict]:
    """Greedy non-max suppression on character-level overlapping span candidates."""
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: -s.get("score", 0.0))
    kept: list[dict] = []
    for s in sorted_spans:
        s_start, s_end = s["start"], s["end"]
        s_len = max(1, s_end - s_start)
        overlap = False
        for k in kept:
            inter_start = max(s_start, k["start"])
            inter_end = min(s_end, k["end"])
            inter = max(0, inter_end - inter_start)
            union = s_len + (k["end"] - k["start"]) - inter
            if union > 0 and inter / union > iou:
                overlap = True
                break
        if not overlap:
            kept.append(s)
    return kept


def _parse_triplets(decoded: str) -> list[dict]:
    rels: list[dict] = []
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
        if source and target and rtype:
            rels.append({"source": source, "target": target, "type": rtype})
    return rels


def extract(text: str) -> dict:
    """Two-stage entity extraction + relation extraction.

    Returns: {
      entities: [{name, type, start, end, score}, ...],
      relationships: [{source, target, type}, ...],
    }
    """
    ml = get_ml_models()

    # Stage 1: span detection
    raw_spans = ml.span.predict_entities(text, ["entity"], threshold=SPAN_THRESHOLD)
    raw_spans = _nms_spans(raw_spans, iou=NMS_IOU)

    entities: list[dict] = []
    if raw_spans:
        # Stage 2: type classification
        marked = [
            text[:s["start"]] + "[ENT]" + text[s["start"]:s["end"]] + "[/ENT]" + text[s["end"]:]
            for s in raw_spans
        ]
        all_preds: list[int] = []
        all_scores: list[float] = []
        for i in range(0, len(marked), TYPE_BATCH):
            chunk = marked[i:i + TYPE_BATCH]
            enc = ml.typer_tok(chunk, return_tensors="pt", truncation=True, max_length=256, padding=True)
            enc = {k: v.to(ml.device) for k, v in enc.items()}
            with torch.no_grad():
                logits = ml.typer(**enc).logits
            probs = F.softmax(logits, dim=-1)
            top1 = probs.argmax(dim=-1)
            all_preds.extend(top1.tolist())
            all_scores.extend(probs.max(dim=-1).values.tolist())
        for span_info, pid, score in zip(raw_spans, all_preds, all_scores):
            entities.append({
                "name": text[span_info["start"]:span_info["end"]],
                "type": ENTITY_TYPES[pid],
                "start": span_info["start"],
                "end": span_info["end"],
                "score": float(score),
            })

    # Relation extraction
    relationships: list[dict] = []
    if len(entities) >= 2:
        ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
        rebel_input = f"{text} | Entities: {ent_str}"
        enc = ml.relation_tok(rebel_input, return_tensors="pt", truncation=True, max_length=REBEL_MAX_SRC)
        enc = {k: v.to(ml.device) for k, v in enc.items()}
        with torch.no_grad():
            out = ml.relation.generate(**enc, max_length=REBEL_MAX_TGT, num_beams=REBEL_NUM_BEAMS)
        decoded = ml.relation_tok.decode(out[0], skip_special_tokens=False)
        raw_rels = _parse_triplets(decoded)
        # Apply REL_MAP post-hoc collapse (30 → 10)
        entity_names = {e["name"] for e in entities}
        for r in raw_rels:
            mapped = REL_MAP.get(r["type"])
            if not mapped:
                continue
            if r["source"] not in entity_names or r["target"] not in entity_names:
                continue  # REBEL hallucinated an entity that isn't in our list
            relationships.append({
                "source": r["source"],
                "target": r["target"],
                "type": mapped,
            })

    return {"entities": entities, "relationships": relationships}
```

### 4. `backend/app/services/memory_classifier_ml.py`

Replaces regex-only `memory_classifier.py`.

```python
import torch
from app.services.ml_models import get_ml_models
from app.config.taxonomy import MEMORY_TYPES

def classify_memory_type(text: str) -> dict:
    ml = get_ml_models()
    enc = ml.classifier_tok(text, return_tensors="pt", truncation=True, max_length=256, padding=False)
    enc = {k: v.to(ml.device) for k, v in enc.items()}
    with torch.no_grad():
        logits = ml.classifier(**enc).logits
    probs = torch.nn.functional.softmax(logits, dim=-1)
    top = probs[0].argmax().item()
    return {
        "memory_type": MEMORY_TYPES[top],
        "score": float(probs[0][top]),
        "probabilities": {MEMORY_TYPES[i]: float(p) for i, p in enumerate(probs[0])},
    }
```

### 5. `backend/app/services/retrieval_embedder.py`

```python
from app.services.ml_models import get_ml_models

_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

def embed_query(text: str) -> list[float]:
    ml = get_ml_models()
    emb = ml.retriever.encode(_QUERY_PREFIX + text, convert_to_numpy=True, normalize_embeddings=True)
    return emb.tolist()

def embed_passage(text: str) -> list[float]:
    ml = get_ml_models()
    emb = ml.retriever.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return emb.tolist()

def embed_batch(texts: list[str], is_query: bool = False) -> list[list[float]]:
    ml = get_ml_models()
    if is_query:
        texts = [_QUERY_PREFIX + t for t in texts]
    emb = ml.retriever.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=32)
    return emb.tolist()
```

## Files to modify

### `backend/app/main.py` (FastAPI app factory)

Add model warm-load on startup:

```python
@app.on_event("startup")
async def warmup_ml_models():
    from app.services.ml_models import get_ml_models
    logger.info("loading darkmem ML models ...")
    ml = get_ml_models()  # triggers load_all()
    logger.info(f"ML models loaded — device={ml.device}")
```

### `backend/app/services/extraction.py`

Replace the body with a thin wrapper:

```python
from app.services.extraction_pipeline import extract as _pipeline_extract

def extract_entities_and_relations(text: str) -> dict:
    return _pipeline_extract(text)
```

Keep the existing `_normalize_names`, `_TRAILING_SUFFIXES`, `_is_acronym_of` helpers — they're called from downstream code that deduplicates graph nodes.

### `backend/app/services/hybrid_search.py`

Swap the embedder import:

```python
# before:
# from app.services.embedding import embed_query, embed_passage
# after:
from app.services.retrieval_embedder import embed_query, embed_passage
```

Assuming the existing hybrid search already takes pluggable embedding functions. If it calls an embedder in-line, refactor to take the function as a parameter.

### `backend/app/services/extraction_tools.py`

Retire its type definitions. Replace the two lists with imports:

```python
from app.config.taxonomy import ENTITY_TYPES, RELATION_TYPES
```

Keep `build_extraction_schema` and `normalize_entity_type` for backwards compatibility with any consumers that haven't migrated to the pipeline yet. Update `_ENTITY_TYPE_MAP` to map legacy 18-type values to the 10-type set.

### `backend/app/services/memory.py`, `graph.py`, `knowledge_graph.py`

Audit every place that references the old 18-type or 14-relation-type sets. Grep for the type names:
- `technology`, `framework`, `library`, `pattern`, `team`, `person`, `organization`, `standard`, `specification`, `infrastructure`, `platform`
- `IMPLEMENTS`, `EXTENDS`, `CONFIGURES`, `PRODUCES`, `COMMUNICATES_WITH`, `DEPLOYED_ON`, `ALTERNATIVE_TO`

For each hit: if it's validating incoming data against the old set, replace the set reference. If it's a business-logic switch statement (e.g. "if type == 'person'"), apply `LEGACY_ENTITY_TYPE_MAP` to translate or update the logic to the 10-type set.

## Taxonomy reconciliation — migration path

The existing darkmem graph may contain nodes tagged with the old 18-type taxonomy. Two options:

**Option A (recommended): one-time migration script.** Run `backend/scripts/migrate_entity_types.py`:
1. Read every entity node from the graph store.
2. Apply `LEGACY_ENTITY_TYPE_MAP` to its type.
3. Update in place.
4. Log which types changed and how many nodes.

This preserves existing data and aligns it with the new pipeline.

**Option B: dual-schema tolerance.** The extraction pipeline emits 10-type. The graph store accepts both. Type-scoped queries union the equivalents (e.g. a query for `tool` returns nodes tagged `tool`, `technology`, `framework`, `library`). Less work up front, more complexity everywhere else.

Go with Option A unless there's a reason not to touch existing data.

## Testing strategy

### Unit tests — `backend/tests/services/test_extraction_pipeline.py`

- **Smoke test**: call `extract("darkmem uses Tree-sitter for parsing.")` and assert entities include `darkmem` (project) and `Tree-sitter` (tool), and a `USES` relationship between them.
- **Empty-text test**: `extract("")` returns `{"entities": [], "relationships": []}`.
- **Noisy-text test**: `extract("We switched from pytst to pytest-asyncio; the postgress pool kept deadlocking.")` extracts at least `pytest-asyncio` and `postgress`; asserts the typos survive as entity names.
- **NMS test**: mock span detector to return two overlapping candidates; assert only the higher-confidence one makes it to the typer.
- **Relation post-hoc map test**: mock REBEL to emit `IMPROVES_ON`; assert final output contains `REPLACES`.

### Integration tests — `backend/tests/integration/test_full_pipeline.py`

- Feed 10 hand-labeled sample memories (checked into the repo at `tests/fixtures/extraction_samples.jsonl`).
- Assert entity-pair F1 ≥ 0.85 on this fixture set (higher than the synthetic test because these are hand-curated).
- Assert relation F1 ≥ 0.55 on the same fixtures.
- Assert p95 latency < 500 ms per row on CPU fallback, < 150 ms on GPU.

### Benchmark suite — `backend/tests/bench_extraction.py`

- Runs the existing `fine-tuning/docs/e2e/scripts/extraction_eval/` 90-example gold against the *production* pipeline (not against the fine-tuning scripts directly).
- Target: lenient entity F1 ≥ 0.90, relation F1 ≥ 0.60. Those are the numbers we measured during development — regressions here indicate the wire-up broke something.

## Rollout plan

### Stage 1 — parallel deployment (1-2 days)

- Land the new services behind a feature flag `DARKMEM_EXTRACTION_BACKEND=ml_pipeline | llm` (default `llm`).
- `extract_entities_and_relations()` dispatches based on the flag.
- In dev, flip to `ml_pipeline` and run the integration test suite.
- In prod, keep `llm` as default until monitoring confirms the ML path is stable.

### Stage 2 — shadow mode (3-5 days)

- Both paths run on every ingest request.
- LLM output is stored as the "authoritative" one; ML output is stored in a shadow column.
- Compare entities/relations on a sample (100-500 rows/day), track agreement rate.
- If ML agrees with LLM ≥ 90% on entities and ≥ 75% on relations, promote.

### Stage 3 — promote (1 day)

- Switch default to `ml_pipeline`.
- LLM path remains available as fallback (e.g. for memories where ML returns zero entities but text is clearly rich).
- Remove shadow mode after 1 week of clean metrics.

### Stage 4 — deprecate LLM extraction (1 week later)

- Delete the LLM extraction prompts from `prompt.py`.
- Delete `extract_entities_and_relations_llm` helper.
- Keep `LLMOrchestrator` — it still serves chat/reasoning.

## Monitoring

Add metrics around the new pipeline:

- `extraction_pipeline_latency_ms` (histogram, buckets 50/100/200/500/1000/5000)
- `extraction_pipeline_entity_count` (histogram)
- `extraction_pipeline_relation_count` (histogram)
- `extraction_pipeline_empty_result_rate` (counter; numerator = memories where pipeline returned 0 entities)
- `extraction_pipeline_ml_agreement_rate` (shadow mode)
- `ml_models_vram_allocated_mb` (gauge, sampled every 60 s from `torch.cuda.memory_allocated()`)

Grafana dashboard: add to the existing darkmem health board. Alert if:
- p95 latency > 500 ms
- empty-result rate > 15% over a 1-hour window
- VRAM > 7.8 GB (80 MB away from ceiling on the 8.15 GB card)

## Risks and mitigations

| risk | likelihood | mitigation |
|---|---|---|
| Taxonomy mismatch breaks existing graph queries | medium | run migration script first; audit `memory.py`/`graph.py` before flipping flag |
| Model cold-start adds 15-20 s to FastAPI first request | high | warm-load at startup (in `main.py`); add readiness probe that waits for `get_ml_models()` to succeed |
| VRAM pressure with qwen3.5:4b already resident | medium | monitored at 7.5 GB total (safe); if it spikes, drop classifier to CPU (lowest-latency head to move — only 300 MB saved but frees headroom) |
| REBEL hallucinating entities not in our list | low | `extraction_pipeline.py` already filters relations whose source/target aren't in the entity set |
| gold-label ceiling caps accuracy | accepted | documented in the PRODUCTION.md; future improvement is a Phase B-style corpus relabel, not a wire-up concern |
| Ollama down → no qwen → extraction still works | low | the ML pipeline doesn't depend on ollama; reasoning degrades to a fallback response |

## Estimated effort

| step | time |
|---|---|
| taxonomy.py + ml_models.py + extraction_pipeline.py + memory_classifier_ml.py + retrieval_embedder.py | 0.5 day |
| wire into main.py + extraction.py shim + hybrid_search swap | 0.25 day |
| unit + integration tests | 0.5 day |
| migration script + run in dev | 0.25 day |
| feature flag + shadow mode wiring | 0.5 day |
| observability + dashboard | 0.5 day |
| **total end-to-end** | **~2.5 days of focused work** |

Stage 2 shadow mode takes elapsed calendar time (3-5 days) for enough comparison data to accumulate, but that's passive — no dev time during that window.

## Verification checklist

Ship when all of these pass on `main`:
- [ ] All 5 models load at startup without error; VRAM ≤ 7.6 GB total with qwen3.5:4b warm
- [ ] `test_extraction_pipeline.py` green
- [ ] `test_full_pipeline.py` meets F1 thresholds
- [ ] `bench_extraction.py` shows entity F1 ≥ 0.90 lenient on 90-gold, relation F1 ≥ 0.60 on coding10 test
- [ ] Migration script has run and logged zero unmapped legacy types
- [ ] Feature flag default switches to `ml_pipeline` with a plan to remove the `llm` path after 1 week
- [ ] Grafana shows p95 latency < 500 ms and empty-result rate < 15% over a 24-hour window
