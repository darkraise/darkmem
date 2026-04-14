"""One-off emitter for shared-base batch-002 — ai_coding domain.

Same pattern as _emit_shared_batch_001.py; only ENTRIES changes.
Appends 50 rows to data/v2/shared/shared.jsonl with ids shared-00051..00100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 50  # batch-001 consumed shared-00001..00050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. problem: bug in file ---
    ("Found the bug in auth_middleware.py line 42: the token expiry check used UTC but the timestamp was local.", "problem", "ai_coding", False,
     [("auth_middleware.py", "file"), ("UTC", "protocol")],
     [],
     "where was the token expiry timezone bug found",
     "auth_middleware.py line 42 UTC timestamp bug"),
    # --- 2. decision: pattern suggestion ---
    ("Claude suggested a factory pattern for the extractors; went with that over the strategy pattern.", "decision", "ai_coding", False,
     [("factory pattern", "pattern"), ("strategy pattern", "pattern")],
     [("factory pattern", "strategy pattern", "REPLACES")],
     "why did we pick factory pattern over strategy for extractors",
     "factory vs strategy extractor design"),
    # --- 3. problem: dependency version ---
    ("Installed gliner-finetune and it required torch>=2.0 plus datasets>=2.14; upgraded both.", "problem", "ai_coding", False,
     [("gliner-finetune", "library"), ("torch", "library"), ("datasets", "library")],
     [("gliner-finetune", "torch", "DEPENDS_ON"), ("gliner-finetune", "datasets", "DEPENDS_ON")],
     "what were the version requirements for gliner-finetune",
     "gliner-finetune torch datasets version bump"),
    # --- 4. config: GPU offload ---
    ("Had to set num_gpu: 999 in the Ollama options to force full GPU offload for gemma4.", "problem", "ai_coding", False,
     [("num_gpu", "config"), ("Ollama", "service"), ("gemma4", "library")],
     [],
     "how do we force full GPU offload in Ollama for gemma4",
     "Ollama num_gpu 999 gemma4 full offload"),
    # --- 5. fact: async pattern ---
    ("The async context manager pattern in Python needs __aenter__ and __aexit__, not just __enter__.", "fact", "ai_coding", False,
     [("Python", "language"), ("__aenter__", "api"), ("__aexit__", "api"), ("__enter__", "api")],
     [],
     "which dunders does an async context manager require in Python",
     "async with-block dunder requirements"),
    # --- 6. problem: type error ---
    ("Hit TypeError: expected str got UUID; fixed by calling str() on memory_id before passing to the vector repo.", "problem", "ai_coding", False,
     [("TypeError", "error"), ("memory_id", "file")],
     [],
     "what caused the TypeError and how was it fixed",
     "TypeError str UUID memory_id cast fix"),
    # --- 7. fact: CUDA setup ---
    ("RTX 5060 requires CUDA 12.8; install torch with --index-url https://download.pytorch.org/whl/cu128.", "fact", "ai_coding", False,
     [("RTX 5060", "infrastructure"), ("CUDA 12.8", "platform"), ("torch", "library")],
     [("torch", "CUDA 12.8", "DEPENDS_ON")],
     "what CUDA and torch setup does the RTX 5060 need",
     "RTX 5060 CUDA 12.8 torch wheel index"),
    # --- 8. problem: ordering gotcha ---
    ("GLiNER on CUDA hangs if loaded before any Ollama embedding call; load GLiNER first or compute embeddings first.", "problem", "ai_coding", False,
     [("GLiNER", "library"), ("CUDA", "platform"), ("Ollama", "service")],
     [],
     "how to avoid the GLiNER CUDA hang with Ollama",
     "GLiNER Ollama load order CUDA deadlock"),
    # --- 9. milestone: feature shipped ---
    ("Finished implementing extraction pipeline v2 on 2026-04-12: tool calling, two-step flow, entity dedup, similarity edges, direction validation.", "milestone", "ai_coding", False,
     [("extraction pipeline v2", "project"), ("2026-04-12", "date")],
     [],
     "when did extraction pipeline v2 complete and what did it include",
     "extraction pipeline v2 completion scope"),
    # --- 10. noise ---
    ("Let me look at this file first before making any changes.", "fact", "noise", True, [], [], None, None),
    # --- 11. decision: test runner ---
    ("Adopted pytest-xdist for parallel test runs; the suite now finishes in under two minutes on eight cores.", "decision", "ai_coding", False,
     [("pytest-xdist", "library")],
     [],
     "why did we adopt pytest-xdist",
     "pytest-xdist parallel suite adoption"),
    # --- 12. problem: import cycle ---
    ("Circular import between models.py and schemas.py broke startup; fixed by moving shared types into types.py.", "problem", "ai_coding", False,
     [("models.py", "file"), ("schemas.py", "file"), ("types.py", "file")],
     [],
     "how was the circular import between models and schemas resolved",
     "circular import models schemas types split"),
    # --- 13. architecture: repo layout ---
    ("The backend follows a ports-and-adapters layout: services call repositories, which wrap database drivers.", "architecture", "ai_coding", False,
     [("ports-and-adapters", "pattern")],
     [],
     "how is the backend code organised",
     "ports-and-adapters backend layout"),
    # --- 14. problem: flaky test ---
    ("The flaky auth test was caused by freezegun not patching asyncio's loop time; switched to pytest-freezegun-async.", "problem", "ai_coding", False,
     [("freezegun", "library"), ("asyncio", "library"), ("pytest-freezegun-async", "library")],
     [("pytest-freezegun-async", "freezegun", "REPLACES")],
     "why was the auth test flaky and how was it fixed",
     "time mocking swap for event loop compatibility"),
    # --- 15. fact: linter ---
    ("ruff is configured with line length 100 and the pyupgrade ruleset.", "fact", "ai_coding", False,
     [("ruff", "tool")],
     [],
     "what line length and rules does ruff use here",
     "ruff line 100 pyupgrade config"),
    # --- 16. decision: pre-commit ---
    ("Removed black from pre-commit hooks; ruff format now handles formatting end-to-end.", "decision", "ai_coding", False,
     [("black", "tool"), ("ruff", "tool"), ("pre-commit", "tool")],
     [("ruff", "black", "REPLACES")],
     "why did we drop black from pre-commit",
     "black to ruff format pre-commit migration"),
    # --- 17. problem: CLI args ---
    ("argparse silently accepted --foo=bar as positional because nargs was misconfigured; switched to click.", "problem", "ai_coding", False,
     [("argparse", "library"), ("click", "library")],
     [("click", "argparse", "REPLACES")],
     "what argparse issue pushed us toward click",
     "argparse nargs silent positional click"),
    # --- 18. pattern: dependency injection ---
    ("Services take a settings object at construction so tests can inject an in-memory variant without monkey-patching.", "architecture", "ai_coding", False,
     [("settings", "config")],
     [],
     "how do services receive configuration for test injection",
     "settings constructor injection test variant"),
    # --- 19. problem: env var typo ---
    ("A typo in DATEBASE_URL (instead of DATABASE_URL) silently connected to the default dev instance during CI.", "problem", "ai_coding", False,
     [("DATEBASE_URL", "config"), ("DATABASE_URL", "config")],
     [],
     "what env var typo caused the wrong CI database connection",
     "DATEBASE_URL typo DATABASE_URL CI bug"),
    # --- 20. decision: snapshot tests ---
    ("Adopted syrupy for Python snapshot tests; reviewing snapshot diffs in PRs is faster than reading fixture files.", "decision", "ai_coding", False,
     [("syrupy", "library"), ("Python", "language")],
     [],
     "why did we adopt syrupy for snapshot tests",
     "syrupy snapshot test adoption"),
    # --- 21. problem: JSON schema ---
    ("Pydantic v2 rejected the old Config inner class; migrated model configs to ConfigDict calls.", "problem", "ai_coding", False,
     [("Pydantic v2", "library"), ("ConfigDict", "api")],
     [],
     "how did we migrate model configs to Pydantic v2",
     "Pydantic v2 Config class to ConfigDict migration"),
    # --- 22. reference: docs ---
    ("Structured concurrency behaviour follows PEP 678 and the Trio primer at trio.readthedocs.io.", "reference", "ai_coding", False,
     [("PEP 678", "publication"), ("Trio", "library")],
     [],
     "which references describe our structured concurrency model",
     "PEP 678 Trio structured concurrency"),
    # --- 23. architecture: logging ---
    ("All services emit structured JSON via structlog; the gateway injects a correlation_id header for tracing.", "architecture", "ai_coding", False,
     [("structlog", "library"), ("correlation_id", "config")],
     [],
     "how do services log and propagate trace ids",
     "structlog JSON correlation_id gateway"),
    # --- 24. problem: coroutine leak ---
    ("asyncio.gather swallowed exceptions from one coroutine, masking the leak; switched to TaskGroup for fail-fast.", "problem", "ai_coding", False,
     [("asyncio.gather", "api"), ("TaskGroup", "api")],
     [("TaskGroup", "asyncio.gather", "REPLACES")],
     "why did asyncio.gather mask the coroutine leak",
     "asyncio.gather TaskGroup fail-fast exception"),
    # --- 25. config: tokenizer ---
    ("The reranker tokenizer is loaded with use_fast=True to avoid the 20x slowdown on long inputs.", "fact", "ai_coding", False,
     [("reranker", "service"), ("use_fast", "config")],
     [],
     "why is use_fast set on the reranker tokenizer",
     "reranker tokenizer use_fast setting"),
    # --- 26. problem: path handling ---
    ("Windows paths broke the fine-tune loader when mixed with forward slashes; standardised on pathlib.Path everywhere.", "problem", "ai_coding", False,
     [("Windows", "platform"), ("pathlib.Path", "api")],
     [],
     "what fixed the cross-platform path issues in the fine-tune loader",
     "Windows path pathlib.Path normalisation"),
    # --- 27. decision: type checker ---
    ("Replaced mypy with pyright in CI; pyright's inference is stricter and the LSP integration is better.", "decision", "ai_coding", False,
     [("mypy", "tool"), ("pyright", "tool")],
     [("pyright", "mypy", "REPLACES")],
     "why did we swap mypy for pyright",
     "mypy to pyright type checker migration"),
    # --- 28. problem: memory growth ---
    ("Long-lived workers grew memory because tenacity stored retry metadata per call; bounded history via its maxsize option.", "problem", "ai_coding", False,
     [("tenacity", "library")],
     [],
     "what caused unbounded memory growth in the worker retries",
     "tenacity retry metadata memory bound"),
    # --- 29. architecture: feature flags ---
    ("Feature flags live in Unleash, evaluated client-side in each service with a 60-second cache.", "architecture", "ai_coding", False,
     [("Unleash", "service")],
     [],
     "where do feature flags live and how are they evaluated",
     "Unleash feature flag client cache"),
    # --- 30. problem: tokenizer mismatch ---
    ("Fine-tuned checkpoint failed to load because the tokenizer was saved separately; bundle both via save_pretrained.", "problem", "ai_coding", False,
     [("save_pretrained", "api")],
     [],
     "why did the fine-tuned checkpoint fail to load",
     "checkpoint tokenizer save_pretrained bundle"),
    # --- 31. preference: commits ---
    ("Team prefers small, scoped commits with Conventional Commits prefixes over large squash merges.", "preference", "ai_coding", False,
     [("Conventional Commits", "pattern")],
     [],
     "how does the team like commits structured",
     "Conventional Commits small scoped preference"),
    # --- 32. problem: migration order ---
    ("Alembic migrations ran in wrong order because revisions shared a down_revision; regenerated the chain with --splice.", "problem", "ai_coding", False,
     [("Alembic", "tool"), ("--splice", "command")],
     [],
     "how did we fix the Alembic migration chain",
     "Alembic down_revision splice repair"),
    # --- 33. decision: schema source ---
    ("Treating Pydantic models as the single source of truth; the OpenAPI spec is generated, not hand-written.", "decision", "ai_coding", False,
     [("Pydantic", "library"), ("OpenAPI", "protocol")],
     [("OpenAPI", "Pydantic", "DEPENDS_ON")],
     "what is the source of truth for API schemas",
     "Pydantic OpenAPI generation source of truth"),
    # --- 34. problem: flaky CI ---
    ("Intermittent CI failures traced to pytest randomisation exposing a global state leak in the legacy registry module.", "problem", "ai_coding", False,
     [("pytest", "library"), ("registry", "file")],
     [],
     "why were CI runs intermittently failing",
     "pytest randomisation registry global state leak"),
    # --- 35. noise ---
    ("Alright, moving on to the next item on the list.", "fact", "noise", True, [], [], None, None),
    # --- 36. decision: packaging ---
    ("Switched project packaging from setup.cfg to pyproject.toml; editable installs and metadata now live in one file.", "decision", "ai_coding", False,
     [("setup.cfg", "file"), ("pyproject.toml", "file")],
     [("pyproject.toml", "setup.cfg", "REPLACES")],
     "why did we move packaging metadata to pyproject.toml",
     "setup.cfg to pyproject.toml packaging"),
    # --- 37. problem: date parsing ---
    ("Parsing dates without tzinfo shifted events by the host TZ offset; forced timezone-aware datetimes at the edge.", "problem", "ai_coding", False,
     [("tzinfo", "api")],
     [],
     "how did we stop date parsing from shifting events by host TZ",
     "tzinfo timezone-aware datetime edge parsing"),
    # --- 38. architecture: tasks ---
    ("Background jobs use Dramatiq with a Redis broker; results get pushed to Postgres by a dedicated collector worker.", "architecture", "ai_coding", False,
     [("Dramatiq", "library"), ("Redis", "database"), ("Postgres", "database")],
     [("Dramatiq", "Redis", "DEPENDS_ON"), ("Dramatiq", "Postgres", "PRODUCES")],
     "how do background jobs run and persist results",
     "Dramatiq Redis Postgres job flow"),
    # --- 39. problem: rate limit ---
    ("Hit the 429 from OpenAI when backfilling embeddings; added a leaky-bucket wrapper with tokens-per-minute budget.", "problem", "ai_coding", False,
     [("429", "error"), ("OpenAI", "service")],
     [],
     "how did we handle the 429 during embedding backfill",
     "OpenAI 429 leaky-bucket embedding backfill"),
    # --- 40. fact: debugging ---
    ("breakpoint() respects PYTHONBREAKPOINT; setting it to IPython.embed drops into IPython instead of pdb.", "fact", "ai_coding", False,
     [("breakpoint()", "api"), ("PYTHONBREAKPOINT", "config"), ("IPython.embed", "api")],
     [],
     "how do you make breakpoint drop into IPython",
     "PYTHONBREAKPOINT IPython.embed breakpoint"),
    # --- 41. decision: test data ---
    ("Moved test fixtures from pytest conftest to polyfactory-generated factories for stronger variance coverage.", "decision", "ai_coding", False,
     [("conftest", "file"), ("polyfactory", "library")],
     [("polyfactory", "conftest", "REPLACES")],
     "why did we move test fixtures to polyfactory",
     "conftest to polyfactory test data migration"),
    # --- 42. problem: JSON truncation ---
    ("Long Ollama responses got truncated because the HTTP client's max_response was 1 MB; raised to 16 MB for the extractor path.", "problem", "ai_coding", False,
     [("Ollama", "service"), ("max_response", "config")],
     [],
     "why were long Ollama responses truncated",
     "Ollama HTTP client max_response truncation"),
    # --- 43. architecture: config loading ---
    ("Settings load from environment variables validated by pydantic-settings; .env files are used only in dev.", "architecture", "ai_coding", False,
     [("pydantic-settings", "library"), (".env", "file")],
     [("pydantic-settings", ".env", "USES")],
     "how does the app load configuration across environments",
     "pydantic-settings env dotenv loading"),
    # --- 44. problem: GPU memory ---
    ("CUDA OOM during fine-tuning was caused by gradient accumulation buffers; cut per-device batch size and raised accum steps.", "problem", "ai_coding", False,
     [("CUDA OOM", "error")],
     [],
     "how did we fix the CUDA OOM during fine-tuning",
     "CUDA OOM gradient accumulation batch size fix"),
    # --- 45. reference: api docs ---
    ("The Ollama HTTP API reference lives at github.com/ollama/ollama/blob/main/docs/api.md.", "reference", "ai_coding", False,
     [("Ollama", "service")],
     [],
     "where is the Ollama HTTP API reference",
     "Ollama API docs github location"),
    # --- 46. decision: notebooks ---
    ("Jupyter notebooks are kept out of source control; exploratory code is promoted to src/experiments.py once stable.", "decision", "ai_coding", False,
     [("Jupyter", "tool"), ("src/experiments.py", "file")],
     [],
     "how do we handle notebooks in this repo",
     "Jupyter notebooks experiments promotion policy"),
    # --- 47. problem: lock file ---
    ("poetry.lock conflicts after rebase kept breaking CI; moved to uv with a simpler requirements.txt lock workflow.", "problem", "ai_coding", False,
     [("poetry.lock", "file"), ("uv", "tool"), ("requirements.txt", "file")],
     [("uv", "poetry.lock", "REPLACES")],
     "why did we switch lock-file tooling after rebase conflicts",
     "poetry.lock to uv requirements lock"),
    # --- 48. preference: docstrings ---
    ("Code-facing docstrings stay short; long rationales belong in PR descriptions and commit bodies, not in the source.", "preference", "ai_coding", False,
     [("docstrings", "pattern")],
     [],
     "how does the team balance docstrings and PR descriptions",
     "where rationale belongs vs what stays in source"),
    # --- 49. problem: CORS ---
    ("CORS preflight failed because the gateway stripped X-Request-Id from allowed headers; added it back explicitly.", "problem", "ai_coding", False,
     [("CORS", "protocol"), ("X-Request-Id", "config")],
     [],
     "what caused the CORS preflight failure and the fix",
     "CORS preflight X-Request-Id allowed headers"),
    # --- 50. milestone: coverage ---
    ("Reached 90 percent line coverage on the backend on 2026-03-25; gate enforced in CI afterwards.", "milestone", "ai_coding", False,
     [("2026-03-25", "date")],
     [],
     "when did the backend cross 90 percent line coverage",
     "backend 90 percent coverage milestone"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("a", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
