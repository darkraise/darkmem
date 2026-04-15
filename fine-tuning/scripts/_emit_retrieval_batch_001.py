"""One-off emitter for retrieval top-up batch-001 — paraphrase kind, shared rows at line offsets 0..99.

Writes 100 rows to data/v2/retrieval/batch_001.tmp.jsonl with ids ret-00001..00100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_001.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 0
SHARED_OFFSET = 0
QUERY_KIND = "paraphrase"

# One query per source row, in the same order as the source rows.
QUERIES: list[str] = [
    # 001: Celery -> asyncio migration because Redis was only remaining dep
    "reason for dropping Celery in favour of native asyncio orchestration",
    # 002: pgvector over Qdrant since Postgres already in prod
    "rationale for picking pgvector given existing Postgres footprint",
    # 003: Kafka -> Flink -> ES + S3 pipeline
    "path events take through the streaming pipeline into storage",
    # 004: Node.js worker leak from unremoved EventEmitter listeners
    "root cause of the leak in the Node worker process",
    # 005: GitHub Actions over Jenkins for greenfield
    "reasoning behind choosing Actions instead of Jenkins on new repos",
    # 006: Redis Streams carries scheduler->worker tasks
    "transport linking the scheduler to the worker pool",
    # 007: GraphQL N+1 because DataLoader missing on author
    "source of the repeated queries on the author resolver",
    # 008: JS -> TS backend rewrite
    "motivation for porting the server code to TypeScript",
    # 009: HTTP caching defined in RFC 7234 / 5861
    "specifications describing cache semantics and stale-while-revalidate",
    # 010: 1M events/day on 2026-02-01 after batched writes
    "date the ingestion throughput first crossed a million events daily",
    # 011: Docker Compose -> Podman on dev laptops
    "driver behind replacing Compose with Podman on developer machines",
    # 012: Hot Postgres, cold Parquet S3, Trino unifies
    "storage tiering strategy and how we query across tiers",
    # 013: Reranker OOM because torch cached tensors per batch
    "why the reranker pod kept running out of memory",
    # 014: Loki replaces ELK; Grafana covers dashboards
    "reason the logging stack moved off Elastic onto Loki",
    # 015: Gateway verifies JWT from Keycloak, injects user header
    "how authenticated identity reaches downstream services from the edge",
    # 016: GLiNER-small ~50ms per 200 tokens on 5060
    "throughput figure for the small GLiNER model on our GPU",
    # 017: JSON -> Protobuf for internal contracts
    "why internal service messages shifted to a binary schema",
    # 018: Duplicate rows bypassed uniqueness without serializable tx
    "what allowed duplicate inserts to evade the unique constraint",
    # 019: Python Optional preferred over None defaults
    "team preference for expressing nullable parameters in Python",
    # 020: Memcached in front of profile service for read spikes
    "layer that shields the profile service during feed fan-out",
    # 021: v2.0 extraction pipeline shipped 2026-03-18 after GLiNER beat LLM
    "ship date of pipeline version two after the GLiNER win",
    # 022: NATS JetStream over AMQP for durable queuing
    "reason JetStream won out over AMQP for durable queues",
    # 023: mTLS failures after cert rotation due to cached CA in sidecar
    "cause of failed TLS handshakes following the cert refresh",
    # 024: PostgreSQL 16.2, pgvector 0.7.0
    "current production versions of the database and vector extension",
    # 025: OpenSearch + embedder + reranker hybrid retrieval
    "how lexical and semantic candidates come together in search",
    # 026: Terraform -> Pulumi so teams can use TypeScript
    "why infra code moved off Terraform onto Pulumi",
    # 027: 5xx caused by sidecar DNS cache ignoring low TTL
    "origin of the intermittent 5xx errors during rollouts",
    # 028: Airflow orchestrates dbt nightly to BigQuery
    "what drives the nightly analytics mart refresh",
    # 029: Alembic replaces raw SQL migrations for diff review
    "reason we swapped hand-written SQL for Alembic migrations",
    # 030: JVM G1 mixed GC caused tail latency; heap tuning fixed P99
    "what was behind the P99 spikes and how they were tamed",
    # 031: 10k API calls/min per tenant at gateway
    "per-tenant throttling ceiling enforced at the edge",
    # 032: Services pull short-lived creds from Vault, refresh on expiry
    "credential lifecycle for services at boot and runtime",
    # 033: HNSW over IVF, recall flat, build half time
    "why the team picked HNSW instead of the IVF index",
    # 034: UTF-8 errors from legacy CP1252 never converted at edge
    "source of encoding validation errors in the ingest path",
    # 035: Argo CD reconciles from Git, Flagger for canaries
    "tooling that reconciles cluster state and rolls out canaries",
    # 036: Stopped long-lived tokens; OIDC device flow + short-lived bearers
    "motivation for retiring static API tokens",
    # 037: Search API P99 200ms under ten terms
    "latency target for the search endpoint on small queries",
    # 038: Inventory deadlock fixed by sorting keys before update
    "how we eliminated the deadlock on inventory updates",
    # 039: Envoy WASM token bucket synced via Redis
    "where rate limiting executes and how state is shared",
    # 040: Team prefers table-driven tests in Go
    "how engineers like to shape their Go test files",
    # 041: noise
    "a quick note about pausing before editing",
    # 042: pg_dump -> WAL-E for PITR
    "why nightly dumps gave way to continuous WAL archiving",
    # 043: Cache stampede from zero TTL jitter; added 10% jitter
    "fix for the post-deploy thundering herd on the cache",
    # 044: Billing consumes Kafka, aggregates in ClickHouse, exports invoices
    "flow of usage data from events to invoices",
    # 045: Embedder outputs 768-dim vectors
    "dimensionality of the embeddings produced in production",
    # 046: graphite-cli for stacked PRs
    "tool adopted to ease stacked pull request workflows",
    # 047: DST bug: scheduler used local time not UTC
    "explanation for the hour-off execution around daylight saving",
    # 048: Debezium CDC Postgres -> Kafka
    "mechanism keeping downstream systems in sync with Postgres writes",
    # 049: noise
    "sign-off note for wrapping up the day",
    # 050: Webhooks follow Standard Webhooks spec
    "authoritative spec for how we sign outgoing webhooks",
    # 051: auth_middleware.py line 42 UTC/local timestamp bug
    "location of the timezone mismatch in the auth middleware",
    # 052: factory over strategy for extractors
    "design pattern selected for building extractor instances",
    # 053: gliner-finetune needs torch>=2.0 and datasets>=2.14
    "dependency bumps required to install the GLiNER fine-tune package",
    # 054: num_gpu:999 in Ollama to force full offload for gemma4
    "trick to push an entire gemma model onto GPU in Ollama",
    # 055: async context manager needs __aenter__ / __aexit__
    "dunder methods required for async with blocks",
    # 056: TypeError str vs UUID; str(memory_id) fix
    "remedy for the UUID versus string error on memory identifiers",
    # 057: RTX 5060 needs CUDA 12.8 torch wheel cu128
    "required CUDA toolkit and wheel index for the new card",
    # 058: GLiNER/Ollama CUDA load-order deadlock
    "workaround for the hang when GLiNER and Ollama share a GPU",
    # 059: Extraction pipeline v2 finished 2026-04-12 with 5 features
    "completion date and feature set for the second extraction revamp",
    # 060: noise
    "a brief statement about reviewing the file first",
    # 061: pytest-xdist adoption for parallel test runs
    "reason the test suite moved to parallel execution",
    # 062: Circular import models/schemas resolved by types.py
    "how the startup import cycle got untangled",
    # 063: Ports-and-adapters layout for backend
    "architectural style organising the backend codebase",
    # 064: freezegun -> pytest-freezegun-async for asyncio loop time
    "replacement chosen for the flaky asyncio time mocking",
    # 065: ruff line length 100 and pyupgrade ruleset
    "configured linter rules and maximum line width",
    # 066: Removed black; ruff format end-to-end
    "why black disappeared from the pre-commit pipeline",
    # 067: argparse nargs bug pushed switch to click
    "argument parser flaw that motivated moving to click",
    # 068: Services accept settings object for test injection
    "pattern letting tests swap configuration per service",
    # 069: DATEBASE_URL typo hit default dev database in CI
    "typo that caused CI to silently use the wrong database",
    # 070: syrupy adoption for Python snapshot testing
    "snapshot library chosen for reviewable Python diffs",
    # 071: Pydantic v2 Config class -> ConfigDict
    "change needed to bring model configs onto Pydantic 2",
    # 072: PEP 678 and Trio primer for structured concurrency
    "sources documenting our structured concurrency approach",
    # 073: structlog JSON plus gateway correlation_id
    "logging format and how trace identifiers travel between services",
    # 074: asyncio.gather swallowed exception; TaskGroup fail-fast
    "reason TaskGroup replaced gather for coroutine fan-out",
    # 075: reranker tokenizer use_fast=True avoids 20x slowdown
    "tokenizer flag keeping the reranker fast on long inputs",
    # 076: Windows paths broke loader; use pathlib.Path everywhere
    "remedy for cross-platform path trouble in the fine-tune loader",
    # 077: mypy -> pyright in CI
    "reason the project moved to pyright for type checking",
    # 078: tenacity retry metadata leak; bound via maxsize
    "fix for memory growth in long-running retry loops",
    # 079: Unleash feature flags with 60s client cache
    "feature flag service and its client refresh interval",
    # 080: Checkpoint failed without tokenizer; use save_pretrained
    "reason a fine-tuned checkpoint would not load correctly",
    # 081: Team prefers scoped Conventional Commits over squash
    "commit style the team favours for history",
    # 082: Alembic duplicate down_revision; regenerated with --splice
    "command that repaired the branched migration graph",
    # 083: Pydantic models are source of truth; OpenAPI generated
    "single source of truth for API schema definitions",
    # 084: pytest randomisation exposed registry global state leak
    "what pytest ordering surfaced in the legacy registry code",
    # 085: noise
    "a short remark about advancing to the next task",
    # 086: setup.cfg -> pyproject.toml
    "reason packaging metadata consolidated into one file",
    # 087: Naive datetime shifted by host TZ; forced tz-aware at edge
    "fix for timestamps drifting by the server timezone",
    # 088: Dramatiq with Redis broker, results to Postgres via collector
    "background job architecture and where results land",
    # 089: OpenAI 429 on backfill; leaky-bucket per-minute budget
    "how the embedding backfill coped with provider rate limits",
    # 090: PYTHONBREAKPOINT=IPython.embed uses IPython instead of pdb
    "way to swap the default debugger for an IPython shell",
    # 091: conftest fixtures -> polyfactory factories
    "reason fixture generation moved to a factory library",
    # 092: Ollama truncation due to 1MB max_response; raised to 16MB
    "why responses from Ollama were getting cut short",
    # 093: pydantic-settings loads env, .env dev only
    "configuration loading mechanism across environments",
    # 094: CUDA OOM from gradient accum buffers; smaller batch, more steps
    "how the fine-tune job stopped running out of GPU memory",
    # 095: Ollama HTTP API docs on github
    "where the Ollama REST endpoint documentation is hosted",
    # 096: Notebooks out of source control; promote to src/experiments.py
    "repository policy on committing Jupyter notebooks",
    # 097: poetry.lock conflicts -> uv + requirements.txt
    "reason dependency locking moved off poetry",
    # 098: Short docstrings; rationale in PR/commit bodies
    "where the team wants long design reasoning to live",
    # 099: CORS preflight stripped X-Request-Id; restored in allowed headers
    "why the preflight check started rejecting tracing headers",
    # 100: 90% backend coverage on 2026-03-25; CI gate added
    "when the server code first hit ninety percent test coverage",
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    sources = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, (query, src) in enumerate(zip(QUERIES, sources), start=1):
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
