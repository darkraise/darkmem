# Fine-Tuned Model Server Integration — Design Spec

## Goal

Integrate fine-tuned GLiNER (entity extraction) and REBEL (relationship extraction) models into the darkmem pipeline as a configurable alternative to LLM-based extraction. Models run in a separate Docker container with GPU access, called by the backend over HTTP.

## Architecture

Three components:

1. **Model Server** — Docker container running FastAPI, loads fine-tuned GLiNER + REBEL on GPU, exposes an extraction HTTP API.
2. **Backend Integration** — New `ModelExtractionService` that calls the model server, sits alongside existing `ExtractionService`. Pipeline selects which to use based on config.
3. **Configuration** — `extraction_mode` feature flag (`"llm"` | `"model"`) controls the extraction path. Switchable live via the existing config API.

### Data Flow (model mode)

```
Memory text
  -> Backend pipeline Phase 2
    -> HTTP POST model-server:8100/extract
      -> GLiNER: entities from text
      -> REBEL: relationships from text + entities
    <- {entities, relationships, memory_type: "fact"}
  -> clean_extraction() (existing dedup/normalization)
  -> Phases 3-5 unchanged (embedding, dedup, storage)
```

### Data Flow (LLM mode — unchanged)

```
Memory text
  -> Backend pipeline Phase 2
    -> ExtractionService.extract() via Ollama HTTP
    <- {entities, relationships, memory_type, importance}
  -> clean_extraction()
  -> Phases 3-5
```

Both modes produce the same output shape. Everything downstream of Phase 2 is unchanged.

---

## Component 1: Model Server

**Location:** `model-server/` at repo root

**Stack:** FastAPI, uvicorn, PyTorch, GLiNER, transformers

### Startup

- Loads fine-tuned GLiNER from `$GLINER_MODEL_PATH` onto GPU
- Loads fine-tuned REBEL from `$REBEL_MODEL_PATH` onto GPU
- Total VRAM: ~1.2 GB (GLiNER small ~0.2 GB + REBEL large ~1.0 GB)
- Fails fast if models not found or GPU unavailable

### API

```
GET /health
  Response: {
    "status": "ok",
    "models": {
      "gliner": "loaded",
      "rebel": "loaded"
    },
    "device": "cuda"
  }

POST /extract
  Request: {
    "text": "We switched from Flask to FastAPI for better performance.",
    "entity_types": ["technology", "service", "library", ...]
  }
  Response: {
    "entities": [
      {"name": "Flask", "type": "framework", "properties": {}},
      {"name": "FastAPI", "type": "framework", "properties": {}}
    ],
    "relationships": [
      {"source": "FastAPI", "target": "Flask", "type": "REPLACES", "weight": 0.8, "properties": {}}
    ],
    "memory_type": "fact"
  }
```

The response shape matches what `ExtractionService.extract()` returns.

### Extraction Logic

1. Run GLiNER `predict_entities(text, entity_types, threshold=0.5)` to get entity spans
2. Deduplicate entities by (name, type)
3. Format REBEL input: `"{text} | Entities: {ent1} ({type1}), {ent2} ({type2})"`
4. Run REBEL `generate()` to get linearized triplets
5. Parse triplets into relationship dicts
6. Return combined result with `memory_type: "fact"` (hardcoded for now)

### Docker

**Dockerfile** in `model-server/`:
- Base: `pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime`
- Install: `fastapi`, `uvicorn`, `gliner`, `transformers`
- Entrypoint: `uvicorn app:app --host 0.0.0.0 --port 8100`

**docker-compose.yml** in `model-server/`:
```yaml
services:
  model-server:
    build: .
    ports:
      - "8100:8100"
    volumes:
      - ../fine-tuning/models:/models:ro
    environment:
      - GLINER_MODEL_PATH=/models/gliner-darkmem/best
      - REBEL_MODEL_PATH=/models/rebel-darkmem/best
      - GLINER_THRESHOLD=0.5
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Models are read-only mounted from `fine-tuning/models/`. Retraining + container restart picks up new weights.

---

## Component 2: Backend Integration

### New File: `backend/app/services/model_extraction.py`

A thin async HTTP client class:

```python
class ModelExtractionService:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def extract(self, content: str) -> dict:
        """Call model server and return extraction result."""
        response = await self.client.post("/extract", json={
            "text": content,
            "entity_types": ENTITY_TYPES,
        })
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        """Check if model server is reachable and models are loaded."""
        ...
```

### Pipeline Change: `backend/app/services/pipeline.py`

In Phase 2, the pipeline checks `feature_flags.extraction_mode`:

- `"llm"`: calls `ExtractionService.extract()` (existing behavior)
- `"model"`: calls `ModelExtractionService.extract()`

Both return the same dict shape. `clean_extraction()` runs on the result either way.

### Lifecycle

`ModelExtractionService` is instantiated at app startup (like `ExtractionService`), injected via FastAPI dependency. The httpx client is shared across requests. Disposal on shutdown closes the client.

---

## Component 3: Configuration

### New Feature Flags

Added to `FeatureFlags` in `backend/app/config.py`:

| Flag | Type | Default | Description |
|---|---|---|---|
| `extraction_mode` | `str` | `"llm"` | `"llm"` or `"model"` |
| `model_server_url` | `str` | `"http://localhost:8100"` | Model server base URL |

### Live Switching

The existing `GET/PUT /api/v1/config/feature-flags` endpoint handles these. Switching `extraction_mode` from `"llm"` to `"model"` takes effect on the next memory processed — no restart needed.

---

## Component 4: Entity/Relationship Type Alignment

### Problem

Fine-tuning data uses 35 entity types and 16 relationship types. The backend currently recognizes 18 entity types and 14 relationship types. Types the model server returns that the backend doesn't recognize will be silently dropped or miscategorized.

### Solution

Expand the canonical type lists in `backend/app/services/extraction_tools.py`:

**New entity types to add:**
- `file`, `command`, `error`, `config`, `pattern`, `api`, `tool` (from ai_coding domain)
- `place`, `event`, `date`, `food`, `activity`, `goal`, `emotion`, `hobby` (from personal domain)
- `concept`, `theory`, `publication`, `method`, `finding`, `claim`, `field` (from knowledge domain)

**New relationship types to add:**
- `FIXES`, `CAUSES` (from ai_coding domain)

**Normalization map updates:**
Add mappings for any aliases the models might produce (e.g., `"tech"` -> `"technology"`).

### Entity types the backend already has that overlap:
`person`, `organization`, `technology`, `service`, `project`, `concept`, `algorithm`, `pattern`, `protocol`, `language`, `framework`, `library`, `database`, `platform`, `infrastructure` — these need no changes.

---

## Error Handling

- **Model server down:** `ModelExtractionService.extract()` catches connection errors and raises a descriptive exception. The pipeline's existing error handling records it as a pipeline failure (retryable).
- **Model server slow:** 30-second timeout on the httpx client. Configurable if needed.
- **Invalid response:** Basic validation that the response has `entities` and `relationships` keys before passing to `clean_extraction()`.

---

## Testing Strategy

- **Model server:** Unit tests with mocked models, integration test that loads real models and extracts from sample text.
- **Backend:** Unit test `ModelExtractionService` with httpx mock (no real model server needed). Test the pipeline toggle between modes.
- **End-to-end:** After deployment, run the existing 90-example gold corpus evaluation against the model server endpoint and compare F1 scores to the LLM baseline.

---

## Out of Scope (for this phase)

- Hybrid mode (GLiNER + LLM combined) — future enhancement
- Memory type classification in the model server — defaults to "fact"
- Importance scoring in the model server — not implemented, backend uses default
- Model hot-reloading without container restart
- Frontend UI changes to show extraction mode
